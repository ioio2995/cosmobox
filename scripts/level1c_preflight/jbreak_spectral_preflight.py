"""1C-4a Phase B -- exploratory, non-normative spectral preflight for the
j_break Hamiltonian case at S=3 (docs/governance/current-task.md).

EXPLORATORY_PREFLIGHT / NON_NORMATIVE / DISPOSABLE. Determines whether
triangle-S3-j_break and ring5-S3-j_break remain spectrally exploitable
for a future inter-S comparison, and whether their spectral windows,
target-group resolution, symmetry labels, self-correlator sum rule, and
local reflection symmetry are consistent with what is already accepted
at S=2. Produces NO normative result: no manifest edited, no write under
/workspaces/level1b_campaign_output/, no call to
launch_normative_campaign/run_campaign/write_case_success/
write_case_failure, no evaluate_robustness/compute_gamma_o call.

Reuses only already-accepted primitives (Level0 diagonalization,
target_selection.select_target_group unchanged, matching.py unchanged,
local_observables.validate_flavor_total_sum unchanged) -- never a second
implementation of any formula. S=2 candidate match keys are read
directly from the already-accepted, immutable artifacts under
/workspaces/level1b_campaign_output/runs/{geometry}-S2-j_break-.../
records.jsonl, in read-only mode, never recomputed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import numpy as np

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import reflection_unitary_automorphism, translation_unitary_automorphism
from cosmobox.level1.local_observables import (
    FLAVOR_TOTAL_SUM_TOLERANCE,
    build_local_flavor_generators,
    flavor_correlator_connected_group,
    validate_flavor_total_sum,
)
from cosmobox.level1.matching import (
    NOT_APPLICABLE,
    NUMERIC,
    UNAVAILABLE,
    SpectralGroupMatchKey,
    SymmetryLabel,
    compute_restricted_symmetry_label,
    compute_twice_T,
    match_spectral_group,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, canonical_multiplet_expectation, extract_group_state
from experiments.level1.manifest import load_manifest
from experiments.level1.target_selection import SELECTED, select_target_group

N_FLAVORS = 2
REPOSITORY_COMMIT = "df6022d79118c693ee5928a88c99e553543948a1"
PREFLIGHT_ID = "level1c-jbreak-preflight-s3-exploratory"
SECTOR_ID = "default"

CANDIDATE_WINDOW = {"triangle": 16, "ring5": 24}
EXPLORATORY_WINDOW = {"triangle": 32, "ring5": 48}

# Already-accepted S=2 j_break normative artifacts, read-only, never
# recomputed and never modified.
S2_ARTIFACT_DIR = {
    "triangle": "/workspaces/level1b_campaign_output/runs/triangle-S2-j_break-default-7a973923a11def77",
    "ring5": "/workspaces/level1b_campaign_output/runs/ring5-S2-j_break-default-fd5be072a5e8b23e",
}
# Already-frozen manifest grid values for the S=2 j_break cases (used
# only to reconstruct low_window_truncated per inter_s.py's own logic,
# never to recompute a spectrum).
S2_PHYSICAL_DIMENSION = {"triangle": 88, "ring5": 1000}
S2_SPECTRAL_WINDOW = {"triangle": 16, "ring5": 24}


def _j_tuple(geometry: str, n_nodes: int) -> tuple[float, ...]:
    return tuple(1.5 if node == 0 else 1.0 for node in range(n_nodes))


def _low_window_truncated_s2(geometry: str) -> bool:
    """Reproduces scripts/level1b_analysis/inter_s.py's own
    _low_window_truncated exactly (dense path only, both S=2 j_break
    cases have physical_dimension <= max_dense_dimension=2000):
    min(spectral_window, dimension) < dimension. Never hardcoded."""
    dimension = S2_PHYSICAL_DIMENSION[geometry]
    window = S2_SPECTRAL_WINDOW[geometry]
    computed = min(window, dimension)
    return computed < dimension


def _load_s2_match_keys(geometry: str) -> list[SpectralGroupMatchKey]:
    """Reads the already-accepted S=2 j_break records.jsonl and
    reconstructs one SpectralGroupMatchKey per distinct
    spectral_window_group_index -- read-only, no recomputation.

    Nuance (1C-4a Phase B3, docs/governance/current-task.md): the
    resulting list only ever contains groups that were ACTUALLY
    SERIALIZED in this corpus. If a given twice_T (e.g. ring5's T_max)
    never appears among these keys, the correct statement is "no group
    carrying that twice_T is present in the accepted S=2 j_break corpus"
    -- never "target_selection resolved T_max as not_in_window at S=2",
    which would require the real per-case TargetSelectionOutcome (never
    itself serialized to records.jsonl) to state with certainty."""
    path = f"{S2_ARTIFACT_DIR[geometry]}/records.jsonl"
    by_group: dict[int, dict] = {}
    with open(path) as handle:
        for line in handle:
            record = json.loads(line)
            spectral_group = record["identity"]["spectral_group"]
            group_index = spectral_group["spectral_window_group_index"]
            entry = by_group.setdefault(
                group_index,
                {
                    "status": spectral_group["status"],
                    "multiplicity": spectral_group["multiplicity"],
                    "twice_T": spectral_group["twice_T"],
                    "hamiltonian": record["identity"]["hamiltonian"],
                    "translation": None,
                    "reflection": None,
                },
            )
            if record["record_kind"] == "symmetry_label" and record["observable_kind"] == "translation_character":
                entry["translation"] = record["payload"]
            if record["record_kind"] == "symmetry_label" and record["observable_kind"] == "reflection_character":
                entry["reflection"] = record["payload"]

    def _label(payload: dict | None) -> SymmetryLabel:
        if payload is None:
            raise ValueError(f"{geometry}: a group is missing its translation/reflection symmetry_label record")
        kind = payload["kind"]
        value = None if payload["value"] is None else complex(payload["value"]["real"], payload["value"]["imag"])
        return SymmetryLabel(kind=kind, value=value)

    keys = []
    for group_index, entry in sorted(by_group.items()):
        hamiltonian_identity_without_spin = (
            tuple(float(v) for v in entry["hamiltonian"]["J"]),
            entry["hamiltonian"]["h_is_zero"],
            float(entry["hamiltonian"]["t"]),
            float(entry["hamiltonian"]["g_E"]),
            float(entry["hamiltonian"]["K"]),
        )
        keys.append(
            SpectralGroupMatchKey(
                geometry=geometry,
                hamiltonian_identity_without_spin=hamiltonian_identity_without_spin,
                sector_identity=SECTOR_ID,
                status=entry["status"],
                multiplicity=entry["multiplicity"],
                twice_T=entry["twice_T"],
                translation_label=_label(entry["translation"]),
                reflection_label=_label(entry["reflection"]),
            )
        )
    return keys


@dataclass
class TargetReport:
    target_id: str
    selection_status: str
    group_index: int | None = None
    start_index: int | None = None
    end_index_exclusive: int | None = None
    multiplicity: int | None = None
    twice_T: int | None = None
    spectral_status: str | None = None
    lower_bound_only: bool | None = None
    representative_energy: float | None = None
    translation_label: str | None = None
    reflection_label: str | None = None
    within_candidate_window: bool | None = None
    v23: dict | None = None
    match_verdict: str | None = None
    local_symmetry_checks: list = field(default_factory=list)


WINDOW_SUFFICIENT = "WINDOW_SUFFICIENT"
WINDOW_INSUFFICIENT = "WINDOW_INSUFFICIENT"
PREFLIGHT_INCONCLUSIVE = "PREFLIGHT_INCONCLUSIVE"

NOT_IN_WINDOW = "not_in_window"
AMBIGUOUS = "ambiguous"
STRUCTURALLY_NOT_APPLICABLE = "structurally_not_applicable"


def evaluate_window_verdict(
    reports: list[TargetReport], candidate_window: int, next_complete_group_after_last_target: dict | None
) -> str:
    """Deterministic closure of the WINDOW_* verdict from already-computed
    measurements only -- no energy threshold, no new science, no
    diagonalization. Evaluated in this EXACT, fixed priority order (first
    match wins), so the same inputs always produce the same verdict:

    1. WINDOW_INSUFFICIENT -- returned immediately if ANY target report
       demonstrates, directly and unambiguously, that candidate_window is
       too small for that target:
         (a) selection_status == "not_in_window": the target is absent
             even from the larger, already-frozen exploratory window, so
             a fortiori it is absent from the smaller candidate_window
             too (exploratory_window > candidate_window by construction,
             frozen in Phase A/B) -- this is the ring5 T_max case;
         (b) selection_status == SELECTED with
             end_index_exclusive >= candidate_window: the target IS
             present, but demonstrably positioned at or beyond the
             candidate_window boundary.
       Neither case requires any judgement about *why* -- both are
       structural facts already measured.

    2. PREFLIGHT_INCONCLUSIVE -- returned if (1) did not trigger for any
       target, but the measurements still cannot jointly confirm
       sufficiency, because at least one of:
         (a) a target's selection_status is "ambiguous" or
             "structurally_not_applicable" (a structural indecision, not
             a demonstrated window-size fact);
         (b) a SELECTED-and-within-candidate_window target has
             lower_bound_only=True (its completeness cannot be
             confirmed);
         (c) a SELECTED-and-complete target has twice_T unresolved
             (None), or translation_label/reflection_label ==
             "unavailable" ("unavailable" is a computation that failed
             to resolve, never treated as equivalent to "not_applicable"
             or "numeric", exactly as matching.py itself never conflates
             the three SymmetryLabel kinds);
         (d) next_complete_group_after_last_target is None -- the
             exploratory window itself ends before a complete group
             beyond the highest selected target could be observed, so
             the required structural margin (Phase A §4/§5) was never
             actually demonstrated, one way or the other;
         (e) a target's V23 result is not (applicable=True and
             is_valid=True), or its local_symmetry_checks list is EMPTY
             (1C-4a Phase B3 corrective: an omitted check must never be
             read as a passing one), or one of its local-reflection
             checks (its own is_valid field) is False -- a pipeline-
             consistency gap, never itself evidence that the WINDOW is
             mis-sized (a V23 failure could equally be a bug elsewhere);
             reported here as inconclusive for the window question
             specifically, while preflight_integrity_pass (computed
             separately, never folded into this verdict) is what
             actually flags a V23 failure.

    3. WINDOW_SUFFICIENT -- only if neither (1) nor (2) triggered for any
       target, i.e. every target is SELECTED, complete_multiplet,
       lower_bound_only=False, strictly within candidate_window, with
       resolved twice_T, translation_label=="not_applicable",
       reflection_label=="numeric", a passing V23, at least one local-
       reflection check actually present and all of them passing, AND a
       complete group is observed beyond the highest selected target.
    """
    for report in reports:
        if report.selection_status == NOT_IN_WINDOW:
            return WINDOW_INSUFFICIENT
        if report.selection_status == SELECTED and report.end_index_exclusive >= candidate_window:
            return WINDOW_INSUFFICIENT

    for report in reports:
        if report.selection_status in (AMBIGUOUS, STRUCTURALLY_NOT_APPLICABLE):
            return PREFLIGHT_INCONCLUSIVE
        if report.selection_status != SELECTED:
            continue
        if report.lower_bound_only:
            return PREFLIGHT_INCONCLUSIVE
        if report.spectral_status != COMPLETE_MULTIPLET:
            return PREFLIGHT_INCONCLUSIVE
        if report.twice_T is None:
            return PREFLIGHT_INCONCLUSIVE
        if report.translation_label == UNAVAILABLE or report.reflection_label == UNAVAILABLE:
            return PREFLIGHT_INCONCLUSIVE
        if report.translation_label != NOT_APPLICABLE or report.reflection_label != NUMERIC:
            return PREFLIGHT_INCONCLUSIVE
        if report.v23 is None or not (report.v23.get("applicable") is True and report.v23.get("is_valid") is True):
            return PREFLIGHT_INCONCLUSIVE
        if len(report.local_symmetry_checks) == 0:
            # An empty list must never pass silently (a pipeline
            # omission is not evidence of a passing check) -- a
            # SELECTED+complete_multiplet target relevant to this
            # preflight is always expected to carry at least one local-
            # reflection check (1 for triangle, 2 for ring5).
            return PREFLIGHT_INCONCLUSIVE
        for symmetry_check in report.local_symmetry_checks:
            if symmetry_check["is_valid"] is not True:
                return PREFLIGHT_INCONCLUSIVE

    if next_complete_group_after_last_target is None:
        return PREFLIGHT_INCONCLUSIVE

    return WINDOW_SUFFICIENT


def compute_preflight_integrity(reports: list[TargetReport]) -> bool:
    """False iff any report with selection_status==SELECTED and
    spectral_status==COMPLETE_MULTIPLET does NOT carry a fully passing
    V23 -- i.e. report.v23 is None, OR report.v23["applicable"] is not
    True, OR report.v23["is_valid"] is not True. For exactly this class
    of report, V23 is REQUIRED to be present and passing; a missing V23
    here (e.g. an upstream pipeline omission) is treated identically to
    a failing one -- both make integrity False, never silently True by
    the mere absence of a value to check (1C-4a Phase B3 corrective,
    docs/governance/current-task.md).

    A report that is not SELECTED, or is SELECTED but partial_subspace,
    is never required to carry V23 at all -- it is skipped entirely,
    never artificially forced to have one. A genuine structural misuse
    of validate_flavor_total_sum still raises ValueError, exactly as
    accepted in 1C-3b -- this function never catches or reinterprets
    that exception as a scientific result."""
    for report in reports:
        if report.selection_status != SELECTED or report.spectral_status != COMPLETE_MULTIPLET:
            continue
        if report.v23 is None:
            return False
        if not (report.v23.get("applicable") is True and report.v23.get("is_valid") is True):
            return False
    return True


def evaluate_resource_verdict(execution_succeeded: bool) -> str:
    """RESOURCE_FEASIBLE / RESOURCE_BLOCKING only, per 1C-4a Phase B3
    (docs/governance/current-task.md): no pre-registered quantitative
    threshold (runtime seconds, memory bytes) exists yet to distinguish
    a merely-slow-but-fine run from a genuinely marginal one, so
    RESOURCE_MARGINAL is NEVER assigned automatically here -- it remains
    reserved for a future resource contract with its own frozen
    threshold. RESOURCE_FEASIBLE reports only an OPERATIONAL feasibility
    observation (the run completed without a capturable resource
    failure), never a quantitative performance classification.
    RESOURCE_BLOCKING is returned only when execution failed for an
    explicitly capturable resource reason (MemoryError during
    diagonalization) -- never inferred from wall-clock time alone."""
    return "RESOURCE_FEASIBLE" if execution_succeeded else "RESOURCE_BLOCKING"


def run_geometry(geometry: str, manifest) -> dict:
    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    basis = build_basis(lattice, N_FLAVORS, 3, external_charges=None)
    key_index = build_key_index(basis.keys)
    dimension = len(basis.keys)

    params = HamiltonianParameters(
        J=_j_tuple(geometry, n_nodes),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, 3, basis.keys, key_index, params)
    options = SpectrumOptions(
        max_dense_dimension=manifest.resource_guardrails.max_dense_dimension,
        max_sparse_dimension=manifest.resource_guardrails.max_sparse_dimension,
        n_eigenvalues=EXPLORATORY_WINDOW[geometry],
        force=False,
        degeneracy_tolerance=manifest.degeneracy_tolerance,
    )

    try:
        start = time.perf_counter()
        level0_report, eigenvectors = build_level0_report_with_eigenvectors(
            lattice, N_FLAVORS, 3, basis, terms, params, spectrum_options=options
        )
        wall_clock_seconds = time.perf_counter() - start
        resource_execution_success = True
    except MemoryError:
        # RESOURCE_BLOCKING captured explicitly and only here -- never
        # inferred from wall-clock time, never a fabricated threshold.
        return {
            "geometry": geometry,
            "physical_dimension": dimension,
            "candidate_window": CANDIDATE_WINDOW[geometry],
            "exploratory_window": EXPLORATORY_WINDOW[geometry],
            "wall_clock_seconds": None,
            "dense_matrix_storage_estimate_bytes": dimension**2 * 16,
            "resource_verdict": evaluate_resource_verdict(False),
            "window_verdict": PREFLIGHT_INCONCLUSIVE,
            "preflight_integrity_pass": None,
        }

    groups = level0_report.spectrum.degeneracy.groups
    group_states = tuple(extract_group_state(eigenvectors, g) for g in groups)
    flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, 3, basis.keys, key_index)
    translation_automorphism = translation_unitary_automorphism(lattice, N_FLAVORS, 3, basis.keys, key_index, external_charges=None)
    reflection_automorphism = reflection_unitary_automorphism(lattice, N_FLAVORS, 3, basis.keys, key_index, external_charges=None)
    hamiltonian_identity_without_spin = (params.J, True, params.t, params.g_E, params.K)

    targets = manifest.target_groups[geometry]
    reports: list[TargetReport] = []
    selected_group_indices: set[int] = set()

    for target in targets:
        outcome = select_target_group(
            target, groups, group_states, flavor_casimir=flavor_casimir, degeneracy_tolerance=manifest.degeneracy_tolerance
        )
        report = TargetReport(target_id=target.target_id, selection_status=outcome.status)
        if outcome.status == SELECTED:
            group = groups[outcome.group_index]
            report.group_index = outcome.group_index
            report.start_index = group.start_index
            report.end_index_exclusive = group.end_index_exclusive
            report.multiplicity = group.multiplicity_observed
            report.twice_T = outcome.twice_T
            report.spectral_status = outcome.selected_group_status
            report.lower_bound_only = group.lower_bound_only
            report.representative_energy = group.representative_energy
            report.within_candidate_window = (
                report.end_index_exclusive < CANDIDATE_WINDOW[geometry]
                and not group.lower_bound_only
                and outcome.selected_group_status == COMPLETE_MULTIPLET
            )
            selected_group_indices.add(outcome.group_index)

            if outcome.selected_group_status == COMPLETE_MULTIPLET:
                state = group_states[outcome.group_index]
                translation_label = compute_restricted_symmetry_label(terms.total, translation_automorphism, state)
                reflection_label = compute_restricted_symmetry_label(terms.total, reflection_automorphism, state)
                report.translation_label = translation_label.kind
                report.reflection_label = reflection_label.kind

                # twice_T is a property of the GROUP itself, resolved the
                # same way for every selection_kind (runner.py's own
                # _group_twice_T pattern) -- outcome.twice_T is only set
                # for flavor_label targets, never for fundamental/
                # first_excited, so it is never used for matching/V23.
                casimir_expectation = canonical_multiplet_expectation(flavor_casimir, state, hermitian=True)
                resolved_twice_T = compute_twice_T(casimir_expectation)
                report.twice_T = resolved_twice_T

                diagonal = {}
                off_diagonal = {}
                generators = {node: build_local_flavor_generators(lattice, N_FLAVORS, 3, basis.keys, key_index, node) for node in lattice.nodes}
                for i in lattice.nodes:
                    diagonal[i] = flavor_correlator_connected_group(generators[i], generators[i], state).value
                    for j in lattice.nodes:
                        if i != j:
                            off_diagonal[(i, j)] = flavor_correlator_connected_group(generators[i], generators[j], state).value
                validation = validate_flavor_total_sum(outcome.selected_group_status, resolved_twice_T, diagonal, off_diagonal)
                report.v23 = {
                    "applicable": validation.applicable,
                    "measured": validation.measured,
                    "expected": validation.expected,
                    "residual": validation.residual,
                    "is_valid": validation.is_valid,
                    "diagonal": diagonal,
                }

                # Local reflection symmetry (1C-4a Phase B3): reuses the
                # SAME diagonal values just computed for V23, the SAME
                # already-accepted tolerance (FLAVOR_TOTAL_SUM_TOLERANCE,
                # 1C-3b) -- never a new tolerance, never recomputed
                # elsewhere. Site pairing is fixed by the {identity,
                # reflection} residual subgroup already established
                # (1C-2a/1C-2b): triangle pairs {1,2}; ring5 pairs
                # {1,4} and {2,3}.
                if geometry == "triangle":
                    diff = abs(diagonal[1] - diagonal[2])
                    report.local_symmetry_checks.append(
                        {"pair": "D1,D2", "diff": diff, "tolerance": FLAVOR_TOTAL_SUM_TOLERANCE, "is_valid": diff <= FLAVOR_TOTAL_SUM_TOLERANCE}
                    )
                elif geometry == "ring5":
                    diff14 = abs(diagonal[1] - diagonal[4])
                    diff23 = abs(diagonal[2] - diagonal[3])
                    report.local_symmetry_checks.append(
                        {"pair": "D1,D4", "diff": diff14, "tolerance": FLAVOR_TOTAL_SUM_TOLERANCE, "is_valid": diff14 <= FLAVOR_TOTAL_SUM_TOLERANCE}
                    )
                    report.local_symmetry_checks.append(
                        {"pair": "D2,D3", "diff": diff23, "tolerance": FLAVOR_TOTAL_SUM_TOLERANCE, "is_valid": diff23 <= FLAVOR_TOTAL_SUM_TOLERANCE}
                    )

                # Matching S=3 -> S=2
                s3_key = SpectralGroupMatchKey(
                    geometry=geometry,
                    hamiltonian_identity_without_spin=hamiltonian_identity_without_spin,
                    sector_identity=SECTOR_ID,
                    status=outcome.selected_group_status,
                    multiplicity=group.multiplicity_observed,
                    twice_T=resolved_twice_T,
                    translation_label=translation_label,
                    reflection_label=reflection_label,
                )
                s2_candidates = _load_s2_match_keys(geometry)
                match_outcome = match_spectral_group(
                    s3_key,
                    s2_candidates,
                    structurally_applicable=True,
                    low_window_truncated=_low_window_truncated_s2(geometry),
                )
                if match_outcome.status == "exact_label_match":
                    report.match_verdict = "MATCH_CANDIDATE_AVAILABLE"
                elif match_outcome.status == "target_group_not_in_window":
                    report.match_verdict = "MATCH_CANDIDATE_MISSING"
                else:
                    report.match_verdict = "MATCH_AMBIGUOUS"
        reports.append(report)

    # last_selected_target: among SELECTED targets, the one whose group
    # has the largest end_index_exclusive (dedup by group).
    selected_reports = [r for r in reports if r.selection_status == SELECTED]
    last_selected = max(selected_reports, key=lambda r: r.end_index_exclusive) if selected_reports else None

    next_complete_group = None
    if last_selected is not None:
        for group in groups:
            if group.start_index >= last_selected.end_index_exclusive and not group.lower_bound_only:
                next_complete_group = {
                    "start_index": group.start_index,
                    "end_index_exclusive": group.end_index_exclusive,
                    "multiplicity_observed": group.multiplicity_observed,
                    "representative_energy": group.representative_energy,
                }
                break

    # Local reflection symmetry: flattened view of each report's own
    # local_symmetry_checks (computed inline above, not recomputed here).
    local_symmetry = [
        {"target_id": report.target_id, **check} for report in selected_reports for check in report.local_symmetry_checks
    ]

    all_required_targets_selected = all(r.selection_status == SELECTED for r in reports)
    all_targets_within_candidate_window = all_required_targets_selected and all(
        r.within_candidate_window is True for r in reports
    )
    next_complete_group_observed = next_complete_group is not None

    window_verdict = evaluate_window_verdict(reports, CANDIDATE_WINDOW[geometry], next_complete_group)
    preflight_integrity_pass = compute_preflight_integrity(reports)
    resource_verdict = evaluate_resource_verdict(resource_execution_success)

    return {
        "geometry": geometry,
        "physical_dimension": dimension,
        "candidate_window": CANDIDATE_WINDOW[geometry],
        "exploratory_window": EXPLORATORY_WINDOW[geometry],
        "wall_clock_seconds": wall_clock_seconds,
        "dense_matrix_storage_estimate_bytes": dimension**2 * 16,
        "number_of_spectral_groups": len(groups),
        "groups": [
            {
                "index": idx,
                "start_index": g.start_index,
                "end_index_exclusive": g.end_index_exclusive,
                "multiplicity_observed": g.multiplicity_observed,
                "lower_bound_only": g.lower_bound_only,
                "representative_energy": g.representative_energy,
            }
            for idx, g in enumerate(groups)
        ],
        "targets": [vars(r) for r in reports],
        "last_selected_target": last_selected.target_id if last_selected else None,
        "next_complete_group_after_last_target": next_complete_group,
        "next_complete_group_observed": next_complete_group_observed,
        "local_symmetry": local_symmetry,
        "low_window_truncated_s2": _low_window_truncated_s2(geometry),
        "all_required_targets_selected": all_required_targets_selected,
        "all_targets_within_candidate_window": all_targets_within_candidate_window,
        "window_verdict": window_verdict,
        "preflight_integrity_pass": preflight_integrity_pass,
        "resource_verdict": resource_verdict,
    }


def main() -> None:
    manifest = load_manifest()
    results = {}
    for geometry in ("triangle", "ring5"):
        results[geometry] = run_geometry(geometry, manifest)
    output = {
        "preflight_id": PREFLIGHT_ID,
        "mode": "exploratory_preflight",
        "repository_commit": REPOSITORY_COMMIT,
        "results": results,
    }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
