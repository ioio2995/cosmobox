"""EXP-0001 implementation, step 6: source-orientation dependence.

Per the step-5 review, this step must measure the *angular* dependence
of the (still free-boundary) compensated-pair injection, not just
compare four global numbers, and must separate two distinct claims:

- covariance by symmetry (checked exactly, against the lattice's own
  verified point-group symmetries — a correctness property of the
  engine+geometry);
- effective isotropy (not assumed; reported as measured only).
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.core.symmetry import lattice_symmetry_permutation, permutation_preserves_edges
from cosmobox.physics.anisotropy import (
    DirectionalRun,
    directional_runs_to_table,
    energy_tensor,
    directional_energy,
    run_directional_study,
    symmetry_trajectory_max_error,
    write_directional_table_csv,
)
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.propagation import node_energy_density
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState
from cosmobox.simulation.injection import apply_injection, tetrahedral_directional_injections

_SPEED = 0.3
_DT = 0.01

# The four 180-degree rotations (identity + one per coordinate axis)
# that were verified (see the propagation-review response) to map the
# TETRA_DIRS set, the DiamondMatrix point set, and its edge set, all
# exactly onto themselves.
_CANDIDATE_TRANSFORMS = {
    "I": np.eye(3),
    "Rx": np.diag([1.0, -1.0, -1.0]),
    "Ry": np.diag([-1.0, 1.0, -1.0]),
    "Rz": np.diag([-1.0, -1.0, 1.0]),
}


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def injections(matrix: DiamondMatrix):
    return tetrahedral_directional_injections(matrix, speed=_SPEED)


def _find_transform(direction_a: np.ndarray, direction_b: np.ndarray) -> np.ndarray:
    for transform in _CANDIDATE_TRANSFORMS.values():
        if np.allclose(transform @ direction_a, direction_b, atol=1e-9):
            return transform
    raise AssertionError(f"no candidate transform maps {direction_a} to {direction_b}")


# --- injection selection across directions ---


def test_four_tetrahedral_directions_are_selected(injections) -> None:
    assert len(injections) == 4
    assert len({inj.node_b for inj in injections}) == 4
    assert len({inj.node_a for inj in injections}) == 1  # same central node


def test_injected_energy_is_identical_across_directions(injections, matrix: DiamondMatrix) -> None:
    energies = []
    for injection in injections:
        velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
        energies.append(0.5 * 1.0 * float(np.sum(velocities**2)))
    assert energies[0] > 0.0
    assert all(e == pytest.approx(energies[0], abs=1e-12) for e in energies)


# --- lattice symmetry validation ---


def test_candidate_transforms_are_exact_lattice_symmetries(matrix: DiamondMatrix) -> None:
    for name, transform in _CANDIDATE_TRANSFORMS.items():
        permutation = lattice_symmetry_permutation(matrix.reference_positions, transform)
        assert permutation_preserves_edges(matrix.edges, permutation), f"{name} does not preserve edges"


def test_every_pair_of_tetrahedral_directions_has_a_mapping_transform(injections) -> None:
    directions = [injection.direction for injection in injections]
    for i in range(len(directions)):
        for j in range(len(directions)):
            _find_transform(directions[i], directions[j])  # raises if none found


# --- exact covariance between directions (correctness, not physics) ---


@pytest.mark.parametrize("target_index", [1, 2, 3])
def test_engine_is_exactly_covariant_under_lattice_symmetry(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, injections, target_index: int
) -> None:
    source_injection = injections[0]
    target_injection = injections[target_index]
    transform = _find_transform(source_injection.direction, target_injection.direction)
    permutation = lattice_symmetry_permutation(matrix.reference_positions, transform)

    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))

    source_velocities = apply_injection(np.zeros_like(matrix.reference_positions), source_injection)
    target_velocities = apply_injection(np.zeros_like(matrix.reference_positions), target_injection)
    source_history = engine.run(
        LatticeState(positions=matrix.reference_positions.copy(), velocities=source_velocities), steps=500
    )
    target_history = engine.run(
        LatticeState(positions=matrix.reference_positions.copy(), velocities=target_velocities), steps=500
    )

    error = symmetry_trajectory_max_error(source_history, target_history, transform, permutation)
    assert error < 1e-9


# --- energy tensor and directional energy ---


def test_energy_tensor_is_symmetric_and_positive_semidefinite(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, injections
) -> None:
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injections[0])
    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))
    history = engine.run(
        LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities), steps=300
    )
    state, _ = history[-1]
    density = node_energy_density(state.positions, state.velocities, matrix.edges, elasticity, node_mass=1.0)
    center = matrix.reference_positions[injections[0].node_a]

    tensor = energy_tensor(matrix.reference_positions, center, density)
    assert np.allclose(tensor, tensor.T)
    eigenvalues = np.linalg.eigvalsh(tensor)
    assert np.all(eigenvalues > -1e-9)


def test_directional_energy_is_monotonic_in_cone_angle_and_recovers_total_at_180(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, injections
) -> None:
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injections[0])
    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=_DT))
    history = engine.run(
        LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities), steps=300
    )
    state, diag = history[-1]
    density = node_energy_density(state.positions, state.velocities, matrix.edges, elasticity, node_mass=1.0)
    center = matrix.reference_positions[injections[0].node_a]

    angles = [5.0, 15.0, 30.0, 60.0, 90.0, 120.0, 180.0]
    energies = [
        directional_energy(matrix.reference_positions, center, density, injections[0].direction, angle)
        for angle in angles
    ]
    assert energies == sorted(energies)
    assert energies[-1] == pytest.approx(diag.total_energy, abs=1e-9)


# --- full directional study ---


@pytest.fixture(scope="module")
def directional_runs(matrix: DiamondMatrix, elasticity: ElasticityConfig) -> list[DirectionalRun]:
    return run_directional_study(
        matrix, elasticity, node_mass=1.0, dt=_DT, steps=2500, speed=_SPEED,
        threshold_fraction=0.01, caution_fraction=0.9,
    )


def test_directional_study_returns_one_run_per_direction(directional_runs: list[DirectionalRun]) -> None:
    assert len(directional_runs) == 4


def test_boundary_influence_time_is_consistent_across_directions(
    directional_runs: list[DirectionalRun],
) -> None:
    times = [run.boundary_influence_time for run in directional_runs]
    assert all(t is not None for t in times)
    assert max(times) - min(times) < 1e-6


def test_final_energy_weighted_radius_is_consistent_across_directions(
    directional_runs: list[DirectionalRun],
) -> None:
    radii = [run.samples[-1].energy_weighted_radius for run in directional_runs]
    assert max(radii) - min(radii) < 1e-6


def test_directional_table_round_trips_through_csv(
    directional_runs: list[DirectionalRun], tmp_path
) -> None:
    csv_path = tmp_path / "directional.csv"
    write_directional_table_csv(directional_runs, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = directional_runs_to_table(directional_runs)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert float(read_row["injected_energy"]) == pytest.approx(expected_row["injected_energy"])
        assert float(read_row["final_energy_weighted_radius"]) == pytest.approx(
            expected_row["final_energy_weighted_radius"]
        )
