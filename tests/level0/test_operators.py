from __future__ import annotations

import itertools

import numpy as np
import pytest

from cosmobox.level0.encoding import decode, encode, required_bits
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.operators import (
    OperatorResult,
    annihilate,
    create,
    electric_field,
    jordan_wigner_sign,
    link_lower,
    link_raise,
    read_flux,
    read_occupation,
    transport,
    transport_dagger,
)

# ---------------------------------------------------------------------------
# Fermion algebra: {c_a, c_b^dagger} = delta_ab * I, {c_a, c_b} = 0, {c_a^dagger, c_b^dagger} = 0
# ---------------------------------------------------------------------------


def _apply_pair(lattice, n_flavors, spin, key, outer_op, outer_mode, inner_op, inner_mode):
    """outer_op(outer_mode) applied after inner_op(inner_mode): (outer . inner)|key>."""
    intermediate = inner_op(lattice, n_flavors, spin, key, *inner_mode)
    if intermediate is None:
        return None
    result = outer_op(lattice, n_flavors, spin, intermediate.key, *outer_mode)
    if result is None:
        return None
    return int(result.key), intermediate.amplitude * result.amplitude


def _anticommutator_sum(lattice, n_flavors, spin, key, op1, mode1, op2, mode2):
    """Explicit, key-grouped sum of (op1 op2 + op2 op1)|key>."""
    contributions: dict[int, complex] = {}
    for outer_op, outer_mode, inner_op, inner_mode in (
        (op1, mode1, op2, mode2),
        (op2, mode2, op1, mode1),
    ):
        term = _apply_pair(lattice, n_flavors, spin, key, outer_op, outer_mode, inner_op, inner_mode)
        if term is not None:
            result_key, amplitude = term
            contributions[result_key] = contributions.get(result_key, 0j) + amplitude
    return contributions


@pytest.mark.parametrize(("geometry", "n_flavors"), [("triangle", 1), ("ring4", 1)])
def test_fermion_anticommutators_exhaustive(geometry: str, n_flavors: int) -> None:
    lattice = build_lattice(geometry)
    spin = 1
    n_modes = len(lattice.nodes) * n_flavors
    flux = tuple(0 for _ in lattice.edges)
    modes = [(node, flavor) for node in lattice.nodes for flavor in range(n_flavors)]

    for occupation in itertools.product((0, 1), repeat=n_modes):
        key = encode(lattice, n_flavors, spin, occupation, flux)
        for a in modes:
            for b in modes:
                cc_dagger = _anticommutator_sum(lattice, n_flavors, spin, key, annihilate, a, create, b)
                if a == b:
                    assert cc_dagger == {int(key): complex(1, 0)}
                else:
                    assert all(v == 0 for v in cc_dagger.values())

                cc = _anticommutator_sum(lattice, n_flavors, spin, key, annihilate, a, annihilate, b)
                assert all(v == 0 for v in cc.values())

                c_dagger_c_dagger = _anticommutator_sum(lattice, n_flavors, spin, key, create, a, create, b)
                assert all(v == 0 for v in c_dagger_c_dagger.values())


# ---------------------------------------------------------------------------
# Jordan-Wigner sign
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_flavors", [1, 2])
def test_jordan_wigner_sign_matches_manual_popcount(n_flavors: int) -> None:
    lattice = build_lattice("ring4")
    spin = 1
    n_modes = len(lattice.nodes) * n_flavors
    flux = tuple(0 for _ in lattice.edges)

    for occupation in itertools.product((0, 1), repeat=n_modes):
        key = encode(lattice, n_flavors, spin, occupation, flux)
        for node in lattice.nodes:
            for flavor in range(n_flavors):
                mode_index = node * n_flavors + flavor
                expected = 1 if sum(occupation[:mode_index]) % 2 == 0 else -1
                assert jordan_wigner_sign(lattice, n_flavors, spin, key, node, flavor) == expected


# ---------------------------------------------------------------------------
# Create/annihilate on the same mode, and forbidden actions
# ---------------------------------------------------------------------------


def test_create_then_annihilate_same_mode_returns_original_key() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    occupation = (0, 0, 0)
    flux = (0, 0, 0)
    key = encode(lattice, n_flavors, spin, occupation, flux)

    created = create(lattice, n_flavors, spin, key, node=0, flavor=0)
    assert created is not None
    back = annihilate(lattice, n_flavors, spin, created.key, node=0, flavor=0)
    assert back is not None
    assert back.key == key
    assert back.amplitude * created.amplitude == complex(1, 0)


def test_annihilate_then_create_same_mode_returns_original_key() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    occupation = (1, 0, 0)
    flux = (0, 0, 0)
    key = encode(lattice, n_flavors, spin, occupation, flux)

    annihilated = annihilate(lattice, n_flavors, spin, key, node=0, flavor=0)
    assert annihilated is not None
    back = create(lattice, n_flavors, spin, annihilated.key, node=0, flavor=0)
    assert back is not None
    assert back.key == key
    assert back.amplitude * annihilated.amplitude == complex(1, 0)


def test_annihilate_on_empty_mode_is_none() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (0, 0, 0))
    assert annihilate(lattice, n_flavors, spin, key, node=0, flavor=0) is None


def test_create_on_occupied_mode_is_none() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (1, 0, 0), (0, 0, 0))
    assert create(lattice, n_flavors, spin, key, node=0, flavor=0) is None


# ---------------------------------------------------------------------------
# S+/S- exact amplitudes, boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spin", [1, 2, 3])
def test_link_raise_exact_amplitude_for_every_m(spin: int) -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    occupation = (0, 0, 0)
    for m in range(-spin, spin + 1):
        flux = [0, 0, 0]
        flux[0] = m
        key = encode(lattice, n_flavors, spin, occupation, flux)
        result = link_raise(lattice, n_flavors, spin, key, edge_index=0)
        if m == spin:
            assert result is None
        else:
            assert result is not None
            expected = (spin * (spin + 1) - m * (m + 1)) ** 0.5
            assert result.amplitude == pytest.approx(complex(expected, 0))
            decoded_occ, decoded_flux = decode(lattice, n_flavors, spin, result.key)
            assert decoded_flux[0] == m + 1


@pytest.mark.parametrize("spin", [1, 2, 3])
def test_link_lower_exact_amplitude_for_every_m(spin: int) -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    occupation = (0, 0, 0)
    for m in range(-spin, spin + 1):
        flux = [0, 0, 0]
        flux[0] = m
        key = encode(lattice, n_flavors, spin, occupation, flux)
        result = link_lower(lattice, n_flavors, spin, key, edge_index=0)
        if m == -spin:
            assert result is None
        else:
            assert result is not None
            expected = (spin * (spin + 1) - m * (m - 1)) ** 0.5
            assert result.amplitude == pytest.approx(complex(expected, 0))
            decoded_occ, decoded_flux = decode(lattice, n_flavors, spin, result.key)
            assert decoded_flux[0] == m - 1


# ---------------------------------------------------------------------------
# electric_field
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spin", [1, 2, 3])
def test_electric_field_leaves_key_unchanged_and_returns_m(spin: int) -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    occupation = (0, 0, 0)
    for m in range(-spin, spin + 1):
        flux = [0, 0, 0]
        flux[0] = m
        key = encode(lattice, n_flavors, spin, occupation, flux)
        result = electric_field(lattice, n_flavors, spin, key, edge_index=0)
        assert result.key == key
        assert result.amplitude == complex(m, 0)


# ---------------------------------------------------------------------------
# [E, U] = U, tested via composition of the real electric_field/transport primitives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spin", [1, 2, 3])
def test_commutator_of_E_and_U_equals_U(spin: int) -> None:
    lattice = build_lattice("ring4")
    n_flavors = 1
    occupation = tuple(0 for _ in range(len(lattice.nodes) * n_flavors))

    for edge_index in range(len(lattice.edges)):
        for m in range(-spin, spin):  # U must succeed: m < spin
            flux = [0] * len(lattice.edges)
            flux[edge_index] = m
            key = encode(lattice, n_flavors, spin, occupation, flux)

            u_result = transport(lattice, n_flavors, spin, key, edge_index)
            assert u_result is not None
            e_after_u = electric_field(lattice, n_flavors, spin, u_result.key, edge_index)
            eu_amplitude = u_result.amplitude * e_after_u.amplitude

            e_result = electric_field(lattice, n_flavors, spin, key, edge_index)
            u_after_e = transport(lattice, n_flavors, spin, e_result.key, edge_index)
            assert u_after_e is not None
            ue_amplitude = e_result.amplitude * u_after_e.amplitude

            assert e_after_u.key == u_after_e.key == u_result.key
            commutator_amplitude = eu_amplitude - ue_amplitude
            assert commutator_amplitude == pytest.approx(u_result.amplitude)


# ---------------------------------------------------------------------------
# U / U^dagger matrix-element adjunction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spin", [1, 2, 3])
def test_transport_dagger_matrix_element_matches_transport(spin: int) -> None:
    lattice = build_lattice("triangle")
    n_flavors = 1
    occupation = (0, 0, 0)
    for m in range(-spin, spin):
        flux = [0, 0, 0]
        flux[0] = m
        key = encode(lattice, n_flavors, spin, occupation, flux)

        u = transport(lattice, n_flavors, spin, key, edge_index=0)
        assert u is not None
        u_dagger = transport_dagger(lattice, n_flavors, spin, u.key, edge_index=0)
        assert u_dagger is not None
        assert u_dagger.key == key
        assert u_dagger.amplitude == pytest.approx(u.amplitude)


def test_link_raise_at_top_boundary_is_none() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 2
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (spin, 0, 0))
    assert link_raise(lattice, n_flavors, spin, key, edge_index=0) is None


def test_link_lower_at_bottom_boundary_is_none() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 2
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (-spin, 0, 0))
    assert link_lower(lattice, n_flavors, spin, key, edge_index=0) is None


# ---------------------------------------------------------------------------
# Conservation of unrelated bits/fields, canonicity of results
# ---------------------------------------------------------------------------


def test_create_only_touches_its_own_bit() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 2, 1
    occupation = (1, 0, 0, 1, 1, 0)  # node0:(1,0) node1:(0,1) node2:(1,0)
    flux = (1, -1, 0)
    key = encode(lattice, n_flavors, spin, occupation, flux)

    result = create(lattice, n_flavors, spin, key, node=0, flavor=1)
    assert result is not None
    decoded_occ, decoded_flux = decode(lattice, n_flavors, spin, result.key)
    assert decoded_flux == flux
    expected_occ = list(occupation)
    expected_occ[0 * n_flavors + 1] = 1
    assert decoded_occ == tuple(expected_occ)


def test_transport_only_touches_its_own_edge() -> None:
    lattice = build_lattice("ring4")
    n_flavors, spin = 1, 2
    occupation = (0, 1, 0, 1)
    flux = (0, -1, 1, 0)
    key = encode(lattice, n_flavors, spin, occupation, flux)

    result = transport(lattice, n_flavors, spin, key, edge_index=2)
    assert result is not None
    decoded_occ, decoded_flux = decode(lattice, n_flavors, spin, result.key)
    assert decoded_occ == occupation
    expected_flux = list(flux)
    expected_flux[2] += 1
    assert decoded_flux == tuple(expected_flux)


@pytest.mark.parametrize(
    "op_call",
    [
        lambda lattice, n_flavors, spin, key: create(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: annihilate(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: link_raise(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: transport(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: electric_field(lattice, n_flavors, spin, key, 0),
    ],
)
def test_results_always_decode_without_error(op_call) -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (1, 0, 0), (0, 0, 0))
    result = op_call(lattice, n_flavors, spin, key)
    if result is not None:
        decode(lattice, n_flavors, spin, result.key)  # must not raise


# ---------------------------------------------------------------------------
# Out-of-range indices
# ---------------------------------------------------------------------------


def test_create_rejects_out_of_range_node() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (0, 0, 0))
    with pytest.raises(ValueError):
        create(lattice, n_flavors, spin, key, node=99, flavor=0)


def test_read_occupation_rejects_out_of_range_flavor() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (0, 0, 0))
    with pytest.raises(ValueError):
        read_occupation(lattice, n_flavors, spin, key, node=0, flavor=5)


def test_read_flux_rejects_out_of_range_edge_index() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (0, 0, 0))
    with pytest.raises(ValueError):
        read_flux(lattice, n_flavors, spin, key, edge_index=99)


def test_link_raise_rejects_out_of_range_edge_index() -> None:
    lattice = build_lattice("triangle")
    n_flavors, spin = 1, 1
    key = encode(lattice, n_flavors, spin, (0, 0, 0), (0, 0, 0))
    with pytest.raises(ValueError):
        link_raise(lattice, n_flavors, spin, key, edge_index=-1)


# ---------------------------------------------------------------------------
# Rejection of non-canonical keys
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "op_call",
    [
        lambda lattice, n_flavors, spin, key: read_occupation(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: read_flux(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: jordan_wigner_sign(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: create(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: annihilate(lattice, n_flavors, spin, key, 0, 0),
        lambda lattice, n_flavors, spin, key: link_raise(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: link_lower(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: transport(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: transport_dagger(lattice, n_flavors, spin, key, 0),
        lambda lattice, n_flavors, spin, key: electric_field(lattice, n_flavors, spin, key, 0),
    ],
)
def test_every_public_operator_rejects_non_canonical_key(op_call) -> None:
    lattice = build_lattice("chain3")
    n_flavors, spin = 1, 1
    bits = required_bits(len(lattice.nodes), n_flavors, len(lattice.edges))
    non_canonical_key = np.uint64(1 << bits)
    with pytest.raises(ValueError):
        op_call(lattice, n_flavors, spin, non_canonical_key)
