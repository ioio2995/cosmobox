"""Unit tests for cosmobox.level2.serialization (lot L2-E-CAMPAIGN-INFRASTRUCTURE).

Every GeometryComparison/CaseExecutionResult used here is built from
hand-constructed MultipletProfileEntry tuples -- no real diagonalization,
no catalog geometry.
"""

from __future__ import annotations

import dataclasses

import numpy as np
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
# Fixtures carrying raw source observables (lot L2-E2), for case_result_payload
# ---------------------------------------------------------------------------


def _c_tt_conn(seed: float) -> np.ndarray:
    return np.array([[seed, seed + 0.5], [seed + 0.5, seed + 1.0]])


def _rho_qq(seed: float) -> dict[tuple[int, int], metrics.RhoQQEntry]:
    return {
        (0, 1): metrics.RhoQQEntry(value=0.1 * seed, null_reason=None),
        (1, 0): metrics.RhoQQEntry(value=None, null_reason="ZERO_LOCAL_CHARGE_VARIANCE"),
    }


def _entry_with_raw_observables(
    q_start: float, q_end: float, *, m_tt: float, r_eff, a_qq: float, m_qq, seed: float
) -> MultipletProfileEntry:
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
        c_tt_conn=_c_tt_conn(seed),
        rho_qq=_rho_qq(seed),
    )


def _entries_with_raw_observables(n: int, *, offset: float = 0.0) -> tuple[MultipletProfileEntry, ...]:
    boundaries = [i / n for i in range(n + 1)]
    return tuple(
        _entry_with_raw_observables(
            boundaries[i],
            boundaries[i + 1],
            m_tt=float(i + 1) + offset,
            r_eff=metrics.Available(0.1 * (i + 1) + offset, None),
            a_qq=0.5,
            m_qq=metrics.Available(0.2, None),
            seed=float(i + 1),
        )
        for i in range(n)
    )


def _result_with_raw_observables(geometry: str, spin: int, n: int, *, offset: float = 0.0) -> CaseExecutionResult:
    entries = _entries_with_raw_observables(n, offset=offset)
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


_CASE_RESULT_PROVENANCE = dict(
    campaign_id="level2-energy-regime-v1",
    manifest_fingerprint="a" * 64,
    repository="ioio2995/cosmobox",
    repository_commit="b" * 40,
    branch="research/level2-energy-regime",
    frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    numerical_guard_m_tt=1e-16,
    numerical_guard_r_eff=1e-15,
    numerical_guard_scope="DELTA_HL_ONLY",
)


# ---------------------------------------------------------------------------
# multiplet_entry_payload
# ---------------------------------------------------------------------------


def test_multiplet_entry_payload_includes_full_c_tt_conn_matrix_diagonal_included():
    entry = _entry_with_raw_observables(0.0, 1.0, m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None), seed=3.0)
    payload = serialization.multiplet_entry_payload(entry)
    assert payload["c_tt_conn"] == entry.c_tt_conn.tolist()
    # diagonal explicitly present, not dropped
    assert payload["c_tt_conn"][0][0] == entry.c_tt_conn[0, 0]
    assert payload["c_tt_conn"][1][1] == entry.c_tt_conn[1, 1]


def test_multiplet_entry_payload_includes_all_ordered_rho_qq_pairs_sorted_by_i_then_j():
    entry = _entry_with_raw_observables(0.0, 1.0, m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None), seed=2.0)
    payload = serialization.multiplet_entry_payload(entry)
    pairs = [(item["i"], item["j"]) for item in payload["rho_qq"]]
    assert pairs == sorted(pairs)
    assert set(pairs) == {(0, 1), (1, 0)}


def test_multiplet_entry_payload_preserves_rho_qq_null_reason_without_imputation():
    entry = _entry_with_raw_observables(0.0, 1.0, m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None), seed=4.0)
    payload = serialization.multiplet_entry_payload(entry)
    by_pair = {(item["i"], item["j"]): item for item in payload["rho_qq"]}
    assert by_pair[(0, 1)]["value"] == entry.rho_qq[(0, 1)].value
    assert by_pair[(0, 1)]["null_reason"] is None
    assert by_pair[(1, 0)]["value"] is None
    assert by_pair[(1, 0)]["null_reason"] == "ZERO_LOCAL_CHARGE_VARIANCE"


def test_multiplet_entry_payload_refuses_missing_raw_observables():
    entry = MultipletProfileEntry(
        energy=0.0, multiplicity=1, epsilon=0.0, q_start=0.0, q_end=1.0, q_midpoint=0.5,
        m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
    )
    assert entry.c_tt_conn is None and entry.rho_qq is None
    with pytest.raises(ValueError):
        serialization.multiplet_entry_payload(entry)


def test_multiplet_entry_payload_round_trips_not_available():
    entry = _entry_with_raw_observables(
        0.0, 1.0, m_tt=1.0, r_eff=metrics.Available(None, "ZERO_CTT_MATRIX"), a_qq=0.5,
        m_qq=metrics.Available(None, "NO_EVALUABLE_PAIR"), seed=1.0,
    )
    payload = serialization.multiplet_entry_payload(entry)
    assert payload["r_eff"] == {"value": None, "reason": "ZERO_CTT_MATRIX"}
    assert payload["m_qq"] == {"value": None, "reason": "NO_EVALUABLE_PAIR"}


# ---------------------------------------------------------------------------
# case_result_payload
# ---------------------------------------------------------------------------


def test_case_result_payload_validates_against_schema():
    result = _result_with_raw_observables("triangle", 2, 3)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    serialization.validate_case_result_document(document)  # no exception
    assert document["geometry"] == "triangle"
    assert document["spin"] == 2
    assert document["dimension"] == 3
    assert document["group_count"] == 3
    assert document["full_spectrum"] is True
    assert document["solver_method"] == "dense"
    assert document["window_truncated"] is False
    assert document["partial_subspace_count"] == 0
    assert len(document["multiplet_entries"]) == 3


def test_case_result_payload_carries_frozen_preregistration_commit_and_numerical_guard_reference():
    result = _result_with_raw_observables("ring4", 3, 2)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    assert document["frozen_preregistration_commit"] == _CASE_RESULT_PROVENANCE["frozen_preregistration_commit"]
    assert document["numerical_guard_reference"] == {
        "guard_m_tt": 1e-16, "guard_r_eff": 1e-15, "guard_scope": "DELTA_HL_ONLY",
    }


def test_case_result_payload_carries_repository():
    result = _result_with_raw_observables("triangle", 2, 2)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    assert document["repository"] == "ioio2995/cosmobox"


def test_validate_case_result_document_rejects_wrong_repository():
    result = _result_with_raw_observables("triangle", 2, 2)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    document["repository"] = "someone-else/cosmobox"
    with pytest.raises(ValueError):
        serialization.validate_case_result_document(document)


def test_case_result_payload_refuses_when_any_entry_is_missing_raw_observables():
    result = _result("triangle", 2, 3)  # built without c_tt_conn/rho_qq (pre-L2-E1-style fixture)
    with pytest.raises(ValueError):
        serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)


def test_validate_case_result_document_rejects_broken_document():
    result = _result_with_raw_observables("ring5", 2, 2)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    del document["multiplet_entries"]
    with pytest.raises(ValueError):
        serialization.validate_case_result_document(document)


def test_case_result_payload_regime_analyses_have_no_primary_control_contamination():
    result = _result_with_raw_observables("triangle", 2, 3)
    document = serialization.case_result_payload(result, **_CASE_RESULT_PROVENANCE)
    forbidden = {"taxonomy", "c_x_23", "d_x_23", "direction_s2", "direction_s3"}
    for metric in ("M_TT", "R_eff", "A_QQ", "M_QQ"):
        analysis = document["regime_analyses"][metric]
        assert set(analysis.keys()) == {"low", "mid", "high", "delta_hl", "delta_ml", "delta_hm"}
        assert set(analysis.keys()) & forbidden == set()


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
        repository="ioio2995/cosmobox",
        repository_commit="b" * 40,
        branch="research/level2-energy-regime",
        frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    )
    serialization.validate_campaign_summary_document(document)  # no exception
    assert document["campaign_status"] == "COMPLETE"
    assert document["repository"] == "ioio2995/cosmobox"
    assert {entry["geometry"] for entry in document["geometries"]} == {"triangle", "ring4", "ring5"}


def test_validate_campaign_summary_document_rejects_wrong_repository():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "ring4", "ring5")]
    document = serialization.campaign_summary_payload(
        comparisons,
        campaign_id="level2-energy-regime-v1",
        manifest_fingerprint="a" * 64,
        repository="ioio2995/cosmobox",
        repository_commit="b" * 40,
        branch="research/level2-energy-regime",
        frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    )
    document["repository"] = "someone-else/cosmobox"
    with pytest.raises(ValueError):
        serialization.validate_campaign_summary_document(document)


def test_campaign_summary_payload_rejects_missing_geometry():
    comparisons = [_geometry_comparison(geometry) for geometry in ("triangle", "ring4")]
    with pytest.raises(ValueError):
        serialization.campaign_summary_payload(
            comparisons,
            campaign_id="c",
            manifest_fingerprint="a" * 64,
            repository="ioio2995/cosmobox",
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
            repository="ioio2995/cosmobox",
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
        repository="ioio2995/cosmobox",
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
