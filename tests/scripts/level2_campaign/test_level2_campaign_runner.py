"""Unit/integration tests for scripts.level2_campaign.runner (lot
L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER).

execution.run_case is always monkeypatched to a synthetic factory --
no real diagonalization anywhere in this file. execution.compare_geometry
is the real function, called on the synthetic (but fully valid)
CaseExecutionResult objects the factory produces. gates.L2_A1_PREFLIGHT_
REFERENCE is monkeypatched to a small synthetic (dimension=3,
group_count=3) table for all six frozen (geometry, spin) pairs, mirroring
tests/scripts/level2_campaign/test_gates.py's own precedent.
provenance.resolve_campaign_provenance/verify_branch_matches_manifest are
monkeypatched to avoid depending on this repository's real git state.
"""

from __future__ import annotations

import json

import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import CaseExecutionResult, CaseSpec, GeometryComparison, compare_geometry
from experiments.level2.manifest import load_manifest
from scripts.level2_campaign import runner
from scripts.level2_campaign.outputs import (
    campaign_manifest_path,
    campaign_summary_path,
    case_artifact_path,
)
from scripts.level2_campaign.provenance import CampaignProvenance
from scripts.level2_campaign.runner import CampaignAlreadyExists, run_campaign

_SYNTHETIC_REFERENCE = {
    ("triangle", 2): (3, 3), ("triangle", 3): (3, 3),
    ("ring4", 2): (3, 3), ("ring4", 3): (3, 3),
    ("ring5", 2): (3, 3), ("ring5", 3): (3, 3),
}

_REPOSITORY_COMMIT = "c" * 40


@pytest.fixture(autouse=True)
def _synthetic_gate_reference(monkeypatch):
    monkeypatch.setattr(runner.gates, "L2_A1_PREFLIGHT_REFERENCE", _SYNTHETIC_REFERENCE)


@pytest.fixture()
def manifest():
    return load_manifest()


@pytest.fixture(autouse=True)
def _fake_provenance(monkeypatch, manifest):
    provenance = CampaignProvenance(
        repository_commit=_REPOSITORY_COMMIT,
        branch=manifest.branch,
        manifest_fingerprint=manifest.fingerprint,
        campaign_id=manifest.campaign_id,
        frozen_preregistration_commit=manifest.frozen_preregistration_commit,
    )

    def fake_resolve(passed_manifest, *, repo_root=None):
        assert passed_manifest is manifest
        return provenance

    monkeypatch.setattr(runner.provenance, "resolve_campaign_provenance", fake_resolve)
    monkeypatch.setattr(runner.provenance, "verify_branch_matches_manifest", lambda *a, **k: None)
    return provenance


def _entry(seed: float, q_start: float, q_end: float) -> MultipletProfileEntry:
    return MultipletProfileEntry(
        energy=seed,
        multiplicity=1,
        epsilon=0.5,
        q_start=q_start,
        q_end=q_end,
        q_midpoint=(q_start + q_end) / 2,
        m_tt=seed,
        r_eff=metrics.Available(0.1 * seed, None),
        a_qq=0.5,
        m_qq=metrics.Available(0.2, None),
        c_tt_conn=[[seed, 0.0], [0.0, seed]],
        rho_qq={
            (0, 1): metrics.RhoQQEntry(value=0.1, null_reason=None),
            (1, 0): metrics.RhoQQEntry(value=None, null_reason="ZERO_LOCAL_CHARGE_VARIANCE"),
        },
    )


def _synthetic_case_result(spec: CaseSpec) -> CaseExecutionResult:
    n = 3
    boundaries = [i / n for i in range(n + 1)]
    entries = tuple(
        _entry(float(i + 1) + spec.spin, boundaries[i], boundaries[i + 1]) for i in range(n)
    )
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=spec,
        dimension=n,
        group_count=n,
        entries=entries,
        m_tt_analysis=analyses["M_TT"],
        r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"],
        m_qq_analysis=analyses["M_QQ"],
    )


@pytest.fixture(autouse=True)
def _fake_run_case(monkeypatch):
    calls: list[CaseSpec] = []

    def fake(spec: CaseSpec) -> CaseExecutionResult:
        calls.append(spec)
        return _synthetic_case_result(spec)

    monkeypatch.setattr(runner, "run_case", fake)
    return calls


@pytest.fixture()
def _compare_geometry_spy(monkeypatch):
    calls: list[tuple] = []
    real = compare_geometry

    def spy(result_s2, result_s3):
        calls.append((result_s2, result_s3))
        return real(result_s2, result_s3)

    monkeypatch.setattr(runner, "compare_geometry", spy)
    return calls


# ---------------------------------------------------------------------------
# End-to-end synthetic integration
# ---------------------------------------------------------------------------


def test_run_campaign_produces_full_artifact_tree(tmp_path, manifest):
    summary_path = run_campaign(tmp_path, manifest=manifest)

    assert summary_path == campaign_summary_path(tmp_path, manifest.campaign_id)
    assert campaign_manifest_path(tmp_path, manifest.campaign_id).exists()
    for geometry, spin in _SYNTHETIC_REFERENCE:
        assert case_artifact_path(tmp_path, manifest.campaign_id, geometry, spin).exists()
    assert summary_path.exists()

    summary_document = json.loads(summary_path.read_text())
    assert summary_document["campaign_status"] == "COMPLETE"
    assert {entry["geometry"] for entry in summary_document["geometries"]} == {"triangle", "ring4", "ring5"}

    manifest_document = json.loads(campaign_manifest_path(tmp_path, manifest.campaign_id).read_text())
    assert manifest_document == manifest.raw

    case_document = json.loads(case_artifact_path(tmp_path, manifest.campaign_id, "triangle", 2).read_text())
    assert case_document["geometry"] == "triangle"
    assert case_document["spin"] == 2
    assert case_document["repository_commit"] == _REPOSITORY_COMMIT
    assert len(case_document["multiplet_entries"]) == 3
    assert len(case_document["multiplet_entries"][0]["c_tt_conn"]) == 2


def test_run_campaign_resolves_provenance_exactly_once(tmp_path, manifest, monkeypatch):
    calls = []
    real_fake = runner.provenance.resolve_campaign_provenance

    def counting_fake(passed_manifest, *, repo_root=None):
        calls.append(passed_manifest)
        return real_fake(passed_manifest, repo_root=repo_root)

    monkeypatch.setattr(runner.provenance, "resolve_campaign_provenance", counting_fake)
    run_campaign(tmp_path, manifest=manifest)
    assert len(calls) == 1


def test_run_campaign_invokes_run_case_exactly_six_times_in_manifest_order(tmp_path, manifest, _fake_run_case):
    run_campaign(tmp_path, manifest=manifest)
    assert len(_fake_run_case) == 6
    assert [(spec.geometry, spec.spin) for spec in _fake_run_case] == [
        (case.geometry, case.spin) for case in manifest.cases
    ]


def test_run_campaign_calls_compare_geometry_exactly_three_times(tmp_path, manifest, _compare_geometry_spy):
    run_campaign(tmp_path, manifest=manifest)
    assert len(_compare_geometry_spy) == 3
    geometries = {result_s2.spec.geometry for result_s2, _ in _compare_geometry_spy}
    assert geometries == {"triangle", "ring4", "ring5"}


# ---------------------------------------------------------------------------
# No implicit resume / refusal paths
# ---------------------------------------------------------------------------


def test_run_campaign_refuses_when_summary_already_exists(tmp_path, manifest):
    run_campaign(tmp_path, manifest=manifest)
    with pytest.raises(CampaignAlreadyExists):
        run_campaign(tmp_path, manifest=manifest)


def test_run_campaign_leaves_no_summary_when_a_case_run_fails(tmp_path, manifest, monkeypatch):
    def failing_run_case(spec: CaseSpec) -> CaseExecutionResult:
        if spec.geometry == "ring5" and spec.spin == 3:
            raise RuntimeError("simulated case failure")
        return _synthetic_case_result(spec)

    monkeypatch.setattr(runner, "run_case", failing_run_case)
    with pytest.raises(RuntimeError):
        run_campaign(tmp_path, manifest=manifest)
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()


def test_run_campaign_leaves_no_summary_when_branch_verification_fails(tmp_path, manifest, monkeypatch):
    from scripts.level2_campaign.provenance import ProvenanceResolutionFailure

    def failing_verify(*args, **kwargs):
        raise ProvenanceResolutionFailure("simulated branch mismatch")

    monkeypatch.setattr(runner.provenance, "verify_branch_matches_manifest", failing_verify)
    with pytest.raises(ProvenanceResolutionFailure):
        run_campaign(tmp_path, manifest=manifest)
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()
    # provenance verification happens before any case is run or persisted
    assert not case_artifact_path(tmp_path, manifest.campaign_id, "triangle", 2).exists()
