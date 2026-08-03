"""Exact point-group symmetries of a DiamondMatrix instance.

Used by the EXP-0001 step 6 orientation study to check that the engine
respects the lattice's actual symmetry (a correctness property of the
simulation, not a physical claim) rather than assumed from theory. A
transform is only accepted as a symmetry once it is verified, node by
node, against the specific finite lattice built (spherical cutoff
included) — never assumed from the infinite lattice's theoretical point
group.
"""
from __future__ import annotations

import numpy as np


def lattice_symmetry_permutation(
    reference_positions: np.ndarray, transform: np.ndarray, orthogonality_atol: float = 1e-9
) -> np.ndarray:
    """If `transform` (a 3x3 orthogonal, lattice-preserving matrix) maps
    the given point set exactly onto itself, return the permutation
    array `perm` such that
    `transform @ reference_positions[i] == reference_positions[perm[i]]`
    for every node `i`. Raises ValueError if:

    - `transform` is not a 3x3 matrix;
    - `transform` is not orthogonal (a non-isometry could accidentally
      map some lattice points onto others without being a genuine
      symmetry, and would corrupt distances/angles downstream);
    - `transform` is not an exact symmetry of this point set — e.g.
      because the spherical cutoff or lattice construction breaks it
      for some transforms even when they preserve the infinite
      lattice;
    - the resulting mapping is not a bijection on this point set (two
      source nodes mapping to the same target), which a non-orthogonal
      or otherwise degenerate transform could produce even if every
      individual target happens to land on a lattice site.

    Coordinates on this lattice are integers under any orthogonal
    coordinate permutation/sign-flip, so matching is done by exact
    rounding, not a floating-point tolerance.
    """
    transform = np.asarray(transform, dtype=float)
    if transform.shape != (3, 3):
        raise ValueError(f"transform must be a 3x3 matrix, got shape {transform.shape}")
    if not np.allclose(transform.T @ transform, np.eye(3), atol=orthogonality_atol):
        raise ValueError("transform must be orthogonal (transform.T @ transform must equal the identity)")

    transformed = reference_positions @ transform.T
    index_by_position = {tuple(np.round(point).astype(int)): index for index, point in enumerate(reference_positions)}

    permutation = np.empty(len(reference_positions), dtype=int)
    for index, point in enumerate(transformed):
        key = tuple(np.round(point).astype(int))
        match = index_by_position.get(key)
        if match is None:
            raise ValueError(
                f"transform is not an exact symmetry of this lattice: node {index} at "
                f"{reference_positions[index]} maps to {point}, which is not in the point set"
            )
        permutation[index] = match

    if len(np.unique(permutation)) != len(permutation):
        raise ValueError(
            "transform does not induce a bijection on this point set: at least two source "
            "nodes map to the same target node"
        )

    return permutation


def permutation_preserves_edges(edges: np.ndarray, permutation: np.ndarray) -> bool:
    """Whether `permutation` (typically from `lattice_symmetry_permutation`)
    maps the edge set onto itself exactly — i.e. is a graph automorphism,
    not just a symmetry of the point cloud. A transform that moves points
    onto other lattice sites without preserving adjacency would still
    pass `lattice_symmetry_permutation` but must fail this check.
    """
    original = {tuple(sorted((int(u), int(v)))) for u, v in edges}
    mapped = {tuple(sorted((int(permutation[u]), int(permutation[v])))) for u, v in edges}
    return original == mapped
