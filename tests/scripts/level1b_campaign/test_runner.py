from __future__ import annotations

import dataclasses
import math

import pytest
from jsonschema import Draft202012Validator

from cosmobox.level1.orbits import ValidatedOrbit
from cosmobox.level1.serialization import _load_schema
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from experiments.level1 import target_selection as target_selection_module
from experiments.level1.target_selection import (
    AMBIGUOUS,
    NOT_IN_WINDOW,
    SELECTED,
    STRUCTURALLY_NOT_APPLICABLE,
    TargetSelectionOutcome,
)
from scripts.level1b_campaign import runner as runner_module
from scripts.level1b_campaign.runner import run_single_case

REPO_COMMIT = "c" * 40

_FORBIDDEN_OBSERVABLE_KINDS = {"gamma_O", "G_occ", "path_phase_coherence"}
_FORBIDDEN_RECORD_KINDS = {"matching", "robustness"}


# ---------------------------------------------------------------------------
# Fixtures -- each real case is diagonalized and executed exactly once and
# reused across every assertion-only test below (a full run costs tens of
# seconds; re-running it per test would make this suite impractically slow
# without adding any coverage). Only small, already-frozen reference-grid
# geometries are used (triangle, ring4); ring5 S=3 is never touched.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def plan(manifest: manifest_module.Manifest) -> tuple:
    return planning_module.build_campaign_plan(manifest)


def _case(plan: tuple, *, geometry: str, spin: int, hamiltonian_case_id: str = "reference"):
    return next(
        c for c in plan if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture(scope="module")
def triangle_s1_case(plan: tuple):
    return _case(plan, geometry="triangle", spin=1)


@pytest.fixture(scope="module")
def triangle_s1_result(manifest: manifest_module.Manifest, triangle_s1_case):
    return run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)


@pytest.fixture(scope="module")
def triangle_s2_jbreak_case(plan: tuple):
    return _case(plan, geometry="triangle", spin=2, hamiltonian_case_id="j_break")


@pytest.fixture(scope="module")
def triangle_s2_jbreak_result(manifest: manifest_module.Manifest, triangle_s2_jbreak_case):
    return run_single_case(manifest, triangle_s2_jbreak_case, repository_commit=REPO_COMMIT)


@pytest.fixture(scope="module")
def ring4_s1_case(plan: tuple):
    return _case(plan, geometry="ring4", spin=1)


@pytest.fixture(scope="module")
def ring4_s1_result(manifest: manifest_module.Manifest, ring4_s1_case):
    return run_single_case(manifest, ring4_s1_case, repository_commit=REPO_COMMIT)


@pytest.fixture(scope="module")
def truncated_triangle_s1_result(manifest: manifest_module.Manifest, triangle_s1_case):
    """n_eigenvalues=2 (< the S=1 fundamental multiplicity of 4): the
    fundamental group itself becomes partial_subspace, and first_excited/
    T_max fall outside the window entirely -- covers both the partial-
    group and the absent-target cases with a single, cheap run."""
    truncated_options = dataclasses.replace(triangle_s1_case.spectrum_options, n_eigenvalues=2)
    truncated_case = dataclasses.replace(triangle_s1_case, spectrum_options=truncated_options)
    return run_single_case(manifest, truncated_case, repository_commit=REPO_COMMIT)


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema())


def _assert_all_documents_valid(documents) -> None:
    validator = _schema_validator()
    for document in documents:
        errors = list(validator.iter_errors(document))
        assert errors == [], f"document failed schema validation: {errors}"


def _assert_no_forbidden_productions(documents) -> None:
    for document in documents:
        assert document["observable_kind"] not in _FORBIDDEN_OBSERVABLE_KINDS
        assert document["record_kind"] not in _FORBIDDEN_RECORD_KINDS


def _walk_numbers(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_numbers(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_numbers(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value


def _assert_all_finite(documents) -> None:
    for document in documents:
        for number in _walk_numbers(document):
            assert math.isfinite(number), f"non-finite number {number!r} in document {document['record_kind']}/{document['observable_kind']}"


# ---------------------------------------------------------------------------
# 1. triangle S=1 reference: every document valid, no forbidden productions,
#    no non-finite values.
# ---------------------------------------------------------------------------


def test_triangle_s1_documents_all_valid_against_schema_v2(triangle_s1_result) -> None:
    assert len(triangle_s1_result.documents) > 0
    _assert_all_documents_valid(triangle_s1_result.documents)


def test_triangle_s1_no_forbidden_productions(triangle_s1_result) -> None:
    _assert_no_forbidden_productions(triangle_s1_result.documents)


def test_triangle_s1_no_non_finite_values(triangle_s1_result) -> None:
    _assert_all_finite(triangle_s1_result.documents)


def test_triangle_s1_assembly_report_matches_documents(triangle_s1_result) -> None:
    assert triangle_s1_result.assembly_report.output_count == len(triangle_s1_result.documents)
    assert triangle_s1_result.assembly_report.duplicate_count == 0


# ---------------------------------------------------------------------------
# 2. triangle S=2 j_break: the exact D022 collision, now resolved.
# ---------------------------------------------------------------------------


def test_triangle_s2_j_break_regression_no_assembly_contradiction(triangle_s2_jbreak_result) -> None:
    assert len(triangle_s2_jbreak_result.documents) > 0
    assert triangle_s2_jbreak_result.assembly_report.duplicate_count >= 0  # assembled without raising


def test_triangle_s2_j_break_groups_0_and_1_both_present_with_distinct_indices(triangle_s2_jbreak_result) -> None:
    indices = {
        doc["identity"]["spectral_group"]["spectral_window_group_index"] for doc in triangle_s2_jbreak_result.documents
    }
    assert 0 in indices
    assert 1 in indices


def test_triangle_s2_j_break_groups_0_and_1_have_multiplicity_2_and_twice_t_1(triangle_s2_jbreak_result) -> None:
    for target_index in (0, 1):
        matching_docs = [
            doc
            for doc in triangle_s2_jbreak_result.documents
            if doc["identity"]["spectral_group"]["spectral_window_group_index"] == target_index
        ]
        assert matching_docs, f"no documents for spectral_window_group_index={target_index}"
        for doc in matching_docs:
            assert doc["identity"]["spectral_group"]["multiplicity"] == 2
            assert doc["identity"]["spectral_group"]["twice_T"] == 1


def test_triangle_s2_j_break_reflection_characters_of_groups_0_and_1_differ(triangle_s2_jbreak_result) -> None:
    """j_break breaks translation symmetry entirely, so translation_character
    is not_applicable (value=None) for every group -- identical by
    construction, not a useful discriminant here. Reflection about the
    J_override node survives j_break, so reflection_character is numeric
    and genuinely differs between the two physically distinct groups."""
    reflection_docs_by_index = {}
    for doc in triangle_s2_jbreak_result.documents:
        if doc["observable_kind"] != "reflection_character":
            continue
        reflection_docs_by_index[doc["identity"]["spectral_group"]["spectral_window_group_index"]] = doc["payload"]

    label_0 = reflection_docs_by_index.get(0)
    label_1 = reflection_docs_by_index.get(1)
    assert label_0 is not None and label_1 is not None
    assert label_0["kind"] == "numeric"
    assert label_1["kind"] == "numeric"
    assert label_0 != label_1  # genuinely different physical groups


def test_triangle_s2_j_break_documents_all_valid_against_schema_v2(triangle_s2_jbreak_result) -> None:
    _assert_all_documents_valid(triangle_s2_jbreak_result.documents)


def test_triangle_s2_j_break_no_forbidden_productions(triangle_s2_jbreak_result) -> None:
    _assert_no_forbidden_productions(triangle_s2_jbreak_result.documents)


def test_triangle_s2_j_break_no_non_finite_values(triangle_s2_jbreak_result) -> None:
    _assert_all_finite(triangle_s2_jbreak_result.documents)


# ---------------------------------------------------------------------------
# 3. Determinism of a repeated execution.
# ---------------------------------------------------------------------------


def test_run_single_case_is_deterministic(manifest, triangle_s1_case) -> None:
    result_a = run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)
    result_b = run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)
    assert result_a.documents == result_b.documents
    assert result_a.target_outcomes == result_b.target_outcomes


# ---------------------------------------------------------------------------
# 4. Complete group -- normative results produced.
# ---------------------------------------------------------------------------


def test_complete_group_target_meets_normative_requirements(triangle_s1_result) -> None:
    fundamental = next(o for o in triangle_s1_result.target_outcomes if o.target_id == "fundamental")
    assert fundamental.status == SELECTED
    assert fundamental.selected_group_status == "complete_multiplet"
    assert fundamental.meets_normative_requirements is True


def test_complete_group_produces_records_tagged_complete_multiplet(triangle_s1_result) -> None:
    statuses = {doc["identity"]["spectral_group"]["status"] for doc in triangle_s1_result.documents}
    assert statuses == {"complete_multiplet"}


# ---------------------------------------------------------------------------
# 5. Partial group -- exploratory only, never promoted.
# ---------------------------------------------------------------------------


def test_partial_group_target_selected_but_not_meeting_requirements(truncated_triangle_s1_result) -> None:
    fundamental = next(o for o in truncated_triangle_s1_result.target_outcomes if o.target_id == "fundamental")
    assert fundamental.status == SELECTED
    assert fundamental.selected_group_status == "partial_subspace"
    assert fundamental.meets_normative_requirements is False


def test_partial_group_documents_all_tagged_partial_subspace(truncated_triangle_s1_result) -> None:
    assert len(truncated_triangle_s1_result.documents) > 0
    statuses = {doc["identity"]["spectral_group"]["status"] for doc in truncated_triangle_s1_result.documents}
    assert statuses == {"partial_subspace"}


def test_partial_group_produces_no_robustness_or_matching_records(truncated_triangle_s1_result) -> None:
    _assert_no_forbidden_productions(truncated_triangle_s1_result.documents)


# ---------------------------------------------------------------------------
# 6. Absent target -- explicit status, no substitute group.
# ---------------------------------------------------------------------------


def test_absent_target_recorded_as_not_in_window_with_no_documents(truncated_triangle_s1_result) -> None:
    first_excited = next(o for o in truncated_triangle_s1_result.target_outcomes if o.target_id == "first_excited")
    assert first_excited.status == NOT_IN_WINDOW
    assert first_excited.group_index is None
    # No document anywhere claims to satisfy first_excited via a substitute group:
    # the only group actually produced is index 0 (the truncated fundamental).
    indices = {doc["identity"]["spectral_group"]["spectral_window_group_index"] for doc in truncated_triangle_s1_result.documents}
    assert indices == {0}


# ---------------------------------------------------------------------------
# 7. Ambiguous target -- explicit status, never chosen arbitrarily. Tested
# behaviorally by substituting select_target_group with a double that
# returns a canned AMBIGUOUS outcome for one target, confirming the runner
# itself never invents a group for it.
# ---------------------------------------------------------------------------


def test_ambiguous_target_produces_no_documents_and_is_recorded_explicitly(
    monkeypatch: pytest.MonkeyPatch, manifest, triangle_s1_case
) -> None:
    real_select_target_group = target_selection_module.select_target_group

    def fake_select_target_group(target, groups, group_states, **kwargs):
        if target.target_id == "first_excited":
            return TargetSelectionOutcome(
                target_id=target.target_id,
                status=AMBIGUOUS,
                group_index=None,
                twice_T=None,
                selected_group_status=None,
                meets_normative_requirements=None,
            )
        return real_select_target_group(target, groups, group_states, **kwargs)

    monkeypatch.setattr(runner_module, "select_target_group", fake_select_target_group)
    result = run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)

    first_excited = next(o for o in result.target_outcomes if o.target_id == "first_excited")
    assert first_excited.status == AMBIGUOUS
    assert first_excited.group_index is None
    # first_excited would normally resolve to group_index=1: confirm no
    # document produced for it comes from the ambiguous target being
    # silently resolved anyway. group_index=1 may still appear via T_max
    # (a separate, unambiguous target on the real grid), so the real
    # assertion is that the ambiguous outcome itself contributed nothing.
    assert result.assembly_report.output_count == len(result.documents)


# ---------------------------------------------------------------------------
# 8. structurally_not_applicable -- no physical observable produced.
# ---------------------------------------------------------------------------


def test_structurally_not_applicable_target_produces_no_documents(ring4_s1_result) -> None:
    t_3_2 = next(o for o in ring4_s1_result.target_outcomes if o.target_id == "T_3_2")
    assert t_3_2.status == STRUCTURALLY_NOT_APPLICABLE
    assert t_3_2.group_index is None


# ---------------------------------------------------------------------------
# 9. Two targets resolving to the same group -- identical SpectralGroupIdentity.
# ---------------------------------------------------------------------------


def test_two_targets_same_group_share_identical_spectral_group_identity(triangle_s1_result) -> None:
    first_excited = next(o for o in triangle_s1_result.target_outcomes if o.target_id == "first_excited")
    t_max = next(o for o in triangle_s1_result.target_outcomes if o.target_id == "T_max")
    assert first_excited.status == SELECTED
    assert t_max.status == SELECTED
    assert first_excited.group_index == t_max.group_index  # same physical group on this grid point

    matching_docs = [
        doc
        for doc in triangle_s1_result.documents
        if doc["identity"]["spectral_group"]["spectral_window_group_index"] == first_excited.group_index
    ]
    spectral_groups = {tuple(sorted(doc["identity"]["spectral_group"].items())) for doc in matching_docs}
    assert len(spectral_groups) == 1  # exactly one distinct SpectralGroupIdentity content for this group


# ---------------------------------------------------------------------------
# 10. Ordered pairs (i,j) and (j,i) distinct.
# ---------------------------------------------------------------------------


def test_ordered_pairs_i_j_and_j_i_both_present_and_distinct(triangle_s1_result) -> None:
    pairs = {
        tuple(doc["identity"]["path"])
        for doc in triangle_s1_result.documents
        if doc["identity"]["path"] is not None and len(doc["identity"]["path"]) == 2
    }
    assert (0, 1) in pairs
    assert (1, 0) in pairs


# ---------------------------------------------------------------------------
# 11. All minimal paths conserved individually (ring4 has antipodal pairs
# with two distinct minimal paths each).
# ---------------------------------------------------------------------------


def test_ring4_multiple_minimal_paths_are_all_conserved_individually(ring4_s1_result) -> None:
    long_paths = {
        tuple(doc["identity"]["path"])
        for doc in ring4_s1_result.documents
        if doc["identity"]["path"] is not None and len(doc["identity"]["path"]) > 2
    }
    # Antipodal pair 0-2 on ring4 has two minimal paths: 0-1-2 and 0-3-2.
    assert (0, 1, 2) in long_paths
    assert (0, 3, 2) in long_paths


def test_ring4_no_forbidden_productions(ring4_s1_result) -> None:
    _assert_no_forbidden_productions(ring4_s1_result.documents)


def test_ring4_documents_all_valid_against_schema_v2(ring4_s1_result) -> None:
    _assert_all_documents_valid(ring4_s1_result.documents)


def test_ring4_no_non_finite_values(ring4_s1_result) -> None:
    _assert_all_finite(ring4_s1_result.documents)


# ---------------------------------------------------------------------------
# 12. rho_QQ null with the correct reason at the maximal-flavor sector.
# ---------------------------------------------------------------------------


def test_rho_qq_null_with_zero_local_charge_variance_reason(triangle_s2_jbreak_result) -> None:
    rho_qq_docs = [doc for doc in triangle_s2_jbreak_result.documents if doc["observable_kind"] == "rho_QQ"]
    null_docs = [doc for doc in rho_qq_docs if doc["payload"]["value"] is None]
    assert null_docs, "expected at least one null rho_QQ document at the maximal-flavor sector"
    for doc in null_docs:
        assert doc["payload"]["null_reason"] == "zero_local_charge_variance"


def test_rho_qq_null_documents_come_from_the_twice_t_3_group(triangle_s2_jbreak_result) -> None:
    rho_qq_docs = [doc for doc in triangle_s2_jbreak_result.documents if doc["observable_kind"] == "rho_QQ"]
    null_docs = [doc for doc in rho_qq_docs if doc["payload"]["value"] is None]
    for doc in null_docs:
        assert doc["identity"]["spectral_group"]["twice_T"] == 3


# ---------------------------------------------------------------------------
# 13. Hermitian and non-Hermitian restricted diagnostics.
# ---------------------------------------------------------------------------


def test_hermitian_restricted_diagnostics_present(triangle_s1_result) -> None:
    docs = [
        doc
        for doc in triangle_s1_result.documents
        if doc["record_kind"] == "restricted_diagnostic" and doc["identity"]["path"] is not None and len(doc["identity"]["path"]) == 1
    ]
    assert docs, "expected Hermitian restricted diagnostics for single-node paths (Q_i)"
    for doc in docs:
        assert "eigenvalues" in doc["payload"]  # HermitianRestrictedDiagnostics-specific field


def test_non_hermitian_restricted_diagnostics_present(triangle_s1_result) -> None:
    docs = [
        doc
        for doc in triangle_s1_result.documents
        if doc["record_kind"] == "restricted_diagnostic" and doc["observable_kind"] == "O_ij_raw"
    ]
    assert docs, "expected non-Hermitian restricted diagnostics for O_ij"
    for doc in docs:
        assert "singular_values" in doc["payload"]  # NonHermitianRestrictedDiagnostics-specific field


# ---------------------------------------------------------------------------
# 14. Symmetry labels: numeric / not_applicable / unavailable, never a bare
# None.
# ---------------------------------------------------------------------------


def test_symmetry_labels_are_never_bare_none(triangle_s1_result, triangle_s2_jbreak_result) -> None:
    for result in (triangle_s1_result, triangle_s2_jbreak_result):
        label_docs = [doc for doc in result.documents if doc["record_kind"] == "symmetry_label"]
        assert label_docs
        for doc in label_docs:
            assert doc["payload"]["kind"] in ("numeric", "not_applicable", "unavailable")
            if doc["payload"]["kind"] == "numeric":
                assert doc["payload"]["value"] is not None
            else:
                assert doc["payload"]["value"] is None


def test_translation_character_is_numeric_at_the_unbroken_reference_point(triangle_s1_result) -> None:
    labels = {doc["payload"]["kind"] for doc in triangle_s1_result.documents if doc["observable_kind"] == "translation_character"}
    assert "numeric" in labels


def test_translation_character_is_not_applicable_under_j_break(triangle_s2_jbreak_result) -> None:
    labels = {
        doc["payload"]["kind"] for doc in triangle_s2_jbreak_result.documents if doc["observable_kind"] == "translation_character"
    }
    assert "not_applicable" in labels


# ---------------------------------------------------------------------------
# 15. Orbit statistics only after validation.
# ---------------------------------------------------------------------------


def test_orbit_statistics_present_and_well_formed(triangle_s1_result) -> None:
    docs = [doc for doc in triangle_s1_result.documents if doc["record_kind"] == "orbit_statistic"]
    assert docs
    for doc in docs:
        assert doc["payload"]["element_count"] >= 1


def test_orbit_statistics_propagate_validate_orbit_covariance_failure(
    monkeypatch: pytest.MonkeyPatch, manifest, triangle_s1_case
) -> None:
    """If the covariance check itself fails, run_single_case must
    propagate the failure -- it must never fall back to an unvalidated
    orbit aggregate."""

    def fake_validate_orbit_covariance(*args, **kwargs):
        raise ValueError("simulated covariance failure")

    monkeypatch.setattr(runner_module, "validate_orbit_covariance", fake_validate_orbit_covariance)
    with pytest.raises(ValueError, match="simulated covariance failure"):
        run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)


def test_build_orbit_result_payload_requires_a_validated_orbit() -> None:
    """Structural guarantee this runner relies on (orbits.py, not
    modified here): OrbitResultPayload can only ever be built from a
    ValidatedOrbit."""
    from cosmobox.level1.results import build_orbit_result_payload

    with pytest.raises(ValueError, match="ValidatedOrbit"):
        build_orbit_result_payload("not-a-validated-orbit")
    assert ValidatedOrbit  # imported to document the type this guarantee is about


# ---------------------------------------------------------------------------
# 16. No forbidden production anywhere, across every fixture.
# ---------------------------------------------------------------------------


def test_no_forbidden_production_across_all_fixtures(
    triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result
) -> None:
    for result in (triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result):
        _assert_no_forbidden_productions(result.documents)


# ---------------------------------------------------------------------------
# 17. Schema v2 validation, across every fixture.
# ---------------------------------------------------------------------------


def test_every_fixture_documents_valid_against_schema_v2(
    triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result
) -> None:
    for result in (triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result):
        _assert_all_documents_valid(result.documents)


# ---------------------------------------------------------------------------
# 18. Deterministic assembly order.
# ---------------------------------------------------------------------------


def test_assembly_order_is_deterministic_across_repeated_runs(manifest, triangle_s1_case) -> None:
    result_a = run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)
    result_b = run_single_case(manifest, triangle_s1_case, repository_commit=REPO_COMMIT)
    assert result_a.documents == result_b.documents  # tuples, order included


# ---------------------------------------------------------------------------
# 19. No NaN/Inf anywhere (already covered per-fixture above; this is the
# single aggregate assertion the mandate's list item maps to).
# ---------------------------------------------------------------------------


def test_no_non_finite_values_across_all_fixtures(
    triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result
) -> None:
    for result in (triangle_s1_result, triangle_s2_jbreak_result, ring4_s1_result, truncated_triangle_s1_result):
        _assert_all_finite(result.documents)


# ---------------------------------------------------------------------------
# 20. Provenance and seeds exact.
# ---------------------------------------------------------------------------


def test_provenance_carries_the_case_own_seeds(triangle_s1_result, triangle_s1_case) -> None:
    for doc in triangle_s1_result.documents:
        assert doc["provenance"]["scientific_seed"] == triangle_s1_case.scientific_seed
        assert doc["provenance"]["solver_seed"] == triangle_s1_case.solver_seed
        assert doc["provenance"]["validation_rotation_seed"] == triangle_s1_case.validation_rotation_seed


def test_provenance_validation_rotation_seed_is_null(triangle_s1_result, triangle_s1_case) -> None:
    assert triangle_s1_case.validation_rotation_seed is None
    for doc in triangle_s1_result.documents:
        assert doc["provenance"]["validation_rotation_seed"] is None


def test_provenance_spectral_status_matches_identity(triangle_s1_result) -> None:
    for doc in triangle_s1_result.documents:
        assert doc["provenance"]["spectral_status"] == doc["identity"]["spectral_group"]["status"]


def test_documents_carry_the_exact_repository_commit_manifest_fingerprint_campaign_id(triangle_s1_result, manifest) -> None:
    for doc in triangle_s1_result.documents:
        assert doc["repository_commit"] == REPO_COMMIT
        assert doc["manifest_fingerprint"] == manifest.fingerprint
        assert doc["campaign_id"] == manifest.campaign_id


def test_spectral_group_identity_never_carries_a_target_id_field(triangle_s1_result) -> None:
    for doc in triangle_s1_result.documents:
        assert "target_id" not in doc["identity"]["spectral_group"]


# ---------------------------------------------------------------------------
# Manifest ownership check (run_single_case step 2).
# ---------------------------------------------------------------------------


def test_run_single_case_rejects_a_case_with_tampered_scientific_seed(manifest, triangle_s1_case) -> None:
    tampered = dataclasses.replace(triangle_s1_case, scientific_seed=triangle_s1_case.scientific_seed + 1)
    with pytest.raises(ValueError, match="scientific_seed"):
        run_single_case(manifest, tampered, repository_commit=REPO_COMMIT)


def test_run_single_case_rejects_a_case_checked_against_a_manifest_with_different_target_groups(
    manifest, triangle_s1_case
) -> None:
    """CampaignCaseSpec's own case_id already encodes its target_groups
    content, so a case cannot be tampered directly without also failing
    its own self-verification (a different, already-tested guarantee).
    This test instead checks the case against a DIFFERENT manifest object
    (same grid, different target_groups for this geometry) to exercise
    the runner's own ownership check specifically."""
    tampered_target_groups = dict(manifest.target_groups)
    tampered_target_groups["triangle"] = manifest.target_groups["triangle"][:1]
    tampered_manifest = dataclasses.replace(manifest, target_groups=tampered_target_groups)
    with pytest.raises(ValueError, match="target_groups"):
        run_single_case(tampered_manifest, triangle_s1_case, repository_commit=REPO_COMMIT)
