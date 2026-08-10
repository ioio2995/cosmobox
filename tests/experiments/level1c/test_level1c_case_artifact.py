from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from experiments.level1c import case_artifact as ca
from experiments.level1c import manifest as m
from experiments.level1c.target_selection import TargetSelectionRecord

_REPO_COMMIT = "23d3b216500fda8d38dd7952a05ebe8744b57848"
_MANIFEST_FINGERPRINT = "31e4c94f1758b426ef3ac05ecbc287ad7291d0b34b9a0c1329f5b746e22944e5"
_SHA256 = "a" * 64


def _record(target_id: str, role: str, *, selected: bool, status: str | None = None) -> TargetSelectionRecord:
    if selected:
        return TargetSelectionRecord(
            target_id=target_id,
            role=role,
            selection_status="selected",
            spectral_window_group_index=0,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )
    return TargetSelectionRecord(
        target_id=target_id,
        role=role,
        selection_status=status or "not_in_window",
        spectral_window_group_index=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )


def _triangle_selections() -> tuple[TargetSelectionRecord, ...]:
    return (
        _record("fundamental", "REQUIRED", selected=True),
        _record("first_excited", "REQUIRED", selected=True),
        _record("T_max", "CALIBRATION_ONLY", selected=False),
    )


def _ring5_selections() -> tuple[TargetSelectionRecord, ...]:
    return (
        _record("fundamental", "REQUIRED", selected=True),
        _record("first_excited", "REQUIRED", selected=True),
        _record("T_3_2", "REQUIRED", selected=True),
        _record("T_max", "CALIBRATION_ONLY", selected=False),
    )


def _success_artifact(geometry: str = "triangle", selections=None) -> ca.Level1CCaseRunArtifact:
    return ca.Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id="level1c-j0-response-v1",
        manifest_fingerprint=_MANIFEST_FINGERPRINT,
        repository_commit=_REPO_COMMIT,
        case_id="triangle-S2-j0-1.00-default-215eee2a56a431a5",
        geometry=geometry,
        spin=2,
        hamiltonian_case_id="j0-1.00",
        sector_id="default",
        spectral_window=9,
        run_status="success",
        target_selections=selections if selections is not None else _triangle_selections(),
        records_sha256=_SHA256,
        record_count=10,
    )


def _failed_artifact() -> ca.Level1CCaseRunArtifact:
    return ca.Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id="level1c-j0-response-v1",
        manifest_fingerprint=_MANIFEST_FINGERPRINT,
        repository_commit=_REPO_COMMIT,
        case_id="triangle-S2-j0-1.00-default-215eee2a56a431a5",
        geometry="triangle",
        spin=2,
        hamiltonian_case_id="j0-1.00",
        sector_id="default",
        spectral_window=9,
        run_status="failed",
        target_selections=(),
        records_sha256=None,
        record_count=0,
    )


# ---------------------------------------------------------------------------
# Schema well-formedness
# ---------------------------------------------------------------------------


def test_case_run_schema_is_a_well_formed_draft202012_schema() -> None:
    Draft202012Validator.check_schema(ca._load_schema())


# ---------------------------------------------------------------------------
# validate_target_selections_match_manifest: counts (30+40=70), order, coverage
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest() -> m.Level1CManifest:
    return m.load_manifest()


def test_triangle_requires_exactly_3_target_outcomes(manifest: m.Level1CManifest) -> None:
    assert len(manifest.target_groups["triangle"]) == 3
    ca.validate_target_selections_match_manifest(_triangle_selections(), manifest.target_groups["triangle"])


def test_ring5_requires_exactly_4_target_outcomes(manifest: m.Level1CManifest) -> None:
    assert len(manifest.target_groups["ring5"]) == 4
    ca.validate_target_selections_match_manifest(_ring5_selections(), manifest.target_groups["ring5"])


def test_total_target_outcomes_across_campaign_is_70(manifest: m.Level1CManifest) -> None:
    triangle_cases = 10  # 2 spins x 5 J0
    ring5_cases = 10
    total = triangle_cases * len(manifest.target_groups["triangle"]) + ring5_cases * len(manifest.target_groups["ring5"])
    assert total == 70


def test_missing_target_is_rejected(manifest: m.Level1CManifest) -> None:
    incomplete = _triangle_selections()[:-1]  # drop T_max
    with pytest.raises(ValueError, match="missing target"):
        ca.validate_target_selections_match_manifest(incomplete, manifest.target_groups["triangle"])


def test_extra_target_is_rejected(manifest: m.Level1CManifest) -> None:
    extra = _triangle_selections() + (_record("unexpected_target", "REQUIRED", selected=True),)
    with pytest.raises(ValueError, match="not declared by the manifest"):
        ca.validate_target_selections_match_manifest(extra, manifest.target_groups["triangle"])


def test_wrong_order_is_rejected(manifest: m.Level1CManifest) -> None:
    reordered = tuple(reversed(_triangle_selections()))
    with pytest.raises(ValueError, match="does not match the manifest's own target order"):
        ca.validate_target_selections_match_manifest(reordered, manifest.target_groups["triangle"])


# ---------------------------------------------------------------------------
# Level1CCaseRunArtifact: selected/non-selected invariants
# ---------------------------------------------------------------------------


def test_selected_valid() -> None:
    record = _record("fundamental", "REQUIRED", selected=True)
    assert record.selection_status == "selected"
    assert record.spectral_window_group_index is not None


@pytest.mark.parametrize("status", ["not_in_window", "ambiguous", "structurally_not_applicable"])
def test_non_selected_statuses_valid(status: str) -> None:
    record = _record("T_max", "CALIBRATION_ONLY", selected=False, status=status)
    assert record.selection_status == status
    assert record.spectral_window_group_index is None
    assert record.selected_group_status is None
    assert record.meets_normative_requirements is None


def test_selected_without_group_index_is_rejected() -> None:
    with pytest.raises(ValueError, match="spectral_window_group_index must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="selected",
            spectral_window_group_index=None,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )


def test_non_selected_with_group_index_is_rejected() -> None:
    with pytest.raises(ValueError, match="spectral_window_group_index must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="not_in_window",
            spectral_window_group_index=0,
            selected_group_status=None,
            meets_normative_requirements=None,
        )


def test_non_selected_with_selected_group_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="selected_group_status must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="ambiguous",
            spectral_window_group_index=None,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=None,
        )


def test_non_selected_with_meets_normative_requirements_is_rejected() -> None:
    with pytest.raises(ValueError, match="meets_normative_requirements must be set if and only if"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="ambiguous",
            spectral_window_group_index=None,
            selected_group_status=None,
            meets_normative_requirements=True,
        )


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValueError, match="role must be"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="SOMETIMES",
            selection_status="selected",
            spectral_window_group_index=0,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )


def test_unknown_selection_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="selection_status must be one of"):
        TargetSelectionRecord(
            target_id="fundamental",
            role="REQUIRED",
            selection_status="found",
            spectral_window_group_index=0,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )


def test_duplicate_target_id_is_rejected() -> None:
    duplicated = _triangle_selections() + (_record("fundamental", "REQUIRED", selected=True),)
    with pytest.raises(ValueError, match="duplicate target_id"):
        _success_artifact(selections=duplicated)


# ---------------------------------------------------------------------------
# T_max / T_3_2 semantics
# ---------------------------------------------------------------------------


def test_t_max_calibration_only_selected_partial_subspace_never_promoted() -> None:
    record = TargetSelectionRecord(
        target_id="T_max",
        role="CALIBRATION_ONLY",
        selection_status="selected",
        spectral_window_group_index=7,
        selected_group_status="partial_subspace",
        meets_normative_requirements=False,
    )
    assert record.role == "CALIBRATION_ONLY"
    assert record.selected_group_status == "partial_subspace"
    assert record.meets_normative_requirements is False


def test_t_3_2_required() -> None:
    record = _record("T_3_2", "REQUIRED", selected=True)
    assert record.role == "REQUIRED"


# ---------------------------------------------------------------------------
# Level1CCaseRunArtifact-level invariants (success / failure)
# ---------------------------------------------------------------------------


def test_success_artifact_is_valid_and_matches_schema() -> None:
    artifact = _success_artifact()
    document = ca.to_json_dict(artifact)
    ca.validate_case_run_document(document)


def test_failed_artifact_is_valid_and_matches_schema() -> None:
    artifact = _failed_artifact()
    document = ca.to_json_dict(artifact)
    ca.validate_case_run_document(document)


def test_success_requires_non_empty_target_selections() -> None:
    with pytest.raises(ValueError, match="target_selections must be non-empty"):
        _success_artifact(selections=())


def test_success_requires_records_sha256() -> None:
    with pytest.raises(ValueError, match="records_sha256 must be a 64-hex"):
        ca.Level1CCaseRunArtifact(
            schema_version="level1c-case-run-v1",
            campaign_id="level1c-j0-response-v1",
            manifest_fingerprint=_MANIFEST_FINGERPRINT,
            repository_commit=_REPO_COMMIT,
            case_id="x",
            geometry="triangle",
            spin=2,
            hamiltonian_case_id="j0-1.00",
            sector_id="default",
            spectral_window=9,
            run_status="success",
            target_selections=_triangle_selections(),
            records_sha256=None,
            record_count=10,
        )


def test_failure_forbids_target_selections() -> None:
    with pytest.raises(ValueError, match="target_selections must be empty"):
        ca.Level1CCaseRunArtifact(
            schema_version="level1c-case-run-v1",
            campaign_id="level1c-j0-response-v1",
            manifest_fingerprint=_MANIFEST_FINGERPRINT,
            repository_commit=_REPO_COMMIT,
            case_id="x",
            geometry="triangle",
            spin=2,
            hamiltonian_case_id="j0-1.00",
            sector_id="default",
            spectral_window=9,
            run_status="failed",
            target_selections=_triangle_selections(),
            records_sha256=None,
            record_count=0,
        )


def test_failure_forbids_records_sha256() -> None:
    with pytest.raises(ValueError, match="records_sha256 must be None"):
        ca.Level1CCaseRunArtifact(
            schema_version="level1c-case-run-v1",
            campaign_id="level1c-j0-response-v1",
            manifest_fingerprint=_MANIFEST_FINGERPRINT,
            repository_commit=_REPO_COMMIT,
            case_id="x",
            geometry="triangle",
            spin=2,
            hamiltonian_case_id="j0-1.00",
            sector_id="default",
            spectral_window=9,
            run_status="resource_guardrail_exceeded",
            target_selections=(),
            records_sha256=_SHA256,
            record_count=0,
        )


# ---------------------------------------------------------------------------
# Schema-level rejections mirroring the artifact-level ones
# ---------------------------------------------------------------------------


def test_schema_rejects_success_with_empty_target_selections() -> None:
    document = ca.to_json_dict(_success_artifact())
    document = copy.deepcopy(document)
    document["target_selections"] = []
    with pytest.raises(ValueError):
        ca.validate_case_run_document(document)


def test_schema_rejects_ring4_geometry() -> None:
    document = copy.deepcopy(ca.to_json_dict(_success_artifact()))
    document["geometry"] = "ring4"
    with pytest.raises(ValueError):
        ca.validate_case_run_document(document)


def test_schema_rejects_spin_1() -> None:
    document = copy.deepcopy(ca.to_json_dict(_success_artifact()))
    document["spin"] = 1
    with pytest.raises(ValueError):
        ca.validate_case_run_document(document)


def test_schema_rejects_unknown_run_status() -> None:
    document = copy.deepcopy(ca.to_json_dict(_success_artifact()))
    document["run_status"] = "partial"
    with pytest.raises(ValueError):
        ca.validate_case_run_document(document)


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def test_canonical_json_bytes_ends_with_single_trailing_newline() -> None:
    document = ca.to_json_dict(_success_artifact())
    data = ca.canonical_json_bytes(document)
    assert data.endswith(b"\n")
    assert not data.endswith(b"\n\n")


def test_canonical_json_bytes_is_deterministic() -> None:
    document = ca.to_json_dict(_success_artifact())
    assert ca.canonical_json_bytes(document) == ca.canonical_json_bytes(copy.deepcopy(document))


# ---------------------------------------------------------------------------
# required_targets_are_satisfied / Level1CCaseRunArtifact.required_targets_satisfied
# (1C-8c "required-target case gate" -- pure derivation, never a new
# run_status value)
# ---------------------------------------------------------------------------


def test_required_targets_satisfied_true_when_all_required_selected_and_conformant() -> None:
    assert ca.required_targets_are_satisfied(_triangle_selections()) is True


def test_required_targets_satisfied_false_when_a_required_target_is_ambiguous() -> None:
    selections = (
        _record("fundamental", "REQUIRED", selected=False, status="ambiguous"),
        _record("first_excited", "REQUIRED", selected=True),
        _record("T_max", "CALIBRATION_ONLY", selected=False),
    )
    assert ca.required_targets_are_satisfied(selections) is False


def test_required_targets_satisfied_false_when_a_required_target_is_not_in_window() -> None:
    selections = (
        _record("fundamental", "REQUIRED", selected=True),
        _record("first_excited", "REQUIRED", selected=False, status="not_in_window"),
        _record("T_max", "CALIBRATION_ONLY", selected=False),
    )
    assert ca.required_targets_are_satisfied(selections) is False


def test_required_targets_satisfied_false_when_required_selected_but_non_conformant() -> None:
    non_conformant = TargetSelectionRecord(
        target_id="first_excited",
        role="REQUIRED",
        selection_status="selected",
        spectral_window_group_index=5,
        selected_group_status="partial_subspace",
        meets_normative_requirements=False,
    )
    selections = (_record("fundamental", "REQUIRED", selected=True), non_conformant, _record("T_max", "CALIBRATION_ONLY", selected=False))
    assert ca.required_targets_are_satisfied(selections) is False


def test_required_targets_satisfied_ignores_calibration_only_non_conformance() -> None:
    """T_max selected-but-partial (non-conformant) never affects the
    gate, since it is CALIBRATION_ONLY."""
    t_max_partial = TargetSelectionRecord(
        target_id="T_max",
        role="CALIBRATION_ONLY",
        selection_status="selected",
        spectral_window_group_index=7,
        selected_group_status="partial_subspace",
        meets_normative_requirements=False,
    )
    selections = (
        _record("fundamental", "REQUIRED", selected=True),
        _record("first_excited", "REQUIRED", selected=True),
        t_max_partial,
    )
    assert ca.required_targets_are_satisfied(selections) is True


def test_case_run_artifact_property_matches_free_function_for_success() -> None:
    artifact = _success_artifact()
    assert artifact.required_targets_satisfied == ca.required_targets_are_satisfied(artifact.target_selections)
    assert artifact.required_targets_satisfied is True


def test_case_run_artifact_property_false_for_failed_run_regardless_of_content() -> None:
    """A failed run always has empty target_selections (enforced by
    __post_init__), so the free function would return True vacuously --
    the property must never do that: run_status is checked first."""
    artifact = _failed_artifact()
    assert artifact.target_selections == ()
    assert ca.required_targets_are_satisfied(artifact.target_selections) is True  # vacuous, documented
    assert artifact.required_targets_satisfied is False  # the property never trusts the vacuous case


def test_case_run_artifact_property_true_when_only_calibration_only_target_missing(manifest: m.Level1CManifest) -> None:
    without_t_max = _triangle_selections()[:-1]  # drops T_max (CALIBRATION_ONLY) only
    artifact = ca.Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id="level1c-j0-response-v1",
        manifest_fingerprint=_MANIFEST_FINGERPRINT,
        repository_commit=_REPO_COMMIT,
        case_id="x",
        geometry="triangle",
        spin=2,
        hamiltonian_case_id="j0-1.00",
        sector_id="default",
        spectral_window=9,
        run_status="success",
        target_selections=without_t_max,
        records_sha256=_SHA256,
        record_count=5,
    )
    # Both REQUIRED targets are still present and conformant -- the gate
    # is still True even though T_max (CALIBRATION_ONLY) is absent.
    assert artifact.required_targets_satisfied is True


def test_case_run_artifact_property_false_when_required_target_ambiguous(manifest: m.Level1CManifest) -> None:
    selections = (
        _record("fundamental", "REQUIRED", selected=True),
        _record("first_excited", "REQUIRED", selected=False, status="ambiguous"),
        _record("T_max", "CALIBRATION_ONLY", selected=False),
    )
    artifact = ca.Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id="level1c-j0-response-v1",
        manifest_fingerprint=_MANIFEST_FINGERPRINT,
        repository_commit=_REPO_COMMIT,
        case_id="x",
        geometry="triangle",
        spin=2,
        hamiltonian_case_id="j0-1.00",
        sector_id="default",
        spectral_window=9,
        run_status="success",
        target_selections=selections,
        records_sha256=_SHA256,
        record_count=5,
    )
    assert artifact.required_targets_satisfied is False
