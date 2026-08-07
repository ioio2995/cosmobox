"""Normative launch entry point for the Level1B campaign. Level1B lot
1B-8e (docs/governance/current-task.md).

prepare_normative_launch/launch_normative_campaign verify every
normative precondition of a real campaign launch -- repository
cleanliness, exact HEAD/branch identity, the single normative manifest
-- and then call run_campaign (lot 1B-8d) unmodified. This module adds
no scientific logic and reconstructs no campaign plan of its own:
run_campaign already builds experiments.level1.planning.
build_campaign_plan(manifest) exactly once, with its own case_id
uniqueness guarantee, and this module never duplicates that.

repository_commit is never a free parameter anywhere in this module's
public API (prepare_normative_launch, launch_normative_campaign, or the
CLI in scripts/run_level1b_campaign.py) -- it is always derived from
`repo_root` itself via `git rev-parse HEAD`, so it cannot be supplied,
overridden, or spoofed by a caller. The same is true of the expected
branch: it is never a hardcoded string in this module, only ever
compared against the loaded manifest's own `branch` field
(experiments.level1.manifest.Manifest.branch).

Any precondition failure raises NormativeLaunchError BEFORE
run_campaign is ever called -- no runs/<case_id>/run.json is ever
written for a precondition failure; it is not a per-case outcome at
all, only individual case executions inside run_campaign produce those.

TOCTOU: a change to the repository between the initial precondition
check and the actual run_campaign call cannot be fully excluded without
a Git-level lock, which this module deliberately does not introduce.
launch_normative_campaign narrows the window instead of claiming to
close it: it re-verifies HEAD, branch, and cleanliness a second time
immediately before calling run_campaign, and aborts (before
run_campaign) if any of the three has changed. The residual window
between that second check and run_campaign's own first internal call is
not eliminated -- see the module docstring above and this function's
own docstring for the honest scope of what is and is not covered.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from experiments.level1.manifest import Manifest, load_manifest

from .campaign import CampaignExecutionReport, NORMATIVE_REPOSITORY_PATHS, check_repository_cleanliness, run_campaign

_HEAD_SHA_LENGTH = 40
_HEAD_SHA_DIGITS = frozenset("0123456789abcdef")

_FORBIDDEN_OUTPUT_DIR_NAME = "results"


class NormativeLaunchError(RuntimeError):
    """Any normative-launch precondition failure -- always raised before
    run_campaign is ever called. dirty_paths is populated only for a
    repository-cleanliness failure; empty for every other precondition
    failure (bad branch, HEAD drift, forbidden output_dir, an underlying
    Git or manifest error, ...)."""

    def __init__(self, message: str, *, dirty_paths: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.dirty_paths = dirty_paths


@dataclass(frozen=True, slots=True)
class NormativeLaunchContext:
    """Everything a validated normative launch needs to actually call
    run_campaign -- built exactly once by prepare_normative_launch and
    never reconstructed afterward. `manifest` is the same Manifest
    object all the way through to run_campaign: campaign_id and
    fingerprint are always read from `manifest.campaign_id`/
    `manifest.fingerprint`, never duplicated onto this dataclass."""

    repository_commit: str
    branch: str
    manifest: Manifest
    output_dir: Path

    def __post_init__(self) -> None:
        if len(self.repository_commit) != _HEAD_SHA_LENGTH or not set(self.repository_commit) <= _HEAD_SHA_DIGITS:
            raise ValueError(
                f"repository_commit must be exactly {_HEAD_SHA_LENGTH} lowercase hex characters, "
                f"got {self.repository_commit!r}"
            )
        if not self.branch or self.branch == "HEAD":
            raise ValueError(f"branch must be non-empty and not the literal 'HEAD' (detached), got {self.branch!r}")
        if not isinstance(self.manifest, Manifest):
            raise ValueError(f"manifest must be a Manifest, got {type(self.manifest)}")
        if self.branch != self.manifest.branch:
            raise ValueError(f"branch ({self.branch!r}) does not match manifest.branch ({self.manifest.branch!r})")
        if not self.output_dir.is_absolute() or self.output_dir != self.output_dir.resolve():
            raise ValueError(f"output_dir must already be an absolute, resolved path, got {self.output_dir!r}")


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _resolve_head_sha(repo_root: Path) -> str:
    """The full, 40-lowercase-hex-character HEAD commit SHA of
    `repo_root` -- never `git rev-parse --short HEAD`. Runs exclusively
    `git rev-parse HEAD`, with check=True: an inaccessible repository or
    an empty repository with no commit raises CalledProcessError, which
    callers let propagate (wrapped in NormativeLaunchError) rather than
    treat as a resolvable value."""
    try:
        sha = _run_git(repo_root, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, OSError) as exc:
        raise NormativeLaunchError(f"could not resolve HEAD for {repo_root}: {exc}") from exc
    if len(sha) != _HEAD_SHA_LENGTH or not set(sha) <= _HEAD_SHA_DIGITS:
        raise NormativeLaunchError(f"git rev-parse HEAD returned an unexpected value: {sha!r}")
    return sha


def _current_branch(repo_root: Path) -> str:
    """The current branch name of `repo_root`, via
    `git rev-parse --abbrev-ref HEAD`. In a detached HEAD state this
    command returns the literal string "HEAD" -- deliberately not
    special-cased here: it is simply never equal to any real
    manifest.branch value, so the branch comparison rejects it
    naturally."""
    try:
        return _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    except (subprocess.CalledProcessError, OSError) as exc:
        raise NormativeLaunchError(f"could not resolve the current branch for {repo_root}: {exc}") from exc


def _resolve_output_dir(repo_root: Path, output_dir: Path) -> Path:
    """Interprets a relative output_dir relative to `repo_root`, never
    relative to an implicit cwd, then resolves both to absolute,
    symlink-free paths for a correct parent/child comparison (a plain
    string prefix check would be fooled by e.g. a missing trailing
    slash or a `..` segment)."""
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    return output_dir.resolve()


def _validate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    resolved_repo_root = repo_root.resolve()
    resolved_output_dir = _resolve_output_dir(repo_root, output_dir)

    if resolved_output_dir == resolved_repo_root:
        raise NormativeLaunchError(f"output_dir must not be the repository root itself: {resolved_output_dir}")

    if resolved_output_dir == resolved_repo_root / _FORBIDDEN_OUTPUT_DIR_NAME:
        raise NormativeLaunchError(
            f"output_dir must not be the legacy {_FORBIDDEN_OUTPUT_DIR_NAME!r} directory: {resolved_output_dir}"
        )

    for normative_path in NORMATIVE_REPOSITORY_PATHS:
        normative_dir = (resolved_repo_root / normative_path).resolve()
        if resolved_output_dir == normative_dir or resolved_output_dir.is_relative_to(normative_dir):
            raise NormativeLaunchError(
                f"output_dir must not be under the normative path {normative_path!r}: {resolved_output_dir}"
            )

    return resolved_output_dir


def prepare_normative_launch(repo_root: Path, *, output_dir: Path) -> NormativeLaunchContext:
    """Verify every normative precondition once and return the resulting
    NormativeLaunchContext -- never calls run_campaign itself. Order:
    resolve HEAD, resolve the current branch, load the single normative
    manifest (load_manifest(), no path argument -- no other manifest
    file can ever be selected), require branch == manifest.branch,
    require the repository to be clean under NORMATIVE_REPOSITORY_PATHS
    (check_repository_cleanliness, reused as-is), then validate
    output_dir. Any failure raises NormativeLaunchError."""
    resolved_repo_root = repo_root.resolve()

    head_sha = _resolve_head_sha(resolved_repo_root)
    branch = _current_branch(resolved_repo_root)
    manifest = load_manifest()

    if branch != manifest.branch:
        raise NormativeLaunchError(
            f"current branch ({branch!r}) does not match the manifest's own branch ({manifest.branch!r})"
        )

    is_clean, dirty_paths = check_repository_cleanliness(resolved_repo_root)
    if not is_clean:
        raise NormativeLaunchError(
            f"repository is not clean under the normative paths: {list(dirty_paths)}", dirty_paths=dirty_paths
        )

    resolved_output_dir = _validate_output_dir(resolved_repo_root, output_dir)

    return NormativeLaunchContext(
        repository_commit=head_sha,
        branch=branch,
        manifest=manifest,
        output_dir=resolved_output_dir,
    )


def launch_normative_campaign(repo_root: Path, *, output_dir: Path) -> CampaignExecutionReport:
    """prepare_normative_launch, then a second, narrower re-verification
    of HEAD/branch/cleanliness immediately before run_campaign -- never
    a second full precondition pass (the manifest and output_dir do not
    carry the same drift risk in this narrow window, and re-loading the
    manifest a second time would risk using a different Manifest object
    than the one already validated). A branch change onto a different
    branch that happens to point at the same commit would leave HEAD and
    cleanliness unchanged, so the branch is re-checked independently,
    not inferred from an unchanged HEAD. repository_commit passed to
    run_campaign is exactly the second, final HEAD value -- not the
    first one from `context` (they are required to be equal for the
    launch to proceed at all, but the second is the one actually in
    effect at the moment run_campaign starts).

    This narrows, but does not close, the TOCTOU window: a change to the
    repository between this second check and run_campaign's own first
    internal action remains possible -- no Git lock is introduced to
    close it. See the module docstring for the full rationale.
    """
    context = prepare_normative_launch(repo_root, output_dir=output_dir)

    second_head_sha = _resolve_head_sha(repo_root.resolve())
    if second_head_sha != context.repository_commit:
        raise NormativeLaunchError(
            f"HEAD changed between prepare and launch: {context.repository_commit!r} -> {second_head_sha!r}"
        )

    second_branch = _current_branch(repo_root.resolve())
    if second_branch != context.branch or second_branch != context.manifest.branch:
        raise NormativeLaunchError(
            f"branch changed between prepare and launch: {context.branch!r} -> {second_branch!r}"
        )

    second_is_clean, second_dirty_paths = check_repository_cleanliness(repo_root.resolve())
    if not second_is_clean:
        raise NormativeLaunchError(
            f"repository became unclean between prepare and launch: {list(second_dirty_paths)}",
            dirty_paths=second_dirty_paths,
        )

    return run_campaign(
        context.manifest,
        output_dir=context.output_dir,
        repository_commit=second_head_sha,
    )
