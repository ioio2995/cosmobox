from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
from types import MappingProxyType

import pytest

from cosmobox.level1.assembly import assemble_execution
from cosmobox.level1.matching import EXACT_LABEL_MATCH, MatchOutcome, SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.serialization import serialize_result_record
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_campaign.outputs import write_case_success
from scripts.level1b_campaign.runner import CaseExecutionResult
from scripts.level1b_analysis import inter_s as inter_s_module
from scripts.level1b_analysis import loader as loader_module
from scripts.level1b_analysis.indexing import CampaignArtifactIndex, build_campaign_artifact_index
from scripts.level1b_analysis.inter_s import (
    InterSGroupMatch,
    InterSMatchingError,
    InterSMatchingReport,
    build_inter_s_matching_report,
)
from scripts.level1b_analysis.loader import LoadedCase

REPO_COMMIT = "d" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "evaluate_robustness",
    "compute_gamma_o",
    "run_single_case",
    "run_campaign",
    "launch_normative_campaign",
)


# ---------------------------------------------------------------------------
# Fixtures -- same pattern as test_loader_and_indexing.py: real
# CampaignCaseSpec objects from the real manifest, a monkeypatched
# build_campaign_plan, small synthetic documents built via the real
# results.py/serialization.py primitives (never a diagonalization),
# written to disk via the real, already-accepted write_case_success.
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
def triangle_s1(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=1)


@pytest.fixture
def triangle_s2(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=2)


@pytest.fixture
def triangle_s2_j_break(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=2, hamiltonian_case_id="j_break")


@pytest.fixture
def triangle_s3(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=3)


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: tuple) -> None:
    monkeypatch.setattr(loader_module, "build_campaign_plan", lambda manifest_arg: plan)


def _replace_case(case, **overrides):
    """Like dataclasses.replace, but always supplies a matching case_id in
    the SAME replace call -- CampaignCaseSpec.__post_init__ enforces
    case_id == compute_case_id(...) over (geometry, spin,
    hamiltonian_case_id, hamiltonian_parameters, sector_id,
    spectral_window, target_groups) on every construction, including an
    intermediate dataclasses.replace call, so the new case_id must be
    computed from the MERGED field set up front and passed alongside the
    other overrides in one shot. physical_dimension/spectrum_options are
    not part of that hash, so overriding them alone still needs no
    case_id change -- computed here regardless, for uniformity."""
    merged = {field.name: overrides.get(field.name, getattr(case, field.name)) for field in dataclasses.fields(case)}
    new_case_id = planning_module.compute_case_id(
        geometry=merged["geometry"],
        spin=merged["spin"],
        hamiltonian_case_id=merged["hamiltonian_case_id"],
        hamiltonian_parameters=merged["hamiltonian_parameters"],
        sector_id=merged["sector_id"],
        spectral_window=merged["spectral_window"],
        target_groups=merged["target_groups"],
    )
    return dataclasses.replace(case, **overrides, case_id=new_case_id)


def _fake_index_from_cases(real_manifest, cases: tuple) -> CampaignArtifactIndex:
    """A CampaignArtifactIndex carrying real CampaignCaseSpec objects but
    no real groups/documents -- LoadedCase.__post_init__ only requires a
    non-empty tuple of deeply frozen documents, and CampaignArtifactIndex.
    __post_init__ only requires non-duplicate case_ids/group keys, so this
    is sufficient (and much cheaper than writing real records.jsonl) to
    unit-test _build_case_pairs, which only ever reads index.cases."""
    dummy_document = MappingProxyType({"dummy": True})
    loaded_cases = tuple(LoadedCase(case=case, documents=(dummy_document,)) for case in cases)
    return CampaignArtifactIndex(
        manifest_fingerprint=real_manifest.fingerprint,
        campaign_id=real_manifest.campaign_id,
        repository_commit=REPO_COMMIT,
        cases=loaded_cases,
        groups=(),
    )


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


def _document(case, group, *, record_kind, observable_kind, payload, path=None, manifest) -> dict:
    identity = ScientificIdentity(
        geometry=case.geometry,
        spin=case.spin,
        n_flavors=2,
        hamiltonian=_hamiltonian_identity(case),
        sector=case.sector_id,
        spectral_group=group,
        path=path,
        flavor_component=None,
        normalization=None,
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


def _default_group_documents(case, group, *, manifest, translation: float = 1.0, reflection: float = 2.0) -> list[dict]:
    """The three mandatory group-level symmetry labels for `group`, plus
    one ordinary observable record -- everything indexing.py requires to
    accept the group, with translation/reflection tunable so a test can
    control whether two groups (possibly in different cases) are label-
    identical (and therefore an exact_label_match candidate) or not."""
    return [
        _symmetry_document(case, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(group.twice_T, 0.0)), manifest=manifest),
        _symmetry_document(case, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(translation, 0.0)), manifest=manifest),
        _symmetry_document(case, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(reflection, 0.0)), manifest=manifest),
        _document(case, group, record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.25, path=(0,), manifest=manifest),
    ]


def _write_case(output_dir: Path, case, documents: list[dict]) -> None:
    assembled, report = assemble_execution(documents)
    result = CaseExecutionResult(case_id=case.case_id, target_outcomes=(), documents=assembled, assembly_report=report)
    write_case_success(output_dir, result)


# ---------------------------------------------------------------------------
# 1/3/4/5/6/9/10/11/12/13/14/15. End-to-end scenario over one geometry
# (triangle): S1/S2/S3 reference plus S2 j_break, all real cases. Proves:
# only the two largest spins (S3, S2) are paired, never S1; j_break is
# never mixed in; a real match_spectral_group call resolves an exact
# match to exactly one concrete low-side group and reports a genuine
# non-exact outcome (no candidate at the right twice_T) as low_group=None;
# high_group identity, provenance, and both orderings are preserved.
# ---------------------------------------------------------------------------


def test_triangle_couple_end_to_end(monkeypatch, real_manifest, triangle_s1, triangle_s2, triangle_s2_j_break, triangle_s3, tmp_path: Path) -> None:
    group_s1 = _group(0, twice_T=1)
    documents_s1 = _default_group_documents(triangle_s1, group_s1, manifest=real_manifest)

    group_s2_match = _group(0, twice_T=1)
    documents_s2 = _default_group_documents(triangle_s2, group_s2_match, manifest=real_manifest)

    group_jbreak = _group(0, twice_T=1)
    documents_jbreak = _default_group_documents(triangle_s2_j_break, group_jbreak, manifest=real_manifest)

    group_s3_match = _group(0, twice_T=1)  # exact-matches group_s2_match
    group_s3_unmatched = _group(1, twice_T=77)  # no twice_T=77 candidate exists at S2
    documents_s3 = _default_group_documents(triangle_s3, group_s3_match, manifest=real_manifest) + _default_group_documents(
        triangle_s3, group_s3_unmatched, manifest=real_manifest
    )

    for case, documents in (
        (triangle_s1, documents_s1),
        (triangle_s2, documents_s2),
        (triangle_s2_j_break, documents_jbreak),
        (triangle_s3, documents_s3),
    ):
        _write_case(tmp_path, case, documents)
    _patch_plan(monkeypatch, (triangle_s1, triangle_s2, triangle_s2_j_break, triangle_s3))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    report = build_inter_s_matching_report(index)

    assert isinstance(report, InterSMatchingReport)
    assert report.campaign_id == real_manifest.campaign_id
    assert report.manifest_fingerprint == real_manifest.fingerprint
    assert report.repository_commit == REPO_COMMIT

    # Never mixes reference/j_break, never pairs S1 (only the two largest
    # spins -- S3, S2 -- are ever used).
    case_ids_involved = {m.high_case_id for m in report.matches} | {m.low_case_id for m in report.matches}
    assert case_ids_involved == {triangle_s3.case_id, triangle_s2.case_id}

    assert len(report.matches) == 2
    for match in report.matches:
        assert isinstance(match, InterSGroupMatch)
        assert match.high_case_id == triangle_s3.case_id
        assert match.low_case_id == triangle_s2.case_id
        assert match.high_spin == 3
        assert match.low_spin == 2

    # Deterministic order of high groups within the couple: index 0 then 1.
    assert [m.high_group.spectral_window_group_index for m in report.matches] == [0, 1]

    exact_match, ambiguous_match = report.matches
    assert exact_match.outcome.status == EXACT_LABEL_MATCH
    assert exact_match.low_group is not None
    assert exact_match.low_group.spectral_window_group_index == 0
    assert exact_match.low_group.match_key == exact_match.outcome.matched_group
    # high_group identity is exactly the IndexedSpectralGroup already
    # built by the index -- never a copy or a reconstruction.
    high_groups = [g for g in index.groups if g.case_id == triangle_s3.case_id]
    assert exact_match.high_group is high_groups[0]

    assert ambiguous_match.outcome.status != EXACT_LABEL_MATCH
    assert ambiguous_match.low_group is None


# ---------------------------------------------------------------------------
# 1. The 3 admissible couples of the real campaign, derived generically
# (never hardcoded) from the full real plan.
# ---------------------------------------------------------------------------


def test_three_couples_across_full_real_plan(monkeypatch, real_manifest, real_plan, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    for case in real_plan:
        _write_case(tmp_path, case, _default_group_documents(case, group, manifest=real_manifest))
    _patch_plan(monkeypatch, tuple(real_plan))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    report = build_inter_s_matching_report(index)

    assert len(report.matches) == 3
    assert all(match.outcome.status == EXACT_LABEL_MATCH for match in report.matches)
    assert [match.high_group.case.geometry for match in report.matches] == ["triangle", "ring4", "ring5"]
    for match in report.matches:
        assert match.high_spin == 3
        assert match.low_spin == 2

    j_break_case_ids = {case.case_id for case in real_plan if case.hamiltonian_case_id == "j_break"}
    matched_case_ids = {match.high_case_id for match in report.matches} | {match.low_case_id for match in report.matches}
    assert matched_case_ids.isdisjoint(j_break_case_ids)


# ---------------------------------------------------------------------------
# 2. No couple for a physical identity with only one available spin.
# ---------------------------------------------------------------------------


def test_no_couple_for_single_spin_identity(monkeypatch, real_manifest, triangle_s2_j_break, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    _write_case(tmp_path, triangle_s2_j_break, _default_group_documents(triangle_s2_j_break, group, manifest=real_manifest))
    _patch_plan(monkeypatch, (triangle_s2_j_break,))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    report = build_inter_s_matching_report(index)

    assert report.matches == ()


# ---------------------------------------------------------------------------
# _build_case_pairs (durcissement secondaire): the two SELECTED spins must
# be the two largest DISTINCT values, never the first two entries of a
# naive spin-descending sort -- and if more than one CampaignCaseSpec
# shares the same physical identity AND the same one of those two spins,
# _build_case_pairs must never pick one arbitrarily.
# ---------------------------------------------------------------------------


def test_build_case_pairs_selects_the_two_largest_distinct_spins(real_manifest, triangle_s1, triangle_s2, triangle_s3) -> None:
    index = _fake_index_from_cases(real_manifest, (triangle_s1, triangle_s2, triangle_s3))

    pairs = inter_s_module._build_case_pairs(index)

    assert len(pairs) == 1
    high, low = pairs[0]
    assert high.case.spin == 3
    assert low.case.spin == 2


def test_build_case_pairs_raises_on_duplicate_case_at_a_selected_spin(real_manifest, triangle_s2, triangle_s3) -> None:
    # Same physical identity (geometry/hamiltonian_identity_without_spin/
    # sector) and same spin (3) as triangle_s3, but a distinct case_id --
    # exactly the "S=3 case A, S=3 case B, S=2 case C" scenario from the
    # mandate. A naive spin-descending sort could silently pair the two
    # S=3 cases together; this must instead raise, never guess.
    duplicate_high = _replace_case(triangle_s3, hamiltonian_case_id="reference-duplicate-for-test")
    assert duplicate_high.case_id != triangle_s3.case_id
    index = _fake_index_from_cases(real_manifest, (triangle_s2, triangle_s3, duplicate_high))

    with pytest.raises(InterSMatchingError, match="share spin 3"):
        inter_s_module._build_case_pairs(index)


# ---------------------------------------------------------------------------
# low_window_truncated reconstruction from CampaignCaseSpec alone -- no
# spectral computation. Covers dense/sparse dispatch, dimension 0/1, and
# the guardrail-exceeded ("not_computed") branch, per the correctif
# mandate: the previous "spectral_window < physical_dimension" formula
# was wrong on the sparse branch (eigsh computes at most dimension - 1
# eigenvalues, never dimension).
# ---------------------------------------------------------------------------


def test_low_window_truncated_dense_true_for_a_real_truncated_case(triangle_s2) -> None:
    assert triangle_s2.physical_dimension <= triangle_s2.spectrum_options.max_dense_dimension
    assert triangle_s2.spectral_window < triangle_s2.physical_dimension
    assert inter_s_module._low_window_truncated(triangle_s2) is True


def test_low_window_truncated_dense_false_when_spectral_window_covers_the_dimension(triangle_s2) -> None:
    case = _replace_case(triangle_s2, physical_dimension=10)  # <= max_dense_dimension: dense path
    assert case.spectral_window >= case.physical_dimension  # 16 >= 10
    assert inter_s_module._low_window_truncated(case) is False


def test_low_window_truncated_sparse_true_when_spectral_window_is_small(triangle_s2) -> None:
    # dimension (3000) > max_dense_dimension (2000): sparse path.
    case = _replace_case(triangle_s2, physical_dimension=3000)
    assert case.physical_dimension > case.spectrum_options.max_dense_dimension
    assert case.spectral_window < case.physical_dimension
    assert inter_s_module._low_window_truncated(case) is True


def test_low_window_truncated_sparse_true_even_when_spectral_window_covers_the_dimension(triangle_s2) -> None:
    # The bug this correctif fixes: sparse can never compute `dimension`
    # eigenvalues (only dimension - 1, at most), so this must stay True
    # even though spectral_window (5000) >= physical_dimension (3000) --
    # the old "spectral_window < physical_dimension" formula wrongly
    # returned False here.
    case = _replace_case(triangle_s2, physical_dimension=3000, spectral_window=5000)
    assert case.physical_dimension > case.spectrum_options.max_dense_dimension
    assert case.spectral_window >= case.physical_dimension
    assert inter_s_module._low_window_truncated(case) is True


def test_low_window_truncated_dimension_one_is_always_false(triangle_s2) -> None:
    case = _replace_case(triangle_s2, physical_dimension=1)
    assert inter_s_module._low_window_truncated(case) is False


def test_low_window_truncated_dimension_zero_raises_structural_error(triangle_s2) -> None:
    case = _replace_case(triangle_s2, physical_dimension=0)
    with pytest.raises(InterSMatchingError, match="physical_dimension == 0"):
        inter_s_module._low_window_truncated(case)


def test_low_window_truncated_guardrail_exceeded_raises_structural_error(triangle_s2) -> None:
    unreachable_dimension = triangle_s2.spectrum_options.max_sparse_dimension + 1
    case = _replace_case(triangle_s2, physical_dimension=unreachable_dimension)
    assert case.spectrum_options.force is False
    with pytest.raises(InterSMatchingError, match="not_computed"):
        inter_s_module._low_window_truncated(case)


# ---------------------------------------------------------------------------
# 7/8. _resolve_low_group structural invariants: zero or multiple
# concrete IndexedSpectralGroup objects matching outcome.matched_group
# are both pipeline errors, never silently picked by any other criterion.
# ---------------------------------------------------------------------------


def test_resolve_low_group_raises_on_zero_concrete_matches(monkeypatch, real_manifest, triangle_s2, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    _write_case(tmp_path, triangle_s2, _default_group_documents(triangle_s2, group, manifest=real_manifest))
    _patch_plan(monkeypatch, (triangle_s2,))
    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    low_groups = tuple(g for g in index.groups if g.case_id == triangle_s2.case_id)

    absent_key = dataclasses.replace(low_groups[0].match_key, multiplicity=low_groups[0].match_key.multiplicity + 5)
    outcome = MatchOutcome(EXACT_LABEL_MATCH, absent_key)

    with pytest.raises(InterSMatchingError, match="found 0"):
        inter_s_module._resolve_low_group(outcome, low_groups, high_case_id="dummy-high-case", high_group_index=0)


def test_resolve_low_group_raises_on_multiple_concrete_matches(monkeypatch, real_manifest, triangle_s2, tmp_path: Path) -> None:
    # Two distinct spectral_window_group_index groups sharing an
    # identical SpectralGroupMatchKey content (spectral_window_group_index
    # itself is never part of the key) -- a genuine, legitimate scenario
    # this function must guard against.
    group0 = _group(0, twice_T=1)
    group1 = _group(1, twice_T=1)
    documents = _default_group_documents(triangle_s2, group0, manifest=real_manifest) + _default_group_documents(
        triangle_s2, group1, manifest=real_manifest
    )
    _write_case(tmp_path, triangle_s2, documents)
    _patch_plan(monkeypatch, (triangle_s2,))
    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    low_groups = tuple(g for g in index.groups if g.case_id == triangle_s2.case_id)
    assert len(low_groups) == 2
    assert low_groups[0].match_key == low_groups[1].match_key

    outcome = MatchOutcome(EXACT_LABEL_MATCH, low_groups[0].match_key)

    with pytest.raises(InterSMatchingError, match="found 2"):
        inter_s_module._resolve_low_group(outcome, low_groups, high_case_id="dummy-high-case", high_group_index=0)


# ---------------------------------------------------------------------------
# 16/17/18. No target_id in the public API; no forbidden import.
# ---------------------------------------------------------------------------


def test_no_target_id_field_anywhere_in_inter_s_api() -> None:
    for cls in (InterSGroupMatch, InterSMatchingReport):
        assert "target_id" not in {f.name for f in dataclasses.fields(cls)}


def test_inter_s_module_never_imports_forbidden_entry_points() -> None:
    source = inspect.getsource(inter_s_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    for token in _FORBIDDEN_IMPORT_TOKENS:
        assert token not in import_lines, f"inter_s.py must never import {token!r}"


# ---------------------------------------------------------------------------
# 5. match_spectral_group is imported and called as-is -- never
# reimplemented locally.
# ---------------------------------------------------------------------------


def test_inter_s_reuses_match_spectral_group_without_reimplementation() -> None:
    source = inspect.getsource(inter_s_module)
    assert "from cosmobox.level1.matching import" in source
    assert "match_spectral_group(" in source
    assert "def match_spectral_group" not in source
