"""Independent Gauss-law control functions for Level0 (G_i = sum_e eps_ie E_e - Q_i - q_i^ext).

This module never imports basis.py: it exists to check basis.py's output
(and any encoded key) from a separate code path, not to build the basis
itself. Charges are handled through charges.py, shared with basis.py.

``is_physical`` contract: a canonical key that does not satisfy G_i = 0
returns ``False``. A structurally invalid key (non-canonical bits, an
out-of-range stored flux field) is not "non-physical" -- it is an encoding
error, and the ``ValueError`` raised by ``encoding.decode`` propagates
unchanged rather than being turned into ``False``.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

import numpy as np

from .charges import doubled_external_charges, normalize_external_charges
from .encoding import decode, validate_flux_length, validate_occupation_length
from .lattice import Lattice


def _validate_occupation_values(occupation: Sequence[int]) -> None:
    for index, value in enumerate(occupation):
        if value not in (0, 1):
            raise ValueError(f"occupation at index {index} must be 0 or 1, got {value!r}")


def _validate_flux_values(flux: Sequence[int]) -> None:
    for index, value in enumerate(flux):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise ValueError(f"flux value at edge {index} must be an integer, got {value!r}")


def node_charge(occupation: Sequence[int], node: int, n_flavors: int) -> Fraction:
    """Q_i = sum_alpha(n_i,alpha - 1/2) for one node, from a full occupation tuple."""
    occ_count = sum(occupation[node * n_flavors : (node + 1) * n_flavors])
    return Fraction(occ_count) - Fraction(n_flavors, 2)


def doubled_node_charge(occupation: Sequence[int], node: int, n_flavors: int) -> int:
    """Q~_i = 2*Q_i, always an integer even when Q_i is a half-integer."""
    occ_count = sum(occupation[node * n_flavors : (node + 1) * n_flavors])
    return 2 * occ_count - n_flavors


def charge_vector(occupation: Sequence[int], lattice: Lattice, n_flavors: int) -> tuple[Fraction, ...]:
    """Q = (Q_1, ..., Q_N) for a full occupation tuple."""
    validate_occupation_length(len(lattice.nodes), n_flavors, occupation)
    _validate_occupation_values(occupation)
    return tuple(node_charge(occupation, node, n_flavors) for node in lattice.nodes)


def incidence_matrix(lattice: Lattice) -> np.ndarray:
    """Dense oriented incidence matrix, shape (N, L): +1 at the source, -1 at the target."""
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    matrix = np.zeros((n_nodes, n_edges), dtype=np.int64)
    for edge_index, edge in enumerate(lattice.edges):
        matrix[edge.source, edge_index] = 1
        matrix[edge.target, edge_index] = -1
    return matrix


def gauss_vector(
    lattice: Lattice,
    n_flavors: int,
    occupation: Sequence[int],
    flux: Sequence[int],
    external_charges: Sequence[object] | None = None,
) -> tuple[Fraction, ...]:
    """G_i = sum_e eps_ie E_e - Q_i - q_i^ext for every node, exact (Fraction)."""
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_occupation_length(n_nodes, n_flavors, occupation)
    _validate_occupation_values(occupation)
    validate_flux_length(n_edges, flux)
    _validate_flux_values(flux)
    ext = normalize_external_charges(n_nodes, external_charges)
    divergence = incidence_matrix(lattice) @ np.asarray(flux, dtype=np.int64)
    return tuple(
        Fraction(int(divergence[node])) - node_charge(occupation, node, n_flavors) - ext[node]
        for node in lattice.nodes
    )


def doubled_gauss_vector(
    lattice: Lattice,
    n_flavors: int,
    occupation: Sequence[int],
    flux: Sequence[int],
    external_charges: Sequence[object] | None = None,
) -> tuple[int, ...]:
    """2*G_i for every node, computed directly in integer arithmetic (no Fraction)."""
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_occupation_length(n_nodes, n_flavors, occupation)
    _validate_occupation_values(occupation)
    validate_flux_length(n_edges, flux)
    _validate_flux_values(flux)
    q2_ext = doubled_external_charges(normalize_external_charges(n_nodes, external_charges))
    divergence = incidence_matrix(lattice) @ np.asarray(flux, dtype=np.int64)
    return tuple(
        2 * int(divergence[node]) - doubled_node_charge(occupation, node, n_flavors) - q2_ext[node]
        for node in lattice.nodes
    )


def is_physical(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    key: np.uint64,
    external_charges: Sequence[object] | None = None,
) -> bool:
    """True iff the canonical key ``key`` satisfies G_i = 0 for every node.

    Raises ``ValueError`` (propagated from ``encoding.decode``) if ``key``
    is not a structurally valid canonical key -- that is an encoding error,
    not a "non-physical" state, and is never reported as ``False``.
    """
    occupation, flux = decode(lattice, n_flavors, spin, key)
    residuals = gauss_vector(lattice, n_flavors, occupation, flux, external_charges)
    return all(residual == 0 for residual in residuals)
