"""Validation of existing symmetry-campaign run files, and atomic manifest/CSV writers.

Deliberately self-contained: does not import atomic_write_text,
validate_existing_run, or any other name from
scripts.level0_reference_campaign.outputs (or the rest of that package).
The run-file shape differs (an extra "symmetry" block, an extra
"degeneracy" sub-block, two extra timings fields), and the helpers small
enough to be shared (atomic_write_text) are cheap to duplicate locally
rather than create a dependency on 5B's internal tooling.
"""

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
from cosmobox.level0.experiments import JSON_SCHEMA_VERSION as LEVEL0_JSON_SCHEMA_VERSION

from .analysis import SYMMETRY_JSON_SCHEMA_VERSION, SYMMETRY_OPERATOR_NAMES
from .grid import SymmetryCampaignExperimentSpec, spec_to_experiment

_SPECTRUM_STATUSES = ("computed", "not_computed", "failed")

SUMMARY_CSV_FIELDS: tuple[str, ...] = (
    "experiment_id",
    "config_fingerprint",
    "geometry",
    "spin",
    "j_pattern",
    "h_eta",
    "t",
    "g_E",
    "K",
    "dimension",
    "solver_method",
    "published_eigenvalues",
    "n_spectral_groups",
    "basis_build_seconds",
    "hamiltonian_build_seconds",
    "report_build_seconds",
    "symmetry_operators_build_seconds",
    "symmetry_diagnostics_seconds",
    "max_restriction_defect_excl_truncated_T2",
    "max_restriction_defect_excl_truncated_T",
    "max_restriction_defect_excl_truncated_R",
    "commutator_defect_T2",
    "commutator_defect_T",
    "commutator_defect_R",
)

_OPERATOR_CSV_LABEL: dict[str, str] = {"T^2": "T2", "T": "T", "R": "R"}


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
    _require_keys(
        environment, ("python_version", "numpy_version", "scipy_version", "cosmobox_version"), "environment"
    )


def _check_timings(timings: object) -> None:
    fields = (
        "basis_build_seconds",
        "hamiltonian_build_seconds",
        "report_build_seconds",
        "symmetry_operators_build_seconds",
        "symmetry_diagnostics_seconds",
    )
    _require_keys(timings, fields, "timings")
    for key in fields:
        value = timings[key]
        _require(_is_finite_number(value) and value >= 0, f"timings[{key!r}] is not a finite, non-negative number")


def _check_provenance(report: dict, expected_config: dict) -> None:
    _require(
        report.get("lattice_name") == expected_config["geometry"],
        "report.lattice_name does not match config.geometry",
    )
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
    _require(
        isinstance(total_stats.get("nnz"), int) and not isinstance(total_stats.get("nnz"), bool),
        "total.nnz is not an integer",
    )
    for key in ("density", "hermiticity_defect"):
        _require(_is_finite_number(total_stats.get(key)), f"total.{key} is not a finite number")


def _check_eigenpair(pair: object, index: int) -> None:
    _require_keys(pair, ("eigenvalue", "residual_norm", "term_expectations"), f"eigenpair {index}")
    _require(_is_finite_number(pair["eigenvalue"]), f"eigenpair {index} eigenvalue is not finite")
    _require(_is_finite_number(pair["residual_norm"]), f"eigenpair {index} residual_norm is not finite")
    expectations = pair["term_expectations"]
    _require_keys(
        expectations, ("dot", "hopping", "electric", "magnetic", "total"), f"eigenpair {index} term_expectations"
    )
    for key in ("dot", "hopping", "electric", "magnetic", "total"):
        _require(_is_finite_number(expectations[key]), f"eigenpair {index} term_expectations[{key!r}] is not finite")


def _check_degeneracy(spectrum: dict) -> list:
    degeneracy = spectrum.get("degeneracy")
    _require_keys(
        degeneracy,
        ("tolerance", "ground_multiplicity_observed", "first_distinct_energy", "first_distinct_gap", "groups", "window_truncated"),
        "spectrum.degeneracy",
    )
    _require(_is_finite_number(degeneracy["tolerance"]) and degeneracy["tolerance"] > 0, "degeneracy.tolerance invalid")
    groups = degeneracy["groups"]
    _require(isinstance(groups, list) and len(groups) >= 1, "spectrum.degeneracy.groups is empty or not a list")
    for index, group in enumerate(groups):
        _require_keys(
            group,
            (
                "start_index",
                "end_index_exclusive",
                "representative_energy",
                "min_energy",
                "max_energy",
                "multiplicity_observed",
                "lower_bound_only",
            ),
            f"degeneracy.groups[{index}]",
        )
        for key in ("representative_energy", "min_energy", "max_energy"):
            _require(_is_finite_number(group[key]), f"degeneracy.groups[{index}].{key} is not finite")
        _require(isinstance(group["lower_bound_only"], bool), f"degeneracy.groups[{index}].lower_bound_only is not a bool")
    return groups


def _check_spectrum(report: dict) -> list:
    spectrum = report.get("spectrum")
    _require_keys(spectrum, ("status", "method", "computed_eigenvalues", "eigenpairs", "spectral_gap", "degeneracy"), "report.spectrum")

    status = spectrum["status"]
    _require(status in _SPECTRUM_STATUSES, f"unexpected spectrum status {status!r}")
    # A valid saved 6C run file only ever exists for a fully-diagnosed
    # experiment: run_symmetry_experiment raises (never writes a run file)
    # when eigenvectors/degeneracy are unavailable, so a persisted run is
    # always "computed" with a real degeneracy block.
    _require(status == "computed", f"a persisted 6C run file must have spectrum.status == 'computed', got {status!r}")

    eigenpairs = spectrum["eigenpairs"]
    _require(isinstance(eigenpairs, list) and len(eigenpairs) >= 1, "spectrum.eigenpairs is empty or not a list")

    computed_eigenvalues = spectrum["computed_eigenvalues"]
    _require(
        isinstance(computed_eigenvalues, int) and not isinstance(computed_eigenvalues, bool),
        "spectrum.computed_eigenvalues is not an integer",
    )
    _require(computed_eigenvalues == len(eigenpairs), "spectrum.computed_eigenvalues does not match len(eigenpairs)")

    for index, pair in enumerate(eigenpairs):
        _check_eigenpair(pair, index)

    spectral_gap = spectrum["spectral_gap"]
    if spectral_gap is not None:
        _require(_is_finite_number(spectral_gap), "spectrum.spectral_gap is not finite")
        _require(len(eigenpairs) >= 2, "spectrum.spectral_gap is set but fewer than 2 eigenpairs are present")

    return _check_degeneracy(spectrum)


def _check_report(report: object, expected_config: dict) -> list:
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
    _check_provenance(report, expected_config)
    _check_terms(report)
    return _check_spectrum(report)


def _check_symmetry_block(symmetry: object, groups: list) -> None:
    _require_keys(
        symmetry,
        ("schema_version", "solver_method", "dimension", "published_eigenvalues", "operators", "diagnostics"),
        "symmetry",
    )
    _require(
        symmetry["schema_version"] == SYMMETRY_JSON_SCHEMA_VERSION,
        f"unexpected symmetry.schema_version {symmetry['schema_version']!r}",
    )
    _require(symmetry["operators"] == list(SYMMETRY_OPERATOR_NAMES), "symmetry.operators does not match the expected operator set")

    diagnostics = symmetry["diagnostics"]
    _require(isinstance(diagnostics, list) and len(diagnostics) > 0, "symmetry.diagnostics is empty or not a list")

    coverage: dict[str, set] = {name: set() for name in SYMMETRY_OPERATOR_NAMES}
    for index, diagnostic in enumerate(diagnostics):
        where = f"symmetry.diagnostics[{index}]"
        _require_keys(
            diagnostic,
            (
                "operator_name",
                "operator_kind",
                "spectral_group_index",
                "spectral_group_lower_bound_only",
                "spectral_group_multiplicity_observed",
                "restricted_eigenvalues",
                "restriction_defect",
                "restricted_hermiticity_defect",
                "restricted_unitarity_defect",
                "subspace_orthonormality_defect",
                "commutator_defect",
            ),
            where,
        )
        name = diagnostic["operator_name"]
        _require(name in coverage, f"{where}.operator_name {name!r} is unexpected")

        group_index = diagnostic["spectral_group_index"]
        _require(
            isinstance(group_index, int) and not isinstance(group_index, bool) and 0 <= group_index < len(groups),
            f"{where}.spectral_group_index is out of range",
        )
        coverage[name].add(group_index)

        expected_group = groups[group_index]
        _require(
            diagnostic["spectral_group_lower_bound_only"] == expected_group["lower_bound_only"],
            f"{where}.spectral_group_lower_bound_only does not match degeneracy.groups[{group_index}]",
        )
        _require(
            diagnostic["spectral_group_multiplicity_observed"] == expected_group["multiplicity_observed"],
            f"{where}.spectral_group_multiplicity_observed does not match degeneracy.groups[{group_index}]",
        )

        _require(
            _is_finite_number(diagnostic["restriction_defect"]) and diagnostic["restriction_defect"] >= 0,
            f"{where}.restriction_defect is invalid",
        )
        _require(
            _is_finite_number(diagnostic["subspace_orthonormality_defect"])
            and diagnostic["subspace_orthonormality_defect"] >= 0,
            f"{where}.subspace_orthonormality_defect is invalid",
        )
        for key in ("restricted_hermiticity_defect", "restricted_unitarity_defect", "commutator_defect"):
            value = diagnostic[key]
            _require(value is None or (_is_finite_number(value) and value >= 0), f"{where}.{key} is invalid")

        eigenvalues = diagnostic["restricted_eigenvalues"]
        _require(isinstance(eigenvalues, list), f"{where}.restricted_eigenvalues is not a list")
        for pair_index, pair in enumerate(eigenvalues):
            _require(
                isinstance(pair, list) and len(pair) == 2 and all(_is_finite_number(v) for v in pair),
                f"{where}.restricted_eigenvalues[{pair_index}] is not a finite [re, im] pair",
            )

    for name in SYMMETRY_OPERATOR_NAMES:
        _require(
            coverage[name] == set(range(len(groups))),
            f"operator {name!r} does not cover every spectral group exactly once",
        )


def _validate_run_payload(parsed: object, spec: SymmetryCampaignExperimentSpec, expected_fingerprint: str) -> None:
    _require_keys(
        parsed, ("schema_version", "config_fingerprint", "config", "environment", "timings", "report", "symmetry"), "run file"
    )
    _require(
        parsed["schema_version"] == LEVEL0_JSON_SCHEMA_VERSION,
        f"unexpected schema_version {parsed['schema_version']!r} (must match "
        "cosmobox.level0.experiments.JSON_SCHEMA_VERSION, the base Level0ExperimentResult contract)",
    )
    _require(
        parsed["config_fingerprint"] == expected_fingerprint,
        "config_fingerprint in file does not match the expected fingerprint",
    )

    expected_config = level0_experiment_config_to_json_dict(spec_to_experiment(spec))
    _require(parsed["config"] == expected_config, "config block in file does not match the expected configuration")

    _check_environment(parsed["environment"])
    _check_timings(parsed["timings"])
    groups = _check_report(parsed["report"], expected_config)
    _check_symmetry_block(parsed["symmetry"], groups)


def validate_existing_run(
    path: Path, spec: SymmetryCampaignExperimentSpec, expected_fingerprint: str
) -> tuple[bool, str | None]:
    """(is_valid, reason_if_invalid). Never raises on a missing/corrupt/incomplete file."""
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
    thresholds: dict,
    records: Sequence[CampaignRunRecord],
) -> None:
    payload = {
        "protocol_version": protocol_version,
        "expected_runs": expected_runs,
        "started_at": started_at,
        "thresholds": dict(thresholds),
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


def _summary_row(spec: SymmetryCampaignExperimentSpec, record: CampaignRunRecord, run_json: dict | None) -> dict:
    row: dict[str, object] = {name: "" for name in SUMMARY_CSV_FIELDS}
    row.update(
        {
            "experiment_id": spec.experiment_id,
            "config_fingerprint": record.config_fingerprint,
            "geometry": spec.geometry,
            "spin": spec.spin,
            "j_pattern": spec.j_pattern,
            "h_eta": spec.h_eta,
            "t": spec.t,
            "g_E": spec.g_E,
            "K": spec.K,
        }
    )

    if run_json is None:
        return row

    report = run_json["report"]
    timings = run_json["timings"]
    symmetry = run_json["symmetry"]
    groups = report["spectrum"]["degeneracy"]["groups"]

    row["dimension"] = report["dimension"]
    row["solver_method"] = symmetry["solver_method"] or ""
    row["published_eigenvalues"] = symmetry["published_eigenvalues"]
    row["n_spectral_groups"] = len(groups)
    row["basis_build_seconds"] = timings["basis_build_seconds"]
    row["hamiltonian_build_seconds"] = timings["hamiltonian_build_seconds"]
    row["report_build_seconds"] = timings["report_build_seconds"]
    row["symmetry_operators_build_seconds"] = timings["symmetry_operators_build_seconds"]
    row["symmetry_diagnostics_seconds"] = timings["symmetry_diagnostics_seconds"]

    by_operator: dict[str, list[dict]] = {name: [] for name in SYMMETRY_OPERATOR_NAMES}
    for diagnostic in symmetry["diagnostics"]:
        by_operator[diagnostic["operator_name"]].append(diagnostic)

    for name in SYMMETRY_OPERATOR_NAMES:
        entries = by_operator[name]
        label = _OPERATOR_CSV_LABEL[name]
        non_truncated = [d for d in entries if not d["spectral_group_lower_bound_only"]]
        if non_truncated:
            row[f"max_restriction_defect_excl_truncated_{label}"] = max(d["restriction_defect"] for d in non_truncated)
        if entries:
            row[f"commutator_defect_{label}"] = entries[0]["commutator_defect"]

    return row


def write_summary_csv(
    path: Path,
    rows: Sequence[tuple[SymmetryCampaignExperimentSpec, CampaignRunRecord, dict | None]],
) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(SUMMARY_CSV_FIELDS))
    writer.writeheader()
    for spec, record, run_json in rows:
        writer.writerow(_summary_row(spec, record, run_json))
    atomic_write_text(path, buffer.getvalue())
