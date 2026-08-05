"""Symmetry operators on the exact physical basis, and restricted-subspace diagnostics.

Lot 6B.1: global flavor-SU(2) generators (T_x, T_y, T_z), their Casimir
(T^2), and analyze_symmetry_in_subspaces, which restricts an already-built
operator to each SpectralLevelGroup of an already-computed DegeneracyReport
and reports how well the subspace is preserved and how the operator
behaves there. It never diagonalizes anything itself -- eigenvectors are
supplied by the caller (reports.py's spectral computation stays internal
to reports.py; this module does not import its private helpers).

Flavor mixing is site-local (c^dagger_{i,alpha} c_{i,beta} moves a fermion
between flavors at the SAME node i, never between nodes and never
touching flux), so it leaves the total occupation n_{i0}+n_{i1} at every
site unchanged. Since Gauss's law G_i = sum_e eps_ie E_e - Q_i - q_i^ext
depends on occupation only through Q_i = sum_alpha n_{i,alpha} - 1 (not on
which flavor is occupied) and flavor mixing never touches E_e, T_x/T_y/T_z
map the physical basis into itself exactly like H_dot's off-diagonal
h-coupling does -- a transition landing outside key_index is therefore a
genuine T2-style invariant violation, not something to drop silently.

Lot 6B.2: geometric automorphisms (cyclic translation, reflection) via a
single shared _build_graph_automorphism_operator. Unlike the flavor
generators, these are not built by composing operators.annihilate/create:
a graph automorphism relabels every occupied mode SIMULTANEOUSLY, and the
resulting fermionic sign is the parity of the number of inversions needed
to re-sort the permuted occupied-mode sequence back into the canonical
increasing-index order the key encoding assumes -- a global sign, not the
local per-transposition JW-hop sign used elsewhere. E_e/U_e transform
according to whether the image edge keeps or reverses its stored
orientation (E_e -> E_image, U_e -> U_image if preserved; E_e -> -E_image,
U_e -> U_image^dagger if reversed) -- never by an "E -> -E under parity"
analogy. Flux conjugation (E -> -E alone, without a matching Q -> -Q) is
deliberately NOT built here: it does not preserve Gauss's law on its own
(Q_i is unchanged while div(E)_i flips sign), so it is not a well-defined
operator on the physical basis, and a combined charge-conjugation is
deferred to a later lot as a new physics convention.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np
import scipy.sparse as sp

from .charges import normalize_external_charges
from .degeneracy import DegeneracyReport
from .encoding import decode, encode
from .hamiltonian import validate_key_index
from .lattice import Lattice
from .operators import OperatorResult, annihilate, create

_PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)


def _row_for_key(key_index: dict[int, int], key: np.uint64) -> int:
    try:
        return key_index[int(key)]
    except KeyError as exc:
        raise RuntimeError(
            f"a flavor operator produced key {int(key):#x}, which is not in the physical basis; "
            "this is an invariant violation (T2-style), not a state to silently drop"
        ) from exc


def _assemble_csr(rows: list[int], cols: list[int], values: list[complex], dim: int) -> sp.csr_matrix:
    row_array = np.asarray(rows, dtype=np.int32)
    col_array = np.asarray(cols, dtype=np.int32)
    value_array = np.asarray(values, dtype=np.complex128)
    coo = sp.coo_matrix((value_array, (row_array, col_array)), shape=(dim, dim))
    return coo.tocsr()


def _one_body_flavor_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    matrix: np.ndarray,
) -> sp.csr_matrix:
    """sum_i sum_{alpha,beta} matrix[alpha, beta] c^dagger_{i,alpha} c_{i,beta}.

    Same composition pattern as hamiltonian.build_dot_term's h-coupling
    loop (annihilate(beta) then create(alpha), diagonal handled directly
    via read_occupation through annihilate/create's own None-on-empty
    behavior) -- reused here, not re-derived: the only new code is this
    assembly loop over nodes/keys, not the elementary fermionic actions.
    """
    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []

    for col, key in enumerate(keys):
        diagonal = 0j
        for node in lattice.nodes:
            for alpha in range(n_flavors):
                for beta in range(n_flavors):
                    coupling = matrix[alpha, beta]
                    if coupling == 0:
                        continue
                    intermediate = annihilate(lattice, n_flavors, spin, key, node, beta)
                    if intermediate is None:
                        continue
                    result = create(lattice, n_flavors, spin, intermediate.key, node, alpha)
                    if result is None:
                        continue
                    amplitude = coupling * intermediate.amplitude * result.amplitude
                    if alpha == beta:
                        # annihilate then create on the same occupied mode returns to `key`
                        # with amplitude 1 (same JW sign both times) -- always diagonal.
                        diagonal += amplitude
                        continue
                    row = _row_for_key(key_index, result.key)
                    rows.append(row)
                    cols.append(col)
                    values.append(amplitude)

        if diagonal != 0:
            rows.append(col)
            cols.append(col)
            values.append(diagonal)

    return _assemble_csr(rows, cols, values, dim)


def build_flavor_generators(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
) -> tuple[sp.csr_matrix, sp.csr_matrix, sp.csr_matrix]:
    """(T_x, T_y, T_z): global flavor-SU(2) generators.

    T^a = (1/2) sum_i sum_{alpha,beta} sigma^a_{alpha,beta} c^dagger_{i,alpha} c_{i,beta},
    with the standard Pauli convention. Defined only for n_flavors == 2
    (M=2, per D006) -- flavor SU(2) has no meaning for a different flavor
    count.
    """
    if n_flavors != 2:
        raise ValueError(
            f"flavor generators are only defined for n_flavors == 2 (M=2, per D006), got {n_flavors}"
        )
    validate_key_index(keys, key_index)
    return tuple(
        _one_body_flavor_operator(lattice, n_flavors, spin, keys, key_index, 0.5 * pauli)
        for pauli in (_PAULI_X, _PAULI_Y, _PAULI_Z)
    )


def build_flavor_casimir(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
) -> sp.csr_matrix:
    """T^2 = T_x^2 + T_y^2 + T_z^2, built from build_flavor_generators.

    A canonical construction rather than asking every caller to recompose
    tx @ tx + ty @ ty + tz @ tz themselves: the Casimir is a central
    observable of this lot.
    """
    tx, ty, tz = build_flavor_generators(lattice, n_flavors, spin, keys, key_index)
    return (tx @ tx + ty @ ty + tz @ tz).tocsr()


# ---------------------------------------------------------------------------
# Restricted-subspace diagnostics
# ---------------------------------------------------------------------------


class OperatorKind(str, Enum):
    HERMITIAN = "hermitian"
    UNITARY = "unitary"
    HERMITIAN_UNITARY = "hermitian_unitary"


_WANTS_HERMITICITY = (OperatorKind.HERMITIAN, OperatorKind.HERMITIAN_UNITARY)
_WANTS_UNITARITY = (OperatorKind.UNITARY, OperatorKind.HERMITIAN_UNITARY)


@dataclass(frozen=True, slots=True)
class SymmetrySectorDiagnostic:
    operator_name: str
    operator_kind: OperatorKind
    spectral_group_index: int
    restricted_eigenvalues: tuple[complex, ...]
    restriction_defect: float
    """||O*psi - psi*O_rest||_F / max(1, ||O*psi||_F): relative, not
    absolute -- scale-invariant under O -> c*O and comparable across
    operators of different magnitude (a Casimir vs. a single generator)."""
    restricted_hermiticity_defect: float | None
    restricted_unitarity_defect: float | None
    subspace_orthonormality_defect: float
    commutator_defect: float | None

    def __post_init__(self) -> None:
        if self.spectral_group_index < 0:
            raise ValueError(f"spectral_group_index must be >= 0, got {self.spectral_group_index}")

        for name, value in (
            ("restriction_defect", self.restriction_defect),
            ("subspace_orthonormality_defect", self.subspace_orthonormality_defect),
        ):
            if not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name} must be finite and >= 0, got {value}")

        wants_hermiticity = self.operator_kind in _WANTS_HERMITICITY
        if wants_hermiticity:
            if self.restricted_hermiticity_defect is None or not (
                math.isfinite(self.restricted_hermiticity_defect) and self.restricted_hermiticity_defect >= 0
            ):
                raise ValueError(
                    f"restricted_hermiticity_defect must be a finite value >= 0 for kind={self.operator_kind}, "
                    f"got {self.restricted_hermiticity_defect!r}"
                )
        elif self.restricted_hermiticity_defect is not None:
            raise ValueError(
                f"restricted_hermiticity_defect must be None for kind={self.operator_kind}, "
                f"got {self.restricted_hermiticity_defect!r}"
            )

        wants_unitarity = self.operator_kind in _WANTS_UNITARITY
        if wants_unitarity:
            if self.restricted_unitarity_defect is None or not (
                math.isfinite(self.restricted_unitarity_defect) and self.restricted_unitarity_defect >= 0
            ):
                raise ValueError(
                    f"restricted_unitarity_defect must be a finite value >= 0 for kind={self.operator_kind}, "
                    f"got {self.restricted_unitarity_defect!r}"
                )
        elif self.restricted_unitarity_defect is not None:
            raise ValueError(
                f"restricted_unitarity_defect must be None for kind={self.operator_kind}, "
                f"got {self.restricted_unitarity_defect!r}"
            )

        if self.commutator_defect is not None and not (
            math.isfinite(self.commutator_defect) and self.commutator_defect >= 0
        ):
            raise ValueError(f"commutator_defect must be None or finite and >= 0, got {self.commutator_defect!r}")

        for index, value in enumerate(self.restricted_eigenvalues):
            if not (math.isfinite(value.real) and math.isfinite(value.imag)):
                raise ValueError(f"restricted_eigenvalues[{index}] is not finite: {value}")


def _frobenius_norm_dense(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix))


def _frobenius_norm_sparse(matrix: sp.spmatrix) -> float:
    matrix = matrix.tocsr()
    return float(np.sqrt(np.sum(np.abs(matrix.data) ** 2))) if matrix.nnz else 0.0


def analyze_symmetry_in_subspaces(
    operator: sp.csr_matrix,
    operator_name: str,
    operator_kind: OperatorKind,
    eigenvectors: np.ndarray,
    degeneracy: DegeneracyReport,
    *,
    total: sp.csr_matrix | None = None,
) -> tuple[SymmetrySectorDiagnostic, ...]:
    """Restrict `operator` to each group of `degeneracy` and diagnose it there.

    `eigenvectors` (dimension x n_computed) and `degeneracy` must come from
    the same diagonalization: eigenvectors.shape[1] must equal
    degeneracy.groups[-1].end_index_exclusive. Computed for every group,
    including singletons -- a singleton's restricted operator is a 1x1
    matrix, and its diagnostics are just as meaningful (e.g. confirming a
    non-degenerate ground state carries <T^2> == 0).

    `total`, if provided, triggers one global (not per-subspace)
    commutator_defect = ||operator @ total - total @ operator||_F on the
    FULL Hilbert space, opt-in because it is a property of the operators
    themselves, not of any particular subspace -- the same value is
    reported for every group, exactly like subspace_orthonormality_defect
    is repeated rather than factored into a separate structure (lot 6A/6B
    design decision).
    """
    if operator.shape[0] != operator.shape[1]:
        raise ValueError(f"operator must be square, got shape {operator.shape}")
    dimension = operator.shape[0]
    if eigenvectors.ndim != 2 or eigenvectors.shape[0] != dimension:
        raise ValueError(
            f"eigenvectors must have shape ({dimension}, n_computed), got {eigenvectors.shape}"
        )
    expected_columns = degeneracy.groups[-1].end_index_exclusive
    if eigenvectors.shape[1] != expected_columns:
        raise ValueError(
            f"eigenvectors has {eigenvectors.shape[1]} columns, but degeneracy covers "
            f"{expected_columns} eigenpairs -- they must come from the same diagonalization"
        )
    if total is not None and total.shape != operator.shape:
        raise ValueError(f"total has shape {total.shape}, expected {operator.shape} (same as operator)")

    commutator_defect: float | None = None
    if total is not None:
        commutator = (operator @ total - total @ operator).tocsr()
        commutator_defect = _frobenius_norm_sparse(commutator)

    diagnostics: list[SymmetrySectorDiagnostic] = []
    for group_index, group in enumerate(degeneracy.groups):
        psi = eigenvectors[:, group.start_index : group.end_index_exclusive]

        gram = psi.conj().T @ psi
        subspace_orthonormality_defect = _frobenius_norm_dense(gram - np.eye(gram.shape[0]))

        operator_psi = operator @ psi
        o_rest = psi.conj().T @ operator_psi
        # Relative, not absolute: a defect measured in absolute Frobenius
        # norm would grow mechanically under O -> c*O for any scalar c, and
        # would not be comparable between operators of different scale (a
        # Casimir vs. a single generator, say). max(1, ...) keeps the
        # denominator from vanishing/blowing up in the ||O*psi|| < 1 regime.
        numerator = _frobenius_norm_dense(operator_psi - psi @ o_rest)
        denominator = max(1.0, _frobenius_norm_dense(operator_psi))
        restriction_defect = float(numerator / denominator)

        if operator_kind in _WANTS_HERMITICITY:
            restricted_eigenvalues = tuple(complex(v) for v in np.linalg.eigvalsh(o_rest))
            restricted_hermiticity_defect: float | None = _frobenius_norm_dense(o_rest - o_rest.conj().T)
        else:
            restricted_eigenvalues = tuple(complex(v) for v in np.linalg.eigvals(o_rest))
            restricted_hermiticity_defect = None

        if operator_kind in _WANTS_UNITARITY:
            identity = np.eye(o_rest.shape[0])
            restricted_unitarity_defect: float | None = _frobenius_norm_dense(
                o_rest.conj().T @ o_rest - identity
            )
        else:
            restricted_unitarity_defect = None

        diagnostics.append(
            SymmetrySectorDiagnostic(
                operator_name=operator_name,
                operator_kind=operator_kind,
                spectral_group_index=group_index,
                restricted_eigenvalues=restricted_eigenvalues,
                restriction_defect=restriction_defect,
                restricted_hermiticity_defect=restricted_hermiticity_defect,
                restricted_unitarity_defect=restricted_unitarity_defect,
                subspace_orthonormality_defect=subspace_orthonormality_defect,
                commutator_defect=commutator_defect,
            )
        )

    return tuple(diagnostics)


# ---------------------------------------------------------------------------
# Geometric automorphisms: cyclic translation, reflection
# ---------------------------------------------------------------------------


def _validate_site_permutation(n_nodes: int, site_permutation: Sequence[int]) -> None:
    if sorted(site_permutation) != list(range(n_nodes)):
        raise ValueError(
            f"site_permutation must be a permutation of range({n_nodes}), got {tuple(site_permutation)!r}"
        )


def _mode_permutation(n_nodes: int, n_flavors: int, site_permutation: Sequence[int]) -> list[int]:
    mode_permutation = [0] * (n_nodes * n_flavors)
    for node in range(n_nodes):
        new_node = site_permutation[node]
        for flavor in range(n_flavors):
            mode_permutation[node * n_flavors + flavor] = new_node * n_flavors + flavor
    return mode_permutation


def _edge_image(lattice: Lattice, site_permutation: Sequence[int]) -> list[tuple[int, int]]:
    """For each stored edge, (image edge index, orientation sign): sign=+1
    if the permuted (source, target) pair matches a stored edge exactly
    (orientation preserved), sign=-1 if it matches only in reversed order
    (orientation inverted). Raises ValueError if neither matches -- the
    permutation is not an automorphism of this lattice's edge set."""
    lookup = {(edge.source, edge.target): index for index, edge in enumerate(lattice.edges)}
    image: list[tuple[int, int]] = []
    for edge in lattice.edges:
        new_source = site_permutation[edge.source]
        new_target = site_permutation[edge.target]
        if (new_source, new_target) in lookup:
            image.append((lookup[(new_source, new_target)], 1))
        elif (new_target, new_source) in lookup:
            image.append((lookup[(new_target, new_source)], -1))
        else:
            raise ValueError(
                f"site_permutation does not map edge ({edge.source}, {edge.target}) onto any stored edge "
                f"in either orientation (image is ({new_source}, {new_target})) -- not a lattice automorphism"
            )
    return image


def _inversion_count(sequence: Sequence[int]) -> int:
    count = 0
    for i in range(len(sequence)):
        for j in range(i + 1, len(sequence)):
            if sequence[i] > sequence[j]:
                count += 1
    return count


def _apply_automorphism(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    key: np.uint64,
    mode_permutation: Sequence[int],
    edge_image: Sequence[tuple[int, int]],
) -> OperatorResult:
    """Relabel every occupied mode and every edge's flux simultaneously.

    The fermion sign is the parity of the number of inversions in the
    sequence obtained by mapping the sorted list of occupied modes through
    mode_permutation. This is exactly the sign needed to re-sort
    c^dagger_{pi(b1)} c^dagger_{pi(b2)} ... |0> (pi applied to the
    originally-sorted b1 < b2 < ...) back into the canonical
    increasing-mode-index order the key encoding assumes -- a single global
    sign for the whole relabeling, not operators.py's local per-transposition
    JW-hop sign (which answers a different question: the sign picked up by
    one creation/annihilation acting past already-occupied lower modes).
    """
    occupation, flux = decode(lattice, n_flavors, spin, key)

    new_occupation = [0] * len(occupation)
    occupied_modes: list[int] = []
    for mode, value in enumerate(occupation):
        new_occupation[mode_permutation[mode]] = value
        if value:
            occupied_modes.append(mode)

    new_flux = [0] * len(flux)
    for edge_index, value in enumerate(flux):
        target_edge, sign = edge_image[edge_index]
        new_flux[target_edge] = sign * value

    mapped_modes = [mode_permutation[mode] for mode in occupied_modes]
    fermion_sign = -1 if _inversion_count(mapped_modes) % 2 else 1

    new_key = encode(lattice, n_flavors, spin, new_occupation, new_flux)
    return OperatorResult(new_key, complex(fermion_sign, 0))


def _build_graph_automorphism_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    site_permutation: Sequence[int],
    *,
    external_charges: Sequence[object] | None = None,
) -> sp.csr_matrix:
    """Shared constructor for translation, reflection, and any other graph
    automorphism: the signed permutation operator that relabels sites via
    site_permutation (see _edge_image and _apply_automorphism for the
    orientation and fermion-sign rules).

    external_charges must be invariant under site_permutation
    (q^ext_{site_permutation[i]} == q^ext_i for every i): Gauss's law
    transforms covariantly, G'_{site_permutation[i]} == G_i, only under
    this condition (the div(E) part is covariant unconditionally, by the
    orientation-sign construction in _edge_image; the -Q_i part is
    covariant unconditionally too, since occupation is directly relabeled;
    only the -q_i^ext part requires this explicit check). Checked here,
    before touching any key, rather than left to surface as a RuntimeError
    from a missing key in the physical basis.
    """
    n_nodes = len(lattice.nodes)
    _validate_site_permutation(n_nodes, site_permutation)
    validate_key_index(keys, key_index)

    normalized_charges = normalize_external_charges(n_nodes, external_charges)
    for node in range(n_nodes):
        image = site_permutation[node]
        if normalized_charges[image] != normalized_charges[node]:
            raise ValueError(
                f"external_charges is not invariant under site_permutation: "
                f"q[{node}]={normalized_charges[node]} != q[{image}]={normalized_charges[image]} "
                f"(image of node {node}); Gauss's law would not transform covariantly"
            )

    mode_permutation = _mode_permutation(n_nodes, n_flavors, site_permutation)
    edge_image = _edge_image(lattice, site_permutation)

    dim = len(keys)
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []
    for col, key in enumerate(keys):
        result = _apply_automorphism(lattice, n_flavors, spin, key, mode_permutation, edge_image)
        row = _row_for_key(key_index, result.key)
        rows.append(row)
        cols.append(col)
        values.append(result.amplitude)

    return _assemble_csr(rows, cols, values, dim)


def build_translation_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    *,
    external_charges: Sequence[object] | None = None,
) -> sp.csr_matrix:
    """Cyclic translation, node i -> (i+1) mod N.

    Requires the lattice's edges to be cyclically consistent under this
    shift (true for the ring geometries as built by lattice.py); raises
    ValueError otherwise -- e.g. chain3, which has no wraparound edge, or
    disk7, whose hub-and-spoke structure this uniform shift does not
    preserve.
    """
    n_nodes = len(lattice.nodes)
    site_permutation = [(node + 1) % n_nodes for node in range(n_nodes)]
    return _build_graph_automorphism_operator(
        lattice, n_flavors, spin, keys, key_index, site_permutation, external_charges=external_charges
    )


def build_reflection_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    *,
    external_charges: Sequence[object] | None = None,
) -> sp.csr_matrix:
    """Reflection, node i -> (N-i) mod N (node 0 fixed).

    Same automorphism requirement as build_translation_operator.
    """
    n_nodes = len(lattice.nodes)
    site_permutation = [(n_nodes - node) % n_nodes for node in range(n_nodes)]
    return _build_graph_automorphism_operator(
        lattice, n_flavors, spin, keys, key_index, site_permutation, external_charges=external_charges
    )
