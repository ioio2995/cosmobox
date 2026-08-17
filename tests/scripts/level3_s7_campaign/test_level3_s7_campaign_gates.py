"""Unit tests for scripts.level3_s7_campaign.gates (lot L3-AC). Synthetic
CaseExecutionResult objects only -- no diagonalization anywhere.
"""

from __future__ import annotations

import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from scripts.level3_s7_campaign.gates import CampaignGateFailure, CaseGateFailure, validate_campaign_completeness, validate_case_result


def _entry(q_start: float, q_end: float, seed: float, *, multiplicity: int = 1) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0, multiplicity=multiplicity, epsilon=0.0,
        q_start=q_start, q_end=q_end, q_midpoint=(q_start + q_end) / 2,
        m_tt=seed, r_eff=metrics.Available(0.1 * seed, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
    )


def _result(geometry: str, dimension: int, *, spin: int = 7) -> CaseExecutionResult:
    n = dimension
    boundaries = [i / n for i in range(n + 1)]
    entries = tuple(_entry(boundaries[i], boundaries[i + 1], float(i + 1)) for i in range(n))
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin), dimension=n, group_count=n, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )


# ---------------------------------------------------------------------------
# validate_case_result: dimension against the L3-AA reference
# ---------------------------------------------------------------------------


def test_validate_case_result_accepts_triangle_288():
    validate_case_result(_result("triangle", 288))  # must not raise


def test_validate_case_result_accepts_ring4_992():
    validate_case_result(_result("ring4", 992))  # must not raise


def test_validate_case_result_accepts_ring5_3520():
    validate_case_result(_result("ring5", 3520))  # must not raise


def test_validate_case_result_rejects_wrong_dimension():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 289))


def test_validate_case_result_rejects_spin_other_than_7():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 288, spin=6))


def test_validate_case_result_rejects_unknown_geometry():
    result = _result("triangle", 288)
    object.__setattr__(result.spec, "geometry", "hexagon")
    with pytest.raises(CaseGateFailure):
        validate_case_result(result)


def test_validate_case_result_rejects_q_coverage_gap():
    # Multiplicities sum to exactly 288 (the triangle S7 reference
    # dimension) so the dimension check passes and the q-coverage check
    # is isolated: q_end=0.3 then q_start=0.35 is a genuine gap.
    entries = (
        _entry(0.0, 0.3, 1.0, multiplicity=96),
        _entry(0.35, 0.6, 2.0, multiplicity=96),
        _entry(0.6, 1.0, 3.0, multiplicity=96),
    )
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    result = CaseExecutionResult(
        spec=CaseSpec(geometry="triangle", spin=7), dimension=288, group_count=3, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )
    with pytest.raises(CaseGateFailure):
        validate_case_result(result)


# ---------------------------------------------------------------------------
# validate_campaign_completeness
# ---------------------------------------------------------------------------


def _comparison(geometry: str):
    result_a = _result(geometry, 4, spin=6)
    result_b = _result(geometry, 5, spin=7)
    return compare_spin_pair(result_a, result_b)


def test_validate_campaign_completeness_accepts_exactly_three_cases_and_comparisons():
    results = [_result("triangle", 288), _result("ring4", 992), _result("ring5", 3520)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    validate_campaign_completeness(results, comparisons)  # must not raise


def test_validate_campaign_completeness_rejects_missing_case():
    results = [_result("triangle", 288), _result("ring4", 992)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)


def test_validate_campaign_completeness_rejects_duplicate_geometry():
    results = [_result("triangle", 288), _result("triangle", 288), _result("ring5", 3520)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)


def test_validate_campaign_completeness_rejects_missing_comparison():
    results = [_result("triangle", 288), _result("ring4", 992), _result("ring5", 3520)]
    comparisons = [_comparison("triangle"), _comparison("ring4")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)
