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
