from __future__ import annotations

import itertools

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.gauge import gauss_vector
from cosmobox.level0.hamiltonian import build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.operators import annihilate, create
from cosmobox.level1.matter import apply_dressed_matter, build_dressed_matter_matrix
from cosmobox.level1.paths import invert_path, make_oriented_path, minimal_paths

N_FLAVORS = 2
SPIN = 1
GAUSS_TOLERANCE = 1e-10

# ---------------------------------------------------------------------------
# Shared helpers (mirror the T3-style pattern already used across Level0's
# own test_hamiltonian.py / test_symmetries.py for Gauss-commutation checks)
# ---------------------------------------------------------------------------


def _full_unconstrained_keys(lattice, n_flavors, spin):
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    return [
        encode(lattice, n_flavors, spin, occupation, flux)
        for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors)
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges)
    ]


def _gauss_operator(lattice, n_flavors, spin, all_keys, node):
    g_values = np.empty(len(all_keys), dtype=np.complex128)
    for row, key in enumerate(all_keys):
        occupation, flux = decode(lattice, n_flavors, spin, key)
        g_values[row] = complex(float(gauss_vector(lattice, n_flavors, occupation, flux)[node]))
    return sp.diags(g_values).tocsr()


def _assert_commutes_with_gauss_law(lattice, path, alpha, beta) -> None:
    all_keys = _full_unconstrained_keys(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(all_keys)
    operator = build_dressed_matter_matrix(lattice, N_FLAVORS, SPIN, all_keys, key_index, path, alpha, beta)
    for node in lattice.nodes:
        g_operator = _gauss_operator(lattice, N_FLAVORS, SPIN, all_keys, node)
        commutator = (operator @ g_operator - g_operator @ operator).tocsr()
        commutator.eliminate_zeros()
        if commutator.nnz:
            assert np.max(np.abs(commutator.data)) < GAUSS_TOLERANCE


# ---------------------------------------------------------------------------
# V01a-d -- gauge (Gauss-law) invariance, four distinct required cases
# ---------------------------------------------------------------------------


def test_v01a_direct_path_commutes_with_gauss_law() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (0, 1))
    _assert_commutes_with_gauss_law(lattice, path, alpha=0, beta=0)


def test_v01b_reversed_step_path_commutes_with_gauss_law() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (1, 0))
    _assert_commutes_with_gauss_law(lattice, path, alpha=0, beta=0)


def test_v01c_zero_length_path_commutes_with_gauss_law() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (0,))
    _assert_commutes_with_gauss_law(lattice, path, alpha=0, beta=0)


def test_v01d_off_diagonal_flavor_commutes_with_gauss_law() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (0, 1))
    _assert_commutes_with_gauss_law(lattice, path, alpha=0, beta=1)


# ---------------------------------------------------------------------------
# V02 -- reversed edge, hand-verified amplitude at the dressed-operator level
# (test_transporters.py already covers this at the transporter level alone)
# ---------------------------------------------------------------------------


def test_v02_reversed_step_dressed_operator_hand_verified_amplitude() -> None:
    lattice = build_lattice("triangle")
    occupation = [0, 0, 0, 0, 0, 0]
    occupation[0] = 1  # node 0, flavor 0 occupied; mode index = 0*2+0 = 0
    key = encode(lattice, N_FLAVORS, SPIN, tuple(occupation), (0, 0, 0))
    path = make_oriented_path(lattice, (1, 0))  # single reversed step on edge 0

    # O_{1,0}^{0,0}[P]: annihilate flavor 0 at node 0 (destination), apply
    # U_0^dagger (m: 0 -> -1, amplitude sqrt(S(S+1)-0*(-1))/sqrt(S(S+1))=1
    # for S=1), create flavor 0 at node 1 (source). No occupied mode below
    # either elementary action's mode index here, so both JW signs are +1.
    result = apply_dressed_matter(lattice, N_FLAVORS, SPIN, key, path, alpha=0, beta=0)
    assert result is not None
    assert result.amplitude == pytest.approx(1.0 + 0j)
    new_occupation, new_flux = decode(lattice, N_FLAVORS, SPIN, result.key)
    assert new_occupation[0] == 0  # node 0 flavor 0 annihilated
    assert new_occupation[2] == 1  # node 1 flavor 0 (mode index 1*2+0=2) created
    assert new_flux == (-1, 0, 0)


# ---------------------------------------------------------------------------
# V03 -- adjoint relation, compared on assembled matrices (not path metadata)
# ---------------------------------------------------------------------------


def test_v03_adjoint_relation_triangle_direct_path() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    path = make_oriented_path(lattice, (0, 1))
    alpha, beta = 0, 1

    forward = build_dressed_matter_matrix(lattice, N_FLAVORS, SPIN, report.keys, key_index, path, alpha, beta)
    backward = build_dressed_matter_matrix(
        lattice, N_FLAVORS, SPIN, report.keys, key_index, invert_path(path), beta, alpha
    )
    diff = (forward.conj().T - backward).tocsr()
    diff.eliminate_zeros()
    assert diff.nnz == 0 or np.max(np.abs(diff.data)) < 1e-12


def test_v03_adjoint_relation_ring4_two_step_path() -> None:
    lattice = build_lattice("ring4")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    path = make_oriented_path(lattice, (0, 1, 2))
    alpha, beta = 1, 0

    forward = build_dressed_matter_matrix(lattice, N_FLAVORS, SPIN, report.keys, key_index, path, alpha, beta)
    backward = build_dressed_matter_matrix(
        lattice, N_FLAVORS, SPIN, report.keys, key_index, invert_path(path), beta, alpha
    )
    diff = (forward.conj().T - backward).tocsr()
    diff.eliminate_zeros()
    assert diff.nnz == 0 or np.max(np.abs(diff.data)) < 1e-12


# ---------------------------------------------------------------------------
# V04 -- zero-length path reduces to the local bilinear, checked against an
# independently built reference (annihilate/create only, no level1 code)
# ---------------------------------------------------------------------------


def test_v04_zero_length_path_matches_independent_local_bilinear() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    zero_path = make_oriented_path(lattice, (0,))
    alpha, beta = 0, 1

    matrix = build_dressed_matter_matrix(lattice, N_FLAVORS, SPIN, report.keys, key_index, zero_path, alpha, beta)

    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []
    for col, key in enumerate(report.keys):
        intermediate = annihilate(lattice, N_FLAVORS, SPIN, key, 0, beta)
        if intermediate is None:
            continue
        result = create(lattice, N_FLAVORS, SPIN, intermediate.key, 0, alpha)
        if result is None:
            continue
        rows.append(key_index[int(result.key)])
        cols.append(col)
        values.append(intermediate.amplitude * result.amplitude)
    dim = len(report.keys)
    reference = sp.coo_matrix(
        (np.asarray(values, dtype=np.complex128), (rows, cols)), shape=(dim, dim)
    ).tocsr()

    diff = (matrix - reference).tocsr()
    diff.eliminate_zeros()
    assert diff.nnz == 0


# ---------------------------------------------------------------------------
# V05 -- basis closure: exhaustive on triangle, deterministic sampling on
# ring4/ring5, and a dedicated negative test with a deliberately incomplete
# key_index.
# ---------------------------------------------------------------------------


def test_v05_exhaustive_closure_on_triangle_physical_basis() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)

    for source in lattice.nodes:
        for destination in lattice.nodes:
            for path in minimal_paths(lattice, source, destination):
                for alpha in range(N_FLAVORS):
                    for beta in range(N_FLAVORS):
                        # Must not raise: every nonzero transition from
                        # every key in the full physical basis lands back
                        # inside it, for every path/flavor combination.
                        build_dressed_matter_matrix(
                            lattice, N_FLAVORS, SPIN, report.keys, key_index, path, alpha, beta
                        )


def test_v05_deterministic_sampling_closure_on_ring4() -> None:
    lattice = build_lattice("ring4")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    sampled_keys = report.keys[::11]
    assert len(sampled_keys) >= 5

    paths = list(minimal_paths(lattice, 0, 1)) + list(minimal_paths(lattice, 0, 2))
    assert len(paths) == 3  # one adjacent + two antipodal minimal paths
    for path in paths:
        for alpha in range(N_FLAVORS):
            for beta in range(N_FLAVORS):
                for key in sampled_keys:
                    # Must not raise. key_index stays the FULL basis index
                    # (targets are checked against the whole physical
                    # basis); only the sampled *source* keys are reduced.
                    apply_dressed_matter(lattice, N_FLAVORS, SPIN, key, path, alpha, beta, key_index=key_index)


def test_v05_deterministic_sampling_closure_on_ring5() -> None:
    lattice = build_lattice("ring5")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    sampled_keys = report.keys[::23]
    assert len(sampled_keys) >= 5

    paths = list(minimal_paths(lattice, 0, 1)) + list(minimal_paths(lattice, 0, 2))
    for path in paths:
        for alpha in range(N_FLAVORS):
            for beta in range(N_FLAVORS):
                for key in sampled_keys:
                    apply_dressed_matter(lattice, N_FLAVORS, SPIN, key, path, alpha, beta, key_index=key_index)


def test_v05_negative_incomplete_key_index_raises() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    path = make_oriented_path(lattice, (0, 1))
    alpha, beta = 0, 0

    source_key = None
    target_key = None
    for key in report.keys:
        result = apply_dressed_matter(lattice, N_FLAVORS, SPIN, key, path, alpha, beta)
        if result is not None:
            source_key, target_key = key, result.key
            break
    assert target_key is not None

    incomplete_keys = tuple(k for k in report.keys if int(k) != int(target_key))
    incomplete_key_index = build_key_index(incomplete_keys)
    assert int(source_key) in incomplete_key_index  # the source column still exists

    with pytest.raises(RuntimeError, match="invariant violation"):
        build_dressed_matter_matrix(
            lattice, N_FLAVORS, SPIN, incomplete_keys, incomplete_key_index, path, alpha, beta
        )


# ---------------------------------------------------------------------------
# Complementary: elementary action must match the assembled matrix,
# column by column, on a small case.
# ---------------------------------------------------------------------------


def test_elementary_action_matches_matrix_column_by_column() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(report.keys)
    path = make_oriented_path(lattice, (0, 1))
    alpha, beta = 1, 0

    matrix = build_dressed_matter_matrix(lattice, N_FLAVORS, SPIN, report.keys, key_index, path, alpha, beta)
    dense = matrix.toarray()

    for col, key in enumerate(report.keys):
        expected = apply_dressed_matter(lattice, N_FLAVORS, SPIN, key, path, alpha, beta, key_index=key_index)
        column = dense[:, col]
        if expected is None:
            assert np.all(column == 0)
        else:
            row = key_index[int(expected.key)]
            assert column[row] == pytest.approx(expected.amplitude)
            assert np.count_nonzero(column) == 1
