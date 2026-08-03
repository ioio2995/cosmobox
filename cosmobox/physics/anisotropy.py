"""Source-orientation dependence study for EXP-0001 step 6.

Replays the free-boundary compensated-pair injection (step 5) along
each of the central node's tetrahedral bond directions, at identical
impulse magnitude and therefore identical injected energy, and reports
raw per-direction measurements plus an energy tensor summarizing the
propagated packet's shape without relying on an arbitrary shell/cone
binning.

Per the step-5 review, this module deliberately separates two
questions instead of conflating them:

- **covariance by symmetry**: does a lattice rotation mapping direction
  A to direction B also map the A-injection's simulated trajectory onto
  the B-injection's trajectory? `symmetry_trajectory_max_error` checks
  this *exactly* against the verified lattice symmetries in
  cosmobox.core.symmetry — it is a correctness property of the
  engine+geometry (if it failed, that would indicate a bug), not a
  physical hypothesis.
- **effective isotropy**: do the raw propagation measurements actually
  come out the same across directions at this scale? This is reported
  as measured (`run_directional_study`'s table), never assumed, and no
  conclusion about isotropy at any scale should be drawn from this
  module alone.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import (
    LinearFit,
    PropagationSample,
    earliest_boundary_influence_time,
    estimate_apparent_velocity,
    node_energy_density,
    propagation_samples,
)
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState, StepDiagnostics
from cosmobox.simulation.injection import apply_injection, tetrahedral_directional_injections


def energy_tensor(reference_positions: np.ndarray, center: np.ndarray, energy_density: np.ndarray) -> np.ndarray:
    """The energy-weighted second-moment (quadrupole-like) tensor
    `M_ab = (1/E) * sum_i E_i * offset_i_a * offset_i_b`, `offset_i =
    reference_positions[i] - center`. Symmetric and positive
    semi-definite by construction, so its eigenvalues quantify the
    packet's spatial extent along its principal axes without depending
    on an arbitrary shell or cone partition.

    This is a second moment about the fixed injection `center`, not a
    covariance matrix about the energy-weighted barycenter (that mean
    is not subtracted here) — do not call it a covariance matrix
    without recentering first.
    """
    total = float(energy_density.sum())
    if total <= 0:
        return np.zeros((3, 3))
    offsets = reference_positions - center
    return np.einsum("i,ia,ib->ab", energy_density, offsets, offsets) / total


def directional_energy(
    reference_positions: np.ndarray,
    center: np.ndarray,
    energy_density: np.ndarray,
    direction: np.ndarray,
    cone_half_angle_deg: float,
) -> float:
    """Energy carried by nodes within a cone of half-angle
    `cone_half_angle_deg`, apex at `center`, axis along `direction`.
    A node exactly at `center` (zero offset) has an undefined angle and
    is counted in *every* cone regardless of angle, rather than
    excluded from all of them — otherwise a cone_half_angle_deg=180
    ("all directions") would not recover the full total energy
    whenever the injection center itself carries energy.

    Cones for different directions can overlap, and the center node is
    always included in all of them: calling this for several
    directions does *not* produce an additive partition of the total
    energy (the sum over several cones' results can exceed
    `total_energy`). For a true angular partition, assign each node to
    exactly one sector and handle the center node's contribution
    explicitly instead of calling this function per sector.
    """
    offsets = reference_positions - center
    norms = np.linalg.norm(offsets, axis=1)
    unit_direction = direction / np.linalg.norm(direction)

    cos_angle = np.full(len(reference_positions), np.inf)
    valid = norms > 1e-12
    # Clip to [-1, 1]: floating-point rounding in the division above can
    # otherwise push an exactly-opposite node's cosine a hair below -1
    # (observed: -1.0000000000000002), which would wrongly exclude it
    # from a 180-degree ("all directions") cone.
    cos_angle[valid] = np.clip((offsets[valid] @ unit_direction) / norms[valid], -1.0, 1.0)

    cos_threshold = np.cos(np.radians(cone_half_angle_deg))
    within_cone = cos_angle >= cos_threshold
    return float(energy_density[within_cone].sum())


@dataclass(slots=True)
class DirectionalRun:
    direction: np.ndarray
    injected_energy: float
    samples: list[PropagationSample]
    velocity_fits: dict[str, LinearFit]
    boundary_influence_time: float | None
    final_tensor: np.ndarray


def run_directional_study(
    matrix: DiamondMatrix,
    elasticity: ElasticityConfig,
    node_mass: float,
    dt: float,
    steps: int,
    speed: float,
    threshold_fraction: float,
    caution_fraction: float,
) -> list[DirectionalRun]:
    injections = tetrahedral_directional_injections(matrix, speed)
    distances = np.linalg.norm(matrix.reference_positions, axis=1)
    center = matrix.reference_positions[injections[0].node_a]

    runs = []
    for injection in injections:
        velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
        initial_state = LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities)
        engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt))
        history = engine.run(initial_state, steps=steps)

        samples = propagation_samples(
            history, distances, matrix.edges, elasticity, node_mass, threshold_fraction
        )
        boundary_time = earliest_boundary_influence_time(samples, matrix.config.radius, caution_fraction)
        fits = estimate_apparent_velocity(samples, boundary_time)

        final_state, _ = history[-1]
        final_density = node_energy_density(
            final_state.positions, final_state.velocities, matrix.edges, elasticity, node_mass
        )
        final_tensor = energy_tensor(matrix.reference_positions, center, final_density)

        runs.append(
            DirectionalRun(
                direction=injection.direction,
                injected_energy=history[0][1].total_energy,
                samples=samples,
                velocity_fits=fits,
                boundary_influence_time=boundary_time,
                final_tensor=final_tensor,
            )
        )
    return runs


def directional_runs_to_table(runs: list[DirectionalRun]) -> list[dict[str, object]]:
    rows = []
    for run in runs:
        eigenvalues = np.linalg.eigvalsh(run.final_tensor)
        rows.append(
            {
                "direction_x": float(run.direction[0]),
                "direction_y": float(run.direction[1]),
                "direction_z": float(run.direction[2]),
                "injected_energy": run.injected_energy,
                "boundary_influence_time": run.boundary_influence_time,
                "slope_threshold_front": run.velocity_fits["threshold_front"].slope,
                "r2_threshold_front": run.velocity_fits["threshold_front"].r_squared,
                "slope_energy_weighted_radius": run.velocity_fits["energy_weighted_radius"].slope,
                "r2_energy_weighted_radius": run.velocity_fits["energy_weighted_radius"].r_squared,
                "final_energy_weighted_radius": run.samples[-1].energy_weighted_radius,
                "final_energy_weighted_spread": run.samples[-1].energy_weighted_spread,
                "tensor_eigenvalue_min": float(eigenvalues[0]),
                "tensor_eigenvalue_mid": float(eigenvalues[1]),
                "tensor_eigenvalue_max": float(eigenvalues[2]),
            }
        )
    return rows


def write_directional_table_csv(runs: list[DirectionalRun], path: Path) -> None:
    table = directional_runs_to_table(runs)
    if not table:
        raise ValueError("no runs to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)


@dataclass(slots=True)
class SymmetryTrajectoryError:
    max_position_error: float
    max_velocity_error: float


def symmetry_trajectory_max_error(
    source_history: list[tuple[LatticeState, StepDiagnostics]],
    target_history: list[tuple[LatticeState, StepDiagnostics]],
    transform: np.ndarray,
    permutation: np.ndarray,
) -> SymmetryTrajectoryError:
    """Maximum, over every step, of the per-node discrepancy between
    `target_history` and the geometric image of `source_history` under
    the lattice symmetry (`transform`, `permutation`) from
    cosmobox.core.symmetry — for *both* positions and velocities, since
    covariance of the full state requires both:

    `target_positions[permutation[i]] == transform @ source_positions[i]`
    `target_velocities[permutation[i]] == transform @ source_velocities[i]`

    at every step (not merely `target_positions[permutation[i]] ==
    source_positions[permutation[i]]`, which would silently pass for
    any permutation without checking the rotation was actually
    applied). Both components ~0 (floating-point noise) if the engine
    is exactly covariant under this symmetry; a real, non-noise-level
    value would indicate a bug in the engine or geometry, not a
    physical effect.
    """
    if len(source_history) != len(target_history):
        raise ValueError("source and target histories must have the same length")

    max_position_error = 0.0
    max_velocity_error = 0.0
    for (source_state, _), (target_state, _) in zip(source_history, target_history):
        rotated_positions = source_state.positions @ transform.T
        predicted_positions = np.empty_like(rotated_positions)
        predicted_positions[permutation] = rotated_positions
        position_error = float(np.max(np.abs(predicted_positions - target_state.positions)))
        max_position_error = max(max_position_error, position_error)

        rotated_velocities = source_state.velocities @ transform.T
        predicted_velocities = np.empty_like(rotated_velocities)
        predicted_velocities[permutation] = rotated_velocities
        velocity_error = float(np.max(np.abs(predicted_velocities - target_state.velocities)))
        max_velocity_error = max(max_velocity_error, velocity_error)

    return SymmetryTrajectoryError(max_position_error=max_position_error, max_velocity_error=max_velocity_error)
