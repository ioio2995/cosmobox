"""Cosmobox Level1B: gauge-invariant relational correlators.

Lots 1B-1 (paths, transporters, dressed matter operators and their matrix
assembly) and 1B-2 (local charge/flavor observables and pure-state
correlators). Reuses Level0's validated primitives (lattice, encoding,
operators, hamiltonian.build_key_index/validate_key_index) without
modification, per docs/levels/level1/implementation-design.md section 2.1.
"""

from .local_observables import (
    FLAVOR_COMPONENTS,
    NORMALIZATION_FLOOR,
    NormalizedMoment,
    build_local_charge_operator,
    build_local_flavor_generator,
    build_local_flavor_generators,
    charge_correlator_connected,
    charge_correlator_raw,
    connected_moment,
    expectation_value,
    flavor_correlator_connected,
    flavor_correlator_raw,
    local_charge_product,
    local_flavor_dot_product,
    normalized_charge_correlator,
    raw_moment,
)
from .matter import apply_dressed_matter, build_dressed_matter_matrix
from .paths import OrientedPath, invert_path, make_oriented_path, minimal_paths
from .restricted import (
    COMPLETE_MULTIPLET,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    build_restricted_operator,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
    extract_group_state,
)
from .transporters import apply_transporter

__all__ = [
    "COMPLETE_MULTIPLET",
    "FLAVOR_COMPONENTS",
    "NORMALIZATION_FLOOR",
    "NormalizedMoment",
    "OrientedPath",
    "PARTIAL_SUBSPACE",
    "SpectralGroupState",
    "apply_dressed_matter",
    "apply_transporter",
    "build_dressed_matter_matrix",
    "build_local_charge_operator",
    "build_local_flavor_generator",
    "build_local_flavor_generators",
    "build_restricted_operator",
    "canonical_multiplet_expectation",
    "charge_correlator_connected",
    "charge_correlator_raw",
    "connected_moment",
    "expectation_value",
    "exploratory_partial_subspace_mean",
    "extract_group_state",
    "flavor_correlator_connected",
    "flavor_correlator_raw",
    "invert_path",
    "local_charge_product",
    "local_flavor_dot_product",
    "make_oriented_path",
    "minimal_paths",
    "normalized_charge_correlator",
    "raw_moment",
]
