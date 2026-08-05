"""Level0 experiment runner: config -> Level0Report, plus canonical JSON export.

experiments.py orchestrates the already-validated public pipeline
(build_lattice -> build_basis -> build_key_index -> build_hamiltonian_terms
-> build_level0_report) for a single, immutable configuration. It adds no
new physics and no new construction logic of its own -- multi-configuration
sweeps/grids and any scientific interpretation of results are out of scope
for this lot.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from importlib import metadata as importlib_metadata

import numpy as np
import scipy

from .basis import build_basis
from .charges import normalize_external_charges
from .hamiltonian import build_hamiltonian_terms, build_key_index
from .lattice import build_lattice
from .params import HamiltonianParameters
from .reports import (
    EigenpairDiagnostic,
    Level0Report,
    SpectrumOptions,
    SpectrumReport,
    TermExpectations,
    TermStatistics,
    build_level0_report,
)

CONFIG_SCHEMA_VERSION = 1
JSON_SCHEMA_VERSION = 1


def _cosmobox_version() -> str | None:
    try:
        return importlib_metadata.version("cosmobox")
    except importlib_metadata.PackageNotFoundError:
        return None


@dataclass(frozen=True, slots=True)
class Level0Experiment:
    """Immutable Level0 experiment configuration.

    ``geometry`` and ``external_charges`` are canonicalized in
    __post_init__ (geometry -> lattice.name, external_charges ->
    normalize_external_charges' output) so that input variants meaning the
    same physical configuration -- e.g. ``(0, 0, 0)`` and
    ``(Fraction(0), Fraction(0), Fraction(0))`` -- produce the same object,
    the same fingerprint, and the same JSON export.
    """

    geometry: str
    n_flavors: int
    spin: int
    external_charges: Sequence[object] | None
    parameters: HamiltonianParameters
    spectrum_options: SpectrumOptions

    def __post_init__(self) -> None:
        lattice = build_lattice(self.geometry)  # raises ValueError on an unknown geometry
        n_nodes = len(lattice.nodes)

        normalized_charges = normalize_external_charges(n_nodes, self.external_charges)
        object.__setattr__(self, "external_charges", normalized_charges)
        object.__setattr__(self, "geometry", lattice.name)

        if len(self.parameters.J) != n_nodes:
            raise ValueError(f"parameters.J has {len(self.parameters.J)} entries, expected {n_nodes}")
        if len(self.parameters.h) != n_nodes:
            raise ValueError(f"parameters.h has {len(self.parameters.h)} entries, expected {n_nodes}")


# ---------------------------------------------------------------------------
# Canonical (hash-stable) payload and SHA-256 fingerprint -- config only,
# never timings, software versions, or results. Defined before
# Level0ExperimentResult because its __post_init__ uses
# _canonical_parameters_payload and compute_config_fingerprint.
# ---------------------------------------------------------------------------


def _canonical_fraction(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _canonical_complex(value: complex) -> list[float]:
    return [float(value.real), float(value.imag)]


def _canonical_matrix(matrix: np.ndarray) -> list[list[list[float]]]:
    return [
        [_canonical_complex(complex(matrix[row, col])) for col in range(matrix.shape[1])]
        for row in range(matrix.shape[0])
    ]


def _canonical_parameters_payload(params: HamiltonianParameters) -> dict:
    return {
        "J": [float(value) for value in params.J],
        "h": [_canonical_matrix(matrix) for matrix in params.h],
        "t": float(params.t),
        "g_E": float(params.g_E),
        "K": float(params.K),
    }


def _canonical_spectrum_options_payload(options: SpectrumOptions) -> dict:
    return {
        "max_dense_dimension": options.max_dense_dimension,
        "max_sparse_dimension": options.max_sparse_dimension,
        "n_eigenvalues": options.n_eigenvalues,
        "tolerance": options.tolerance,
        "max_iterations": options.max_iterations,
        "force": options.force,
        "seed": options.seed,
    }


def _canonical_config_payload(config: Level0Experiment) -> dict:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "geometry": config.geometry,
        "n_flavors": config.n_flavors,
        "spin": config.spin,
        "external_charges": [_canonical_fraction(q) for q in config.external_charges],
        "parameters": _canonical_parameters_payload(config.parameters),
        "spectrum_options": _canonical_spectrum_options_payload(config.spectrum_options),
    }


def compute_config_fingerprint(config: Level0Experiment) -> str:
    payload = _canonical_config_payload(config)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Level0ExperimentResult:
    """Lightweight run outcome: config, report, timings, provenance. No
    basis, no key_index, no CSR matrices, no eigenvectors."""

    config: Level0Experiment
    report: Level0Report
    basis_build_seconds: float
    hamiltonian_build_seconds: float
    report_build_seconds: float
    python_version: str
    numpy_version: str
    scipy_version: str
    cosmobox_version: str | None
    config_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("basis_build_seconds", self.basis_build_seconds),
            ("hamiltonian_build_seconds", self.hamiltonian_build_seconds),
            ("report_build_seconds", self.report_build_seconds),
        ):
            if not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name} must be finite and >= 0, got {value}")

        fingerprint = self.config_fingerprint
        if len(fingerprint) != 64 or fingerprint != fingerprint.lower() or any(
            c not in "0123456789abcdef" for c in fingerprint
        ):
            raise ValueError(f"config_fingerprint must be 64 lowercase hex characters, got {fingerprint!r}")
        expected_fingerprint = compute_config_fingerprint(self.config)
        if fingerprint != expected_fingerprint:
            raise ValueError(
                f"config_fingerprint {fingerprint!r} does not match compute_config_fingerprint(config) "
                f"({expected_fingerprint!r}); a well-formed but wrong fingerprint is a provenance failure"
            )

        for name, value in (
            ("python_version", self.python_version),
            ("numpy_version", self.numpy_version),
            ("scipy_version", self.scipy_version),
        ):
            if not value:
                raise ValueError(f"{name} must be non-empty")
        # cosmobox_version may legitimately be None (package metadata unavailable).

        if self.report.lattice_name != self.config.geometry:
            raise ValueError("report.lattice_name does not match config.geometry")
        if self.report.n_flavors != self.config.n_flavors:
            raise ValueError("report.n_flavors does not match config.n_flavors")
        if self.report.spin != self.config.spin:
            raise ValueError("report.spin does not match config.spin")

        # HamiltonianParameters.h holds numpy arrays, so dataclass value
        # equality (==) on it raises ("truth value of an array is
        # ambiguous"). Compare canonical payloads instead: this accepts two
        # distinct-but-equivalent HamiltonianParameters objects (the same
        # scientific configuration) and rejects any numeric difference,
        # which is the semantics we actually want here -- not object identity.
        if _canonical_parameters_payload(self.report.parameters) != _canonical_parameters_payload(
            self.config.parameters
        ):
            raise ValueError("report.parameters is not equivalent to config.parameters")
        if self.report.spectrum_options != self.config.spectrum_options:
            raise ValueError("report.spectrum_options does not match config.spectrum_options")
        if self.report.external_charges != self.config.external_charges:
            raise ValueError("report.external_charges does not match config.external_charges")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_level0_experiment(config: Level0Experiment) -> Level0ExperimentResult:
    lattice = build_lattice(config.geometry)

    start = time.perf_counter_ns()
    basis = build_basis(lattice, config.n_flavors, config.spin, external_charges=config.external_charges)
    after_basis = time.perf_counter_ns()

    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, config.parameters
    )
    after_hamiltonian = time.perf_counter_ns()

    report = build_level0_report(
        lattice,
        config.n_flavors,
        config.spin,
        basis,
        terms,
        config.parameters,
        external_charges=config.external_charges,
        spectrum_options=config.spectrum_options,
    )
    after_report = time.perf_counter_ns()

    return Level0ExperimentResult(
        config=config,
        report=report,
        basis_build_seconds=(after_basis - start) / 1e9,
        hamiltonian_build_seconds=(after_hamiltonian - after_basis) / 1e9,
        report_build_seconds=(after_report - after_hamiltonian) / 1e9,
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        scipy_version=scipy.__version__,
        cosmobox_version=_cosmobox_version(),
        config_fingerprint=compute_config_fingerprint(config),
    )


# ---------------------------------------------------------------------------
# Human-readable JSON export (distinct from the canonical hash payload):
# Fraction -> "n/d" string, complex -> [re, im]. No CSR matrices, no
# eigenvectors -- Level0Report never carries either in the first place.
# ---------------------------------------------------------------------------


def _fraction_to_json(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _complex_to_json(value: complex) -> list[float]:
    return [float(value.real), float(value.imag)]


def _matrix_to_json(matrix: np.ndarray) -> list[list[list[float]]]:
    return [
        [_complex_to_json(complex(matrix[row, col])) for col in range(matrix.shape[1])]
        for row in range(matrix.shape[0])
    ]


def _parameters_to_json(params: HamiltonianParameters) -> dict:
    return {
        "J": list(params.J),
        "h": [_matrix_to_json(matrix) for matrix in params.h],
        "t": params.t,
        "g_E": params.g_E,
        "K": params.K,
    }


def _spectrum_options_to_json(options: SpectrumOptions) -> dict:
    return {
        "max_dense_dimension": options.max_dense_dimension,
        "max_sparse_dimension": options.max_sparse_dimension,
        "n_eigenvalues": options.n_eigenvalues,
        "tolerance": options.tolerance,
        "max_iterations": options.max_iterations,
        "force": options.force,
        "seed": options.seed,
    }


def _term_statistics_to_json(stats: TermStatistics) -> dict:
    return {
        "name": stats.name,
        "nnz": stats.nnz,
        "density": stats.density,
        "hermiticity_defect": stats.hermiticity_defect,
        "frobenius_norm": stats.frobenius_norm,
    }


def _term_expectations_to_json(expectations: TermExpectations) -> dict:
    return {
        "dot": expectations.dot,
        "hopping": expectations.hopping,
        "electric": expectations.electric,
        "magnetic": expectations.magnetic,
        "total": expectations.total,
    }


def _eigenpair_to_json(eigenpair: EigenpairDiagnostic) -> dict:
    return {
        "index": eigenpair.index,
        "eigenvalue": eigenpair.eigenvalue,
        "residual_norm": eigenpair.residual_norm,
        "term_expectations": _term_expectations_to_json(eigenpair.term_expectations),
    }


def _spectrum_to_json(spectrum: SpectrumReport) -> dict:
    return {
        "status": spectrum.status,
        "method": spectrum.method,
        "requested_eigenvalues": spectrum.requested_eigenvalues,
        "computed_eigenvalues": spectrum.computed_eigenvalues,
        "tolerance": spectrum.tolerance,
        "reason": spectrum.reason,
        "eigenpairs": [_eigenpair_to_json(eigenpair) for eigenpair in spectrum.eigenpairs],
        "spectral_gap": spectrum.spectral_gap,
    }


def _report_to_json(report: Level0Report) -> dict:
    return {
        "lattice_name": report.lattice_name,
        "n_flavors": report.n_flavors,
        "spin": report.spin,
        "external_charges": [_fraction_to_json(q) for q in report.external_charges],
        "dimension": report.dimension,
        "sector_count": report.sector_count,
        "excluded_sector_count": report.excluded_sector_count,
        "mean_flux_configs_per_occupation": report.mean_flux_configs_per_occupation,
        "max_flux_configs_per_occupation": report.max_flux_configs_per_occupation,
        "terms": [_term_statistics_to_json(stats) for stats in report.terms],
        "spectrum": _spectrum_to_json(report.spectrum),
        "spectrum_options": _spectrum_options_to_json(report.spectrum_options),
        "parameters": _parameters_to_json(report.parameters),
    }


def level0_experiment_config_to_json_dict(config: Level0Experiment) -> dict:
    """The "config" sub-block on its own -- e.g. to compute the JSON shape a
    given Level0Experiment *would* produce without running it, for
    validating an existing result file against a currently-expected config
    (as scripts/level0_reference_campaign/outputs.py does)."""
    return {
        "geometry": config.geometry,
        "n_flavors": config.n_flavors,
        "spin": config.spin,
        "external_charges": [_fraction_to_json(q) for q in config.external_charges],
        "parameters": _parameters_to_json(config.parameters),
        "spectrum_options": _spectrum_options_to_json(config.spectrum_options),
    }


def level0_experiment_result_to_json_dict(result: Level0ExperimentResult) -> dict:
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "config_fingerprint": result.config_fingerprint,
        "config": level0_experiment_config_to_json_dict(result.config),
        "environment": {
            "python_version": result.python_version,
            "numpy_version": result.numpy_version,
            "scipy_version": result.scipy_version,
            "cosmobox_version": result.cosmobox_version,
        },
        "timings": {
            "basis_build_seconds": result.basis_build_seconds,
            "hamiltonian_build_seconds": result.hamiltonian_build_seconds,
            "report_build_seconds": result.report_build_seconds,
        },
        "report": _report_to_json(result.report),
    }


def dump_level0_experiment_result_json(result: Level0ExperimentResult, *, indent: int | None = 2) -> str:
    payload = level0_experiment_result_to_json_dict(result)
    return json.dumps(payload, sort_keys=True, indent=indent, ensure_ascii=True, allow_nan=False)
