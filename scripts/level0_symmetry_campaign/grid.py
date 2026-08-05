"""Frozen grid definition for the Level0 symmetry-diagnostics campaign (6C).

8 unique physical configurations, all at S=2 (M=2, external_charges=None):

  3 reference points     (triangle, ring4, ring5 -- J=1, h=0, t=g_E=K=1)
  3 h_eta sweep points    (ring5 only, at the reference couplings)
  2 spatial J-break points (triangle, ring5 -- J_0=1.5, J_i=1 for i != 0)
  --
  8

n_eigenvalues=16 for every experiment: the spectral window this campaign
diagnoses T^2/translation/reflection over. Does not overlap 5B's grid
(different spin, different geometry/parameter combinations) and does not
duplicate any of 5B's own reference/h_eta points.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.level0 import HamiltonianParameters, Level0Experiment, SpectrumOptions, build_lattice

SYMMETRY_CAMPAIGN_EXPECTED_RUNS = 8

SPIN_REFERENCE = 2
N_EIGENVALUES = 16

MAIN_GEOMETRIES: tuple[str, ...] = ("triangle", "ring4", "ring5")
H_ETA_GEOMETRY = "ring5"
# Same frozen convention as scripts/level0_reference_campaign/grid.py's
# H_SENSITIVITY_ETAS/H_SENSITIVITY_MATRIX -- duplicated here (not imported)
# per the explicit decision that 6C must not depend on the 5B package.
H_ETA_VALUES: tuple[float, ...] = (0.1, 0.25, 0.5)
H_MATRIX = np.array([[0.5, 0.5], [0.5, -0.5]], dtype=np.complex128)

J_BREAK_GEOMETRIES: tuple[str, ...] = ("triangle", "ring5")
J_REFERENCE = 1.0
J_BROKEN_NODE0 = 1.5  # J_0 = 1.5, J_i = 1.0 for i != 0 -- the sole breaking pattern (validated)

COMMON_SPECTRUM_OPTIONS = SpectrumOptions(
    max_dense_dimension=2000,
    max_sparse_dimension=200_000,
    n_eigenvalues=N_EIGENVALUES,
    tolerance=1e-10,
    max_iterations=None,
    force=False,
    seed=0,
    degeneracy_tolerance=1e-10,
)

# Pre-registered validity thresholds (recorded in the manifest before any
# experiment runs, per the validated design -- not a scientific verdict,
# just the numeric context under which the raw diagnostics were produced).
SYMMETRY_CAMPAIGN_THRESHOLDS: dict[str, float] = {
    "degeneracy_tolerance": 1e-10,
    "subspace_orthonormality_tolerance": 1e-8,
    "exact_symmetry_commutator_tolerance": 1e-8,
    "complete_group_restriction_tolerance": 1e-8,
}


@dataclass(frozen=True, slots=True)
class SymmetryCampaignExperimentSpec:
    """One grid point. `roles` is purely descriptive (manifest grouping) --
    it never enters HamiltonianParameters/Level0Experiment and therefore
    never affects the config_fingerprint."""

    experiment_id: str
    geometry: str
    spin: int
    j_pattern: str  # "uniform" | "broken_node0"
    h_eta: float
    t: float
    g_E: float
    K: float
    roles: tuple[str, ...]


def _j_values(n_nodes: int, j_pattern: str) -> tuple[float, ...]:
    if j_pattern == "uniform":
        return tuple(J_REFERENCE for _ in range(n_nodes))
    if j_pattern == "broken_node0":
        return tuple(J_BROKEN_NODE0 if node == 0 else J_REFERENCE for node in range(n_nodes))
    raise ValueError(f"unknown j_pattern {j_pattern!r}")


def _uniform_h(n_nodes: int, eta: float) -> tuple[np.ndarray, ...]:
    return tuple(eta * H_MATRIX for _ in range(n_nodes))


def spec_to_experiment(spec: SymmetryCampaignExperimentSpec) -> Level0Experiment:
    lattice = build_lattice(spec.geometry)
    n_nodes = len(lattice.nodes)
    parameters = HamiltonianParameters(
        J=_j_values(n_nodes, spec.j_pattern),
        h=_uniform_h(n_nodes, spec.h_eta),
        t=spec.t,
        g_E=spec.g_E,
        K=spec.K,
    )
    return Level0Experiment(
        geometry=spec.geometry,
        n_flavors=2,
        spin=spec.spin,
        external_charges=None,
        parameters=parameters,
        spectrum_options=COMMON_SPECTRUM_OPTIONS,
    )


def build_symmetry_campaign_specs() -> tuple[SymmetryCampaignExperimentSpec, ...]:
    specs: dict[str, SymmetryCampaignExperimentSpec] = {}

    def _add(spec: SymmetryCampaignExperimentSpec) -> None:
        if spec.experiment_id in specs:
            raise ValueError(f"duplicate experiment_id generated: {spec.experiment_id}")
        specs[spec.experiment_id] = spec

    for geometry in MAIN_GEOMETRIES:
        _add(
            SymmetryCampaignExperimentSpec(
                experiment_id=f"{geometry}/reference",
                geometry=geometry,
                spin=SPIN_REFERENCE,
                j_pattern="uniform",
                h_eta=0.0,
                t=1.0,
                g_E=1.0,
                K=1.0,
                roles=("reference",),
            )
        )

    for eta in H_ETA_VALUES:
        _add(
            SymmetryCampaignExperimentSpec(
                experiment_id=f"{H_ETA_GEOMETRY}/h_eta={eta}",
                geometry=H_ETA_GEOMETRY,
                spin=SPIN_REFERENCE,
                j_pattern="uniform",
                h_eta=eta,
                t=1.0,
                g_E=1.0,
                K=1.0,
                roles=("h_sensitivity",),
            )
        )

    for geometry in J_BREAK_GEOMETRIES:
        _add(
            SymmetryCampaignExperimentSpec(
                experiment_id=f"{geometry}/j_break",
                geometry=geometry,
                spin=SPIN_REFERENCE,
                j_pattern="broken_node0",
                h_eta=0.0,
                t=1.0,
                g_E=1.0,
                K=1.0,
                roles=("j_break",),
            )
        )

    result = tuple(specs.values())
    if len(result) != SYMMETRY_CAMPAIGN_EXPECTED_RUNS:
        raise ValueError(f"generated {len(result)} experiment specs, expected {SYMMETRY_CAMPAIGN_EXPECTED_RUNS}")
    return result


def validate_unique_fingerprints(specs: tuple[SymmetryCampaignExperimentSpec, ...]) -> dict[str, str]:
    """experiment_id -> config_fingerprint. Raises on any fingerprint collision.

    A safety net, not a tolerated-overlap mechanism: the grid above is
    built so no two distinct experiment_ids should ever collide.
    """
    from cosmobox.level0 import compute_config_fingerprint

    seen: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    for spec in specs:
        fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
        if fingerprint in seen:
            raise ValueError(
                f"config_fingerprint collision between {seen[fingerprint]!r} and {spec.experiment_id!r}"
            )
        seen[fingerprint] = spec.experiment_id
        fingerprints[spec.experiment_id] = fingerprint
    return fingerprints
