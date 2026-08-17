"""Canonical uint64 encoding of Level0 states (occupations + link flux).

A state is the full configuration (fermionic occupations on all N*M modes,
electric flux E_e on all L edges), packed into a single ``numpy.uint64``:

- bits [0, N*M): occupation of mode ``b = node*M + flavor`` ;
- then ``flux_bits_per_edge(spin)`` bits per edge, storing
  ``v_e = E_e + S`` with ``0 <= v_e <= 2*S``.

An exception is raised if ``N*M + flux_bits_per_edge(spin)*L > 64``.

``flux_bits_per_edge`` is exactly 3 for every S already validated by Level0
(S=1,2,3): the on-disk/in-memory bit layout for those spins is completely
unchanged (see ``L3-A-SPIN-GENERALIZATION-AUDIT`` review). It only widens
beyond 3 bits for S>=4, where 3 bits (``v_e`` up to 7) can no longer hold
``v_e`` up to ``2*S``.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .lattice import Lattice

MAX_KEY_BITS = 64
MIN_SPIN = 1
_HISTORICAL_FLUX_BITS_PER_EDGE = 3
"""The fixed field width Level0 used for every spin it validated before
the spin generalization (S=1,2,3). ``flux_bits_per_edge`` never returns
less than this, so the encoding of every already-validated case is
bit-for-bit unchanged."""


def occupation_bit(node: int, flavor: int, n_flavors: int) -> int:
    """Bit index of mode (node, flavor) in the occupation block."""
    return node * n_flavors + flavor


def flux_bits_per_edge(spin: int) -> int:
    """Bits needed to store ``v_e = E_e + S in [0, 2*S]`` for one edge:
    ``max(3, ceil(log2(2*spin + 1)))``.

    The floor of 3 preserves the historical S=1,2,3 encoding exactly.
    Above that, ``2*spin`` is never itself a value requiring fewer bits
    than ``2*spin + 1`` distinct values (``2*spin + 1`` is always odd,
    hence never a power of two for spin >= 1), so
    ``(2 * spin).bit_length()`` is exactly ``ceil(log2(2*spin + 1))`` --
    computed in exact integer arithmetic, never float ``log2``.
    """
    validate_spin(spin)
    return max(_HISTORICAL_FLUX_BITS_PER_EDGE, (2 * spin).bit_length())


def flux_bit_offset(n_nodes: int, n_flavors: int, edge_index: int, spin: int) -> int:
    """Bit offset of ``edge_index``'s ``flux_bits_per_edge(spin)``-bit flux field in the key."""
    return n_nodes * n_flavors + flux_bits_per_edge(spin) * edge_index


def required_bits(n_nodes: int, n_flavors: int, n_edges: int, spin: int) -> int:
    if n_flavors <= 0:
        raise ValueError(f"n_flavors must be strictly positive, got {n_flavors}")
    return n_nodes * n_flavors + flux_bits_per_edge(spin) * n_edges


def validate_capacity(n_nodes: int, n_flavors: int, n_edges: int, spin: int) -> None:
    bits = required_bits(n_nodes, n_flavors, n_edges, spin)
    if bits > MAX_KEY_BITS:
        raise ValueError(
            f"encoding requires {bits} bits (N*M + flux_bits_per_edge(S)*L = "
            f"{n_nodes}*{n_flavors} + {flux_bits_per_edge(spin)}*{n_edges}), "
            f"exceeds uint64 capacity of {MAX_KEY_BITS}"
        )


def validate_spin(spin: int) -> None:
    if isinstance(spin, bool) or not isinstance(spin, (int, np.integer)) or spin < MIN_SPIN:
        raise ValueError(f"spin S={spin!r} is not supported at level 0; expected an integer >= {MIN_SPIN}")


def validate_occupation_length(n_nodes: int, n_flavors: int, occupation: Sequence[int]) -> None:
    expected = n_nodes * n_flavors
    if len(occupation) != expected:
        raise ValueError(f"expected {expected} occupation values, got {len(occupation)}")


def validate_flux_length(n_edges: int, flux: Sequence[int]) -> None:
    if len(flux) != n_edges:
        raise ValueError(f"expected {n_edges} flux values, got {len(flux)}")


def _check_canonical_bits(key_int: int, n_nodes: int, n_flavors: int, n_edges: int, spin: int) -> None:
    """Shared structural check used by both decode() and validate_canonical_key()."""
    bits = required_bits(n_nodes, n_flavors, n_edges, spin)
    canonical_mask = (1 << bits) - 1
    if key_int & ~canonical_mask:
        raise ValueError(f"key {key_int:#x} sets bits beyond the canonical range of {bits} bits")
    field_mask = (1 << flux_bits_per_edge(spin)) - 1
    for edge_index in range(n_edges):
        stored_value = (key_int >> flux_bit_offset(n_nodes, n_flavors, edge_index, spin)) & field_mask
        if not (0 <= stored_value <= 2 * spin):
            raise ValueError(
                f"stored flux value v_e={stored_value} at edge {edge_index} is outside [0, {2 * spin}]"
            )


def validate_canonical_key(lattice: Lattice, n_flavors: int, spin: int, key: np.uint64) -> None:
    """Raise ValueError unless ``key`` is structurally canonical for (lattice, n_flavors, spin).

    Checks exactly the same invariants as decode(): total capacity, no bits
    set beyond the canonical range, and every flux field within [0, 2*spin].
    """
    validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges, spin)
    _check_canonical_bits(int(key), n_nodes, n_flavors, n_edges, spin)


def encode(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    occupations: Sequence[int],
    flux: Sequence[int],
) -> np.uint64:
    """Pack occupations and per-edge electric field E_e into a canonical uint64 key."""
    validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges, spin)
    validate_occupation_length(n_nodes, n_flavors, occupations)
    validate_flux_length(n_edges, flux)

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
        key |= stored_value << flux_bit_offset(n_nodes, n_flavors, edge_index, spin)

    return np.uint64(key)


def decode(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    key: np.uint64,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Unpack a canonical uint64 key into (occupations, electric field E_e per edge)."""
    validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges, spin)

    key_int = int(key)
    _check_canonical_bits(key_int, n_nodes, n_flavors, n_edges, spin)

    field_mask = (1 << flux_bits_per_edge(spin)) - 1
    occupations = tuple((key_int >> bit_index) & 1 for bit_index in range(n_nodes * n_flavors))
    flux = tuple(
        ((key_int >> flux_bit_offset(n_nodes, n_flavors, edge_index, spin)) & field_mask) - spin
        for edge_index in range(n_edges)
    )

    return occupations, flux
