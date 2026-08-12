"""Level2 real full-spectrum preflight: technical invariants only.

Lot L2-D4-REAL-PREFLIGHT. Rebuilds each of the six frozen Level2 cases
through exactly the same Level0 construction path as
cosmobox.level2.execution.run_case (build_lattice -> build_basis ->
build_key_index -> build_hamiltonian_terms ->
build_level0_report_with_eigenvectors, with
SpectrumOptions(n_eigenvalues=dimension)), reusing execution.py's own
frozen parameter derivation verbatim (REFERENCE_N_FLAVORS,
REFERENCE_EXTERNAL_CHARGES, build_reference_hamiltonian_parameters) --
J/h/t/g_E/K/n_flavors/external_charges are never redefined here.

Stops immediately after Level0Report is produced. Never calls
adapter.build_case_operators, adapter.build_case_multiplet_profile, any
Level1 correlator function, or orchestration.analyze_case_metric /
compare_geometry -- no C_TT_conn, no rho_QQ, no Level2 metric, no
regime/contrast/shape-descriptor/taxonomy is ever computed or inspected
anywhere in this module. The eigenvectors returned by
build_level0_report_with_eigenvectors are discarded immediately in
build_case_level0_report -- never stored, returned, or passed onward.

This is a technical, non-interpretive check of already-known spectral
invariants (Hilbert-space dimension, solver method, full-spectrum
completeness, spectral group count, partial-subspace count, multiplicity
coverage) against the L2-A1 reference values already frozen in
docs/governance/current-task.md
(cosmobox.level2.execution.L2_A1_PREFLIGHT_REFERENCE) -- not a normative
Level2 campaign, and no individual energy, eigenvector, or observable
value is ever reported.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.reports import Level0Report, SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level2 import execution
from cosmobox.level2.execution import CaseSpec

PASS = "PASS"
FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class CasePreflightReport:
    """Technical preflight outcome for one case. Carries only structural
    spectral invariants -- no energy, no eigenvector, no observable
    value."""

    geometry: str
    spin: int
    dimension: int
    requested_eigenvalues: int
    returned_eigenpairs: int
    solver_method: str | None
    window_truncated: bool | None
    group_count: int
    partial_subspace_count: int
    multiplicity_sum: int
    expected_dimension: int
    expected_group_count: int
    status: str

    def __post_init__(self) -> None:
        if self.status not in (PASS, FAIL):
            raise ValueError(f"status must be one of ({PASS!r}, {FAIL!r}), got {self.status!r}")


def build_case_level0_report(spec: CaseSpec) -> Level0Report:
    """Exactly cosmobox.level2.execution.run_case's own Level0
    construction path, stopped immediately after Level0Report is
    produced -- never proceeds to adapter.build_case_operators/
    build_case_multiplet_profile or any D3 orchestration. Reuses
    execution.py's own frozen parameter derivation verbatim, never
    redefines it. The eigenvectors returned by
    build_level0_report_with_eigenvectors are discarded immediately: this
    function never stores or returns them."""
    lattice = build_lattice(spec.geometry)
    hamiltonian_params = execution.build_reference_hamiltonian_parameters(len(lattice.nodes))

    basis = build_basis(lattice, execution.REFERENCE_N_FLAVORS, spec.spin)
    dimension = len(basis.keys)
    key_index = build_key_index(basis.keys)

    terms = build_hamiltonian_terms(
        lattice, execution.REFERENCE_N_FLAVORS, spec.spin, basis.keys, key_index, hamiltonian_params
    )
    report, _eigenvectors = build_level0_report_with_eigenvectors(
        lattice,
        execution.REFERENCE_N_FLAVORS,
        spec.spin,
        basis,
        terms,
        hamiltonian_params,
        external_charges=execution.REFERENCE_EXTERNAL_CHARGES,
        spectrum_options=SpectrumOptions(n_eigenvalues=dimension),
    )
    return report


def evaluate_report(
    report: Level0Report,
    *,
    expected_dimension: int,
    expected_group_count: int,
    geometry: str,
    spin: int,
) -> CasePreflightReport:
    """Pure function of an already-built Level0Report: derives the
    technical preflight invariants and the PASS/FAIL verdict against the
    supplied L2-A1 reference values. No Hamiltonian/spectrum computation
    happens here -- `report` is assumed already produced elsewhere."""
    degeneracy = report.spectrum.degeneracy
    groups = degeneracy.groups if degeneracy is not None else ()
    window_truncated = degeneracy.window_truncated if degeneracy is not None else None

    partial_subspace_count = sum(1 for group in groups if group.lower_bound_only)
    multiplicity_sum = sum(group.multiplicity_observed for group in groups)

    ok = (
        report.dimension == expected_dimension
        and report.spectrum.requested_eigenvalues == report.dimension
        and report.spectrum.computed_eigenvalues == report.dimension
        and report.spectrum.method == "dense"
        and window_truncated is False
        and len(groups) == expected_group_count
        and partial_subspace_count == 0
        and multiplicity_sum == report.dimension
    )

    return CasePreflightReport(
        geometry=geometry,
        spin=spin,
        dimension=report.dimension,
        requested_eigenvalues=report.spectrum.requested_eigenvalues,
        returned_eigenpairs=report.spectrum.computed_eigenvalues,
        solver_method=report.spectrum.method,
        window_truncated=window_truncated,
        group_count=len(groups),
        partial_subspace_count=partial_subspace_count,
        multiplicity_sum=multiplicity_sum,
        expected_dimension=expected_dimension,
        expected_group_count=expected_group_count,
        status=PASS if ok else FAIL,
    )


def run_case_preflight(spec: CaseSpec) -> CasePreflightReport:
    """Real Level0 construction (build_case_level0_report) for `spec`,
    evaluated against its L2_A1_PREFLIGHT_REFERENCE values."""
    expected_dimension, expected_group_count = execution.L2_A1_PREFLIGHT_REFERENCE[(spec.geometry, spec.spin)]
    report = build_case_level0_report(spec)
    return evaluate_report(
        report,
        expected_dimension=expected_dimension,
        expected_group_count=expected_group_count,
        geometry=spec.geometry,
        spin=spec.spin,
    )


def run_all_cases_preflight() -> tuple[CasePreflightReport, ...]:
    """The six frozen Level2 cases, in
    cosmobox.level2.execution.build_all_reference_case_specs's own order.
    Performs six real diagonalizations -- not intended for routine
    automated test runs (see tests/scripts/level2_preflight, which tests
    evaluate_report only, on synthetic Level0Report objects)."""
    return tuple(run_case_preflight(spec) for spec in execution.build_all_reference_case_specs())


def all_cases_pass(reports: tuple[CasePreflightReport, ...]) -> bool:
    return all(report.status == PASS for report in reports)


def _format_report_line(report: CasePreflightReport) -> str:
    return (
        f"{report.geometry:8s} S={report.spin}  "
        f"D={report.dimension:5d} (expected {report.expected_dimension:5d})  "
        f"eigenpairs={report.returned_eigenpairs:5d}/{report.requested_eigenvalues:<5d}  "
        f"method={str(report.solver_method):10s}  "
        f"window_truncated={str(report.window_truncated):5s}  "
        f"groups={report.group_count:4d} (expected {report.expected_group_count:4d})  "
        f"partial_subspace={report.partial_subspace_count}  "
        f"multiplicity_sum={report.multiplicity_sum:5d}  "
        f"status={report.status}"
    )


def main() -> int:
    reports = run_all_cases_preflight()
    for report in reports:
        print(_format_report_line(report))
    overall = all_cases_pass(reports)
    print(f"ALL_6_CASES_PASS = {'YES' if overall else 'NO'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
