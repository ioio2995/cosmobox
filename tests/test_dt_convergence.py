"""EXP-0001 implementation, step 4: time-step (dt) convergence study.

Per docs/05_decisions/0001-moteur-conservatif-minimal.md and the
step-3 review: verify the *observed order of convergence*, not just
"error improves as dt shrinks". Same lattice, injection, m/k/c and
initial state across all dt; physical duration T held fixed by scaling
the number of steps (N = T / dt) — comparing runs at a fixed step count
would silently compare different physical durations.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.simulation.convergence import (
    ConvergenceRow,
    observed_energy_error_orders,
    rows_to_table,
    run_dt_convergence_study,
    write_convergence_table_csv,
)
from cosmobox.simulation.engine import LatticeState
from cosmobox.simulation.injection import apply_injection, compensated_pair_injection

_DURATION = 2.0
_TIME_STEPS = [0.04, 0.02, 0.01, 0.005]


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def initial_state(matrix: DiamondMatrix) -> LatticeState:
    injection = compensated_pair_injection(matrix, speed=0.3)
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    return LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities)


@pytest.fixture(scope="module")
def initial_state_snapshot(initial_state: LatticeState) -> LatticeState:
    # Captured synchronously, before any other module-scoped fixture
    # (e.g. convergence_rows) gets a chance to consume `initial_state` —
    # a true pre-study snapshot, not just a same-value re-read after the
    # fact, so an accidental in-place mutation inside the study would
    # actually be caught here.
    return LatticeState(
        positions=initial_state.positions.copy(),
        velocities=initial_state.velocities.copy(),
    )


@pytest.fixture(scope="module")
def convergence_rows(
    matrix: DiamondMatrix,
    elasticity: ElasticityConfig,
    initial_state: LatticeState,
    initial_state_snapshot: LatticeState,
) -> list[ConvergenceRow]:
    return run_dt_convergence_study(
        matrix.edges, elasticity, node_mass=1.0, initial_state=initial_state,
        duration=_DURATION, time_steps=_TIME_STEPS,
    )


def test_every_run_covers_the_same_physical_duration(convergence_rows: list[ConvergenceRow]) -> None:
    for row in convergence_rows:
        assert row.steps * row.dt == pytest.approx(_DURATION)


def test_initial_state_is_untouched_by_the_study(
    initial_state: LatticeState,
    initial_state_snapshot: LatticeState,
    convergence_rows: list[ConvergenceRow],  # ensure the study has actually run first
) -> None:
    # run_dt_convergence_study must not mutate the initial_state it was
    # handed — every dt run has to start from the exact same bit-for-bit
    # condition, not a state left over from a previous run.
    assert np.array_equal(initial_state.positions, initial_state_snapshot.positions)
    assert np.array_equal(initial_state.velocities, initial_state_snapshot.velocities)


def test_momentum_is_conserved_at_every_resolution(convergence_rows: list[ConvergenceRow]) -> None:
    for row in convergence_rows:
        assert row.max_momentum_drift < 1e-9


def test_max_energy_error_decreases_monotonically_as_dt_shrinks(
    convergence_rows: list[ConvergenceRow],
) -> None:
    ordered = sorted(convergence_rows, key=lambda row: row.dt, reverse=True)
    errors = [row.max_relative_energy_error for row in ordered]
    assert errors == sorted(errors, reverse=True)
    assert errors[0] > errors[-1]


def test_trajectory_error_decreases_as_dt_shrinks(convergence_rows: list[ConvergenceRow]) -> None:
    # Excludes the reference row (finest dt), which has no error against
    # itself by definition.
    non_reference = sorted(
        (row for row in convergence_rows if row.rms_position_error is not None),
        key=lambda row: row.dt,
        reverse=True,
    )
    assert len(non_reference) == len(_TIME_STEPS) - 1

    position_errors = [row.rms_position_error for row in non_reference]
    velocity_errors = [row.rms_velocity_error for row in non_reference]
    assert position_errors == sorted(position_errors, reverse=True)
    assert velocity_errors == sorted(velocity_errors, reverse=True)


def test_observed_order_is_close_to_second_order_on_finer_steps(
    convergence_rows: list[ConvergenceRow],
) -> None:
    orders = observed_energy_error_orders(convergence_rows)
    assert len(orders) == len(_TIME_STEPS) - 1  # all three consecutive halvings

    # A reasonable band around 2, not an artificial exact match — the
    # coarsest pair is allowed the most slack, the two finest pairs
    # (closer to the asymptotic regime) are held to a tighter band.
    for order in orders:
        assert 1.5 < order < 2.5
    for order in orders[-2:]:
        assert 1.8 < order < 2.2


def test_convergence_table_round_trips_through_csv(
    convergence_rows: list[ConvergenceRow], tmp_path
) -> None:
    csv_path = tmp_path / "dt_convergence.csv"
    write_convergence_table_csv(convergence_rows, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = rows_to_table(convergence_rows)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert float(read_row["dt"]) == pytest.approx(expected_row["dt"])
        assert int(read_row["steps"]) == expected_row["steps"]
        assert float(read_row["max_rel_energy_error"]) == pytest.approx(
            expected_row["max_rel_energy_error"]
        )
        if expected_row["rms_position_error"] is None:
            assert read_row["rms_position_error"] == ""
        else:
            assert float(read_row["rms_position_error"]) == pytest.approx(
                expected_row["rms_position_error"]
            )
