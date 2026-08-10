"""Level1C case run artifact: structure, validation, canonical
serialization. Lot 1C-8b-fix.

TARGET_SELECTION_PERSISTENCE = CASE_RUN_ARTIFACT_ONLY: a
TargetSelectionRecord (experiments.level1c.target_selection) is a
case-level outcome, never a ResultRecord -- an ambiguous/not_in_window/
structurally_not_applicable outcome has no selected spectral group at
all, so it can never be attached to identity.spectral_group (schemas/
level1c/result-record-v1.schema.json, which is reserved for documents
genuinely tied to a physical group). Level1CCaseRunArtifact is the
case-level counterpart, mirroring scripts/level1b_campaign/outputs.py's
run.json convention (case_id/campaign_id/manifest_fingerprint/
repository_commit/run_status/record_count/records_sha256, reused
verbatim as a naming/status convention) extended with `target_selections`.

This module validates and serializes structure only: it never runs a
scientific computation, never reads a real artifact, and never
diagonalizes anything.

required_targets_are_satisfied / Level1CCaseRunArtifact.
required_targets_satisfied (1C-8c) resolve the "required-target case
gate": whether a case's REQUIRED targets were all found and conformant
is a fact already fully derivable from the persisted target_selections
(role + selection_status + meets_normative_requirements, all already
present) -- so it is exposed as a pure, tested query, never a new
run_status value and never a new field on the schema/dataclass.
run_status keeps meaning exactly what it means in Level1B (scripts/
level1b_campaign/outputs.py): whether the computation executed without
technical error (no exception, no resource guardrail exceeded) -- a
case can be run_status=success while still failing this gate (e.g. a
REQUIRED target selected on a partial_subspace group, or not found at
all), exactly as Level1B never failed a run merely because a target
was not found. CALIBRATION_ONLY targets never affect this gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .manifest import Level1CTargetSpec
from .target_selection import TargetSelectionRecord

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "case-run-v1.schema.json"

SUCCESS = "success"
FAILED = "failed"
RESOURCE_GUARDRAIL_EXCEEDED = "resource_guardrail_exceeded"
RUN_STATUSES = (SUCCESS, FAILED, RESOURCE_GUARDRAIL_EXCEEDED)
"""Reused verbatim from scripts/level1b_campaign/outputs.py's own
run_status convention -- no new scientific status invented."""

_SHA256_HEX_LENGTH = 64
_SHA256_HEX_DIGITS = frozenset("0123456789abcdef")
_GIT_SHA_LENGTH = 40
_GIT_SHA_DIGITS = frozenset("0123456789abcdef")


def _is_sha256_hex(value: str) -> bool:
    return len(value) == _SHA256_HEX_LENGTH and set(value) <= _SHA256_HEX_DIGITS


def _is_git_sha_hex(value: str) -> bool:
    return len(value) == _GIT_SHA_LENGTH and set(value) <= _GIT_SHA_DIGITS


@dataclass(frozen=True, slots=True)
class Level1CCaseRunArtifact:
    """One Level1C case's run outcome: identity/provenance fields
    mirroring Level1B's run.json, plus target_selections (the case-level
    target-selection outcomes, in manifest order -- never a set/dict
    reconstruction). For a `success` run, target_selections must be
    non-empty and records_sha256/record_count must be present; for
    `failed`/`resource_guardrail_exceeded`, no target selection was ever
    attempted, so target_selections is empty and records_sha256/
    record_count are null/0 -- never a fabricated placeholder outcome."""

    schema_version: str
    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str
    case_id: str
    geometry: str
    spin: int
    hamiltonian_case_id: str
    sector_id: str
    spectral_window: int
    run_status: str
    target_selections: tuple[TargetSelectionRecord, ...]
    records_sha256: str | None
    record_count: int

    def __post_init__(self) -> None:
        if self.schema_version != "level1c-case-run-v1":
            raise ValueError(f"schema_version must be 'level1c-case-run-v1', got {self.schema_version!r}")
        if self.campaign_id != "level1c-j0-response-v1":
            raise ValueError(f"campaign_id must be 'level1c-j0-response-v1', got {self.campaign_id!r}")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not isinstance(self.repository_commit, str) or not _is_git_sha_hex(self.repository_commit):
            raise ValueError(f"repository_commit must be a 40-hex-character git SHA, got {self.repository_commit!r}")
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if self.geometry not in ("triangle", "ring5"):
            raise ValueError(f"geometry must be 'triangle' or 'ring5', got {self.geometry!r}")
        if self.spin not in (2, 3):
            raise ValueError(f"spin must be 2 or 3, got {self.spin!r}")
        if not self.hamiltonian_case_id.startswith("j0-"):
            raise ValueError(f"hamiltonian_case_id must start with 'j0-', got {self.hamiltonian_case_id!r}")
        if self.sector_id != "default":
            raise ValueError(f"sector_id must be 'default', got {self.sector_id!r}")
        if isinstance(self.spectral_window, bool) or not isinstance(self.spectral_window, int) or self.spectral_window < 1:
            raise ValueError(f"spectral_window must be a positive int, got {self.spectral_window!r}")
        if self.run_status not in RUN_STATUSES:
            raise ValueError(f"run_status must be one of {RUN_STATUSES}, got {self.run_status!r}")

        target_ids = [record.target_id for record in self.target_selections]
        if len(target_ids) != len(set(target_ids)):
            duplicates = sorted({target_id for target_id in target_ids if target_ids.count(target_id) > 1})
            raise ValueError(f"target_selections has duplicate target_id(s): {duplicates}")

        if self.run_status == SUCCESS:
            if not isinstance(self.records_sha256, str) or not _is_sha256_hex(self.records_sha256):
                raise ValueError(
                    f"records_sha256 must be a 64-hex-character SHA-256 digest for a successful run, "
                    f"got {self.records_sha256!r}"
                )
            if isinstance(self.record_count, bool) or not isinstance(self.record_count, int) or self.record_count <= 0:
                raise ValueError(f"record_count must be a positive int for a successful run, got {self.record_count!r}")
            if not self.target_selections:
                raise ValueError("target_selections must be non-empty for a successful run")
        else:
            if self.records_sha256 is not None:
                raise ValueError(f"records_sha256 must be None for run_status {self.run_status!r}, got {self.records_sha256!r}")
            if self.record_count != 0:
                raise ValueError(f"record_count must be 0 for run_status {self.run_status!r}, got {self.record_count!r}")
            if self.target_selections:
                raise ValueError(
                    f"target_selections must be empty for run_status {self.run_status!r} -- no selection is ever "
                    "attempted for a case that did not succeed, never a fabricated placeholder outcome"
                )

    @property
    def required_targets_satisfied(self) -> bool:
        """The required-target case gate (1C-8c): False outright for any
        non-success run_status (no selection was ever attempted);
        otherwise delegates to required_targets_are_satisfied. Never a
        new run_status value -- see the module docstring."""
        if self.run_status != SUCCESS:
            return False
        return required_targets_are_satisfied(self.target_selections)


def required_targets_are_satisfied(target_selections: tuple[TargetSelectionRecord, ...]) -> bool:
    """Whether every REQUIRED record actually PRESENT in
    `target_selections` was found (selection_status == 'selected') and
    satisfies its own normative requirement (meets_normative_
    requirements is True). CALIBRATION_ONLY targets never affect this
    result, whatever their outcome (T_max may be absent, ambiguous, or
    selected-but-non-conformant without ever changing this gate).

    This function does not itself check that `target_selections`
    actually covers every target the manifest declares for the case's
    geometry -- that completeness/order guarantee is
    validate_target_selections_match_manifest's own job, always
    enforced before a Level1CCaseRunArtifact is ever persisted
    (scripts.level1c_campaign.outputs.write_case_success); a
    REQUIRED target silently absent from an otherwise-untouched list
    would not be caught here. Assumes an already-validated
    target_selections sequence from a successful run -- an empty
    sequence (as persisted for a failed/resource_guardrail_exceeded run)
    returns True vacuously, which is why Level1CCaseRunArtifact.
    required_targets_satisfied always checks run_status first; call this
    function directly only when run_status == 'success' is already
    known."""
    required = [record for record in target_selections if record.role == "REQUIRED"]
    return all(record.selection_status == "selected" and record.meets_normative_requirements is True for record in required)


def validate_target_selections_match_manifest(
    target_selections: tuple[TargetSelectionRecord, ...], target_specs: tuple[Level1CTargetSpec, ...]
) -> None:
    """Cross-checks target_selections against the manifest's own
    Level1CTargetSpec list for this case's geometry: same length, same
    target_id at each position, in the manifest's own order -- never a
    set/dict-reconstructed order. Raises ValueError on any missing,
    extra, or misordered target."""
    expected_ids = [spec.target.target_id for spec in target_specs]
    actual_ids = [record.target_id for record in target_selections]
    if actual_ids == expected_ids:
        return

    missing = [target_id for target_id in expected_ids if target_id not in actual_ids]
    extra = [target_id for target_id in actual_ids if target_id not in expected_ids]
    if missing:
        raise ValueError(f"target_selections is missing target(s) {missing} required by the manifest")
    if extra:
        raise ValueError(f"target_selections has target(s) {extra} not declared by the manifest for this geometry")
    raise ValueError(
        f"target_selections order {actual_ids} does not match the manifest's own target order {expected_ids} "
        "-- target order is contractual, never a set/dict-reconstructed order"
    )


def _target_selection_payload(record: TargetSelectionRecord) -> dict:
    return {
        "target_id": record.target_id,
        "role": record.role,
        "selection_status": record.selection_status,
        "spectral_window_group_index": record.spectral_window_group_index,
        "selected_group_status": record.selected_group_status,
        "meets_normative_requirements": record.meets_normative_requirements,
    }


def to_json_dict(artifact: Level1CCaseRunArtifact) -> dict:
    """The canonical JSON-safe dict representation of a
    Level1CCaseRunArtifact -- pure transcription, no computation."""
    return {
        "schema_version": artifact.schema_version,
        "campaign_id": artifact.campaign_id,
        "manifest_fingerprint": artifact.manifest_fingerprint,
        "repository_commit": artifact.repository_commit,
        "case_id": artifact.case_id,
        "geometry": artifact.geometry,
        "spin": artifact.spin,
        "hamiltonian_case_id": artifact.hamiltonian_case_id,
        "sector_id": artifact.sector_id,
        "spectral_window": artifact.spectral_window,
        "run_status": artifact.run_status,
        "target_selections": [_target_selection_payload(record) for record in artifact.target_selections],
        "records_sha256": artifact.records_sha256,
        "record_count": artifact.record_count,
    }


def canonical_json_bytes(payload: dict) -> bytes:
    """UTF-8, sort_keys, ensure_ascii, allow_nan=False, single trailing
    newline -- the same convention as scripts/level1b_campaign/
    outputs.py's own run.json writer."""
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


def validate_case_run_document(document: dict) -> None:
    """Raises ValueError (never a bare jsonschema exception) listing
    every violation, not just the first."""
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against the Level1C case-run schema: {messages}")
