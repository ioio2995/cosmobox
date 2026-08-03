"""EXP-0001 implementation, step 5: propagation characterization of the
existing compensated-pair injection, free boundary only.

Per the step-4 review: this step is scoped to raw, serializable
measurements only (front position, apparent velocity, radial width,
spatial energy distribution, earliest boundary influence time — not a
reflection detector, see propagation.earliest_boundary_influence_time).
No conclusion about propagation speed, isotropy, or particle-like
behavior is drawn here — the injection is a single oriented dipole, not
an isotropic source (see cosmobox/physics/propagation.py docstring);
separating source-orientation effects from network effects is step 6.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import (
    LinearFit,
    PropagationSample,
    earliest_boundary_influence_time,
    estimate_apparent_velocity,
    node_energy_density,
    propagation_samples,
    radial_energy_profile,
    samples_to_table,
    write_propagation_table_csv,
)
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState
from cosmobox.simulation.injection import apply_injection, compensated_pair_injection

_DT = 0.01
_STEPS = 6000  # T = 60, long enough to reach the domain boundary (radius 8.2)
_THRESHOLD_FRACTION = 0.01
_CAUTION_FRACTION = 0.9


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=8.2, cell_range=7))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def distances(matrix: DiamondMatrix) -> np.ndarray:
    return np.linalg.norm(matrix.reference_positions, axis=1)


@pytest.fixture(scope="module")
def history(matrix: DiamondMatrix, elasticity: ElasticityConfig):
    injection = compensated_pair_injection(matrix, speed=0.3)
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    initial_state = LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities)
    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))
    return engine.run(initial_state, steps=_STEPS)


@pytest.fixture(scope="module")
def samples(
    history, distances: np.ndarray, matrix: DiamondMatrix, elasticity: ElasticityConfig
) -> list[PropagationSample]:
    return propagation_samples(
        history, distances, matrix.edges, elasticity, node_mass=1.0, threshold_fraction=_THRESHOLD_FRACTION
    )


@pytest.fixture(scope="module")
def boundary_influence_time(samples: list[PropagationSample], matrix: DiamondMatrix) -> float | None:
    return earliest_boundary_influence_time(samples, matrix.config.radius, _CAUTION_FRACTION)


def test_node_energy_density_sums_to_total_energy(history, matrix: DiamondMatrix, elasticity: ElasticityConfig) -> None:
    for state, diag in history[::500]:  # sampled for speed
        density = node_energy_density(state.positions, state.velocities, matrix.edges, elasticity, node_mass=1.0)
        assert density.sum() == pytest.approx(diag.total_energy, abs=1e-9)


def test_radial_profile_covers_all_the_energy(
    history, distances: np.ndarray, matrix: DiamondMatrix, elasticity: ElasticityConfig
) -> None:
    bin_edges = np.arange(0.0, matrix.config.radius + 1.0, 1.0)
    for state, diag in history[::1000]:
        density = node_energy_density(state.positions, state.velocities, matrix.edges, elasticity, node_mass=1.0)
        profile = radial_energy_profile(distances, density, bin_edges)
        assert profile.sum() == pytest.approx(diag.total_energy, abs=1e-9)


def test_radial_profile_rejects_bin_edges_that_do_not_cover_the_farthest_node(
    distances: np.ndarray,
) -> None:
    short_bin_edges = np.arange(0.0, distances.max(), 1.0)  # deliberately too short
    energy_density = np.ones_like(distances)
    with pytest.raises(ValueError, match="must exceed the maximum node"):
        radial_energy_profile(distances, energy_density, short_bin_edges)


def test_boundary_caution_zone_is_reached_within_the_run(
    boundary_influence_time: float | None,
) -> None:
    # This only proves the front *touches* the 90%-radius caution zone
    # within the run — not that a reflection has come back and disturbed
    # the measured region. See earliest_boundary_influence_time's
    # docstring for why those are different claims.
    assert boundary_influence_time is not None
    assert 0.0 < boundary_influence_time < _STEPS * _DT


def test_energy_spreads_outward_before_the_caution_zone(
    samples: list[PropagationSample], boundary_influence_time: float | None
) -> None:
    pre_caution = [s for s in samples if s.time < boundary_influence_time]
    assert len(pre_caution) > 10
    assert pre_caution[-1].energy_weighted_radius > pre_caution[0].energy_weighted_radius


def test_energy_weighted_spread_is_finite_and_nonnegative(samples: list[PropagationSample]) -> None:
    spreads = np.array([s.energy_weighted_spread for s in samples])
    assert np.all(np.isfinite(spreads))
    assert np.all(spreads >= 0.0)


def test_apparent_velocity_estimates_are_well_formed(
    samples: list[PropagationSample], boundary_influence_time: float | None
) -> None:
    fits = estimate_apparent_velocity(samples, boundary_influence_time)
    assert set(fits) == {"threshold_front", "energy_weighted_radius"}

    for fit in fits.values():
        assert isinstance(fit, LinearFit)
        assert np.isfinite(fit.slope)
        assert 0.0 <= fit.r_squared <= 1.0 + 1e-9
        assert fit.slope > 0.0  # net outward expansion before the caution zone

    # The energy-weighted radius is a smoother signal than the raw
    # threshold front (which crosses in/out at single-node granularity)
    # and is expected to fit a line much more cleanly; not asserted for
    # threshold_front, which is noisier by construction.
    assert fits["energy_weighted_radius"].r_squared > 0.7


def test_propagation_table_round_trips_through_csv(samples: list[PropagationSample], tmp_path) -> None:
    csv_path = tmp_path / "propagation.csv"
    write_propagation_table_csv(samples, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = samples_to_table(samples)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back[::200], expected[::200]):
        assert float(read_row["time"]) == pytest.approx(expected_row["time"])
        assert float(read_row["energy_weighted_radius"]) == pytest.approx(
            expected_row["energy_weighted_radius"]
        )
