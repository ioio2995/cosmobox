from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from experiments.level1c import manifest as manifest_module
from experiments.level1c import planning as planning_module
from scripts.level1c_campaign import campaign as campaign_module
from scripts.level1c_campaign.campaign import (
    CASE_ORCHESTRATION_STATUSES,
    Level1CCampaignExecutionReport,
    Level1CCaseOrchestrationOutcome,
    run_level1c_campaign,
)
from scripts.level1c_campaign.outputs import Level1CCaseRunValidation

REPO_COMMIT = "d" * 40


# ---------------------------------------------------------------------------
# Fixtures -- the real manifest and build_level1c_campaign_plan (pure, no
# diagonalization) supply the real 20-case plan. run_level1c_case,
# write_case_success, write_case_failure, and validate_existing_level1c_
# case_run are always monkeypatched with recording fakes -- no
# diagonalization ever runs in this suite.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest() -> manifest_module.Level1CManifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def real_plan(manifest: manifest_module.Level1CManifest) -> tuple:
    return planning_module.build_level1c_campaign_plan(manifest)


def _case(real_plan: tuple, *, geometry: str, spin: int, hamiltonian_case_id: str):
    return next(
        c
        for c in real_plan
        if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture
def two_cases(real_plan: tuple) -> tuple:
    return (
        _case(real_plan, geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00"),
        _case(real_plan, geometry="ring5", spin=2, hamiltonian_case_id="j0-1.00"),
    )


@pytest.fixture
def three_cases(real_plan: tuple) -> tuple:
    return (
        _case(real_plan, geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00"),
        _case(real_plan, geometry="triangle", spin=3, hamiltonian_case_id="j0-1.00"),
        _case(real_plan, geometry="ring5", spin=2, hamiltonian_case_id="j0-1.00"),
    )


class _Recorder:
    def __init__(self) -> None:
        self.validate_calls: list[dict] = []
        self.run_calls: list[str] = []
        self.success_calls: list[str] = []
        self.failure_calls: list[dict] = []


@dataclasses.dataclass(frozen=True)
class _FakeResult:
    case_id: str


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: tuple) -> None:
    def fake_build_level1c_campaign_plan(manifest_arg):
        return plan

    monkeypatch.setattr(campaign_module, "build_level1c_campaign_plan", fake_build_level1c_campaign_plan)


def _patch_validate(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, valid_case_ids: frozenset[str] = frozenset()
) -> None:
    def fake_validate_existing_level1c_case_run(output_dir, case_id, *, level1c_manifest, repository_commit):
        recorder.validate_calls.append(
            dict(
                output_dir=output_dir,
                case_id=case_id,
                campaign_id=level1c_manifest.campaign_id,
                manifest_fingerprint=level1c_manifest.fingerprint,
                repository_commit=repository_commit,
            )
        )
        if case_id in valid_case_ids:
            return Level1CCaseRunValidation(is_valid=True, reason=None)
        return Level1CCaseRunValidation(is_valid=False, reason="not reusable (test)")

    monkeypatch.setattr(campaign_module, "validate_existing_level1c_case_run", fake_validate_existing_level1c_case_run)


def _patch_run_level1c_case(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, raise_map: dict[str, BaseException] | None = None
) -> None:
    raise_map = raise_map or {}

    def fake_run_level1c_case(manifest_arg, case, *, repository_commit):
        recorder.run_calls.append(case.case_id)
        if case.case_id in raise_map:
            raise raise_map[case.case_id]
        return _FakeResult(case_id=case.case_id)

    monkeypatch.setattr(campaign_module, "run_level1c_case", fake_run_level1c_case)


def _patch_write_case_success(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, raise_for: frozenset[str] = frozenset()
) -> None:
    def fake_write_case_success(output_dir, manifest_arg, case, result, *, repository_commit):
        recorder.success_calls.append(result.case_id)
        if result.case_id in raise_for:
            raise RuntimeError(f"write_case_success failed for {result.case_id}")

    monkeypatch.setattr(campaign_module, "write_case_success", fake_write_case_success)


def _patch_write_case_failure(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, raise_for: frozenset[str] = frozenset()
) -> None:
    def fake_write_case_failure(output_dir, manifest_arg, case, *, repository_commit, run_status):
        recorder.failure_calls.append(dict(case_id=case.case_id, run_status=run_status, repository_commit=repository_commit))
        if case.case_id in raise_for:
            raise RuntimeError(f"write_case_failure failed for {case.case_id}")

    monkeypatch.setattr(campaign_module, "write_case_failure", fake_write_case_failure)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    manifest: manifest_module.Level1CManifest,
    tmp_path: Path,
    plan: tuple,
    *,
    valid_case_ids: frozenset[str] = frozenset(),
    raise_map: dict[str, BaseException] | None = None,
    success_raise_for: frozenset[str] = frozenset(),
    failure_raise_for: frozenset[str] = frozenset(),
    repository_commit: str = REPO_COMMIT,
) -> tuple[Level1CCampaignExecutionReport, _Recorder]:
    recorder = _Recorder()
    _patch_plan(monkeypatch, plan)
    _patch_validate(monkeypatch, recorder, valid_case_ids=valid_case_ids)
    _patch_run_level1c_case(monkeypatch, recorder, raise_map=raise_map)
    _patch_write_case_success(monkeypatch, recorder, raise_for=success_raise_for)
    _patch_write_case_failure(monkeypatch, recorder, raise_for=failure_raise_for)
    report = run_level1c_campaign(manifest, output_dir=tmp_path, repository_commit=repository_commit)
    return report, recorder


# ---------------------------------------------------------------------------
# Real 20-case plan, order, and full traversal (no diagonalization: only
# run_level1c_case/write_case_success/write_case_failure/validate_existing_
# level1c_case_run are monkeypatched -- build_level1c_campaign_plan itself
# is the REAL manifest-derived plan).
# ---------------------------------------------------------------------------


def test_real_plan_has_exactly_20_cases(real_plan: tuple) -> None:
    assert len(real_plan) == 20


def test_all_20_real_cases_are_traversed_and_executed(monkeypatch, manifest, tmp_path, real_plan) -> None:
    recorder = _Recorder()
    _patch_validate(monkeypatch, recorder, valid_case_ids=frozenset())
    _patch_run_level1c_case(monkeypatch, recorder)
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder)
    report = run_level1c_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)

    assert report.total_required == 20
    assert report.executed_success_count == 20
    assert report.global_success is True
    assert recorder.run_calls == [case.case_id for case in real_plan]


def test_case_outcomes_preserve_real_plan_order(monkeypatch, manifest, tmp_path, real_plan) -> None:
    recorder = _Recorder()
    _patch_validate(monkeypatch, recorder, valid_case_ids=frozenset())
    _patch_run_level1c_case(monkeypatch, recorder)
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder)
    report = run_level1c_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)

    assert [outcome.case_id for outcome in report.case_outcomes] == [case.case_id for case in real_plan]


# ---------------------------------------------------------------------------
# Skip / resume behavior (small monkeypatched plans, mirroring
# tests/scripts/level1b_campaign/test_campaign.py's own structure).
# ---------------------------------------------------------------------------


def test_all_new_cases_are_all_executed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert report.executed_success_count == 2
    assert report.reused_success_count == 0
    assert sorted(recorder.run_calls) == sorted(case.case_id for case in two_cases)


def test_all_valid_existing_runs_are_all_skipped(monkeypatch, manifest, tmp_path, two_cases) -> None:
    valid_ids = frozenset(case.case_id for case in two_cases)
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=valid_ids)
    assert report.reused_success_count == 2
    assert report.executed_success_count == 0
    assert recorder.run_calls == []


def test_no_writer_invoked_for_a_skipped_case(monkeypatch, manifest, tmp_path, two_cases) -> None:
    valid_ids = frozenset(case.case_id for case in two_cases)
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=valid_ids)
    assert recorder.success_calls == []
    assert recorder.failure_calls == []


def test_mixed_skip_and_new(monkeypatch, manifest, tmp_path, three_cases) -> None:
    valid_ids = frozenset({three_cases[1].case_id})
    report, recorder = _run(monkeypatch, manifest, tmp_path, three_cases, valid_case_ids=valid_ids)
    assert report.reused_success_count == 1
    assert report.executed_success_count == 2
    assert sorted(recorder.run_calls) == sorted(c.case_id for c in (three_cases[0], three_cases[2]))


def test_invalid_existing_run_triggers_reexecution(monkeypatch, manifest, tmp_path, two_cases) -> None:
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=frozenset())
    assert report.executed_success_count == 2
    assert len(recorder.run_calls) == 2


def test_success_status_only_after_write_case_success_called(monkeypatch, manifest, tmp_path, two_cases) -> None:
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert all(outcome.status == "success" for outcome in report.case_outcomes)
    assert sorted(recorder.success_calls) == sorted(recorder.run_calls)


# ---------------------------------------------------------------------------
# Exception isolation.
# ---------------------------------------------------------------------------


def test_run_level1c_case_failure_yields_failed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing_id: ValueError("boom")})
    outcome = next(o for o in report.case_outcomes if o.case_id == failing_id)
    assert outcome.status == "failed"
    assert "boom" in outcome.errors[0]
    assert recorder.failure_calls[0]["case_id"] == failing_id
    assert recorder.failure_calls[0]["run_status"] == "failed"


def test_next_case_executed_after_ordinary_failure(monkeypatch, manifest, tmp_path, three_cases) -> None:
    failing_id = three_cases[0].case_id
    report, recorder = _run(monkeypatch, manifest, tmp_path, three_cases, raise_map={failing_id: RuntimeError("x")})
    assert set(recorder.run_calls) == {c.case_id for c in three_cases}
    assert report.failed_count == 1
    assert report.executed_success_count == 2


def test_blank_exception_message_still_yields_non_empty_error(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id

    class _BlankError(Exception):
        pass

    report, _ = _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing_id: _BlankError()})
    outcome = next(o for o in report.case_outcomes if o.case_id == failing_id)
    assert outcome.errors[0] == "_BlankError"


def test_keyboard_interrupt_is_not_swallowed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id
    with pytest.raises(KeyboardInterrupt):
        _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing_id: KeyboardInterrupt()})


def test_system_exit_is_not_swallowed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id
    with pytest.raises(SystemExit):
        _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing_id: SystemExit()})


def test_write_case_success_failure_yields_failed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    """A write_case_success failure is an ordinary exception like any
    other raised inside the try block -- caught, converted into a
    'failed' outcome via write_case_failure, never propagated raw (this
    matches scripts.level1b_campaign.campaign.run_campaign's own already-
    accepted behavior exactly: only a failure of write_case_failure
    itself is left uncaught, see test_write_case_failure_failure_
    propagates below)."""
    failing_id = two_cases[0].case_id
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, success_raise_for=frozenset({failing_id}))
    outcome = next(o for o in report.case_outcomes if o.case_id == failing_id)
    assert outcome.status == "failed"
    assert recorder.failure_calls[0]["case_id"] == failing_id
    assert recorder.failure_calls[0]["run_status"] == "failed"


def test_write_case_failure_failure_propagates(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id
    with pytest.raises(RuntimeError, match="write_case_failure failed"):
        _run(
            monkeypatch,
            manifest,
            tmp_path,
            two_cases,
            raise_map={failing_id: ValueError("boom")},
            failure_raise_for=frozenset({failing_id}),
        )


# ---------------------------------------------------------------------------
# Resource guardrail (defensive only -- never triggered by the real
# manifest's 20 cases, exercised here via a synthetic dimension override).
# ---------------------------------------------------------------------------


def test_dimension_exceedance_yields_resource_guardrail_exceeded(monkeypatch, manifest, tmp_path, two_cases) -> None:
    oversized_case = dataclasses.replace(two_cases[0], physical_dimension=two_cases[0].spectrum_options.max_sparse_dimension + 1)
    plan = (oversized_case, two_cases[1])
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    outcome = next(o for o in report.case_outcomes if o.case_id == oversized_case.case_id)
    assert outcome.status == "resource_guardrail_exceeded"
    assert oversized_case.case_id not in recorder.run_calls
    assert recorder.failure_calls[0]["run_status"] == "resource_guardrail_exceeded"


def test_dimension_within_sparse_bound_is_not_an_exceedance(monkeypatch, manifest, tmp_path, two_cases) -> None:
    fine_case = dataclasses.replace(two_cases[0], physical_dimension=two_cases[0].spectrum_options.max_sparse_dimension)
    plan = (fine_case,)
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    assert report.executed_success_count == 1
    assert fine_case.case_id in recorder.run_calls


# ---------------------------------------------------------------------------
# Provenance and counters.
# ---------------------------------------------------------------------------


def test_repository_commit_is_forwarded_exactly(monkeypatch, manifest, tmp_path, two_cases) -> None:
    custom_commit = "f" * 40
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, repository_commit=custom_commit)
    assert all(call["repository_commit"] == custom_commit for call in recorder.validate_calls)


def test_manifest_provenance_is_forwarded_to_validate(monkeypatch, manifest, tmp_path, two_cases) -> None:
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert all(call["campaign_id"] == manifest.campaign_id for call in recorder.validate_calls)
    assert all(call["manifest_fingerprint"] == manifest.fingerprint for call in recorder.validate_calls)


def test_repository_commit_must_be_non_empty(manifest, tmp_path) -> None:
    with pytest.raises(ValueError, match="repository_commit must be non-empty"):
        run_level1c_campaign(manifest, output_dir=tmp_path, repository_commit="")


def test_global_counters_are_exact(monkeypatch, manifest, tmp_path, three_cases) -> None:
    valid_ids = frozenset({three_cases[0].case_id})
    failing_id = three_cases[1].case_id
    report, _ = _run(monkeypatch, manifest, tmp_path, three_cases, valid_case_ids=valid_ids, raise_map={failing_id: ValueError("x")})
    assert report.reused_success_count == 1
    assert report.executed_success_count == 1
    assert report.failed_count == 1
    assert report.resource_guardrail_exceeded_count == 0
    assert report.total_required == 3
    assert report.global_success is False


def test_global_success_true_only_when_all_success_or_skipped(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing_id = two_cases[0].case_id
    report, _ = _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing_id: ValueError("x")})
    assert report.global_success is False

    report_ok, _ = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert report_ok.global_success is True


# ---------------------------------------------------------------------------
# Report dataclasses: internal-consistency rejection.
# ---------------------------------------------------------------------------


def test_case_orchestration_statuses_are_exactly_the_frozen_taxonomy() -> None:
    assert CASE_ORCHESTRATION_STATUSES == ("success", "skipped_existing_valid", "resource_guardrail_exceeded", "failed")


def test_case_orchestration_outcome_rejects_errors_for_success() -> None:
    with pytest.raises(ValueError, match="errors must be empty"):
        Level1CCaseOrchestrationOutcome(case_id="x", status="success", errors=("oops",))


def test_case_orchestration_outcome_rejects_missing_errors_for_failure() -> None:
    with pytest.raises(ValueError, match="errors must be non-empty"):
        Level1CCaseOrchestrationOutcome(case_id="x", status="failed", errors=())


def test_case_orchestration_outcome_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        Level1CCaseOrchestrationOutcome(case_id="x", status="bogus", errors=())


def test_campaign_execution_report_rejects_inconsistent_counters() -> None:
    outcome = Level1CCaseOrchestrationOutcome(case_id="x", status="success", errors=())
    with pytest.raises(ValueError, match="does not match"):
        Level1CCampaignExecutionReport(
            case_outcomes=(outcome,),
            total_required=1,
            executed_success_count=0,  # wrong: should be 1
            reused_success_count=0,
            resource_guardrail_exceeded_count=0,
            failed_count=0,
            global_success=True,
        )


def test_campaign_execution_report_rejects_wrong_global_success() -> None:
    outcome = Level1CCaseOrchestrationOutcome(case_id="x", status="failed", errors=("e",))
    with pytest.raises(ValueError, match="global_success"):
        Level1CCampaignExecutionReport(
            case_outcomes=(outcome,),
            total_required=1,
            executed_success_count=0,
            reused_success_count=0,
            resource_guardrail_exceeded_count=0,
            failed_count=1,
            global_success=True,  # wrong: a failed case means global_success must be False
        )


def test_campaign_execution_report_rejects_duplicate_case_ids() -> None:
    outcome_a = Level1CCaseOrchestrationOutcome(case_id="x", status="success", errors=())
    outcome_b = Level1CCaseOrchestrationOutcome(case_id="x", status="success", errors=())
    with pytest.raises(ValueError, match="duplicate case_id"):
        Level1CCampaignExecutionReport(
            case_outcomes=(outcome_a, outcome_b),
            total_required=2,
            executed_success_count=2,
            reused_success_count=0,
            resource_guardrail_exceeded_count=0,
            failed_count=0,
            global_success=True,
        )
