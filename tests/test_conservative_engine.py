"""Tests for the conservative minimal engine (EXP-0001 implementation,
step 2: physics/elasticity.py + simulation/engine.py, velocity-Verlet,
free boundary, control zero).
"""
from __future__ import annotations

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_forces
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState

# --- physics/elasticity.py, in isolation from the engine and from DiamondMatrix ---

_TWO_NODE_EDGES = np.array([[0, 1]], dtype=int)


def test_bond_at_rest_length_has_zero_energy_and_zero_force() -> None:
    config = ElasticityConfig(rest_length=1.0, stiffness=5.0)
    positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    assert bond_energy(positions, _TWO_NODE_EDGES, config) == pytest.approx(0.0)
    forces = bond_forces(positions, _TWO_NODE_EDGES, config)
    assert np.allclose(forces, 0.0)


def test_stretched_bond_pulls_nodes_together() -> None:
    config = ElasticityConfig(rest_length=1.0, stiffness=5.0)
    positions = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])  # extension = 1.0

    energy = bond_energy(positions, _TWO_NODE_EDGES, config)
    assert energy == pytest.approx(0.5 * 5.0 * 1.0**2)

    forces = bond_forces(positions, _TWO_NODE_EDGES, config)
    # Node 0 should be pulled toward node 1 (+x), node 1 toward node 0 (-x),
    # with magnitude k * extension, by Newton's third law.
    assert forces[0] == pytest.approx([5.0, 0.0, 0.0])
    assert forces[1] == pytest.approx([-5.0, 0.0, 0.0])


def test_compressed_bond_pushes_nodes_apart() -> None:
    config = ElasticityConfig(rest_length=1.0, stiffness=5.0)
    positions = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]])  # extension = -0.5

    forces = bond_forces(positions, _TWO_NODE_EDGES, config)
    assert forces[0] == pytest.approx([-2.5, 0.0, 0.0])
    assert forces[1] == pytest.approx([2.5, 0.0, 0.0])


# --- simulation/engine.py: free-boundary velocity-Verlet on the diamond lattice ---


@pytest.fixture(
    scope="module",
    params=[MatrixConfig(radius=3.0, cell_range=3), MatrixConfig(radius=5.5, cell_range=5)],
    ids=["tiny", "small"],
)
def matrix(request: pytest.FixtureRequest) -> DiamondMatrix:
    return DiamondMatrix(request.param)


@pytest.fixture
def engine(matrix: DiamondMatrix) -> ConservativeLatticeEngine:
    elasticity = ElasticityConfig(rest_length=matrix.c, stiffness=1.0)
    engine_config = EngineConfig(node_mass=1.0, dt=0.01)
    return ConservativeLatticeEngine(matrix.edges, elasticity, engine_config)


def test_control_zero_stays_at_rest(matrix: DiamondMatrix, engine: ConservativeLatticeEngine) -> None:
    # EXP-0001 §8.1: with no injection, the lattice at rest must remain
    # stationary. Every bond starts exactly at rest length (guaranteed by
    # test_all_edges_share_the_same_rest_length in
    # test_diamond_matrix_invariants.py), so every force is exactly zero
    # and the network should not move at all beyond floating-point noise.
    initial_state = LatticeState(
        positions=matrix.reference_positions.copy(),
        velocities=np.zeros_like(matrix.reference_positions),
    )

    history = engine.run(initial_state, steps=50)

    max_displacement = max(
        float(np.max(np.linalg.norm(state.positions - matrix.reference_positions, axis=1)))
        for state, _ in history
    )
    max_speed = max(float(np.max(np.linalg.norm(state.velocities, axis=1))) for state, _ in history)
    max_total_energy = max(diag.total_energy for _, diag in history)

    assert max_displacement < 1e-9
    assert max_speed < 1e-9
    assert max_total_energy < 1e-9


def test_diagnostics_are_reported_for_every_step(
    matrix: DiamondMatrix, engine: ConservativeLatticeEngine
) -> None:
    initial_state = LatticeState(
        positions=matrix.reference_positions.copy(),
        velocities=np.zeros_like(matrix.reference_positions),
    )

    steps = 10
    history = engine.run(initial_state, steps=steps)

    assert len(history) == steps + 1
    times = [diag.time for _, diag in history]
    assert times == sorted(times)
    assert times[0] == pytest.approx(0.0)
    assert times[-1] == pytest.approx(steps * engine.engine.dt)
    for _, diag in history:
        assert np.isfinite(diag.kinetic_energy)
        assert np.isfinite(diag.elastic_energy)
        assert np.isfinite(diag.total_energy)
        assert diag.momentum.shape == (3,)
        assert np.isfinite(diag.momentum_norm)
