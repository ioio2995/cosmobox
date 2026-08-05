"""CLI entry point for the Level0 symmetry-diagnostics campaign (6C).

Run from the repository root as a module, so `scripts` resolves as a
package:

    python -m scripts.run_level0_symmetry_campaign --output-dir symmetry_campaign_output

The importable pieces live in scripts/level0_symmetry_campaign/
(grid.py, analysis.py, outputs.py, runner.py); this file is only argument
parsing and the call into runner.run_campaign.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.level0_symmetry_campaign.grid import build_symmetry_campaign_specs
from scripts.level0_symmetry_campaign.runner import run_campaign


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("symmetry_campaign_output"),
        help="directory for runs/, manifest.json, summary.csv",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help='stop after the first run_status="error" (default: continue)'
    )
    parser.add_argument(
        "--overwrite-invalid",
        action="store_true",
        help="rerun and overwrite a run file that exists but does not match the expected configuration "
        "(default: report it as an error instead)",
    )
    args = parser.parse_args()

    specs = build_symmetry_campaign_specs()
    records = run_campaign(
        specs,
        args.output_dir,
        stop_on_error=args.stop_on_error,
        overwrite_invalid=args.overwrite_invalid,
    )

    counts: dict[str, int] = {}
    for record in records:
        counts[record.run_status] = counts.get(record.run_status, 0) + 1
    print(f"{len(records)}/{len(specs)} experiments processed: {counts}")


if __name__ == "__main__":
    main()
