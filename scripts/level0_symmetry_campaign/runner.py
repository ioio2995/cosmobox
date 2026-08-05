"""Resumable execution of the Level0 symmetry-diagnostics campaign (6C)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from cosmobox.level0 import compute_config_fingerprint

from .analysis import run_symmetry_experiment, symmetry_experiment_result_to_json_dict
from .grid import SYMMETRY_CAMPAIGN_THRESHOLDS, SymmetryCampaignExperimentSpec, spec_to_experiment
from .outputs import CampaignRunRecord, atomic_write_text, validate_existing_run, write_manifest, write_summary_csv

CAMPAIGN_PROTOCOL_VERSION = 1


def run_campaign(
    specs: Sequence[SymmetryCampaignExperimentSpec],
    output_dir: Path,
    *,
    stop_on_error: bool = False,
    overwrite_invalid: bool = False,
) -> tuple[CampaignRunRecord, ...]:
    """Run (or resume) the campaign. Never raises on a single bad experiment
    unless stop_on_error=True -- an unexpected exception (including a
    consistency-check failure from analysis._check_commutator_restriction_consistency)
    becomes a run_status="error" record and the campaign moves on.

    The validity thresholds are pre-registered in manifest.json before any
    experiment runs (a write with an empty records list), not only once the
    first result is available.
    """
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()

    write_manifest(
        output_dir / "manifest.json",
        protocol_version=CAMPAIGN_PROTOCOL_VERSION,
        expected_runs=len(specs),
        started_at=started_at,
        thresholds=SYMMETRY_CAMPAIGN_THRESHOLDS,
        records=(),
    )

    records: list[CampaignRunRecord] = []
    run_jsons: list[dict | None] = []

    for spec in specs:
        config = spec_to_experiment(spec)
        fingerprint = compute_config_fingerprint(config)
        run_path = runs_dir / f"{fingerprint}.json"

        is_valid, reason = validate_existing_run(run_path, spec, fingerprint)

        if is_valid:
            run_json = json.loads(run_path.read_text(encoding="utf-8"))
            record = CampaignRunRecord(
                experiment_id=spec.experiment_id,
                roles=spec.roles,
                config_fingerprint=fingerprint,
                run_status="skipped",
                spectrum_status=run_json["report"]["spectrum"]["status"],
                error_message=None,
            )
        elif run_path.exists() and not overwrite_invalid:
            run_json = None
            record = CampaignRunRecord(
                experiment_id=spec.experiment_id,
                roles=spec.roles,
                config_fingerprint=fingerprint,
                run_status="error",
                spectrum_status=None,
                error_message=f"existing run file is invalid and overwrite_invalid=False: {reason}",
            )
        else:
            try:
                result = run_symmetry_experiment(config)
                run_json = symmetry_experiment_result_to_json_dict(result)
                text = json.dumps(run_json, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
                atomic_write_text(run_path, text)
                record = CampaignRunRecord(
                    experiment_id=spec.experiment_id,
                    roles=spec.roles,
                    config_fingerprint=fingerprint,
                    run_status="success",
                    spectrum_status=result.base.report.spectrum.status,
                    error_message=None,
                )
            except Exception as exc:  # noqa: BLE001 -- one bad run must not abort the whole campaign
                run_json = None
                record = CampaignRunRecord(
                    experiment_id=spec.experiment_id,
                    roles=spec.roles,
                    config_fingerprint=fingerprint,
                    run_status="error",
                    spectrum_status=None,
                    error_message=str(exc),
                )

        records.append(record)
        run_jsons.append(run_json)

        write_manifest(
            output_dir / "manifest.json",
            protocol_version=CAMPAIGN_PROTOCOL_VERSION,
            expected_runs=len(specs),
            started_at=started_at,
            thresholds=SYMMETRY_CAMPAIGN_THRESHOLDS,
            records=records,
        )
        write_summary_csv(
            output_dir / "summary.csv",
            list(zip(specs[: len(records)], records, run_jsons)),
        )

        if stop_on_error and record.run_status == "error":
            break

    return tuple(records)
