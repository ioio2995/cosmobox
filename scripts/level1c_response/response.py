"""PHASE_R response core: ResponseRecord, eligibility gate, Delta_C_TT,
rho_QQ pairwise concordance control, artifact schema, and orchestration.
Lot 1C-8f-impl. See the package docstring for the full scope.

This module performs no diagonalization, no re-tracking, and no
re-execution of PHASE_P or the baseline non-regression gate.
"""

from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator

from cosmobox.level1.matching import NUMERIC, SymmetryLabel
from experiments.level1c.manifest import GEOMETRIES, Level1CManifest, SPIN_VALUES
from scripts.level1c_baseline_gate.gate import (
    BaselineGateInputError,
    GroupStructuralData,
    level1c_group_documents,
    level1c_group_structural_data,
)
from scripts.level1c_tracking.tracking import (
    EMITTABLE_TRACKING_STATUSES,
    TRACKED_ONE_TO_ONE,
    load_and_verify_tracking_records,
    load_baseline_for_tracking,
    load_perturbed_for_tracking,
)

SCHEMA_VERSION = "level1c-response-record-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "response-record-v1.schema.json"

RESPONSE_AVAILABLE = "RESPONSE_AVAILABLE"
RESPONSE_NOT_AVAILABLE = "RESPONSE_NOT_AVAILABLE"
RESPONSE_STATUSES = (RESPONSE_AVAILABLE, RESPONSE_NOT_AVAILABLE)
"""RESPONSE_ELIGIBILITY (identifiability-preregistration.md section
20.17): orthogonal to tracking_status, never fused with it, never a
physical verdict."""

_GIT_SHA_LENGTH = 40
_GIT_SHA_DIGITS = frozenset("0123456789abcdef")


def _is_git_sha_hex(value: str) -> bool:
    return isinstance(value, str) and len(value) == _GIT_SHA_LENGTH and set(value) <= _GIT_SHA_DIGITS


# ---------------------------------------------------------------------------
# Payload structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeltaCTTPair:
    """Delta_C_TT(i,j) = C_TT_conn_perturbed(i,j) - C_TT_conn_baseline(i,j)
    -- a direct arithmetic difference, never a tolerance-gated
    comparison, never a physical significance threshold (section 20.17,
    PHYSICAL_RESPONSE_THRESHOLD=OPEN)."""

    i: int
    j: int
    baseline_value: float
    perturbed_value: float
    delta: float

    def __post_init__(self) -> None:
        if isinstance(self.i, bool) or not isinstance(self.i, int) or self.i < 0:
            raise ValueError(f"i must be a non-negative int, got {self.i!r}")
        if isinstance(self.j, bool) or not isinstance(self.j, int) or self.j < 0:
            raise ValueError(f"j must be a non-negative int, got {self.j!r}")
        if self.i == self.j:
            raise ValueError(f"i and j must differ (off-diagonal only), got i=j={self.i!r}")
        for name, value in (("baseline_value", self.baseline_value), ("perturbed_value", self.perturbed_value), ("delta", self.delta)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
        expected_delta = self.perturbed_value - self.baseline_value
        if self.delta != expected_delta:
            raise ValueError(
                f"delta ({self.delta!r}) does not match perturbed_value - baseline_value ({expected_delta!r}) -- "
                "a well-formed but wrong delta is a provenance failure"
            )


@dataclass(frozen=True, slots=True)
class RhoPairControl:
    """rho_QQ_baseline(i,j) and rho_QQ_perturbed(i,j) juxtaposed side by
    side -- a descriptive control, never a derived observable. No
    delta/ratio/relative_change field exists on this dataclass at all
    (RHO_RESPONSE_ROLE=PAIRWISE_CONCORDANCE_CONTROL): all four
    numeric/null combinations are preserved exactly, with no verdict
    derived from a numeric/null mismatch."""

    i: int
    j: int
    baseline_value: float | None
    baseline_null_reason: str | None
    perturbed_value: float | None
    perturbed_null_reason: str | None

    def __post_init__(self) -> None:
        if isinstance(self.i, bool) or not isinstance(self.i, int) or self.i < 0:
            raise ValueError(f"i must be a non-negative int, got {self.i!r}")
        if isinstance(self.j, bool) or not isinstance(self.j, int) or self.j < 0:
            raise ValueError(f"j must be a non-negative int, got {self.j!r}")
        if self.i == self.j:
            raise ValueError(f"i and j must differ (off-diagonal only), got i=j={self.i!r}")
        for value_name, reason_name in (
            ("baseline_value", "baseline_null_reason"),
            ("perturbed_value", "perturbed_null_reason"),
        ):
            value = getattr(self, value_name)
            reason = getattr(self, reason_name)
            if (value is None) != (reason is not None):
                raise ValueError(f"{reason_name} must be set if and only if {value_name} is null")
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f"{value_name} must be a finite number or None, got {value!r}")


# ---------------------------------------------------------------------------
# ResponseRecord: structure, validation, canonical serialization
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResponseRecord:
    """One PHASE_R response outcome for one (target_id, tracking edge)
    pair, one-to-one with a tracking-record-v1 document.

    Null-ability contract: response_eligibility==RESPONSE_AVAILABLE
    requires tracking_status==TRACKED_ONE_TO_ONE, baseline_group_index/
    perturbed_group_index both non-null, delta_ctt_pairs/
    rho_pair_controls both non-null, and failure_reasons empty.
    response_eligibility==RESPONSE_NOT_AVAILABLE requires delta_ctt_pairs
    and rho_pair_controls both null and failure_reasons non-empty --
    never a partial scientific payload under RESPONSE_NOT_AVAILABLE.
    baseline_group_index/perturbed_group_index remain diagnostic
    pass-through fields (transcribed from the source tracking record)
    and may be populated even under RESPONSE_NOT_AVAILABLE."""

    schema_version: str
    campaign_id: str
    repository_commit: str
    manifest_fingerprint: str
    geometry: str
    spin: int
    baseline_case_id: str
    perturbed_case_id: str
    baseline_hamiltonian_case_id: str
    perturbed_hamiltonian_case_id: str
    target_id: str
    tracking_status: str
    response_eligibility: str
    baseline_group_index: int | None
    perturbed_group_index: int | None
    delta_ctt_pairs: tuple[DeltaCTTPair, ...] | None
    rho_pair_controls: tuple[RhoPairControl, ...] | None
    failure_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}, got {self.schema_version!r}")
        if self.campaign_id != "level1c-j0-response-v1":
            raise ValueError(f"campaign_id must be 'level1c-j0-response-v1', got {self.campaign_id!r}")
        if not _is_git_sha_hex(self.repository_commit):
            raise ValueError(f"repository_commit must be a 40-hex-character git SHA, got {self.repository_commit!r}")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin not in SPIN_VALUES:
            raise ValueError(f"spin must be one of {SPIN_VALUES}, got {self.spin!r}")
        for field_name, value in (
            ("baseline_case_id", self.baseline_case_id),
            ("perturbed_case_id", self.perturbed_case_id),
            ("baseline_hamiltonian_case_id", self.baseline_hamiltonian_case_id),
            ("perturbed_hamiltonian_case_id", self.perturbed_hamiltonian_case_id),
            ("target_id", self.target_id),
        ):
            if not value:
                raise ValueError(f"{field_name} must be non-empty")

        if self.tracking_status not in EMITTABLE_TRACKING_STATUSES:
            raise ValueError(f"tracking_status must be one of {EMITTABLE_TRACKING_STATUSES}, got {self.tracking_status!r}")
        if self.response_eligibility not in RESPONSE_STATUSES:
            raise ValueError(f"response_eligibility must be one of {RESPONSE_STATUSES}, got {self.response_eligibility!r}")

        if self.response_eligibility == RESPONSE_AVAILABLE:
            if self.tracking_status != TRACKED_ONE_TO_ONE:
                raise ValueError("tracking_status must be TRACKED_ONE_TO_ONE when response_eligibility == RESPONSE_AVAILABLE")
            if self.baseline_group_index is None or self.perturbed_group_index is None:
                raise ValueError("baseline_group_index and perturbed_group_index must both be set when RESPONSE_AVAILABLE")
            if self.delta_ctt_pairs is None or self.rho_pair_controls is None:
                raise ValueError("delta_ctt_pairs and rho_pair_controls must both be set when RESPONSE_AVAILABLE")
            if self.failure_reasons:
                raise ValueError("failure_reasons must be empty when response_eligibility == RESPONSE_AVAILABLE")
        else:
            if self.delta_ctt_pairs is not None or self.rho_pair_controls is not None:
                raise ValueError(
                    "delta_ctt_pairs and rho_pair_controls must both be None when response_eligibility == "
                    "RESPONSE_NOT_AVAILABLE -- never a partial scientific payload"
                )
            if not self.failure_reasons:
                raise ValueError("failure_reasons must be non-empty when response_eligibility == RESPONSE_NOT_AVAILABLE")


def _symmetry_label_payload(label: SymmetryLabel) -> dict:
    if label.kind == NUMERIC:
        return {"kind": "numeric", "value": {"real": label.value.real, "imag": label.value.imag}}
    return {"kind": label.kind, "value": None}


def _delta_ctt_pair_payload(pair: DeltaCTTPair) -> dict:
    return {"i": pair.i, "j": pair.j, "baseline_value": pair.baseline_value, "perturbed_value": pair.perturbed_value, "delta": pair.delta}


def _rho_pair_control_payload(control: RhoPairControl) -> dict:
    return {
        "i": control.i,
        "j": control.j,
        "baseline_value": control.baseline_value,
        "baseline_null_reason": control.baseline_null_reason,
        "perturbed_value": control.perturbed_value,
        "perturbed_null_reason": control.perturbed_null_reason,
    }


def to_json_dict(record: ResponseRecord) -> dict:
    return {
        "schema_version": record.schema_version,
        "campaign_id": record.campaign_id,
        "repository_commit": record.repository_commit,
        "manifest_fingerprint": record.manifest_fingerprint,
        "geometry": record.geometry,
        "spin": record.spin,
        "baseline_case_id": record.baseline_case_id,
        "perturbed_case_id": record.perturbed_case_id,
        "baseline_hamiltonian_case_id": record.baseline_hamiltonian_case_id,
        "perturbed_hamiltonian_case_id": record.perturbed_hamiltonian_case_id,
        "target_id": record.target_id,
        "tracking_status": record.tracking_status,
        "response_eligibility": record.response_eligibility,
        "baseline_group_index": record.baseline_group_index,
        "perturbed_group_index": record.perturbed_group_index,
        "delta_ctt_pairs": None if record.delta_ctt_pairs is None else [_delta_ctt_pair_payload(pair) for pair in record.delta_ctt_pairs],
        "rho_pair_controls": None if record.rho_pair_controls is None else [_rho_pair_control_payload(control) for control in record.rho_pair_controls],
        "failure_reasons": list(record.failure_reasons),
    }


def canonical_json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_response_record_document(document: dict) -> None:
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against the Level1C response-record schema: {messages}")


# ---------------------------------------------------------------------------
# Observable extraction (duplicate/missing/non-finite discipline, section
# 15/19 of the mandate -- never a silent duplicate pick, never a
# coercion of a non-finite value)
# ---------------------------------------------------------------------------


def _extract_unique_ctt_pairs(group_documents: Sequence[Mapping]) -> tuple[dict[tuple[int, int], float] | None, str | None]:
    """Returns (pairs, None) on success or (None, failure_reason) on a
    duplicate or non-finite value -- never silently picks one of several
    duplicate records for the same pair."""
    counts: dict[tuple[int, int], int] = {}
    values: dict[tuple[int, int], float] = {}
    for document in group_documents:
        if document["record_kind"] != "raw_observable" or document["observable_kind"] != "C_TT_conn":
            continue
        path = document["identity"]["path"]
        if path is None or len(path) != 2 or path[0] == path[1]:
            continue
        pair = (int(path[0]), int(path[1]))
        counts[pair] = counts.get(pair, 0) + 1
        values[pair] = document["payload"]

    duplicates = sorted(pair for pair, count in counts.items() if count > 1)
    if duplicates:
        return None, f"CTT_DUPLICATE_PAIR: {duplicates}"

    for pair, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None, f"CTT_NON_FINITE_VALUE: {pair}"

    return values, None


def _extract_unique_rho_pairs(
    group_documents: Sequence[Mapping],
) -> tuple[dict[tuple[int, int], tuple[float | None, str | None]] | None, str | None]:
    """Same duplicate/non-finite discipline as _extract_unique_ctt_pairs,
    plus preserved numeric/null semantics -- never a coercion null->0."""
    counts: dict[tuple[int, int], int] = {}
    values: dict[tuple[int, int], tuple[float | None, str | None]] = {}
    for document in group_documents:
        if document["record_kind"] != "normalized_observable" or document["observable_kind"] != "rho_QQ":
            continue
        path = document["identity"]["path"]
        if path is None or len(path) != 2 or path[0] == path[1]:
            continue
        pair = (int(path[0]), int(path[1]))
        counts[pair] = counts.get(pair, 0) + 1
        payload = document["payload"]
        values[pair] = (payload.get("value"), payload.get("null_reason"))

    duplicates = sorted(pair for pair, count in counts.items() if count > 1)
    if duplicates:
        return None, f"RHO_DUPLICATE_PAIR: {duplicates}"

    for pair, (value, _null_reason) in values.items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            return None, f"RHO_NON_FINITE_VALUE: {pair}"

    return values, None


# ---------------------------------------------------------------------------
# Local eligibility gates (sections 10-13 of the mandate)
# ---------------------------------------------------------------------------


def _find_target_selection_entry(run_document: Mapping, target_id: str) -> Mapping | None:
    for entry in run_document["target_selections"]:
        if entry["target_id"] == target_id:
            return entry
    return None


def _target_locally_selected_on(run_document: Mapping, target_id: str, expected_group_index: int) -> bool:
    """The LOCAL, per-target gate (section 11 of the mandate): this
    target_id alone (never the case-level normative_case_valid
    aggregate) must be SELECTED, normatively conformant, and resolved to
    exactly `expected_group_index` -- a case that is globally
    normative_case_valid==false because of a DIFFERENT REQUIRED target
    can still yield RESPONSE_AVAILABLE for this one."""
    entry = _find_target_selection_entry(run_document, target_id)
    if entry is None:
        return False
    return (
        entry["selection_status"] == "selected"
        and entry["meets_normative_requirements"] is True
        and entry["spectral_window_group_index"] == expected_group_index
    )


def _tracking_p_cross_check_reasons(
    tracking_document: Mapping, baseline_structural: GroupStructuralData, perturbed_structural: GroupStructuralData
) -> tuple[str, ...]:
    """Re-derives baseline/candidate structural facts directly from the
    P records actually loaded, and compares them against tracking.jsonl's
    own persisted values for exact/consistent agreement -- never a new
    tolerance (the scientific matching, symmetry_labels_match/
    SYMMETRY_TOLERANCE, already happened in PHASE_T; R only checks that
    tracking.jsonl was not altered relative to the P artifacts it claims
    to summarize)."""
    reasons: list[str] = []
    if tracking_document["baseline_multiplicity"] != baseline_structural.multiplicity:
        reasons.append("TRACKING_P_BASELINE_MULTIPLICITY_MISMATCH")
    if tracking_document["baseline_twice_T"] != baseline_structural.twice_T:
        reasons.append("TRACKING_P_BASELINE_TWICE_T_MISMATCH")
    if tracking_document["baseline_reflection_label"] != _symmetry_label_payload(baseline_structural.reflection_label):
        reasons.append("TRACKING_P_BASELINE_REFLECTION_MISMATCH")
    if tracking_document["candidate_multiplicity"] != perturbed_structural.multiplicity:
        reasons.append("TRACKING_P_CANDIDATE_MULTIPLICITY_MISMATCH")
    if tracking_document["candidate_twice_T"] != perturbed_structural.twice_T:
        reasons.append("TRACKING_P_CANDIDATE_TWICE_T_MISMATCH")
    if tracking_document["candidate_reflection_label"] != _symmetry_label_payload(perturbed_structural.reflection_label):
        reasons.append("TRACKING_P_CANDIDATE_REFLECTION_MISMATCH")
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Per-tracking-record response construction (sections 6-23 of the mandate)
# ---------------------------------------------------------------------------


def build_response_record(
    tracking_document: Mapping,
    baseline_loaded: tuple[dict | None, tuple[dict, ...] | None, str | None],
    perturbed_loaded: tuple[dict | None, tuple[dict, ...] | None, str | None],
    *,
    campaign_id: str,
    repository_commit: str,
    manifest_fingerprint: str,
) -> ResponseRecord:
    """Never raises: every unavailable/inconsistent state is captured as
    a RESPONSE_NOT_AVAILABLE ResponseRecord with an explicit
    failure_reason. `baseline_loaded`/`perturbed_loaded` are the exact
    (run_document, records, failure_reason) tuples returned by
    scripts.level1c_tracking.tracking's own load_baseline_for_tracking/
    load_perturbed_for_tracking -- never reloaded independently here."""
    geometry = tracking_document["geometry"]
    spin = tracking_document["spin"]
    baseline_case_id = tracking_document["baseline_case_id"]
    perturbed_case_id = tracking_document["perturbed_case_id"]
    baseline_hamiltonian_case_id = tracking_document["baseline_hamiltonian_case_id"]
    perturbed_hamiltonian_case_id = tracking_document["perturbed_hamiltonian_case_id"]
    target_id = tracking_document["target_id"]
    tracking_status = tracking_document["status"]
    baseline_group_index = tracking_document["baseline_group_index"]
    perturbed_group_index = tracking_document["candidate_group_index"]

    def _record(*, response_eligibility: str, delta_ctt_pairs=None, rho_pair_controls=None, failure_reasons: tuple[str, ...] = ()) -> ResponseRecord:
        return ResponseRecord(
            schema_version=SCHEMA_VERSION,
            campaign_id=campaign_id,
            repository_commit=repository_commit,
            manifest_fingerprint=manifest_fingerprint,
            geometry=geometry,
            spin=spin,
            baseline_case_id=baseline_case_id,
            perturbed_case_id=perturbed_case_id,
            baseline_hamiltonian_case_id=baseline_hamiltonian_case_id,
            perturbed_hamiltonian_case_id=perturbed_hamiltonian_case_id,
            target_id=target_id,
            tracking_status=tracking_status,
            response_eligibility=response_eligibility,
            baseline_group_index=baseline_group_index,
            perturbed_group_index=perturbed_group_index,
            delta_ctt_pairs=delta_ctt_pairs,
            rho_pair_controls=rho_pair_controls,
            failure_reasons=failure_reasons,
        )

    if tracking_status != TRACKED_ONE_TO_ONE:
        return _record(
            response_eligibility=RESPONSE_NOT_AVAILABLE,
            failure_reasons=(f"TRACKING_STATUS_NOT_TRACKED_ONE_TO_ONE: {tracking_status}",),
        )

    baseline_run_document, baseline_records, baseline_failure_reason = baseline_loaded
    if baseline_failure_reason is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"BASELINE_UNAVAILABLE: {baseline_failure_reason}",))

    if not _target_locally_selected_on(baseline_run_document, target_id, baseline_group_index):
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=("BASELINE_TARGET_SELECTION_MISMATCH",))

    perturbed_run_document, perturbed_records, perturbed_failure_reason = perturbed_loaded
    if perturbed_failure_reason is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"PERTURBED_UNAVAILABLE: {perturbed_failure_reason}",))

    if not _target_locally_selected_on(perturbed_run_document, target_id, perturbed_group_index):
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=("PERTURBED_TARGET_SELECTION_MISMATCH",))

    try:
        baseline_structural = level1c_group_structural_data(baseline_records, baseline_group_index)
        perturbed_structural = level1c_group_structural_data(perturbed_records, perturbed_group_index)
    except BaselineGateInputError as exc:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"STRUCTURAL_DATA_UNAVAILABLE: {exc}",))

    cross_check_reasons = _tracking_p_cross_check_reasons(tracking_document, baseline_structural, perturbed_structural)
    if cross_check_reasons:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=cross_check_reasons)

    baseline_group_documents = level1c_group_documents(baseline_records, baseline_group_index)
    perturbed_group_documents = level1c_group_documents(perturbed_records, perturbed_group_index)

    baseline_ctt, baseline_ctt_error = _extract_unique_ctt_pairs(baseline_group_documents)
    if baseline_ctt_error is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"BASELINE_{baseline_ctt_error}",))
    perturbed_ctt, perturbed_ctt_error = _extract_unique_ctt_pairs(perturbed_group_documents)
    if perturbed_ctt_error is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"PERTURBED_{perturbed_ctt_error}",))

    if set(baseline_ctt) != set(perturbed_ctt):
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=("CTT_PAIR_SET_MISMATCH",))

    baseline_rho, baseline_rho_error = _extract_unique_rho_pairs(baseline_group_documents)
    if baseline_rho_error is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"BASELINE_{baseline_rho_error}",))
    perturbed_rho, perturbed_rho_error = _extract_unique_rho_pairs(perturbed_group_documents)
    if perturbed_rho_error is not None:
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=(f"PERTURBED_{perturbed_rho_error}",))

    if set(baseline_rho) != set(perturbed_rho):
        return _record(response_eligibility=RESPONSE_NOT_AVAILABLE, failure_reasons=("RHO_PAIR_SET_MISMATCH",))

    delta_ctt_pairs = tuple(
        DeltaCTTPair(i=i, j=j, baseline_value=baseline_ctt[(i, j)], perturbed_value=perturbed_ctt[(i, j)], delta=perturbed_ctt[(i, j)] - baseline_ctt[(i, j)])
        for i, j in sorted(baseline_ctt)
    )
    rho_pair_controls = tuple(
        RhoPairControl(
            i=i,
            j=j,
            baseline_value=baseline_rho[(i, j)][0],
            baseline_null_reason=baseline_rho[(i, j)][1],
            perturbed_value=perturbed_rho[(i, j)][0],
            perturbed_null_reason=perturbed_rho[(i, j)][1],
        )
        for i, j in sorted(baseline_rho)
    )

    return _record(response_eligibility=RESPONSE_AVAILABLE, delta_ctt_pairs=delta_ctt_pairs, rho_pair_controls=rho_pair_controls, failure_reasons=())


# ---------------------------------------------------------------------------
# Orchestration (never invoked against real data in this lot -- mirrors
# 1C-8d/1C-8e's own posture)
# ---------------------------------------------------------------------------


def run_phase_r(level1c_manifest: Level1CManifest, output_dir: Path, *, repository_commit: str) -> tuple[ResponseRecord, ...]:
    """Reads tracking.jsonl (fully verified: schema, provenance, and the
    exact canonical 40-record sequence -- never repaired or reordered)
    and produces exactly one ResponseRecord per tracking record, in the
    same order. Each of the (up to 4) distinct baseline cases and (up to
    16) distinct perturbed cases referenced is loaded/verified exactly
    once, never once per target."""
    tracking_documents = load_and_verify_tracking_records(output_dir, level1c_manifest, repository_commit=repository_commit)

    baseline_cache: dict[str, tuple[dict | None, tuple[dict, ...] | None, str | None]] = {}
    perturbed_cache: dict[str, tuple[dict | None, tuple[dict, ...] | None, str | None]] = {}

    records: list[ResponseRecord] = []
    for tracking_document in tracking_documents:
        baseline_case_id = tracking_document["baseline_case_id"]
        perturbed_case_id = tracking_document["perturbed_case_id"]

        if baseline_case_id not in baseline_cache:
            baseline_cache[baseline_case_id] = load_baseline_for_tracking(
                output_dir, baseline_case_id, level1c_manifest=level1c_manifest, repository_commit=repository_commit
            )
        if perturbed_case_id not in perturbed_cache:
            perturbed_cache[perturbed_case_id] = load_perturbed_for_tracking(
                output_dir, perturbed_case_id, level1c_manifest=level1c_manifest, repository_commit=repository_commit
            )

        records.append(
            build_response_record(
                tracking_document,
                baseline_cache[baseline_case_id],
                perturbed_cache[perturbed_case_id],
                campaign_id=level1c_manifest.campaign_id,
                repository_commit=repository_commit,
                manifest_fingerprint=level1c_manifest.fingerprint,
            )
        )

    return tuple(records)


# ---------------------------------------------------------------------------
# Persistence (response.jsonl -- same atomic-write convention as
# scripts.level1c_tracking, duplicated rather than imported: a small,
# purely generic OS-level utility with zero scientific content, and this
# is a separate package.)
# ---------------------------------------------------------------------------


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def write_response_records(output_dir: Path, records: tuple[ResponseRecord, ...]) -> None:
    """Writes `<output_dir>/response.jsonl`, one JSON object per line, in
    `records`' own order -- never a set/dict-reconstructed order. Every
    record is schema-validated before being written. No campaign-level
    artifact (no summary/index file) is ever created by this function or
    this package."""
    documents = []
    for record in records:
        document = to_json_dict(record)
        validate_response_record_document(document)
        documents.append(document)

    payload = b"".join(canonical_json_bytes(document) for document in documents)
    _atomic_write_bytes(Path(output_dir) / "response.jsonl", payload)
