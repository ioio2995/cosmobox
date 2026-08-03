"""Linearized rigidity analysis for EXP-0001 step 7A.

Builds the rigidity matrix `B` (`d(bond length) = B @ d(positions)`)
and the linearized stiffness matrix `K = k * B.T @ B` for the current,
undamped, central-force-only harmonic bond law
(cosmobox.physics.elasticity) on a DiamondMatrix instance, and
characterizes `K`'s null space: which infinitesimal deformations cost
zero elastic energy to linear order, beyond the six expected
rigid-body motions (3 translations + 3 infinitesimal rotations, for a
free-standing 3D aggregate).

No angular spring, volume term, or extra-neighbor coupling is
introduced here — this module only measures the rigidity of the
network exactly as currently defined (central bonds between first
neighbors only). If it finds more than six near-zero modes, that is
precisely the soft-mode risk flagged in
docs/05_decisions/0001-moteur-conservatif-minimal.md, and must be
reported as measured, not corrected away by adding new physics.

Dense linear algebra only (numpy), suitable for the small/moderate
lattices used in this test suite (up to ~1000 nodes, i.e. 3N ~ 3000,
`eigh` well under a second). A much larger lattice would need a sparse
`B` and an iterative eigensolver (e.g. scipy.sparse.linalg.eigsh)
instead of a dense `eigh` on the full `3N x 3N` `K` — out of scope
here, and not added as a dependency until actually needed.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def rigidity_matrix(reference_positions: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """`B` such that, flattening `d(positions)` as `(3*N,)`,
    `d(length)[e] == B[e] @ d(positions).ravel()` for every edge
    `e = (i, j)`: row `e` has `-n_ij` at node `i`'s 3 columns and
    `+n_ij` at node `j`'s 3 columns, `n_ij` the unit bond direction
    from `i` to `j`.
    """
    n_nodes = len(reference_positions)
    n_edges = len(edges)
    vectors = reference_positions[edges[:, 1]] - reference_positions[edges[:, 0]]
    lengths = np.linalg.norm(vectors, axis=1)
    directions = vectors / lengths[:, None]

    B = np.zeros((n_edges, 3 * n_nodes))
    for e, (i, j) in enumerate(edges):
        B[e, 3 * i : 3 * i + 3] = -directions[e]
        B[e, 3 * j : 3 * j + 3] = directions[e]
    return B


def stiffness_matrix(rigidity: np.ndarray, stiffness: float) -> np.ndarray:
    return stiffness * rigidity.T @ rigidity


def rigid_translation_basis(n_nodes: int) -> np.ndarray:
    """`(3, 3N)` orthonormal rows: infinitesimal translations along x, y, z."""
    basis = np.zeros((3, 3 * n_nodes))
    for axis in range(3):
        basis[axis, axis::3] = 1.0
        basis[axis] /= np.linalg.norm(basis[axis])
    return basis


def rigid_rotation_basis(reference_positions: np.ndarray, translation_basis: np.ndarray) -> np.ndarray:
    """`(3, 3N)` orthonormal rows: infinitesimal rotations about x, y, z
    through the coordinate origin (`delta_x_i = axis x reference_positions[i]`),
    with the translation subspace projected out and the remaining three
    vectors mutually orthogonalized (Gram-Schmidt) — translations and
    rotations are not guaranteed orthogonal for an arbitrary point set,
    only verified so here numerically for this centered, symmetric
    lattice (see tests).
    """
    axes = np.eye(3)
    raw = np.zeros((3, reference_positions.size))
    for k in range(3):
        raw[k] = np.cross(axes[k], reference_positions).ravel()

    basis: list[np.ndarray] = []
    for vector in raw:
        vector = vector.copy()
        for existing in list(translation_basis) + basis:
            vector = vector - np.dot(vector, existing) * existing
        norm = np.linalg.norm(vector)
        if norm < 1e-9:
            raise ValueError("a rotation generator degenerates to (near) zero after orthogonalization")
        basis.append(vector / norm)
    return np.array(basis)


def verify_rigid_motions_are_null(
    K: np.ndarray, translation_basis: np.ndarray, rotation_basis: np.ndarray
) -> dict[str, float]:
    """`||K @ v||` for each of the 6 candidate rigid-motion vectors,
    checked directly against `K` rather than inferred from the
    eigen-decomposition's lowest eigenvalues — the two are independent
    computations that should agree, not the same fact stated twice.
    """
    residuals: dict[str, float] = {}
    for axis, name in zip(range(3), "xyz"):
        residuals[f"translation_{name}"] = float(np.linalg.norm(K @ translation_basis[axis]))
        residuals[f"rotation_{name}"] = float(np.linalg.norm(K @ rotation_basis[axis]))
    return residuals


@dataclass(slots=True)
class Mode:
    eigenvalue: float
    relative_eigenvalue: float
    participation_ratio: float
    boundary_energy_fraction: float
    rigid_translation_overlap: float
    rigid_rotation_overlap: float
    displacement: np.ndarray  # (N, 3)


@dataclass(slots=True)
class RigidityAnalysis:
    n_dof: int
    n_edges: int
    rank_B: int
    null_space_dimension: int  # via eigenvalue tolerance
    null_tolerance: float
    rigid_motion_residuals: dict[str, float]
    modes: list[Mode]  # the null_space_dimension lowest modes


def analyze_modes(
    reference_positions: np.ndarray,
    edges: np.ndarray,
    degrees: np.ndarray,
    stiffness: float,
    null_tolerance: float = 1e-6,
) -> RigidityAnalysis:
    n_nodes = len(reference_positions)
    B = rigidity_matrix(reference_positions, edges)
    K = stiffness_matrix(B, stiffness)

    eigenvalues, eigenvectors = np.linalg.eigh(K)  # ascending
    max_eigenvalue = float(eigenvalues[-1])
    if max_eigenvalue <= 0:
        raise ValueError("stiffness matrix has no positive eigenvalue; check inputs")

    translation_basis = rigid_translation_basis(n_nodes)
    rotation_basis = rigid_rotation_basis(reference_positions, translation_basis)
    rigid_motion_residuals = verify_rigid_motions_are_null(K, translation_basis, rotation_basis)

    boundary_mask = degrees < 4

    modes: list[Mode] = []
    for eigenvalue, eigenvector in zip(eigenvalues, eigenvectors.T):
        relative = float(eigenvalue / max_eigenvalue)
        if relative > null_tolerance:
            break  # eigenvalues ascending: nothing past this point is null

        displacement = eigenvector.reshape(n_nodes, 3)
        node_weight = np.sum(displacement**2, axis=1)
        total_weight = float(node_weight.sum())
        probability = node_weight / total_weight
        participation_ratio = float(1.0 / (n_nodes * np.sum(probability**2)))
        boundary_energy_fraction = float(node_weight[boundary_mask].sum() / total_weight)

        translation_overlap = float(np.sum((translation_basis @ eigenvector) ** 2))
        rotation_overlap = float(np.sum((rotation_basis @ eigenvector) ** 2))

        modes.append(
            Mode(
                eigenvalue=float(eigenvalue),
                relative_eigenvalue=relative,
                participation_ratio=participation_ratio,
                boundary_energy_fraction=boundary_energy_fraction,
                rigid_translation_overlap=translation_overlap,
                rigid_rotation_overlap=rotation_overlap,
                displacement=displacement,
            )
        )

    rank_B = int(np.linalg.matrix_rank(B))

    return RigidityAnalysis(
        n_dof=3 * n_nodes,
        n_edges=len(edges),
        rank_B=rank_B,
        null_space_dimension=len(modes),
        null_tolerance=null_tolerance,
        rigid_motion_residuals=rigid_motion_residuals,
        modes=modes,
    )


def modes_to_table(modes: list[Mode]) -> list[dict[str, object]]:
    return [
        {
            "eigenvalue": mode.eigenvalue,
            "relative_eigenvalue": mode.relative_eigenvalue,
            "participation_ratio": mode.participation_ratio,
            "boundary_energy_fraction": mode.boundary_energy_fraction,
            "rigid_translation_overlap": mode.rigid_translation_overlap,
            "rigid_rotation_overlap": mode.rigid_rotation_overlap,
        }
        for mode in modes
    ]


def write_modes_table_csv(modes: list[Mode], path: Path) -> None:
    table = modes_to_table(modes)
    if not table:
        raise ValueError("no modes to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
