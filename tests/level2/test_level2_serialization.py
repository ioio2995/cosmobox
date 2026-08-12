"""Unit tests for cosmobox.level2.serialization (lot L2-E-CAMPAIGN-INFRASTRUCTURE).

Every GeometryComparison/CaseExecutionResult used here is built from
hand-constructed MultipletProfileEntry tuples -- no real diagonalization,
no catalog geometry.
"""

from __future__ import annotations

import dataclasses

import pytest

from cosmobox.level2 import metrics, orchestration, serialization
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import CaseExecutionResult, CaseSpec, GeometryComparison, compare_geometry


def _entry(q_start: float, q_end: float, *, m_tt: float, r_eff, a_qq: float, m_qq) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0,
        multiplicity=1,
        epsilon=0.0,
        q_start=q_start,
        q_end=q_end,
        q_midpoint=(q_start + q_end) / 2,
        m_tt=m_tt,
        r_eff=r_eff,
        a_qq=a_qq,
        m_qq=m_qq,
    )


def _entries(n: int, *, offset: float = 0.0) -> tuple[MultipletProfileEntry, ...]:
    boundaries = [i / n for i in range(n + 1)]
    return tuple(
        _entry(
            boundaries[i],
            boundaries[i + 1],
            m_tt=float(i + 1) + offset,
            r_eff=metrics.Available(0.1 * (i + 1) + offset, None),
            a_qq=0.5,
            m_qq=metrics.Available(0.2, None),
        )
        for i in range(n)
    )


def _result(geometry: str, spin: int, n: int, *, offset: float = 0.0) -> CaseExecutionResult:
    entries = _entries(n, offset=offset)
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


def _geometry_comparison(geometry: str) -> GeometryComparison:
    return compare_geometry(_result(geometry, 2, 3), _result(geometry, 3, 4, offset=1.0))


# ---------------------------------------------------------------------------
# Primitive payloads
# ---------------------------------------------------------------------------


def test_available_payload_round_trip_numeric():
    payload = serialization.available_payload(metrics.Available(0.5, None))
    assert payload == {"value": 0.5, "reason": None}


def test_available_payload_round_trip_not_available():
    payload = serialization.available_payload(metrics.Available(None, "ZERO_CTT_MATRIX"))
    assert payload == {"value": None, "reason": "ZERO_CTT_MATRIX"}


def test_regime_mean_payload_preserves_evaluable_weight_fraction():
    comparison = _geometry_comparison("triangle")
    low = comparison.result_s2.m_tt_analysis.low
    payload = serialization.regime_mean_payload(low)
    assert payload["value"] == low.value
    assert payload["reason"] == low.reason
    assert payload["evaluable_weight_fraction"] == low.evaluable_weight_fraction


# ---------------------------------------------------------------------------
# Primary vs control JSON separation
# ---------------------------------------------------------------------------


def test_primary_inter_s_comparison_payload_has_taxonomy_and_shape_descriptors():
    comparison = _geometry_comparison("triangle")
    payload = serialization.primary_inter_s_comparison_payload(comparison.m_tt)
    assert payload["metric"] == "M_TT"
    assert payload["taxonomy"] == comparison.m_tt.classification.taxonomy
    assert "c_x_23" in payload
    assert "d_x_23" in payload


def test_control_metric_analysis_payload_has_no_taxonomy_or_shape_descriptor():
    comparison = _geometry_comparison("triangle")
    payload = serialization.control_metric_analysis_payload(comparison.a_qq)
    assert payload["metric"] == "A_QQ"
    forbidden = {"taxonomy", "c_x_23", "d_x_23", "direction_s2", "direction_s3"}
    assert set(payload.keys()) & forbidden == set()
    assert set(payload.keys()) == {
        "metric", "delta_hl_s2", "delta_ml_s2", "delta_hm_s2", "delta_hl_s3", "delta_ml_s3", "delta_hm_s3"
    }


# ---------------------------------------------------------------------------
# campaign_summary_payload -- shape, validation, and completeness
# ---------------------------------------------------------------------------


def test_campaign_summary_payload_validates_against_schema():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "ring4", "ring5")]
    document = serialization.campaign_summary_payload(
        comparisons,
        campaign_id="level2-energy-regime-v1",
        manifest_fingerprint="a" * 64,
        repository_commit="b" * 40,
        branch="research/level2-energy-regime",
        frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    )
    serialization.validate_campaign_summary_document(document)  # no exception
    assert document["campaign_status"] == "COMPLETE"
    assert {entry["geometry"] for entry in document["geometries"]} == {"triangle", "ring4", "ring5"}


def test_campaign_summary_payload_rejects_missing_geometry():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "ring4")]
    with pytest.raises(ValueError):
        serialization.campaign_summary_payload(
            comparisons,
            campaign_id="c",
            manifest_fingerprint="a" * 64,
            repository_commit="b" * 40,
            branch="research/level2-energy-regime",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )


def test_campaign_summary_payload_rejects_duplicate_geometry():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "triangle", "ring5")]
    with pytest.raises(ValueError):
        serialization.campaign_summary_payload(
            comparisons,
            campaign_id="c",
            manifest_fingerprint="a" * 64,
            repository_commit="b" * 40,
            branch="research/level2-energy-regime",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )


def test_validate_campaign_summary_document_rejects_incomplete_status():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "ring4", "ring5")]
    document = serialization.campaign_summary_payload(
        comparisons,
        campaign_id="c",
        manifest_fingerprint="a" * 64,
        repository_commit="b" * 40,
        branch="research/level2-energy-regime",
        frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    )
    document["campaign_status"] = "INCOMPLETE"
    with pytest.raises(ValueError):
        serialization.validate_campaign_summary_document(document)


def test_geometry_comparison_payload_matches_direct_calls():
    comparison = _geometry_comparison("ring4")
    payload = serialization.geometry_comparison_payload(comparison)
    assert payload["m_tt"] == serialization.primary_inter_s_comparison_payload(comparison.m_tt)
    assert payload["a_qq"] == serialization.control_metric_analysis_payload(comparison.a_qq)
