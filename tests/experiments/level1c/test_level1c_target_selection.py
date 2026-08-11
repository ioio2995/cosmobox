from __future__ import annotations

import pytest

from experiments.level1.manifest import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, TargetGroupSpec
from experiments.level1.target_selection import (
    AMBIGUOUS,
    NOT_IN_WINDOW,
    SELECTED,
    STRUCTURALLY_NOT_APPLICABLE,
    TargetSelectionOutcome,
)
from experiments.level1c.manifest import CALIBRATION_ONLY, REQUIRED, Level1CTargetSpec
from experiments.level1c.target_selection import TargetSelectionRecord, build_target_selection_record


def _fundamental_spec(role: str) -> Level1CTargetSpec:
    target = TargetGroupSpec(
        target_id="fundamental",
        selection_kind="fundamental",
        target_twice_T=None,
        selection_within_label=None,
        required_spectral_status="complete_multiplet",
        requires_inter_s_exact_match=False,
    )
    return Level1CTargetSpec(target=target, role=role)


def _t_max_spec() -> Level1CTargetSpec:
    target = TargetGroupSpec(
        target_id="T_max",
        selection_kind="flavor_label",
        target_twice_T=3,
        selection_within_label="lowest_representative_energy",
        required_spectral_status="complete_multiplet",
        requires_inter_s_exact_match=False,
    )
    return Level1CTargetSpec(target=target, role=CALIBRATION_ONLY)


# ---------------------------------------------------------------------------
# build_target_selection_record: transcription correctness
# ---------------------------------------------------------------------------


def test_selected_outcome_is_transcribed_verbatim() -> None:
    spec = _fundamental_spec(REQUIRED)
    outcome = TargetSelectionOutcome(
        target_id="fundamental",
        status=SELECTED,
        group_index=0,
        twice_T=None,
        selected_group_status=COMPLETE_MULTIPLET,
        meets_normative_requirements=True,
    )
    record = build_target_selection_record(spec, outcome)
    assert record == TargetSelectionRecord(
        target_id="fundamental",
        role=REQUIRED,
        selection_status=SELECTED,
        spectral_window_group_index=0,
        selected_group_status=COMPLETE_MULTIPLET,
        meets_normative_requirements=True,
    )


def test_role_is_never_inferred_from_required_spectral_status() -> None:
    """T_max keeps required_spectral_status=complete_multiplet (like any
    other flavor_label target) while role=CALIBRATION_ONLY -- the two
    fields are independent (1C-8a-fix)."""
    spec = _t_max_spec()
    assert spec.target.required_spectral_status == "complete_multiplet"
    assert spec.role == CALIBRATION_ONLY


def test_t_max_selected_on_partial_subspace_is_never_promoted_to_valid() -> None:
    spec = _t_max_spec()
    outcome = TargetSelectionOutcome(
        target_id="T_max",
        status=SELECTED,
        group_index=7,
        twice_T=3,
        selected_group_status=PARTIAL_SUBSPACE,
        meets_normative_requirements=False,
    )
    record = build_target_selection_record(spec, outcome)
    assert record.role == CALIBRATION_ONLY
    assert record.selected_group_status == PARTIAL_SUBSPACE
    assert record.meets_normative_requirements is False


@pytest.mark.parametrize("status", [AMBIGUOUS, NOT_IN_WINDOW])
def test_t_max_absent_or_ambiguous_is_transcribed_non_blocking_by_role(status: str) -> None:
    spec = _t_max_spec()
    outcome = TargetSelectionOutcome(
        target_id="T_max",
        status=status,
        group_index=None,
        twice_T=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    record = build_target_selection_record(spec, outcome)
    assert record.role == CALIBRATION_ONLY
    assert record.selection_status == status
    assert record.spectral_window_group_index is None


def test_mismatched_target_id_is_rejected() -> None:
    spec = _fundamental_spec(REQUIRED)
    outcome = TargetSelectionOutcome(
        target_id="first_excited",
        status=SELECTED,
        group_index=1,
        twice_T=None,
        selected_group_status=COMPLETE_MULTIPLET,
        meets_normative_requirements=True,
    )
    with pytest.raises(ValueError, match="does not match"):
        build_target_selection_record(spec, outcome)


# ---------------------------------------------------------------------------
# TargetSelectionRecord invariants
# ---------------------------------------------------------------------------


def test_uses_only_the_four_existing_selection_statuses() -> None:
    from experiments.level1c.target_selection import SELECTION_STATUSES

    assert SELECTION_STATUSES == (SELECTED, AMBIGUOUS, NOT_IN_WINDOW, STRUCTURALLY_NOT_APPLICABLE)


def test_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="role must be"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="OPTIONAL",
            selection_status=SELECTED,
            spectral_window_group_index=0,
            selected_group_status=COMPLETE_MULTIPLET,
            meets_normative_requirements=True,
        )


def test_rejects_group_index_set_when_not_selected() -> None:
    with pytest.raises(ValueError, match="spectral_window_group_index must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role=REQUIRED,
            selection_status=NOT_IN_WINDOW,
            spectral_window_group_index=0,
            selected_group_status=None,
            meets_normative_requirements=None,
        )


def test_rejects_missing_group_index_when_selected() -> None:
    with pytest.raises(ValueError, match="spectral_window_group_index must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role=REQUIRED,
            selection_status=SELECTED,
            spectral_window_group_index=None,
            selected_group_status=COMPLETE_MULTIPLET,
            meets_normative_requirements=True,
        )


def test_structurally_not_applicable_carries_no_group_fields() -> None:
    record = TargetSelectionRecord(
        target_id="fundamental",
        role=REQUIRED,
        selection_status=STRUCTURALLY_NOT_APPLICABLE,
        spectral_window_group_index=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    assert record.spectral_window_group_index is None
