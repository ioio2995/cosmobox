from __future__ import annotations

import dataclasses
import inspect

import pytest

from cosmobox.level1.matching import AMBIGUOUS_CROSS_TRUNCATION_MATCH, EXACT_LABEL_MATCH, MatchOutcome, SpectralGroupMatchKey, SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_analysis import loader as loader_module
from scripts.level1b_analysis import synthesis as synthesis_module
from scripts.level1b_analysis.comparisons import build_inter_s_observable_comparison_report
from scripts.level1b_analysis.indexing import IndexedSpectralGroup, SpectralGroupIdentity
from scripts.level1b_analysis.inter_s import InterSGroupMatch, InterSMatchingReport
from scripts.level1b_analysis.robustness_evaluation import build_inter_s_robustness_report
from scripts.level1b_analysis.synthesis import (
    DescriptiveStatistics,
    GammaOStatistics,
    InterSSynthesisError,
    InterSSynthesisReport,
    ROBUSTNESS_EVALUATION_ORDER,
    VerdictCounts,
    build_inter_s_synthesis_report,
)

REPO_COMMIT = "d" * 40


# ---------------------------------------------------------------------------
# Fixtures -- same self-contained pattern as test_robustness_evaluation.py.
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
    # twice_T varies with group_index so distinct groups of the same case
    # carry genuinely distinct SpectralGroupMatchKey content -- needed to
    # exercise match_key-based group-membership checks meaningfully.
    twice_T = group_index + 1
    return IndexedSpectralGroup(
        case_id=case.case_id,
        case=case,
        spectral_group_identity=SpectralGroupIdentity(
            status=status, multiplicity=1, twice_T=twice_T, spectral_window_group_index=group_index, representative_energy=-1.0
        ),
        spectral_window_group_index=group_index,
        match_key=_dummy_match_key(case, status=status, twice_T=twice_T),
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


def _fake_matching_report(*matches: InterSGroupMatch, campaign_id: str = "test-campaign", manifest_fingerprint: str = "f" * 64, repository_commit: str = REPO_COMMIT) -> InterSMatchingReport:
    return InterSMatchingReport(campaign_id=campaign_id, manifest_fingerprint=manifest_fingerprint, repository_commit=repository_commit, matches=matches)


def _build_all(triangle_s2, triangle_s3, high_documents: tuple, low_documents: tuple, *, status: str = EXACT_LABEL_MATCH, group_status: str = COMPLETE_MULTIPLET):
    high_group = _fake_group(triangle_s3, documents=high_documents, status=group_status)
    low_group = _fake_group(triangle_s2, documents=low_documents, status=group_status)
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group, status=status)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)
    return match, matching_report, comparison_report, robustness_report, synthesis


def _dummy_symmetry_doc(**kwargs):
    """A document whose observable_kind is never one of the 4 closed
    1B-9d targets -- silently ignored by comparisons.py, never a
    candidate, never an error. Used to build a genuine exact_label_match
    spectral group carrying zero 1B-9d comparisons."""
    return _doc(record_kind="symmetry_label", observable_kind="translation_character", payload={"kind": "not_applicable", "value": None}, **kwargs)


# ---------------------------------------------------------------------------
# Correctif: matching_report.matches (not comparison_report.comparisons)
# is the source of truth for group existence/order. An exact_label_match
# with a concrete low_group must produce an (empty) InterSGroupSynthesis
# even with zero 1B-9d comparisons; a non-exact match never does, but
# stays counted in matching_count.
# ---------------------------------------------------------------------------


def test_exact_match_without_comparisons_still_produces_an_empty_group(triangle_s2, triangle_s3) -> None:
    high_group_0 = _fake_group(triangle_s3, group_index=0, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group_0 = _fake_group(triangle_s2, group_index=0, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match_0 = _fake_match(triangle_s3, triangle_s2, high_group_0, low_group_0)

    # A genuine exact_label_match spectral group pairing whose documents
    # never touch any of the 4 closed 1B-9d observable kinds.
    high_group_1 = _fake_group(triangle_s3, group_index=1, documents=(_dummy_symmetry_doc(),))
    low_group_1 = _fake_group(triangle_s2, group_index=1, documents=(_dummy_symmetry_doc(),))
    match_1 = _fake_match(triangle_s3, triangle_s2, high_group_1, low_group_1)

    matching_report = _fake_matching_report(match_0, match_1)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    assert synthesis.matching_count == 2
    assert synthesis.exact_match_count == 2
    assert len(synthesis.groups) == 2
    assert len(synthesis.groups) == synthesis.exact_match_count
    assert [g.high_group_index for g in synthesis.groups] == [0, 1]

    empty_group = synthesis.groups[1]
    assert empty_group.evaluations == ()
    assert empty_group.unevaluable_comparisons == ()
    assert empty_group.verdicts == VerdictCounts(robust=0, non_robust=0, indeterminate=0)
    assert [count.observable_kind for count in empty_group.observable_counts] == list(ROBUSTNESS_EVALUATION_ORDER)
    assert all(count.evaluation_count == 0 for count in empty_group.observable_counts)


def test_group_order_follows_matching_report_with_a_non_exact_match_interleaved(triangle_s2, triangle_s3) -> None:
    high_group_0 = _fake_group(triangle_s3, group_index=0, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group_0 = _fake_group(triangle_s2, group_index=0, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match_0 = _fake_match(triangle_s3, triangle_s2, high_group_0, low_group_0)

    high_group_na = _fake_group(triangle_s3, group_index=2, documents=(_c_tt_conn_doc(-0.5, path=(0, 1)),))
    low_group_na = _fake_group(triangle_s2, group_index=2, documents=(_c_tt_conn_doc(-0.6, path=(0, 1)),))
    match_non_exact = _fake_match(triangle_s3, triangle_s2, high_group_na, low_group_na, status=AMBIGUOUS_CROSS_TRUNCATION_MATCH)

    high_group_1 = _fake_group(triangle_s3, group_index=1, documents=(_c_tt_conn_doc(-0.3, path=(0, 1)),))
    low_group_1 = _fake_group(triangle_s2, group_index=1, documents=(_c_tt_conn_doc(-0.4, path=(0, 1)),))
    match_1 = _fake_match(triangle_s3, triangle_s2, high_group_1, low_group_1)

    matching_report = _fake_matching_report(match_0, match_non_exact, match_1)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    assert synthesis.matching_count == 3
    assert synthesis.exact_match_count == 2
    assert len(synthesis.groups) == 2
    assert [g.high_group_index for g in synthesis.groups] == [0, 1]
    assert len(synthesis.couples) == 1
    assert len(synthesis.couples[0].groups) == 2


def test_group_synthesis_rejects_an_evaluation_from_a_different_group_of_the_same_couple(triangle_s2, triangle_s3) -> None:
    high_group_0 = _fake_group(triangle_s3, group_index=0, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group_0 = _fake_group(triangle_s2, group_index=0, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match_0 = _fake_match(triangle_s3, triangle_s2, high_group_0, low_group_0)

    high_group_1 = _fake_group(triangle_s3, group_index=1, documents=(_c_tt_conn_doc(-0.3, path=(0, 1)),))
    low_group_1 = _fake_group(triangle_s2, group_index=1, documents=(_c_tt_conn_doc(-0.4, path=(0, 1)),))
    match_1 = _fake_match(triangle_s3, triangle_s2, high_group_1, low_group_1)

    matching_report = _fake_matching_report(match_0, match_1)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    group_0_synthesis = synthesis.groups[0]
    group_1_evaluation = synthesis.groups[1].evaluations[0]

    with pytest.raises(ValueError, match="match_key mismatch"):
        dataclasses.replace(group_0_synthesis, evaluations=(group_1_evaluation,))


def test_group_synthesis_rejects_an_unevaluable_comparison_from_a_different_group_of_the_same_couple(triangle_s2, triangle_s3) -> None:
    high_group_0 = _fake_group(triangle_s3, group_index=0, documents=(_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),))
    low_group_0 = _fake_group(triangle_s2, group_index=0, documents=(_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),))
    match_0 = _fake_match(triangle_s3, triangle_s2, high_group_0, low_group_0)

    high_group_1 = _fake_group(triangle_s3, group_index=1, documents=(_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),))
    low_group_1 = _fake_group(triangle_s2, group_index=1, documents=(_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),))
    match_1 = _fake_match(triangle_s3, triangle_s2, high_group_1, low_group_1)

    matching_report = _fake_matching_report(match_0, match_1)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    group_0_synthesis = synthesis.groups[0]
    group_1_unevaluable = synthesis.groups[1].unevaluable_comparisons[0]

    with pytest.raises(ValueError, match="match_key mismatch"):
        dataclasses.replace(group_0_synthesis, unevaluable_comparisons=(group_1_unevaluable,))


def test_group_synthesis_requires_all_four_observable_kinds_in_fixed_order(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    group = synthesis.groups[0]
    with pytest.raises(ValueError, match="observable_counts must contain"):
        dataclasses.replace(group, observable_counts=group.observable_counts[:3])


def test_couple_synthesis_requires_all_four_observable_kinds_in_fixed_order(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    couple = synthesis.couples[0]
    with pytest.raises(ValueError, match="observable_counts must contain"):
        dataclasses.replace(couple, observable_counts=couple.observable_counts[:3])


def test_len_groups_equals_exact_match_count_invariant_is_enforced(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    with pytest.raises(ValueError, match="exact_match_count"):
        dataclasses.replace(synthesis, exact_match_count=synthesis.exact_match_count + 1)


# ---------------------------------------------------------------------------
# 1/2. Provenance conservation / rejection of incompatible provenance.
# ---------------------------------------------------------------------------


def test_provenance_is_conserved_exactly(triangle_s2, triangle_s3) -> None:
    _, matching_report, _, _, synthesis = _build_all(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    assert synthesis.campaign_id == matching_report.campaign_id
    assert synthesis.manifest_fingerprint == matching_report.manifest_fingerprint
    assert synthesis.repository_commit == matching_report.repository_commit


def test_incompatible_provenance_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match, campaign_id="campaign-A")
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    mismatched_comparison_report = dataclasses.replace(comparison_report, campaign_id="campaign-B")

    with pytest.raises(InterSSynthesisError, match="provenance"):
        build_inter_s_synthesis_report(matching_report, mismatched_comparison_report, robustness_report)


# ---------------------------------------------------------------------------
# 3/4/5/6. Full conservation of evaluations/unevaluable comparisons;
# global counts equal the sum of their own categories.
# ---------------------------------------------------------------------------


def test_all_evaluations_and_unevaluable_are_conserved(triangle_s2, triangle_s3) -> None:
    high_documents = (_rho_qq_doc(value=0.5, path=(0, 1)), _c_tt_conn_doc(-0.1, path=(0, 2)))
    low_documents = (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)), _c_tt_conn_doc(-0.2, path=(0, 2)))
    _, _, comparison_report, robustness_report, synthesis = _build_all(triangle_s2, triangle_s3, high_documents, low_documents)

    assert synthesis.source_comparison_count == len(comparison_report.comparisons)
    assert synthesis.evaluated_count == len(robustness_report.evaluations)
    assert synthesis.unevaluable_count == len(robustness_report.unevaluable_comparisons)
    assert synthesis.evaluated_count + synthesis.unevaluable_count == synthesis.source_comparison_count

    evaluated_ids_from_groups = {id(e) for group in synthesis.groups for e in group.evaluations}
    unevaluable_ids_from_groups = {id(c) for group in synthesis.groups for c in group.unevaluable_comparisons}
    assert evaluated_ids_from_groups == {id(e) for e in robustness_report.evaluations}
    assert unevaluable_ids_from_groups == {id(c) for c in robustness_report.unevaluable_comparisons}


def test_no_evaluation_is_double_counted_across_groups(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report, synthesis = _build_all(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    seen: set[int] = set()
    for group in synthesis.groups:
        for evaluation in group.evaluations:
            assert id(evaluation) not in seen
            seen.add(id(evaluation))
    assert seen == {id(e) for e in robustness_report.evaluations}


# ---------------------------------------------------------------------------
# 7/8/9. Per-observable/per-couple/per-group counts equal the sources.
# ---------------------------------------------------------------------------


def test_per_observable_counts_equal_sources(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report, synthesis = _build_all(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    for observable in synthesis.observables:
        expected = sum(1 for e in robustness_report.evaluations if e.observable_kind == observable.observable_kind)
        assert observable.evaluation_count == expected


def test_per_couple_counts_equal_sources(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report, synthesis = _build_all(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    assert len(synthesis.couples) == 1
    couple = synthesis.couples[0]
    assert couple.evaluation_count == len(robustness_report.evaluations)
    assert couple.unevaluable_count == len(robustness_report.unevaluable_comparisons)


def test_per_group_counts_equal_sources(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report, synthesis = _build_all(
        triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),)
    )
    assert len(synthesis.groups) == 1
    group = synthesis.groups[0]
    assert len(group.evaluations) == len(robustness_report.evaluations)
    assert len(group.unevaluable_comparisons) == len(robustness_report.unevaluable_comparisons)


# ---------------------------------------------------------------------------
# 10/11/12. Median correctness (even/odd cardinality); empty statistics.
# ---------------------------------------------------------------------------


def test_median_even_cardinality() -> None:
    stats = synthesis_module._descriptive_statistics((1.0, 2.0, 3.0, 4.0))
    assert stats.count == 4
    assert stats.median == pytest.approx(2.5)
    assert stats.minimum == 1.0
    assert stats.maximum == 4.0


def test_median_odd_cardinality() -> None:
    stats = synthesis_module._descriptive_statistics((1.0, 5.0, 2.0))
    assert stats.count == 3
    assert stats.median == 2.0
    assert stats.minimum == 1.0
    assert stats.maximum == 5.0


def test_empty_statistics_are_represented_with_none() -> None:
    stats = synthesis_module._descriptive_statistics(())
    assert stats.count == 0
    assert stats.minimum is None
    assert stats.maximum is None
    assert stats.median is None


def test_descriptive_statistics_rejects_inconsistent_none_pattern() -> None:
    with pytest.raises(ValueError, match="must all be None"):
        DescriptiveStatistics(count=0, minimum=1.0, maximum=None, median=None)
    with pytest.raises(ValueError, match="must all be set"):
        DescriptiveStatistics(count=1, minimum=None, maximum=None, median=None)


# ---------------------------------------------------------------------------
# 13/14. gamma_O null conserved independently of verdict; a source-null
# comparison is never turned into a verdict.
# ---------------------------------------------------------------------------


def test_gamma_o_null_conserved_independently_of_verdict(triangle_s2, triangle_s3) -> None:
    _, _, comparison_report, robustness_report, synthesis = _build_all(
        triangle_s2, triangle_s3, (_o_ij_raw_doc(0 + 0j, path=(0, 1)),), (_o_ij_raw_doc(0 + 0j, path=(0, 1)),)
    )
    gamma_o_synthesis = next(o for o in synthesis.observables if o.observable_kind == "gamma_O")
    assert gamma_o_synthesis.gamma_o.null_count == 1
    assert gamma_o_synthesis.gamma_o.defined_count == 0
    assert gamma_o_synthesis.verdicts.robust == 1
    assert gamma_o_synthesis.verdicts.indeterminate == 0

    group = synthesis.groups[0]
    assert group.evaluations[0].result.gamma_o.value is None
    assert group.evaluations[0].result.verdict == "robust"


def test_source_null_comparison_never_becomes_a_verdict(triangle_s2, triangle_s3) -> None:
    _, _, comparison_report, robustness_report, synthesis = _build_all(
        triangle_s2,
        triangle_s3,
        (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),),
        (_rho_qq_doc(value=0.4, path=(0, 1)),),
    )
    assert synthesis.evaluated_count == 0
    assert synthesis.unevaluable_count == 1
    assert synthesis.verdicts.total == 0
    rho_qq_synthesis = next(o for o in synthesis.observables if o.observable_kind == "rho_QQ")
    assert rho_qq_synthesis.unevaluable_count == 1
    assert rho_qq_synthesis.evaluation_count == 0
    group = synthesis.groups[0]
    assert len(group.unevaluable_comparisons) == 1
    assert group.unevaluable_comparisons[0].high_null_reason == "zero_local_charge_variance"


# ---------------------------------------------------------------------------
# 15. partial_subspace/indeterminate is conserved, never promoted or hidden.
# ---------------------------------------------------------------------------


def test_partial_subspace_indeterminate_is_conserved_without_promotion(triangle_s2, triangle_s3) -> None:
    _, _, _, robustness_report, synthesis = _build_all(
        triangle_s2,
        triangle_s3,
        (_c_tt_conn_doc(-0.1, path=(0, 1)),),
        (_c_tt_conn_doc(-0.2, path=(0, 1)),),
        group_status=PARTIAL_SUBSPACE,
    )
    group = synthesis.groups[0]
    assert group.match_status == EXACT_LABEL_MATCH
    assert group.verdicts.indeterminate == 1
    assert group.verdicts.robust == 0
    assert group.evaluations[0].result.null_reason == "truncated_spectral_group"

    c_tt_conn_synthesis = next(o for o in synthesis.observables if o.observable_kind == "C_TT_conn")
    assert c_tt_conn_synthesis.verdicts.indeterminate == 1
    assert synthesis.verdicts.indeterminate == 1


# ---------------------------------------------------------------------------
# 16/17/18/19. No forbidden calls/imports; no runs/ read.
# ---------------------------------------------------------------------------


def test_synthesis_module_never_imports_forbidden_entry_points() -> None:
    source = inspect.getsource(synthesis_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    for token in ("evaluate_robustness", "compute_gamma_o", "match_spectral_group", "run_single_case", "run_campaign", "launch_normative_campaign", "run_level1b_campaign"):
        assert token not in import_lines, f"synthesis.py must never import {token!r}"
        assert f"{token}(" not in source, f"synthesis.py must never call {token!r}"


def test_synthesis_module_never_reads_the_filesystem() -> None:
    source = inspect.getsource(synthesis_module)
    for forbidden in ("open(", "Path(", "load_case_records", "validate_existing_case_run"):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# 20. Determinism: rebuilding from the same source reports produces the
# same counts/keys/order (never compared via dataclass == directly,
# since InterSGroupMatch carries unhashable numpy fields deep inside).
# ---------------------------------------------------------------------------


def _summary(report: InterSSynthesisReport) -> tuple:
    return (
        report.matching_count,
        report.exact_match_count,
        report.source_comparison_count,
        report.evaluated_count,
        report.unevaluable_count,
        report.verdicts,
        tuple((c.high_case_id, c.low_case_id, len(c.groups), c.evaluation_count, c.unevaluable_count) for c in report.couples),
        tuple(
            (g.high_case_id, g.low_case_id, g.high_group_index, g.low_group_index, len(g.evaluations), len(g.unevaluable_comparisons))
            for g in report.groups
        ),
        tuple((o.observable_kind, o.evaluation_count, o.unevaluable_count, o.verdicts) for o in report.observables),
    )


def test_report_is_deterministic_for_identical_inputs(triangle_s2, triangle_s3) -> None:
    high_documents = (_rho_qq_doc(value=0.5, path=(0, 1)), _c_tt_conn_doc(-0.1, path=(0, 2)))
    low_documents = (_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)), _c_tt_conn_doc(-0.2, path=(0, 2)))
    high_group = _fake_group(triangle_s3, documents=high_documents)
    low_group = _fake_group(triangle_s2, documents=low_documents)
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group)
    matching_report = _fake_matching_report(match)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)

    first = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)
    second = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    assert _summary(first) == _summary(second)


# ---------------------------------------------------------------------------
# Order: couples/groups follow comparison_report.comparisons' own order.
# ---------------------------------------------------------------------------


def test_group_and_couple_order_follows_the_matching_report(triangle_s2, triangle_s3) -> None:
    high_group_0 = _fake_group(triangle_s3, group_index=0, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group_0 = _fake_group(triangle_s2, group_index=0, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    high_group_1 = _fake_group(triangle_s3, group_index=1, documents=(_c_tt_conn_doc(-0.3, path=(0, 1)),))
    low_group_1 = _fake_group(triangle_s2, group_index=1, documents=(_c_tt_conn_doc(-0.4, path=(0, 1)),))
    match_0 = _fake_match(triangle_s3, triangle_s2, high_group_0, low_group_0)
    match_1 = _fake_match(triangle_s3, triangle_s2, high_group_1, low_group_1)
    matching_report = _fake_matching_report(match_0, match_1)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    assert [g.high_group_index for g in synthesis.groups] == [0, 1]
    assert len(synthesis.couples) == 1
    assert len(synthesis.couples[0].groups) == 2


# ---------------------------------------------------------------------------
# Public-constructor hardening: reject a list where a tuple is required,
# and an element of the wrong type.
# ---------------------------------------------------------------------------


def test_report_rejects_a_list_for_groups(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    with pytest.raises(ValueError, match="must be a tuple"):
        dataclasses.replace(synthesis, groups=list(synthesis.groups))


def test_report_rejects_a_wrong_element_type_in_couples(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    with pytest.raises(ValueError, match="InterSCoupleSynthesis"):
        dataclasses.replace(synthesis, couples=("not-a-couple",))


def test_group_synthesis_rejects_a_list_for_evaluations(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    group = synthesis.groups[0]
    with pytest.raises(ValueError, match="must be a tuple"):
        dataclasses.replace(group, evaluations=list(group.evaluations))


def test_verdict_counts_rejects_negative_and_bool() -> None:
    with pytest.raises(ValueError):
        VerdictCounts(robust=-1, non_robust=0, indeterminate=0)
    with pytest.raises(ValueError):
        VerdictCounts(robust=True, non_robust=0, indeterminate=0)


def test_gamma_o_statistics_rejects_mismatched_defined_count() -> None:
    with pytest.raises(ValueError, match="defined_count"):
        GammaOStatistics(defined_count=2, null_count=0, values=DescriptiveStatistics(count=1, minimum=0.1, maximum=0.1, median=0.1))


def test_observable_synthesis_rejects_verdicts_total_mismatch(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    observable = next(o for o in synthesis.observables if o.observable_kind == "C_TT_conn")
    with pytest.raises(ValueError, match="verdicts.total"):
        dataclasses.replace(observable, evaluation_count=observable.evaluation_count + 1)


def test_couple_synthesis_rejects_evaluation_count_mismatch(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    couple = synthesis.couples[0]
    with pytest.raises(ValueError, match="evaluation_count"):
        dataclasses.replace(couple, evaluation_count=couple.evaluation_count + 1)


def test_observables_must_be_in_the_fixed_order(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    reversed_observables = tuple(reversed(synthesis.observables))
    with pytest.raises(ValueError, match="fixed order"):
        dataclasses.replace(synthesis, observables=reversed_observables)


def test_robustness_evaluation_order_matches_the_documented_four_observables() -> None:
    assert ROBUSTNESS_EVALUATION_ORDER == ("gamma_O", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio")


# ---------------------------------------------------------------------------
# Immutability.
# ---------------------------------------------------------------------------


def test_synthesis_report_is_immutable(triangle_s2, triangle_s3) -> None:
    _, _, _, _, synthesis = _build_all(triangle_s2, triangle_s3, (_c_tt_conn_doc(-0.1, path=(0, 1)),), (_c_tt_conn_doc(-0.2, path=(0, 1)),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        synthesis.groups = ()


# ---------------------------------------------------------------------------
# End-to-end: real pipeline (write/load/index/match/compare/evaluate/
# synthesize), not just hand-built documents.
# ---------------------------------------------------------------------------


def test_real_pipeline_end_to_end(monkeypatch, real_manifest, triangle_s2, triangle_s3, tmp_path) -> None:
    from cosmobox.level1.assembly import assemble_execution
    from cosmobox.level1.local_observables import NormalizedMoment
    from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity
    from cosmobox.level1.results import build_result_record as _build_result_record_impl
    from cosmobox.level1.serialization import serialize_result_record
    from scripts.level1b_campaign.outputs import write_case_success
    from scripts.level1b_campaign.runner import CaseExecutionResult
    from scripts.level1b_analysis.indexing import build_campaign_artifact_index
    from scripts.level1b_analysis.inter_s import build_inter_s_matching_report

    def build_result_record(*args, **kwargs):
        kwargs.setdefault("scientific_seed", 1001)
        kwargs.setdefault("solver_seed", 2002)
        return _build_result_record_impl(*args, **kwargs)

    def hamiltonian_identity(case) -> HamiltonianIdentity:
        return HamiltonianIdentity(
            J=case.hamiltonian_parameters.J, h_is_zero=True, t=case.hamiltonian_parameters.t, g_E=case.hamiltonian_parameters.g_E, K=case.hamiltonian_parameters.K
        )

    def document(case, group, *, record_kind, observable_kind, payload, path=None, flavor_component=None, normalization=None):
        identity = ScientificIdentity(
            geometry=case.geometry, spin=case.spin, n_flavors=2, hamiltonian=hamiltonian_identity(case), sector=case.sector_id,
            spectral_group=group, path=path, flavor_component=flavor_component, normalization=normalization,
        )
        record = build_result_record(
            identity, record_kind, observable_kind, payload, scientific_seed=case.scientific_seed, solver_seed=case.solver_seed,
            validation_rotation_seed=case.validation_rotation_seed,
        )
        return serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint=real_manifest.fingerprint, campaign_id=real_manifest.campaign_id)

    def symmetry_document(case, group, observable_kind, label):
        identity = ScientificIdentity(
            geometry=case.geometry, spin=case.spin, n_flavors=2, hamiltonian=hamiltonian_identity(case), sector=case.sector_id,
            spectral_group=group, path=None, flavor_component=None, normalization=None,
        )
        record = build_result_record(
            identity, "symmetry_label", observable_kind, label, scientific_seed=case.scientific_seed, solver_seed=case.solver_seed,
            validation_rotation_seed=case.validation_rotation_seed,
        )
        return serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint=real_manifest.fingerprint, campaign_id=real_manifest.campaign_id)

    group0 = SpectralGroupIdentity(status=COMPLETE_MULTIPLET, multiplicity=1, twice_T=1, spectral_window_group_index=0, representative_energy=-1.0)

    def case_documents(case, c_tt_value: float):
        documents = [
            symmetry_document(case, group0, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))),
            symmetry_document(case, group0, "translation_character", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))),
            symmetry_document(case, group0, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0))),
            document(case, group0, record_kind="raw_observable", observable_kind="C_TT_conn", payload=c_tt_value, path=(0, 1)),
            document(case, group0, record_kind="normalized_observable", observable_kind="rho_QQ", payload=NormalizedMoment(value=0.3, null_reason=None), path=(0, 1)),
        ]
        return documents

    def write_case(output_dir, case, documents):
        assembled, report = assemble_execution(documents)
        result = CaseExecutionResult(case_id=case.case_id, target_outcomes=(), documents=assembled, assembly_report=report)
        write_case_success(output_dir, result)

    write_case(tmp_path, triangle_s3, case_documents(triangle_s3, -0.05))
    write_case(tmp_path, triangle_s2, case_documents(triangle_s2, -0.04))
    monkeypatch.setattr(loader_module, "build_campaign_plan", lambda manifest_arg: (triangle_s2, triangle_s3))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    matching_report = build_inter_s_matching_report(index)
    comparison_report = build_inter_s_observable_comparison_report(matching_report)
    robustness_report = build_inter_s_robustness_report(matching_report, comparison_report)
    synthesis = build_inter_s_synthesis_report(matching_report, comparison_report, robustness_report)

    assert synthesis.campaign_id == real_manifest.campaign_id
    assert synthesis.repository_commit == REPO_COMMIT
    assert synthesis.matching_count == 1
    assert synthesis.exact_match_count == 1
    assert synthesis.evaluated_count == synthesis.source_comparison_count
    assert synthesis.unevaluable_count == 0
    assert len(synthesis.couples) == 1
    assert len(synthesis.groups) == 1
