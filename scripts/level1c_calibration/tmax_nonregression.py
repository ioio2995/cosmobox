"""Target-id-free non-regression calibration tool (1C-7c2c).

Implements exactly the calibration contract frozen by 1C-7c2a/1C-7c2a2/
1C-7c2b/1C-7c2b-fix (docs/levels/level1c/identifiability-preregistration.md
section 20.22, `[ETAT COURANT]` block -- the `CALIBRATION_SET=T_max`
block immediately above it is `[HISTORIQUE -- SUPERSEDED BY 1C-7c2b]`
and is never implemented here):

    CALIBRATION_HOLDOUT_KIND = TARGET_ID_FREE_PERSISTED_GROUP_HOLDOUT
    CALIBRATION_CASE_FILTER  = exactly {triangle S=1, ring4 S=1, ring4
        S=2, ring4 S=3, ring5 S=1}, hamiltonian_case_id="reference"
    ALL_5_HOLDOUT_CASES_REQUIRED = YES -- no fallback, no adaptive subset
    CALIBRATION_GROUP_FILTER : persisted, complete_multiplet, twice_T
        resolved, translation/reflection labels NUMERIC, complete
        off-diagonal C_TT_conn/rho_QQ pair sets -- never target_id,
        never a target-selection rule, never an energy rank
    CURRENT_MATCH : same case identity, same spectral_window_group_index
        (a REQUIRED structural reproducibility component HERE, unlike
        inter-J0 tracking, because the Hamiltonian is replayed
        identically), same multiplicity, same twice_T, translation/
        reflection labels concordant via symmetry_labels_match --
        representative_energy is never part of this match
    CALIBRATION_METRIC_CTT/RHO = MAX_ABS, NULLITY_POLICY,
        PAIR_SET_EQUALITY (exact set equality, never an intersection),
        NON_FINITE_POLICY, TOLERANCE_DERIVATION_RULE = CEIL_DECADE_POLICY
        (TOL >= E guaranteed by construction, never via
        round(log10(E), N))

The historical Level1B corpus this tool compares against is never
discovered by glob/mtime/"latest": the caller supplies an explicit
`--historical-output-dir`, and the five required cases are located
deterministically under `<dir>/runs/<case_id>/` -- `case_id` itself is
never invented here, it is derived the same way the historical campaign
itself derived it, via `experiments.level1.planning.build_campaign_plan`
applied to the SAME frozen manifest. No `HistoricalGroupSelector`, no
operator-supplied group identity, no `target_id`, and no reuse of
`experiments.level1.target_selection.select_target_group` exist in this
module: which historical spectral group is examined is decided entirely
by CALIBRATION_GROUP_FILTER, a purely structural rule evaluated over
every group `scripts.level1b_analysis.indexing.build_campaign_artifact_
index` (reused verbatim, never a second JSONL parser) actually finds
persisted -- never by asking what a target rule once selected it for.

This module is a standalone calibration tool, not a campaign runner: it
never produces a J0 != 1 response, a Delta_C_TT, an inter-J0 tracking
verdict, or a geometry-inference result.

CLI: `python -m scripts.level1c_calibration.tmax_nonregression --help`
prints usage and performs no computation. Actually running the
calibration requires the explicit `--confirm-run-calibration` flag --
this lot (1C-7c2c) never passes it and never runs the calibration.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.reports import build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import reflection_unitary_automorphism, translation_unitary_automorphism
from cosmobox.level1.local_observables import (
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.matching import NUMERIC, SymmetryLabel, compute_restricted_symmetry_label, compute_twice_T, symmetry_labels_match
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    SpectralGroupState,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
    extract_group_state,
)
from experiments.level1.manifest import Manifest, load_manifest
from experiments.level1.planning import CampaignCaseSpec, build_campaign_plan, build_ordered_pairs

from scripts.level1b_analysis.indexing import (
    CampaignArtifactIndex,
    IndexedSpectralGroup,
    SpectralGroupIndexError,
    UnresolvedFlavorLabelError,
    build_campaign_artifact_index,
)
from scripts.level1b_analysis.loader import CampaignLoadError
from scripts.level1c_preflight.j0_grid_preflight import PreflightInternalFailure as _GitProvenanceFailure
from scripts.level1c_preflight.j0_grid_preflight import require_clean_worktree as _require_clean_git_worktree
from scripts.level1c_preflight.j0_grid_preflight import resolve_code_commit as _resolve_git_head_sha

# ---------------------------------------------------------------------------
# Frozen calibration contract (docs/levels/level1c/identifiability-
# preregistration.md section 20.22, TARGET_ID_FREE_PERSISTED_GROUP_HOLDOUT)
# -- never rederived, never optimized.
# ---------------------------------------------------------------------------

N_FLAVORS = 2
REFERENCE_HAMILTONIAN_CASE_ID = "reference"

REQUIRED_CASE_ORDER: tuple[tuple[str, int, str], ...] = (
    ("triangle", 1, REFERENCE_HAMILTONIAN_CASE_ID),
    ("ring4", 1, REFERENCE_HAMILTONIAN_CASE_ID),
    ("ring4", 2, REFERENCE_HAMILTONIAN_CASE_ID),
    ("ring4", 3, REFERENCE_HAMILTONIAN_CASE_ID),
    ("ring5", 1, REFERENCE_HAMILTONIAN_CASE_ID),
)
"""Exactly the five cases frozen by 1C-7c2a/1C-7c2a2/1C-7c2b, in a fixed,
explicit, deterministic order (1C-7c3-fix: a tuple, never a bare
frozenset iterated directly -- frozenset iteration order for str/tuple
elements is randomized per-process by CPython's default PYTHONHASHSEED,
confirmed empirically to differ across separate process invocations).
This order governs select_required_cases, the case loop in
run_calibration, and the historical_cases/failure_reasons ordering in
the final artifact -- same-geometry S=1 (triangle, ring5) plus ring4 S
in {1,2,3}, all hamiltonian_case_id="reference", disjoint from the
REQUIRED_NON_REGRESSION baseline (triangle/ring5 S in {2,3}) and from
j_break. ALL_5_HOLDOUT_CASES_REQUIRED=YES: no fallback, no adaptive
subset."""

REQUIRED_CASE_KEYS: frozenset[tuple[str, int, str]] = frozenset(REQUIRED_CASE_ORDER)
"""Derived from REQUIRED_CASE_ORDER (never a second, independently
maintained list) -- reserved for membership testing only (`in`,
set-difference), never iterated directly for anything user-visible or
order-sensitive."""

EXPECTED_HISTORICAL_REPOSITORY_COMMIT = "0ff65ac66b4aa054f739b350cd384c26ecd19752"
"""The frozen provenance value documented in section 20.22 for the 1B-8g
normative execution that produced the five holdout cases. Passed as the
repository_commit parameter to build_campaign_artifact_index, which
cross-checks it against every historical document's own field -- a
mismatch there is exactly a provenance failure, never silently accepted.
historical_campaign_id/historical_manifest_fingerprint are never
separately hardcoded here: they are read directly off the SAME Manifest
object used to build the plan and load the historical index, so they
cannot silently diverge from it."""

CALIBRATION_CONTRACT_VERSION = "level1c-nonregression-calibration-v2"
"""Bumped from v1 (1C-7c2, T_max-based, never accepted): the holdout
kind, case filter, and group filter are all incompatible with v1 -- v1
and v2 are never claimed equivalent."""

CALIBRATION_ARTIFACT_SCHEMA_VERSION = "level1c-nonregression-calibration-artifact-v2"

CTT_OBSERVABLE_KIND = "C_TT_conn"
RHO_OBSERVABLE_KIND = "rho_QQ"


# ---------------------------------------------------------------------------
# Information firewall: a single, generic, constant exception for every
# FAIL HARD path in this module's analysis phase -- the same discipline
# as scripts.level1c_preflight.j0_grid_preflight.PreflightInternalFailure.
# ---------------------------------------------------------------------------


class CalibrationInternalFailure(RuntimeError):
    _PUBLIC_MESSAGE = "internal calibration analysis failed"

    def __init__(self) -> None:
        super().__init__(self._PUBLIC_MESSAGE)


class CalibrationConfigError(ValueError):
    """Raised for a problem in the CALLER's own configuration or in the
    historical artifacts' provenance/structure (a required case missing
    from build_campaign_plan(manifest), a historical artifact directory
    that is missing/invalid/inconsistent, a repository_commit mismatch).
    Deliberately NOT sanitized like CalibrationInternalFailure: this
    reports a problem in already-public configuration/provenance facts
    (case ids, commit hashes, manifest fingerprints), never a computed
    scientific value."""


# ---------------------------------------------------------------------------
# Git provenance -- thin, correctly-named wrappers around the already-
# accepted, generic (git-only, preflight-agnostic) helpers in
# j0_grid_preflight.py. Reused rather than duplicated.
# ---------------------------------------------------------------------------


def resolve_calibration_code_commit(repo_root: str | None = None) -> str:
    try:
        return _resolve_git_head_sha(repo_root)
    except _GitProvenanceFailure:
        raise CalibrationInternalFailure() from None


def require_clean_worktree(repo_root: str | None = None) -> None:
    try:
        _require_clean_git_worktree(repo_root)
    except _GitProvenanceFailure:
        raise CalibrationInternalFailure() from None


# ---------------------------------------------------------------------------
# Environment fingerprint (docs section 20.22/20.23): canonical, JSON-
# safe, deterministic. BLAS/LAPACK identity is read via numpy's own
# structured runtime API, never fragile stdout parsing; if unavailable,
# an explicit "unavailable" structure is produced -- and, per the 1C-
# 7c2c hardening, such an incomplete fingerprint now FAILS the
# calibration rather than being silently accepted as normative.
# ---------------------------------------------------------------------------

_ENVIRONMENT_FINGERPRINT_UNAVAILABLE = "unavailable"


def _blas_lapack_identity() -> dict:
    try:
        config = np.show_config(mode="dicts")
    except Exception:
        config = None
    if not isinstance(config, dict):
        return {
            "blas_name": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "blas_version": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "lapack_name": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "lapack_version": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
        }
    dependencies = config.get("Build Dependencies", {})
    blas = dependencies.get("blas", {}) if isinstance(dependencies, dict) else {}
    lapack = dependencies.get("lapack", {}) if isinstance(dependencies, dict) else {}
    return {
        "blas_name": str(blas.get("name", _ENVIRONMENT_FINGERPRINT_UNAVAILABLE)),
        "blas_version": str(blas.get("version", _ENVIRONMENT_FINGERPRINT_UNAVAILABLE)),
        "lapack_name": str(lapack.get("name", _ENVIRONMENT_FINGERPRINT_UNAVAILABLE)),
        "lapack_version": str(lapack.get("version", _ENVIRONMENT_FINGERPRINT_UNAVAILABLE)),
    }


def build_environment_fingerprint() -> dict:
    return {
        "python_version": platform.python_version(),
        "numpy_version": str(np.__version__),
        "scipy_version": str(scipy.__version__),
        "blas_lapack": _blas_lapack_identity(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }


def environments_are_equal(a: Mapping, b: Mapping) -> bool:
    """Exact field-by-field equality -- no notion of a version being
    "close enough"."""
    return dict(a) == dict(b)


def environment_fingerprint_is_complete(fingerprint: Mapping) -> bool:
    """A normatively required environment fingerprint must never carry
    an "unavailable"/empty value for any of its fields (1C-7c2c
    hardening -- the previous implementation accepted an incomplete
    fingerprint as normative, which the 1C-7c2 audit correctly
    rejected)."""
    for key in ("python_version", "numpy_version", "scipy_version", "platform", "architecture"):
        value = fingerprint.get(key)
        if not value or value == _ENVIRONMENT_FINGERPRINT_UNAVAILABLE:
            return False
    blas_lapack = fingerprint.get("blas_lapack")
    if not isinstance(blas_lapack, Mapping):
        return False
    for key in ("blas_name", "blas_version", "lapack_name", "lapack_version"):
        value = blas_lapack.get(key)
        if not value or value == _ENVIRONMENT_FINGERPRINT_UNAVAILABLE:
            return False
    return True


# ---------------------------------------------------------------------------
# Canonical JSON.
# ---------------------------------------------------------------------------


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n"


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# CEIL_DECADE_POLICY -- corrected (1C-7c2c hardening): no round(log10(E),
# N) (which could push a value slightly above an exact power of ten onto
# the wrong decade, violating TOL >= E). Computes a candidate decade via
# floor(log10(x)), promotes it once if the candidate is still below x,
# and defensively verifies the invariant before returning -- the
# scientific rule itself (10 ** ceil(log10(E))) is unchanged; only its
# float64 implementation is hardened.
# ---------------------------------------------------------------------------


def _power_of_ten_or_fail(exponent: int) -> float:
    """10.0 ** exponent, sanitized: a decade that is not representable
    as a finite float64 (an OverflowError near float64.max, or -- for
    defense in depth on a platform/implementation that behaves
    differently -- a silently returned inf) is never allowed to leak a
    raw Python exception or an invented substitute value (never inf,
    never float64.max: neither is the mathematically correct decade).
    Raises CalibrationInternalFailure instead -- no new physical bound
    is invented, this is purely a representability failure."""
    try:
        value = 10.0**exponent
    except OverflowError:
        raise CalibrationInternalFailure() from None
    if not math.isfinite(value):
        raise CalibrationInternalFailure()
    return value


def derive_absolute_tolerance(e: float) -> float:
    """CEIL_DECADE_POLICY: the smallest power of ten >= E for E > 0, or
    the smallest power of ten >= the float64 machine epsilon for E == 0
    -- a deterministic governance convention (docs section 20.22), never
    a rigorous numerical error bound, never a solver-accuracy claim,
    never a physical-response threshold. Raises ValueError for a
    negative, NaN, or infinite E. If the normative decade itself is not
    representable as a finite float64 (E within roughly one decade of
    float64.max), raises the sanitized CalibrationInternalFailure rather
    than an uncaught OverflowError or an invented substitute -- this is
    a representability limit of float64, never a new physical bound."""
    if isinstance(e, bool) or not isinstance(e, (int, float)):
        raise ValueError(f"E must be a real number, got {e!r}")
    e = float(e)
    if math.isnan(e) or math.isinf(e):
        raise ValueError(f"E must be finite, got {e}")
    if e < 0:
        raise ValueError(f"E must be >= 0, got {e}")

    x = float(np.finfo(np.float64).eps) if e == 0.0 else e
    exponent = math.floor(math.log10(x))
    candidate = _power_of_ten_or_fail(exponent)
    if candidate < x:
        exponent += 1
        candidate = _power_of_ten_or_fail(exponent)
    if candidate < x:
        # Defensive: this should be mathematically unreachable (a single
        # decade promotion always suffices for float64 log10's error
        # magnitude), but the invariant is verified explicitly rather
        # than merely assumed.
        raise CalibrationInternalFailure()
    return candidate


# ---------------------------------------------------------------------------
# Required cases -- selected from the manifest's own deterministic plan,
# never hand-built HamiltonianParameters/SpectrumOptions.
# ---------------------------------------------------------------------------


def select_required_cases(manifest: Manifest) -> dict[tuple[str, int, str], CampaignCaseSpec]:
    """The five CampaignCaseSpec objects (spectral_window/degeneracy_
    tolerance/resource guardrails/Hamiltonian parameters all already
    correctly embedded, exactly as the historical campaign itself used
    them) -- raises CalibrationConfigError before any computation if
    even one is missing from build_campaign_plan(manifest). No fallback,
    no adaptive subset (ALL_5_HOLDOUT_CASES_REQUIRED=YES).

    Returns a dict whose iteration order (a plain Python dict preserves
    insertion order) is exactly REQUIRED_CASE_ORDER -- never derived by
    iterating REQUIRED_CASE_KEYS (a frozenset) directly (1C-7c3-fix)."""
    plan = build_campaign_plan(manifest)
    by_key = {(case.geometry, case.spin, case.hamiltonian_case_id): case for case in plan}
    missing = [key for key in REQUIRED_CASE_ORDER if key not in by_key]
    if missing:
        raise CalibrationConfigError(
            f"required calibration holdout case(s) missing from build_campaign_plan(manifest): {missing}"
        )
    return {key: by_key[key] for key in REQUIRED_CASE_ORDER}


# ---------------------------------------------------------------------------
# Historical loading -- reuses scripts.level1b_analysis.loader/indexing
# verbatim (already-accepted schema validation, provenance cross-checks,
# and group indexing). Never a second JSONL parser.
# ---------------------------------------------------------------------------


def load_historical_index(historical_output_dir: str | Path, manifest: Manifest) -> CampaignArtifactIndex:
    try:
        return build_campaign_artifact_index(
            manifest, Path(historical_output_dir), repository_commit=EXPECTED_HISTORICAL_REPOSITORY_COMMIT
        )
    except (CampaignLoadError, SpectralGroupIndexError, UnresolvedFlavorLabelError) as exc:
        raise CalibrationConfigError(
            f"historical campaign artifacts under {historical_output_dir} are not usable: {exc}"
        ) from exc


def _extract_pairs(documents: Sequence[Mapping], *, record_kind: str, observable_kind: str) -> dict[tuple[int, int], object]:
    result: dict[tuple[int, int], object] = {}
    for document in documents:
        if document["record_kind"] != record_kind or document["observable_kind"] != observable_kind:
            continue
        identity = document["identity"]
        path = identity["path"]
        if path is None or len(path) != 2 or path[0] == path[1]:
            continue
        result[(int(path[0]), int(path[1]))] = document["payload"]
    return result


def extract_historical_ctt_pairs(group: IndexedSpectralGroup) -> dict[tuple[int, int], float]:
    return {
        pair: float(payload)
        for pair, payload in _extract_pairs(group.documents, record_kind="raw_observable", observable_kind=CTT_OBSERVABLE_KIND).items()
    }


def extract_historical_rho_pairs(group: IndexedSpectralGroup) -> dict[tuple[int, int], tuple[float | None, str | None]]:
    return {
        pair: (payload.get("value"), payload.get("null_reason"))
        for pair, payload in _extract_pairs(
            group.documents, record_kind="normalized_observable", observable_kind=RHO_OBSERVABLE_KIND
        ).items()
    }


# ---------------------------------------------------------------------------
# CALIBRATION_GROUP_FILTER -- purely structural, never target_id, never
# an energy value, never an observable magnitude.
# ---------------------------------------------------------------------------


def is_group_eligible(group: IndexedSpectralGroup, *, n_nodes: int) -> bool:
    identity = group.spectral_group_identity
    if identity.status != COMPLETE_MULTIPLET:
        return False
    if identity.twice_T is None:
        return False
    if group.match_key.translation_label.kind != NUMERIC:
        return False
    if group.match_key.reflection_label.kind != NUMERIC:
        return False
    expected_pairs = frozenset(build_ordered_pairs(n_nodes))
    if frozenset(extract_historical_ctt_pairs(group)) != expected_pairs:
        return False
    if frozenset(extract_historical_rho_pairs(group)) != expected_pairs:
        return False
    return True


def eligible_groups_for_case(index: CampaignArtifactIndex, case_id: str, *, n_nodes: int) -> tuple[IndexedSpectralGroup, ...]:
    """index.groups is already canonically ordered (case order from the
    manifest's own plan, then spectral_window_group_index ascending
    within each case -- scripts.level1b_analysis.indexing's own
    construction), so this filter already preserves that order. The
    explicit sort below (1C-7c3-fix) changes no scientific identity --
    it is a pure reordering by the same already-canonical key -- and is
    kept only as defense in depth against that upstream guarantee ever
    silently changing."""
    matching = (group for group in index.groups if group.case_id == case_id and is_group_eligible(group, n_nodes=n_nodes))
    return tuple(sorted(matching, key=lambda group: group.spectral_window_group_index))


# ---------------------------------------------------------------------------
# Current (Level 1C) recomputation -- reuses the case's own frozen
# CampaignCaseSpec.hamiltonian_parameters/spectrum_options verbatim
# (same Hamiltonian, same historical spectral_window, same degeneracy
# tolerance, same resource guardrails -- never redeepened, never a
# second definition). Never uses target_selection.select_target_group:
# which group to examine is decided entirely by the historical side's
# own eligible spectral_window_group_index.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CaseContext:
    n_nodes: int
    groups: tuple
    group_states: tuple[SpectralGroupState, ...]
    flavor_casimir: object
    terms: object
    translation_automorphism: object
    reflection_automorphism: object
    generators_by_node: Mapping[int, Mapping[str, object]]
    charge_by_node: Mapping[int, object]
    ordered_pairs: tuple[tuple[int, int], ...]


def build_case_context(case: CampaignCaseSpec) -> _CaseContext:
    """Performs the real diagonalization for one holdout case, reusing
    case.hamiltonian_parameters/case.spectrum_options exactly as the
    manifest's own plan defines them (same Hamiltonian, same historical
    spectral_window, same degeneracy_tolerance, same resource
    guardrails). NEVER called by this lot's tests directly (that would
    require a real diagonalization) -- reserved for a future execution
    lot."""
    lattice = build_lattice(case.geometry)
    n_nodes = len(lattice.nodes)
    basis = build_basis(lattice, N_FLAVORS, case.spin, external_charges=None)
    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, case.spin, basis.keys, key_index, case.hamiltonian_parameters)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, case.spin, basis, terms, case.hamiltonian_parameters, spectrum_options=case.spectrum_options
    )
    groups = level0_report.spectrum.degeneracy.groups
    group_states = tuple(extract_group_state(eigenvectors, g) for g in groups)
    flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, case.spin, basis.keys, key_index)
    translation_automorphism = translation_unitary_automorphism(
        lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None
    )
    reflection_automorphism = reflection_unitary_automorphism(
        lattice, N_FLAVORS, case.spin, basis.keys, key_index, external_charges=None
    )
    generators_by_node = {
        node: build_local_flavor_generators(lattice, N_FLAVORS, case.spin, basis.keys, key_index, node) for node in lattice.nodes
    }
    charge_by_node = {
        node: build_local_charge_operator(lattice, N_FLAVORS, case.spin, basis.keys, key_index, node) for node in lattice.nodes
    }
    return _CaseContext(
        n_nodes=n_nodes,
        groups=groups,
        group_states=group_states,
        flavor_casimir=flavor_casimir,
        terms=terms,
        translation_automorphism=translation_automorphism,
        reflection_automorphism=reflection_automorphism,
        generators_by_node=generators_by_node,
        charge_by_node=charge_by_node,
        ordered_pairs=build_ordered_pairs(n_nodes),
    )


@dataclass(frozen=True, slots=True)
class CurrentGroupResult:
    multiplicity: int
    twice_T: int | None
    translation_label: SymmetryLabel
    reflection_label: SymmetryLabel
    ctt: Mapping[tuple[int, int], float]
    rho: Mapping[tuple[int, int], tuple[float | None, str | None]]


def _dispatch_casimir_expectation(context: _CaseContext, state: SpectralGroupState) -> float:
    if state.status == COMPLETE_MULTIPLET:
        return canonical_multiplet_expectation(context.flavor_casimir, state, hermitian=True)
    return exploratory_partial_subspace_mean(context.flavor_casimir, state, hermitian=True)


def compute_current_group_result(context: _CaseContext, group_index: int) -> CurrentGroupResult | None:
    """None iff the current recomputation's own window does not reach
    `group_index` at all -- CURRENT_MATCH then fails structurally
    (compare_group), never a search for a different index."""
    if group_index < 0 or group_index >= len(context.groups):
        return None
    state = context.group_states[group_index]

    twice_T = compute_twice_T(_dispatch_casimir_expectation(context, state))
    translation_label = compute_restricted_symmetry_label(context.terms.total, context.translation_automorphism, state)
    reflection_label = compute_restricted_symmetry_label(context.terms.total, context.reflection_automorphism, state)

    variance_by_node = {
        node: charge_correlator_connected_group(context.charge_by_node[node], context.charge_by_node[node], state).value
        for node in context.charge_by_node
    }
    ctt: dict[tuple[int, int], float] = {}
    rho: dict[tuple[int, int], tuple[float | None, str | None]] = {}
    for i, j in context.ordered_pairs:
        ctt[(i, j)] = flavor_correlator_connected_group(context.generators_by_node[i], context.generators_by_node[j], state).value
        connected_qq = charge_correlator_connected_group(context.charge_by_node[i], context.charge_by_node[j], state).value
        moment = normalized_charge_correlator(connected_qq, variance_by_node[i], variance_by_node[j])
        rho[(i, j)] = (moment.value, moment.null_reason)

    return CurrentGroupResult(
        multiplicity=state.multiplicity, twice_T=twice_T, translation_label=translation_label, reflection_label=reflection_label, ctt=ctt, rho=rho
    )


# ---------------------------------------------------------------------------
# CURRENT_MATCH + comparison. Direct indexed lookup only -- never a
# search for an alternative current group index.
# ---------------------------------------------------------------------------

GROUP_MATCH_OK = "MATCH_OK"
GROUP_MATCH_MISSING_CURRENT_INDEX = "MISSING_CURRENT_INDEX"
GROUP_MATCH_MULTIPLICITY_MISMATCH = "MULTIPLICITY_MISMATCH"
GROUP_MATCH_TWICE_T_MISMATCH = "TWICE_T_MISMATCH"
GROUP_MATCH_TRANSLATION_MISMATCH = "TRANSLATION_LABEL_MISMATCH"
GROUP_MATCH_REFLECTION_MISMATCH = "REFLECTION_LABEL_MISMATCH"
GROUP_MATCH_CTT_PAIR_SET_MISMATCH = "CTT_PAIR_SET_MISMATCH"
GROUP_MATCH_RHO_PAIR_SET_MISMATCH = "RHO_PAIR_SET_MISMATCH"
GROUP_MATCH_NON_FINITE_VALUE = "NON_FINITE_VALUE"
GROUP_MATCH_RHO_NULLITY_MISMATCH = "RHO_NULLITY_MISMATCH"
GROUP_MATCH_RHO_NULL_REASON_MISMATCH = "RHO_NULL_REASON_MISMATCH"


@dataclass(frozen=True, slots=True)
class CttPairRecord:
    abs_diff: float


@dataclass(frozen=True, slots=True)
class RhoPairRecord:
    abs_diff: float | None
    both_null: bool


@dataclass(frozen=True, slots=True)
class GroupComparison:
    status: str
    ctt_records: tuple[CttPairRecord, ...]
    rho_records: tuple[RhoPairRecord, ...]

    @property
    def ok(self) -> bool:
        return self.status == GROUP_MATCH_OK


def compare_group(historical_group: IndexedSpectralGroup, current: CurrentGroupResult | None) -> GroupComparison:
    if current is None:
        return GroupComparison(GROUP_MATCH_MISSING_CURRENT_INDEX, (), ())

    identity = historical_group.spectral_group_identity
    if current.multiplicity != identity.multiplicity:
        return GroupComparison(GROUP_MATCH_MULTIPLICITY_MISMATCH, (), ())
    if current.twice_T != identity.twice_T:
        return GroupComparison(GROUP_MATCH_TWICE_T_MISMATCH, (), ())
    if not symmetry_labels_match(current.translation_label, historical_group.match_key.translation_label):
        return GroupComparison(GROUP_MATCH_TRANSLATION_MISMATCH, (), ())
    if not symmetry_labels_match(current.reflection_label, historical_group.match_key.reflection_label):
        return GroupComparison(GROUP_MATCH_REFLECTION_MISMATCH, (), ())

    historical_ctt = extract_historical_ctt_pairs(historical_group)
    historical_rho = extract_historical_rho_pairs(historical_group)
    if set(current.ctt) != set(historical_ctt):
        return GroupComparison(GROUP_MATCH_CTT_PAIR_SET_MISMATCH, (), ())
    if set(current.rho) != set(historical_rho):
        return GroupComparison(GROUP_MATCH_RHO_PAIR_SET_MISMATCH, (), ())

    ctt_records: list[CttPairRecord] = []
    for pair, historical_value in historical_ctt.items():
        current_value = current.ctt[pair]
        if not (math.isfinite(current_value) and math.isfinite(historical_value)):
            return GroupComparison(GROUP_MATCH_NON_FINITE_VALUE, (), ())
        ctt_records.append(CttPairRecord(abs(current_value - historical_value)))

    rho_records: list[RhoPairRecord] = []
    for pair, (historical_value, historical_reason) in historical_rho.items():
        current_value, current_reason = current.rho[pair]
        current_null = current_value is None
        historical_null = historical_value is None
        if current_null != historical_null:
            return GroupComparison(GROUP_MATCH_RHO_NULLITY_MISMATCH, (), ())
        if current_null and historical_null:
            if current_reason != historical_reason:
                return GroupComparison(GROUP_MATCH_RHO_NULL_REASON_MISMATCH, (), ())
            rho_records.append(RhoPairRecord(None, True))
        else:
            if not (math.isfinite(current_value) and math.isfinite(historical_value)):
                return GroupComparison(GROUP_MATCH_NON_FINITE_VALUE, (), ())
            rho_records.append(RhoPairRecord(abs(current_value - historical_value), False))

    return GroupComparison(GROUP_MATCH_OK, tuple(ctt_records), tuple(rho_records))


# ---------------------------------------------------------------------------
# Aggregation -- MAX_ABS over all pooled comparison records.
# ---------------------------------------------------------------------------

RHO_NUMERIC_UNAVAILABLE = "NO_NUMERIC_RHO_CALIBRATION_RECORD"


@dataclass(frozen=True, slots=True)
class CalibrationMetrics:
    e_ctt: float | None
    e_rho: float | None
    rho_numeric_status: str | None


def aggregate_metrics(comparisons: Sequence[GroupComparison]) -> CalibrationMetrics:
    ctt_diffs = [record.abs_diff for comparison in comparisons for record in comparison.ctt_records]
    rho_records = [record for comparison in comparisons for record in comparison.rho_records]
    rho_numeric_diffs = [record.abs_diff for record in rho_records if not record.both_null]

    e_ctt = max(ctt_diffs) if ctt_diffs else None
    if rho_numeric_diffs:
        e_rho = max(rho_numeric_diffs)
        rho_numeric_status = None
    else:
        e_rho = None
        rho_numeric_status = RHO_NUMERIC_UNAVAILABLE if rho_records else None

    return CalibrationMetrics(e_ctt=e_ctt, e_rho=e_rho, rho_numeric_status=rho_numeric_status)


# ---------------------------------------------------------------------------
# Public artifact.
# ---------------------------------------------------------------------------

CALIBRATION_SUCCESS = "SUCCESS"
CALIBRATION_FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class HistoricalCaseSummary:
    case_id: str
    records_sha256: str
    eligible_group_count: int


@dataclass(frozen=True, slots=True)
class CalibrationArtifact:
    status: str
    calibration_contract_version: str
    schema_version: str
    code_commit: str
    historical_campaign_id: str
    historical_manifest_fingerprint: str
    historical_repository_commit: str
    historical_cases: tuple[HistoricalCaseSummary, ...]
    environment_fingerprint: dict
    e_ctt: float | None
    e_rho: float | None
    non_regression_ctt_abs_tol: float | None
    non_regression_rho_abs_tol: float | None
    failure_reasons: tuple[str, ...]


def _records_sha256_for_case(historical_output_dir: Path, case_id: str) -> str:
    return compute_file_sha256(historical_output_dir / "runs" / case_id / "records.jsonl")


# ---------------------------------------------------------------------------
# PRECONDITION_PHASE (1C-7c3-fix): every check below costs zero
# diagonalization. RUN_START is defined as the point immediately after
# this phase returns successfully -- no build_case_context call can
# ever happen before every one of these checks has passed for ALL FIVE
# required cases. A failure here is a PRE-RUN READINESS FAILURE: an
# exception (CalibrationConfigError for configuration/historical-
# archive problems, CalibrationInternalFailure for sanitized internal
# ones), never a CalibrationArtifact, never a diagonalization, and
# therefore never a consumption of CALIBRATION_RUN_POLICY=
# SINGLE_ACCEPTED_RUN's one accepted attempt.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreparedHoldoutCase:
    """One required case, fully validated as usable (>=1 eligible
    group), with everything the RUN_START phase will need already
    computed -- records_sha256 is never recomputed after RUN_START."""

    key: tuple[str, int, str]
    case: CampaignCaseSpec
    n_nodes: int
    eligible_groups: tuple[IndexedSpectralGroup, ...]
    records_sha256: str


def prepare_holdout_cases(
    index: CampaignArtifactIndex, required_cases: Mapping[tuple[str, int, str], CampaignCaseSpec], historical_output_dir: Path
) -> tuple[PreparedHoldoutCase, ...]:
    """Precomputes eligibility for ALL FIVE required cases before any
    diagonalization (1C-7c3-fix, closes the ALL-5 prevalidation gap):
    if even one required case has zero eligible groups, raises
    CalibrationConfigError listing every unusable case found -- never
    after some other cases have already been diagonalized, and never a
    fallback that proceeds with fewer than five. Iterates
    REQUIRED_CASE_ORDER exactly (never a frozenset), so the returned
    tuple's order is deterministic and reused, unchanged, everywhere
    downstream (historical_cases, failure_reasons, the recomputation
    loop itself). No diagonalization happens anywhere in this function
    -- only structural filtering of already-loaded documents and a file
    hash -- but the loop body is still wrapped in a sanitizing
    try/except (matching the discipline used everywhere else in this
    module): an unexpected exception here can only ever be an internal
    inconsistency, never a reason to leak a raw message, and never a
    reason to treat it as a legitimate CalibrationConfigError."""
    prepared: list[PreparedHoldoutCase] = []
    unusable_case_ids: list[str] = []
    try:
        for key in REQUIRED_CASE_ORDER:
            case = required_cases[key]
            geometry, _spin, _hamiltonian_case_id = key
            n_nodes = len(build_lattice(geometry).nodes)
            eligible = eligible_groups_for_case(index, case.case_id, n_nodes=n_nodes)
            records_sha256 = _records_sha256_for_case(historical_output_dir, case.case_id)
            prepared.append(
                PreparedHoldoutCase(key=key, case=case, n_nodes=n_nodes, eligible_groups=eligible, records_sha256=records_sha256)
            )
            if not eligible:
                unusable_case_ids.append(case.case_id)
    except Exception:
        raise CalibrationInternalFailure() from None

    if unusable_case_ids:
        raise CalibrationConfigError(
            f"required calibration holdout case(s) have zero eligible calibration group: {unusable_case_ids}"
        )
    return tuple(prepared)


def run_calibration(
    historical_output_dir: str | Path, manifest: Manifest | None = None, *, repo_root: str | None = None
) -> CalibrationArtifact:
    """Runs the full target-id-free calibration and returns the public
    artifact. NEVER called by this lot's tests or CLI default path --
    reserved for a future, single-invocation execution lot
    (CALIBRATION_RUN_POLICY=SINGLE_ACCEPTED_RUN, unchanged).

    PRECONDITION_PHASE (1C-7c3-fix): select_required_cases -> git
    cleanliness -> current code SHA -> environment fingerprint ->
    environment completeness -> historical archive validation
    (load_historical_index, all 11 planned cases) -> eligibility for
    ALL FIVE required cases (prepare_holdout_cases) -- every one of
    these costs zero diagonalization, and a failure anywhere in this
    phase raises before RUN_START, never producing a CalibrationArtifact
    and never consuming the single accepted run.

    RUN_START: immediately after prepare_holdout_cases returns. Only
    real recomputation (CALIBRATION SCIENTIFIC FAIL, a CalibrationArtifact
    with status=FAIL) happens from this point on."""
    resolved_manifest = manifest if manifest is not None else load_manifest()
    historical_output_dir = Path(historical_output_dir)

    # --- PRECONDITION_PHASE: zero diagonalization above this line, and
    # for every line below until RUN_START. ---
    required_cases = select_required_cases(resolved_manifest)
    require_clean_worktree(repo_root)
    code_commit = resolve_calibration_code_commit(repo_root)
    environment_fingerprint = build_environment_fingerprint()
    if not environment_fingerprint_is_complete(environment_fingerprint):
        raise CalibrationInternalFailure()
    index = load_historical_index(historical_output_dir, resolved_manifest)
    prepared_cases = prepare_holdout_cases(index, required_cases, historical_output_dir)
    # --- RUN_START: prepared_cases holds all five cases, each with
    # >=1 eligible group, everything else about them already validated. ---

    case_summaries: list[HistoricalCaseSummary] = []
    comparisons: list[GroupComparison] = []
    failure_reasons: list[str] = []

    try:
        for prepared in prepared_cases:
            case_summaries.append(
                HistoricalCaseSummary(
                    case_id=prepared.case.case_id, records_sha256=prepared.records_sha256, eligible_group_count=len(prepared.eligible_groups)
                )
            )
            context = build_case_context(prepared.case)
            for historical_group in prepared.eligible_groups:
                current = compute_current_group_result(context, historical_group.spectral_window_group_index)
                comparison = compare_group(historical_group, current)
                comparisons.append(comparison)
                if not comparison.ok:
                    failure_reasons.append(
                        f"case {prepared.case.case_id!r} group {historical_group.spectral_window_group_index}: {comparison.status}"
                    )
    except MemoryError:
        raise CalibrationInternalFailure() from None
    except (CalibrationConfigError, CalibrationInternalFailure):
        raise
    except Exception:
        raise CalibrationInternalFailure() from None

    metrics = aggregate_metrics([comparison for comparison in comparisons if comparison.ok])
    if metrics.e_ctt is None:
        failure_reasons.append("no numeric C_TT_conn calibration record was produced")
    if metrics.e_rho is None:
        failure_reasons.append("no numeric rho_QQ calibration record was produced")

    status = CALIBRATION_SUCCESS if not failure_reasons else CALIBRATION_FAIL
    non_regression_ctt_abs_tol = derive_absolute_tolerance(metrics.e_ctt) if status == CALIBRATION_SUCCESS else None
    non_regression_rho_abs_tol = derive_absolute_tolerance(metrics.e_rho) if status == CALIBRATION_SUCCESS else None

    return CalibrationArtifact(
        status=status,
        calibration_contract_version=CALIBRATION_CONTRACT_VERSION,
        schema_version=CALIBRATION_ARTIFACT_SCHEMA_VERSION,
        code_commit=code_commit,
        historical_campaign_id=index.campaign_id,
        historical_manifest_fingerprint=index.manifest_fingerprint,
        historical_repository_commit=index.repository_commit,
        historical_cases=tuple(case_summaries),
        environment_fingerprint=environment_fingerprint,
        e_ctt=metrics.e_ctt,
        e_rho=metrics.e_rho,
        non_regression_ctt_abs_tol=non_regression_ctt_abs_tol,
        non_regression_rho_abs_tol=non_regression_rho_abs_tol,
        failure_reasons=tuple(failure_reasons),
    )


# ---------------------------------------------------------------------------
# CLI -- safe by default. `--help` never computes anything; actually
# running the calibration requires the explicit --confirm-run-calibration
# flag, never passed by this lot. No group selector, no target_id.
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmax_nonregression",
        description=(
            "Target-id-free non-regression calibration tool (1C-7c2c). Compares five historical Level 1B "
            "reference-Hamiltonian cases (triangle S=1, ring4 S in {1,2,3}, ring5 S=1) against a fresh "
            "recomputation and derives NON_REGRESSION_CTT_ABS_TOL/NON_REGRESSION_RHO_ABS_TOL. Never produces "
            "a J0!=1 response, a Delta_C_TT, or a geometry-inference result."
        ),
    )
    parser.add_argument(
        "--historical-output-dir",
        type=str,
        default=None,
        help=(
            "Path to the historical Level1B campaign output directory (containing runs/<case_id>/). Never "
            "discovered by glob/mtime/'latest'."
        ),
    )
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root for git provenance resolution (defaults to cwd).")
    parser.add_argument(
        "--confirm-run-calibration",
        action="store_true",
        help=(
            "Required to actually run the calibration (recomputation + historical comparison). Without this "
            "flag the CLI only prints this help text and performs no computation."
        ),
    )
    return parser


def _artifact_to_json(artifact: CalibrationArtifact) -> dict:
    return dataclasses.asdict(artifact)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if not args.confirm_run_calibration:
        parser.print_help()
        return 0
    if not args.historical_output_dir:
        parser.error("--historical-output-dir is required with --confirm-run-calibration")
    artifact = run_calibration(args.historical_output_dir, repo_root=args.repo_root)
    sys.stdout.write(canonical_json_bytes(_artifact_to_json(artifact)).decode("utf-8"))
    return 0 if artifact.status == CALIBRATION_SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
