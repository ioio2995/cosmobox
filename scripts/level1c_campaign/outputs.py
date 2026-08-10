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

load_and_verify_case_artifact (1C-8e) is the shared, read-only
integrity core reused by both scripts.level1c_baseline_gate.gate
(1C-8d-fix) and scripts.level1c_tracking (1C-8e): it verifies run.json
schema validity, run.json's own case_id, records.jsonl's exact-byte
SHA-256 against run.json's records_sha256, record_count, per-record
schema validity and campaign/manifest/repository provenance, and each
record's scientific identity (geometry/spin/sector/Hamiltonian) against
the exact CampaignCaseSpec build_level1c_campaign_plan(manifest)
produces for that case_id. It deliberately does NOT check run_status or
normative_case_valid -- callers apply their own validity gating on top
(the baseline gate requires run_status=success AND normative_case_
valid=true; tracking's perturbed side requires only run_status=success,
section 1C-8e "PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE").
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

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
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.result_schema import validate_result_record

from .runner import Level1CCaseExecutionResult

_FAILURE_RUN_STATUSES = (FAILED, RESOURCE_GUARDRAIL_EXCEEDED)


class Level1CArtifactIntegrityError(RuntimeError):
    """Raised by load_and_verify_case_artifact for any integrity or
    provenance failure of a persisted Level1C case artifact -- never a
    bare exception. Callers (scripts.level1c_baseline_gate.gate,
    scripts.level1c_tracking) catch this and re-raise their own,
    module-scoped exception type, preserving the exact message."""


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


def _case_hamiltonian_identity_tuple(case: CampaignCaseSpec) -> tuple:
    """Generic, non-holdout-specific tuple representation of a
    CampaignCaseSpec's own Hamiltonian, for comparison against a
    document's identity.hamiltonian."""
    parameters = case.hamiltonian_parameters
    h_is_zero = all(bool((matrix == 0).all()) for matrix in parameters.h)
    return (
        tuple(float(value) for value in parameters.J),
        h_is_zero,
        float(parameters.t),
        float(parameters.g_E),
        float(parameters.K),
    )


def _document_hamiltonian_identity_tuple(hamiltonian: Mapping) -> tuple:
    return (
        tuple(float(value) for value in hamiltonian["J"]),
        hamiltonian["h_is_zero"],
        float(hamiltonian["t"]),
        float(hamiltonian["g_E"]),
        float(hamiltonian["K"]),
    )


def _expected_campaign_case_spec(level1c_manifest: Level1CManifest, case_id: str) -> CampaignCaseSpec:
    """The exact CampaignCaseSpec build_level1c_campaign_plan(manifest)
    itself produces for `case_id` -- never a heuristic reconstruction.
    Raises Level1CArtifactIntegrityError if case_id is not one of the
    manifest's own planned cases."""
    for case in build_level1c_campaign_plan(level1c_manifest):
        if case.case_id == case_id:
            return case
    raise Level1CArtifactIntegrityError(f"case_id {case_id!r} is not present in build_level1c_campaign_plan(level1c_manifest)")


def _require_record_matches_expected_case(record: Mapping, expected_case: CampaignCaseSpec, *, case_id: str, line_index: int) -> None:
    identity = record["identity"]
    if identity["geometry"] != expected_case.geometry:
        raise Level1CArtifactIntegrityError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.geometry "
            f"({identity['geometry']!r}) does not match the expected case's geometry ({expected_case.geometry!r})"
        )
    if identity["spin"] != expected_case.spin:
        raise Level1CArtifactIntegrityError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.spin ({identity['spin']!r}) "
            f"does not match the expected case's spin ({expected_case.spin!r})"
        )
    if identity["sector"] != expected_case.sector_id:
        raise Level1CArtifactIntegrityError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.sector ({identity['sector']!r}) "
            f"does not match the expected case's sector_id ({expected_case.sector_id!r})"
        )
    if _document_hamiltonian_identity_tuple(identity["hamiltonian"]) != _case_hamiltonian_identity_tuple(expected_case):
        raise Level1CArtifactIntegrityError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.hamiltonian does not match the "
            "expected case's own hamiltonian_parameters"
        )


def load_and_verify_case_run_document(output_dir: Path, case_id: str) -> dict:
    """Reads and schema-validates runs/<case_id>/run.json, and verifies
    its own case_id matches the requested one. The FIRST step of the
    frozen chain (case_id -> run_status -> normative_case_valid ->
    records_sha256 -> record_count -> per-record provenance -> exact
    CampaignCaseSpec scientific identity, 1C-8d-fix): deliberately
    split from load_and_verify_case_records so a caller can apply its
    own run_status/normative_case_valid gating (each caller's own
    validity semantics) BEFORE the heavier records.jsonl integrity
    checks ever run -- never after, so a technically-failed or
    normatively-invalid case is rejected before its (possibly absent or
    irrelevant) records.jsonl is ever touched."""
    case_dir = Path(output_dir) / "runs" / case_id
    run_path = case_dir / "run.json"
    if not run_path.exists():
        raise Level1CArtifactIntegrityError(f"missing Level1C run.json for case {case_id!r} under {output_dir}")

    try:
        run_document = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Level1CArtifactIntegrityError(f"Level1C run.json for case {case_id!r} could not be parsed: {exc}") from exc

    validate_case_run_document(run_document)

    if run_document["case_id"] != case_id:
        raise Level1CArtifactIntegrityError(
            f"run.json case_id ({run_document['case_id']!r}) does not match the requested case_id ({case_id!r})"
        )

    return run_document


def load_and_verify_case_records(
    output_dir: Path, case_id: str, run_document: Mapping, *, level1c_manifest: Level1CManifest
) -> tuple[dict, ...]:
    """The SECOND step of the frozen chain: records.jsonl's exact-byte
    SHA-256 against run_document's own records_sha256 (never
    reconstructed from parsed JSON), record_count, per-record schema
    validity and campaign/manifest/repository provenance consistency
    with run_document, and per-record scientific identity consistency
    with the exact CampaignCaseSpec build_level1c_campaign_plan(manifest)
    produces for this case_id. Callers must call load_and_verify_case_
    run_document first and apply their own run_status/normative_case_
    valid gating before calling this."""
    case_dir = Path(output_dir) / "runs" / case_id
    records_path = case_dir / "records.jsonl"
    if not records_path.exists():
        raise Level1CArtifactIntegrityError(f"missing records.jsonl for case {case_id!r} under {output_dir}")

    try:
        records_bytes = records_path.read_bytes()
    except OSError as exc:
        raise Level1CArtifactIntegrityError(f"records.jsonl for case {case_id!r} could not be read: {exc}") from exc

    actual_sha256 = hashlib.sha256(records_bytes).hexdigest()
    if actual_sha256 != run_document["records_sha256"]:
        raise Level1CArtifactIntegrityError(
            f"records.jsonl for case {case_id!r} SHA-256 ({actual_sha256}) does not match run.json "
            f"records_sha256 ({run_document['records_sha256']!r}) -- integrity check failed on the exact "
            "persisted bytes, never reconstructed from parsed JSON"
        )

    try:
        records = load_case_records(case_dir)
    except ValueError as exc:
        raise Level1CArtifactIntegrityError(f"records.jsonl for case {case_id!r} could not be loaded: {exc}") from exc

    if len(records) != run_document["record_count"]:
        raise Level1CArtifactIntegrityError(
            f"records.jsonl for case {case_id!r} has {len(records)} document(s), run.json record_count is "
            f"{run_document['record_count']!r}"
        )

    expected_case = _expected_campaign_case_spec(level1c_manifest, case_id)

    for index, record in enumerate(records):
        try:
            validate_result_record(record)
        except ValueError as exc:
            raise Level1CArtifactIntegrityError(f"records.jsonl line {index} for case {case_id!r} failed schema validation: {exc}") from exc
        for key in ("campaign_id", "manifest_fingerprint", "repository_commit"):
            if record[key] != run_document[key]:
                raise Level1CArtifactIntegrityError(
                    f"records.jsonl line {index} for case {case_id!r} has {key} ({record[key]!r}) that does not "
                    f"match run.json's own {key} ({run_document[key]!r})"
                )
        _require_record_matches_expected_case(record, expected_case, case_id=case_id, line_index=index)

    return tuple(records)


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


# ---------------------------------------------------------------------------
# Resume validation for the PHASE_P campaign loop (1C-8h)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Level1CCaseRunValidation:
    """Whether an existing runs/<case_id>/ directory is exactly reusable
    for PHASE_P (never re-executed). `is_valid=True` iff every reuse
    condition holds; `reason` is set if and only if `is_valid` is False
    -- never an exception for a simple "not reusable" outcome (mirrors
    scripts.level1b_campaign.outputs.CaseRunValidation's own contract)."""

    is_valid: bool
    reason: str | None

    def __post_init__(self) -> None:
        if self.is_valid != (self.reason is None):
            raise ValueError("reason must be set if and only if is_valid is False")


def validate_existing_level1c_case_run(
    output_dir: Path, case_id: str, *, level1c_manifest: Level1CManifest, repository_commit: str
) -> Level1CCaseRunValidation:
    """Answers exactly: does `<output_dir>/runs/<case_id>/` already hold
    an exactly-reusable PHASE_P run for (case_id, level1c_manifest.
    campaign_id, level1c_manifest.fingerprint, repository_commit)? Never
    re-executes run_level1c_case, never raises for a simple "not
    reusable" outcome -- every failure mode returns
    Level1CCaseRunValidation(False, reason) instead.

    Reuses load_and_verify_case_run_document/load_and_verify_case_records
    verbatim (never a third JSON/JSONL parser) for schema validity,
    exact-byte SHA-256, record_count, and per-record scientific identity.
    Those two shared functions deliberately verify only INTERNAL
    consistency (records agree with their own run.json; run.json's own
    case_id matches the directory) -- neither ever compares campaign_id/
    manifest_fingerprint/repository_commit against what THIS caller
    currently expects. That external provenance check is added here
    explicitly (the same 3-line pattern already applied twice by
    scripts.level1c_tracking.tracking's own load_baseline_for_tracking/
    load_perturbed_for_tracking) -- without it, a run.json produced under
    a different campaign_id/manifest_fingerprint/repository_commit would
    be wrongly treated as reusable.

    run_status must be 'success' -- any other value (including
    'failed'/'resource_guardrail_exceeded') is simply not reusable, and
    is retried unconditionally on the next campaign loop pass (no
    terminal failure state; RUN_STATUS_SEMANTICS=TECHNICAL_EXECUTION_
    STATUS, 1C-8c-fix). normative_case_valid is NEVER consulted here: a
    technically successful, structurally intact run is a valid,
    immutable PHASE_P artifact regardless of its normative verdict --
    that verdict belongs exclusively to downstream consumers (the
    baseline gate, tracking) which apply their own, stricter criteria on
    top of this same artifact, never conflated with PHASE_P's own resume
    criterion.
    """
    try:
        run_document = load_and_verify_case_run_document(output_dir, case_id)
    except Level1CArtifactIntegrityError as exc:
        return Level1CCaseRunValidation(is_valid=False, reason=str(exc))

    if run_document["run_status"] != "success":
        return Level1CCaseRunValidation(is_valid=False, reason=f"run_status is {run_document['run_status']!r}, not 'success'")

    for key, expected in (
        ("campaign_id", level1c_manifest.campaign_id),
        ("manifest_fingerprint", level1c_manifest.fingerprint),
        ("repository_commit", repository_commit),
    ):
        if run_document[key] != expected:
            return Level1CCaseRunValidation(
                is_valid=False,
                reason=f"run.json {key} ({run_document[key]!r}) does not match expected ({expected!r})",
            )

    try:
        load_and_verify_case_records(output_dir, case_id, run_document, level1c_manifest=level1c_manifest)
    except Level1CArtifactIntegrityError as exc:
        return Level1CCaseRunValidation(is_valid=False, reason=str(exc))

    return Level1CCaseRunValidation(is_valid=True, reason=None)

    return tuple(documents)
