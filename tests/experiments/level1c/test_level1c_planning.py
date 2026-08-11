from __future__ import annotations

import pytest

from experiments.level1c import manifest as m
from experiments.level1c import planning as p


@pytest.fixture(scope="module")
def manifest() -> m.Level1CManifest:
    return m.load_manifest()


@pytest.fixture(scope="module")
def cases(manifest: m.Level1CManifest) -> tuple:
    return p.build_level1c_campaign_plan(manifest)


# ---------------------------------------------------------------------------
# Case count / canonical order (governance-mandated: 20 cases)
# ---------------------------------------------------------------------------


def test_build_level1c_campaign_plan_produces_exactly_20_cases(cases: tuple) -> None:
    assert len(cases) == 20


def test_case_order_is_geometry_then_spin_then_increasing_j0(cases: tuple) -> None:
    expected_order = [
        (geometry, spin, j0)
        for geometry in m.GEOMETRIES
        for spin in m.SPIN_VALUES
        for j0 in m.J0_GRID
    ]
    # J0 is not directly a field of CampaignCaseSpec; recover it from
    # hamiltonian_case_id via the same naming convention the manifest uses.
    actual_order = [
        (case.geometry, case.spin, float(case.hamiltonian_case_id.removeprefix("j0-")))
        for case in cases
    ]
    assert actual_order == expected_order


def test_case_ids_are_all_unique(cases: tuple) -> None:
    case_ids = [case.case_id for case in cases]
    assert len(case_ids) == len(set(case_ids))


def test_case_id_uses_compute_case_id_convention(manifest: m.Level1CManifest, cases: tuple) -> None:
    """The case_id must be exactly what experiments.level1.planning.
    compute_case_id would produce for the same content -- no separate ID
    scheme invented for Level1C."""
    from experiments.level1.planning import compute_case_id

    first = cases[0]
    recomputed = compute_case_id(
        geometry=first.geometry,
        spin=first.spin,
        hamiltonian_case_id=first.hamiltonian_case_id,
        hamiltonian_parameters=first.hamiltonian_parameters,
        sector_id=first.sector_id,
        spectral_window=first.spectral_window,
        target_groups=first.target_groups,
    )
    assert recomputed == first.case_id


def test_spectral_window_matches_frozen_production_window(manifest: m.Level1CManifest, cases: tuple) -> None:
    for case in cases:
        j0 = float(case.hamiltonian_case_id.removeprefix("j0-"))
        assert case.spectral_window == m.FROZEN_PRODUCTION_WINDOWS[(case.geometry, j0)]


def test_j0_perturbation_is_on_node_0_only(cases: tuple) -> None:
    for case in cases:
        j = case.hamiltonian_parameters.J
        j0 = float(case.hamiltonian_case_id.removeprefix("j0-"))
        assert j[0] == j0
        assert all(value == 1.0 for value in j[1:])


# ---------------------------------------------------------------------------
# Baseline mapping (governance-mandated: 4 baselines, 16 perturbed, explicit)
# ---------------------------------------------------------------------------


def test_exactly_4_baseline_cases(cases: tuple) -> None:
    baseline_id = p.hamiltonian_case_id_for_j0(p.J0_BASELINE)
    baselines = [case for case in cases if case.hamiltonian_case_id == baseline_id]
    assert len(baselines) == 4


def test_exactly_16_perturbed_cases(cases: tuple) -> None:
    baseline_id = p.hamiltonian_case_id_for_j0(p.J0_BASELINE)
    perturbed = [case for case in cases if case.hamiltonian_case_id != baseline_id]
    assert len(perturbed) == 16


def test_baseline_mapping_has_exactly_16_entries(cases: tuple) -> None:
    mapping = p.build_baseline_mapping(cases)
    assert len(mapping) == 16


def test_baseline_mapping_is_explicit_same_geometry_and_spin(cases: tuple) -> None:
    mapping = p.build_baseline_mapping(cases)
    cases_by_id = {case.case_id: case for case in cases}
    for perturbed_id, baseline_id in mapping.items():
        perturbed = cases_by_id[perturbed_id]
        baseline = cases_by_id[baseline_id]
        assert perturbed.geometry == baseline.geometry
        assert perturbed.spin == baseline.spin
        assert baseline.hamiltonian_case_id == p.hamiltonian_case_id_for_j0(p.J0_BASELINE)
        assert perturbed.hamiltonian_case_id != baseline.hamiltonian_case_id


def test_baseline_mapping_never_maps_a_baseline_to_itself(cases: tuple) -> None:
    mapping = p.build_baseline_mapping(cases)
    baseline_id = p.hamiltonian_case_id_for_j0(p.J0_BASELINE)
    cases_by_id = {case.case_id: case for case in cases}
    for case_id in mapping:
        assert cases_by_id[case_id].hamiltonian_case_id != baseline_id


# ---------------------------------------------------------------------------
# Tracking edges (governance-mandated: 16 = 4 baselines x 4 perturbations)
# ---------------------------------------------------------------------------


def test_exactly_16_tracking_edges(cases: tuple) -> None:
    edges = p.build_tracking_edges(cases)
    assert len(edges) == 16


def test_each_baseline_has_exactly_4_tracking_edges(cases: tuple) -> None:
    edges = p.build_tracking_edges(cases)
    from collections import Counter

    counts = Counter(baseline_id for _perturbed_id, baseline_id in edges)
    assert len(counts) == 4
    assert all(count == 4 for count in counts.values())


def test_tracking_edge_order_follows_case_order(cases: tuple) -> None:
    edges = p.build_tracking_edges(cases)
    baseline_id = p.hamiltonian_case_id_for_j0(p.J0_BASELINE)
    expected_perturbed_order = [case.case_id for case in cases if case.hamiltonian_case_id != baseline_id]
    assert [perturbed_id for perturbed_id, _baseline_id in edges] == expected_perturbed_order
