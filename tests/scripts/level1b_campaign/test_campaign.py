from __future__ import annotations

import dataclasses
import inspect
import subprocess
from pathlib import Path

import pytest

from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_campaign import campaign as campaign_module
from scripts.level1b_campaign.campaign import (
    CASE_ORCHESTRATION_STATUSES,
    CampaignExecutionReport,
    CaseOrchestrationOutcome,
    check_repository_cleanliness,
    run_campaign,
)
from scripts.level1b_campaign.outputs import CaseRunValidation

REPO_COMMIT = "d" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "load_case_records",
    "matching",
    "MatchOutcome",
    "gamma_O",
    "G_occ",
    "path_phase_coherence",
)


# ---------------------------------------------------------------------------
# Fixtures -- the real manifest and build_campaign_plan (pure, no
# diagonalization) supply realistic, self-verifying CampaignCaseSpec
# objects; individual tests derive small, deterministic synthetic plans
# from them via dataclasses.replace (physical_dimension and
# spectrum_options are not encoded in case_id, so replacing them keeps a
# self-consistent CampaignCaseSpec). run_single_case, write_case_success,
# write_case_failure, and validate_existing_case_run are always
# monkeypatched with recording fakes -- no diagonalization ever runs in
# this suite.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def real_plan(manifest: manifest_module.Manifest) -> tuple:
    return planning_module.build_campaign_plan(manifest)


def _case(real_plan: tuple, *, geometry: str, spin: int, hamiltonian_case_id: str = "reference"):
    return next(
        c
        for c in real_plan
        if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture
def two_cases(real_plan: tuple) -> tuple:
    return (
        _case(real_plan, geometry="triangle", spin=1),
        _case(real_plan, geometry="ring4", spin=1),
    )


@pytest.fixture
def three_cases(real_plan: tuple) -> tuple:
    return (
        _case(real_plan, geometry="triangle", spin=1),
        _case(real_plan, geometry="triangle", spin=2),
        _case(real_plan, geometry="ring4", spin=1),
    )


class _Recorder:
    def __init__(self) -> None:
        self.build_plan_calls = 0
        self.validate_calls: list[dict] = []
        self.run_calls: list[str] = []
        self.success_calls: list[str] = []
        self.failure_calls: list[dict] = []


@dataclasses.dataclass(frozen=True)
class _FakeResult:
    case_id: str


def _patch_plan(monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, plan: tuple) -> None:
    def fake_build_campaign_plan(manifest_arg):
        recorder.build_plan_calls += 1
        return plan

    monkeypatch.setattr(campaign_module, "build_campaign_plan", fake_build_campaign_plan)


def _patch_validate(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, valid_case_ids: frozenset[str] = frozenset()
) -> None:
    def fake_validate_existing_case_run(case_dir, *, case_id, campaign_id, manifest_fingerprint, repository_commit):
        recorder.validate_calls.append(
            dict(
                case_dir=case_dir,
                case_id=case_id,
                campaign_id=campaign_id,
                manifest_fingerprint=manifest_fingerprint,
                repository_commit=repository_commit,
            )
        )
        if case_id in valid_case_ids:
            return CaseRunValidation(is_valid=True, reason=None)
        return CaseRunValidation(is_valid=False, reason="not reusable (test)")

    monkeypatch.setattr(campaign_module, "validate_existing_case_run", fake_validate_existing_case_run)


def _patch_run_single_case(
    monkeypatch: pytest.MonkeyPatch,
    recorder: _Recorder,
    *,
    raise_map: dict[str, BaseException] | None = None,
) -> None:
    raise_map = raise_map or {}

    def fake_run_single_case(manifest_arg, case, *, repository_commit):
        recorder.run_calls.append(case.case_id)
        if case.case_id in raise_map:
            raise raise_map[case.case_id]
        return _FakeResult(case_id=case.case_id)

    monkeypatch.setattr(campaign_module, "run_single_case", fake_run_single_case)


def _patch_write_case_success(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, raise_for: frozenset[str] = frozenset()
) -> None:
    def fake_write_case_success(output_dir, result):
        recorder.success_calls.append(result.case_id)
        if result.case_id in raise_for:
            raise RuntimeError(f"write_case_success failed for {result.case_id}")

    monkeypatch.setattr(campaign_module, "write_case_success", fake_write_case_success)


def _patch_write_case_failure(
    monkeypatch: pytest.MonkeyPatch, recorder: _Recorder, *, raise_for: frozenset[str] = frozenset()
) -> None:
    def fake_write_case_failure(
        output_dir, case_id, *, campaign_id, manifest_fingerprint, repository_commit, run_status, errors
    ):
        recorder.failure_calls.append(
            dict(case_id=case_id, run_status=run_status, errors=list(errors), repository_commit=repository_commit)
        )
        if case_id in raise_for:
            raise RuntimeError(f"write_case_failure failed for {case_id}")

    monkeypatch.setattr(campaign_module, "write_case_failure", fake_write_case_failure)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    manifest: manifest_module.Manifest,
    tmp_path: Path,
    plan: tuple,
    *,
    valid_case_ids: frozenset[str] = frozenset(),
    raise_map: dict[str, BaseException] | None = None,
    success_raise_for: frozenset[str] = frozenset(),
    failure_raise_for: frozenset[str] = frozenset(),
    repository_commit: str = REPO_COMMIT,
) -> tuple[CampaignExecutionReport, _Recorder]:
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, plan)
    _patch_validate(monkeypatch, recorder, valid_case_ids=valid_case_ids)
    _patch_run_single_case(monkeypatch, recorder, raise_map=raise_map)
    _patch_write_case_success(monkeypatch, recorder, raise_for=success_raise_for)
    _patch_write_case_failure(monkeypatch, recorder, raise_for=failure_raise_for)
    report = run_campaign(manifest, output_dir=tmp_path, repository_commit=repository_commit)
    return report, recorder


# ---------------------------------------------------------------------------
# 1. build_campaign_plan called exactly once.
# ---------------------------------------------------------------------------


def test_build_campaign_plan_called_exactly_once(monkeypatch, manifest, tmp_path, two_cases) -> None:
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert recorder.build_plan_calls == 1


# ---------------------------------------------------------------------------
# 2. Exact plan order preserved; 25. outcome order == plan order.
# ---------------------------------------------------------------------------


def test_case_outcomes_preserve_plan_order(monkeypatch, manifest, tmp_path, three_cases) -> None:
    report, _ = _run(monkeypatch, manifest, tmp_path, three_cases)
    assert [outcome.case_id for outcome in report.case_outcomes] == [case.case_id for case in three_cases]


# ---------------------------------------------------------------------------
# 3. Signature accepts no free-form case list.
# ---------------------------------------------------------------------------


def test_run_campaign_signature_has_no_case_list_parameter() -> None:
    parameters = inspect.signature(run_campaign).parameters
    assert set(parameters) == {"manifest", "output_dir", "repository_commit"}
    assert parameters["output_dir"].kind == inspect.Parameter.KEYWORD_ONLY
    assert parameters["repository_commit"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# 4. All new -> all executed. 5. All valid -> all skipped_existing_valid,
# no runner/writer called. 6. Mixed skip/new. 7. Invalid existing run ->
# re-execution (implied: not in valid_case_ids).
# ---------------------------------------------------------------------------


def test_all_new_cases_are_all_executed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert [outcome.status for outcome in report.case_outcomes] == ["success", "success"]
    assert set(recorder.run_calls) == {case.case_id for case in two_cases}
    assert set(recorder.success_calls) == {case.case_id for case in two_cases}
    assert recorder.failure_calls == []


def test_all_valid_existing_runs_are_all_skipped(monkeypatch, manifest, tmp_path, two_cases) -> None:
    valid = frozenset(case.case_id for case in two_cases)
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=valid)
    assert [outcome.status for outcome in report.case_outcomes] == [
        "skipped_existing_valid",
        "skipped_existing_valid",
    ]
    assert recorder.run_calls == []
    assert recorder.success_calls == []
    assert recorder.failure_calls == []


def test_mixed_skip_and_new(monkeypatch, manifest, tmp_path, three_cases) -> None:
    valid = frozenset({three_cases[1].case_id})
    report, recorder = _run(monkeypatch, manifest, tmp_path, three_cases, valid_case_ids=valid)
    statuses = {outcome.case_id: outcome.status for outcome in report.case_outcomes}
    assert statuses[three_cases[0].case_id] == "success"
    assert statuses[three_cases[1].case_id] == "skipped_existing_valid"
    assert statuses[three_cases[2].case_id] == "success"
    assert recorder.run_calls == [three_cases[0].case_id, three_cases[2].case_id]


def test_invalid_existing_run_triggers_reexecution(monkeypatch, manifest, tmp_path, two_cases) -> None:
    # No case_id is in valid_case_ids -- validate_existing_case_run
    # returns is_valid=False for every case, as it would for a stale or
    # mismatched run.json.
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert recorder.run_calls == [case.case_id for case in two_cases]
    assert all(outcome.status == "success" for outcome in report.case_outcomes)


# ---------------------------------------------------------------------------
# 8/9. Success recorded only after write_case_success succeeds.
# ---------------------------------------------------------------------------


def test_success_status_only_after_write_case_success_called(monkeypatch, manifest, tmp_path, two_cases) -> None:
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert recorder.success_calls == [case.case_id for case in two_cases]


# ---------------------------------------------------------------------------
# 10. run_single_case failure -> failed. 11. write_case_success failure ->
# failed. 12. next case still executed after an ordinary failure.
# ---------------------------------------------------------------------------


def test_run_single_case_failure_yields_failed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    report, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing: RuntimeError("boom")})
    outcome = next(o for o in report.case_outcomes if o.case_id == failing)
    assert outcome.status == "failed"
    assert outcome.errors == ("RuntimeError: boom",)
    assert recorder.failure_calls[0]["run_status"] == "failed"
    assert recorder.success_calls == [two_cases[1].case_id]


def test_write_case_success_failure_yields_failed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    report, recorder = _run(
        monkeypatch, manifest, tmp_path, two_cases, success_raise_for=frozenset({failing})
    )
    outcome = next(o for o in report.case_outcomes if o.case_id == failing)
    assert outcome.status == "failed"
    assert recorder.failure_calls[0]["case_id"] == failing
    assert recorder.failure_calls[0]["run_status"] == "failed"


def test_next_case_executed_after_ordinary_failure(monkeypatch, manifest, tmp_path, three_cases) -> None:
    failing = three_cases[0].case_id
    report, recorder = _run(monkeypatch, manifest, tmp_path, three_cases, raise_map={failing: RuntimeError("x")})
    assert recorder.run_calls == [case.case_id for case in three_cases]
    statuses = {outcome.case_id: outcome.status for outcome in report.case_outcomes}
    assert statuses[three_cases[1].case_id] == "success"
    assert statuses[three_cases[2].case_id] == "success"


# ---------------------------------------------------------------------------
# 13. str(exc) == "" still yields a non-empty message.
# ---------------------------------------------------------------------------


class _BlankMessageError(RuntimeError):
    pass


def test_blank_exception_message_still_yields_non_empty_error(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    report, recorder = _run(
        monkeypatch, manifest, tmp_path, two_cases, raise_map={failing: _BlankMessageError()}
    )
    outcome = next(o for o in report.case_outcomes if o.case_id == failing)
    assert outcome.status == "failed"
    assert len(outcome.errors) == 1
    assert outcome.errors[0] == "_BlankMessageError"
    assert outcome.errors[0] != ""


# ---------------------------------------------------------------------------
# 14/17/18. Genuine guardrail exceedance -> resource_guardrail_exceeded,
# runner never called; max_dense < dim <= max_sparse is NOT an
# exceedance; force=True is never auto-classified as a guardrail.
# ---------------------------------------------------------------------------


def test_true_dimension_exceedance_yields_resource_guardrail_exceeded(
    monkeypatch, manifest, tmp_path, two_cases
) -> None:
    base = two_cases[0]
    oversized = dataclasses.replace(base, physical_dimension=base.spectrum_options.max_sparse_dimension + 1)
    plan = (oversized, two_cases[1])
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    outcome = next(o for o in report.case_outcomes if o.case_id == oversized.case_id)
    assert outcome.status == "resource_guardrail_exceeded"
    assert len(outcome.errors) == 1
    assert str(oversized.physical_dimension) in outcome.errors[0]
    assert str(oversized.spectrum_options.max_sparse_dimension) in outcome.errors[0]
    assert oversized.case_id not in recorder.run_calls
    assert recorder.failure_calls[0]["run_status"] == "resource_guardrail_exceeded"


def test_dimension_between_dense_and_sparse_is_not_an_exceedance(monkeypatch, manifest, tmp_path, two_cases) -> None:
    base = two_cases[0]
    assert base.spectrum_options.max_dense_dimension < base.spectrum_options.max_sparse_dimension
    mid_dimension = (base.spectrum_options.max_dense_dimension + base.spectrum_options.max_sparse_dimension) // 2
    case = dataclasses.replace(base, physical_dimension=mid_dimension)
    plan = (case,)
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    outcome = report.case_outcomes[0]
    assert outcome.status == "success"
    assert case.case_id in recorder.run_calls


def test_force_true_is_a_configuration_failure_not_a_guardrail(monkeypatch, manifest, tmp_path, two_cases) -> None:
    """force=True is the only value under which the physical_dimension
    pre-check is NOT equivalent to Level0's own guardrail behavior (see
    _exceeds_resource_guardrail's docstring) -- such a case must never
    be classified resource_guardrail_exceeded (no guardrail was actually
    evaluated) and must never reach run_single_case either; it is an
    ordinary campaign-configuration `failed`, exactly like any other
    pre-execution rejection."""
    base = two_cases[0]
    forced = dataclasses.replace(
        base,
        physical_dimension=base.spectrum_options.max_sparse_dimension + 1,
        spectrum_options=dataclasses.replace(base.spectrum_options, force=True),
    )
    plan = (forced,)
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    outcome = report.case_outcomes[0]
    assert outcome.status == "failed"
    assert outcome.status != "resource_guardrail_exceeded"
    assert len(outcome.errors) == 1
    assert "force=True" in outcome.errors[0]
    assert forced.case_id not in recorder.run_calls
    assert recorder.failure_calls == [
        dict(
            case_id=forced.case_id,
            run_status="failed",
            errors=[outcome.errors[0]],
            repository_commit=REPO_COMMIT,
        )
    ]


def test_force_true_with_dimension_within_sparse_bound_is_still_a_configuration_failure(
    monkeypatch, manifest, tmp_path, two_cases
) -> None:
    """The force=True rejection is unconditional on dimension -- a
    force=True case whose physical_dimension does NOT exceed
    max_sparse_dimension must still be rejected as `failed`, never
    silently allowed through to run_single_case."""
    base = two_cases[0]
    forced = dataclasses.replace(base, spectrum_options=dataclasses.replace(base.spectrum_options, force=True))
    assert forced.physical_dimension <= forced.spectrum_options.max_sparse_dimension
    plan = (forced,)
    report, recorder = _run(monkeypatch, manifest, tmp_path, plan)
    outcome = report.case_outcomes[0]
    assert outcome.status == "failed"
    assert forced.case_id not in recorder.run_calls


def test_force_true_write_case_failure_failure_propagates(monkeypatch, manifest, tmp_path, two_cases) -> None:
    base = two_cases[0]
    forced = dataclasses.replace(base, spectrum_options=dataclasses.replace(base.spectrum_options, force=True))
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, (forced,))
    _patch_validate(monkeypatch, recorder)
    _patch_run_single_case(monkeypatch, recorder)
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder, raise_for=frozenset({forced.case_id}))
    with pytest.raises(RuntimeError, match="write_case_failure failed"):
        run_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)
    assert recorder.run_calls == []


# ---------------------------------------------------------------------------
# 16. No exception-message parsing to classify a guardrail: an exception
# whose text mentions the guardrail wording, on a case whose dimension
# does NOT actually exceed the threshold, must still be "failed".
# ---------------------------------------------------------------------------


def test_guardrail_wording_in_exception_message_is_never_parsed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    case = two_cases[0]
    assert case.physical_dimension <= case.spectrum_options.max_sparse_dimension
    misleading = RuntimeError(
        f"dimension {case.physical_dimension} exceeds max_sparse_dimension={case.spectrum_options.max_sparse_dimension}"
    )
    report, recorder = _run(monkeypatch, manifest, tmp_path, (case,), raise_map={case.case_id: misleading})
    outcome = report.case_outcomes[0]
    assert outcome.status == "failed"
    assert recorder.failure_calls[0]["run_status"] == "failed"


# ---------------------------------------------------------------------------
# 19. write_case_failure failure is propagated and aborts run_campaign --
# both for an ordinary failure and for a guardrail exceedance.
# ---------------------------------------------------------------------------


def test_write_case_failure_failure_propagates_for_ordinary_failure(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, two_cases)
    _patch_validate(monkeypatch, recorder)
    _patch_run_single_case(monkeypatch, recorder, raise_map={failing: RuntimeError("boom")})
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder, raise_for=frozenset({failing}))
    with pytest.raises(RuntimeError, match="write_case_failure failed"):
        run_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)


def test_write_case_failure_failure_propagates_for_guardrail(monkeypatch, manifest, tmp_path, two_cases) -> None:
    base = two_cases[0]
    oversized = dataclasses.replace(base, physical_dimension=base.spectrum_options.max_sparse_dimension + 1)
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, (oversized,))
    _patch_validate(monkeypatch, recorder)
    _patch_run_single_case(monkeypatch, recorder)
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder, raise_for=frozenset({oversized.case_id}))
    with pytest.raises(RuntimeError, match="write_case_failure failed"):
        run_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 20/21. KeyboardInterrupt / SystemExit are never swallowed.
# ---------------------------------------------------------------------------


def test_keyboard_interrupt_is_not_swallowed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, two_cases)
    _patch_validate(monkeypatch, recorder)
    _patch_run_single_case(monkeypatch, recorder, raise_map={failing: KeyboardInterrupt()})
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder)
    with pytest.raises(KeyboardInterrupt):
        run_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)
    assert recorder.failure_calls == []


def test_system_exit_is_not_swallowed(monkeypatch, manifest, tmp_path, two_cases) -> None:
    failing = two_cases[0].case_id
    recorder = _Recorder()
    _patch_plan(monkeypatch, recorder, two_cases)
    _patch_validate(monkeypatch, recorder)
    _patch_run_single_case(monkeypatch, recorder, raise_map={failing: SystemExit(1)})
    _patch_write_case_success(monkeypatch, recorder)
    _patch_write_case_failure(monkeypatch, recorder)
    with pytest.raises(SystemExit):
        run_campaign(manifest, output_dir=tmp_path, repository_commit=REPO_COMMIT)
    assert recorder.failure_calls == []


# ---------------------------------------------------------------------------
# 22/23/24. Exact global counters; CampaignExecutionReport invariants.
# ---------------------------------------------------------------------------


def test_global_counters_are_exact(monkeypatch, manifest, tmp_path, three_cases) -> None:
    valid = frozenset({three_cases[1].case_id})
    failing = three_cases[2].case_id
    report, _ = _run(monkeypatch, manifest, tmp_path, three_cases, valid_case_ids=valid, raise_map={failing: RuntimeError("x")})
    assert report.total_required == 3
    assert report.executed_success_count == 1
    assert report.reused_success_count == 1
    assert report.failed_count == 1
    assert report.resource_guardrail_exceeded_count == 0
    assert report.global_success is False


def test_campaign_execution_report_rejects_inconsistent_counters() -> None:
    outcomes = (CaseOrchestrationOutcome(case_id="a", status="success", errors=()),)
    with pytest.raises(ValueError):
        CampaignExecutionReport(
            case_outcomes=outcomes,
            total_required=1,
            executed_success_count=0,  # wrong: should be 1
            reused_success_count=0,
            resource_guardrail_exceeded_count=0,
            failed_count=0,
            global_success=True,
        )


def test_campaign_execution_report_rejects_wrong_global_success() -> None:
    outcomes = (CaseOrchestrationOutcome(case_id="a", status="failed", errors=("boom",)),)
    with pytest.raises(ValueError):
        CampaignExecutionReport(
            case_outcomes=outcomes,
            total_required=1,
            executed_success_count=0,
            reused_success_count=0,
            resource_guardrail_exceeded_count=0,
            failed_count=1,
            global_success=True,  # wrong: must be False
        )


def test_case_orchestration_outcome_rejects_errors_for_success() -> None:
    with pytest.raises(ValueError):
        CaseOrchestrationOutcome(case_id="a", status="success", errors=("unexpected",))


def test_case_orchestration_outcome_rejects_missing_errors_for_failure() -> None:
    with pytest.raises(ValueError):
        CaseOrchestrationOutcome(case_id="a", status="failed", errors=())


def test_case_orchestration_outcome_rejects_unknown_status() -> None:
    with pytest.raises(ValueError):
        CaseOrchestrationOutcome(case_id="a", status="running", errors=())


def test_case_orchestration_statuses_are_exactly_the_frozen_taxonomy() -> None:
    assert CASE_ORCHESTRATION_STATUSES == (
        "success",
        "skipped_existing_valid",
        "resource_guardrail_exceeded",
        "failed",
    )


# ---------------------------------------------------------------------------
# 16 (b) / 24. global_success True only when every outcome is
# success/skipped.
# ---------------------------------------------------------------------------


def test_global_success_true_only_when_all_success_or_skipped(monkeypatch, manifest, tmp_path, two_cases) -> None:
    valid = frozenset({two_cases[0].case_id})
    report, _ = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=valid)
    assert report.global_success is True

    failing = two_cases[1].case_id
    report_with_failure, _ = _run(monkeypatch, manifest, tmp_path, two_cases, raise_map={failing: RuntimeError("x")})
    assert report_with_failure.global_success is False


# ---------------------------------------------------------------------------
# 26/27. Different repository_commit / manifest_fingerprint are forwarded
# unmodified to validate_existing_case_run (invalidating reuse is
# validate_existing_case_run's own responsibility, already tested in
# test_outputs.py -- this suite only verifies the orchestrator passes the
# real values through, never substituting or omitting one).
# ---------------------------------------------------------------------------


def test_repository_commit_is_forwarded_exactly(monkeypatch, manifest, tmp_path, two_cases) -> None:
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, repository_commit="e" * 40)
    assert all(call["repository_commit"] == "e" * 40 for call in recorder.validate_calls)


def test_manifest_fingerprint_is_forwarded_exactly(monkeypatch, manifest, tmp_path, two_cases) -> None:
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases)
    assert all(call["manifest_fingerprint"] == manifest.fingerprint for call in recorder.validate_calls)
    assert all(call["campaign_id"] == manifest.campaign_id for call in recorder.validate_calls)


def test_repository_commit_must_be_non_empty(manifest, tmp_path) -> None:
    with pytest.raises(ValueError):
        run_campaign(manifest, output_dir=tmp_path, repository_commit="")


# ---------------------------------------------------------------------------
# 28. No existing valid file is ever rewritten on a skip -- write_case_
# success/write_case_failure are simply never called for a skipped case.
# ---------------------------------------------------------------------------


def test_skip_never_calls_a_writer(monkeypatch, manifest, tmp_path, two_cases) -> None:
    valid = frozenset(case.case_id for case in two_cases)
    _, recorder = _run(monkeypatch, manifest, tmp_path, two_cases, valid_case_ids=valid)
    assert recorder.success_calls == []
    assert recorder.failure_calls == []


# ---------------------------------------------------------------------------
# check_repository_cleanliness (29-34).
# ---------------------------------------------------------------------------


def _init_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
    # Every normative directory already exists and holds a tracked file --
    # mirrors the real repository, where none of these directories is
    # ever entirely untracked, so a newly added file inside one always
    # shows up under its own full path rather than a collapsed directory
    # entry.
    for relative in (
        "src/placeholder.py",
        "docs/placeholder.md",
        "schemas/placeholder.json",
        "experiments/placeholder.py",
        "scripts/placeholder.py",
        "archive/placeholder.py",
        "archive/other.py",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_root, check=True)


def test_check_repository_cleanliness_on_clean_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is True
    assert dirty_paths == ()


def test_check_repository_cleanliness_detects_tracked_modification_under_src(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "src" / "placeholder.py").write_text("changed\n", encoding="utf-8")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is False
    assert "src/placeholder.py" in dirty_paths


def test_check_repository_cleanliness_detects_untracked_under_scripts(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "new_file.py").write_text("x\n", encoding="utf-8")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is False
    assert "scripts/new_file.py" in dirty_paths


def test_check_repository_cleanliness_ignores_root_results_directory(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "old_output.json").write_text("{}\n", encoding="utf-8")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is True
    assert dirty_paths == ()


def test_check_repository_cleanliness_returns_deterministic_order(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "scripts" / "z_new.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "z_new.py").write_text("z\n", encoding="utf-8")
    (tmp_path / "docs" / "a_new.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "a_new.md").write_text("a\n", encoding="utf-8")
    _, dirty_paths = check_repository_cleanliness(tmp_path)
    assert dirty_paths == tuple(sorted(dirty_paths))
    assert list(dirty_paths) == sorted(["scripts/z_new.py", "docs/a_new.md"])


def _git_mv(repo_root: Path, source: str, destination: str) -> None:
    destination_path = repo_root / destination
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "mv", source, destination], cwd=repo_root, check=True)


def test_check_repository_cleanliness_detects_rename_out_of_normative_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git_mv(tmp_path, "src/placeholder.py", "archive/placeholder_moved.py")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is False
    assert "src/placeholder.py" in dirty_paths


def test_check_repository_cleanliness_detects_rename_into_normative_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git_mv(tmp_path, "archive/placeholder.py", "src/placeholder_moved.py")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is False
    assert "src/placeholder_moved.py" in dirty_paths


def test_check_repository_cleanliness_ignores_rename_entirely_outside_normative_paths(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git_mv(tmp_path, "archive/placeholder.py", "archive/placeholder_moved.py")
    is_clean, dirty_paths = check_repository_cleanliness(tmp_path)
    assert is_clean is True
    assert dirty_paths == ()


def test_check_repository_cleanliness_rename_order_is_deterministic(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git_mv(tmp_path, "src/placeholder.py", "archive/z_moved.py")
    _git_mv(tmp_path, "archive/other.py", "docs/a_moved.py")
    _, dirty_paths = check_repository_cleanliness(tmp_path)
    assert dirty_paths == tuple(sorted(dirty_paths))
    assert list(dirty_paths) == sorted(["src/placeholder.py", "docs/a_moved.py"])


def test_check_repository_cleanliness_never_mutates_git_state(monkeypatch, tmp_path: Path) -> None:
    _init_repo(tmp_path)
    calls: list[list[str]] = []
    real_run = subprocess.run

    def spying_run(command, *args, **kwargs):
        calls.append(list(command))
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(campaign_module.subprocess, "run", spying_run)
    check_repository_cleanliness(tmp_path)
    assert calls == [["git", "status", "--porcelain"]]
    for command in calls:
        assert command[:2] not in (["git", "reset"], ["git", "clean"], ["git", "stash"], ["git", "checkout"])


# ---------------------------------------------------------------------------
# 35. No inter-S production/aggregation, no cross-case physical payload
# reading -- checked both structurally (forbidden identifiers absent from
# the module source) and behaviorally (run_campaign never touches
# load_case_records or a document's payload; the fakes above never
# expose one).
# ---------------------------------------------------------------------------


def test_campaign_module_imports_no_inter_s_or_payload_reading_symbol() -> None:
    """run_campaign never reads a document's physical payload nor
    produces an inter-S quantity -- checked at the import level (its own
    import statements are the exhaustive list of what it can possibly
    call), not by forbidding the word in explanatory prose (the module's
    own docstring legitimately explains what it does NOT do, exactly
    like runner.py's docstring does)."""
    source = inspect.getsource(campaign_module)
    import_lines = "\n".join(
        line for line in source.splitlines() if line.startswith("import ") or line.startswith("from ")
    )
    for token in _FORBIDDEN_IMPORT_TOKENS:
        assert token not in import_lines


def test_run_campaign_does_not_call_check_repository_cleanliness(monkeypatch, manifest, tmp_path, two_cases) -> None:
    called = []
    monkeypatch.setattr(campaign_module, "check_repository_cleanliness", lambda repo_root: called.append(repo_root))
    _run(monkeypatch, manifest, tmp_path, two_cases)
    assert called == []
