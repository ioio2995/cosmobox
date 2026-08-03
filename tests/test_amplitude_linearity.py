"""EXP-0001 implementation, step 8: amplitude-linearity study for the
longitudinal (bond-aligned) propagation used in steps 3-6.

Per the step-7 closing review: the quadratic/quartic separation is
already covered by step 7B-3 (kernel vs complement) and is not
repeated here. This targets the longitudinal injection specifically:
injected energy ~ amplitude^2, propagation-slope (in)dependence on
amplitude, superposition of energy-normalized spatial profiles at
small amplitude, and their measurable, growing deviation at larger
amplitude.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.amplitude_linearity import (
    AmplitudeRun,
    amplitude_runs_to_table,
    apparent_velocity_relative_spread,
    injected_energy_scaling_order,
    normalized_profile_deviation,
    run_amplitude_series,
    write_amplitude_table_csv,
)
from cosmobox.physics.elasticity import ElasticityConfig

_SPEEDS = [0.05, 0.1, 0.2, 0.4, 0.8]
_DT = 0.01
_STEPS = 1500  # T = 15
_PROFILE_STEP_INDEX = 1000  # t = 10, well before the front nears the boundary


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=8.2, cell_range=7))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def runs(matrix: DiamondMatrix, elasticity: ElasticityConfig) -> list[AmplitudeRun]:
    bin_edges = np.arange(0.0, matrix.config.radius + 1.0, 1.0)
    return run_amplitude_series(
        matrix, elasticity, node_mass=1.0, dt=_DT, steps=_STEPS, speeds=_SPEEDS,
        threshold_fraction=0.01, caution_fraction=0.9,
        profile_bin_edges=bin_edges, profile_step_index=_PROFILE_STEP_INDEX,
    )


def test_runs_stay_within_the_boundary_free_window(runs: list[AmplitudeRun]) -> None:
    # If any run had already reached the 90%-radius caution zone within
    # T=15, the propagation-slope and profile comparisons below could
    # be confounded by boundary effects rather than amplitude effects.
    assert all(run.boundary_influence_time is None for run in runs)


# --- 1. injected energy ~ amplitude^2 ---


def test_injected_energy_scales_quadratically_with_amplitude(runs: list[AmplitudeRun]) -> None:
    order = injected_energy_scaling_order(runs)
    assert order == pytest.approx(2.0, abs=1e-6)


# --- 2. propagation slope (in)dependence on amplitude ---


def test_propagation_slope_is_nearly_amplitude_independent_at_small_amplitude(
    runs: list[AmplitudeRun],
) -> None:
    small_amplitude_runs = runs[:3]  # 0.05, 0.1, 0.2
    spread = apparent_velocity_relative_spread(small_amplitude_runs, "energy_weighted_radius")
    assert spread < 0.05


def test_propagation_slope_spread_grows_once_larger_amplitudes_are_included(
    runs: list[AmplitudeRun],
) -> None:
    small_spread = apparent_velocity_relative_spread(runs[:3], "energy_weighted_radius")
    full_spread = apparent_velocity_relative_spread(runs, "energy_weighted_radius")
    assert full_spread > small_spread


# --- 3 & 4. superposition of normalized profiles, and its breakdown ---


def test_normalized_profiles_superpose_at_small_amplitude(runs: list[AmplitudeRun]) -> None:
    deviations = normalized_profile_deviation(runs, reference_index=0)
    assert deviations[0] == 0.0  # the reference against itself
    # 0.1 and 0.2, relative to the 0.05 reference: small deviation.
    assert deviations[1] < 0.005
    assert deviations[2] < 0.01


def test_normalized_profile_deviation_grows_monotonically_with_amplitude(
    runs: list[AmplitudeRun],
) -> None:
    deviations = normalized_profile_deviation(runs, reference_index=0)
    assert deviations == sorted(deviations)
    # The largest amplitude's departure from the small-amplitude
    # reference must be clearly measurable, not just numerical noise.
    assert deviations[-1] > 10 * deviations[1]


# --- serialization ---


def test_amplitude_table_round_trips_through_csv(runs: list[AmplitudeRun], tmp_path) -> None:
    csv_path = tmp_path / "amplitude_linearity.csv"
    write_amplitude_table_csv(runs, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = amplitude_runs_to_table(runs)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert float(read_row["speed"]) == pytest.approx(expected_row["speed"])
        assert float(read_row["injected_energy"]) == pytest.approx(expected_row["injected_energy"])
        assert float(read_row["normalized_profile_rms_deviation"]) == pytest.approx(
            expected_row["normalized_profile_rms_deviation"], abs=1e-12
        )
