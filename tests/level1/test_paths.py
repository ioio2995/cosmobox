from __future__ import annotations

import pytest

from cosmobox.level0.lattice import Edge, Lattice, build_lattice
from cosmobox.level1.paths import OrientedPath, invert_path, make_oriented_path, minimal_paths

# ---------------------------------------------------------------------------
# OrientedPath.__post_init__ -- a directly constructed instance (bypassing
# make_oriented_path) must not be able to smuggle a structurally invalid
# step past construction.
# ---------------------------------------------------------------------------


def test_oriented_path_rejects_sense_zero() -> None:
    with pytest.raises(ValueError, match="sense"):
        OrientedPath(nodes=(0, 1), steps=((0, 0),))


def test_oriented_path_rejects_sense_two() -> None:
    with pytest.raises(ValueError, match="sense"):
        OrientedPath(nodes=(0, 1), steps=((0, 2),))


def test_oriented_path_rejects_negative_edge_index() -> None:
    with pytest.raises(ValueError, match="edge_index"):
        OrientedPath(nodes=(0, 1), steps=((-1, 1),))


def test_oriented_path_rejects_mismatched_node_and_step_counts() -> None:
    with pytest.raises(ValueError, match="step"):
        OrientedPath(nodes=(0, 1, 2), steps=((0, 1),))


# ---------------------------------------------------------------------------
# make_oriented_path -- construction and validation
# ---------------------------------------------------------------------------


def test_make_oriented_path_direct_step() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (0, 1))
    assert path.nodes == (0, 1)
    assert path.steps == ((0, 1),)  # edge 0 = Edge(0, 1), stored orientation
    assert path.source == 0
    assert path.destination == 1
    assert path.length == 1


def test_make_oriented_path_reversed_step() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (1, 0))
    assert path.steps == ((0, -1),)


def test_make_oriented_path_zero_length() -> None:
    lattice = build_lattice("triangle")
    path = make_oriented_path(lattice, (0,))
    assert path.nodes == (0,)
    assert path.steps == ()
    assert path.source == path.destination == 0
    assert path.length == 0


def test_make_oriented_path_rejects_empty_nodes() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError, match="at least one node"):
        make_oriented_path(lattice, ())


def test_make_oriented_path_rejects_out_of_range_node() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError, match="out of range"):
        make_oriented_path(lattice, (0, 5))


def test_make_oriented_path_rejects_discontinuous_pair() -> None:
    # chain3: nodes 0-1-2, no direct edge between 0 and 2.
    lattice = build_lattice("chain3")
    with pytest.raises(ValueError, match="no edge connects"):
        make_oriented_path(lattice, (0, 2))


def test_make_oriented_path_rejects_inconsistent_endpoints() -> None:
    lattice = build_lattice("ring4")
    # nodes 0 and 2 are not adjacent on ring4 (antipodal, distance 2).
    with pytest.raises(ValueError, match="no edge connects"):
        make_oriented_path(lattice, (0, 2))


def test_edge_lookup_rejects_multiple_edges_for_same_pair() -> None:
    # Synthetic lattice, hand-built to bypass build_lattice's own
    # _validate_edges (which already forbids this at construction time):
    # the current absence of multi-edges in every real Level0 geometry
    # must not become a silent, untested assumption inside paths.py.
    fake_lattice = Lattice(
        name="fake-multi-edge",
        nodes=(0, 1),
        edges=(Edge(0, 1), Edge(1, 0)),
        root=0,
        tree_edges=(0,),
        chords=(),
        plaquettes=(),
        resolution_order=(1, 0),
    )
    with pytest.raises(ValueError, match="more than one edge"):
        make_oriented_path(fake_lattice, (0, 1))


# ---------------------------------------------------------------------------
# invert_path
# ---------------------------------------------------------------------------


def test_invert_path_reverses_nodes_and_negates_sense() -> None:
    lattice = build_lattice("ring4")
    path = make_oriented_path(lattice, (0, 1, 2))
    inverted = invert_path(path)
    assert inverted.nodes == (2, 1, 0)
    assert inverted.steps == tuple((edge, -sense) for edge, sense in reversed(path.steps))


def test_invert_path_is_involution() -> None:
    lattice = build_lattice("ring5")
    path = make_oriented_path(lattice, (0, 1, 2))
    assert invert_path(invert_path(path)) == path


def test_invert_path_zero_length_is_self_inverse() -> None:
    lattice = build_lattice("triangle")
    zero = make_oriented_path(lattice, (0,))
    assert invert_path(zero) == zero


# ---------------------------------------------------------------------------
# minimal_paths -- determinism and required cases
# ---------------------------------------------------------------------------


def test_minimal_paths_zero_length() -> None:
    lattice = build_lattice("triangle")
    paths = minimal_paths(lattice, 1, 1)
    assert paths == (make_oriented_path(lattice, (1,)),)


def test_minimal_paths_adjacent_pair_is_unique_length_one() -> None:
    lattice = build_lattice("triangle")
    paths = minimal_paths(lattice, 0, 1)
    assert len(paths) == 1
    assert paths[0].nodes == (0, 1)


def test_minimal_paths_ring4_antipodes_two_distinct_paths() -> None:
    lattice = build_lattice("ring4")
    paths = minimal_paths(lattice, 0, 2)
    assert len(paths) == 2
    assert {p.nodes for p in paths} == {(0, 1, 2), (0, 3, 2)}
    assert all(p.length == 2 for p in paths)


def test_minimal_paths_ring4_antipodes_canonically_sorted() -> None:
    lattice = build_lattice("ring4")
    paths = minimal_paths(lattice, 0, 2)
    assert [p.nodes for p in paths] == sorted(p.nodes for p in paths)


def test_minimal_paths_ring5_length_two() -> None:
    lattice = build_lattice("ring5")
    paths = minimal_paths(lattice, 0, 2)
    assert len(paths) == 1
    assert paths[0].nodes == (0, 1, 2)


def test_minimal_paths_is_deterministic_across_calls() -> None:
    lattice = build_lattice("ring5")
    first = minimal_paths(lattice, 0, 3)
    second = minimal_paths(lattice, 0, 3)
    assert first == second


def test_minimal_paths_rejects_out_of_range_source() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError, match="out of range"):
        minimal_paths(lattice, 5, 0)


def test_minimal_paths_rejects_out_of_range_destination() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError, match="out of range"):
        minimal_paths(lattice, 0, 5)


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5", "ring6", "disk7"])
def test_minimal_paths_every_pair_has_at_least_one_path(geometry: str) -> None:
    lattice = build_lattice(geometry)
    for source in lattice.nodes:
        for destination in lattice.nodes:
            paths = minimal_paths(lattice, source, destination)
            assert len(paths) >= 1
            for path in paths:
                assert path.source == source
                assert path.destination == destination
