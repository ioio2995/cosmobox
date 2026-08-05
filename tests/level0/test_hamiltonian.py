from __future__ import annotations

import itertools

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.gauge import gauss_vector
from cosmobox.level0.hamiltonian import (
    _assemble_csr,
    _row_for_key,
    build_dot_term,
    build_electric_term,
    build_key_index,
)
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters

HERMITICITY_ATOL = 1e-13


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _random_params(n_nodes: int, seed: int, *, g_E: float = 0.7) -> HamiltonianParameters:
    rng = np.random.default_rng(seed)
    J = tuple(float(rng.uniform(-1, 1)) for _ in range(n_nodes))
    h = tuple(
        _hermitian_matrix(
            float(rng.uniform(-1, 1)),
            float(rng.uniform(-1, 1)),
            complex(rng.uniform(-1, 1), rng.uniform(-1, 1)),
        )
        for _ in range(n_nodes)
    )
    return HamiltonianParameters(J=J, h=h, t=0.0, g_E=g_E, K=0.0)


def _hermiticity_defect(matrix: sp.csr_matrix) -> float:
    difference = (matrix - matrix.conj().T).tocsr()
    difference.eliminate_zeros()
    if difference.nnz == 0:
        return 0.0
    return float(np.max(np.abs(difference.data)))


# ---------------------------------------------------------------------------
# COO -> CSR duplicate summation is locked as an explicit infrastructure test
# ---------------------------------------------------------------------------


def test_assemble_csr_sums_duplicate_row_col_contributions() -> None:
    matrix = _assemble_csr([0, 0, 1], [0, 0, 1], [complex(2, 0), complex(3, 0), complex(5, 0)], dim=2)
    dense = matrix.toarray()
    assert dense[0, 0] == complex(5, 0)
    assert dense[1, 1] == complex(5, 0)
    assert dense[0, 1] == 0
    assert dense[1, 0] == 0


def test_row_for_key_raises_on_missing_key() -> None:
    key_index = {1: 0, 2: 1}
    with pytest.raises(RuntimeError):
        _row_for_key(key_index, np.uint64(99))


# ---------------------------------------------------------------------------
# T1 -- hermiticity, term by term
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "chain3", "ring4"])
def test_t1_hermiticity_dot_and_electric(geometry: str) -> None:
    lattice = build_lattice(geometry)
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=1)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, params)

    assert _hermiticity_defect(dot) < HERMITICITY_ATOL
    assert _hermiticity_defect(electric) < HERMITICITY_ATOL
    assert _hermiticity_defect((dot + electric).tocsr()) < HERMITICITY_ATOL


# ---------------------------------------------------------------------------
# T2 -- closure of the physical subspace
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "chain3", "ring4", "ring5"])
def test_t2_dot_term_never_leaves_the_physical_basis(geometry: str) -> None:
    lattice = build_lattice(geometry)
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=2)

    # Must not raise RuntimeError: every transition stays inside the basis.
    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    assert dot.shape == (len(report.keys), len(report.keys))


# ---------------------------------------------------------------------------
# T3 -- gauge invariance in the small unconstrained (non-physical) space
# ---------------------------------------------------------------------------


def test_t3_dot_and_electric_commute_with_gauss_law_in_the_full_space() -> None:
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

    # Sanity: this unconstrained space contains states with G_i != 0.
    has_non_physical_state = False
    for key in all_keys:
        occupation, flux = decode(lattice, n_flavors, spin, key)
        if any(residual != 0 for residual in gauss_vector(lattice, n_flavors, occupation, flux)):
            has_non_physical_state = True
            break
    assert has_non_physical_state

    params = _random_params(n_nodes, seed=3)
    dot = build_dot_term(lattice, n_flavors, spin, all_keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, all_keys, params)

    for node in lattice.nodes:
        g_values = np.empty(dim, dtype=np.complex128)
        for row, key in enumerate(all_keys):
            occupation, flux = decode(lattice, n_flavors, spin, key)
            g_values[row] = complex(float(gauss_vector(lattice, n_flavors, occupation, flux)[node]))
        g_operator = sp.diags(g_values).tocsr()

        for term in (dot, electric):
            commutator = (term @ g_operator - g_operator @ term).tocsr()
            commutator.eliminate_zeros()
            if commutator.nnz:
                assert np.max(np.abs(commutator.data)) < 1e-10


# ---------------------------------------------------------------------------
# T7 -- total fermion number conservation
# ---------------------------------------------------------------------------


def test_t7_dot_term_transitions_conserve_total_occupation() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=4)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    coo = dot.tocoo()

    for row, col in zip(coo.row, coo.col):
        occ_col, _ = decode(lattice, n_flavors, spin, report.keys[col])
        occ_row, _ = decode(lattice, n_flavors, spin, report.keys[row])
        assert sum(occ_col) == sum(occ_row)


# ---------------------------------------------------------------------------
# T8 -- shape sanity (no leakage possible by construction at this lot)
# ---------------------------------------------------------------------------


def test_t8_matrix_shape_matches_basis_dimension() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=5)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, params)
    dim = len(report.keys)
    assert dot.shape == (dim, dim)
    assert electric.shape == (dim, dim)


# ---------------------------------------------------------------------------
# T9 -- analytic limits
# ---------------------------------------------------------------------------


def test_t9_all_couplings_zero_gives_zero_matrices() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    zero_h = tuple(_hermitian_matrix(0, 0, 0) for _ in lattice.nodes)
    params = HamiltonianParameters(J=(0.0, 0.0, 0.0), h=zero_h, t=0.0, g_E=0.0, K=0.0)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, params)
    assert dot.nnz == 0
    assert electric.nnz == 0


def test_t9_electric_only_diagonal_matches_closed_form() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    zero_h = tuple(_hermitian_matrix(0, 0, 0) for _ in lattice.nodes)
    g_E = 1.3
    params = HamiltonianParameters(J=(0.0, 0.0, 0.0), h=zero_h, t=0.0, g_E=g_E, K=0.0)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, params)
    assert dot.nnz == 0

    dense = electric.toarray()
    for index, key in enumerate(report.keys):
        _, flux = decode(lattice, n_flavors, spin, key)
        expected = 0.5 * g_E * sum(e * e for e in flux)
        assert dense[index, index] == pytest.approx(expected)
        off_diagonal = np.delete(dense[index, :], index)
        assert np.all(off_diagonal == 0)


def test_t9_j_only_spectrum_matches_analytic_diagonal() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    zero_h = tuple(_hermitian_matrix(0, 0, 0) for _ in lattice.nodes)
    J = (0.6, -1.1, 0.4)
    params = HamiltonianParameters(J=J, h=zero_h, t=0.0, g_E=0.0, K=0.0)

    dot = build_dot_term(lattice, n_flavors, spin, report.keys, key_index, params)
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, params)
    assert electric.nnz == 0

    expected_diagonal = []
    for key in report.keys:
        occupation, _ = decode(lattice, n_flavors, spin, key)
        total = 0.0
        for node in lattice.nodes:
            n0, n1 = occupation[node * n_flavors], occupation[node * n_flavors + 1]
            total += J[node] * (n0 - 0.5) * (n1 - 0.5)
        expected_diagonal.append(total)

    numeric_spectrum = sorted(np.linalg.eigvalsh(dot.toarray()))
    analytic_spectrum = sorted(expected_diagonal)
    assert numeric_spectrum == pytest.approx(analytic_spectrum)
