"""Validation of existing run files, and atomic manifest/CSV writers."""

from __future__ import annotations

import csv
import io
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cosmobox.level0 import level0_experiment_config_to_json_dict
from cosmobox.level0.lattice import build_lattice

from .grid import CampaignExperimentSpec, spec_to_experiment

JSON_SCHEMA_VERSION = 1  # must track cosmobox.level0.experiments.JSON_SCHEMA_VERSION

SUMMARY_CSV_FIELDS: tuple[str, ...] = (
    "experiment_id",
    "config_fingerprint",
    "geometry",
    "spin",
    "J",
    "h_eta",
    "t",
    "g_E",
    "K",
    "dimension",
    "sector_count",
    "basis_build_seconds",
    "hamiltonian_build_seconds",
    "report_build_seconds",
    "spectrum_status",
    "spectrum_method",
    "computed_eigenvalues",
    "ground_energy",
    "first_excited_energy",
    "spectral_gap",
    "ground_dot_expectation",
    "ground_hopping_expectation",
    "ground_electric_expectation",
    "ground_magnetic_expectation",
    "ground_total_expectation",
    "ground_residual_norm",
    "total_nnz",
    "total_density",
    "total_hermiticity_defect",
    "n_sites",
    "n_edges",
    "n_plaquettes",
)


@dataclass(frozen=True, slots=True)
class CampaignRunRecord:
    experiment_id: str
    roles: tuple[str, ...]
    config_fingerprint: str
    run_status: str  # "success" | "skipped" | "error"
    spectrum_status: str | None
    error_message: str | None


def atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file in the same directory, then os.replace (atomic
    rename) -- the destination is never observed half-written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def validate_existing_run(
    path: Path, spec: CampaignExperimentSpec, expected_fingerprint: str
) -> tuple[bool, str | None]:
    """(is_valid, reason_if_invalid). Never raises on a missing/corrupt file."""
    if not path.exists():
        return False, "no existing run file"

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"could not parse existing run file: {exc}"

    if not isinstance(parsed, dict):
        return False, "existing run file does not contain a JSON object"

    if parsed.get("schema_version") != JSON_SCHEMA_VERSION:
        return False, f"unexpected schema_version {parsed.get('schema_version')!r}"

    if parsed.get("config_fingerprint") != expected_fingerprint:
        return False, "config_fingerprint in file does not match the expected fingerprint"

    expected_config = level0_experiment_config_to_json_dict(spec_to_experiment(spec))
    if parsed.get("config") != expected_config:
        return False, "config block in file does not match the expected configuration"

    return True, None


def write_manifest(
    path: Path,
    *,
    protocol_version: int,
    expected_runs: int,
    started_at: str,
    records: Sequence[CampaignRunRecord],
) -> None:
    payload = {
        "protocol_version": protocol_version,
        "expected_runs": expected_runs,
        "started_at": started_at,
        "runs": [
            {
                "experiment_id": record.experiment_id,
                "roles": list(record.roles),
                "config_fingerprint": record.config_fingerprint,
                "run_status": record.run_status,
                "spectrum_status": record.spectrum_status,
                "error_message": record.error_message,
            }
            for record in records
        ],
    }
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
    atomic_write_text(path, text)


def _summary_row(spec: CampaignExperimentSpec, record: CampaignRunRecord, run_json: dict | None) -> dict:
    lattice = build_lattice(spec.geometry)
    row: dict[str, object] = {name: "" for name in SUMMARY_CSV_FIELDS}
    row.update(
        {
            "experiment_id": spec.experiment_id,
            "config_fingerprint": record.config_fingerprint,
            "geometry": spec.geometry,
            "spin": spec.spin,
            "J": spec.J,
            "h_eta": spec.h_eta,
            "t": spec.t,
            "g_E": spec.g_E,
            "K": spec.K,
            "n_sites": len(lattice.nodes),
            "n_edges": len(lattice.edges),
            "n_plaquettes": len(lattice.plaquettes),
        }
    )

    if run_json is None:
        return row

    report = run_json["report"]
    timings = run_json["timings"]
    spectrum = report["spectrum"]

    row["dimension"] = report["dimension"]
    row["sector_count"] = report["sector_count"]
    row["basis_build_seconds"] = timings["basis_build_seconds"]
    row["hamiltonian_build_seconds"] = timings["hamiltonian_build_seconds"]
    row["report_build_seconds"] = timings["report_build_seconds"]
    row["spectrum_status"] = spectrum["status"]
    row["spectrum_method"] = spectrum["method"] if spectrum["method"] is not None else ""
    row["computed_eigenvalues"] = spectrum["computed_eigenvalues"]
    row["spectral_gap"] = spectrum["spectral_gap"] if spectrum["spectral_gap"] is not None else ""

    eigenpairs = spectrum["eigenpairs"]
    if len(eigenpairs) >= 1:
        ground = eigenpairs[0]
        row["ground_energy"] = ground["eigenvalue"]
        row["ground_residual_norm"] = ground["residual_norm"]
        expectations = ground["term_expectations"]
        row["ground_dot_expectation"] = expectations["dot"]
        row["ground_hopping_expectation"] = expectations["hopping"]
        row["ground_electric_expectation"] = expectations["electric"]
        row["ground_magnetic_expectation"] = expectations["magnetic"]
        row["ground_total_expectation"] = expectations["total"]
    if len(eigenpairs) >= 2:
        row["first_excited_energy"] = eigenpairs[1]["eigenvalue"]

    total_stats = next(term for term in report["terms"] if term["name"] == "total")
    row["total_nnz"] = total_stats["nnz"]
    row["total_density"] = total_stats["density"]
    row["total_hermiticity_defect"] = total_stats["hermiticity_defect"]

    return row


def write_summary_csv(
    path: Path,
    rows: Sequence[tuple[CampaignExperimentSpec, CampaignRunRecord, dict | None]],
) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(SUMMARY_CSV_FIELDS))
    writer.writeheader()
    for spec, record, run_json in rows:
        writer.writerow(_summary_row(spec, record, run_json))
    atomic_write_text(path, buffer.getvalue())
