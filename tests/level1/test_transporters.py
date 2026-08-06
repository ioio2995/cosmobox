from __future__ import annotations

from cosmobox.level0.encoding import encode
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.operators import transport, transport_dagger
from cosmobox.level1.paths import make_oriented_path
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
