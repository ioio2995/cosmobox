"""EXP-0001 implementation, step 7B-3: transverse impulses decomposed
against the linearized kernel (cosmobox.physics.rigidity).

Per the step-7B-2 review: two orthogonal transverse polarizations,
spectral decomposition (f0 + f_perp = 1), three executions per
polarization (raw / kernel-only / complement-only) in both natural and
energy-renormalized presentations, and an amplitude scan for the
kernel-only component's elastic-energy scaling power.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.rigidity import analyze_modes, kernel_projector
from cosmobox.physics.transverse import (
    TransverseStudy,
    kernel_energy_scaling,
    observed_scaling_order,
    run_transverse_polarization_study,
    spectral_fractions,
    transverse_basis,
    transverse_samples_to_table,
    write_transverse_samples_csv,
)
from cosmobox.simulation.injection import (
    apply_injection,
    closest_interior_node_to_center,
    compensated_pair_injection,
    neighbors_sorted_by_direction,
)

_DT = 0.005
_STEPS = 500
_SPEED = 0.1


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def central_pair(matrix: DiamondMatrix) -> tuple[int, int]:
    node_a = closest_interior_node_to_center(matrix)
    node_b = neighbors_sorted_by_direction(matrix, node_a)[0]
    return node_a, node_b


@pytest.fixture(scope="module")
def bond_direction(matrix: DiamondMatrix, central_pair: tuple[int, int]) -> np.ndarray:
    node_a, node_b = central_pair
    return matrix.reference_positions[node_b] - matrix.reference_positions[node_a]


@pytest.fixture(scope="module")
def projector(matrix: DiamondMatrix) -> np.ndarray:
    analysis = analyze_modes(matrix.reference_positions, matrix.edges, matrix.degrees, stiffness=1.0)
    kernel_basis = np.array([mode.displacement.ravel() for mode in analysis.modes])
    return kernel_projector(kernel_basis)


@pytest.fixture(scope="module")
def polarizations(bond_direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return transverse_basis(bond_direction)


# --- basis construction ---


def test_transverse_basis_is_orthonormal_and_perpendicular_to_the_bond(
    bond_direction: np.ndarray, polarizations: tuple[np.ndarray, np.ndarray]
) -> None:
    t1, t2 = polarizations
    unit_n = bond_direction / np.linalg.norm(bond_direction)
    assert np.linalg.norm(t1) == pytest.approx(1.0)
    assert np.linalg.norm(t2) == pytest.approx(1.0)
    assert t1 @ unit_n == pytest.approx(0.0, abs=1e-9)
    assert t2 @ unit_n == pytest.approx(0.0, abs=1e-9)
    assert t1 @ t2 == pytest.approx(0.0, abs=1e-9)


# --- spectral decomposition ---


@pytest.fixture(scope="module", params=[0, 1], ids=["t1", "t2"])
def study(
    request: pytest.FixtureRequest, matrix: DiamondMatrix, elasticity: ElasticityConfig,
    central_pair: tuple[int, int], polarizations: tuple[np.ndarray, np.ndarray],
    projector: np.ndarray,
) -> TransverseStudy:
    node_a, node_b = central_pair
    direction = polarizations[request.param]
    distances = np.linalg.norm(matrix.reference_positions, axis=1)
    return run_transverse_polarization_study(
        matrix, elasticity, 1.0, _DT, _STEPS, node_a, node_b, direction, _SPEED,
        projector, distances, polarization_label=f"t{request.param + 1}",
    )


def test_spectral_fractions_sum_to_one(study: TransverseStudy) -> None:
    assert study.initial_kernel_fraction + study.initial_complement_fraction == pytest.approx(1.0, abs=1e-9)


def test_transverse_polarization_has_substantial_kernel_overlap(study: TransverseStudy) -> None:
    # Not asserted to be any specific value (that would overfit this
    # particular local bond geometry) — only that a transverse
    # polarization measurably overlaps the kernel, unlike a
    # bond-aligned (longitudinal) injection (see the next test).
    assert 0.1 < study.initial_kernel_fraction < 0.9


def test_longitudinal_injection_has_essentially_zero_kernel_overlap(
    matrix: DiamondMatrix, projector: np.ndarray
) -> None:
    injection = compensated_pair_injection(matrix, speed=_SPEED)
    velocity_flat = apply_injection(np.zeros_like(matrix.reference_positions), injection).ravel()
    f0, f_perp = spectral_fractions(velocity_flat, projector)
    assert f0 < 1e-9
    assert f_perp == pytest.approx(1.0, abs=1e-9)


# --- the three executions, natural and renormalized ---


def test_all_five_runs_are_present(study: TransverseStudy) -> None:
    assert set(study.runs) == {
        "raw", "kernel_natural", "complement_natural", "kernel_renormalized", "complement_renormalized",
    }


def test_kernel_and_complement_runs_start_purely_in_their_respective_subspace(
    study: TransverseStudy,
) -> None:
    assert study.runs["kernel_natural"].initial_kernel_fraction == pytest.approx(1.0, abs=1e-9)
    assert study.runs["complement_natural"].initial_kernel_fraction == pytest.approx(0.0, abs=1e-9)
    assert study.runs["kernel_renormalized"].initial_kernel_fraction == pytest.approx(1.0, abs=1e-9)
    assert study.runs["complement_renormalized"].initial_kernel_fraction == pytest.approx(0.0, abs=1e-9)


def test_renormalized_runs_match_the_raw_runs_injected_energy(study: TransverseStudy) -> None:
    raw_energy = study.runs["raw"].injected_energy
    assert study.runs["kernel_renormalized"].injected_energy == pytest.approx(raw_energy, rel=1e-9)
    assert study.runs["complement_renormalized"].injected_energy == pytest.approx(raw_energy, rel=1e-9)
    # The natural presentations, by contrast, do NOT match it (that's
    # the whole point of also reporting the renormalized ones).
    assert study.runs["kernel_natural"].injected_energy < 0.9 * raw_energy
    assert study.runs["complement_natural"].injected_energy < 0.9 * raw_energy


def test_kernel_only_component_generates_little_elastic_energy_relative_to_complement(
    study: TransverseStudy,
) -> None:
    def peak_ratio(run) -> float:
        peak_elastic = max(sample.elastic_energy for sample in run.samples)
        return peak_elastic / run.injected_energy

    kernel_ratio = peak_ratio(study.runs["kernel_renormalized"])
    complement_ratio = peak_ratio(study.runs["complement_renormalized"])

    # Same injected energy in both (checked above) — the difference in
    # peak elastic/injected ratio is a dynamical one, not an amplitude
    # artifact.
    assert kernel_ratio < 0.05
    assert complement_ratio > 0.5
    assert complement_ratio > 10 * kernel_ratio


# --- amplitude scaling of the kernel-only component ---


def test_kernel_component_elastic_energy_scales_with_a_higher_power_than_speed_squared(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, central_pair: tuple[int, int],
    polarizations: tuple[np.ndarray, np.ndarray], projector: np.ndarray,
) -> None:
    node_a, node_b = central_pair
    t1, _ = polarizations
    speeds = [0.025, 0.05, 0.1, 0.2]
    rows = kernel_energy_scaling(matrix, elasticity, 1.0, _DT, 800, node_a, node_b, t1, speeds, projector)

    assert len(rows) == len(speeds)
    assert all(row.peak_elastic_energy > 0 for row in rows)

    orders = [observed_scaling_order(a, b) for a, b in zip(rows, rows[1:])]
    assert all(order is not None for order in orders)
    # A normal elastic excitation would scale as speed**2; the
    # kernel-only component is expected to scale with a distinctly
    # higher power (measured ~3.9-4.0), generously bounded here to
    # avoid over-fitting the exact exponent.
    for order in orders:
        assert order > 3.0


# --- serialization ---


def test_transverse_samples_round_trip_through_csv(study: TransverseStudy, tmp_path) -> None:
    samples = study.runs["raw"].samples
    csv_path = tmp_path / "transverse.csv"
    write_transverse_samples_csv(samples, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = transverse_samples_to_table(samples)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back[::50], expected[::50]):
        assert float(read_row["time"]) == pytest.approx(expected_row["time"])
        assert float(read_row["elastic_energy"]) == pytest.approx(expected_row["elastic_energy"])
