"""Gauge-invariant dressed matter operator O_ij^{alpha,beta}[P] = c^dagger_{i,alpha} W_P c_{j,beta}.

Application order on a ket (right to left, per
docs/level1-implementation-design.md section 4.6): annihilate flavor beta
at node j = path.destination; apply W_P; create flavor alpha at node
i = path.source. Reduces to c^dagger_{i,alpha} c_{i,beta} for the empty
path (section 4.7) through the same code path -- zero transporter steps is
a no-op, no special-cased branch.

Derivation of the transporter order: for O_ij[P], c_j acts first on a ket,
annihilating at j = v_l. The transporter must then carry the resulting
state back toward i = v_0, one edge at a time -- so the LAST path step
(nearest j) applies first, and the FIRST step (nearest i) applies last,
immediately before c^dagger_i. This is the same order convention already
used for the closed plaquette loop in
cosmobox.level0.hamiltonian._apply_plaquette (W_p is also applied by
iterating reversed(steps)), and is consistent with H_hop's single-edge
convention c^dagger_i U_e c_j (docs/physical-model.md): a length-1 path
reduces to exactly that formula, with no ordering ambiguity to resolve.

Basis closure (Level0's T2 practice, reused here rather than an arbitrary
generic RuntimeError): a nonzero transition whose resulting key is absent
from the supplied key_index is an invariant violation and raises
RuntimeError with the same "invariant violation, not a state to silently
drop" wording already used by cosmobox.level0.hamiltonian._row_for_key and
cosmobox.level0.symmetries._row_for_key.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.hamiltonian import validate_key_index
from cosmobox.level0.lattice import Lattice
from cosmobox.level0.operators import OperatorResult, annihilate, create

from .paths import OrientedPath
from .transporters import apply_transporter


def apply_dressed_matter(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    key: np.uint64,
    path: OrientedPath,
    alpha: int,
    beta: int,
    *,
    key_index: dict[int, int] | None = None,
) -> OperatorResult | None:
    """O_ij^{alpha,beta}[P] |key>, with i = path.source, j = path.destination.

    The final amplitude is the explicit product, via a single accumulator,
    of the annihilation amplitude, every individual link-transport
    amplitude along the path (apply_transporter's own return value is
    itself already that exact product, accumulated the same way -- see
    transporters.py), and the creation amplitude. Returns None as soon as
    any elementary step has an exactly-zero amplitude.

    When key_index is provided, a nonzero result whose key is absent from
    key_index raises RuntimeError (T2-style invariant violation).
    """
    amplitude = complex(1.0, 0.0)

    annihilated = annihilate(lattice, n_flavors, spin, key, path.destination, beta)
    if annihilated is None:
        return None
    amplitude *= annihilated.amplitude

    transported = apply_transporter(lattice, n_flavors, spin, annihilated.key, path)
    if transported is None:
        return None
    amplitude *= transported.amplitude  # already the explicit product of every link-transport amplitude

    created = create(lattice, n_flavors, spin, transported.key, path.source, alpha)
    if created is None:
        return None
    amplitude *= created.amplitude

    if key_index is not None and int(created.key) not in key_index:
        raise RuntimeError(
            f"the dressed matter operator O_ij[alpha={alpha},beta={beta}] for path {path.nodes} "
            f"applied to key {int(key):#x} produced key {int(created.key):#x}, which is not in "
            "the supplied key_index; this is an invariant violation, not a state to silently drop"
        )

    return OperatorResult(created.key, amplitude)


def build_dressed_matter_matrix(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    path: OrientedPath,
    alpha: int,
    beta: int,
) -> sp.csr_matrix:
    """Assemble O_ij^{alpha,beta}[P] as a sparse matrix over the basis
    (keys, key_index). Every nonzero transition must land in key_index --
    apply_dressed_matter's closure check is always exercised here."""
    validate_key_index(keys, key_index)

    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []
    for col, key in enumerate(keys):
        result = apply_dressed_matter(lattice, n_flavors, spin, key, path, alpha, beta, key_index=key_index)
        if result is not None:
            rows.append(key_index[int(result.key)])
            cols.append(col)
            values.append(result.amplitude)

    row_array = np.asarray(rows, dtype=np.int32)
    col_array = np.asarray(cols, dtype=np.int32)
    value_array = np.asarray(values, dtype=np.complex128)
    coo = sp.coo_matrix((value_array, (row_array, col_array)), shape=(dim, dim))
    return coo.tocsr()
