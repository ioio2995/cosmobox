"""Free-boundary propagation diagnostics for EXP-0001 step 5.

Characterizes what the existing compensated-pair injection
(cosmobox.simulation.injection) does on a free-boundary lattice: where
the energy is, how far and how fast it has spread by an energy-weighted
and a threshold-based measure, and from when the perturbation may start
interacting with the boundary. Produces raw, serializable numbers only.
`earliest_boundary_influence_time` is a conservative caution bound, not
an actual reflection detector — see its docstring.

No conclusion about a propagation speed limit, the network's isotropy,
or particle-like structure should be drawn from this module alone: the
injection is a single dipole aligned along one bond (a specific
orientation, not an isotropic source), so any anisotropy observed here
could come from the network, the source orientation, or the spherical
domain cutoff — separating those is step 6, not this one.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig, bond_lengths
from cosmobox.simulation.engine import LatticeState, StepDiagnostics


def node_energy_density(
    positions: np.ndarray,
    velocities: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
) -> np.ndarray:
    """Per-node energy: kinetic energy of the node plus half the elastic
    energy of every bond it participates in, so summing this array
    reproduces the engine's total_energy exactly (verified in tests).
    """
    kinetic = 0.5 * node_mass * np.sum(velocities**2, axis=1)

    lengths = bond_lengths(positions, edges)
    extension = lengths - elasticity.rest_length
    bond_energies = 0.5 * elasticity.stiffness * extension**2

    elastic_share = np.zeros(len(positions))
    np.add.at(elastic_share, edges[:, 0], 0.5 * bond_energies)
    np.add.at(elastic_share, edges[:, 1], 0.5 * bond_energies)

    return kinetic + elastic_share


def radial_energy_profile(
    distances: np.ndarray, energy_density: np.ndarray, bin_edges: np.ndarray
) -> np.ndarray:
    """Total energy within each [bin_edges[i], bin_edges[i+1]) shell,
    using each node's *reference*-position distance from the injection
    center as a fixed radial coordinate (displacements are negligible
    at this amplitude/duration — see the dt-convergence RMS position
    errors, ~1e-5 against a lattice spacing of ~1.7). This is the
    "répartition spatiale de l'énergie" measurement.

    `bin_edges[-1]` must strictly exceed the farthest node's distance,
    or that node (and any other past the last edge) would be silently
    dropped from the profile by `np.digitize`.
    """
    if bin_edges[-1] <= distances.max():
        raise ValueError(
            f"bin_edges upper bound {bin_edges[-1]} must exceed the maximum node "
            f"distance {distances.max()}, otherwise the farthest node(s) would be "
            "silently excluded from the profile"
        )
    shell_indices = np.digitize(distances, bin_edges) - 1
    profile = np.zeros(len(bin_edges) - 1)
    for shell in range(len(profile)):
        profile[shell] = energy_density[shell_indices == shell].sum()
    return profile


def energy_weighted_radius(distances: np.ndarray, energy_density: np.ndarray) -> float:
    total = float(energy_density.sum())
    if total <= 0:
        return 0.0
    return float((energy_density * distances).sum() / total)


def energy_weighted_radial_spread(distances: np.ndarray, energy_density: np.ndarray) -> float:
    total = float(energy_density.sum())
    if total <= 0:
        return 0.0
    mean_radius = energy_weighted_radius(distances, energy_density)
    variance = float((energy_density * (distances - mean_radius) ** 2).sum() / total)
    return float(np.sqrt(max(variance, 0.0)))


def threshold_front_radius(distances: np.ndarray, energy_density: np.ndarray, threshold: float) -> float:
    """Farthest node whose energy density exceeds the absolute
    `threshold` (callers derive it as a fraction of the global maximum
    energy density observed over the whole run, per EXP-0001 §11).
    Returns 0.0 if no node exceeds it.
    """
    above = distances[energy_density > threshold]
    return float(above.max()) if above.size else 0.0


def peak_radius(distances: np.ndarray, energy_density: np.ndarray) -> float:
    """Distance of the single node carrying the most energy — the
    control method EXP-0001 §11 requires alongside the threshold
    method ("une seconde méthode ... doit être conservée comme
    contrôle").
    """
    return float(distances[int(np.argmax(energy_density))])


@dataclass(slots=True)
class PropagationSample:
    time: float
    energy_weighted_radius: float
    energy_weighted_spread: float
    threshold_front_radius: float
    peak_radius: float


def propagation_samples(
    history: list[tuple[LatticeState, StepDiagnostics]],
    distances: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    node_mass: float,
    threshold_fraction: float,
) -> list[PropagationSample]:
    energy_densities = [
        node_energy_density(state.positions, state.velocities, edges, elasticity, node_mass)
        for state, _ in history
    ]
    global_max = max(float(density.max()) for density in energy_densities)
    threshold = threshold_fraction * global_max

    samples = []
    for (_, diagnostics), density in zip(history, energy_densities):
        samples.append(
            PropagationSample(
                time=diagnostics.time,
                energy_weighted_radius=energy_weighted_radius(distances, density),
                energy_weighted_spread=energy_weighted_radial_spread(distances, density),
                threshold_front_radius=threshold_front_radius(distances, density, threshold),
                peak_radius=peak_radius(distances, density),
            )
        )
    return samples


@dataclass(slots=True)
class LinearFit:
    slope: float
    r_squared: float
    n_samples: int


def _linear_fit(times: np.ndarray, values: np.ndarray) -> LinearFit:
    if len(times) < 2:
        raise ValueError("need at least two samples to fit a slope")
    slope, intercept = np.polyfit(times, values, 1)
    predicted = slope * times + intercept
    residuals = values - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((values - values.mean()) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return LinearFit(slope=float(slope), r_squared=r_squared, n_samples=len(times))


def estimate_apparent_velocity(
    samples: list[PropagationSample], contamination_time: float | None
) -> dict[str, LinearFit]:
    """Two independent linear fits against time, restricted to samples
    before `contamination_time` (if any): one against the
    threshold-based front (the method EXP-0001 specifies), one against
    the energy-weighted radius (smoother, less sensitive to the
    threshold's per-node granularity). Both are reported — this module
    does not pick one as "the" apparent velocity.
    """
    usable = [sample for sample in samples if contamination_time is None or sample.time < contamination_time]
    if len(usable) < 2:
        raise ValueError("not enough samples before contamination to estimate a slope")

    times = np.array([sample.time for sample in usable])
    return {
        "threshold_front": _linear_fit(times, np.array([s.threshold_front_radius for s in usable])),
        "energy_weighted_radius": _linear_fit(times, np.array([s.energy_weighted_radius for s in usable])),
    }


def earliest_boundary_influence_time(
    samples: list[PropagationSample], domain_radius: float, caution_fraction: float
) -> float | None:
    """First time the threshold front radius reaches `caution_fraction`
    of the domain radius.

    This is a conservative safety bound, not a reflection detector: it
    marks when the perturbation first approaches/touches the boundary,
    not when a wave reflected off the boundary has actually traveled
    back and disturbed the measured region — that would need a
    separate signal this function does not compute (e.g. a reversal of
    the radial energy flux, a secondary rise in the inner shells'
    energy, or a comparison between two different domain radii).
    Samples after this time should be read as "boundary influence
    cannot yet be ruled out", not as "contaminated". None if the run
    never reaches the caution zone.
    """
    caution_radius = caution_fraction * domain_radius
    for sample in samples:
        if sample.threshold_front_radius >= caution_radius:
            return sample.time
    return None


def samples_to_table(samples: list[PropagationSample]) -> list[dict[str, object]]:
    return [
        {
            "time": sample.time,
            "energy_weighted_radius": sample.energy_weighted_radius,
            "energy_weighted_spread": sample.energy_weighted_spread,
            "threshold_front_radius": sample.threshold_front_radius,
            "peak_radius": sample.peak_radius,
        }
        for sample in samples
    ]


def write_propagation_table_csv(samples: list[PropagationSample], path: Path) -> None:
    table = samples_to_table(samples)
    if not table:
        raise ValueError("no samples to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
