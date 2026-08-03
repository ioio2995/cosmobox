"""EXP-0001 implementation, step 3: momentum-compensated injection on a
free-boundary lattice, and the formal conservation measurements that go
with it (docs/05_decisions/0001-moteur-conservatif-minimal.md).

Scope, per the reviewed plan: compensated injection only (no single-node,
radial or transverse forms yet), free boundary only, energy threshold is
not a physical acceptance criterion here — only "bounded and
non-secular for a given dt". Quantitative convergence in dt is step 4.
"""
from __future__ import annotations

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig, bond_forces
from cosmobox.simulation.analysis import analyze_conservation
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState
from cosmobox.simulation.injection import (
    apply_injection,
    closest_interior_node_to_center,
    compensated_pair_injection,
)

_SPEED = 0.3
_STEPS = 500


@pytest.fixture(
    scope="module",
    params=[MatrixConfig(radius=5.5, cell_range=5), MatrixConfig()],
    ids=["small", "default"],
)
def matrix(request: pytest.FixtureRequest) -> DiamondMatrix:
    return DiamondMatrix(request.param)


@pytest.fixture
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture
def engine(matrix: DiamondMatrix, elasticity: ElasticityConfig) -> ConservativeLatticeEngine:
    return ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=1.0, dt=0.01))


@pytest.fixture
def injected_history(matrix: DiamondMatrix, engine: ConservativeLatticeEngine):
    injection = compensated_pair_injection(matrix, speed=_SPEED)
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    initial_state = LatticeState(positions=matrix.reference_positions.copy(), velocities=velocities)
    return engine.run(initial_state, steps=_STEPS)


# --- injection selection ---


def test_injection_node_selection_is_deterministic(matrix: DiamondMatrix) -> None:
    injection_1 = compensated_pair_injection(matrix, speed=_SPEED)
    injection_2 = compensated_pair_injection(matrix, speed=_SPEED)
    assert injection_1.node_a == injection_2.node_a == closest_interior_node_to_center(matrix)
    assert injection_1.node_b == injection_2.node_b
    assert injection_1.node_a != injection_1.node_b


def test_injection_has_zero_total_momentum(matrix: DiamondMatrix) -> None:
    injection = compensated_pair_injection(matrix, speed=_SPEED)
    velocities = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    total_momentum = (1.0 * velocities).sum(axis=0)  # node_mass = 1.0
    assert np.linalg.norm(total_momentum) < 1e-12


def test_injected_energy_is_positive_and_finite(injected_history) -> None:
    initial_energy = injected_history[0][1].total_energy
    assert initial_energy > 0.0
    assert np.isfinite(initial_energy)


# --- conservation over the run ---


def test_momentum_stays_constant_over_the_run(injected_history) -> None:
    report = analyze_conservation(injected_history)
    assert report.max_momentum_drift < 1e-9


def test_center_of_mass_does_not_drift(injected_history) -> None:
    reference = injected_history[0][1].center_of_mass_position
    drift = max(
        float(np.linalg.norm(diag.center_of_mass_position - reference))
        for _, diag in injected_history
    )
    assert drift < 1e-9


def test_energy_error_stays_bounded_and_is_not_secular(injected_history) -> None:
    # A coarse regression guard, not a rigorous absence-of-drift proof: a
    # slowly-growing error could still satisfy the 10x ratio below. The
    # rigorous version — checking the observed order of convergence in
    # dt — is tests/test_dt_convergence.py (step 4); no physical
    # conclusion should be drawn from this test alone.
    report = analyze_conservation(injected_history)
    assert report.energy_relative_error is not None

    # Not a physical acceptance threshold (that belongs to the dt-
    # convergence study in step 4) — just checks the symplectic
    # integrator's bounded-oscillating-error behavior holds at this dt,
    # per docs/05_decisions/0001-moteur-conservatif-minimal.md.
    assert report.max_energy_relative_error < 1e-2

    # Non-secular: the error late in the run should be the same order of
    # magnitude as early in the run, not monotonically growing.
    error = np.abs(report.energy_relative_error)
    quarter = len(error) // 4
    early = float(np.max(error[:quarter]))
    late = float(np.max(error[-quarter:]))
    assert late < 10 * max(early, 1e-12)


def test_internal_forces_sum_to_zero_at_every_step(
    injected_history, matrix: DiamondMatrix, elasticity: ElasticityConfig
) -> None:
    # Newton's third law must hold at every evaluation along the
    # trajectory, not just at the resting configuration.
    for state, _ in injected_history[::20]:  # sampled for speed on the larger fixture
        forces = bond_forces(state.positions, matrix.edges, elasticity)
        assert np.linalg.norm(forces.sum(axis=0)) < 1e-9
