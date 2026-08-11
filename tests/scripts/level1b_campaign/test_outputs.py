from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from cosmobox.level1.assembly import AssemblyReport, assemble_execution
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.serialization import serialize_result_record
from scripts.level1b_campaign import outputs as outputs_module
from scripts.level1b_campaign.outputs import (
    CaseRunValidation,
    load_case_records,
    validate_existing_case_run,
    write_case_failure,
    write_case_success,
)
from scripts.level1b_campaign.runner import CaseExecutionResult

CAMPAIGN_ID = "c1"
MANIFEST_FINGERPRINT = "f" * 16
REPOSITORY_COMMIT = "a" * 40


def build_result_record(*args, **kwargs):
    kwargs.setdefault("scientific_seed", 1001)
    kwargs.setdefault("solver_seed", 2002)
    return _build_result_record_impl(*args, **kwargs)


def _document(
    *,
    campaign_id: str = CAMPAIGN_ID,
    manifest_fingerprint: str = MANIFEST_FINGERPRINT,
    repository_commit: str = REPOSITORY_COMMIT,
    payload: float = 0.5,
    observable_kind: str = "C_QQ_raw",
    spin: int = 1,
    spectral_window_group_index: int = 0,
) -> dict:
    """A small, fast, genuinely v2-schema-valid document -- built via the
    real results.py/serialization.py primitives, never a diagonalization."""
    hamiltonian = HamiltonianIdentity(J=(1.0,), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    group = SpectralGroupIdentity(
        status=COMPLETE_MULTIPLET,
        multiplicity=1,
        twice_T=0,
        spectral_window_group_index=spectral_window_group_index,
        representative_energy=-1.0,
    )
    identity = ScientificIdentity(
        geometry="triangle",
        spin=spin,
        n_flavors=2,
        hamiltonian=hamiltonian,
        sector="default",
        spectral_group=group,
        path=None,
        flavor_component=None,
        normalization=None,
    )
    record = build_result_record(identity, "raw_observable", observable_kind, payload)
    return serialize_result_record(
        record, repository_commit=repository_commit, manifest_fingerprint=manifest_fingerprint, campaign_id=campaign_id
    )


def _case_execution_result(documents: tuple[dict, ...], *, case_id: str = "synthetic-case-0000000000000000") -> CaseExecutionResult:
    """The normal, well-formed path: assemble_execution builds the report
    that actually matches `documents`."""
    assembled, report = assemble_execution(list(documents))
    return CaseExecutionResult(case_id=case_id, target_outcomes=(), documents=assembled, assembly_report=report)


# ---------------------------------------------------------------------------
# 1, 2, 3, 4. write_case_success: basic success, deterministic
# records.jsonl, exact SHA, exact count.
# ---------------------------------------------------------------------------


def test_write_case_success_writes_both_files(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    assert (case_dir / "records.jsonl").exists()
    assert (case_dir / "run.json").exists()


def test_records_jsonl_is_deterministic(tmp_path: Path) -> None:
    result = _case_execution_result((_document(payload=0.1), _document(payload=0.2, spin=2)))
    write_case_success(tmp_path / "a", result)
    write_case_success(tmp_path / "b", result)
    bytes_a = (tmp_path / "a" / "runs" / result.case_id / "records.jsonl").read_bytes()
    bytes_b = (tmp_path / "b" / "runs" / result.case_id / "records.jsonl").read_bytes()
    assert bytes_a == bytes_b


def test_records_sha256_is_exact(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    records_bytes = (case_dir / "records.jsonl").read_bytes()
    run_payload = json.loads((case_dir / "run.json").read_text())
    assert run_payload["records_sha256"] == hashlib.sha256(records_bytes).hexdigest()


def test_record_count_is_exact(tmp_path: Path) -> None:
    documents = (_document(payload=0.1), _document(payload=0.2, spin=2), _document(payload=0.3, spin=3))
    result = _case_execution_result(documents)
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    run_payload = json.loads((case_dir / "run.json").read_text())
    assert run_payload["record_count"] == 3
    lines = (case_dir / "records.jsonl").read_text().splitlines()
    assert len(lines) == 3


def test_each_line_ends_with_newline_including_the_last(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    raw = (case_dir / "records.jsonl").read_bytes()
    assert raw.endswith(b"\n")
    assert b"\n\n" not in raw  # no extra blank line


def test_records_jsonl_lines_are_canonical_json(tmp_path: Path) -> None:
    doc = _document()
    result = _case_execution_result((doc,))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    line = (case_dir / "records.jsonl").read_text().splitlines()[0]
    expected = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    assert line == expected


# ---------------------------------------------------------------------------
# 5, 6. run.json written after records.jsonl (interception, not timestamps);
# round-trip of every document.
# ---------------------------------------------------------------------------


def test_run_json_written_after_records_jsonl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    call_order: list[str] = []
    real_atomic_write_bytes = outputs_module._atomic_write_bytes

    def recording_atomic_write_bytes(path, data):
        call_order.append(path.name)
        return real_atomic_write_bytes(path, data)

    monkeypatch.setattr(outputs_module, "_atomic_write_bytes", recording_atomic_write_bytes)

    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)

    assert call_order == ["records.jsonl", "run.json"]


def test_round_trip_of_every_document(tmp_path: Path) -> None:
    documents = (_document(payload=0.1), _document(payload=0.2, spin=2))
    result = _case_execution_result(documents)
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    loaded = load_case_records(case_dir)
    assert loaded == result.documents


# ---------------------------------------------------------------------------
# 7. v2 validation of every line (via validate_existing_case_run).
# ---------------------------------------------------------------------------


def test_validation_checks_v2_schema_of_every_line(tmp_path: Path) -> None:
    result = _case_execution_result((_document(), _document(payload=0.2, spin=2)))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    validation = validate_existing_case_run(
        case_dir,
        case_id=result.case_id,
        campaign_id=CAMPAIGN_ID,
        manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT,
    )
    assert validation == CaseRunValidation(is_valid=True, reason=None)


# ---------------------------------------------------------------------------
# 8. Resume of a perfectly valid run.
# ---------------------------------------------------------------------------


def test_resume_of_a_perfectly_valid_run(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    validation = validate_existing_case_run(
        case_dir,
        case_id=result.case_id,
        campaign_id=CAMPAIGN_ID,
        manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT,
    )
    assert validation.is_valid is True
    assert validation.reason is None


# ---------------------------------------------------------------------------
# 9, 10, 11, 12. Rejection on mismatched commit/fingerprint/campaign_id/
# case_id.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,wrong_value",
    [
        ("repository_commit", "b" * 40),
        ("manifest_fingerprint", "wrong-fingerprint"),
        ("campaign_id", "wrong-campaign"),
        ("case_id", "wrong-case-id"),
    ],
)
def test_rejects_mismatched_identifier(tmp_path: Path, field: str, wrong_value: str) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    kwargs = dict(
        case_id=result.case_id,
        campaign_id=CAMPAIGN_ID,
        manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT,
    )
    kwargs[field] = wrong_value
    validation = validate_existing_case_run(case_dir, **kwargs)
    assert validation.is_valid is False
    assert validation.reason is not None


# ---------------------------------------------------------------------------
# 13, 14. Rejection on wrong SHA / wrong count.
# ---------------------------------------------------------------------------


def test_rejects_tampered_records_sha256(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    run_payload = json.loads((case_dir / "run.json").read_text())
    run_payload["records_sha256"] = "0" * 64
    (case_dir / "run.json").write_text(json.dumps(run_payload))

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False
    assert "SHA-256" in validation.reason


def test_rejects_tampered_record_count(tmp_path: Path) -> None:
    result = _case_execution_result((_document(), _document(payload=0.2, spin=2)))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    run_payload = json.loads((case_dir / "run.json").read_text())
    run_payload["record_count"] = 999
    (case_dir / "run.json").write_text(json.dumps(run_payload))

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False


# ---------------------------------------------------------------------------
# 15, 16. Corrupted JSON line / schema-invalid document.
# ---------------------------------------------------------------------------


def test_rejects_corrupted_json_line(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    (case_dir / "records.jsonl").write_bytes(b"{not valid json\n")

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False


def test_load_case_records_raises_on_corrupted_json_line(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    (case_dir / "records.jsonl").write_bytes(b"{not valid json\n")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_case_records(case_dir)


def test_rejects_schema_invalid_document(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id

    doc = json.loads((case_dir / "records.jsonl").read_text().splitlines()[0])
    doc["identity"]["geometry"] = "not_a_real_geometry"
    broken_bytes = (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    (case_dir / "records.jsonl").write_bytes(broken_bytes)

    run_payload = json.loads((case_dir / "run.json").read_text())
    run_payload["records_sha256"] = hashlib.sha256(broken_bytes).hexdigest()
    (case_dir / "run.json").write_text(json.dumps(run_payload))

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False


# ---------------------------------------------------------------------------
# 17. Assembly contradiction.
# ---------------------------------------------------------------------------


def test_rejects_assembly_contradiction(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id

    doc = json.loads((case_dir / "records.jsonl").read_text().splitlines()[0])
    contradicting = dict(doc)
    contradicting["payload"] = 0.999999  # same identity, different payload

    combined_bytes = b"".join(
        (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for document in (doc, contradicting)
    )
    (case_dir / "records.jsonl").write_bytes(combined_bytes)

    run_payload = json.loads((case_dir / "run.json").read_text())
    run_payload["records_sha256"] = hashlib.sha256(combined_bytes).hexdigest()
    run_payload["record_count"] = 2
    (case_dir / "run.json").write_text(json.dumps(run_payload))

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False


# ---------------------------------------------------------------------------
# 18, 19. Missing run.json / missing records.jsonl.
# ---------------------------------------------------------------------------


def test_missing_run_json_not_reusable(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    (case_dir / "run.json").unlink()

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False
    assert "run.json" in validation.reason


def test_missing_records_jsonl_not_reusable(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    (case_dir / "records.jsonl").unlink()

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is False
    assert "records.jsonl" in validation.reason


# ---------------------------------------------------------------------------
# 20. A leftover temp file is ignored.
# ---------------------------------------------------------------------------


def test_stale_temp_file_is_ignored(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),))
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / result.case_id
    (case_dir / "records.jsonl.deadbeefdeadbeefdeadbeefdeadbeef.tmp").write_bytes(b"garbage, not touched")

    validation = validate_existing_case_run(
        case_dir, case_id=result.case_id, campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT, repository_commit=REPOSITORY_COMMIT
    )
    assert validation.is_valid is True

    loaded = load_case_records(case_dir)
    assert loaded == result.documents


# ---------------------------------------------------------------------------
# 21. No synthetic ResultRecord for failed/resource_guardrail_exceeded.
# ---------------------------------------------------------------------------


def test_write_case_failure_never_writes_records_jsonl(tmp_path: Path) -> None:
    write_case_failure(
        tmp_path, "failure-case", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT, run_status="failed", errors=["boom"],
    )
    case_dir = tmp_path / "runs" / "failure-case"
    assert not (case_dir / "records.jsonl").exists()
    assert (case_dir / "run.json").exists()


def test_write_case_failure_removes_a_stale_records_jsonl_from_an_earlier_success(tmp_path: Path) -> None:
    result = _case_execution_result((_document(),), case_id="reused-case-id")
    write_case_success(tmp_path, result)
    case_dir = tmp_path / "runs" / "reused-case-id"
    assert (case_dir / "records.jsonl").exists()

    write_case_failure(
        tmp_path, "reused-case-id", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT, run_status="failed", errors=["boom"],
    )
    assert not (case_dir / "records.jsonl").exists()


def test_write_case_failure_record_count_zero_and_sha_null(tmp_path: Path) -> None:
    write_case_failure(
        tmp_path, "failure-case", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
        repository_commit=REPOSITORY_COMMIT, run_status="resource_guardrail_exceeded", errors=["dimension too large"],
    )
    run_payload = json.loads((tmp_path / "runs" / "failure-case" / "run.json").read_text())
    assert run_payload["record_count"] == 0
    assert run_payload["records_sha256"] is None


def test_write_case_failure_requires_non_empty_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="errors"):
        write_case_failure(
            tmp_path, "failure-case", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
            repository_commit=REPOSITORY_COMMIT, run_status="failed", errors=[],
        )


def test_write_case_failure_rejects_an_unknown_run_status(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_status"):
        write_case_failure(
            tmp_path, "failure-case", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
            repository_commit=REPOSITORY_COMMIT, run_status="running", errors=["x"],
        )


def test_write_case_failure_rejects_success_as_a_status(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_status"):
        write_case_failure(
            tmp_path, "failure-case", campaign_id=CAMPAIGN_ID, manifest_fingerprint=MANIFEST_FINGERPRINT,
            repository_commit=REPOSITORY_COMMIT, run_status="success", errors=["x"],
        )


# ---------------------------------------------------------------------------
# 22. Atomic write: temp + flush + fsync + replace.
# ---------------------------------------------------------------------------


def test_atomic_write_bytes_calls_flush_fsync_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fsync_calls: list[int] = []
    replace_calls: list[tuple] = []
    real_fsync = os.fsync
    real_replace = os.replace

    def recording_fsync(fd):
        fsync_calls.append(fd)
        return real_fsync(fd)

    def recording_replace(src, dst):
        replace_calls.append((src, dst))
        return real_replace(src, dst)

    monkeypatch.setattr(outputs_module.os, "fsync", recording_fsync)
    monkeypatch.setattr(outputs_module.os, "replace", recording_replace)

    outputs_module._atomic_write_bytes(tmp_path / "target.txt", b"hello")

    assert len(fsync_calls) >= 1
    assert len(replace_calls) == 1
    assert (tmp_path / "target.txt").read_bytes() == b"hello"


def test_atomic_write_bytes_uses_a_unique_temp_file_in_the_same_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen_sources: list[Path] = []
    real_replace = os.replace

    def recording_replace(src, dst):
        seen_sources.append(Path(src))
        return real_replace(src, dst)

    monkeypatch.setattr(outputs_module.os, "replace", recording_replace)

    target = tmp_path / "sub" / "target.txt"
    outputs_module._atomic_write_bytes(target, b"hello")

    assert len(seen_sources) == 1
    tmp_source = seen_sources[0]
    assert tmp_source.parent == target.parent
    assert tmp_source.name != target.name
    assert tmp_source.name.startswith(target.name)
    assert tmp_source.name.endswith(".tmp")
    assert not tmp_source.exists()  # renamed away, nothing left behind


def test_atomic_write_bytes_removes_its_own_temp_file_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def failing_replace(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(outputs_module.os, "replace", failing_replace)

    target = tmp_path / "target.txt"
    with pytest.raises(OSError, match="simulated replace failure"):
        outputs_module._atomic_write_bytes(target, b"hello")

    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []
    assert not target.exists()


# ---------------------------------------------------------------------------
# write_case_success defensive checks (never trusts a caller-supplied
# CaseExecutionResult blindly).
# ---------------------------------------------------------------------------


def test_write_case_success_rejects_empty_documents(tmp_path: Path) -> None:
    empty_report = AssemblyReport(input_count=0, output_count=0, duplicate_count=0)
    result = CaseExecutionResult(case_id="empty-case", target_outcomes=(), documents=(), assembly_report=empty_report)
    with pytest.raises(ValueError, match="non-empty"):
        write_case_success(tmp_path, result)


def test_write_case_success_rejects_divergent_metadata(tmp_path: Path) -> None:
    doc_a = _document(campaign_id="campaign-a")
    doc_b = _document(campaign_id="campaign-b", spin=2)
    fake_report = AssemblyReport(input_count=2, output_count=2, duplicate_count=0)
    result = CaseExecutionResult(case_id="mixed-case", target_outcomes=(), documents=(doc_a, doc_b), assembly_report=fake_report)
    with pytest.raises(ValueError, match="campaign_id"):
        write_case_success(tmp_path, result)


def test_write_case_success_rejects_a_duplicate_document(tmp_path: Path) -> None:
    doc = _document()
    fake_report = AssemblyReport(input_count=2, output_count=2, duplicate_count=0)  # lies: claims no duplicate
    result = CaseExecutionResult(case_id="dup-case", target_outcomes=(), documents=(doc, dict(doc)), assembly_report=fake_report)
    with pytest.raises(ValueError, match="duplicate"):
        write_case_success(tmp_path, result)


def test_write_case_success_rejects_documents_not_in_assembled_order(tmp_path: Path) -> None:
    doc_low_spin = _document(spin=1)
    doc_high_spin = _document(spin=3)
    fake_report = AssemblyReport(input_count=2, output_count=2, duplicate_count=0)
    # Deliberately the wrong order relative to what assemble_execution would produce.
    result = CaseExecutionResult(
        case_id="unordered-case", target_outcomes=(), documents=(doc_high_spin, doc_low_spin), assembly_report=fake_report
    )
    with pytest.raises(ValueError, match="order"):
        write_case_success(tmp_path, result)


def test_write_case_success_rejects_a_schema_invalid_document(tmp_path: Path) -> None:
    doc = _document()
    broken = dict(doc)
    broken["identity"] = dict(doc["identity"])
    broken["identity"]["geometry"] = "not_a_real_geometry"
    fake_report = AssemblyReport(input_count=1, output_count=1, duplicate_count=0)
    result = CaseExecutionResult(case_id="broken-case", target_outcomes=(), documents=(broken,), assembly_report=fake_report)
    with pytest.raises(ValueError):
        write_case_success(tmp_path, result)
