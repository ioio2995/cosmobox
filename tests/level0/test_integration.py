"""End-to-end checks across the whole public API, not a duplicate of the
per-module unit suites: does the published surface (cosmobox.level0)
compose into a coherent pipeline, and is that pipeline deterministic.
"""

from __future__ import annotations

import numpy as np

from cosmobox.level0 import (
    HamiltonianParameters,
    build_basis,
    build_hamiltonian_terms,
    build_key_index,
    build_lattice,
)


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _deterministic_params(n_nodes: int) -> HamiltonianParameters:
    J = tuple(0.3 + 0.1 * i for i in range(n_nodes))
    h = tuple(_hermitian_matrix(0.2 * i, -0.2 * i, 0.15 + 0.1j) for i in range(n_nodes))
    return HamiltonianParameters(J=J, h=h, t=0.8, g_E=0.6, K=0.5)


def test_end_to_end_triangle_hamiltonian_pipeline() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1

    report = build_basis(lattice, n_flavors, spin)
    assert report.keys

    key_index = build_key_index(report.keys)
    params = _deterministic_params(len(lattice.nodes))

    terms = build_hamiltonian_terms(lattice, n_flavors, spin, report.keys, key_index, params)
    dim = len(report.keys)

    assert terms.dot.shape == terms.hopping.shape == terms.electric.shape == terms.magnetic.shape
    assert terms.total.shape == (dim, dim)

    defect = (terms.total - terms.total.conj().T).tocsr()
    defect.eliminate_zeros()
    assert defect.nnz == 0 or float(np.max(np.abs(defect.data))) < 1e-12

    dense = terms.total.toarray()
    eigenvalues = np.linalg.eigvalsh(dense)  # real by construction for a Hermitian input

    assert eigenvalues.dtype == np.float64
    assert list(eigenvalues) == sorted(eigenvalues)


def test_reproducible_end_to_end_construction_is_bitwise_identical() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    params = _deterministic_params(len(lattice.nodes))

    def _build():
        report = build_basis(lattice, n_flavors, spin)
        key_index = build_key_index(report.keys)
        return build_hamiltonian_terms(lattice, n_flavors, spin, report.keys, key_index, params)

    terms_a = _build()
    terms_b = _build()

    for name in ("dot", "hopping", "electric", "magnetic"):
        matrix_a = getattr(terms_a, name)
        matrix_b = getattr(terms_b, name)
        assert np.array_equal(matrix_a.indptr, matrix_b.indptr)
        assert np.array_equal(matrix_a.indices, matrix_b.indices)
        assert np.array_equal(matrix_a.data, matrix_b.data)  # exact, not approx: deterministic construction
