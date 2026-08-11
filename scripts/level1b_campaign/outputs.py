"""Atomic per-case persistence and resume validation for the Level1B
campaign. Level1B lot 1B-8c (docs/governance/current-task.md).

Persists exactly one case's already-produced CaseExecutionResult
(runner.run_single_case, unmodified by this module) to
`<output_dir>/runs/<case_id>/{records.jsonl,run.json}`, and validates an
existing on-disk run for reuse without ever re-running the scientific
pipeline. Introduces no scientific logic: it never recomputes an
observable, never re-derives a payload, and never repairs a partially
valid run silently -- an invalid run is simply reported as such
(CaseRunValidation), never patched.

This lot does not loop over a campaign, does not launch one, and does
not touch inter-S concerns (gamma_O, robustness verdicts, G_occ,
path_phase_coherence) -- see docs/governance/current-task.md for the
exact authorized scope.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cosmobox.level1.assembly import assemble_execution
from cosmobox.level1.serialization import validate_document

from .runner import CaseExecutionResult

_METADATA_FIELDS = ("campaign_id", "manifest_fingerprint", "repository_commit")

_FAILURE_RUN_STATUSES = ("failed", "resource_guardrail_exceeded")

_REQUIRED_RUN_JSON_KEYS = (
    "case_id",
    "campaign_id",
    "manifest_fingerprint",
    "repository_commit",
    "run_status",
    "record_count",
    "records_sha256",
    "errors",
)

_SHA256_HEX_LENGTH = 64
_SHA256_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class CaseRunValidation:
    """Whether an existing runs/<case_id>/ directory is exactly
    reusable. is_valid=True iff every reuse condition holds; reason is a
    short, human-readable explanation set if and only if is_valid is
    False -- never an exception for a simple "not reusable" outcome."""

    is_valid: bool
    reason: str | None

    def __post_init__(self) -> None:
        if self.is_valid != (self.reason is None):
            raise ValueError("reason must be set if and only if is_valid is False")


def _case_run_dir(output_dir: Path, case_id: str) -> Path:
    return output_dir / "runs" / case_id


def _canonical_document_line_bytes(document: dict) -> bytes:
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("utf-8")


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically: a uniquely-named temporary file
    in the same directory (same filesystem, so os.replace is atomic),
    flushed and fsync'd before the rename, then the parent directory is
    itself fsync'd (best-effort -- not every platform/filesystem supports
    directory fsync, so a failure there is not fatal). On any error
    before the replace, only the temporary file created by this call is
    removed; a stale temp file left by an earlier interrupted run is
    never touched. No non-atomic copy fallback exists."""
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
        pass  # best-effort: not every platform/filesystem supports this
    finally:
        os.close(directory_fd)


def write_case_success(output_dir: Path, result: CaseExecutionResult) -> None:
    """Persist a successful CaseExecutionResult to
    <output_dir>/runs/<result.case_id>/{records.jsonl,run.json}.
    case_id/campaign_id/manifest_fingerprint/repository_commit are
    derived exclusively from `result` -- never accepted as independent
    parameters that could silently diverge from what the documents
    themselves already carry.

    Defensively re-verified before any write (never recomputing an
    observable, only structural facts already guaranteed upstream by
    run_single_case -- re-checked here because this is the boundary
    where results leave memory and become a durable, load-bearing
    artifact): every document is non-empty and schema-valid, every
    document shares the same run metadata, and assemble_execution on
    result.documents reproduces it exactly (no duplicate, same order).
    """
    if not result.documents:
        raise ValueError("result.documents must be non-empty")

    for document in result.documents:
        validate_document(document)

    reference_metadata = {field: result.documents[0][field] for field in _METADATA_FIELDS}
    for document in result.documents:
        for field in _METADATA_FIELDS:
            if document[field] != reference_metadata[field]:
                raise ValueError(
                    f"result.documents disagree on {field!r}: {reference_metadata[field]!r} != {document[field]!r}"
                )

    assembled_documents, assembly_report = assemble_execution(result.documents)
    if assembly_report.duplicate_count != 0:
        raise ValueError(
            f"result.documents contains {assembly_report.duplicate_count} duplicate(s) -- a CaseExecutionResult "
            "must already be deduplicated"
        )
    if assembled_documents != tuple(result.documents):
        raise ValueError(
            "assemble_execution(result.documents) does not reproduce result.documents in the same order -- "
            "result.documents is not already the canonical assembled output"
        )
    if result.assembly_report.output_count != len(result.documents):
        raise ValueError(
            f"result.assembly_report.output_count ({result.assembly_report.output_count}) does not match "
            f"len(result.documents) ({len(result.documents)})"
        )

    case_dir = _case_run_dir(output_dir, result.case_id)

    records_bytes = b"".join(_canonical_document_line_bytes(document) for document in result.documents)
    _atomic_write_bytes(case_dir / "records.jsonl", records_bytes)

    records_sha256 = hashlib.sha256(records_bytes).hexdigest()
    run_payload = {
        "case_id": result.case_id,
        "campaign_id": reference_metadata["campaign_id"],
        "manifest_fingerprint": reference_metadata["manifest_fingerprint"],
        "repository_commit": reference_metadata["repository_commit"],
        "run_status": "success",
        "record_count": len(result.documents),
        "records_sha256": records_sha256,
        "errors": [],
    }
    _atomic_write_bytes(case_dir / "run.json", _canonical_json_bytes(run_payload))


def write_case_failure(
    output_dir: Path,
    case_id: str,
    *,
    campaign_id: str,
    manifest_fingerprint: str,
    repository_commit: str,
    run_status: str,
    errors: Sequence[str],
) -> None:
    """Persist a failed or resource-guardrail-exceeded case: run.json
    only, never records.jsonl -- a failure has no exploitable results,
    and no synthetic ResultRecord is ever invented to fill one. If a
    records.jsonl from an earlier (successful) run of this case_id still
    exists on disk, it is removed first, so it can never be mistaken for
    this failed run's own results."""
    if run_status not in _FAILURE_RUN_STATUSES:
        raise ValueError(f"run_status must be one of {_FAILURE_RUN_STATUSES}, got {run_status!r}")

    error_list = list(errors)
    if not error_list:
        raise ValueError("errors must be non-empty for a failure run")
    for error in error_list:
        if not isinstance(error, str) or not error:
            raise ValueError(f"each error must be a non-empty string, got {error!r}")

    case_dir = _case_run_dir(output_dir, case_id)

    stale_records_path = case_dir / "records.jsonl"
    if stale_records_path.exists():
        stale_records_path.unlink()

    run_payload = {
        "case_id": case_id,
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository_commit": repository_commit,
        "run_status": run_status,
        "record_count": 0,
        "records_sha256": None,
        "errors": error_list,
    }
    _atomic_write_bytes(case_dir / "run.json", _canonical_json_bytes(run_payload))


def load_case_records(case_dir: Path) -> tuple[dict, ...]:
    """Load records.jsonl from `case_dir` (the case's own directory, not
    output_dir) into a tuple of documents, in file order. Requires
    records.jsonl to exist, requires every non-trailing line to be a
    non-empty, valid JSON object -- raises ValueError otherwise, never
    silently drops a malformed line. Does not itself validate schema
    conformance or run.json consistency; that is
    validate_existing_case_run's job."""
    records_path = case_dir / "records.jsonl"
    if not records_path.exists():
        raise ValueError(f"{records_path} does not exist")

    text = records_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]  # the single trailing newline's own empty tail, not a blank line

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


def _invalid(reason: str) -> CaseRunValidation:
    return CaseRunValidation(is_valid=False, reason=reason)


def validate_existing_case_run(
    case_dir: Path,
    *,
    case_id: str,
    campaign_id: str,
    manifest_fingerprint: str,
    repository_commit: str,
) -> CaseRunValidation:
    """Answers exactly: does case_dir already hold an exactly-reusable
    run for (case_id, campaign_id, manifest_fingerprint,
    repository_commit)? Never re-executes run_single_case. Never raises
    for a simple "not reusable" outcome -- only for manifestly invalid
    arguments would this raise, and none of the checks below do that;
    every failure mode returns CaseRunValidation(False, reason) instead.
    A stale `*.tmp` file never participates: only the exact
    `run.json`/`records.jsonl` names are ever read.
    """
    run_json_path = case_dir / "run.json"
    if not run_json_path.exists():
        return _invalid("run.json does not exist")

    try:
        run_payload = json.loads(run_json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _invalid(f"run.json could not be parsed: {exc}")
    if not isinstance(run_payload, dict):
        return _invalid(f"run.json is not a JSON object, got {type(run_payload)}")

    for key in _REQUIRED_RUN_JSON_KEYS:
        if key not in run_payload:
            return _invalid(f"run.json is missing {key!r}")

    if run_payload["run_status"] != "success":
        return _invalid(f"run_status is {run_payload['run_status']!r}, not 'success'")

    for key, expected in (
        ("case_id", case_id),
        ("campaign_id", campaign_id),
        ("manifest_fingerprint", manifest_fingerprint),
        ("repository_commit", repository_commit),
    ):
        if run_payload[key] != expected:
            return _invalid(f"run.json {key} ({run_payload[key]!r}) does not match expected ({expected!r})")

    record_count = run_payload["record_count"]
    if isinstance(record_count, bool) or not isinstance(record_count, int) or record_count <= 0:
        return _invalid(f"run.json record_count must be a positive int, got {record_count!r}")

    records_sha256 = run_payload["records_sha256"]
    if (
        not isinstance(records_sha256, str)
        or len(records_sha256) != _SHA256_HEX_LENGTH
        or not set(records_sha256) <= _SHA256_HEX_DIGITS
    ):
        return _invalid(f"run.json records_sha256 is not a valid SHA-256 hex digest: {records_sha256!r}")

    if run_payload["errors"] != []:
        return _invalid(f"run.json errors is not empty for a success run: {run_payload['errors']!r}")

    records_path = case_dir / "records.jsonl"
    if not records_path.exists():
        return _invalid("records.jsonl does not exist")

    try:
        records_bytes = records_path.read_bytes()
    except OSError as exc:
        return _invalid(f"records.jsonl could not be read: {exc}")

    actual_sha256 = hashlib.sha256(records_bytes).hexdigest()
    if actual_sha256 != records_sha256:
        return _invalid(
            f"records.jsonl SHA-256 ({actual_sha256}) does not match run.json records_sha256 ({records_sha256})"
        )

    try:
        documents = load_case_records(case_dir)
    except ValueError as exc:
        return _invalid(f"records.jsonl could not be loaded: {exc}")

    if len(documents) != record_count:
        return _invalid(f"records.jsonl has {len(documents)} document(s), run.json record_count is {record_count}")

    for index, document in enumerate(documents):
        try:
            validate_document(document)
        except ValueError as exc:
            return _invalid(f"records.jsonl line {index} failed schema validation: {exc}")
        for key, expected in (
            ("campaign_id", campaign_id),
            ("manifest_fingerprint", manifest_fingerprint),
            ("repository_commit", repository_commit),
        ):
            if document[key] != expected:
                return _invalid(f"records.jsonl line {index} has {key} ({document[key]!r}) != expected ({expected!r})")

    try:
        assembled_documents, assembly_report = assemble_execution(list(documents))
    except ValueError as exc:
        return _invalid(f"records.jsonl documents failed assembly: {exc}")

    if assembly_report.duplicate_count != 0:
        return _invalid(f"records.jsonl contains {assembly_report.duplicate_count} duplicate document(s)")
    if assembly_report.output_count != record_count:
        return _invalid(
            f"assembly output_count ({assembly_report.output_count}) does not match record_count ({record_count})"
        )
    if assembled_documents != documents:
        return _invalid("assemble_execution does not reproduce records.jsonl's own document order")

    return CaseRunValidation(is_valid=True, reason=None)
