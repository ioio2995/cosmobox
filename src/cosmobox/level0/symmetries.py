"""Symmetry operators on the exact physical basis, and restricted-subspace diagnostics.

Lot 6B.1: global flavor-SU(2) generators (T_x, T_y, T_z), their Casimir
(T^2), and analyze_symmetry_in_subspaces, which restricts an already-built
operator to each SpectralLevelGroup of an already-computed DegeneracyReport
and reports how well the subspace is preserved and how the operator
behaves there. It never diagonalizes anything itself -- eigenvectors are
supplied by the caller (reports.py's spectral computation stays internal
to reports.py; this module does not import its private helpers).

Geometric automorphisms (translation, reflection) are lot 6B.2, not here.

Flavor mixing is site-local (c^dagger_{i,alpha} c_{i,beta} moves a fermion
between flavors at the SAME node i, never between nodes and never
touching flux), so it leaves the total occupation n_{i0}+n_{i1} at every
site unchanged. Since Gauss's law G_i = sum_e eps_ie E_e - Q_i - q_i^ext
depends on occupation only through Q_i = sum_alpha n_{i,alpha} - 1 (not on
which flavor is occupied) and flavor mixing never touches E_e, T_x/T_y/T_z
map the physical basis into itself exactly like H_dot's off-diagonal
h-coupling does -- a transition landing outside key_index is therefore a
genuine T2-style invariant violation, not something to drop silently.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np
import scipy.sparse as sp

from .degeneracy import DegeneracyReport
from .hamiltonian import validate_key_index
from .lattice import Lattice
from .operators import annihilate, create

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
