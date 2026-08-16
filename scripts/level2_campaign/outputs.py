"""Atomic persistence for Level2 campaign artifacts.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE (campaign-summary.json) extended by
L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER (per-case artifacts under
cases/<geometry>-S<spin>.json, the manifest snapshot, and the shared
reload/integrity-check primitive).

Mirrors experiments/level1c/case_artifact.py::canonical_json_bytes'
canonical JSON convention (sort_keys, indent=2, ensure_ascii,
allow_nan=False, single trailing newline) and scripts/level1c_campaign/
outputs.py's atomic-write pattern (write to a sibling temp file, then
os.rename -- atomic on the same filesystem) and its own
load_and_verify_case_run_document/load_and_verify_case_records split
(schema validity, then own-identity check, then external-provenance
check against what the caller currently expects). Per docs/governance/
current-task.md, campaign artifacts live under `results/level2/...`,
never under `experiments/level2/` (which is library code only, .gitignore
already excludes `results/`).

NO_IMPLICIT_RESUME (L2-E2, conservative first normative runner): both
write_case_result and write_campaign_summary refuse (raise) if an
artifact already exists at their destination path -- no overwrite, no
merge, no automatic deletion of an existing scientific artifact. A
caller that genuinely wants to re-run a campaign must choose a new
output directory or campaign_id itself; this module never decides that
for them.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from cosmobox.level2 import serialization


def canonical_json_bytes(document: dict) -> bytes:
    """UTF-8, sort_keys, ensure_ascii, allow_nan=False, single trailing
    newline -- the same convention already used by
    experiments/level1c/case_artifact.py::canonical_json_bytes."""
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def atomic_write_json(path: Path, document: dict) -> None:
    """Write `document` to `path` atomically: serialize to a sibling
    temp file (same directory, so os.rename stays on one filesystem),
    fsync it, then rename over the destination. `path`'s parent
    directory is created if needed. The temp file is removed on any
    failure -- a partially written file is never left where a reader
    could mistake it for `path`."""
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
    already exists at the destination path. NO_IMPLICIT_RESUME (see this
    module's own docstring): a campaign that has already been finalized
    is never silently re-finalized or overwritten."""


class CaseArtifactAlreadyExists(RuntimeError):
    """Raised by write_case_result when a case-result artifact already
    exists at the destination path -- compatible or not. NO_IMPLICIT_
    RESUME (see this module's own docstring): no automatic partial-resume
    merging is attempted for this first normative runner."""


class CaseArtifactIntegrityError(ValueError):
    """Raised by load_and_verify_case_result (and, transitively,
    verify_case_artifacts_share_provenance) for any parse, schema, or
    provenance-consistency failure of a persisted Level2 case-result
    artifact."""


def write_campaign_summary(output_root: Path, campaign_id: str, document: dict) -> Path:
    """Write campaign-summary.json atomically. Callers must only invoke
    this once campaign completeness has already been fully established
    (gates.validate_campaign_completeness) and `document` has already
    been schema-validated (serialization.campaign_summary_payload does
    this itself) -- this function performs no completeness or schema
    check of its own; it is a pure persistence primitive. Its mere
    existence on disk is the campaign's COMPLETE marker: a campaign that
    fails or is interrupted before this call leaves no
    campaign-summary.json at all. Raises CampaignSummaryAlreadyExists
    (never silently overwriting) if one is already present."""
    path = campaign_summary_path(output_root, campaign_id)
    if path.exists():
        raise CampaignSummaryAlreadyExists(f"campaign-summary.json already exists at {path}; refusing to overwrite")
    atomic_write_json(path, document)
    return path


def write_campaign_manifest(output_root: Path, campaign_id: str, raw_manifest: dict) -> Path:
    """Write a durable snapshot of the exact pre-registered manifest
    content (Level2Manifest.raw) that drove this campaign to
    manifest.json, atomically. A self-contained reproducibility record
    alongside the campaign's own outputs -- mirrors the manifest.json
    convention already established by scripts/level0_reference_campaign
    and scripts/level0_symmetry_campaign. Every case-result/
    campaign-summary document already carries manifest_fingerprint
    (the SHA-256 of this exact content), so this snapshot is a
    convenience for a reader, not the sole integrity anchor."""
    path = campaign_manifest_path(output_root, campaign_id)
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
    schema-valid against schemas/level2/case-result-v1.schema.json
    (serialization.validate_case_result_document -- never a second,
    duplicated jsonschema call), and verify its own campaign_id/
    manifest_fingerprint/repository_commit/geometry/spin all match what
    the caller currently expects. Raises CaseArtifactIntegrityError on
    any failure. This is the single, shared integrity core: both the
    campaign runner and any later finalizer/diagnostic tool must call
    this rather than duplicating parse/schema/provenance logic."""
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
        serialization.validate_case_result_document(document)
    except ValueError as exc:
        raise CaseArtifactIntegrityError(
            f"case-result artifact for ({geometry!r}, {spin!r}) failed schema validation: {exc}"
        ) from exc

    expected = {
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
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
    share exactly campaign_id/manifest_fingerprint/repository_commit
    with the values passed here. Raises CaseArtifactIntegrityError on
    the first mismatch -- a campaign whose persisted case artifacts do
    not all share one provenance can never reach campaign-summary
    finalization. Returns the loaded documents in `case_keys` order."""
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
