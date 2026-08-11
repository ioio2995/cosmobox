from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from experiments.level1c.case_artifact import required_targets_are_satisfied, validate_case_run_document
from scripts.level1c_campaign import outputs as o

REPO_COMMIT = "5159c2d68a060858cfd751e9b76365eecb2aba3e"


def test_write_case_success_creates_records_and_run_json(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    assert (case_dir / "records.jsonl").exists()
    assert (case_dir / "run.json").exists()


def test_run_json_records_count_matches_records_jsonl(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    run_document = json.loads((case_dir / "run.json").read_text())
    records = o.load_case_records(case_dir)
    assert run_document["record_count"] == len(records) == len(triangle_j0_1_00_result.documents)


def test_run_json_records_sha256_matches_actual_bytes(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    run_document = json.loads((case_dir / "run.json").read_text())
    actual_sha256 = hashlib.sha256((case_dir / "records.jsonl").read_bytes()).hexdigest()
    assert run_document["records_sha256"] == actual_sha256


def test_run_json_target_selections_match_result(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    run_document = json.loads((case_dir / "run.json").read_text())
    assert [entry["target_id"] for entry in run_document["target_selections"]] == [
        record.target_id for record in triangle_j0_1_00_result.target_selections
    ]


def test_run_json_normative_case_valid_matches_required_targets_are_satisfied(
    tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result
) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    run_document = json.loads((case_dir / "run.json").read_text())
    assert run_document["normative_case_valid"] == required_targets_are_satisfied(triangle_j0_1_00_result.target_selections)
    assert run_document["normative_case_valid"] is True  # both REQUIRED targets found and conformant in this real case


def test_write_case_success_never_refuses_a_normatively_invalid_case(
    tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result
) -> None:
    """A REQUIRED target ambiguous/not_in_window/non-conformant must
    never turn into a write refusal or a different run_status
    (RUN_STATUS_SEMANTICS=TECHNICAL_EXECUTION_STATUS, 1C-8c-fix): the
    computation itself still succeeded technically, so run_status stays
    'success' and the artifact is fully persisted for diagnosis, with
    normative_case_valid=False."""
    tampered_selections = tuple(
        dataclasses.replace(record, selection_status="ambiguous", spectral_window_group_index=None, selected_group_status=None, meets_normative_requirements=None)
        if record.target_id == "first_excited"
        else record
        for record in triangle_j0_1_00_result.target_selections
    )
    tampered_result = dataclasses.replace(triangle_j0_1_00_result, target_selections=tampered_selections)

    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, tampered_result, repository_commit=REPO_COMMIT)

    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    assert (case_dir / "records.jsonl").exists()
    run_document = json.loads((case_dir / "run.json").read_text())
    assert run_document["run_status"] == "success"
    assert run_document["normative_case_valid"] is False
    validate_case_run_document(run_document)


def test_run_json_validates_against_case_run_schema(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    run_document = json.loads((case_dir / "run.json").read_text())
    validate_case_run_document(run_document)


def test_records_jsonl_has_single_trailing_newline_and_canonical_lines(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    data = (case_dir / "records.jsonl").read_bytes()
    assert data.endswith(b"\n")
    lines = data.decode("utf-8").split("\n")[:-1]
    assert len(lines) == len(triangle_j0_1_00_result.documents)
    for line in lines:
        # Canonical: sort_keys + compact separators -- no extraneous spaces.
        assert ", " not in line
        assert ": " not in line
        json.loads(line)  # each line is itself valid JSON


def test_run_json_is_deterministic_across_repeated_writes(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    output_dir_a = tmp_path / "a"
    output_dir_b = tmp_path / "b"
    o.write_case_success(output_dir_a, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    o.write_case_success(output_dir_b, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    run_a = (output_dir_a / "runs" / triangle_j0_1_00_case.case_id / "run.json").read_bytes()
    run_b = (output_dir_b / "runs" / triangle_j0_1_00_case.case_id / "run.json").read_bytes()
    assert run_a == run_b


def test_write_case_failure_produces_no_records_jsonl(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    o.write_case_failure(tmp_path, manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT, run_status="failed")
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    assert not (case_dir / "records.jsonl").exists()
    assert (case_dir / "run.json").exists()
    run_document = json.loads((case_dir / "run.json").read_text())
    assert run_document["run_status"] == "failed"
    assert run_document["target_selections"] == []
    assert run_document["records_sha256"] is None
    assert run_document["record_count"] == 0
    validate_case_run_document(run_document)


def test_write_case_failure_removes_stale_records_jsonl(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    case_dir = tmp_path / "runs" / triangle_j0_1_00_case.case_id
    assert (case_dir / "records.jsonl").exists()

    o.write_case_failure(tmp_path, manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT, run_status="resource_guardrail_exceeded")
    assert not (case_dir / "records.jsonl").exists()


def test_write_case_failure_rejects_success_status(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    with pytest.raises(ValueError, match="run_status must be one of"):
        o.write_case_failure(tmp_path, manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT, run_status="success")


def test_write_case_success_rejects_empty_documents(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    empty_result = dataclasses.replace(triangle_j0_1_00_result, documents=())
    with pytest.raises(ValueError, match="must be non-empty"):
        o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, empty_result, repository_commit=REPO_COMMIT)


def test_write_case_success_rejects_mismatched_case_id(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, ring5_j0_1_00_case) -> None:
    with pytest.raises(ValueError, match="does not match case.case_id"):
        o.write_case_success(tmp_path, manifest, ring5_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# validate_existing_level1c_case_run (1C-8h): PHASE_P resume validation
# ---------------------------------------------------------------------------


def _run_json_path(tmp_path, case):
    return tmp_path / "runs" / case.case_id / "run.json"


def test_resume_missing_case_directory_is_not_valid(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert validation.reason is not None
    assert "missing" in validation.reason.lower()


def test_resume_valid_success_run_is_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is True
    assert validation.reason is None


def test_resume_normative_case_valid_false_still_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    """normative_case_valid is NEVER a resume criterion for PHASE_P: a
    technically successful, structurally intact run is reusable
    regardless of its normative verdict."""
    tampered_selections = tuple(
        dataclasses.replace(record, selection_status="ambiguous", spectral_window_group_index=None, selected_group_status=None, meets_normative_requirements=None)
        if record.target_id == "first_excited"
        else record
        for record in triangle_j0_1_00_result.target_selections
    )
    tampered_result = dataclasses.replace(triangle_j0_1_00_result, target_selections=tampered_selections)
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, tampered_result, repository_commit=REPO_COMMIT)

    run_document = json.loads(_run_json_path(tmp_path, triangle_j0_1_00_case).read_text())
    assert run_document["normative_case_valid"] is False  # precondition of this test

    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is True


def test_resume_failed_run_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    o.write_case_failure(tmp_path, manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT, run_status="failed")
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "run_status" in validation.reason


def test_resume_resource_guardrail_exceeded_run_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    o.write_case_failure(tmp_path, manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT, run_status="resource_guardrail_exceeded")
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False


def test_resume_invalid_run_json_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    _run_json_path(tmp_path, triangle_j0_1_00_case).write_text("{ not valid json")
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "parsed" in validation.reason or "JSON" in validation.reason


def test_resume_records_sha256_mismatch_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    records_path = tmp_path / "runs" / triangle_j0_1_00_case.case_id / "records.jsonl"
    records_path.write_bytes(records_path.read_bytes() + b'{"tampered": true}\n')
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "SHA-256" in validation.reason


def test_resume_record_count_mismatch_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    run_json_path = _run_json_path(tmp_path, triangle_j0_1_00_case)
    run_document = json.loads(run_json_path.read_text())
    records_path = tmp_path / "runs" / triangle_j0_1_00_case.case_id / "records.jsonl"
    # Bump record_count while keeping records_sha256 as-is: forces the
    # SHA-256 check to pass (bytes unchanged) but record_count to diverge.
    tampered_bytes = json.dumps({**run_document, "record_count": run_document["record_count"] + 1}, sort_keys=True).encode("utf-8")
    run_json_path.write_bytes(tampered_bytes)
    # Recompute the SHA against the (unchanged) records.jsonl so the SHA
    # check itself passes and the record_count check is isolated.
    actual_sha256 = hashlib.sha256(records_path.read_bytes()).hexdigest()
    run_document_2 = json.loads(run_json_path.read_text())
    run_document_2["records_sha256"] = actual_sha256
    run_json_path.write_text(json.dumps(run_document_2, sort_keys=True))

    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "record_count" in validation.reason


def test_resume_campaign_id_mismatch_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is True  # sanity: baseline is valid before tampering

    class _FakeManifest:
        campaign_id = "some-other-campaign-id"
        fingerprint = manifest.fingerprint

    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=_FakeManifest(), repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "campaign_id" in validation.reason


def test_resume_manifest_fingerprint_mismatch_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)

    class _FakeManifest:
        campaign_id = manifest.campaign_id
        fingerprint = "0" * 64

    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=_FakeManifest(), repository_commit=REPO_COMMIT
    )
    assert validation.is_valid is False
    assert "manifest_fingerprint" in validation.reason


def test_resume_repository_commit_mismatch_is_not_reusable(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result) -> None:
    o.write_case_success(tmp_path, manifest, triangle_j0_1_00_case, triangle_j0_1_00_result, repository_commit=REPO_COMMIT)
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit="1" * 40
    )
    assert validation.is_valid is False
    assert "repository_commit" in validation.reason


def test_resume_never_raises_for_ordinary_invalid_states(tmp_path, manifest, triangle_j0_1_00_case) -> None:
    """An absent/invalid existing artifact must never crash the resume
    check -- it is always reported as Level1CCaseRunValidation(False,
    reason), never an exception."""
    validation = o.validate_existing_level1c_case_run(
        tmp_path, triangle_j0_1_00_case.case_id, level1c_manifest=manifest, repository_commit=REPO_COMMIT
    )
    assert isinstance(validation, o.Level1CCaseRunValidation)
    assert validation.is_valid is False


def test_level1c_case_run_validation_requires_reason_iff_invalid() -> None:
    with pytest.raises(ValueError, match="reason must be set"):
        o.Level1CCaseRunValidation(is_valid=False, reason=None)
    with pytest.raises(ValueError, match="reason must be set"):
        o.Level1CCaseRunValidation(is_valid=True, reason="unexpected")
