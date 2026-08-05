from __future__ import annotations

import itertools

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.gauge import gauss_vector, is_physical
from cosmobox.level0.hamiltonian import (
    _assemble_csr,
    _row_for_key,
    build_dot_term,
    build_electric_term,
    build_hopping_term,
    build_key_index,
    validate_key_index,
)
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.operators import annihilate, create, jordan_wigner_sign, transport
from cosmobox.level0.params import HamiltonianParameters

HERMITICITY_ATOL = 1e-13


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _random_params(n_nodes: int, seed: int, *, g_E: float = 0.7, t: float = 0.0) -> HamiltonianParameters:
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
    return HamiltonianParameters(J=J, h=h, t=t, g_E=g_E, K=0.0)


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
# keys <-> key_index invariant: duplicate keys, and any index that is not
# exactly the row/col position of `keys`, must be rejected explicitly.
# ---------------------------------------------------------------------------


def test_build_key_index_rejects_duplicate_key() -> None:
    keys = [np.uint64(1), np.uint64(2), np.uint64(1)]
    with pytest.raises(ValueError):
        build_key_index(keys)


def test_build_key_index_matches_position_for_distinct_keys() -> None:
    keys = [np.uint64(5), np.uint64(3), np.uint64(9)]
    key_index = build_key_index(keys)
    assert key_index == {5: 0, 3: 1, 9: 2}


def test_validate_key_index_accepts_a_correct_index() -> None:
    keys = [np.uint64(5), np.uint64(3), np.uint64(9)]
    key_index = build_key_index(keys)
    validate_key_index(keys, key_index)  # must not raise


def test_validate_key_index_rejects_index_built_from_a_different_order() -> None:
    keys = [np.uint64(5), np.uint64(3), np.uint64(9)]
    shuffled_index = build_key_index([np.uint64(3), np.uint64(5), np.uint64(9)])
    with pytest.raises(ValueError):
        validate_key_index(keys, shuffled_index)


def test_validate_key_index_rejects_missing_entry() -> None:
    keys = [np.uint64(5), np.uint64(3), np.uint64(9)]
    incomplete_index = {5: 0, 3: 1}
    with pytest.raises(ValueError):
        validate_key_index(keys, incomplete_index)


def test_validate_key_index_rejects_out_of_range_row() -> None:
    keys = [np.uint64(5), np.uint64(3)]
    out_of_range_index = {5: 0, 3: 7}
    with pytest.raises(ValueError):
        validate_key_index(keys, out_of_range_index)


def test_validate_key_index_rejects_duplicated_row() -> None:
    keys = [np.uint64(5), np.uint64(3)]
    duplicated_row_index = {5: 0, 3: 0}
    with pytest.raises(ValueError):
        validate_key_index(keys, duplicated_row_index)


def test_build_dot_term_rejects_a_stale_key_index() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    stale_index = {int(key): 0 for key in report.keys}  # every key mapped to row 0
    params = _random_params(len(lattice.nodes), seed=6)
    with pytest.raises(ValueError):
        build_dot_term(lattice, n_flavors, spin, report.keys, stale_index, params)


def test_build_electric_term_rejects_a_stale_key_index() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    stale_index = {int(key): 0 for key in report.keys}
    params = _random_params(len(lattice.nodes), seed=7)
    with pytest.raises(ValueError):
        build_electric_term(lattice, n_flavors, spin, report.keys, stale_index, params)


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
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, key_index, params)

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
    electric = build_electric_term(lattice, n_flavors, spin, all_keys, key_index, params)

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
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, key_index, params)
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
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, key_index, params)
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
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, key_index, params)
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
    electric = build_electric_term(lattice, n_flavors, spin, report.keys, key_index, params)
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


# ===========================================================================
# H_hop (lot 4B)
# ===========================================================================


def _chain3_full_unconstrained_keys(n_flavors: int, spin: int) -> list[np.uint64]:
    lattice = build_lattice("chain3")
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    return [
        encode(lattice, n_flavors, spin, occupation, flux)
        for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors)
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges)
    ]


# ---------------------------------------------------------------------------
# T1 -- hermiticity, chains (acyclic) and cycles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["chain3", "triangle", "ring4"])
def test_t1_hopping_hermiticity(geometry: str) -> None:
    lattice = build_lattice(geometry)
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=10, t=1.7)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    assert _hermiticity_defect(hopping) < HERMITICITY_ATOL


# ---------------------------------------------------------------------------
# T2 -- closure: positive (real physical basis) and negative (deliberately
# incomplete basis must raise RuntimeError, not drop the transition)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "chain3", "ring4", "ring5"])
def test_t2_hopping_never_leaves_the_physical_basis(geometry: str) -> None:
    lattice = build_lattice(geometry)
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=11, t=0.9)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    assert hopping.shape == (len(report.keys), len(report.keys))


def test_t2_hopping_raises_on_a_deliberately_incomplete_basis() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    all_keys = _chain3_full_unconstrained_keys(n_flavors, spin)

    source_key = encode(lattice, n_flavors, spin, (0, 1, 0), (0, -1))
    target_key = encode(lattice, n_flavors, spin, (1, 0, 0), (1, -1))
    assert source_key in all_keys
    assert target_key in all_keys

    incomplete_keys = [key for key in all_keys if int(key) != int(target_key)]
    key_index = build_key_index(incomplete_keys)  # self-consistent, just missing target_key
    params = HamiltonianParameters(
        J=(0.0, 0.0, 0.0),
        h=(_hermitian_matrix(0, 0, 0),) * 3,
        t=1.0,
        g_E=0.0,
        K=0.0,
    )

    with pytest.raises(RuntimeError):
        build_hopping_term(lattice, n_flavors, spin, incomplete_keys, key_index, params)


# ---------------------------------------------------------------------------
# T3 -- gauge invariance in the full unconstrained space (the decisive test:
# a sign error between the fermionic move and the flux change would show up
# here as a nonzero commutator)
# ---------------------------------------------------------------------------


def test_t3_hopping_commutes_with_gauss_law_in_the_full_space() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    all_keys = _chain3_full_unconstrained_keys(n_flavors, spin)
    key_index = build_key_index(all_keys)
    dim = len(all_keys)

    has_non_physical_state = False
    for key in all_keys:
        occupation, flux = decode(lattice, n_flavors, spin, key)
        if any(residual != 0 for residual in gauss_vector(lattice, n_flavors, occupation, flux)):
            has_non_physical_state = True
            break
    assert has_non_physical_state

    params = _random_params(len(lattice.nodes), seed=12, t=1.1)
    hopping = build_hopping_term(lattice, n_flavors, spin, all_keys, key_index, params)

    for node in lattice.nodes:
        g_values = np.empty(dim, dtype=np.complex128)
        for row, key in enumerate(all_keys):
            occupation, flux = decode(lattice, n_flavors, spin, key)
            g_values[row] = complex(float(gauss_vector(lattice, n_flavors, occupation, flux)[node]))
        g_operator = sp.diags(g_values).tocsr()

        commutator = (hopping @ g_operator - g_operator @ hopping).tocsr()
        commutator.eliminate_zeros()
        if commutator.nnz:
            assert np.max(np.abs(commutator.data)) < 1e-10


# ---------------------------------------------------------------------------
# T7 -- total fermion number conservation
# ---------------------------------------------------------------------------


def test_t7_hopping_transitions_conserve_total_occupation() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=13, t=1.0)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    coo = hopping.tocoo()
    for row, col in zip(coo.row, coo.col):
        occ_col, _ = decode(lattice, n_flavors, spin, report.keys[col])
        occ_row, _ = decode(lattice, n_flavors, spin, report.keys[row])
        assert sum(occ_col) == sum(occ_row)


# ---------------------------------------------------------------------------
# T8 -- every nonzero transition independently: canonical, physical, indexed
# ---------------------------------------------------------------------------


def test_t8_every_hopping_transition_is_canonical_physical_and_indexed() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=14, t=1.0)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    coo = hopping.tocoo()
    assert coo.nnz > 0

    for row in coo.row:
        result_key = report.keys[row]
        decode(lattice, n_flavors, spin, result_key)  # must not raise
        assert is_physical(lattice, n_flavors, spin, result_key) is True
        assert int(result_key) in key_index


# ---------------------------------------------------------------------------
# t = 0 and no artificial diagonal contribution
# ---------------------------------------------------------------------------


def test_hopping_with_t_zero_gives_the_zero_matrix() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=15, t=0.0)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    assert hopping.nnz == 0


def test_hopping_never_contributes_to_the_diagonal() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=16, t=1.0)

    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    coo = hopping.tocoo()
    assert np.all(coo.row != coo.col)


# ---------------------------------------------------------------------------
# T9 -- analytic limit, a single isolated transition on chain3
# ---------------------------------------------------------------------------


def test_t9_single_isolated_hopping_transition_matches_analytic_amplitude() -> None:
    lattice = build_lattice("chain3")  # edges: 0=(0,1), 1=(1,2)
    n_flavors, spin = 1, 1
    t = 1.3

    # node0 empty, node1 occupied, node2 empty:
    #  - edge0 direct  (annihilate node1, transport edge0, create node0): allowed.
    #  - edge0 conjugate (annihilate node0): blocked, node0 empty.
    #  - edge1 direct  (annihilate node2): blocked, node2 empty.
    #  - edge1 conjugate (annihilate node1, transport_dagger edge1 at m=-S): blocked by
    #    flux truncation, not by occupation.
    occupation = (0, 1, 0)
    flux = (0, -spin)
    key = encode(lattice, n_flavors, spin, occupation, flux)

    params = HamiltonianParameters(
        J=(0.0, 0.0, 0.0), h=(_hermitian_matrix(0, 0, 0),) * 3, t=t, g_E=0.0, K=0.0
    )
    report_keys = _chain3_full_unconstrained_keys(n_flavors, spin)
    key_index = build_key_index(report_keys)

    hopping = build_hopping_term(lattice, n_flavors, spin, report_keys, key_index, params)
    col = key_index[int(key)]
    column = hopping.getcol(col).tocoo()
    assert column.nnz == 1, "exactly one (row, col) pair must be produced from this key"

    # Recompute the amplitude independently, from the explicit operator composition.
    a_ann = jordan_wigner_sign(lattice, n_flavors, spin, key, node=1, flavor=0)
    annihilated = annihilate(lattice, n_flavors, spin, key, node=1, flavor=0)
    assert annihilated is not None
    assert annihilated.amplitude == complex(a_ann, 0)

    transported = transport(lattice, n_flavors, spin, annihilated.key, edge_index=0)
    assert transported is not None
    m = flux[0]
    a_u = ((spin * (spin + 1) - m * (m + 1)) / (spin * (spin + 1))) ** 0.5
    assert transported.amplitude == pytest.approx(a_u)

    a_cre = jordan_wigner_sign(lattice, n_flavors, spin, annihilated.key, node=0, flavor=0)
    created = create(lattice, n_flavors, spin, transported.key, node=0, flavor=0)
    assert created is not None
    assert created.amplitude == complex(a_cre, 0)

    expected_amplitude = -t * a_ann * a_u * a_cre
    target_row = key_index[int(created.key)]

    assert column.row[0] == target_row
    assert column.data[0] == pytest.approx(expected_amplitude)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_hopping_rejects_non_positive_n_flavors_even_with_an_empty_basis() -> None:
    lattice = build_lattice("triangle")
    params = HamiltonianParameters(
        J=(0.0, 0.0, 0.0), h=(_hermitian_matrix(0, 0, 0),) * 3, t=1.0, g_E=0.0, K=0.0
    )
    with pytest.raises(ValueError):
        build_hopping_term(lattice, 0, 1, [], {}, params)


def test_hopping_accepts_an_empty_basis_and_returns_a_0x0_matrix() -> None:
    lattice = build_lattice("triangle")
    params = HamiltonianParameters(
        J=(0.0, 0.0, 0.0), h=(_hermitian_matrix(0, 0, 0),) * 3, t=1.0, g_E=0.0, K=0.0
    )
    hopping = build_hopping_term(lattice, 1, 1, [], {}, params)
    assert hopping.shape == (0, 0)


def test_hopping_rejects_a_stale_key_index() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    stale_index = {int(key): 0 for key in report.keys}
    params = _random_params(len(lattice.nodes), seed=17, t=1.0)
    with pytest.raises(ValueError):
        build_hopping_term(lattice, n_flavors, spin, report.keys, stale_index, params)


def test_hopping_works_for_multiple_flavors() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    key_index = build_key_index(report.keys)
    params = _random_params(len(lattice.nodes), seed=18, t=1.0)
    hopping = build_hopping_term(lattice, n_flavors, spin, report.keys, key_index, params)
    assert _hermiticity_defect(hopping) < HERMITICITY_ATOL
