from __future__ import annotations

from pathlib import Path

from level1c_tracking_helpers import (
    REPO_COMMIT,
    make_group_structural_data,
    real_baseline_case_id,
    real_level1c_case_id,
    write_level1c_case,
    write_level1c_failed_case,
)

from scripts.level1c_tracking.tracking import load_baseline_for_tracking, load_perturbed_for_tracking


def test_load_baseline_for_tracking_success(tmp_path: Path, level1c_manifest) -> None:
    case_id = real_baseline_case_id(level1c_manifest, "triangle", 2)
    fundamental = make_group_structural_data(0, twice_T=0, multiplicity=1)
    first_excited = make_group_structural_data(1, twice_T=1, multiplicity=2)
    write_level1c_case(
        tmp_path, case_id=case_id, geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00",
        manifest_fingerprint=level1c_manifest.fingerprint, campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT,
        target_group_data={"fundamental": (0, fundamental), "first_excited": (1, first_excited)},
        role_by_target={"fundamental": "REQUIRED", "first_excited": "REQUIRED"},
    )
    run_document, records, failure_reason = load_baseline_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert failure_reason is None
    assert run_document["case_id"] == case_id
    assert len(records) > 0


def test_load_baseline_for_tracking_missing_case(tmp_path: Path, level1c_manifest) -> None:
    case_id = real_baseline_case_id(level1c_manifest, "triangle", 2)
    run_document, records, failure_reason = load_baseline_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert run_document is None
    assert records is None
    assert failure_reason is not None


def test_load_baseline_for_tracking_normative_case_valid_false_rejected(tmp_path: Path, level1c_manifest) -> None:
    """A normatively invalid baseline is never usable as a tracking
    branch source (matches 1C-8d's own baseline gate discipline)."""
    import hashlib
    import json

    from experiments.level1c.case_artifact import Level1CCaseRunArtifact, canonical_json_bytes, to_json_dict
    from experiments.level1c.target_selection import TargetSelectionRecord
    from level1c_tracking_helpers import _group_documents

    case_id = real_baseline_case_id(level1c_manifest, "triangle", 2)
    fundamental = make_group_structural_data(0, twice_T=0, multiplicity=1)
    documents = _group_documents(
        geometry="triangle", spin=2, repository_commit=REPO_COMMIT, manifest_fingerprint=level1c_manifest.fingerprint,
        campaign_id=level1c_manifest.campaign_id, group_index=0, data=fundamental, hamiltonian_case_id="j0-1.00",
    )
    target_selections = (
        TargetSelectionRecord(
            target_id="fundamental", role="REQUIRED", selection_status="selected",
            spectral_window_group_index=0, selected_group_status="complete_multiplet", meets_normative_requirements=True,
        ),
        TargetSelectionRecord(
            target_id="first_excited", role="REQUIRED", selection_status="ambiguous",
            spectral_window_group_index=None, selected_group_status=None, meets_normative_requirements=None,
        ),
    )
    records_bytes = b"".join(
        (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        for document in documents
    )
    artifact = Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1", campaign_id=level1c_manifest.campaign_id,
        manifest_fingerprint=level1c_manifest.fingerprint, repository_commit=REPO_COMMIT, case_id=case_id,
        geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00", sector_id="default", spectral_window=99,
        run_status="success", target_selections=target_selections,
        records_sha256=hashlib.sha256(records_bytes).hexdigest(), record_count=len(documents),
        normative_case_valid=False,
    )
    case_dir = tmp_path / "runs" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "records.jsonl").write_bytes(records_bytes)
    (case_dir / "run.json").write_bytes(canonical_json_bytes(to_json_dict(artifact)))

    run_document, records, failure_reason = load_baseline_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert run_document is None
    assert "normative_case_valid" in failure_reason


def test_load_baseline_for_tracking_provenance_mismatch(tmp_path: Path, level1c_manifest) -> None:
    case_id = real_baseline_case_id(level1c_manifest, "triangle", 2)
    fundamental = make_group_structural_data(0, twice_T=0, multiplicity=1)
    first_excited = make_group_structural_data(1, twice_T=1, multiplicity=2)
    write_level1c_case(
        tmp_path, case_id=case_id, geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00",
        manifest_fingerprint=level1c_manifest.fingerprint, campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT,
        target_group_data={"fundamental": (0, fundamental), "first_excited": (1, first_excited)},
        role_by_target={"fundamental": "REQUIRED", "first_excited": "REQUIRED"},
    )
    run_document, records, failure_reason = load_baseline_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit="1" * 40
    )
    assert run_document is None
    assert "REPOSITORY_COMMIT_MISMATCH" in failure_reason


def test_load_perturbed_for_tracking_success(tmp_path: Path, level1c_manifest) -> None:
    case_id = real_level1c_case_id(level1c_manifest, "triangle", 2, "j0-0.75")
    fundamental = make_group_structural_data(0, twice_T=0, multiplicity=1)
    write_level1c_case(
        tmp_path, case_id=case_id, geometry="triangle", spin=2, hamiltonian_case_id="j0-0.75",
        manifest_fingerprint=level1c_manifest.fingerprint, campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT,
        target_group_data={"fundamental": (0, fundamental)},
        role_by_target={"fundamental": "REQUIRED"},
    )
    run_document, records, failure_reason = load_perturbed_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert failure_reason is None
    assert run_document["case_id"] == case_id


def test_load_perturbed_for_tracking_technical_failure(tmp_path: Path, level1c_manifest) -> None:
    case_id = real_level1c_case_id(level1c_manifest, "triangle", 2, "j0-0.75")
    write_level1c_failed_case(
        tmp_path, case_id=case_id, geometry="triangle", spin=2, hamiltonian_case_id="j0-0.75",
        manifest_fingerprint=level1c_manifest.fingerprint, campaign_id=level1c_manifest.campaign_id,
        repository_commit=REPO_COMMIT, run_status="failed",
    )
    run_document, records, failure_reason = load_perturbed_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert run_document is None
    assert records is None
    assert "run_status" in failure_reason


def test_load_perturbed_for_tracking_ignores_normative_case_valid(tmp_path: Path, level1c_manifest) -> None:
    """A perturbed case with run_status=success but normative_case_valid
    False (e.g. first_excited ambiguous) must still be fully loadable --
    PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE=IRRELEVANT_TO_STRUCTURAL_
    TRACKING."""
    import hashlib
    import json

    from experiments.level1c.case_artifact import Level1CCaseRunArtifact, canonical_json_bytes, to_json_dict
    from experiments.level1c.target_selection import TargetSelectionRecord
    from level1c_tracking_helpers import _group_documents

    case_id = real_level1c_case_id(level1c_manifest, "triangle", 2, "j0-0.75")
    fundamental = make_group_structural_data(0, twice_T=0, multiplicity=1)
    documents = _group_documents(
        geometry="triangle", spin=2, repository_commit=REPO_COMMIT, manifest_fingerprint=level1c_manifest.fingerprint,
        campaign_id=level1c_manifest.campaign_id, group_index=0, data=fundamental, hamiltonian_case_id="j0-0.75",
    )
    target_selections = (
        TargetSelectionRecord(
            target_id="fundamental", role="REQUIRED", selection_status="selected",
            spectral_window_group_index=0, selected_group_status="complete_multiplet", meets_normative_requirements=True,
        ),
        TargetSelectionRecord(
            target_id="first_excited", role="REQUIRED", selection_status="ambiguous",
            spectral_window_group_index=None, selected_group_status=None, meets_normative_requirements=None,
        ),
    )
    records_bytes = b"".join(
        (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        for document in documents
    )
    artifact = Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1", campaign_id=level1c_manifest.campaign_id,
        manifest_fingerprint=level1c_manifest.fingerprint, repository_commit=REPO_COMMIT, case_id=case_id,
        geometry="triangle", spin=2, hamiltonian_case_id="j0-0.75", sector_id="default", spectral_window=99,
        run_status="success", target_selections=target_selections,
        records_sha256=hashlib.sha256(records_bytes).hexdigest(), record_count=len(documents),
        normative_case_valid=False,
    )
    case_dir = tmp_path / "runs" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "records.jsonl").write_bytes(records_bytes)
    (case_dir / "run.json").write_bytes(canonical_json_bytes(to_json_dict(artifact)))

    run_document, records, failure_reason = load_perturbed_for_tracking(
        tmp_path, case_id, level1c_manifest=level1c_manifest, repository_commit=REPO_COMMIT
    )
    assert failure_reason is None
    assert run_document["normative_case_valid"] is False
    assert records is not None
