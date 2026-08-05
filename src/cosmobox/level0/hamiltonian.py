"""Sparse Hamiltonian assembly on the exact physical basis (lot 4B: + H_hop).

Each term is built as its own COO -> CSR matrix over an explicit,
caller-supplied ``key_index`` (row/col position of every physical basis
key). A transition that lands on a key absent from ``key_index`` is an
invariant violation (T2) and raises ``RuntimeError`` -- it is never
silently dropped. Separate term constructors are kept distinct (no
combined ``HamiltonianTerms``/``.total`` yet); that assembly is deferred to
lot 4C once H_B exists too.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp

from .encoding import validate_capacity
from .lattice import Lattice
from .operators import annihilate, create, read_flux, read_occupation, transport, transport_dagger
from .params import HamiltonianParameters


def build_key_index(keys: Sequence[np.uint64]) -> dict[int, int]:
    """Deterministic key -> row/col index, built once from the (sorted) physical basis.

    Raises ValueError on a duplicate key: as in basis.py, a duplicated
    basis entry is an invariant violation, not something to overwrite
    silently in the index.
    """
    key_index: dict[int, int] = {}
    for row, key in enumerate(keys):
        key_int = int(key)
        if key_int in key_index:
            raise ValueError(
                f"duplicate basis key {key_int:#x} at rows {key_index[key_int]} and {row}"
            )
        key_index[key_int] = row
    return key_index


def validate_key_index(keys: Sequence[np.uint64], key_index: dict[int, int]) -> None:
    """Check that key_index is exactly the row/col index of keys -- not just any dict.

    Guards against a stale index (built from a different/reordered key
    sequence), a partial index, or one with out-of-range/duplicated rows,
    none of which _row_for_key's lookup alone would ever catch.
    """
    if len(key_index) != len(keys):
        raise ValueError(f"key_index has {len(key_index)} entries, expected {len(keys)}")
    dim = len(keys)
    seen_rows: set[int] = set()
    for row, key in enumerate(keys):
        key_int = int(key)
        if key_int not in key_index:
            raise ValueError(f"key {key_int:#x} (row {row}) is missing from key_index")
        indexed_row = key_index[key_int]
        if not (0 <= indexed_row < dim):
            raise ValueError(f"key_index[{key_int:#x}] = {indexed_row} is out of range [0, {dim})")
        if indexed_row != row:
            raise ValueError(
                f"key_index[{key_int:#x}] = {indexed_row} does not match its position {row} in keys"
            )
        if indexed_row in seen_rows:
            raise ValueError(f"row {indexed_row} is assigned to more than one key in key_index")
        seen_rows.add(indexed_row)


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
    validate_key_index(keys, key_index)
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
    key_index: dict[int, int],
    params: HamiltonianParameters,
) -> sp.csr_matrix:
    """H_E = (g_E/2) sum_e E_e^2, diagonal.

    key_index is not used for any lookup here (H_E never changes the key),
    but is still validated against keys for the same reason build_dot_term
    validates it: catching a stale or mismatched index at the boundary of
    every term builder, not only the ones that happen to need it today.
    """
    validate_key_index(keys, key_index)
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


def build_hopping_term(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    params: HamiltonianParameters,
) -> sp.csr_matrix:
    """H_hop = -t sum_{e=(i->j),alpha} [ c^dagger_ia U_e c_ja + c^dagger_ja U_e^dagger c_ia ].

    No M restriction (unlike H_dot): iterates every flavor 0..n_flavors-1
    and every edge in lattice.edges (all physical links, independent of
    the tree_edges/chords split, which is only a basis.py construction
    aid). Both directions are generated explicitly from the composed
    operator primitives -- never restored by symmetrizing the matrix.
    """
    validate_capacity(len(lattice.nodes), n_flavors, len(lattice.edges))
    validate_key_index(keys, key_index)

    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []

    if params.t != 0:
        for col, key in enumerate(keys):
            for edge_index, edge in enumerate(lattice.edges):
                source, target = edge.source, edge.target
                for flavor in range(n_flavors):
                    # Direct: c^dagger_source,flavor U_e c_target,flavor
                    annihilated = annihilate(lattice, n_flavors, spin, key, target, flavor)
                    if annihilated is not None:
                        transported = transport(lattice, n_flavors, spin, annihilated.key, edge_index)
                        if transported is not None:
                            created = create(lattice, n_flavors, spin, transported.key, source, flavor)
                            if created is not None:
                                amplitude = (
                                    -params.t * annihilated.amplitude * transported.amplitude * created.amplitude
                                )
                                row = _row_for_key(key_index, created.key)
                                rows.append(row)
                                cols.append(col)
                                values.append(amplitude)

                    # Conjugate: c^dagger_target,flavor U_e^dagger c_source,flavor
                    annihilated_hc = annihilate(lattice, n_flavors, spin, key, source, flavor)
                    if annihilated_hc is not None:
                        transported_hc = transport_dagger(
                            lattice, n_flavors, spin, annihilated_hc.key, edge_index
                        )
                        if transported_hc is not None:
                            created_hc = create(lattice, n_flavors, spin, transported_hc.key, target, flavor)
                            if created_hc is not None:
                                amplitude_hc = (
                                    -params.t
                                    * annihilated_hc.amplitude
                                    * transported_hc.amplitude
                                    * created_hc.amplitude
                                )
                                row_hc = _row_for_key(key_index, created_hc.key)
                                rows.append(row_hc)
                                cols.append(col)
                                values.append(amplitude_hc)

    return _assemble_csr(rows, cols, values, dim)
