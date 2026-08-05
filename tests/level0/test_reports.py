from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import BasisReport, SectorReport, build_basis
from cosmobox.level0.hamiltonian import HamiltonianTerms, build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import (
    EigenpairDiagnostic,
    Level0Report,
    SpectrumOptions,
    SpectrumReport,
    TermExpectations,
    TermStatistics,
    _eigenpair_diagnostic,
    build_level0_report,
)


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _params(n_nodes: int, *, t: float = 0.7, g_E: float = 0.6, K: float = 0.5) -> HamiltonianParameters:
    J = tuple(0.3 - 0.2 * i for i in range(n_nodes))
    h = tuple(_hermitian_matrix(0.2 * i, -0.2 * i, 0.15 + 0.1j) for i in range(n_nodes))
    return HamiltonianParameters(J=J, h=h, t=t, g_E=g_E, K=K)


def _build(geometry: str, n_flavors: int = 2, spin: int = 1):
    lattice = build_lattice(geometry)
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _params(len(lattice.nodes))
    terms = build_hamiltonian_terms(lattice, n_flavors, spin, report.keys, key_index, params)
    return lattice, report, terms, params


# ---------------------------------------------------------------------------
# SpectrumOptions validation
# ---------------------------------------------------------------------------


def test_spectrum_options_defaults_are_valid() -> None:
    SpectrumOptions()  # must not raise


def test_spectrum_options_rejects_negative_max_dense_dimension() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(max_dense_dimension=-1)


def test_spectrum_options_rejects_negative_max_sparse_dimension() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(max_sparse_dimension=-1)


def test_spectrum_options_rejects_dense_threshold_above_sparse_threshold() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(max_dense_dimension=100, max_sparse_dimension=10)


def test_spectrum_options_rejects_non_positive_n_eigenvalues() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(n_eigenvalues=0)


@pytest.mark.parametrize("bad_tolerance", [0.0, -1e-10, float("inf"), float("nan")])
def test_spectrum_options_rejects_bad_tolerance(bad_tolerance: float) -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(tolerance=bad_tolerance)


def test_spectrum_options_rejects_non_positive_max_iterations() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(max_iterations=0)


# ---------------------------------------------------------------------------
# Dense path
# ---------------------------------------------------------------------------


def test_dense_path_on_triangle() -> None:
    lattice, report, terms, params = _build("triangle")
    result = build_level0_report(lattice, 2, 1, report, terms, params)

    assert result.dimension == len(report.keys)
    assert result.spectrum.status == "computed"
    assert result.spectrum.method == "dense"
    assert result.spectrum.computed_eigenvalues == min(6, result.dimension)

    eigenvalues = [ep.eigenvalue for ep in result.spectrum.eigenpairs]
    assert eigenvalues == sorted(eigenvalues)
    assert all(np.isfinite(e) for e in eigenvalues)

    for eigenpair in result.spectrum.eigenpairs:
        assert eigenpair.residual_norm < 1e-8
        te = eigenpair.term_expectations
        assert (te.dot + te.hopping + te.electric + te.magnetic) == pytest.approx(te.total, abs=1e-8)
        assert te.total == pytest.approx(eigenpair.eigenvalue, abs=1e-8)

    assert result.spectrum.spectral_gap == pytest.approx(
        result.spectrum.eigenpairs[1].eigenvalue - result.spectrum.eigenpairs[0].eigenvalue
    )


def test_term_statistics_are_in_fixed_order_with_five_entries() -> None:
    lattice, report, terms, params = _build("triangle")
    result = build_level0_report(lattice, 2, 1, report, terms, params)
    assert [t.name for t in result.terms] == ["dot", "hopping", "electric", "magnetic", "total"]


def test_term_statistics_values_are_sane() -> None:
    lattice, report, terms, params = _build("triangle")
    result = build_level0_report(lattice, 2, 1, report, terms, params)
    dim = result.dimension
    for stats in result.terms:
        assert 0 <= stats.nnz <= dim * dim
        assert 0.0 <= stats.density <= 1.0
        assert stats.hermiticity_defect < 1e-10
        assert stats.frobenius_norm >= 0.0


# ---------------------------------------------------------------------------
# Sparse path -- forced by lowering max_dense_dimension on a small system,
# never by picking a heavy geometry to cross the default threshold
# ---------------------------------------------------------------------------


def test_sparse_path_matches_dense_within_tolerance() -> None:
    lattice, report, terms, params = _build("ring4")

    dense_options = SpectrumOptions(max_dense_dimension=10_000, n_eigenvalues=4)
    sparse_options = SpectrumOptions(max_dense_dimension=0, n_eigenvalues=4)

    dense_result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=dense_options)
    sparse_result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=sparse_options)

    assert dense_result.spectrum.method == "dense"
    assert sparse_result.spectrum.method == "sparse_eigsh"

    dense_eigenvalues = [ep.eigenvalue for ep in dense_result.spectrum.eigenpairs]
    sparse_eigenvalues = [ep.eigenvalue for ep in sparse_result.spectrum.eigenpairs]
    assert sparse_eigenvalues == pytest.approx(dense_eigenvalues, abs=1e-6)

    for eigenpair in sparse_result.spectrum.eigenpairs:
        assert eigenpair.residual_norm < 1e-6


def test_sparse_path_reports_failed_status_on_arpack_non_convergence() -> None:
    lattice, report, terms, params = _build("ring4")
    options = SpectrumOptions(max_dense_dimension=0, n_eigenvalues=3, max_iterations=1)
    result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)

    assert result.spectrum.status == "failed"
    assert result.spectrum.method == "sparse_eigsh"
    assert result.spectrum.eigenpairs == ()
    assert result.spectrum.computed_eigenvalues == 0
    assert result.spectrum.spectral_gap is None
    assert result.spectrum.reason  # non-empty, explicit
    # the rest of the report remains fully populated even on spectral failure
    assert result.dimension == len(report.keys)
    assert len(result.terms) == 5


# ---------------------------------------------------------------------------
# not_computed -- small system, artificially lowered max_sparse_dimension.
# No disk7 construction anywhere in this file.
# ---------------------------------------------------------------------------


def test_not_computed_when_dimension_exceeds_max_sparse_dimension() -> None:
    lattice, report, terms, params = _build("triangle")
    dimension = len(report.keys)
    options = SpectrumOptions(max_dense_dimension=0, max_sparse_dimension=dimension - 1)

    result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)

    assert result.spectrum.status == "not_computed"
    assert result.spectrum.method is None
    assert result.spectrum.eigenpairs == ()
    assert result.spectrum.computed_eigenvalues == 0
    assert result.spectrum.spectral_gap is None
    assert result.spectrum.reason  # non-empty and specific
    assert str(dimension) in result.spectrum.reason

    # base and matrix statistics remain available
    assert result.dimension == dimension
    assert len(result.terms) == 5
    assert all(stats.hermiticity_defect < 1e-10 for stats in result.terms)


def test_force_overrides_max_sparse_dimension_but_not_max_dense_conversion() -> None:
    lattice, report, terms, params = _build("triangle")
    dimension = len(report.keys)
    options = SpectrumOptions(max_dense_dimension=0, max_sparse_dimension=dimension - 1, force=True)

    result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)

    # force bypasses max_sparse_dimension, but dense is only ever chosen by
    # the dimension <= max_dense_dimension test -- never forced.
    assert result.spectrum.status == "computed"
    assert result.spectrum.method == "sparse_eigsh"


# ---------------------------------------------------------------------------
# Reproducibility: exact for combinatorial/matrix fields, tolerance for
# spectral results, never a bitwise eigenvector comparison
# ---------------------------------------------------------------------------


def test_reproducibility_combinatorial_and_matrix_fields_exact() -> None:
    lattice, report, terms, params = _build("triangle")
    result_a = build_level0_report(lattice, 2, 1, report, terms, params)
    result_b = build_level0_report(lattice, 2, 1, report, terms, params)

    assert result_a.dimension == result_b.dimension
    assert result_a.sector_count == result_b.sector_count
    assert result_a.excluded_sector_count == result_b.excluded_sector_count
    for stats_a, stats_b in zip(result_a.terms, result_b.terms):
        assert stats_a.nnz == stats_b.nnz
        assert stats_a.density == stats_b.density
        assert stats_a.hermiticity_defect == stats_b.hermiticity_defect
        assert stats_a.frobenius_norm == stats_b.frobenius_norm


def test_reproducibility_dense_spectrum_within_tolerance() -> None:
    lattice, report, terms, params = _build("triangle")
    result_a = build_level0_report(lattice, 2, 1, report, terms, params)
    result_b = build_level0_report(lattice, 2, 1, report, terms, params)

    eigenvalues_a = [ep.eigenvalue for ep in result_a.spectrum.eigenpairs]
    eigenvalues_b = [ep.eigenvalue for ep in result_b.spectrum.eigenpairs]
    assert eigenvalues_a == pytest.approx(eigenvalues_b, abs=1e-12)


def test_reproducibility_sparse_spectrum_within_tolerance() -> None:
    lattice, report, terms, params = _build("ring4")
    options = SpectrumOptions(max_dense_dimension=0, n_eigenvalues=4)
    result_a = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)
    result_b = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)

    eigenvalues_a = [ep.eigenvalue for ep in result_a.spectrum.eigenpairs]
    eigenvalues_b = [ep.eigenvalue for ep in result_b.spectrum.eigenpairs]
    assert eigenvalues_a == pytest.approx(eigenvalues_b, abs=1e-8)
    residuals_a = [ep.residual_norm for ep in result_a.spectrum.eigenpairs]
    residuals_b = [ep.residual_norm for ep in result_b.spectrum.eigenpairs]
    assert residuals_a == pytest.approx(residuals_b, abs=1e-6)


# ---------------------------------------------------------------------------
# Edge cases: dimension 0, dimension 1
# ---------------------------------------------------------------------------


def _empty_csr() -> sp.csr_matrix:
    return sp.csr_matrix((0, 0), dtype=np.complex128)


def test_dimension_zero_is_computed_direct_and_empty() -> None:
    lattice = build_lattice("triangle")
    basis = BasisReport(
        keys=(), sectors=(), excluded_sectors=(), mean_flux_configs_per_occupation=0.0, max_flux_configs_per_occupation=0
    )
    empty = _empty_csr()
    terms = HamiltonianTerms(dot=empty, hopping=empty, electric=empty, magnetic=empty)
    params = _params(len(lattice.nodes))

    result = build_level0_report(lattice, 2, 1, basis, terms, params)

    assert result.dimension == 0
    assert result.spectrum.status == "computed"
    assert result.spectrum.method == "direct"
    assert result.spectrum.computed_eigenvalues == 0
    assert result.spectrum.eigenpairs == ()
    assert result.spectrum.spectral_gap is None
    for stats in result.terms:
        assert stats.nnz == 0
        assert stats.density == 0.0


def test_dimension_one_is_computed_direct_with_diagonal_eigenvalue() -> None:
    lattice = build_lattice("triangle")
    real_report = build_basis(lattice, 2, 1)
    single_key = real_report.keys[0]

    basis = BasisReport(
        keys=(single_key,),
        sectors=(SectorReport(charge_vector=(Fraction(0),) * 3, matter_multiplicity=1, n_flux_admissible=1, dimension=1),),
        excluded_sectors=(),
        mean_flux_configs_per_occupation=1.0,
        max_flux_configs_per_occupation=1,
    )
    diagonal_value = 1.75
    single = sp.csr_matrix(np.array([[diagonal_value]], dtype=np.complex128))
    zero = sp.csr_matrix((1, 1), dtype=np.complex128)
    terms = HamiltonianTerms(dot=zero, hopping=zero, electric=single, magnetic=zero)
    params = _params(len(lattice.nodes))

    result = build_level0_report(lattice, 2, 1, basis, terms, params)

    assert result.dimension == 1
    assert result.spectrum.status == "computed"
    assert result.spectrum.method == "direct"
    assert result.spectrum.computed_eigenvalues == 1
    eigenpair = result.spectrum.eigenpairs[0]
    assert eigenpair.eigenvalue == pytest.approx(diagonal_value)
    assert eigenpair.residual_norm < 1e-12
    assert eigenpair.term_expectations.electric == pytest.approx(diagonal_value)
    assert eigenpair.term_expectations.total == pytest.approx(diagonal_value)
    assert result.spectrum.spectral_gap is None


# ---------------------------------------------------------------------------
# n_eigenvalues larger than the dimension
# ---------------------------------------------------------------------------


def test_n_eigenvalues_larger_than_dimension_is_capped() -> None:
    lattice, report, terms, params = _build("triangle")
    dimension = len(report.keys)
    options = SpectrumOptions(n_eigenvalues=dimension + 1000)
    result = build_level0_report(lattice, 2, 1, report, terms, params, spectrum_options=options)
    assert result.spectrum.computed_eigenvalues == dimension


# ---------------------------------------------------------------------------
# Structural consistency checks
# ---------------------------------------------------------------------------


def test_rejects_terms_with_shape_incompatible_with_basis() -> None:
    lattice, report, terms, params = _build("triangle")
    wrong_shape = sp.csr_matrix((len(report.keys) + 1, len(report.keys) + 1), dtype=np.complex128)
    mismatched = HamiltonianTerms(dot=wrong_shape, hopping=wrong_shape, electric=wrong_shape, magnetic=wrong_shape)
    with pytest.raises(ValueError):
        build_level0_report(lattice, 2, 1, report, mismatched, params)


def test_rejects_duplicate_keys_in_basis() -> None:
    lattice, report, terms, params = _build("triangle")
    duplicated_keys = report.keys + (report.keys[0],)
    duplicated_basis = BasisReport(
        keys=duplicated_keys,
        sectors=report.sectors,
        excluded_sectors=report.excluded_sectors,
        mean_flux_configs_per_occupation=report.mean_flux_configs_per_occupation,
        max_flux_configs_per_occupation=report.max_flux_configs_per_occupation,
    )
    wrong_shape = sp.csr_matrix((len(duplicated_keys), len(duplicated_keys)), dtype=np.complex128)
    resized_terms = HamiltonianTerms(dot=wrong_shape, hopping=wrong_shape, electric=wrong_shape, magnetic=wrong_shape)
    with pytest.raises(ValueError):
        build_level0_report(lattice, 2, 1, duplicated_basis, resized_terms, params)


def test_rejects_basis_inconsistent_with_declared_external_charges() -> None:
    lattice, report, terms, params = _build("triangle")
    # report.keys is physical for *no* external charge; declaring a nonzero
    # one makes every key inconsistent with the declared provenance.
    with pytest.raises(ValueError):
        build_level0_report(
            lattice, 2, 1, report, terms, params, external_charges=(1, 0, 0)
        )


def test_rejects_non_positive_n_flavors() -> None:
    lattice, report, terms, params = _build("triangle")
    with pytest.raises(ValueError):
        build_level0_report(lattice, 0, 1, report, terms, params)


# ---------------------------------------------------------------------------
# SpectrumOptions.seed validation
# ---------------------------------------------------------------------------


def test_spectrum_options_rejects_negative_seed() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(seed=-1)


def test_spectrum_options_rejects_bool_seed() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(seed=True)


def test_spectrum_options_rejects_non_int_seed() -> None:
    with pytest.raises(ValueError):
        SpectrumOptions(seed=1.5)


# ---------------------------------------------------------------------------
# Refuse to diagonalize a non-Hermitian H_total (dense and sparse)
# ---------------------------------------------------------------------------


def _two_key_basis_and_non_hermitian_terms():
    lattice = build_lattice("triangle")
    real_report = build_basis(lattice, 2, 1)
    two_keys = real_report.keys[:2]
    basis = BasisReport(
        keys=two_keys,
        sectors=(),
        excluded_sectors=(),
        mean_flux_configs_per_occupation=0.0,
        max_flux_configs_per_occupation=0,
    )
    zero = sp.csr_matrix((2, 2), dtype=np.complex128)
    non_hermitian = sp.csr_matrix(np.array([[0, 1], [0, 0]], dtype=np.complex128))
    terms = HamiltonianTerms(dot=zero, hopping=zero, electric=zero, magnetic=non_hermitian)
    return lattice, basis, terms


def test_dense_path_rejects_non_hermitian_total() -> None:
    lattice, basis, terms = _two_key_basis_and_non_hermitian_terms()
    params = _params(len(lattice.nodes))
    options = SpectrumOptions(max_dense_dimension=10)
    with pytest.raises(ValueError, match="not Hermitian"):
        build_level0_report(lattice, 2, 1, basis, terms, params, spectrum_options=options)


def test_sparse_path_rejects_non_hermitian_total() -> None:
    lattice, basis, terms = _two_key_basis_and_non_hermitian_terms()
    params = _params(len(lattice.nodes))
    options = SpectrumOptions(max_dense_dimension=0, n_eigenvalues=1)
    # non-Hermitian input must be a ValueError (consistency error), never a
    # SpectrumReport(status="failed") produced by letting ARPACK choke on it.
    with pytest.raises(ValueError, match="not Hermitian"):
        build_level0_report(lattice, 2, 1, basis, terms, params, spectrum_options=options)


# ---------------------------------------------------------------------------
# params.J / params.h length checks (declared-provenance sanity check)
# ---------------------------------------------------------------------------


def test_rejects_params_j_with_wrong_length() -> None:
    lattice, report, terms, _ = _build("triangle")
    bad_params = HamiltonianParameters(
        J=(0.1, 0.2), h=(_hermitian_matrix(0, 0, 0),) * 3, t=0.0, g_E=0.0, K=0.0
    )
    with pytest.raises(ValueError):
        build_level0_report(lattice, 2, 1, report, terms, bad_params)


def test_rejects_params_h_with_wrong_length() -> None:
    lattice, report, terms, _ = _build("triangle")
    bad_params = HamiltonianParameters(
        J=(0.1, 0.2, 0.3), h=(_hermitian_matrix(0, 0, 0),) * 2, t=0.0, g_E=0.0, K=0.0
    )
    with pytest.raises(ValueError):
        build_level0_report(lattice, 2, 1, report, terms, bad_params)


# ---------------------------------------------------------------------------
# _eigenpair_diagnostic invariants, exercised directly (white-box): a
# mismatched (eigenvalue, eigenvector) pair, an inconsistent set of term
# matrices, and non-finite inputs must all raise -- not just get caught by
# the test suite's own external comparisons.
# ---------------------------------------------------------------------------


def test_eigenpair_diagnostic_rejects_eigenvalue_not_matching_total_expectation() -> None:
    lattice, report, terms, _ = _build("triangle")
    dense = terms.total.toarray()
    eigenvalues, eigenvectors = np.linalg.eigh(dense)
    psi = eigenvectors[:, 0]
    wrong_eigenvalue = eigenvalues[0] + 10.0  # deliberately not an eigenvalue for psi

    with pytest.raises(ValueError, match="does not match the eigenvalue"):
        _eigenpair_diagnostic(0, wrong_eigenvalue, psi, terms, tolerance=1e-10)


def test_eigenpair_diagnostic_rejects_inconsistent_term_sum() -> None:
    class _InconsistentTerms:
        def __init__(self, matrix2x2_zero: sp.csr_matrix, matrix2x2_nonzero: sp.csr_matrix) -> None:
            self.dot = matrix2x2_zero
            self.hopping = matrix2x2_zero
            self.electric = matrix2x2_zero
            self.magnetic = matrix2x2_zero
            self.total = matrix2x2_nonzero  # deliberately NOT dot+hopping+electric+magnetic

    zero = sp.csr_matrix((2, 2), dtype=np.complex128)
    nonzero_total = sp.csr_matrix(np.array([[5.0, 0], [0, 5.0]], dtype=np.complex128))
    fake_terms = _InconsistentTerms(zero, nonzero_total)
    psi = np.array([1.0 + 0j, 0.0 + 0j])

    with pytest.raises(ValueError, match="does not match"):
        _eigenpair_diagnostic(0, 0.0, psi, fake_terms, tolerance=1e-10)


def test_eigenpair_diagnostic_rejects_non_finite_eigenvalue() -> None:
    lattice, report, terms, _ = _build("triangle")
    psi = np.array([1.0 + 0j] + [0.0 + 0j] * (len(report.keys) - 1))
    with pytest.raises(ValueError, match="not finite"):
        _eigenpair_diagnostic(0, float("nan"), psi, terms, tolerance=1e-10)
