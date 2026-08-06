from __future__ import annotations

import pytest

from cosmobox.level0.encoding import encode
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.operators import transport, transport_dagger
from cosmobox.level1.paths import OrientedPath, make_oriented_path
from cosmobox.level1.transporters import apply_transporter

N_FLAVORS = 2
SPIN = 1


def _key(lattice, occupation=None, flux=None):
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    occupation = occupation if occupation is not None else (0,) * (n_nodes * N_FLAVORS)
    flux = flux if flux is not None else (0,) * n_edges
    return encode(lattice, N_FLAVORS, SPIN, occupation, flux)


# ---------------------------------------------------------------------------
# Empty path is the identity
# ---------------------------------------------------------------------------


def test_apply_transporter_empty_path_is_identity() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = make_oriented_path(lattice, (0,))
    result = apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
    assert result is not None
    assert int(result.key) == int(key)
    assert result.amplitude == 1.0 + 0j


# ---------------------------------------------------------------------------
# Direct / reversed single step (V02)
# ---------------------------------------------------------------------------


def test_apply_transporter_direct_step_matches_transport() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = make_oriented_path(lattice, (0, 1))  # edge 0, sense +1
    expected = transport(lattice, N_FLAVORS, SPIN, key, 0)
    result = apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
    assert result is not None and expected is not None
    assert int(result.key) == int(expected.key)
    assert result.amplitude == expected.amplitude


def test_apply_transporter_reversed_step_matches_transport_dagger() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = make_oriented_path(lattice, (1, 0))  # edge 0, sense -1
    expected = transport_dagger(lattice, N_FLAVORS, SPIN, key, 0)
    result = apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
    assert result is not None and expected is not None
    assert int(result.key) == int(expected.key)
    assert result.amplitude == expected.amplitude


# ---------------------------------------------------------------------------
# Saturation -> None (upper and lower bound of the finite link)
# ---------------------------------------------------------------------------


def test_apply_transporter_returns_none_on_high_saturation() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice, flux=(SPIN, 0, 0))  # edge 0 at m = +S
    path = make_oriented_path(lattice, (0, 1))  # sense +1 -> transport (raises m)
    assert apply_transporter(lattice, N_FLAVORS, SPIN, key, path) is None


def test_apply_transporter_returns_none_on_low_saturation() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice, flux=(-SPIN, 0, 0))  # edge 0 at m = -S
    path = make_oriented_path(lattice, (1, 0))  # sense -1 -> transport_dagger (lowers m)
    assert apply_transporter(lattice, N_FLAVORS, SPIN, key, path) is None


def test_apply_transporter_middle_step_saturation_short_circuits() -> None:
    # A 2-step path where the SECOND applied step (path step 0, applied
    # last in application order -- see the reversed(steps) iteration)
    # saturates: must still return None, not a partial result.
    lattice = build_lattice("ring4")
    key = _key(lattice, flux=(SPIN, 0, 0, 0))  # edge 0 (between nodes 0 and 1) at m=+S
    path = make_oriented_path(lattice, (0, 1, 2))  # step0=edge0 (sense+1), step1=edge1 (sense+1)
    assert apply_transporter(lattice, N_FLAVORS, SPIN, key, path) is None


# ---------------------------------------------------------------------------
# No additional normalization (nu_S = 1): the multi-step amplitude is
# exactly the raw product of each individual transport/transport_dagger
# amplitude, nothing else.
# ---------------------------------------------------------------------------


def test_apply_transporter_multi_step_amplitude_is_exact_raw_product() -> None:
    lattice = build_lattice("ring4")
    key = _key(lattice)
    path = make_oriented_path(lattice, (0, 1, 2))  # step0=edge0 sense+1, step1=edge1 sense+1

    # Application order: last path step first (see module docstring).
    step1_result = transport(lattice, N_FLAVORS, SPIN, key, 1)
    assert step1_result is not None
    step0_result = transport(lattice, N_FLAVORS, SPIN, step1_result.key, 0)
    assert step0_result is not None
    expected_amplitude = step1_result.amplitude * step0_result.amplitude

    result = apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
    assert result is not None
    assert int(result.key) == int(step0_result.key)
    assert result.amplitude == expected_amplitude


def test_apply_transporter_mixed_sense_amplitude_is_exact_raw_product() -> None:
    lattice = build_lattice("ring4")
    key = _key(lattice)
    path = make_oriented_path(lattice, (0, 3, 2))  # step0=edge3 (Edge(3,0), sense=-1), step1=edge2 (Edge(2,3), sense=-1)

    step1_result = transport_dagger(lattice, N_FLAVORS, SPIN, key, 2)
    assert step1_result is not None
    step0_result = transport_dagger(lattice, N_FLAVORS, SPIN, step1_result.key, 3)
    assert step0_result is not None
    expected_amplitude = step1_result.amplitude * step0_result.amplitude

    result = apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
    assert result is not None
    assert int(result.key) == int(step0_result.key)
    assert result.amplitude == expected_amplitude


# ---------------------------------------------------------------------------
# apply_transporter's own explicit validation against the lattice: an
# out-of-range edge_index (genuinely lattice-dependent, cannot be checked
# by OrientedPath.__post_init__ alone) and a defense-in-depth check for a
# malformed sense reaching apply_transporter despite OrientedPath's own
# construction-time guard.
# ---------------------------------------------------------------------------


def test_apply_transporter_rejects_edge_index_at_n_edges() -> None:
    lattice = build_lattice("triangle")  # 3 edges: valid indices are 0, 1, 2
    key = _key(lattice)
    path = OrientedPath(nodes=(0, 1), steps=((3, 1),))  # constructible: 3 >= 0, sense valid
    with pytest.raises(ValueError, match="edge_index"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


def test_apply_transporter_rejects_edge_index_far_out_of_range() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = OrientedPath(nodes=(0, 1), steps=((99, -1),))
    with pytest.raises(ValueError, match="edge_index"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


def test_apply_transporter_rejects_malformed_sense_bypassing_construction() -> None:
    # OrientedPath.__post_init__ already rejects sense not in {+1, -1} at
    # construction time (see test_paths.py), so a normally constructed
    # path can never carry a bad sense here. This test simulates a
    # corrupted/hand-assembled path (object.__setattr__ on the frozen
    # instance, bypassing __post_init__ entirely) to prove
    # apply_transporter's own explicit check is real and independent, not
    # merely inherited from OrientedPath and dead code in practice.
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = make_oriented_path(lattice, (0, 1))
    object.__setattr__(path, "steps", ((0, 2),))
    with pytest.raises(ValueError, match="sense"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


# ---------------------------------------------------------------------------
# Genuine node<->edge<->sense consistency: a structurally valid
# (edge_index, sense) pair is not enough if it doesn't actually match the
# path's own node sequence.
# ---------------------------------------------------------------------------


def test_apply_transporter_rejects_edge_not_connecting_the_claimed_nodes() -> None:
    # Right step count, in-range edge_index and valid sense, but edge 1
    # (Edge(1, 2)) does not connect nodes 0 and 1.
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = OrientedPath(nodes=(0, 1), steps=((1, 1),))
    with pytest.raises(ValueError, match="does not connect"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


def test_apply_transporter_rejects_sense_inconsistent_with_nodes() -> None:
    # Edge 0 (Edge(0, 1)) does connect nodes 0 and 1, but travelling from
    # 0 to 1 follows the stored orientation (sense should be +1, not -1).
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = OrientedPath(nodes=(0, 1), steps=((0, -1),))
    with pytest.raises(ValueError, match="requires sense"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


def test_apply_transporter_rejects_negative_node() -> None:
    lattice = build_lattice("triangle")
    key = _key(lattice)
    path = OrientedPath(nodes=(-1, 0), steps=((0, 1),))
    with pytest.raises(ValueError, match="out of range"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)


def test_apply_transporter_rejects_node_at_n_nodes() -> None:
    lattice = build_lattice("triangle")  # 3 nodes: valid indices are 0, 1, 2
    key = _key(lattice)
    path = OrientedPath(nodes=(0, 3), steps=((0, 1),))
    with pytest.raises(ValueError, match="out of range"):
        apply_transporter(lattice, N_FLAVORS, SPIN, key, path)
