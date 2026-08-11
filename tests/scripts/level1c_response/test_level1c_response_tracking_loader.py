from __future__ import annotations

from pathlib import Path

import pytest
from level1c_response_helpers import REPO_COMMIT

from cosmobox.level1.matching import SymmetryLabel
from experiments.level1c.planning import build_level1c_campaign_plan, build_tracking_edges
from scripts.level1c_baseline_gate.gate import REQUIRED_TARGET_IDS
from scripts.level1c_tracking.tracking import (
    NOT_AVAILABLE,
    TrackingArtifactIntegrityError,
    TrackingRecord,
    load_and_verify_tracking_records,
    write_tracking_records,
)


def _make_canonical_records(level1c_manifest) -> tuple[TrackingRecord, ...]:
    cases = build_level1c_campaign_plan(level1c_manifest)
    cases_by_id = {case.case_id: case for case in cases}
    edges = build_tracking_edges(cases)
    records = []
    for perturbed_case_id, baseline_case_id in edges:
        geometry = cases_by_id[baseline_case_id].geometry
        spin = cases_by_id[baseline_case_id].spin
        for target_id in REQUIRED_TARGET_IDS[geometry]:
            records.append(
                TrackingRecord(
                    schema_version="level1c-tracking-record-v1",
                    campaign_id=level1c_manifest.campaign_id,
                    repository_commit=REPO_COMMIT,
                    manifest_fingerprint=level1c_manifest.fingerprint,
                    geometry=geometry,
                    spin=spin,
                    baseline_case_id=baseline_case_id,
                    perturbed_case_id=perturbed_case_id,
                    baseline_hamiltonian_case_id=cases_by_id[baseline_case_id].hamiltonian_case_id,
                    perturbed_hamiltonian_case_id=cases_by_id[perturbed_case_id].hamiltonian_case_id,
                    target_id=target_id,
                    baseline_group_index=0,
                    baseline_multiplicity=1,
                    baseline_twice_T=0,
                    baseline_reflection_label=SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)),
                    status=NOT_AVAILABLE,
                    candidate_group_index=None,
                    candidate_multiplicity=None,
                    candidate_twice_T=None,
                    candidate_reflection_label=None,
                    class_pool_size=0,
                    failure_reasons=("CLASS_POOL_EMPTY",),
                )
            )
    return tuple(records)


def test_load_and_verify_tracking_records_success(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)
    write_tracking_records(tmp_path, records)
    documents = load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)
    assert len(documents) == 40


def test_load_and_verify_tracking_records_missing_file(tmp_path: Path, level1c_manifest) -> None:
    with pytest.raises(TrackingArtifactIntegrityError, match="missing tracking.jsonl"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)


def test_load_and_verify_tracking_records_wrong_repository_commit(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)
    write_tracking_records(tmp_path, records)
    with pytest.raises(TrackingArtifactIntegrityError, match="repository_commit"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit="1" * 40)


def test_load_and_verify_tracking_records_count_not_40(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)[:39]
    write_tracking_records(tmp_path, records)
    with pytest.raises(TrackingArtifactIntegrityError, match="canonical expected sequence"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)


def test_load_and_verify_tracking_records_duplicate_rejected(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)
    records = records[:39] + (records[0],)
    write_tracking_records(tmp_path, records)
    with pytest.raises(TrackingArtifactIntegrityError, match="canonical expected sequence"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)


def test_load_and_verify_tracking_records_reordered_rejected(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)
    records = (records[1], records[0]) + records[2:]
    write_tracking_records(tmp_path, records)
    with pytest.raises(TrackingArtifactIntegrityError, match="canonical expected sequence"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)


def test_load_and_verify_tracking_records_internal_blank_line_rejected(tmp_path: Path, level1c_manifest) -> None:
    records = _make_canonical_records(level1c_manifest)
    write_tracking_records(tmp_path, records)
    path = tmp_path / "tracking.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.insert(1, "")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(TrackingArtifactIntegrityError, match="empty"):
        load_and_verify_tracking_records(tmp_path, level1c_manifest, repository_commit=REPO_COMMIT)
