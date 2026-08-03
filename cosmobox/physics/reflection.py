"""Free-vs-fixed-boundary reflection analysis for EXP-0001 step 9A.

Compares the *same* lattice, injection, amplitude, dt and duration run
once with a free boundary
(cosmobox.simulation.engine.ConservativeLatticeEngine) and once with a
fixed boundary
(cosmobox.simulation.boundary_engine.FixedBoundaryLatticeEngine), using
the existing propagation diagnostics (cosmobox.physics.propagation) on
both — so reflection can be characterized by an actual before/after
comparison, rather than inferred from the free-boundary caution-zone
proxy (`earliest_boundary_influence_time`) used in earlier steps, which
only ever claimed to mark contact, never an observed return signal.

Note on what "free" means here: both configurations are a *finite*
lattice, so neither is an infinite, non-reflecting medium — a free
edge and a fixed edge are two different classical boundary conditions,
both of which generally reflect (just with different phase/character,
as for a free vs. fixed end of a string), not "reflects" vs.
"doesn't". The comparison below is between the two, not against an
idealized absorbing case (that is step 9B).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import PropagationSample, node_energy_density
from cosmobox.simulation.boundary_engine import FixedBoundaryStepDiagnostics
from cosmobox.simulation.engine import LatticeState, StepDiagnostics


def peak_energy_weighted_radius(samples: list[PropagationSample]) -> tuple[float, float]:
    """`(time, value)` of the maximum `energy_weighted_radius` reached
    over the run.
    """
    values = [sample.energy_weighted_radius for sample in samples]
    peak_index = int(np.argmax(values))
    return samples[peak_index].time, values[peak_index]


def _energy_fraction_where(density: np.ndarray, mask: np.ndarray) -> float:
    total = float(density.sum())
    if total <= 0:
        return 0.0
    return float(density[mask].sum() / total)


def inner_shell_energy_fraction(
    positions: np.ndarray,
    velocities: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    distances: np.ndarray,
    inner_radius: float,
) -> float:
    """Fraction of the total energy currently held by nodes within
    `inner_radius` of the injection center.
    """
    density = node_energy_density(positions, velocities, edges, elasticity, node_mass)
    return _energy_fraction_where(density, distances < inner_radius)


def outer_shell_energy_fraction(
    positions: np.ndarray,
    velocities: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    distances: np.ndarray,
    outer_radius: float,
) -> float:
    """Fraction of the total energy currently held by nodes at or
    beyond `outer_radius` of the injection center — a direct measure
    of how much energy is sitting near the boundary at a given time,
    used to compare how efficiently the free vs. fixed boundary
    condition sends energy back toward the interior.
    """
    density = node_energy_density(positions, velocities, edges, elasticity, node_mass)
    return _energy_fraction_where(density, distances >= outer_radius)


@dataclass(slots=True)
class BoundaryComparisonRow:
    time: float
    free_energy_weighted_radius: float
    fixed_energy_weighted_radius: float
    free_outer_shell_fraction: float
    fixed_outer_shell_fraction: float


def boundary_comparison_table(
    free_history: list[tuple[LatticeState, StepDiagnostics]],
    fixed_history: list[tuple[LatticeState, FixedBoundaryStepDiagnostics]],
    free_samples: list[PropagationSample],
    fixed_samples: list[PropagationSample],
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    distances: np.ndarray,
    outer_radius: float,
    step_indices: list[int],
) -> list[BoundaryComparisonRow]:
    """One row per `step_indices` entry, pairing the free and fixed
    runs at the same physical time (both histories must share the same
    dt and therefore the same step-to-time mapping).
    """
    rows = []
    for index in step_indices:
        free_state, _ = free_history[index]
        fixed_state, _ = fixed_history[index]
        free_outer = outer_shell_energy_fraction(
            free_state.positions, free_state.velocities, edges, elasticity, node_mass, distances, outer_radius
        )
        fixed_outer = outer_shell_energy_fraction(
            fixed_state.positions, fixed_state.velocities, edges, elasticity, node_mass, distances, outer_radius
        )
        rows.append(
            BoundaryComparisonRow(
                time=free_samples[index].time,
                free_energy_weighted_radius=free_samples[index].energy_weighted_radius,
                fixed_energy_weighted_radius=fixed_samples[index].energy_weighted_radius,
                free_outer_shell_fraction=free_outer,
                fixed_outer_shell_fraction=fixed_outer,
            )
        )
    return rows


def boundary_comparison_rows_to_table(rows: list[BoundaryComparisonRow]) -> list[dict[str, object]]:
    return [
        {
            "time": row.time,
            "free_energy_weighted_radius": row.free_energy_weighted_radius,
            "fixed_energy_weighted_radius": row.fixed_energy_weighted_radius,
            "free_outer_shell_fraction": row.free_outer_shell_fraction,
            "fixed_outer_shell_fraction": row.fixed_outer_shell_fraction,
        }
        for row in rows
    ]


def write_boundary_comparison_table_csv(rows: list[BoundaryComparisonRow], path: Path) -> None:
    table = boundary_comparison_rows_to_table(rows)
    if not table:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
