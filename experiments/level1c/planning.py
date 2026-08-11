"""Deterministic Level1C campaign planning. Lot 1C-8b.

Turns an already-loaded, already-validated Level1CManifest into a
deterministic, pure sequence of CampaignCaseSpec objects -- one per grid
point (20 total: 2 geometries x 2 spins x 5 J0). Reuses
experiments.level1.planning's own generic primitives verbatim
(CampaignCaseSpec, compute_case_id, derive_case_seed,
build_ordered_pairs) -- none of them carry any Level1B-only semantics,
so none are reimplemented here. Level1CTargetSpec.role is stripped
before constructing a CampaignCaseSpec (compute_case_id/CampaignCaseSpec
only ever need the underlying TargetGroupSpec; role is a manifest/
reporting-level concept consumed separately by
experiments.level1c.target_selection).

This module performs no diagonalization, no matching, no observable
computation, and launches nothing.
"""

from __future__ import annotations

import numpy as np

from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions
from experiments.level1.manifest import HamiltonianCaseSpec
from experiments.level1.planning import CampaignCaseSpec, build_ordered_pairs, compute_case_id, derive_case_seed

from .manifest import J0_BASELINE, Level1CManifest, hamiltonian_case_id_for_j0


def _build_hamiltonian_parameters(case: HamiltonianCaseSpec, n_nodes: int) -> HamiltonianParameters:
    override_node, override_value = case.J_override
    J = tuple(override_value if node == override_node else case.J_uniform for node in range(n_nodes))
    zero_h = tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes))
    return HamiltonianParameters(J=J, h=zero_h, t=case.t, g_E=case.g_E, K=case.K)


def _build_spectrum_options(manifest: Level1CManifest, spectral_window: int, solver_seed: int) -> SpectrumOptions:
    return SpectrumOptions(
        max_dense_dimension=manifest.resource_guardrails.max_dense_dimension,
        max_sparse_dimension=manifest.resource_guardrails.max_sparse_dimension,
        n_eigenvalues=spectral_window,
        force=False,
        seed=solver_seed,
        degeneracy_tolerance=manifest.degeneracy_tolerance,
    )


def build_level1c_campaign_plan(manifest: Level1CManifest) -> tuple[CampaignCaseSpec, ...]:
    """Deterministic, pure plan: one CampaignCaseSpec per Level1C grid
    point, in the manifest's own grid order (the canonical order already
    accepted for the J0 x S preflight: geometry, then S, then increasing
    J0 -- section 17.15/1C-6g). Builds objects and derives seeds only --
    never diagonalizes, matches, or computes an observable."""
    root_seed = manifest.scientific_seed
    hamiltonian_cases_by_id = {case.hamiltonian_case_id: case for case in manifest.hamiltonian_cases}
    lattice_node_counts: dict[str, int] = {}

    cases: list[CampaignCaseSpec] = []
    for grid_point in manifest.grid:
        if grid_point.geometry not in lattice_node_counts:
            lattice_node_counts[grid_point.geometry] = len(build_lattice(grid_point.geometry).nodes)
        n_nodes = lattice_node_counts[grid_point.geometry]
        target_groups = tuple(spec.target for spec in manifest.target_groups[grid_point.geometry])

        hamiltonian_case_id = grid_point.hamiltonian_case_ids[0]
        hamiltonian_case = hamiltonian_cases_by_id[hamiltonian_case_id]
        hamiltonian_parameters = _build_hamiltonian_parameters(hamiltonian_case, n_nodes)

        for sector_id in manifest.sectors:
            case_id = compute_case_id(
                geometry=grid_point.geometry,
                spin=grid_point.spin,
                hamiltonian_case_id=hamiltonian_case_id,
                hamiltonian_parameters=hamiltonian_parameters,
                sector_id=sector_id,
                spectral_window=grid_point.spectral_window,
                target_groups=target_groups,
            )
            scientific_seed = derive_case_seed(root_seed, case_id, "scientific")
            solver_seed = derive_case_seed(root_seed, case_id, "solver")
            cases.append(
                CampaignCaseSpec(
                    geometry=grid_point.geometry,
                    spin=grid_point.spin,
                    hamiltonian_case_id=hamiltonian_case_id,
                    hamiltonian_parameters=hamiltonian_parameters,
                    sector_id=sector_id,
                    spectral_window=grid_point.spectral_window,
                    physical_dimension=grid_point.physical_dimension,
                    spectrum_options=_build_spectrum_options(manifest, grid_point.spectral_window, solver_seed),
                    target_groups=target_groups,
                    ordered_pairs=build_ordered_pairs(n_nodes),
                    scientific_seed=scientific_seed,
                    solver_seed=solver_seed,
                    validation_rotation_seed=None,
                    case_id=case_id,
                )
            )

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
        raise ValueError(f"build_level1c_campaign_plan produced duplicate case_id(s): {duplicates}")

    return tuple(cases)


def build_baseline_mapping(cases: tuple[CampaignCaseSpec, ...]) -> dict[str, str]:
    """perturbed_case_id -> baseline_case_id, explicit and deterministic
    (section 20.9/20.10: INTER_J0_TRACKING_TOPOLOGY=BASELINE_CENTERED).
    Never a heuristic search: baselines are located exactly by
    hamiltonian_case_id == hamiltonian_case_id_for_j0(J0_BASELINE), then
    matched to their perturbed siblings by (geometry, spin) alone -- the
    only two fields a baseline and its perturbed points share."""
    baseline_id = hamiltonian_case_id_for_j0(J0_BASELINE)
    baselines_by_key: dict[tuple[str, int], str] = {}
    for case in cases:
        if case.hamiltonian_case_id == baseline_id:
            key = (case.geometry, case.spin)
            if key in baselines_by_key:
                raise ValueError(f"more than one baseline case found for (geometry, spin) = {key}")
            baselines_by_key[key] = case.case_id

    mapping: dict[str, str] = {}
    for case in cases:
        if case.hamiltonian_case_id == baseline_id:
            continue
        key = (case.geometry, case.spin)
        if key not in baselines_by_key:
            raise ValueError(f"no baseline case found for perturbed case {case.case_id!r} (geometry, spin) = {key}")
        mapping[case.case_id] = baselines_by_key[key]
    return mapping


def build_tracking_edges(cases: tuple[CampaignCaseSpec, ...]) -> tuple[tuple[str, str], ...]:
    """(perturbed_case_id, baseline_case_id) pairs, one per perturbed
    case -- 16 for the frozen grid (4 baselines x 4 perturbations each,
    section 20.10). Order follows `cases`' own order (the manifest's
    canonical grid order), never a dict/set iteration order."""
    mapping = build_baseline_mapping(cases)
    return tuple((case.case_id, mapping[case.case_id]) for case in cases if case.case_id in mapping)
