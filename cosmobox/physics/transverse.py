"""Transverse-impulse / kernel-decomposition study for EXP-0001
step 7B-3.

Injects a momentum-compensated pair impulse along two directions
transverse to the central bond, decomposes each initial velocity field
into its component inside the linearized kernel (cosmobox.physics.rigidity)
and its orthogonal complement, and runs all three (raw, kernel-only,
complement-only) — in both their natural amplitude and a version
renormalized to the raw impulse's injected energy, so an amplitude
difference is never mistaken for a dynamical one.

Expected discriminating result (not assumed, checked): the kernel-only
component should show no first-order elastic restoring force (its
elastic energy stays near the injected value's numerical floor at
small amplitude and grows with a higher power of the speed than the v0^2
scaling of a normal elastic excitation — see `kernel_energy_scaling`),
while the complement-only component should show immediate,
near-complete kinetic/elastic energy exchange.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.diagnostics import kinetic_energy
from cosmobox.physics.elasticity import ElasticityConfig, bond_energy, bond_lengths
from cosmobox.physics.propagation import energy_weighted_radius, node_energy_density
from cosmobox.simulation.engine import ConservativeLatticeEngine, EngineConfig, LatticeState, StepDiagnostics
from cosmobox.simulation.injection import apply_injection, pair_injection_along


def transverse_basis(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors `(t1, t2)`, both orthogonal to `direction` and
    to each other (`t1 . direction = t2 . direction = t1 . t2 = 0`).
    """
    unit_direction = direction / np.linalg.norm(direction)
    axes = np.eye(3)
    helper = axes[int(np.argmin(np.abs(unit_direction)))]
    t1 = np.cross(unit_direction, helper)
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(unit_direction, t1)
    t2 /= np.linalg.norm(t2)
    return t1, t2


def spectral_fractions(flat_vector: np.ndarray, projector: np.ndarray) -> tuple[float, float]:
    """`(f0, f_perp)`: the fraction of `flat_vector`'s squared norm
    lying inside the kernel (`projector`, from
    cosmobox.physics.rigidity.kernel_projector) and in its orthogonal
    complement. `f0 + f_perp == 1` by construction (`projector` is an
    orthogonal projector), checked in tests rather than assumed.
    """
    norm_sq = float(np.dot(flat_vector, flat_vector))
    if norm_sq <= 0:
        return 0.0, 0.0
    kernel_component = projector @ flat_vector
    f0 = float(np.dot(kernel_component, kernel_component) / norm_sq)
    return f0, 1.0 - f0


def renormalize_to_energy(velocity_field: np.ndarray, node_mass: float, target_energy: float) -> np.ndarray:
    """`velocity_field` rescaled so its kinetic energy equals
    `target_energy` — used to compare the kernel-only and
    complement-only components on an equal energy footing with the raw
    impulse, since their *natural* energies differ (by `f0`/`f_perp`).
    """
    current_energy = kinetic_energy(velocity_field, node_mass)
    if current_energy <= 0:
        raise ValueError("cannot renormalize a zero (or zero-energy) velocity field")
    return velocity_field * np.sqrt(target_energy / current_energy)


@dataclass(slots=True)
class TransverseSample:
    time: float
    total_energy: float
    kinetic_energy: float
    elastic_energy: float
    energy_weighted_radius: float
    max_displacement: float
    max_speed: float
    max_bond_extension: float
    displacement_kernel_fraction: float  # f0 of (x(t) - X), the current displacement field
    velocity_kernel_fraction: float  # f0 of v(t)


def transverse_samples(
    history: list[tuple[LatticeState, StepDiagnostics]],
    reference_positions: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    projector: np.ndarray,
    distances: np.ndarray,
) -> list[TransverseSample]:
    samples = []
    for state, diagnostics in history:
        displacement_flat = (state.positions - reference_positions).ravel()
        velocity_flat = state.velocities.ravel()
        displacement_f0, _ = spectral_fractions(displacement_flat, projector)
        velocity_f0, _ = spectral_fractions(velocity_flat, projector)

        density = node_energy_density(state.positions, state.velocities, edges, elasticity, node_mass)
        extensions = bond_lengths(state.positions, edges) - elasticity.rest_length

        samples.append(
            TransverseSample(
                time=diagnostics.time,
                total_energy=diagnostics.total_energy,
                kinetic_energy=diagnostics.kinetic_energy,
                elastic_energy=diagnostics.elastic_energy,
                energy_weighted_radius=energy_weighted_radius(distances, density),
                max_displacement=float(np.max(np.linalg.norm(state.positions - reference_positions, axis=1))),
                max_speed=float(np.max(np.linalg.norm(state.velocities, axis=1))),
                max_bond_extension=float(np.max(np.abs(extensions))),
                displacement_kernel_fraction=displacement_f0,
                velocity_kernel_fraction=velocity_f0,
            )
        )
    return samples


@dataclass(slots=True)
class TransverseRun:
    label: str
    initial_kernel_fraction: float
    initial_complement_fraction: float
    injected_energy: float
    samples: list[TransverseSample]


def _run_from_velocity_field(
    matrix, elasticity: ElasticityConfig, node_mass: float, dt: float, steps: int,
    label: str, velocity_field: np.ndarray, projector: np.ndarray, distances: np.ndarray,
) -> TransverseRun:
    velocity_flat = velocity_field.ravel()
    f0, f_perp = spectral_fractions(velocity_flat, projector)

    engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt))
    initial_state = LatticeState(positions=matrix.reference_positions.copy(), velocities=velocity_field)
    history = engine.run(initial_state, steps=steps)

    samples = transverse_samples(
        history, matrix.reference_positions, matrix.edges, elasticity, node_mass, projector, distances
    )
    return TransverseRun(
        label=label,
        initial_kernel_fraction=f0,
        initial_complement_fraction=f_perp,
        injected_energy=kinetic_energy(velocity_field, node_mass),
        samples=samples,
    )


@dataclass(slots=True)
class TransverseStudy:
    polarization_label: str
    initial_kernel_fraction: float  # f0 of the raw impulse
    initial_complement_fraction: float
    runs: dict[str, TransverseRun]  # "raw", "kernel_natural", "complement_natural", "kernel_renormalized", "complement_renormalized"


def run_transverse_polarization_study(
    matrix,
    elasticity: ElasticityConfig,
    node_mass: float,
    dt: float,
    steps: int,
    node_a: int,
    node_b: int,
    direction: np.ndarray,
    speed: float,
    projector: np.ndarray,
    distances: np.ndarray,
    polarization_label: str,
) -> TransverseStudy:
    injection = pair_injection_along(matrix, node_a, node_b, direction, speed)
    v_raw = apply_injection(np.zeros_like(matrix.reference_positions), injection)
    v_raw_flat = v_raw.ravel()

    f0, f_perp = spectral_fractions(v_raw_flat, projector)
    v_kernel_natural_flat = projector @ v_raw_flat
    v_complement_natural_flat = v_raw_flat - v_kernel_natural_flat
    raw_energy = kinetic_energy(v_raw, node_mass)

    runs: dict[str, TransverseRun] = {
        "raw": _run_from_velocity_field(matrix, elasticity, node_mass, dt, steps, "raw", v_raw, projector, distances),
        "kernel_natural": _run_from_velocity_field(
            matrix, elasticity, node_mass, dt, steps, "kernel_natural",
            v_kernel_natural_flat.reshape(-1, 3), projector, distances,
        ),
        "complement_natural": _run_from_velocity_field(
            matrix, elasticity, node_mass, dt, steps, "complement_natural",
            v_complement_natural_flat.reshape(-1, 3), projector, distances,
        ),
    }

    for label, natural_flat in (("kernel", v_kernel_natural_flat), ("complement", v_complement_natural_flat)):
        natural_field = natural_flat.reshape(-1, 3)
        natural_energy = kinetic_energy(natural_field, node_mass)
        if natural_energy > 1e-24:
            renormalized_field = renormalize_to_energy(natural_field, node_mass, raw_energy)
            runs[f"{label}_renormalized"] = _run_from_velocity_field(
                matrix, elasticity, node_mass, dt, steps, f"{label}_renormalized",
                renormalized_field, projector, distances,
            )

    return TransverseStudy(
        polarization_label=polarization_label,
        initial_kernel_fraction=f0,
        initial_complement_fraction=f_perp,
        runs=runs,
    )


@dataclass(slots=True)
class AmplitudeScalingRow:
    speed: float
    peak_elastic_energy: float


def kernel_energy_scaling(
    matrix,
    elasticity: ElasticityConfig,
    node_mass: float,
    dt: float,
    steps: int,
    node_a: int,
    node_b: int,
    direction: np.ndarray,
    speeds: list[float],
    projector: np.ndarray,
) -> list[AmplitudeScalingRow]:
    """For each `speed`, injects the pair impulse along `direction`,
    projects it onto the kernel only, runs it, and records the peak
    elastic energy reached over the run — to check the empirical
    scaling power of that peak with `speed` (see
    `observed_scaling_order`): a normal elastic excitation scales as
    `speed**2`; a kernel-only excitation is expected to scale with a
    higher power, since it has no first-order (linear) restoring force
    by construction.
    """
    rows = []
    for speed in speeds:
        injection = pair_injection_along(matrix, node_a, node_b, direction, speed)
        v_raw_flat = apply_injection(np.zeros_like(matrix.reference_positions), injection).ravel()
        v_kernel = (projector @ v_raw_flat).reshape(-1, 3)

        engine = ConservativeLatticeEngine(matrix.edges, elasticity, EngineConfig(node_mass=node_mass, dt=dt))
        history = engine.run(
            LatticeState(positions=matrix.reference_positions.copy(), velocities=v_kernel), steps=steps
        )
        peak_elastic = max(bond_energy(state.positions, matrix.edges, elasticity) for state, _ in history)
        rows.append(AmplitudeScalingRow(speed=float(speed), peak_elastic_energy=float(peak_elastic)))
    return rows


def observed_scaling_order(row_a: AmplitudeScalingRow, row_b: AmplitudeScalingRow) -> float | None:
    """`log(E_b/E_a) / log(speed_b/speed_a)` — the empirical power `p`
    such that `peak_elastic_energy ~ speed**p` between these two
    amplitudes. None if either peak is not strictly positive (nothing
    to take a logarithm of).
    """
    if row_a.peak_elastic_energy <= 0 or row_b.peak_elastic_energy <= 0:
        return None
    return float(
        np.log(row_b.peak_elastic_energy / row_a.peak_elastic_energy)
        / np.log(row_b.speed / row_a.speed)
    )


def transverse_samples_to_table(samples: list[TransverseSample]) -> list[dict[str, object]]:
    return [
        {
            "time": s.time,
            "total_energy": s.total_energy,
            "kinetic_energy": s.kinetic_energy,
            "elastic_energy": s.elastic_energy,
            "energy_weighted_radius": s.energy_weighted_radius,
            "max_displacement": s.max_displacement,
            "max_speed": s.max_speed,
            "max_bond_extension": s.max_bond_extension,
            "displacement_kernel_fraction": s.displacement_kernel_fraction,
            "velocity_kernel_fraction": s.velocity_kernel_fraction,
        }
        for s in samples
    ]


def write_transverse_samples_csv(samples: list[TransverseSample], path: Path) -> None:
    table = transverse_samples_to_table(samples)
    if not table:
        raise ValueError("no samples to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
