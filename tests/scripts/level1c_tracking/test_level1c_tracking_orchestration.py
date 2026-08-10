from __future__ import annotations

from pathlib import Path

from level1c_tracking_helpers import REPO_COMMIT, make_group_structural_data, write_level1c_case, write_level1c_failed_case

from experiments.level1c.planning import build_level1c_campaign_plan, build_tracking_edges
from scripts.level1c_baseline_gate.gate import REQUIRED_TARGET_IDS
from scripts.level1c_tracking.tracking import TRACKED_ONE_TO_ONE, run_inter_j0_tracking, write_tracking_records

_TARGET_GROUPS_BY_GEOMETRY = {
    "triangle": {
        "fundamental": (0, {"twice_T": 0, "multiplicity": 1}),
        "first_excited": (1, {"twice_T": 1, "multiplicity": 1}),
    },
    "ring5": {
        "fundamental": (0, {"twice_T": 0, "multiplicity": 1}),
        "first_excited": (1, {"twice_T": 1, "multiplicity": 1}),
        "T_3_2": (2, {"twice_T": 3, "multiplicity": 1}),
    },
}


def _write_all_cases(output_dir: Path, level1c_manifest) -> None:
    """Writes all 20 grid cases with identical (group_index, twice_T,
    multiplicity, NUMERIC reflection) per target across every J0 value
    for a given (geometry, spin) -- deliberately unrealistic physics,
    but a deterministic fixture that makes every tracking edge resolve
    to TRACKED_ONE_TO_ONE, so the orchestration-level invariants (edge
    count, record count, order, T_max absence) can be checked cleanly."""
    for case in build_level1c_campaign_plan(level1c_manifest):
        target_group_data = {}
        role_by_target = {}
        for target_id, (group_index, params) in _TARGET_GROUPS_BY_GEOMETRY[case.geometry].items():
            target_group_data[target_id] = (group_index, make_group_structural_data(group_index, **params))
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


def test_run_inter_j0_tracking_produces_exactly_40_records_all_tracked(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert len(records) == 40
    assert all(record.status == TRACKED_ONE_TO_ONE for record in records)
    assert all(record.target_id != "T_max" for record in records)


def test_run_inter_j0_tracking_geometry_split_matches_target_counts(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    triangle_records = [r for r in records if r.geometry == "triangle"]
    ring5_records = [r for r in records if r.geometry == "ring5"]
    assert len(triangle_records) == 8 * len(REQUIRED_TARGET_IDS["triangle"])
    assert len(ring5_records) == 8 * len(REQUIRED_TARGET_IDS["ring5"])


def test_run_inter_j0_tracking_deterministic_order_matches_edges_then_targets(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)

    cases = build_level1c_campaign_plan(level1c_manifest)
    cases_by_id = {case.case_id: case for case in cases}
    edges = build_tracking_edges(cases)
    expected_order = [
        (perturbed_case_id, baseline_case_id, target_id)
        for perturbed_case_id, baseline_case_id in edges
        for target_id in REQUIRED_TARGET_IDS[cases_by_id[baseline_case_id].geometry]
    ]
    actual_order = [(record.perturbed_case_id, record.baseline_case_id, record.target_id) for record in records]
    assert actual_order == expected_order


def test_run_inter_j0_tracking_deterministic_repeatable(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    first = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    second = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert first == second


def test_run_inter_j0_tracking_technical_failure_yields_ambiguous_not_silent_exclusion(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    # overwrite one perturbed case with a technical failure.
    failing_case = next(
        case for case in build_level1c_campaign_plan(level1c_manifest)
        if case.geometry == "triangle" and case.spin == 2 and case.hamiltonian_case_id == "j0-0.75"
    )
    write_level1c_failed_case(
        tmp_path, case_id=failing_case.case_id, geometry="triangle", spin=2, hamiltonian_case_id="j0-0.75",
        manifest_fingerprint=level1c_manifest.fingerprint, campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT, run_status="failed",
    )
    records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert len(records) == 40
    affected = [r for r in records if r.perturbed_case_id == failing_case.case_id]
    assert len(affected) == len(REQUIRED_TARGET_IDS["triangle"])
    assert all(r.status == "AMBIGUOUS" for r in affected)
    assert all(any("PERTURBED_UNAVAILABLE" in reason for reason in r.failure_reasons) for r in affected)
    # every other record is unaffected.
    unaffected = [r for r in records if r.perturbed_case_id != failing_case.case_id]
    assert all(r.status == TRACKED_ONE_TO_ONE for r in unaffected)


def test_write_tracking_records_round_trips(tmp_path: Path, level1c_manifest) -> None:
    _write_all_cases(tmp_path, level1c_manifest)
    records = run_inter_j0_tracking(level1c_manifest, tmp_path, repository_commit=REPO_COMMIT)
    write_tracking_records(tmp_path, records)

    tracking_path = tmp_path / "tracking.jsonl"
    assert tracking_path.exists()
    lines = tracking_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 40
