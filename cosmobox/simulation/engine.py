"""Conservative, free-boundary velocity-Verlet engine for EXP-0001.

Separate from the legacy prototype (cosmobox.core.mechanics): no
damping, no deformation-factor evolution, no implicit center-of-mass
correction. Only the harmonic bond force law from
cosmobox.physics.elasticity is used. Fixed and absorbing boundaries are
out of scope here (see docs/05_decisions/0001-moteur-conservatif-minimal.md,
implementation order) — every node evolves freely under its own forces.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.physics.diagnostics import kinetic_energy, total_momentum
from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_forces


@dataclass(slots=True)
class LatticeState:
    positions: np.ndarray
    velocities: np.ndarray


@dataclass(slots=True)
class EngineConfig:
    node_mass: float
    dt: float


@dataclass(slots=True)
class StepDiagnostics:
    time: float
    kinetic_energy: float
    elastic_energy: float
    total_energy: float
    momentum: np.ndarray

    @property
    def momentum_norm(self) -> float:
        return float(np.linalg.norm(self.momentum))


class ConservativeLatticeEngine:
    def __init__(self, edges: np.ndarray, elasticity: ElasticityConfig, engine: EngineConfig):
        self.edges = edges
        self.elasticity = elasticity
        self.engine = engine

    def forces(self, positions: np.ndarray) -> np.ndarray:
        return bond_forces(positions, self.edges, self.elasticity)

    def diagnostics(self, state: LatticeState, time: float) -> StepDiagnostics:
        kinetic = kinetic_energy(state.velocities, self.engine.node_mass)
        elastic = bond_energy(state.positions, self.edges, self.elasticity)
        momentum = total_momentum(state.velocities, self.engine.node_mass)
        return StepDiagnostics(
            time=time,
            kinetic_energy=kinetic,
            elastic_energy=elastic,
            total_energy=kinetic + elastic,
            momentum=momentum,
        )

    def step(self, state: LatticeState) -> LatticeState:
        dt = self.engine.dt
        mass = self.engine.node_mass

        acceleration = self.forces(state.positions) / mass
        new_positions = state.positions + state.velocities * dt + 0.5 * acceleration * dt**2
        new_acceleration = self.forces(new_positions) / mass
        new_velocities = state.velocities + 0.5 * (acceleration + new_acceleration) * dt

        return LatticeState(positions=new_positions, velocities=new_velocities)

    def run(self, initial_state: LatticeState, steps: int) -> list[tuple[LatticeState, StepDiagnostics]]:
        dt = self.engine.dt
        state = initial_state
        history = [(state, self.diagnostics(state, time=0.0))]
        for step_index in range(1, steps + 1):
            state = self.step(state)
            history.append((state, self.diagnostics(state, time=step_index * dt)))
        return history
