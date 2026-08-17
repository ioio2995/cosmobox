"""Unit tests for cosmobox.level3.s5_serialization (lot L3-P).

No real S=5 execution anywhere: case-result payloads are built from
synthetic CaseExecutionResult objects (spin=5, but never produced by
run_case), and the S4<->S5 comparisons are built either from synthetic
CaseExecutionResult pairs or from the real frozen S4 reference loaded by
cosmobox.level3.frozen_s4_reference (read-only).
"""

from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.metrics import Available
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from cosmobox.level3.frozen_s4_reference import frozen_metric_comparison, load_campaign_summary, reconstruct_case_execution_result
from cosmobox.level3.s5_serialization import (
    NOT_EVALUABLE,
    REVERSAL_COUNT_NOT_EVALUABLE,
    S5_CONTRAST_UNRESOLVED,
    S5_DIRECTION_PERSISTS,
    S5_DIRECTION_REVERSES,
    campaign_summary_payload,
    case_result_payload,
    primary_s4_s5_taxonomy,
    reversal_count_2345,
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
    result = _synthetic_result("triangle", 5, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    validate_case_result_document(document)  # must not raise
    assert document["spin"] == 5
    assert document["schema_version"] == "level3-s5-case-result-v1"


def test_case_result_payload_rejects_spin_other_than_5():
    result = _synthetic_result("triangle", 4, 5)
    with pytest.raises(ValueError):
        case_result_payload(
            result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
            numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
        )


def test_validate_case_result_document_rejects_window_truncated_true():
    result = _synthetic_result("triangle", 5, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["window_truncated"] = True
    with pytest.raises(ValueError):
        validate_case_result_document(document)


def test_validate_case_result_document_rejects_partial_subspace_count_above_zero():
    result = _synthetic_result("triangle", 5, 5)
    document = case_result_payload(
        result, campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
        numerical_guard_m_tt=1e-16, numerical_guard_r_eff=1e-15, numerical_guard_scope="DELTA_HL_ONLY",
    )
    document["partial_subspace_count"] = 3
    with pytest.raises(ValueError):
        validate_case_result_document(document)


# ---------------------------------------------------------------------------
# primary_s4_s5_taxonomy
# ---------------------------------------------------------------------------


def test_primary_s4_s5_taxonomy_persists():
    assert primary_s4_s5_taxonomy("SAME_INTER_S_DIRECTION") == S5_DIRECTION_PERSISTS


def test_primary_s4_s5_taxonomy_reverses():
    assert primary_s4_s5_taxonomy("OPPOSITE_INTER_S_DIRECTION") == S5_DIRECTION_REVERSES


def test_primary_s4_s5_taxonomy_unresolved():
    assert primary_s4_s5_taxonomy("NO_RESOLVED_SPECTRAL_CONTRAST") == S5_CONTRAST_UNRESOLVED


def test_primary_s4_s5_taxonomy_not_evaluable():
    assert primary_s4_s5_taxonomy("NOT_EVALUABLE") == NOT_EVALUABLE


def test_primary_s4_s5_taxonomy_rejects_unknown_input():
    with pytest.raises(ValueError):
        primary_s4_s5_taxonomy("SOMETHING_ELSE")


# ---------------------------------------------------------------------------
# reversal_count_2345
# ---------------------------------------------------------------------------


def test_reversal_count_zero_when_all_same_direction():
    assert reversal_count_2345("NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE") == 0
    assert reversal_count_2345("POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE") == 0


def test_reversal_count_one():
    assert reversal_count_2345("NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE") == 1


def test_reversal_count_two():
    assert reversal_count_2345("NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE") == 2


def test_reversal_count_three():
    assert reversal_count_2345("NEGATIVE", "POSITIVE", "NEGATIVE", "POSITIVE") == 3


def test_reversal_count_not_evaluable_when_any_direction_unresolved():
    assert reversal_count_2345(None, "NEGATIVE", "NEGATIVE", "NEGATIVE") == REVERSAL_COUNT_NOT_EVALUABLE
    assert reversal_count_2345("NEGATIVE", "NUMERICALLY_UNRESOLVED", "NEGATIVE", "NEGATIVE") == REVERSAL_COUNT_NOT_EVALUABLE
    assert reversal_count_2345("NEGATIVE", "NEGATIVE", "NEGATIVE", None) == REVERSAL_COUNT_NOT_EVALUABLE


# ---------------------------------------------------------------------------
# Generic C_X_45/D_X_45 via compare_spin_pair on synthetic S4<->S5 structures
# ---------------------------------------------------------------------------


def test_c_x_45_d_x_45_computed_generically_with_synthetic_structures():
    result_s4 = _synthetic_result("ring5", 4, 5, m_tt_values=[0.1, 0.2, 0.15, 0.3, 0.25])
    result_s5 = _synthetic_result("ring5", 5, 7, m_tt_values=[0.05, 0.4, 0.1, 0.35, 0.2, 0.3, 0.25])
    comparison = compare_spin_pair(result_s4, result_s5)
    assert comparison.m_tt.cross_profile_correlation.value is not None
    assert comparison.m_tt.cross_profile_distance.value is not None


# ---------------------------------------------------------------------------
# Full campaign-summary payload, real frozen S4 (embedding S2/S3), synthetic S5
# ---------------------------------------------------------------------------


def test_campaign_summary_payload_validates_against_schema():
    frozen_s4_summary = load_campaign_summary()
    comparisons = []
    for geometry in ("triangle", "ring4", "ring5"):
        result_s4 = reconstruct_case_execution_result(geometry)
        result_s5 = _synthetic_result(geometry, 5, 5)
        comparisons.append(compare_spin_pair(result_s4, result_s5))

    document = campaign_summary_payload(
        comparisons, frozen_s4_campaign_summary=frozen_s4_summary,
        campaign_id="level3-s5-truncation-extension-v1", manifest_fingerprint="fp",
        repository="ioio2995/cosmobox", repository_commit="a" * 40, branch="b",
        frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
    )
    validate_campaign_summary_document(document)  # must not raise
    assert document["campaign_status"] == "COMPLETE"
    assert document["level2_reference"]["campaign_id"] == "level2-energy-regime-v1"
    assert document["level3_s4_reference"]["campaign_id"] == "level3-s4-truncation-extension-v1"
    assert {g["geometry"] for g in document["geometries"]} == {"triangle", "ring4", "ring5"}


def test_campaign_summary_payload_rejects_missing_geometry():
    frozen_s4_summary = load_campaign_summary()
    result_s4 = reconstruct_case_execution_result("triangle")
    result_s5 = _synthetic_result("triangle", 5, 5)
    comparisons = [compare_spin_pair(result_s4, result_s5)]
    with pytest.raises(ValueError):
        campaign_summary_payload(
            comparisons, frozen_s4_campaign_summary=frozen_s4_summary,
            campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
            repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
        )


def test_frozen_metric_comparison_feeds_primary_comparison_payload_unchanged():
    # delta_hl_s2/s3/s4, c_x_34, d_x_34 in the payload must equal the
    # frozen S4 values verbatim, never recomputed.
    frozen_s4_summary = load_campaign_summary()
    comparisons = [
        compare_spin_pair(reconstruct_case_execution_result(g), _synthetic_result(g, 5, 5))
        for g in ("triangle", "ring4", "ring5")
    ]
    document = campaign_summary_payload(
        comparisons, frozen_s4_campaign_summary=frozen_s4_summary,
        campaign_id="c", manifest_fingerprint="fp", repository="ioio2995/cosmobox",
        repository_commit="a" * 40, branch="b", frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
    )
    triangle_entry = next(g for g in document["geometries"] if g["geometry"] == "triangle")
    frozen_m_tt = frozen_metric_comparison("triangle", "M_TT")
    assert triangle_entry["m_tt"]["delta_hl_s2"] == frozen_m_tt["delta_hl_s2"]
    assert triangle_entry["m_tt"]["delta_hl_s3"] == frozen_m_tt["delta_hl_s3"]
    assert triangle_entry["m_tt"]["delta_hl_s4"] == frozen_m_tt["delta_hl_s4"]
    assert triangle_entry["m_tt"]["c_x_34"] == frozen_m_tt["c_x_34"]
    assert triangle_entry["m_tt"]["d_x_34"] == frozen_m_tt["d_x_34"]
