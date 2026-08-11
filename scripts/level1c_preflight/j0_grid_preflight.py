"""Blind structural preflight for the frozen J0 grid campaign (1C-6h).

Implements exactly the contract frozen by 1C-6d/1C-6e/1C-6f/1C-6g
(docs/levels/level1c/identifiability-preregistration.md sections 17-18,
docs/governance/current-task.md "Lot 1C-6d".."Lot 1C-6g"):

    DELTA_J0 = 0.25, J0_GRID = {0.5, 0.75, 1.0, 1.25, 1.5}
    PREFLIGHT_CASE_SET = FULL_20_CASE_GRID (2 geometries x 2 S x 5 J0)
    FULL_DENSE_EXPLORATORY_WINDOW = FROZEN
        (exploratory_window = full_spectrum_dimension)
    WINDOW_SELECTION_POLICY = FULL_SPECTRUM_DERIVED_PRODUCTION_WINDOW
    PRODUCTION_WINDOW_RULE = A
        (production_window = last_required_end + 1, or
        full_spectrum_dimension when last_required_end already equals it)
    PRODUCTION_WINDOW_SCOPE = PER_CASE
    PREFLIGHT_INFORMATION_FIREWALL = DEFINED
        (INTERNAL_PREFLIGHT_COMPUTATION / PUBLIC_PREFLIGHT_REPORT)
    ENERGY_PUBLIC_POLICY = INDICES_ONLY
    PREFLIGHT_V23_POLICY = VALIDATE_WITHOUT_EXPOSING_VALUES
    PREFLIGHT_GLOBAL_POLICY = ALL_REQUIRED_CASES
    PREFLIGHT_ARTIFACT_REUSE_FOR_NORMATIVE = NO

This module introduces no new scientific primitive: it orchestrates
already-accepted Level0/Level1 primitives (build_level0_report_with_
eigenvectors, target_selection.select_target_group, matching.
compute_restricted_symmetry_label/compute_twice_T, restricted.
canonical_multiplet_expectation/extract_group_state, local_observables.
build_local_flavor_generators/flavor_correlator_connected_group/
validate_flavor_total_sum) and never modifies matching.py, target_
selection.py, or the Level 1B manifest.

Public/internal separation (the information firewall): every function
whose return value is meant to be read by an operator making a design
decision (window/target-set/delta) returns only PublicTargetReport /
PublicCaseReport / PublicPreflightReport -- dataclasses that structurally
cannot carry a numeric energy, a C_TT_conn value, or a V23
measured/expected/residual (tests assert this by inspecting their
`dataclasses.fields()`). Anything that computes such a value (raw
eigenvalues, C_TT_conn, the V23 dataclass) is a local variable inside
run_case, discarded once the public report is built, and never logged.

CLI: `python -m scripts.level1c_preflight.j0_grid_preflight --help`
prints usage and performs no diagonalization. Actually diagonalizing the
20-case grid requires the explicit `--confirm-run-full-grid` flag -- this
lot (1C-6h) never passes it and never runs the grid.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import (
    UNITARITY_TOLERANCE,
    reflection_unitary_automorphism,
    translation_unitary_automorphism,
)
from cosmobox.level1.local_observables import (
    build_local_flavor_generators,
    flavor_correlator_connected_group,
    validate_flavor_total_sum,
)
from cosmobox.level1.matching import NUMERIC, compute_restricted_symmetry_label, compute_twice_T
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    SpectralGroupState,
    build_restricted_operator,
    canonical_multiplet_expectation,
    extract_group_state,
)
from experiments.level1.manifest import FLAVOR_LABEL, Manifest, TargetGroupSpec, load_manifest
from experiments.level1.target_selection import (
    AMBIGUOUS,
    NOT_IN_WINDOW,
    SELECTED,
    STRUCTURALLY_NOT_APPLICABLE,
    TargetSelectionOutcome,
    select_target_group,
)

# ---------------------------------------------------------------------------
# Frozen grid contract (1C-6d/1C-6e) -- never rederived, never optimized.
# ---------------------------------------------------------------------------

N_FLAVORS = 2
GEOMETRIES: tuple[str, ...] = ("triangle", "ring5")
SPIN_VALUES: tuple[int, ...] = (2, 3)
DELTA_J0 = 0.25
J0_GRID: tuple[float, ...] = (
    1.0 - 2 * DELTA_J0,
    1.0 - DELTA_J0,
    1.0,
    1.0 + DELTA_J0,
    1.0 + 2 * DELTA_J0,
)

PREFLIGHT_CONTRACT_VERSION = "level1c-j0-blind-preflight-v1"
"""Operational version identifier of the frozen 1C-6d..1C-6g contract
this module implements (DELTA_J0=0.25, FULL_20_CASE_GRID,
FULL_DENSE_EXPLORATORY_WINDOW, PRODUCTION_WINDOW_RULE=A,
PRODUCTION_WINDOW_SCOPE=PER_CASE, ENERGY_PUBLIC_POLICY=INDICES_ONLY,
PREFLIGHT_INFORMATION_FIREWALL) -- never a new scientific rule, never a
dynamic date. Bumped only if this already-frozen contract is itself
revised by a future, separately-governed lot."""

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


# ---------------------------------------------------------------------------
# Information firewall (1C-6i/1C-6j correctif): a single, generic,
# constant exception used for every FAIL HARD path in this module other
# than MemoryError-driven RESOURCE_BLOCKING. Several already-accepted
# internal primitives embed a raw numeric physical value in their own
# ValueError message on an internal-consistency failure (e.g.
# restricted._hermitian_aware_normalized_trace's "Tr(O_rest)/multiplicity
# is not finite: {trace}", matching.SymmetryLabel.__post_init__'s "value
# is not finite: {self.value}") -- exactly the class of exception the
# frozen PREFLIGHT_INFORMATION_FIREWALL contract requires never reach
# stdout/stderr/the public report. Raising PreflightInternalFailure()
# `from None` clears __cause__ and sets __suppress_context__=True, so
# standard traceback rendering (traceback.format_exc/print_exc, and the
# default unhandled-exception handler Python itself uses) never displays
# the original exception -- verified directly by test. (The original
# exception object technically remains reachable via __context__ for a
# caller that goes out of its way to inspect it, which no code in this
# module -- or in a normal CLI invocation -- ever does; only
# __cause__/rendered output are asserted, per the exact 1C-6j audit
# request.) This is a FAIL HARD path: it never converts an internal
# failure into a falsely-reassuring case report.
# ---------------------------------------------------------------------------


class PreflightInternalFailure(RuntimeError):
    _PUBLIC_MESSAGE = "internal preflight analysis failed"

    def __init__(self) -> None:
        super().__init__(self._PUBLIC_MESSAGE)


# ---------------------------------------------------------------------------
# Provenance (1C-6j correctif): resolved BEFORE any case is run, so that
# a provenance failure costs zero diagonalizations (section 12 of the
# 1C-6j mandate). manifest_fingerprint reuses Manifest.fingerprint
# verbatim (already computed by load_manifest() -- never a second,
# parallel fingerprint computation). code_commit is the exact, strictly
# validated (40 lowercase hex characters) `git rev-parse HEAD` of the
# code actually executing -- never "unknown"/"dirty"/best-effort: any
# failure to resolve it is FAIL HARD. DIRTY_WORKTREE_POLICY =
# REFUSE_EXECUTION: code_commit alone cannot represent uncommitted local
# modifications, so a non-empty `git status --porcelain` refuses
# execution before any case runs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreflightProvenance:
    code_commit: str
    manifest_fingerprint: str
    preflight_contract_version: str

    def __post_init__(self) -> None:
        if not _GIT_SHA_PATTERN.fullmatch(self.code_commit):
            raise ValueError(f"code_commit must be a 40-character lowercase hex SHA, got {self.code_commit!r}")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if self.preflight_contract_version != PREFLIGHT_CONTRACT_VERSION:
            raise ValueError(
                f"preflight_contract_version must be {PREFLIGHT_CONTRACT_VERSION!r}, "
                f"got {self.preflight_contract_version!r}"
            )


def resolve_code_commit(repo_root: str | None = None) -> str:
    """The exact `git rev-parse HEAD` of `repo_root` (ambient cwd if
    None), strictly validated as 40 lowercase hex characters -- never a
    short SHA, never a fallback value. Any subprocess failure (missing
    git, no commits, non-zero exit) or an unexpected stdout shape is
    FAIL HARD via the single sanitized PreflightInternalFailure, never a
    best-effort placeholder."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        )
    except Exception:
        raise PreflightInternalFailure() from None
    sha = completed.stdout.strip()
    if not _GIT_SHA_PATTERN.fullmatch(sha):
        raise PreflightInternalFailure()
    return sha


def _repository_is_clean(repo_root: str | None = None) -> bool:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True
        )
    except Exception:
        raise PreflightInternalFailure() from None
    return completed.stdout.strip() == ""


def require_clean_worktree(repo_root: str | None = None) -> None:
    """DIRTY_WORKTREE_POLICY = REFUSE_EXECUTION (1C-6j section 9): a
    non-empty `git status --porcelain` refuses execution before any
    case runs -- the public failure message never carries diff content
    or file paths, only the single generic PreflightInternalFailure
    message."""
    if not _repository_is_clean(repo_root):
        raise PreflightInternalFailure()


def resolve_preflight_provenance(manifest: Manifest, *, repo_root: str | None = None) -> PreflightProvenance:
    require_clean_worktree(repo_root)
    code_commit = resolve_code_commit(repo_root)
    return PreflightProvenance(
        code_commit=code_commit,
        manifest_fingerprint=manifest.fingerprint,
        preflight_contract_version=PREFLIGHT_CONTRACT_VERSION,
    )


# ---------------------------------------------------------------------------
# Required/optional target roles (1C-6e/1C-6f section 17.7/18.4).
# T_max is CALIBRATION_ONLY: it never enters last_required_end,
# production_window, or the window verdict.
# ---------------------------------------------------------------------------

TARGET_ROLE_REQUIRED = "REQUIRED"
TARGET_ROLE_OPTIONAL_CALIBRATION = "OPTIONAL_CALIBRATION"
_OPTIONAL_CALIBRATION_TARGET_IDS: tuple[str, ...] = ("T_max",)


def classify_target_role(target_id: str) -> str:
    """T_max is the only OPTIONAL_CALIBRATION target id in the manifest's
    target_groups; every other target_id present for a geometry
    (fundamental, first_excited, T_3_2) is REQUIRED. Geometry-specific
    absence (e.g. triangle never lists T_3_2) is already encoded by the
    manifest itself -- this function never needs to know the geometry."""
    if target_id in _OPTIONAL_CALIBRATION_TARGET_IDS:
        return TARGET_ROLE_OPTIONAL_CALIBRATION
    return TARGET_ROLE_REQUIRED


# ---------------------------------------------------------------------------
# Target-level selection vocabulary (1C-6f section 9/1C-6g section 14).
# ---------------------------------------------------------------------------

TARGET_SELECTED = "selected"
TARGET_NOT_IDENTIFIABLE = "target_not_identifiable"
SUBCAUSE_ABSENT_IN_FULL_SPECTRUM = "target_absent_in_full_spectrum"
SUBCAUSE_SELECTION_AMBIGUOUS = "target_selection_ambiguous"

# ---------------------------------------------------------------------------
# Case-level window vocabulary. TARGET_NOT_IDENTIFIABLE is reused here as
# the highest-priority case-level verdict (a required target could not be
# identified at all -- nothing about window sizing can rescue that).
# ---------------------------------------------------------------------------

WINDOW_SUFFICIENT = "window_sufficient"
WINDOW_INSUFFICIENT = "window_insufficient"
WINDOW_INCONCLUSIVE = "window_inconclusive"

RESOURCE_FEASIBLE = "resource_feasible"
RESOURCE_BLOCKING = "resource_blocking"

# TRACKING_PREFLIGHT_STATUS is exclusive to this preflight (1C-6f section
# 14/1C-6g section 26) -- never TRACKED_ONE_TO_ONE/TRACKED_SPLIT_BRANCH/
# AMBIGUOUS/DISCONTINUOUS/NOT_AVAILABLE, which belong to the final,
# not-yet-implemented, inter-J0 analysis layer.
TRACKING_FEASIBLE = "feasible"
TRACKING_STRUCTURALLY_AMBIGUOUS = "structurally_ambiguous"
TRACKING_NOT_EVALUATED = "not_evaluated"
TRACKING_PREFLIGHT_STATUSES: tuple[str, ...] = (
    TRACKING_FEASIBLE,
    TRACKING_STRUCTURALLY_AMBIGUOUS,
    TRACKING_NOT_EVALUATED,
)

GLOBAL_SUFFICIENT = "global_preflight_sufficient"
GLOBAL_FAIL = "global_preflight_fail"

V23_OK = "v23_ok"
V23_VALIDATION_FAILED = "v23_validation_failed"


# ---------------------------------------------------------------------------
# Case plan (pure, deterministic, no I/O -- 1C-6h section 3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreflightCase:
    geometry: str
    spin: int
    j0: float

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin not in SPIN_VALUES:
            raise ValueError(f"spin must be one of {SPIN_VALUES}, got {self.spin!r}")
        if self.j0 not in J0_GRID:
            raise ValueError(f"j0 must be one of {J0_GRID}, got {self.j0!r}")
        if not self.j0 > 0:
            raise ValueError(f"j0 must be strictly positive, got {self.j0!r}")


def build_j0_grid_plan() -> tuple[PreflightCase, ...]:
    """Exactly the 20 cases, in the frozen deterministic order: geometry,
    then S, then increasing J0 (1C-6e section 27/1C-6g). Order carries no
    scientific meaning (RUN_ORDER_POLICY=IRRELEVANT_BUT_FIXED) -- fixed
    only for auditability."""
    return tuple(
        PreflightCase(geometry=geometry, spin=spin, j0=j0)
        for geometry in GEOMETRIES
        for spin in SPIN_VALUES
        for j0 in J0_GRID
    )


# ---------------------------------------------------------------------------
# Public report structures -- the only surface an operator ever reads.
# Deliberately carry no eigenvalue/representative_energy/min_energy/
# max_energy/energy_gap field, and no C_TT_conn/Delta_C_TT/measured/
# expected/residual field (ENERGY_PUBLIC_POLICY=INDICES_ONLY,
# PREFLIGHT_V23_POLICY=VALIDATE_WITHOUT_EXPOSING_VALUES).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicTargetReport:
    target_id: str
    role: str
    selection_status: str
    subcause: str | None
    group_start_index: int | None
    group_end_index_exclusive: int | None
    multiplicity: int | None
    twice_T: int | None
    translation_label_kind: str | None
    reflection_label_kind: str | None
    reflection_restriction_valid: bool | None
    complete_multiplet: bool | None
    lower_bound_only: bool | None
    v23_applicable: bool | None
    v23_is_valid: bool | None
    v23_status: str | None


@dataclass(frozen=True, slots=True)
class PublicCaseReport:
    geometry: str
    spin: int
    j0: float
    full_spectrum_dimension: int
    eigensolver_dispatch: str
    exploratory_window: int
    production_window: int | None
    last_required_end: int | None
    margin_group_start_index: int | None
    margin_group_end_index_exclusive: int | None
    resource_status: str
    window_status: str
    tracking_preflight_status: str
    targets: tuple[PublicTargetReport, ...]


@dataclass(frozen=True, slots=True)
class PublicPreflightReport:
    provenance: PreflightProvenance
    cases: tuple[PublicCaseReport, ...]
    global_status: str


# ---------------------------------------------------------------------------
# Internal (structural-only, never containing an energy value) per-target
# outcome -- the shared input to every pure derivation function below, so
# they are all testable without any diagonalization (1C-6h section 27/28).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequiredTargetOutcome:
    target_id: str
    role: str
    selection_status: str
    subcause: str | None
    group_index: int | None
    group: SpectralLevelGroup | None
    group_state_status: str | None
    twice_T: int | None
    translation_label_kind: str | None
    reflection_label_kind: str | None
    reflection_restriction_valid: bool | None
    v23_applicable: bool | None
    v23_is_valid: bool | None
    v23_status: str | None

    def __post_init__(self) -> None:
        if self.selection_status not in (TARGET_SELECTED, TARGET_NOT_IDENTIFIABLE):
            raise ValueError(f"selection_status must be selected/target_not_identifiable, got {self.selection_status!r}")
        if (self.selection_status == TARGET_NOT_IDENTIFIABLE) != (self.subcause is not None):
            raise ValueError("subcause must be set if and only if selection_status == target_not_identifiable")
        if self.subcause is not None and self.subcause not in (SUBCAUSE_ABSENT_IN_FULL_SPECTRUM, SUBCAUSE_SELECTION_AMBIGUOUS):
            raise ValueError(f"subcause must be a known subcause, got {self.subcause!r}")


def classify_selection_outcome(
    outcome: TargetSelectionOutcome, *, unresolved_twice_T_present: bool
) -> tuple[str, str | None]:
    """Maps target_selection.TargetSelectionOutcome.status onto the
    cautious public vocabulary (1C-6f section 9): a target is never
    reported "physically absent" merely because the selection rule failed.
    `unresolved_twice_T_present` must only ever be True when the caller
    already restricted it to a flavor_label target and at least one group
    in the FULL spectrum has an unresolved twice_T (compute_twice_T
    returned None) -- for rank-based targets (fundamental/first_excited)
    it must always be False, since NOT_IN_WINDOW there is an unambiguous
    structural fact (fewer than two distinct energy groups exist)."""
    if outcome.status == SELECTED:
        return TARGET_SELECTED, None
    if outcome.status == AMBIGUOUS:
        return TARGET_NOT_IDENTIFIABLE, SUBCAUSE_SELECTION_AMBIGUOUS
    if outcome.status == STRUCTURALLY_NOT_APPLICABLE:
        return TARGET_NOT_IDENTIFIABLE, SUBCAUSE_ABSENT_IN_FULL_SPECTRUM
    if outcome.status == NOT_IN_WINDOW:
        if unresolved_twice_T_present:
            return TARGET_NOT_IDENTIFIABLE, SUBCAUSE_SELECTION_AMBIGUOUS
        return TARGET_NOT_IDENTIFIABLE, SUBCAUSE_ABSENT_IN_FULL_SPECTRUM
    raise ValueError(f"unknown target_selection outcome status {outcome.status!r}")


def compute_required_group_indices(required_outcomes: Sequence[RequiredTargetOutcome]) -> frozenset[int]:
    """Deduplicates by the group actually selected -- two target_ids
    pointing at the same spectral group must count once (1C-6f section
    11/1C-6h section 11)."""
    return frozenset(
        outcome.group_index for outcome in required_outcomes if outcome.selection_status == TARGET_SELECTED
    )


def compute_last_required_end(required_outcomes: Sequence[RequiredTargetOutcome]) -> int | None:
    """None iff no REQUIRED target was SELECTED at all (a case already
    doomed to TARGET_NOT_IDENTIFIABLE)."""
    indices = compute_required_group_indices(required_outcomes)
    if not indices:
        return None
    end_by_index = {
        outcome.group_index: outcome.group.end_index_exclusive
        for outcome in required_outcomes
        if outcome.group_index in indices
    }
    return max(end_by_index.values())


def find_margin_group(groups: Sequence[SpectralLevelGroup], last_required_end: int) -> SpectralLevelGroup | None:
    """The margin group is a pure structural witness (1C-6f section
    4/1C-6g section 18.5): it is never a target, never entered into
    matching or V23. None iff last_required_end already equals the full
    spectrum dimension (the required group is the topmost group of the
    entire spectrum -- see compute_production_window's own fallback)."""
    for group in groups:
        if group.start_index >= last_required_end and not group.lower_bound_only:
            return group
    return None


def compute_production_window(last_required_end: int, full_spectrum_dimension: int) -> int:
    """PRODUCTION_WINDOW_RULE = A (1C-6f section 5/6, corrected from an
    initial B after auditing degeneracy.py's sequential, never-lookahead
    boundary decisions): a single spectrally distinct point after
    last_required_end already proves lower_bound_only=False for the
    required group itself -- the margin group's own completeness is never
    required in the production artifact. Falls back to the full
    dimension exactly when last_required_end already reaches it (no `+1`
    index exists beyond the top of the spectrum)."""
    if last_required_end < full_spectrum_dimension:
        return last_required_end + 1
    return full_spectrum_dimension


def derive_window_decision(
    required_outcomes: Sequence[RequiredTargetOutcome],
    margin_group: SpectralLevelGroup | None,
    last_required_end: int | None,
    full_spectrum_dimension: int,
) -> str:
    """Deterministic, fixed-priority closure (1C-6f section 14/1C-6g
    section 18.15, mirroring 1C-4a's own evaluate_window_verdict
    discipline): (1) any REQUIRED target not identifiable at all always
    wins, regardless of every other condition ; (2) a defensive check that
    every SELECTED required target is genuinely complete_multiplet (an
    invariant already guaranteed by exploratory_window=full_spectrum_
    dimension, per degeneracy.py's own lower_bound_only=(end==n and
    n<dimension) formula, but never merely assumed here) ; (3) the margin
    witness and V23 applicability/validity, both structural, gate
    WINDOW_INCONCLUSIVE, never SUFFICIENT ; (4) SUFFICIENT only if none of
    the above triggered. T_max (never a member of `required_outcomes`)
    never enters this decision."""
    for outcome in required_outcomes:
        if outcome.selection_status == TARGET_NOT_IDENTIFIABLE:
            return TARGET_NOT_IDENTIFIABLE

    for outcome in required_outcomes:
        if outcome.group_state_status != COMPLETE_MULTIPLET:
            return WINDOW_INSUFFICIENT

    if last_required_end is None:
        return WINDOW_INCONCLUSIVE
    if last_required_end < full_spectrum_dimension and margin_group is None:
        return WINDOW_INCONCLUSIVE

    for outcome in required_outcomes:
        if not (outcome.v23_applicable is True and outcome.v23_is_valid is True):
            return WINDOW_INCONCLUSIVE

    return WINDOW_SUFFICIENT


def derive_tracking_preflight_status(required_outcomes: Sequence[RequiredTargetOutcome]) -> str:
    """FEASIBLE/STRUCTURALLY_AMBIGUOUS/NOT_EVALUATED only -- never one of
    the final-analysis tracking verdicts (TRACKED_ONE_TO_ONE etc.), which
    apply to a PAIR of adjacent J0 points, never to a single case."""
    if not required_outcomes:
        return TRACKING_NOT_EVALUATED
    for outcome in required_outcomes:
        if outcome.selection_status == TARGET_NOT_IDENTIFIABLE and outcome.subcause == SUBCAUSE_SELECTION_AMBIGUOUS:
            return TRACKING_STRUCTURALLY_AMBIGUOUS
    for outcome in required_outcomes:
        if outcome.selection_status == TARGET_SELECTED and outcome.reflection_restriction_valid is not True:
            return TRACKING_STRUCTURALLY_AMBIGUOUS
    if all(outcome.selection_status == TARGET_SELECTED for outcome in required_outcomes):
        return TRACKING_FEASIBLE
    return TRACKING_NOT_EVALUATED


def aggregate_preflight(
    provenance: PreflightProvenance, case_reports: Sequence[PublicCaseReport]
) -> PublicPreflightReport:
    """PREFLIGHT_GLOBAL_POLICY = ALL_REQUIRED_CASES (1C-6f section
    18/1C-6g section 27): a single blocking case fails the whole grid --
    never a partial-grid fallback."""
    sufficient = all(
        case.window_status == WINDOW_SUFFICIENT and case.resource_status == RESOURCE_FEASIBLE
        for case in case_reports
    )
    return PublicPreflightReport(
        provenance=provenance,
        cases=tuple(case_reports),
        global_status=GLOBAL_SUFFICIENT if sufficient else GLOBAL_FAIL,
    )


# ---------------------------------------------------------------------------
# V23 -- computed internally, never exposed beyond applicable/is_valid
# (PREFLIGHT_V23_POLICY=VALIDATE_WITHOUT_EXPOSING_VALUES). The broad
# `except Exception` here is deliberate and specific to this one firewall
# boundary: validate_flavor_total_sum's own ValueError messages can embed
# measured/expected/residual (see its docstring), so nothing about the
# exception -- not its type, not its message -- may ever reach the public
# surface. This is not a substitute for the project's existing, narrower
# exception discipline elsewhere (e.g. MemoryError-only resource handling
# below); it exists only at this specific internal/public boundary.
# ---------------------------------------------------------------------------


def sanitize_v23_result(
    status: str,
    twice_T: int | None,
    diagonal_values: Mapping[int, float],
    off_diagonal_values: Mapping[tuple[int, int], float],
) -> tuple[bool | None, bool | None, str]:
    try:
        validation = validate_flavor_total_sum(status, twice_T, diagonal_values, off_diagonal_values)
    except Exception:
        return None, None, V23_VALIDATION_FAILED
    return validation.applicable, validation.is_valid, V23_OK


# ---------------------------------------------------------------------------
# R_rest^2 = I on the RESTRICTED reflection operator (1C-6h correctif,
# ChatGPT audit): the frozen contract requires validating the involution
# of R_rest = Psi^dagger R Psi for the SELECTED group's own subspace --
# never the global unitary R alone, whose square is always exactly the
# identity on the FULL Hilbert space by construction of a reflection
# automorphism, and therefore proves nothing about how R acts once
# restricted to one specific degenerate multiplet.
#
# Reuses restricted.build_restricted_operator verbatim -- never a second
# construction of Psi^dagger R Psi (already built identically by
# matching.compute_restricted_symmetry_label for its own unitarity/
# stability checks) -- and automorphisms.UNITARITY_TOLERANCE verbatim,
# never a newly invented tolerance: R_rest^2=I is exactly the same style
# of Frobenius-distance-from-identity check on a low-dimensional
# double-precision operator that UNITARITY_TOLERANCE already governs
# elsewhere in this project (UnitaryAutomorphism.__post_init__'s own
# U^dagger U - I check), now applied to the multiplicity x multiplicity
# restricted operator instead of the full dimension x dimension one.
# ---------------------------------------------------------------------------


def restricted_reflection_squared_identity_defect(
    reflection_unitary: sp.spmatrix, group_state: SpectralGroupState
) -> float:
    r_rest = build_restricted_operator(reflection_unitary, group_state)
    identity = np.eye(r_rest.shape[0], dtype=np.complex128)
    return float(np.linalg.norm(r_rest @ r_rest - identity, "fro"))


# ---------------------------------------------------------------------------
# Orchestration -- performs the real diagonalization. Never unit-tested
# directly (that would require a real diagonalization); every decision it
# delegates to is one of the pure functions above, which are.
# ---------------------------------------------------------------------------


def _build_case_hamiltonian_parameters(n_nodes: int, j0: float) -> HamiltonianParameters:
    """J_i=1 for every site except J_0=j0 -- the same on-site perturbation
    already accepted for the j_break case (docs/levels/level1/
    specification.md section 14), never a new physical model."""
    return HamiltonianParameters(
        J=tuple(j0 if node == 0 else 1.0 for node in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )


def run_case(case: PreflightCase, manifest: Manifest) -> PublicCaseReport:
    lattice = build_lattice(case.geometry)
    n_nodes = len(lattice.nodes)
    basis = build_basis(lattice, N_FLAVORS, case.spin, external_charges=None)
    key_index = build_key_index(basis.keys)
    full_spectrum_dimension = len(basis.keys)

    params = _build_case_hamiltonian_parameters(n_nodes, case.j0)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, case.spin, basis.keys, key_index, params)
    options = SpectrumOptions(
        max_dense_dimension=manifest.resource_guardrails.max_dense_dimension,
        max_sparse_dimension=manifest.resource_guardrails.max_sparse_dimension,
        n_eigenvalues=full_spectrum_dimension,
        force=False,
        degeneracy_tolerance=manifest.degeneracy_tolerance,
    )

    # Everything below this point is the real per-case analysis phase
    # (1C-6j correctif): a single try/except covers it end to end.
    # MemoryError -> RESOURCE_BLOCKING (unchanged, never converted into
    # PreflightInternalFailure). Any OTHER exception -> FAIL HARD via the
    # single, generic, sanitized PreflightInternalFailure -- several
    # already-accepted internal primitives called in this phase
    # (canonical_multiplet_expectation, compute_restricted_symmetry_label,
    # build_restricted_operator, flavor_correlator_connected_group) embed
    # a raw numeric value in their own exception message on an internal
    # inconsistency; none of that may ever reach stdout/stderr/the public
    # report. `except Exception` deliberately never becomes `except
    # BaseException`: KeyboardInterrupt/SystemExit must still propagate
    # unsanitized and uninterrupted.
    try:
        level0_report, eigenvectors = build_level0_report_with_eigenvectors(
            lattice, N_FLAVORS, case.spin, basis, terms, params, spectrum_options=options
        )

        groups = level0_report.spectrum.degeneracy.groups
        # Invariant guaranteed by exploratory_window=full_spectrum_dimension
        # (degeneracy.py: lower_bound_only=(end==n and n<dimension), and here
        # n==dimension always) -- never assumed without this direct check.
        if any(group.lower_bound_only for group in groups):
            raise AssertionError(
                "full-spectrum preflight produced a lower_bound_only group -- exploratory_window was not full"
            )

        group_states: tuple[SpectralGroupState, ...] = tuple(extract_group_state(eigenvectors, g) for g in groups)
        flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, case.spin, basis.keys, key_index)
        translation_automorphism = translation_unitary_automorphism(
            lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None
        )
        reflection_automorphism = reflection_unitary_automorphism(
            lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None
        )

        resolved_twice_T: list[int | None] = [
            compute_twice_T(canonical_multiplet_expectation(flavor_casimir, state, hermitian=True))
            for state in group_states
        ]
        any_unresolved_twice_T = any(value is None for value in resolved_twice_T)

        generators_by_node = {
            node: build_local_flavor_generators(lattice, N_FLAVORS, case.spin, basis.keys, key_index, node)
            for node in lattice.nodes
        }

        target_specs: Sequence[TargetGroupSpec] = manifest.target_groups[case.geometry]
        required_outcomes: list[RequiredTargetOutcome] = []
        public_targets: list[PublicTargetReport] = []

        for target in target_specs:
            role = classify_target_role(target.target_id)
            outcome = select_target_group(
                target,
                groups,
                group_states,
                flavor_casimir=flavor_casimir,
                degeneracy_tolerance=manifest.degeneracy_tolerance,
            )
            unresolved_relevant = any_unresolved_twice_T if target.selection_kind == FLAVOR_LABEL else False
            selection_status, subcause = classify_selection_outcome(
                outcome, unresolved_twice_T_present=unresolved_relevant
            )

            group = None
            state = None
            translation_kind = None
            reflection_kind = None
            reflection_restriction_valid = None
            twice_T_value = None
            v23_applicable = v23_is_valid = None
            v23_status = None

            if selection_status == TARGET_SELECTED:
                group = groups[outcome.group_index]
                state = group_states[outcome.group_index]
                twice_T_value = resolved_twice_T[outcome.group_index]
                translation_label = compute_restricted_symmetry_label(terms.total, translation_automorphism, state)
                reflection_label = compute_restricted_symmetry_label(terms.total, reflection_automorphism, state)
                translation_kind = translation_label.kind
                reflection_kind = reflection_label.kind
                if reflection_kind == NUMERIC:
                    restricted_defect = restricted_reflection_squared_identity_defect(
                        reflection_automorphism.unitary, state
                    )
                    reflection_restriction_valid = restricted_defect <= UNITARITY_TOLERANCE
                else:
                    reflection_restriction_valid = False

                if role == TARGET_ROLE_REQUIRED and state.status == COMPLETE_MULTIPLET:
                    diagonal = {
                        node: flavor_correlator_connected_group(
                            generators_by_node[node], generators_by_node[node], state
                        ).value
                        for node in lattice.nodes
                    }
                    off_diagonal = {
                        (i, j): flavor_correlator_connected_group(
                            generators_by_node[i], generators_by_node[j], state
                        ).value
                        for i in lattice.nodes
                        for j in lattice.nodes
                        if i != j
                    }
                    v23_applicable, v23_is_valid, v23_status = sanitize_v23_result(
                        state.status, twice_T_value, diagonal, off_diagonal
                    )

            target_outcome = RequiredTargetOutcome(
                target_id=target.target_id,
                role=role,
                selection_status=selection_status,
                subcause=subcause,
                group_index=outcome.group_index,
                group=group,
                group_state_status=state.status if state is not None else None,
                twice_T=twice_T_value,
                translation_label_kind=translation_kind,
                reflection_label_kind=reflection_kind,
                reflection_restriction_valid=reflection_restriction_valid,
                v23_applicable=v23_applicable,
                v23_is_valid=v23_is_valid,
                v23_status=v23_status,
            )
            if role == TARGET_ROLE_REQUIRED:
                required_outcomes.append(target_outcome)

            public_targets.append(
                PublicTargetReport(
                    target_id=target.target_id,
                    role=role,
                    selection_status=selection_status,
                    subcause=subcause,
                    group_start_index=group.start_index if group is not None else None,
                    group_end_index_exclusive=group.end_index_exclusive if group is not None else None,
                    multiplicity=group.multiplicity_observed if group is not None else None,
                    twice_T=twice_T_value,
                    translation_label_kind=translation_kind,
                    reflection_label_kind=reflection_kind,
                    reflection_restriction_valid=reflection_restriction_valid,
                    complete_multiplet=(state.status == COMPLETE_MULTIPLET) if state is not None else None,
                    lower_bound_only=group.lower_bound_only if group is not None else None,
                    v23_applicable=v23_applicable,
                    v23_is_valid=v23_is_valid,
                    v23_status=v23_status,
                )
            )

        last_required_end = compute_last_required_end(required_outcomes)
        margin_group = find_margin_group(groups, last_required_end) if last_required_end is not None else None
        production_window = (
            compute_production_window(last_required_end, full_spectrum_dimension)
            if last_required_end is not None
            else None
        )
        window_status = derive_window_decision(
            required_outcomes, margin_group, last_required_end, full_spectrum_dimension
        )
        tracking_status = derive_tracking_preflight_status(required_outcomes)

        return PublicCaseReport(
            geometry=case.geometry,
            spin=case.spin,
            j0=case.j0,
            full_spectrum_dimension=full_spectrum_dimension,
            eigensolver_dispatch=level0_report.spectrum.method or "unknown",
            exploratory_window=full_spectrum_dimension,
            production_window=production_window,
            last_required_end=last_required_end,
            margin_group_start_index=margin_group.start_index if margin_group is not None else None,
            margin_group_end_index_exclusive=margin_group.end_index_exclusive if margin_group is not None else None,
            resource_status=RESOURCE_FEASIBLE,
            window_status=window_status,
            tracking_preflight_status=tracking_status,
            targets=tuple(public_targets),
        )
    except MemoryError:
        return PublicCaseReport(
            geometry=case.geometry,
            spin=case.spin,
            j0=case.j0,
            full_spectrum_dimension=full_spectrum_dimension,
            eigensolver_dispatch="unknown",
            exploratory_window=full_spectrum_dimension,
            production_window=None,
            last_required_end=None,
            margin_group_start_index=None,
            margin_group_end_index_exclusive=None,
            resource_status=RESOURCE_BLOCKING,
            window_status=WINDOW_INCONCLUSIVE,
            tracking_preflight_status=TRACKING_NOT_EVALUATED,
            targets=(),
        )
    except Exception:
        raise PreflightInternalFailure() from None


def run_preflight(manifest: Manifest | None = None, *, repo_root: str | None = None) -> PublicPreflightReport:
    """Runs all 20 cases and aggregates them. NEVER called by this lot's
    tests or CLI default path -- reserved for a future execution lot.
    Provenance (including the clean-worktree refusal) is resolved BEFORE
    the first case, so a provenance failure costs zero diagonalizations."""
    resolved_manifest = manifest if manifest is not None else load_manifest()
    provenance = resolve_preflight_provenance(resolved_manifest, repo_root=repo_root)
    plan = build_j0_grid_plan()
    case_reports = [run_case(case, resolved_manifest) for case in plan]
    return aggregate_preflight(provenance, case_reports)


# ---------------------------------------------------------------------------
# CLI -- safe by default. `--help` never diagonalizes anything; running
# the real 20-case grid requires the explicit --confirm-run-full-grid
# flag, never passed by this lot.
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="j0_grid_preflight",
        description=(
            "Blind structural preflight for the frozen J0 grid campaign "
            "(1C-6d..1C-6h). Reports window/resource feasibility only -- "
            "never C_TT_conn/Delta_C_TT/geometric conclusions."
        ),
    )
    parser.add_argument(
        "--confirm-run-full-grid",
        action="store_true",
        help=(
            "Required to actually diagonalize the 20-case grid. Without "
            "this flag the CLI only prints this help text and performs "
            "no diagonalization."
        ),
    )
    return parser


def _public_report_to_json(report: PublicPreflightReport) -> dict:
    return dataclasses.asdict(report)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if not args.confirm_run_full_grid:
        parser.print_help()
        return 0
    report = run_preflight()
    print(json.dumps(_public_report_to_json(report), indent=2))
    return 0 if report.global_status == GLOBAL_SUFFICIENT else 1


if __name__ == "__main__":
    raise SystemExit(main())
