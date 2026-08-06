"""Flavor invariants of the dressed correlator's complete 2x2 flavor
matrix G. Level1B lot 1B-4 (docs/levels/level1/specification.md section 8,
docs/levels/level1/implementation-design.md section 7.1).

G^{alpha,beta}_ij[P] = Tr(rho O_ij^{alpha,beta}[P]) (specification.md
section 7). A non-degenerate eigenstate is the multiplicity-1 special case
of a spectral group, so this reuses lot 1B-3's
canonical_multiplet_expectation / exploratory_partial_subspace_mean
directly (with hermitian=False, since O_ij for i != j is generally
non-Hermitian) rather than introducing a separate pure-state expectation
function -- no second definition of "expectation value" is needed here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.level0.lattice import Lattice

from .local_observables import NORMALIZATION_FLOOR, NormalizedMoment
from .matter import build_dressed_matter_matrix
from .paths import OrientedPath
from .restricted import (
    COMPLETE_MULTIPLET,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
)


@dataclass(frozen=True, slots=True)
class FlavorCorrelatorMatrix:
    """G^{alpha,beta}_ij[P]: the full complex 2x2 flavor block, together
    with the spectral group's status.

    status is carried alongside matrix, not left implicit, so a value
    computed from a partial_subspace group can never be silently confused
    with a canonical complete_multiplet average downstream (the same
    concern SpectralGroupState addresses for Psi -- this type follows the
    same pattern: a public, directly-constructible type owns its own
    invariants in __post_init__, not only in whichever builder happens to
    also enforce them).
    """

    matrix: np.ndarray
    status: str

    def __post_init__(self) -> None:
        matrix = np.asarray(self.matrix, dtype=np.complex128)
        if matrix.shape != (2, 2):
            raise ValueError(f"matrix must have shape (2, 2), got {matrix.shape}")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("matrix contains non-finite values")
        if self.status not in (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE):
            raise ValueError(
                f"status must be one of ({COMPLETE_MULTIPLET!r}, {PARTIAL_SUBSPACE!r}), got {self.status!r}"
            )

        matrix = np.array(matrix, copy=True)
        matrix.setflags(write=False)
        object.__setattr__(self, "matrix", matrix)


def build_flavor_correlator_matrix(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys,
    key_index: dict[int, int],
    group_state: SpectralGroupState,
    path: OrientedPath,
) -> FlavorCorrelatorMatrix:
    """G[alpha, beta] = Tr(rho O_ij^{alpha,beta}[path]), assembled via
    build_dressed_matter_matrix (1B-1) and the status-appropriate 1B-3
    expectation function -- canonical_multiplet_expectation for a complete
    group, exploratory_partial_subspace_mean for a partial one, never
    mixed."""
    if n_flavors != 2:
        raise ValueError(f"the flavor correlator matrix is only defined for n_flavors == 2 (M=2, per D006), got {n_flavors}")

    expectation = canonical_multiplet_expectation if group_state.is_complete else exploratory_partial_subspace_mean

    entries = np.zeros((2, 2), dtype=np.complex128)
    for alpha in range(2):
        for beta in range(2):
            operator = build_dressed_matter_matrix(lattice, n_flavors, spin, keys, key_index, path, alpha, beta)
            entries[alpha, beta] = expectation(operator, group_state, hermitian=False)

    status = COMPLETE_MULTIPLET if group_state.is_complete else PARTIAL_SUBSPACE
    return FlavorCorrelatorMatrix(matrix=entries, status=status)


def flavor_singlet(correlator: FlavorCorrelatorMatrix) -> complex:
    """Tr_f(G)."""
    return complex(np.trace(correlator.matrix))


def flavor_frobenius_squared(correlator: FlavorCorrelatorMatrix) -> float:
    """Tr_f(G^dagger G) = sum_{alpha,beta} |G^{alpha,beta}|^2 -- manifestly
    real and non-negative, computed directly rather than via a trace that
    would need a separate realness check."""
    return float(np.sum(np.abs(correlator.matrix) ** 2))


def flavor_singular_values(correlator: FlavorCorrelatorMatrix) -> tuple[float, float]:
    """[sigma_1, sigma_2], sigma_1 >= sigma_2 >= 0 (numpy's SVD already
    returns singular values in descending order)."""
    singular_values = np.linalg.svd(correlator.matrix, compute_uv=False)
    return (float(singular_values[0]), float(singular_values[1]))


def flavor_singular_value_ratio(
    correlator: FlavorCorrelatorMatrix, *, floor: float = NORMALIZATION_FLOOR
) -> NormalizedMoment:
    """sigma_2 / sigma_1, defined only if sigma_1 exceeds `floor`
    (specification.md section 8). "normalization_denominator_below_floor"
    is the schema's existing, generic denominator-below-floor reason
    (schemas/level1/correlators-v1.schema.json null_reason enum) -- reused
    exactly as-is, not a new "sigma_1_below_floor" string invented by
    analogy."""
    sigma_1, sigma_2 = flavor_singular_values(correlator)
    if sigma_1 <= floor:
        return NormalizedMoment(value=None, null_reason="normalization_denominator_below_floor")
    return NormalizedMoment(value=sigma_2 / sigma_1, null_reason=None)
