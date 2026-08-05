from __future__ import annotations

import itertools

import numpy as np
import pytest

from cosmobox.level0.encoding import (
    decode,
    encode,
    flux_bit_offset,
    occupation_bit,
    required_bits,
    validate_canonical_key,
    validate_capacity,
    validate_flux_length,
    validate_occupation_length,
)
from cosmobox.level0.lattice import build_lattice


def _all_occupations(n_bits: int):
    return itertools.product((0, 1), repeat=n_bits)


def _all_flux(n_edges: int, spin: int):
    return itertools.product(range(-spin, spin + 1), repeat=n_edges)


@pytest.mark.parametrize(
    ("geometry", "n_flavors", "spin"),
    [
        ("triangle", 1, 1),
        ("chain3", 2, 1),
        ("chain3", 1, 3),
        ("ring4", 1, 1),
    ],
)
def test_round_trip_is_bijective_over_all_small_configurations(geometry: str, n_flavors: int, spin: int) -> None:
    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)

    for occupations in _all_occupations(n_nodes * n_flavors):
        for flux in _all_flux(n_edges, spin):
            key = encode(lattice, n_flavors, spin, occupations, flux)
            assert isinstance(key, np.uint64)
            decoded_occupations, decoded_flux = decode(lattice, n_flavors, spin, key)
            assert decoded_occupations == tuple(occupations)
            assert decoded_flux == tuple(flux)


def test_occupation_bit_layout() -> None:
    assert occupation_bit(0, 0, n_flavors=2) == 0
    assert occupation_bit(0, 1, n_flavors=2) == 1
    assert occupation_bit(1, 0, n_flavors=2) == 2
    assert occupation_bit(3, 2, n_flavors=5) == 17


def test_flux_bit_offset_layout() -> None:
    # N*M = 6 occupation bits, then 3 bits per edge.
    assert flux_bit_offset(n_nodes=3, n_flavors=2, edge_index=0) == 6
    assert flux_bit_offset(n_nodes=3, n_flavors=2, edge_index=1) == 9
    assert flux_bit_offset(n_nodes=3, n_flavors=2, edge_index=2) == 12


def test_required_bits_and_capacity_boundary() -> None:
    assert required_bits(n_nodes=61, n_flavors=1, n_edges=1) == 64
    validate_capacity(n_nodes=61, n_flavors=1, n_edges=1)  # must not raise

    assert required_bits(n_nodes=62, n_flavors=1, n_edges=1) == 65
    with pytest.raises(ValueError):
        validate_capacity(n_nodes=62, n_flavors=1, n_edges=1)


@pytest.mark.parametrize("n_flavors", [0, -1])
def test_required_bits_rejects_non_positive_n_flavors(n_flavors: int) -> None:
    with pytest.raises(ValueError):
        required_bits(n_nodes=3, n_flavors=n_flavors, n_edges=2)


@pytest.mark.parametrize("n_flavors", [0, -1])
def test_encode_rejects_non_positive_n_flavors(n_flavors: int) -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, n_flavors, 1, occupations=[], flux=[0, 0, 0])


def test_encode_raises_when_capacity_exceeds_64_bits() -> None:
    lattice = build_lattice("disk7")  # N=7, L=12 -> N*M + 3*L = 7*M + 36
    n_flavors = 5  # 7*5 + 36 = 71 > 64
    occupations = [0] * (len(lattice.nodes) * n_flavors)
    flux = [0] * len(lattice.edges)
    with pytest.raises(ValueError):
        encode(lattice, n_flavors, 1, occupations, flux)


def test_encode_rejects_wrong_occupation_length() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, 1, 1, occupations=[0, 0], flux=[0, 0, 0])


def test_encode_rejects_wrong_flux_length() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, 1, 1, occupations=[0, 0, 0], flux=[0, 0])


def test_encode_rejects_non_binary_occupation() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, 1, 1, occupations=[0, 2, 0], flux=[0, 0, 0])


def test_encode_rejects_flux_outside_spin_range() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, 1, 1, occupations=[0, 0, 0], flux=[2, 0, 0])


@pytest.mark.parametrize("spin", [0, 4, -1])
def test_encode_rejects_unsupported_spin(spin: int) -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        encode(lattice, 1, spin, occupations=[0, 0, 0], flux=[0, 0, 0])


@pytest.mark.parametrize("spin", [0, 4, -1])
def test_decode_rejects_unsupported_spin(spin: int) -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        decode(lattice, 1, spin, np.uint64(0))


def test_decode_rejects_key_with_non_canonical_high_bits() -> None:
    lattice = build_lattice("chain3")  # N*M + 3*L = 3*1 + 3*2 = 9 bits with n_flavors=1
    n_flavors = 1
    spin = 1
    bits = required_bits(len(lattice.nodes), n_flavors, len(lattice.edges))
    key = np.uint64(1 << bits)  # one bit above the canonical range
    with pytest.raises(ValueError):
        decode(lattice, n_flavors, spin, key)


def test_decode_rejects_flux_field_exceeding_two_spin() -> None:
    lattice = build_lattice("chain3")
    n_flavors = 1
    spin = 1  # 2*spin = 2, but we store 5 in the 3-bit field of edge 0
    n_nodes = len(lattice.nodes)
    offset = flux_bit_offset(n_nodes, n_flavors, edge_index=0)
    key = np.uint64(5 << offset)
    with pytest.raises(ValueError):
        decode(lattice, n_flavors, spin, key)


def test_unused_bits_are_zero_in_a_canonical_key() -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    spin = 1
    key = encode(lattice, n_flavors, spin, occupations=[1, 0, 1], flux=[1, -1, 0])
    bits = required_bits(len(lattice.nodes), n_flavors, len(lattice.edges))
    assert int(key) < (1 << bits)


def test_validate_occupation_length_accepts_correct_length() -> None:
    validate_occupation_length(3, 2, [0, 0, 0, 0, 0, 0])  # must not raise


def test_validate_occupation_length_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        validate_occupation_length(3, 2, [0, 0, 0])


def test_validate_flux_length_accepts_correct_length() -> None:
    validate_flux_length(3, [0, 0, 0])  # must not raise


def test_validate_flux_length_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        validate_flux_length(3, [0, 0])


def test_validate_canonical_key_accepts_a_valid_key() -> None:
    lattice = build_lattice("triangle")
    key = encode(lattice, 1, 1, [1, 0, 1], [1, -1, 0])
    validate_canonical_key(lattice, 1, 1, key)  # must not raise


def test_validate_canonical_key_rejects_non_canonical_high_bits() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    bits = required_bits(len(lattice.nodes), n_flavors, len(lattice.edges))
    key = np.uint64(1 << bits)
    with pytest.raises(ValueError):
        validate_canonical_key(lattice, n_flavors, spin, key)


def test_validate_canonical_key_rejects_flux_field_exceeding_two_spin() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    offset = flux_bit_offset(len(lattice.nodes), n_flavors, edge_index=0)
    key = np.uint64(5 << offset)
    with pytest.raises(ValueError):
        validate_canonical_key(lattice, n_flavors, spin, key)
