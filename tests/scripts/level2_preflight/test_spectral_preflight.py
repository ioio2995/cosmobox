"""Unit tests for scripts.level2_preflight.spectral_preflight (lot
L2-D4-REAL-PREFLIGHT).

Every test exercises evaluate_report on a hand-assembled, synthetic
Level0Report (same construction technique as tests/level2/test_adapter.py)
-- never a real Level0 diagonalization, never one of the six frozen Level2
geometries. run_all_cases_preflight's own wiring/ordering is checked with
run_case_preflight monkeypatched, also without any real diagonalization.
"""

from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level0.degeneracy import analyze_spectral_degeneracies
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import (
    EigenpairDiagnostic,
    Level0Report,
    SpectrumOptions,
    SpectrumReport,
    TermExpectations,
    TermStatistics,
)
from cosmobox.level2.execution import CaseSpec
from scripts.level2_preflight.spectral_preflight import (
    FAIL,
    PASS,
    all_cases_pass,
    evaluate_report,
    run_all_cases_preflight,
)

_TERM_NAMES = ("dot", "hopping", "electric", "magnetic", "total")


def _synthetic_report(
    eigenvalues: list[float],
    *,
    method: str = "dense",
    degeneracy_dimension: int | None = None,
    report_dimension: int | None = None,
) -> Level0Report:
    n = len(eigenvalues)
    degeneracy_dimension = n if degeneracy_dimension is None else degeneracy_dimension
    report_dimension = degeneracy_dimension if report_dimension is None else report_dimension

    degeneracy = analyze_spectral_degeneracies(eigenvalues, dimension=degeneracy_dimension)
    eigenpairs = tuple(
        EigenpairDiagnostic(
            index=i,
            eigenvalue=e,
            residual_norm=0.0,
            term_expectations=TermExpectations(dot=0.0, hopping=0.0, electric=0.0, magnetic=0.0, total=e),
        )
        for i, e in enumerate(eigenvalues)
    )
    spectrum = SpectrumReport(
        status="computed",
        method=method,
        requested_eigenvalues=n,
        computed_eigenvalues=n,
        tolerance=1e-10,
        reason=None,
        eigenpairs=eigenpairs,
        spectral_gap=(eigenvalues[1] - eigenvalues[0]) if n >= 2 else None,
        degeneracy=degeneracy,
    )
    term_stats = tuple(
        TermStatistics(name=name, nnz=0, density=0.0, hermiticity_defect=0.0, frobenius_norm=0.0)
        for name in _TERM_NAMES
    )
    parameters = HamiltonianParameters(J=(1.0,), h=(np.zeros((2, 2), dtype=complex),), t=1.0, g_E=1.0, K=1.0)
    return Level0Report(
        lattice_name="synthetic",
        n_flavors=2,
        spin=1,
        external_charges=(),
        dimension=report_dimension,
        sector_count=0,
        excluded_sector_count=0,
        mean_flux_configs_per_occupation=0.0,
        max_flux_configs_per_occupation=0,
        terms=term_stats,
        spectrum=spectrum,
        spectrum_options=SpectrumOptions(n_eigenvalues=n),
        parameters=parameters,
    )


def _evaluate(report: Level0Report, *, expected_dimension: int, expected_group_count: int):
    return evaluate_report(
        report,
        expected_dimension=expected_dimension,
        expected_group_count=expected_group_count,
        geometry="triangle",
        spin=2,
    )


# ---------------------------------------------------------------------------
# evaluate_report -- PASS and every FAIL mode
# ---------------------------------------------------------------------------


def test_evaluate_report_pass_when_every_invariant_matches():
    report = _synthetic_report([0.0, 0.0, 1.0])  # dimension 3, 2 groups (mult 2, mult 1)
    result = _evaluate(report, expected_dimension=3, expected_group_count=2)

    assert result.status == PASS
    assert result.dimension == 3
    assert result.requested_eigenvalues == 3
    assert result.returned_eigenpairs == 3
    assert result.solver_method == "dense"
    assert result.window_truncated is False
    assert result.group_count == 2
    assert result.partial_subspace_count == 0
    assert result.multiplicity_sum == 3
    assert result.expected_dimension == 3
    assert result.expected_group_count == 2


def test_evaluate_report_fails_on_dimension_mismatch():
    report = _synthetic_report([0.0, 0.0, 1.0])
    result = _evaluate(report, expected_dimension=99, expected_group_count=2)
    assert result.status == FAIL
    assert result.dimension == 3
    assert result.expected_dimension == 99


def test_evaluate_report_fails_on_window_truncated_and_partial_subspace():
    # only 2 of a declared 5-dimensional spectrum computed -> window
    # truncated, last group is partial_subspace
    report = _synthetic_report([0.0, 1.0], degeneracy_dimension=5, report_dimension=5)
    result = _evaluate(report, expected_dimension=5, expected_group_count=2)
    assert result.status == FAIL
    assert result.window_truncated is True
    assert result.partial_subspace_count == 1


def test_evaluate_report_fails_on_non_dense_solver_method():
    report = _synthetic_report([0.0, 0.0, 1.0], method="sparse_eigsh")
    result = _evaluate(report, expected_dimension=3, expected_group_count=2)
    assert result.status == FAIL
    assert result.solver_method == "sparse_eigsh"


def test_evaluate_report_fails_on_group_count_mismatch():
    report = _synthetic_report([0.0, 0.0, 1.0])  # 2 real groups
    result = _evaluate(report, expected_dimension=3, expected_group_count=99)
    assert result.status == FAIL
    assert result.group_count == 2
    assert result.expected_group_count == 99


def test_evaluate_report_reports_no_energy_or_observable_fields():
    import dataclasses

    from scripts.level2_preflight.spectral_preflight import CasePreflightReport

    field_names = {field.name for field in dataclasses.fields(CasePreflightReport)}
    forbidden = {"eigenvalues", "eigenvectors", "energies", "c_tt_conn", "rho_qq", "m_tt", "r_eff", "a_qq", "m_qq"}
    assert field_names & forbidden == set()


def test_case_preflight_report_rejects_unknown_status():
    from scripts.level2_preflight.spectral_preflight import CasePreflightReport

    with pytest.raises(ValueError):
        CasePreflightReport(
            geometry="triangle",
            spin=2,
            dimension=3,
            requested_eigenvalues=3,
            returned_eigenpairs=3,
            solver_method="dense",
            window_truncated=False,
            group_count=2,
            partial_subspace_count=0,
            multiplicity_sum=3,
            expected_dimension=3,
            expected_group_count=2,
            status="MAYBE",
        )


# ---------------------------------------------------------------------------
# all_cases_pass
# ---------------------------------------------------------------------------


def test_all_cases_pass_true_only_when_every_report_passes():
    passing = _evaluate(_synthetic_report([0.0, 0.0, 1.0]), expected_dimension=3, expected_group_count=2)
    failing = _evaluate(_synthetic_report([0.0, 0.0, 1.0]), expected_dimension=99, expected_group_count=2)

    assert all_cases_pass((passing, passing)) is True
    assert all_cases_pass((passing, failing)) is False
    assert all_cases_pass(()) is True  # vacuously true, never consumed without at least one real report


# ---------------------------------------------------------------------------
# run_all_cases_preflight -- wiring/ordering only, no real diagonalization
# ---------------------------------------------------------------------------


def test_run_all_cases_preflight_iterates_in_build_all_reference_case_specs_order(monkeypatch):
    import scripts.level2_preflight.spectral_preflight as preflight_module
    from cosmobox.level2 import execution

    seen_specs: list[CaseSpec] = []

    def fake_run_case_preflight(spec: CaseSpec):
        seen_specs.append(spec)
        return f"report-for-{spec.geometry}-{spec.spin}"

    monkeypatch.setattr(preflight_module, "run_case_preflight", fake_run_case_preflight)

    reports = run_all_cases_preflight()

    expected_specs = execution.build_all_reference_case_specs()
    assert seen_specs == list(expected_specs)
    assert reports == tuple(f"report-for-{spec.geometry}-{spec.spin}" for spec in expected_specs)
