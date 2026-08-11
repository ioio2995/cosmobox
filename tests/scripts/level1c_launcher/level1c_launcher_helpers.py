"""Non-fixture test helpers for the Level1C normative launcher test
suite. Deliberately NOT named conftest.py (see sibling packages'
identically-named helper modules for why): a plain `from conftest
import ...` in a test module collides across sibling test directories
collected in the same pytest invocation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.level1c_campaign.campaign import Level1CCampaignExecutionReport, Level1CCaseOrchestrationOutcome
from scripts.level1c_launcher import launch as launch_module


@dataclass(frozen=True, slots=True)
class _FakeGateArtifact:
    """Duck-typed stand-in: Level1CNormativeLaunchReport.__post_init__
    only ever reads `.gate_status` off this object -- a full,
    schema-valid BaselineNonRegressionArtifact is never required for
    orchestration-level tests (write_gate_artifact is itself always
    monkeypatched in those tests, so the real schema is never touched)."""

    gate_status: str


def empty_success_phase_p_report() -> Level1CCampaignExecutionReport:
    return Level1CCampaignExecutionReport(
        case_outcomes=(),
        total_required=0,
        executed_success_count=0,
        reused_success_count=0,
        resource_guardrail_exceeded_count=0,
        failed_count=0,
        global_success=True,
    )


def failed_phase_p_report() -> Level1CCampaignExecutionReport:
    return Level1CCampaignExecutionReport(
        case_outcomes=(Level1CCaseOrchestrationOutcome(case_id="x", status="failed", errors=("boom",)),),
        total_required=1,
        executed_success_count=0,
        reused_success_count=0,
        resource_guardrail_exceeded_count=0,
        failed_count=1,
        global_success=False,
    )


class Recorder:
    def __init__(self) -> None:
        self.head_calls: list[Path] = []
        self.branch_calls: list[Path] = []
        self.cleanliness_calls: list[Path] = []
        self.load_manifest_calls: list[tuple] = []
        self.run_level1c_campaign_calls: list[dict] = []
        self.run_gate_calls: list[dict] = []
        self.write_gate_calls: list[dict] = []
        self.run_tracking_calls: list[dict] = []
        self.write_tracking_calls: list[dict] = []
        self.run_r_calls: list[dict] = []
        self.write_r_calls: list[dict] = []


def patch_git(monkeypatch, recorder: Recorder, *, head_values, branch_values) -> None:
    head_iter = iter(head_values)
    branch_iter = iter(branch_values)

    def fake_head(repo_root):
        recorder.head_calls.append(repo_root)
        return next(head_iter)

    def fake_branch(repo_root):
        recorder.branch_calls.append(repo_root)
        return next(branch_iter)

    monkeypatch.setattr(launch_module, "_resolve_head_sha", fake_head)
    monkeypatch.setattr(launch_module, "_current_branch", fake_branch)


def patch_cleanliness(monkeypatch, recorder: Recorder, results) -> None:
    results_iter = iter(results)

    def fake(repo_root):
        recorder.cleanliness_calls.append(repo_root)
        return next(results_iter)

    monkeypatch.setattr(launch_module, "check_repository_cleanliness", fake)


def patch_load_manifest(monkeypatch, recorder: Recorder, manifest_obj) -> None:
    def fake(*args, **kwargs):
        recorder.load_manifest_calls.append((args, kwargs))
        return manifest_obj

    monkeypatch.setattr(launch_module, "load_manifest", fake)


def patch_run_level1c_campaign(monkeypatch, recorder: Recorder, report: Level1CCampaignExecutionReport) -> None:
    def fake(manifest, *, output_dir, repository_commit):
        recorder.run_level1c_campaign_calls.append(dict(manifest=manifest, output_dir=output_dir, repository_commit=repository_commit))
        return report

    monkeypatch.setattr(launch_module, "run_level1c_campaign", fake)


def patch_gate(monkeypatch, recorder: Recorder, *, artifact, write_raises: Exception | None = None) -> None:
    def fake_run_gate(manifest, level1c_output_dir, historical_output_dir, *, repository_commit):
        recorder.run_gate_calls.append(
            dict(manifest=manifest, level1c_output_dir=level1c_output_dir, historical_output_dir=historical_output_dir, repository_commit=repository_commit)
        )
        return artifact

    def fake_write_gate(output_dir, artifact_arg):
        recorder.write_gate_calls.append(dict(output_dir=output_dir, artifact=artifact_arg))
        if write_raises is not None:
            raise write_raises

    monkeypatch.setattr(launch_module, "run_baseline_nonregression_gate", fake_run_gate)
    monkeypatch.setattr(launch_module, "write_gate_artifact", fake_write_gate)


def patch_tracking(monkeypatch, recorder: Recorder, *, records=("fake-tracking-record",), write_raises: Exception | None = None) -> None:
    def fake_run(manifest, output_dir, *, repository_commit):
        recorder.run_tracking_calls.append(dict(manifest=manifest, output_dir=output_dir, repository_commit=repository_commit))
        return records

    def fake_write(output_dir, records_arg):
        recorder.write_tracking_calls.append(dict(output_dir=output_dir, records=records_arg))
        if write_raises is not None:
            raise write_raises

    monkeypatch.setattr(launch_module, "run_inter_j0_tracking", fake_run)
    monkeypatch.setattr(launch_module, "write_tracking_records", fake_write)


def patch_response(monkeypatch, recorder: Recorder, *, records=("fake-response-record",), write_raises: Exception | None = None) -> None:
    def fake_run(manifest, output_dir, *, repository_commit):
        recorder.run_r_calls.append(dict(manifest=manifest, output_dir=output_dir, repository_commit=repository_commit))
        return records

    def fake_write(output_dir, records_arg):
        recorder.write_r_calls.append(dict(output_dir=output_dir, records=records_arg))
        if write_raises is not None:
            raise write_raises

    monkeypatch.setattr(launch_module, "run_phase_r", fake_run)
    monkeypatch.setattr(launch_module, "write_response_records", fake_write)


def setup_full_success_chain(monkeypatch, recorder: Recorder, real_manifest, *, historical_dir: Path) -> None:
    """Wires every phase to succeed technically, with the gate PASSing --
    the full P -> gate -> T -> R chain reaches COMPLETED. head_values/
    branch_values/cleanliness_values each need exactly 3 entries: prepare,
    pre-PHASE_P, post-PHASE_P."""
    sha = "a" * 40
    patch_git(monkeypatch, recorder, head_values=(sha, sha, sha), branch_values=(real_manifest.branch,) * 3)
    patch_cleanliness(monkeypatch, recorder, ((True, ()), (True, ()), (True, ())))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    patch_gate(monkeypatch, recorder, artifact=_FakeGateArtifact(gate_status="PASS"))
    patch_tracking(monkeypatch, recorder)
    patch_response(monkeypatch, recorder)


def init_repo(repo_root: Path, branch: str) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "placeholder.py").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_root, check=True)
