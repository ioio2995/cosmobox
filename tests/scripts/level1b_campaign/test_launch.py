from __future__ import annotations

import dataclasses
import inspect
import subprocess
from pathlib import Path

import pytest

from experiments.level1 import manifest as manifest_module
from scripts import run_level1b_campaign as cli_module
from scripts.level1b_campaign import campaign as campaign_module
from scripts.level1b_campaign import launch as launch_module
from scripts.level1b_campaign.campaign import CampaignExecutionReport
from scripts.level1b_campaign.launch import (
    NormativeLaunchContext,
    NormativeLaunchError,
    launch_normative_campaign,
    prepare_normative_launch,
)

SHA_A = "a" * 40
SHA_B = "b" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "run_single_case",
    "build_campaign_plan",
    "matching",
    "MatchOutcome",
    "gamma_O",
    "G_occ",
    "path_phase_coherence",
)


# ---------------------------------------------------------------------------
# Fixtures -- the real manifest (load_manifest, pure, no diagonalization)
# supplies a genuine Manifest whose .branch is exactly
# "research/level1-correlators" (confirmed empirically); Git and
# run_campaign are always monkeypatched with recording/sequencing fakes.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


class _Recorder:
    def __init__(self) -> None:
        self.head_calls: list[Path] = []
        self.branch_calls: list[Path] = []
        self.cleanliness_calls: list[Path] = []
        self.load_manifest_calls: list[tuple] = []
        self.run_campaign_calls: list[dict] = []


def _patch_git(monkeypatch, recorder: _Recorder, *, head_values, branch_values) -> None:
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


def _patch_cleanliness(monkeypatch, recorder: _Recorder, results) -> None:
    results_iter = iter(results)

    def fake(repo_root):
        recorder.cleanliness_calls.append(repo_root)
        return next(results_iter)

    monkeypatch.setattr(launch_module, "check_repository_cleanliness", fake)


def _patch_load_manifest(monkeypatch, recorder: _Recorder, manifest_obj) -> None:
    def fake(*args, **kwargs):
        recorder.load_manifest_calls.append((args, kwargs))
        return manifest_obj

    monkeypatch.setattr(launch_module, "load_manifest", fake)


def _patch_run_campaign(monkeypatch, recorder: _Recorder, report: CampaignExecutionReport) -> None:
    def fake(manifest, *, output_dir, repository_commit):
        recorder.run_campaign_calls.append(
            dict(manifest=manifest, output_dir=output_dir, repository_commit=repository_commit)
        )
        return report

    monkeypatch.setattr(launch_module, "run_campaign", fake)


def _empty_success_report() -> CampaignExecutionReport:
    return CampaignExecutionReport(
        case_outcomes=(),
        total_required=0,
        executed_success_count=0,
        reused_success_count=0,
        resource_guardrail_exceeded_count=0,
        failed_count=0,
        global_success=True,
    )


def _setup(
    monkeypatch,
    recorder: _Recorder,
    real_manifest: manifest_module.Manifest,
    *,
    head_values=(SHA_A, SHA_A),
    branch_values=None,
    cleanliness_values=((True, ()), (True, ())),
    manifest_obj=None,
) -> None:
    if branch_values is None:
        branch_values = (real_manifest.branch, real_manifest.branch)
    _patch_git(monkeypatch, recorder, head_values=head_values, branch_values=branch_values)
    _patch_cleanliness(monkeypatch, recorder, cleanliness_values)
    _patch_load_manifest(monkeypatch, recorder, manifest_obj if manifest_obj is not None else real_manifest)


# ---------------------------------------------------------------------------
# 1/2. HEAD derived automatically; no repository_commit parameter.
# ---------------------------------------------------------------------------


def test_head_sha_derived_automatically(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert context.repository_commit == SHA_A
    assert len(recorder.head_calls) == 1


def test_prepare_and_launch_signatures_have_no_repository_commit_parameter() -> None:
    for function in (prepare_normative_launch, launch_normative_campaign):
        parameters = inspect.signature(function).parameters
        assert "repository_commit" not in parameters
        assert set(parameters) == {"repo_root", "output_dir"}


# ---------------------------------------------------------------------------
# 3/4. load_manifest called without a path; no manifest_path exposed.
# ---------------------------------------------------------------------------


def test_load_manifest_called_without_path(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.load_manifest_calls == [((), {})]


def test_no_manifest_path_parameter_anywhere() -> None:
    for function in (prepare_normative_launch, launch_normative_campaign):
        assert "manifest_path" not in inspect.signature(function).parameters
        assert "manifest" not in inspect.signature(function).parameters


# ---------------------------------------------------------------------------
# 5/6/7/8. Branch read from manifest.branch; correct accepted, incorrect
# and detached-HEAD rejected.
# ---------------------------------------------------------------------------


def test_correct_branch_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert context.branch == real_manifest.branch


def test_incorrect_branch_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=("some-other-branch",))
    with pytest.raises(NormativeLaunchError, match="branch"):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")


def test_detached_head_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=("HEAD",))
    with pytest.raises(NormativeLaunchError):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")


def test_branch_is_compared_against_manifest_branch_field(monkeypatch, real_manifest, tmp_path: Path) -> None:
    """No hardcoded branch constant in launch.py -- a manifest with a
    different (but still valid) .branch value changes what is accepted."""
    other_manifest = dataclasses.replace(real_manifest, branch="a-different-normative-branch")
    recorder = _Recorder()
    _setup(
        monkeypatch,
        recorder,
        real_manifest,
        head_values=(SHA_A,),
        branch_values=("a-different-normative-branch",),
        manifest_obj=other_manifest,
    )
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert context.branch == "a-different-normative-branch"


# ---------------------------------------------------------------------------
# 9/10. Dirty repository rejected; dirty_paths propagated.
# ---------------------------------------------------------------------------


def test_dirty_repository_is_rejected_with_dirty_paths(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(
        monkeypatch,
        recorder,
        real_manifest,
        head_values=(SHA_A,),
        branch_values=(real_manifest.branch,),
        cleanliness_values=((False, ("src/dirty.py",)),),
    )
    with pytest.raises(NormativeLaunchError) as excinfo:
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert excinfo.value.dirty_paths == ("src/dirty.py",)


# ---------------------------------------------------------------------------
# 11. run_campaign never called after a prepare failure.
# ---------------------------------------------------------------------------


def test_run_campaign_never_called_after_prepare_failure(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=("wrong-branch",))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    with pytest.raises(NormativeLaunchError):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.run_campaign_calls == []


# ---------------------------------------------------------------------------
# Precondition-primitive error normalization (correctif to 92572f0):
# load_manifest() and check_repository_cleanliness() are themselves
# precondition primitives -- any exception they raise is exactly as much
# a launch precondition failure as a bad branch or a dirty tree, so it
# must be normalized to NormativeLaunchError (with the original
# exception preserved as __cause__), never left as a raw
# ValueError/CalledProcessError, and never allowed to be confused with
# an exception raised by run_campaign itself (a genuinely different
# kind of failure that must never be relabeled as a precondition
# failure).
# ---------------------------------------------------------------------------


def test_load_manifest_value_error_is_normalized(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _patch_git(monkeypatch, recorder, head_values=(SHA_A,), branch_values=(real_manifest.branch,))

    original = ValueError("manifest does not validate against its schema")

    def raising_load_manifest():
        raise original

    monkeypatch.setattr(launch_module, "load_manifest", raising_load_manifest)
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())

    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert excinfo.value.__cause__ is original
    assert recorder.run_campaign_calls == []


def test_first_cleanliness_check_process_error_is_normalized(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _patch_git(monkeypatch, recorder, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    _patch_load_manifest(monkeypatch, recorder, real_manifest)

    original = subprocess.CalledProcessError(1, ["git", "status", "--porcelain"])

    def raising_cleanliness(repo_root):
        raise original

    monkeypatch.setattr(launch_module, "check_repository_cleanliness", raising_cleanliness)
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())

    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert excinfo.value.__cause__ is original
    assert excinfo.value.dirty_paths == ()
    assert recorder.run_campaign_calls == []


def test_second_cleanliness_check_process_error_is_normalized(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _patch_git(monkeypatch, recorder, head_values=(SHA_A, SHA_A), branch_values=(real_manifest.branch, real_manifest.branch))
    _patch_load_manifest(monkeypatch, recorder, real_manifest)

    original = subprocess.CalledProcessError(1, ["git", "status", "--porcelain"])
    results = [(True, ())]

    def flaky_cleanliness(repo_root):
        recorder.cleanliness_calls.append(repo_root)
        if results:
            return results.pop(0)
        raise original

    monkeypatch.setattr(launch_module, "check_repository_cleanliness", flaky_cleanliness)
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())

    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert excinfo.value.__cause__ is original
    assert excinfo.value.dirty_paths == ()
    assert recorder.run_campaign_calls == []
    assert len(recorder.cleanliness_calls) == 2


def test_run_campaign_exception_is_not_converted_to_normative_launch_error(
    monkeypatch, real_manifest, tmp_path: Path
) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))

    def raising_run_campaign(manifest, *, output_dir, repository_commit):
        raise RuntimeError("run_campaign internal failure")

    monkeypatch.setattr(launch_module, "run_campaign", raising_run_campaign)

    with pytest.raises(RuntimeError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert not isinstance(excinfo.value, NormativeLaunchError)


def test_cli_normalizes_load_manifest_error_to_exit_code_2(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _patch_git(monkeypatch, recorder, head_values=(SHA_A,), branch_values=(real_manifest.branch,))

    def raising_load_manifest():
        raise ValueError("bad manifest")

    monkeypatch.setattr(launch_module, "load_manifest", raising_load_manifest)

    exit_code = cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path / "repo")])
    assert exit_code == 2


def test_cli_does_not_catch_run_campaign_exceptions(monkeypatch, tmp_path: Path) -> None:
    def raising_launch(repo_root, *, output_dir):
        raise RuntimeError("run_campaign internal failure")

    monkeypatch.setattr(cli_module, "launch_normative_campaign", raising_launch)
    with pytest.raises(RuntimeError):
        cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path)])


# ---------------------------------------------------------------------------
# 12. Context carries the exact Manifest object loaded.
# ---------------------------------------------------------------------------


def test_context_carries_the_exact_manifest_loaded(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out")
    assert context.manifest is real_manifest


# ---------------------------------------------------------------------------
# 13/14. output_dir relative resolution and an externally-valid output_dir.
# ---------------------------------------------------------------------------


def test_relative_output_dir_resolved_against_repo_root(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    repo_root = tmp_path / "repo"
    context = prepare_normative_launch(repo_root, output_dir=Path("campaign_out"))
    assert context.output_dir == (repo_root.resolve() / "campaign_out")


def test_external_output_dir_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    repo_root = tmp_path / "repo"
    output_dir = tmp_path / "campaign_out"
    context = prepare_normative_launch(repo_root, output_dir=output_dir)
    assert context.output_dir == output_dir.resolve()


# ---------------------------------------------------------------------------
# 15-21. Forbidden output_dir targets.
# ---------------------------------------------------------------------------


def _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path: Path, output_dir: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    prepare_normative_launch(tmp_path / "repo", output_dir=output_dir)


def test_output_dir_equal_to_repo_root_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root)


def test_output_dir_results_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root / "results")


@pytest.mark.parametrize("normative_path", ["src", "docs", "schemas", "experiments", "scripts"])
def test_output_dir_under_normative_path_is_rejected(monkeypatch, real_manifest, tmp_path: Path, normative_path: str) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root / normative_path / "nested")


# ---------------------------------------------------------------------------
# 22/23. Second HEAD verification called; HEAD change detected.
# ---------------------------------------------------------------------------


def test_second_head_verification_is_performed(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert len(recorder.head_calls) == 2


def test_head_change_between_prepare_and_launch_is_detected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_B))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    with pytest.raises(NormativeLaunchError, match="HEAD changed"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.run_campaign_calls == []


# ---------------------------------------------------------------------------
# 24/25. Second branch verification called; branch change with identical
# SHA detected.
# ---------------------------------------------------------------------------


def test_second_branch_verification_is_performed(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert len(recorder.branch_calls) == 2


def test_branch_change_with_identical_sha_is_detected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(
        monkeypatch,
        recorder,
        real_manifest,
        head_values=(SHA_A, SHA_A),  # identical -- HEAD alone would not catch this
        branch_values=(real_manifest.branch, "checked-out-elsewhere"),
    )
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    with pytest.raises(NormativeLaunchError, match="branch changed"):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.run_campaign_calls == []


# ---------------------------------------------------------------------------
# 26/27. Second cleanliness verification called; repo becoming dirty
# between prepare and launch is detected.
# ---------------------------------------------------------------------------


def test_second_cleanliness_verification_is_performed(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert len(recorder.cleanliness_calls) == 2


def test_repository_becoming_dirty_between_prepare_and_launch_is_detected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(
        monkeypatch,
        recorder,
        real_manifest,
        head_values=(SHA_A, SHA_A),
        cleanliness_values=((True, ()), (False, ("scripts/new.py",))),
    )
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert excinfo.value.dirty_paths == ("scripts/new.py",)
    assert recorder.run_campaign_calls == []


# ---------------------------------------------------------------------------
# 28/29. repository_commit == second head; the same Manifest object is
# forwarded to run_campaign.
# ---------------------------------------------------------------------------


def test_repository_commit_passed_to_run_campaign_is_the_final_verified_head(
    monkeypatch, real_manifest, tmp_path: Path
) -> None:
    """A successful launch requires the first and second HEAD to be
    equal (see test_head_change_..._is_detected above for the case where
    they differ) -- so this only confirms the value forwarded matches
    that shared value, together with launch.py's own source (which
    explicitly binds run_campaign's repository_commit to the local
    `second_head_sha`, never to `context.repository_commit`)."""
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.run_campaign_calls[0]["repository_commit"] == SHA_A


def test_same_manifest_object_forwarded_to_run_campaign(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = _Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A))
    _patch_run_campaign(monkeypatch, recorder, _empty_success_report())
    launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out")
    assert recorder.run_campaign_calls[0]["manifest"] is real_manifest
    # load_manifest is called exactly once for the whole launch -- never
    # reloaded for the second verification.
    assert len(recorder.load_manifest_calls) == 1


# ---------------------------------------------------------------------------
# 30. No direct plan reconstruction in launch.py.
# ---------------------------------------------------------------------------


def test_launch_module_never_imports_build_campaign_plan() -> None:
    source = inspect.getsource(launch_module)
    import_lines = "\n".join(
        line for line in source.splitlines() if line.startswith("import ") or line.startswith("from ")
    )
    assert "build_campaign_plan" not in import_lines


def test_launch_module_imports_no_inter_s_or_diagonalization_symbol() -> None:
    source = inspect.getsource(launch_module)
    import_lines = "\n".join(
        line for line in source.splitlines() if line.startswith("import ") or line.startswith("from ")
    )
    for token in _FORBIDDEN_IMPORT_TOKENS:
        assert token not in import_lines


# ---------------------------------------------------------------------------
# 31. No Git mutation command, anywhere in a real prepare_normative_launch
# call against a real (throwaway) repository.
# ---------------------------------------------------------------------------


def _init_repo(repo_root: Path, branch: str) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "placeholder.py").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_root, check=True)


def test_launch_module_never_calls_a_git_mutation_command(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    branch = real_manifest.branch
    _init_repo(repo_root, branch)

    recorder = _Recorder()
    _patch_load_manifest(monkeypatch, recorder, real_manifest)

    calls: list[list[str]] = []
    real_run = subprocess.run

    def spying_run(command, *args, **kwargs):
        calls.append(list(command))
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spying_run)

    context = prepare_normative_launch(repo_root, output_dir=tmp_path / "campaign_out")
    assert context.repository_commit is not None

    mutating_prefixes = (
        ["git", "reset"],
        ["git", "clean"],
        ["git", "stash"],
        ["git", "checkout"],
        ["git", "commit"],
        ["git", "add"],
        ["git", "push"],
        ["git", "merge"],
        ["git", "rebase"],
    )
    for command in calls:
        assert command[0] == "git"
        assert command[:2] not in mutating_prefixes


# ---------------------------------------------------------------------------
# CLI (32-37).
# ---------------------------------------------------------------------------


def test_cli_parser_has_no_repository_commit_manifest_path_force_or_cleanliness_override() -> None:
    parser = cli_module._build_parser()
    dests = {action.dest for action in parser._actions}
    assert dests == {"help", "output_dir", "repo_root"}


def test_cli_output_dir_is_required(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main(["--repo-root", str(tmp_path)])
    assert excinfo.value.code == 2


def test_cli_global_success_true_yields_exit_code_0(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_module, "launch_normative_campaign", lambda repo_root, *, output_dir: _empty_success_report())
    exit_code = cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path)])
    assert exit_code == 0


def test_cli_global_success_false_yields_exit_code_1(monkeypatch, tmp_path: Path) -> None:
    # Build a genuinely failing report via the real, invariant-checked
    # dataclass rather than bypassing its validation.
    from scripts.level1b_campaign.campaign import CaseOrchestrationOutcome

    failed_report = CampaignExecutionReport(
        case_outcomes=(CaseOrchestrationOutcome(case_id="x", status="failed", errors=("boom",)),),
        total_required=1,
        executed_success_count=0,
        reused_success_count=0,
        resource_guardrail_exceeded_count=0,
        failed_count=1,
        global_success=False,
    )
    monkeypatch.setattr(cli_module, "launch_normative_campaign", lambda repo_root, *, output_dir: failed_report)
    exit_code = cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path)])
    assert exit_code == 1


def test_cli_normative_launch_error_yields_exit_code_2(monkeypatch, tmp_path: Path) -> None:
    def raise_error(repo_root, *, output_dir):
        raise NormativeLaunchError("boom")

    monkeypatch.setattr(cli_module, "launch_normative_campaign", raise_error)
    exit_code = cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path)])
    assert exit_code == 2


def test_cli_default_repo_root_is_derived_from_script_location() -> None:
    assert cli_module._DEFAULT_REPO_ROOT == Path(cli_module.__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 37. No real scientific campaign anywhere in this suite -- run_campaign
# and load_manifest are always monkeypatched above; this test only
# double-checks that campaign_module.run_single_case (the actual
# diagonalizing entry point) is never imported into launch.py or the CLI.
# ---------------------------------------------------------------------------


def test_no_diagonalizing_entry_point_imported_by_launch_or_cli() -> None:
    for module in (launch_module, cli_module, campaign_module):
        source = inspect.getsource(module)
        assert "build_level0_report_with_eigenvectors" not in source


def test_normative_launch_context_invariants() -> None:
    manifest = manifest_module.load_manifest()
    with pytest.raises(ValueError):
        NormativeLaunchContext(
            repository_commit="not-a-sha",
            branch=manifest.branch,
            manifest=manifest,
            output_dir=Path("/tmp/out").resolve(),
        )
    with pytest.raises(ValueError):
        NormativeLaunchContext(
            repository_commit=SHA_A,
            branch="HEAD",
            manifest=manifest,
            output_dir=Path("/tmp/out").resolve(),
        )
    with pytest.raises(ValueError):
        NormativeLaunchContext(
            repository_commit=SHA_A,
            branch="not-the-manifest-branch",
            manifest=manifest,
            output_dir=Path("/tmp/out").resolve(),
        )
    with pytest.raises(ValueError):
        NormativeLaunchContext(
            repository_commit=SHA_A,
            branch=manifest.branch,
            manifest=manifest,
            output_dir=Path("relative/out"),
        )
