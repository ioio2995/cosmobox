"""Time-step (dt) convergence study for EXP-0001.

Runs the *same* lattice, injection, m/k/c and initial state over a
*common physical duration* T for a range of time steps dt = T/N, and
reports, per dt, the maximum relative energy error and the RMS
position/velocity error against the finest-dt run in the series, used
as a numerical reference (docs/05_decisions/0001-moteur-conservatif-minimal.md,
implementation order step 4 and its review).

Comparing runs at a fixed *number of steps* rather than a fixed
*physical duration* would be invalid, since each run would then cover a
different span of simulated time — hence `duration` here, not `steps`.

The reference-state RMS errors are provisional: they are measured
against the finest dt actually run, not an independently finer
resolution or a Richardson extrapolation between three resolutions.
That refinement is left for whenever step 4's results call for it.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.simulation.analysis import analyze_conservation
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState


@dataclass(slots=True)
class ConvergenceRow:
    dt: float
    steps: int
    max_relative_energy_error: float
    max_momentum_drift: float
    rms_position_error: float | None  # None for the reference (finest-dt) row
    rms_velocity_error: float | None


def _rms_error(values: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum((values - reference) ** 2, axis=1))))


def run_dt_convergence_study(
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    initial_state: LatticeState,
    duration: float,
    time_steps: list[float],
) -> list[ConvergenceRow]:
    if len(time_steps) < 2:
        raise ValueError("need at least two time steps to study convergence")

    ordered_dts = sorted(time_steps, reverse=True)
    reference_dt = ordered_dts[-1]

    final_states: dict[float, LatticeState] = {}
    rows_by_dt: dict[float, ConvergenceRow] = {}

    for dt in ordered_dts:
        steps = round(duration / dt)
        if not np.isclose(steps * dt, duration, rtol=0, atol=1e-9):
            raise ValueError(
                f"duration {duration} is not (numerically) an integer multiple of dt {dt}"
            )

        engine = ConservativeLatticeEngine(edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt))
        history = engine.run(initial_state, steps=steps)
        report = analyze_conservation(history)

        final_state, _ = history[-1]
        final_states[dt] = final_state
        rows_by_dt[dt] = ConvergenceRow(
            dt=dt,
            steps=steps,
            max_relative_energy_error=report.max_energy_relative_error,
            max_momentum_drift=report.max_momentum_drift,
            rms_position_error=None,
            rms_velocity_error=None,
        )

    reference_state = final_states[reference_dt]
    for dt, row in rows_by_dt.items():
        if dt == reference_dt:
            continue
        final_state = final_states[dt]
        row.rms_position_error = _rms_error(final_state.positions, reference_state.positions)
        row.rms_velocity_error = _rms_error(final_state.velocities, reference_state.velocities)

    return [rows_by_dt[dt] for dt in ordered_dts]


def rows_to_table(rows: list[ConvergenceRow]) -> list[dict[str, object]]:
    """Plain-dict rows, in the column order shown in
    docs/05_decisions/0001-moteur-conservatif-minimal.md's example table
    — kept separate from ConvergenceRow so the study's result can be
    serialized (CSV, JSON, ...) instead of only existing inside a test.
    """
    return [
        {
            "dt": row.dt,
            "steps": row.steps,
            "max_rel_energy_error": row.max_relative_energy_error,
            "max_momentum_drift": row.max_momentum_drift,
            "rms_position_error": row.rms_position_error,
            "rms_velocity_error": row.rms_velocity_error,
        }
        for row in rows
    ]


def write_convergence_table_csv(rows: list[ConvergenceRow], path: Path) -> None:
    table = rows_to_table(rows)
    if not table:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)


def observed_energy_error_orders(rows: list[ConvergenceRow]) -> list[float]:
    """log2(e(dt_coarse) / e(dt_fine)) for each consecutive pair in `rows`
    (sorted coarsest first) whose step sizes differ by exactly a factor
    of 2. Pairs that are not a clean halving, or where either error is
    zero, are skipped rather than raising — this is a diagnostic, not a
    strict schedule requirement.
    """
    ordered = sorted(rows, key=lambda row: row.dt, reverse=True)
    orders = []
    for coarse, fine in zip(ordered, ordered[1:]):
        if not np.isclose(coarse.dt / fine.dt, 2.0, rtol=0, atol=1e-9):
            continue
        if coarse.max_relative_energy_error <= 0 or fine.max_relative_energy_error <= 0:
            continue
        orders.append(
            float(np.log(coarse.max_relative_energy_error / fine.max_relative_energy_error) / np.log(2))
        )
    return orders
