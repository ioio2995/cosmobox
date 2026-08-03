"""Deterministic injection selection for EXP-0001.

An injection is the initial perturbation applied to an otherwise resting
lattice. Node selection must be reproducible independent of array/edge
insertion order — never "the first neighbor found" — per
docs/05_decisions/0001-moteur-conservatif-minimal.md (types d'injection).
Only the momentum-compensated pair injection is implemented here; the
single-node, radial and transverse forms are later steps.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.core.matrix import DiamondMatrix


@dataclass(slots=True)
class CompensatedInjection:
    node_a: int
    node_b: int
    velocity: np.ndarray  # applied as +velocity to node_a, -velocity to node_b


def closest_interior_node_to_center(matrix: DiamondMatrix) -> int:
    """The interior (degree-4) node closest to the domain's geometric
    center. Unique for lattices built by DiamondMatrix — see
    tests/test_diamond_matrix_invariants.py::test_central_node_selection_is_unambiguous,
    which checks this is never a tie.
    """
    interior = np.flatnonzero(matrix.degrees == 4)
    distances = np.linalg.norm(matrix.reference_positions[interior], axis=1)
    order = np.argsort(distances)
    return int(interior[order[0]])


def _neighbor_along_canonical_direction(matrix: DiamondMatrix, node: int) -> int:
    """The bonded neighbor of `node` chosen by comparing bond direction
    vectors, not by position in `matrix.node_edges[node]` (which reflects
    edge-list insertion order, not geometry). Mirrors the tie-break
    already used in cosmobox.physics.particle.build_particles
    (`sorted(range(4), key=lambda i: directions[i])`), so the two
    prototypes agree on what "the first neighbor" means.
    """
    edge_ids = matrix.node_edges[node]
    if not edge_ids:
        raise ValueError(f"node {node} has no bonded neighbors")

    candidates: list[tuple[tuple[float, ...], int]] = []
    for edge_id in edge_ids:
        u, v = matrix.edges[edge_id]
        other = int(v if u == node else u)
        direction = tuple((matrix.reference_positions[other] - matrix.reference_positions[node]).tolist())
        candidates.append((direction, other))

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def compensated_pair_injection(matrix: DiamondMatrix, speed: float) -> CompensatedInjection:
    """A momentum-neutral perturbation: the central node and its
    canonical bonded neighbor receive opposite velocity impulses of
    equal magnitude `speed`, along their shared bond direction. For the
    uniform node mass used by ConservativeLatticeEngine this makes
    `sum(m * delta_v) = 0` exactly, regardless of which two nodes are
    chosen — the determinism requirement is about reproducibility, not
    about the compensation itself.
    """
    if speed <= 0:
        raise ValueError(f"speed must be strictly positive, got {speed}")

    node_a = closest_interior_node_to_center(matrix)
    node_b = _neighbor_along_canonical_direction(matrix, node_a)

    direction = matrix.reference_positions[node_b] - matrix.reference_positions[node_a]
    unit_direction = direction / np.linalg.norm(direction)

    return CompensatedInjection(node_a=node_a, node_b=node_b, velocity=speed * unit_direction)


def apply_injection(velocities: np.ndarray, injection: CompensatedInjection) -> np.ndarray:
    perturbed = velocities.copy()
    perturbed[injection.node_a] += injection.velocity
    perturbed[injection.node_b] -= injection.velocity
    return perturbed
