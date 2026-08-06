"""Cosmobox Level1B: gauge-invariant relational correlators.

Lot 1B-1 only (paths, transporters, dressed matter operators and their
matrix assembly). Reuses Level0's validated primitives (lattice, encoding,
operators, hamiltonian.build_key_index/validate_key_index) without
modification, per docs/level1-implementation-design.md section 2.1.
"""

from .matter import apply_dressed_matter, build_dressed_matter_matrix
from .paths import OrientedPath, invert_path, make_oriented_path, minimal_paths
from .transporters import apply_transporter

__all__ = [
    "OrientedPath",
    "apply_dressed_matter",
    "apply_transporter",
    "build_dressed_matter_matrix",
    "invert_path",
    "make_oriented_path",
    "minimal_paths",
]
