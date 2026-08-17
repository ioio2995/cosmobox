"""Campaign-start Git provenance resolution for Level3 S5 campaigns.

Deliberately duplicated from scripts/level3_campaign/provenance.py's own
generic git primitives (resolve_code_commit, resolve_current_branch,
require_clean_worktree, DIRTY_WORKTREE_POLICY=REFUSE_EXECUTION) rather
than imported, per the same isolation decision the S4 campaign layer
itself made from Level2.

CampaignProvenance additionally carries BOTH the frozen Level2 reference
identity AND the frozen Level3 S4 reference identity, pinned to the exact
constants cosmobox.level3.frozen_reference and
cosmobox.level3.frozen_s4_reference themselves validate against -- so a
campaign's own provenance record and the two frozen-reference loaders can
never silently diverge on which campaigns are the S2/S3 and S4 sources.
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
from cosmobox.level3.frozen_s4_reference import (
    LEVEL3_S4_REFERENCE_CAMPAIGN_ID,
    LEVEL3_S4_REFERENCE_FROZEN_PREREGISTRATION_COMMIT,
    LEVEL3_S4_REFERENCE_MANIFEST_FINGERPRINT,
    LEVEL3_S4_REFERENCE_REPOSITORY_COMMIT,
)
from experiments.level3.s5_manifest import Level3S5Manifest

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

REPOSITORY_IDENTITY = "ioio2995/cosmobox"
"""The frozen repository identity every persisted Level3 S5 artifact must
carry -- a fixed constant, never a caller-supplied or git-remote-derived
value."""


class ProvenanceResolutionFailure(RuntimeError):
    """Raised when the repository's Git state cannot be resolved, or is
    not clean. Carries no diff content or file paths -- a generic,
    sanitized failure only."""


def resolve_code_commit(repo_root: str | None = None) -> str:
    """The exact `git rev-parse HEAD` of `repo_root` (ambient cwd if
    None), strictly validated as 40 lowercase hex characters."""
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
    """The exact `git rev-parse --abbrev-ref HEAD` of `repo_root`
    (ambient cwd if None). A detached HEAD fails hard."""
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
    """The provenance record every persisted Level3 S5 artifact must
    carry, resolved once per campaign, plus the pinned identity of both
    frozen reference campaigns (Level2 for S=2/S=3, Level3 S4 for S=4)."""

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
    level3_s4_reference_campaign_id: str
    level3_s4_reference_manifest_fingerprint: str
    level3_s4_reference_repository_commit: str
    level3_s4_reference_frozen_preregistration_commit: str

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
        if self.level3_s4_reference_campaign_id != LEVEL3_S4_REFERENCE_CAMPAIGN_ID:
            raise ValueError(
                f"level3_s4_reference_campaign_id must be {LEVEL3_S4_REFERENCE_CAMPAIGN_ID!r}, "
                f"got {self.level3_s4_reference_campaign_id!r}"
            )
        if self.level3_s4_reference_manifest_fingerprint != LEVEL3_S4_REFERENCE_MANIFEST_FINGERPRINT:
            raise ValueError(
                f"level3_s4_reference_manifest_fingerprint must be {LEVEL3_S4_REFERENCE_MANIFEST_FINGERPRINT!r}, "
                f"got {self.level3_s4_reference_manifest_fingerprint!r}"
            )
        if self.level3_s4_reference_repository_commit != LEVEL3_S4_REFERENCE_REPOSITORY_COMMIT:
            raise ValueError(
                f"level3_s4_reference_repository_commit must be {LEVEL3_S4_REFERENCE_REPOSITORY_COMMIT!r}, "
                f"got {self.level3_s4_reference_repository_commit!r}"
            )
        if self.level3_s4_reference_frozen_preregistration_commit != LEVEL3_S4_REFERENCE_FROZEN_PREREGISTRATION_COMMIT:
            raise ValueError(
                "level3_s4_reference_frozen_preregistration_commit must be "
                f"{LEVEL3_S4_REFERENCE_FROZEN_PREREGISTRATION_COMMIT!r}, "
                f"got {self.level3_s4_reference_frozen_preregistration_commit!r}"
            )


def resolve_campaign_provenance(manifest: Level3S5Manifest, *, repo_root: str | None = None) -> CampaignProvenance:
    """require_clean_worktree, then resolve_code_commit, exactly once.
    branch/campaign_id/frozen_preregistration_commit/manifest_fingerprint/
    level2_reference_*/level3_s4_reference_* come from `manifest` itself
    -- never re-derived. repository is always exactly REPOSITORY_IDENTITY."""
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
        level3_s4_reference_campaign_id=manifest.level3_s4_reference.campaign_id,
        level3_s4_reference_manifest_fingerprint=manifest.level3_s4_reference.manifest_fingerprint,
        level3_s4_reference_repository_commit=manifest.level3_s4_reference.repository_commit,
        level3_s4_reference_frozen_preregistration_commit=manifest.level3_s4_reference.frozen_preregistration_commit,
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
