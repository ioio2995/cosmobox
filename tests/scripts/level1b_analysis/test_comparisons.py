from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest

from cosmobox.level1.assembly import assemble_execution
from cosmobox.level1.local_observables import NORMALIZATION_FLOOR, NormalizedMoment
from cosmobox.level1.matching import (
    AMBIGUOUS_CROSS_TRUNCATION_MATCH,
    EXACT_LABEL_MATCH,
    MatchOutcome,
    SpectralGroupMatchKey,
    SymmetryLabel,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.robustness import compute_gamma_o
from cosmobox.level1.serialization import serialize_result_record
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_campaign.outputs import write_case_success
from scripts.level1b_campaign.runner import CaseExecutionResult
from scripts.level1b_analysis import comparisons as comparisons_module
from scripts.level1b_analysis import loader as loader_module
from scripts.level1b_analysis.comparisons import (
    GammaOComparison,
    InterSObservableComparisonError,
    InterSObservableComparisonReport,
    ScalarObservableComparison,
    build_inter_s_observable_comparison_report,
)
from scripts.level1b_analysis.indexing import IndexedSpectralGroup, build_campaign_artifact_index
from scripts.level1b_analysis.inter_s import InterSGroupMatch, InterSMatchingReport, build_inter_s_matching_report

REPO_COMMIT = "d" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "evaluate_robustness",
    "run_single_case",
    "run_campaign",
    "launch_normative_campaign",
    "run_level1b_campaign",
)


# ---------------------------------------------------------------------------
# Fixtures -- same pattern as test_inter_s.py.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def real_plan(real_manifest: manifest_module.Manifest) -> tuple:
    return planning_module.build_campaign_plan(real_manifest)


def _case(real_plan: tuple, *, geometry: str = "triangle", spin: int = 1, hamiltonian_case_id: str = "reference"):
    return next(
        c for c in real_plan if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture
def triangle_s2(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=2)


@pytest.fixture
def triangle_s3(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=3)


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: tuple) -> None:
    monkeypatch.setattr(loader_module, "build_campaign_plan", lambda manifest_arg: plan)


def build_result_record(*args, **kwargs):
    kwargs.setdefault("scientific_seed", 1001)
    kwargs.setdefault("solver_seed", 2002)
    return _build_result_record_impl(*args, **kwargs)


def _hamiltonian_identity(case) -> HamiltonianIdentity:
    return HamiltonianIdentity(
        J=case.hamiltonian_parameters.J,
        h_is_zero=True,
        t=case.hamiltonian_parameters.t,
        g_E=case.hamiltonian_parameters.g_E,
        K=case.hamiltonian_parameters.K,
    )


def _group(index: int, *, twice_T: int = 1, multiplicity: int = 1, status: str = COMPLETE_MULTIPLET, energy: float = -1.0):
    return SpectralGroupIdentity(
        status=status, multiplicity=multiplicity, twice_T=twice_T, spectral_window_group_index=index, representative_energy=energy
    )


def _document(case, group, *, record_kind, observable_kind, payload, path=None, flavor_component=None, normalization=None, manifest) -> dict:
    identity = ScientificIdentity(
        geometry=case.geometry,
        spin=case.spin,
        n_flavors=2,
        hamiltonian=_hamiltonian_identity(case),
        sector=case.sector_id,
        spectral_group=group,
        path=path,
        flavor_component=flavor_component,
        normalization=normalization,
    )
    record = build_result_record(
        identity,
        record_kind,
        observable_kind,
        payload,
        scientific_seed=case.scientific_seed,
        solver_seed=case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed,
    )
    return serialize_result_record(
        record, repository_commit=REPO_COMMIT, manifest_fingerprint=manifest.fingerprint, campaign_id=manifest.campaign_id
    )


def _symmetry_document(case, group, observable_kind: str, label: SymmetryLabel, *, manifest) -> dict:
    identity = ScientificIdentity(
        geometry=case.geometry,
        spin=case.spin,
        n_flavors=2,
        hamiltonian=_hamiltonian_identity(case),
        sector=case.sector_id,
        spectral_group=group,
        path=None,
        flavor_component=None,
        normalization=None,
    )
    record = build_result_record(
        identity,
        "symmetry_label",
        observable_kind,
        label,
        scientific_seed=case.scientific_seed,
        solver_seed=case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed,
    )
    return serialize_result_record(
        record, repository_commit=REPO_COMMIT, manifest_fingerprint=manifest.fingerprint, campaign_id=manifest.campaign_id
    )


def _group_level_documents(case, group, *, manifest) -> list[dict]:
    """The three mandatory group-level symmetry labels indexing.py
    requires to accept a group -- nothing else."""
    return [
        _symmetry_document(case, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(group.twice_T, 0.0)), manifest=manifest),
        _symmetry_document(case, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=manifest),
        _symmetry_document(case, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=manifest),
    ]


def _write_case(output_dir: Path, case, documents: list[dict]) -> None:
    assembled, report = assemble_execution(documents)
    result = CaseExecutionResult(case_id=case.case_id, target_outcomes=(), documents=assembled, assembly_report=report)
    write_case_success(output_dir, result)


# ---------------------------------------------------------------------------
# Hand-built fixtures: a document dict shaped exactly like an already-
# frozen, already-serialized real one (freezing via loader_module.
# _freeze_document, the same already-accepted primitive 1B-9b uses) --
# lets every structural-error/edge-case scenario be tested directly
# against comparisons.py's own logic, without a full write/load/index
# round trip for every case.
# ---------------------------------------------------------------------------


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


def _flavor_ratio_doc(*, value: float | None = None, null_reason: str | None = None, **kwargs):
    return _doc(
        record_kind="flavor_diagnostic", observable_kind="flavor_singular_value_ratio", payload={"value": value, "null_reason": null_reason}, **kwargs
    )


def _dummy_match_key(case, *, twice_T: int = 1) -> SpectralGroupMatchKey:
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
        status=COMPLETE_MULTIPLET,
        multiplicity=1,
        twice_T=twice_T,
        translation_label=SymmetryLabel(kind="not_applicable", value=None),
        reflection_label=SymmetryLabel(kind="not_applicable", value=None),
    )


def _fake_group(case, *, group_index: int = 0, documents: tuple) -> IndexedSpectralGroup:
    return IndexedSpectralGroup(
        case_id=case.case_id,
        case=case,
        spectral_group_identity=_group(group_index),
        spectral_window_group_index=group_index,
        match_key=_dummy_match_key(case),
        documents=documents,
    )


def _fake_match(high_case, low_case, high_group: IndexedSpectralGroup, low_group: IndexedSpectralGroup | None, *, status: str = EXACT_LABEL_MATCH) -> InterSGroupMatch:
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


def _fake_report(match: InterSGroupMatch, *, campaign_id: str = "test-campaign", manifest_fingerprint: str = "f" * 64, repository_commit: str = REPO_COMMIT) -> InterSMatchingReport:
    return InterSMatchingReport(campaign_id=campaign_id, manifest_fingerprint=manifest_fingerprint, repository_commit=repository_commit, matches=(match,))


# ---------------------------------------------------------------------------
# 1/2/3/4. O_ij_raw comparability axes: path/flavor_component/
# normalization must ALL match exactly, or the eligible high document is
# a structural error (never a silently wrong association).
# ---------------------------------------------------------------------------


def test_o_ij_raw_same_axes_creates_a_pair(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(1 + 2j, path=(0, 1), flavor_component="alpha0_beta0"),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(1.1 + 1.9j, path=(0, 1), flavor_component="alpha0_beta0"),))
    report = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))

    assert len(report.comparisons) == 1
    comparison = report.comparisons[0]
    assert isinstance(comparison, GammaOComparison)
    assert comparison.high_value == 1 + 2j
    assert comparison.low_value == 1.1 + 1.9j


def test_o_ij_raw_different_path_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(1 + 2j, path=(0, 1), flavor_component="alpha0_beta0"),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(1.1 + 1.9j, path=(0, 2), flavor_component="alpha0_beta0"),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


def test_o_ij_raw_different_flavor_component_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(1 + 2j, path=(0, 1), flavor_component="alpha0_beta0"),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(1.1 + 1.9j, path=(0, 1), flavor_component="alpha0_beta1"),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


def test_o_ij_raw_different_normalization_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(1 + 2j, path=(0, 1), flavor_component="a", normalization=None),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(1.1 + 1.9j, path=(0, 1), flavor_component="a", normalization="raw_G"),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


# ---------------------------------------------------------------------------
# 5/6/7. compute_gamma_o is really used (not reimplemented); a normal
# numeric case; the floor -> null case.
# ---------------------------------------------------------------------------


def test_gamma_o_uses_the_real_compute_gamma_o_primitive(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(2 + 0j, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(1 + 0j, path=(0, 1)),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    expected = compute_gamma_o(2 + 0j, 1 + 0j)
    assert comparison.gamma_o == expected
    assert comparison.gamma_o.value == pytest.approx(0.5)


def test_gamma_o_below_floor_is_null_with_exact_reason(triangle_s2, triangle_s3) -> None:
    tiny = NORMALIZATION_FLOOR / 10
    high_group = _fake_group(triangle_s3, documents=(_o_ij_raw_doc(complex(tiny, 0.0), path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_o_ij_raw_doc(0 + 0j, path=(0, 1)),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    assert comparison.gamma_o.value is None
    assert comparison.gamma_o.null_reason == "normalization_denominator_below_floor"


# ---------------------------------------------------------------------------
# 8/9/17. rho_QQ: exact path required, (i,j) != (j,i); duplicate low key
# raises.
# ---------------------------------------------------------------------------


def test_rho_qq_exact_path_creates_a_pair(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_rho_qq_doc(value=0.5, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_rho_qq_doc(value=0.4, path=(0, 1)),))
    comparisons = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons
    assert len(comparisons) == 1
    assert isinstance(comparisons[0], ScalarObservableComparison)
    assert comparisons[0].high_value == 0.5
    assert comparisons[0].low_value == 0.4


def test_rho_qq_inverted_path_is_not_the_same_key(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_rho_qq_doc(value=0.5, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_rho_qq_doc(value=0.4, path=(1, 0)),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


def test_duplicate_low_key_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_rho_qq_doc(value=0.5, path=(0, 1)),))
    low_group = _fake_group(
        triangle_s2,
        documents=(
            _rho_qq_doc(value=0.4, path=(0, 1)),
            _rho_qq_doc(value=0.45, path=(0, 1)),  # same comparability key, distinct value
        ),
    )
    with pytest.raises(InterSObservableComparisonError, match="duplicate low"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


# ---------------------------------------------------------------------------
# 10. C_TT_conn: same axis rules, bare float payload (never null).
# ---------------------------------------------------------------------------


def test_c_tt_conn_exact_axes_creates_a_pair(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.12, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.11, path=(0, 1)),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    assert comparison.high_value == -0.12
    assert comparison.low_value == -0.11
    assert comparison.high_null_reason is None
    assert comparison.low_null_reason is None


# ---------------------------------------------------------------------------
# 11/12/13. flavor_singular_value_ratio is path-dependent: same endpoints
# but a different internal path is NOT comparable; normalization is part
# of the comparability key too.
# ---------------------------------------------------------------------------


def test_flavor_ratio_requires_the_full_identical_path(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_flavor_ratio_doc(value=0.9, path=(0, 1), normalization="raw_G"),))
    low_group = _fake_group(triangle_s2, documents=(_flavor_ratio_doc(value=0.8, path=(0, 1), normalization="raw_G"),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]
    assert comparison.high_value == 0.9
    assert comparison.low_value == 0.8


def test_flavor_ratio_same_endpoints_different_internal_path_is_not_comparable(triangle_s2, triangle_s3) -> None:
    # Same (start, end) = (0, 2), but a different, longer internal path --
    # formally forbidden to reduce to just the endpoints.
    high_group = _fake_group(triangle_s3, documents=(_flavor_ratio_doc(value=0.9, path=(0, 2), normalization="raw_G"),))
    low_group = _fake_group(triangle_s2, documents=(_flavor_ratio_doc(value=0.8, path=(0, 1, 2), normalization="raw_G"),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


def test_flavor_ratio_normalization_axis_is_enforced(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_flavor_ratio_doc(value=0.9, path=(0, 1), normalization="raw_G"),))
    low_group = _fake_group(triangle_s2, documents=(_flavor_ratio_doc(value=0.8, path=(0, 1), normalization=None),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


# ---------------------------------------------------------------------------
# 14/15/16. null high/low conserved exactly, never replaced by 0 or an
# epsilon.
# ---------------------------------------------------------------------------


def test_null_high_value_is_conserved_exactly(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_rho_qq_doc(null_reason="zero_local_charge_variance", path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_rho_qq_doc(value=0.4, path=(0, 1)),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    assert comparison.high_value is None
    assert comparison.high_null_reason == "zero_local_charge_variance"
    assert comparison.low_value == 0.4


def test_null_low_value_is_conserved_exactly(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_flavor_ratio_doc(value=0.9, path=(0, 1), normalization="raw_G"),))
    low_group = _fake_group(
        triangle_s2, documents=(_flavor_ratio_doc(null_reason="normalization_denominator_below_floor", path=(0, 1), normalization="raw_G"),)
    )
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    assert comparison.low_value is None
    assert comparison.low_null_reason == "normalization_denominator_below_floor"
    assert comparison.high_value == 0.9
    # Never silently substituted:
    assert comparison.low_value != 0.0


# ---------------------------------------------------------------------------
# 18. High eligible without a matching low document raises.
# ---------------------------------------------------------------------------


def test_high_without_matching_low_raises(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 2)),))
    with pytest.raises(InterSObservableComparisonError, match="no low document"):
        build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))


# ---------------------------------------------------------------------------
# 20. A non-exact match produces no comparison at all.
# ---------------------------------------------------------------------------


def test_non_exact_match_produces_no_comparison(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    match = _fake_match(triangle_s3, triangle_s2, high_group, low_group, status=AMBIGUOUS_CROSS_TRUNCATION_MATCH)

    report = build_inter_s_observable_comparison_report(_fake_report(match))

    assert report.comparisons == ()


# ---------------------------------------------------------------------------
# 21/22/23/24/25. Provenance and identity conservation.
# ---------------------------------------------------------------------------


def test_high_low_case_and_group_identity_are_conserved(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    comparison = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons[0]

    assert comparison.high_case_id == triangle_s3.case_id
    assert comparison.low_case_id == triangle_s2.case_id
    assert comparison.high_group is high_group
    assert comparison.low_group is low_group


def test_report_provenance_is_conserved_from_the_matching_report(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    matching_report = _fake_report(
        _fake_match(triangle_s3, triangle_s2, high_group, low_group),
        campaign_id="level1b-reference-v1",
        manifest_fingerprint="1" * 64,
        repository_commit="0ff65ac66b4aa054f739b350cd384c26ecd19752",
    )

    report = build_inter_s_observable_comparison_report(matching_report)

    assert report.campaign_id == "level1b-reference-v1"
    assert report.manifest_fingerprint == "1" * 64
    assert report.repository_commit == "0ff65ac66b4aa054f739b350cd384c26ecd19752"


# ---------------------------------------------------------------------------
# 26. Deterministic order: follows high_group.documents order exactly,
# interleaving GammaOComparison/ScalarObservableComparison as they occur.
# ---------------------------------------------------------------------------


def test_order_follows_high_group_documents_order(triangle_s2, triangle_s3) -> None:
    high_documents = (
        _rho_qq_doc(value=0.5, path=(0, 1)),
        _o_ij_raw_doc(1 + 1j, path=(0, 1), flavor_component="a"),
        _c_tt_conn_doc(-0.1, path=(0, 1)),
    )
    low_documents = (
        _c_tt_conn_doc(-0.2, path=(0, 1)),
        _o_ij_raw_doc(0.9 + 0.9j, path=(0, 1), flavor_component="a"),
        _rho_qq_doc(value=0.4, path=(0, 1)),
    )
    high_group = _fake_group(triangle_s3, documents=high_documents)
    low_group = _fake_group(triangle_s2, documents=low_documents)

    comparisons = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group))).comparisons

    kinds = [type(c).__name__ for c in comparisons]
    assert kinds == ["ScalarObservableComparison", "GammaOComparison", "ScalarObservableComparison"]
    assert comparisons[0].high_value == 0.5
    assert comparisons[2].high_value == -0.1


# ---------------------------------------------------------------------------
# 27/28/29/30. No target_id; no evaluate_robustness/verdict/threshold
# anywhere in the API; no forbidden runner/campaign/launcher import.
# ---------------------------------------------------------------------------


def test_no_target_id_field_anywhere_in_comparisons_api() -> None:
    for cls in (GammaOComparison, ScalarObservableComparison, InterSObservableComparisonReport):
        assert "target_id" not in {f.name for f in dataclasses.fields(cls)}


def test_no_verdict_or_threshold_field_anywhere_in_comparisons_api() -> None:
    forbidden_field_names = {"verdict", "threshold", "robust", "non_robust", "indeterminate"}
    for cls in (GammaOComparison, ScalarObservableComparison, InterSObservableComparisonReport):
        field_names = {f.name for f in dataclasses.fields(cls)}
        assert field_names.isdisjoint(forbidden_field_names)


def test_comparisons_module_never_imports_forbidden_entry_points() -> None:
    source = inspect.getsource(comparisons_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    for token in _FORBIDDEN_IMPORT_TOKENS:
        assert token not in import_lines, f"comparisons.py must never import {token!r}"
    assert "def evaluate_robustness" not in source


# ---------------------------------------------------------------------------
# 31. Result objects are immutable.
# ---------------------------------------------------------------------------


def test_result_objects_are_immutable(triangle_s2, triangle_s3) -> None:
    high_group = _fake_group(triangle_s3, documents=(_c_tt_conn_doc(-0.1, path=(0, 1)),))
    low_group = _fake_group(triangle_s2, documents=(_c_tt_conn_doc(-0.2, path=(0, 1)),))
    report = build_inter_s_observable_comparison_report(_fake_report(_fake_match(triangle_s3, triangle_s2, high_group, low_group)))
    comparison = report.comparisons[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        comparison.high_value = 999.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.comparisons = ()


# ---------------------------------------------------------------------------
# 19. End-to-end nominal scenario over the real write/load/index/match
# pipeline (not hand-built documents): all 4 target observable_kinds,
# genuine O_ij_raw disambiguation against a real orbit_statistic record
# sharing the exact same observable_kind/path/flavor_component.
# ---------------------------------------------------------------------------


def test_real_pipeline_end_to_end(monkeypatch, real_manifest, triangle_s2, triangle_s3, tmp_path: Path) -> None:
    group0 = _group(0, twice_T=1)

    def _case_documents(case, o_ij_high_low_value: complex):
        documents = list(_group_level_documents(case, group0, manifest=real_manifest))
        documents.append(_document(case, group0, record_kind="raw_observable", observable_kind="O_ij_raw", payload=o_ij_high_low_value, path=(0, 1), flavor_component="alpha0_beta0", manifest=real_manifest))
        documents.append(_document(case, group0, record_kind="normalized_observable", observable_kind="rho_QQ", payload=NormalizedMoment(value=0.3, null_reason=None), path=(0, 1), manifest=real_manifest))
        documents.append(_document(case, group0, record_kind="raw_observable", observable_kind="C_TT_conn", payload=-0.05, path=(0, 1), manifest=real_manifest))
        documents.append(
            _document(
                case,
                group0,
                record_kind="flavor_diagnostic",
                observable_kind="flavor_singular_value_ratio",
                payload=NormalizedMoment(value=0.95, null_reason=None),
                path=(0, 1),
                normalization="raw_G",
                manifest=real_manifest,
            )
        )
        return documents

    _write_case(tmp_path, triangle_s3, _case_documents(triangle_s3, 1.0 + 0j))
    _write_case(tmp_path, triangle_s2, _case_documents(triangle_s2, 0.9 + 0j))
    _patch_plan(monkeypatch, (triangle_s2, triangle_s3))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    matching_report = build_inter_s_matching_report(index)
    assert len(matching_report.matches) == 1
    assert matching_report.matches[0].outcome.status == EXACT_LABEL_MATCH

    report = build_inter_s_observable_comparison_report(matching_report)

    assert isinstance(report, InterSObservableComparisonReport)
    by_kind: dict[str, list] = {}
    for comparison in report.comparisons:
        kind = "O_ij_raw" if isinstance(comparison, GammaOComparison) else comparison.observable_kind
        by_kind.setdefault(kind, []).append(comparison)

    assert len(by_kind["O_ij_raw"]) == 1
    assert by_kind["O_ij_raw"][0].high_value == 1.0 + 0j
    assert by_kind["O_ij_raw"][0].low_value == 0.9 + 0j
    assert by_kind["O_ij_raw"][0].gamma_o.value == pytest.approx(0.1)
    assert len(by_kind["rho_QQ"]) == 1
    assert len(by_kind["C_TT_conn"]) == 1
    assert len(by_kind["flavor_singular_value_ratio"]) == 1
