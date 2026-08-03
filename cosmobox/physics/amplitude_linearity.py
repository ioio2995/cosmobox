"""Amplitude-linearity study for the longitudinal (bond-aligned)
propagation used in steps 3-6, per the step-7 closing review.

Per that review, the quadratic-vs-quartic separation is already
covered by step 7B-3 (transverse impulses vs the kernel) and should
not be repeated here. This module targets exactly the four checks
requested for the *longitudinal* injection instead:

1. injected energy proportional to amplitude squared (checked, not
   assumed — though it is guaranteed by construction here, since
   compensated_pair_injection's two opposite impulses of magnitude
   `speed` give `E0 = node_mass * speed**2` exactly);
2. the propagation slope's (in)dependence on amplitude;
3. superposition of energy-normalized spatial profiles across
   amplitudes;
4. measurable emergence of nonlinearity as amplitude grows, via the
   normalized profiles' deviation from a small-amplitude reference.

All of this is reported as measured over the specific amplitudes,
duration and lattice tested — not claimed as a universal law.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import (
    LinearFit,
    PropagationSample,
    earliest_boundary_influence_time,
    estimate_apparent_velocity,
    node_energy_density,
    propagation_samples,
    radial_energy_profile,
)
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState
from cosmobox.simulation.injection import apply_injection, compensated_pair_injection


@dataclass(slots=True)
class AmplitudeRun:
    speed: float
    injected_energy: float
    samples: list[PropagationSample]
    velocity_fits: dict[str, LinearFit]
    boundary_influence_time: float | None
    normalized_radial_profile: np.ndarray  # radial_energy_profile(...) / injected_energy, at profile_step_index


def run_amplitude_series(
    matrix,
    elasticity: ElasticityConfig,
    node_mass: float,
    dt: float,
    steps: int,
    speeds: list[float],
    threshold_fraction: float,
    caution_fraction: float,
    profile_bin_edges: np.ndarray,
    profile_step_index: int,
) -> list[AmplitudeRun]:
    distances = np.linalg.norm(matrix.reference_positions, axis=1)

    runs = []
    for speed in speeds:
        injection = compensated_pair_injection(matrix, speed=speed)
        velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
        engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt))
        history = engine.run(
            LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities), steps=steps
        )

        injected_energy = history[0][1].total_energy
        samples = propagation_samples(
            history, distances, matrix.edges, elasticity, node_mass, threshold_fraction
        )
        boundary_time = earliest_boundary_influence_time(samples, matrix.config.radius, caution_fraction)
        fits = estimate_apparent_velocity(samples, boundary_time)

        profile_state, _ = history[profile_step_index]
        density = node_energy_density(
            profile_state.positions, profile_state.velocities, matrix.edges, elasticity, node_mass
        )
        profile = radial_energy_profile(distances, density, profile_bin_edges)
        normalized_profile = profile / injected_energy

        runs.append(
            AmplitudeRun(
                speed=speed,
                injected_energy=injected_energy,
                samples=samples,
                velocity_fits=fits,
                boundary_influence_time=boundary_time,
                normalized_radial_profile=normalized_profile,
            )
        )
    return runs


def injected_energy_scaling_order(runs: list[AmplitudeRun]) -> float:
    """log-log regression slope of `injected_energy` against `speed`
    across all runs — expected near 2 (quadratic), checked rather than
    assumed even though it follows from the injection's construction.
    """
    log_speeds = np.log([run.speed for run in runs])
    log_energies = np.log([run.injected_energy for run in runs])
    slope, _ = np.polyfit(log_speeds, log_energies, 1)
    return float(slope)


def apparent_velocity_relative_spread(runs: list[AmplitudeRun], fit_key: str) -> float:
    """`(max - min) / mean` of the given fit's slope across all runs —
    0 would mean perfectly amplitude-independent propagation speed;
    growing subsets (e.g. excluding the largest amplitudes) can be
    passed in to separate a "linear regime" spread from the full range.
    """
    slopes = np.array([run.velocity_fits[fit_key].slope for run in runs])
    return float((slopes.max() - slopes.min()) / slopes.mean())


def normalized_profile_deviation(runs: list[AmplitudeRun], reference_index: int = 0) -> list[float]:
    """RMS deviation of each run's `normalized_radial_profile` from the
    profile of `runs[reference_index]` (typically the smallest
    amplitude) — 0 for the reference itself, growing values indicate
    departure from linear-regime superposition.
    """
    reference = runs[reference_index].normalized_radial_profile
    return [float(np.sqrt(np.mean((run.normalized_radial_profile - reference) ** 2))) for run in runs]


def amplitude_runs_to_table(runs: list[AmplitudeRun]) -> list[dict[str, object]]:
    deviations = normalized_profile_deviation(runs)
    return [
        {
            "speed": run.speed,
            "injected_energy": run.injected_energy,
            "boundary_influence_time": run.boundary_influence_time,
            "slope_threshold_front": run.velocity_fits["threshold_front"].slope,
            "r2_threshold_front": run.velocity_fits["threshold_front"].r_squared,
            "slope_energy_weighted_radius": run.velocity_fits["energy_weighted_radius"].slope,
            "r2_energy_weighted_radius": run.velocity_fits["energy_weighted_radius"].r_squared,
            "normalized_profile_rms_deviation": deviation,
        }
        for run, deviation in zip(runs, deviations)
    ]


def write_amplitude_table_csv(runs: list[AmplitudeRun], path: Path) -> None:
    table = amplitude_runs_to_table(runs)
    if not table:
        raise ValueError("no runs to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
