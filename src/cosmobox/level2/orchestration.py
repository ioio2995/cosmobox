"""Minimal analytic orchestration above adapter.MultipletProfileEntry:
per-case, per-metric regime aggregation and contrasts for all four
metrics, and the inter-S comparison step -- primary taxonomy plus C_X_23/
D_X_23 for M_TT/R_eff only, per the L2-D3 arbitration recorded in
docs/governance/current-task.md ("Arbitrage L2-D3 -- metriques de
controle"); A_QQ/M_QQ remain descriptive-only (LOW/MID/HIGH and the three
Delta_* contrasts), with no taxonomy, no shape descriptor, and no L2-C1
guard ever reachable for them.

Lot L2-D3-ANALYTIC-ORCHESTRATION. Every function here composes
already-accepted primitives (cosmobox.level2.metrics, cosmobox.level2.
profiles) and D2's own output type (cosmobox.level2.adapter.
MultipletProfileEntry) -- no new metric, threshold, or numerical tolerance
is introduced. No real Level2 geometry is diagonalized or consumed here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cosmobox.level2 import metrics, profiles
from cosmobox.level2.adapter import MultipletProfileEntry

PRIMARY_METRICS: tuple[str, ...] = ("M_TT", "R_eff")
CONTROL_METRICS: tuple[str, ...] = ("A_QQ", "M_QQ")
ALL_METRICS: tuple[str, ...] = PRIMARY_METRICS + CONTROL_METRICS

INCOMPLETE_PROFILE_COVERAGE = "INCOMPLETE_PROFILE_COVERAGE"
"""Orchestration-level reason (not a D1 scientific reason string): C_X_23/
D_X_23 require each profile to cover exactly [0,1]
(profiles.cross_profile_correlation/distance's own documented
precondition). This module checks that precondition itself before calling
them, rather than letting their ValueError propagate as an unhandled
exception."""

_METRIC_EXTRACTORS: dict[str, Callable[[MultipletProfileEntry], float | None]] = {
    "M_TT": lambda entry: entry.m_tt,
    "R_eff": lambda entry: entry.r_eff.value,
    "A_QQ": lambda entry: entry.a_qq,
    "M_QQ": lambda entry: entry.m_qq.value,
}


def _has_full_coverage(pieces: Sequence[profiles.ProfilePiece]) -> bool:
    """True iff `pieces`, sorted by start, cover [0,1] contiguously with no
    gap or overlap -- mirrors profiles._validate_full_coverage's exact
    contiguous-coverage check (that D1 function is private and raises
    rather than returning a boolean, so this orchestration layer needs its
    own non-raising query to decide NOT_AVAILABLE before calling)."""
    if not pieces:
        return False
    ordered = sorted(pieces, key=lambda piece: piece.start)
    if ordered[0].start != 0.0 or ordered[-1].end != 1.0:
        return False
    for previous, current in zip(ordered, ordered[1:]):
        if current.start != previous.end:
            return False
    return True


# ---------------------------------------------------------------------------
# 1-3. Per-case, per-metric analysis: GroupValue/ProfilePiece, LOW/MID/HIGH,
# Delta_HL/ML/HM. Identical shape and identical code path for all four
# metrics -- primary or control -- since regime aggregation and contrasts
# carry no metric-specific guard or taxonomy.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseMetricAnalysis:
    """One metric's regime aggregation and contrasts for one case (one
    geometry, one S). Carries no taxonomy and no shape descriptor field --
    those exist only on PrimaryInterSComparison, never here."""

    metric: str
    groups: tuple[profiles.GroupValue, ...]
    pieces: tuple[profiles.ProfilePiece, ...]
    low: profiles.RegimeMean
    mid: profiles.RegimeMean
    high: profiles.RegimeMean
    delta_hl: metrics.Available
    delta_ml: metrics.Available
    delta_hm: metrics.Available

    def __post_init__(self) -> None:
        if self.metric not in ALL_METRICS:
            raise ValueError(f"metric must be one of {ALL_METRICS}, got {self.metric!r}")


def analyze_case_metric(entries: Sequence[MultipletProfileEntry], metric: str) -> CaseMetricAnalysis:
    """Build the LOW/MID/HIGH regime means and the three descriptive
    contrasts for `metric` in {"M_TT", "R_eff", "A_QQ", "M_QQ"}, from one
    case's ordered MultipletProfileEntry sequence. A NOT_AVAILABLE metric
    value on an entry (R_eff or M_QQ) stays None end to end -- never
    imputed -- via profiles.GroupValue/build_profile's own null-aware
    contract."""
    if metric not in _METRIC_EXTRACTORS:
        raise ValueError(f"metric must be one of {sorted(_METRIC_EXTRACTORS)}, got {metric!r}")
    if not entries:
        raise ValueError("entries must not be empty")

    extractor = _METRIC_EXTRACTORS[metric]
    intervals = [profiles.SpectralInterval(entry.q_start, entry.q_end, entry.q_midpoint) for entry in entries]
    values = [extractor(entry) for entry in entries]

    groups = tuple(profiles.GroupValue(interval, value) for interval, value in zip(intervals, values))
    pieces = tuple(profiles.build_profile(intervals, values))

    low = profiles.regime_mean(groups, profiles.LOW)
    mid = profiles.regime_mean(groups, profiles.MID)
    high = profiles.regime_mean(groups, profiles.HIGH)

    return CaseMetricAnalysis(
        metric=metric,
        groups=groups,
        pieces=pieces,
        low=low,
        mid=mid,
        high=high,
        delta_hl=profiles.delta_hl(high, low),
        delta_ml=profiles.delta_ml(mid, low),
        delta_hm=profiles.delta_hm(high, mid),
    )


# ---------------------------------------------------------------------------
# 4-5. Primary inter-S comparison (M_TT, R_eff only): taxonomy + C_X_23/
# D_X_23, gated on exact [0,1] coverage of both profiles.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrimaryInterSComparison:
    """Inter-S comparison for a PRIMARY metric (M_TT or R_eff) only:
    carries the primary taxonomy and the two shape descriptors. `metric`
    is restricted to PRIMARY_METRICS in __post_init__ -- this type can
    never represent a control metric's comparison."""

    metric: str
    delta_hl_s2: metrics.Available
    delta_hl_s3: metrics.Available
    classification: profiles.InterSClassification
    c_x_23: metrics.Available
    d_x_23: metrics.Available

    def __post_init__(self) -> None:
        if self.metric not in PRIMARY_METRICS:
            raise ValueError(f"metric must be one of {PRIMARY_METRICS}, got {self.metric!r}")


def compare_primary_metric_inter_s(
    analysis_s2: CaseMetricAnalysis, analysis_s3: CaseMetricAnalysis, *, metric: str
) -> PrimaryInterSComparison:
    """Taxonomy (via profiles.classify_inter_s, which alone may reach the
    L2-C1 guard through classify_contrast on Delta_HL) plus C_X_23/D_X_23,
    computed only when both profiles cover exactly [0,1]; otherwise both
    are NOT_AVAILABLE (INCOMPLETE_PROFILE_COVERAGE), and
    cross_profile_correlation/distance are never called -- their coverage
    precondition never has a chance to raise."""
    if metric not in PRIMARY_METRICS:
        raise ValueError(f"metric must be one of {PRIMARY_METRICS}, got {metric!r}")
    if analysis_s2.metric != metric or analysis_s3.metric != metric:
        raise ValueError(
            f"analysis_s2/analysis_s3 must both be a {metric!r} CaseMetricAnalysis, "
            f"got {analysis_s2.metric!r} and {analysis_s3.metric!r}"
        )

    classification = profiles.classify_inter_s(analysis_s2.delta_hl, analysis_s3.delta_hl, metric=metric)

    if _has_full_coverage(analysis_s2.pieces) and _has_full_coverage(analysis_s3.pieces):
        c_x_23 = profiles.cross_profile_correlation(analysis_s2.pieces, analysis_s3.pieces)
        d_x_23 = profiles.cross_profile_distance(analysis_s2.pieces, analysis_s3.pieces)
    else:
        c_x_23 = metrics.Available(None, INCOMPLETE_PROFILE_COVERAGE)
        d_x_23 = metrics.Available(None, INCOMPLETE_PROFILE_COVERAGE)

    return PrimaryInterSComparison(
        metric=metric,
        delta_hl_s2=analysis_s2.delta_hl,
        delta_hl_s3=analysis_s3.delta_hl,
        classification=classification,
        c_x_23=c_x_23,
        d_x_23=d_x_23,
    )


# ---------------------------------------------------------------------------
# 6. Control metric inter-S companion (A_QQ, M_QQ only): descriptive only.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ControlMetricAnalysis:
    """Inter-S companion for a CONTROL metric (A_QQ or M_QQ): holds both
    S's per-case CaseMetricAnalysis side by side, and nothing else. This
    is a structural guarantee, not a documentary one: the dataclass has no
    field capable of holding a taxonomy, a C_X_23/D_X_23 value, or an
    L2-C1-guard-derived sign classification -- constructing one with such
    data is a TypeError, not merely an omitted convention."""

    metric: str
    analysis_s2: CaseMetricAnalysis
    analysis_s3: CaseMetricAnalysis

    def __post_init__(self) -> None:
        if self.metric not in CONTROL_METRICS:
            raise ValueError(f"metric must be one of {CONTROL_METRICS}, got {self.metric!r}")
        if self.analysis_s2.metric != self.metric or self.analysis_s3.metric != self.metric:
            raise ValueError(
                f"analysis_s2/analysis_s3 must both be a {self.metric!r} CaseMetricAnalysis, "
                f"got {self.analysis_s2.metric!r} and {self.analysis_s3.metric!r}"
            )


def compare_control_metric_inter_s(
    analysis_s2: CaseMetricAnalysis, analysis_s3: CaseMetricAnalysis, *, metric: str
) -> ControlMetricAnalysis:
    """Pairs both S's already-computed descriptive CaseMetricAnalysis for
    `metric` in {"A_QQ", "M_QQ"}. No C_X_23, no D_X_23, no taxonomy, no
    L2-C1 guard: none of profiles.classify_inter_s, profiles.
    cross_profile_correlation, or profiles.cross_profile_distance is ever
    called here."""
    if metric not in CONTROL_METRICS:
        raise ValueError(f"metric must be one of {CONTROL_METRICS}, got {metric!r}")
    return ControlMetricAnalysis(metric=metric, analysis_s2=analysis_s2, analysis_s3=analysis_s3)
