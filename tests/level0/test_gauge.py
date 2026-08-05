from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode, required_bits
from cosmobox.level0.gauge import (
    doubled_gauss_vector,
    gauss_vector,
    incidence_matrix,
    is_physical,
)
from cosmobox.level0.lattice import GEOMETRIES, build_lattice

ALL_GEOMETRIES = GEOMETRIES


@pytest.mark.parametrize("name", ALL_GEOMETRIES)
def test_incidence_matrix_signs(name: str) -> None:
    lattice = build_lattice(name)
    matrix = incidence_matrix(lattice)
    assert matrix.shape == (len(lattice.nodes), len(lattice.edges))
    assert matrix.dtype == np.int64

    for edge_index, edge in enumerate(lattice.edges):
        for node in lattice.nodes:
            if node == edge.source:
                expected = 1
            elif node == edge.target:
                expected = -1
            else:
                expected = 0
            assert matrix[node, edge_index] == expected


@pytest.mark.parametrize("name", ALL_GEOMETRIES)
def test_incidence_matrix_column_sums_are_zero(name: str) -> None:
    lattice = build_lattice(name)
    matrix = incidence_matrix(lattice)
    assert np.all(matrix.sum(axis=0) == 0)


# A handful of deterministic, not-necessarily-physical (occupation, flux)
# patterns, used to exercise the pure structural identity
# sum_i G_i = -(Q_tot + sum_i q_i^ext), which holds regardless of whether
# any individual G_i vanishes.
def _sample_configs(n_nodes: int, n_flavors: int, n_edges: int, spin: int):
    zero_occ = tuple(0 for _ in range(n_nodes * n_flavors))
    full_occ = tuple(1 for _ in range(n_nodes * n_flavors))
    alt_occ = tuple(i % 2 for i in range(n_nodes * n_flavors))

    zero_flux = tuple(0 for _ in range(n_edges))
    max_flux = tuple(spin for _ in range(n_edges))
    alt_flux = tuple((spin if i % 2 == 0 else -spin) for i in range(n_edges))

    for occupation in (zero_occ, full_occ, alt_occ):
        for flux in (zero_flux, max_flux, alt_flux):
            yield occupation, flux


@pytest.mark.parametrize("name", ALL_GEOMETRIES)
@pytest.mark.parametrize(
    "external_charges",
    [None, "half_integer"],
)
def test_global_gauss_sum_matches_charge_identity_for_arbitrary_configs(
    name: str, external_charges
) -> None:
    lattice = build_lattice(name)
    n_nodes = len(lattice.nodes)
    n_flavors = 1
    spin = 1
    ext = (
        None
        if external_charges is None
        else tuple(Fraction(1, 2) for _ in range(n_nodes))
    )
    ext_sum = Fraction(0) if ext is None else sum(ext, start=Fraction(0))

    for occupation, flux in _sample_configs(n_nodes, n_flavors, len(lattice.edges), spin):
        residuals = gauss_vector(lattice, n_flavors, occupation, flux, ext)
        q_tot = sum(
            (Fraction(sum(occupation[node * n_flavors : (node + 1) * n_flavors])) - Fraction(n_flavors, 2))
            for node in lattice.nodes
        )
        assert sum(residuals, start=Fraction(0)) == -(q_tot + ext_sum)


@pytest.mark.parametrize("name", ALL_GEOMETRIES)
@pytest.mark.parametrize("external_charges", [None, "half_integer"])
def test_doubled_gauss_vector_matches_doubled_fraction_vector(name: str, external_charges) -> None:
    lattice = build_lattice(name)
    n_nodes = len(lattice.nodes)
    n_flavors = 1
    spin = 1
    ext = (
        None
        if external_charges is None
        else tuple(Fraction(1, 2) for _ in range(n_nodes))
    )

    for occupation, flux in _sample_configs(n_nodes, n_flavors, len(lattice.edges), spin):
        fraction_residuals = gauss_vector(lattice, n_flavors, occupation, flux, ext)
        doubled_residuals = doubled_gauss_vector(lattice, n_flavors, occupation, flux, ext)
        assert doubled_residuals == tuple(int(2 * r) for r in fraction_residuals)
        for r in fraction_residuals:
            assert (2 * r).denominator == 1


@pytest.mark.parametrize(
    ("geometry", "n_flavors", "spin"),
    [
        ("triangle", 2, 1),
        ("ring4", 2, 1),
        ("ring5", 2, 1),
        ("chain3", 2, 1),
    ],
)
def test_every_basis_key_is_physical(geometry: str, n_flavors: int, spin: int) -> None:
    lattice = build_lattice(geometry)
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys
    for key in report.keys:
        assert is_physical(lattice, n_flavors, spin, key) is True


def test_deliberately_shifted_interior_flux_is_rejected() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 2, 1
    report = build_basis(lattice, n_flavors, spin)
    assert report.keys

    key = report.keys[0]
    occupation, flux = decode(lattice, n_flavors, spin, key)
    assert is_physical(lattice, n_flavors, spin, key) is True

    edge_index = 0
    delta = 1 if flux[edge_index] < spin else -1
    shifted_flux = list(flux)
    shifted_flux[edge_index] += delta

    shifted_key = encode(lattice, n_flavors, spin, occupation, shifted_flux)  # must stay canonical
    decoded_occupation, decoded_flux = decode(lattice, n_flavors, spin, shifted_key)
    assert decoded_occupation == occupation
    assert decoded_flux == tuple(shifted_flux)

    residuals = gauss_vector(lattice, n_flavors, occupation, shifted_flux)
    edge = lattice.edges[edge_index]
    for node, residual in enumerate(residuals):
        if node == edge.source:
            assert residual == delta
        elif node == edge.target:
            assert residual == -delta
        else:
            assert residual == 0

    assert is_physical(lattice, n_flavors, spin, shifted_key) is False


def test_is_physical_propagates_valueerror_on_non_canonical_key() -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    bits = required_bits(len(lattice.nodes), n_flavors, len(lattice.edges))
    non_canonical_key = np.uint64(1 << bits)  # one bit above the canonical range
    with pytest.raises(ValueError):
        is_physical(lattice, n_flavors, spin, non_canonical_key)


def test_gauss_vector_with_integer_and_half_integer_external_charges() -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    occupation = (0, 0, 0)  # Q = (-1/2, -1/2, -1/2)
    flux = (0, 0, 0)
    residuals = gauss_vector(lattice, n_flavors, occupation, flux, external_charges=(1, Fraction(1, 2), 0))
    # G_i = 0 - Q_i - q_i^ext
    assert residuals == (Fraction(1, 2) - 1, Fraction(1, 2) - Fraction(1, 2), Fraction(1, 2) - 0)
