"""Atomic per-case persistence for the Level1C campaign. Lot 1C-8c.

Persists exactly one case's already-produced Level1CCaseExecutionResult
(scripts.level1c_campaign.runner.run_level1c_case, unmodified by this
module) to `<output_dir>/runs/<case_id>/{records.jsonl,run.json}`,
mirroring scripts/level1b_campaign/outputs.py's own convention and
atomic-write pattern (duplicated here rather than imported: it is a
small, purely generic OS-level utility with zero scientific content,
and scripts.level1c_campaign is a separate package from
scripts.level1b_campaign, so importing its private helper across
packages would be an unusual dependency for a 15-line utility).

run.json here is a Level1CCaseRunArtifact (schemas/level1c/
case-run-v1.schema.json), never the Level1B run.json shape --
target_selections is persisted exclusively here
(TARGET_SELECTION_PERSISTENCE=CASE_RUN_ARTIFACT_ONLY, 1C-8b-fix), never
inside records.jsonl.

This module introduces no scientific logic: it never recomputes an
observable, never re-derives a payload, and never repairs a partially
valid run silently. It does not loop over a campaign, does not launch
one, and does not touch tracking/response/non-regression-gate concerns
-- see the package docstring for the exact authorized scope.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from experiments.level1.planning import CampaignCaseSpec
from experiments.level1c.case_artifact import (
    FAILED,
    RESOURCE_GUARDRAIL_EXCEEDED,
    Level1CCaseRunArtifact,
    canonical_json_bytes,
    required_targets_are_satisfied,
    to_json_dict,
    validate_case_run_document,
    validate_target_selections_match_manifest,
)
from experiments.level1c.manifest import Level1CManifest
from experiments.level1c.result_schema import validate_result_record

from .runner import Level1CCaseExecutionResult

_FAILURE_RUN_STATUSES = (FAILED, RESOURCE_GUARDRAIL_EXCEEDED)


def _case_run_dir(output_dir: Path, case_id: str) -> Path:
    return output_dir / "runs" / case_id


def _canonical_document_line_bytes(document: dict) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically -- same pattern as
    scripts/level1b_campaign/outputs.py's own _atomic_write_bytes: a
    uniquely-named temporary file in the same directory, flushed and
    fsync'd before an atomic os.replace, then a best-effort directory
    fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def write_case_success(
    output_dir: Path,
    manifest: Level1CManifest,
    case: CampaignCaseSpec,
    result: Level1CCaseExecutionResult,
    *,
    repository_commit: str,
) -> None:
    """Persist a successful Level1CCaseExecutionResult. Defensively
    re-verified before any write (never recomputing an observable, only
    re-checking structural facts already guaranteed upstream): every
    document is re-validated against result-record-v1, and
    target_selections is re-cross-checked against the manifest's own
    target list for this case's geometry -- the exact boundary where
    results leave memory and become a durable, load-bearing artifact.

    normative_case_valid (RUN_STATUS_SEMANTICS=TECHNICAL_EXECUTION_
    STATUS, 1C-8c-fix) is always computed and persisted here, whatever
    its value: a normatively invalid case (e.g. a REQUIRED target
    ambiguous or selected on a partial_subspace group) is never refused
    -- its artifact remains available for diagnosis, exactly like any
    other successful run. This function never converts a normative gate
    failure into a write refusal or a different run_status."""
    if not result.documents:
        raise ValueError("result.documents must be non-empty for a successful run")
    if result.case_id != case.case_id:
        raise ValueError(f"result.case_id ({result.case_id!r}) does not match case.case_id ({case.case_id!r})")

    for document in result.documents:
        validate_result_record(document)

    validate_target_selections_match_manifest(result.target_selections, manifest.target_groups[case.geometry])
    normative_case_valid = required_targets_are_satisfied(result.target_selections)

    records_bytes = b"".join(_canonical_document_line_bytes(document) for document in result.documents)
    records_sha256 = hashlib.sha256(records_bytes).hexdigest()

    artifact = Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id=manifest.campaign_id,
        manifest_fingerprint=manifest.fingerprint,
        repository_commit=repository_commit,
        case_id=case.case_id,
        geometry=case.geometry,
        spin=case.spin,
        hamiltonian_case_id=case.hamiltonian_case_id,
        sector_id=case.sector_id,
        spectral_window=case.spectral_window,
        run_status="success",
        target_selections=result.target_selections,
        records_sha256=records_sha256,
        record_count=len(result.documents),
        normative_case_valid=normative_case_valid,
    )
    run_document = to_json_dict(artifact)
    validate_case_run_document(run_document)

    case_dir = _case_run_dir(output_dir, case.case_id)
    _atomic_write_bytes(case_dir / "records.jsonl", records_bytes)
    _atomic_write_bytes(case_dir / "run.json", canonical_json_bytes(run_document))


def write_case_failure(
    output_dir: Path,
    manifest: Level1CManifest,
    case: CampaignCaseSpec,
    *,
    repository_commit: str,
    run_status: str,
) -> None:
    """Persist a failed or resource-guardrail-exceeded case: run.json
    only, never records.jsonl -- no synthetic record and no fabricated
    target_selections are ever invented to fill one, and
    normative_case_valid is persisted as None (NOT_EVALUATED, never
    False): a technical failure was never scientifically evaluated. If a records.jsonl
    from an earlier (successful) run of this case_id still exists on
    disk, it is removed first, so it can never be mistaken for this
    failed run's own results."""
    if run_status not in _FAILURE_RUN_STATUSES:
        raise ValueError(f"run_status must be one of {_FAILURE_RUN_STATUSES}, got {run_status!r}")

    case_dir = _case_run_dir(output_dir, case.case_id)
    stale_records_path = case_dir / "records.jsonl"
    if stale_records_path.exists():
        stale_records_path.unlink()

    artifact = Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id=manifest.campaign_id,
        manifest_fingerprint=manifest.fingerprint,
        repository_commit=repository_commit,
        case_id=case.case_id,
        geometry=case.geometry,
        spin=case.spin,
        hamiltonian_case_id=case.hamiltonian_case_id,
        sector_id=case.sector_id,
        spectral_window=case.spectral_window,
        run_status=run_status,
        target_selections=(),
        records_sha256=None,
        record_count=0,
        normative_case_valid=None,
    )
    run_document = to_json_dict(artifact)
    validate_case_run_document(run_document)
    _atomic_write_bytes(case_dir / "run.json", canonical_json_bytes(run_document))


def load_case_records(case_dir: Path) -> tuple[dict, ...]:
    """Load records.jsonl from `case_dir` into a tuple of documents, in
    file order. Mirrors scripts/level1b_campaign/outputs.py's own
    load_case_records exactly."""
    records_path = case_dir / "records.jsonl"
    if not records_path.exists():
        raise ValueError(f"{records_path} does not exist")

    text = records_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    documents: list[dict] = []
    for index, line in enumerate(lines):
        if line == "":
            raise ValueError(f"records.jsonl line {index} is empty")
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"records.jsonl line {index} is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"records.jsonl line {index} is not a JSON object, got {type(parsed)}")
        documents.append(parsed)

    return tuple(documents)
