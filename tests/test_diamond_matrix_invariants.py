"""Geometric invariant checks for DiamondMatrix.

Step 1 of the EXP-0001 implementation order (docs/05_decisions/
0001-moteur-conservatif-minimal.md): DiamondMatrix reuse is conditioned
on these invariants holding, not assumed. Run against several domain
sizes, not just the default MatrixConfig, so a check that only happens
to hold for one lattice size is not mistaken for a general invariant.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix

# Independent of cosmobox.core.matrix.TETRA_DIRS: these are the four
# tetrahedral bond directions of a diamond lattice by construction, not a
# value read out of the implementation under test.
_TETRA_DIRECTIONS = np.array(
    [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]],
    dtype=int,
)


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


def _is_geometrically_interior(point: np.ndarray, sublattice: int, radius: float) -> bool:
    """Whether all four ideal tetrahedral neighbors of `point` lie inside
    the spherical domain, independently of whether DiamondMatrix actually
    materialized them as edges.

    This is the geometric definition of "interior" against which the
    matrix's reported degree is checked, so that a bug dropping an edge at
    a truly interior node would show up as a contradiction rather than
    silently being relabeled as a boundary node.
    """
    directions = _TETRA_DIRECTIONS if sublattice == 0 else -_TETRA_DIRECTIONS
    neighbors = point + directions
    return bool(np.all(np.linalg.norm(neighbors, axis=1) <= radius))


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


@pytest.fixture(
    scope="module",
    params=[
        MatrixConfig(radius=3.0, cell_range=3),
        MatrixConfig(radius=5.5, cell_range=5),
        MatrixConfig(),
        MatrixConfig(radius=12.0, cell_range=10),
    ],
    ids=["tiny", "small", "default", "large"],
)
def matrix(request: pytest.FixtureRequest) -> DiamondMatrix:
    return DiamondMatrix(request.param)


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
    assert np.any(matrix.degrees == 4)
    assert np.any(matrix.degrees < 4)


def test_geometrically_interior_nodes_have_degree_four(matrix: DiamondMatrix) -> None:
    # Degree alone cannot prove "interior" is defined correctly: a bug
    # that silently drops one edge at a truly interior node would just
    # relabel it as degree 3 without failing a degree-only check. Here
    # "interior" is derived purely from geometry (do all four ideal
    # neighbor positions fall inside the sphere?), independently of the
    # matrix's own edge list, and then compared against the reported
    # degree in both directions.
    for index, (point, degree) in enumerate(zip(matrix.reference_positions, matrix.degrees)):
        sublattice = _sublattice_of(point)
        geometrically_interior = _is_geometrically_interior(point, sublattice, matrix.config.radius)
        if geometrically_interior:
            assert degree == 4, (
                f"node {index} at {point} has all four ideal neighbors inside "
                f"the domain (radius={matrix.config.radius}) but degree {degree}"
            )
        else:
            assert degree < 4, (
                f"node {index} at {point} is missing at least one ideal neighbor "
                f"from the domain but was reported with the full degree 4"
            )


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


def test_point_cloud_is_symmetric_about_the_coordinate_origin(matrix: DiamondMatrix) -> None:
    # NOTE: the spherical cutoff in DiamondMatrix._build_lattice is applied
    # as `norm(point) <= radius`, i.e. centered on the origin by
    # construction — this test does not re-derive that independently. It
    # only checks that the resulting point cloud is in fact mass-symmetric
    # about the origin, which is a necessary (not sufficient) consequence
    # and would catch, e.g., an off-center basis or an asymmetric range
    # bug in the tiling loop.
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
