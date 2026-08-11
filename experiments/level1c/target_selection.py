"""Target-selection persistence for Level1C. Lot 1C-8b.

Level1B's single-case runner (scripts/level1b_campaign/runner.py) already
computes, per case, exactly which spectral group each target resolved to
(experiments.level1.target_selection.TargetSelectionOutcome) -- but never
writes that mapping to disk (scripts/level1b_campaign/outputs.py persists
only records.jsonl/run.json's summary fields). This is D022's own root
cause for the abandoned T_max calibration hold-out
(identifiability-preregistration.md section 20.22, historical): without a
persisted target_id -> spectral_window_group_index mapping, the identity
of a historical target can never be recovered from the archive alone.

TargetSelectionRecord closes this gap for Level1C: a pure, serializable
transcription of a TargetSelectionOutcome plus the target's normative
role (Level1CTargetSpec.role, 1C-8a-fix) -- itself never inferred from
required_spectral_status. This module defines no new selection-status
taxonomy: it reuses experiments.level1.target_selection's own four
statuses verbatim.

This module performs no selection, no diagonalization: build_target_
selection_record is a pure function of an already-computed
TargetSelectionOutcome (produced elsewhere, by the existing, unmodified
select_target_group) and the manifest's own Level1CTargetSpec.
"""

from __future__ import annotations

from dataclasses import dataclass

from experiments.level1.target_selection import (
    AMBIGUOUS,
    NOT_IN_WINDOW,
    SELECTED,
    STRUCTURALLY_NOT_APPLICABLE,
    TargetSelectionOutcome,
)
from experiments.level1.manifest import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE

from .manifest import Level1CTargetSpec

SELECTION_STATUSES = (SELECTED, AMBIGUOUS, NOT_IN_WINDOW, STRUCTURALLY_NOT_APPLICABLE)
"""Re-exported, never redefined: the exact four statuses already frozen
by experiments.level1.target_selection.TargetSelectionOutcome."""


@dataclass(frozen=True, slots=True)
class TargetSelectionRecord:
    """The persisted counterpart of a TargetSelectionOutcome, plus its
    normative role. `role` is orthogonal to `selected_group_status`/
    `meets_normative_requirements` (1C-8a-fix): a CALIBRATION_ONLY
    target selected on a partial_subspace group is transcribed exactly
    as such (selected_group_status=partial_subspace,
    meets_normative_requirements=False) -- it is never promoted to a
    valid normative target by its role, and its role never suppresses
    an accurate transcription of its own non-conformity. Role only ever
    governs whether this outcome blocks campaign_status."""

    target_id: str
    role: str
    selection_status: str
    spectral_window_group_index: int | None
    selected_group_status: str | None
    meets_normative_requirements: bool | None

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id must be non-empty")
        if self.role not in ("REQUIRED", "CALIBRATION_ONLY"):
            raise ValueError(f"role must be 'REQUIRED' or 'CALIBRATION_ONLY', got {self.role!r}")
        if self.selection_status not in SELECTION_STATUSES:
            raise ValueError(f"selection_status must be one of {SELECTION_STATUSES}, got {self.selection_status!r}")
        is_selected = self.selection_status == SELECTED
        if is_selected != (self.spectral_window_group_index is not None):
            raise ValueError("spectral_window_group_index must be set if and only if selection_status == 'selected'")
        if is_selected != (self.selected_group_status is not None):
            raise ValueError("selected_group_status must be set if and only if selection_status == 'selected'")
        if is_selected != (self.meets_normative_requirements is not None):
            raise ValueError("meets_normative_requirements must be set if and only if selection_status == 'selected'")
        if self.spectral_window_group_index is not None and self.spectral_window_group_index < 0:
            raise ValueError(f"spectral_window_group_index must be >= 0, got {self.spectral_window_group_index}")
        if self.selected_group_status is not None and self.selected_group_status not in (
            COMPLETE_MULTIPLET,
            PARTIAL_SUBSPACE,
        ):
            raise ValueError(
                f"selected_group_status must be None, {COMPLETE_MULTIPLET!r}, or {PARTIAL_SUBSPACE!r}, "
                f"got {self.selected_group_status!r}"
            )


def build_target_selection_record(target_spec: Level1CTargetSpec, outcome: TargetSelectionOutcome) -> TargetSelectionRecord:
    """Transcribe an already-computed TargetSelectionOutcome (from the
    existing, unmodified experiments.level1.target_selection.
    select_target_group) into a persistable TargetSelectionRecord,
    attaching target_spec.role verbatim. Cross-checks that `outcome`
    actually belongs to `target_spec.target` before transcribing --
    never silently pairs an outcome with an unrelated target."""
    if outcome.target_id != target_spec.target.target_id:
        raise ValueError(
            f"outcome.target_id ({outcome.target_id!r}) does not match "
            f"target_spec.target.target_id ({target_spec.target.target_id!r})"
        )
    return TargetSelectionRecord(
        target_id=outcome.target_id,
        role=target_spec.role,
        selection_status=outcome.status,
        spectral_window_group_index=outcome.group_index,
        selected_group_status=outcome.selected_group_status,
        meets_normative_requirements=outcome.meets_normative_requirements,
    )
