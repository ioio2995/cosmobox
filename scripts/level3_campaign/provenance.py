"""Campaign-start Git provenance resolution for Level3 S4 campaigns.

Deliberately duplicated from scripts/level2_campaign/provenance.py's own
generic git primitives (resolve_code_commit, resolve_current_branch,
require_clean_worktree, DIRTY_WORKTREE_POLICY=REFUSE_EXECUTION) rather
than imported, per the L3-I mandate's explicit isolation decision:
scripts/level3_campaign/ never depends on scripts/level2_campaign/ at
runtime, even though the two modules are structurally identical.

REPOSITORY_COMMIT_CAPTURE = ONCE_AT_CAMPAIGN_START_AFTER_CLEAN_WORKTREE_
CHECK, same as Level2: resolve_campaign_provenance is called exactly once
per campaign; the CampaignProvenance it returns is then threaded
unchanged through every case and the campaign-summary.

CampaignProvenance additionally carries the frozen Level2 reference
identity (level2_reference_*), pinned to the exact constants
cosmobox.level3.frozen_reference itself validates against -- so a
campaign's own provenance record and the frozen-reference loader can
never silently diverge on which Level2 campaign is the S=2/S=3 source.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from cosmobox.level3.frozen_reference import (
    LEVEL2_REFERENCE_CAMPAIGN_ID,
    LEVEL2_REFERENCE_FROZEN_PREREGISTRATION_COMMIT,
    LEVEL2_REFERENCE_MANIFEST_FINGERPRINT,
    LEVEL2_REFERENCE_REPOSITORY_COMMIT,
)
from experiments.level3.manifest import Level3Manifest

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

REPOSITORY_IDENTITY = "ioio2995/cosmobox"
"""The frozen repository identity every persisted Level3 artifact must
carry -- a fixed constant, never a caller-supplied or git-remote-derived
value."""


class ProvenanceResolutionFailure(RuntimeError):
    """Raised when the repository's Git state cannot be resolved, or is
    not clean. Carries no diff content or file paths -- a generic,
    sanitized failure only."""


def resolve_code_commit(repo_root: str | None = None) -> str:
    """The exact `git rev-parse HEAD` of `repo_root` (ambient cwd if
    None), strictly validated as 40 lowercase hex characters -- never a
    short SHA, never a fallback value."""
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
    cwd if None). A detached HEAD (reported as the literal string "HEAD")
    fails hard, never a best-effort placeholder."""
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
    """The provenance record every persisted Level3 S4 artifact must
    carry, resolved once per campaign, plus the pinned identity of the
    frozen Level2 reference campaign that supplied the S=2/S=3 data."""

    repository: str
    repository_commit: str
    branch: str
    manifest_fingerprint: str
    campaign_id: str
    frozen_preregistration_commit: str
    level2_reference_campaign_id: str
    level2_reference_manifest_fingerprint: str
    level2_reference_repository_commit: str
    level2_reference_frozen_preregistration_commit: str

    def __post_init__(self) -> None:
        if self.repository != REPOSITORY_IDENTITY:
            raise ValueError(f"repository must be {REPOSITORY_IDENTITY!r}, got {self.repository!r}")
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
        if self.level2_reference_campaign_id != LEVEL2_REFERENCE_CAMPAIGN_ID:
            raise ValueError(
                f"level2_reference_campaign_id must be {LEVEL2_REFERENCE_CAMPAIGN_ID!r}, "
                f"got {self.level2_reference_campaign_id!r}"
            )
        if self.level2_reference_manifest_fingerprint != LEVEL2_REFERENCE_MANIFEST_FINGERPRINT:
            raise ValueError(
                f"level2_reference_manifest_fingerprint must be {LEVEL2_REFERENCE_MANIFEST_FINGERPRINT!r}, "
                f"got {self.level2_reference_manifest_fingerprint!r}"
            )
        if self.level2_reference_repository_commit != LEVEL2_REFERENCE_REPOSITORY_COMMIT:
            raise ValueError(
                f"level2_reference_repository_commit must be {LEVEL2_REFERENCE_REPOSITORY_COMMIT!r}, "
                f"got {self.level2_reference_repository_commit!r}"
            )
        if self.level2_reference_frozen_preregistration_commit != LEVEL2_REFERENCE_FROZEN_PREREGISTRATION_COMMIT:
            raise ValueError(
                "level2_reference_frozen_preregistration_commit must be "
                f"{LEVEL2_REFERENCE_FROZEN_PREREGISTRATION_COMMIT!r}, "
                f"got {self.level2_reference_frozen_preregistration_commit!r}"
            )


def resolve_campaign_provenance(manifest: Level3Manifest, *, repo_root: str | None = None) -> CampaignProvenance:
    """require_clean_worktree, then resolve_code_commit, exactly once.
    branch/campaign_id/frozen_preregistration_commit/manifest_fingerprint/
    level2_reference_* come from `manifest` itself -- never re-derived.
    repository is always exactly REPOSITORY_IDENTITY. Does not verify
    that manifest.branch matches the repository's actual current
    branch -- callers requiring that check call
    verify_branch_matches_manifest separately."""
    require_clean_worktree(repo_root)
    repository_commit = resolve_code_commit(repo_root)
    return CampaignProvenance(
        repository=REPOSITORY_IDENTITY,
        repository_commit=repository_commit,
        branch=manifest.branch,
        manifest_fingerprint=manifest.fingerprint,
        campaign_id=manifest.campaign_id,
        frozen_preregistration_commit=manifest.frozen_preregistration_commit,
        level2_reference_campaign_id=manifest.level2_reference.campaign_id,
        level2_reference_manifest_fingerprint=manifest.level2_reference.manifest_fingerprint,
        level2_reference_repository_commit=manifest.level2_reference.repository_commit,
        level2_reference_frozen_preregistration_commit=manifest.level2_reference.frozen_preregistration_commit,
    )


def verify_branch_matches_manifest(provenance: CampaignProvenance, *, repo_root: str | None = None) -> None:
    """Refuses a campaign whose manifest-declared branch does not match
    the repository's actual current branch at campaign start."""
    actual_branch = resolve_current_branch(repo_root)
    if actual_branch != provenance.branch:
        raise ProvenanceResolutionFailure(
            f"manifest branch {provenance.branch!r} does not match the repository's actual "
            f"current branch {actual_branch!r}"
        )
