"""Level0: exact finite gauge model (geometry, encoding, physical basis, Hamiltonian, reports, experiments).

Public API surface for external use. Internal helpers (module-private,
prefixed with an underscore -- e.g. hamiltonian._apply_plaquette,
hamiltonian._assemble_csr, hamiltonian._row_for_key,
hamiltonian._canonical_csr, reports._term_statistics,
reports._eigenpair_diagnostic, reports._SpectrumComputation,
reports._compute_spectrum, experiments._canonical_config_payload,
symmetries._one_body_flavor_operator, symmetries._row_for_key,
symmetries._assemble_csr) are intentionally not re-exported here.
"""

from .basis import BasisReport, SectorReport, build_basis
from .degeneracy import DegeneracyReport, SpectralLevelGroup, analyze_spectral_degeneracies
from .experiments import (
    Level0Experiment,
    Level0ExperimentResult,
    compute_config_fingerprint,
    dump_level0_experiment_result_json,
    level0_experiment_config_to_json_dict,
    level0_experiment_result_to_json_dict,
    run_level0_experiment,
)
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
from .symmetries import (
    OperatorKind,
    SymmetrySectorDiagnostic,
    analyze_symmetry_in_subspaces,
    build_flavor_casimir,
    build_flavor_generators,
)

__all__ = [
    "BasisReport",
    "DegeneracyReport",
    "EigenpairDiagnostic",
    "HamiltonianParameters",
    "HamiltonianTerms",
    "Level0Experiment",
    "Level0ExperimentResult",
    "Level0Report",
    "OperatorKind",
    "SectorReport",
    "SpectralLevelGroup",
    "SpectrumOptions",
    "SpectrumReport",
    "SymmetrySectorDiagnostic",
    "TermExpectations",
    "TermStatistics",
    "analyze_spectral_degeneracies",
    "analyze_symmetry_in_subspaces",
    "build_basis",
    "build_flavor_casimir",
    "build_flavor_generators",
    "build_hamiltonian_terms",
    "build_key_index",
    "build_lattice",
    "build_level0_report",
    "compute_config_fingerprint",
    "doubled_gauss_vector",
    "dump_level0_experiment_result_json",
    "gauss_vector",
    "is_physical",
    "level0_experiment_config_to_json_dict",
    "level0_experiment_result_to_json_dict",
    "run_level0_experiment",
]
