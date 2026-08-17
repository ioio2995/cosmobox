"""Unit tests for scripts.level3_campaign.gates (lot L3-I). Synthetic
CaseExecutionResult objects only -- no diagonalization anywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from scripts.level3_campaign.gates import CampaignGateFailure, CaseGateFailure, validate_campaign_completeness, validate_case_result


def _entry(q_start: float, q_end: float, seed: float, *, multiplicity: int = 1) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0, multiplicity=multiplicity, epsilon=0.0,
        q_start=q_start, q_end=q_end, q_midpoint=(q_start + q_end) / 2,
        m_tt=seed, r_eff=metrics.Available(0.1 * seed, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
    )


def _result(geometry: str, dimension: int, *, spin: int = 4) -> CaseExecutionResult:
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
# validate_case_result: dimension against the L3-C reference
# ---------------------------------------------------------------------------


def test_validate_case_result_accepts_triangle_168():
    validate_case_result(_result("triangle", 168))  # must not raise


def test_validate_case_result_accepts_ring4_572():
    validate_case_result(_result("ring4", 572))  # must not raise


def test_validate_case_result_accepts_ring5_2008():
    validate_case_result(_result("ring5", 2008))  # must not raise


def test_validate_case_result_rejects_wrong_dimension():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 169))


def test_validate_case_result_rejects_spin_other_than_4():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 168, spin=3))


def test_validate_case_result_rejects_unknown_geometry():
    result = _result("triangle", 168)
    object.__setattr__(result.spec, "geometry", "hexagon")
    with pytest.raises(CaseGateFailure):
        validate_case_result(result)


def test_validate_case_result_rejects_q_coverage_gap():
    # Multiplicities sum to exactly 168 (the triangle S4 reference
    # dimension) so the dimension check passes and the q-coverage check
    # is isolated: q_end=0.3 then q_start=0.35 is a genuine gap.
    entries = (
        _entry(0.0, 0.3, 1.0, multiplicity=50),
        _entry(0.35, 0.6, 2.0, multiplicity=59),
        _entry(0.6, 1.0, 3.0, multiplicity=59),
    )
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    result = CaseExecutionResult(
        spec=CaseSpec(geometry="triangle", spin=4), dimension=168, group_count=3, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )
    with pytest.raises(CaseGateFailure):
        validate_case_result(result)


# ---------------------------------------------------------------------------
# CaseExecutionResult itself already refuses a multiplicity/dimension
# mismatch (its own __post_init__) -- confirmed here as a gate-adjacent
# invariant, not re-implemented by gates.py.
# ---------------------------------------------------------------------------


def test_case_execution_result_rejects_multiplicity_sum_mismatch():
    entries = (_entry(0.0, 1.0, 1.0),)
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    with pytest.raises(ValueError):
        CaseExecutionResult(
            spec=CaseSpec(geometry="triangle", spin=4),
            dimension=168,  # does not match sum(multiplicities) == 1
            group_count=1,
            entries=entries,
            m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
            a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
        )


# ---------------------------------------------------------------------------
# validate_campaign_completeness
# ---------------------------------------------------------------------------


def _comparison(geometry: str):
    result_a = _result(geometry, 3, spin=3)
    result_b = _result(geometry, 4, spin=4)
    return compare_spin_pair(result_a, result_b)


def test_validate_campaign_completeness_accepts_exactly_three_cases_and_comparisons():
    results = [_result("triangle", 168), _result("ring4", 572), _result("ring5", 2008)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    validate_campaign_completeness(results, comparisons)  # must not raise


def test_validate_campaign_completeness_rejects_missing_case():
    results = [_result("triangle", 168), _result("ring4", 572)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)


def test_validate_campaign_completeness_rejects_duplicate_geometry():
    results = [_result("triangle", 168), _result("triangle", 168), _result("ring5", 2008)]
    comparisons = [_comparison("triangle"), _comparison("ring4"), _comparison("ring5")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)


def test_validate_campaign_completeness_rejects_missing_comparison():
    results = [_result("triangle", 168), _result("ring4", 572), _result("ring5", 2008)]
    comparisons = [_comparison("triangle"), _comparison("ring4")]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(results, comparisons)
