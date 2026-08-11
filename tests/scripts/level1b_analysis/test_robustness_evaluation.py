from __future__ import annotations

import dataclasses
import inspect

import pytest

from cosmobox.level1.matching import EXACT_LABEL_MATCH, MatchOutcome, SpectralGroupMatchKey, SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from cosmobox.level1.results import ROBUSTNESS_OBSERVABLE_KINDS
from cosmobox.level1.robustness import RobustnessResult, TRUNCATED_SPECTRAL_GROUP, evaluate_robustness
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_analysis import loader as loader_module
from scripts.level1b_analysis import robustness_evaluation as robustness_evaluation_module
from scripts.level1b_analysis.comparisons import (
    GammaOComparison,
    ScalarObservableComparison,
    build_inter_s_observable_comparison_report,
)
from scripts.level1b_analysis.indexing import IndexedSpectralGroup, SpectralGroupIdentity
from scripts.level1b_analysis.inter_s import InterSGroupMatch, InterSMatchingReport
from scripts.level1b_analysis.robustness_evaluation import (
    EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS,
    GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND,
    InterSRobustnessError,
    InterSRobustnessEvaluation,
    InterSRobustnessReport,
    build_inter_s_robustness_report,
)

REPO_COMMIT = "d" * 40


# ---------------------------------------------------------------------------
# Fixtures -- same self-contained pattern as test_inter_s.py/test_comparisons.py.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def real_plan(real_manifest: manifest_module.Manifest) -> tuple:
    return planning_module.build_campaign_plan(real_manifest)


def _case(real_plan: tuple, *, geometry: str = "triangle", spin: int, hamiltonian_case_id: str = "reference"):
    return next(
        c for c in real_plan if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture
def triangle_s2(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=2)


@pytest.fixture
def triangle_s3(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=3)


def _doc(*, record_kind, observable_kind, path=None, flavor_component=None, normalization=None, payload):
    raw = {
        "record_kind": record_kind,
        "observable_kind": observable_kind,
        "identity": {
            "path": list(path) if path is not None else None,
            "flavor_component": flavor_component,
            "normalization": normalization,
        },
        "payload": payload,
    }
    return loader_module._freeze_document(raw)


def _o_ij_raw_doc(value: complex, **kwargs):
    value = complex(value)
    return _doc(record_kind="raw_observable", observable_kind="O_ij_raw", payload={"real": value.real, "imag": value.imag}, **kwargs)


def _c_tt_conn_doc(value: float, **kwargs):
    return _doc(record_kind="raw_observable", observable_kind="C_TT_conn", payload=float(value), **kwargs)


def _rho_qq_doc(*, value: float | None = None, null_reason: str | None = None, **kwargs):
    return _doc(record_kind="normalized_observable", observable_kind="rho_QQ", payload={"value": value, "null_reason": null_reason}, **kwargs)


def _dummy_match_key(case, *, status: str = COMPLETE_MULTIPLET, twice_T: int = 1) -> SpectralGroupMatchKey:
    parameters = case.hamiltonian_parameters
    return SpectralGroupMatchKey(
        geometry=case.geometry,
        hamiltonian_identity_without_spin=(
            tuple(float(v) for v in parameters.J),
            True,
            float(parameters.t),
            float(parameters.g_E),
            float(parameters.K),
        ),
        sector_identity=case.sector_id,
        status=status,
        multiplicity=1,
        twice_T=twice_T,
        translation_label=SymmetryLabel(kind="not_applicable", value=None),
        reflection_label=SymmetryLabel(kind="not_applicable", value=None),
    )


def _fake_group(case, *, group_index: int = 0, documents: tuple, status: str = COMPLETE_MULTIPLET) -> IndexedSpectralGroup:
    return IndexedSpectralGroup(
        case_id=case.case_id,
        case=case,
        spectral_group_identity=SpectralGroupIdentity(
            status=status, multiplicity=1, twice_T=1, spectral_window_group_index=group_index, representative_energy=-1.0
        ),
        spectral_window_group_index=group_index,
        match_key=_dummy_match_key(case, status=status),
        documents=documents,
    )


def _fake_match(high_case, low_case, high_group: IndexedSpectralGroup, low_group: IndexedSpectralGroup, *, status: str = EXACT_LABEL_MATCH) -> InterSGroupMatch:
    matched_group = low_group.match_key if status == EXACT_LABEL_MATCH else None
    return InterSGroupMatch(
        high_case_id=high_case.case_id,
        low_case_id=low_case.case_id,
        high_spin=high_case.spin,
        low_spin=low_case.spin,
        high_group=high_group,
        low_group=low_group if status == EXACT_LABEL_MATCH else None,
        outcome=MatchOutcome(status, matched_group),
    )


def _fake_matching_report(match: InterSGroupMatch, *, campaign_id: str = "test-campaign", manifest_fingerprint: str = "f" * 64, repository_commit: str = REPO_COMMIT) -> InterSMatchingReport:
    return InterSMatchingReport(campaign_id=campaign_id, manifest_fingerprint=manifest_fingerprint, repository_commit=repository_commit, matches=(match,))


def _build(triangle_s2, triangle_s3, high_documents: tuple, low_documents: tuple, *, status: str = EXACT_LABEL_MATCH, group_status: str = COMPLETE_MULTIPLET):
    high_group = _fake_group(triangle_s3, documents=high_documents, status=group_status)
    low_group = _fake_group(triangle_s2, documents=low_documents, status=group_status)
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group, status=status)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    return match, matching_report, comparison_report, robustness_report


# ---------------------------------------------------------------------------
# 1/2/17. GammaOComparison numeric -> real evaluate_robustness call, exact
# gamma_o conservation, observable_kind == "gamma_O".
# ---------------------------------------------------------------------------


def test_gamma_o_numeric_uses_real_evaluate_robustness(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2, triangle_s3, (_o_ij_raw_doc(2 + 0j, path=(0, 1)),), (_o_ij_raw_doc(1 + 0j, path=(0, 1)),)
    )
    assert len(robustness_report.evaluations) == 1
    evaluation = robustness_report.evaluations[0]
    comparison = comparison_report.comparisons[0]
    assert isinstance(comparison, GammaOComparison)
    assert evaluation.observable_kind == GAMMA_O_ROBUSTNESS_OBSERVABLE_KIND == "gamma_O"

    expected = evaluate_robustness(match.outcome, comparison.high_value, comparison.low_value)
    assert evaluation.result == expected
    assert evaluation.result.gamma_o == comparison.gamma_o


# ---------------------------------------------------------------------------
# 3/4. gamma_O under the normalization floor still receives a definitive
# verdict -- gamma_o.value is None must never force verdict=indeterminate.
# ---------------------------------------------------------------------------


def test_gamma_o_below_floor_still_gets_a_definitive_verdict(triangle_s2, triangle_s3) -> None:
    # high == low == 0: amplitude (0) <= floor -> gamma_o.value is None,
    # but difference (0) <= threshold (0.05) -> a genuinely definitive
    # robust verdict from evaluate_robustness itself.
    match, _, comparison_report, robustness_report = _build(
        triangle_s2, triangle_s3, (_o_ij_raw_doc(0 + 0j, path=(0, 1)),), (_o_ij_raw_doc(0 + 0j, path=(0, 1)),)
    )
    evaluation = robustness_report.evaluations[0]
    comparison = comparison_report.comparisons[0]

    assert comparison.gamma_o.value is None
    assert comparison.gamma_o.null_reason == "normalization_denominator_below_floor"
    assert evaluation.result.gamma_o.value is None
    # The rule this test forbids: gamma_o.value is None must NEVER by
    # itself force an indeterminate verdict.
    assert evaluation.result.verdict != "indeterminate"
    assert evaluation.result.verdict == "robust"


# ---------------------------------------------------------------------------
# 5/6/7/18. Scalar observables (rho_QQ/C_TT_conn/flavor_singular_value_
# ratio) numeric -> real evaluate_robustness call, observable_kind kept.
# ---------------------------------------------------------------------------


def test_rho_qq_numeric_uses_real_evaluate_robustness(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2, triangle_s3, (_rho_qq_doc(value=0.5, path=(0, 1)),), (_rho_qq_doc(value=0.4, path=(0, 1)),)
    )
    evaluation = robustness_report.evaluations[0]
    comparison = comparison_report.comparisons[0]
    assert isinstance(comparison, ScalarObservableComparison)
    assert evaluation.observable_kind == "rho_QQ"
    expected = evaluate_robustness(match.outcome, complex(0.5), complex(0.4))
    assert evaluation.result == expected


def test_c_tt_conn_numeric_uses_real_evaluate_robustness(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    evaluation = robustness_report.evaluations[0]
    assert evaluation.observable_kind == "C_TT_conn"
    expected = evaluate_robustness(match.outcome, complex(-0.1), complex(-0.2))
    assert evaluation.result == expected


def test_flavor_singular_value_ratio_numeric_uses_real_evaluate_robustness(triangle_s2, triangle_s3) -> None:
    def _flavor_ratio_doc(*, value=None, null_reason=None, **kwargs):
        return _doc(record_kind="flavor_diagnostic", observable_kind="flavor_singular_value_ratio", payload={"value": value, "null_reason": null_reason}, **kwargs)

    match, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_flavor_ratio_doc(value=0.9, path=(0, 1), normalization="raw_G"),),
        (_flavor_ratio_doc(value=0.8, path=(0, 1), normalization="raw_G"),),
    )
    evaluation = robustness_report.evaluations[0]
    assert evaluation.observable_kind == "flavor_singular_value_ratio"
    expected = evaluate_robustness(match.outcome, complex(0.9), complex(0.8))
    assert evaluation.result == expected


# ---------------------------------------------------------------------------
# 8/9/10/11. Source-null scalars are never evaluated -- carried in
# unevaluable_comparisons, no fabricated RobustnessResult/null_reason.
# ---------------------------------------------------------------------------


def test_high_scalar_null_is_unevaluable(triangle_s2, triangle_s3) -> None:
    _, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
        (_rho_qq_doc(value=0.4, path=(0, 1)),),
    )
    assert robustness_report.evaluations == ()
    assert len(robustness_report.unevaluable_comparisons) == 1
    unevaluable = robustness_report.unevaluable_comparisons[0]
    assert unevaluable is comparison_report.comparisons[0]
    assert unevaluable.high_value is None
    assert unevaluable.high_null_reason == "zero_local_charge_variance"


def test_low_scalar_null_is_unevaluable(triangle_s2, triangle_s3) -> None:
    _, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_rho_qq_doc(value=0.5, path=(0, 1)),),
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
    )
    assert robustness_report.evaluations == ()
    assert len(robustness_report.unevaluable_comparisons) == 1
    assert robustness_report.unevaluable_comparisons[0].low_value is None


def test_both_scalar_null_is_unevaluable(triangle_s2, triangle_s3) -> None:
    _, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
    )
    assert robustness_report.evaluations == ()
    unevaluable = robustness_report.unevaluable_comparisons[0]
    assert unevaluable.high_value is None
    assert unevaluable.low_value is None
    # No new robustness null_reason invented -- the ORIGINAL 1B-9d
    # null_reason is exactly what is carried, untouched.
    assert unevaluable.high_null_reason == "zero_local_charge_variance"
    assert unevaluable.low_null_reason == "zero_local_charge_variance"


def test_robustness_module_never_fabricates_a_new_null_reason() -> None:
    source = inspect.getsource(robustness_evaluation_module)
    for forbidden in ("source_value_null", "observable_unavailable", "normalization_failure", "missing_value"):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# 12. partial_subspace synthetic -> the exact RobustnessResult from
# evaluate_robustness, notably truncated_spectral_group, never rewritten.
# ---------------------------------------------------------------------------


def test_partial_subspace_match_yields_truncated_spectral_group(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_c_tt_conn_doc(-0.1, path=(0, 1)),),
        (_c_tt_conn_doc(-0.2, path=(0, 1)),),
        group_status=PARTIAL_SUBSPACE,
    )
    evaluation = robustness_report.evaluations[0]
    assert evaluation.result.verdict == "indeterminate"
    assert evaluation.result.null_reason == TRUNCATED_SPECTRAL_GROUP
    # Both values ARE reported (an exploratory difference/gamma_o is
    # still computed by evaluate_robustness -- never suppressed).
    assert evaluation.result.difference is not None
    assert evaluation.result.gamma_o is not None


# ---------------------------------------------------------------------------
# 13/14/15. Provenance mismatch / zero / multiple source matches.
# ---------------------------------------------------------------------------


def test_mismatched_provenance_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match, campaign_id="campaign-A")
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    mismatched_comparison_report = dataclasses.replace(comparison_report, campaign_id="campaign-B")

    with pytest.raises(InterSRobustnessError, match="provenance"):
        build_inter_s_robustness_report(matching_report, mismatched_comparison_report)


def test_zero_source_match_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)

    # A matching report whose match points at DIFFERENT group objects --
    # the comparison's own high_group/low_group are then found nowhere.
    other_high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    other_low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    other_match = _fake_match(triangle_s3, triangle_s2, other_high_group, other_low_group)
    other_matching_report = _fake_matching_report(other_match)

    with pytest.raises(InterSRobustnessError, match="found 0"):
        build_inter_s_robustness_report(other_matching_report, comparison_report)


def test_multiple_source_matches_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)

    duplicate_matches_report = InterSMatchingReport(
        campaign_id=matching_report.campaign_id,
        manifest_fingerprint=matching_report.manifest_fingerprint,
        repository_commit=matching_report.repository_commit,
        matches=(match, match),
    )

    with pytest.raises(InterSRobustnessError, match="found 2"):
        build_inter_s_robustness_report(duplicate_matches_report, comparison_report)


# ---------------------------------------------------------------------------
# 16. The real MatchOutcome is conserved on the evaluation.
# ---------------------------------------------------------------------------


def test_real_match_outcome_is_conserved(triangle_s2, triangle_s3) -> None:
    match, _, _, robustness_report = _build(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    evaluation = robustness_report.evaluations[0]
    assert evaluation.match is match
    assert evaluation.match.outcome is match.outcome


# ---------------------------------------------------------------------------
# 19/20. Closed robustness list respected; a synthetic non-eligible
# observable_kind is rejected at construction.
# ---------------------------------------------------------------------------


def test_evaluated_observable_kinds_are_a_subset_of_the_closed_robustness_list() -> None:
    for kind in EVALUATED_ROBUSTNESS_OBSERVABLE_KINDS:
        assert kind in ROBUSTNESS_OBSERVABLE_KINDS


def test_evaluation_rejects_a_non_eligible_observable_kind(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, _ = _build(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    comparison = comparison_report.comparisons[0]
    result = evaluate_robustness(match.outcome, complex(-0.1), complex(-0.2))
    with pytest.raises(ValueError, match="observable_kind"):
        InterSRobustnessEvaluation(comparison=comparison, match=match, observable_kind="flavor_singlet", result=result)


# ---------------------------------------------------------------------------
# 21/22. Relative order of evaluations and of unevaluable_comparisons
# each independently follows comparison_report.comparisons.
# ---------------------------------------------------------------------------


def test_order_is_preserved_independently_in_each_bucket(triangle_s2, triangle_s3) -> None:
    high_documents = (
        _rho_qq_doc(value=0.5, path=(0, 1)),  # evaluable
        _c_tt_conn_doc(-0.1, path=(0, 1)),  # evaluable
    )
    low_documents = (
        _rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),  # -> unevaluable
        _c_tt_conn_doc(-0.2, path=(0, 1)),  # evaluable
    )
    # A third, later-in-document-order pair that is also unevaluable, to
    # prove relative order within unevaluable_comparisons is preserved.
    high_group = _fake_group(
        triangle_s3,
        documents=high_documents + (_rho_qq_doc(value=0.7, path=(0, 2)),),
    )
    low_group = _fake_group(
        triangle_s2,
        documents=low_documents + (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 2)),),
    )
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)

    # comparisons order: rho_QQ(0,1) [null->unevaluable], C_TT_conn(0,1) [evaluable], rho_QQ(0,2) [null->unevaluable]
    assert len(robustness_report.evaluations) == 1
    assert robustness_report.evaluations[0].observable_kind == "C_TT_conn"
    assert len(robustness_report.unevaluable_comparisons) == 2
    assert robustness_report.unevaluable_comparisons[0].path == (0, 1)
    assert robustness_report.unevaluable_comparisons[1].path == (0, 2)


# ---------------------------------------------------------------------------
# 23/24/26. Report/evaluation constructors reject a mutable list and a
# wrong element type; result must be a real RobustnessResult.
# ---------------------------------------------------------------------------


def test_report_rejects_a_list_for_evaluations(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report = _build(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    with pytest.raises(ValueError, match="must be a tuple"):
        InterSRobustnessReport(
            campaign_id="c",
            manifest_fingerprint="f" * 64,
            repository_commit=REPO_COMMIT,
            evaluations=list(robustness_report.evaluations),
            unevaluable_comparisons=(),
        )


def test_report_rejects_a_wrong_element_type_in_evaluations() -> None:
    with pytest.raises(ValueError, match="InterSRobustnessEvaluation"):
        InterSRobustnessReport(
            campaign_id="c", manifest_fingerprint="f" * 64, repository_commit=REPO_COMMIT, evaluations=("not-an-evaluation",), unevaluable_comparisons=()
        )


def test_report_rejects_a_wrong_element_type_in_unevaluable_comparisons() -> None:
    with pytest.raises(ValueError, match="ScalarObservableComparison"):
        InterSRobustnessReport(
            campaign_id="c", manifest_fingerprint="f" * 64, repository_commit=REPO_COMMIT, evaluations=(), unevaluable_comparisons=("not-a-comparison",)
        )


def test_evaluation_rejects_a_non_robustness_result(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, _ = _build(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    comparison = comparison_report.comparisons[0]
    with pytest.raises(ValueError, match="RobustnessResult"):
        InterSRobustnessEvaluation(comparison=comparison, match=match, observable_kind="C_TT_conn", result="not-a-result")


# ---------------------------------------------------------------------------
# 25. Evaluation refuses a null-valued ScalarObservableComparison.
# ---------------------------------------------------------------------------


def test_evaluation_rejects_a_null_valued_scalar_comparison(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2,
        triangle_s3,
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
    )
    null_comparison = robustness_report.unevaluable_comparisons[0]
    dummy_result = RobustnessResult(verdict="robust", null_reason=None, gamma_o=None, difference=0.0, amplitude=0.0)
    with pytest.raises(ValueError, match="null"):
        InterSRobustnessEvaluation(comparison=null_comparison, match=match, observable_kind="rho_QQ", result=dummy_result)


# ---------------------------------------------------------------------------
# 27. No comparison object appears in both evaluations and
# unevaluable_comparisons.
# ---------------------------------------------------------------------------


def test_report_rejects_a_comparison_present_in_both_buckets(triangle_s2, triangle_s3) -> None:
    match, _, comparison_report, robustness_report = _build(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    evaluation = robustness_report.evaluations[0]
    with pytest.raises(ValueError, match="both evaluations and unevaluable_comparisons"):
        InterSRobustnessReport(
            campaign_id="c",
            manifest_fingerprint="f" * 64,
            repository_commit=REPO_COMMIT,
            evaluations=(evaluation,),
            unevaluable_comparisons=(evaluation.comparison,),
        )


# ---------------------------------------------------------------------------
# 28. Source repository_commit is conserved (distinct from the analysis
# code's own HEAD).
# ---------------------------------------------------------------------------


def test_source_repository_commit_is_conserved(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match, repository_commit="0ff65ac66b4aa054f739b350cd384c26ecd19752")
    comparison_report = build_inter_s_observable_comparison_report(matching_report)

    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)

    assert robustness_report.repository_commit == "0ff65ac66b4aa054f739b350cd384c26ecd19752"


# ---------------------------------------------------------------------------
# 29/30. No persistence; no forbidden runner/campaign/launcher import.
# ---------------------------------------------------------------------------


def test_robustness_module_never_imports_forbidden_entry_points() -> None:
    import inspect

    from scripts.level1b_analysis import robustness_evaluation as robustness_evaluation_module

    source = inspect.getsource(robustness_evaluation_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    for token in ("run_single_case", "run_campaign", "launch_normative_campaign", "run_level1b_campaign"):
        assert token not in import_lines, f"robustness_evaluation.py must never import {token!r}"
    assert "open(" not in source
