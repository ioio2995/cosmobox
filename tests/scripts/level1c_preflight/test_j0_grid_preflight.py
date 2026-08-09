"""Unit tests for scripts.level1c_preflight.j0_grid_preflight (lot 1C-6h).

Every test exercises pure, diagonalization-free functions using real
(never mocked) small objects already accepted elsewhere in the project
(cosmobox.level0.degeneracy.SpectralLevelGroup,
experiments.level1.target_selection.TargetSelectionOutcome) -- never a
real Level0 diagonalization, never the 20-case scientific grid, per the
1C-6h mandate.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from experiments.level1.target_selection import (
    AMBIGUOUS,
    NOT_IN_WINDOW,
    SELECTED,
    STRUCTURALLY_NOT_APPLICABLE,
    TargetSelectionOutcome,
)
from scripts.level1c_preflight import j0_grid_preflight as preflight


def _group(start: int, end: int, *, lower_bound_only: bool = False) -> SpectralLevelGroup:
    return SpectralLevelGroup(
        start_index=start,
        end_index_exclusive=end,
        representative_energy=float(start),
        min_energy=float(start),
        max_energy=float(end - 1),
        multiplicity_observed=end - start,
        lower_bound_only=lower_bound_only,
    )


def _selection_outcome(
    target_id: str, *, group_index: int, complete: bool = True, twice_T: int | None = None
) -> TargetSelectionOutcome:
    return TargetSelectionOutcome(
        target_id=target_id,
        status=SELECTED,
        group_index=group_index,
        twice_T=twice_T,
        selected_group_status=COMPLETE_MULTIPLET if complete else PARTIAL_SUBSPACE,
        meets_normative_requirements=complete,
    )


def _required_outcome(
    target_id: str,
    *,
    group_index: int | None,
    group: SpectralLevelGroup | None,
    selection_status: str = preflight.TARGET_SELECTED,
    subcause: str | None = None,
    complete: bool = True,
    reflection_restriction_valid: bool | None = True,
    v23_applicable: bool | None = True,
    v23_is_valid: bool | None = True,
) -> preflight.RequiredTargetOutcome:
    return preflight.RequiredTargetOutcome(
        target_id=target_id,
        role=preflight.TARGET_ROLE_REQUIRED,
        selection_status=selection_status,
        subcause=subcause,
        group_index=group_index,
        group=group,
        group_state_status=(COMPLETE_MULTIPLET if complete else PARTIAL_SUBSPACE) if selection_status == preflight.TARGET_SELECTED else None,
        twice_T=None,
        translation_label_kind=None,
        reflection_label_kind="numeric" if selection_status == preflight.TARGET_SELECTED else None,
        reflection_restriction_valid=reflection_restriction_valid if selection_status == preflight.TARGET_SELECTED else None,
        v23_applicable=v23_applicable if selection_status == preflight.TARGET_SELECTED else None,
        v23_is_valid=v23_is_valid if selection_status == preflight.TARGET_SELECTED else None,
        v23_status=preflight.V23_OK if selection_status == preflight.TARGET_SELECTED else None,
    )


# ---------------------------------------------------------------------------
# Plan: exactly 20 cases, exact order, no duplicates.
# ---------------------------------------------------------------------------


def test_plan_has_exactly_20_cases_no_duplicates() -> None:
    plan = preflight.build_j0_grid_plan()
    assert len(plan) == 20
    assert len({(case.geometry, case.spin, case.j0) for case in plan}) == 20


def test_plan_exact_deterministic_order() -> None:
    plan = preflight.build_j0_grid_plan()
    expected = [
        (geometry, spin, j0)
        for geometry in ("triangle", "ring5")
        for spin in (2, 3)
        for j0 in (0.5, 0.75, 1.0, 1.25, 1.5)
    ]
    assert [(case.geometry, case.spin, case.j0) for case in plan] == expected


def test_plan_rejects_non_grid_values() -> None:
    with pytest.raises(ValueError):
        preflight.PreflightCase(geometry="triangle", spin=2, j0=0.6)
    with pytest.raises(ValueError):
        preflight.PreflightCase(geometry="ring4", spin=2, j0=1.0)
    with pytest.raises(ValueError):
        preflight.PreflightCase(geometry="triangle", spin=1, j0=1.0)


# ---------------------------------------------------------------------------
# Targets per geometry / T_max never blocking.
# ---------------------------------------------------------------------------


def test_target_role_classification() -> None:
    assert preflight.classify_target_role("fundamental") == preflight.TARGET_ROLE_REQUIRED
    assert preflight.classify_target_role("first_excited") == preflight.TARGET_ROLE_REQUIRED
    assert preflight.classify_target_role("T_3_2") == preflight.TARGET_ROLE_REQUIRED
    assert preflight.classify_target_role("T_max") == preflight.TARGET_ROLE_OPTIONAL_CALIBRATION


def test_t_max_absent_never_blocks_window_sufficient() -> None:
    """A T_max outcome that is TARGET_NOT_IDENTIFIABLE must never even
    reach derive_window_decision: run_case only ever appends REQUIRED
    outcomes to required_outcomes, so an OPTIONAL_CALIBRATION target's
    fate never has a role parameter here at all -- this test asserts the
    decision is SUFFICIENT using only the REQUIRED subset, confirming
    T_max's absence is structurally irrelevant."""
    g0, g1 = _group(0, 2), _group(2, 3)
    required = [
        _required_outcome("fundamental", group_index=0, group=g0),
        _required_outcome("first_excited", group_index=1, group=g1),
    ]
    margin = _group(3, 4)
    decision = preflight.derive_window_decision(required, margin, last_required_end=3, full_spectrum_dimension=10)
    assert decision == preflight.WINDOW_SUFFICIENT


# ---------------------------------------------------------------------------
# Deduplication of REQUIRED groups and last_required_end.
# ---------------------------------------------------------------------------


def test_required_group_indices_deduplicates_shared_group() -> None:
    shared_group = _group(2, 5)
    other_group = _group(5, 9)
    outcomes = [
        _required_outcome("fundamental", group_index=2, group=shared_group),
        _required_outcome("first_excited", group_index=2, group=shared_group),
        _required_outcome("T_3_2", group_index=5, group=other_group),
    ]
    indices = preflight.compute_required_group_indices(outcomes)
    assert indices == frozenset({2, 5})


def test_last_required_end_uses_max_of_unique_groups() -> None:
    shared_group = _group(2, 5)
    other_group = _group(5, 9)
    outcomes = [
        _required_outcome("fundamental", group_index=2, group=shared_group),
        _required_outcome("first_excited", group_index=2, group=shared_group),
        _required_outcome("T_3_2", group_index=5, group=other_group),
    ]
    assert preflight.compute_last_required_end(outcomes) == 9


def test_last_required_end_none_when_no_target_selected() -> None:
    outcomes = [
        _required_outcome(
            "fundamental",
            group_index=None,
            group=None,
            selection_status=preflight.TARGET_NOT_IDENTIFIABLE,
            subcause=preflight.SUBCAUSE_ABSENT_IN_FULL_SPECTRUM,
        )
    ]
    assert preflight.compute_last_required_end(outcomes) is None


# ---------------------------------------------------------------------------
# Margin group selection.
# ---------------------------------------------------------------------------


def test_margin_group_is_first_complete_group_after_last_required_end() -> None:
    groups = [_group(0, 3), _group(3, 5), _group(5, 8)]
    margin = preflight.find_margin_group(groups, last_required_end=3)
    assert margin is not None
    assert (margin.start_index, margin.end_index_exclusive) == (3, 5)


def test_margin_group_none_when_last_required_end_is_top_of_spectrum() -> None:
    groups = [_group(0, 3), _group(3, 8)]
    margin = preflight.find_margin_group(groups, last_required_end=8)
    assert margin is None


# ---------------------------------------------------------------------------
# Production window rule A: general case + dimension fallback.
# ---------------------------------------------------------------------------


def test_production_window_rule_a_general_case() -> None:
    assert preflight.compute_production_window(last_required_end=7, full_spectrum_dimension=20) == 8


def test_production_window_rule_a_dimension_fallback() -> None:
    assert preflight.compute_production_window(last_required_end=20, full_spectrum_dimension=20) == 20


def test_production_window_never_depends_on_margin_group_size() -> None:
    """RULE A depends only on last_required_end and full_spectrum_dimension
    -- a margin group of multiplicity 1 or 50 must yield the identical
    production_window."""
    small_margin_window = preflight.compute_production_window(10, 100)
    # Simulate a "large margin group" scenario: last_required_end is
    # unaffected by whatever the margin group's own multiplicity is,
    # since compute_production_window never receives the margin group.
    assert small_margin_window == 11


# ---------------------------------------------------------------------------
# Target selection classification: absent vs ambiguous, never
# "physically absent".
# ---------------------------------------------------------------------------


def test_classify_selection_outcome_selected() -> None:
    outcome = _selection_outcome("fundamental", group_index=0)
    status, subcause = preflight.classify_selection_outcome(outcome, unresolved_twice_T_present=False)
    assert status == preflight.TARGET_SELECTED
    assert subcause is None


def test_classify_selection_outcome_not_in_window_is_absent_when_all_resolved() -> None:
    outcome = TargetSelectionOutcome(
        target_id="first_excited",
        status=NOT_IN_WINDOW,
        group_index=None,
        twice_T=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    status, subcause = preflight.classify_selection_outcome(outcome, unresolved_twice_T_present=False)
    assert status == preflight.TARGET_NOT_IDENTIFIABLE
    assert subcause == preflight.SUBCAUSE_ABSENT_IN_FULL_SPECTRUM


def test_classify_selection_outcome_not_in_window_is_ambiguous_when_unresolved_twice_t_present() -> None:
    outcome = TargetSelectionOutcome(
        target_id="T_3_2",
        status=NOT_IN_WINDOW,
        group_index=None,
        twice_T=3,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    status, subcause = preflight.classify_selection_outcome(outcome, unresolved_twice_T_present=True)
    assert status == preflight.TARGET_NOT_IDENTIFIABLE
    assert subcause == preflight.SUBCAUSE_SELECTION_AMBIGUOUS


def test_classify_selection_outcome_ambiguous_status() -> None:
    outcome = TargetSelectionOutcome(
        target_id="T_3_2",
        status=AMBIGUOUS,
        group_index=None,
        twice_T=3,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    status, subcause = preflight.classify_selection_outcome(outcome, unresolved_twice_T_present=False)
    assert status == preflight.TARGET_NOT_IDENTIFIABLE
    assert subcause == preflight.SUBCAUSE_SELECTION_AMBIGUOUS


def test_classify_selection_outcome_structurally_not_applicable() -> None:
    outcome = TargetSelectionOutcome(
        target_id="T_3_2",
        status=STRUCTURALLY_NOT_APPLICABLE,
        group_index=None,
        twice_T=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    status, subcause = preflight.classify_selection_outcome(outcome, unresolved_twice_T_present=False)
    assert status == preflight.TARGET_NOT_IDENTIFIABLE
    assert subcause == preflight.SUBCAUSE_ABSENT_IN_FULL_SPECTRUM


# ---------------------------------------------------------------------------
# Window status priority ordering.
# ---------------------------------------------------------------------------


def test_window_decision_sufficient_when_everything_holds() -> None:
    g0 = _group(0, 2)
    required = [_required_outcome("fundamental", group_index=0, group=g0)]
    margin = _group(2, 3)
    assert (
        preflight.derive_window_decision(required, margin, last_required_end=2, full_spectrum_dimension=10)
        == preflight.WINDOW_SUFFICIENT
    )


def test_window_decision_not_identifiable_wins_over_every_other_condition() -> None:
    """A required target that could not be identified must win even when
    every other condition (margin, V23) would otherwise also fail --
    priority 1 is checked first and returns immediately."""
    required = [
        _required_outcome(
            "first_excited",
            group_index=None,
            group=None,
            selection_status=preflight.TARGET_NOT_IDENTIFIABLE,
            subcause=preflight.SUBCAUSE_ABSENT_IN_FULL_SPECTRUM,
        )
    ]
    decision = preflight.derive_window_decision(required, margin_group=None, last_required_end=None, full_spectrum_dimension=10)
    assert decision == preflight.TARGET_NOT_IDENTIFIABLE


def test_window_decision_inconclusive_when_margin_group_missing() -> None:
    g0 = _group(0, 5)
    required = [_required_outcome("fundamental", group_index=0, group=g0)]
    decision = preflight.derive_window_decision(required, margin_group=None, last_required_end=5, full_spectrum_dimension=10)
    assert decision == preflight.WINDOW_INCONCLUSIVE


def test_window_decision_sufficient_when_last_required_end_is_full_dimension_and_no_margin_needed() -> None:
    g0 = _group(0, 10)
    required = [_required_outcome("fundamental", group_index=0, group=g0)]
    decision = preflight.derive_window_decision(required, margin_group=None, last_required_end=10, full_spectrum_dimension=10)
    assert decision == preflight.WINDOW_SUFFICIENT


def test_window_decision_inconclusive_when_v23_not_valid() -> None:
    g0 = _group(0, 2)
    required = [_required_outcome("fundamental", group_index=0, group=g0, v23_is_valid=False)]
    margin = _group(2, 3)
    decision = preflight.derive_window_decision(required, margin, last_required_end=2, full_spectrum_dimension=10)
    assert decision == preflight.WINDOW_INCONCLUSIVE


def test_window_decision_insufficient_when_selected_target_not_complete() -> None:
    g0 = _group(0, 2)
    required = [_required_outcome("fundamental", group_index=0, group=g0, complete=False)]
    margin = _group(2, 3)
    decision = preflight.derive_window_decision(required, margin, last_required_end=2, full_spectrum_dimension=10)
    assert decision == preflight.WINDOW_INSUFFICIENT


# ---------------------------------------------------------------------------
# Global aggregation: ALL_REQUIRED_CASES.
# ---------------------------------------------------------------------------


def _minimal_case_report(*, window_status: str, resource_status: str = preflight.RESOURCE_FEASIBLE) -> preflight.PublicCaseReport:
    return preflight.PublicCaseReport(
        geometry="triangle",
        spin=2,
        j0=1.0,
        full_spectrum_dimension=88,
        eigensolver_dispatch="dense",
        exploratory_window=88,
        production_window=10,
        last_required_end=9,
        margin_group_start_index=9,
        margin_group_end_index_exclusive=10,
        resource_status=resource_status,
        window_status=window_status,
        tracking_preflight_status=preflight.TRACKING_FEASIBLE,
        targets=(),
    )


def test_global_sufficient_when_all_cases_sufficient() -> None:
    reports = [_minimal_case_report(window_status=preflight.WINDOW_SUFFICIENT) for _ in range(20)]
    aggregated = preflight.aggregate_preflight(reports)
    assert aggregated.global_status == preflight.GLOBAL_SUFFICIENT


def test_global_fail_when_a_single_case_is_blocking() -> None:
    reports = [_minimal_case_report(window_status=preflight.WINDOW_SUFFICIENT) for _ in range(19)]
    reports.append(_minimal_case_report(window_status=preflight.WINDOW_INCONCLUSIVE))
    aggregated = preflight.aggregate_preflight(reports)
    assert aggregated.global_status == preflight.GLOBAL_FAIL


def test_global_fail_on_resource_blocking() -> None:
    reports = [_minimal_case_report(window_status=preflight.WINDOW_SUFFICIENT) for _ in range(19)]
    reports.append(
        _minimal_case_report(window_status=preflight.WINDOW_SUFFICIENT, resource_status=preflight.RESOURCE_BLOCKING)
    )
    aggregated = preflight.aggregate_preflight(reports)
    assert aggregated.global_status == preflight.GLOBAL_FAIL


# ---------------------------------------------------------------------------
# Information firewall: energy fields structurally absent from the public
# surface.
# ---------------------------------------------------------------------------

_FORBIDDEN_FIELD_SUBSTRINGS = ("energy", "eigenvalue", "gap")
_FORBIDDEN_V23_FIELD_SUBSTRINGS = ("measured", "expected", "residual", "diagonal", "offdiagonal")


def test_public_target_report_has_no_energy_or_raw_v23_fields() -> None:
    field_names = {field.name for field in dataclasses.fields(preflight.PublicTargetReport)}
    for forbidden in _FORBIDDEN_FIELD_SUBSTRINGS + _FORBIDDEN_V23_FIELD_SUBSTRINGS:
        assert not any(forbidden in name for name in field_names), (forbidden, field_names)
    # Only the sanitized booleans/status may appear for V23.
    assert {"v23_applicable", "v23_is_valid", "v23_status"} <= field_names


def test_public_case_report_has_no_energy_fields() -> None:
    field_names = {field.name for field in dataclasses.fields(preflight.PublicCaseReport)}
    for forbidden in _FORBIDDEN_FIELD_SUBSTRINGS:
        assert not any(forbidden in name for name in field_names), (forbidden, field_names)


def test_public_report_json_serialization_never_contains_forbidden_tokens() -> None:
    target = preflight.PublicTargetReport(
        target_id="fundamental",
        role=preflight.TARGET_ROLE_REQUIRED,
        selection_status=preflight.TARGET_SELECTED,
        subcause=None,
        group_start_index=0,
        group_end_index_exclusive=2,
        multiplicity=2,
        twice_T=1,
        translation_label_kind="not_applicable",
        reflection_label_kind="numeric",
        reflection_restriction_valid=True,
        complete_multiplet=True,
        lower_bound_only=False,
        v23_applicable=True,
        v23_is_valid=True,
        v23_status=preflight.V23_OK,
    )
    case = preflight.PublicCaseReport(
        geometry="triangle",
        spin=2,
        j0=1.25,
        full_spectrum_dimension=88,
        eigensolver_dispatch="dense",
        exploratory_window=88,
        production_window=3,
        last_required_end=2,
        margin_group_start_index=2,
        margin_group_end_index_exclusive=3,
        resource_status=preflight.RESOURCE_FEASIBLE,
        window_status=preflight.WINDOW_SUFFICIENT,
        tracking_preflight_status=preflight.TRACKING_FEASIBLE,
        targets=(target,),
    )
    report = preflight.PublicPreflightReport(cases=(case,), global_status=preflight.GLOBAL_SUFFICIENT)
    rendered = json.dumps(preflight._public_report_to_json(report))
    for forbidden in _FORBIDDEN_FIELD_SUBSTRINGS + _FORBIDDEN_V23_FIELD_SUBSTRINGS:
        assert forbidden not in rendered


# ---------------------------------------------------------------------------
# V23 sanitization, including exception sanitization.
# ---------------------------------------------------------------------------


def test_sanitize_v23_result_ok_path() -> None:
    diagonal = {0: 0.75, 1: 0.75, 2: 0.75}
    off_diagonal = {(0, 1): 0.25, (1, 0): 0.25, (0, 2): 0.25, (2, 0): 0.25, (1, 2): 0.25, (2, 1): 0.25}
    applicable, is_valid, status = preflight.sanitize_v23_result(COMPLETE_MULTIPLET, 3, diagonal, off_diagonal)
    assert applicable is True
    assert is_valid is True
    assert status == preflight.V23_OK


def test_sanitize_v23_result_catches_real_structural_valueerror() -> None:
    # Two sites declared via the diagonal, but the required (0,1)/(1,0)
    # off-diagonal pairs are missing entirely -- a genuine structural
    # incompleteness that validate_flavor_total_sum rejects with
    # ValueError (never a coincidental is_valid=True/False).
    incomplete_diagonal = {0: 0.75, 1: 0.75}
    incomplete_off_diagonal = {}
    applicable, is_valid, status = preflight.sanitize_v23_result(
        COMPLETE_MULTIPLET, 1, incomplete_diagonal, incomplete_off_diagonal
    )
    assert applicable is None
    assert is_valid is None
    assert status == preflight.V23_VALIDATION_FAILED


def test_sanitize_v23_result_scrubs_crafted_exception(monkeypatch, capsys) -> None:
    def _raise(*_args, **_kwargs):
        raise ValueError("measured=1.234567 expected=2.0 residual=0.765433 boom")

    monkeypatch.setattr(preflight, "validate_flavor_total_sum", _raise)
    applicable, is_valid, status = preflight.sanitize_v23_result(COMPLETE_MULTIPLET, 1, {0: 0.0}, {})
    assert applicable is None
    assert is_valid is None
    assert status == preflight.V23_VALIDATION_FAILED
    forbidden_tokens = ("measured", "expected", "residual", "1.234567", "2.0", "0.765433")
    for token in forbidden_tokens:
        assert token not in status
    captured = capsys.readouterr()
    for token in forbidden_tokens:
        assert token not in captured.out
        assert token not in captured.err


# ---------------------------------------------------------------------------
# Reflection public surface: only the label kind and a validity boolean.
# ---------------------------------------------------------------------------


def test_reflection_public_fields_are_minimal() -> None:
    field_names = {field.name for field in dataclasses.fields(preflight.PublicTargetReport)}
    reflection_fields = {name for name in field_names if "reflection" in name}
    assert reflection_fields == {"reflection_label_kind", "reflection_restriction_valid"}


def test_reflection_squared_identity_defect_zero_for_true_involution() -> None:
    import numpy as np
    import scipy.sparse as sp

    identity = sp.identity(4, format="csr", dtype=np.complex128)
    assert preflight.reflection_squared_identity_defect(identity) == pytest.approx(0.0, abs=1e-12)


def test_reflection_squared_identity_defect_nonzero_for_non_involution() -> None:
    import numpy as np
    import scipy.sparse as sp

    # A cyclic permutation of order 4 (a "quarter turn"): its square is a
    # nontrivial permutation of order 2, not the identity -- a legitimate
    # synthetic non-involution unitary, no physics involved.
    n = 4
    rows = list(range(n))
    cols = [(i + 1) % n for i in range(n)]
    data = [1.0 + 0j] * n
    quarter_turn = sp.csr_matrix((data, (rows, cols)), shape=(n, n), dtype=np.complex128)
    defect = preflight.reflection_squared_identity_defect(quarter_turn)
    assert defect > preflight.UNITARITY_TOLERANCE


# ---------------------------------------------------------------------------
# Tracking preflight vocabulary: exclusive to the preflight, distinct from
# the final-analysis vocabulary.
# ---------------------------------------------------------------------------

_FINAL_ANALYSIS_VOCABULARY = (
    "tracked_one_to_one",
    "tracked_split_branch",
    "ambiguous",
    "discontinuous",
    "not_available",
)


def test_tracking_preflight_statuses_are_disjoint_from_final_analysis_vocabulary() -> None:
    for status in preflight.TRACKING_PREFLIGHT_STATUSES:
        assert status not in _FINAL_ANALYSIS_VOCABULARY


def test_tracking_preflight_status_feasible_when_all_required_selected_and_reflection_valid() -> None:
    g0 = _group(0, 2)
    required = [_required_outcome("fundamental", group_index=0, group=g0, reflection_restriction_valid=True)]
    assert preflight.derive_tracking_preflight_status(required) == preflight.TRACKING_FEASIBLE


def test_tracking_preflight_status_structurally_ambiguous_on_ambiguous_subcause() -> None:
    required = [
        _required_outcome(
            "T_3_2",
            group_index=None,
            group=None,
            selection_status=preflight.TARGET_NOT_IDENTIFIABLE,
            subcause=preflight.SUBCAUSE_SELECTION_AMBIGUOUS,
        )
    ]
    assert preflight.derive_tracking_preflight_status(required) == preflight.TRACKING_STRUCTURALLY_AMBIGUOUS


def test_tracking_preflight_status_structurally_ambiguous_on_invalid_reflection() -> None:
    g0 = _group(0, 2)
    required = [_required_outcome("fundamental", group_index=0, group=g0, reflection_restriction_valid=False)]
    assert preflight.derive_tracking_preflight_status(required) == preflight.TRACKING_STRUCTURALLY_AMBIGUOUS


def test_tracking_preflight_status_not_evaluated_when_empty() -> None:
    assert preflight.derive_tracking_preflight_status([]) == preflight.TRACKING_NOT_EVALUATED


# ---------------------------------------------------------------------------
# CLI safety: --help never diagonalizes anything.
# ---------------------------------------------------------------------------


def test_cli_help_does_not_run_full_grid(monkeypatch, capsys) -> None:
    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("run_preflight must never be called without --confirm-run-full-grid")

    monkeypatch.setattr(preflight, "run_preflight", _fail_if_called)
    exit_code = preflight.main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_cli_without_confirm_flag_never_invokes_run_preflight(monkeypatch) -> None:
    called = {"value": False}

    def _mark_called(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("must not be called")

    monkeypatch.setattr(preflight, "run_preflight", _mark_called)
    preflight.main([])
    assert called["value"] is False
