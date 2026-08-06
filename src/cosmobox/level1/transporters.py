"""Application of the path transporter W_P to a canonical Level0 key.

W_P = U_{e_0}^{s_0} . U_{e_1}^{s_1} . ... . U_{e_{l-1}}^{s_{l-1}} (product in
path-step order), so applying it to a ket goes right to left: the LAST
step of the path acts first, the FIRST step acts last. This is exactly the
"reversed(steps)" pattern already used by
cosmobox.level0.hamiltonian._apply_plaquette for W_p. The full derivation
(telescoping-divergence argument, consistency with H_hop's single-edge
convention) is documented once in matter.py's module docstring.

Only the validated Level0 link primitives are used (transport = U_e,
transport_dagger = U_e^dagger) -- no additional normalization is applied
anywhere in this module (nu_S = 1, frozen).
"""

from __future__ import annotations

import numpy as np

from cosmobox.level0.lattice import Lattice
from cosmobox.level0.operators import OperatorResult, transport, transport_dagger

from .paths import OrientedPath


def _validate_steps_against_lattice(lattice: Lattice, path: OrientedPath) -> None:
    """Reject any step whose sense is not exactly +1/-1, or whose
    edge_index is out of range for THIS lattice.

    OrientedPath.__post_init__ already rejects a bad sense or a negative
    edge_index unconditionally (lattice-independent), so those branches
    are unreachable through a normally constructed path -- kept here
    anyway as an explicit, self-contained guard: apply_transporter must
    never silently treat a malformed sense (e.g. 0 or 2) as "reversed"
    just because it happens to differ from +1, and must never let a
    corrupted or hand-assembled path (e.g. via object.__setattr__ on a
    frozen instance) through unchecked. The upper bound on edge_index is
    genuinely lattice-dependent and can only be checked here.
    """
    n_edges = len(lattice.edges)
    for index, (edge_index, sense) in enumerate(path.steps):
        if sense not in (1, -1):
            raise ValueError(f"path step {index} has sense={sense!r}, expected +1 or -1")
        if not (0 <= edge_index < n_edges):
            raise ValueError(
                f"path step {index} references edge_index={edge_index}, out of range "
                f"[0, {n_edges}) for lattice {lattice.name!r}"
            )


def apply_transporter(
    lattice: Lattice, n_flavors: int, spin: int, key: np.uint64, path: OrientedPath
) -> OperatorResult | None:
    """W_P |key>.

    None if any step's amplitude is exactly zero due to link truncation
    (S saturation) -- propagated directly from transport/transport_dagger,
    never re-derived. The empty path (path.steps == ()) returns the key
    unchanged with amplitude 1 (W_P = I), the same contract for every path
    length, no special case.

    Raises ValueError before applying anything if any step is malformed
    (see _validate_steps_against_lattice).
    """
    _validate_steps_against_lattice(lattice, path)

    current_key = key
    amplitude = complex(1.0, 0.0)
    for edge_index, sense in reversed(path.steps):
        step = transport if sense == 1 else transport_dagger
        result = step(lattice, n_flavors, spin, current_key, edge_index)
        if result is None:
            return None
        current_key = result.key
        amplitude *= result.amplitude
    return OperatorResult(current_key, amplitude)
