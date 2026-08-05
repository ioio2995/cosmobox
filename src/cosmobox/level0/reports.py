"""Numeric description of an already-built Level0 model (basis + Hamiltonian terms).

reports.py analyzes a BasisReport and HamiltonianTerms that the caller has
already constructed -- it never builds the basis or the Hamiltonian itself
(that stays basis.py's and hamiltonian.py's job). It validates that the
objects it was handed are mutually consistent, reports combinatorial-exact
counts, direct matrix diagnostics (density, norms, Hermiticity defect), and
-- only when the dimension makes it reasonable, per an explicit policy --
a numeric spectral diagnostic (eigenvalues, residuals, per-term energy
expectations, spectral gap). No physical interpretation beyond that.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import ArpackNoConvergence, eigsh

from .basis import BasisReport
from .charges import normalize_external_charges
from .encoding import validate_capacity, validate_spin
from .gauge import is_physical
from .hamiltonian import HamiltonianTerms
from .lattice import Lattice
from .params import HamiltonianParameters

FIXED_REPORT_SEED = 0
"""Default seed for the deterministic v0 used by the sparse (eigsh) spectral path."""

_TERM_NAMES = ("dot", "hopping", "electric", "magnetic", "total")


@dataclass(frozen=True, slots=True)
class SpectrumOptions:
    max_dense_dimension: int = 2000
    max_sparse_dimension: int = 200_000
    n_eigenvalues: int = 6
    tolerance: float = 1e-10
    max_iterations: int | None = None
    force: bool = False
    seed: int = FIXED_REPORT_SEED

    def __post_init__(self) -> None:
        if self.max_dense_dimension < 0:
            raise ValueError(f"max_dense_dimension must be >= 0, got {self.max_dense_dimension}")
        if self.max_sparse_dimension < 0:
            raise ValueError(f"max_sparse_dimension must be >= 0, got {self.max_sparse_dimension}")
        if self.max_dense_dimension > self.max_sparse_dimension:
            raise ValueError(
                f"max_dense_dimension ({self.max_dense_dimension}) must be <= "
                f"max_sparse_dimension ({self.max_sparse_dimension})"
            )
        if self.n_eigenvalues < 1:
            raise ValueError(f"n_eigenvalues must be >= 1, got {self.n_eigenvalues}")
        if not (math.isfinite(self.tolerance) and self.tolerance > 0):
            raise ValueError(f"tolerance must be positive and finite, got {self.tolerance}")
        if self.max_iterations is not None and self.max_iterations <= 0:
            raise ValueError(f"max_iterations must be positive when provided, got {self.max_iterations}")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError(f"seed must be a non-negative int, got {self.seed!r}")


@dataclass(frozen=True, slots=True)
class TermExpectations:
    dot: float
    hopping: float
    electric: float
    magnetic: float
    total: float


@dataclass(frozen=True, slots=True)
class TermStatistics:
    name: str
    nnz: int
    density: float
    hermiticity_defect: float
    frobenius_norm: float


@dataclass(frozen=True, slots=True)
class EigenpairDiagnostic:
    index: int
    eigenvalue: float
    residual_norm: float
    term_expectations: TermExpectations


@dataclass(frozen=True, slots=True)
class SpectrumReport:
    status: str  # "computed" | "not_computed" | "failed"
    method: str | None  # "direct" | "dense" | "sparse_eigsh" | None
    requested_eigenvalues: int
    computed_eigenvalues: int
    tolerance: float | None
    reason: str | None
    eigenpairs: tuple[EigenpairDiagnostic, ...]
    spectral_gap: float | None


@dataclass(frozen=True, slots=True)
class Level0Report:
    """external_charges and parameters are provenance *declared* by the
    caller, not verified against the origin of `terms`: reports.py checks
    every basis key is physical for the declared external_charges (an
    independent, real check), and that params.J/params.h have the right
    length for `lattice`, but it cannot prove either object is literally
    the one used to build `terms` -- that identity is the caller's
    responsibility, since reports.py never (re)builds the matrices itself.
    """

    lattice_name: str
    n_flavors: int
    spin: int
    external_charges: tuple[Fraction, ...]
    dimension: int
    sector_count: int
    excluded_sector_count: int
    mean_flux_configs_per_occupation: float
    max_flux_configs_per_occupation: int
    terms: tuple[TermStatistics, ...]
    spectrum: SpectrumReport
    spectrum_options: SpectrumOptions
    parameters: HamiltonianParameters


def _term_statistics(name: str, matrix: sp.csr_matrix, dimension: int) -> TermStatistics:
    nnz = matrix.nnz
    density = (nnz / dimension**2) if dimension > 0 else 0.0

    difference = (matrix - matrix.conj().T).tocsr()
    difference.eliminate_zeros()
    hermiticity_defect = float(np.max(np.abs(difference.data))) if difference.nnz else 0.0

    frobenius_norm = float(np.sqrt(np.sum(np.abs(matrix.data) ** 2))) if matrix.nnz else 0.0

    return TermStatistics(
        name=name, nnz=nnz, density=density, hermiticity_defect=hermiticity_defect, frobenius_norm=frobenius_norm
    )


def _eigenpair_diagnostic(
    index: int,
    eigenvalue: float,
    eigenvector: np.ndarray,
    terms: HamiltonianTerms,
    tolerance: float,
) -> EigenpairDiagnostic:
    if not math.isfinite(eigenvalue):
        raise ValueError(f"eigenvalue at index {index} is not finite: {eigenvalue}")

    psi = np.asarray(eigenvector, dtype=np.complex128)
    if not np.all(np.isfinite(psi)):
        raise ValueError(f"eigenvector at index {index} contains non-finite entries")

    residual = terms.total @ psi - eigenvalue * psi
    residual_norm = float(np.linalg.norm(residual))
    if not math.isfinite(residual_norm):
        raise ValueError(f"residual norm at index {index} is not finite: {residual_norm}")

    def _expectation(name: str, matrix: sp.csr_matrix) -> float:
        value = complex(np.vdot(psi, matrix @ psi))
        if not (math.isfinite(value.real) and math.isfinite(value.imag)):
            raise ValueError(f"<psi|H_{name}|psi> at eigenpair {index} is not finite: {value}")
        if abs(value.imag) > tolerance:
            raise ValueError(
                f"<psi|H_{name}|psi> has a non-negligible imaginary part {value.imag} at eigenpair {index}"
            )
        return float(value.real)

    term_expectations = TermExpectations(
        dot=_expectation("dot", terms.dot),
        hopping=_expectation("hopping", terms.hopping),
        electric=_expectation("electric", terms.electric),
        magnetic=_expectation("magnetic", terms.magnetic),
        total=_expectation("total", terms.total),
    )

    # E_dot + E_hop + E_E + E_B ~= E_total ~= eigenvalue -- an invariant this
    # module must enforce itself, not something only the test suite checks.
    component_sum = (
        term_expectations.dot + term_expectations.hopping + term_expectations.electric + term_expectations.magnetic
    )
    scale = max(1.0, abs(component_sum), abs(term_expectations.total), abs(eigenvalue))
    allowed = tolerance * scale
    if abs(component_sum - term_expectations.total) > allowed:
        raise ValueError(
            f"sum of term expectations ({component_sum}) does not match <psi|H_total|psi> "
            f"({term_expectations.total}) at eigenpair {index}: "
            f"|diff|={abs(component_sum - term_expectations.total)} > allowed={allowed}"
        )
    if abs(term_expectations.total - eigenvalue) > allowed:
        raise ValueError(
            f"<psi|H_total|psi> ({term_expectations.total}) does not match the eigenvalue ({eigenvalue}) "
            f"at eigenpair {index}: |diff|={abs(term_expectations.total - eigenvalue)} > allowed={allowed}"
        )

    return EigenpairDiagnostic(
        index=index,
        eigenvalue=float(eigenvalue),
        residual_norm=residual_norm,
        term_expectations=term_expectations,
    )


def _spectral_gap(eigenpairs: tuple[EigenpairDiagnostic, ...]) -> float | None:
    if len(eigenpairs) < 2:
        return None
    return eigenpairs[1].eigenvalue - eigenpairs[0].eigenvalue


def _require_hermitian_total(term_stats: tuple[TermStatistics, ...], options: SpectrumOptions) -> None:
    """Refuse eigh/eigsh on a non-Hermitian H_total: a solver-input-consistency issue, not a solver failure."""
    total_stats = term_stats[-1]  # "total" is always last, per _TERM_NAMES order
    if total_stats.hermiticity_defect > options.tolerance:
        raise ValueError(
            f"H_total is not Hermitian within tolerance: defect={total_stats.hermiticity_defect}, "
            f"tolerance={options.tolerance}"
        )


def _direct_spectrum_dimension_zero(options: SpectrumOptions) -> SpectrumReport:
    return SpectrumReport(
        status="computed",
        method="direct",
        requested_eigenvalues=options.n_eigenvalues,
        computed_eigenvalues=0,
        tolerance=None,
        reason=None,
        eigenpairs=(),
        spectral_gap=None,
    )


def _direct_spectrum_dimension_one(terms: HamiltonianTerms, options: SpectrumOptions) -> SpectrumReport:
    raw_eigenvalue = complex(terms.total[0, 0])
    if abs(raw_eigenvalue.imag) > options.tolerance:
        raise ValueError(
            f"H_total[0,0] has a non-negligible imaginary part {raw_eigenvalue.imag} for a 1-dimensional system"
        )
    psi = np.array([1.0 + 0j])
    eigenpair = _eigenpair_diagnostic(0, raw_eigenvalue.real, psi, terms, options.tolerance)
    return SpectrumReport(
        status="computed",
        method="direct",
        requested_eigenvalues=options.n_eigenvalues,
        computed_eigenvalues=1,
        tolerance=options.tolerance,
        reason=None,
        eigenpairs=(eigenpair,),
        spectral_gap=None,
    )


def _dense_spectrum(terms: HamiltonianTerms, dimension: int, options: SpectrumOptions) -> SpectrumReport:
    eigenvalues, eigenvectors = np.linalg.eigh(terms.total.toarray())
    k = min(options.n_eigenvalues, dimension)
    eigenpairs = tuple(
        _eigenpair_diagnostic(index, eigenvalues[index], eigenvectors[:, index], terms, options.tolerance)
        for index in range(k)
    )
    return SpectrumReport(
        status="computed",
        method="dense",
        requested_eigenvalues=options.n_eigenvalues,
        computed_eigenvalues=len(eigenpairs),
        tolerance=options.tolerance,
        reason=None,
        eigenpairs=eigenpairs,
        spectral_gap=_spectral_gap(eigenpairs),
    )


def _sparse_spectrum(terms: HamiltonianTerms, dimension: int, options: SpectrumOptions) -> SpectrumReport:
    k = min(options.n_eigenvalues, dimension - 1)
    rng = np.random.default_rng(options.seed)
    v0 = rng.standard_normal(dimension)
    v0 = v0 / np.linalg.norm(v0)

    try:
        eigenvalues, eigenvectors = eigsh(
            terms.total, k=k, which="SA", v0=v0, tol=options.tolerance, maxiter=options.max_iterations
        )
    except ArpackNoConvergence as exc:
        return SpectrumReport(
            status="failed",
            method="sparse_eigsh",
            requested_eigenvalues=options.n_eigenvalues,
            computed_eigenvalues=0,
            tolerance=options.tolerance,
            reason=f"ARPACK did not converge: {exc}",
            eigenpairs=(),
            spectral_gap=None,
        )

    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    eigenpairs = tuple(
        _eigenpair_diagnostic(index, eigenvalues[index], eigenvectors[:, index], terms, options.tolerance)
        for index in range(len(eigenvalues))
    )
    return SpectrumReport(
        status="computed",
        method="sparse_eigsh",
        requested_eigenvalues=options.n_eigenvalues,
        computed_eigenvalues=len(eigenpairs),
        tolerance=options.tolerance,
        reason=None,
        eigenpairs=eigenpairs,
        spectral_gap=_spectral_gap(eigenpairs),
    )


def build_level0_report(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    basis: BasisReport,
    terms: HamiltonianTerms,
    params: HamiltonianParameters,
    *,
    external_charges: Sequence[object] | None = None,
    spectrum_options: SpectrumOptions | None = None,
) -> Level0Report:
    """Analyze an already-built (basis, terms) pair. Never constructs either."""
    options = spectrum_options if spectrum_options is not None else SpectrumOptions()

    validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges)

    dimension = len(basis.keys)

    for name, matrix in zip(
        _TERM_NAMES, (terms.dot, terms.hopping, terms.electric, terms.magnetic, terms.total)
    ):
        if matrix.shape != (dimension, dimension):
            raise ValueError(
                f"{name} has shape {matrix.shape}, expected ({dimension}, {dimension}) to match basis.keys"
            )

    key_ints = [int(key) for key in basis.keys]
    if len(set(key_ints)) != len(key_ints):
        raise ValueError("basis.keys contains duplicate keys")

    external = normalize_external_charges(n_nodes, external_charges)
    for key in basis.keys:
        if not is_physical(lattice, n_flavors, spin, key, external_charges=external):
            raise ValueError(
                f"basis key {int(key):#x} is not physical for the declared external_charges; "
                "basis and external_charges are inconsistent"
            )

    # params is declared provenance (like external_charges): reports.py cannot
    # prove it is the exact object used to build `terms`, only catch a
    # manifest inconsistency in the shapes it does control.
    if len(params.J) != n_nodes:
        raise ValueError(f"params.J has {len(params.J)} entries, expected {n_nodes}")
    if len(params.h) != n_nodes:
        raise ValueError(f"params.h has {len(params.h)} entries, expected {n_nodes}")

    term_stats = tuple(
        _term_statistics(name, matrix, dimension)
        for name, matrix in zip(
            _TERM_NAMES, (terms.dot, terms.hopping, terms.electric, terms.magnetic, terms.total)
        )
    )

    if dimension == 0:
        spectrum = _direct_spectrum_dimension_zero(options)
    elif dimension == 1:
        spectrum = _direct_spectrum_dimension_one(terms, options)
    elif dimension <= options.max_dense_dimension:
        _require_hermitian_total(term_stats, options)
        spectrum = _dense_spectrum(terms, dimension, options)
    elif options.force or dimension <= options.max_sparse_dimension:
        _require_hermitian_total(term_stats, options)
        spectrum = _sparse_spectrum(terms, dimension, options)
    else:
        spectrum = SpectrumReport(
            status="not_computed",
            method=None,
            requested_eigenvalues=options.n_eigenvalues,
            computed_eigenvalues=0,
            tolerance=None,
            reason=(
                f"dimension {dimension} exceeds max_sparse_dimension={options.max_sparse_dimension} "
                f"(max_dense_dimension={options.max_dense_dimension}); pass force=True to override"
            ),
            eigenpairs=(),
            spectral_gap=None,
        )

    return Level0Report(
        lattice_name=lattice.name,
        n_flavors=n_flavors,
        spin=spin,
        external_charges=external,
        dimension=dimension,
        sector_count=len(basis.sectors),
        excluded_sector_count=len(basis.excluded_sectors),
        mean_flux_configs_per_occupation=basis.mean_flux_configs_per_occupation,
        max_flux_configs_per_occupation=basis.max_flux_configs_per_occupation,
        terms=term_stats,
        spectrum=spectrum,
        spectrum_options=options,
        parameters=params,
    )
