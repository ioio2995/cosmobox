from __future__ import annotations

import math

import pytest

from experiments.level1.target_selection import AMBIGUOUS, NOT_IN_WINDOW, SELECTED, TargetSelectionOutcome
from experiments.level1c.case_artifact import required_targets_are_satisfied
from experiments.level1c.result_schema import validate_result_record
from scripts.level1c_campaign.runner import (
    _complete_group_indices,
    _selected_group_indices,
    run_level1c_case,
)

# ---------------------------------------------------------------------------
# Pure helpers (_complete_group_indices / _selected_group_indices): fully
# synthetic, no diagonalization, no monkeypatching -- direct unit tests of
# the two invariants (SPECTRAL_STRUCTURE_PRODUCTION /
# PHYSICAL_OBSERVABLE_PRODUCTION) in isolation.
# ---------------------------------------------------------------------------


class _FakeGroupState:
    def __init__(self, status: str) -> None:
        self.status = status


def test_complete_group_indices_selects_only_complete_status() -> None:
    states = [
        _FakeGroupState("complete_multiplet"),
        _FakeGroupState("partial_subspace"),
        _FakeGroupState("complete_multiplet"),
    ]
    assert _complete_group_indices(states) == (0, 2)


def test_complete_group_indices_empty_when_none_complete() -> None:
    states = [_FakeGroupState("partial_subspace"), _FakeGroupState("partial_subspace")]
    assert _complete_group_indices(states) == ()


def _outcome(target_id: str, status: str, group_index: int | None) -> TargetSelectionOutcome:
    if status == SELECTED:
        return TargetSelectionOutcome(
            target_id=target_id,
            status=SELECTED,
            group_index=group_index,
            twice_T=None,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )
    return TargetSelectionOutcome(
        target_id=target_id, status=status, group_index=None, twice_T=None, selected_group_status=None, meets_normative_requirements=None
    )


def test_selected_group_indices_deduplicates_shared_group() -> None:
    outcomes = (_outcome("a", SELECTED, 0), _outcome("b", SELECTED, 1), _outcome("c", SELECTED, 1))
    assert _selected_group_indices(outcomes) == (0, 1)


def test_selected_group_indices_ignores_non_selected() -> None:
    outcomes = (_outcome("a", SELECTED, 0), _outcome("b", NOT_IN_WINDOW, None), _outcome("c", AMBIGUOUS, None))
    assert _selected_group_indices(outcomes) == (0,)


def test_selected_group_indices_empty_when_nothing_selected() -> None:
    outcomes = (_outcome("a", NOT_IN_WINDOW, None), _outcome("b", AMBIGUOUS, None))
    assert _selected_group_indices(outcomes) == ()


# ---------------------------------------------------------------------------
# Real single-case runs (small triangle cases + one ring5 case) --
# triangle target order, T_max non-blocking, all-structure-groups,
# observables-only-on-selected, group start/end persisted, no target
# selection leaking into documents, schema validation, no NaN/inf.
# ---------------------------------------------------------------------------


def test_triangle_target_order(triangle_j0_1_00_result) -> None:
    assert [record.target_id for record in triangle_j0_1_00_result.target_selections] == [
        "fundamental",
        "first_excited",
        "T_max",
    ]


def test_ring5_target_order(ring5_j0_1_00_result) -> None:
    assert [record.target_id for record in ring5_j0_1_00_result.target_selections] == [
        "fundamental",
        "first_excited",
        "T_3_2",
        "T_max",
    ]


def test_t_max_nonblocking_when_not_in_window(ring5_j0_1_00_result) -> None:
    t_max = next(record for record in ring5_j0_1_00_result.target_selections if record.target_id == "T_max")
    assert t_max.role == "CALIBRATION_ONLY"
    assert t_max.selection_status == "not_in_window"
    assert required_targets_are_satisfied(ring5_j0_1_00_result.target_selections) is True


def test_t_max_nonblocking_when_selected_but_partial(triangle_j0_0_50_result) -> None:
    t_max = next(record for record in triangle_j0_0_50_result.target_selections if record.target_id == "T_max")
    assert t_max.role == "CALIBRATION_ONLY"
    assert t_max.selection_status == "selected"
    assert t_max.selected_group_status == "partial_subspace"
    assert t_max.meets_normative_requirements is False
    assert required_targets_are_satisfied(triangle_j0_0_50_result.target_selections) is True


def test_t_3_2_required(ring5_j0_1_00_result) -> None:
    t_3_2 = next(record for record in ring5_j0_1_00_result.target_selections if record.target_id == "T_3_2")
    assert t_3_2.role == "REQUIRED"
    assert t_3_2.selection_status == "selected"
    assert t_3_2.meets_normative_requirements is True


def test_required_target_missing_makes_gate_false() -> None:
    from experiments.level1c.target_selection import TargetSelectionRecord

    selections = (
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="ambiguous",
            spectral_window_group_index=None,
            selected_group_status=None,
            meets_normative_requirements=None,
        ),
        TargetSelectionRecord(
            target_id="first_excited",
            role="REQUIRED",
            selection_status="selected",
            spectral_window_group_index=1,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        ),
        TargetSelectionRecord(
            target_id="T_max",
            role="CALIBRATION_ONLY",
            selection_status="not_in_window",
            spectral_window_group_index=None,
            selected_group_status=None,
            meets_normative_requirements=None,
        ),
    )
    assert required_targets_are_satisfied(selections) is False


@pytest.mark.parametrize(
    "result_fixture",
    ["triangle_j0_1_00_result", "triangle_j0_0_50_result", "ring5_j0_1_00_result"],
)
def test_all_structural_records_are_on_complete_groups_only(result_fixture, request) -> None:
    result = request.getfixturevalue(result_fixture)
    for document in result.documents:
        if document["record_kind"] == "symmetry_label":
            assert document["identity"]["spectral_group"]["status"] == "complete_multiplet"


def test_triangle_baseline_both_complete_groups_are_structurally_present(triangle_j0_1_00_result) -> None:
    structural_groups = sorted(
        {
            document["identity"]["spectral_group"]["spectral_window_group_index"]
            for document in triangle_j0_1_00_result.documents
            if document["record_kind"] == "symmetry_label"
        }
    )
    assert structural_groups == [0, 1]
    for group_index in structural_groups:
        count = sum(
            1
            for document in triangle_j0_1_00_result.documents
            if document["record_kind"] == "symmetry_label"
            and document["identity"]["spectral_group"]["spectral_window_group_index"] == group_index
        )
        assert count == 3  # flavor_casimir_label, translation_character, reflection_character


def test_perturbed_triangle_partial_group_never_gets_structural_records(triangle_j0_0_50_result) -> None:
    """T_max resolves to a partial_subspace group (index 2) in this real
    case -- it must receive observables (selected) but never structural
    symmetry_label records (not complete)."""
    structural_groups = {
        document["identity"]["spectral_group"]["spectral_window_group_index"]
        for document in triangle_j0_0_50_result.documents
        if document["record_kind"] == "symmetry_label"
    }
    observable_groups = {
        document["identity"]["spectral_group"]["spectral_window_group_index"]
        for document in triangle_j0_0_50_result.documents
        if document["record_kind"] in ("raw_observable", "normalized_observable")
    }
    assert 2 not in structural_groups
    assert 2 in observable_groups


def test_observables_only_on_selected_target_groups(triangle_j0_1_00_result) -> None:
    selected_group_indices = {
        record.spectral_window_group_index
        for record in triangle_j0_1_00_result.target_selections
        if record.selection_status == "selected"
    }
    observable_groups = {
        document["identity"]["spectral_group"]["spectral_window_group_index"]
        for document in triangle_j0_1_00_result.documents
        if document["record_kind"] in ("raw_observable", "normalized_observable")
    }
    assert observable_groups == selected_group_indices


def test_group_start_end_persisted_and_consistent(ring5_j0_1_00_result) -> None:
    for document in ring5_j0_1_00_result.documents:
        group = document["identity"]["spectral_group"]
        assert group["group_start_index"] < group["group_end_index_exclusive"]
        assert group["group_end_index_exclusive"] - group["group_start_index"] == group["multiplicity"]


def test_target_selections_never_appear_in_documents(triangle_j0_1_00_result) -> None:
    record_kinds = {document["record_kind"] for document in triangle_j0_1_00_result.documents}
    assert "target_selection" not in record_kinds
    assert record_kinds <= {"raw_observable", "normalized_observable", "symmetry_label"}


@pytest.mark.parametrize(
    "result_fixture",
    ["triangle_j0_1_00_result", "triangle_j0_0_50_result", "ring5_j0_1_00_result"],
)
def test_all_documents_valid_against_result_record_schema(result_fixture, request) -> None:
    result = request.getfixturevalue(result_fixture)
    for document in result.documents:
        validate_result_record(document)


@pytest.mark.parametrize(
    "result_fixture",
    ["triangle_j0_1_00_result", "triangle_j0_0_50_result", "ring5_j0_1_00_result"],
)
def test_no_non_finite_values_in_any_document(result_fixture, request) -> None:
    result = request.getfixturevalue(result_fixture)
    for document in result.documents:
        payload = document["payload"]
        if document["record_kind"] == "raw_observable":
            assert math.isfinite(payload)
        elif document["record_kind"] == "normalized_observable":
            if payload["value"] is not None:
                assert math.isfinite(payload["value"])
        elif document["record_kind"] == "symmetry_label" and payload["kind"] == "numeric":
            assert math.isfinite(payload["value"]["real"])
            assert math.isfinite(payload["value"]["imag"])
        assert math.isfinite(document["identity"]["spectral_group"]["representative_energy"])


def test_case_not_in_plan_is_rejected(manifest, triangle_j0_1_00_case) -> None:
    import dataclasses

    # solver_seed is not part of compute_case_id's own inputs, so this
    # tampered case still self-validates (CampaignCaseSpec.__post_init__
    # passes) -- it must instead be rejected by run_level1c_case's own
    # plan-membership check (_case_matches_planned_case), never silently
    # diagonalized with a seed the plan never derived.
    tampered = dataclasses.replace(triangle_j0_1_00_case, solver_seed=triangle_j0_1_00_case.solver_seed + 1)
    with pytest.raises(ValueError, match="differs from the case build_level1c_campaign_plan"):
        run_level1c_case(manifest, tampered, repository_commit="5159c2d68a060858cfd751e9b76365eecb2aba3e")
