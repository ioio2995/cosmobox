"""Canonical uint64 encoding of Level0 states (occupations + link flux).

A state is the full configuration (fermionic occupations on all N*M modes,
electric flux E_e on all L edges), packed into a single ``numpy.uint64``:

- bits [0, N*M): occupation of mode ``b = node*M + flavor`` ;
- then 3 bits per edge, storing ``v_e = E_e + S`` with ``0 <= v_e <= 2*S``.

An exception is raised if ``N*M + 3*L > 64``.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .lattice import Lattice

FLUX_BITS_PER_EDGE = 3
MAX_KEY_BITS = 64
SUPPORTED_SPINS: tuple[int, ...] = (1, 2, 3)


def occupation_bit(node: int, flavor: int, n_flavors: int) -> int:
    """Bit index of mode (node, flavor) in the occupation block."""
    return node * n_flavors + flavor


def flux_bit_offset(n_nodes: int, n_flavors: int, edge_index: int) -> int:
    """Bit offset of the 3-bit flux field of ``edge_index`` in the key."""
    return n_nodes * n_flavors + FLUX_BITS_PER_EDGE * edge_index


def required_bits(n_nodes: int, n_flavors: int, n_edges: int) -> int:
    return n_nodes * n_flavors + FLUX_BITS_PER_EDGE * n_edges


def validate_capacity(n_nodes: int, n_flavors: int, n_edges: int) -> None:
    bits = required_bits(n_nodes, n_flavors, n_edges)
    if bits > MAX_KEY_BITS:
        raise ValueError(
            f"encoding requires {bits} bits (N*M + 3*L = "
            f"{n_nodes}*{n_flavors} + 3*{n_edges}), exceeds uint64 capacity of {MAX_KEY_BITS}"
        )


def _validate_spin(spin: int) -> None:
    if spin not in SUPPORTED_SPINS:
        raise ValueError(f"spin S={spin} is not supported at level 0; expected one of {SUPPORTED_SPINS}")


def encode(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    occupations: Sequence[int],
    flux: Sequence[int],
) -> np.uint64:
    """Pack occupations and per-edge electric field E_e into a canonical uint64 key."""
    _validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges)

    if len(occupations) != n_nodes * n_flavors:
        raise ValueError(f"expected {n_nodes * n_flavors} occupation values, got {len(occupations)}")
    if len(flux) != n_edges:
        raise ValueError(f"expected {n_edges} flux values, got {len(flux)}")

    key = 0
    for bit_index, occupation in enumerate(occupations):
        if occupation not in (0, 1):
            raise ValueError(f"occupation at bit {bit_index} must be 0 or 1, got {occupation}")
        if occupation:
            key |= 1 << bit_index

    for edge_index, electric_field in enumerate(flux):
        if not (-spin <= electric_field <= spin):
            raise ValueError(f"flux E_e={electric_field} at edge {edge_index} is outside [-{spin}, {spin}]")
        stored_value = electric_field + spin
        key |= stored_value << flux_bit_offset(n_nodes, n_flavors, edge_index)

    return np.uint64(key)


def decode(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    key: np.uint64,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Unpack a canonical uint64 key into (occupations, electric field E_e per edge)."""
    _validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges)

    key_int = int(key)
    bits = required_bits(n_nodes, n_flavors, n_edges)
    canonical_mask = (1 << bits) - 1
    if key_int & ~canonical_mask:
        raise ValueError(f"key {key_int:#x} sets bits beyond the canonical range of {bits} bits")

    occupations = tuple((key_int >> bit_index) & 1 for bit_index in range(n_nodes * n_flavors))

    flux = []
    for edge_index in range(n_edges):
        stored_value = (key_int >> flux_bit_offset(n_nodes, n_flavors, edge_index)) & 0b111
        if not (0 <= stored_value <= 2 * spin):
            raise ValueError(
                f"stored flux value v_e={stored_value} at edge {edge_index} is outside [0, {2 * spin}]"
            )
        flux.append(stored_value - spin)

    return occupations, tuple(flux)
