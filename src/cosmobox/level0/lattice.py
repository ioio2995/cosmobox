"""Deterministic finite lattice geometries for Cosmobox Level0.

Each geometry declares its nodes, its oriented edges and its plaquettes
explicitly. The spanning tree (``tree_edges``/``chords``) is derived from a
deterministic breadth-first search and is only a construction aid for the
future Gauss-law resolution and basis enumeration (lot 2) -- it is not used
to derive plaquettes, which are intrinsic to each geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

GEOMETRIES: tuple[str, ...] = ("triangle", "chain3", "ring4", "ring5", "ring6", "disk7")


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed edge (source -> target). Its orientation fixes the sign of E_e."""

    source: int
    target: int


@dataclass(frozen=True, slots=True)
class Plaquette:
    """An ordered, oriented cycle: a sequence of (edge_index, sense) pairs.

    ``sense`` is +1 if the walk follows the stored orientation of the edge
    and -1 if it follows the reverse direction.
    """

    steps: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class Lattice:
    """A finite geometry: nodes, oriented edges, spanning tree and plaquettes."""

    name: str
    nodes: tuple[int, ...]
    edges: tuple[Edge, ...]
    root: int
    tree_edges: tuple[int, ...]
    chords: tuple[int, ...]
    plaquettes: tuple[Plaquette, ...]
    resolution_order: tuple[int, ...]


def _validate_edges(n_nodes: int, edges: tuple[Edge, ...]) -> None:
    seen: set[tuple[int, int]] = set()
    for edge in edges:
        if not (0 <= edge.source < n_nodes) or not (0 <= edge.target < n_nodes):
            raise ValueError(f"edge {edge} references a node outside [0, {n_nodes})")
        if edge.source == edge.target:
            raise ValueError(f"self-loop edge is not allowed: {edge}")
        pair = (edge.source, edge.target)
        if pair in seen:
            raise ValueError(f"duplicate directed edge: {edge}")
        seen.add(pair)


def _validate_plaquettes(edges: tuple[Edge, ...], plaquettes: tuple[Plaquette, ...]) -> None:
    n_edges = len(edges)
    for plaquette in plaquettes:
        if not plaquette.steps:
            raise ValueError("a plaquette must contain at least one step")
        start_node: int | None = None
        current_node: int | None = None
        for edge_index, sense in plaquette.steps:
            if not (0 <= edge_index < n_edges):
                raise ValueError(f"plaquette references unknown edge index {edge_index}")
            if sense not in (1, -1):
                raise ValueError(f"plaquette sense must be +1 or -1, got {sense}")
            edge = edges[edge_index]
            step_start, step_end = (edge.source, edge.target) if sense == 1 else (edge.target, edge.source)
            if start_node is None:
                start_node = step_start
            elif current_node != step_start:
                raise ValueError("plaquette steps do not form a contiguous walk")
            current_node = step_end
        if current_node != start_node:
            raise ValueError("plaquette is not a closed walk")


def _spanning_tree(n_nodes: int, edges: tuple[Edge, ...], root: int) -> tuple[frozenset[int], dict[int, int]]:
    adjacency: dict[int, list[tuple[int, int]]] = {node: [] for node in range(n_nodes)}
    for edge_index, edge in enumerate(edges):
        adjacency[edge.source].append((edge.target, edge_index))
        adjacency[edge.target].append((edge.source, edge_index))
    for neighbours in adjacency.values():
        neighbours.sort(key=lambda pair: pair[0])

    depth = {root: 0}
    tree_edge_indices: set[int] = set()
    queue = [root]
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        for neighbour, edge_index in adjacency[node]:
            if neighbour not in depth:
                depth[neighbour] = depth[node] + 1
                tree_edge_indices.add(edge_index)
                queue.append(neighbour)

    if len(depth) != n_nodes:
        raise ValueError("lattice is not connected: the spanning tree misses nodes")

    return frozenset(tree_edge_indices), depth


def _resolution_order(n_nodes: int, depth: dict[int, int]) -> tuple[int, ...]:
    return tuple(sorted(range(n_nodes), key=lambda node: (-depth[node], node)))


def _build(
    name: str,
    n_nodes: int,
    edges: tuple[Edge, ...],
    plaquettes: tuple[Plaquette, ...],
    root: int = 0,
) -> Lattice:
    _validate_edges(n_nodes, edges)
    _validate_plaquettes(edges, plaquettes)
    tree_edge_set, depth = _spanning_tree(n_nodes, edges, root)
    tree_edges = tuple(i for i in range(len(edges)) if i in tree_edge_set)
    chords = tuple(i for i in range(len(edges)) if i not in tree_edge_set)
    resolution_order = _resolution_order(n_nodes, depth)
    return Lattice(
        name=name,
        nodes=tuple(range(n_nodes)),
        edges=edges,
        root=root,
        tree_edges=tree_edges,
        chords=chords,
        plaquettes=plaquettes,
        resolution_order=resolution_order,
    )


def _ring_edges(n_nodes: int) -> tuple[Edge, ...]:
    return tuple(Edge(i, (i + 1) % n_nodes) for i in range(n_nodes))


def _ring_plaquette(n_nodes: int) -> Plaquette:
    return Plaquette(tuple((i, 1) for i in range(n_nodes)))


def build_triangle() -> Lattice:
    return _build("triangle", 3, _ring_edges(3), (_ring_plaquette(3),))


def build_chain3() -> Lattice:
    edges = (Edge(0, 1), Edge(1, 2))
    return _build("chain3", 3, edges, ())


def build_ring4() -> Lattice:
    return _build("ring4", 4, _ring_edges(4), (_ring_plaquette(4),))


def build_ring5() -> Lattice:
    return _build("ring5", 5, _ring_edges(5), (_ring_plaquette(5),))


def build_ring6() -> Lattice:
    return _build("ring6", 6, _ring_edges(6), (_ring_plaquette(6),))


def build_disk7() -> Lattice:
    """Centre (node 0) + a ring of six periphery nodes (1..6), 12 edges, 6 triangles."""
    spokes = tuple(Edge(0, k) for k in range(1, 7))
    ring = tuple(Edge(k, k % 6 + 1) for k in range(1, 7))
    edges = spokes + ring

    plaquettes = []
    for k in range(1, 7):
        next_k = k % 6 + 1
        spoke_out = k - 1
        ring_edge = 6 + (k - 1)
        spoke_back = next_k - 1
        plaquettes.append(Plaquette(((spoke_out, 1), (ring_edge, 1), (spoke_back, -1))))

    return _build("disk7", 7, edges, tuple(plaquettes))


_BUILDERS = {
    "triangle": build_triangle,
    "chain3": build_chain3,
    "ring4": build_ring4,
    "ring5": build_ring5,
    "ring6": build_ring6,
    "disk7": build_disk7,
}


def build_lattice(name: str) -> Lattice:
    try:
        builder = _BUILDERS[name]
    except KeyError as exc:
        raise ValueError(f"unknown geometry {name!r}; expected one of {GEOMETRIES}") from exc
    return builder()
