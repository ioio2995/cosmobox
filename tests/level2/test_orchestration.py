"""Unit tests for cosmobox.level2.orchestration (lot L2-D3-ANALYTIC-ORCHESTRATION).

Every test builds MultipletProfileEntry instances by hand -- no
Level0Report, no adapter.build_case_multiplet_profile, no real
diagonalization, no catalog geometry.
"""

from __future__ import annotations

import dataclasses

import pytest

from cosmobox.level2 import metrics, profiles
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.orchestration import (
    ALL_METRICS,
    CONTROL_METRICS,
    INCOMPLETE_PROFILE_COVERAGE,
    PRIMARY_METRICS,
    CaseMetricAnalysis,
    ControlMetricAnalysis,
    PrimaryInterSComparison,
    analyze_case_metric,
    compare_control_metric_inter_s,
    compare_primary_metric_inter_s,
)


def _entry(
    q_start: float,
    q_end: float,
    *,
    m_tt: float,
    r_eff: metrics.Available,
    a_qq: float,
    m_qq: metrics.Available,
    energy: float = 0.0,
    multiplicity: int = 1,
    epsilon: float = 0.0,
) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=energy,
        multiplicity=multiplicity,
        epsilon=epsilon,
        q_start=q_start,
        q_end=q_end,
        q_midpoint=(q_start + q_end) / 2,
        m_tt=m_tt,
        r_eff=r_eff,
        a_qq=a_qq,
        m_qq=m_qq,
    )


def _synthetic_case_entries(*, r_eff_middle_available: bool = True) -> tuple[MultipletProfileEntry, ...]:
    """Three groups covering [0,1] in exact thirds -- LOW/MID/HIGH each
    fully evaluable by construction. Optionally makes the middle group's
    R_eff/M_QQ NOT_AVAILABLE, to exercise propagation without imputation."""
    r_eff_mid = (
        metrics.Available(0.5, None) if r_eff_middle_available else metrics.Available(None, "ZERO_CTT_MATRIX")
    )
    m_qq_mid = (
        metrics.Available(0.3, None) if r_eff_middle_available else metrics.Available(None, "NO_NUMERIC_RHO_QQ_PAIR")
    )
    return (
        _entry(0.0, 1 / 3, m_tt=1.0, r_eff=metrics.Available(0.4, None), a_qq=0.8, m_qq=metrics.Available(0.2, None)),
        _entry(1 / 3, 2 / 3, m_tt=2.0, r_eff=r_eff_mid, a_qq=0.7, m_qq=m_qq_mid),
        _entry(2 / 3, 1.0, m_tt=3.0, r_eff=metrics.Available(0.6, None), a_qq=0.9, m_qq=metrics.Available(0.4, None)),
    )


def _synthetic_case_entries_s3() -> tuple[MultipletProfileEntry, ...]:
    """A different partition (four groups, quarters instead of thirds) --
    deliberately not aligned with _synthetic_case_entries, to demonstrate
    that no multiplet-by-multiplet matching is needed for the inter-S
    comparison."""
    return (
        _entry(0.0, 0.25, m_tt=1.5, r_eff=metrics.Available(1.0, None), a_qq=0.6, m_qq=metrics.Available(0.1, None)),
        _entry(0.25, 0.5, m_tt=2.5, r_eff=metrics.Available(1.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None)),
        _entry(0.5, 0.75, m_tt=3.5, r_eff=metrics.Available(2.0, None), a_qq=0.4, m_qq=metrics.Available(0.3, None)),
        _entry(0.75, 1.0, m_tt=4.5, r_eff=metrics.Available(2.5, None), a_qq=0.3, m_qq=metrics.Available(0.4, None)),
    )


# ---------------------------------------------------------------------------
# 1. analyze_case_metric -- mapping and metric coverage
# ---------------------------------------------------------------------------


def test_analyze_case_metric_maps_each_metric_correctly():
    entries = _synthetic_case_entries()
    expected_by_metric = {
        "M_TT": [1.0, 2.0, 3.0],
        "R_eff": [0.4, 0.5, 0.6],
        "A_QQ": [0.8, 0.7, 0.9],
        "M_QQ": [0.2, 0.3, 0.4],
    }
    assert set(expected_by_metric) == set(ALL_METRICS)
    for metric, expected_values in expected_by_metric.items():
        analysis = analyze_case_metric(entries, metric)
        assert analysis.metric == metric
        assert [group.value for group in analysis.groups] == pytest.approx(expected_values)


def test_analyze_case_metric_rejects_unknown_metric():
    with pytest.raises(ValueError):
        analyze_case_metric(_synthetic_case_entries(), "C_TT_conn")


def test_analyze_case_metric_rejects_empty_entries():
    with pytest.raises(ValueError):
        analyze_case_metric((), "M_TT")


# ---------------------------------------------------------------------------
# 2. NOT_AVAILABLE propagation without imputation
# ---------------------------------------------------------------------------


def test_analyze_case_metric_propagates_not_available_without_imputation():
    entries = _synthetic_case_entries(r_eff_middle_available=False)

    r_eff_analysis = analyze_case_metric(entries, "R_eff")
    assert [group.value for group in r_eff_analysis.groups] == [0.4, None, 0.6]
    assert len(r_eff_analysis.pieces) == 2  # the unavailable middle group is dropped, never imputed

    m_qq_analysis = analyze_case_metric(entries, "M_QQ")
    assert [group.value for group in m_qq_analysis.groups] == [0.2, None, 0.4]
    assert len(m_qq_analysis.pieces) == 2

    # the very same entries stay fully available/complete for M_TT and A_QQ
    m_tt_analysis = analyze_case_metric(entries, "M_TT")
    assert all(group.value is not None for group in m_tt_analysis.groups)
    assert len(m_tt_analysis.pieces) == 3


# ---------------------------------------------------------------------------
# 3. LOW/MID/HIGH and evaluable_weight_fraction
# ---------------------------------------------------------------------------


def test_analyze_case_metric_regimes_match_direct_regime_mean_call():
    entries = _synthetic_case_entries()
    analysis = analyze_case_metric(entries, "M_TT")

    assert analysis.low == profiles.regime_mean(analysis.groups, profiles.LOW)
    assert analysis.mid == profiles.regime_mean(analysis.groups, profiles.MID)
    assert analysis.high == profiles.regime_mean(analysis.groups, profiles.HIGH)

    assert analysis.low.value == pytest.approx(1.0)
    assert analysis.mid.value == pytest.approx(2.0)
    assert analysis.high.value == pytest.approx(3.0)
    assert analysis.low.evaluable_weight_fraction == pytest.approx(1.0)
    assert analysis.mid.evaluable_weight_fraction == pytest.approx(1.0)
    assert analysis.high.evaluable_weight_fraction == pytest.approx(1.0)


def test_analyze_case_metric_regime_evaluable_weight_fraction_with_gap():
    entries = _synthetic_case_entries(r_eff_middle_available=False)
    analysis = analyze_case_metric(entries, "R_eff")

    assert analysis.mid.value is None
    assert analysis.mid.evaluable_weight_fraction == pytest.approx(0.0)
    assert analysis.low.evaluable_weight_fraction == pytest.approx(1.0)
    assert analysis.high.evaluable_weight_fraction == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 4. Delta_HL/ML/HM for primary AND control metrics
# ---------------------------------------------------------------------------


def test_analyze_case_metric_deltas_match_direct_calls_for_primary_and_control():
    entries = _synthetic_case_entries()
    for metric in ("M_TT", "A_QQ"):
        analysis = analyze_case_metric(entries, metric)
        assert analysis.delta_hl == profiles.delta_hl(analysis.high, analysis.low)
        assert analysis.delta_ml == profiles.delta_ml(analysis.mid, analysis.low)
        assert analysis.delta_hm == profiles.delta_hm(analysis.high, analysis.mid)


# ---------------------------------------------------------------------------
# 5/7/9. Primary inter-S comparison: full coverage, incomplete coverage,
# rejection of control metrics
# ---------------------------------------------------------------------------


def test_compare_primary_metric_inter_s_full_coverage_computes_shape_descriptors():
    analysis_s2 = analyze_case_metric(_synthetic_case_entries(), "M_TT")
    analysis_s3 = analyze_case_metric(_synthetic_case_entries_s3(), "M_TT")

    comparison = compare_primary_metric_inter_s(analysis_s2, analysis_s3, metric="M_TT")

    assert comparison.c_x_23 == profiles.cross_profile_correlation(analysis_s2.pieces, analysis_s3.pieces)
    assert comparison.d_x_23 == profiles.cross_profile_distance(analysis_s2.pieces, analysis_s3.pieces)
    assert comparison.c_x_23.value is not None
    assert comparison.d_x_23.value is not None
    assert comparison.classification == profiles.classify_inter_s(
        analysis_s2.delta_hl, analysis_s3.delta_hl, metric="M_TT"
    )


def test_compare_primary_metric_inter_s_incomplete_coverage_is_not_available_without_exception():
    analysis_s2 = analyze_case_metric(_synthetic_case_entries(r_eff_middle_available=False), "R_eff")
    analysis_s3 = analyze_case_metric(_synthetic_case_entries_s3(), "R_eff")

    comparison = compare_primary_metric_inter_s(analysis_s2, analysis_s3, metric="R_eff")

    assert comparison.c_x_23.value is None
    assert comparison.c_x_23.reason == INCOMPLETE_PROFILE_COVERAGE
    assert comparison.d_x_23.value is None
    assert comparison.d_x_23.reason == INCOMPLETE_PROFILE_COVERAGE
    # the taxonomy does not require full profile coverage -- it is still produced
    assert comparison.classification.taxonomy is not None


def test_compare_primary_metric_inter_s_rejects_control_metric():
    analysis = analyze_case_metric(_synthetic_case_entries(), "A_QQ")
    with pytest.raises(ValueError):
        compare_primary_metric_inter_s(analysis, analysis, metric="A_QQ")


# ---------------------------------------------------------------------------
# 6/8/9. Control metric analysis: descriptive only, structurally incapable
# of a taxonomy/shape descriptor/L2-C1 guard
# ---------------------------------------------------------------------------


def test_control_metric_analysis_has_no_taxonomy_or_shape_descriptor_fields():
    field_names = {field.name for field in dataclasses.fields(ControlMetricAnalysis)}
    assert field_names == {"metric", "analysis_s2", "analysis_s3"}

    analysis = analyze_case_metric(_synthetic_case_entries(), "A_QQ")
    with pytest.raises(TypeError):
        ControlMetricAnalysis(
            metric="A_QQ",
            analysis_s2=analysis,
            analysis_s3=analysis,
            classification="not-a-real-field",  # type: ignore[call-arg]
        )


def test_compare_control_metric_inter_s_rejects_primary_metric():
    analysis = analyze_case_metric(_synthetic_case_entries(), "M_TT")
    with pytest.raises(ValueError):
        compare_control_metric_inter_s(analysis, analysis, metric="M_TT")


def test_l2_c1_guards_never_reachable_for_control_metrics():
    entries_s2 = _synthetic_case_entries()
    entries_s3 = _synthetic_case_entries_s3()
    for metric in CONTROL_METRICS:
        analysis_s2 = analyze_case_metric(entries_s2, metric)
        analysis_s3 = analyze_case_metric(entries_s3, metric)

        control = compare_control_metric_inter_s(analysis_s2, analysis_s3, metric=metric)
        assert control.metric == metric
        assert control.analysis_s2 is analysis_s2
        assert control.analysis_s3 is analysis_s3

        # the underlying D1 guard machinery itself refuses these metric
        # names -- confirming there is no path through which a control
        # metric's comparison could ever reach the L2-C1 guard
        with pytest.raises(ValueError):
            metrics.classify_contrast(0.1, metric=metric)
        with pytest.raises(ValueError):
            profiles.classify_inter_s(analysis_s2.delta_hl, analysis_s3.delta_hl, metric=metric)


# ---------------------------------------------------------------------------
# 10. Synthetic end-to-end case across all four metrics
# ---------------------------------------------------------------------------


def test_end_to_end_synthetic_case_across_all_four_metrics():
    entries_s2 = _synthetic_case_entries()
    entries_s3 = _synthetic_case_entries_s3()

    primary_results: dict[str, PrimaryInterSComparison] = {}
    for metric in PRIMARY_METRICS:
        analysis_s2 = analyze_case_metric(entries_s2, metric)
        analysis_s3 = analyze_case_metric(entries_s3, metric)
        primary_results[metric] = compare_primary_metric_inter_s(analysis_s2, analysis_s3, metric=metric)

    control_results: dict[str, ControlMetricAnalysis] = {}
    for metric in CONTROL_METRICS:
        analysis_s2 = analyze_case_metric(entries_s2, metric)
        analysis_s3 = analyze_case_metric(entries_s3, metric)
        control_results[metric] = compare_control_metric_inter_s(analysis_s2, analysis_s3, metric=metric)

    assert set(primary_results) == set(PRIMARY_METRICS)
    assert set(control_results) == set(CONTROL_METRICS)

    taxonomy_values = {
        profiles.NOT_EVALUABLE,
        profiles.NO_RESOLVED_SPECTRAL_CONTRAST,
        profiles.OPPOSITE_INTER_S_DIRECTION,
        profiles.SAME_INTER_S_DIRECTION,
    }
    for metric, comparison in primary_results.items():
        assert comparison.metric == metric
        assert comparison.classification.taxonomy in taxonomy_values

    for metric, comparison in control_results.items():
        assert comparison.metric == metric
        assert not hasattr(comparison, "classification")
        assert not hasattr(comparison, "c_x_23")
        assert not hasattr(comparison, "d_x_23")
        assert comparison.analysis_s2.delta_hl is not None  # descriptive contrast still present
        assert comparison.analysis_s3.delta_hl is not None
