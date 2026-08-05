from __future__ import annotations

import itertools

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.degeneracy import DegeneracyReport, SpectralLevelGroup, analyze_spectral_degeneracies
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.gauge import gauss_vector
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.symmetries import (
    OperatorKind,
    SymmetrySectorDiagnostic,
    _apply_automorphism,
    _edge_image,
    _mode_permutation,
    analyze_symmetry_in_subspaces,
    build_flavor_casimir,
    build_flavor_generators,
    build_reflection_operator,
    build_translation_operator,
)

HERMITICITY_ATOL = 1e-12
COMMUTATOR_ATOL = 1e-10

# H_SENSITIVITY_MATRIX from scripts/level0_reference_campaign/grid.py: eta * this
# is proportional to the single global generator T_n with n = (1, 0, 1)/sqrt(2).
_ALIGNED_H = np.array([[0.5, 0.5], [0.5, -0.5]], dtype=np.complex128)


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _build(geometry: str, n_flavors: int = 2, spin: int = 1):
    lattice = build_lattice(geometry)
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    return lattice, report, key_index


def _params(n_nodes: int, *, h, t: float = 0.7, g_E: float = 0.6, K: float = 0.5, J: float = 0.3) -> HamiltonianParameters:
    return HamiltonianParameters(J=tuple(J for _ in range(n_nodes)), h=h, t=t, g_E=g_E, K=K)


def _uniform_h(n_nodes: int, matrix: np.ndarray) -> tuple[np.ndarray, ...]:
    return tuple(matrix for _ in range(n_nodes))


def _random_nonuniform_h(n_nodes: int, seed: int) -> tuple[np.ndarray, ...]:
    rng = np.random.default_rng(seed)
    return tuple(
        _hermitian_matrix(
            float(rng.uniform(-1, 1)), float(rng.uniform(-1, 1)), complex(rng.uniform(-1, 1), rng.uniform(-1, 1))
        )
        for _ in range(n_nodes)
    )


def _hermiticity_defect(matrix: sp.spmatrix) -> float:
    difference = (matrix - matrix.conj().T).tocsr()
    difference.eliminate_zeros()
    return float(np.max(np.abs(difference.data))) if difference.nnz else 0.0


def _commutator_max_norm(a: sp.spmatrix, b: sp.spmatrix) -> float:
    """Max-abs-element norm of [a, b] -- used only for this file's own pass/fail
    assertions. Deliberately NOT the same norm as
    SymmetrySectorDiagnostic.commutator_defect, which is a global Frobenius
    norm (see analyze_symmetry_in_subspaces); the two are not meant to be
    compared numerically against each other, only each used consistently
    within its own context."""
    commutator = (a @ b - b @ a).tocsr()
    commutator.eliminate_zeros()
    return float(np.max(np.abs(commutator.data))) if commutator.nnz else 0.0


# ---------------------------------------------------------------------------
# build_flavor_generators -- validation
# ---------------------------------------------------------------------------


def test_rejects_n_flavors_other_than_two() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, 3, 1)
    key_index = build_key_index(report.keys)
    with pytest.raises(ValueError, match="n_flavors == 2"):
        build_flavor_generators(lattice, 3, 1, report.keys, key_index)


def test_rejects_a_stale_key_index() -> None:
    lattice, report, key_index = _build("triangle")
    stale_index = build_key_index(tuple(reversed(report.keys)))
    with pytest.raises(ValueError):
        build_flavor_generators(lattice, 2, 1, report.keys, stale_index)


# ---------------------------------------------------------------------------
# T1-style: Hermiticity of T_x, T_y, T_z and T^2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5"])
def test_generators_and_casimir_are_hermitian(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    casimir = build_flavor_casimir(lattice, 2, 1, report.keys, key_index)
    for operator in (tx, ty, tz, casimir):
        assert _hermiticity_defect(operator) < HERMITICITY_ATOL


# ---------------------------------------------------------------------------
# T2-style: never leaves the physical basis (implicit -- no RuntimeError)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5", "chain3"])
def test_generators_never_leave_the_physical_basis(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    dim = len(report.keys)
    for operator in (tx, ty, tz):
        assert operator.shape == (dim, dim)


# ---------------------------------------------------------------------------
# T3-style: commutes with Gauss's law in the full unconstrained space
# ---------------------------------------------------------------------------


def test_generators_commute_with_gauss_law_in_the_full_space() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 2, 1
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)

    all_keys = [
        encode(lattice, n_flavors, spin, occupation, flux)
        for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors)
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges)
    ]
    key_index = build_key_index(all_keys)
    dim = len(all_keys)

    tx, ty, tz = build_flavor_generators(lattice, n_flavors, spin, all_keys, key_index)

    for node in lattice.nodes:
        g_values = np.empty(dim, dtype=np.complex128)
        for row, key in enumerate(all_keys):
            occupation, flux = decode(lattice, n_flavors, spin, key)
            g_values[row] = complex(float(gauss_vector(lattice, n_flavors, occupation, flux)[node]))
        g_operator = sp.diags(g_values).tocsr()

        for operator in (tx, ty, tz):
            assert _commutator_max_norm(operator, g_operator) < 1e-10


# ---------------------------------------------------------------------------
# build_flavor_casimir matches tx@tx + ty@ty + tz@tz
# ---------------------------------------------------------------------------


def test_casimir_matches_manual_sum_of_squares() -> None:
    lattice, report, key_index = _build("ring4")
    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    casimir = build_flavor_casimir(lattice, 2, 1, report.keys, key_index)
    manual = (tx @ tx + ty @ ty + tz @ tz).tocsr()
    difference = (casimir - manual).tocsr()
    difference.eliminate_zeros()
    assert difference.nnz == 0 or np.max(np.abs(difference.data)) < 1e-12


# ---------------------------------------------------------------------------
# SU(2) algebra: [Tx,Ty] = i*Tz (cyclic), [T^2, T_a] = 0
# ---------------------------------------------------------------------------


def test_flavor_generators_satisfy_su2_commutation_relations() -> None:
    lattice, report, key_index = _build("ring4")
    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)

    for a, b, c in ((tx, ty, tz), (ty, tz, tx), (tz, tx, ty)):
        commutator = (a @ b - b @ a).tocsr()
        expected = (1j * c).tocsr()
        difference = (commutator - expected).tocsr()
        difference.eliminate_zeros()
        assert difference.nnz == 0 or np.max(np.abs(difference.data)) < 1e-10


def test_casimir_commutes_with_every_generator() -> None:
    lattice, report, key_index = _build("ring4")
    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    casimir = build_flavor_casimir(lattice, 2, 1, report.keys, key_index)
    for operator in (tx, ty, tz):
        assert _commutator_max_norm(casimir, operator) < 1e-10


# ---------------------------------------------------------------------------
# Flavor-symmetry breaking by h: only the aligned direction survives
# ---------------------------------------------------------------------------


def test_generators_commute_with_h_when_h_is_zero() -> None:
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    zero_h = tuple(_hermitian_matrix(0, 0, 0) for _ in range(n_nodes))
    params = _params(n_nodes, h=zero_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)

    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    for operator in (tx, ty, tz):
        assert _commutator_max_norm(operator, terms.total) < COMMUTATOR_ATOL


def test_only_the_aligned_flavor_direction_commutes_with_uniform_h() -> None:
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    aligned_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=aligned_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)

    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    t_n = ((tx + tz) / np.sqrt(2)).tocsr()

    assert _commutator_max_norm(t_n, terms.total) < COMMUTATOR_ATOL
    # Tz alone is not aligned with (sigma_x + sigma_z)/sqrt(2) -- must not commute.
    assert _commutator_max_norm(tz, terms.total) > 1e-6


def test_casimir_commutes_with_uniform_h_since_it_is_a_single_generator_direction() -> None:
    # A spatially uniform h is proportional to a single global generator
    # T_n; the Casimir commutes with every individual generator (SU(2)
    # algebra identity), hence with any linear combination of them too --
    # including this uniform h-term, for any eta.
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    aligned_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=aligned_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    casimir = build_flavor_casimir(lattice, 2, 1, report.keys, key_index)
    assert _commutator_max_norm(casimir, terms.total) < COMMUTATOR_ATOL


def test_no_generator_commutes_with_a_generic_nonuniform_h() -> None:
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    params = _params(n_nodes, h=_random_nonuniform_h(n_nodes, seed=11))
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)

    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    for operator in (tx, ty, tz):
        assert _commutator_max_norm(operator, terms.total) > 1e-6


# ---------------------------------------------------------------------------
# SymmetrySectorDiagnostic construction invariants
# ---------------------------------------------------------------------------


def _valid_diagnostic_kwargs(**overrides) -> dict:
    kwargs = dict(
        operator_name="T^2",
        operator_kind=OperatorKind.HERMITIAN,
        spectral_group_index=0,
        restricted_eigenvalues=(1.0 + 0j,),
        restriction_defect=0.0,
        restricted_hermiticity_defect=0.0,
        restricted_unitarity_defect=None,
        subspace_orthonormality_defect=0.0,
        commutator_defect=None,
    )
    kwargs.update(overrides)
    return kwargs


def test_diagnostic_accepts_valid_hermitian_construction() -> None:
    SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs())  # must not raise


def test_diagnostic_accepts_valid_unitary_construction() -> None:
    SymmetrySectorDiagnostic(
        **_valid_diagnostic_kwargs(
            operator_kind=OperatorKind.UNITARY,
            restricted_hermiticity_defect=None,
            restricted_unitarity_defect=0.0,
        )
    )


def test_diagnostic_accepts_valid_hermitian_unitary_construction() -> None:
    SymmetrySectorDiagnostic(
        **_valid_diagnostic_kwargs(
            operator_kind=OperatorKind.HERMITIAN_UNITARY,
            restricted_hermiticity_defect=0.0,
            restricted_unitarity_defect=0.0,
        )
    )


def test_diagnostic_rejects_negative_group_index() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(spectral_group_index=-1))


@pytest.mark.parametrize("field", ["restriction_defect", "subspace_orthonormality_defect"])
@pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
def test_diagnostic_rejects_bad_always_present_defects(field: str, bad_value: float) -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(**{field: bad_value}))


def test_diagnostic_rejects_missing_hermiticity_defect_for_hermitian_kind() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(restricted_hermiticity_defect=None))


def test_diagnostic_rejects_present_hermiticity_defect_for_unitary_kind() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(
            **_valid_diagnostic_kwargs(operator_kind=OperatorKind.UNITARY, restricted_unitarity_defect=0.0)
        )  # restricted_hermiticity_defect still set to 0.0 from defaults -- must raise


def test_diagnostic_rejects_missing_unitarity_defect_for_unitary_kind() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(
            **_valid_diagnostic_kwargs(
                operator_kind=OperatorKind.UNITARY,
                restricted_hermiticity_defect=None,
                restricted_unitarity_defect=None,
            )
        )


def test_diagnostic_rejects_present_unitarity_defect_for_hermitian_kind() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(restricted_unitarity_defect=0.0))


@pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
def test_diagnostic_rejects_bad_commutator_defect_when_present(bad_value: float) -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(commutator_defect=bad_value))


def test_diagnostic_rejects_non_finite_restricted_eigenvalue() -> None:
    with pytest.raises(ValueError):
        SymmetrySectorDiagnostic(**_valid_diagnostic_kwargs(restricted_eigenvalues=(complex(float("nan"), 0),)))


# ---------------------------------------------------------------------------
# analyze_symmetry_in_subspaces -- shape validation
# ---------------------------------------------------------------------------


def _small_degeneracy(dimension: int, n_computed: int) -> DegeneracyReport:
    eigenvalues = [float(i) for i in range(n_computed)]
    return analyze_spectral_degeneracies(eigenvalues, dimension=dimension, tolerance=1e-10)


def test_rejects_non_square_operator() -> None:
    operator = sp.csr_matrix((2, 3), dtype=np.complex128)
    eigenvectors = np.eye(2, dtype=np.complex128)
    degeneracy = _small_degeneracy(2, 2)
    with pytest.raises(ValueError, match="square"):
        analyze_symmetry_in_subspaces(operator, "X", OperatorKind.HERMITIAN, eigenvectors, degeneracy)


def test_rejects_eigenvectors_with_wrong_row_count() -> None:
    operator = sp.identity(3, format="csr", dtype=np.complex128)
    eigenvectors = np.eye(2, dtype=np.complex128)
    degeneracy = _small_degeneracy(3, 2)
    with pytest.raises(ValueError, match="eigenvectors"):
        analyze_symmetry_in_subspaces(operator, "X", OperatorKind.HERMITIAN, eigenvectors, degeneracy)


def test_rejects_eigenvectors_column_count_mismatch_with_degeneracy() -> None:
    operator = sp.identity(3, format="csr", dtype=np.complex128)
    eigenvectors = np.eye(3, dtype=np.complex128)[:, :2]  # only 2 columns
    degeneracy = _small_degeneracy(3, 3)  # covers 3 eigenpairs
    with pytest.raises(ValueError, match="eigenvectors"):
        analyze_symmetry_in_subspaces(operator, "X", OperatorKind.HERMITIAN, eigenvectors, degeneracy)


def test_rejects_total_with_wrong_shape() -> None:
    operator = sp.identity(2, format="csr", dtype=np.complex128)
    wrong_total = sp.identity(3, format="csr", dtype=np.complex128)
    eigenvectors = np.eye(2, dtype=np.complex128)
    degeneracy = _small_degeneracy(2, 2)
    with pytest.raises(ValueError, match="total"):
        analyze_symmetry_in_subspaces(
            operator, "X", OperatorKind.HERMITIAN, eigenvectors, degeneracy, total=wrong_total
        )


# ---------------------------------------------------------------------------
# analyze_symmetry_in_subspaces -- white-box correctness on a synthetic operator
# ---------------------------------------------------------------------------


def test_identity_operator_has_zero_defects_in_every_singleton_group() -> None:
    operator = sp.identity(3, format="csr", dtype=np.complex128)
    eigenvectors = np.eye(3, dtype=np.complex128)
    degeneracy = _small_degeneracy(3, 3)  # three singleton groups

    diagnostics = analyze_symmetry_in_subspaces(operator, "I", OperatorKind.HERMITIAN, eigenvectors, degeneracy)

    assert len(diagnostics) == 3
    for index, diagnostic in enumerate(diagnostics):
        assert diagnostic.spectral_group_index == index
        assert diagnostic.restriction_defect == pytest.approx(0.0, abs=1e-12)
        assert diagnostic.subspace_orthonormality_defect == pytest.approx(0.0, abs=1e-12)
        assert diagnostic.restricted_hermiticity_defect == pytest.approx(0.0, abs=1e-12)
        assert diagnostic.restricted_unitarity_defect is None
        assert diagnostic.commutator_defect is None
        assert diagnostic.restricted_eigenvalues == pytest.approx((1.0 + 0j,))


def test_degenerate_group_restricted_eigenvalues_match_full_spectrum() -> None:
    # A 2x2 Hermitian operator with a doubly-degenerate eigenvalue 5.0,
    # diagonalized in a basis that mixes the two degenerate eigenvectors:
    # analyze_symmetry_in_subspaces must recover 5.0 (twice) when restricted
    # to that single 2-dimensional group, and -- since the operator is 5*I,
    # exactly proportional to identity -- ANY 2-dimensional subspace of it
    # is exactly invariant, so restriction_defect must vanish at machine
    # precision even though the columns supplied are not individually
    # eigenvectors of the operator's own natural (standard) basis.
    operator = sp.csr_matrix(np.diag([5.0, 5.0]).astype(np.complex128))
    theta = 0.7
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]], dtype=np.complex128)
    degeneracy = analyze_spectral_degeneracies([5.0, 5.0], dimension=2)  # one true 2-dim group

    diagnostics = analyze_symmetry_in_subspaces(operator, "D", OperatorKind.HERMITIAN, rotation, degeneracy)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.restricted_eigenvalues == pytest.approx((5.0, 5.0))
    assert diagnostic.restriction_defect == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# restriction_defect normalization: relative, not absolute
# ---------------------------------------------------------------------------


def test_restriction_defect_is_scale_invariant() -> None:
    # A 2x2 Hermitian operator with a purely off-diagonal coupling: psi (the
    # first standard basis vector) is not invariant under it, and
    # ||O @ psi|| = 2 > 1, so the normalization denominator is that norm,
    # not the max(1, ...) floor -- scaling O by 1000 must leave the ratio
    # exactly unchanged.
    operator = sp.csr_matrix(np.array([[0.0, 2.0], [2.0, 0.0]], dtype=np.complex128))
    eigenvectors = np.array([[1.0], [0.0]], dtype=np.complex128)
    degeneracy = _small_degeneracy(2, 1)

    small = analyze_symmetry_in_subspaces(operator, "O", OperatorKind.HERMITIAN, eigenvectors, degeneracy)
    scaled_operator = (1000.0 * operator).tocsr()
    large = analyze_symmetry_in_subspaces(
        scaled_operator, "1000*O", OperatorKind.HERMITIAN, eigenvectors, degeneracy
    )

    assert small[0].restriction_defect == pytest.approx(1.0)
    assert small[0].restriction_defect == pytest.approx(large[0].restriction_defect, rel=1e-10)


def test_restriction_defect_denominator_stays_one_below_unit_norm() -> None:
    # ||O @ psi|| = 0.3 < 1, so the max(1, ...) floor keeps the denominator
    # at exactly 1 -- restriction_defect must equal the raw (unnormalized)
    # residual norm in this regime, not a rescaled version of it.
    operator = sp.csr_matrix(np.array([[0.0, 0.3], [0.3, 0.0]], dtype=np.complex128))
    eigenvectors = np.array([[1.0], [0.0]], dtype=np.complex128)
    degeneracy = _small_degeneracy(2, 1)

    diagnostics = analyze_symmetry_in_subspaces(operator, "O", OperatorKind.HERMITIAN, eigenvectors, degeneracy)
    assert diagnostics[0].restriction_defect == pytest.approx(0.3, abs=1e-12)


def test_commutator_defect_is_shared_across_all_groups() -> None:
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    aligned_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=aligned_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    dimension = len(report.keys)

    eigenvalues, eigenvectors = np.linalg.eigh(terms.total.toarray())
    degeneracy = analyze_spectral_degeneracies(list(eigenvalues), dimension=dimension)

    tx, ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)
    t_n = ((tx + tz) / np.sqrt(2)).tocsr()

    diagnostics = analyze_symmetry_in_subspaces(
        t_n, "T_n", OperatorKind.HERMITIAN, eigenvectors, degeneracy, total=terms.total
    )
    assert len(diagnostics) == len(degeneracy.groups)
    commutator_values = {d.commutator_defect for d in diagnostics}
    assert len(commutator_values) == 1  # identical across every group
    assert next(iter(commutator_values)) < COMMUTATOR_ATOL
    for diagnostic in diagnostics:
        assert diagnostic.restriction_defect < 1e-8  # T_n preserves every H-eigenspace exactly


def test_non_commuting_operator_has_nonzero_global_commutator_defect() -> None:
    lattice, report, key_index = _build("triangle")
    n_nodes = len(lattice.nodes)
    aligned_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=aligned_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    dimension = len(report.keys)

    eigenvalues, eigenvectors = np.linalg.eigh(terms.total.toarray())
    degeneracy = analyze_spectral_degeneracies(list(eigenvalues), dimension=dimension)

    _tx, _ty, tz = build_flavor_generators(lattice, 2, 1, report.keys, key_index)

    diagnostics = analyze_symmetry_in_subspaces(
        tz, "T_z", OperatorKind.HERMITIAN, eigenvectors, degeneracy, total=terms.total
    )
    assert diagnostics[0].commutator_defect > 1e-6


# ===========================================================================
# Lot 6B.2: geometric automorphisms (translation, reflection)
# ===========================================================================


def _frobenius_diff(a: sp.spmatrix, b) -> float:
    diff = (a - b).tocsr()
    diff.eliminate_zeros()
    return float(np.sqrt(np.sum(np.abs(diff.data) ** 2))) if diff.nnz else 0.0


# ---------------------------------------------------------------------------
# Rejects a site_permutation that is not a lattice automorphism
# ---------------------------------------------------------------------------


def test_translation_rejects_chain3_which_has_no_wraparound_edge() -> None:
    lattice, report, key_index = _build("chain3")
    with pytest.raises(ValueError, match="automorphism"):
        build_translation_operator(lattice, 2, 1, report.keys, key_index)


def test_translation_rejects_disk7_hub_and_spoke_structure() -> None:
    # No basis build here: the shift's edge-image mismatch is detected
    # before any key is touched, so an empty (but self-consistent) key set
    # is enough -- building disk7's ~450k-state basis just for this
    # negative path is exactly the cost this project avoids paying in the
    # unit suite.
    lattice = build_lattice("disk7")
    with pytest.raises(ValueError, match="automorphism"):
        build_translation_operator(lattice, 2, 1, (), {})


# ---------------------------------------------------------------------------
# external_charges invariance guardrail
# ---------------------------------------------------------------------------


def test_translation_rejects_noninvariant_external_charges() -> None:
    lattice, report, key_index = _build("ring4")
    with pytest.raises(ValueError, match="external_charges"):
        build_translation_operator(lattice, 2, 1, report.keys, key_index, external_charges=(1, 0, 0, 0))


def test_translation_accepts_default_none_external_charges() -> None:
    lattice, report, key_index = _build("ring4")
    build_translation_operator(lattice, 2, 1, report.keys, key_index)  # must not raise


def test_reflection_accepts_symmetric_but_translation_rejects_asymmetric_charges() -> None:
    lattice, report, key_index = _build("triangle")
    # Invariant under reflection (node 0 fixed, nodes 1 and 2 swapped) but
    # not under a cyclic shift.
    charges = (5, 2, 2)
    build_reflection_operator(lattice, 2, 1, report.keys, key_index, external_charges=charges)  # must not raise
    with pytest.raises(ValueError, match="external_charges"):
        build_translation_operator(lattice, 2, 1, report.keys, key_index, external_charges=charges)


# ---------------------------------------------------------------------------
# Fermion sign: hand-derived inversion-count example (triangle, translation)
# ---------------------------------------------------------------------------


def test_fermion_sign_matches_hand_derived_inversion_count() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    site_permutation = [(node + 1) % n_nodes for node in range(n_nodes)]
    mode_permutation = _mode_permutation(n_nodes, n_flavors, site_permutation)
    edge_image = _edge_image(lattice, site_permutation)
    # mode_permutation = [2, 3, 4, 5, 0, 1] for this site_permutation.

    # Occupied modes {0, 2} (node0-flavor0, node1-flavor0): sorted [0, 2] maps
    # to [mode_permutation[0], mode_permutation[2]] = [2, 4] -- no inversion,
    # so the sign is +1.
    occupation_a = [0] * (n_nodes * n_flavors)
    occupation_a[0] = 1
    occupation_a[2] = 1
    flux = [0] * n_edges
    key_a = encode(lattice, n_flavors, spin, occupation_a, flux)
    result_a = _apply_automorphism(lattice, n_flavors, spin, key_a, mode_permutation, edge_image)
    assert result_a.amplitude == pytest.approx(1.0 + 0j)

    # Occupied modes {0, 4} (node0-flavor0, node2-flavor0): sorted [0, 4] maps
    # to [mode_permutation[0], mode_permutation[4]] = [2, 0] -- one inversion
    # (2 > 0): c^dagger_2 c^dagger_0 |0> = -c^dagger_0 c^dagger_2 |0>, sign -1.
    # The resulting occupied set {2, 0} == {0, 2} is exactly key_a's occupation.
    occupation_b = [0] * (n_nodes * n_flavors)
    occupation_b[0] = 1
    occupation_b[4] = 1
    key_b = encode(lattice, n_flavors, spin, occupation_b, flux)
    result_b = _apply_automorphism(lattice, n_flavors, spin, key_b, mode_permutation, edge_image)
    assert result_b.amplitude == pytest.approx(-1.0 + 0j)
    assert int(result_b.key) == int(key_a)


# ---------------------------------------------------------------------------
# Gauss covariance in the full unconstrained space
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["translation", "reflection"])
def test_automorphism_covaries_gauss_law_in_the_full_space(kind: str) -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)

    if kind == "translation":
        site_permutation = [(node + 1) % n_nodes for node in range(n_nodes)]
    else:
        site_permutation = [(n_nodes - node) % n_nodes for node in range(n_nodes)]
    mode_permutation = _mode_permutation(n_nodes, n_flavors, site_permutation)
    edge_image = _edge_image(lattice, site_permutation)

    all_keys = [
        encode(lattice, n_flavors, spin, occupation, flux)
        for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors)
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges)
    ]

    for key in all_keys:
        occupation, flux = decode(lattice, n_flavors, spin, key)
        g_original = gauss_vector(lattice, n_flavors, occupation, flux)

        result = _apply_automorphism(lattice, n_flavors, spin, key, mode_permutation, edge_image)
        new_occupation, new_flux = decode(lattice, n_flavors, spin, result.key)
        g_transformed = gauss_vector(lattice, n_flavors, new_occupation, new_flux)

        for node in range(n_nodes):
            assert g_transformed[site_permutation[node]] == g_original[node]


# ---------------------------------------------------------------------------
# Algebraic relations: T^N = I, R^2 = I, unitarity, R T R = T^-1 (dihedral)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5", "ring6"])
def test_translation_to_the_n_is_identity_and_unitary(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    n_nodes = len(lattice.nodes)
    dim = len(report.keys)
    identity = sp.identity(dim, format="csr", dtype=np.complex128)

    T = build_translation_operator(lattice, 2, 1, report.keys, key_index)
    power = identity
    for _ in range(n_nodes):
        power = (power @ T).tocsr()
    assert _frobenius_diff(power, identity) < 1e-10
    assert _frobenius_diff(T.conj().T @ T, identity) < 1e-10


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5", "ring6"])
def test_reflection_is_an_involution_hermitian_and_unitary(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    dim = len(report.keys)
    identity = sp.identity(dim, format="csr", dtype=np.complex128)

    R = build_reflection_operator(lattice, 2, 1, report.keys, key_index)
    assert _frobenius_diff(R @ R, identity) < 1e-10
    assert _frobenius_diff(R, R.conj().T) < 1e-12
    assert _frobenius_diff(R.conj().T @ R, identity) < 1e-10


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5", "ring6"])
def test_dihedral_relation_r_t_r_equals_t_inverse(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    T = build_translation_operator(lattice, 2, 1, report.keys, key_index)
    R = build_reflection_operator(lattice, 2, 1, report.keys, key_index)
    lhs = (R @ T @ R).tocsr()
    rhs = T.conj().T  # T unitary: T^-1 == T^dagger
    assert _frobenius_diff(lhs, rhs) < 1e-10


# ---------------------------------------------------------------------------
# Commutation with H at spatially uniform parameters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5"])
def test_translation_and_reflection_commute_with_uniform_h(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    n_nodes = len(lattice.nodes)
    uniform_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=uniform_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)

    T = build_translation_operator(lattice, 2, 1, report.keys, key_index)
    R = build_reflection_operator(lattice, 2, 1, report.keys, key_index)

    for operator in (T, R):
        assert _commutator_max_norm(operator, terms.total) < COMMUTATOR_ATOL


# ---------------------------------------------------------------------------
# analyze_symmetry_in_subspaces integration: UNITARY (T), HERMITIAN_UNITARY (R)
# ---------------------------------------------------------------------------


def test_translation_restricted_diagnostics_are_unitary_and_commute_with_h() -> None:
    lattice, report, key_index = _build("ring4")
    n_nodes = len(lattice.nodes)
    uniform_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=uniform_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    dimension = len(report.keys)

    eigenvalues, eigenvectors = np.linalg.eigh(terms.total.toarray())
    degeneracy = analyze_spectral_degeneracies(list(eigenvalues), dimension=dimension)

    T = build_translation_operator(lattice, 2, 1, report.keys, key_index)
    diagnostics = analyze_symmetry_in_subspaces(
        T, "T", OperatorKind.UNITARY, eigenvectors, degeneracy, total=terms.total
    )
    for diagnostic in diagnostics:
        assert diagnostic.restricted_hermiticity_defect is None
        assert diagnostic.restricted_unitarity_defect < 1e-8
        assert diagnostic.commutator_defect < COMMUTATOR_ATOL
        assert diagnostic.restriction_defect < 1e-8
        for eigenvalue in diagnostic.restricted_eigenvalues:
            assert abs(eigenvalue) == pytest.approx(1.0, abs=1e-6)


def test_reflection_restricted_diagnostics_are_hermitian_and_unitary() -> None:
    lattice, report, key_index = _build("ring4")
    n_nodes = len(lattice.nodes)
    uniform_h = _uniform_h(n_nodes, 0.3 * _ALIGNED_H)
    params = _params(n_nodes, h=uniform_h)
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    dimension = len(report.keys)

    eigenvalues, eigenvectors = np.linalg.eigh(terms.total.toarray())
    degeneracy = analyze_spectral_degeneracies(list(eigenvalues), dimension=dimension)

    R = build_reflection_operator(lattice, 2, 1, report.keys, key_index)
    diagnostics = analyze_symmetry_in_subspaces(
        R, "R", OperatorKind.HERMITIAN_UNITARY, eigenvectors, degeneracy, total=terms.total
    )
    for diagnostic in diagnostics:
        assert diagnostic.restricted_hermiticity_defect < 1e-8
        assert diagnostic.restricted_unitarity_defect < 1e-8
        assert diagnostic.commutator_defect < COMMUTATOR_ATOL
        assert diagnostic.restriction_defect < 1e-8
        for eigenvalue in diagnostic.restricted_eigenvalues:
            assert abs(eigenvalue.imag) < 1e-6  # R Hermitian -> real eigenvalues
            assert abs(abs(eigenvalue.real) - 1.0) < 1e-6  # R^2 = I -> eigenvalues +-1


# ---------------------------------------------------------------------------
# No flux-conjugation operator is exposed
# ---------------------------------------------------------------------------


def test_no_flux_conjugation_operator_is_exported() -> None:
    import cosmobox.level0.symmetries as symmetries_module
    import cosmobox.level0 as level0_module

    assert not hasattr(symmetries_module, "build_flux_conjugation_operator")
    assert not hasattr(level0_module, "build_flux_conjugation_operator")
