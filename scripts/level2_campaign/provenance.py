"""Campaign-start Git provenance resolution for Level2 campaigns.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. Mirrors scripts/level1c_preflight/
j0_grid_preflight.py's own resolve_code_commit/require_clean_worktree
(DIRTY_WORKTREE_POLICY = REFUSE_EXECUTION): a non-clean `git status
--porcelain` refuses campaign execution before any case runs.

REPOSITORY_COMMIT_CAPTURE = ONCE_AT_CAMPAIGN_START_AFTER_CLEAN_WORKTREE_
CHECK (docs/governance/current-task.md, L2-E decision): resolve_campaign_
provenance is called exactly once per campaign; the CampaignProvenance it
returns is then threaded unchanged through every case and geometry
comparison -- never re-resolved mid-campaign, so no campaign can ever mix
cases from different commits by construction of the runner's own control
flow.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from experiments.level2.manifest import Level2Manifest

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ProvenanceResolutionFailure(RuntimeError):
    """Raised when the repository's Git state cannot be resolved, or is
    not clean. Carries no diff content or file paths -- a generic,
    sanitized failure only, matching scripts/level1c_preflight/
    j0_grid_preflight.py's own PreflightInternalFailure discipline."""


def resolve_code_commit(repo_root: str | None = None) -> str:
    """The exact `git rev-parse HEAD` of `repo_root` (ambient cwd if
    None), strictly validated as 40 lowercase hex characters -- never a
    short SHA, never a fallback value. Any subprocess failure (missing
    git, no commits, non-zero exit) or an unexpected stdout shape fails
    hard, never a best-effort placeholder."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        )
    except Exception:
        raise ProvenanceResolutionFailure("could not resolve the repository's HEAD commit") from None
    sha = completed.stdout.strip()
    if not _GIT_SHA_PATTERN.fullmatch(sha):
        raise ProvenanceResolutionFailure("git rev-parse HEAD did not return a 40-character hex commit")
    return sha


def resolve_current_branch(repo_root: str | None = None) -> str:
    """The exact `git rev-parse --abbrev-ref HEAD` of `repo_root` (ambient
    cwd if None). Any subprocess failure or a detached HEAD (which
    `git rev-parse --abbrev-ref` reports as the literal string "HEAD")
    fails hard, never a best-effort placeholder -- mirrors
    resolve_code_commit's own discipline."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        )
    except Exception:
        raise ProvenanceResolutionFailure("could not resolve the repository's current branch") from None
    branch = completed.stdout.strip()
    if not branch or branch == "HEAD":
        raise ProvenanceResolutionFailure(
            "git rev-parse --abbrev-ref HEAD did not return a branch name (detached HEAD?)"
        )
    return branch


def _repository_is_clean(repo_root: str | None = None) -> bool:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True
        )
    except Exception:
        raise ProvenanceResolutionFailure("could not determine the repository's worktree status") from None
    return completed.stdout.strip() == ""


def require_clean_worktree(repo_root: str | None = None) -> None:
    """DIRTY_WORKTREE_POLICY = REFUSE_EXECUTION: a non-empty `git status
    --porcelain` refuses campaign execution before any case runs."""
    if not _repository_is_clean(repo_root):
        raise ProvenanceResolutionFailure("repository worktree is not clean; refusing campaign execution")


@dataclass(frozen=True, slots=True)
class CampaignProvenance:
    """The provenance quintuple every persisted Level2 artifact must
    carry. Resolved once per campaign (resolve_campaign_provenance),
    never per case."""

    repository_commit: str
    branch: str
    manifest_fingerprint: str
    campaign_id: str
    frozen_preregistration_commit: str

    def __post_init__(self) -> None:
        if not _GIT_SHA_PATTERN.fullmatch(self.repository_commit):
            raise ValueError(
                f"repository_commit must be a 40-character lowercase hex string, got {self.repository_commit!r}"
            )
        if not self.branch:
            raise ValueError("branch must be non-empty")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not _GIT_SHA_PATTERN.fullmatch(self.frozen_preregistration_commit):
            raise ValueError(
                f"frozen_preregistration_commit must be a 40-character lowercase hex string, "
                f"got {self.frozen_preregistration_commit!r}"
            )


def resolve_campaign_provenance(manifest: Level2Manifest, *, repo_root: str | None = None) -> CampaignProvenance:
    """require_clean_worktree, then resolve_code_commit, exactly once.
    branch/campaign_id/frozen_preregistration_commit/manifest_fingerprint
    come from `manifest` itself -- never re-derived. Does not verify
    that manifest.branch matches the repository's actual current branch
    -- callers requiring that check call verify_branch_matches_manifest
    separately (kept as a distinct step so this already-reviewed
    function's own behavior is unchanged by that addition)."""
    require_clean_worktree(repo_root)
    repository_commit = resolve_code_commit(repo_root)
    return CampaignProvenance(
        repository_commit=repository_commit,
        branch=manifest.branch,
        manifest_fingerprint=manifest.fingerprint,
        campaign_id=manifest.campaign_id,
        frozen_preregistration_commit=manifest.frozen_preregistration_commit,
    )


def verify_branch_matches_manifest(provenance: CampaignProvenance, *, repo_root: str | None = None) -> None:
    """Refuses a campaign whose manifest-declared branch
    (provenance.branch, threaded from Level2Manifest.branch) does not
    match the repository's actual current branch at campaign start. A
    separate step from resolve_campaign_provenance itself (see that
    function's own docstring) -- callers that need this check call it
    explicitly, right after resolving provenance."""
    actual_branch = resolve_current_branch(repo_root)
    if actual_branch != provenance.branch:
        raise ProvenanceResolutionFailure(
            f"manifest branch {provenance.branch!r} does not match the repository's actual "
            f"current branch {actual_branch!r}"
        )
