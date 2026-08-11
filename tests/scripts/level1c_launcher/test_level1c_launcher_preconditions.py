from __future__ import annotations

import dataclasses
import inspect
import subprocess
from pathlib import Path

import pytest
from level1c_launcher_helpers import (
    Recorder,
    empty_success_phase_p_report,
    init_repo,
    patch_cleanliness,
    patch_git,
    patch_load_manifest,
    patch_run_level1c_campaign,
)

from scripts.level1c_launcher import launch as launch_module
from scripts.level1c_launcher.launch import (
    Level1CNormativeLaunchContext,
    NormativeLaunchError,
    launch_normative_campaign,
    prepare_normative_launch,
)

SHA_A = "a" * 40
SHA_B = "b" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "run_level1c_case",
    "build_level1c_campaign_plan",
    "compare_structural",
    "extract_complete_groups",
    "build_class_pool",
    "build_response_record",
)


def _historical_dir(tmp_path: Path) -> Path:
    historical = tmp_path / "historical"
    historical.mkdir(parents=True, exist_ok=True)
    return historical


def _setup(
    monkeypatch,
    recorder: Recorder,
    real_manifest,
    *,
    head_values=(SHA_A,),
    branch_values=None,
    cleanliness_values=((True, ()),),
    manifest_obj=None,
) -> None:
    if branch_values is None:
        branch_values = (real_manifest.branch,) * len(head_values)
    patch_git(monkeypatch, recorder, head_values=head_values, branch_values=branch_values)
    patch_cleanliness(monkeypatch, recorder, cleanliness_values)
    patch_load_manifest(monkeypatch, recorder, manifest_obj if manifest_obj is not None else real_manifest)


# ---------------------------------------------------------------------------
# HEAD derived automatically; no repository_commit parameter anywhere.
# ---------------------------------------------------------------------------


def test_head_sha_derived_automatically(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert context.repository_commit == SHA_A
    assert len(recorder.head_calls) == 1


def test_prepare_and_launch_signatures_have_no_repository_commit_parameter() -> None:
    for function in (prepare_normative_launch, launch_normative_campaign):
        parameters = inspect.signature(function).parameters
        assert "repository_commit" not in parameters
        assert set(parameters) == {"repo_root", "output_dir", "historical_output_dir"}


# ---------------------------------------------------------------------------
# load_manifest called without a path; no manifest_path exposed.
# ---------------------------------------------------------------------------


def test_load_manifest_called_without_path(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.load_manifest_calls == [((), {})]


def test_no_manifest_path_parameter_anywhere() -> None:
    for function in (prepare_normative_launch, launch_normative_campaign):
        assert "manifest_path" not in inspect.signature(function).parameters
        assert "manifest" not in inspect.signature(function).parameters


# ---------------------------------------------------------------------------
# Branch read from manifest.branch; correct accepted, incorrect and
# detached-HEAD rejected.
# ---------------------------------------------------------------------------


def test_correct_branch_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert context.branch == real_manifest.branch


def test_incorrect_branch_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, branch_values=("some-other-branch",))
    with pytest.raises(NormativeLaunchError, match="branch"):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))


def test_detached_head_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, branch_values=("HEAD",))
    with pytest.raises(NormativeLaunchError):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))


def test_branch_is_compared_against_manifest_branch_field(monkeypatch, real_manifest, tmp_path: Path) -> None:
    other_manifest = dataclasses.replace(real_manifest, branch="a-different-normative-branch")
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, branch_values=("a-different-normative-branch",), manifest_obj=other_manifest)
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert context.branch == "a-different-normative-branch"


# ---------------------------------------------------------------------------
# Dirty repository rejected; dirty_paths propagated.
# ---------------------------------------------------------------------------


def test_dirty_repository_is_rejected_with_dirty_paths(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, cleanliness_values=((False, ("src/dirty.py",)),))
    with pytest.raises(NormativeLaunchError) as excinfo:
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert excinfo.value.dirty_paths == ("src/dirty.py",)


# ---------------------------------------------------------------------------
# run_level1c_campaign never called after a prepare failure.
# ---------------------------------------------------------------------------


def test_run_level1c_campaign_never_called_after_prepare_failure(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, branch_values=("wrong-branch",))
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())
    with pytest.raises(NormativeLaunchError):
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert recorder.run_level1c_campaign_calls == []


# ---------------------------------------------------------------------------
# Precondition-primitive error normalization.
# ---------------------------------------------------------------------------


def test_load_manifest_value_error_is_normalized(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    original = ValueError("manifest does not validate against its schema")

    def raising_load_manifest():
        raise original

    monkeypatch.setattr(launch_module, "load_manifest", raising_load_manifest)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())

    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert excinfo.value.__cause__ is original
    assert recorder.run_level1c_campaign_calls == []


def test_first_cleanliness_check_process_error_is_normalized(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    patch_git(monkeypatch, recorder, head_values=(SHA_A,), branch_values=(real_manifest.branch,))
    patch_load_manifest(monkeypatch, recorder, real_manifest)
    original = subprocess.CalledProcessError(1, ["git", "status", "--porcelain"])

    def raising_cleanliness(repo_root):
        raise original

    monkeypatch.setattr(launch_module, "check_repository_cleanliness", raising_cleanliness)
    patch_run_level1c_campaign(monkeypatch, recorder, empty_success_phase_p_report())

    with pytest.raises(NormativeLaunchError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert excinfo.value.__cause__ is original
    assert excinfo.value.dirty_paths == ()
    assert recorder.run_level1c_campaign_calls == []


def test_run_level1c_campaign_exception_is_not_converted_to_normative_launch_error(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest, head_values=(SHA_A, SHA_A), cleanliness_values=((True, ()), (True, ())))

    def raising(manifest, *, output_dir, repository_commit):
        raise RuntimeError("run_level1c_campaign internal failure")

    monkeypatch.setattr(launch_module, "run_level1c_campaign", raising)

    with pytest.raises(RuntimeError) as excinfo:
        launch_normative_campaign(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert not isinstance(excinfo.value, NormativeLaunchError)


# ---------------------------------------------------------------------------
# Context carries the exact manifest object loaded.
# ---------------------------------------------------------------------------


def test_context_carries_the_exact_manifest_loaded(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=_historical_dir(tmp_path))
    assert context.manifest is real_manifest


# ---------------------------------------------------------------------------
# output_dir relative resolution and an externally-valid output_dir.
# ---------------------------------------------------------------------------


def test_relative_output_dir_resolved_against_repo_root(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    repo_root = tmp_path / "repo"
    context = prepare_normative_launch(repo_root, output_dir=Path("campaign_out"), historical_output_dir=_historical_dir(tmp_path))
    assert context.output_dir == (repo_root.resolve() / "campaign_out")


def test_external_output_dir_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    repo_root = tmp_path / "repo"
    output_dir = tmp_path / "campaign_out"
    context = prepare_normative_launch(repo_root, output_dir=output_dir, historical_output_dir=_historical_dir(tmp_path))
    assert context.output_dir == output_dir.resolve()


def test_results_level1c_campaign_subdirectory_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    """results/ itself is forbidden (bare root only) -- a scoped
    subdirectory such as results/level1c/campaign/ remains explicitly
    allowed (1C-8i/1C-8j)."""
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    repo_root = tmp_path / "repo"
    output_dir = repo_root / "results" / "level1c" / "campaign"
    context = prepare_normative_launch(repo_root, output_dir=output_dir, historical_output_dir=_historical_dir(tmp_path))
    assert context.output_dir == output_dir.resolve()


# ---------------------------------------------------------------------------
# Forbidden output_dir targets.
# ---------------------------------------------------------------------------


def _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path: Path, output_dir: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    prepare_normative_launch(tmp_path / "repo", output_dir=output_dir, historical_output_dir=_historical_dir(tmp_path))


def test_output_dir_equal_to_repo_root_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root)


def test_output_dir_results_bare_root_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root / "results")


@pytest.mark.parametrize("normative_path", ["src", "docs", "schemas", "experiments", "scripts"])
def test_output_dir_under_normative_path_is_rejected(monkeypatch, real_manifest, tmp_path: Path, normative_path: str) -> None:
    repo_root = tmp_path / "repo"
    with pytest.raises(NormativeLaunchError):
        _prepare_with_output_dir(monkeypatch, real_manifest, tmp_path, repo_root / normative_path / "nested")


# ---------------------------------------------------------------------------
# historical_output_dir validation.
# ---------------------------------------------------------------------------


def test_missing_historical_output_dir_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    with pytest.raises(NormativeLaunchError, match="historical_output_dir"):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=tmp_path / "does-not-exist")


def test_historical_output_dir_that_is_a_file_is_rejected(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    historical_file = tmp_path / "historical_file"
    historical_file.write_text("not a directory")
    with pytest.raises(NormativeLaunchError, match="historical_output_dir"):
        prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=historical_file)


def test_existing_historical_output_dir_is_accepted(monkeypatch, real_manifest, tmp_path: Path) -> None:
    recorder = Recorder()
    _setup(monkeypatch, recorder, real_manifest)
    historical = _historical_dir(tmp_path)
    context = prepare_normative_launch(tmp_path / "repo", output_dir=tmp_path / "out", historical_output_dir=historical)
    assert context.historical_output_dir == historical.resolve()


# ---------------------------------------------------------------------------
# No real Git mutation command, against a real (throwaway) repository.
# ---------------------------------------------------------------------------


def test_launch_module_never_calls_a_git_mutation_command(monkeypatch, real_manifest, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    branch = real_manifest.branch
    init_repo(repo_root, branch)

    recorder = Recorder()
    patch_load_manifest(monkeypatch, recorder, real_manifest)

    calls: list[list[str]] = []
    real_run = subprocess.run

    def spying_run(command, *args, **kwargs):
        calls.append(list(command))
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spying_run)

    context = prepare_normative_launch(repo_root, output_dir=tmp_path / "campaign_out", historical_output_dir=_historical_dir(tmp_path))
    assert context.repository_commit is not None

    mutating_prefixes = (
        ["git", "reset"], ["git", "clean"], ["git", "stash"], ["git", "checkout"],
        ["git", "commit"], ["git", "add"], ["git", "push"], ["git", "merge"], ["git", "rebase"],
    )
    for command in calls:
        assert command[0] == "git"
        assert command[:2] not in mutating_prefixes


# ---------------------------------------------------------------------------
# No scientific/diagonalizing symbol imported by the launcher.
# ---------------------------------------------------------------------------


def test_launch_module_never_imports_build_level1c_campaign_plan() -> None:
    source = inspect.getsource(launch_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    assert "build_level1c_campaign_plan" not in import_lines


def test_launch_module_imports_no_scientific_symbol() -> None:
    source = inspect.getsource(launch_module)
    import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
    for token in _FORBIDDEN_IMPORT_TOKENS:
        assert token not in import_lines


def test_normative_launch_context_invariants() -> None:
    manifest = None
    from experiments.level1c.manifest import load_manifest

    manifest = load_manifest()
    with pytest.raises(ValueError):
        Level1CNormativeLaunchContext(
            repository_commit="not-a-sha", branch=manifest.branch, manifest=manifest,
            output_dir=Path("/tmp/out").resolve(), historical_output_dir=Path("/tmp/hist").resolve(),
        )
    with pytest.raises(ValueError):
        Level1CNormativeLaunchContext(
            repository_commit=SHA_A, branch="HEAD", manifest=manifest,
            output_dir=Path("/tmp/out").resolve(), historical_output_dir=Path("/tmp/hist").resolve(),
        )
    with pytest.raises(ValueError):
        Level1CNormativeLaunchContext(
            repository_commit=SHA_A, branch="not-the-manifest-branch", manifest=manifest,
            output_dir=Path("/tmp/out").resolve(), historical_output_dir=Path("/tmp/hist").resolve(),
        )
    with pytest.raises(ValueError):
        Level1CNormativeLaunchContext(
            repository_commit=SHA_A, branch=manifest.branch, manifest=manifest,
            output_dir=Path("relative/out"), historical_output_dir=Path("/tmp/hist").resolve(),
        )
    with pytest.raises(ValueError):
        Level1CNormativeLaunchContext(
            repository_commit=SHA_A, branch=manifest.branch, manifest=manifest,
            output_dir=Path("/tmp/out").resolve(), historical_output_dir=Path("relative/hist"),
        )
