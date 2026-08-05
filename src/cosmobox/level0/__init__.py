"""Level0: exact finite gauge model (geometry, encoding, physical basis, Hamiltonian, reports).

Public API surface for external use. Internal helpers (module-private,
prefixed with an underscore -- e.g. hamiltonian._apply_plaquette,
hamiltonian._assemble_csr, hamiltonian._row_for_key,
hamiltonian._canonical_csr, reports._term_statistics,
reports._eigenpair_diagnostic) are intentionally not re-exported here.
"""

from .basis import BasisReport, SectorReport, build_basis
from .gauge import doubled_gauss_vector, gauss_vector, is_physical
from .hamiltonian import HamiltonianTerms, build_hamiltonian_terms, build_key_index
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

__all__ = [
    "BasisReport",
    "EigenpairDiagnostic",
    "HamiltonianParameters",
    "HamiltonianTerms",
    "Level0Report",
    "SectorReport",
    "SpectrumOptions",
    "SpectrumReport",
    "TermExpectations",
    "TermStatistics",
    "build_basis",
    "build_hamiltonian_terms",
    "build_key_index",
    "build_lattice",
    "build_level0_report",
    "doubled_gauss_vector",
    "gauss_vector",
    "is_physical",
]
