"""Oriented paths and deterministic minimal-path enumeration for Level1B.

An OrientedPath identifies a sequence of lattice edges traversed from a
source node to a destination node. ``steps`` uses the same (edge_index,
sense) encoding as ``lattice.Plaquette.steps``: sense=+1 means the step
follows the edge's stored orientation (source -> target), sense=-1 means
it goes against it (target -> source).

lattice.py exports no public adjacency/edge-lookup helper -- its own
spanning-tree construction builds one internally, but it is private to
that module. This module builds its own, locally, rather than modifying
lattice.py or the rest of the Level0 package.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cosmobox.level0.lattice import Lattice


@dataclass(frozen=True, slots=True)
class OrientedPath:
    """``nodes`` is the canonical identifier: v0=source, ..., vk=destination.
    ``steps`` mirrors lattice.Plaquette.steps' (edge_index, sense) encoding.
    A zero-length path (source == destination) has nodes=(i,), steps=().

    A general OrientedPath is an oriented walk, not necessarily simple --
    only minimal_paths' enumeration guarantees simplicity.

    __post_init__ validates everything that does not require a specific
    lattice (node/step count consistency, sense in {+1, -1}, edge_index
    non-negative) -- a directly constructed OrientedPath cannot bypass
    these checks. The remaining lattice-dependent check (edge_index within
    the lattice's actual edge count) cannot be done here, since this type
    carries no lattice reference; it is enforced at application time by
    transporters.apply_transporter before any operator is applied.
    """

    nodes: tuple[int, ...]
    steps: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if len(self.nodes) == 0:
            raise ValueError("OrientedPath.nodes must contain at least one node")
        if len(self.steps) != len(self.nodes) - 1:
            raise ValueError(
                f"OrientedPath has {len(self.nodes)} node(s) but {len(self.steps)} step(s), "
                f"expected {len(self.nodes) - 1} step(s)"
            )
        for index, (edge_index, sense) in enumerate(self.steps):
            if sense not in (1, -1):
                raise ValueError(f"OrientedPath step {index} has sense={sense!r}, expected +1 or -1")
            if edge_index < 0:
                raise ValueError(
                    f"OrientedPath step {index} has edge_index={edge_index}, expected a non-negative integer"
                )

    @property
    def source(self) -> int:
        return self.nodes[0]

    @property
    def destination(self) -> int:
        return self.nodes[-1]

    @property
    def length(self) -> int:
        return len(self.steps)


def _edge_lookup(lattice: Lattice) -> dict[frozenset[int], tuple[int, int, int]]:
    """{frozenset({u, v}): (edge_index, source, target)}, one entry per
    physical link.

    Explicitly rejects a node pair associated with more than one stored
    edge. No current Level0 geometry has multi-edges (lattice._validate_edges
    already forbids it, including reverse-duplicates, at build_lattice
    time), but that absence must not become a silent assumption here: a
    genuine collision must raise, not be resolved by "last one wins".
    """
    lookup: dict[frozenset[int], tuple[int, int, int]] = {}
    for edge_index, edge in enumerate(lattice.edges):
        pair = frozenset((edge.source, edge.target))
        if pair in lookup:
            previous_index = lookup[pair][0]
            raise ValueError(
                f"node pair {set(pair)} is associated with more than one edge in lattice "
                f"{lattice.name!r} (edges {previous_index} and {edge_index}); OrientedPath "
                "construction requires a unique edge per unordered node pair"
            )
        lookup[pair] = (edge_index, edge.source, edge.target)
    return lookup


def _step_for_pair(edge_lookup: dict[frozenset[int], tuple[int, int, int]], u: int, v: int) -> tuple[int, int]:
    pair = frozenset((u, v))
    try:
        edge_index, source, target = edge_lookup[pair]
    except KeyError as exc:
        raise ValueError(f"no edge connects nodes {u} and {v}") from exc
    sense = 1 if (source, target) == (u, v) else -1
    return edge_index, sense


def make_oriented_path(lattice: Lattice, nodes: Sequence[int]) -> OrientedPath:
    """Build and validate an OrientedPath from an explicit node sequence.

    Raises ValueError if ``nodes`` is empty, references an out-of-range
    node, or any consecutive pair is not connected by a stored edge (a
    discontinuous path or inconsistent endpoints).
    """
    if len(nodes) == 0:
        raise ValueError("nodes must contain at least one node")
    for node in nodes:
        if not (0 <= node < len(lattice.nodes)):
            raise ValueError(f"node {node} is out of range [0, {len(lattice.nodes)})")

    edge_lookup = _edge_lookup(lattice)
    steps = tuple(_step_for_pair(edge_lookup, nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1))
    return OrientedPath(nodes=tuple(nodes), steps=steps)


def invert_path(path: OrientedPath) -> OrientedPath:
    """P^{-1}: reversed node order, each step's sense negated.

    Self-inverse under a second application: invert_path(invert_path(P)) == P
    (structural dataclass equality on the reconstructed, equal tuples).
    """
    reversed_steps = tuple((edge_index, -sense) for edge_index, sense in reversed(path.steps))
    return OrientedPath(nodes=tuple(reversed(path.nodes)), steps=reversed_steps)


def _sorted_neighbours(lattice: Lattice) -> dict[int, list[tuple[int, int]]]:
    """node -> sorted [(neighbour, edge_index), ...], undirected.

    Sorted by neighbour index for deterministic BFS regardless of
    dict/set iteration order -- mirrors lattice.py's own
    _spanning_tree adjacency discipline.
    """
    adjacency: dict[int, list[tuple[int, int]]] = {node: [] for node in lattice.nodes}
    for edge_index, edge in enumerate(lattice.edges):
        adjacency[edge.source].append((edge.target, edge_index))
        adjacency[edge.target].append((edge.source, edge_index))
    for neighbours in adjacency.values():
        neighbours.sort(key=lambda pair: pair[0])
    return adjacency


def minimal_paths(lattice: Lattice, source: int, destination: int) -> tuple[OrientedPath, ...]:
    """All simple shortest paths between source and destination (undirected
    graph distance), as a deterministic, canonically sorted tuple.

    source == destination yields the single zero-length path. Determinism:
    BFS uses node-index-sorted adjacency and records every predecessor at
    the shortest distance (a shortest-path DAG, so no minimal path is
    missed when there are several); the final result is additionally
    sorted lexicographically on ``nodes``, so the returned order never
    depends on internal traversal or dict/set order.
    """
    n_nodes = len(lattice.nodes)
    if not (0 <= source < n_nodes):
        raise ValueError(f"source {source} is out of range [0, {n_nodes})")
    if not (0 <= destination < n_nodes):
        raise ValueError(f"destination {destination} is out of range [0, {n_nodes})")

    if source == destination:
        return (make_oriented_path(lattice, (source,)),)

    adjacency = _sorted_neighbours(lattice)

    distance: dict[int, int] = {source: 0}
    predecessors: dict[int, list[int]] = {source: []}
    frontier = [source]
    current_distance = 0
    while frontier and destination not in distance:
        next_frontier: list[int] = []
        next_distance = current_distance + 1
        for node in frontier:
            for neighbour, _edge_index in adjacency[node]:
                if neighbour not in distance:
                    distance[neighbour] = next_distance
                    predecessors[neighbour] = []
                    next_frontier.append(neighbour)
                if distance[neighbour] == next_distance:
                    # `node` is a valid shortest-path predecessor of
                    # `neighbour` regardless of whether `neighbour` was
                    # just discovered by `node` or by an earlier node in
                    # this same layer -- every same-layer predecessor must
                    # be recorded, not only the first one found.
                    predecessors[neighbour].append(node)
        frontier = next_frontier
        current_distance = next_distance

    if destination not in distance:
        # Defensive: every Level0 geometry is validated connected at
        # build_lattice time, so this is unreachable for real lattices,
        # but the invariant must not be assumed silently here.
        raise ValueError(f"no path connects node {source} to node {destination} in lattice {lattice.name!r}")

    node_sequences: list[tuple[int, ...]] = []

    def _walk_back(node: int, tail: tuple[int, ...]) -> None:
        sequence = (node,) + tail
        if node == source:
            node_sequences.append(sequence)
            return
        for predecessor in predecessors[node]:
            _walk_back(predecessor, sequence)

    _walk_back(destination, ())
    node_sequences.sort()

    return tuple(make_oriented_path(lattice, nodes) for nodes in node_sequences)
