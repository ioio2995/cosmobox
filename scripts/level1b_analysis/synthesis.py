"""Deterministic, descriptive synthesis of already-produced inter-S
results (1B-9c/1B-9d/1B-9e, docs/governance/current-task.md). Level1B
lot 1B-9f.

build_inter_s_synthesis_report reorganizes and counts objects already
produced by matching.py (via inter_s.py), 1B-9d (comparisons.py), and
1B-9e (robustness_evaluation.py) into four independent, non-destructive
views (global, per-couple, per-matched-group, per-observable). It never
calls match_spectral_group, compute_gamma_o, or evaluate_robustness, and
never recomputes difference/amplitude/gamma_O/threshold/verdict/
null_reason from source values when a RobustnessResult already exists --
RobustnessResult remains the sole source of truth for all of those; this
module only counts, groups, and computes ordinary descriptive statistics
(count/min/max/median, Python's own statistics.median, over already-
existing numeric fields) on top of it.

This module produces no verdict of any kind beyond passing through the
ones evaluate_robustness already produced. It never fuses per-comparison
verdicts into a new aggregate verdict, never declares a geometry,
distance, metric, curvature, or causality, never extrapolates across S,
and never averages across different observables or different spectral
groups. "684/684 robust" is reported as a plain count here -- this
module draws no conclusion from it.

Unit of synthesis: the inter-S matched spectral group (one
InterSGroupMatch, identified by its SpectralGroupMatchKey pair, never by
representative_energy, rank, or file order). The source of truth for
which groups EXIST and in what ORDER is matching_report.matches itself,
never comparison_report.comparisons: a group produces an
InterSGroupSynthesis whenever its InterSGroupMatch carries a concrete
low_group (exact_label_match, per InterSGroupMatch.__post_init__'s own
already-accepted invariant that exact_label_match holds if and only if
low_group is not None -- verified directly in inter_s.py before relying
on it here), independently of whether the closed 1B-9d observable list
produced any comparison for it. A match without a concrete low_group is
not a spectral group pairing at all and is never turned into a group
synthesis, though it stays counted in matching_count. Comparison ->
source match association (used only to bucket each comparison into its
already-existing group, never to decide whether that group exists)
reuses robustness_evaluation.py's own private object-identity index
(_index_matches_by_group_identity/_find_source_match), imported
directly rather than reimplemented, for exactly the same reason 1B-9e
itself cannot use dataclass value-equality: IndexedSpectralGroup/
CampaignCaseSpec carry unhashable numpy.ndarray fields whose == returns
an array, not a bool. Each InterSGroupSynthesis independently re-checks
that every evaluation/unevaluable comparison it carries genuinely
belongs to ITS OWN exact spectral group pairing (match_key and index
equality against evaluation.match/comparison.high_group/low_group,
never energy or proximity) -- a same-couple, different-group evaluation
can never be silently attributed to the wrong group.

Ordering: couples/groups follow the order of matching_report.matches
itself (restricted to entries with a concrete low_group); observables
follow ROBUSTNESS_EVALUATION_ORDER, the same fixed 4-tuple 1B-9e already
defines. Nothing is ever sorted by difference, gamma_O, amplitude,
verdict, or representative_energy -- those orderings are used only
internally, transiently, to compute a median, never to decide output
order.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from cosmobox.level1.matching import EXACT_LABEL_MATCH, SpectralGroupMatchKey

from .comparisons import InterSObservableComparisonReport, ScalarObservableComparison
from .inter_s import InterSMatchingReport
from .robustness_evaluation import (
    EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS,
    InterSRobustnessEvaluation,
    InterSRobustnessReport,
    _find_source_match,
    _index_matches_by_group_identity,
)

ROBUSTNESS_EVALUATION_ORDER = EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS
"""The fixed, non-scientific display order this module always uses for
the per-observable breakdown -- the exact same 4-tuple 1B-9e already
defines (gamma_O, rho_QQ, C_TT_conn, flavor_singular_value_ratio),
restated here under its own name since this module's own ordering
guarantee is about display, not about robustness_evaluation.py's
internal eligibility check."""


class InterSSynthesisError(RuntimeError):
    """Raised for a structural inconsistency in this lot's own pipeline:
    mismatched provenance across the three source reports, or a
    comparison found in neither evaluations nor unevaluable_comparisons
    of the given robustness_report (implies comparison_report/
    robustness_report were not built from the same pipeline run)."""


def _require_tuple(name: str, value: object) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a tuple, got {type(value)} -- never silently converted")


def _require_elements(name: str, value: tuple, element_type: type | tuple[type, ...]) -> None:
    for index, item in enumerate(value):
        if not isinstance(item, element_type):
            raise ValueError(f"{name}[{index}] must be an instance of {element_type}, got {type(item)}")


# ---------------------------------------------------------------------------
# Small, reusable statistics/count types.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DescriptiveStatistics:
    """count == 0 iff minimum/maximum/median are all None. statistics.
    median follows Python's own stdlib definition, unmodified: the
    middle value for an odd count, the arithmetic mean of the two middle
    values for an even count -- exactly the rule this lot's mandate
    specifies, reused rather than reimplemented."""

    count: int
    minimum: float | None
    maximum: float | None
    median: float | None

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 0:
            raise ValueError(f"count must be a non-negative int, got {self.count!r}")
        if self.count == 0:
            if self.minimum is not None or self.maximum is not None or self.median is not None:
                raise ValueError("minimum/maximum/median must all be None when count == 0")
            return
        if self.minimum is None or self.maximum is None or self.median is None:
            raise ValueError("minimum/maximum/median must all be set when count > 0")
        for name, value in (("minimum", self.minimum), ("maximum", self.maximum), ("median", self.median)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not (value == value and abs(value) != float("inf")):
                raise ValueError(f"{name} must be a finite real number, got {value!r}")
        if self.minimum > self.maximum:
            raise ValueError(f"minimum ({self.minimum}) must be <= maximum ({self.maximum})")
        if not (self.minimum <= self.median <= self.maximum):
            raise ValueError(f"median ({self.median}) must lie within [minimum, maximum] = [{self.minimum}, {self.maximum}]")


def _descriptive_statistics(values: tuple[float, ...]) -> DescriptiveStatistics:
    if not values:
        return DescriptiveStatistics(count=0, minimum=None, maximum=None, median=None)
    return DescriptiveStatistics(count=len(values), minimum=min(values), maximum=max(values), median=statistics.median(values))


@dataclass(frozen=True, slots=True)
class GammaOStatistics:
    """Every RobustnessResult evaluate_robustness produces -- regardless
    of which observable_kind was being compared -- carries its own
    gamma_o (the normalized difference ratio of the two values actually
    compared for THAT evaluation), possibly null via the normalization
    floor. defined_count + null_count == the observable's own
    evaluation_count; `values` is the descriptive statistics of the
    defined (non-null) gamma_o.value entries only."""

    defined_count: int
    null_count: int
    values: DescriptiveStatistics

    def __post_init__(self) -> None:
        for name, value in (("defined_count", self.defined_count), ("null_count", self.null_count)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if not isinstance(self.values, DescriptiveStatistics):
            raise ValueError(f"values must be a DescriptiveStatistics, got {type(self.values)}")
        if self.values.count != self.defined_count:
            raise ValueError(f"values.count ({self.values.count}) must equal defined_count ({self.defined_count})")


@dataclass(frozen=True, slots=True)
class VerdictCounts:
    robust: int
    non_robust: int
    indeterminate: int

    def __post_init__(self) -> None:
        for name, value in (("robust", self.robust), ("non_robust", self.non_robust), ("indeterminate", self.indeterminate)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")

    @property
    def total(self) -> int:
        return self.robust + self.non_robust + self.indeterminate


def _count_verdicts(evaluations: tuple[InterSRobustnessEvaluation, ...]) -> VerdictCounts:
    robust = sum(1 for e in evaluations if e.result.verdict == "robust")
    non_robust = sum(1 for e in evaluations if e.result.verdict == "non_robust")
    indeterminate = sum(1 for e in evaluations if e.result.verdict == "indeterminate")
    return VerdictCounts(robust=robust, non_robust=non_robust, indeterminate=indeterminate)


@dataclass(frozen=True, slots=True)
class ObservableEvaluationCounts:
    """A lightweight per-observable count breakdown (no statistics) used
    at the per-group/per-couple level; the full statistics-carrying
    breakdown (InterSObservableSynthesis) is only ever produced once,
    globally."""

    observable_kind: str
    evaluation_count: int
    verdicts: VerdictCounts

    def __post_init__(self) -> None:
        if self.observable_kind not in EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS:
            raise ValueError(f"observable_kind must be one of {EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS}, got {self.observable_kind!r}")
        if isinstance(self.evaluation_count, bool) or not isinstance(self.evaluation_count, int) or self.evaluation_count < 0:
            raise ValueError(f"evaluation_count must be a non-negative int, got {self.evaluation_count!r}")
        if not isinstance(self.verdicts, VerdictCounts):
            raise ValueError(f"verdicts must be a VerdictCounts, got {type(self.verdicts)}")
        if self.verdicts.total != self.evaluation_count:
            raise ValueError(f"verdicts.total ({self.verdicts.total}) must equal evaluation_count ({self.evaluation_count})")


def _build_observable_counts(evaluations: tuple[InterSRobustnessEvaluation, ...]) -> tuple[ObservableEvaluationCounts, ...]:
    counts = []
    for kind in ROBUSTNESS_EVALUATION_ORDER:
        kind_evaluations = tuple(e for e in evaluations if e.observable_kind == kind)
        counts.append(ObservableEvaluationCounts(observable_kind=kind, evaluation_count=len(kind_evaluations), verdicts=_count_verdicts(kind_evaluations)))
    return tuple(counts)


# ---------------------------------------------------------------------------
# Per-matched-group and per-couple synthesis.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InterSGroupSynthesis:
    """One inter-S matched spectral group -- identified by its
    SpectralGroupMatchKey pair (never by representative_energy, rank, or
    file order). Exists for every matching_report.matches entry that
    carries a concrete low_group (exact_label_match, per InterSGroupMatch
    's own already-accepted invariant), independently of whether the
    closed 1B-9d observable list produced any comparison for it -- an
    exact spectral group pairing with zero comparisons is a legitimate,
    empty group, never an error. evaluations/unevaluable_comparisons are
    the exact source objects belonging to THIS group (never copies, and
    never an object belonging to a different group of the same couple --
    checked below via match_key/index, never energy or proximity): the
    synthesis never replaces the elementary data, it only reorganizes
    references to it. spectral_window_group_index is carried purely as
    intra-case display/diagnostic metadata, never as part of the group's
    identity."""

    high_case_id: str
    low_case_id: str
    high_spin: int
    low_spin: int
    high_group_match_key: SpectralGroupMatchKey
    low_group_match_key: SpectralGroupMatchKey
    high_group_index: int
    low_group_index: int
    match_status: str
    evaluations: tuple[InterSRobustnessEvaluation, ...]
    unevaluable_comparisons: tuple[ScalarObservableComparison, ...]
    observable_counts: tuple[ObservableEvaluationCounts, ...]
    verdicts: VerdictCounts

    def __post_init__(self) -> None:
        if self.high_spin <= self.low_spin:
            raise ValueError(f"high_spin ({self.high_spin}) must be > low_spin ({self.low_spin})")
        if not isinstance(self.high_group_match_key, SpectralGroupMatchKey):
            raise ValueError(f"high_group_match_key must be a SpectralGroupMatchKey, got {type(self.high_group_match_key)}")
        if not isinstance(self.low_group_match_key, SpectralGroupMatchKey):
            raise ValueError(f"low_group_match_key must be a SpectralGroupMatchKey, got {type(self.low_group_match_key)}")

        _require_tuple("evaluations", self.evaluations)
        _require_elements("evaluations", self.evaluations, InterSRobustnessEvaluation)
        _require_tuple("unevaluable_comparisons", self.unevaluable_comparisons)
        _require_elements("unevaluable_comparisons", self.unevaluable_comparisons, ScalarObservableComparison)

        for evaluation in self.evaluations:
            match = evaluation.match
            if match.high_case_id != self.high_case_id or match.low_case_id != self.low_case_id:
                raise ValueError("an evaluation's match does not belong to (high_case_id, low_case_id)")
            if match.high_group.match_key != self.high_group_match_key or match.low_group.match_key != self.low_group_match_key:
                raise ValueError("an evaluation's match does not belong to this exact spectral group pairing (match_key mismatch)")
            if match.high_group.spectral_window_group_index != self.high_group_index or match.low_group.spectral_window_group_index != self.low_group_index:
                raise ValueError("an evaluation's match group indices are inconsistent with this group synthesis")

        for comparison in self.unevaluable_comparisons:
            if comparison.high_case_id != self.high_case_id or comparison.low_case_id != self.low_case_id:
                raise ValueError("an unevaluable comparison does not belong to (high_case_id, low_case_id)")
            if comparison.high_group.match_key != self.high_group_match_key or comparison.low_group.match_key != self.low_group_match_key:
                raise ValueError("an unevaluable comparison does not belong to this exact spectral group pairing (match_key mismatch)")
            if comparison.high_group.spectral_window_group_index != self.high_group_index or comparison.low_group.spectral_window_group_index != self.low_group_index:
                raise ValueError("an unevaluable comparison's group indices are inconsistent with this group synthesis")

        _require_tuple("observable_counts", self.observable_counts)
        _require_elements("observable_counts", self.observable_counts, ObservableEvaluationCounts)
        if tuple(count.observable_kind for count in self.observable_counts) != ROBUSTNESS_EVALUATION_ORDER:
            raise ValueError(f"observable_counts must contain exactly the four kinds in {ROBUSTNESS_EVALUATION_ORDER}")
        if not isinstance(self.verdicts, VerdictCounts):
            raise ValueError(f"verdicts must be a VerdictCounts, got {type(self.verdicts)}")
        if self.verdicts.total != len(self.evaluations):
            raise ValueError(f"verdicts.total ({self.verdicts.total}) must equal len(evaluations) ({len(self.evaluations)})")
        if sum(count.evaluation_count for count in self.observable_counts) != len(self.evaluations):
            raise ValueError("sum of observable_counts.evaluation_count must equal len(evaluations)")


@dataclass(frozen=True, slots=True)
class InterSCoupleSynthesis:
    """One (high_case_id, low_case_id) couple. groups preserves the
    order its matched spectral groups first appeared in; evaluation_
    count/unevaluable_count/observable_counts/verdicts are derived
    exclusively from `groups` (checked in __post_init__), never an
    independent count -- groups remains the single source of truth."""

    high_case_id: str
    low_case_id: str
    high_spin: int
    low_spin: int
    groups: tuple[InterSGroupSynthesis, ...]
    evaluation_count: int
    unevaluable_count: int
    observable_counts: tuple[ObservableEvaluationCounts, ...]
    verdicts: VerdictCounts

    def __post_init__(self) -> None:
        if self.high_spin <= self.low_spin:
            raise ValueError(f"high_spin ({self.high_spin}) must be > low_spin ({self.low_spin})")
        _require_tuple("groups", self.groups)
        _require_elements("groups", self.groups, InterSGroupSynthesis)
        if not self.groups:
            raise ValueError(f"couple ({self.high_case_id!r} -> {self.low_case_id!r}) has no groups")
        for group in self.groups:
            if group.high_case_id != self.high_case_id or group.low_case_id != self.low_case_id:
                raise ValueError("a group in this couple does not belong to (high_case_id, low_case_id)")

        expected_evaluation_count = sum(len(g.evaluations) for g in self.groups)
        expected_unevaluable_count = sum(len(g.unevaluable_comparisons) for g in self.groups)
        if self.evaluation_count != expected_evaluation_count:
            raise ValueError(f"evaluation_count ({self.evaluation_count}) must equal the sum over groups ({expected_evaluation_count})")
        if self.unevaluable_count != expected_unevaluable_count:
            raise ValueError(f"unevaluable_count ({self.unevaluable_count}) must equal the sum over groups ({expected_unevaluable_count})")

        _require_tuple("observable_counts", self.observable_counts)
        _require_elements("observable_counts", self.observable_counts, ObservableEvaluationCounts)
        if tuple(count.observable_kind for count in self.observable_counts) != ROBUSTNESS_EVALUATION_ORDER:
            raise ValueError(f"observable_counts must contain exactly the four kinds in {ROBUSTNESS_EVALUATION_ORDER}")
        if not isinstance(self.verdicts, VerdictCounts):
            raise ValueError(f"verdicts must be a VerdictCounts, got {type(self.verdicts)}")
        if self.verdicts.total != self.evaluation_count:
            raise ValueError(f"verdicts.total ({self.verdicts.total}) must equal evaluation_count ({self.evaluation_count})")


@dataclass(frozen=True, slots=True)
class InterSObservableSynthesis:
    """One of the four evaluated observable_kinds, globally across the
    whole report. difference/amplitude/gamma_o statistics are computed
    purely by reading RobustnessResult.difference/amplitude/gamma_o off
    each already-existing evaluation -- never recomputed."""

    observable_kind: str
    evaluation_count: int
    unevaluable_count: int
    verdicts: VerdictCounts
    difference: DescriptiveStatistics
    amplitude: DescriptiveStatistics
    gamma_o: GammaOStatistics

    def __post_init__(self) -> None:
        if self.observable_kind not in EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS:
            raise ValueError(f"observable_kind must be one of {EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS}, got {self.observable_kind!r}")
        for name, value in (("evaluation_count", self.evaluation_count), ("unevaluable_count", self.unevaluable_count)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if not isinstance(self.verdicts, VerdictCounts):
            raise ValueError(f"verdicts must be a VerdictCounts, got {type(self.verdicts)}")
        if self.verdicts.total != self.evaluation_count:
            raise ValueError(f"verdicts.total ({self.verdicts.total}) must equal evaluation_count ({self.evaluation_count})")
        if not isinstance(self.difference, DescriptiveStatistics):
            raise ValueError(f"difference must be a DescriptiveStatistics, got {type(self.difference)}")
        if not isinstance(self.amplitude, DescriptiveStatistics):
            raise ValueError(f"amplitude must be a DescriptiveStatistics, got {type(self.amplitude)}")
        if not isinstance(self.gamma_o, GammaOStatistics):
            raise ValueError(f"gamma_o must be a GammaOStatistics, got {type(self.gamma_o)}")


def _build_observable_synthesis(observable_kind: str, robustness_report: InterSRobustnessReport) -> InterSObservableSynthesis:
    evaluations = tuple(e for e in robustness_report.evaluations if e.observable_kind == observable_kind)
    unevaluable = tuple(
        c
        for c in robustness_report.unevaluable_comparisons
        if isinstance(c, ScalarObservableComparison) and c.observable_kind == observable_kind
    )

    differences = tuple(e.result.difference for e in evaluations if e.result.difference is not None)
    amplitudes = tuple(e.result.amplitude for e in evaluations if e.result.amplitude is not None)
    gamma_defined = tuple(e.result.gamma_o.value for e in evaluations if e.result.gamma_o is not None and e.result.gamma_o.value is not None)
    gamma_null_count = sum(1 for e in evaluations if e.result.gamma_o is not None and e.result.gamma_o.value is None)

    return InterSObservableSynthesis(
        observable_kind=observable_kind,
        evaluation_count=len(evaluations),
        unevaluable_count=len(unevaluable),
        verdicts=_count_verdicts(evaluations),
        difference=_descriptive_statistics(differences),
        amplitude=_descriptive_statistics(amplitudes),
        gamma_o=GammaOStatistics(defined_count=len(gamma_defined), null_count=gamma_null_count, values=_descriptive_statistics(gamma_defined)),
    )


# ---------------------------------------------------------------------------
# Global report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InterSSynthesisReport:
    """Provenance is that of the SOURCE campaign, copied unchanged from
    the three input reports (already required to agree exactly) -- never
    the analysis code's own commit. couples/groups/observables are each
    independently frozen tuples; no field here is ever computed by
    calling match_spectral_group/compute_gamma_o/evaluate_robustness --
    every number is either a direct count or an ordinary descriptive
    statistic over RobustnessResult fields that already existed."""

    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str

    matching_count: int
    exact_match_count: int
    source_comparison_count: int
    evaluated_count: int
    unevaluable_count: int
    verdicts: VerdictCounts

    couples: tuple[InterSCoupleSynthesis, ...]
    groups: tuple[InterSGroupSynthesis, ...]
    observables: tuple[InterSObservableSynthesis, ...]

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.repository_commit:
            raise ValueError("repository_commit must be non-empty")

        for name, value in (
            ("matching_count", self.matching_count),
            ("exact_match_count", self.exact_match_count),
            ("source_comparison_count", self.source_comparison_count),
            ("evaluated_count", self.evaluated_count),
            ("unevaluable_count", self.unevaluable_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if self.exact_match_count > self.matching_count:
            raise ValueError(f"exact_match_count ({self.exact_match_count}) must be <= matching_count ({self.matching_count})")
        if self.evaluated_count + self.unevaluable_count != self.source_comparison_count:
            raise ValueError(
                f"evaluated_count + unevaluable_count ({self.evaluated_count + self.unevaluable_count}) must equal "
                f"source_comparison_count ({self.source_comparison_count})"
            )
        if not isinstance(self.verdicts, VerdictCounts):
            raise ValueError(f"verdicts must be a VerdictCounts, got {type(self.verdicts)}")
        if self.verdicts.total != self.evaluated_count:
            raise ValueError(f"verdicts.total ({self.verdicts.total}) must equal evaluated_count ({self.evaluated_count})")

        _require_tuple("couples", self.couples)
        _require_elements("couples", self.couples, InterSCoupleSynthesis)
        _require_tuple("groups", self.groups)
        _require_elements("groups", self.groups, InterSGroupSynthesis)
        _require_tuple("observables", self.observables)
        _require_elements("observables", self.observables, InterSObservableSynthesis)

        if len(self.groups) != self.exact_match_count:
            raise ValueError(
                f"len(groups) ({len(self.groups)}) must equal exact_match_count ({self.exact_match_count}) -- "
                "InterSGroupMatch guarantees exact_label_match iff a concrete low_group exists"
            )
        if sum(len(couple.groups) for couple in self.couples) != len(self.groups):
            raise ValueError("sum of couples[*].groups length must equal len(groups)")
        if sum(couple.evaluation_count for couple in self.couples) != self.evaluated_count:
            raise ValueError("sum of couples[*].evaluation_count must equal evaluated_count")
        if sum(couple.unevaluable_count for couple in self.couples) != self.unevaluable_count:
            raise ValueError("sum of couples[*].unevaluable_count must equal unevaluable_count")
        if sum(len(group.evaluations) for group in self.groups) != self.evaluated_count:
            raise ValueError("sum of groups[*].evaluations length must equal evaluated_count")
        if sum(len(group.unevaluable_comparisons) for group in self.groups) != self.unevaluable_count:
            raise ValueError("sum of groups[*].unevaluable_comparisons length must equal unevaluable_count")

        if tuple(o.observable_kind for o in self.observables) != ROBUSTNESS_EVALUATION_ORDER:
            raise ValueError(f"observables must be in the fixed order {ROBUSTNESS_EVALUATION_ORDER}")
        if sum(o.evaluation_count for o in self.observables) != self.evaluated_count:
            raise ValueError("sum of observables[*].evaluation_count must equal evaluated_count")
        if sum(o.unevaluable_count for o in self.observables) != self.unevaluable_count:
            raise ValueError("sum of observables[*].unevaluable_count must equal unevaluable_count")


# ---------------------------------------------------------------------------
# Builder.
# ---------------------------------------------------------------------------


def _require_consistent_provenance(
    matching_report: InterSMatchingReport, comparison_report: InterSObservableComparisonReport, robustness_report: InterSRobustnessReport
) -> None:
    provenances = {
        (matching_report.campaign_id, matching_report.manifest_fingerprint, matching_report.repository_commit),
        (comparison_report.campaign_id, comparison_report.manifest_fingerprint, comparison_report.repository_commit),
        (robustness_report.campaign_id, robustness_report.manifest_fingerprint, robustness_report.repository_commit),
    }
    if len(provenances) != 1:
        raise InterSSynthesisError(
            f"matching_report/comparison_report/robustness_report do not share identical provenance: {sorted(provenances)!r}"
        )


def build_inter_s_synthesis_report(
    matching_report: InterSMatchingReport,
    comparison_report: InterSObservableComparisonReport,
    robustness_report: InterSRobustnessReport,
) -> InterSSynthesisReport:
    """Reorganizes and counts objects already produced by 1B-9c/9d/9e --
    never re-matches, never recomputes a value, never writes anything.
    """
    _require_consistent_provenance(matching_report, comparison_report, robustness_report)

    matches_by_identity = _index_matches_by_group_identity(matching_report)
    evaluation_by_comparison_id = {id(evaluation.comparison): evaluation for evaluation in robustness_report.evaluations}
    unevaluable_ids = {id(comparison) for comparison in robustness_report.unevaluable_comparisons}

    per_match_evaluations: dict[int, list[InterSRobustnessEvaluation]] = {}
    per_match_unevaluable: dict[int, list[ScalarObservableComparison]] = {}

    for comparison in comparison_report.comparisons:
        match = _find_source_match(comparison, matches_by_identity)
        comparison_id = id(comparison)
        if comparison_id in evaluation_by_comparison_id:
            per_match_evaluations.setdefault(id(match), []).append(evaluation_by_comparison_id[comparison_id])
        elif comparison_id in unevaluable_ids:
            per_match_unevaluable.setdefault(id(match), []).append(comparison)
        else:
            raise InterSSynthesisError(
                "a comparison in comparison_report.comparisons is neither evaluated nor unevaluable in "
                "robustness_report -- comparison_report and robustness_report were not built from the same pipeline run"
            )

    # Source of truth for group EXISTENCE and ORDER is matching_report.
    # matches itself, never comparison_report.comparisons: an
    # exact_label_match with a concrete low_group must be represented
    # even when the closed 1B-9d observable list produced zero
    # comparisons for it. A match without a concrete low_group (non-exact
    # outcome) is not a spectral group pairing representable by a
    # SpectralGroupMatchKey pair -- it stays counted in matching_count,
    # never in groups/couples. InterSGroupMatch.__post_init__ already
    # guarantees (exact_label_match) iff (low_group is not None), so
    # filtering on low_group here is exactly filtering on exactness.
    groups: list[InterSGroupSynthesis] = []
    for match in matching_report.matches:
        if match.low_group is None:
            continue
        evaluations = tuple(per_match_evaluations.get(id(match), ()))
        unevaluable = tuple(per_match_unevaluable.get(id(match), ()))
        groups.append(
            InterSGroupSynthesis(
                high_case_id=match.high_case_id,
                low_case_id=match.low_case_id,
                high_spin=match.high_spin,
                low_spin=match.low_spin,
                high_group_match_key=match.high_group.match_key,
                low_group_match_key=match.low_group.match_key,
                high_group_index=match.high_group.spectral_window_group_index,
                low_group_index=match.low_group.spectral_window_group_index,
                match_status=match.outcome.status,
                evaluations=evaluations,
                unevaluable_comparisons=unevaluable,
                observable_counts=_build_observable_counts(evaluations),
                verdicts=_count_verdicts(evaluations),
            )
        )
    groups_t = tuple(groups)

    grouped_by_couple: dict[tuple[str, str], list[InterSGroupSynthesis]] = {}
    for group in groups_t:
        grouped_by_couple.setdefault((group.high_case_id, group.low_case_id), []).append(group)

    couples: list[InterSCoupleSynthesis] = []
    for (high_case_id, low_case_id), couple_groups in grouped_by_couple.items():
        couple_groups_t = tuple(couple_groups)
        couple_evaluations = tuple(evaluation for group in couple_groups_t for evaluation in group.evaluations)
        couples.append(
            InterSCoupleSynthesis(
                high_case_id=high_case_id,
                low_case_id=low_case_id,
                high_spin=couple_groups_t[0].high_spin,
                low_spin=couple_groups_t[0].low_spin,
                groups=couple_groups_t,
                evaluation_count=sum(len(group.evaluations) for group in couple_groups_t),
                unevaluable_count=sum(len(group.unevaluable_comparisons) for group in couple_groups_t),
                observable_counts=_build_observable_counts(couple_evaluations),
                verdicts=_count_verdicts(couple_evaluations),
            )
        )
    couples_t = tuple(couples)

    observables_t = tuple(_build_observable_synthesis(kind, robustness_report) for kind in ROBUSTNESS_EVALUATION_ORDER)

    return InterSSynthesisReport(
        campaign_id=matching_report.campaign_id,
        manifest_fingerprint=matching_report.manifest_fingerprint,
        repository_commit=matching_report.repository_commit,
        matching_count=len(matching_report.matches),
        exact_match_count=sum(1 for match in matching_report.matches if match.outcome.status == EXACT_LABEL_MATCH),
        source_comparison_count=len(comparison_report.comparisons),
        evaluated_count=len(robustness_report.evaluations),
        unevaluable_count=len(robustness_report.unevaluable_comparisons),
        verdicts=_count_verdicts(robustness_report.evaluations),
        couples=couples_t,
        groups=groups_t,
        observables=observables_t,
    )
