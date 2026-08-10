from __future__ import annotations

from pathlib import Path

import pytest
from level1c_launcher_helpers import (
    Recorder,
    _FakeGateArtifact,
    empty_success_phase_p_report,
    failed_phase_p_report,
    patch_cleanliness,
    patch_gate,
    patch_git,
    patch_load_manifest,
    patch_response,
    patch_run_level1c_campaign,
    patch_tracking,
    setup_full_success_chain,
)

from scripts.level1c_launcher.launch import (
    COMPLETED,
    STOP_BEFORE_GATE,
    STOP_NORMATIVE_PIPELINE_BEFORE_T,
    NormativeLaunchError,
    launch_normative_campaign,
)

SHA_A = "a" * 40
SHA_B = "b" * 40


def _historical_dir(tmp_path: Path) -> Path:
    historical = tmp_path / "historical"
    historical.mkdir(parents=True, exist_ok=True)
    return historical


# ---------------------------------------------------------------------------
# TOCTOU: pre-PHASE_P and post-PHASE_P re-verification.
# ---------------------------------------------------------------------------


def test_pre_p_head_change_stops_before_p(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_B), branch_values=(real_manifest.branch, real_manifest.branch))
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())

    with pytest.raises(NormativeLaunchError, match="HEAD changed before PHASE_P"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_level1c_campaign_calls == []


def test_pre_p_branch_change_stops_before_p(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A), branch_values=(real_manifest.branch, "elsewhere"))
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())

    with pytest.raises(NormativeLaunchError, match="branch changed before PHASE_P"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_level1c_campaign_calls == []


def test_pre_p_dirty_stops_before_p(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A), branch_values=(real_manifest.branch, real_manifest.branch))
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (False, ("scripts/x.py",))))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())

    with pytest.raises(NormativeLaunchError, match="unclean before PHASE_P") as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert excinfo.value.dirty_paths == ("scripts/x.py",)
    assert recorder.run_level1c_campaign_calls == []


def test_post_p_head_change_stops_before_gate(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_B), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))

    with pytest.raises(NormativeLaunchError, match="HEAD changed after PHASE_P"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    # P DID run (it is the phase whose completion triggers this check) --
    # but the gate must never be reached.
    assert len(recorder.run_level1c_campaign_calls) == 1
    assert recorder.run_gate_calls == []


def test_post_p_branch_change_stops_before_gate(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch, real_manifest.branch, "elsewhere"))
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))

    with pytest.raises(NormativeLaunchError, match="branch changed after PHASE_P"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_gate_calls == []


def test_post_p_dirty_stops_before_gate(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (False, ("experiments/x.json",))))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))

    with pytest.raises(NormativeLaunchError, match="unclean after PHASE_P") as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert excinfo.value.dirty_paths == ("experiments/x.json",)
    assert recorder.run_gate_calls == []


def test_repository_commit_never_replaced_by_post_p_reread(monkeypatch, real_manifest, tmp_path: Path) -> None:
    """Even though the post-P check re-reads HEAD, the value forwarded to
    the gate/T/R must remain the ORIGINAL one resolved at prepare time --
    never a later re-read (the check is an equality assertion, not a
    re-adoption)."""
    recorder = Recorder()
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=_historical_dir(tmp_path))
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_level1c_campaign_calls[0]["repository_commit"] == SHA_A
    assert recorder.run_gate_calls[0]["repository_commit"] == SHA_A
    assert recorder.run_tracking_calls[0]["repository_commit"] == SHA_A
    assert recorder.run_r_calls[0]["repository_commit"] == SHA_A


def test_three_head_branch_cleanliness_checks_performed_on_full_success(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=_historical_dir(tmp_path))
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert len(recorder.head_calls) == 3
    assert len(recorder.branch_calls) == 3
    assert len(recorder.cleanliness_calls) == 3


# ---------------------------------------------------------------------------
# P global_success == False -> STOP_BEFORE_GATE, nothing downstream called.
# ---------------------------------------------------------------------------


def test_p_failure_yields_stop_before_gate(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A), branch_values=(real_manifest.branch, real_manifest.branch))
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, failed_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))
    patch_tracking(monkeypatch, recorder)
    patch_response(monkeypatch, recorder)

    report = launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert report.pipeline_status == STOP_BEFORE_GATE
    assert report.gate_artifact is None
    assert report.tracking_records is None
    assert report.response_records is None
    assert recorder.run_gate_calls == []
    assert recorder.run_tracking_calls == []
    assert recorder.run_r_calls == []
    # Only 2 checks (prepare + pre-P): the post-P check never happens
    # because P's own failure is detected before it would run.
    assert len(recorder.head_calls) == 2


# ---------------------------------------------------------------------------
# Gate FAIL -> STOP_NORMATIVE_PIPELINE_BEFORE_T; artifact still persisted;
# T/R never called.
# ---------------------------------------------------------------------------


def test_gate_fail_yields_stop_before_t_and_is_persisted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    fail_artifact = _FakeGateArtifact(gate_status="FAIL")
    patch_gate(monkeypatch, recorder, artifact=fail_artifact)
    patch_tracking(monkeypatch, recorder)
    patch_response(monkeypatch, recorder)

    report = launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert report.pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T
    assert report.gate_artifact is fail_artifact
    assert report.tracking_records is None
    assert report.response_records is None
    # The artifact was persisted BEFORE the FAIL verdict stopped the pipeline.
    assert len(recorder.write_gate_calls) == 1
    assert recorder.write_gate_calls[0]["artifact"] is fail_artifact
    assert recorder.run_tracking_calls == []
    assert recorder.run_r_calls == []


def test_gate_artifact_write_happens_before_status_inspection(monkeypatch, real_manifest, tmp_path: Path) -> None:
    """A write_gate_artifact failure must propagate -- the pipeline must
    never claim a gate verdict was reached if its artifact was not
    durably persisted."""
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"), write_raises=RuntimeError("disk full"))
    patch_tracking(monkeypatch, recorder)
    patch_response(monkeypatch, recorder)

    with pytest.raises(RuntimeError, match="disk full"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_tracking_calls == []


# ---------------------------------------------------------------------------
# Gate PASS -> T -> write -> R -> write -> COMPLETED, exact order.
# ---------------------------------------------------------------------------


def test_gate_pass_runs_t_then_r_in_order(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=_historical_dir(tmp_path))
    report = launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))

    assert report.pipeline_status == COMPLETED
    assert report.gate_artifact.gate_status == "PASS"
    assert report.tracking_records == ("fake-tracking-record",)
    assert report.response_records == ("fake-response-record",)
    assert len(recorder.run_tracking_calls) == 1
    assert len(recorder.write_tracking_calls) == 1
    assert len(recorder.run_r_calls) == 1
    assert len(recorder.write_r_calls) == 1


def test_r_never_called_if_write_tracking_records_fails(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))
    patch_tracking(monkeypatch, recorder, write_raises=RuntimeError("tracking write failed"))
    patch_response(monkeypatch, recorder)

    with pytest.raises(RuntimeError, match="tracking write failed"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_r_calls == []
    assert recorder.write_r_calls == []


def test_write_response_records_failure_propagates(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A, SHA_A), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))
    patch_tracking(monkeypatch, recorder)
    patch_response(monkeypatch, recorder, write_raises=RuntimeError("response write failed"))

    with pytest.raises(RuntimeError, match="response write failed"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))


def test_same_manifest_object_forwarded_to_every_phase(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=_historical_dir(tmp_path))
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_level1c_campaign_calls[0]["manifest"] is real_manifest
    assert recorder.run_gate_calls[0]["manifest"] is real_manifest
    assert recorder.run_tracking_calls[0]["manifest"] is real_manifest
    assert recorder.run_r_calls[0]["manifest"] is real_manifest
    assert len(recorder.load_manifest_calls) == 1


def test_historical_output_dir_forwarded_to_gate(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    historical = _historical_dir(tmp_path)
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=historical)
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=historical)
    assert recorder.run_gate_calls[0]["historical_output_dir"] == historical.resolve()


# ---------------------------------------------------------------------------
# Re-launch when P is already fully reusable -> gate/T/R still executed
# (never silently skipped); T/R always recomputed/rewritten, never reused
# (T_R_CACHE_REUSE_IMPLEMENTED = NO, 1C-8i, ratified).
# ---------------------------------------------------------------------------


def test_relaunch_with_fully_reusable_p_still_runs_gate_and_recomputes_t_r(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    setup_full_success_chain(monkeypatch, recorder, real_manifest, historical_dir=_historical_dir(tmp_path))
    # phase_p_report already reflects reused_success_count > 0 -- global_success is still True.
    from scripts.level1c_campaign.campaign import Level1CCampaignExecutionReport, Level1CCaseOrchestrationOutcome

    reused_report = Level1CCampaignExecutionReport(
        case_outcomes=(Level1CCaseOrchestrationOutcome(case_id="x", status="skipped_existing_valid", errors=()),),
        total_required=1, executed_success_count=0, reused_success_count=1,
        resource_guardrail_exceeded_count=0, failed_count=0, global_success=True,
    )
    patch_run_level1c_campaign(monkeypatch, recorder, reused_report)

    report = launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert report.pipeline_status == COMPLETED
    assert report.phase_p_report.reused_success_count == 1
    # gate/T/R still ran and their writers were still called (never
    # skipped just because P itself was fully reused).
    assert len(recorder.run_gate_calls) == 1
    assert len(recorder.run_tracking_calls) == 1
    assert len(recorder.write_tracking_calls) == 1
    assert len(recorder.run_r_calls) == 1
    assert len(recorder.write_r_calls) == 1
