"""Baseline non-regression gate: comparison logic, historical group
identity proof, and artifact schema. Lot 1C-8d, integrity-hardened by
1C-8d-fix.

This module performs no diagonalization anywhere. It reads already-
persisted Level1C case artifacts (runs/<case_id>/{run.json,
records.jsonl}, produced by scripts.level1c_campaign.outputs, never
regenerated here) and already-persisted Level1B historical artifacts
(via scripts.level1b_analysis.indexing.build_campaign_artifact_index,
the same accepted primitive scripts.level1c_calibration.
tmax_nonregression already reuses for its own historical corpus
access).

HISTORICAL_RECORDS_INTEGRITY = VERIFIED_BY_EXISTING_INDEXER (1C-8d-fix
audit, section 7): build_campaign_artifact_index already routes through
scripts.level1b_analysis.loader.load_validated_cases, which itself
requires scripts.level1b_campaign.outputs.validate_existing_case_run's
own is_valid check for every planned case before ever calling
load_case_records -- that check already verifies records.jsonl's
SHA-256 against run.json's own records_sha256 (on the exact persisted
bytes), record_count, and per-document campaign_id/manifest_
fingerprint/repository_commit/case_id consistency. No historical-side
integrity check is duplicated here.

load_level1c_baseline_case below is this module's OWN, symmetric
integrity gate for the Level1C side (no equivalent existed before
1C-8d-fix): SHA-256 verified on the exact persisted bytes of
records.jsonl (never reconstructed from parsed JSON), record_count
verified, run.json's own case_id cross-checked, every record's
campaign_id/manifest_fingerprint/repository_commit cross-checked
against run.json's own, and every record's scientific identity
(geometry/spin/sector/Hamiltonian) cross-checked against the exact
CampaignCaseSpec build_level1c_campaign_plan(manifest) produces for
that case_id -- never a new identity rule, the same plan the manifest
itself already defines.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator

from cosmobox.level1.matching import SYMMETRY_TOLERANCE, SymmetryLabel, symmetry_labels_match
from experiments.level1.manifest import Manifest, TargetGroupSpec, load_manifest
from experiments.level1.planning import build_campaign_plan
from experiments.level1c.case_artifact import validate_case_run_document
from experiments.level1c.manifest import J0_BASELINE, Level1CManifest, hamiltonian_case_id_for_j0
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.result_schema import validate_result_record
from scripts.level1b_analysis.indexing import (
    CampaignArtifactIndex,
    IndexedSpectralGroup,
    SpectralGroupIndexError,
    UnresolvedFlavorLabelError,
    build_campaign_artifact_index,
)
from scripts.level1b_analysis.loader import CampaignLoadError
from scripts.level1c_campaign.outputs import load_case_records
from scripts.level1c_calibration.tmax_nonregression import (
    extract_historical_ctt_pairs,
    extract_historical_rho_pairs,
)

SCHEMA_VERSION = "level1c-baseline-nonregression-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "baseline-nonregression-v1.schema.json"

HISTORICAL_CAMPAIGN_ID = "level1b-reference-v1"
HISTORICAL_MANIFEST_FINGERPRINT = "159660cac738518dc620b9627ec95fd67c5dbc283707fdf72e572886364693ab"
HISTORICAL_REPOSITORY_COMMIT = "0ff65ac66b4aa054f739b350cd384c26ecd19752"
"""Reused as frozen constants, not imported from scripts.level1c_calibration.
tmax_nonregression: these identity facts belong to the historical
corpus itself (already documented verbatim in identifiability-
preregistration.md section 20.22), not to the calibration tool."""

PASS = "PASS"
FAIL = "FAIL"
_STATUSES = (PASS, FAIL)

REQUIRED_GEOMETRIES = ("triangle", "ring5")
REQUIRED_SPINS = (2, 3)
BASELINE_CASE_SPECS = tuple((geometry, spin) for geometry in REQUIRED_GEOMETRIES for spin in REQUIRED_SPINS)
"""Canonical order: triangle S2, triangle S3, ring5 S2, ring5 S3."""

REQUIRED_TARGET_IDS = {
    "triangle": ("fundamental", "first_excited"),
    "ring5": ("fundamental", "first_excited", "T_3_2"),
}
"""T_max is EXCLUDED from this gate's comparison scope (section 20.19) --
never compared, though its manifest entry is still consulted internally
by the exclusion proof below (it participates in the closed set of
possible causes of historical persistence, without ever being an
output of this gate)."""


class HistoricalGroupProofError(RuntimeError):
    """Raised when a REQUIRED historical target's persisted group index
    cannot be proven by exclusion (section 22 audit) -- never resolved
    by a fallback, a heuristic, or an operator assertion."""


class BaselineGateInputError(RuntimeError):
    """Raised for a missing/invalid input to a single baseline case
    comparison (missing artifact, provenance mismatch, non-success run,
    normatively invalid case, schema violation). Always caught and
    converted into a FAIL CaseComparisonResult with an explicit
    failure_reason -- the gate itself never aborts early on a single
    case's problem, so all four baselines are always attempted and
    reported."""


# ---------------------------------------------------------------------------
# Historical group identity by exclusion (D022, section 22 audit)
# ---------------------------------------------------------------------------


def _target_could_explain_group(target: TargetGroupSpec, group_index: int, twice_T: int | None) -> bool:
    """The frozen, deterministic NECESSARY condition `target`'s own
    selection rule imposes on any group it could ever select -- never a
    sufficient condition, never a reconstruction of which candidate
    among several would have won. fundamental/first_excited's condition
    is purely positional (a direct consequence of how
    spectral_window_group_index is built, D022) -- never itself in
    doubt. flavor_label's condition is only "shares this twice_T" --
    the tie-break rule (lowest_representative_energy) is never
    re-applied here, and never needs to be: this function is used only
    to EXCLUDE targets that cannot possibly explain a given persisted
    group, never to pick a winner among several candidates."""
    if target.selection_kind == "fundamental":
        return group_index == 0
    if target.selection_kind == "first_excited":
        return group_index == 1
    if target.selection_kind == "flavor_label":
        return twice_T == target.target_twice_T
    if target.selection_kind == "structurally_not_applicable":
        return False
    raise ValueError(f"unsupported selection_kind {target.selection_kind!r}")


def historical_group_index_for_required_target(
    target_id: str,
    persisted_groups: Sequence[tuple[int, int | None]],
    geometry_targets: tuple[TargetGroupSpec, ...],
) -> int:
    """Proves, by exclusion over the CLOSED set of historical manifest
    targets for this geometry, which persisted group (spectral_window_
    group_index, twice_T) is the historical counterpart of `target_id`.

    fundamental/first_excited: positional, no exclusion needed --
    always spectral_window_group_index 0/1 respectively (a direct
    consequence of section 20.6/D022's own construction of that field,
    never a lookup of what Level1B's original run happened to select).

    flavor_label (e.g. ring5's T_3_2): proof by elimination. The
    historical runner only ever persists a group that SOME target in
    the closed manifest actually selected (scripts/level1b_campaign/
    runner.py: `if outcome.status != SELECTED: continue`). For a
    persisted group to be provably `target_id`'s counterpart: (1) it
    must satisfy target_id's own necessary condition (twice_T ==
    target_twice_T), and (2) NO OTHER target in the manifest may also
    satisfy ITS OWN necessary condition for that same group (otherwise
    the persisted group's true cause is ambiguous between two possible
    explanations). If exactly one persisted group satisfies both
    conditions, it is target_id's proven historical counterpart --
    never a reconstruction of the historical candidate pool, never the
    rejected heuristic "the unique group with a matching twice_T is the
    target" (that heuristic ignores condition (2) entirely and was
    explicitly rejected for T_max)."""
    target_spec = next((target for target in geometry_targets if target.target_id == target_id), None)
    if target_spec is None:
        raise HistoricalGroupProofError(f"no historical manifest target named {target_id!r} for this geometry")

    if target_spec.selection_kind == "fundamental":
        return 0
    if target_spec.selection_kind == "first_excited":
        return 1
    if target_spec.selection_kind != "flavor_label":
        raise HistoricalGroupProofError(
            f"target {target_id!r} has selection_kind {target_spec.selection_kind!r}, not supported by this proof"
        )

    other_targets = tuple(target for target in geometry_targets if target.target_id != target_id)
    candidates: list[int] = []
    for group_index, twice_T in persisted_groups:
        if not _target_could_explain_group(target_spec, group_index, twice_T):
            continue
        if any(_target_could_explain_group(other, group_index, twice_T) for other in other_targets):
            continue  # ambiguous cause: another manifest target could also explain this same group
        candidates.append(group_index)

    if not candidates:
        raise HistoricalGroupProofError(
            f"no persisted group satisfies the exclusion proof for target {target_id!r} "
            f"(persisted_groups={list(persisted_groups)})"
        )
    if len(candidates) > 1:
        raise HistoricalGroupProofError(
            f"more than one persisted group satisfies the exclusion proof for target {target_id!r}: {candidates}"
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# Common structural/observable data shape (both sides converted into this
# before any comparison -- comparison logic below never touches a
# CampaignArtifactIndex or a raw JSON document directly).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupStructuralData:
    spectral_window_group_index: int
    multiplicity: int
    twice_T: int | None
    translation_label: SymmetryLabel
    reflection_label: SymmetryLabel
    representative_energy: float
    ctt_pairs: Mapping[tuple[int, int], float]
    rho_pairs: Mapping[tuple[int, int], tuple[float | None, str | None]]


def historical_group_structural_data(group: IndexedSpectralGroup) -> GroupStructuralData:
    identity = group.spectral_group_identity
    return GroupStructuralData(
        spectral_window_group_index=identity.spectral_window_group_index,
        multiplicity=identity.multiplicity,
        twice_T=identity.twice_T,
        translation_label=group.match_key.translation_label,
        reflection_label=group.match_key.reflection_label,
        representative_energy=identity.representative_energy,
        ctt_pairs=extract_historical_ctt_pairs(group),
        rho_pairs=extract_historical_rho_pairs(group),
    )


def _symmetry_label_from_payload(payload: Mapping) -> SymmetryLabel:
    if payload["kind"] == "numeric":
        value = payload["value"]
        return SymmetryLabel(kind="numeric", value=complex(value["real"], value["imag"]))
    return SymmetryLabel(kind=payload["kind"], value=None)


def level1c_group_documents(documents: Sequence[Mapping], group_index: int) -> tuple[Mapping, ...]:
    return tuple(
        document
        for document in documents
        if document["identity"]["spectral_group"]["spectral_window_group_index"] == group_index
    )


def _extract_level1c_pairs(documents: Sequence[Mapping], *, record_kind: str, observable_kind: str) -> dict[tuple[int, int], object]:
    result: dict[tuple[int, int], object] = {}
    for document in documents:
        if document["record_kind"] != record_kind or document["observable_kind"] != observable_kind:
            continue
        path = document["identity"]["path"]
        if path is None or len(path) != 2 or path[0] == path[1]:
            continue
        result[(int(path[0]), int(path[1]))] = document["payload"]
    return result


def extract_level1c_ctt_pairs(documents: Sequence[Mapping]) -> dict[tuple[int, int], float]:
    return {
        pair: float(payload)
        for pair, payload in _extract_level1c_pairs(documents, record_kind="raw_observable", observable_kind="C_TT_conn").items()
    }


def extract_level1c_rho_pairs(documents: Sequence[Mapping]) -> dict[tuple[int, int], tuple[float | None, str | None]]:
    return {
        pair: (payload.get("value"), payload.get("null_reason"))
        for pair, payload in _extract_level1c_pairs(
            documents, record_kind="normalized_observable", observable_kind="rho_QQ"
        ).items()
    }


def level1c_group_structural_data(documents: Sequence[Mapping], group_index: int) -> GroupStructuralData:
    group_documents = level1c_group_documents(documents, group_index)
    if not group_documents:
        raise BaselineGateInputError(f"no Level1C documents found for spectral_window_group_index={group_index}")

    spectral_group = group_documents[0]["identity"]["spectral_group"]
    translation_label: SymmetryLabel | None = None
    reflection_label: SymmetryLabel | None = None
    for document in group_documents:
        if document["record_kind"] != "symmetry_label":
            continue
        if document["observable_kind"] == "translation_character":
            translation_label = _symmetry_label_from_payload(document["payload"])
        elif document["observable_kind"] == "reflection_character":
            reflection_label = _symmetry_label_from_payload(document["payload"])
    if translation_label is None or reflection_label is None:
        raise BaselineGateInputError(
            f"missing translation/reflection symmetry_label record(s) for spectral_window_group_index={group_index}"
        )

    return GroupStructuralData(
        spectral_window_group_index=group_index,
        multiplicity=spectral_group["multiplicity"],
        twice_T=spectral_group["twice_T"],
        translation_label=translation_label,
        reflection_label=reflection_label,
        representative_energy=spectral_group["representative_energy"],
        ctt_pairs=extract_level1c_ctt_pairs(group_documents),
        rho_pairs=extract_level1c_rho_pairs(group_documents),
    )


# ---------------------------------------------------------------------------
# Comparisons (sections 6-11 of the mandate)
# ---------------------------------------------------------------------------


def compare_structural(historical: GroupStructuralData, current: GroupStructuralData) -> tuple[str, tuple[str, ...]]:
    """multiplicity/twice_T: exact equality. translation/reflection:
    symmetry_labels_match with SYMMETRY_TOLERANCE only -- never the
    1e-15 non-regression tolerance, a different category (section 9).
    representative_energy is never compared here (OPTIONAL_DIAGNOSTIC,
    section 11)."""
    reasons: list[str] = []
    if historical.multiplicity != current.multiplicity:
        reasons.append(f"MULTIPLICITY_MISMATCH: historical={historical.multiplicity} current={current.multiplicity}")
    if historical.twice_T != current.twice_T:
        reasons.append(f"TWICE_T_MISMATCH: historical={historical.twice_T} current={current.twice_T}")
    if not symmetry_labels_match(historical.translation_label, current.translation_label, tolerance=SYMMETRY_TOLERANCE):
        reasons.append("TRANSLATION_LABEL_MISMATCH")
    if not symmetry_labels_match(historical.reflection_label, current.reflection_label, tolerance=SYMMETRY_TOLERANCE):
        reasons.append("REFLECTION_LABEL_MISMATCH")
    return (PASS if not reasons else FAIL), tuple(reasons)


def compare_ctt(historical: GroupStructuralData, current: GroupStructuralData, *, abs_tol: float) -> tuple[str, float | None, tuple[str, ...]]:
    """Strict pair-set equality, then max_abs_diff <= abs_tol -- never a
    relative tolerance, never a pair-set intersection (section 7)."""
    if set(historical.ctt_pairs) != set(current.ctt_pairs):
        return FAIL, None, ("CTT_PAIR_SET_MISMATCH",)

    max_abs_diff = 0.0
    for pair, historical_value in historical.ctt_pairs.items():
        current_value = current.ctt_pairs[pair]
        if not (math.isfinite(historical_value) and math.isfinite(current_value)):
            return FAIL, None, ("CTT_NON_FINITE_VALUE",)
        max_abs_diff = max(max_abs_diff, abs(historical_value - current_value))

    if max_abs_diff > abs_tol:
        return FAIL, max_abs_diff, (f"CTT_TOLERANCE_EXCEEDED: max_abs_diff={max_abs_diff!r} > {abs_tol!r}",)
    return PASS, max_abs_diff, ()


def compare_rho(historical: GroupStructuralData, current: GroupStructuralData, *, abs_tol: float) -> tuple[str, float | None, tuple[str, ...]]:
    """Strict pair-set equality; numeric/numeric compared with abs_tol;
    null/null requires identical null_reason; numeric/null or
    null/numeric always FAIL; null/null with a different null_reason
    always FAIL (section 8)."""
    if set(historical.rho_pairs) != set(current.rho_pairs):
        return FAIL, None, ("RHO_PAIR_SET_MISMATCH",)

    reasons: list[str] = []
    max_abs_diff: float | None = None
    for pair, (historical_value, historical_null_reason) in historical.rho_pairs.items():
        current_value, current_null_reason = current.rho_pairs[pair]
        historical_is_null = historical_value is None
        current_is_null = current_value is None
        if historical_is_null != current_is_null:
            reasons.append(f"RHO_NULLITY_MISMATCH at {pair}")
            continue
        if historical_is_null and current_is_null:
            if historical_null_reason != current_null_reason:
                reasons.append(f"RHO_NULL_REASON_MISMATCH at {pair}: {historical_null_reason!r} != {current_null_reason!r}")
            continue
        if not (math.isfinite(historical_value) and math.isfinite(current_value)):
            reasons.append(f"RHO_NON_FINITE_VALUE at {pair}")
            continue
        diff = abs(historical_value - current_value)
        max_abs_diff = diff if max_abs_diff is None else max(max_abs_diff, diff)

    if max_abs_diff is not None and max_abs_diff > abs_tol:
        reasons.append(f"RHO_TOLERANCE_EXCEEDED: max_abs_diff={max_abs_diff!r} > {abs_tol!r}")

    return (PASS if not reasons else FAIL), max_abs_diff, tuple(reasons)


# ---------------------------------------------------------------------------
# Per-target / per-case / global artifact structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetComparisonResult:
    target_id: str
    level1c_group_index: int | None
    historical_group_index: int | None
    structural_status: str
    ctt_status: str
    rho_status: str
    max_abs_ctt: float | None
    max_abs_rho: float | None
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaseComparisonResult:
    level1c_case_id: str | None
    historical_case_id: str | None
    geometry: str
    spin: int
    target_results: tuple[TargetComparisonResult, ...]
    structural_status: str
    ctt_status: str
    rho_status: str
    max_abs_ctt: float | None
    max_abs_rho: float | None
    case_status: str
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BaselineNonRegressionArtifact:
    schema_version: str
    campaign_id: str
    repository_commit: str
    manifest_fingerprint: str
    historical_campaign_id: str
    historical_manifest_fingerprint: str
    historical_repository_commit: str
    ctt_abs_tol: float
    rho_abs_tol: float
    case_comparisons: tuple[CaseComparisonResult, ...]
    e_ctt: float | None
    e_rho: float | None
    gate_status: str
    failure_reasons: tuple[str, ...]


def _aggregate_status(target_results: tuple[TargetComparisonResult, ...], field: str) -> str:
    if not target_results:
        return FAIL
    return PASS if all(getattr(result, field) == PASS for result in target_results) else FAIL


def _aggregate_max(target_results: tuple[TargetComparisonResult, ...], field: str) -> float | None:
    values = [value for value in (getattr(result, field) for result in target_results) if value is not None]
    return max(values) if values else None


def build_case_comparison_result(
    geometry: str,
    spin: int,
    level1c_case_id: str | None,
    historical_case_id: str | None,
    target_results: tuple[TargetComparisonResult, ...],
    extra_failure_reasons: tuple[str, ...] = (),
) -> CaseComparisonResult:
    structural_status = _aggregate_status(target_results, "structural_status")
    ctt_status = _aggregate_status(target_results, "ctt_status")
    rho_status = _aggregate_status(target_results, "rho_status")
    case_status = PASS if (structural_status == PASS and ctt_status == PASS and rho_status == PASS and not extra_failure_reasons) else FAIL
    failure_reasons = extra_failure_reasons + tuple(
        f"{result.target_id}: {reason}" for result in target_results for reason in result.failure_reasons
    )
    return CaseComparisonResult(
        level1c_case_id=level1c_case_id,
        historical_case_id=historical_case_id,
        geometry=geometry,
        spin=spin,
        target_results=target_results,
        structural_status=structural_status,
        ctt_status=ctt_status,
        rho_status=rho_status,
        max_abs_ctt=_aggregate_max(target_results, "max_abs_ctt"),
        max_abs_rho=_aggregate_max(target_results, "max_abs_rho"),
        case_status=case_status,
        failure_reasons=failure_reasons,
    )


# ---------------------------------------------------------------------------
# Level1C-side loading (read-only: never calls run_level1c_case, never
# diagonalizes)
# ---------------------------------------------------------------------------


def _case_hamiltonian_identity_tuple(case) -> tuple:
    """Generic, non-holdout-specific tuple representation of a
    CampaignCaseSpec's own Hamiltonian, for comparison against a
    document's identity.hamiltonian -- written locally rather than
    importing scripts.level1b_analysis.indexing's private equivalent
    across packages (same precedent as 1C-8c's runner.py)."""
    parameters = case.hamiltonian_parameters
    h_is_zero = all(bool((matrix == 0).all()) for matrix in parameters.h)
    return (
        tuple(float(value) for value in parameters.J),
        h_is_zero,
        float(parameters.t),
        float(parameters.g_E),
        float(parameters.K),
    )


def _document_hamiltonian_identity_tuple(hamiltonian: Mapping) -> tuple:
    return (
        tuple(float(value) for value in hamiltonian["J"]),
        hamiltonian["h_is_zero"],
        float(hamiltonian["t"]),
        float(hamiltonian["g_E"]),
        float(hamiltonian["K"]),
    )


def _expected_campaign_case_spec(level1c_manifest: Level1CManifest, case_id: str):
    """The exact CampaignCaseSpec build_level1c_campaign_plan(manifest)
    itself produces for `case_id` -- never a heuristic reconstruction.
    Raises BaselineGateInputError if case_id is not one of the
    manifest's own planned cases: a baseline's case_id must always
    resolve to a real planned case, exactly as scripts.level1b_campaign.
    runner._verify_case_belongs_to_manifest already requires for
    Level1B/Level1C production."""
    for case in build_level1c_campaign_plan(level1c_manifest):
        if case.case_id == case_id:
            return case
    raise BaselineGateInputError(f"case_id {case_id!r} is not present in build_level1c_campaign_plan(level1c_manifest)")


def _require_record_matches_expected_case(record: Mapping, expected_case, *, case_id: str, line_index: int) -> None:
    identity = record["identity"]
    if identity["geometry"] != expected_case.geometry:
        raise BaselineGateInputError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.geometry "
            f"({identity['geometry']!r}) does not match the expected case's geometry ({expected_case.geometry!r})"
        )
    if identity["spin"] != expected_case.spin:
        raise BaselineGateInputError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.spin ({identity['spin']!r}) "
            f"does not match the expected case's spin ({expected_case.spin!r})"
        )
    if identity["sector"] != expected_case.sector_id:
        raise BaselineGateInputError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.sector ({identity['sector']!r}) "
            f"does not match the expected case's sector_id ({expected_case.sector_id!r})"
        )
    if _document_hamiltonian_identity_tuple(identity["hamiltonian"]) != _case_hamiltonian_identity_tuple(expected_case):
        raise BaselineGateInputError(
            f"records.jsonl line {line_index} for case {case_id!r}: identity.hamiltonian does not match the "
            "expected case's own hamiltonian_parameters"
        )


def load_level1c_baseline_case(
    output_dir: Path, case_id: str, *, level1c_manifest: Level1CManifest
) -> tuple[dict, tuple[dict, ...]]:
    """Reads runs/<case_id>/{run.json,records.jsonl} from an already-
    produced Level1C case output directory. Raises BaselineGateInputError
    (never a bare exception) if the case is missing, invalid, not a
    technical success, not normatively valid, or its records.jsonl does
    not byte-exactly match run.json's own records_sha256/record_count --
    callers must never attempt a partial or integrity-broken comparison.

    The SHA-256 is always computed on the exact persisted bytes of
    records.jsonl, never reconstructed from parsed JSON documents: a
    file modified after production (structurally valid JSON, but
    different bytes) is caught here, before any comparison ever reads
    its content as ground truth. Internal blank lines are never
    silently dropped (reuses scripts.level1c_campaign.outputs.
    load_case_records's own canonical parsing, which already implements
    exactly this policy) -- only a single, conventional trailing
    newline is tolerated.
    """
    case_dir = Path(output_dir) / "runs" / case_id
    run_path = case_dir / "run.json"
    if not run_path.exists():
        raise BaselineGateInputError(f"missing Level1C run.json for case {case_id!r} under {output_dir}")

    try:
        run_document = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineGateInputError(f"Level1C run.json for case {case_id!r} could not be parsed: {exc}") from exc

    validate_case_run_document(run_document)

    if run_document["case_id"] != case_id:
        raise BaselineGateInputError(
            f"run.json case_id ({run_document['case_id']!r}) does not match the requested case_id ({case_id!r})"
        )
    if run_document["run_status"] != "success":
        raise BaselineGateInputError(f"case {case_id!r} run_status is {run_document['run_status']!r}, not 'success'")
    if run_document["normative_case_valid"] is not True:
        raise BaselineGateInputError(
            f"case {case_id!r} normative_case_valid is {run_document['normative_case_valid']!r}, not True -- "
            "a normatively invalid baseline can never be used for the non-regression gate"
        )

    records_path = case_dir / "records.jsonl"
    if not records_path.exists():
        raise BaselineGateInputError(f"missing records.jsonl for case {case_id!r} under {output_dir}")

    try:
        records_bytes = records_path.read_bytes()
    except OSError as exc:
        raise BaselineGateInputError(f"records.jsonl for case {case_id!r} could not be read: {exc}") from exc

    actual_sha256 = hashlib.sha256(records_bytes).hexdigest()
    if actual_sha256 != run_document["records_sha256"]:
        raise BaselineGateInputError(
            f"records.jsonl for case {case_id!r} SHA-256 ({actual_sha256}) does not match run.json "
            f"records_sha256 ({run_document['records_sha256']!r}) -- integrity check failed on the exact "
            "persisted bytes, never reconstructed from parsed JSON"
        )

    try:
        records = load_case_records(case_dir)
    except ValueError as exc:
        raise BaselineGateInputError(f"records.jsonl for case {case_id!r} could not be loaded: {exc}") from exc

    if len(records) != run_document["record_count"]:
        raise BaselineGateInputError(
            f"records.jsonl for case {case_id!r} has {len(records)} document(s), run.json record_count is "
            f"{run_document['record_count']!r}"
        )

    expected_case = _expected_campaign_case_spec(level1c_manifest, case_id)

    for index, record in enumerate(records):
        try:
            validate_result_record(record)
        except ValueError as exc:
            raise BaselineGateInputError(f"records.jsonl line {index} for case {case_id!r} failed schema validation: {exc}") from exc
        for key in ("campaign_id", "manifest_fingerprint", "repository_commit"):
            if record[key] != run_document[key]:
                raise BaselineGateInputError(
                    f"records.jsonl line {index} for case {case_id!r} has {key} ({record[key]!r}) that does not "
                    f"match run.json's own {key} ({run_document[key]!r})"
                )
        _require_record_matches_expected_case(record, expected_case, case_id=case_id, line_index=index)

    return run_document, tuple(records)


def _level1c_group_index_for_target(run_document: Mapping, target_id: str) -> int:
    for entry in run_document["target_selections"]:
        if entry["target_id"] == target_id:
            if entry["selection_status"] != "selected":
                raise BaselineGateInputError(
                    f"target {target_id!r} is REQUIRED but selection_status is {entry['selection_status']!r}, "
                    "not 'selected' -- this should never happen for a normative_case_valid=true case"
                )
            return entry["spectral_window_group_index"]
    raise BaselineGateInputError(f"target {target_id!r} not found in target_selections")


# ---------------------------------------------------------------------------
# Orchestration (never invoked against real data in this lot -- 1C-8d
# implements the tool only)
# ---------------------------------------------------------------------------


def compare_baseline_target(
    target_id: str,
    level1c_run_document: Mapping,
    level1c_records: Sequence[Mapping],
    historical_persisted_groups: Sequence[tuple[int, int | None]],
    historical_groups_by_index: Mapping[int, IndexedSpectralGroup],
    historical_geometry_targets: tuple[TargetGroupSpec, ...],
    *,
    ctt_abs_tol: float,
    rho_abs_tol: float,
) -> TargetComparisonResult:
    """Never raises: every failure mode is captured as a FAIL
    TargetComparisonResult with an explicit failure_reason."""
    try:
        level1c_group_index = _level1c_group_index_for_target(level1c_run_document, target_id)
    except BaselineGateInputError as exc:
        return TargetComparisonResult(target_id, None, None, FAIL, FAIL, FAIL, None, None, (f"LEVEL1C_TARGET_LOOKUP_FAILED: {exc}",))

    try:
        historical_group_index = historical_group_index_for_required_target(
            target_id, historical_persisted_groups, historical_geometry_targets
        )
    except HistoricalGroupProofError as exc:
        return TargetComparisonResult(target_id, level1c_group_index, None, FAIL, FAIL, FAIL, None, None, (f"HISTORICAL_GROUP_PROOF_FAILED: {exc}",))

    historical_group = historical_groups_by_index.get(historical_group_index)
    if historical_group is None:
        return TargetComparisonResult(
            target_id, level1c_group_index, historical_group_index, FAIL, FAIL, FAIL, None, None,
            (f"HISTORICAL_GROUP_NOT_PERSISTED: index {historical_group_index}",),
        )

    try:
        historical_data = historical_group_structural_data(historical_group)
        current_data = level1c_group_structural_data(level1c_records, level1c_group_index)
    except BaselineGateInputError as exc:
        return TargetComparisonResult(target_id, level1c_group_index, historical_group_index, FAIL, FAIL, FAIL, None, None, (str(exc),))

    structural_status, structural_reasons = compare_structural(historical_data, current_data)
    ctt_status, max_abs_ctt, ctt_reasons = compare_ctt(historical_data, current_data, abs_tol=ctt_abs_tol)
    rho_status, max_abs_rho, rho_reasons = compare_rho(historical_data, current_data, abs_tol=rho_abs_tol)

    return TargetComparisonResult(
        target_id=target_id,
        level1c_group_index=level1c_group_index,
        historical_group_index=historical_group_index,
        structural_status=structural_status,
        ctt_status=ctt_status,
        rho_status=rho_status,
        max_abs_ctt=max_abs_ctt,
        max_abs_rho=max_abs_rho,
        failure_reasons=structural_reasons + ctt_reasons + rho_reasons,
    )


def compare_baseline_case(
    geometry: str,
    spin: int,
    level1c_manifest: Level1CManifest,
    level1c_output_dir: Path,
    level1c_case_id: str,
    historical_index: CampaignArtifactIndex,
    historical_manifest: Manifest,
    historical_case_id: str,
    *,
    repository_commit: str,
    ctt_abs_tol: float,
    rho_abs_tol: float,
) -> CaseComparisonResult:
    """Never raises: any failure produces a FAIL CaseComparisonResult
    with diagnostic failure_reasons, so all four baselines are always
    attempted and reported (section 1/3: absence/invalidity of a single
    baseline never aborts the others)."""
    try:
        run_document, records = load_level1c_baseline_case(level1c_output_dir, level1c_case_id, level1c_manifest=level1c_manifest)
    except BaselineGateInputError as exc:
        return build_case_comparison_result(geometry, spin, level1c_case_id, historical_case_id, (), (f"LEVEL1C_BASELINE_UNAVAILABLE: {exc}",))

    provenance_reasons = []
    if run_document["campaign_id"] != level1c_manifest.campaign_id:
        provenance_reasons.append("LEVEL1C_CAMPAIGN_ID_MISMATCH")
    if run_document["manifest_fingerprint"] != level1c_manifest.fingerprint:
        provenance_reasons.append("LEVEL1C_MANIFEST_FINGERPRINT_MISMATCH")
    if run_document["repository_commit"] != repository_commit:
        provenance_reasons.append("LEVEL1C_REPOSITORY_COMMIT_MISMATCH")
    if provenance_reasons:
        return build_case_comparison_result(geometry, spin, level1c_case_id, historical_case_id, (), tuple(provenance_reasons))

    historical_groups_for_case = tuple(
        (group.spectral_window_group_index, group.spectral_group_identity.twice_T)
        for group in historical_index.groups
        if group.case_id == historical_case_id
    )
    if not historical_groups_for_case:
        return build_case_comparison_result(
            geometry, spin, level1c_case_id, historical_case_id, (), (f"HISTORICAL_BASELINE_UNAVAILABLE: no groups persisted for {historical_case_id!r}",)
        )
    historical_groups_by_index = {
        group.spectral_window_group_index: group for group in historical_index.groups if group.case_id == historical_case_id
    }
    historical_geometry_targets = historical_manifest.target_groups[geometry]

    target_results = tuple(
        compare_baseline_target(
            target_id,
            run_document,
            records,
            historical_groups_for_case,
            historical_groups_by_index,
            historical_geometry_targets,
            ctt_abs_tol=ctt_abs_tol,
            rho_abs_tol=rho_abs_tol,
        )
        for target_id in REQUIRED_TARGET_IDS[geometry]
    )

    return build_case_comparison_result(geometry, spin, level1c_case_id, historical_case_id, target_results)


def run_baseline_nonregression_gate(
    level1c_manifest: Level1CManifest,
    level1c_output_dir: Path,
    historical_output_dir: Path,
    *,
    repository_commit: str,
) -> BaselineNonRegressionArtifact:
    """Never diagonalizes, never calls run_level1c_case. Reads the four
    Level1C baselines (already produced) and the Level1B historical
    corpus (already produced), compares them, and returns a fully
    populated artifact -- PASS only if all four baselines are present/
    valid AND every structural/CTT/rho comparison passes AND provenance
    is complete/coherent (section 16). Never invoked against real data
    in this lot (1C-8d implements the tool only)."""
    calibration = level1c_manifest.non_regression_calibration
    ctt_abs_tol = calibration.ctt_abs_tol
    rho_abs_tol = calibration.rho_abs_tol

    historical_manifest = load_manifest()

    try:
        historical_index = build_campaign_artifact_index(
            historical_manifest, Path(historical_output_dir), repository_commit=HISTORICAL_REPOSITORY_COMMIT
        )
    except (CampaignLoadError, SpectralGroupIndexError, UnresolvedFlavorLabelError) as exc:
        case_comparisons = tuple(
            build_case_comparison_result(geometry, spin, None, None, (), (f"HISTORICAL_CAMPAIGN_UNUSABLE: {exc}",))
            for geometry, spin in BASELINE_CASE_SPECS
        )
        return _finalize_artifact(level1c_manifest, repository_commit, case_comparisons, ctt_abs_tol, rho_abs_tol)

    provenance_reasons: tuple[str, ...] = ()
    if historical_index.campaign_id != HISTORICAL_CAMPAIGN_ID or historical_index.manifest_fingerprint != HISTORICAL_MANIFEST_FINGERPRINT:
        provenance_reasons = ("HISTORICAL_CAMPAIGN_PROVENANCE_MISMATCH",)

    historical_case_id_by_geometry_spin: dict[tuple[str, int], str] = {}
    for case in build_campaign_plan(historical_manifest):
        if case.hamiltonian_case_id == "reference" and (case.geometry, case.spin) in BASELINE_CASE_SPECS:
            historical_case_id_by_geometry_spin[(case.geometry, case.spin)] = case.case_id

    level1c_cases_by_geometry_spin = {
        (geometry, spin): _level1c_baseline_case_id(level1c_manifest, geometry, spin) for geometry, spin in BASELINE_CASE_SPECS
    }

    case_comparisons = []
    for geometry, spin in BASELINE_CASE_SPECS:
        if provenance_reasons:
            case_comparisons.append(
                build_case_comparison_result(geometry, spin, level1c_cases_by_geometry_spin.get((geometry, spin)), historical_case_id_by_geometry_spin.get((geometry, spin)), (), provenance_reasons)
            )
            continue
        historical_case_id = historical_case_id_by_geometry_spin.get((geometry, spin))
        level1c_case_id = level1c_cases_by_geometry_spin.get((geometry, spin))
        if historical_case_id is None or level1c_case_id is None:
            case_comparisons.append(
                build_case_comparison_result(geometry, spin, level1c_case_id, historical_case_id, (), ("CASE_IDENTITY_UNRESOLVED",))
            )
            continue
        case_comparisons.append(
            compare_baseline_case(
                geometry,
                spin,
                level1c_manifest,
                Path(level1c_output_dir),
                level1c_case_id,
                historical_index,
                historical_manifest,
                historical_case_id,
                repository_commit=repository_commit,
                ctt_abs_tol=ctt_abs_tol,
                rho_abs_tol=rho_abs_tol,
            )
        )

    return _finalize_artifact(level1c_manifest, repository_commit, tuple(case_comparisons), ctt_abs_tol, rho_abs_tol)


def _level1c_baseline_case_id(level1c_manifest: Level1CManifest, geometry: str, spin: int) -> str | None:
    baseline_hamiltonian_case_id = hamiltonian_case_id_for_j0(J0_BASELINE)
    for case in build_level1c_campaign_plan(level1c_manifest):
        if case.geometry == geometry and case.spin == spin and case.hamiltonian_case_id == baseline_hamiltonian_case_id:
            return case.case_id
    return None


def _finalize_artifact(
    level1c_manifest: Level1CManifest,
    repository_commit: str,
    case_comparisons: tuple[CaseComparisonResult, ...],
    ctt_abs_tol: float,
    rho_abs_tol: float,
) -> BaselineNonRegressionArtifact:
    failure_reasons: list[str] = []
    if len(case_comparisons) != 4:
        failure_reasons.append(f"expected exactly 4 baseline case comparisons, got {len(case_comparisons)}")
    for case_result in case_comparisons:
        if case_result.case_status != PASS:
            failure_reasons.append(f"({case_result.geometry}, S={case_result.spin}): {case_result.case_status}")

    e_ctt = _max_optional(result.max_abs_ctt for result in case_comparisons)
    e_rho = _max_optional(result.max_abs_rho for result in case_comparisons)

    gate_status = PASS if not failure_reasons else FAIL

    return BaselineNonRegressionArtifact(
        schema_version=SCHEMA_VERSION,
        campaign_id=level1c_manifest.campaign_id,
        repository_commit=repository_commit,
        manifest_fingerprint=level1c_manifest.fingerprint,
        historical_campaign_id=HISTORICAL_CAMPAIGN_ID,
        historical_manifest_fingerprint=HISTORICAL_MANIFEST_FINGERPRINT,
        historical_repository_commit=HISTORICAL_REPOSITORY_COMMIT,
        ctt_abs_tol=ctt_abs_tol,
        rho_abs_tol=rho_abs_tol,
        case_comparisons=case_comparisons,
        e_ctt=e_ctt,
        e_rho=e_rho,
        gate_status=gate_status,
        failure_reasons=tuple(failure_reasons),
    )


def _max_optional(values) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


# ---------------------------------------------------------------------------
# Canonical serialization / schema validation
# ---------------------------------------------------------------------------


def _target_comparison_payload(result: TargetComparisonResult) -> dict:
    return {
        "target_id": result.target_id,
        "level1c_group_index": result.level1c_group_index,
        "historical_group_index": result.historical_group_index,
        "structural_status": result.structural_status,
        "ctt_status": result.ctt_status,
        "rho_status": result.rho_status,
        "max_abs_ctt": result.max_abs_ctt,
        "max_abs_rho": result.max_abs_rho,
        "failure_reasons": list(result.failure_reasons),
    }


def _case_comparison_payload(result: CaseComparisonResult) -> dict:
    return {
        "level1c_case_id": result.level1c_case_id,
        "historical_case_id": result.historical_case_id,
        "geometry": result.geometry,
        "spin": result.spin,
        "target_results": [_target_comparison_payload(target_result) for target_result in result.target_results],
        "structural_status": result.structural_status,
        "ctt_status": result.ctt_status,
        "rho_status": result.rho_status,
        "max_abs_ctt": result.max_abs_ctt,
        "max_abs_rho": result.max_abs_rho,
        "case_status": result.case_status,
        "failure_reasons": list(result.failure_reasons),
    }


def to_json_dict(artifact: BaselineNonRegressionArtifact) -> dict:
    return {
        "schema_version": artifact.schema_version,
        "campaign_id": artifact.campaign_id,
        "repository_commit": artifact.repository_commit,
        "manifest_fingerprint": artifact.manifest_fingerprint,
        "historical_campaign_id": artifact.historical_campaign_id,
        "historical_manifest_fingerprint": artifact.historical_manifest_fingerprint,
        "historical_repository_commit": artifact.historical_repository_commit,
        "ctt_abs_tol": artifact.ctt_abs_tol,
        "rho_abs_tol": artifact.rho_abs_tol,
        "case_comparisons": [_case_comparison_payload(case_result) for case_result in artifact.case_comparisons],
        "e_ctt": artifact.e_ctt,
        "e_rho": artifact.e_rho,
        "gate_status": artifact.gate_status,
        "failure_reasons": list(artifact.failure_reasons),
    }


def canonical_json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_gate_artifact_document(document: dict) -> None:
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against the Level1C baseline non-regression gate schema: {messages}")
