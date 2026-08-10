"""Level1C Phase-P single-case execution. Lot 1C-8c.

run_level1c_case executes exactly ONE CampaignCaseSpec (already planned
by experiments.level1c.planning.build_level1c_campaign_plan) against the
Level1CManifest it was planned from: diagonalizes it via Level0 (reusing
cosmobox.level0/cosmobox.level1 primitives verbatim, never duplicating
scientific logic), selects every target via experiments.level1.
target_selection.select_target_group (unchanged), and enforces the
frozen P-phase contract (identifiability-preregistration.md section
20.6/20.7):

  SPECTRAL_STRUCTURE_PRODUCTION  = ALL_COMPLETE_GROUPS_IN_PRODUCTION_WINDOW
  PHYSICAL_OBSERVABLE_PRODUCTION = PREREGISTERED_TARGETS_ONLY

Every COMPLETE_MULTIPLET group in the case's own production_window gets
its three structural symmetry-label records (flavor_casimir_label,
translation_character, reflection_character) -- never a partial group,
which cannot support the tracking CLASS_POOL rule (section 20.12) and
is therefore never structurally productive. C_TT_conn (diagonal and
off-diagonal) and rho_QQ (off-diagonal) are produced only for the
groups that a manifest target actually SELECTED -- regardless of
whether that group is complete or partial (mirroring Level1B's own
runner, which never gates observable production on
meets_normative_requirements: a partial_subspace selection is still a
real result, only ever flagged as such, never suppressed or promoted).

TargetSelectionRecord persistence (D022/1C-8a-fix/1C-8b-fix) is built
here from the same TargetSelectionOutcome objects the selection already
produces -- never a second, independent selection pass. No
TargetSelectionRecord is ever placed among the returned `documents`
(TARGET_SELECTION_PERSISTENCE=CASE_RUN_ARTIFACT_ONLY, 1C-8b-fix): they
are returned separately on Level1CCaseExecutionResult, for the caller
(scripts.level1c_campaign.outputs) to persist into the case run
artifact, never into records.jsonl.

This module never writes to disk, never loops over multiple cases,
never tracks a group across J0, never derives a baseline-non-regression
verdict, and never computes G/flavor_singular_value_ratio/Delta_C_TT --
see the package docstring for the exact authorized scope.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.reports import build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import (
    reflection_unitary_automorphism,
    translation_unitary_automorphism,
)
from cosmobox.level1.local_observables import (
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.matching import (
    NUMERIC,
    SYMMETRY_TOLERANCE,
    SymmetryLabel,
    compute_restricted_symmetry_label,
    compute_twice_T,
)
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
    extract_group_state,
)
from cosmobox.level1.results import build_spectral_group_identity
from experiments.level1.planning import CampaignCaseSpec
from experiments.level1.target_selection import SELECTED, select_target_group
from experiments.level1c.case_artifact import validate_target_selections_match_manifest
from experiments.level1c.manifest import CAMPAIGN_ID, Level1CManifest
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.result_schema import validate_result_record
from experiments.level1c.target_selection import TargetSelectionRecord, build_target_selection_record

N_FLAVORS = 2
SCHEMA_VERSION = "level1c-result-record-v1"
SOURCE_MODULE = "scripts.level1c_campaign.runner"


@dataclass(frozen=True, slots=True)
class Level1CCaseExecutionResult:
    """The in-memory result of executing exactly one Level1C
    CampaignCaseSpec. `documents` are already schema-validated
    (result-record-v1) -- nothing is written to disk. `target_selections`
    is the case-level persistence artifact for D022 (1C-8a section 11,
    1C-8b-fix section 12) -- never itself a document, never mixed into
    `documents`."""

    case_id: str
    target_selections: tuple[TargetSelectionRecord, ...]
    documents: tuple[dict, ...]


def _hamiltonian_parameters_equal(a, b) -> bool:
    """HamiltonianParameters.h holds numpy arrays, so a bare `a == b`
    raises ("truth value of an array is ambiguous") rather than compare
    -- mirrors scripts.level1b_campaign.runner's own private helper
    (rebuilt here, not imported across packages)."""
    if a.J != b.J or a.t != b.t or a.g_E != b.g_E or a.K != b.K:
        return False
    if len(a.h) != len(b.h):
        return False
    return all((x == y).all() for x, y in zip(a.h, b.h))


def _case_matches_planned_case(case: CampaignCaseSpec, planned: CampaignCaseSpec) -> bool:
    """Field-by-field comparison, deliberately not `case == planned`:
    CampaignCaseSpec.hamiltonian_parameters.h holds numpy arrays, so the
    dataclass-generated __eq__ would raise rather than compare."""
    return (
        case.geometry == planned.geometry
        and case.spin == planned.spin
        and case.hamiltonian_case_id == planned.hamiltonian_case_id
        and _hamiltonian_parameters_equal(case.hamiltonian_parameters, planned.hamiltonian_parameters)
        and case.sector_id == planned.sector_id
        and case.spectral_window == planned.spectral_window
        and case.physical_dimension == planned.physical_dimension
        and case.spectrum_options == planned.spectrum_options
        and case.target_groups == planned.target_groups
        and case.ordered_pairs == planned.ordered_pairs
        and case.scientific_seed == planned.scientific_seed
        and case.solver_seed == planned.solver_seed
        and case.validation_rotation_seed == planned.validation_rotation_seed
        and case.case_id == planned.case_id
    )


def _verify_case_belongs_to_manifest(case: CampaignCaseSpec, manifest: Level1CManifest) -> None:
    """`case` must be EXACTLY the CampaignCaseSpec build_level1c_campaign_
    plan(manifest) itself produces for this case_id -- mirrors
    scripts.level1b_campaign.runner's own guard verbatim in spirit. No
    force/override/experimental escape hatch: a case outside the plan is
    always rejected before any diagonalization."""
    planned_cases = build_level1c_campaign_plan(manifest)
    planned_by_case_id = {planned.case_id: planned for planned in planned_cases}
    planned = planned_by_case_id.get(case.case_id)
    if planned is None:
        raise ValueError(
            f"case_id {case.case_id!r} is not present in build_level1c_campaign_plan(manifest) -- this case "
            "was not planned from this manifest"
        )
    if not _case_matches_planned_case(case, planned):
        raise ValueError(
            f"case (case_id={case.case_id!r}) differs from the case build_level1c_campaign_plan(manifest) "
            "itself produces for this case_id on at least one normative field -- this case was not planned "
            "from this manifest"
        )


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return value


def _hamiltonian_identity_payload(case: CampaignCaseSpec) -> dict:
    return {
        "J": [_finite(value, "J") for value in case.hamiltonian_parameters.J],
        "h_is_zero": True,
        "t": _finite(case.hamiltonian_parameters.t, "t"),
        "g_E": _finite(case.hamiltonian_parameters.g_E, "g_E"),
        "K": _finite(case.hamiltonian_parameters.K, "K"),
    }


def _spectral_group_payload(group, group_state, *, spectral_window_group_index: int, twice_T: int | None) -> dict:
    identity = build_spectral_group_identity(
        group, group_state, spectral_window_group_index=spectral_window_group_index, twice_T=twice_T
    )
    return {
        "status": identity.status,
        "multiplicity": identity.multiplicity,
        "twice_T": identity.twice_T,
        "spectral_window_group_index": identity.spectral_window_group_index,
        "group_start_index": group.start_index,
        "group_end_index_exclusive": group.end_index_exclusive,
        "representative_energy": _finite(identity.representative_energy, "representative_energy"),
    }


def _identity_payload(
    case: CampaignCaseSpec,
    spectral_group_payload: dict,
    *,
    path: tuple[int, ...] | None,
    flavor_component: str | None = None,
    normalization: str | None = None,
) -> dict:
    return {
        "geometry": case.geometry,
        "spin": case.spin,
        "n_flavors": N_FLAVORS,
        "hamiltonian": _hamiltonian_identity_payload(case),
        "sector": case.sector_id,
        "spectral_group": spectral_group_payload,
        "path": list(path) if path is not None else None,
        "flavor_component": flavor_component,
        "normalization": normalization,
    }


def _provenance_payload(case: CampaignCaseSpec, group_status: str, *, source_type: str) -> dict:
    return {
        "spectral_status": group_status,
        "source_type": source_type,
        "source_module": SOURCE_MODULE,
        "scientific_seed": case.scientific_seed,
        "solver_seed": case.solver_seed,
        "validation_rotation_seed": case.validation_rotation_seed,
    }


def _document(
    case: CampaignCaseSpec,
    *,
    repository_commit: str,
    manifest_fingerprint: str,
    spectral_group_payload: dict,
    group_status: str,
    record_kind: str,
    observable_kind: str,
    payload: object,
    path: tuple[int, ...] | None = None,
    flavor_component: str | None = None,
    normalization: str | None = None,
) -> dict:
    document = {
        "schema_version": SCHEMA_VERSION,
        "repository_commit": repository_commit,
        "manifest_fingerprint": manifest_fingerprint,
        "campaign_id": CAMPAIGN_ID,
        "identity": _identity_payload(
            case, spectral_group_payload, path=path, flavor_component=flavor_component, normalization=normalization
        ),
        "provenance": _provenance_payload(case, group_status, source_type=record_kind),
        "record_kind": record_kind,
        "observable_kind": observable_kind,
        "payload": payload,
    }
    validate_result_record(document)
    return document


def _flavor_casimir_label_payload(twice_T: int | None) -> dict:
    if twice_T is None:
        return {"kind": "unavailable", "value": None}
    return {"kind": "numeric", "value": {"real": float(twice_T), "imag": 0.0}}


def _symmetry_label_payload(label: SymmetryLabel) -> dict:
    if label.kind == NUMERIC:
        return {"kind": "numeric", "value": {"real": _finite(label.value.real, "value.real"), "imag": _finite(label.value.imag, "value.imag")}}
    return {"kind": label.kind, "value": None}


def _complete_group_indices(group_states) -> tuple[int, ...]:
    """Every group index whose status is COMPLETE_MULTIPLET, in
    ascending order -- exactly SPECTRAL_STRUCTURE_PRODUCTION=
    ALL_COMPLETE_GROUPS_IN_PRODUCTION_WINDOW (section 20.6). A pure
    function of `group_states` alone, independently testable with
    synthetic group states (no diagonalization required)."""
    return tuple(index for index, state in enumerate(group_states) if state.status == COMPLETE_MULTIPLET)


def _selected_group_indices(outcomes) -> tuple[int, ...]:
    """Every distinct group index selected by at least one target, in
    first-seen order -- exactly PHYSICAL_OBSERVABLE_PRODUCTION=
    PREREGISTERED_TARGETS_ONLY (section 20.6), deduplicated (two targets
    may resolve to the same physical group). A pure function of
    `outcomes` alone, independently testable with synthetic
    TargetSelectionOutcome objects (no diagonalization required)."""
    seen: list[int] = []
    seen_set: set[int] = set()
    for outcome in outcomes:
        if outcome.status != SELECTED or outcome.group_index in seen_set:
            continue
        seen_set.add(outcome.group_index)
        seen.append(outcome.group_index)
    return tuple(seen)


def _casimir_expectation(flavor_casimir, group_state) -> float:
    """Dispatch on group_state.status -- the same pattern
    scripts.level1b_campaign.runner's own private _dispatch_expectation
    uses, rebuilt here from the same public primitives (no import of a
    private cross-package symbol)."""
    if group_state.status == COMPLETE_MULTIPLET:
        return canonical_multiplet_expectation(flavor_casimir, group_state, hermitian=True)
    return exploratory_partial_subspace_mean(flavor_casimir, group_state, hermitian=True)


def run_level1c_case(manifest: Level1CManifest, case: CampaignCaseSpec, *, repository_commit: str) -> Level1CCaseExecutionResult:
    """Execute exactly one Level1C CampaignCaseSpec: verify ownership,
    diagonalize, select every target, produce structural records for
    every complete group and observable records for every selected
    target's group, and return everything assembled in memory. Never
    writes to disk."""
    _verify_case_belongs_to_manifest(case, manifest)

    lattice = build_lattice(case.geometry)
    basis = build_basis(lattice, N_FLAVORS, case.spin, external_charges=None)
    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, case.spin, basis.keys, key_index, case.hamiltonian_parameters)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, case.spin, basis, terms, case.hamiltonian_parameters, spectrum_options=case.spectrum_options
    )

    # The FULL, unfiltered spectral-window sequence -- identity is
    # established for every group, complete or partial, before any
    # target selection (D022): a target may select a partial group
    # (e.g. T_max), and select_target_group itself needs the full
    # group_states sequence to operate on.
    groups = level0_report.spectrum.degeneracy.groups
    group_states = tuple(extract_group_state(eigenvectors, group) for group in groups)

    flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, case.spin, basis.keys, key_index)
    hamiltonian = terms.total

    group_twice_Ts = tuple(compute_twice_T(_casimir_expectation(flavor_casimir, state)) for state in group_states)
    spectral_group_payloads = tuple(
        _spectral_group_payload(group, state, spectral_window_group_index=index, twice_T=twice_T)
        for index, (group, state, twice_T) in enumerate(zip(groups, group_states, group_twice_Ts))
    )

    outcomes = tuple(
        select_target_group(
            target,
            groups,
            group_states,
            flavor_casimir=flavor_casimir,
            degeneracy_tolerance=case.spectrum_options.degeneracy_tolerance,
        )
        for target in case.target_groups
    )

    level1c_target_specs = manifest.target_groups[case.geometry]
    target_selections = tuple(
        build_target_selection_record(spec, outcome) for spec, outcome in zip(level1c_target_specs, outcomes)
    )
    validate_target_selections_match_manifest(target_selections, level1c_target_specs)

    documents: list[dict] = []

    # --- Structural records: every COMPLETE group only (section 20.6) ---
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None)
    for group_index in _complete_group_indices(group_states):
        group_state = group_states[group_index]
        twice_T = group_twice_Ts[group_index]
        spectral_payload = spectral_group_payloads[group_index]
        translation_label = compute_restricted_symmetry_label(hamiltonian, translation, group_state, tolerance=SYMMETRY_TOLERANCE)
        reflection_label = compute_restricted_symmetry_label(hamiltonian, reflection, group_state, tolerance=SYMMETRY_TOLERANCE)
        documents.append(
            _document(
                case,
                repository_commit=repository_commit,
                manifest_fingerprint=manifest.fingerprint,
                spectral_group_payload=spectral_payload,
                group_status=group_state.status,
                record_kind="symmetry_label",
                observable_kind="flavor_casimir_label",
                payload=_flavor_casimir_label_payload(twice_T),
            )
        )
        documents.append(
            _document(
                case,
                repository_commit=repository_commit,
                manifest_fingerprint=manifest.fingerprint,
                spectral_group_payload=spectral_payload,
                group_status=group_state.status,
                record_kind="symmetry_label",
                observable_kind="translation_character",
                payload=_symmetry_label_payload(translation_label),
            )
        )
        documents.append(
            _document(
                case,
                repository_commit=repository_commit,
                manifest_fingerprint=manifest.fingerprint,
                spectral_group_payload=spectral_payload,
                group_status=group_state.status,
                record_kind="symmetry_label",
                observable_kind="reflection_character",
                payload=_symmetry_label_payload(reflection_label),
            )
        )

    # --- Physical observables: only for SELECTED targets' groups ---
    # (PHYSICAL_OBSERVABLE_PRODUCTION=PREREGISTERED_TARGETS_ONLY, section
    # 20.6) -- regardless of complete/partial status: a partial selection
    # is a real, flagged result, never suppressed (mirrors Level1B).
    # _selected_group_indices already deduplicates group indices shared
    # by more than one target (e.g. T_3_2 and a coincidentally identical
    # fundamental): each such group's observables are produced exactly
    # once.
    for group_index in _selected_group_indices(outcomes):
        group_state = group_states[group_index]
        spectral_payload = spectral_group_payloads[group_index]
        group_status = group_state.status

        for node in lattice.nodes:
            generators = build_local_flavor_generators(lattice, N_FLAVORS, case.spin, basis.keys, key_index, node)
            self_correlator = flavor_correlator_connected_group(generators, generators, group_state)
            documents.append(
                _document(
                    case,
                    repository_commit=repository_commit,
                    manifest_fingerprint=manifest.fingerprint,
                    spectral_group_payload=spectral_payload,
                    group_status=group_status,
                    record_kind="raw_observable",
                    observable_kind="C_TT_conn",
                    payload=_finite(self_correlator.value, "C_TT_conn"),
                    path=(node, node),
                )
            )

        for i, j in case.ordered_pairs:
            charge_i = build_local_charge_operator(lattice, N_FLAVORS, case.spin, basis.keys, key_index, i)
            charge_j = build_local_charge_operator(lattice, N_FLAVORS, case.spin, basis.keys, key_index, j)
            generators_i = build_local_flavor_generators(lattice, N_FLAVORS, case.spin, basis.keys, key_index, i)
            generators_j = build_local_flavor_generators(lattice, N_FLAVORS, case.spin, basis.keys, key_index, j)

            connected_flavor = flavor_correlator_connected_group(generators_i, generators_j, group_state)
            documents.append(
                _document(
                    case,
                    repository_commit=repository_commit,
                    manifest_fingerprint=manifest.fingerprint,
                    spectral_group_payload=spectral_payload,
                    group_status=group_status,
                    record_kind="raw_observable",
                    observable_kind="C_TT_conn",
                    payload=_finite(connected_flavor.value, "C_TT_conn"),
                    path=(i, j),
                )
            )

            connected_charge = charge_correlator_connected_group(charge_i, charge_j, group_state)
            variance_i = charge_correlator_connected_group(charge_i, charge_i, group_state)
            variance_j = charge_correlator_connected_group(charge_j, charge_j, group_state)
            rho = normalized_charge_correlator(connected_charge.value, variance_i.value, variance_j.value)
            documents.append(
                _document(
                    case,
                    repository_commit=repository_commit,
                    manifest_fingerprint=manifest.fingerprint,
                    spectral_group_payload=spectral_payload,
                    group_status=group_status,
                    record_kind="normalized_observable",
                    observable_kind="rho_QQ",
                    payload={"value": rho.value, "null_reason": rho.null_reason},
                    path=(i, j),
                )
            )

    return Level1CCaseExecutionResult(case_id=case.case_id, target_selections=target_selections, documents=tuple(documents))
