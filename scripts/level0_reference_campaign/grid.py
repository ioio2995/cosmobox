"""Frozen grid definition for the Level0 reference campaign (5B).

72 unique physical configurations:

  15 analytic controls        (5 per geometry x 3 main geometries)
  48 additional sweep points  (4 params x 4 non-reference values x 3 geometries)
   3 spin-truncation points
   6 h/J sensitivity points
  --
  72

The `reference` point of each main geometry (J=t=g_E=K=1, h=0, S=1) is
emitted exactly once, under `{geometry}/reference`, and carries every role
it logically belongs to: analytic control, and midpoint (x=1) of all four
parameter sweeps. It is never regenerated under a sweep-specific id -- the
sweeps below only emit their non-1 values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.level0 import HamiltonianParameters, Level0Experiment, SpectrumOptions, build_lattice

REFERENCE_CAMPAIGN_EXPECTED_RUNS = 72

MAIN_GEOMETRIES: tuple[str, ...] = ("triangle", "ring4", "ring5")
SWEEP_PARAMETERS: tuple[str, ...] = ("J", "t", "g_E", "K")
SWEEP_VALUES: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 4.0)
ADDITIONAL_SWEEP_VALUES: tuple[float, ...] = tuple(x for x in SWEEP_VALUES if x != 1.0)

TRUNCATION_POINTS: tuple[tuple[str, int], ...] = (("triangle", 2), ("triangle", 3), ("ring4", 2))

H_SENSITIVITY_GEOMETRIES: tuple[str, ...] = ("triangle", "ring4")
H_SENSITIVITY_ETAS: tuple[float, ...] = (0.1, 0.25, 0.5)
H_SENSITIVITY_MATRIX = np.array([[0.5, 0.5], [0.5, -0.5]], dtype=np.complex128)

COMMON_SPECTRUM_OPTIONS = SpectrumOptions(
    max_dense_dimension=2000,
    max_sparse_dimension=200_000,
    n_eigenvalues=6,
    tolerance=1e-10,
    max_iterations=None,
    force=False,
    seed=0,
)


@dataclass(frozen=True, slots=True)
class CampaignExperimentSpec:
    """One grid point. `roles` is purely descriptive (manifest grouping) --
    it never enters HamiltonianParameters/Level0Experiment and therefore
    never affects the 5A config_fingerprint."""

    experiment_id: str
    geometry: str
    spin: int
    J: float
    h_eta: float
    t: float
    g_E: float
    K: float
    roles: tuple[str, ...]


def _uniform_h(n_nodes: int, eta: float) -> tuple[np.ndarray, ...]:
    return tuple(eta * H_SENSITIVITY_MATRIX for _ in range(n_nodes))


def spec_to_experiment(spec: CampaignExperimentSpec) -> Level0Experiment:
    lattice = build_lattice(spec.geometry)
    n_nodes = len(lattice.nodes)
    parameters = HamiltonianParameters(
        J=tuple(spec.J for _ in range(n_nodes)),
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


def build_reference_campaign_specs() -> tuple[CampaignExperimentSpec, ...]:
    specs: dict[str, CampaignExperimentSpec] = {}

    def _add(spec: CampaignExperimentSpec) -> None:
        if spec.experiment_id in specs:
            raise ValueError(f"duplicate experiment_id generated: {spec.experiment_id}")
        specs[spec.experiment_id] = spec

    # 1. Five analytic controls per main geometry. `reference` carries every
    #    role it plays: control, reference, and midpoint of all 4 sweeps.
    reference_roles = ("control", "reference") + tuple(f"sweep_{p}" for p in SWEEP_PARAMETERS)
    analytic_controls = {
        "local_only": (0.0, 0.0, 0.0, ("control",)),
        "hopping_only": (1.0, 0.0, 0.0, ("control",)),
        "electric_only": (0.0, 1.0, 0.0, ("control",)),
        "magnetic_only": (0.0, 0.0, 1.0, ("control",)),
        "reference": (1.0, 1.0, 1.0, reference_roles),
    }
    for geometry in MAIN_GEOMETRIES:
        for name, (t, g_E, K, roles) in analytic_controls.items():
            _add(
                CampaignExperimentSpec(
                    experiment_id=f"{geometry}/{name}",
                    geometry=geometry,
                    spin=1,
                    J=1.0,
                    h_eta=0.0,
                    t=t,
                    g_E=g_E,
                    K=K,
                    roles=roles,
                )
            )

    # 2. Additional sweep points (x != 1) for each of J, t, g_E, K.
    for geometry in MAIN_GEOMETRIES:
        for param in SWEEP_PARAMETERS:
            for x in ADDITIONAL_SWEEP_VALUES:
                values = {"J": 1.0, "t": 1.0, "g_E": 1.0, "K": 1.0}
                values[param] = x
                _add(
                    CampaignExperimentSpec(
                        experiment_id=f"{geometry}/sweep_{param}={x}",
                        geometry=geometry,
                        spin=1,
                        J=values["J"],
                        h_eta=0.0,
                        t=values["t"],
                        g_E=values["g_E"],
                        K=values["K"],
                        roles=(f"sweep_{param}",),
                    )
                )

    # 3. Spin-truncation points at the reference couplings.
    for geometry, spin in TRUNCATION_POINTS:
        _add(
            CampaignExperimentSpec(
                experiment_id=f"{geometry}/S={spin}",
                geometry=geometry,
                spin=spin,
                J=1.0,
                h_eta=0.0,
                t=1.0,
                g_E=1.0,
                K=1.0,
                roles=("spin_truncation",),
            )
        )

    # 4. h/J sensitivity points at the reference couplings (eta=0 already
    #    covered by each geometry's `reference` control).
    for geometry in H_SENSITIVITY_GEOMETRIES:
        for eta in H_SENSITIVITY_ETAS:
            _add(
                CampaignExperimentSpec(
                    experiment_id=f"{geometry}/h_eta={eta}",
                    geometry=geometry,
                    spin=1,
                    J=1.0,
                    h_eta=eta,
                    t=1.0,
                    g_E=1.0,
                    K=1.0,
                    roles=("h_sensitivity",),
                )
            )

    result = tuple(specs.values())
    if len(result) != REFERENCE_CAMPAIGN_EXPECTED_RUNS:
        raise ValueError(
            f"generated {len(result)} experiment specs, expected {REFERENCE_CAMPAIGN_EXPECTED_RUNS}"
        )
    return result


def validate_unique_fingerprints(specs: tuple[CampaignExperimentSpec, ...]) -> dict[str, str]:
    """experiment_id -> config_fingerprint. Raises on any fingerprint collision.

    A safety net, not a tolerated-overlap mechanism: the grid above is
    built so no two distinct experiment_ids should ever collide. If they
    do, that is a bug to surface, not a duplicate to silently merge.
    """
    from cosmobox.level0 import compute_config_fingerprint

    fingerprints: dict[str, str] = {}
    seen: dict[str, str] = {}
    for spec in specs:
        fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
        if fingerprint in seen:
            raise ValueError(
                f"config_fingerprint collision between {seen[fingerprint]!r} and {spec.experiment_id!r}"
            )
        seen[fingerprint] = spec.experiment_id
        fingerprints[spec.experiment_id] = fingerprint
    return fingerprints
