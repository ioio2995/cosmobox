"""Unit tests for cosmobox.level2.execution (lot L2-D4-EXECUTION).

run_case's heavy dependencies (build_lattice, build_basis, build_key_index,
build_hamiltonian_terms, build_level0_report_with_eigenvectors,
adapter.build_case_operators, adapter.build_case_multiplet_profile) are all
monkeypatched with fakes, so no real lattice, basis, Hamiltonian, or
diagonalization ever runs. orchestration.analyze_case_metric runs for real
against hand-built MultipletProfileEntry tuples (cheap, pure, already
tested by L2-D3) -- this checks the real wiring/math of this layer's own
new code, not Level0/Level1's.
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from cosmobox.level2 import adapter, metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import (
    GEOMETRIES,
    SPINS,
    CaseExecutionResult,
    CaseSpec,
    GeometryComparison,
    build_all_reference_case_specs,
    build_reference_case_spec,
    build_reference_hamiltonian_parameters,
    compare_geometry,
    run_case,
)


def _entry(q_start: float, q_end: float, *, m_tt: float, r_eff: metrics.Available, a_qq: float, m_qq: metrics.Available) -> MultipletProfileEntry:
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


def _reference_spec(geometry: str = "triangle", spin: int = 2) -> CaseSpec:
    return CaseSpec(
        geometry=geometry,
        spin=spin,
        n_flavors=2,
        hamiltonian_params=build_reference_hamiltonian_parameters(3),
    )


# ---------------------------------------------------------------------------
# 1. CaseSpec -- domain, and the six normative combinations
# ---------------------------------------------------------------------------


def test_case_spec_accepts_exactly_the_level2_domain():
    for geometry in GEOMETRIES:
        for spin in SPINS:
            spec = build_reference_case_spec(geometry, spin)
            assert spec.geometry == geometry
            assert spec.spin == spin
            assert spec.n_flavors == 2
            assert spec.external_charges is None


def test_case_spec_rejects_geometry_outside_contract():
    with pytest.raises(ValueError):
        CaseSpec(geometry="ring6", spin=2, n_flavors=2, hamiltonian_params=build_reference_hamiltonian_parameters(3))


def test_case_spec_rejects_spin_outside_contract():
    with pytest.raises(ValueError):
        CaseSpec(geometry="triangle", spin=1, n_flavors=2, hamiltonian_params=build_reference_hamiltonian_parameters(3))


def test_case_spec_rejects_n_flavors_other_than_two():
    with pytest.raises(ValueError):
        CaseSpec(geometry="triangle", spin=2, n_flavors=3, hamiltonian_params=build_reference_hamiltonian_parameters(3))


def test_build_reference_hamiltonian_parameters_matches_frozen_contract():
    params = build_reference_hamiltonian_parameters(4)
    assert params.J == (1.0, 1.0, 1.0, 1.0)
    assert params.t == 1.0
    assert params.g_E == 1.0
    assert params.K == 1.0
    assert len(params.h) == 4
    for matrix in params.h:
        assert (matrix == 0).all()


def test_build_all_reference_case_specs_covers_exactly_the_six_normative_cases():
    specs = build_all_reference_case_specs()
    combos = {(spec.geometry, spec.spin) for spec in specs}
    assert combos == {(geometry, spin) for geometry in GEOMETRIES for spin in SPINS}
    assert len(specs) == 6


# ---------------------------------------------------------------------------
# 2-5. run_case: wiring, SpectrumOptions(n_eigenvalues=dimension), single
# operator construction, four D3 analyses
# ---------------------------------------------------------------------------


def test_run_case_wires_level0_and_d2_pipeline_without_real_diagonalization(monkeypatch):
    spec = _reference_spec()

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
        calls["build_case_operators"] = calls.get("build_case_operators", 0)
        calls["build_case_operators_count"] = calls.get("build_case_operators_count", 0) + 1
        calls["build_case_operators_args"] = (lattice, n_flavors, spin, keys, key_index)
        return fake_charge_operators, fake_flavor_generators

    def fake_build_case_multiplet_profile(report, eigenvectors, charge_operators, flavor_generators):
        calls["build_case_multiplet_profile"] = (report, eigenvectors, charge_operators, flavor_generators)
        return fake_entries

    import cosmobox.level2.execution as execution_module

    monkeypatch.setattr(execution_module, "build_lattice", fake_build_lattice)
    monkeypatch.setattr(execution_module, "build_basis", fake_build_basis)
    monkeypatch.setattr(execution_module, "build_key_index", fake_build_key_index)
    monkeypatch.setattr(execution_module, "build_hamiltonian_terms", fake_build_hamiltonian_terms)
    monkeypatch.setattr(
        execution_module, "build_level0_report_with_eigenvectors", fake_build_level0_report_with_eigenvectors
    )
    monkeypatch.setattr(adapter, "build_case_operators", fake_build_case_operators)
    monkeypatch.setattr(adapter, "build_case_multiplet_profile", fake_build_case_multiplet_profile)

    result = run_case(spec)

    # wiring: build_lattice -> build_basis -> build_key_index, in that order
    assert calls["build_lattice"] == "triangle"
    assert calls["build_basis"] == (fake_lattice, 2, 2)
    assert calls["build_key_index"] == fake_basis.keys

    # build_hamiltonian_terms receives spec.hamiltonian_params, never a copy
    assert calls["build_hamiltonian_terms"] == (fake_lattice, 2, 2, fake_basis.keys, fake_key_index, spec.hamiltonian_params)

    # SpectrumOptions.n_eigenvalues is exactly dimension = len(fake_basis.keys) == 3,
    # never a smaller/overridable window
    report_call = calls["build_level0_report_with_eigenvectors"]
    assert report_call["lattice"] is fake_lattice
    assert report_call["terms"] is fake_terms
    assert report_call["params"] is spec.hamiltonian_params
    assert report_call["external_charges"] == spec.external_charges
    assert report_call["spectrum_options"].n_eigenvalues == 3

    # operators are constructed exactly once per case
    assert calls["build_case_operators_count"] == 1
    assert calls["build_case_operators_args"] == (fake_lattice, 2, 2, fake_basis.keys, fake_key_index)

    assert calls["build_case_multiplet_profile"] == (fake_report, fake_eigenvectors, fake_charge_operators, fake_flavor_generators)

    # CaseExecutionResult assembly
    assert result.spec is spec
    assert result.dimension == 3
    assert result.group_count == len(fake_entries)
    assert result.entries == fake_entries
    for metric in orchestration.ALL_METRICS:
        assert result.analysis_for(metric).metric == metric


def test_run_case_exposes_no_smaller_eigenvalue_window_parameter():
    import inspect

    signature = inspect.signature(run_case)
    assert list(signature.parameters) == ["spec"]  # no n_eigenvalues/window override is exposable at all


# ---------------------------------------------------------------------------
# CaseExecutionResult -- structural validation, no premature provenance
# ---------------------------------------------------------------------------


def test_case_execution_result_validates_dimension_and_group_count():
    spec = _reference_spec()
    entries = _synthetic_entries(2)
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}

    with pytest.raises(ValueError):
        CaseExecutionResult(
            spec=spec,
            dimension=99,  # deliberately wrong
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


def test_geometry_comparison_carries_no_premature_provenance_fields():
    field_names = {field.name for field in dataclasses.fields(GeometryComparison)}
    forbidden = {"repository_commit", "campaign_id", "manifest_fingerprint", "schema_version"}
    assert field_names & forbidden == set()


# ---------------------------------------------------------------------------
# 6. compare_geometry -- structural validation, primary vs control split,
# no inter-S multiplet matching
# ---------------------------------------------------------------------------


def _result(geometry: str, spin: int, n: int) -> CaseExecutionResult:
    spec = _reference_spec(geometry=geometry, spin=spin)
    entries = _synthetic_entries(n)
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=spec,
        dimension=n,
        group_count=n,
        entries=entries,
        m_tt_analysis=analyses["M_TT"],
        r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"],
        m_qq_analysis=analyses["M_QQ"],
    )


def test_compare_geometry_requires_same_geometry():
    result_s2 = _result("triangle", 2, 3)
    result_s3 = _result("ring4", 3, 4)
    with pytest.raises(ValueError):
        compare_geometry(result_s2, result_s3)


def test_compare_geometry_requires_spin_2_then_spin_3():
    result_s2 = _result("triangle", 2, 3)
    result_s3 = _result("triangle", 2, 4)  # wrong spin
    with pytest.raises(ValueError):
        compare_geometry(result_s2, result_s3)

    result_wrong_order = _result("triangle", 3, 3)
    result_also_s3 = _result("triangle", 3, 4)
    with pytest.raises(ValueError):
        compare_geometry(result_wrong_order, result_also_s3)


def test_compare_geometry_splits_primary_and_control_correctly_without_multiplet_matching():
    # different group counts/partitions for S=2 and S=3 -- no matching required
    result_s2 = _result("ring5", 2, 3)
    result_s3 = _result("ring5", 3, 5)

    comparison = compare_geometry(result_s2, result_s3)

    assert comparison.geometry == "ring5"
    assert comparison.result_s2 is result_s2
    assert comparison.result_s3 is result_s3

    assert comparison.m_tt.metric == "M_TT"
    assert comparison.r_eff.metric == "R_eff"
    assert comparison.m_tt.classification.taxonomy in {
        orchestration.profiles.NOT_EVALUABLE,
        orchestration.profiles.NO_RESOLVED_SPECTRAL_CONTRAST,
        orchestration.profiles.OPPOSITE_INTER_S_DIRECTION,
        orchestration.profiles.SAME_INTER_S_DIRECTION,
    }

    assert comparison.a_qq.metric == "A_QQ"
    assert comparison.m_qq.metric == "M_QQ"
    assert not hasattr(comparison.a_qq, "classification")
    assert not hasattr(comparison.a_qq, "c_x_23")
    assert not hasattr(comparison.m_qq, "d_x_23")


def test_compare_geometry_matches_direct_orchestration_calls():
    result_s2 = _result("triangle", 2, 3)
    result_s3 = _result("triangle", 3, 3)

    comparison = compare_geometry(result_s2, result_s3)

    expected_m_tt = orchestration.compare_primary_metric_inter_s(
        result_s2.analysis_for("M_TT"), result_s3.analysis_for("M_TT"), metric="M_TT"
    )
    assert comparison.m_tt == expected_m_tt

    expected_a_qq = orchestration.compare_control_metric_inter_s(
        result_s2.analysis_for("A_QQ"), result_s3.analysis_for("A_QQ"), metric="A_QQ"
    )
    assert comparison.a_qq == expected_a_qq
