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
    """One vector of a possibly highly degenerate null (or near-null)
    space, as returned by `eigh`.

    CAUTION — basis-dependent: when `null_space_dimension` is large (as
    it is here), any orthogonal recombination of the null eigenvectors
    is an equally valid basis for the same subspace and the same
    physics. `participation_ratio`, `boundary_energy_fraction` and the
    two overlaps below are therefore properties of *this particular*
    vector as chosen by LAPACK, not physically meaningful on their own
    — do not interpret "mode number 17" individually. For
    basis-independent statements about the whole kernel, use
    `RigidityAnalysis.kernel_boundary_weight_fraction` and
    `kernel_boundary_localization_range` instead, which only depend on
    the subspace itself.
    """

    eigenvalue: float
    relative_eigenvalue: float
    participation_ratio: float
    boundary_energy_fraction: float
    rigid_translation_overlap: float
    rigid_rotation_overlap: float
    displacement: np.ndarray  # (N, 3)


def kernel_projector(kernel_basis: np.ndarray) -> np.ndarray:
    """`P0 = V.T @ V` for any orthonormal basis `V` (rows) of the
    kernel subspace. Basis-independent: for another orthonormal basis
    `V' = Q @ V` with `Q` orthogonal, `V'.T @ V' = V.T @ Q.T @ Q @ V =
    V.T @ V` — unlike the individual rows of `V`, the projector itself
    does not depend on which orthonormal basis was used to compute it.
    """
    return kernel_basis.T @ kernel_basis


def kernel_boundary_weight_fraction(projector: np.ndarray, boundary_mask: np.ndarray) -> float:
    """Fraction of the kernel's total dimension (`trace(P0)`) that sits
    on boundary-node degrees of freedom, summed over the *whole*
    subspace at once — basis-independent, unlike any individual
    eigenvector's `boundary_energy_fraction`.
    """
    per_node_weight = np.diag(projector).reshape(-1, 3).sum(axis=1)
    total = float(per_node_weight.sum())  # == kernel dimension, up to float error
    return float(per_node_weight[boundary_mask].sum() / total)


def kernel_boundary_localization_range(kernel_basis: np.ndarray, boundary_mask: np.ndarray) -> tuple[float, float]:
    """`(min, max)` of the boundary-energy fraction achievable by *any*
    unit vector inside the kernel subspace, found by diagonalizing the
    boundary-weight operator restricted to the kernel (a
    `null_space_dimension x null_space_dimension` matrix, not the full
    `K`). Both numbers are basis-independent even though the specific
    vectors that realize them are, again, just one more arbitrary
    choice of basis for the (possibly degenerate) extremal eigenspaces.
    """
    boundary_weight_flat = np.repeat(boundary_mask.astype(float), 3)
    reduced = (kernel_basis * boundary_weight_flat) @ kernel_basis.T
    eigenvalues = np.linalg.eigvalsh(reduced)
    return float(eigenvalues[0]), float(eigenvalues[-1])


def kernel_contains_rigid_subspace(
    projector: np.ndarray, translation_basis: np.ndarray, rotation_basis: np.ndarray
) -> dict[str, float]:
    """`||P0 @ v - v||` for each of the 6 rigid-motion generators: ~0
    means `v` lies exactly inside the kernel subspace `P0` projects
    onto. A basis-independent restatement of
    `verify_rigid_motions_are_null` (which checks `K @ v ~ 0` directly)
    — the two should agree, since a vector with `K @ v = 0` is by
    definition in `ker K`, but this version depends only on the
    subspace `P0`, not on `K` or the specific eigenvectors LAPACK chose
    to span it.
    """
    residuals: dict[str, float] = {}
    for axis, name in zip(range(3), "xyz"):
        for label, basis in (("translation", translation_basis), ("rotation", rotation_basis)):
            vector = basis[axis]
            residuals[f"{label}_{name}"] = float(np.linalg.norm(projector @ vector - vector))
    return residuals


@dataclass(slots=True)
class RigidityAnalysis:
    n_dof: int
    n_edges: int
    rank_B: int
    null_space_dimension: int  # via eigenvalue tolerance
    null_tolerance: float
    rigid_motion_residuals: dict[str, float]
    kernel_rigid_subspace_residuals: dict[str, float]
    kernel_boundary_weight_fraction: float
    kernel_boundary_localization_range: tuple[float, float]
    modes: list[Mode]  # the null_space_dimension lowest modes; see Mode's caveat


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

    kernel_basis = np.array([mode.displacement.ravel() for mode in modes])
    projector = kernel_projector(kernel_basis)
    kernel_rigid_residuals = kernel_contains_rigid_subspace(projector, translation_basis, rotation_basis)
    boundary_weight_fraction = kernel_boundary_weight_fraction(projector, boundary_mask)
    boundary_localization_range = kernel_boundary_localization_range(kernel_basis, boundary_mask)

    return RigidityAnalysis(
        n_dof=3 * n_nodes,
        n_edges=len(edges),
        rank_B=rank_B,
        null_space_dimension=len(modes),
        null_tolerance=null_tolerance,
        rigid_motion_residuals=rigid_motion_residuals,
        kernel_rigid_subspace_residuals=kernel_rigid_residuals,
        kernel_boundary_weight_fraction=boundary_weight_fraction,
        kernel_boundary_localization_range=boundary_localization_range,
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
