"""Local operator primitives acting on a single canonical Level0 key.

Every public function validates that ``key`` is canonical for
``(lattice, n_flavors, spin)`` via ``encoding.validate_canonical_key``
before doing anything else, and rejects out-of-range mode/edge indices
explicitly. The private helpers (prefixed ``_``) assume an already-int,
already-validated key and are only ever called after that single check, so
a composed public call (e.g. ``transport`` delegating to ``link_raise``)
never re-validates the same key twice.

No term combination, no CSR, no Hamiltonian: these are the elementary
actions a future hamiltonian.py will call once per term.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

from .encoding import flux_bit_offset, occupation_bit, validate_canonical_key
from .lattice import Lattice


@dataclass(frozen=True, slots=True)
class OperatorResult:
    key: np.uint64
    amplitude: complex


def _validate_node_flavor(lattice: Lattice, n_flavors: int, node: int, flavor: int) -> None:
    if not (0 <= node < len(lattice.nodes)):
        raise ValueError(f"node {node} is out of range [0, {len(lattice.nodes)})")
    if not (0 <= flavor < n_flavors):
        raise ValueError(f"flavor {flavor} is out of range [0, {n_flavors})")


def _validate_edge_index(lattice: Lattice, edge_index: int) -> None:
    if not (0 <= edge_index < len(lattice.edges)):
        raise ValueError(f"edge_index {edge_index} is out of range [0, {len(lattice.edges)})")


def _read_occupation_bit(key_int: int, node: int, flavor: int, n_flavors: int) -> int:
    return (key_int >> occupation_bit(node, flavor, n_flavors)) & 1


def _read_flux_field(key_int: int, lattice: Lattice, n_flavors: int, spin: int, edge_index: int) -> int:
    offset = flux_bit_offset(len(lattice.nodes), n_flavors, edge_index)
    stored_value = (key_int >> offset) & 0b111
    return stored_value - spin


def _set_flux_field(
    key_int: int, lattice: Lattice, n_flavors: int, spin: int, edge_index: int, new_value: int
) -> int:
    offset = flux_bit_offset(len(lattice.nodes), n_flavors, edge_index)
    cleared = key_int & ~(0b111 << offset)
    stored_value = new_value + spin
    return cleared | (stored_value << offset)


def _jordan_wigner_sign(key_int: int, mode_index: int) -> int:
    below = key_int & ((1 << mode_index) - 1)
    return -1 if below.bit_count() % 2 else 1


def read_occupation(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, node: int, flavor: int
) -> int:
    """Occupation n_a of mode a = node*M + flavor (0 or 1)."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_node_flavor(lattice, n_flavors, node, flavor)
    return _read_occupation_bit(int(key), node, flavor, n_flavors)


def read_flux(lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int) -> int:
    """Electric field E_e on edge_index, m in [-S, S]."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_edge_index(lattice, edge_index)
    return _read_flux_field(int(key), lattice, n_flavors, spin, edge_index)


def jordan_wigner_sign(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, node: int, flavor: int
) -> int:
    """(-1)^(number of occupied modes strictly below a = node*M + flavor)."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_node_flavor(lattice, n_flavors, node, flavor)
    mode_index = occupation_bit(node, flavor, n_flavors)
    return _jordan_wigner_sign(int(key), mode_index)


def create(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, node: int, flavor: int
) -> OperatorResult | None:
    """c_a^dagger |...>: None if mode a is already occupied."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_node_flavor(lattice, n_flavors, node, flavor)
    key_int = int(key)
    mode_index = occupation_bit(node, flavor, n_flavors)
    if _read_occupation_bit(key_int, node, flavor, n_flavors):
        return None
    sign = _jordan_wigner_sign(key_int, mode_index)
    new_key = key_int | (1 << mode_index)
    return OperatorResult(np.uint64(new_key), complex(sign))


def annihilate(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, node: int, flavor: int
) -> OperatorResult | None:
    """c_a |...>: None if mode a is empty."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_node_flavor(lattice, n_flavors, node, flavor)
    key_int = int(key)
    mode_index = occupation_bit(node, flavor, n_flavors)
    if not _read_occupation_bit(key_int, node, flavor, n_flavors):
        return None
    sign = _jordan_wigner_sign(key_int, mode_index)
    new_key = key_int & ~(1 << mode_index)
    return OperatorResult(np.uint64(new_key), complex(sign))


def link_raise(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int
) -> OperatorResult | None:
    """S_e^+ |m>: None if m = S."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_edge_index(lattice, edge_index)
    key_int = int(key)
    m = _read_flux_field(key_int, lattice, n_flavors, spin, edge_index)
    if m == spin:
        return None
    amplitude = sqrt(spin * (spin + 1) - m * (m + 1))
    new_key = _set_flux_field(key_int, lattice, n_flavors, spin, edge_index, m + 1)
    return OperatorResult(np.uint64(new_key), complex(amplitude))


def link_lower(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int
) -> OperatorResult | None:
    """S_e^- |m>: None if m = -S."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_edge_index(lattice, edge_index)
    key_int = int(key)
    m = _read_flux_field(key_int, lattice, n_flavors, spin, edge_index)
    if m == -spin:
        return None
    amplitude = sqrt(spin * (spin + 1) - m * (m - 1))
    new_key = _set_flux_field(key_int, lattice, n_flavors, spin, edge_index, m - 1)
    return OperatorResult(np.uint64(new_key), complex(amplitude))


def transport(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int
) -> OperatorResult | None:
    """U_e = S_e^+ / sqrt(S(S+1))."""
    result = link_raise(lattice, n_flavors, spin, key, edge_index)
    if result is None:
        return None
    normalization = sqrt(spin * (spin + 1))
    return OperatorResult(result.key, result.amplitude / normalization)


def transport_dagger(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int
) -> OperatorResult | None:
    """U_e^dagger = S_e^- / sqrt(S(S+1))."""
    result = link_lower(lattice, n_flavors, spin, key, edge_index)
    if result is None:
        return None
    normalization = sqrt(spin * (spin + 1))
    return OperatorResult(result.key, result.amplitude / normalization)


def electric_field(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, edge_index: int
) -> OperatorResult:
    """E_e |m> = m |m>: diagonal, never None for a valid edge_index."""
    validate_canonical_key(lattice, n_flavors, spin, key)
    _validate_edge_index(lattice, edge_index)
    m = _read_flux_field(int(key), lattice, n_flavors, spin, edge_index)
    return OperatorResult(np.uint64(key), complex(m, 0))
