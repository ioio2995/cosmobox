"""CLI entry point for the normative Level1B campaign launch (lot
1B-8e). Thin wrapper only -- all normative logic (precondition
verification, resume, execution) lives in
scripts/level1b_campaign/launch.py and campaign.py; this file is only
argument parsing and the call into launch_normative_campaign.

Run from the repository root as a module, so `scripts` resolves as a
package:

    python -m scripts.run_level1b_campaign --output-dir campaign_output

Deliberately accepts no --repository-commit, --manifest-path, --branch,
--force, or repository-cleanliness override: the only way to influence
what gets launched is --output-dir (and, for testing, --repo-root).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.level1b_campaign.launch import NormativeLaunchError, launch_normative_campaign

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory under which runs/<case_id>/{records.jsonl,run.json} are written",
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
        report = launch_normative_campaign(args.repo_root, output_dir=args.output_dir)
    except NormativeLaunchError as exc:
        print(f"normative launch precondition failed: {exc}")
        return 2

    print(
        f"total_required={report.total_required} "
        f"executed_success_count={report.executed_success_count} "
        f"reused_success_count={report.reused_success_count} "
        f"resource_guardrail_exceeded_count={report.resource_guardrail_exceeded_count} "
        f"failed_count={report.failed_count} "
        f"global_success={report.global_success}"
    )
    return 0 if report.global_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
