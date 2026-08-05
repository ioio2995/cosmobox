"""Validation of existing run files, and atomic manifest/CSV writers."""

from __future__ import annotations

import csv
import io
import json
import math
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cosmobox.level0 import level0_experiment_config_to_json_dict
from cosmobox.level0.lattice import build_lattice

from .grid import CampaignExperimentSpec, spec_to_experiment

JSON_SCHEMA_VERSION = 1  # must track cosmobox.level0.experiments.JSON_SCHEMA_VERSION

_SPECTRUM_STATUSES = ("computed", "not_computed", "failed")

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


class _InvalidRun(Exception):
    """Internal control-flow exception: caught once in validate_existing_run
    and turned into (False, str(exc)). Never escapes this module."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise _InvalidRun(message)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_keys(obj: object, keys: tuple[str, ...], where: str) -> None:
    _require(isinstance(obj, dict), f"{where} is not a JSON object")
    for key in keys:
        _require(key in obj, f"{where} is missing {key!r}")


def _check_environment(environment: object) -> None:
    _require_keys(environment, ("python_version", "numpy_version", "scipy_version", "cosmobox_version"), "environment")


def _check_timings(timings: object) -> None:
    _require_keys(
        timings, ("basis_build_seconds", "hamiltonian_build_seconds", "report_build_seconds"), "timings"
    )
    for key in ("basis_build_seconds", "hamiltonian_build_seconds", "report_build_seconds"):
        value = timings[key]
        _require(_is_finite_number(value) and value >= 0, f"timings[{key!r}] is not a finite, non-negative number")


def _check_provenance(report: dict, expected_config: dict) -> None:
    """A run file can have the right `config` block yet an unrelated
    `report` (e.g. copied from a different run). Cross-check the fields
    reports.Level0Report itself guarantees match config at construction --
    same invariant, re-checked here because this is raw JSON, not the typed
    object that already enforced it once when the file was written."""
    _require(report.get("lattice_name") == expected_config["geometry"], "report.lattice_name does not match config.geometry")
    _require(report.get("n_flavors") == expected_config["n_flavors"], "report.n_flavors does not match config.n_flavors")
    _require(report.get("spin") == expected_config["spin"], "report.spin does not match config.spin")
    _require(
        report.get("external_charges") == expected_config["external_charges"],
        "report.external_charges does not match config.external_charges",
    )
    _require(
        report.get("parameters") == expected_config["parameters"],
        "report.parameters does not match config.parameters",
    )
    _require(
        report.get("spectrum_options") == expected_config["spectrum_options"],
        "report.spectrum_options does not match config.spectrum_options",
    )


def _check_terms(report: dict) -> None:
    terms = report.get("terms")
    _require(isinstance(terms, list), "report.terms is not a list")
    total_entries = [term for term in terms if isinstance(term, dict) and term.get("name") == "total"]
    _require(len(total_entries) == 1, "report.terms does not contain exactly one 'total' entry")
    total_stats = total_entries[0]
    _require(isinstance(total_stats.get("nnz"), int) and not isinstance(total_stats.get("nnz"), bool), "total.nnz is not an integer")
    for key in ("density", "hermiticity_defect"):
        _require(_is_finite_number(total_stats.get(key)), f"total.{key} is not a finite number")


def _check_eigenpair(pair: object, index: int) -> None:
    _require_keys(pair, ("eigenvalue", "residual_norm", "term_expectations"), f"eigenpair {index}")
    _require(_is_finite_number(pair["eigenvalue"]), f"eigenpair {index} eigenvalue is not finite")
    _require(_is_finite_number(pair["residual_norm"]), f"eigenpair {index} residual_norm is not finite")
    expectations = pair["term_expectations"]
    _require_keys(expectations, ("dot", "hopping", "electric", "magnetic", "total"), f"eigenpair {index} term_expectations")
    for key in ("dot", "hopping", "electric", "magnetic", "total"):
        _require(_is_finite_number(expectations[key]), f"eigenpair {index} term_expectations[{key!r}] is not finite")


def _check_spectrum(report: dict) -> None:
    spectrum = report.get("spectrum")
    _require_keys(spectrum, ("status", "method", "computed_eigenvalues", "eigenpairs", "spectral_gap"), "report.spectrum")

    status = spectrum["status"]
    _require(status in _SPECTRUM_STATUSES, f"unexpected spectrum status {status!r}")

    eigenpairs = spectrum["eigenpairs"]
    _require(isinstance(eigenpairs, list), "spectrum.eigenpairs is not a list")

    if status in ("not_computed", "failed"):
        _require(len(eigenpairs) == 0, f"spectrum.status={status!r} but eigenpairs is not empty")

    computed_eigenvalues = spectrum["computed_eigenvalues"]
    _require(
        isinstance(computed_eigenvalues, int) and not isinstance(computed_eigenvalues, bool),
        "spectrum.computed_eigenvalues is not an integer",
    )
    _require(
        computed_eigenvalues == len(eigenpairs),
        "spectrum.computed_eigenvalues does not match len(eigenpairs)",
    )

    for index, pair in enumerate(eigenpairs):
        _check_eigenpair(pair, index)

    spectral_gap = spectrum["spectral_gap"]
    if spectral_gap is not None:
        _require(_is_finite_number(spectral_gap), "spectrum.spectral_gap is not finite")
        _require(len(eigenpairs) >= 2, "spectrum.spectral_gap is set but fewer than 2 eigenpairs are present")


def _check_report(report: object, expected_config: dict) -> None:
    _require_keys(
        report,
        (
            "lattice_name",
            "n_flavors",
            "spin",
            "external_charges",
            "parameters",
            "spectrum_options",
            "dimension",
            "sector_count",
            "terms",
            "spectrum",
        ),
        "report",
    )
    _require(
        isinstance(report["dimension"], int) and not isinstance(report["dimension"], bool),
        "report.dimension is not an integer",
    )
    _require(
        isinstance(report["sector_count"], int) and not isinstance(report["sector_count"], bool),
        "report.sector_count is not an integer",
    )
    _check_provenance(report, expected_config)
    _check_terms(report)
    _check_spectrum(report)


def _validate_run_payload(
    parsed: object, spec: CampaignExperimentSpec, expected_fingerprint: str
) -> None:
    _require_keys(
        parsed, ("schema_version", "config_fingerprint", "config", "environment", "timings", "report"), "run file"
    )
    _require(parsed["schema_version"] == JSON_SCHEMA_VERSION, f"unexpected schema_version {parsed['schema_version']!r}")
    _require(
        parsed["config_fingerprint"] == expected_fingerprint,
        "config_fingerprint in file does not match the expected fingerprint",
    )

    expected_config = level0_experiment_config_to_json_dict(spec_to_experiment(spec))
    _require(parsed["config"] == expected_config, "config block in file does not match the expected configuration")

    _check_environment(parsed["environment"])
    _check_timings(parsed["timings"])
    _check_report(parsed["report"], expected_config)


def validate_existing_run(
    path: Path, spec: CampaignExperimentSpec, expected_fingerprint: str
) -> tuple[bool, str | None]:
    """(is_valid, reason_if_invalid). Never raises on a missing/corrupt/incomplete file.

    Checks the full structure a "skipped" run must have to be safely read
    by run_campaign (report["spectrum"]["status"]) and _summary_row
    (report["terms"]/["spectrum"]["eigenpairs"]/...) without a KeyError or
    a NaN silently reaching the CSV -- not just that config_fingerprint and
    the config block look right; a truncated or field-swapped file with a
    correct fingerprint would otherwise pass and crash the campaign later.
    """
    if not path.exists():
        return False, "no existing run file"

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"could not parse existing run file: {exc}"

    try:
        _validate_run_payload(parsed, spec, expected_fingerprint)
    except _InvalidRun as exc:
        return False, str(exc)

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
