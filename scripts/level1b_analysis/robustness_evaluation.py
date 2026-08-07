"""Robustness verdicts applied to already-built inter-S observable
comparisons (1B-9d, docs/governance/current-task.md). Level1B lot 1B-9e.

build_inter_s_robustness_report is the ONLY place in this package that
ever calls cosmobox.level1.robustness.evaluate_robustness, unmodified --
it never recodes D_S = |x_high - x_low|, threshold = max(0.05,
0.15 * amplitude), the robust/non_robust decision, or the
truncated_spectral_group/non-exact-match indeterminate reasons: all of
that logic stays exactly where it already lives, inside evaluate_
robustness itself. This lot applies the already-frozen contract; it
never redefines a formula, a threshold, or a null_reason.

Audit of the real corpus (read-only, before implementation): for the
three scalar observables (rho_QQ, C_TT_conn, flavor_singular_value_
ratio), the accepted campaign only ever exhibits "both sides numeric"
or "both sides null" -- never one side null and the other numeric.
C_TT_conn is 100% numeric (structurally, per 1B-9d). This module still
handles the general case (either side independently null) uniformly,
since nothing in the accepted contract rules it out for a future
campaign.

gamma_O's own null-by-floor is NOT a reason to skip evaluate_robustness:
GammaOComparison.high_value/low_value are always present (O_ij_raw's
raw_observable payload is never null), so evaluate_robustness is always
called for every GammaOComparison, exactly with those two values, via
match.outcome. gamma_o.value being None (normalization_denominator_
below_floor) and RobustnessResult.verdict being a definitive robust/
non_robust are two entirely independent facts computed by two different
parts of the SAME primitive call -- this module never conflates the
two into a manufactured "indeterminate".

Only a source value that is itself None (a ScalarObservableComparison
with high_value or low_value already null, per 1B-9d's own contract)
is never passed to evaluate_robustness -- the primitive requires finite
numeric values and defines no verdict for a missing source value. Such
a comparison is instead carried, unchanged, into
InterSRobustnessReport.unevaluable_comparisons: no RobustnessResult is
fabricated, and this module never mints any brand-new robustness
null_reason string of its own -- the reason a comparison is unevaluable
is already fully carried by its own high_null_reason/low_null_reason
fields, exactly as 1B-9d produced them.

Comparison -> InterSGroupMatch association: 1B-9c's matching is never
re-run, re-derived, or re-implemented here. Because comparisons.py
always passes match.high_group/match.low_group straight through
(object identity, never a copy) when building a GammaOComparison/
ScalarObservableComparison, the exact source InterSGroupMatch for a
given comparison is found by (high_case_id, low_case_id, id(high_group),
id(low_group)) -- Python object identity, not dataclass value equality:
IndexedSpectralGroup/CampaignCaseSpec carry numpy.ndarray fields (h in
HamiltonianParameters), which are themselves unhashable and whose `==`
returns an elementwise array rather than a bool, making the dataclass-
generated __eq__/__hash__ unusable (and liable to crash) for this
purpose. Identity comparison is both correct (the accepted pipeline
never copies these objects) and safe. Exactly one source match must be
found; zero or more than one is a structural inconsistency of this
lot's own pipeline (never matching.py's concern) and raises
InterSRobustnessError -- never chosen by energy, group index, order, or
proximity.

evaluate_robustness always receives match.outcome exactly as matching.py
produced it -- never assumed complete_multiplet, never rewritten. A
partial_subspace matched group yields verdict=indeterminate,
null_reason="truncated_spectral_group" from evaluate_robustness itself;
this module carries that RobustnessResult unchanged.

No diagonalization, no eigenvector reconstruction, no new threshold, no
new formula, no new robustness null_reason, and no write to disk occur
anywhere in this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from cosmobox.level1.robustness import RobustnessResult, evaluate_robustness

from .comparisons import GammaOComparison, InterSObservableComparisonReport, ScalarObservableComparison
from .inter_s import InterSGroupMatch, InterSMatchingReport

GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND = "gamma_O"
SCALAR_ROBUSTNESS_OBSERVABLE_KINDS = ("rho_QQ", "C_TT_conn", "flavor_singular_value_ratio")
"""Mirrors comparisons.SCALAR_OBSERVABLE_KINDS -- restated here (rather
than imported) only as the literal tuple this module's own eligibility
check is defined against; both are, and must remain, subsets of
cosmobox.level1.results.ROBUSTNESS_OBSERVABLE_KINDS (verified by test,
never re-derived from it here to avoid coupling this closed list's
wording to results.py's own unrelated G_occ entry, which this package
never produces)."""
EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS = (GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND,) + SCALAR_ROBUSTNESS_OBSERVABLE_KINDS


class InterSRobustnessError(RuntimeError):
    """Raised for a structural inconsistency in this lot's own pipeline:
    mismatched provenance between the matching and comparison reports,
    or zero/more-than-one source InterSGroupMatch found for a
    comparison. Never raised for an ordinary source-null comparison
    (that is expected, ordinary data -- see unevaluable_comparisons)."""


@dataclass(frozen=True, slots=True)
class InterSRobustnessEvaluation:
    """One comparison, its exact source InterSGroupMatch, and the real
    RobustnessResult evaluate_robustness produced for it -- never a
    parallel dataclass recopying verdict/difference/amplitude/gamma_o/
    null_reason independently of RobustnessResult, which remains the
    sole source of truth for all of them."""

    comparison: GammaOComparison | ScalarObservableComparison
    match: InterSGroupMatch
    observable_kind: str
    result: RobustnessResult

    def __post_init__(self) -> None:
        if not isinstance(self.comparison, (GammaOComparison, ScalarObservableComparison)):
            raise ValueError(f"comparison must be a GammaOComparison or ScalarObservableComparison, got {type(self.comparison)}")
        if not isinstance(self.match, InterSGroupMatch):
            raise ValueError(f"match must be an InterSGroupMatch, got {type(self.match)}")
        if not isinstance(self.result, RobustnessResult):
            raise ValueError(f"result must be a RobustnessResult, got {type(self.result)}")
        if self.observable_kind not in EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS:
            raise ValueError(f"observable_kind must be one of {EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS}, got {self.observable_kind!r}")
        if self.comparison.high_case_id != self.match.high_case_id:
            raise ValueError(f"comparison.high_case_id ({self.comparison.high_case_id!r}) != match.high_case_id ({self.match.high_case_id!r})")
        if self.comparison.low_case_id != self.match.low_case_id:
            raise ValueError(f"comparison.low_case_id ({self.comparison.low_case_id!r}) != match.low_case_id ({self.match.low_case_id!r})")
        if self.comparison.high_group is not self.match.high_group:
            raise ValueError("comparison.high_group is not the same object as match.high_group")
        if self.comparison.low_group is not self.match.low_group:
            raise ValueError("comparison.low_group is not the same object as match.low_group")

        if isinstance(self.comparison, GammaOComparison):
            if self.observable_kind != GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND:
                raise ValueError(f"observable_kind must be {GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND!r} for a GammaOComparison, got {self.observable_kind!r}")
            if self.result.gamma_o != self.comparison.gamma_o:
                raise ValueError(
                    "result.gamma_o does not match comparison.gamma_o -- both must come from the same "
                    "compute_gamma_o(high_value, low_value) call"
                )
        else:
            if self.observable_kind != self.comparison.observable_kind:
                raise ValueError(f"observable_kind ({self.observable_kind!r}) != comparison.observable_kind ({self.comparison.observable_kind!r})")
            if self.comparison.high_value is None or self.comparison.low_value is None:
                raise ValueError(
                    "a ScalarObservableComparison with a null high_value/low_value must never be wrapped in an "
                    "InterSRobustnessEvaluation -- it belongs in unevaluable_comparisons instead"
                )


@dataclass(frozen=True, slots=True)
class InterSRobustnessReport:
    """Provenance is that of the SOURCE campaign (campaign_id/manifest_
    fingerprint/repository_commit), copied unchanged from the matching/
    comparison reports that produced this one -- never the analysis
    code's own commit. evaluations and unevaluable_comparisons each
    independently preserve the relative order of comparison_report.
    comparisons -- neither is ever sorted by verdict, value, observable,
    or filesystem order. No comparison object may appear in both."""

    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str
    evaluations: tuple[InterSRobustnessEvaluation, ...]
    unevaluable_comparisons: tuple[ScalarObservableComparison, ...]

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.repository_commit:
            raise ValueError("repository_commit must be non-empty")

        if not isinstance(self.evaluations, tuple):
            raise ValueError(f"evaluations must be a tuple, got {type(self.evaluations)} -- never silently converted")
        if not isinstance(self.unevaluable_comparisons, tuple):
            raise ValueError(f"unevaluable_comparisons must be a tuple, got {type(self.unevaluable_comparisons)} -- never silently converted")

        # Checked before the per-element loops below: a comparison object
        # present in both collections is rejected as an identity clash in
        # its own right, rather than being left to surface indirectly as
        # whichever per-element check happens to run into it first.
        evaluated_ids = {id(evaluation.comparison) for evaluation in self.evaluations if isinstance(evaluation, InterSRobustnessEvaluation)}
        unevaluable_ids = {id(comparison) for comparison in self.unevaluable_comparisons}
        overlap = evaluated_ids & unevaluable_ids
        if overlap:
            raise ValueError(f"{len(overlap)} comparison(s) appear in both evaluations and unevaluable_comparisons")

        for index, evaluation in enumerate(self.evaluations):
            if not isinstance(evaluation, InterSRobustnessEvaluation):
                raise ValueError(f"evaluations[{index}] must be an InterSRobustnessEvaluation, got {type(evaluation)}")

        for index, comparison in enumerate(self.unevaluable_comparisons):
            if not isinstance(comparison, ScalarObservableComparison):
                raise ValueError(f"unevaluable_comparisons[{index}] must be a ScalarObservableComparison, got {type(comparison)}")
            if comparison.high_value is not None and comparison.low_value is not None:
                raise ValueError(
                    f"unevaluable_comparisons[{index}] has both high_value and low_value non-null -- it should "
                    "have been evaluated, not carried as unevaluable"
                )


def _require_matching_comparison_provenance(matching_report: InterSMatchingReport, comparison_report: InterSObservableComparisonReport) -> None:
    matching_provenance = (matching_report.campaign_id, matching_report.manifest_fingerprint, matching_report.repository_commit)
    comparison_provenance = (comparison_report.campaign_id, comparison_report.manifest_fingerprint, comparison_report.repository_commit)
    if matching_provenance != comparison_provenance:
        raise InterSRobustnessError(
            f"matching_report provenance {matching_provenance!r} does not match comparison_report provenance "
            f"{comparison_provenance!r} -- refusing to evaluate a comparison report against a mismatched matching report"
        )


def _group_identity_key(high_case_id: str, low_case_id: str, high_group: object, low_group: object) -> tuple:
    return (high_case_id, low_case_id, id(high_group), id(low_group))


def _index_matches_by_group_identity(matching_report: InterSMatchingReport) -> dict[tuple, list[InterSGroupMatch]]:
    index: dict[tuple, list[InterSGroupMatch]] = {}
    for match in matching_report.matches:
        key = _group_identity_key(match.high_case_id, match.low_case_id, match.high_group, match.low_group)
        index.setdefault(key, []).append(match)
    return index


def _find_source_match(
    comparison: GammaOComparison | ScalarObservableComparison, matches_by_identity: dict[tuple, list[InterSGroupMatch]]
) -> InterSGroupMatch:
    key = _group_identity_key(comparison.high_case_id, comparison.low_case_id, comparison.high_group, comparison.low_group)
    candidates = matches_by_identity.get(key, ())
    if len(candidates) != 1:
        raise InterSRobustnessError(
            f"expected exactly 1 source InterSGroupMatch for a comparison (high_case_id={comparison.high_case_id!r}, "
            f"low_case_id={comparison.low_case_id!r}), found {len(candidates)}"
        )
    return candidates[0]


def build_inter_s_robustness_report(
    matching_report: InterSMatchingReport, comparison_report: InterSObservableComparisonReport
) -> InterSRobustnessReport:
    """For each comparison in comparison_report.comparisons (in order):
    finds its exact source InterSGroupMatch, then either calls
    evaluate_robustness (GammaOComparison always; a ScalarObservableComparison
    only when both sides are non-null) or carries it unchanged into
    unevaluable_comparisons. No diagonalization, no write, no formula
    recoded."""
    _require_matching_comparison_provenance(matching_report, comparison_report)
    matches_by_identity = _index_matches_by_group_identity(matching_report)

    evaluations: list[InterSRobustnessEvaluation] = []
    unevaluable: list[ScalarObservableComparison] = []

    for comparison in comparison_report.comparisons:
        match = _find_source_match(comparison, matches_by_identity)

        if isinstance(comparison, GammaOComparison):
            result = evaluate_robustness(match.outcome, comparison.high_value, comparison.low_value)
            if result.gamma_o != comparison.gamma_o:
                raise InterSRobustnessError(
                    "evaluate_robustness's own gamma_o diverges from comparison.gamma_o for identical high_value/"
                    f"low_value (high_case_id={comparison.high_case_id!r}, low_case_id={comparison.low_case_id!r})"
                )
            evaluations.append(
                InterSRobustnessEvaluation(
                    comparison=comparison, match=match, observable_kind=GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND, result=result
                )
            )
            continue

        if comparison.high_value is None or comparison.low_value is None:
            unevaluable.append(comparison)
            continue

        result = evaluate_robustness(match.outcome, complex(comparison.high_value), complex(comparison.low_value))
        evaluations.append(
            InterSRobustnessEvaluation(comparison=comparison, match=match, observable_kind=comparison.observable_kind, result=result)
        )

    return InterSRobustnessReport(
        campaign_id=matching_report.campaign_id,
        manifest_fingerprint=matching_report.manifest_fingerprint,
        repository_commit=matching_report.repository_commit,
        evaluations=tuple(evaluations),
        unevaluable_comparisons=tuple(unevaluable),
    )
