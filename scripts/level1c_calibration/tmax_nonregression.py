"""T_max baseline non-regression calibration tool (1C-7c2).

Implements exactly the calibration contract frozen by 1C-7b/1C-7b2/
1C-7b3/1C-7c (docs/levels/level1c/identifiability-preregistration.md
section 20, in particular 20.22 CALIBRATION_SET/CALIBRATION_METRIC_CTT/
CALIBRATION_METRIC_RHO/NULLITY_POLICY/TOLERANCE_DERIVATION_RULE):

    CALIBRATION_SET = T_max, J0=1 ("reference" Hamiltonian identity),
        geometry in {triangle, ring5}, spin in {2, 3}, only where T_max
        is naturally selected within the frozen production_window
        baseline (9 for triangle, 15 for ring5) -- never deepened.
    CALIBRATION_METRIC_CTT = MAX_ABS over off-diagonal (i != j)
        C_TT_conn comparison records.
    CALIBRATION_METRIC_RHO = MAX_ABS over rho_QQ comparison records
        where both sides are non-null.
    NULLITY_POLICY = a nullity disagreement, or a null/null disagreement
        on null_reason, fails the whole calibration.
    TOLERANCE_DERIVATION_RULE = CEIL_DECADE_POLICY: TOL =
        10**ceil(log10(E)) for E > 0, or 10**ceil(log10(machine_epsilon))
        for E == 0 -- a deterministic governance convention, never a
        rigorous error bound, never a safety-factor multiplier, never a
        floor invented ad hoc.

This module is a standalone calibration tool, not a campaign runner: it
never produces a J0 != 1 response, a Delta_C_TT, an inter-J0 tracking
verdict, or a geometry-inference result. It introduces no new scientific
primitive -- it orchestrates already-accepted Level0/Level1 primitives
(build_level0_report_with_eigenvectors, target_selection.
select_target_group, matching.compute_restricted_symmetry_label/
symmetry_labels_match/compute_twice_T, restricted.extract_group_state/
canonical_multiplet_expectation, local_observables.
build_local_flavor_generators/build_local_charge_operator/
flavor_correlator_connected_group/charge_correlator_connected_group/
normalized_charge_correlator, results.build_spectral_group_identity) and
never modifies matching.py, target_selection.py, or the Level 1B
manifest.

The historical Level 1B corpus this tool compares against is never
discovered by this tool (no glob, no "latest", no mtime heuristic): the
caller supplies an explicit, self-describing JSON "historical
calibration manifest" (see HistoricalCalibrationManifest/
load_historical_calibration_manifest) naming, for each (geometry, spin)
case it wants attempted, the exact records.jsonl directory, its expected
SHA-256, and an explicit target-group selector (spectral_window_group_
index, twice_T, multiplicity) identifying which archived spectral group
is T_max for that case -- a fact already established when the original
Level 1B campaign actually ran (target_selection.select_target_group's
own flavor_label outcome at that time), which this tool only VALIDATES
(against the manifest's own frozen target_twice_T and against internal
corpus consistency), never re-derives. The persisted schema-v2 documents
carry no "target_id" field (audited directly against results.py/
serialization.py/correlators-v2.schema.json): reconstructing "which
archived record is T_max" from generic structural fields alone (twice_T
could coincide with another selected target's own resolved twice_T) is
not unambiguous, so this tool never attempts it -- it is exactly the
"STOP, do not invent a new mechanism" case the 1C-7c2 mandate warns
against, resolved by requiring the already-known selector explicitly.

CLI: `python -m scripts.level1c_calibration.tmax_nonregression --help`
prints usage and performs no computation. Actually running the
calibration requires the explicit `--confirm-run-calibration` flag --
this lot (1C-7c2) never passes it and never runs the calibration.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import reflection_unitary_automorphism, translation_unitary_automorphism
from cosmobox.level1.local_observables import (
    NormalizedMoment,
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.matching import SymmetryLabel, compute_restricted_symmetry_label, compute_twice_T, symmetry_labels_match
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, SpectralGroupState, extract_group_state
from cosmobox.level1.results import build_spectral_group_identity
from experiments.level1.manifest import Manifest, load_manifest
from experiments.level1.target_selection import SELECTED, select_target_group

from scripts.level1c_preflight.j0_grid_preflight import PreflightInternalFailure as _GitProvenanceFailure
from scripts.level1c_preflight.j0_grid_preflight import require_clean_worktree as _require_clean_git_worktree
from scripts.level1c_preflight.j0_grid_preflight import resolve_code_commit as _resolve_git_head_sha

# ---------------------------------------------------------------------------
# Frozen calibration contract (docs/levels/level1c/identifiability-
# preregistration.md section 20.22) -- never rederived, never optimized.
# ---------------------------------------------------------------------------

N_FLAVORS = 2
GEOMETRIES: tuple[str, ...] = ("triangle", "ring5")
SPIN_VALUES: tuple[int, ...] = (2, 3)
REFERENCE_J0 = 1.0
TARGET_ID_T_MAX = "T_max"

PRODUCTION_WINDOW_BASELINE: Mapping[tuple[str, int], int] = {
    ("triangle", 2): 9,
    ("triangle", 3): 9,
    ("ring5", 2): 15,
    ("ring5", 3): 15,
}
"""The already-frozen baseline (J0=1) production_window values (docs/
levels/level1c/identifiability-preregistration.md section 19.8), reused
here as a frozen INPUT -- never rederived, never redeepened. Retaining
exactly this many lowest eigenpairs is the same production window the
future normative baseline itself will use; if T_max does not naturally
fall within it, that (geometry, spin) case is simply unavailable for
calibration (docs section 20.22's own minimum-availability rule), never
a reason to widen the window."""

CALIBRATION_CONTRACT_VERSION = "level1c-nonregression-calibration-v1"
"""Operational version identifier of the frozen 1C-7b3/1C-7c calibration
contract this module implements -- never a new scientific rule, never a
dynamic date. Bumped only if this already-frozen contract is itself
revised by a future, separately-governed lot."""

CALIBRATION_ARTIFACT_SCHEMA_VERSION = "level1c-nonregression-calibration-artifact-v1"
"""Version identifier of THIS module's own public artifact shape --
distinct from CALIBRATION_CONTRACT_VERSION (the scientific contract) and
from schema_version (correlators-v2, the historical corpus's own
schema)."""

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REFERENCE_HAMILTONIAN_T = 1.0
REFERENCE_HAMILTONIAN_G_E = 1.0
REFERENCE_HAMILTONIAN_K = 1.0

CTT_OBSERVABLE_KIND = "C_TT_conn"
RHO_OBSERVABLE_KIND = "rho_QQ"
TRANSLATION_OBSERVABLE_KIND = "translation_character"
REFLECTION_OBSERVABLE_KIND = "reflection_character"

_ZERO_LOCAL_CHARGE_VARIANCE_REASON = "zero_local_charge_variance"


# ---------------------------------------------------------------------------
# Information firewall: a single, generic, constant exception for every
# FAIL HARD path in this module's analysis phase -- exactly the same
# discipline as scripts.level1c_preflight.j0_grid_preflight.
# PreflightInternalFailure (1C-6i/1C-6j audit): several already-accepted
# internal primitives embed a raw numeric value in their own exception
# message on an internal-consistency failure (restricted._hermitian_
# aware_normalized_trace, matching.SymmetryLabel.__post_init__, ...).
# Raising CalibrationInternalFailure() `from None` clears __cause__, so
# standard traceback rendering never displays the original exception.
# ---------------------------------------------------------------------------


class CalibrationInternalFailure(RuntimeError):
    _PUBLIC_MESSAGE = "internal calibration analysis failed"

    def __init__(self) -> None:
        super().__init__(self._PUBLIC_MESSAGE)


class CalibrationConfigError(ValueError):
    """Raised for a malformed or self-inconsistent CALLER-SUPPLIED
    historical calibration manifest/config (bad JSON, missing field,
    SHA-256 mismatch against the caller's own declared expectation, a
    selector whose twice_T disagrees with the frozen manifest's own
    T_max target_twice_T, a campaign_id/manifest_fingerprint mismatch
    inside a supplied historical document). Deliberately NOT sanitized
    like CalibrationInternalFailure: this reports a problem in the
    OPERATOR's own input file, never a computed scientific value, so a
    descriptive message is safe and useful."""


# ---------------------------------------------------------------------------
# Git provenance -- thin, correctly-named wrappers around the already-
# accepted, generic (git-only, preflight-agnostic) helpers in
# j0_grid_preflight.py. Reused rather than duplicated (the mandate's own
# instruction); the foreign PreflightInternalFailure this tool's actual
# caller would otherwise see is caught here and re-raised as this
# module's own CalibrationInternalFailure, so a calibration failure is
# never mislabeled as a "preflight" failure.
# ---------------------------------------------------------------------------


def resolve_calibration_code_commit(repo_root: str | None = None) -> str:
    try:
        return _resolve_git_head_sha(repo_root)
    except _GitProvenanceFailure:
        raise CalibrationInternalFailure() from None


def require_clean_worktree(repo_root: str | None = None) -> None:
    """DIRTY_WORKTREE_POLICY = REFUSE_EXECUTION, same as the preflight
    (docs section 20 does not relax this for calibration)."""
    try:
        _require_clean_git_worktree(repo_root)
    except _GitProvenanceFailure:
        raise CalibrationInternalFailure() from None


# ---------------------------------------------------------------------------
# Environment fingerprint (docs section 20.23): a canonical, JSON-safe,
# deterministically serialized description of the runtime that produced
# the CURRENT recomputation -- never a repr(), never a bare str(dict),
# never a memory address or temp path. BLAS/LAPACK identity is read via
# numpy's own structured runtime API (numpy.show_config(mode="dicts")),
# never by fragile stdout parsing; if that API is unavailable or raises,
# an explicit "unavailable" structure is produced instead of inventing a
# value.
# ---------------------------------------------------------------------------

_ENVIRONMENT_FINGERPRINT_UNAVAILABLE = "unavailable"


def _blas_lapack_identity() -> dict:
    try:
        config = np.show_config(mode="dicts")
    except Exception:
        return {
            "blas_name": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "blas_version": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "lapack_name": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
            "lapack_version": _ENVIRONMENT_FINGERPRINT_UNAVAILABLE,
        }
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
    """A plain, canonical (JSON-simple-typed, deterministically keyed)
    dict -- never a repr()/str(dict) of a live object. Contains no
    timestamp (docs section 20's own timestamp-non-identity precedent,
    outputs.py's _METADATA_FIELDS) and no filesystem path."""
    return {
        "python_version": platform.python_version(),
        "numpy_version": str(np.__version__),
        "scipy_version": str(scipy.__version__),
        "blas_lapack": _blas_lapack_identity(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }


def environments_are_equal(a: Mapping, b: Mapping) -> bool:
    """Exact field-by-field equality on the normative environment
    fingerprint fields -- no notion of a version being "close enough".
    Deliberately structural (dict equality on canonical JSON-safe
    values), never a fuzzy/semantic version comparison."""
    return dict(a) == dict(b)


# ---------------------------------------------------------------------------
# Canonical JSON (docs section 20's own sort_keys/allow_nan=False
# discipline, matching scripts.level1b_campaign.outputs._canonical_json_bytes
# verbatim in spirit -- duplicated as a small, standard local helper per
# this project's own established practice, e.g. local_observables.py's
# own Pauli-matrix duplication rationale, rather than reaching into
# another script package's private function).
# ---------------------------------------------------------------------------


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n"


# ---------------------------------------------------------------------------
# Historical calibration manifest (caller-supplied, explicit -- never
# discovered by glob/mtime/"latest"). One JSON file names, for each
# (geometry, spin) case the caller wants attempted, the exact records.jsonl
# directory, its expected SHA-256, and the explicit historical target
# selector.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HistoricalGroupSelector:
    """The already-known (from when the historical Level 1B campaign
    itself ran target_selection.select_target_group) structural identity
    of the archived spectral group that IS T_max for one case --
    supplied explicitly by the caller, never guessed by this tool from
    twice_T alone (which the persisted schema-v2 corpus cannot
    disambiguate on its own: no "target_id" field exists in a record's
    identity, and another selected target could coincidentally share the
    same twice_T)."""

    spectral_window_group_index: int
    twice_T: int
    multiplicity: int

    def __post_init__(self) -> None:
        for name, value in (
            ("spectral_window_group_index", self.spectral_window_group_index),
            ("twice_T", self.twice_T),
            ("multiplicity", self.multiplicity),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if self.multiplicity < 1:
            raise ValueError(f"multiplicity must be >= 1, got {self.multiplicity}")


@dataclass(frozen=True, slots=True)
class HistoricalCaseReference:
    geometry: str
    spin: int
    case_dir: str
    expected_records_sha256: str
    target_group_selector: HistoricalGroupSelector

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise CalibrationConfigError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin not in SPIN_VALUES:
            raise CalibrationConfigError(f"spin must be one of {SPIN_VALUES}, got {self.spin!r}")
        if not self.case_dir:
            raise CalibrationConfigError("case_dir must be non-empty")
        if not _SHA256_HEX_PATTERN.fullmatch(self.expected_records_sha256):
            raise CalibrationConfigError(
                f"expected_records_sha256 must be a 64-character lowercase hex string, got "
                f"{self.expected_records_sha256!r}"
            )
        if not isinstance(self.target_group_selector, HistoricalGroupSelector):
            raise CalibrationConfigError("target_group_selector must be a HistoricalGroupSelector")


@dataclass(frozen=True, slots=True)
class HistoricalCalibrationManifest:
    campaign_id: str
    manifest_fingerprint: str
    cases: tuple[HistoricalCaseReference, ...]

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise CalibrationConfigError("campaign_id must be non-empty")
        if not self.manifest_fingerprint:
            raise CalibrationConfigError("manifest_fingerprint must be non-empty")
        seen: set[tuple[str, int]] = set()
        for case in self.cases:
            if not isinstance(case, HistoricalCaseReference):
                raise CalibrationConfigError("every case must be a HistoricalCaseReference")
            key = (case.geometry, case.spin)
            if key in seen:
                raise CalibrationConfigError(f"duplicate (geometry, spin) entry in historical manifest: {key}")
            seen.add(key)


def _selector_from_json(payload: dict, *, context: str) -> HistoricalGroupSelector:
    required = ("spectral_window_group_index", "twice_T", "multiplicity")
    for key in required:
        if key not in payload:
            raise CalibrationConfigError(f"{context}: target_group_selector missing required key {key!r}")
    return HistoricalGroupSelector(
        spectral_window_group_index=payload["spectral_window_group_index"],
        twice_T=payload["twice_T"],
        multiplicity=payload["multiplicity"],
    )


def load_historical_calibration_manifest(path: str | Path) -> HistoricalCalibrationManifest:
    """Parses the explicit, caller-supplied JSON historical calibration
    manifest. Never globs, never picks "latest", never infers a path --
    `path` itself must be given explicitly by the caller (CLI
    --historical-manifest)."""
    resolved = Path(path)
    if not resolved.is_file():
        raise CalibrationConfigError(f"historical calibration manifest not found: {resolved}")
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalibrationConfigError(f"historical calibration manifest is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise CalibrationConfigError("historical calibration manifest must be a JSON object")

    for key in ("campaign_id", "manifest_fingerprint", "cases"):
        if key not in raw:
            raise CalibrationConfigError(f"historical calibration manifest missing required key {key!r}")
    if not isinstance(raw["cases"], list) or not raw["cases"]:
        raise CalibrationConfigError("historical calibration manifest 'cases' must be a non-empty JSON array")

    cases: list[HistoricalCaseReference] = []
    for index, entry in enumerate(raw["cases"]):
        context = f"cases[{index}]"
        if not isinstance(entry, dict):
            raise CalibrationConfigError(f"{context} must be a JSON object")
        for key in ("geometry", "spin", "case_dir", "expected_records_sha256", "target_group_selector"):
            if key not in entry:
                raise CalibrationConfigError(f"{context} missing required key {key!r}")
        if not isinstance(entry["target_group_selector"], dict):
            raise CalibrationConfigError(f"{context}.target_group_selector must be a JSON object")
        cases.append(
            HistoricalCaseReference(
                geometry=entry["geometry"],
                spin=entry["spin"],
                case_dir=entry["case_dir"],
                expected_records_sha256=entry["expected_records_sha256"],
                target_group_selector=_selector_from_json(entry["target_group_selector"], context=context),
            )
        )
    return HistoricalCalibrationManifest(
        campaign_id=raw["campaign_id"], manifest_fingerprint=raw["manifest_fingerprint"], cases=tuple(cases)
    )


# ---------------------------------------------------------------------------
# Historical record loading and extraction. load_case_records is REUSED
# verbatim from the already-accepted Level1B campaign persistence layer
# (scripts.level1b_campaign.outputs) -- never a second JSONL parser.
# ---------------------------------------------------------------------------


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_and_verify_historical_documents(case: HistoricalCaseReference) -> tuple[dict, ...]:
    from scripts.level1b_campaign.outputs import load_case_records

    case_dir = Path(case.case_dir)
    records_path = case_dir / "records.jsonl"
    if not records_path.is_file():
        raise CalibrationConfigError(f"{case.geometry} S={case.spin}: records.jsonl not found under {case_dir}")

    actual_sha256 = compute_file_sha256(records_path)
    if actual_sha256 != case.expected_records_sha256:
        raise CalibrationConfigError(
            f"{case.geometry} S={case.spin}: records.jsonl SHA-256 mismatch -- expected "
            f"{case.expected_records_sha256}, got {actual_sha256}"
        )
    return load_case_records(case_dir)


def _hamiltonian_identity_is_reference(hamiltonian: Mapping, n_nodes: int) -> bool:
    """True iff `hamiltonian` (a schema-v2 identity.hamiltonian dict)
    describes the uniform J=1 "reference" Hamiltonian case (the same
    identity the Level1B manifest's own "reference" hamiltonian_case_id
    and the Level1C baseline J0=1 both share) -- never the j_break case,
    never any other perturbation."""
    j_values = hamiltonian.get("J")
    if not isinstance(j_values, list) or len(j_values) != n_nodes:
        return False
    if not all(value == REFERENCE_J0 for value in j_values):
        return False
    return (
        hamiltonian.get("h_is_zero") is True
        and hamiltonian.get("t") == REFERENCE_HAMILTONIAN_T
        and hamiltonian.get("g_E") == REFERENCE_HAMILTONIAN_G_E
        and hamiltonian.get("K") == REFERENCE_HAMILTONIAN_K
    )


def _document_matches_selector(
    document: Mapping,
    *,
    geometry: str,
    spin: int,
    campaign_id: str,
    manifest_fingerprint: str,
    n_nodes: int,
    selector: HistoricalGroupSelector,
) -> bool:
    if document.get("campaign_id") != campaign_id or document.get("manifest_fingerprint") != manifest_fingerprint:
        return False
    identity = document.get("identity")
    if not isinstance(identity, dict):
        return False
    if identity.get("geometry") != geometry or identity.get("spin") != spin:
        return False
    hamiltonian = identity.get("hamiltonian")
    if not isinstance(hamiltonian, dict) or not _hamiltonian_identity_is_reference(hamiltonian, n_nodes):
        return False
    group = identity.get("spectral_group")
    if not isinstance(group, dict):
        return False
    return (
        group.get("spectral_window_group_index") == selector.spectral_window_group_index
        and group.get("twice_T") == selector.twice_T
        and group.get("multiplicity") == selector.multiplicity
    )


@dataclass(frozen=True, slots=True)
class HistoricalTargetRecords:
    """Everything this tool extracted from the historical corpus for one
    (geometry, spin) case's T_max group -- never containing more than
    the caller's own historical corpus itself already exposes. `ctt` and
    `rho` map an ordered pair (i, j), i != j, to the record's own payload
    (a float for C_TT_conn, a (value, null_reason) pair for rho_QQ).
    `translation_label`/`reflection_label` are the group-level symmetry
    labels (path=None records)."""

    ctt: Mapping[tuple[int, int], float]
    rho: Mapping[tuple[int, int], tuple[float | None, str | None]]
    translation_label: SymmetryLabel | None
    reflection_label: SymmetryLabel | None
    spectral_status: str
    twice_T: int
    multiplicity: int


def _symmetry_label_from_payload(payload: Mapping) -> SymmetryLabel:
    kind = payload.get("kind")
    raw_value = payload.get("value")
    value = complex(raw_value["real"], raw_value["imag"]) if raw_value is not None else None
    return SymmetryLabel(kind=kind, value=value)


def extract_historical_target_records(
    documents: Sequence[Mapping],
    *,
    geometry: str,
    spin: int,
    campaign_id: str,
    manifest_fingerprint: str,
    n_nodes: int,
    selector: HistoricalGroupSelector,
) -> HistoricalTargetRecords | None:
    """None iff no document in `documents` matches `selector` at all --
    the historical side of T_max is simply unavailable for this case
    (never a hard failure by itself). Raises CalibrationConfigError for
    any internal inconsistency among the matching documents themselves
    (a duplicate (i, j)/observable_kind pair, or two matching documents
    disagreeing on the group's own status) -- an ambiguous or
    self-contradictory extraction is never silently resolved by picking
    one candidate."""
    matching = [
        document
        for document in documents
        if _document_matches_selector(
            document,
            geometry=geometry,
            spin=spin,
            campaign_id=campaign_id,
            manifest_fingerprint=manifest_fingerprint,
            n_nodes=n_nodes,
            selector=selector,
        )
    ]
    if not matching:
        return None

    statuses = {document["identity"]["spectral_group"]["status"] for document in matching}
    if len(statuses) != 1:
        raise CalibrationConfigError(
            f"{geometry} S={spin}: historical documents matching the supplied selector disagree on "
            f"spectral_group.status: {sorted(statuses)}"
        )
    spectral_status = next(iter(statuses))

    ctt: dict[tuple[int, int], float] = {}
    rho: dict[tuple[int, int], tuple[float | None, str | None]] = {}
    translation_label: SymmetryLabel | None = None
    reflection_label: SymmetryLabel | None = None

    for document in matching:
        identity = document["identity"]
        observable_kind = document.get("observable_kind")
        path = identity.get("path")

        if observable_kind == CTT_OBSERVABLE_KIND and path is not None and len(path) == 2 and path[0] != path[1]:
            key = (int(path[0]), int(path[1]))
            if key in ctt:
                raise CalibrationConfigError(f"{geometry} S={spin}: duplicate historical C_TT_conn record for {key}")
            ctt[key] = float(document["payload"])
        elif observable_kind == RHO_OBSERVABLE_KIND and path is not None and len(path) == 2 and path[0] != path[1]:
            key = (int(path[0]), int(path[1]))
            if key in rho:
                raise CalibrationConfigError(f"{geometry} S={spin}: duplicate historical rho_QQ record for {key}")
            moment = document["payload"]
            rho[key] = (moment.get("value"), moment.get("null_reason"))
        elif observable_kind == TRANSLATION_OBSERVABLE_KIND and path is None:
            if translation_label is not None:
                raise CalibrationConfigError(f"{geometry} S={spin}: duplicate historical translation_character record")
            translation_label = _symmetry_label_from_payload(document["payload"])
        elif observable_kind == REFLECTION_OBSERVABLE_KIND and path is None:
            if reflection_label is not None:
                raise CalibrationConfigError(f"{geometry} S={spin}: duplicate historical reflection_character record")
            reflection_label = _symmetry_label_from_payload(document["payload"])

    return HistoricalTargetRecords(
        ctt=ctt,
        rho=rho,
        translation_label=translation_label,
        reflection_label=reflection_label,
        spectral_status=spectral_status,
        twice_T=selector.twice_T,
        multiplicity=selector.multiplicity,
    )


# ---------------------------------------------------------------------------
# Current (Level 1C, J0=1) recomputation. Reuses experiments.level1.
# target_selection.select_target_group directly (no reimplementation of
# the flavor_label selection rule) and results.build_spectral_group_identity
# directly (no second identity constructor).
# ---------------------------------------------------------------------------

_TMAX_UNAVAILABLE_NOT_SELECTED = "current_target_not_selected"
_TMAX_UNAVAILABLE_NOT_COMPLETE = "current_target_not_complete_multiplet"


def _build_reference_hamiltonian_parameters(n_nodes: int) -> HamiltonianParameters:
    """J_i=1 for every site -- the manifest's own "reference" Hamiltonian
    identity (J_uniform=1.0, J_override=null), duplicated here as a
    small, standard construction rather than reaching into
    scripts.level1c_preflight.j0_grid_preflight's own private j_break-
    parameterized helper."""
    return HamiltonianParameters(
        J=tuple(REFERENCE_J0 for _ in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=REFERENCE_HAMILTONIAN_T,
        g_E=REFERENCE_HAMILTONIAN_G_E,
        K=REFERENCE_HAMILTONIAN_K,
    )


@dataclass(frozen=True, slots=True)
class CurrentTargetRecords:
    ctt: Mapping[tuple[int, int], float]
    rho: Mapping[tuple[int, int], tuple[float | None, str | None]]
    translation_label: SymmetryLabel
    reflection_label: SymmetryLabel
    twice_T: int
    multiplicity: int
    spectral_status: str


def compute_current_tmax_case(geometry: str, spin: int, manifest: Manifest) -> tuple[CurrentTargetRecords | None, str | None]:
    """Returns (records, None) if T_max is naturally selected and
    complete_multiplet within the frozen baseline production_window;
    (None, reason) if it is genuinely unavailable there (never a
    failure by itself: docs section 20.22's own minimum-availability
    rule handles this at the aggregation level, never by deepening this
    single case's window)."""
    production_window = PRODUCTION_WINDOW_BASELINE[(geometry, spin)]

    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    basis = build_basis(lattice, N_FLAVORS, spin, external_charges=None)
    key_index = build_key_index(basis.keys)

    params = _build_reference_hamiltonian_parameters(n_nodes)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, basis.keys, key_index, params)
    options = SpectrumOptions(
        max_dense_dimension=manifest.resource_guardrails.max_dense_dimension,
        max_sparse_dimension=manifest.resource_guardrails.max_sparse_dimension,
        n_eigenvalues=production_window,
        force=False,
        degeneracy_tolerance=manifest.degeneracy_tolerance,
    )

    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, basis, terms, params, spectrum_options=options
    )
    groups = level0_report.spectrum.degeneracy.groups
    group_states: tuple[SpectralGroupState, ...] = tuple(extract_group_state(eigenvectors, g) for g in groups)
    flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, spin, basis.keys, key_index)

    target_specs = manifest.target_groups[geometry]
    target = next((spec for spec in target_specs if spec.target_id == TARGET_ID_T_MAX), None)
    if target is None:
        return None, _TMAX_UNAVAILABLE_NOT_SELECTED

    outcome = select_target_group(
        target, groups, group_states, flavor_casimir=flavor_casimir, degeneracy_tolerance=manifest.degeneracy_tolerance
    )
    if outcome.status != SELECTED:
        return None, _TMAX_UNAVAILABLE_NOT_SELECTED

    state = group_states[outcome.group_index]
    if state.status != COMPLETE_MULTIPLET:
        return None, _TMAX_UNAVAILABLE_NOT_COMPLETE

    group = groups[outcome.group_index]
    spectral_group_identity = build_spectral_group_identity(
        group, state, spectral_window_group_index=outcome.group_index, twice_T=outcome.twice_T
    )

    translation_automorphism = translation_unitary_automorphism(
        lattice, N_FLAVORS, spin, basis.keys, key_index, external_charges=None
    )
    reflection_automorphism = reflection_unitary_automorphism(
        lattice, N_FLAVORS, spin, basis.keys, key_index, external_charges=None
    )
    translation_label = compute_restricted_symmetry_label(terms.total, translation_automorphism, state)
    reflection_label = compute_restricted_symmetry_label(terms.total, reflection_automorphism, state)

    generators_by_node = {
        node: build_local_flavor_generators(lattice, N_FLAVORS, spin, basis.keys, key_index, node) for node in lattice.nodes
    }
    charge_by_node = {
        node: build_local_charge_operator(lattice, N_FLAVORS, spin, basis.keys, key_index, node) for node in lattice.nodes
    }
    variance_by_node = {
        node: charge_correlator_connected_group(charge_by_node[node], charge_by_node[node], state).value
        for node in lattice.nodes
    }

    ctt: dict[tuple[int, int], float] = {}
    rho: dict[tuple[int, int], tuple[float | None, str | None]] = {}
    for i in lattice.nodes:
        for j in lattice.nodes:
            if i == j:
                continue
            ctt[(i, j)] = flavor_correlator_connected_group(generators_by_node[i], generators_by_node[j], state).value
            connected_qq = charge_correlator_connected_group(charge_by_node[i], charge_by_node[j], state).value
            moment: NormalizedMoment = normalized_charge_correlator(connected_qq, variance_by_node[i], variance_by_node[j])
            rho[(i, j)] = (moment.value, moment.null_reason)

    return (
        CurrentTargetRecords(
            ctt=ctt,
            rho=rho,
            translation_label=translation_label,
            reflection_label=reflection_label,
            twice_T=spectral_group_identity.twice_T,
            multiplicity=spectral_group_identity.multiplicity,
            spectral_status=spectral_group_identity.status,
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Per-case comparison. AVAILABLE only if BOTH sides produced a usable
# T_max group; every REQUIRED_NON_REGRESSION structural field (docs
# section 20.19/20.22) is checked before any numeric difference is even
# computed, per case.
# ---------------------------------------------------------------------------

CASE_AVAILABLE = "AVAILABLE"
CASE_CURRENT_UNAVAILABLE = "CURRENT_UNAVAILABLE"
CASE_HISTORICAL_UNAVAILABLE = "HISTORICAL_UNAVAILABLE"
CASE_STRUCTURAL_MISMATCH = "STRUCTURAL_MISMATCH"
CASE_NULLITY_MISMATCH = "NULLITY_MISMATCH"


@dataclass(frozen=True, slots=True)
class CttPairRecord:
    geometry: str
    spin: int
    i: int
    j: int
    abs_diff: float


@dataclass(frozen=True, slots=True)
class RhoPairRecord:
    geometry: str
    spin: int
    i: int
    j: int
    abs_diff: float | None
    both_null: bool


@dataclass(frozen=True, slots=True)
class CaseComparison:
    geometry: str
    spin: int
    status: str
    detail: str | None
    ctt_records: tuple[CttPairRecord, ...]
    rho_records: tuple[RhoPairRecord, ...]


def compare_case(
    geometry: str,
    spin: int,
    current: CurrentTargetRecords | None,
    current_unavailable_reason: str | None,
    historical: HistoricalTargetRecords | None,
) -> CaseComparison:
    if current is None:
        return CaseComparison(geometry, spin, CASE_CURRENT_UNAVAILABLE, current_unavailable_reason, (), ())
    if historical is None:
        return CaseComparison(geometry, spin, CASE_HISTORICAL_UNAVAILABLE, "no historical document matched the supplied selector", (), ())

    if current.spectral_status != historical.spectral_status:
        return CaseComparison(
            geometry, spin, CASE_STRUCTURAL_MISMATCH,
            f"spectral_group.status differs: current={current.spectral_status!r}, historical={historical.spectral_status!r}",
            (), (),
        )
    if current.twice_T != historical.twice_T:
        return CaseComparison(
            geometry, spin, CASE_STRUCTURAL_MISMATCH,
            f"twice_T differs: current={current.twice_T!r}, historical={historical.twice_T!r}",
            (), (),
        )
    if current.multiplicity != historical.multiplicity:
        return CaseComparison(
            geometry, spin, CASE_STRUCTURAL_MISMATCH,
            f"multiplicity differs: current={current.multiplicity!r}, historical={historical.multiplicity!r}",
            (), (),
        )
    if historical.translation_label is None or historical.reflection_label is None:
        return CaseComparison(geometry, spin, CASE_STRUCTURAL_MISMATCH, "historical corpus is missing translation/reflection symmetry labels for T_max", (), ())
    if not symmetry_labels_match(current.translation_label, historical.translation_label):
        return CaseComparison(geometry, spin, CASE_STRUCTURAL_MISMATCH, "translation label does not match between current and historical", (), ())
    if not symmetry_labels_match(current.reflection_label, historical.reflection_label):
        return CaseComparison(geometry, spin, CASE_STRUCTURAL_MISMATCH, "reflection label does not match between current and historical", (), ())

    common_ctt_pairs = sorted(set(current.ctt) & set(historical.ctt))
    ctt_records = tuple(
        CttPairRecord(geometry, spin, i, j, abs(current.ctt[(i, j)] - historical.ctt[(i, j)])) for i, j in common_ctt_pairs
    )

    common_rho_pairs = sorted(set(current.rho) & set(historical.rho))
    rho_records: list[RhoPairRecord] = []
    for i, j in common_rho_pairs:
        current_value, current_reason = current.rho[(i, j)]
        historical_value, historical_reason = historical.rho[(i, j)]
        current_null = current_value is None
        historical_null = historical_value is None
        if current_null != historical_null:
            return CaseComparison(
                geometry, spin, CASE_NULLITY_MISMATCH,
                f"rho_QQ({i},{j}): historical null={historical_null}, current null={current_null}",
                (), (),
            )
        if current_null and historical_null:
            if current_reason != historical_reason:
                return CaseComparison(
                    geometry, spin, CASE_NULLITY_MISMATCH,
                    f"rho_QQ({i},{j}): both null but null_reason differs (current={current_reason!r}, historical={historical_reason!r})",
                    (), (),
                )
            rho_records.append(RhoPairRecord(geometry, spin, i, j, None, True))
        else:
            rho_records.append(RhoPairRecord(geometry, spin, i, j, abs(current_value - historical_value), False))

    return CaseComparison(geometry, spin, CASE_AVAILABLE, None, ctt_records, tuple(rho_records))


# ---------------------------------------------------------------------------
# Tolerance derivation -- CEIL_DECADE_POLICY (docs section 20.22),
# entirely deterministic, no invented floor, no invented safety factor.
# The rounding of log10(E) before ceil guards against a genuine risk for
# E an exact power of ten: a libm whose log10 returns a value a few ULP
# on the wrong side of the exact integer would otherwise silently shift
# the derived decade by one -- this function must be stable regardless.
# ---------------------------------------------------------------------------

_LOG10_ROUNDING_DECIMALS = 9


def derive_absolute_tolerance(e: float) -> float:
    """CEIL_DECADE_POLICY: 10**ceil(log10(E)) for E > 0, or
    10**ceil(log10(machine_epsilon_float64)) for E == 0 (currently
    1e-15) -- a deterministic governance convention (docs section
    20.22), never a rigorous numerical error bound, never a solver-
    accuracy claim, never a physical-response threshold. Raises
    ValueError for a negative, NaN, or infinite E: none of those is a
    valid observed maximum absolute difference."""
    if isinstance(e, bool) or not isinstance(e, (int, float)):
        raise ValueError(f"E must be a real number, got {e!r}")
    e = float(e)
    if math.isnan(e) or math.isinf(e):
        raise ValueError(f"E must be finite, got {e}")
    if e < 0:
        raise ValueError(f"E must be >= 0, got {e}")
    if e == 0.0:
        e = float(np.finfo(np.float64).eps)
    exponent = math.ceil(round(math.log10(e), _LOG10_ROUNDING_DECIMALS))
    return 10.0**exponent


# ---------------------------------------------------------------------------
# Aggregation -- MAX_ABS over all pooled comparison records (docs
# section 20.22): never a mean, never an RMS, never a quantile.
# ---------------------------------------------------------------------------

RHO_NUMERIC_UNAVAILABLE = "NO_NUMERIC_RHO_CALIBRATION_RECORD"


@dataclass(frozen=True, slots=True)
class CalibrationMetrics:
    e_ctt: float | None
    e_rho: float | None
    rho_numeric_status: str | None
    ctt_record_count: int
    rho_record_count: int
    rho_numeric_record_count: int


def aggregate_metrics(case_comparisons: Sequence[CaseComparison]) -> CalibrationMetrics:
    ctt_diffs = [record.abs_diff for case in case_comparisons for record in case.ctt_records]
    rho_numeric_diffs = [
        record.abs_diff for case in case_comparisons for record in case.rho_records if not record.both_null
    ]
    rho_record_count = sum(len(case.rho_records) for case in case_comparisons)

    e_ctt = max(ctt_diffs) if ctt_diffs else None
    if rho_numeric_diffs:
        e_rho = max(rho_numeric_diffs)
        rho_numeric_status = None
    else:
        e_rho = None
        rho_numeric_status = RHO_NUMERIC_UNAVAILABLE if rho_record_count > 0 else None

    return CalibrationMetrics(
        e_ctt=e_ctt,
        e_rho=e_rho,
        rho_numeric_status=rho_numeric_status,
        ctt_record_count=len(ctt_diffs),
        rho_record_count=rho_record_count,
        rho_numeric_record_count=len(rho_numeric_diffs),
    )


def usable_geometries(case_comparisons: Sequence[CaseComparison]) -> frozenset[str]:
    return frozenset(case.geometry for case in case_comparisons if case.status == CASE_AVAILABLE)


# ---------------------------------------------------------------------------
# Public artifact -- structurally cannot carry a raw historical/current
# observable value, an eigenvalue, or an energy (docs section 20's own
# public-firewall philosophy, mirroring PublicPreflightReport). Only
# aggregated E_CTT/E_RHO, derived tolerances, counts, and status are
# public.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalibrationProvenance:
    calibration_contract_version: str
    code_commit: str
    historical_campaign_id: str
    historical_manifest_fingerprint: str
    environment_fingerprint: dict


@dataclass(frozen=True, slots=True)
class PublicCaseOutcome:
    geometry: str
    spin: int
    status: str
    detail: str | None
    historical_records_sha256: str | None
    ctt_pair_count: int
    rho_pair_count: int


CALIBRATION_SUCCESS = "SUCCESS"
CALIBRATION_FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class CalibrationArtifact:
    schema_version: str
    provenance: CalibrationProvenance
    cases: tuple[PublicCaseOutcome, ...]
    status: str
    failure_reasons: tuple[str, ...]
    e_ctt: float | None
    e_rho: float | None
    rho_numeric_status: str | None
    non_regression_ctt_abs_tol: float | None
    non_regression_rho_abs_tol: float | None


def _public_case_outcome(case: CaseComparison, *, historical_sha256: str | None) -> PublicCaseOutcome:
    return PublicCaseOutcome(
        geometry=case.geometry,
        spin=case.spin,
        status=case.status,
        detail=case.detail,
        historical_records_sha256=historical_sha256,
        ctt_pair_count=len(case.ctt_records),
        rho_pair_count=len(case.rho_records),
    )


def run_calibration(
    historical_manifest: HistoricalCalibrationManifest, manifest: Manifest | None = None, *, repo_root: str | None = None
) -> CalibrationArtifact:
    """Runs the full T_max calibration and returns the public artifact.
    NEVER called by this lot's tests or CLI default path -- reserved for
    a future, single-invocation execution lot. Provenance (including the
    clean-worktree refusal) is resolved BEFORE any case is analyzed, so a
    provenance failure costs zero recomputation."""
    resolved_manifest = manifest if manifest is not None else load_manifest()

    if historical_manifest.manifest_fingerprint != resolved_manifest.fingerprint:
        raise CalibrationConfigError(
            "historical calibration manifest_fingerprint does not match the currently loaded Level 1B manifest -- "
            "refusing to compare against a historical corpus produced under a different manifest"
        )

    require_clean_worktree(repo_root)
    code_commit = resolve_calibration_code_commit(repo_root)
    environment_fingerprint = build_environment_fingerprint()

    target_twice_T_by_geometry: dict[str, int] = {}
    for geometry in GEOMETRIES:
        target = next((spec for spec in resolved_manifest.target_groups[geometry] if spec.target_id == TARGET_ID_T_MAX), None)
        if target is None or target.target_twice_T is None:
            raise CalibrationConfigError(f"manifest has no T_max target_twice_T for geometry {geometry!r}")
        target_twice_T_by_geometry[geometry] = target.target_twice_T

    historical_by_case = {(case.geometry, case.spin): case for case in historical_manifest.cases}

    case_comparisons: list[CaseComparison] = []
    sha256_by_case: dict[tuple[str, int], str] = {}
    failure_reasons: list[str] = []

    try:
        for geometry in GEOMETRIES:
            for spin in SPIN_VALUES:
                historical_case = historical_by_case.get((geometry, spin))
                current_records, current_unavailable_reason = compute_current_tmax_case(geometry, spin, resolved_manifest)

                if historical_case is None:
                    case_comparisons.append(
                        CaseComparison(geometry, spin, CASE_HISTORICAL_UNAVAILABLE, "no historical case reference supplied", (), ())
                    )
                    continue

                selector = historical_case.target_group_selector
                if selector.twice_T != target_twice_T_by_geometry[geometry]:
                    raise CalibrationConfigError(
                        f"{geometry} S={spin}: supplied target_group_selector.twice_T ({selector.twice_T}) does not "
                        f"match the manifest's own T_max target_twice_T ({target_twice_T_by_geometry[geometry]}) for "
                        "this geometry -- the supplied historical selector is inconsistent with the frozen manifest"
                    )

                documents = _load_and_verify_historical_documents(historical_case)
                sha256_by_case[(geometry, spin)] = historical_case.expected_records_sha256
                n_nodes = len(build_lattice(geometry).nodes)
                historical_records = extract_historical_target_records(
                    documents,
                    geometry=geometry,
                    spin=spin,
                    campaign_id=historical_manifest.campaign_id,
                    manifest_fingerprint=historical_manifest.manifest_fingerprint,
                    n_nodes=n_nodes,
                    selector=selector,
                )

                comparison = compare_case(geometry, spin, current_records, current_unavailable_reason, historical_records)
                case_comparisons.append(comparison)
                if comparison.status in (CASE_STRUCTURAL_MISMATCH, CASE_NULLITY_MISMATCH):
                    failure_reasons.append(f"{geometry} S={spin}: {comparison.status}: {comparison.detail}")
    except MemoryError:
        raise CalibrationInternalFailure() from None
    except (CalibrationConfigError, CalibrationInternalFailure):
        raise
    except Exception:
        raise CalibrationInternalFailure() from None

    for geometry in GEOMETRIES:
        if geometry not in usable_geometries(case_comparisons):
            failure_reasons.append(f"no usable calibration case for geometry {geometry!r}")

    metrics = aggregate_metrics(case_comparisons)
    status = CALIBRATION_SUCCESS if not failure_reasons else CALIBRATION_FAIL

    non_regression_ctt_abs_tol = derive_absolute_tolerance(metrics.e_ctt) if status == CALIBRATION_SUCCESS and metrics.e_ctt is not None else None
    non_regression_rho_abs_tol = derive_absolute_tolerance(metrics.e_rho) if status == CALIBRATION_SUCCESS and metrics.e_rho is not None else None
    if status == CALIBRATION_SUCCESS and metrics.e_ctt is None:
        failure_reasons.append("no C_TT_conn calibration record was ever produced")
        status = CALIBRATION_FAIL
        non_regression_ctt_abs_tol = None

    provenance = CalibrationProvenance(
        calibration_contract_version=CALIBRATION_CONTRACT_VERSION,
        code_commit=code_commit,
        historical_campaign_id=historical_manifest.campaign_id,
        historical_manifest_fingerprint=historical_manifest.manifest_fingerprint,
        environment_fingerprint=environment_fingerprint,
    )

    return CalibrationArtifact(
        schema_version=CALIBRATION_ARTIFACT_SCHEMA_VERSION,
        provenance=provenance,
        cases=tuple(
            _public_case_outcome(case, historical_sha256=sha256_by_case.get((case.geometry, case.spin)))
            for case in case_comparisons
        ),
        status=status,
        failure_reasons=tuple(failure_reasons),
        e_ctt=metrics.e_ctt,
        e_rho=metrics.e_rho,
        rho_numeric_status=metrics.rho_numeric_status,
        non_regression_ctt_abs_tol=non_regression_ctt_abs_tol,
        non_regression_rho_abs_tol=non_regression_rho_abs_tol,
    )


# ---------------------------------------------------------------------------
# CLI -- safe by default. `--help` never computes anything; actually
# running the calibration requires the explicit --confirm-run-calibration
# flag, never passed by this lot.
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmax_nonregression",
        description=(
            "T_max baseline non-regression calibration tool (1C-7c2..). Compares a historical Level 1B T_max "
            "record against a freshly recomputed Level 1C J0=1 T_max record and derives "
            "NON_REGRESSION_CTT_ABS_TOL/NON_REGRESSION_RHO_ABS_TOL. Never produces a J0!=1 response, a "
            "Delta_C_TT, or a geometry-inference result."
        ),
    )
    parser.add_argument(
        "--historical-manifest",
        type=str,
        default=None,
        help=(
            "Path to the explicit, self-describing JSON historical calibration manifest (see "
            "load_historical_calibration_manifest). Never discovered by glob/mtime/'latest'."
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
    if not args.historical_manifest:
        parser.error("--historical-manifest is required with --confirm-run-calibration")
    historical_manifest = load_historical_calibration_manifest(args.historical_manifest)
    artifact = run_calibration(historical_manifest, repo_root=args.repo_root)
    sys.stdout.write(canonical_json_bytes(_artifact_to_json(artifact)).decode("utf-8"))
    return 0 if artifact.status == CALIBRATION_SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
