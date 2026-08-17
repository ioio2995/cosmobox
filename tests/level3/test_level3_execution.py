"""Unit tests for cosmobox.level3.execution (lot L3-B-GENERIC-EXECUTION-LAYER).

run_case's heavy dependencies are monkeypatched with fakes for the wiring
test, exactly as tests/level2/test_execution.py does -- no real lattice,
basis, Hamiltonian, or diagonalization runs there. compare_spin_pair is
exercised on synthetic CaseExecutionResult objects built directly (no
run_case call) for spins beyond S=3, since REAL_S4_EXECUTION is forbidden
by this lot's mandate. The only *real* physical execution in this file is
at S=2/S=3 (build_lattice/build_basis/... for real, on the small
"triangle" geometry) -- reused to demonstrate non-regression against the
already-accepted cosmobox.level2.execution.compare_geometry.
"""

from __future__ import annotations

import dataclasses
import inspect
from types import SimpleNamespace

import pytest

from cosmobox.level0.lattice import GEOMETRIES as LEVEL0_GEOMETRIES
from cosmobox.level2 import adapter, metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import REFERENCE_EXTERNAL_CHARGES, REFERENCE_N_FLAVORS
from cosmobox.level2.execution import build_reference_hamiltonian_parameters as level2_build_reference_hamiltonian_parameters
from cosmobox.level2.execution import compare_geometry
from cosmobox.level2.execution import run_case as level2_run_case
from cosmobox.level2.execution import CaseSpec as Level2CaseSpec
from cosmobox.level3.execution import (
    CaseExecutionResult,
    CaseSpec,
    SpinPairComparison,
    SpinPairControlComparison,
    SpinPairPrimaryComparison,
    compare_spin_pair,
    run_case,
)


def _entry(
    q_start: float, q_end: float, *, m_tt: float, r_eff: metrics.Available, a_qq: float, m_qq: metrics.Available
) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0,
        multiplicity=1,
        epsilon=0.0,
        q_start=q_start,
        q_end=q_end,
        q_midpoint=(q_start + q_end) / 2,
        m_tt=m_tt,
        r_eff=r_eff,
        a_qq=a_qq,
        m_qq=m_qq,
    )


def _synthetic_entries(n: int) -> tuple[MultipletProfileEntry, ...]:
    boundaries = [i / n for i in range(n + 1)]
    return tuple(
        _entry(
            boundaries[i],
            boundaries[i + 1],
            m_tt=float(i + 1),
            r_eff=metrics.Available(0.1 * (i + 1), None),
            a_qq=0.5,
            m_qq=metrics.Available(0.2, None),
        )
        for i in range(n)
    )


def _analyses(entries: tuple[MultipletProfileEntry, ...]) -> dict[str, orchestration.CaseMetricAnalysis]:
    return {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}


def _result(geometry: str, spin: int, n: int) -> CaseExecutionResult:
    """A purely synthetic CaseExecutionResult: no run_case, no Level0
    primitive, no physical execution of any kind -- safe to use at any
    spin, including spin=4 and beyond."""
    entries = _synthetic_entries(n)
    analyses = _analyses(entries)
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin),
        dimension=n,
        group_count=n,
        entries=entries,
        m_tt_analysis=analyses["M_TT"],
        r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"],
        m_qq_analysis=analyses["M_QQ"],
    )


# ---------------------------------------------------------------------------
# 1. CaseSpec -- generic spin, no whitelist, no physical degree of freedom
# ---------------------------------------------------------------------------


def test_case_spec_has_no_physical_degree_of_freedom():
    field_names = {field.name for field in dataclasses.fields(CaseSpec)}
    assert field_names == {"geometry", "spin"}
    forbidden = {"n_flavors", "hamiltonian_params", "external_charges", "J", "h", "t", "g_E", "K"}
    assert field_names & forbidden == set()


def test_case_spec_represents_spin_2():
    spec = CaseSpec(geometry="triangle", spin=2)
    assert spec.spin == 2


def test_case_spec_represents_spin_3():
    spec = CaseSpec(geometry="triangle", spin=3)
    assert spec.spin == 3


def test_case_spec_represents_spin_4_without_any_physical_execution():
    # CaseSpec construction alone must never trigger build_lattice/
    # build_basis/diagonalization -- it is a plain, validated data holder.
    spec = CaseSpec(geometry="triangle", spin=4)
    assert spec.spin == 4
    assert spec.geometry == "triangle"


def test_case_spec_accepts_every_level0_geometry_and_a_range_of_spins():
    for geometry in LEVEL0_GEOMETRIES:
        for spin in (1, 2, 3, 4, 5, 6, 10):
            spec = CaseSpec(geometry=geometry, spin=spin)
            assert spec.geometry == geometry
            assert spec.spin == spin


def test_case_spec_rejects_unknown_geometry():
    with pytest.raises(ValueError):
        CaseSpec(geometry="not-a-geometry", spin=2)


@pytest.mark.parametrize("spin", [0, -1])
def test_case_spec_rejects_spin_below_the_generic_level0_floor(spin: int):
    with pytest.raises(ValueError):
        CaseSpec(geometry="triangle", spin=spin)


def test_case_spec_does_not_recreate_a_spin_whitelist():
    # No (2, 3), (2, 3, 4)-style whitelist exists at this layer: every
    # module-level name is checked, since a whitelist could otherwise hide
    # behind any constant name.
    import cosmobox.level3.execution as level3_execution

    for name in dir(level3_execution):
        if name.startswith("_"):
            continue
        value = getattr(level3_execution, name)
        if isinstance(value, tuple) and value and all(isinstance(item, int) for item in value):
            pytest.fail(f"module-level integer tuple {name}={value!r} looks like a reintroduced spin whitelist")


# ---------------------------------------------------------------------------
# 2. run_case -- wiring identical to Level2's own run_case, generic in spin
# ---------------------------------------------------------------------------


def test_run_case_wires_level0_and_d2_pipeline_with_frozen_parameters_only(monkeypatch):
    spec = CaseSpec(geometry="triangle", spin=4)

    fake_lattice = SimpleNamespace(nodes=(0, 1, 2))
    fake_basis = SimpleNamespace(keys=(101, 102, 103))
    fake_key_index = {101: 0, 102: 1, 103: 2}
    fake_terms = SimpleNamespace(tag="fake-terms")
    fake_report = SimpleNamespace(tag="fake-report")
    fake_eigenvectors = "fake-eigenvectors"
    fake_charge_operators = ("charge-0", "charge-1", "charge-2")
    fake_flavor_generators = ("flavor-0", "flavor-1", "flavor-2")
    fake_entries = _synthetic_entries(3)

    calls: dict[str, object] = {}

    def fake_build_lattice(geometry):
        calls["build_lattice"] = geometry
        return fake_lattice

    def fake_build_basis(lattice, n_flavors, spin):
        calls["build_basis"] = (lattice, n_flavors, spin)
        return fake_basis

    def fake_build_key_index(keys):
        calls["build_key_index"] = keys
        return fake_key_index

    def fake_build_hamiltonian_terms(lattice, n_flavors, spin, keys, key_index, params):
        calls["build_hamiltonian_terms"] = (lattice, n_flavors, spin, keys, key_index, params)
        return fake_terms

    def fake_build_level0_report_with_eigenvectors(
        lattice, n_flavors, spin, basis, terms, params, *, external_charges, spectrum_options
    ):
        calls["build_level0_report_with_eigenvectors"] = dict(
            lattice=lattice,
            n_flavors=n_flavors,
            spin=spin,
            basis=basis,
            terms=terms,
            params=params,
            external_charges=external_charges,
            spectrum_options=spectrum_options,
        )
        return fake_report, fake_eigenvectors

    def fake_build_case_operators(lattice, n_flavors, spin, keys, key_index):
        calls["build_case_operators_count"] = calls.get("build_case_operators_count", 0) + 1
        calls["build_case_operators_args"] = (lattice, n_flavors, spin, keys, key_index)
        return fake_charge_operators, fake_flavor_generators

    def fake_build_case_multiplet_profile(report, eigenvectors, charge_operators, flavor_generators):
        calls["build_case_multiplet_profile"] = (report, eigenvectors, charge_operators, flavor_generators)
        return fake_entries

    import cosmobox.level3.execution as level3_execution

    monkeypatch.setattr(level3_execution, "build_lattice", fake_build_lattice)
    monkeypatch.setattr(level3_execution, "build_basis", fake_build_basis)
    monkeypatch.setattr(level3_execution, "build_key_index", fake_build_key_index)
    monkeypatch.setattr(level3_execution, "build_hamiltonian_terms", fake_build_hamiltonian_terms)
    monkeypatch.setattr(
        level3_execution, "build_level0_report_with_eigenvectors", fake_build_level0_report_with_eigenvectors
    )
    monkeypatch.setattr(adapter, "build_case_operators", fake_build_case_operators)
    monkeypatch.setattr(adapter, "build_case_multiplet_profile", fake_build_case_multiplet_profile)

    result = run_case(spec)

    # wiring: build_lattice -> build_basis -> build_key_index, in that
    # order, with spin=4 threaded through unchanged (never silently
    # clamped/rewritten to 2 or 3)
    assert calls["build_lattice"] == "triangle"
    assert calls["build_basis"] == (fake_lattice, REFERENCE_N_FLAVORS, 4)
    assert calls["build_key_index"] == fake_basis.keys

    expected_params = level2_build_reference_hamiltonian_parameters(len(fake_lattice.nodes))
    _, _, spin_used, _, _, used_params = calls["build_hamiltonian_terms"]
    assert spin_used == 4
    assert used_params.J == expected_params.J == (1.0, 1.0, 1.0)
    assert all((matrix == 0).all() for matrix in used_params.h)
    assert used_params.t == expected_params.t == 1.0
    assert used_params.g_E == expected_params.g_E == 1.0
    assert used_params.K == expected_params.K == 1.0

    report_call = calls["build_level0_report_with_eigenvectors"]
    assert report_call["lattice"] is fake_lattice
    assert report_call["spin"] == 4
    assert report_call["terms"] is fake_terms
    assert report_call["params"] is used_params
    assert report_call["n_flavors"] == REFERENCE_N_FLAVORS == 2
    assert report_call["external_charges"] == REFERENCE_EXTERNAL_CHARGES is None
    assert report_call["spectrum_options"].n_eigenvalues == 3

    assert calls["build_case_operators_count"] == 1
    assert calls["build_case_operators_args"] == (fake_lattice, REFERENCE_N_FLAVORS, 4, fake_basis.keys, fake_key_index)
    assert calls["build_case_multiplet_profile"] == (
        fake_report,
        fake_eigenvectors,
        fake_charge_operators,
        fake_flavor_generators,
    )

    assert result.spec is spec
    assert result.dimension == 3
    assert result.group_count == len(fake_entries)
    for metric in orchestration.ALL_METRICS:
        assert result.analysis_for(metric).metric == metric


def test_run_case_exposes_no_overridable_parameter_at_all():
    signature = inspect.signature(run_case)
    assert list(signature.parameters) == ["spec"]


# ---------------------------------------------------------------------------
# CaseExecutionResult -- structural validation, no premature provenance
# ---------------------------------------------------------------------------


def test_case_execution_result_validates_dimension_and_group_count():
    entries = _synthetic_entries(2)
    analyses = _analyses(entries)
    with pytest.raises(ValueError):
        CaseExecutionResult(
            spec=CaseSpec(geometry="triangle", spin=2),
            dimension=99,
            group_count=len(entries),
            entries=entries,
            m_tt_analysis=analyses["M_TT"],
            r_eff_analysis=analyses["R_eff"],
            a_qq_analysis=analyses["A_QQ"],
            m_qq_analysis=analyses["M_QQ"],
        )


def test_case_execution_result_carries_no_premature_provenance_fields():
    field_names = {field.name for field in dataclasses.fields(CaseExecutionResult)}
    forbidden = {"repository_commit", "campaign_id", "manifest_fingerprint", "schema_version"}
    assert field_names & forbidden == set()


# ---------------------------------------------------------------------------
# SpinPairComparison / compare_spin_pair -- generic pair semantics, no
# S=2/S=3-branded public field names
# ---------------------------------------------------------------------------


def test_spin_pair_comparison_public_api_has_no_s2_s3_branded_field():
    for cls in (SpinPairComparison, SpinPairPrimaryComparison, SpinPairControlComparison):
        field_names = {field.name for field in dataclasses.fields(cls)}
        forbidden = {"result_s2", "result_s3", "analysis_s2", "analysis_s3", "delta_hl_s2", "delta_hl_s3", "direction_s2", "direction_s3", "c_x_23", "d_x_23"}
        assert field_names & forbidden == set(), f"{cls.__name__} exposes S2/S3-branded field(s): {field_names & forbidden}"


def test_spin_pair_comparison_carries_no_premature_provenance_fields():
    field_names = {field.name for field in dataclasses.fields(SpinPairComparison)}
    forbidden = {"repository_commit", "campaign_id", "manifest_fingerprint", "schema_version"}
    assert field_names & forbidden == set()


def test_compare_spin_pair_requires_same_geometry():
    result_a = _result("triangle", 2, 3)
    result_b = _result("ring4", 3, 4)
    with pytest.raises(ValueError):
        compare_spin_pair(result_a, result_b)


def test_compare_spin_pair_rejects_identical_spins():
    result_a = _result("triangle", 3, 3)
    result_b = _result("triangle", 3, 4)
    with pytest.raises(ValueError):
        compare_spin_pair(result_a, result_b)


def test_compare_spin_pair_rejects_reversed_order():
    higher = _result("triangle", 4, 3)
    lower = _result("triangle", 2, 4)
    with pytest.raises(ValueError):
        compare_spin_pair(higher, lower)  # result_a.spin (4) >= result_b.spin (2)


def test_compare_spin_pair_accepts_2_and_3():
    result_a = _result("triangle", 2, 3)
    result_b = _result("triangle", 3, 4)
    comparison = compare_spin_pair(result_a, result_b)
    assert comparison.result_a.spec.spin == 2
    assert comparison.result_b.spec.spin == 3


def test_compare_spin_pair_accepts_a_non_consecutive_synthetic_pair_3_4():
    # Purely synthetic: no run_case, no real S=4 physical execution.
    result_a = _result("ring5", 3, 5)
    result_b = _result("ring5", 4, 7)

    comparison = compare_spin_pair(result_a, result_b)

    assert comparison.geometry == "ring5"
    assert comparison.result_a is result_a
    assert comparison.result_b is result_b
    assert comparison.m_tt.metric == "M_TT"
    assert comparison.r_eff.metric == "R_eff"
    assert comparison.m_tt.taxonomy in {
        orchestration.profiles.NOT_EVALUABLE,
        orchestration.profiles.NO_RESOLVED_SPECTRAL_CONTRAST,
        orchestration.profiles.OPPOSITE_INTER_S_DIRECTION,
        orchestration.profiles.SAME_INTER_S_DIRECTION,
    }
    assert comparison.a_qq.metric == "A_QQ"
    assert comparison.m_qq.metric == "M_QQ"
    assert not hasattr(comparison.a_qq, "taxonomy")
    assert not hasattr(comparison.a_qq, "cross_profile_correlation")


def test_compare_spin_pair_accepts_a_synthetic_pair_4_6():
    result_a = _result("triangle", 4, 3)
    result_b = _result("triangle", 6, 5)
    comparison = compare_spin_pair(result_a, result_b)
    assert comparison.result_a.spec.spin == 4
    assert comparison.result_b.spec.spin == 6


def test_compare_spin_pair_matches_direct_orchestration_calls():
    result_a = _result("triangle", 2, 3)
    result_b = _result("triangle", 3, 3)

    comparison = compare_spin_pair(result_a, result_b)

    raw_m_tt = orchestration.compare_primary_metric_inter_s(
        result_a.analysis_for("M_TT"), result_b.analysis_for("M_TT"), metric="M_TT"
    )
    assert comparison.m_tt.delta_hl_lower == raw_m_tt.delta_hl_s2
    assert comparison.m_tt.delta_hl_higher == raw_m_tt.delta_hl_s3
    assert comparison.m_tt.taxonomy == raw_m_tt.classification.taxonomy
    assert comparison.m_tt.direction_lower == raw_m_tt.classification.direction_s2
    assert comparison.m_tt.direction_higher == raw_m_tt.classification.direction_s3
    assert comparison.m_tt.cross_profile_correlation == raw_m_tt.c_x_23
    assert comparison.m_tt.cross_profile_distance == raw_m_tt.d_x_23

    raw_a_qq = orchestration.compare_control_metric_inter_s(
        result_a.analysis_for("A_QQ"), result_b.analysis_for("A_QQ"), metric="A_QQ"
    )
    assert comparison.a_qq.analysis_a == raw_a_qq.analysis_s2
    assert comparison.a_qq.analysis_b == raw_a_qq.analysis_s3


# ---------------------------------------------------------------------------
# Non-regression: real S=2/S=3 execution on "triangle" reproduces the
# already-accepted Level2 dimension/group_count and matches
# cosmobox.level2.execution.compare_geometry's own verdict exactly, without
# re-running the frozen normative campaign.
# ---------------------------------------------------------------------------


def test_run_case_reproduces_l2_a1_reference_for_triangle_s2_and_s3():
    from cosmobox.level2.execution import L2_A1_PREFLIGHT_REFERENCE

    for spin in (2, 3):
        result = run_case(CaseSpec(geometry="triangle", spin=spin))
        expected_dimension, expected_group_count = L2_A1_PREFLIGHT_REFERENCE[("triangle", spin)]
        assert result.dimension == expected_dimension
        assert result.group_count == expected_group_count


def test_compare_spin_pair_matches_legacy_compare_geometry_for_s2_s3_triangle():
    level3_result_a = run_case(CaseSpec(geometry="triangle", spin=2))
    level3_result_b = run_case(CaseSpec(geometry="triangle", spin=3))
    level3_comparison = compare_spin_pair(level3_result_a, level3_result_b)

    legacy_result_s2 = level2_run_case(Level2CaseSpec(geometry="triangle", spin=2))
    legacy_result_s3 = level2_run_case(Level2CaseSpec(geometry="triangle", spin=3))
    legacy_comparison = compare_geometry(legacy_result_s2, legacy_result_s3)

    assert level3_comparison.geometry == legacy_comparison.geometry
    assert level3_comparison.m_tt.taxonomy == legacy_comparison.m_tt.classification.taxonomy
    assert level3_comparison.m_tt.direction_lower == legacy_comparison.m_tt.classification.direction_s2
    assert level3_comparison.m_tt.direction_higher == legacy_comparison.m_tt.classification.direction_s3
    assert level3_comparison.m_tt.cross_profile_correlation == legacy_comparison.m_tt.c_x_23
    assert level3_comparison.m_tt.cross_profile_distance == legacy_comparison.m_tt.d_x_23
    assert level3_comparison.r_eff.taxonomy == legacy_comparison.r_eff.classification.taxonomy
    assert level3_comparison.a_qq.analysis_a == legacy_comparison.a_qq.analysis_s2
    assert level3_comparison.a_qq.analysis_b == legacy_comparison.a_qq.analysis_s3
