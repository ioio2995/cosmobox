"""Unit tests for cosmobox.level3.serialization (lot L3-I).

No real S=4 execution anywhere: case-result payloads are built from
synthetic CaseExecutionResult objects (spin=4, but never produced by
run_case), and the S3<->S4 comparisons are built either from synthetic
CaseExecutionResult pairs or from the real frozen S2/S3 reference loaded
by cosmobox.level3.frozen_reference (read-only).
"""

from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.metrics import Available
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from cosmobox.level3.frozen_reference import frozen_metric_comparison, load_campaign_summary, reconstruct_case_execution_result
from cosmobox.level3.serialization import (
    S4_CONTRAST_UNRESOLVED,
    S4_DIRECTION_PERSISTS,
    S4_DIRECTION_REVERSES,
    SECOND_DIRECTION_REVERSAL_AT_S4,
    S3_S4_PERSIST_AFTER_S2_S3_REVERSAL,
    THREE_SPIN_DIRECTION_NOT_EVALUABLE,
    THREE_SPIN_SAME_DIRECTION,
    campaign_summary_payload,
    case_result_payload,
    primary_s3_s4_taxonomy,
    r_d_x,
    r_delta_x,
    t_x,
    three_spin_sequence_taxonomy,
    validate_campaign_summary_document,
    validate_case_result_document,
)

NOT_EVALUABLE = "NOT_EVALUABLE"


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
    result = _synthetic_result("triangle", 4, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    validate_case_result_document(document)  # must not raise
    assert document["spin"] == 4
    assert document["schema_version"] == "level3-s4-case-result-v1"


def test_case_result_payload_rejects_spin_other_than_4():
    result = _synthetic_result("triangle", 3, 5)
    with pytest.raises(ValueError):
        case_result_payload(
            result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
            numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
        )


def test_validate_case_result_document_rejects_window_truncated_true():
    result = _synthetic_result("triangle", 4, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["window_truncated"] = True
    with pytest.raises(ValueError):
        validate_case_result_document(document)


def test_validate_case_result_document_rejects_partial_subspace_count_above_zero():
    result = _synthetic_result("triangle", 4, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["partial_subspace_count"] = 2
    with pytest.raises(ValueError):
        validate_case_result_document(document)


# ---------------------------------------------------------------------------
# primary_s3_s4_taxonomy
# ---------------------------------------------------------------------------


def test_primary_s3_s4_taxonomy_persists():
    assert primary_s3_s4_taxonomy("SAME_INTER_S_DIRECTION") == S4_DIRECTION_PERSISTS


def test_primary_s3_s4_taxonomy_reverses():
    assert primary_s3_s4_taxonomy("OPPOSITE_INTER_S_DIRECTION") == S4_DIRECTION_REVERSES


def test_primary_s3_s4_taxonomy_unresolved():
    assert primary_s3_s4_taxonomy("NO_RESOLVED_SPECTRAL_CONTRAST") == S4_CONTRAST_UNRESOLVED


def test_primary_s3_s4_taxonomy_not_evaluable():
    assert primary_s3_s4_taxonomy("NOT_EVALUABLE") == NOT_EVALUABLE


def test_primary_s3_s4_taxonomy_rejects_unknown_input():
    with pytest.raises(ValueError):
        primary_s3_s4_taxonomy("SOMETHING_ELSE")


# ---------------------------------------------------------------------------
# three_spin_sequence_taxonomy
# ---------------------------------------------------------------------------


def test_three_spin_sequence_same_direction():
    assert three_spin_sequence_taxonomy("NEGATIVE", "NEGATIVE", "NEGATIVE") == THREE_SPIN_SAME_DIRECTION
    assert three_spin_sequence_taxonomy("POSITIVE", "POSITIVE", "POSITIVE") == THREE_SPIN_SAME_DIRECTION


def test_three_spin_sequence_persist_after_s2_s3_reversal():
    assert three_spin_sequence_taxonomy("POSITIVE", "NEGATIVE", "NEGATIVE") == S3_S4_PERSIST_AFTER_S2_S3_REVERSAL


def test_three_spin_sequence_second_reversal_at_s4():
    assert three_spin_sequence_taxonomy("NEGATIVE", "NEGATIVE", "POSITIVE") == SECOND_DIRECTION_REVERSAL_AT_S4
    # also unconditional on S2<->S3: a reversal-then-reversal case still
    # classifies purely on S3 vs S4
    assert three_spin_sequence_taxonomy("POSITIVE", "NEGATIVE", "POSITIVE") == SECOND_DIRECTION_REVERSAL_AT_S4


def test_three_spin_sequence_not_evaluable_when_any_direction_unresolved():
    assert three_spin_sequence_taxonomy(None, "NEGATIVE", "NEGATIVE") == THREE_SPIN_DIRECTION_NOT_EVALUABLE
    assert three_spin_sequence_taxonomy("NEGATIVE", "NUMERICALLY_UNRESOLVED", "NEGATIVE") == THREE_SPIN_DIRECTION_NOT_EVALUABLE
    assert three_spin_sequence_taxonomy("NEGATIVE", "NEGATIVE", None) == THREE_SPIN_DIRECTION_NOT_EVALUABLE


# ---------------------------------------------------------------------------
# Continuous descriptors: t_x_23/t_x_34/r_delta_x/r_d_x
# ---------------------------------------------------------------------------


def test_t_x_computes_absolute_difference():
    result = t_x(Available(-0.01, None), Available(-0.05, None))
    assert result.value == pytest.approx(0.04)
    assert result.reason is None


def test_t_x_not_available_when_input_missing():
    result = t_x(Available(None, "reason"), Available(0.1, None))
    assert result.value is None
    assert result.reason is not None


def test_r_delta_x_computed_when_t_x_23_positive():
    t23 = Available(0.02, None)
    t34 = Available(0.06, None)
    result = r_delta_x(t23, t34)
    assert result.value == pytest.approx(3.0)


def test_r_delta_x_unavailable_when_t_x_23_is_zero():
    t23 = Available(0.0, None)
    t34 = Available(0.06, None)
    result = r_delta_x(t23, t34)
    assert result.value is None
    assert result.reason == "T_X_23_NOT_POSITIVE"


def test_r_d_x_computed_when_d_x_23_positive():
    d23 = Available(1.5, None)
    d34 = Available(3.0, None)
    result = r_d_x(d23, d34)
    assert result.value == pytest.approx(2.0)


def test_r_d_x_unavailable_when_d_x_23_is_zero():
    d23 = Available(0.0, None)
    d34 = Available(3.0, None)
    result = r_d_x(d23, d34)
    assert result.value is None
    assert result.reason == "D_X_23_NOT_POSITIVE"


def test_r_d_x_unavailable_when_d_x_23_not_available():
    d23 = Available(None, "some reason")
    d34 = Available(3.0, None)
    result = r_d_x(d23, d34)
    assert result.value is None
    assert result.reason == "D_X_NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# Generic C_X_34/D_X_34 via compare_spin_pair on synthetic S3<->S4 structures
# ---------------------------------------------------------------------------


def test_c_x_34_d_x_34_computed_generically_with_synthetic_structures():
    result_s3 = _synthetic_result("ring5", 3, 5, m_tt_values=[0.1, 0.2, 0.15, 0.3, 0.25])
    result_s4 = _synthetic_result("ring5", 4, 7, m_tt_values=[0.05, 0.4, 0.1, 0.35, 0.2, 0.3, 0.25])
    comparison = compare_spin_pair(result_s3, result_s4)
    assert comparison.m_tt.cross_profile_correlation.value is not None
    assert comparison.m_tt.cross_profile_distance.value is not None


# ---------------------------------------------------------------------------
# Full campaign-summary payload, real frozen S2/S3, synthetic S4
# ---------------------------------------------------------------------------


def test_campaign_summary_payload_validates_against_schema():
    frozen_summary = load_campaign_summary()
    comparisons = []
    for geometry in ("triangle", "ring4", "ring5"):
        result_s3 = reconstruct_case_execution_result(geometry, 3)
        result_s4 = _synthetic_result(geometry, 4, 5)
        comparisons.append(compare_spin_pair(result_s3, result_s4))

    document = campaign_summary_payload(
        comparisons, frozen_campaign_summary=frozen_summary,
        campaign_id="level3-s4-truncation-extension-v1", manifest_fingerprint="fp",
        repository="ioio2995/cosmobox", repository_commit="a" * 40, branch="b",
        frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
    )
    validate_campaign_summary_document(document)  # must not raise
    assert document["campaign_status"] == "COMPLETE"
    assert document["level2_reference"]["campaign_id"] == "level2-energy-regime-v1"
    assert {g["geometry"] for g in document["geometries"]} == {"triangle", "ring4", "ring5"}


def test_campaign_summary_payload_rejects_missing_geometry():
    frozen_summary = load_campaign_summary()
    result_s3 = reconstruct_case_execution_result("triangle", 3)
    result_s4 = _synthetic_result("triangle", 4, 5)
    comparisons = [compare_spin_pair(result_s3, result_s4)]
    with pytest.raises(ValueError):
        campaign_summary_payload(
            comparisons, frozen_campaign_summary=frozen_summary,
            campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
        )


def test_frozen_metric_comparison_feeds_primary_comparison_payload_unchanged():
    # delta_hl_s2/c_x_23/d_x_23 in the payload must equal the frozen
    # values verbatim, never recomputed.
    frozen_summary = load_campaign_summary()
    result_s3 = reconstruct_case_execution_result("triangle", 3)
    result_s4 = _synthetic_result("triangle", 4, 5)
    comparison = compare_spin_pair(result_s3, result_s4)
    document = campaign_summary_payload(
        [comparison] + [
            compare_spin_pair(reconstruct_case_execution_result(g, 3), _synthetic_result(g, 4, 5))
            for g in ("ring4", "ring5")
        ],
        frozen_campaign_summary=frozen_summary,
        campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
    )
    triangle_entry = next(g for g in document["geometries"] if g["geometry"] == "triangle")
    frozen_m_tt = frozen_metric_comparison("triangle", "M_TT")
    assert triangle_entry["m_tt"]["delta_hl_s2"] == frozen_m_tt["delta_hl_s2"]
    assert triangle_entry["m_tt"]["c_x_23"] == frozen_m_tt["c_x_23"]
    assert triangle_entry["m_tt"]["d_x_23"] == frozen_m_tt["d_x_23"]
