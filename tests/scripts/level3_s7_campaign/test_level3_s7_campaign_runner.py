"""Unit/integration tests for scripts.level3_s7_campaign.runner (lot L3-AC).

execution.run_case is ALWAYS monkeypatched to a synthetic factory here --
no real diagonalization, no real S=7 Hamiltonian, anywhere in this file.
The frozen S=6 reference (cosmobox.level3.frozen_s6_reference) and the
frozen S=2/S=3/S=4/S=5 references it embeds are the real, versioned
data -- read-only, never modified, never faked.
execution.compare_spin_pair is the real function, called on the synthetic
(but fully valid) S7 CaseExecutionResult and the real reconstructed S6
CaseExecutionResult. provenance.resolve_campaign_provenance/
verify_branch_matches_manifest are monkeypatched to avoid depending on
this repository's real git state.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from cosmobox.level2 import metrics, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec, compare_spin_pair
from experiments.level3.s7_manifest import load_manifest
from scripts.level3_s7_campaign import runner
from scripts.level3_s7_campaign.outputs import campaign_manifest_path, campaign_summary_path, case_artifact_path
from scripts.level3_s7_campaign.provenance import REPOSITORY_IDENTITY, CampaignProvenance
from scripts.level3_s7_campaign.runner import CampaignAlreadyExists, run_campaign

_REPOSITORY_COMMIT = "c" * 40
_SYNTHETIC_DIMENSIONS = {"triangle": 5, "ring4": 5, "ring5": 5}


@pytest.fixture()
def manifest():
    return load_manifest()


@pytest.fixture(autouse=True)
def _fake_provenance(monkeypatch, manifest):
    provenance = CampaignProvenance(
        repository=REPOSITORY_IDENTITY,
        repository_commit=_REPOSITORY_COMMIT,
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
        level3_s5_reference_campaign_id=manifest.level3_s5_reference.campaign_id,
        level3_s5_reference_manifest_fingerprint=manifest.level3_s5_reference.manifest_fingerprint,
        level3_s5_reference_repository_commit=manifest.level3_s5_reference.repository_commit,
        level3_s5_reference_frozen_preregistration_commit=manifest.level3_s5_reference.frozen_preregistration_commit,
        level3_s6_reference_campaign_id=manifest.level3_s6_reference.campaign_id,
        level3_s6_reference_manifest_fingerprint=manifest.level3_s6_reference.manifest_fingerprint,
        level3_s6_reference_repository_commit=manifest.level3_s6_reference.repository_commit,
        level3_s6_reference_frozen_preregistration_commit=manifest.level3_s6_reference.frozen_preregistration_commit,
    )

    def fake_resolve(passed_manifest, *, repo_root=None):
        assert passed_manifest is manifest
        return provenance

    monkeypatch.setattr(runner.provenance, "resolve_campaign_provenance", fake_resolve)
    monkeypatch.setattr(runner.provenance, "verify_branch_matches_manifest", lambda *a, **k: None)
    return provenance


@pytest.fixture(autouse=True)
def _synthetic_gate_reference(monkeypatch):
    # The real L3-AA dimensions (288/992/3520) would require a real
    # diagonalization to produce a matching synthetic result; replace
    # the gate's expected-dimension table with one matching the small
    # synthetic dimension (5) this file's fake run_case actually returns.
    monkeypatch.setattr(runner.gates, "EXPECTED_S7_DIMENSIONS", dict(_SYNTHETIC_DIMENSIONS))


def _entry(seed: float, q_start: float, q_end: float) -> MultipletProfileEntry:
    matrix = np.array([[seed, 0.0], [0.0, seed]])
    return MultipletProfileEntry(
        energy=seed, multiplicity=1, epsilon=0.5,
        q_start=q_start, q_end=q_end, q_midpoint=(q_start + q_end) / 2,
        m_tt=seed, r_eff=metrics.Available(0.1 * seed, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
        c_tt_conn=matrix,
        rho_qq={
            (0, 1): metrics.RhoQQEntry(value=0.1, null_reason=None),
            (1, 0): metrics.RhoQQEntry(value=None, null_reason="ZERO_LOCAL_CHARGE_VARIANCE"),
        },
    )


def _synthetic_case_result(spec: CaseSpec, *, n: int = 5) -> CaseExecutionResult:
    boundaries = [i / n for i in range(n + 1)]
    entries = tuple(_entry(float(i + 1), boundaries[i], boundaries[i + 1]) for i in range(n))
    analyses = {metric: orchestration.analyze_case_metric(entries, metric) for metric in orchestration.ALL_METRICS}
    return CaseExecutionResult(
        spec=spec, dimension=n, group_count=n, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )


@pytest.fixture()
def _fake_run_case(monkeypatch):
    calls: list[CaseSpec] = []

    def fake(spec: CaseSpec) -> CaseExecutionResult:
        calls.append(spec)
        return _synthetic_case_result(spec)

    monkeypatch.setattr(runner, "run_case", fake)
    return calls


@pytest.fixture()
def _compare_spin_pair_spy(monkeypatch):
    calls: list[tuple] = []
    real = compare_spin_pair

    def spy(result_a, result_b):
        calls.append((result_a, result_b))
        return real(result_a, result_b)

    monkeypatch.setattr(runner, "compare_spin_pair", spy)
    return calls


# ---------------------------------------------------------------------------
# End-to-end synthetic integration -- REAL frozen S6/S5/S4/S3/S2 reference, FAKE S7
# ---------------------------------------------------------------------------


def test_run_campaign_produces_full_artifact_tree(tmp_path, manifest, _fake_run_case):
    summary_path = run_campaign(tmp_path, manifest=manifest)

    assert summary_path == campaign_summary_path(tmp_path, manifest.campaign_id)
    assert campaign_manifest_path(tmp_path, manifest.campaign_id).exists()
    for geometry in ("triangle", "ring4", "ring5"):
        assert case_artifact_path(tmp_path, manifest.campaign_id, geometry, 7).exists()
    assert summary_path.exists()

    summary_document = json.loads(summary_path.read_text())
    assert summary_document["campaign_status"] == "COMPLETE"
    assert summary_document["repository"] == REPOSITORY_IDENTITY
    assert summary_document["level2_reference"]["campaign_id"] == "level2-energy-regime-v1"
    assert summary_document["level3_s4_reference"]["campaign_id"] == "level3-s4-truncation-extension-v1"
    assert summary_document["level3_s5_reference"]["campaign_id"] == "level3-s5-truncation-extension-v1"
    assert summary_document["level3_s6_reference"]["campaign_id"] == "level3-s6-truncation-extension-v1"
    assert {entry["geometry"] for entry in summary_document["geometries"]} == {"triangle", "ring4", "ring5"}

    manifest_document = json.loads(campaign_manifest_path(tmp_path, manifest.campaign_id).read_text())
    assert manifest_document == manifest.raw

    case_document = json.loads(case_artifact_path(tmp_path, manifest.campaign_id, "triangle", 7).read_text())
    assert case_document["geometry"] == "triangle"
    assert case_document["spin"] == 7
    assert case_document["repository_commit"] == _REPOSITORY_COMMIT


def test_run_campaign_invokes_run_case_exactly_three_times_in_manifest_order(tmp_path, manifest, _fake_run_case):
    run_campaign(tmp_path, manifest=manifest)
    assert len(_fake_run_case) == 3
    assert [(spec.geometry, spec.spin) for spec in _fake_run_case] == [
        (case.geometry, case.spin) for case in manifest.cases
    ]
    assert all(spec.spin == 7 for spec in _fake_run_case)


def test_run_campaign_calls_compare_spin_pair_exactly_three_times(tmp_path, manifest, _fake_run_case, _compare_spin_pair_spy):
    run_campaign(tmp_path, manifest=manifest)
    assert len(_compare_spin_pair_spy) == 3
    geometries = {result_a.spec.geometry for result_a, _ in _compare_spin_pair_spy}
    assert geometries == {"triangle", "ring4", "ring5"}
    # result_a is always the reconstructed S6 reference, result_b the S7 result
    assert all(result_a.spec.spin == 6 for result_a, _ in _compare_spin_pair_spy)
    assert all(result_b.spec.spin == 7 for _, result_b in _compare_spin_pair_spy)


# ---------------------------------------------------------------------------
# Ordering: plan 3/3 before any comparison; no comparison before all three
# S7 cases are persisted
# ---------------------------------------------------------------------------


def test_run_campaign_plans_all_three_cases_before_running_any(tmp_path, manifest, monkeypatch):
    events: list[str] = []
    real_plan = runner.planning.plan_campaign
    real_run_case = _synthetic_case_result

    def spy_plan(passed_manifest):
        events.append("plan")
        return real_plan(passed_manifest)

    def fake_run_case(spec):
        events.append(f"run_case:{spec.geometry}")
        return real_run_case(spec)

    monkeypatch.setattr(runner.planning, "plan_campaign", spy_plan)
    monkeypatch.setattr(runner, "run_case", fake_run_case)

    run_campaign(tmp_path, manifest=manifest)

    plan_index = events.index("plan")
    run_case_indices = [i for i, e in enumerate(events) if e.startswith("run_case:")]
    assert all(plan_index < i for i in run_case_indices)


def test_run_campaign_never_compares_before_all_three_s7_cases_are_persisted(tmp_path, manifest, monkeypatch):
    events: list[str] = []
    real = compare_spin_pair

    def fake_run_case(spec):
        result = _synthetic_case_result(spec)
        events.append(f"case_persisted:{spec.geometry}")
        return result

    def spy_compare(result_a, result_b):
        events.append(f"compare:{result_b.spec.geometry}")
        return real(result_a, result_b)

    monkeypatch.setattr(runner, "run_case", fake_run_case)
    monkeypatch.setattr(runner, "compare_spin_pair", spy_compare)

    run_campaign(tmp_path, manifest=manifest)

    first_compare_index = next(i for i, e in enumerate(events) if e.startswith("compare:"))
    case_persisted_indices = [i for i, e in enumerate(events) if e.startswith("case_persisted:")]
    assert len(case_persisted_indices) == 3
    assert all(i < first_compare_index for i in case_persisted_indices)


def test_run_campaign_writes_campaign_summary_last(tmp_path, manifest, _fake_run_case):
    run_campaign(tmp_path, manifest=manifest)
    summary_path = campaign_summary_path(tmp_path, manifest.campaign_id)
    case_paths = [case_artifact_path(tmp_path, manifest.campaign_id, g, 7) for g in ("triangle", "ring4", "ring5")]
    summary_mtime = summary_path.stat().st_mtime_ns
    assert all(path.stat().st_mtime_ns <= summary_mtime for path in case_paths)


# ---------------------------------------------------------------------------
# No implicit resume / refusal paths / no partial normative campaign
# ---------------------------------------------------------------------------


def test_run_campaign_refuses_when_summary_already_exists(tmp_path, manifest, _fake_run_case):
    run_campaign(tmp_path, manifest=manifest)
    with pytest.raises(CampaignAlreadyExists):
        run_campaign(tmp_path, manifest=manifest)


def test_run_campaign_leaves_no_summary_when_a_case_run_fails(tmp_path, manifest, monkeypatch):
    def failing_run_case(spec: CaseSpec) -> CaseExecutionResult:
        if spec.geometry == "ring5":
            raise RuntimeError("simulated case failure")
        return _synthetic_case_result(spec)

    monkeypatch.setattr(runner, "run_case", failing_run_case)
    with pytest.raises(RuntimeError):
        run_campaign(tmp_path, manifest=manifest)
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()


def test_run_campaign_leaves_no_summary_and_no_comparison_when_second_case_fails(tmp_path, manifest, monkeypatch):
    events: list[str] = []
    real = compare_spin_pair

    def failing_run_case(spec: CaseSpec) -> CaseExecutionResult:
        if spec.geometry == "ring4":
            raise RuntimeError("simulated second-case failure")
        events.append(f"case:{spec.geometry}")
        return _synthetic_case_result(spec)

    def spy_compare(result_a, result_b):
        events.append(f"compare:{result_b.spec.geometry}")
        return real(result_a, result_b)

    monkeypatch.setattr(runner, "run_case", failing_run_case)
    monkeypatch.setattr(runner, "compare_spin_pair", spy_compare)

    with pytest.raises(RuntimeError):
        run_campaign(tmp_path, manifest=manifest)

    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()
    assert not any(event.startswith("compare:") for event in events)


def test_run_campaign_leaves_no_summary_when_branch_verification_fails(tmp_path, manifest, monkeypatch):
    from scripts.level3_s7_campaign.provenance import ProvenanceResolutionFailure

    def failing_verify(*args, **kwargs):
        raise ProvenanceResolutionFailure("simulated branch mismatch")

    monkeypatch.setattr(runner.provenance, "verify_branch_matches_manifest", failing_verify)
    with pytest.raises(ProvenanceResolutionFailure):
        run_campaign(tmp_path, manifest=manifest)
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()
    assert not case_artifact_path(tmp_path, manifest.campaign_id, "triangle", 7).exists()


def test_run_campaign_fails_when_manifest_json_already_exists(tmp_path, manifest, _fake_run_case):
    campaign_manifest_path(tmp_path, manifest.campaign_id).parent.mkdir(parents=True, exist_ok=True)
    campaign_manifest_path(tmp_path, manifest.campaign_id).write_text('{"stale": true}\n')

    with pytest.raises(runner.outputs.CampaignManifestAlreadyExists):
        run_campaign(tmp_path, manifest=manifest)

    assert len(_fake_run_case) == 0
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()


def test_run_campaign_cannot_overwrite_manifest_of_a_partial_old_campaign(tmp_path, manifest, _fake_run_case):
    campaign_manifest_path(tmp_path, manifest.campaign_id).parent.mkdir(parents=True, exist_ok=True)
    campaign_manifest_path(tmp_path, manifest.campaign_id).write_text(json.dumps(manifest.raw) + "\n")
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()

    with pytest.raises(runner.outputs.CampaignManifestAlreadyExists):
        run_campaign(tmp_path, manifest=manifest)

    assert len(_fake_run_case) == 0
    assert not campaign_summary_path(tmp_path, manifest.campaign_id).exists()


# ---------------------------------------------------------------------------
# No real S=7 physical function is ever reachable from the runner
# ---------------------------------------------------------------------------


def test_run_campaign_never_calls_a_real_physical_s7_primitive(tmp_path, manifest, monkeypatch, _fake_run_case):
    import cosmobox.level0.hamiltonian as hamiltonian_module
    import cosmobox.level0.reports as reports_module

    def forbidden(*args, **kwargs):
        raise AssertionError("the runner must never call a Level0 physics primitive directly")

    monkeypatch.setattr(hamiltonian_module, "build_hamiltonian_terms", forbidden)
    monkeypatch.setattr(reports_module, "build_level0_report_with_eigenvectors", forbidden)

    run_campaign(tmp_path, manifest=manifest)  # must not raise: run_case is faked, never reaches these
