"""Interior relaxation under a fixed, affinely-sheared boundary shell,
for EXP-0001 step 7B-2.

For a given global shear amplitude gamma, the boundary shell is fixed
at its affine-sheared position while the interior nodes' positions are
free; both a linear reference (direct block solve of the linearized
system) and a full nonlinear relaxation (minimizing the exact harmonic
bond energy, dependency-free steepest descent with backtracking line
search — this project does not depend on scipy) are provided, so the
two can be cross-checked against each other in the small-gamma regime.

Two boundary definitions are supported (`boundary_mask_by_degree`,
`boundary_mask_by_radius`) per the step-7B-1 review: `degrees < 4`
alone was flagged as an unstudied choice, not to be used without a
sensitivity check against at least one alternative.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_forces, bond_lengths


def boundary_mask_by_degree(degrees: np.ndarray) -> np.ndarray:
    return degrees < 4


def boundary_mask_by_radius(reference_positions: np.ndarray, domain_radius: float, alpha: float) -> np.ndarray:
    """Nodes whose reference distance from the origin is at least
    `alpha * domain_radius` (e.g. `alpha=0.85`) — an alternative to
    `boundary_mask_by_degree` that does not depend on the local
    coordination number, to check results are not an artifact of one
    particular boundary definition.
    """
    distances = np.linalg.norm(reference_positions, axis=1)
    return distances >= alpha * domain_radius


@dataclass(slots=True)
class LinearRelaxationResult:
    displacement: np.ndarray  # (N, 3), full state: solved interior + imposed boundary
    energy: float
    interior_mechanism_dimension: int  # nullity of K_II: interior mechanisms compatible with this fixed boundary


def linear_relaxation(K: np.ndarray, boundary_mask: np.ndarray, boundary_displacement: np.ndarray) -> LinearRelaxationResult:
    """Solves the linearized problem `K_II @ u_I = -K_IB @ u_B` for the
    interior displacement `u_I` given a fixed boundary displacement
    `u_B` (`boundary_displacement`, flat `(3N,)`, only its
    boundary-node entries are used), via least squares (handles `K_II`
    being singular — expected here — returning its minimum-norm
    solution rather than failing). Also reports `nullity(K_II)`: the
    dimension of interior mechanisms still compatible with *this*
    particular fixed boundary (not the same as the free-lattice kernel
    dimension from cosmobox.physics.rigidity, which had no boundary
    constraint at all).
    """
    n_dof = K.shape[0]
    n_nodes = n_dof // 3
    boundary_dof = np.repeat(boundary_mask, 3)
    interior_dof = ~boundary_dof

    K_II = K[np.ix_(interior_dof, interior_dof)]
    K_IB = K[np.ix_(interior_dof, boundary_dof)]
    u_B = boundary_displacement[boundary_dof]

    rhs = -K_IB @ u_B
    u_I, _, rank_K_II, _ = np.linalg.lstsq(K_II, rhs, rcond=None)

    u_full = np.zeros(n_dof)
    u_full[interior_dof] = u_I
    u_full[boundary_dof] = u_B
    energy = float(0.5 * u_full @ K @ u_full)

    return LinearRelaxationResult(
        displacement=u_full.reshape(n_nodes, 3),
        energy=energy,
        interior_mechanism_dimension=int(K_II.shape[0] - rank_K_II),
    )


@dataclass(slots=True)
class RelaxationResult:
    positions: np.ndarray  # (N, 3)
    energy: float
    gradient_norm: float  # ||interior forces|| at the returned positions
    iterations: int
    converged: bool
    min_bond_length: float  # degeneracy check: a near-zero value means a collapsed configuration
    non_affine_displacement: np.ndarray  # (N, 3): relaxed - initial_positions, interior rows only meaningful


def relax_interior_positions(
    reference_positions: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    boundary_mask: np.ndarray,
    initial_positions: np.ndarray,
    max_iterations: int = 2000,
    gradient_tolerance: float = 1e-9,
    initial_step: float = 0.5,
) -> RelaxationResult:
    """Steepest descent with Armijo backtracking line search on the
    exact nonlinear `bond_energy`, moving only interior-node positions
    (`~boundary_mask` rows); boundary rows of `initial_positions` are
    treated as fixed and never updated. `initial_positions` is
    typically the affine-sheared guess (boundary already at its
    imposed position, interior nodes starting from the same affine
    field) but is not required to be.
    """
    interior_mask = ~boundary_mask
    positions = initial_positions.copy()
    energy = bond_energy(positions, edges, elasticity)

    step = initial_step
    gradient_norm = float("inf")
    converged = False
    iterations_used = 0

    for iteration in range(1, max_iterations + 1):
        iterations_used = iteration
        forces = bond_forces(positions, edges, elasticity)
        interior_forces = forces[interior_mask]
        gradient_norm = float(np.linalg.norm(interior_forces))
        if gradient_norm < gradient_tolerance:
            converged = True
            break

        direction = np.zeros_like(positions)
        direction[interior_mask] = interior_forces  # forces = -gradient, so this is steepest descent

        trial_step = step
        while True:
            trial_positions = positions + trial_step * direction
            trial_energy = bond_energy(trial_positions, edges, elasticity)
            if trial_energy <= energy - 1e-4 * trial_step * gradient_norm**2 or trial_step < 1e-18:
                break
            trial_step *= 0.5

        positions = trial_positions
        energy = trial_energy
        step = min(trial_step * 1.5, initial_step)

    return RelaxationResult(
        positions=positions,
        energy=float(energy),
        gradient_norm=gradient_norm,
        iterations=iterations_used,
        converged=converged,
        min_bond_length=float(bond_lengths(positions, edges).min()),
        non_affine_displacement=positions - initial_positions,
    )


@dataclass(slots=True)
class ShearRelaxationRow:
    gamma: float
    affine_energy: float
    relaxed_energy: float
    ratio: float  # relaxed_energy / affine_energy
    converged: bool
    iterations: int
    gradient_norm: float
    min_bond_length: float
    max_non_affine_displacement: float  # over interior nodes only


def run_shear_relaxation_study(
    reference_positions: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    boundary_mask: np.ndarray,
    shear_direction: np.ndarray,
    gammas: np.ndarray,
    max_iterations: int = 2000,
    gradient_tolerance: float = 1e-9,
) -> list[ShearRelaxationRow]:
    """For each `gamma`: builds the affine-sheared configuration
    (`reference_positions + gamma * shear_direction`, boundary rows
    fixed there), relaxes the interior nodes against the exact
    nonlinear bond energy, and reports `E_affine(gamma)`,
    `E_relaxed(gamma)`, and their ratio — plus the optimizer
    diagnostics (convergence, iterations, final gradient norm) and a
    degeneracy check (`min_bond_length`) for each run.
    """
    n_nodes = len(reference_positions)
    reshaped_direction = shear_direction.reshape(n_nodes, 3)
    interior_mask = ~boundary_mask

    rows: list[ShearRelaxationRow] = []
    for gamma in gammas:
        affine_positions = reference_positions + gamma * reshaped_direction
        affine_energy = float(bond_energy(affine_positions, edges, elasticity))

        result = relax_interior_positions(
            reference_positions, edges, elasticity, boundary_mask, affine_positions,
            max_iterations=max_iterations, gradient_tolerance=gradient_tolerance,
        )

        ratio = result.energy / affine_energy if affine_energy > 0 else float("nan")
        if np.any(interior_mask):
            max_non_affine = float(
                np.max(np.linalg.norm(result.non_affine_displacement[interior_mask], axis=1))
            )
        else:
            max_non_affine = 0.0

        rows.append(
            ShearRelaxationRow(
                gamma=float(gamma),
                affine_energy=affine_energy,
                relaxed_energy=result.energy,
                ratio=float(ratio),
                converged=result.converged,
                iterations=result.iterations,
                gradient_norm=result.gradient_norm,
                min_bond_length=result.min_bond_length,
                max_non_affine_displacement=max_non_affine,
            )
        )
    return rows


def shear_relaxation_rows_to_table(rows: list[ShearRelaxationRow]) -> list[dict[str, object]]:
    return [
        {
            "gamma": row.gamma,
            "affine_energy": row.affine_energy,
            "relaxed_energy": row.relaxed_energy,
            "ratio": row.ratio,
            "converged": row.converged,
            "iterations": row.iterations,
            "gradient_norm": row.gradient_norm,
            "min_bond_length": row.min_bond_length,
            "max_non_affine_displacement": row.max_non_affine_displacement,
        }
        for row in rows
    ]


def write_shear_relaxation_table_csv(rows: list[ShearRelaxationRow], path: Path) -> None:
    table = shear_relaxation_rows_to_table(rows)
    if not table:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
