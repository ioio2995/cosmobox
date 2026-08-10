"""Inter-J0 tracking: CLASS_POOL construction, TrackingRecord, artifact
schema, and orchestration. Lot 1C-8e.

See the package docstring for the full scope and the two design
decisions this lot resolved without a DESIGN_BLOCKER:

PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE = IRRELEVANT_TO_STRUCTURAL_TRACKING:
a perturbed case's normative_case_valid is never consulted here -- only
run_status=='success' gates whether its records can be used at all.

REFLECTION_RESTRICTION_VALID_PERSISTENCE = PROVABLE_EQUIVALENT_TO_NUMERIC_KIND:
cosmobox.level1.matching.compute_restricted_symmetry_label returns
kind==NUMERIC if and only if the commutator-defect (when applicable),
stability-defect, and unitarity-defect are all within tolerance -- the
last two being exactly section 18.13's frozen definition of
reflection_restriction_valid ("stabilite + unitarite"). No separate
reflection_restriction_valid field is persisted or checked anywhere in
this module: `reflection_label.kind == NUMERIC` is used directly, and is
already a proven witness of that property.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator

from cosmobox.level1.matching import NUMERIC, SYMMETRY_TOLERANCE, SymmetryLabel, symmetry_labels_match
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from experiments.level1c.manifest import GEOMETRIES, Level1CManifest, SPIN_VALUES
from experiments.level1c.planning import build_level1c_campaign_plan, build_tracking_edges
from scripts.level1c_baseline_gate.gate import (
    BaselineGateInputError,
    GroupStructuralData,
    REQUIRED_TARGET_IDS,
    level1c_group_structural_data,
    load_level1c_baseline_case,
)
from scripts.level1c_campaign.outputs import (
    Level1CArtifactIntegrityError,
    load_and_verify_case_records,
    load_and_verify_case_run_document,
)

SCHEMA_VERSION = "level1c-tracking-record-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "tracking-record-v1.schema.json"

TRACKED_ONE_TO_ONE = "TRACKED_ONE_TO_ONE"
AMBIGUOUS = "AMBIGUOUS"
NOT_AVAILABLE = "NOT_AVAILABLE"
TRACKED_SPLIT_BRANCH = "TRACKED_SPLIT_BRANCH"
DISCONTINUOUS = "DISCONTINUOUS"
"""TRACKED_SPLIT_BRANCH/DISCONTINUOUS are reserved by the frozen v1
taxonomy (section 20.12/1C-8e section 7) -- never emitted by this
module. Listed here only for completeness/documentation, never included
in EMITTABLE_TRACKING_STATUSES."""

EMITTABLE_TRACKING_STATUSES = (TRACKED_ONE_TO_ONE, AMBIGUOUS, NOT_AVAILABLE)

_GIT_SHA_LENGTH = 40
_GIT_SHA_DIGITS = frozenset("0123456789abcdef")


def _is_git_sha_hex(value: str) -> bool:
    return isinstance(value, str) and len(value) == _GIT_SHA_LENGTH and set(value) <= _GIT_SHA_DIGITS


# ---------------------------------------------------------------------------
# CLASS_POOL construction (sections 4-11 of the mandate)
# ---------------------------------------------------------------------------


def extract_complete_groups(records: tuple[Mapping, ...]) -> tuple[GroupStructuralData, ...]:
    """Every COMPLETE_MULTIPLET group persisted in `records`, as
    GroupStructuralData, in ascending spectral_window_group_index order
    (a deterministic output order only -- group_index itself is never a
    matching discriminant, section 11). partial_subspace groups are
    never included (section 4: CLASS_POOL is built exclusively from
    complete groups)."""
    seen_indices: set[int] = set()
    for document in records:
        spectral_group = document["identity"]["spectral_group"]
        if spectral_group["status"] == COMPLETE_MULTIPLET:
            seen_indices.add(spectral_group["spectral_window_group_index"])
    return tuple(level1c_group_structural_data(records, index) for index in sorted(seen_indices))


@dataclass(frozen=True, slots=True)
class ClassPoolResult:
    """`pool`: perturbed complete groups PROVEN to share the baseline
    branch's identity. `unresolved_candidates`: perturbed complete
    groups whose own twice_T or reflection character is unresolved and
    which therefore can never be safely EXCLUDED (section 8) -- a group
    that might match is never conflated with one that provably does
    not. Both are disjoint by construction: a group only ever ends up in
    one of the two, never both."""

    pool: tuple[GroupStructuralData, ...]
    unresolved_candidates: tuple[GroupStructuralData, ...]


def build_class_pool(baseline: GroupStructuralData, perturbed_groups: tuple[GroupStructuralData, ...]) -> ClassPoolResult:
    """CLASS_POOL construction (section 20.12 of the preregistration,
    section 5/8 of the 1C-8e mandate). Assumes baseline's own identity
    (twice_T, reflection) is already resolved -- callers must check that
    first (section 1C-8e section 14/1C-8e "baseline identity
    unresolved" case is handled by the caller, never here).

    Multiplicity and translation are never identity components here
    (sections 6/10); representative_energy/spectral rank/
    spectral_window_group_index are never discriminants (section 11)."""
    pool: list[GroupStructuralData] = []
    unresolved: list[GroupStructuralData] = []
    for candidate in perturbed_groups:
        if candidate.twice_T is None:
            unresolved.append(candidate)
            continue
        if candidate.twice_T != baseline.twice_T:
            continue
        if candidate.reflection_label.kind != NUMERIC:
            unresolved.append(candidate)
            continue
        if not symmetry_labels_match(candidate.reflection_label, baseline.reflection_label, tolerance=SYMMETRY_TOLERANCE):
            continue
        pool.append(candidate)
    return ClassPoolResult(pool=tuple(pool), unresolved_candidates=tuple(unresolved))


# ---------------------------------------------------------------------------
# TrackingRecord: structure, validation, canonical serialization
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrackingRecord:
    """One tracking outcome for one (target_id, tracking edge) pair.

    Null-ability contract:
      baseline_group_index/baseline_multiplicity/baseline_reflection_label
        are None together, if and only if the baseline branch itself
        could not be loaded/located at all (BASELINE_UNAVAILABLE).
      baseline_twice_T is None whenever baseline_group_index is None, but
        may ALSO be None even when the baseline group IS known (its own
        twice_T computation failed) -- a distinct, expected case, never
        conflated with BASELINE_UNAVAILABLE.
      candidate_group_index/candidate_multiplicity/candidate_twice_T/
        candidate_reflection_label are populated if and only if
        status == TRACKED_ONE_TO_ONE (a unique, identified branch).
      class_pool_size is None whenever CLASS_POOL was never well-defined
        (baseline identity unresolved/unavailable, or the perturbed case
        itself unusable) -- an int (>= 0) otherwise, counting only PROVEN
        pool members, never unresolved candidates.
      failure_reasons is empty if and only if status == TRACKED_ONE_TO_ONE.
    """

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
    baseline_group_index: int | None
    baseline_multiplicity: int | None
    baseline_twice_T: int | None
    baseline_reflection_label: SymmetryLabel | None
    status: str
    candidate_group_index: int | None
    candidate_multiplicity: int | None
    candidate_twice_T: int | None
    candidate_reflection_label: SymmetryLabel | None
    class_pool_size: int | None
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

        if self.status not in EMITTABLE_TRACKING_STATUSES:
            raise ValueError(f"status must be one of {EMITTABLE_TRACKING_STATUSES}, got {self.status!r}")

        baseline_known = self.baseline_group_index is not None
        if baseline_known != (self.baseline_multiplicity is not None):
            raise ValueError("baseline_group_index and baseline_multiplicity must be None together")
        if baseline_known != (self.baseline_reflection_label is not None):
            raise ValueError("baseline_group_index and baseline_reflection_label must be None together")
        if not baseline_known and self.baseline_twice_T is not None:
            raise ValueError("baseline_twice_T must be None when baseline_group_index is None")
        if not baseline_known and self.class_pool_size is not None:
            raise ValueError("class_pool_size must be None when the baseline branch is unavailable")

        if self.class_pool_size is not None and self.class_pool_size < 0:
            raise ValueError(f"class_pool_size must be >= 0, got {self.class_pool_size!r}")

        if self.status == TRACKED_ONE_TO_ONE:
            if self.failure_reasons:
                raise ValueError("failure_reasons must be empty when status == TRACKED_ONE_TO_ONE")
            if self.class_pool_size != 1:
                raise ValueError(f"class_pool_size must be 1 when status == TRACKED_ONE_TO_ONE, got {self.class_pool_size!r}")
            if (
                self.candidate_group_index is None
                or self.candidate_multiplicity is None
                or self.candidate_twice_T is None
                or self.candidate_reflection_label is None
            ):
                raise ValueError("candidate_* fields must all be populated when status == TRACKED_ONE_TO_ONE")
        else:
            if not self.failure_reasons:
                raise ValueError(f"failure_reasons must be non-empty when status == {self.status!r}")
            if (
                self.candidate_group_index is not None
                or self.candidate_multiplicity is not None
                or self.candidate_twice_T is not None
                or self.candidate_reflection_label is not None
            ):
                raise ValueError(f"candidate_* fields must all be None when status == {self.status!r}")


def _symmetry_label_payload(label: SymmetryLabel | None) -> dict | None:
    if label is None:
        return None
    if label.kind == NUMERIC:
        return {"kind": "numeric", "value": {"real": label.value.real, "imag": label.value.imag}}
    return {"kind": label.kind, "value": None}


def to_json_dict(record: TrackingRecord) -> dict:
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
        "baseline_group_index": record.baseline_group_index,
        "baseline_multiplicity": record.baseline_multiplicity,
        "baseline_twice_T": record.baseline_twice_T,
        "baseline_reflection_label": _symmetry_label_payload(record.baseline_reflection_label),
        "status": record.status,
        "candidate_group_index": record.candidate_group_index,
        "candidate_multiplicity": record.candidate_multiplicity,
        "candidate_twice_T": record.candidate_twice_T,
        "candidate_reflection_label": _symmetry_label_payload(record.candidate_reflection_label),
        "class_pool_size": record.class_pool_size,
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


def validate_tracking_record_document(document: dict) -> None:
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against the Level1C tracking-record schema: {messages}")


# ---------------------------------------------------------------------------
# Loading (read-only: never diagonalizes, never calls run_level1c_case)
# ---------------------------------------------------------------------------


def _provenance_mismatch_reasons(run_document: Mapping, level1c_manifest: Level1CManifest, repository_commit: str) -> tuple[str, ...]:
    reasons = []
    if run_document["campaign_id"] != level1c_manifest.campaign_id:
        reasons.append("CAMPAIGN_ID_MISMATCH")
    if run_document["manifest_fingerprint"] != level1c_manifest.fingerprint:
        reasons.append("MANIFEST_FINGERPRINT_MISMATCH")
    if run_document["repository_commit"] != repository_commit:
        reasons.append("REPOSITORY_COMMIT_MISMATCH")
    return tuple(reasons)


def load_baseline_for_tracking(
    output_dir: Path, baseline_case_id: str, *, level1c_manifest: Level1CManifest, repository_commit: str
) -> tuple[dict | None, tuple[dict, ...] | None, str | None]:
    """Returns (run_document, records, failure_reason). Never raises:
    every failure mode of baseline loading becomes a single descriptive
    string (run_document/records are then both None), so a single bad
    baseline never aborts the rest of the orchestration (mirrors
    scripts.level1c_baseline_gate.gate's own discipline). Reuses
    load_level1c_baseline_case verbatim (run_status=success AND
    normative_case_valid=true, the exact baseline validity gate already
    ratified in 1C-8d/1C-8d-fix), adding only the campaign_id/manifest_
    fingerprint/repository_commit provenance cross-check against the
    expected values (mirroring scripts.level1c_baseline_gate.gate.
    compare_baseline_case's own external provenance check, since
    load_level1c_baseline_case itself only checks internal self-
    consistency, never the caller's expected identity)."""
    try:
        run_document, records = load_level1c_baseline_case(output_dir, baseline_case_id, level1c_manifest=level1c_manifest)
    except BaselineGateInputError as exc:
        return None, None, str(exc)

    provenance_reasons = _provenance_mismatch_reasons(run_document, level1c_manifest, repository_commit)
    if provenance_reasons:
        return None, None, "; ".join(provenance_reasons)

    return run_document, records, None


def load_perturbed_for_tracking(
    output_dir: Path, perturbed_case_id: str, *, level1c_manifest: Level1CManifest, repository_commit: str
) -> tuple[dict | None, tuple[dict, ...] | None, str | None]:
    """Returns (run_document, records, failure_reason). Only run_status
    == 'success' is required of the perturbed side
    (PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE=
    IRRELEVANT_TO_STRUCTURAL_TRACKING, see the package docstring):
    normative_case_valid is never consulted here."""
    try:
        run_document = load_and_verify_case_run_document(output_dir, perturbed_case_id)
    except Level1CArtifactIntegrityError as exc:
        return None, None, str(exc)

    if run_document["run_status"] != "success":
        return None, None, f"run_status is {run_document['run_status']!r}, not 'success'"

    try:
        records = load_and_verify_case_records(output_dir, perturbed_case_id, run_document, level1c_manifest=level1c_manifest)
    except Level1CArtifactIntegrityError as exc:
        return None, None, str(exc)

    provenance_reasons = _provenance_mismatch_reasons(run_document, level1c_manifest, repository_commit)
    if provenance_reasons:
        return None, None, "; ".join(provenance_reasons)

    return run_document, records, None


def _find_target_group_index(run_document: Mapping, target_id: str) -> int | None:
    """None if the target cannot be resolved to a selected group -- for
    a baseline that already passed load_level1c_baseline_case's own
    normative_case_valid=true gate this should never happen for a
    REQUIRED target, but this function stays defensive rather than
    assuming it."""
    for entry in run_document["target_selections"]:
        if entry["target_id"] == target_id and entry["selection_status"] == "selected":
            return entry["spectral_window_group_index"]
    return None


# ---------------------------------------------------------------------------
# Per-(target, edge) tracking (sections 5-14 of the mandate)
# ---------------------------------------------------------------------------


def track_target_edge(
    *,
    target_id: str,
    geometry: str,
    spin: int,
    baseline_case_id: str,
    perturbed_case_id: str,
    baseline_hamiltonian_case_id: str,
    perturbed_hamiltonian_case_id: str,
    baseline_run_document: Mapping | None,
    baseline_records: tuple[Mapping, ...] | None,
    baseline_failure_reason: str | None,
    perturbed_groups: tuple[GroupStructuralData, ...] | None,
    perturbed_failure_reason: str | None,
    campaign_id: str,
    repository_commit: str,
    manifest_fingerprint: str,
) -> TrackingRecord:
    """The core per-(target, edge) decision (sections 5-14). Never
    raises: every unresolved/unavailable state is captured as an
    AMBIGUOUS TrackingRecord with an explicit failure_reason, per the
    frozen principle "un calcul non resolu ne prouve ni presence ni
    absence" (section 20.12) -- NOT_AVAILABLE is reserved exclusively
    for the case where the baseline identity is fully resolved AND every
    perturbed complete group's own identity is resolved AND CLASS_POOL
    is then cleanly empty (section 9)."""

    def _record(*, status: str, class_pool_size: int | None, baseline_data: GroupStructuralData | None, candidate: GroupStructuralData | None, failure_reasons: tuple[str, ...]) -> TrackingRecord:
        return TrackingRecord(
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
            baseline_group_index=None if baseline_data is None else baseline_data.spectral_window_group_index,
            baseline_multiplicity=None if baseline_data is None else baseline_data.multiplicity,
            baseline_twice_T=None if baseline_data is None else baseline_data.twice_T,
            baseline_reflection_label=None if baseline_data is None else baseline_data.reflection_label,
            status=status,
            candidate_group_index=None if candidate is None else candidate.spectral_window_group_index,
            candidate_multiplicity=None if candidate is None else candidate.multiplicity,
            candidate_twice_T=None if candidate is None else candidate.twice_T,
            candidate_reflection_label=None if candidate is None else candidate.reflection_label,
            class_pool_size=class_pool_size,
            failure_reasons=failure_reasons,
        )

    if baseline_failure_reason is not None:
        return _record(
            status=AMBIGUOUS, class_pool_size=None, baseline_data=None, candidate=None,
            failure_reasons=(f"BASELINE_UNAVAILABLE: {baseline_failure_reason}",),
        )

    baseline_group_index = _find_target_group_index(baseline_run_document, target_id)
    if baseline_group_index is None:
        return _record(
            status=AMBIGUOUS, class_pool_size=None, baseline_data=None, candidate=None,
            failure_reasons=(f"BASELINE_TARGET_LOOKUP_FAILED: target {target_id!r} not selected in baseline",),
        )
    baseline_data = level1c_group_structural_data(baseline_records, baseline_group_index)

    baseline_unresolved_reasons: list[str] = []
    if baseline_data.twice_T is None:
        baseline_unresolved_reasons.append("BASELINE_TWICE_T_UNRESOLVED")
    if baseline_data.reflection_label.kind != NUMERIC:
        baseline_unresolved_reasons.append(f"BASELINE_REFLECTION_NOT_NUMERIC: kind={baseline_data.reflection_label.kind!r}")
    if baseline_unresolved_reasons:
        return _record(
            status=AMBIGUOUS, class_pool_size=None, baseline_data=baseline_data, candidate=None,
            failure_reasons=tuple(baseline_unresolved_reasons),
        )

    if perturbed_failure_reason is not None:
        return _record(
            status=AMBIGUOUS, class_pool_size=None, baseline_data=baseline_data, candidate=None,
            failure_reasons=(f"PERTURBED_UNAVAILABLE: {perturbed_failure_reason}",),
        )

    pool_result = build_class_pool(baseline_data, perturbed_groups)

    if pool_result.unresolved_candidates:
        reasons = tuple(
            f"PERTURBED_CANDIDATE_UNRESOLVED: group_index={candidate.spectral_window_group_index}"
            for candidate in pool_result.unresolved_candidates
        )
        return _record(
            status=AMBIGUOUS, class_pool_size=len(pool_result.pool), baseline_data=baseline_data, candidate=None,
            failure_reasons=reasons,
        )

    if len(pool_result.pool) == 0:
        return _record(status=NOT_AVAILABLE, class_pool_size=0, baseline_data=baseline_data, candidate=None, failure_reasons=("CLASS_POOL_EMPTY",))

    if len(pool_result.pool) > 1:
        return _record(
            status=AMBIGUOUS, class_pool_size=len(pool_result.pool), baseline_data=baseline_data, candidate=None,
            failure_reasons=(f"CLASS_POOL_NOT_UNIQUE: size={len(pool_result.pool)}",),
        )

    candidate = pool_result.pool[0]
    if candidate.multiplicity != baseline_data.multiplicity:
        return _record(
            status=AMBIGUOUS, class_pool_size=1, baseline_data=baseline_data, candidate=None,
            failure_reasons=(f"MULTIPLICITY_MISMATCH: baseline={baseline_data.multiplicity} candidate={candidate.multiplicity}",),
        )

    return _record(status=TRACKED_ONE_TO_ONE, class_pool_size=1, baseline_data=baseline_data, candidate=candidate, failure_reasons=())


# ---------------------------------------------------------------------------
# Orchestration (never invoked against real data in this lot -- 1C-8e
# implements the tool only, mirroring 1C-8d's own posture)
# ---------------------------------------------------------------------------


def run_inter_j0_tracking(level1c_manifest: Level1CManifest, output_dir: Path, *, repository_commit: str) -> tuple[TrackingRecord, ...]:
    """Produces exactly one TrackingRecord per (REQUIRED target, tracking
    edge) pair: 16 edges (build_tracking_edges) x {2 triangle targets, 3
    ring5 targets} = 40 records for the frozen grid, in canonical edge
    order (edges' own order) then manifest target order within each
    edge. Each of the 4 distinct baseline cases and the (up to) 16
    distinct perturbed cases is loaded/verified exactly once, never once
    per target."""
    cases = build_level1c_campaign_plan(level1c_manifest)
    cases_by_id = {case.case_id: case for case in cases}
    edges = build_tracking_edges(cases)

    baseline_cache: dict[str, tuple[dict | None, tuple[dict, ...] | None, str | None]] = {}
    perturbed_cache: dict[str, tuple[dict | None, tuple[dict, ...] | None, str | None]] = {}
    perturbed_groups_cache: dict[str, tuple[GroupStructuralData, ...] | None] = {}

    records: list[TrackingRecord] = []
    for perturbed_case_id, baseline_case_id in edges:
        baseline_case = cases_by_id[baseline_case_id]
        perturbed_case = cases_by_id[perturbed_case_id]
        geometry = baseline_case.geometry
        spin = baseline_case.spin

        if baseline_case_id not in baseline_cache:
            baseline_cache[baseline_case_id] = load_baseline_for_tracking(
                output_dir, baseline_case_id, level1c_manifest=level1c_manifest, repository_commit=repository_commit
            )
        baseline_run_document, baseline_records, baseline_failure_reason = baseline_cache[baseline_case_id]

        if perturbed_case_id not in perturbed_cache:
            perturbed_cache[perturbed_case_id] = load_perturbed_for_tracking(
                output_dir, perturbed_case_id, level1c_manifest=level1c_manifest, repository_commit=repository_commit
            )
            _, perturbed_records, _ = perturbed_cache[perturbed_case_id]
            perturbed_groups_cache[perturbed_case_id] = None if perturbed_records is None else extract_complete_groups(perturbed_records)
        _, _, perturbed_failure_reason = perturbed_cache[perturbed_case_id]
        perturbed_groups = perturbed_groups_cache[perturbed_case_id]

        for target_id in REQUIRED_TARGET_IDS[geometry]:
            records.append(
                track_target_edge(
                    target_id=target_id,
                    geometry=geometry,
                    spin=spin,
                    baseline_case_id=baseline_case_id,
                    perturbed_case_id=perturbed_case_id,
                    baseline_hamiltonian_case_id=baseline_case.hamiltonian_case_id,
                    perturbed_hamiltonian_case_id=perturbed_case.hamiltonian_case_id,
                    baseline_run_document=baseline_run_document,
                    baseline_records=baseline_records,
                    baseline_failure_reason=baseline_failure_reason,
                    perturbed_groups=perturbed_groups,
                    perturbed_failure_reason=perturbed_failure_reason,
                    campaign_id=level1c_manifest.campaign_id,
                    repository_commit=repository_commit,
                    manifest_fingerprint=level1c_manifest.fingerprint,
                )
            )

    return tuple(records)


# ---------------------------------------------------------------------------
# Persistence (tracking.jsonl -- same atomic-write convention as
# scripts.level1c_campaign.outputs, duplicated rather than imported: a
# small, purely generic OS-level utility with zero scientific content,
# and this is a separate package, mirroring scripts.level1c_campaign.
# outputs's own stated rationale for not importing scripts.level1b_
# campaign.outputs's version).
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


def write_tracking_records(output_dir: Path, records: tuple[TrackingRecord, ...]) -> None:
    """Writes `<output_dir>/tracking.jsonl`, one JSON object per line, in
    `records`' own order -- never a set/dict-reconstructed order. Every
    record is schema-validated before being written."""
    documents = []
    for record in records:
        document = to_json_dict(record)
        validate_tracking_record_document(document)
        documents.append(document)

    payload = b"".join(canonical_json_bytes(document) for document in documents)
    _atomic_write_bytes(Path(output_dir) / "tracking.jsonl", payload)
