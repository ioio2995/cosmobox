"""Unit tests for scripts.level2_campaign.provenance (lot
L2-E-CAMPAIGN-INFRASTRUCTURE).

subprocess.run is monkeypatched throughout -- no real `git` invocation
depended upon for the failure/parsing-logic paths; resolve_code_commit's
own success path is exercised against this repository's real git state
(cheap, read-only, matches scripts/level1c_preflight's own precedent of
resolving the real HEAD in its own test suite).
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from experiments.level2.manifest import load_manifest
from scripts.level2_campaign.provenance import (
    CampaignProvenance,
    ProvenanceResolutionFailure,
    require_clean_worktree,
    resolve_campaign_provenance,
    resolve_code_commit,
)


def _fake_run(stdout: str, *, returncode: int = 0):
    def run(*args, **kwargs):
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, args)
        return SimpleNamespace(stdout=stdout, returncode=0)

    return run


# ---------------------------------------------------------------------------
# resolve_code_commit
# ---------------------------------------------------------------------------


def test_resolve_code_commit_returns_a_valid_sha_for_this_real_repository():
    sha = resolve_code_commit()
    assert len(sha) == 40
    assert all(char in "0123456789abcdef" for char in sha)


def test_resolve_code_commit_rejects_a_short_sha(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("abc123\n"))
    with pytest.raises(ProvenanceResolutionFailure):
        resolve_code_commit()


def test_resolve_code_commit_fails_hard_on_subprocess_error(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("", returncode=1))
    with pytest.raises(ProvenanceResolutionFailure):
        resolve_code_commit()


# ---------------------------------------------------------------------------
# require_clean_worktree
# ---------------------------------------------------------------------------


def test_require_clean_worktree_passes_when_porcelain_is_empty(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(""))
    require_clean_worktree()  # no exception


def test_require_clean_worktree_refuses_when_porcelain_is_nonempty(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(" M some/file.py\n"))
    with pytest.raises(ProvenanceResolutionFailure):
        require_clean_worktree()


# ---------------------------------------------------------------------------
# CampaignProvenance
# ---------------------------------------------------------------------------


def test_campaign_provenance_rejects_short_repository_commit():
    with pytest.raises(ValueError):
        CampaignProvenance(
            repository_commit="a" * 39,
            branch="research/level2-energy-regime",
            manifest_fingerprint="f" * 64,
            campaign_id="c",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )


def test_campaign_provenance_rejects_empty_campaign_id():
    with pytest.raises(ValueError):
        CampaignProvenance(
            repository_commit="a" * 40,
            branch="research/level2-energy-regime",
            manifest_fingerprint="f" * 64,
            campaign_id="",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )


# ---------------------------------------------------------------------------
# resolve_campaign_provenance -- wiring, once per campaign
# ---------------------------------------------------------------------------


def test_resolve_campaign_provenance_wires_manifest_fields_and_resolved_commit(monkeypatch):
    calls: list[tuple] = []

    def fake_run(args, **kwargs):
        calls.append(tuple(args))
        if args[1] == "status":
            return SimpleNamespace(stdout="", returncode=0)
        return SimpleNamespace(stdout="c" * 40 + "\n", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    manifest = load_manifest()
    provenance = resolve_campaign_provenance(manifest)

    assert provenance.repository_commit == "c" * 40
    assert provenance.branch == manifest.branch
    assert provenance.manifest_fingerprint == manifest.fingerprint
    assert provenance.campaign_id == manifest.campaign_id
    assert provenance.frozen_preregistration_commit == manifest.frozen_preregistration_commit
    # clean-worktree check happens before the commit is resolved
    assert calls[0][1] == "status"
    assert calls[1][1] == "rev-parse"


def test_resolve_campaign_provenance_refuses_dirty_worktree(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(" M dirty.py\n"))
    manifest = load_manifest()
    with pytest.raises(ProvenanceResolutionFailure):
        resolve_campaign_provenance(manifest)
