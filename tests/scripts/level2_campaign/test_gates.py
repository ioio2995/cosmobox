"""Unit tests for scripts.level2_campaign.gates (lot
L2-E-CAMPAIGN-INFRASTRUCTURE). L2_A1_PREFLIGHT_REFERENCE is monkeypatched
to a small synthetic table -- these tests exercise gate LOGIC, never the
real six-case numbers (already verified for real by
scripts/level2_preflight, L2-D4-REAL-PREFLIGHT).
"""

from __future__ import annotations

import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import CaseExecutionResult, CaseSpec, compare_geometry
import scripts.level2_campaign.gates as gates_module
from scripts.level2_campaign.gates import (
    CampaignGateFailure,
    CaseGateFailure,
    validate_campaign_completeness,
    validate_case_result,
)


def _entry(q_start: float, q_end: float) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0,
        multiplicity=1,
        epsilon=0.0,
        q_start=q_start,
        q_end=q_end,
        q_midpoint=(q_start + q_end) / 2,
        m_tt=1.0,
        r_eff=metrics.Available(0.5, None),
        a_qq=0.5,
        m_qq=metrics.Available(0.2, None),
    )


def _result(geometry: str, spin: int, n: int, *, with_gap: bool = False) -> CaseExecutionResult:
    boundaries = [i / n for i in range(n + 1)]
    entries = tuple(_entry(boundaries[i], boundaries[i + 1]) for i in range(n))
    if with_gap:
        # shrink the last piece so q coverage stops short of 1.0
        shrunk_start = entries[-1].q_start
        shrunk_end = entries[-1].q_end - 0.01
        broken_last = MultipletProfileEntry(
            energy=0.0, multiplicity=1, epsilon=0.0,
            q_start=shrunk_start, q_end=shrunk_end,
            q_midpoint=(shrunk_start + shrunk_end) / 2,
            m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
        )
        entries = entries[:-1] + (broken_last,)
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin),
        dimension=n,
        group_count=n,
        entries=entries,
        m_tt_analysis=analyses["M_TT"],
        r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"],
        m_qq_analysis=analyses["M_QQ"],
    )


@pytest.fixture(autouse=True)
def _synthetic_reference(monkeypatch):
    reference = {("triangle", 2): (3, 3), ("triangle", 3): (4, 4)}
    monkeypatch.setattr(gates_module, "L2_A1_PREFLIGHT_REFERENCE", reference)
    return reference


# ---------------------------------------------------------------------------
# validate_case_result
# ---------------------------------------------------------------------------


def test_validate_case_result_passes_when_matching_reference():
    validate_case_result(_result("triangle", 2, 3))  # no exception


def test_validate_case_result_rejects_dimension_mismatch():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 2, 5))


def test_validate_case_result_rejects_case_outside_reference_table():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("ring4", 2, 3))


def test_validate_case_result_rejects_incomplete_q_coverage():
    with pytest.raises(CaseGateFailure):
        validate_case_result(_result("triangle", 2, 3, with_gap=True))


# ---------------------------------------------------------------------------
# validate_campaign_completeness
# ---------------------------------------------------------------------------


def test_validate_campaign_completeness_passes_for_six_cases_and_three_geometries(monkeypatch):
    reference = {
        ("triangle", 2): (3, 3), ("triangle", 3): (3, 3),
        ("ring4", 2): (3, 3), ("ring4", 3): (3, 3),
        ("ring5", 2): (3, 3), ("ring5", 3): (3, 3),
    }
    monkeypatch.setattr(gates_module, "L2_A1_PREFLIGHT_REFERENCE", reference)
    case_results = [_result(geometry, spin, 3) for geometry, spin in reference]
    comparisons = [
        compare_geometry(_result(geometry, 2, 3), _result(geometry, 3, 3)) for geometry in ("triangle", "ring4", "ring5")
    ]
    validate_campaign_completeness(case_results, comparisons)  # no exception


def test_validate_campaign_completeness_rejects_missing_case(monkeypatch):
    reference = {
        ("triangle", 2): (3, 3), ("triangle", 3): (3, 3),
        ("ring4", 2): (3, 3), ("ring4", 3): (3, 3),
        ("ring5", 2): (3, 3), ("ring5", 3): (3, 3),
    }
    monkeypatch.setattr(gates_module, "L2_A1_PREFLIGHT_REFERENCE", reference)
    case_results = [_result(geometry, spin, 3) for geometry, spin in list(reference)[:5]]
    comparisons = [
        compare_geometry(_result(geometry, 2, 3), _result(geometry, 3, 3)) for geometry in ("triangle", "ring4", "ring5")
    ]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(case_results, comparisons)


def test_validate_campaign_completeness_rejects_duplicate_case(monkeypatch):
    reference = {
        ("triangle", 2): (3, 3), ("triangle", 3): (3, 3),
        ("ring4", 2): (3, 3), ("ring4", 3): (3, 3),
        ("ring5", 2): (3, 3), ("ring5", 3): (3, 3),
    }
    monkeypatch.setattr(gates_module, "L2_A1_PREFLIGHT_REFERENCE", reference)
    case_results = [_result(geometry, spin, 3) for geometry, spin in reference]
    case_results[-1] = case_results[0]
    comparisons = [
        compare_geometry(_result(geometry, 2, 3), _result(geometry, 3, 3)) for geometry in ("triangle", "ring4", "ring5")
    ]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(case_results, comparisons)


def test_validate_campaign_completeness_rejects_missing_geometry_comparison(monkeypatch):
    reference = {
        ("triangle", 2): (3, 3), ("triangle", 3): (3, 3),
        ("ring4", 2): (3, 3), ("ring4", 3): (3, 3),
        ("ring5", 2): (3, 3), ("ring5", 3): (3, 3),
    }
    monkeypatch.setattr(gates_module, "L2_A1_PREFLIGHT_REFERENCE", reference)
    case_results = [_result(geometry, spin, 3) for geometry, spin in reference]
    comparisons = [
        compare_geometry(_result(geometry, 2, 3), _result(geometry, 3, 3)) for geometry in ("triangle", "ring4")
    ]
    with pytest.raises(CampaignGateFailure):
        validate_campaign_completeness(case_results, comparisons)
