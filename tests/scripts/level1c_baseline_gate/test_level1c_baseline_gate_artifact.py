from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from scripts.level1c_baseline_gate import gate
from scripts.level1c_baseline_gate.gate import (
    FAIL,
    PASS,
    REQUIRED_TARGET_IDS,
    BaselineGateInputError,
    build_case_comparison_result,
    canonical_json_bytes,
    compare_baseline_case,
    load_level1c_baseline_case,
    run_baseline_nonregression_gate,
    to_json_dict,
    validate_gate_artifact_document,
)

from conftest import real_historical_group_data, real_level1c_baseline_case_id, write_fake_level1c_baseline_case

REPO_COMMIT = "79c0b8b8a5f2208acb6c4b8776ef6323ad8bbd98"


def _geometry_targets(geometry: str) -> tuple[str, ...]:
    return REQUIRED_TARGET_IDS[geometry]


def _matching_level1c_baseline(output_dir, historical_index, historical_case_id, level1c_manifest, geometry, spin, level1c_case_id) -> None:
    target_group_data = {}
    for index, target_id in enumerate(_geometry_targets(geometry)):
        data = real_historical_group_data(historical_index, historical_case_id, index)
        target_group_data[target_id] = (index, data)
    write_fake_level1c_baseline_case(
        output_dir,
        case_id=level1c_case_id,
        geometry=geometry,
        spin=spin,
        hamiltonian_case_id="j0-1.00",
        manifest_fingerprint=level1c_manifest.fingerprint,
        campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT,
        target_group_data=target_group_data,
        role_by_target={target_id: "REQUIRED" for target_id in _geometry_targets(geometry)},
    )


def test_schema_is_a_well_formed_draft202012_schema() -> None:
    Draft202012Validator.check_schema(gate._load_schema())


# ---------------------------------------------------------------------------
# Single-case comparison: missing baseline / provenance / status gating
# ---------------------------------------------------------------------------


def test_missing_level1c_baseline_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    result = compare_baseline_case(
        "ring5", 2, level1c_manifest, tmp_path, "does-not-exist",
        historical_index, historical_manifest, historical_case_id,
        repository_commit=REPO_COMMIT, ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
    )
    assert result.case_status == FAIL
    assert any("LEVEL1C_BASELINE_UNAVAILABLE" in reason for reason in result.failure_reasons)


def test_level1c_provenance_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    result = compare_baseline_case(
        "ring5", 2, level1c_manifest, tmp_path, level1c_case_id,
        historical_index, historical_manifest, historical_case_id,
        repository_commit="0" * 40,  # deliberately wrong
        ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
    )
    assert result.case_status == FAIL
    assert "LEVEL1C_REPOSITORY_COMMIT_MISMATCH" in result.failure_reasons


def test_run_status_not_success_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["run_status"] = "failed"
    document["records_sha256"] = None
    document["record_count"] = 0
    document["target_selections"] = []
    document["normative_case_valid"] = None
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="run_status"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_normative_case_valid_not_true_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["normative_case_valid"] = False
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="normative_case_valid"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_historical_campaign_provenance_mismatch_fails() -> None:
    result = build_case_comparison_result("ring5", 2, "level1c-x", "historical-x", (), ("HISTORICAL_CAMPAIGN_PROVENANCE_MISMATCH",))
    assert result.case_status == FAIL
    assert result.failure_reasons == ("HISTORICAL_CAMPAIGN_PROVENANCE_MISMATCH",)


def test_t_max_never_in_required_target_ids() -> None:
    for geometry_targets in REQUIRED_TARGET_IDS.values():
        assert "T_max" not in geometry_targets


# ---------------------------------------------------------------------------
# Level1C artifact integrity (1C-8d-fix): SHA-256, record_count, blank
# lines, run.json case_id, per-record provenance/scientific identity.
# ---------------------------------------------------------------------------


def test_valid_records_hash_and_count_are_accepted(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_document, records = load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)
    assert len(records) == run_document["record_count"]


def test_records_jsonl_byte_modification_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    records_path = tmp_path / "runs" / level1c_case_id / "records.jsonl"
    data = bytearray(records_path.read_bytes())
    # Flip one ASCII digit somewhere in the middle of the file -- keeps
    # the file byte-length identical and (very likely) still valid
    # JSONL, but the SHA-256 no longer matches run.json's own value.
    for index in range(len(data)):
        if chr(data[index]).isdigit():
            data[index] = ord("9") if chr(data[index]) != "9" else ord("8")
            break
    records_path.write_bytes(bytes(data))

    with pytest.raises(BaselineGateInputError, match="SHA-256"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_wrong_records_sha256_in_run_json_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["records_sha256"] = "a" * 64
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="SHA-256"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_wrong_record_count_in_run_json_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["record_count"] = document["record_count"] + 1
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="record_count"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_internal_blank_line_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    import hashlib

    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    records_path = tmp_path / "runs" / level1c_case_id / "records.jsonl"
    original = records_path.read_bytes()
    tampered = original[:-1] + b"\n" + original[-1:]  # inject an internal blank line before the final line
    records_path.write_bytes(tampered)

    # Recompute records_sha256/record_count to match the tampered file
    # exactly, isolating the blank-line policy from the hash/count checks.
    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["records_sha256"] = hashlib.sha256(tampered).hexdigest()
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="could not be loaded"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_run_json_case_id_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["case_id"] = "some-other-case-id"
    run_path.write_text(json.dumps(document))

    with pytest.raises(BaselineGateInputError, match="case_id"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def _tamper_first_record(tmp_path, level1c_case_id: str, key: str, value) -> None:
    import hashlib

    records_path = tmp_path / "runs" / level1c_case_id / "records.jsonl"
    lines = records_path.read_bytes().decode("utf-8").split("\n")
    assert lines and lines[-1] == ""
    content_lines = lines[:-1]
    first = json.loads(content_lines[0])
    if key in ("geometry", "spin", "sector"):
        first["identity"][key] = value
    elif key == "hamiltonian_J0":
        first["identity"]["hamiltonian"] = dict(first["identity"]["hamiltonian"])
        first["identity"]["hamiltonian"]["J"] = list(first["identity"]["hamiltonian"]["J"])
        first["identity"]["hamiltonian"]["J"][0] = value
    else:
        first[key] = value
    content_lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    tampered_bytes = ("\n".join(content_lines) + "\n").encode("utf-8")
    records_path.write_bytes(tampered_bytes)

    run_path = tmp_path / "runs" / level1c_case_id / "run.json"
    document = json.loads(run_path.read_text())
    document["records_sha256"] = hashlib.sha256(tampered_bytes).hexdigest()
    run_path.write_text(json.dumps(document))


def test_record_campaign_id_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "campaign_id", "some-other-campaign")

    with pytest.raises(BaselineGateInputError, match="campaign_id"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_record_manifest_fingerprint_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "manifest_fingerprint", "0" * 64)

    with pytest.raises(BaselineGateInputError, match="manifest_fingerprint"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_record_repository_commit_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "repository_commit", "1" * 40)

    with pytest.raises(BaselineGateInputError, match="repository_commit"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_record_geometry_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "geometry", "triangle")

    with pytest.raises(BaselineGateInputError, match="geometry"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_record_spin_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "spin", 3)

    with pytest.raises(BaselineGateInputError, match="spin"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_record_hamiltonian_mismatch_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    historical_case_id = historical_case_ids[("ring5", 2)]
    level1c_case_id = level1c_case_ids[("ring5", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, level1c_case_id)
    _tamper_first_record(tmp_path, level1c_case_id, "hamiltonian_J0", 0.5)

    with pytest.raises(BaselineGateInputError, match="hamiltonian"):
        load_level1c_baseline_case(tmp_path, level1c_case_id, level1c_manifest=level1c_manifest)


def test_case_id_not_in_manifest_plan_fails(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest) -> None:
    """A baseline whose case_id does not resolve to any real planned
    case must never be silently accepted, even if run.json/records.jsonl
    are otherwise internally consistent."""
    historical_case_id = historical_case_ids[("ring5", 2)]
    fake_case_id = "ring5-S2-j0-1.00-default-NOTINPLAN"
    _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, "ring5", 2, fake_case_id)

    with pytest.raises(BaselineGateInputError, match="not present in build_level1c_campaign_plan"):
        load_level1c_baseline_case(tmp_path, fake_case_id, level1c_manifest=level1c_manifest)


# ---------------------------------------------------------------------------
# Full 4/4 exact-match gate: PASS
# ---------------------------------------------------------------------------


def test_full_gate_all_4_baselines_exact_match_passes(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    results = []
    for (geometry, spin), historical_case_id in historical_case_ids.items():
        level1c_case_id = level1c_case_ids[(geometry, spin)]
        _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, geometry, spin, level1c_case_id)
        results.append(
            compare_baseline_case(
                geometry, spin, level1c_manifest, tmp_path, level1c_case_id,
                historical_index, historical_manifest, historical_case_id,
                repository_commit=REPO_COMMIT, ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
            )
        )

    assert len(results) == 4
    assert all(result.case_status == PASS for result in results)
    for result in results:
        assert result.max_abs_ctt == 0.0
        assert result.max_abs_rho == 0.0


def test_full_orchestration_run_baseline_nonregression_gate_passes(
    tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids, monkeypatch
) -> None:
    """Exercises run_baseline_nonregression_gate itself (not just
    compare_baseline_case), using the manifest's own real, deterministic
    case_id for each Level1C baseline -- never a hand-picked fake id --
    and monkeypatches build_campaign_artifact_index to reuse the
    already-loaded real historical_index fixture (avoiding a second,
    redundant real-archive load per test)."""
    for (geometry, spin), historical_case_id in historical_case_ids.items():
        level1c_case_id = level1c_case_ids[(geometry, spin)]
        _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, geometry, spin, level1c_case_id)

    monkeypatch.setattr(
        "scripts.level1c_baseline_gate.gate.build_campaign_artifact_index",
        lambda manifest, output_dir, *, repository_commit: historical_index,
    )

    artifact = run_baseline_nonregression_gate(level1c_manifest, tmp_path, "/irrelevant/mocked/path", repository_commit=REPO_COMMIT)
    assert artifact.gate_status == PASS
    assert artifact.failure_reasons == ()
    assert artifact.e_ctt == 0.0
    assert artifact.e_rho == 0.0
    assert len(artifact.case_comparisons) == 4
    validate_gate_artifact_document(to_json_dict(artifact))


def test_full_gate_one_baseline_fails_others_still_evaluated(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    """A single missing/invalid baseline must never abort the other
    three -- all four are always attempted and reported (section 3)."""
    triangle_s2_id = historical_case_ids[("triangle", 2)]
    real_case_id = level1c_case_ids[("triangle", 2)]
    _matching_level1c_baseline(tmp_path, historical_index, triangle_s2_id, level1c_manifest, "triangle", 2, real_case_id)
    # triangle S3, ring5 S2, ring5 S3 are intentionally never written -> missing.

    results = {}
    results[("triangle", 2)] = compare_baseline_case(
        "triangle", 2, level1c_manifest, tmp_path, real_case_id,
        historical_index, historical_manifest, triangle_s2_id,
        repository_commit=REPO_COMMIT, ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
    )
    for geometry, spin in [("triangle", 3), ("ring5", 2), ("ring5", 3)]:
        historical_case_id = historical_case_ids[(geometry, spin)]
        results[(geometry, spin)] = compare_baseline_case(
            geometry, spin, level1c_manifest, tmp_path, "missing-case-id",
            historical_index, historical_manifest, historical_case_id,
            repository_commit=REPO_COMMIT, ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
        )

    assert results[("triangle", 2)].case_status == PASS
    for geometry, spin in [("triangle", 3), ("ring5", 2), ("ring5", 3)]:
        assert results[(geometry, spin)].case_status == FAIL
        assert any("LEVEL1C_BASELINE_UNAVAILABLE" in reason for reason in results[(geometry, spin)].failure_reasons)


# ---------------------------------------------------------------------------
# Canonical serialization / schema round trip
# ---------------------------------------------------------------------------


def test_gate_artifact_round_trips_through_schema(tmp_path, historical_index, historical_manifest, historical_case_ids, level1c_manifest, level1c_case_ids) -> None:
    from scripts.level1c_baseline_gate.gate import _finalize_artifact

    results = []
    for (geometry, spin), historical_case_id in historical_case_ids.items():
        level1c_case_id = level1c_case_ids[(geometry, spin)]
        _matching_level1c_baseline(tmp_path, historical_index, historical_case_id, level1c_manifest, geometry, spin, level1c_case_id)
        results.append(
            compare_baseline_case(
                geometry, spin, level1c_manifest, tmp_path, level1c_case_id,
                historical_index, historical_manifest, historical_case_id,
                repository_commit=REPO_COMMIT, ctt_abs_tol=1e-15, rho_abs_tol=1e-15,
            )
        )

    artifact = _finalize_artifact(level1c_manifest, REPO_COMMIT, tuple(results), 1e-15, 1e-15)
    assert artifact.gate_status == PASS
    assert artifact.failure_reasons == ()

    document = to_json_dict(artifact)
    validate_gate_artifact_document(document)

    data = canonical_json_bytes(document)
    assert data.endswith(b"\n")
    assert not data.endswith(b"\n\n")


def test_schema_rejects_non_pass_status_with_empty_failure_reasons() -> None:
    document = {
        "schema_version": "level1c-baseline-nonregression-v1",
        "campaign_id": "level1c-j0-response-v1",
        "repository_commit": REPO_COMMIT,
        "manifest_fingerprint": "x",
        "historical_campaign_id": "level1b-reference-v1",
        "historical_manifest_fingerprint": "159660cac738518dc620b9627ec95fd67c5dbc283707fdf72e572886364693ab",
        "historical_repository_commit": "0ff65ac66b4aa054f739b350cd384c26ecd19752",
        "ctt_abs_tol": 1e-15,
        "rho_abs_tol": 1e-15,
        "case_comparisons": [],
        "e_ctt": None,
        "e_rho": None,
        "gate_status": "PASS",
        "failure_reasons": ["should not be here"],
    }
    with pytest.raises(ValueError):
        validate_gate_artifact_document(document)


def test_schema_rejects_wrong_number_of_case_comparisons() -> None:
    base_case = {
        "level1c_case_id": "x", "historical_case_id": "y", "geometry": "triangle", "spin": 2,
        "target_results": [], "structural_status": "PASS", "ctt_status": "PASS", "rho_status": "PASS",
        "max_abs_ctt": 0.0, "max_abs_rho": 0.0, "case_status": "PASS", "failure_reasons": [],
    }
    document = {
        "schema_version": "level1c-baseline-nonregression-v1",
        "campaign_id": "level1c-j0-response-v1",
        "repository_commit": REPO_COMMIT,
        "manifest_fingerprint": "x",
        "historical_campaign_id": "level1b-reference-v1",
        "historical_manifest_fingerprint": "159660cac738518dc620b9627ec95fd67c5dbc283707fdf72e572886364693ab",
        "historical_repository_commit": "0ff65ac66b4aa054f739b350cd384c26ecd19752",
        "ctt_abs_tol": 1e-15,
        "rho_abs_tol": 1e-15,
        "case_comparisons": [base_case, base_case, base_case],  # only 3, not 4
        "e_ctt": 0.0,
        "e_rho": 0.0,
        "gate_status": "PASS",
        "failure_reasons": [],
    }
    with pytest.raises(ValueError):
        validate_gate_artifact_document(document)
