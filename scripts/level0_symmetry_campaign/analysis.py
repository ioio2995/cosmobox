"""Runs one symmetry-diagnostics experiment: config -> SymmetryExperimentResult.

Builds on the same public cosmobox.level0 pipeline as
experiments.run_level0_experiment, but additionally retains eigenvectors
(build_level0_report_with_eigenvectors) and runs
analyze_symmetry_in_subspaces for T^2, translation, and reflection over
every spectral group. Which operators to diagnose and how to check their
mutual consistency is campaign-specific orchestration -- it lives here,
outside cosmobox.level0, not as a new engine primitive.
"""

from __future__ import annotations

import math
import platform
import time
from dataclasses import dataclass
from importlib import metadata as importlib_metadata

import numpy as np
import scipy

from cosmobox.level0 import (
    Level0Experiment,
    Level0ExperimentResult,
    OperatorKind,
    SymmetrySectorDiagnostic,
    analyze_symmetry_in_subspaces,
    build_basis,
    build_flavor_casimir,
    build_hamiltonian_terms,
    build_key_index,
    build_lattice,
    build_level0_report_with_eigenvectors,
    build_reflection_operator,
    build_translation_operator,
    compute_config_fingerprint,
    level0_experiment_result_to_json_dict,
)

SYMMETRY_OPERATOR_NAMES: tuple[str, ...] = ("T^2", "T", "R")


def _cosmobox_version() -> str | None:
    """Local copy of experiments._cosmobox_version -- that helper is private
    to cosmobox.level0.experiments and not re-exported, so it is duplicated
    here rather than imported (same reasoning as not depending on
    scripts.level0_reference_campaign's internals: don't reach into another
    module's private surface for a three-line helper)."""
    try:
        return importlib_metadata.version("cosmobox")
    except importlib_metadata.PackageNotFoundError:
        return None

EXACT_SYMMETRY_COMMUTATOR_TOLERANCE = 1e-8
COMPLETE_GROUP_RESTRICTION_TOLERANCE = 1e-8


@dataclass(frozen=True, slots=True)
class SymmetryExperimentResult:
    """base carries everything experiments.Level0ExperimentResult already
    validates (config/report/fingerprint/timings/versions) -- reused as-is
    rather than re-implemented. diagnostics and the two extra timings are
    this campaign's own addition on top."""

    base: Level0ExperimentResult
    diagnostics: tuple[SymmetrySectorDiagnostic, ...]
    symmetry_operators_build_seconds: float
    symmetry_diagnostics_seconds: float

    def __post_init__(self) -> None:
        for name, value in (
            ("symmetry_operators_build_seconds", self.symmetry_operators_build_seconds),
            ("symmetry_diagnostics_seconds", self.symmetry_diagnostics_seconds),
        ):
            if not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name} must be finite and >= 0, got {value}")
        if len(self.diagnostics) == 0:
            raise ValueError("diagnostics must not be empty")


def _check_commutator_restriction_consistency(
    diagnostics: tuple[SymmetrySectorDiagnostic, ...], degeneracy
) -> None:
    """A necessary numeric consistency condition, not a physics
    interpretation: if an operator's global commutator with H is below
    tolerance (it numerically commutes), it must preserve every COMPLETE
    spectral group's subspace almost exactly -- restriction_defect can't
    stay large there without something being wrong (a bug, or an operator
    that doesn't actually commute as its own commutator_defect claims).

    Exempted for a window-truncated last group (lower_bound_only=True):
    only a partial slice of a possibly-larger degenerate manifold is
    available there, and that slice is not guaranteed individually
    invariant even when the operator genuinely commutes with H on the
    full (unobserved) manifold -- a large restriction_defect there is
    ambiguous, not necessarily a bug, so it must never raise.
    """
    for diagnostic in diagnostics:
        group = degeneracy.groups[diagnostic.spectral_group_index]
        if group.lower_bound_only:
            continue
        if diagnostic.commutator_defect is None:
            continue
        if diagnostic.commutator_defect < EXACT_SYMMETRY_COMMUTATOR_TOLERANCE:
            if diagnostic.restriction_defect >= COMPLETE_GROUP_RESTRICTION_TOLERANCE:
                raise RuntimeError(
                    f"{diagnostic.operator_name} group {diagnostic.spectral_group_index}: "
                    f"commutator_defect={diagnostic.commutator_defect} < "
                    f"{EXACT_SYMMETRY_COMMUTATOR_TOLERANCE} (claims global commutation) but "
                    f"restriction_defect={diagnostic.restriction_defect} >= "
                    f"{COMPLETE_GROUP_RESTRICTION_TOLERANCE} on a non-truncated group"
                )


def run_symmetry_experiment(config: Level0Experiment) -> SymmetryExperimentResult:
    lattice = build_lattice(config.geometry)

    start = time.perf_counter_ns()
    basis = build_basis(lattice, config.n_flavors, config.spin, external_charges=config.external_charges)
    after_basis = time.perf_counter_ns()

    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, config.parameters
    )
    after_hamiltonian = time.perf_counter_ns()

    report, eigenvectors = build_level0_report_with_eigenvectors(
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

    base = Level0ExperimentResult(
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

    if eigenvectors is None or report.spectrum.degeneracy is None:
        raise RuntimeError(
            "symmetry diagnostics require a computed spectrum with retained eigenvectors and "
            f"degeneracy; got status={report.spectrum.status!r}, dimension={report.dimension}"
        )
    degeneracy = report.spectrum.degeneracy

    casimir = build_flavor_casimir(lattice, config.n_flavors, config.spin, basis.keys, key_index)
    translation = build_translation_operator(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, external_charges=config.external_charges
    )
    reflection = build_reflection_operator(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, external_charges=config.external_charges
    )
    after_operators = time.perf_counter_ns()

    diagnostics = (
        analyze_symmetry_in_subspaces(
            casimir, "T^2", OperatorKind.HERMITIAN, eigenvectors, degeneracy, total=terms.total
        )
        + analyze_symmetry_in_subspaces(
            translation, "T", OperatorKind.UNITARY, eigenvectors, degeneracy, total=terms.total
        )
        + analyze_symmetry_in_subspaces(
            reflection, "R", OperatorKind.HERMITIAN_UNITARY, eigenvectors, degeneracy, total=terms.total
        )
    )
    after_diagnostics = time.perf_counter_ns()

    _check_commutator_restriction_consistency(diagnostics, degeneracy)

    return SymmetryExperimentResult(
        base=base,
        diagnostics=diagnostics,
        symmetry_operators_build_seconds=(after_operators - after_report) / 1e9,
        symmetry_diagnostics_seconds=(after_diagnostics - after_operators) / 1e9,
    )


# ---------------------------------------------------------------------------
# JSON export -- reuses cosmobox.level0.experiments' own encoder for the
# config/environment/timings/report blocks (no re-implementation of
# Level0Report's JSON shape), and adds a "symmetry" block on top.
# ---------------------------------------------------------------------------

SYMMETRY_JSON_SCHEMA_VERSION = 1
"""This package's own schema version, independent of
cosmobox.level0.experiments.JSON_SCHEMA_VERSION -- the "symmetry" block and
the two extra timings fields are this campaign's own contract."""


def _complex_to_json(value: complex) -> list[float]:
    return [float(value.real), float(value.imag)]


def _diagnostic_to_json(diagnostic: SymmetrySectorDiagnostic, degeneracy) -> dict:
    group = degeneracy.groups[diagnostic.spectral_group_index]
    return {
        "operator_name": diagnostic.operator_name,
        "operator_kind": diagnostic.operator_kind.value,
        "spectral_group_index": diagnostic.spectral_group_index,
        "spectral_group_lower_bound_only": group.lower_bound_only,
        "spectral_group_multiplicity_observed": group.multiplicity_observed,
        "restricted_eigenvalues": [_complex_to_json(value) for value in diagnostic.restricted_eigenvalues],
        "restriction_defect": diagnostic.restriction_defect,
        "restricted_hermiticity_defect": diagnostic.restricted_hermiticity_defect,
        "restricted_unitarity_defect": diagnostic.restricted_unitarity_defect,
        "subspace_orthonormality_defect": diagnostic.subspace_orthonormality_defect,
        "commutator_defect": diagnostic.commutator_defect,
    }


def symmetry_experiment_result_to_json_dict(result: SymmetryExperimentResult) -> dict:
    payload = level0_experiment_result_to_json_dict(result.base)
    payload["schema_version"] = SYMMETRY_JSON_SCHEMA_VERSION
    payload["timings"]["symmetry_operators_build_seconds"] = result.symmetry_operators_build_seconds
    payload["timings"]["symmetry_diagnostics_seconds"] = result.symmetry_diagnostics_seconds

    degeneracy = result.base.report.spectrum.degeneracy
    payload["symmetry"] = {
        "solver_method": result.base.report.spectrum.method,
        "dimension": result.base.report.dimension,
        "published_eigenvalues": result.base.report.spectrum.computed_eigenvalues,
        "operators": list(SYMMETRY_OPERATOR_NAMES),
        "diagnostics": [_diagnostic_to_json(diagnostic, degeneracy) for diagnostic in result.diagnostics],
    }
    return payload
