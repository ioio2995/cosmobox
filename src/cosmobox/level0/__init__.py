"""Level0: exact finite gauge model (geometry, encoding, physical basis, Hamiltonian).

Public API surface for external use. Internal helpers (module-private,
prefixed with an underscore -- e.g. hamiltonian._apply_plaquette,
hamiltonian._assemble_csr, hamiltonian._row_for_key,
hamiltonian._canonical_csr) are intentionally not re-exported here.
"""

from .basis import BasisReport, SectorReport, build_basis
from .gauge import doubled_gauss_vector, gauss_vector, is_physical
from .hamiltonian import HamiltonianTerms, build_hamiltonian_terms, build_key_index
from .lattice import build_lattice
from .params import HamiltonianParameters

__all__ = [
    "BasisReport",
    "HamiltonianParameters",
    "HamiltonianTerms",
    "SectorReport",
    "build_basis",
    "build_hamiltonian_terms",
    "build_key_index",
    "build_lattice",
    "doubled_gauss_vector",
    "gauss_vector",
    "is_physical",
]
