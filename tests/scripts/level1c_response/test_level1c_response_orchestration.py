from __future__ import annotations

from pathlib import Path

from level1c_response_helpers import REPO_COMMIT, write_level1c_case

from experiments.level1c.planning import build_level1c_campaign_plan
from scripts.level1c_baseline_gate.gate import REQUIRED_TARGET_IDS
from scripts.level1c_response.response import RESPONSE_AVAILABLE, run_phase_r, write_response_records
from scripts.level1c_tracking.tracking import run_inter_j0_tracking, write_tracking_records

_TARGET_PARAMS_BY_GEOMETRY = {
    "triangle": {
        "fundamental": (0, {"multiplicity": 1, "twice_T": 0}),
        "first_excited": (1, {"multiplicity": 1, "twice_T": 1}),
    },
    "ring5": {
        "fundamental": (0, {"multiplicity": 1, "twice_T": 0}),
        "first_excited": (1, {"multiplicity": 1, "twice_T": 1}),
        "T_3_2": (2, {"multiplicity": 1, "twice_T": 3}),
    },
}


def _j0_of(hamiltonian_case_id: str) -> float:
    return float(hamiltonian_case_id.removeprefix("j0-"))


def _write_all_cases(output_dir: Path, level1c_manifest) -> None:
    """Every grid case gets identical (group_index, twice_T, multiplicity,
    NUMERIC reflection) per target across every J0 -- exactly like
    tests/scripts/level1c_tracking/test_level1c_tracking_orchestration.py's
    own fixture -- so every tracking edge resolves to TRACKED_ONE_TO_ONE,
    plus a J0-dependent C_TT_conn/rho_QQ payload so Delta_C_TT is
    non-trivial and identical between the two ordered pairs used."""
    for case in build_level1c_campaign_plan(level1c_manifest):
        j0 = _j0_of(case.hamiltonian_case_id)
        target_group_data = {}
        role_by_target = {}
        for target_id, (group_index, params) in _TARGET_PARAMS_BY_GEOMETRY[case.geometry].items():
            target_group_data[target_id] = (
                group_index,
                {
                    **params,
                    "ctt_records": [(0, 1, j0), (1, 0, -j0)],
                    "rho_records": [(0, 1, -0.5 * j0, None), (1, 0, None, "zero_local_charge_variance")],
                },
            )
            role_by_target[target_id] = "REQUIRED"
        write_level1c_case(
            output_dir,
            case_id=case.case_id,
            geometry=case.geometry,
            spin=case.spin,
            hamiltonian_case_id=case.hamiltonian_case_id,
            manifest_fingerprint=level1c_manifest.fingerprint,
            campaign_id=level1c_manifest.campaign_id,
            repository_commit=REPO_COMMIT,
            target_group_data=target_group_data,
            role_by_target=role_by_target,
        )


def test_run_phase_r_produces_exactly_40_response_records_all_available(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert len(tracking_records) == 40
    write_tracking_records(tmp_path, tracking_records)

    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert len(response_records) == 40
    assert all(record.response_eligibility == RESPONSE_AVAILABLE for record in response_records)
    assert all(record.target_id != "T_max" for record in response_records)


def test_run_phase_r_delta_ctt_matches_j0_difference(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, tracking_records)
    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)

    baseline_j0 = 1.0
    for record in response_records:
        perturbed_j0 = _j0_of(record.perturbed_hamiltonian_case_id)
        for pair in record.delta_ctt_pairs:
            if (pair.i, pair.j) == (0, 1):
                assert abs(pair.baseline_value - baseline_j0) < 1e-12
                assert abs(pair.perturbed_value - perturbed_j0) < 1e-12
                assert abs(pair.delta - (perturbed_j0 - baseline_j0)) < 1e-12


def test_run_phase_r_geometry_split_matches_target_counts(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, tracking_records)
    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)

    triangle_records = [r for r in response_records if r.geometry == "triangle"]
    ring5_records = [r for r in response_records if r.geometry == "ring5"]
    assert len(triangle_records) == 8 * len(REQUIRED_TARGET_IDS["triangle"])
    assert len(ring5_records) == 8 * len(REQUIRED_TARGET_IDS["ring5"])


def test_run_phase_r_deterministic_order_matches_tracking_order(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, tracking_records)
    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)

    expected_order = [(record.perturbed_case_id, record.baseline_case_id, record.target_id) for record in tracking_records]
    actual_order = [(record.perturbed_case_id, record.baseline_case_id, record.target_id) for record in response_records]
    assert actual_order == expected_order


def test_write_response_records_round_trips(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, tracking_records)
    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_response_records(tmp_path, response_records)

    response_path = tmp_path / "response.jsonl"
    assert response_path.exists()
    lines = response_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 40


def test_run_phase_r_no_campaign_level_artifact_created(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    tracking_records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, tracking_records)
    response_records = run_phase_r(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_response_records(tmp_path, response_records)

    for forbidden_name in ("campaign.json", "response-summary.json", "response-index.json"):
        assert not (tmp_path / forbidden_name).exists()
