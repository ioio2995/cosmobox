"""Sparse Hamiltonian assembly on the exact physical basis (lot 4A: H_dot + H_E only).

Each term is built as its own COO -> CSR matrix over an explicit,
caller-supplied ``key_index`` (row/col position of every physical basis
key). A transition that lands on a key absent from ``key_index`` is an
invariant violation (T2) and raises ``RuntimeError`` -- it is never
silently dropped. Separate term constructors are kept distinct (no
combined ``HamiltonianTerms``/``.total`` yet); that assembly is deferred to
lot 4C once H_hop and H_B exist too.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp

from .lattice import Lattice
from .operators import create, annihilate, read_flux, read_occupation
from .params import HamiltonianParameters


def build_key_index(keys: Sequence[np.uint64]) -> dict[int, int]:
    """Deterministic key -> row/col index, built once from the (sorted) physical basis."""
    return {int(key): row for row, key in enumerate(keys)}


def _row_for_key(key_index: dict[int, int], key: np.uint64) -> int:
    try:
        return key_index[int(key)]
    except KeyError as exc:
        raise RuntimeError(
            f"a term produced key {int(key):#x}, which is not in the physical basis; "
            "this is an invariant violation (T2), not a state to silently drop"
        ) from exc


def _assemble_csr(
    rows: list[int], cols: list[int], values: list[complex], dim: int
) -> sp.csr_matrix:
    row_array = np.asarray(rows, dtype=np.int32)
    col_array = np.asarray(cols, dtype=np.int32)
    value_array = np.asarray(values, dtype=np.complex128)
    coo = sp.coo_matrix((value_array, (row_array, col_array)), shape=(dim, dim))
    return coo.tocsr()


def build_dot_term(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    params: HamiltonianParameters,
) -> sp.csr_matrix:
    """H_dot = sum_i [ J_i(n_i1-1/2)(n_i2-1/2) + sum_ab h^(i)_ab c^dagger_ia c_ib ]. M=2 only (D006)."""
    if n_flavors != 2:
        raise ValueError(f"H_dot is only defined for n_flavors == 2 (M=2, per D006), got {n_flavors}")
    n_nodes = len(lattice.nodes)
    if len(params.J) != n_nodes:
        raise ValueError(f"expected {n_nodes} J values, got {len(params.J)}")
    if len(params.h) != n_nodes:
        raise ValueError(f"expected {n_nodes} h matrices, got {len(params.h)}")

    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []

    for col, key in enumerate(keys):
        diagonal = 0j
        for node in lattice.nodes:
            n0 = read_occupation(lattice, n_flavors, spin, key, node, 0)
            n1 = read_occupation(lattice, n_flavors, spin, key, node, 1)
            diagonal += params.J[node] * (n0 - 0.5) * (n1 - 0.5)
            diagonal += params.h[node][0, 0] * n0 + params.h[node][1, 1] * n1

            for alpha, beta in ((0, 1), (1, 0)):
                coupling = params.h[node][alpha, beta]
                if coupling == 0:
                    continue
                intermediate = annihilate(lattice, n_flavors, spin, key, node, beta)
                if intermediate is None:
                    continue
                result = create(lattice, n_flavors, spin, intermediate.key, node, alpha)
                if result is None:
                    continue
                amplitude = coupling * intermediate.amplitude * result.amplitude
                row = _row_for_key(key_index, result.key)
                rows.append(row)
                cols.append(col)
                values.append(amplitude)

        if diagonal != 0:
            rows.append(col)
            cols.append(col)
            values.append(diagonal)

    return _assemble_csr(rows, cols, values, dim)


def build_electric_term(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    params: HamiltonianParameters,
) -> sp.csr_matrix:
    """H_E = (g_E/2) sum_e E_e^2, diagonal."""
    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []

    for index, key in enumerate(keys):
        total_squared_flux = sum(
            read_flux(lattice, n_flavors, spin, key, edge_index) ** 2
            for edge_index in range(len(lattice.edges))
        )
        diagonal = 0.5 * params.g_E * total_squared_flux
        if diagonal != 0:
            rows.append(index)
            cols.append(index)
            values.append(complex(diagonal))

    return _assemble_csr(rows, cols, values, dim)
