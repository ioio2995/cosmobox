"""CLI entry point for the normative Level1C campaign launch (lot
1C-8j). Thin wrapper only -- all normative logic (precondition
verification, orchestration of P -> BASELINE_NON_REGRESSION_GATE ->
T -> R) lives in scripts/level1c_launcher/launch.py; this file is only
argument parsing and the call into launch_normative_campaign.

Run from the repository root as a module, so `scripts` resolves as a
package:

    python -m scripts.run_level1c_campaign \
        --output-dir results/level1c/campaign \
        --historical-output-dir /workspaces/level1b_campaign_output

Deliberately accepts no --repository-commit, --manifest-path, --branch,
--force, or repository-cleanliness override, and no J0/S/target/
production_window/threshold override of any kind: the only ways to
influence what gets launched are --output-dir, --historical-output-dir
(both operational file locations, never scientific parameters), and
--repo-root (for testing).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.level1c_launcher.launch import (
    COMPLETED,
    NormativeLaunchError,
    STOP_BEFORE_GATE,
    STOP_NORMATIVE_PIPELINE_BEFORE_T,
    launch_normative_campaign,
)

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory under which runs/<case_id>/{records.jsonl,run.json}, baseline-nonregression.json, "
        "tracking.jsonl, and response.jsonl are written",
    )
    parser.add_argument(
        "--historical-output-dir",
        type=Path,
        required=True,
        help="path to the already-produced Level1B historical corpus consulted by the baseline non-regression "
        "gate -- an operational file location, never a scientific parameter",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_DEFAULT_REPO_ROOT,
        help="repository root (default: derived from this script's own location, not the cwd)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        report = launch_normative_campaign(
            args.repo_root, output_dir=args.output_dir, historical_output_dir=args.historical_output_dir
        )
    except NormativeLaunchError as exc:
        print(f"normative launch precondition failed: {exc}")
        return 2

    print(f"pipeline_status={report.pipeline_status}")
    print(
        f"phase_p: total_required={report.phase_p_report.total_required} "
        f"executed_success_count={report.phase_p_report.executed_success_count} "
        f"reused_success_count={report.phase_p_report.reused_success_count} "
        f"resource_guardrail_exceeded_count={report.phase_p_report.resource_guardrail_exceeded_count} "
        f"failed_count={report.phase_p_report.failed_count} "
        f"global_success={report.phase_p_report.global_success}"
    )
    if report.gate_artifact is not None:
        print(f"gate_status={report.gate_artifact.gate_status}")
    if report.tracking_records is not None:
        print(f"tracking_records={len(report.tracking_records)}")
    if report.response_records is not None:
        print(f"response_records={len(report.response_records)}")

    if report.pipeline_status == COMPLETED:
        return 0
    if report.pipeline_status in (STOP_BEFORE_GATE, STOP_NORMATIVE_PIPELINE_BEFORE_T):
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
