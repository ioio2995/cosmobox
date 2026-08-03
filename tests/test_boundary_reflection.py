"""EXP-0001 implementation, step 9A: fixed boundary and free-vs-fixed
reflection comparison.

Per the step-8 closing review: the reaction force is computed
explicitly (not by resetting positions after the fact), the momentum
balance dP_mobile == J_reaction is checked directly, and free vs fixed
are compared on the same lattice/injection/amplitude/dt/duration using
two independent boundary-mask definitions (from step 7B-2).
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import propagation_samples
from cosmobox.physics.reflection import (
    BoundaryComparisonRow,
    boundary_comparison_rows_to_table,
    boundary_comparison_table,
    outer_shell_energy_fraction,
    peak_energy_weighted_radius,
    write_boundary_comparison_table_csv,
)
from cosmobox.physics.relaxation import boundary_mask_by_degree, boundary_mask_by_radius
from cosmobox.simulation.boundary_engine import FixedBoundaryLatticeEngine, momentum_balance_residual
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState
from cosmobox.simulation.injection import apply_injection, compensated_pair_injection

_DT = 0.01
_STEPS = 8000  # T = 80
_SPEED = 0.3
_CHECK_INDICES = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def distances(matrix: DiamondMatrix) -> np.ndarray:
    return np.linalg.norm(matrix.reference_positions, axis=1)


@pytest.fixture(scope="module")
def initial_state(matrix: DiamondMatrix) -> LatticeState:
    injection = compensated_pair_injection(matrix, speed=_SPEED)
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    return LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities)


@pytest.fixture(scope="module")
def free_history(matrix: DiamondMatrix, elasticity: ElasticityConfig, initial_state: LatticeState):
    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))
    return engine.run(initial_state, steps=_STEPS)


@pytest.fixture(scope="module")
def free_samples(free_history, distances: np.ndarray, matrix: DiamondMatrix, elasticity: ElasticityConfig):
    return propagation_samples(free_history, distances, matrix.edges, elasticity, node_mass=1.0, threshold_fraction=0.01)


@pytest.fixture(
    scope="module",
    params=[("degree", None), ("radius_0.85", 0.85)],
    ids=["degree", "radius"],
)
def boundary(request: pytest.FixtureRequest, matrix: DiamondMatrix) -> tuple[str, np.ndarray]:
    name, alpha = request.param
    if alpha is None:
        return name, boundary_mask_by_degree(matrix.degrees)
    return name, boundary_mask_by_radius(matrix.reference_positions, matrix.config.radius, alpha)


@pytest.fixture(scope="module")
def fixed_history(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, initial_state: LatticeState,
    boundary: tuple[str, np.ndarray],
):
    _, mask = boundary
    engine = FixedBoundaryLatticeEngine(
        matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT), mask, matrix.reference_positions
    )
    return engine.run(initial_state, steps=_STEPS)


@pytest.fixture(scope="module")
def fixed_samples(fixed_history, distances: np.ndarray, matrix: DiamondMatrix, elasticity: ElasticityConfig):
    return propagation_samples(fixed_history, distances, matrix.edges, elasticity, node_mass=1.0, threshold_fraction=0.01)


# --- boundary is exactly held ---


def test_boundary_nodes_stay_exactly_at_rest_throughout(
    matrix: DiamondMatrix, fixed_history, boundary: tuple[str, np.ndarray]
) -> None:
    _, mask = boundary
    for state, _ in fixed_history[::500]:
        assert np.allclose(state.positions[mask], matrix.reference_positions[mask], atol=1e-12)
        assert np.allclose(state.velocities[mask], 0.0, atol=1e-12)


# --- momentum bookkeeping ---


def test_free_boundary_momentum_is_conserved(free_history) -> None:
    p0 = free_history[0][1].momentum
    pf = free_history[-1][1].momentum
    assert np.linalg.norm(pf - p0) < 1e-9


def test_fixed_boundary_mobile_momentum_is_not_conserved(fixed_history) -> None:
    # Expected, not a bug: the rigid boundary absorbs momentum via its
    # reaction force.
    p0 = fixed_history[0][1].momentum
    pf = fixed_history[-1][1].momentum
    assert np.linalg.norm(pf - p0) > 1e-3


def test_momentum_balance_residual_is_near_zero(fixed_history) -> None:
    residual = momentum_balance_residual(fixed_history, _DT)
    assert residual < 1e-9


# --- energy bookkeeping ---


def test_fixed_boundary_energy_stays_bounded(fixed_history) -> None:
    e0 = fixed_history[0][1].total_energy
    energies = [diag.total_energy for _, diag in fixed_history]
    max_relative_drift = max(abs(e - e0) for e in energies) / e0
    assert max_relative_drift < 1e-3


# --- free vs fixed: energy retained near the boundary ---


def test_fixed_boundary_retains_less_energy_near_the_edge_on_average(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, distances: np.ndarray,
    free_history, fixed_history,
) -> None:
    outer_radius = 0.7 * matrix.config.radius
    free_fractions = []
    fixed_fractions = []
    for index in _CHECK_INDICES:
        free_state, _ = free_history[index]
        fixed_state, _ = fixed_history[index]
        free_fractions.append(
            outer_shell_energy_fraction(
                free_state.positions, free_state.velocities, matrix.edges, elasticity, 1.0, distances, outer_radius
            )
        )
        fixed_fractions.append(
            outer_shell_energy_fraction(
                fixed_state.positions, fixed_state.velocities, matrix.edges, elasticity, 1.0, distances, outer_radius
            )
        )

    # A robust, aggregate comparison — not asserted point-by-point,
    # since individual sampled times can be dominated by transient
    # multi-reflection interference (observed for the radius-based mask
    # at a single check time), which is a real feature of the dynamics,
    # not noise to be papered over by cherry-picking check times.
    assert np.mean(fixed_fractions) < 0.8 * np.mean(free_fractions)


# --- sanity on the raw peak-radius stat ---


def test_peak_energy_weighted_radius_is_well_formed(free_samples, fixed_samples) -> None:
    for samples in (free_samples, fixed_samples):
        peak_time, peak_value = peak_energy_weighted_radius(samples)
        assert 0.0 <= peak_time <= _STEPS * _DT
        assert peak_value > 0.0
        assert np.isfinite(peak_value)


# --- serialization ---


def test_boundary_comparison_table_round_trips_through_csv(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, distances: np.ndarray,
    free_history, fixed_history, free_samples, fixed_samples, tmp_path,
) -> None:
    outer_radius = 0.7 * matrix.config.radius
    rows = boundary_comparison_table(
        free_history, fixed_history, free_samples, fixed_samples,
        matrix.edges, elasticity, 1.0, distances, outer_radius, _CHECK_INDICES,
    )
    assert len(rows) == len(_CHECK_INDICES)
    assert all(isinstance(row, BoundaryComparisonRow) for row in rows)

    csv_path = tmp_path / "boundary_comparison.csv"
    write_boundary_comparison_table_csv(rows, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = boundary_comparison_rows_to_table(rows)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert float(read_row["time"]) == pytest.approx(expected_row["time"])
        assert float(read_row["fixed_outer_shell_fraction"]) == pytest.approx(
            expected_row["fixed_outer_shell_fraction"]
        )
