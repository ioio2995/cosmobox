"""Unit tests for cosmobox.level3.s7_serialization (lot L3-AC).

No real S=7 execution anywhere: case-result payloads are built from
synthetic CaseExecutionResult objects (spin=7, but never produced by
run_case), and the S6<->S7 comparisons are built either from synthetic
CaseExecutionResult pairs or from the real frozen S6 reference loaded by
cosmobox.level3.frozen_s6_reference (read-only).
"""

from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.metrics import Available
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from cosmobox.level3.frozen_s6_reference import frozen_metric_comparison, load_campaign_summary, reconstruct_case_execution_result
from cosmobox.level3.s7_serialization import (
    LAST_TWO_TRANSITIONS_567_NO,
    LAST_TWO_TRANSITIONS_567_NOT_EVALUABLE,
    LAST_TWO_TRANSITIONS_567_YES,
    NOT_EVALUABLE,
    PAIRWISE_BLOCK_RECURRENCE_NO,
    PAIRWISE_BLOCK_RECURRENCE_NOT_EVALUABLE,
    PAIRWISE_BLOCK_RECURRENCE_YES,
    REVERSAL_COUNT_NOT_EVALUABLE,
    S7_CONTRAST_UNRESOLVED,
    S7_DIRECTION_PERSISTS,
    S7_DIRECTION_REVERSES,
    campaign_summary_payload,
    case_result_payload,
    last_two_transitions_directionally_continuous_567,
    pairwise_block_recurrence_23_45_67,
    primary_s6_s7_taxonomy,
    reversal_count_234567,
    validate_campaign_summary_document,
    validate_case_result_document,
)


# ---------------------------------------------------------------------------
# Synthetic case construction helpers
# ---------------------------------------------------------------------------


def _entry_with_raw_observables(q_start: float, q_end: float, *, m_tt: float, r_eff: Available, a_qq: float, m_qq: Available) -> MultipletProfileEntry:
    matrix = np.eye(2) * max(m_tt, 1e-9)
    rho_qq = {(0, 1): metrics.RhoQQEntry(0.1, None), (1, 0): metrics.RhoQQEntry(0.1, None)}
    return MultipletProfileEntry(
        energy=0.0, multiplicity=1, epsilon=0.0,
        q_start=q_start, q_end=q_end, q_midpoint=(q_start + q_end) / 2,
        m_tt=m_tt, r_eff=r_eff, a_qq=a_qq, m_qq=m_qq,
        c_tt_conn=matrix, rho_qq=rho_qq,
    )


def _synthetic_result(geometry: str, spin: int, n: int, *, m_tt_values=None) -> CaseExecutionResult:
    boundaries = [i / n for i in range(n + 1)]
    values = m_tt_values if m_tt_values is not None else [float(i + 1) * 0.01 for i in range(n)]
    entries = tuple(
        _entry_with_raw_observables(
            boundaries[i], boundaries[i + 1],
            m_tt=values[i], r_eff=Available(0.1 * (i + 1), None), a_qq=0.5, m_qq=Available(0.2, None),
        )
        for i in range(n)
    )
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin), dimension=n, group_count=n, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )


# ---------------------------------------------------------------------------
# case_result_payload
# ---------------------------------------------------------------------------


def test_case_result_payload_validates_against_schema():
    result = _synthetic_result("triangle", 7, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    validate_case_result_document(document)  # must not raise
    assert document["spin"] == 7
    assert document["schema_version"] == "level3-s7-case-result-v1"


def test_case_result_payload_rejects_spin_other_than_7():
    result = _synthetic_result("triangle", 6, 5)
    with pytest.raises(ValueError):
        case_result_payload(
            result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
            numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
        )


def test_validate_case_result_document_rejects_window_truncated_true():
    result = _synthetic_result("triangle", 7, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["window_truncated"] = True
    with pytest.raises(ValueError):
        validate_case_result_document(document)


def test_validate_case_result_document_rejects_partial_subspace_count_above_zero():
    result = _synthetic_result("triangle", 7, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["partial_subspace_count"] = 3
    with pytest.raises(ValueError):
        validate_case_result_document(document)


# ---------------------------------------------------------------------------
# primary_s6_s7_taxonomy
# ---------------------------------------------------------------------------


def test_primary_s6_s7_taxonomy_persists():
    assert primary_s6_s7_taxonomy("SAME_INTER_S_DIRECTION") == S7_DIRECTION_PERSISTS


def test_primary_s6_s7_taxonomy_reverses():
    assert primary_s6_s7_taxonomy("OPPOSITE_INTER_S_DIRECTION") == S7_DIRECTION_REVERSES


def test_primary_s6_s7_taxonomy_unresolved():
    assert primary_s6_s7_taxonomy("NO_RESOLVED_SPECTRAL_CONTRAST") == S7_CONTRAST_UNRESOLVED


def test_primary_s6_s7_taxonomy_not_evaluable():
    assert primary_s6_s7_taxonomy("NOT_EVALUABLE") == NOT_EVALUABLE


def test_primary_s6_s7_taxonomy_rejects_unknown_input():
    with pytest.raises(ValueError):
        primary_s6_s7_taxonomy("SOMETHING_ELSE")


# ---------------------------------------------------------------------------
# reversal_count_234567
# ---------------------------------------------------------------------------


def test_reversal_count_zero_when_all_same_direction():
    assert reversal_count_234567("NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE") == 0
    assert reversal_count_234567("POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE") == 0


def test_reversal_count_one():
    assert reversal_count_234567("NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE") == 1


def test_reversal_count_two():
    assert reversal_count_234567("NEGATIVE", "NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE") == 2


def test_reversal_count_three():
    assert reversal_count_234567("NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE", "POSITIVE") == 3


def test_reversal_count_four():
    assert reversal_count_234567("NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "POSITIVE", "NEGATIVE") == 4


def test_reversal_count_five():
    assert reversal_count_234567("NEGATIVE", "POSITIVE", "NEGATIVE", "POSITIVE", "NEGATIVE", "POSITIVE") == 5


def test_reversal_count_not_evaluable_when_any_direction_unresolved():
    assert (
        reversal_count_234567(None, "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE")
        == REVERSAL_COUNT_NOT_EVALUABLE
    )
    assert (
        reversal_count_234567("NEGATIVE", "NUMERICALLY_UNRESOLVED", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE")
        == REVERSAL_COUNT_NOT_EVALUABLE
    )
    assert (
        reversal_count_234567("NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", None)
        == REVERSAL_COUNT_NOT_EVALUABLE
    )


# ---------------------------------------------------------------------------
# last_two_transitions_directionally_continuous_567
# ---------------------------------------------------------------------------


def test_last_two_transitions_567_yes_when_all_three_same():
    assert last_two_transitions_directionally_continuous_567("POSITIVE", "POSITIVE", "POSITIVE") == LAST_TWO_TRANSITIONS_567_YES
    assert last_two_transitions_directionally_continuous_567("NEGATIVE", "NEGATIVE", "NEGATIVE") == LAST_TWO_TRANSITIONS_567_YES


def test_last_two_transitions_567_no_when_s5_to_s6_reverses():
    assert last_two_transitions_directionally_continuous_567("NEGATIVE", "POSITIVE", "POSITIVE") == LAST_TWO_TRANSITIONS_567_NO


def test_last_two_transitions_567_no_when_s6_to_s7_reverses():
    assert last_two_transitions_directionally_continuous_567("POSITIVE", "POSITIVE", "NEGATIVE") == LAST_TWO_TRANSITIONS_567_NO


def test_last_two_transitions_567_no_when_both_transitions_reverse():
    assert last_two_transitions_directionally_continuous_567("NEGATIVE", "POSITIVE", "NEGATIVE") == LAST_TWO_TRANSITIONS_567_NO


def test_last_two_transitions_567_not_evaluable_when_any_sign_unresolved():
    assert (
        last_two_transitions_directionally_continuous_567(None, "POSITIVE", "POSITIVE")
        == LAST_TWO_TRANSITIONS_567_NOT_EVALUABLE
    )
    assert (
        last_two_transitions_directionally_continuous_567("POSITIVE", "NUMERICALLY_UNRESOLVED", "POSITIVE")
        == LAST_TWO_TRANSITIONS_567_NOT_EVALUABLE
    )
    assert (
        last_two_transitions_directionally_continuous_567("POSITIVE", "POSITIVE", None)
        == LAST_TWO_TRANSITIONS_567_NOT_EVALUABLE
    )


# ---------------------------------------------------------------------------
# pairwise_block_recurrence_23_45_67
# ---------------------------------------------------------------------------


def test_pairwise_block_recurrence_yes_for_a_a_b_b_a_a():
    # sign(S2)=sign(S3)=NEGATIVE, sign(S4)=sign(S5)=POSITIVE, sign(S6)=sign(S7)=NEGATIVE
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE")
        == PAIRWISE_BLOCK_RECURRENCE_YES
    )
    # the opposite polarity is equally valid: A=POSITIVE, B=NEGATIVE
    assert (
        pairwise_block_recurrence_23_45_67("POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE")
        == PAIRWISE_BLOCK_RECURRENCE_YES
    )


def test_pairwise_block_recurrence_no_when_s2_s3_pair_disagrees():
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "POSITIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NO
    )


def test_pairwise_block_recurrence_no_when_s4_s5_pair_disagrees():
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "NEGATIVE", "POSITIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NO
    )


def test_pairwise_block_recurrence_no_when_s6_s7_pair_disagrees():
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "POSITIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NO
    )


def test_pairwise_block_recurrence_no_when_a_block_equals_b_block():
    # sign(S2) == sign(S4) violates the required inequality
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NO
    )


def test_pairwise_block_recurrence_no_when_third_block_does_not_match_first():
    # sign(S2) != sign(S6) violates the required equality
    assert (
        pairwise_block_recurrence_23_45_67("NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NO
    )


def test_pairwise_block_recurrence_not_evaluable_when_any_direction_unresolved():
    assert (
        pairwise_block_recurrence_23_45_67(None, "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE")
        == PAIRWISE_BLOCK_RECURRENCE_NOT_EVALUABLE
    )
    assert (
        pairwise_block_recurrence_23_45_67(
            "NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE", "NUMERICALLY_UNRESOLVED"
        )
        == PAIRWISE_BLOCK_RECURRENCE_NOT_EVALUABLE
    )


# ---------------------------------------------------------------------------
# Generic C_X_67/D_X_67 via compare_spin_pair on synthetic S6<->S7 structures
# ---------------------------------------------------------------------------


def test_c_x_67_d_x_67_computed_generically_with_synthetic_structures():
    result_s6 = _synthetic_result("ring5", 6, 5, m_tt_values=[0.1, 0.2, 0.15, 0.3, 0.25])
    result_s7 = _synthetic_result("ring5", 7, 7, m_tt_values=[0.05, 0.4, 0.1, 0.35, 0.2, 0.3, 0.25])
    comparison = compare_spin_pair(result_s6, result_s7)
    assert comparison.m_tt.cross_profile_correlation.value is not None
    assert comparison.m_tt.cross_profile_distance.value is not None


# ---------------------------------------------------------------------------
# Full campaign-summary payload, real frozen S6 (embedding S2/S3/S4/S5), synthetic S7
# ---------------------------------------------------------------------------


def test_campaign_summary_payload_validates_against_schema():
    frozen_s6_summary = load_campaign_summary()
    comparisons = []
    for geometry in ("triangle", "ring4", "ring5"):
        result_s6 = reconstruct_case_execution_result(geometry)
        result_s7 = _synthetic_result(geometry, 7, 5)
        comparisons.append(compare_spin_pair(result_s6, result_s7))

    document = campaign_summary_payload(
        comparisons, frozen_s6_campaign_summary=frozen_s6_summary,
        campaign_id="level3-s7-truncation-extension-v1", manifest_fingerprint="fp",
        repository="ioio2995/cosmobox", repository_commit="a" * 40, branch="b",
        frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
    )
    validate_campaign_summary_document(document)  # must not raise
    assert document["campaign_status"] == "COMPLETE"
    assert document["level2_reference"]["campaign_id"] == "level2-energy-regime-v1"
    assert document["level3_s4_reference"]["campaign_id"] == "level3-s4-truncation-extension-v1"
    assert document["level3_s5_reference"]["campaign_id"] == "level3-s5-truncation-extension-v1"
    assert document["level3_s6_reference"]["campaign_id"] == "level3-s6-truncation-extension-v1"
    assert {g["geometry"] for g in document["geometries"]} == {"triangle", "ring4", "ring5"}


def test_campaign_summary_payload_rejects_missing_geometry():
    frozen_s6_summary = load_campaign_summary()
    result_s6 = reconstruct_case_execution_result("triangle")
    result_s7 = _synthetic_result("triangle", 7, 5)
    comparisons = [compare_spin_pair(result_s6, result_s7)]
    with pytest.raises(ValueError):
        campaign_summary_payload(
            comparisons, frozen_s6_campaign_summary=frozen_s6_summary,
            campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
        )


def test_frozen_metric_comparison_feeds_primary_comparison_payload_unchanged():
    # delta_hl_s2/s3/s4/s5/s6, c_x_56, d_x_56 in the payload must equal
    # the frozen S6 values verbatim, never recomputed.
    frozen_s6_summary = load_campaign_summary()
    comparisons = [
        compare_spin_pair(reconstruct_case_execution_result(g), _synthetic_result(g, 7, 5))
        for g in ("triangle", "ring4", "ring5")
    ]
    document = campaign_summary_payload(
        comparisons, frozen_s6_campaign_summary=frozen_s6_summary,
        campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="cc0ffdadbeb7d40fc443ab11150c9f47e3e12776",
    )
    triangle_entry = next(g for g in document["geometries"] if g["geometry"] == "triangle")
    frozen_m_tt = frozen_metric_comparison("triangle", "M_TT")
    assert triangle_entry["m_tt"]["delta_hl_s2"] == frozen_m_tt["delta_hl_s2"]
    assert triangle_entry["m_tt"]["delta_hl_s3"] == frozen_m_tt["delta_hl_s3"]
    assert triangle_entry["m_tt"]["delta_hl_s4"] == frozen_m_tt["delta_hl_s4"]
    assert triangle_entry["m_tt"]["delta_hl_s5"] == frozen_m_tt["delta_hl_s5"]
    assert triangle_entry["m_tt"]["delta_hl_s6"] == frozen_m_tt["delta_hl_s6"]
    assert triangle_entry["m_tt"]["c_x_56"] == frozen_m_tt["c_x_56"]
    assert triangle_entry["m_tt"]["d_x_56"] == frozen_m_tt["d_x_56"]
