"""Unit tests for scripts.level2_campaign.outputs (lot
L2-E-CAMPAIGN-INFRASTRUCTURE, extended by
L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER). Filesystem-only for the
lower-level primitives; case-result read/write tests build a real,
schema-valid document via cosmobox.level2.serialization.case_result_payload
from hand-constructed, fully synthetic MultipletProfileEntry/
CaseExecutionResult objects -- no diagonalization anywhere in this file.
"""

from __future__ import annotations

import json

import pytest

from cosmobox.level2 import metrics, orchestration, serialization
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import CaseExecutionResult, CaseSpec
from scripts.level2_campaign.outputs import (
    CampaignSummaryAlreadyExists,
    CaseArtifactAlreadyExists,
    CaseArtifactIntegrityError,
    atomic_write_json,
    campaign_manifest_path,
    campaign_output_dir,
    campaign_summary_path,
    canonical_json_bytes,
    case_artifact_path,
    load_and_verify_case_result,
    verify_case_artifacts_share_provenance,
    write_campaign_manifest,
    write_campaign_summary,
    write_case_result,
)

_PROVENANCE = dict(
    campaign_id="level2-energy-regime-v1",
    manifest_fingerprint="a" * 64,
    repository_commit="b" * 40,
    branch="research/level2-energy-regime",
    frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
    numerical_guard_m_tt=1e-16,
    numerical_guard_r_eff=1e-15,
    numerical_guard_scope="DELTA_HL_ONLY",
)


def _entry(seed: float) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=0.0,
        multiplicity=1,
        epsilon=0.0,
        q_start=0.0,
        q_end=1.0,
        q_midpoint=0.5,
        m_tt=seed,
        r_eff=metrics.Available(0.1 * seed, None),
        a_qq=0.5,
        m_qq=metrics.Available(0.2, None),
        c_tt_conn=[[seed, 0.0], [0.0, seed]],
        rho_qq={
            (0, 1): metrics.RhoQQEntry(value=0.1, null_reason=None),
            (1, 0): metrics.RhoQQEntry(value=None, null_reason="ZERO_LOCAL_CHARGE_VARIANCE"),
        },
    )


def _case_result_document(geometry: str, spin: int, *, provenance: dict = _PROVENANCE) -> dict:
    entries = (_entry(1.0),)
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}
    result = CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin),
        dimension=1,
        group_count=1,
        entries=entries,
        m_tt_analysis=analyses["M_TT"],
        r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"],
        m_qq_analysis=analyses["M_QQ"],
    )
    return serialization.case_result_payload(result, **provenance)


def test_canonical_json_bytes_is_sorted_deterministic_and_newline_terminated():
    payload_a = canonical_json_bytes({"b": 1, "a": 2})
    payload_b = canonical_json_bytes({"a": 2, "b": 1})
    assert payload_a == payload_b
    assert payload_a.endswith(b"\n")
    assert json.loads(payload_a) == {"a": 2, "b": 1}


def test_atomic_write_json_creates_parent_directories_and_content(tmp_path):
    path = tmp_path / "nested" / "dir" / "document.json"
    atomic_write_json(path, {"hello": "world"})
    assert path.exists()
    assert json.loads(path.read_text()) == {"hello": "world"}


def test_atomic_write_json_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "document.json"
    atomic_write_json(path, {"a": 1})
    remaining = list(tmp_path.iterdir())
    assert remaining == [path]


def test_atomic_write_json_does_not_leave_a_partial_temp_file_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "document.json"

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("os.replace", _boom)
    with pytest.raises(RuntimeError):
        atomic_write_json(path, {"a": 1})
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_campaign_output_dir_and_summary_path_layout(tmp_path):
    output_dir = campaign_output_dir(tmp_path, "level2-energy-regime-v1")
    assert output_dir == tmp_path / "level2-energy-regime-v1"
    summary_path = campaign_summary_path(tmp_path, "level2-energy-regime-v1")
    assert summary_path == output_dir / "campaign-summary.json"


def test_write_campaign_summary_is_atomic_and_readable(tmp_path):
    document = {"schema_version": "level2-campaign-summary-v1", "campaign_status": "COMPLETE"}
    path = write_campaign_summary(tmp_path, "level2-energy-regime-v1", document)
    assert path == campaign_summary_path(tmp_path, "level2-energy-regime-v1")
    assert json.loads(path.read_text()) == document


def test_write_campaign_summary_refuses_to_overwrite_existing(tmp_path):
    document = {"schema_version": "level2-campaign-summary-v1", "campaign_status": "COMPLETE"}
    write_campaign_summary(tmp_path, "level2-energy-regime-v1", document)
    with pytest.raises(CampaignSummaryAlreadyExists):
        write_campaign_summary(tmp_path, "level2-energy-regime-v1", document)


# ---------------------------------------------------------------------------
# campaign_manifest_path / write_campaign_manifest
# ---------------------------------------------------------------------------


def test_campaign_manifest_path_layout(tmp_path):
    path = campaign_manifest_path(tmp_path, "level2-energy-regime-v1")
    assert path == campaign_output_dir(tmp_path, "level2-energy-regime-v1") / "manifest.json"


def test_write_campaign_manifest_is_atomic_and_readable(tmp_path):
    raw = {"campaign_id": "level2-energy-regime-v1", "cases": []}
    path = write_campaign_manifest(tmp_path, "level2-energy-regime-v1", raw)
    assert path == campaign_manifest_path(tmp_path, "level2-energy-regime-v1")
    assert json.loads(path.read_text()) == raw


# ---------------------------------------------------------------------------
# case_artifact_path / write_case_result
# ---------------------------------------------------------------------------


def test_case_artifact_path_layout(tmp_path):
    path = case_artifact_path(tmp_path, "level2-energy-regime-v1", "triangle", 2)
    assert path == campaign_output_dir(tmp_path, "level2-energy-regime-v1") / "cases" / "triangle-S2.json"


def test_write_case_result_is_atomic_and_readable(tmp_path):
    document = _case_result_document("triangle", 2)
    path = write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)
    assert path == case_artifact_path(tmp_path, "level2-energy-regime-v1", "triangle", 2)
    assert json.loads(path.read_text()) == document


def test_write_case_result_refuses_to_overwrite_existing(tmp_path):
    document = _case_result_document("triangle", 2)
    write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)
    with pytest.raises(CaseArtifactAlreadyExists):
        write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)


# ---------------------------------------------------------------------------
# load_and_verify_case_result
# ---------------------------------------------------------------------------


def test_load_and_verify_case_result_round_trips_a_valid_artifact(tmp_path):
    document = _case_result_document("ring4", 3)
    write_case_result(tmp_path, "level2-energy-regime-v1", "ring4", 3, document)
    loaded = load_and_verify_case_result(
        tmp_path, "level2-energy-regime-v1", "ring4", 3,
        manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
        repository_commit=_PROVENANCE["repository_commit"],
    )
    assert loaded == document


def test_load_and_verify_case_result_raises_when_artifact_missing(tmp_path):
    with pytest.raises(CaseArtifactIntegrityError):
        load_and_verify_case_result(
            tmp_path, "level2-energy-regime-v1", "ring4", 3,
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )


def test_load_and_verify_case_result_raises_on_schema_invalid_artifact(tmp_path):
    document = _case_result_document("triangle", 2)
    del document["multiplet_entries"]
    atomic_write_json(case_artifact_path(tmp_path, "level2-energy-regime-v1", "triangle", 2), document)
    with pytest.raises(CaseArtifactIntegrityError):
        load_and_verify_case_result(
            tmp_path, "level2-energy-regime-v1", "triangle", 2,
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )


def test_load_and_verify_case_result_raises_on_repository_commit_mismatch(tmp_path):
    document = _case_result_document("triangle", 2)
    write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)
    with pytest.raises(CaseArtifactIntegrityError):
        load_and_verify_case_result(
            tmp_path, "level2-energy-regime-v1", "triangle", 2,
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit="c" * 40,
        )


def test_load_and_verify_case_result_raises_on_manifest_fingerprint_mismatch(tmp_path):
    document = _case_result_document("triangle", 2)
    write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)
    with pytest.raises(CaseArtifactIntegrityError):
        load_and_verify_case_result(
            tmp_path, "level2-energy-regime-v1", "triangle", 2,
            manifest_fingerprint="z" * 64,
            repository_commit=_PROVENANCE["repository_commit"],
        )


def test_load_and_verify_case_result_raises_on_campaign_id_mismatch(tmp_path):
    document = _case_result_document("triangle", 2)
    write_case_result(tmp_path, "level2-energy-regime-v1", "triangle", 2, document)
    with pytest.raises(CaseArtifactIntegrityError):
        load_and_verify_case_result(
            tmp_path, "other-campaign-id", "triangle", 2,
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )


# ---------------------------------------------------------------------------
# verify_case_artifacts_share_provenance
# ---------------------------------------------------------------------------


def test_verify_case_artifacts_share_provenance_passes_when_consistent(tmp_path):
    for geometry, spin in (("triangle", 2), ("triangle", 3)):
        write_case_result(tmp_path, "level2-energy-regime-v1", geometry, spin, _case_result_document(geometry, spin))
    documents = verify_case_artifacts_share_provenance(
        tmp_path, "level2-energy-regime-v1", [("triangle", 2), ("triangle", 3)],
        manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
        repository_commit=_PROVENANCE["repository_commit"],
    )
    assert len(documents) == 2


def test_verify_case_artifacts_share_provenance_raises_on_mixed_repository_commit(tmp_path):
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 2, _case_result_document("triangle", 2)
    )
    mismatched_provenance = dict(_PROVENANCE, repository_commit="d" * 40)
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 3,
        _case_result_document("triangle", 3, provenance=mismatched_provenance),
    )
    with pytest.raises(CaseArtifactIntegrityError):
        verify_case_artifacts_share_provenance(
            tmp_path, "level2-energy-regime-v1", [("triangle", 2), ("triangle", 3)],
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )


def test_verify_case_artifacts_share_provenance_raises_on_mixed_manifest_fingerprint(tmp_path):
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 2, _case_result_document("triangle", 2)
    )
    mismatched_provenance = dict(_PROVENANCE, manifest_fingerprint="e" * 64)
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 3,
        _case_result_document("triangle", 3, provenance=mismatched_provenance),
    )
    with pytest.raises(CaseArtifactIntegrityError):
        verify_case_artifacts_share_provenance(
            tmp_path, "level2-energy-regime-v1", [("triangle", 2), ("triangle", 3)],
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )


def test_verify_case_artifacts_share_provenance_raises_on_mixed_campaign_id(tmp_path):
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 2, _case_result_document("triangle", 2)
    )
    mismatched_provenance = dict(_PROVENANCE, campaign_id="other-campaign-id")
    write_case_result(
        tmp_path, "level2-energy-regime-v1", "triangle", 3,
        _case_result_document("triangle", 3, provenance=mismatched_provenance),
    )
    with pytest.raises(CaseArtifactIntegrityError):
        verify_case_artifacts_share_provenance(
            tmp_path, "level2-energy-regime-v1", [("triangle", 2), ("triangle", 3)],
            manifest_fingerprint=_PROVENANCE["manifest_fingerprint"],
            repository_commit=_PROVENANCE["repository_commit"],
        )
