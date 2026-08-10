"""Normative launch entry point for the Level1C campaign. Lot 1C-8j.

prepare_normative_launch/launch_normative_campaign verify every
normative precondition of a real campaign launch -- repository
cleanliness, exact HEAD/branch identity, the single normative Level1C
manifest, output_dir/historical_output_dir safety -- and then
orchestrate the four already-accepted phase entry points in strict
order (P -> BASELINE_NON_REGRESSION_GATE -> T -> R), never PHASE_G. See
the package docstring for the full governance/provenance contract.

Engineering pattern only, never imported from: scripts/level1b_campaign/
launch.py (Level1B, a different manifest/campaign type, never reused
directly here). check_repository_cleanliness/NORMATIVE_REPOSITORY_PATHS
ARE reused verbatim by direct import (audited in 1C-8i as fully generic,
carrying no Level1B-specific content whatsoever) -- everything else in
this module is a fresh, Level1C-scoped implementation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from experiments.level1c.manifest import Level1CManifest, load_manifest
from scripts.level1b_campaign.campaign import NORMATIVE_REPOSITORY_PATHS, check_repository_cleanliness
from scripts.level1c_baseline_gate.gate import (
    FAIL,
    PASS,
    BaselineNonRegressionArtifact,
    run_baseline_nonregression_gate,
    write_gate_artifact,
)
from scripts.level1c_campaign.campaign import Level1CCampaignExecutionReport, run_level1c_campaign
from scripts.level1c_response.response import ResponseRecord, run_phase_r, write_response_records
from scripts.level1c_tracking.tracking import TrackingRecord, run_inter_j0_tracking, write_tracking_records

_HEAD_SHA_LENGTH = 40
_HEAD_SHA_DIGITS = frozenset("0123456789abcdef")

_FORBIDDEN_OUTPUT_DIR_NAME = "results"
"""Never the bare shared `results/` root itself (an exact-equality
check, never a prefix check -- a scoped subdirectory such as
results/level1c/campaign/ remains explicitly allowed): results/ is the
established, .gitignore'd local-artifact root already shared by Level0
(results/level0-*-v1/runs/) and Level1C's own calibration/preflight
artifacts (results/level1c/{calibration,preflight}/) -- writing an
entire campaign's runs/ tree directly into that shared root would risk
collision/clutter across unrelated concerns. This is a Level1C-specific
engineering justification (separation of artifact spaces), never a
"legacy" designation carried over from Level1B."""

STOP_BEFORE_GATE = "STOP_BEFORE_GATE"
STOP_NORMATIVE_PIPELINE_BEFORE_T = "STOP_NORMATIVE_PIPELINE_BEFORE_T"
COMPLETED = "COMPLETED"
PIPELINE_STATUSES = (STOP_BEFORE_GATE, STOP_NORMATIVE_PIPELINE_BEFORE_T, COMPLETED)


class NormativeLaunchError(RuntimeError):
    """Any normative-launch precondition failure, or a Git-state drift
    detected at the pre-PHASE_P or post-PHASE_P re-verification --
    always raised before the corresponding phase call, never masked as
    a phase-internal failure. `dirty_paths` is populated only for a
    repository-cleanliness failure; empty otherwise."""

    def __init__(self, message: str, *, dirty_paths: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.dirty_paths = dirty_paths


@dataclass(frozen=True, slots=True)
class Level1CNormativeLaunchContext:
    """Everything a validated normative launch needs to actually run the
    P -> gate -> T -> R chain -- built exactly once by
    prepare_normative_launch and never reconstructed afterward.
    `manifest` is the same Level1CManifest object threaded through every
    phase call: campaign_id/fingerprint are always read from
    `manifest.campaign_id`/`manifest.fingerprint`, never duplicated onto
    this dataclass."""

    repository_commit: str
    branch: str
    manifest: Level1CManifest
    output_dir: Path
    historical_output_dir: Path

    def __post_init__(self) -> None:
        if len(self.repository_commit) != _HEAD_SHA_LENGTH or not set(self.repository_commit) <= _HEAD_SHA_DIGITS:
            raise ValueError(
                f"repository_commit must be exactly {_HEAD_SHA_LENGTH} lowercase hex characters, "
                f"got {self.repository_commit!r}"
            )
        if not self.branch or self.branch == "HEAD":
            raise ValueError(f"branch must be non-empty and not the literal 'HEAD' (detached), got {self.branch!r}")
        if not isinstance(self.manifest, Level1CManifest):
            raise ValueError(f"manifest must be a Level1CManifest, got {type(self.manifest)}")
        if self.branch != self.manifest.branch:
            raise ValueError(f"branch ({self.branch!r}) does not match manifest.branch ({self.manifest.branch!r})")
        if not self.output_dir.is_absolute() or self.output_dir != self.output_dir.resolve():
            raise ValueError(f"output_dir must already be an absolute, resolved path, got {self.output_dir!r}")
        if not self.historical_output_dir.is_absolute() or self.historical_output_dir != self.historical_output_dir.resolve():
            raise ValueError(
                f"historical_output_dir must already be an absolute, resolved path, got {self.historical_output_dir!r}"
            )


@dataclass(frozen=True, slots=True)
class Level1CNormativeLaunchReport:
    """The full, in-memory, purely TECHNICAL result of one
    launch_normative_campaign invocation. Never persisted to disk as a
    campaign-wide artifact, never computes or claims
    NORMATIVE_CAMPAIGN_VALID, never a physical verdict. `pipeline_status`
    is a strictly closed taxonomy whose three values enforce, in
    __post_init__, exactly which of gate_artifact/tracking_records/
    response_records may be present -- an impossible combination (e.g.
    STOP_BEFORE_GATE with a gate_artifact present) can never be
    constructed."""

    phase_p_report: Level1CCampaignExecutionReport
    gate_artifact: BaselineNonRegressionArtifact | None
    tracking_records: tuple[TrackingRecord, ...] | None
    response_records: tuple[ResponseRecord, ...] | None
    pipeline_status: str

    def __post_init__(self) -> None:
        if self.pipeline_status not in PIPELINE_STATUSES:
            raise ValueError(f"pipeline_status must be one of {PIPELINE_STATUSES}, got {self.pipeline_status!r}")

        if self.pipeline_status == STOP_BEFORE_GATE:
            if self.gate_artifact is not None or self.tracking_records is not None or self.response_records is not None:
                raise ValueError("gate_artifact/tracking_records/response_records must all be None when pipeline_status == STOP_BEFORE_GATE")
        elif self.pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T:
            if self.gate_artifact is None:
                raise ValueError("gate_artifact must be set when pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T")
            if self.gate_artifact.gate_status != FAIL:
                raise ValueError(
                    f"gate_artifact.gate_status must be {FAIL!r} when pipeline_status == "
                    f"STOP_NORMATIVE_PIPELINE_BEFORE_T, got {self.gate_artifact.gate_status!r}"
                )
            if self.tracking_records is not None or self.response_records is not None:
                raise ValueError("tracking_records/response_records must both be None when pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T")
        else:  # COMPLETED
            if not self.phase_p_report.global_success:
                raise ValueError("phase_p_report.global_success must be True when pipeline_status == COMPLETED")
            if self.gate_artifact is None or self.gate_artifact.gate_status != PASS:
                raise ValueError(f"gate_artifact must be set with gate_status == {PASS!r} when pipeline_status == COMPLETED")
            if self.tracking_records is None or self.response_records is None:
                raise ValueError("tracking_records and response_records must both be set when pipeline_status == COMPLETED")


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
    `repo_root` -- never `git rev-parse --short HEAD`."""
    try:
        sha = _run_git(repo_root, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, OSError) as exc:
        raise NormativeLaunchError(f"could not resolve HEAD for {repo_root}: {exc}") from exc
    if len(sha) != _HEAD_SHA_LENGTH or not set(sha) <= _HEAD_SHA_DIGITS:
        raise NormativeLaunchError(f"git rev-parse HEAD returned an unexpected value: {sha!r}")
    return sha


def _current_branch(repo_root: Path) -> str:
    """Via `git rev-parse --abbrev-ref HEAD`. In a detached HEAD state
    this returns the literal string "HEAD" -- never special-cased: it is
    simply never equal to any real manifest.branch value."""
    try:
        return _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    except (subprocess.CalledProcessError, OSError) as exc:
        raise NormativeLaunchError(f"could not resolve the current branch for {repo_root}: {exc}") from exc


def _resolve_path(repo_root: Path, path: Path) -> Path:
    """Interprets a relative path relative to `repo_root`, never an
    implicit cwd, then resolves to an absolute, symlink-free path."""
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _load_normative_level1c_manifest() -> Level1CManifest:
    """load_manifest() itself can raise -- normalized here into
    NormativeLaunchError, with the original exception preserved as
    __cause__, exactly like the Git helpers above do for Git failures.
    No path argument is ever accepted: no other manifest file can ever
    be selected."""
    try:
        return load_manifest()
    except Exception as exc:  # noqa: BLE001 -- any manifest-loading failure is a precondition failure
        raise NormativeLaunchError(f"could not load the normative Level1C manifest: {exc}") from exc


def _check_repository_cleanliness_or_fail(repo_root: Path) -> tuple[bool, tuple[str, ...]]:
    try:
        return check_repository_cleanliness(repo_root)
    except Exception as exc:  # noqa: BLE001 -- any cleanliness-check failure is a precondition failure
        raise NormativeLaunchError(f"could not determine repository cleanliness for {repo_root}: {exc}") from exc


def _validate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    resolved_repo_root = repo_root.resolve()
    resolved_output_dir = _resolve_path(repo_root, output_dir)

    if resolved_output_dir == resolved_repo_root:
        raise NormativeLaunchError(f"output_dir must not be the repository root itself: {resolved_output_dir}")

    if resolved_output_dir == resolved_repo_root / _FORBIDDEN_OUTPUT_DIR_NAME:
        raise NormativeLaunchError(
            f"output_dir must not be the shared {_FORBIDDEN_OUTPUT_DIR_NAME!r} root itself (a scoped "
            f"subdirectory such as {_FORBIDDEN_OUTPUT_DIR_NAME}/level1c/campaign/ is fine): {resolved_output_dir}"
        )

    for normative_path in NORMATIVE_REPOSITORY_PATHS:
        normative_dir = (resolved_repo_root / normative_path).resolve()
        if resolved_output_dir == normative_dir or resolved_output_dir.is_relative_to(normative_dir):
            raise NormativeLaunchError(
                f"output_dir must not be under the normative path {normative_path!r}: {resolved_output_dir}"
            )

    return resolved_output_dir


def _validate_historical_output_dir(repo_root: Path, historical_output_dir: Path) -> Path:
    """historical_output_dir is an OPERATIONAL path to the already-
    produced Level1B historical corpus -- never a scientific parameter
    (operational location != normative identity, already documented in
    identifiability-preregistration.md). The only precondition checked
    here is that it exists as a directory: run_baseline_nonregression_
    gate itself already handles a genuinely unusable/corrupt historical
    corpus gracefully (a diagnostic FAIL case_comparison, never a crash)
    -- this check exists only to catch an obvious operator mistake (a
    missing/mistyped path) before ever running PHASE_P."""
    resolved = _resolve_path(repo_root, historical_output_dir)
    if not resolved.is_dir():
        raise NormativeLaunchError(f"historical_output_dir does not exist or is not a directory: {resolved}")
    return resolved


def prepare_normative_launch(
    repo_root: Path, *, output_dir: Path, historical_output_dir: Path
) -> Level1CNormativeLaunchContext:
    """Verify every normative precondition once and return the resulting
    Level1CNormativeLaunchContext -- never calls run_level1c_campaign or
    any other phase itself. Order: resolve HEAD, resolve the current
    branch, load the single normative Level1C manifest (load_manifest(),
    no path argument), require branch == manifest.branch, require the
    repository to be clean under NORMATIVE_REPOSITORY_PATHS (reused
    as-is), validate output_dir, validate historical_output_dir. Any
    failure raises NormativeLaunchError."""
    resolved_repo_root = repo_root.resolve()

    head_sha = _resolve_head_sha(resolved_repo_root)
    branch = _current_branch(resolved_repo_root)
    manifest = _load_normative_level1c_manifest()

    if branch != manifest.branch:
        raise NormativeLaunchError(
            f"current branch ({branch!r}) does not match the manifest's own branch ({manifest.branch!r})"
        )

    is_clean, dirty_paths = _check_repository_cleanliness_or_fail(resolved_repo_root)
    if not is_clean:
        raise NormativeLaunchError(
            f"repository is not clean under the normative paths: {list(dirty_paths)}", dirty_paths=dirty_paths
        )

    resolved_output_dir = _validate_output_dir(resolved_repo_root, output_dir)
    resolved_historical_output_dir = _validate_historical_output_dir(resolved_repo_root, historical_output_dir)

    return Level1CNormativeLaunchContext(
        repository_commit=head_sha,
        branch=branch,
        manifest=manifest,
        output_dir=resolved_output_dir,
        historical_output_dir=resolved_historical_output_dir,
    )


def _reverify_git_state_or_fail(repo_root: Path, context: Level1CNormativeLaunchContext, *, when: str) -> None:
    """Re-checks HEAD/branch/cleanliness against `context`'s own already-
    validated values -- never re-adopts a new HEAD/branch, only asserts
    they are unchanged. `when` is purely for the error message (e.g.
    "before PHASE_P", "after PHASE_P"). Raises NormativeLaunchError on
    any drift -- the caller must never continue with a different
    provenance than the one validated by prepare_normative_launch."""
    resolved_repo_root = repo_root.resolve()

    current_head_sha = _resolve_head_sha(resolved_repo_root)
    if current_head_sha != context.repository_commit:
        raise NormativeLaunchError(
            f"HEAD changed {when}: {context.repository_commit!r} -> {current_head_sha!r}"
        )

    current_branch = _current_branch(resolved_repo_root)
    if current_branch != context.branch:
        raise NormativeLaunchError(f"branch changed {when}: {context.branch!r} -> {current_branch!r}")

    is_clean, dirty_paths = _check_repository_cleanliness_or_fail(resolved_repo_root)
    if not is_clean:
        raise NormativeLaunchError(f"repository became unclean {when}: {list(dirty_paths)}", dirty_paths=dirty_paths)


def launch_normative_campaign(
    repo_root: Path, *, output_dir: Path, historical_output_dir: Path
) -> Level1CNormativeLaunchReport:
    """prepare_normative_launch, then orchestrate P -> BASELINE_NON_
    REGRESSION_GATE -> T -> R in strict order, never PHASE_G.

    Git state is re-verified (never re-adopted) twice beyond the initial
    prepare_normative_launch pass: immediately before PHASE_P (the only
    long-running phase -- diagonalization) and immediately after PHASE_P
    completes, before the baseline gate. repository_commit passed to
    every phase call is always context.repository_commit, the ONE value
    resolved at prepare_normative_launch time -- never replaced by a
    later HEAD read, even though later reads are used to detect drift.
    A drift at either checkpoint raises NormativeLaunchError and aborts
    the whole launch attempt; PHASE_P's own already-produced case
    artifacts (if any) remain exactly as persisted (immutable, resumable
    by a future launch attempt), never discarded.

    P_GLOBAL_SUCCESS == False -> returns immediately with
    pipeline_status=STOP_BEFORE_GATE; the baseline gate, T, and R are
    never called. The gate artifact is always persisted (write_gate_
    artifact) BEFORE its gate_status is ever inspected -- a write
    failure propagates (never masked as if the gate had reached a
    verdict). gate_status == FAIL -> STOP_NORMATIVE_PIPELINE_BEFORE_T,
    T and R never called (no diagnostic downstream execution -- that
    belongs to a separate, explicit, non-normative tool, never this
    launcher). gate_status == PASS -> T is run and its full 40-record
    tracking.jsonl is written; only after that write succeeds is R run
    and its response.jsonl written. T_R_CACHE_REUSE_IMPLEMENTED = NO:
    tracking.jsonl/response.jsonl are always fully recomputed and
    atomically rewritten, never reused from a prior run.
    """
    context = prepare_normative_launch(repo_root, output_dir=output_dir, historical_output_dir=historical_output_dir)

    _reverify_git_state_or_fail(repo_root, context, when="before PHASE_P")

    phase_p_report = run_level1c_campaign(
        context.manifest, output_dir=context.output_dir, repository_commit=context.repository_commit
    )

    if not phase_p_report.global_success:
        return Level1CNormativeLaunchReport(
            phase_p_report=phase_p_report,
            gate_artifact=None,
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_BEFORE_GATE,
        )

    _reverify_git_state_or_fail(repo_root, context, when="after PHASE_P")

    gate_artifact = run_baseline_nonregression_gate(
        context.manifest,
        context.output_dir,
        context.historical_output_dir,
        repository_commit=context.repository_commit,
    )
    write_gate_artifact(context.output_dir, gate_artifact)

    if gate_artifact.gate_status != PASS:
        return Level1CNormativeLaunchReport(
            phase_p_report=phase_p_report,
            gate_artifact=gate_artifact,
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )

    tracking_records = run_inter_j0_tracking(
        context.manifest, context.output_dir, repository_commit=context.repository_commit
    )
    write_tracking_records(context.output_dir, tracking_records)

    response_records = run_phase_r(context.manifest, context.output_dir, repository_commit=context.repository_commit)
    write_response_records(context.output_dir, response_records)

    return Level1CNormativeLaunchReport(
        phase_p_report=phase_p_report,
        gate_artifact=gate_artifact,
        tracking_records=tracking_records,
        response_records=response_records,
        pipeline_status=COMPLETED,
    )
