"""EXP-0001 implementation, step 9B: absorbing boundary layer.

Per the step-9A closing review: implemented only after the fixed
boundary was validated. Damping is exactly zero in the interior,
grows smoothly through an outer shell, is applied via an exact
exponential-decay half-step (Strang splitting around the conservative
velocity-Verlet step — not an ad hoc post-step velocity rescale), and
the dissipated kinetic energy is computed directly from before/after
velocities at each half-step, not approximated by gamma*|v|^2*dt. A
small sensitivity study (width, gamma_max, exponent) is run rather
than a single "it seems to work" configuration, and free/fixed/
absorbing are compared on identical lattice/injection/dt/duration.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.reflection import outer_shell_energy_fraction
from cosmobox.physics.relaxation import boundary_mask_by_degree
from cosmobox.simulation.absorbing_engine import (
    AbsorbingLatticeEngine,
    AbsorbingLayerConfig,
    SensitivityRow,
    absorbing_layer_damping_coefficients,
    energy_balance_summary,
    run_sensitivity_study,
    sensitivity_rows_to_table,
    write_sensitivity_table_csv,
)
from cosmobox.simulation.boundary_engine import FixedBoundaryLatticeEngine
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


# --- config validation ---


@pytest.mark.parametrize(
    "absorption_radius,gamma_max,exponent",
    [(5.5, 2.0, 2.0), (-1.0, 2.0, 2.0), (3.0, -1.0, 2.0), (3.0, 2.0, 0.0), (3.0, 2.0, -1.0)],
)
def test_config_rejects_invalid_parameters(absorption_radius: float, gamma_max: float, exponent: float) -> None:
    with pytest.raises(ValueError):
        AbsorbingLayerConfig(
            domain_radius=5.5, absorption_radius=absorption_radius, gamma_max=gamma_max, exponent=exponent
        )


# --- damping profile ---


def test_damping_is_exactly_zero_in_the_interior(distances: np.ndarray, matrix: DiamondMatrix) -> None:
    config = AbsorbingLayerConfig(domain_radius=matrix.config.radius, absorption_radius=0.7 * matrix.config.radius, gamma_max=2.0, exponent=2.0)
    gamma = absorbing_layer_damping_coefficients(config, distances)
    assert np.all(gamma[distances <= config.absorption_radius] == 0.0)


def test_damping_grows_and_is_bounded_by_gamma_max_in_the_layer(distances: np.ndarray, matrix: DiamondMatrix) -> None:
    config = AbsorbingLayerConfig(domain_radius=matrix.config.radius, absorption_radius=0.7 * matrix.config.radius, gamma_max=2.0, exponent=2.0)
    gamma = absorbing_layer_damping_coefficients(config, distances)
    in_layer = distances > config.absorption_radius
    assert np.any(in_layer)
    assert np.all(gamma[in_layer] > 0.0)
    assert np.all(gamma <= config.gamma_max + 1e-12)


# --- energy balance closure ---


@pytest.fixture(scope="module")
def mid_history(matrix: DiamondMatrix, elasticity: ElasticityConfig, distances: np.ndarray, initial_state: LatticeState):
    config = AbsorbingLayerConfig(domain_radius=matrix.config.radius, absorption_radius=0.7 * matrix.config.radius, gamma_max=2.0, exponent=2.0)
    gamma = absorbing_layer_damping_coefficients(config, distances)
    engine = AbsorbingLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT), gamma)
    return engine.run(initial_state, steps=_STEPS)


def test_energy_balance_is_closed(mid_history) -> None:
    summary = energy_balance_summary(mid_history)
    assert summary["balance_relative_error"] < 1e-3
    assert 0.0 < summary["absorbed_fraction"] < 1.0
    assert 0.0 < summary["mechanical_remaining_fraction"] < 1.0


def test_absorbed_energy_never_decreases(mid_history) -> None:
    absorbed = [diag.absorbed_energy for _, diag in mid_history]
    assert absorbed == sorted(absorbed)


def test_layer_barely_perturbs_dynamics_before_the_front_arrives(mid_history) -> None:
    # At t=1, the energy-weighted radius is nowhere near the layer
    # (r_abs = 0.7*5.5 = 3.85) — only a tiny high-energy precursor tail
    # can have reached it.
    early_index = 100  # t = 1.0
    summary_like = mid_history[early_index][1]
    assert summary_like.absorbed_energy / mid_history[0][1].total_energy < 1e-3


# --- sensitivity study: width, gamma_max (too weak / mid / too strong), exponent ---


@pytest.fixture(scope="module")
def sensitivity_rows(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, distances: np.ndarray, initial_state: LatticeState
) -> list[SensitivityRow]:
    R = matrix.config.radius
    configs = [
        ("too_weak", AbsorbingLayerConfig(R, 0.7 * R, 0.1, 2.0)),
        ("mid", AbsorbingLayerConfig(R, 0.7 * R, 2.0, 2.0)),
        ("too_strong", AbsorbingLayerConfig(R, 0.7 * R, 50.0, 2.0)),
        ("mid_p1", AbsorbingLayerConfig(R, 0.7 * R, 2.0, 1.0)),
        ("narrower_layer", AbsorbingLayerConfig(R, 0.85 * R, 2.0, 2.0)),
    ]
    return run_sensitivity_study(matrix.edges, elasticity, 1.0, _DT, _STEPS, initial_state, distances, configs)


def test_sensitivity_study_covers_the_requested_minimum(sensitivity_rows: list[SensitivityRow]) -> None:
    labels = {row.label for row in sensitivity_rows}
    assert {"too_weak", "mid", "too_strong", "mid_p1", "narrower_layer"} <= labels
    gamma_maxes = {row.gamma_max for row in sensitivity_rows}
    assert len(gamma_maxes) >= 3
    exponents = {row.exponent for row in sensitivity_rows}
    assert len(exponents) >= 2
    absorption_radii = {row.absorption_radius for row in sensitivity_rows}
    assert len(absorption_radii) >= 2


def test_all_sensitivity_configurations_close_the_energy_balance(sensitivity_rows: list[SensitivityRow]) -> None:
    for row in sensitivity_rows:
        assert row.balance_relative_error < 1e-3


def test_too_weak_and_too_strong_absorb_less_than_the_intermediate_setting(
    sensitivity_rows: list[SensitivityRow],
) -> None:
    # The expected trade-off: too little damping lets energy leave
    # mostly unabsorbed; too much damping creates an impedance mismatch
    # that reflects energy back at the layer's entrance instead of
    # absorbing it. A well-chosen middle value should beat both.
    by_label = {row.label: row for row in sensitivity_rows}
    mid_fraction = by_label["mid"].absorbed_fraction
    assert by_label["too_weak"].absorbed_fraction < mid_fraction
    assert by_label["too_strong"].absorbed_fraction < mid_fraction


def test_sensitivity_table_round_trips_through_csv(sensitivity_rows: list[SensitivityRow], tmp_path) -> None:
    csv_path = tmp_path / "sensitivity.csv"
    write_sensitivity_table_csv(sensitivity_rows, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = sensitivity_rows_to_table(sensitivity_rows)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert read_row["label"] == expected_row["label"]
        assert float(read_row["absorbed_fraction"]) == pytest.approx(expected_row["absorbed_fraction"])


# --- three-way comparison: free / fixed / absorbing ---


def test_absorbing_layer_retains_less_outer_shell_energy_than_free_or_fixed(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, distances: np.ndarray, initial_state: LatticeState,
) -> None:
    outer_radius = 0.7 * matrix.config.radius

    free_engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))
    free_history = free_engine.run(initial_state, steps=_STEPS)

    mask = boundary_mask_by_degree(matrix.degrees)
    fixed_engine = FixedBoundaryLatticeEngine(
        matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT), mask, matrix.reference_positions
    )
    fixed_history = fixed_engine.run(initial_state, steps=_STEPS)

    config = AbsorbingLayerConfig(domain_radius=matrix.config.radius, absorption_radius=outer_radius, gamma_max=2.0, exponent=2.0)
    gamma = absorbing_layer_damping_coefficients(config, distances)
    absorbing_engine = AbsorbingLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT), gamma)
    absorbing_history = absorbing_engine.run(initial_state, steps=_STEPS)

    def mean_outer_fraction(history) -> float:
        fractions = []
        for index in _CHECK_INDICES:
            state, _ = history[index]
            fractions.append(
                outer_shell_energy_fraction(
                    state.positions, state.velocities, matrix.edges, elasticity, 1.0, distances, outer_radius
                )
            )
        return float(np.mean(fractions))

    free_mean = mean_outer_fraction(free_history)
    fixed_mean = mean_outer_fraction(fixed_history)
    absorbing_mean = mean_outer_fraction(absorbing_history)

    # Aggregate comparison, as in step 9A — not point-by-point.
    assert absorbing_mean < fixed_mean
    assert absorbing_mean < free_mean
