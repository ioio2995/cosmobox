"""Absorbing-boundary-layer velocity-Verlet engine for EXP-0001 step 9B.

A radial damping coefficient gamma(r) — zero in the central domain,
growing smoothly through an outer shell — is applied via Strang
(symmetric) operator splitting: an exact exponential-decay half-step
for the dissipative part `m*dv/dt = -gamma*v`, a standard conservative
velocity-Verlet full step on the bond forces, then another exact
exponential-decay half-step. This is not an ad hoc "multiply velocities
by a constant after the step" — each half-step's kinetic-energy loss is
computed directly from the velocities before and after applying it
(`0.5*m*|v|^2`), not approximated by `gamma*|v|^2*dt`, and accumulated
into `absorbed_energy`, so
`mechanical_energy(t) + absorbed_energy(t) ~= mechanical_energy(0)`
can be checked directly rather than assumed.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.diagnostics import kinetic_energy
from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_forces
from cosmobox.simulation.engine import EngineConfig, LatticeState


@dataclass(slots=True)
class AbsorbingLayerConfig:
    domain_radius: float  # R
    absorption_radius: float  # r_abs: damping is exactly zero for r <= this
    gamma_max: float
    exponent: float  # p

    def __post_init__(self) -> None:
        if not (0.0 <= self.absorption_radius < self.domain_radius):
            raise ValueError(
                f"absorption_radius must satisfy 0 <= r_abs < domain_radius, "
                f"got r_abs={self.absorption_radius}, domain_radius={self.domain_radius}"
            )
        if self.gamma_max < 0.0:
            raise ValueError(f"gamma_max must be non-negative, got {self.gamma_max}")
        if self.exponent <= 0.0:
            raise ValueError(f"exponent must be strictly positive, got {self.exponent}")


def absorbing_layer_damping_coefficients(config: AbsorbingLayerConfig, distances: np.ndarray) -> np.ndarray:
    """`gamma_i`: 0 for `distances[i] <= absorption_radius`, growing as
    `gamma_max * ((r - r_abs) / (R - r_abs)) ** exponent` in the outer
    shell (clipped to `gamma_max` beyond `domain_radius`, for nodes
    that may sit slightly past R due to the lattice's discrete shape).
    """
    width = config.domain_radius - config.absorption_radius
    fraction = np.clip((distances - config.absorption_radius) / width, 0.0, 1.0)
    return config.gamma_max * fraction**config.exponent


@dataclass(slots=True)
class AbsorbingStepDiagnostics:
    time: float
    kinetic_energy: float
    elastic_energy: float
    mechanical_energy: float  # kinetic + elastic
    absorbed_energy: float  # cumulative, cannot decrease
    total_energy: float  # mechanical + absorbed; the conserved quantity


class AbsorbingLatticeEngine:
    def __init__(
        self,
        edges: np.ndarray,
        elasticity: ElasticityConfig,
        engine: EngineConfig,
        damping_coefficients: np.ndarray,
    ):
        self.edges = edges
        self.elasticity = elasticity
        self.engine = engine
        self.damping_coefficients = damping_coefficients
        self._decay = np.exp(
            -damping_coefficients * engine.dt / (2.0 * engine.node_mass)
        )[:, None]

    def forces(self, positions: np.ndarray) -> np.ndarray:
        return bond_forces(positions, self.edges, self.elasticity)

    def step(self, state: LatticeState) -> tuple[LatticeState, float]:
        """Returns the new state and the mechanical (kinetic) energy
        dissipated during this step (both damping half-steps combined).
        """
        dt = self.engine.dt
        mass = self.engine.node_mass

        kinetic_before_first_half = kinetic_energy(state.velocities, mass)
        v_half = state.velocities * self._decay
        kinetic_after_first_half = kinetic_energy(v_half, mass)
        dissipated = kinetic_before_first_half - kinetic_after_first_half

        acceleration = self.forces(state.positions) / mass
        new_positions = state.positions + v_half * dt + 0.5 * acceleration * dt**2
        new_acceleration = self.forces(new_positions) / mass
        v_conservative = v_half + 0.5 * (acceleration + new_acceleration) * dt

        kinetic_before_second_half = kinetic_energy(v_conservative, mass)
        new_velocities = v_conservative * self._decay
        kinetic_after_second_half = kinetic_energy(new_velocities, mass)
        dissipated += kinetic_before_second_half - kinetic_after_second_half

        return LatticeState(positions=new_positions, velocities=new_velocities), dissipated

    def diagnostics(self, state: LatticeState, time: float, cumulative_absorbed: float) -> AbsorbingStepDiagnostics:
        kinetic = kinetic_energy(state.velocities, self.engine.node_mass)
        elastic = bond_energy(state.positions, self.edges, self.elasticity)
        mechanical = kinetic + elastic
        return AbsorbingStepDiagnostics(
            time=time,
            kinetic_energy=kinetic,
            elastic_energy=elastic,
            mechanical_energy=mechanical,
            absorbed_energy=cumulative_absorbed,
            total_energy=mechanical + cumulative_absorbed,
        )

    def run(self, initial_state: LatticeState, steps: int) -> list[tuple[LatticeState, AbsorbingStepDiagnostics]]:
        dt = self.engine.dt
        state = LatticeState(
            positions=initial_state.positions.copy(), velocities=initial_state.velocities.copy()
        )
        cumulative_absorbed = 0.0
        history = [(state, self.diagnostics(state, 0.0, cumulative_absorbed))]
        for step_index in range(1, steps + 1):
            state, dissipated = self.step(state)
            cumulative_absorbed += dissipated
            history.append((state, self.diagnostics(state, step_index * dt, cumulative_absorbed)))
        return history


def energy_balance_summary(history: list[tuple[LatticeState, AbsorbingStepDiagnostics]]) -> dict[str, float]:
    """`mechanical_energy(t) + absorbed_energy(t)` should stay close to
    its initial value — this reports the actual closure error, plus
    the fraction absorbed and the fraction still mechanical, at the
    end of the run.
    """
    initial = history[0][1]
    final = history[-1][1]
    return {
        "initial_total_energy": initial.total_energy,
        "final_total_energy": final.total_energy,
        "balance_relative_error": abs(final.total_energy - initial.total_energy) / initial.total_energy,
        "absorbed_fraction": final.absorbed_energy / initial.total_energy,
        "mechanical_remaining_fraction": final.mechanical_energy / initial.total_energy,
    }


@dataclass(slots=True)
class SensitivityRow:
    label: str
    gamma_max: float
    exponent: float
    absorption_radius: float
    balance_relative_error: float
    absorbed_fraction: float
    mechanical_remaining_fraction: float


def run_sensitivity_study(
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    dt: float,
    steps: int,
    initial_state: LatticeState,
    distances: np.ndarray,
    configs: list[tuple[str, AbsorbingLayerConfig]],
) -> list[SensitivityRow]:
    """Runs the same lattice/injection/dt/duration under several
    `AbsorbingLayerConfig`s (varying width, gamma_max, exponent), for a
    small parameter-sensitivity study rather than a single "it seems to
    work" configuration.
    """
    rows = []
    for label, config in configs:
        gamma = absorbing_layer_damping_coefficients(config, distances)
        engine = AbsorbingLatticeEngine(edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt), gamma)
        history = engine.run(initial_state, steps=steps)
        summary = energy_balance_summary(history)
        rows.append(
            SensitivityRow(
                label=label,
                gamma_max=config.gamma_max,
                exponent=config.exponent,
                absorption_radius=config.absorption_radius,
                balance_relative_error=summary["balance_relative_error"],
                absorbed_fraction=summary["absorbed_fraction"],
                mechanical_remaining_fraction=summary["mechanical_remaining_fraction"],
            )
        )
    return rows


def sensitivity_rows_to_table(rows: list[SensitivityRow]) -> list[dict[str, object]]:
    return [
        {
            "label": row.label,
            "gamma_max": row.gamma_max,
            "exponent": row.exponent,
            "absorption_radius": row.absorption_radius,
            "balance_relative_error": row.balance_relative_error,
            "absorbed_fraction": row.absorbed_fraction,
            "mechanical_remaining_fraction": row.mechanical_remaining_fraction,
        }
        for row in rows
    ]


def write_sensitivity_table_csv(rows: list[SensitivityRow], path: Path) -> None:
    table = sensitivity_rows_to_table(rows)
    if not table:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
