"""Atomic persistence for Level3 S7 campaign artifacts.

Deliberately duplicated from scripts/level3_s6_campaign/outputs.py's own
generic canonical-JSON/atomic-write/reload-and-verify primitives rather
than imported, per the same isolation decision the S4/S5/S6 campaign
layers themselves made from their predecessors.

NO_IMPLICIT_RESUME: write_case_result and write_campaign_summary both
refuse (raise) if an artifact already exists at their destination path.
Campaign artifacts live under `results/level3/level3-s7-truncation-
extension-v1/` (gitignored by default, like every non-frozen results/
entry -- only the already-frozen reference campaigns are versioned).
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from cosmobox.level3 import s7_serialization

REPOSITORY_IDENTITY = "ioio2995/cosmobox"


def canonical_json_bytes(document: dict) -> bytes:
    """UTF-8, sort_keys, ensure_ascii, allow_nan=False, single trailing
    newline -- the same convention already used by
    scripts/level3_s6_campaign/outputs.py."""
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def atomic_write_json(path: Path, document: dict) -> None:
    """Write `document` to `path` atomically: serialize to a sibling
    temp file (same directory, so os.rename stays on one filesystem),
    fsync it, then rename over the destination. The temp file is removed
    on any failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(document)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def campaign_output_dir(output_root: Path, campaign_id: str) -> Path:
    return Path(output_root) / campaign_id


def campaign_summary_path(output_root: Path, campaign_id: str) -> Path:
    return campaign_output_dir(output_root, campaign_id) / "campaign-summary.json"


def campaign_manifest_path(output_root: Path, campaign_id: str) -> Path:
    return campaign_output_dir(output_root, campaign_id) / "manifest.json"


def case_artifact_path(output_root: Path, campaign_id: str, geometry: str, spin: int) -> Path:
    return campaign_output_dir(output_root, campaign_id) / "cases" / f"{geometry}-S{spin}.json"


class CampaignSummaryAlreadyExists(RuntimeError):
    """Raised by write_campaign_summary when campaign-summary.json
    already exists at the destination path."""


class CaseArtifactAlreadyExists(RuntimeError):
    """Raised by write_case_result when a case-result artifact already
    exists at the destination path -- compatible or not."""


class CampaignManifestAlreadyExists(RuntimeError):
    """Raised by write_campaign_manifest when manifest.json already
    exists at the destination path -- compatible or not."""


class CaseArtifactIntegrityError(ValueError):
    """Raised by load_and_verify_case_result (and, transitively,
    verify_case_artifacts_share_provenance) for any parse, schema, or
    provenance-consistency failure of a persisted Level3 S7 case-result
    artifact."""


def write_campaign_summary(output_root: Path, campaign_id: str, document: dict) -> Path:
    """Write campaign-summary.json atomically. Its mere existence on disk
    is the campaign's COMPLETE marker. Raises CampaignSummaryAlreadyExists
    (never silently overwriting) if one is already present."""
    path = campaign_summary_path(output_root, campaign_id)
    if path.exists():
        raise CampaignSummaryAlreadyExists(f"campaign-summary.json already exists at {path}; refusing to overwrite")
    atomic_write_json(path, document)
    return path


def write_campaign_manifest(output_root: Path, campaign_id: str, raw_manifest: dict) -> Path:
    """Write a durable snapshot of the exact pre-registered manifest
    content (Level3S7Manifest.raw) that drove this campaign to
    manifest.json, atomically. Raises CampaignManifestAlreadyExists
    (never silently overwriting) if one is already present."""
    path = campaign_manifest_path(output_root, campaign_id)
    if path.exists():
        raise CampaignManifestAlreadyExists(f"manifest.json already exists at {path}; refusing to overwrite")
    atomic_write_json(path, raw_manifest)
    return path


def write_case_result(output_root: Path, campaign_id: str, geometry: str, spin: int, document: dict) -> Path:
    """Write one case's case-result document atomically to
    cases/<geometry>-S<spin>.json. Raises CaseArtifactAlreadyExists
    (never silently overwriting) if one is already present at that path."""
    path = case_artifact_path(output_root, campaign_id, geometry, spin)
    if path.exists():
        raise CaseArtifactAlreadyExists(f"case-result artifact already exists at {path}; refusing to overwrite")
    atomic_write_json(path, document)
    return path


def load_and_verify_case_result(
    output_root: Path,
    campaign_id: str,
    geometry: str,
    spin: int,
    *,
    manifest_fingerprint: str,
    repository_commit: str,
) -> dict:
    """Read cases/<geometry>-S<spin>.json, verify it parses, verify it is
    schema-valid against schemas/level3/s7-case-result-v1.schema.json
    (s7_serialization.validate_case_result_document), and verify its own
    campaign_id/manifest_fingerprint/repository/repository_commit/
    geometry/spin all match what the caller currently expects. Raises
    CaseArtifactIntegrityError on any failure."""
    path = case_artifact_path(output_root, campaign_id, geometry, spin)
    if not path.exists():
        raise CaseArtifactIntegrityError(f"missing case-result artifact for ({geometry!r}, {spin!r}) under {path}")

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaseArtifactIntegrityError(
            f"case-result artifact for ({geometry!r}, {spin!r}) could not be parsed: {exc}"
        ) from exc

    try:
        s7_serialization.validate_case_result_document(document)
    except ValueError as exc:
        raise CaseArtifactIntegrityError(
            f"case-result artifact for ({geometry!r}, {spin!r}) failed schema validation: {exc}"
        ) from exc

    expected = {
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository": REPOSITORY_IDENTITY,
        "repository_commit": repository_commit,
        "geometry": geometry,
        "spin": spin,
    }
    for key, expected_value in expected.items():
        if document[key] != expected_value:
            raise CaseArtifactIntegrityError(
                f"case-result artifact for ({geometry!r}, {spin!r}) has {key} ({document[key]!r}) that does "
                f"not match expected ({expected_value!r})"
            )

    return document


def verify_case_artifacts_share_provenance(
    output_root: Path,
    campaign_id: str,
    case_keys,
    *,
    manifest_fingerprint: str,
    repository_commit: str,
) -> tuple[dict, ...]:
    """Reloads and integrity-checks every (geometry, spin) case artifact
    in `case_keys` via load_and_verify_case_result, each required to
    share exactly campaign_id/manifest_fingerprint/repository_commit with
    the values passed here. Raises CaseArtifactIntegrityError on the
    first mismatch."""
    return tuple(
        load_and_verify_case_result(
            output_root,
            campaign_id,
            geometry,
            spin,
            manifest_fingerprint=manifest_fingerprint,
            repository_commit=repository_commit,
        )
        for geometry, spin in case_keys
    )
