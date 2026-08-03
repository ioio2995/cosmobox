"""Fixed-boundary velocity-Verlet engine for EXP-0001 step 9A.

A subset of nodes (`boundary_mask`) is held exactly at its reference
position with zero velocity for the whole run — not by resetting
positions after an unconstrained update, but by setting the
constrained nodes' acceleration to exactly zero at every evaluation,
which is equivalent to an explicit reaction force
`F_reaction = -F_bond` there (the net force on a node whose position
and velocity never change must be exactly zero). Because velocity is
identically zero at the boundary, it does zero work
(`sum_i F_reaction_i . v_i = 0`) — an idealized, perfectly rigid wall.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.physics.diagnostics import kinetic_energy
from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_forces
from cosmobox.simulation.engine import EngineConfig, LatticeState


@dataclass(slots=True)
class FixedBoundaryStepDiagnostics:
    time: float
    kinetic_energy: float
    elastic_energy: float
    total_energy: float
    momentum: np.ndarray  # of the mobile (interior) nodes only; boundary contributes exactly 0 (v=0)
    reaction_force_total: np.ndarray  # (3,): sum over boundary nodes of the force needed to hold them fixed


class FixedBoundaryLatticeEngine:
    def __init__(
        self,
        edges: np.ndarray,
        elasticity: ElasticityConfig,
        engine: EngineConfig,
        boundary_mask: np.ndarray,
        reference_positions: np.ndarray,
    ):
        self.edges = edges
        self.elasticity = elasticity
        self.engine = engine
        self.boundary_mask = boundary_mask
        self.interior_mask = ~boundary_mask
        self.reference_positions = reference_positions

    def forces(self, positions: np.ndarray) -> np.ndarray:
        return bond_forces(positions, self.edges, self.elasticity)

    def diagnostics(self, state: LatticeState, time: float) -> FixedBoundaryStepDiagnostics:
        kinetic = kinetic_energy(state.velocities, self.engine.node_mass)
        elastic = bond_energy(state.positions, self.edges, self.elasticity)
        momentum = self.engine.node_mass * state.velocities[self.interior_mask].sum(axis=0)
        boundary_bond_forces = self.forces(state.positions)[self.boundary_mask]
        reaction_force_total = -boundary_bond_forces.sum(axis=0)
        return FixedBoundaryStepDiagnostics(
            time=time,
            kinetic_energy=kinetic,
            elastic_energy=elastic,
            total_energy=kinetic + elastic,
            momentum=momentum,
            reaction_force_total=reaction_force_total,
        )

    def step(self, state: LatticeState) -> LatticeState:
        dt = self.engine.dt
        mass = self.engine.node_mass

        acceleration = self.forces(state.positions) / mass
        acceleration[self.boundary_mask] = 0.0
        new_positions = state.positions + state.velocities * dt + 0.5 * acceleration * dt**2
        new_positions[self.boundary_mask] = self.reference_positions[self.boundary_mask]

        new_acceleration = self.forces(new_positions) / mass
        new_acceleration[self.boundary_mask] = 0.0
        new_velocities = state.velocities + 0.5 * (acceleration + new_acceleration) * dt
        new_velocities[self.boundary_mask] = 0.0

        return LatticeState(positions=new_positions, velocities=new_velocities)

    def run(
        self, initial_state: LatticeState, steps: int
    ) -> list[tuple[LatticeState, FixedBoundaryStepDiagnostics]]:
        dt = self.engine.dt
        state = LatticeState(
            positions=initial_state.positions.copy(), velocities=initial_state.velocities.copy()
        )
        state.positions[self.boundary_mask] = self.reference_positions[self.boundary_mask]
        state.velocities[self.boundary_mask] = 0.0

        history = [(state, self.diagnostics(state, 0.0))]
        for step_index in range(1, steps + 1):
            state = self.step(state)
            history.append((state, self.diagnostics(state, step_index * dt)))
        return history


def cumulative_reaction_impulse(
    history: list[tuple[LatticeState, FixedBoundaryStepDiagnostics]], dt: float
) -> np.ndarray:
    """Trapezoidal-rule integral of `reaction_force_total(t)` over the
    run: the total impulse the boundary constraint delivered to hold
    itself in place.
    """
    forces_over_time = np.array([diagnostics.reaction_force_total for _, diagnostics in history])
    return dt * (forces_over_time[0] / 2 + forces_over_time[1:-1].sum(axis=0) + forces_over_time[-1] / 2)


def momentum_balance_residual(
    history: list[tuple[LatticeState, FixedBoundaryStepDiagnostics]], dt: float
) -> float:
    """`||delta_P_mobile - J_reaction||`.

    By Newton's third law, internal bond forces always sum to zero
    over *all* nodes (mobile + boundary) regardless of which are
    constrained, so the net bond force on the mobile nodes always
    equals minus the net bond force on the boundary — which, by
    definition of `reaction_force_total = -sum(bond_force_on_boundary)`,
    equals `reaction_force_total` itself. Integrating:
    `d(P_mobile)/dt = reaction_force_total(t)`, so
    `delta_P_mobile == J_reaction` exactly (not `== -J_reaction`, which
    would be the balance if `J_reaction` were instead defined as the
    impulse the mobile system delivers *to* the boundary — the
    physically equivalent, oppositely-signed convention). This
    residual should be ~0 (floating-point/quadrature noise).
    """
    initial_momentum = history[0][1].momentum
    final_momentum = history[-1][1].momentum
    delta_momentum = final_momentum - initial_momentum
    impulse = cumulative_reaction_impulse(history, dt)
    return float(np.linalg.norm(delta_momentum - impulse))
