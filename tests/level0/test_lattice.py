from __future__ import annotations

import pytest

from cosmobox.level0.lattice import (
    GEOMETRIES,
    Edge,
    Plaquette,
    build_chain3,
    build_disk7,
    build_lattice,
    build_ring4,
    build_ring5,
    build_ring6,
    build_triangle,
    _validate_edges,
    _validate_plaquettes,
)

EXPECTED_SIZES = {
    "triangle": (3, 3),
    "chain3": (3, 2),
    "ring4": (4, 4),
    "ring5": (5, 5),
    "ring6": (6, 6),
    "disk7": (7, 12),
}

EXPECTED_PLAQUETTE_COUNTS = {
    "triangle": 1,
    "chain3": 0,
    "ring4": 1,
    "ring5": 1,
    "ring6": 1,
    "disk7": 6,
}

DIRECT_BUILDERS = {
    "triangle": build_triangle,
    "chain3": build_chain3,
    "ring4": build_ring4,
    "ring5": build_ring5,
    "ring6": build_ring6,
    "disk7": build_disk7,
}


@pytest.mark.parametrize("name", GEOMETRIES)
def test_node_and_edge_counts(name: str) -> None:
    lattice = build_lattice(name)
    n_nodes, n_edges = EXPECTED_SIZES[name]
    assert lattice.nodes == tuple(range(n_nodes))
    assert len(lattice.edges) == n_edges


@pytest.mark.parametrize("name", GEOMETRIES)
def test_edges_are_unique_directed_pairs_without_self_loops(name: str) -> None:
    lattice = build_lattice(name)
    pairs = [(edge.source, edge.target) for edge in lattice.edges]
    assert len(pairs) == len(set(pairs))
    for source, target in pairs:
        assert source != target


@pytest.mark.parametrize("name", GEOMETRIES)
def test_tree_is_spanning_and_acyclic(name: str) -> None:
    lattice = build_lattice(name)
    n_nodes, _ = EXPECTED_SIZES[name]
    assert len(lattice.tree_edges) == n_nodes - 1

    parent = list(range(n_nodes))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for edge_index in lattice.tree_edges:
        edge = lattice.edges[edge_index]
        ra, rb = find(edge.source), find(edge.target)
        assert ra != rb, "tree edges must not form a cycle"
        parent[ra] = rb

    roots = {find(node) for node in lattice.nodes}
    assert len(roots) == 1, "tree edges must connect every node"


@pytest.mark.parametrize("name", GEOMETRIES)
def test_chords_are_edges_minus_tree_edges_in_global_order(name: str) -> None:
    lattice = build_lattice(name)
    all_indices = tuple(range(len(lattice.edges)))
    tree_set = set(lattice.tree_edges)
    expected_chords = tuple(i for i in all_indices if i not in tree_set)
    assert lattice.chords == expected_chords
    assert set(lattice.tree_edges) | set(lattice.chords) == set(all_indices)
    assert set(lattice.tree_edges) & set(lattice.chords) == set()
    # global order preserved
    assert lattice.tree_edges == tuple(i for i in all_indices if i in tree_set)


@pytest.mark.parametrize("name", GEOMETRIES)
def test_chord_count_matches_l_minus_n_plus_1(name: str) -> None:
    lattice = build_lattice(name)
    n_nodes, n_edges = EXPECTED_SIZES[name]
    assert len(lattice.chords) == n_edges - n_nodes + 1


@pytest.mark.parametrize("name", GEOMETRIES)
def test_plaquette_count(name: str) -> None:
    lattice = build_lattice(name)
    assert len(lattice.plaquettes) == EXPECTED_PLAQUETTE_COUNTS[name]


@pytest.mark.parametrize("name", GEOMETRIES)
def test_plaquettes_are_closed_and_oriented_walks(name: str) -> None:
    lattice = build_lattice(name)
    for plaquette in lattice.plaquettes:
        start = None
        current = None
        for edge_index, sense in plaquette.steps:
            assert sense in (1, -1)
            edge = lattice.edges[edge_index]
            step_start, step_end = (edge.source, edge.target) if sense == 1 else (edge.target, edge.source)
            if start is None:
                start = step_start
            else:
                assert current == step_start
            current = step_end
        assert current == start


def test_triangle_plaquette_is_the_full_oriented_cycle() -> None:
    lattice = build_triangle()
    assert lattice.plaquettes[0].steps == ((0, 1), (1, 1), (2, 1))


@pytest.mark.parametrize("name", ["ring4", "ring5", "ring6"])
def test_ring_plaquette_is_the_full_oriented_cycle(name: str) -> None:
    lattice = build_lattice(name)
    n_nodes, _ = EXPECTED_SIZES[name]
    assert lattice.plaquettes[0].steps == tuple((i, 1) for i in range(n_nodes))


def test_chain3_has_no_plaquette() -> None:
    lattice = build_chain3()
    assert lattice.plaquettes == ()


def test_disk7_spokes_then_ring_edge_order() -> None:
    lattice = build_disk7()
    spokes = lattice.edges[:6]
    ring = lattice.edges[6:]
    assert spokes == tuple(Edge(0, k) for k in range(1, 7))
    assert ring == tuple(Edge(k, k % 6 + 1) for k in range(1, 7))


def test_disk7_plaquettes_use_minus_one_on_the_return_spoke() -> None:
    lattice = build_disk7()
    for plaquette in lattice.plaquettes:
        (spoke_out, sense_out), (ring_edge, sense_ring), (spoke_back, sense_back) = plaquette.steps
        assert sense_out == 1
        assert sense_ring == 1
        assert sense_back == -1
        assert lattice.edges[spoke_out].source == 0
        assert lattice.edges[spoke_back].source == 0


def test_disk7_tree_is_the_spokes_and_chords_are_the_ring() -> None:
    lattice = build_disk7()
    assert set(lattice.tree_edges) == set(range(6))
    assert set(lattice.chords) == set(range(6, 12))


@pytest.mark.parametrize("name", GEOMETRIES)
def test_root_is_node_zero(name: str) -> None:
    lattice = build_lattice(name)
    assert lattice.root == 0


@pytest.mark.parametrize("name", GEOMETRIES)
def test_resolution_order_is_a_permutation_ending_at_the_root(name: str) -> None:
    lattice = build_lattice(name)
    assert tuple(sorted(lattice.resolution_order)) == lattice.nodes
    assert lattice.resolution_order[-1] == lattice.root


def test_chain3_resolution_order_is_leaves_to_root() -> None:
    lattice = build_chain3()
    assert lattice.resolution_order == (2, 1, 0)


@pytest.mark.parametrize("name", GEOMETRIES)
def test_determinism_of_construction(name: str) -> None:
    first = build_lattice(name)
    second = build_lattice(name)
    assert first == second


@pytest.mark.parametrize("name", GEOMETRIES)
def test_build_lattice_dispatch_matches_direct_builder(name: str) -> None:
    assert build_lattice(name) == DIRECT_BUILDERS[name]()


def test_build_lattice_rejects_unknown_geometry() -> None:
    with pytest.raises(ValueError):
        build_lattice("hexagon-of-doom")


def test_validate_edges_rejects_self_loop() -> None:
    with pytest.raises(ValueError):
        _validate_edges(2, (Edge(0, 0),))


def test_validate_edges_rejects_duplicate_directed_edge() -> None:
    with pytest.raises(ValueError):
        _validate_edges(2, (Edge(0, 1), Edge(0, 1)))


def test_validate_edges_rejects_reverse_duplicate() -> None:
    with pytest.raises(ValueError):
        _validate_edges(2, (Edge(0, 1), Edge(1, 0)))


def test_validate_edges_rejects_out_of_range_node() -> None:
    with pytest.raises(ValueError):
        _validate_edges(2, (Edge(0, 5),))


def test_validate_plaquettes_rejects_non_contiguous_walk() -> None:
    edges = (Edge(0, 1), Edge(1, 2), Edge(2, 0))
    # step (0,1)+1 ends at node 1, but the next step starts at node 2 instead.
    bad_plaquette = Plaquette(((0, 1), (2, 1)))
    with pytest.raises(ValueError):
        _validate_plaquettes(edges, (bad_plaquette,))


def test_validate_plaquettes_rejects_non_closed_walk() -> None:
    edges = (Edge(0, 1), Edge(1, 2))
    bad_plaquette = Plaquette(((0, 1), (1, 1)))
    with pytest.raises(ValueError):
        _validate_plaquettes(edges, (bad_plaquette,))


def test_validate_plaquettes_rejects_invalid_sense() -> None:
    edges = (Edge(0, 1),)
    bad_plaquette = Plaquette(((0, 2),))
    with pytest.raises(ValueError):
        _validate_plaquettes(edges, (bad_plaquette,))


def test_validate_plaquettes_rejects_unknown_edge_index() -> None:
    edges = (Edge(0, 1),)
    bad_plaquette = Plaquette(((7, 1),))
    with pytest.raises(ValueError):
        _validate_plaquettes(edges, (bad_plaquette,))


def test_validate_plaquettes_rejects_empty_steps() -> None:
    edges = (Edge(0, 1),)
    with pytest.raises(ValueError):
        _validate_plaquettes(edges, (Plaquette(()),))


def test_all_geometries_are_covered_by_dispatch_table() -> None:
    assert set(GEOMETRIES) == set(DIRECT_BUILDERS)
    for name in GEOMETRIES:
        build_lattice(name)  # must not raise
