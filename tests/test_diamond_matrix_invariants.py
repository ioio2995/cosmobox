"""Geometric invariant checks for DiamondMatrix.

Step 1 of the EXP-0001 implementation order (docs/05_decisions/
0001-moteur-conservatif-minimal.md): DiamondMatrix reuse is conditioned
on these invariants holding, not assumed.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix


def _sublattice_of(point: np.ndarray) -> int:
    """Recompute FCC-sublattice membership from raw coordinates only.

    Independent of DiamondMatrix's internal bookkeeping: the two
    interpenetrating FCC sublattices used to build the diamond lattice
    differ by a coordinate-sum residue mod 4 (0 for the "a" sites, 3 for
    the "a + (1,1,1)" sites), which stays invariant under any 4*(ix,iy,iz)
    translation used to tile cells.
    """
    residue = int(round(point.sum())) % 4
    if residue == 0:
        return 0
    if residue == 3:
        return 1
    raise AssertionError(f"unexpected coordinate-sum residue {residue} for point {point}")


def _connected_components(num_nodes: int, edges: np.ndarray) -> list[set[int]]:
    adjacency: list[list[int]] = [[] for _ in range(num_nodes)]
    for u, v in edges:
        adjacency[int(u)].append(int(v))
        adjacency[int(v)].append(int(u))

    visited = [False] * num_nodes
    components = []
    for start in range(num_nodes):
        if visited[start]:
            continue
        component = {start}
        visited[start] = True
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return components


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig())


def test_all_edges_share_the_same_rest_length(matrix: DiamondMatrix) -> None:
    assert np.allclose(matrix.base_lengths, matrix.c, rtol=0, atol=1e-9)


def test_no_duplicate_edges(matrix: DiamondMatrix) -> None:
    pairs = {tuple(sorted((int(u), int(v)))) for u, v in matrix.edges}
    assert len(pairs) == len(matrix.edges)


def test_no_isolated_nodes(matrix: DiamondMatrix) -> None:
    assert np.all(matrix.degrees >= 1)


def test_network_is_connected(matrix: DiamondMatrix) -> None:
    components = _connected_components(len(matrix.positions), matrix.edges)
    assert len(components) == 1, f"expected a single connected component, found {len(components)}"


def test_no_node_exceeds_the_tetrahedral_coordination_number(matrix: DiamondMatrix) -> None:
    assert np.all(matrix.degrees <= 4)


def test_interior_and_boundary_nodes_are_both_present(matrix: DiamondMatrix) -> None:
    # Interior nodes (degree 4, all four ideal neighbors present) and
    # boundary nodes (degree < 4, cut off by the spherical domain) must
    # both exist and be distinguishable for a finite sphere cutoff.
    assert np.any(matrix.degrees == 4)
    assert np.any(matrix.degrees < 4)


def test_lattice_is_bipartite_between_the_two_fcc_sublattices(matrix: DiamondMatrix) -> None:
    sublattices = np.array([_sublattice_of(p) for p in matrix.reference_positions])
    assert set(sublattices.tolist()) == {0, 1}

    offenders = [
        (int(u), int(v))
        for u, v in matrix.edges
        if sublattices[int(u)] == sublattices[int(v)]
    ]
    assert not offenders, (
        "a diamond-lattice edge must connect the two interpenetrating FCC "
        f"sublattices, but found same-sublattice edges: {offenders[:5]}"
        + (" ..." if len(offenders) > 5 else "")
    )


def test_geometric_center_of_the_domain_is_the_coordinate_origin(matrix: DiamondMatrix) -> None:
    # The sphere cutoff (config.radius) is applied around the coordinate
    # origin, so the point cloud's centroid must coincide with it.
    centroid = matrix.reference_positions.mean(axis=0)
    assert np.linalg.norm(centroid) < 1e-9


def test_central_node_selection_is_unambiguous(matrix: DiamondMatrix) -> None:
    # EXP-0001's injection node is "the interior node closest to the
    # geometric center". This must not be a coin flip between candidates
    # at the same distance, and it must actually be an interior node.
    interior = np.flatnonzero(matrix.degrees == 4)
    distances = np.linalg.norm(matrix.reference_positions[interior], axis=1)
    order = np.argsort(distances)

    closest_distance = distances[order[0]]
    second_closest_distance = distances[order[1]]
    assert closest_distance < second_closest_distance - 1e-9, (
        "closest and second-closest interior nodes are tied "
        f"({closest_distance} vs {second_closest_distance}); "
        "the injection node is not uniquely defined"
    )

    central_node = int(interior[order[0]])
    assert matrix.degrees[central_node] == 4
    assert np.linalg.norm(matrix.reference_positions[central_node]) < 1e-9
