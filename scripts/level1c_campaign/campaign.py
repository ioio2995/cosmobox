"""PHASE_P multi-case campaign loop with resume, for the Level1C
normative campaign. Lot 1C-8h.

run_level1c_campaign executes the manifest's full deterministic plan
(experiments.level1c.planning.build_level1c_campaign_plan), case by
case, in plan order, reusing exclusively the already-accepted
single-case and persistence primitives -- runner.run_level1c_case
(1C-8c) and outputs.validate_existing_level1c_case_run/write_case_
success/write_case_failure (1C-8c/1C-8h) -- unmodified. It introduces
no new scientific logic: it never diagonalizes, computes an observable,
or reads a document's physical payload itself; it only decides, per
case, whether to skip (valid existing run), reject on a resource
guardrail, execute, or record an isolated technical failure, and
aggregates the outcomes into an in-memory Level1CCampaignExecutionReport
-- never persisted to disk (no campaign-wide file is ever written by
this module).

This is PHASE_P only: no baseline non-regression gate, no tracking, no
response, no PHASE_G, and no git/branch/worktree precondition checks --
those belong to a future normative launcher, never opened here. This
module never launches a real campaign against the 20 real cases; it is
exercised only against synthetic fixtures in tests/scripts/
level1c_campaign/.

global_success below is a purely TECHNICAL summary (no case suffered a
technical execution failure) -- it never means NORMATIVE_CAMPAIGN_VALID
(a distinct, not-yet-implemented concept belonging to a future
orchestration lot, itself gated by the baseline non-regression gate,
never by this module).

CaseOrchestrationOutcome/CampaignExecutionReport (scripts.level1b_
campaign.campaign) are reused only as an engineering PATTERN, never by
direct cross-package import: they are small, purely generic dataclasses
carrying no Level1B-specific content, but scripts.level1c_campaign is a
separate package -- the same reasoning already documented in outputs.py
for _atomic_write_bytes applies identically here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.level1c.manifest import Level1CManifest
from experiments.level1c.planning import build_level1c_campaign_plan

from .outputs import validate_existing_level1c_case_run, write_case_failure, write_case_success
from .runner import run_level1c_case

CASE_ORCHESTRATION_STATUSES = (
    "success",
    "skipped_existing_valid",
    "resource_guardrail_exceeded",
    "failed",
)

_NON_ERROR_STATUSES = ("success", "skipped_existing_valid")
_ERROR_STATUSES = ("resource_guardrail_exceeded", "failed")


@dataclass(frozen=True, slots=True)
class Level1CCaseOrchestrationOutcome:
    """The orchestration-level outcome of exactly one planned Level1C
    case. `status` is one of CASE_ORCHESTRATION_STATUSES -- a strictly
    closed taxonomy, never a free-form string. `errors` is empty for
    `success`/`skipped_existing_valid` (nothing went wrong), and
    non-empty for `resource_guardrail_exceeded`/`failed` (there is
    always at least one concrete reason). This is purely a TECHNICAL
    outcome: it never reflects normative_case_valid, which belongs to
    the persisted run.json artifact itself, never to this in-memory
    report."""

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
class Level1CCampaignExecutionReport:
    """The full, in-memory result of one run_level1c_campaign
    invocation. `case_outcomes` preserves build_level1c_campaign_plan
    (manifest)'s own order exactly -- no additional sort. Every counter
    is re-verified here against case_outcomes itself in __post_init__,
    so a caller can trust the counters without recomputing them. Never
    persisted to disk by this module -- no campaign-wide artifact/schema
    exists for it."""

    case_outcomes: tuple[Level1CCaseOrchestrationOutcome, ...]
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
                f"{_NON_ERROR_STATUSES} for outcome in case_outcomes) ({expected_global_success}) -- "
                "global_success is a purely technical summary, never NORMATIVE_CAMPAIGN_VALID"
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
    max_sparse_dimension is never diagonalized. Defensive only: for the
    real 20-case Level1C grid every physical_dimension (max 1504,
    ring5/S=3) is far below max_sparse_dimension (200000), so this path
    is never expected to trigger against the real manifest -- kept for
    robustness against any future manifest change, mirroring
    scripts.level1b_campaign.campaign's own identical guardrail."""
    return case.physical_dimension > case.spectrum_options.max_sparse_dimension


def run_level1c_campaign(
    manifest: Level1CManifest,
    *,
    output_dir: Path,
    repository_commit: str,
) -> Level1CCampaignExecutionReport:
    """Execute the manifest's full deterministic plan, case by case, in
    exactly build_level1c_campaign_plan(manifest)'s own order -- no
    additional sort, no ad hoc/free-form case list accepted. For each
    case: reuse a valid existing run if one exists (validate_existing_
    level1c_case_run, never re-running, never rewriting it, regardless
    of normative_case_valid); otherwise pre-check the resource guardrail
    using already-known plan data (never calling run_level1c_case for an
    oversized case); otherwise execute normally, persisting success only
    after both run_level1c_case and write_case_success succeed, and
    isolating an ordinary Exception as a `failed` outcome for this case
    only, continuing with the next case. A failure while persisting the
    `failed`/`resource_guardrail_exceeded` marker itself is never
    swallowed -- it propagates and aborts run_level1c_campaign, since the
    case's durable state is no longer guaranteed. Never
    `except BaseException`: KeyboardInterrupt and SystemExit always
    propagate.
    """
    if not repository_commit:
        raise ValueError("repository_commit must be non-empty")

    plan = build_level1c_campaign_plan(manifest)

    outcomes: list[Level1CCaseOrchestrationOutcome] = []
    for case in plan:
        validation = validate_existing_level1c_case_run(
            output_dir, case.case_id, level1c_manifest=manifest, repository_commit=repository_commit
        )
        if validation.is_valid:
            outcomes.append(Level1CCaseOrchestrationOutcome(case_id=case.case_id, status="skipped_existing_valid", errors=()))
            continue

        if _exceeds_resource_guardrail(case):
            message = (
                f"physical_dimension ({case.physical_dimension}) exceeds max_sparse_dimension "
                f"({case.spectrum_options.max_sparse_dimension})"
            )
            write_case_failure(
                output_dir,
                manifest,
                case,
                repository_commit=repository_commit,
                run_status="resource_guardrail_exceeded",
            )
            outcomes.append(
                Level1CCaseOrchestrationOutcome(case_id=case.case_id, status="resource_guardrail_exceeded", errors=(message,))
            )
            continue

        try:
            result = run_level1c_case(manifest, case, repository_commit=repository_commit)
            write_case_success(output_dir, manifest, case, result, repository_commit=repository_commit)
        except Exception as exc:  # noqa: BLE001 -- one bad case must not abort the whole campaign
            message = _exception_message(exc)
            # Not caught: if this itself raises, the case's durable state
            # is no longer guaranteed -- run_level1c_campaign must abort
            # rather than report a status it cannot actually promise on
            # disk.
            write_case_failure(
                output_dir,
                manifest,
                case,
                repository_commit=repository_commit,
                run_status="failed",
            )
            outcomes.append(Level1CCaseOrchestrationOutcome(case_id=case.case_id, status="failed", errors=(message,)))
            continue

        outcomes.append(Level1CCaseOrchestrationOutcome(case_id=case.case_id, status="success", errors=()))

    executed_success_count = sum(1 for outcome in outcomes if outcome.status == "success")
    reused_success_count = sum(1 for outcome in outcomes if outcome.status == "skipped_existing_valid")
    resource_guardrail_exceeded_count = sum(1 for outcome in outcomes if outcome.status == "resource_guardrail_exceeded")
    failed_count = sum(1 for outcome in outcomes if outcome.status == "failed")
    global_success = all(outcome.status in _NON_ERROR_STATUSES for outcome in outcomes)

    return Level1CCampaignExecutionReport(
        case_outcomes=tuple(outcomes),
        total_required=len(outcomes),
        executed_success_count=executed_success_count,
        reused_success_count=reused_success_count,
        resource_guardrail_exceeded_count=resource_guardrail_exceeded_count,
        failed_count=failed_count,
        global_success=global_success,
    )
