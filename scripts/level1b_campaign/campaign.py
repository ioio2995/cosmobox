"""Multi-case campaign orchestration with resume, for the Level1B
campaign. Level1B lot 1B-8d (docs/governance/current-task.md).

run_campaign executes the manifest's full deterministic plan
(experiments.level1.planning.build_campaign_plan), case by case, in
plan order, reusing exclusively the already-accepted single-case and
persistence primitives -- runner.run_single_case (lot 1B-8) and
outputs.validate_existing_case_run/write_case_success/write_case_failure
(lot 1B-8c) -- unmodified. It introduces no new scientific logic: it
never diagonalizes, computes an observable, or reads a document's
physical payload; it only decides, per case, whether to skip (valid
existing run), reject on a resource guardrail, execute, or record an
isolated failure, and aggregates the outcomes into an in-memory
CampaignExecutionReport.

Resource guardrail: Level0 (cosmobox.level0.reports._compute_spectrum)
never raises for a dimension exceeding max_sparse_dimension when
force=False -- it returns SpectrumReport(status="not_computed", ...).
runner.run_single_case does not itself check spectrum.status before
dereferencing spectrum.degeneracy.groups, so calling it directly on an
oversized case would raise an undifferentiated AttributeError, not a
clean, classifiable signal. This orchestrator therefore never relies on
catching a Level0 exception or parsing its message: it pre-checks the
same condition Level0 itself would apply -- case.physical_dimension
against case.spectrum_options.max_sparse_dimension, with
case.spectrum_options.force required to be False (the only value
planning.py ever produces) -- using data already known from the plan,
strictly before ever calling run_single_case. If force is not False for
some case, this is treated as an ordinary campaign-configuration failure,
never assumed to be an equivalent guardrail.

This lot performs no inter-S aggregation, no gamma_O, no robustness
verdict, no G_occ, no path_phase_coherence, and reads no physical
payload from any document to compare cases -- see
docs/governance/current-task.md for the exact authorized scope. It
writes no campaign-wide file: CampaignExecutionReport is an in-memory
object only, and the only durable outputs remain the per-case
runs/<case_id>/{records.jsonl,run.json} artifacts already defined by
lot 1B-8c.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from experiments.level1.manifest import Manifest
from experiments.level1.planning import build_campaign_plan

from .outputs import validate_existing_case_run, write_case_failure, write_case_success
from .runner import run_single_case

CASE_ORCHESTRATION_STATUSES = (
    "success",
    "skipped_existing_valid",
    "resource_guardrail_exceeded",
    "failed",
)

_NON_ERROR_STATUSES = ("success", "skipped_existing_valid")
_ERROR_STATUSES = ("resource_guardrail_exceeded", "failed")

_CLEANLINESS_PATHS = ("src/", "docs/", "schemas/", "experiments/", "scripts/")


@dataclass(frozen=True, slots=True)
class CaseOrchestrationOutcome:
    """The orchestration-level outcome of exactly one planned case.
    `status` is one of CASE_ORCHESTRATION_STATUSES -- a strictly closed
    taxonomy, never a free-form string. `errors` is empty for `success`
    and `skipped_existing_valid` (nothing went wrong), and non-empty for
    `resource_guardrail_exceeded`/`failed` (there is always at least one
    concrete reason)."""

    case_id: str
    status: str
    errors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if self.status not in CASE_ORCHESTRATION_STATUSES:
            raise ValueError(f"status must be one of {CASE_ORCHESTRATION_STATUSES}, got {self.status!r}")
        if self.status in _NON_ERROR_STATUSES and self.errors != ():
            raise ValueError(f"errors must be empty for status {self.status!r}, got {self.errors!r}")
        if self.status in _ERROR_STATUSES and not self.errors:
            raise ValueError(f"errors must be non-empty for status {self.status!r}")
        for error in self.errors:
            if not isinstance(error, str) or not error:
                raise ValueError(f"each error must be a non-empty string, got {error!r}")


@dataclass(frozen=True, slots=True)
class CampaignExecutionReport:
    """The full, in-memory result of one run_campaign invocation.
    case_outcomes preserves build_campaign_plan(manifest)'s own order
    exactly -- no additional sort. Every counter is re-verified here
    against case_outcomes itself in __post_init__, so a caller can trust
    the counters without recomputing them."""

    case_outcomes: tuple[CaseOrchestrationOutcome, ...]
    total_required: int
    executed_success_count: int
    reused_success_count: int
    resource_guardrail_exceeded_count: int
    failed_count: int
    global_success: bool

    def __post_init__(self) -> None:
        if self.total_required != len(self.case_outcomes):
            raise ValueError(
                f"total_required ({self.total_required}) does not match len(case_outcomes) "
                f"({len(self.case_outcomes)})"
            )
        case_ids = [outcome.case_id for outcome in self.case_outcomes]
        if len(case_ids) != len(set(case_ids)):
            duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
            raise ValueError(f"case_outcomes contains duplicate case_id(s): {duplicates}")

        for name, value in (
            ("executed_success_count", self.executed_success_count),
            ("reused_success_count", self.reused_success_count),
            ("resource_guardrail_exceeded_count", self.resource_guardrail_exceeded_count),
            ("failed_count", self.failed_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")

        counted_total = (
            self.executed_success_count
            + self.reused_success_count
            + self.resource_guardrail_exceeded_count
            + self.failed_count
        )
        if counted_total != self.total_required:
            raise ValueError(
                f"executed_success_count + reused_success_count + resource_guardrail_exceeded_count + "
                f"failed_count ({counted_total}) does not match total_required ({self.total_required})"
            )

        actual_executed_success = sum(1 for outcome in self.case_outcomes if outcome.status == "success")
        actual_reused_success = sum(1 for outcome in self.case_outcomes if outcome.status == "skipped_existing_valid")
        actual_guardrail = sum(1 for outcome in self.case_outcomes if outcome.status == "resource_guardrail_exceeded")
        actual_failed = sum(1 for outcome in self.case_outcomes if outcome.status == "failed")
        if actual_executed_success != self.executed_success_count:
            raise ValueError(
                f"executed_success_count ({self.executed_success_count}) does not match the number of "
                f"'success' outcomes ({actual_executed_success})"
            )
        if actual_reused_success != self.reused_success_count:
            raise ValueError(
                f"reused_success_count ({self.reused_success_count}) does not match the number of "
                f"'skipped_existing_valid' outcomes ({actual_reused_success})"
            )
        if actual_guardrail != self.resource_guardrail_exceeded_count:
            raise ValueError(
                f"resource_guardrail_exceeded_count ({self.resource_guardrail_exceeded_count}) does not match "
                f"the number of 'resource_guardrail_exceeded' outcomes ({actual_guardrail})"
            )
        if actual_failed != self.failed_count:
            raise ValueError(
                f"failed_count ({self.failed_count}) does not match the number of 'failed' outcomes "
                f"({actual_failed})"
            )

        expected_global_success = all(outcome.status in _NON_ERROR_STATUSES for outcome in self.case_outcomes)
        if self.global_success != expected_global_success:
            raise ValueError(
                f"global_success ({self.global_success}) does not match all(outcome.status in "
                f"{_NON_ERROR_STATUSES} for outcome in case_outcomes) ({expected_global_success})"
            )


def _exception_message(exc: Exception) -> str:
    """Always a non-empty string: some exceptions (e.g. a bare
    `raise SomeError()`) stringify to "" -- fall back to the exception's
    own type name so a persisted error is never blank."""
    detail = str(exc)
    if detail:
        return f"{type(exc).__name__}: {detail}"
    return type(exc).__name__


def _exceeds_resource_guardrail(case) -> bool:
    """The exact condition Level0 itself applies when
    spectrum_options.force is False: a dimension over
    max_sparse_dimension is never diagonalized. max_dense_dimension only
    selects dense vs sparse solving -- it is never itself a guardrail.
    Only equivalent to Level0's own behavior when force is False; the
    caller (run_campaign) must reject force=True cases as an ordinary
    configuration failure before ever reaching this check."""
    return case.physical_dimension > case.spectrum_options.max_sparse_dimension


def run_campaign(
    manifest: Manifest,
    *,
    output_dir: Path,
    repository_commit: str,
) -> CampaignExecutionReport:
    """Execute the manifest's full deterministic plan, case by case, in
    exactly build_campaign_plan(manifest)'s own order -- no additional
    sort, no ad hoc/free-form case list accepted (the only case source is
    the plan built from `manifest` itself). For each case: reuse a valid
    existing run if one exists (never re-running, never rewriting it);
    otherwise pre-check the resource guardrail using already-known plan
    data (never calling run_single_case for an oversized case); otherwise
    execute normally, persisting success only after both run_single_case
    and write_case_success succeed, and isolating an ordinary exception
    as a `failed` outcome for this case only, continuing with the next
    case. A failure while persisting the `failed`/`resource_guardrail_
    exceeded` marker itself is never swallowed -- it propagates and
    aborts run_campaign, since the case's durable state is no longer
    guaranteed. Never `except BaseException`: KeyboardInterrupt and
    SystemExit always propagate.
    """
    if not repository_commit:
        raise ValueError("repository_commit must be non-empty")

    plan = build_campaign_plan(manifest)

    outcomes: list[CaseOrchestrationOutcome] = []
    for case in plan:
        case_dir = output_dir / "runs" / case.case_id

        validation = validate_existing_case_run(
            case_dir,
            case_id=case.case_id,
            campaign_id=manifest.campaign_id,
            manifest_fingerprint=manifest.fingerprint,
            repository_commit=repository_commit,
        )
        if validation.is_valid:
            outcomes.append(CaseOrchestrationOutcome(case_id=case.case_id, status="skipped_existing_valid", errors=()))
            continue

        if case.spectrum_options.force is not False:
            # The dimensional pre-check below is only equivalent to
            # Level0's own guardrail when force is False (the only value
            # planning.py ever produces): with force=True, Level0 would
            # attempt sparse diagonalization regardless of dimension, so
            # this pre-check could no longer stand in for it. Rather than
            # silently reusing an inapplicable check, or forwarding to
            # run_single_case anyway, a force=True case is treated as a
            # campaign-configuration failure -- ordinary `failed`, never
            # `resource_guardrail_exceeded` (no guardrail was actually
            # evaluated), and run_single_case is never called for it.
            message = (
                f"case {case.case_id!r} has spectrum_options.force={case.spectrum_options.force!r}: "
                "force=True is incompatible with the normative 1B campaign plan (planning.py always "
                "produces force=False), so the resource-guardrail pre-check cannot stand in for Level0's "
                "own guardrail for this case"
            )
            write_case_failure(
                output_dir,
                case.case_id,
                campaign_id=manifest.campaign_id,
                manifest_fingerprint=manifest.fingerprint,
                repository_commit=repository_commit,
                run_status="failed",
                errors=[message],
            )
            outcomes.append(CaseOrchestrationOutcome(case_id=case.case_id, status="failed", errors=(message,)))
            continue

        if _exceeds_resource_guardrail(case):
            message = (
                f"physical_dimension ({case.physical_dimension}) exceeds max_sparse_dimension "
                f"({case.spectrum_options.max_sparse_dimension})"
            )
            write_case_failure(
                output_dir,
                case.case_id,
                campaign_id=manifest.campaign_id,
                manifest_fingerprint=manifest.fingerprint,
                repository_commit=repository_commit,
                run_status="resource_guardrail_exceeded",
                errors=[message],
            )
            outcomes.append(
                CaseOrchestrationOutcome(case_id=case.case_id, status="resource_guardrail_exceeded", errors=(message,))
            )
            continue

        try:
            result = run_single_case(manifest, case, repository_commit=repository_commit)
            write_case_success(output_dir, result)
        except Exception as exc:  # noqa: BLE001 -- one bad case must not abort the whole campaign
            message = _exception_message(exc)
            # Not caught: if this itself raises, the case's durable state
            # is no longer guaranteed -- run_campaign must abort rather
            # than report a status it cannot actually promise on disk.
            write_case_failure(
                output_dir,
                case.case_id,
                campaign_id=manifest.campaign_id,
                manifest_fingerprint=manifest.fingerprint,
                repository_commit=repository_commit,
                run_status="failed",
                errors=[message],
            )
            outcomes.append(CaseOrchestrationOutcome(case_id=case.case_id, status="failed", errors=(message,)))
            continue

        outcomes.append(CaseOrchestrationOutcome(case_id=case.case_id, status="success", errors=()))

    executed_success_count = sum(1 for outcome in outcomes if outcome.status == "success")
    reused_success_count = sum(1 for outcome in outcomes if outcome.status == "skipped_existing_valid")
    resource_guardrail_exceeded_count = sum(1 for outcome in outcomes if outcome.status == "resource_guardrail_exceeded")
    failed_count = sum(1 for outcome in outcomes if outcome.status == "failed")
    global_success = all(outcome.status in _NON_ERROR_STATUSES for outcome in outcomes)

    return CampaignExecutionReport(
        case_outcomes=tuple(outcomes),
        total_required=len(outcomes),
        executed_success_count=executed_success_count,
        reused_success_count=reused_success_count,
        resource_guardrail_exceeded_count=resource_guardrail_exceeded_count,
        failed_count=failed_count,
        global_success=global_success,
    )


def check_repository_cleanliness(repo_root: Path) -> tuple[bool, tuple[str, ...]]:
    """Whether the repository is clean under the normative campaign
    paths (src/, docs/, schemas/, experiments/, scripts/) -- any tracked
    modification or untracked file under those paths makes it unclean.
    The pre-existing, untracked root `results/` directory is deliberately
    outside this filter (it is not one of the normative paths); campaign
    outputs must never be written there regardless.

    Read-only: runs exactly `git status --porcelain` from `repo_root` and
    inspects its output. Never modifies, resets, cleans, or stashes
    anything. Returns (is_clean, dirty_paths) with dirty_paths sorted
    for a deterministic order.

    A future normative campaign-launching entry point MUST call this and
    refuse to launch if is_clean is False. run_campaign itself never
    calls this and exposes no parameter to bypass it -- it is not a
    precondition of run_campaign, so its own unit tests are never forced
    to run against a clean tree.
    """
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    dirty_paths: set[str] = set()
    for line in completed.stdout.splitlines():
        if not line:
            continue
        # `git status --porcelain` format: two status chars, a space, then
        # the path -- except a rename entry, which uses "old -> new" for
        # that trailing part. Both the source and the destination are
        # examined independently: a rename OUT of a normative path (e.g.
        # src/foo.py -> archive/foo.py) is exactly as much a change to a
        # normative path as a rename INTO one, so either side matching a
        # normative prefix makes the tree dirty.
        path = line[3:]
        if " -> " in path:
            source_path, destination_path = path.split(" -> ", 1)
            candidates = (source_path, destination_path)
        else:
            candidates = (path,)
        for candidate in candidates:
            if candidate.startswith(_CLEANLINESS_PATHS):
                dirty_paths.add(candidate)

    return (len(dirty_paths) == 0, tuple(sorted(dirty_paths)))
