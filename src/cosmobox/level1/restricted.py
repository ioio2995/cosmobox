"""Multiplet state, canonical mixed state, and restricted operators.

Level1B lot 1B-3 (docs/levels/level1/specification.md section 4,
docs/levels/level1/implementation-design.md section 6). Covers V08
(multiplet basis invariance), V09 (canonical mixed state), and V10
(truncated group contract) only -- V06/V07 (automorphism covariance,
symmetry-group reduction) are deferred to lot 1B-4 per explicit scope
decision, and the detailed restricted-operator diagnostics (eigenvalues,
singular values, Frobenius norm) are deferred to the lot that follows this
one.

For a complete spectral group with orthonormal eigenvector columns Psi
(dimension x multiplicity), the canonical mixed state is
rho = Psi Psi^dagger / d. Its trace against any operator O reduces, by
cyclicity of the trace, to

    Tr(rho O) = Tr(Psi^dagger O Psi) / d = Tr(O_rest) / d,

where O_rest = Psi^dagger O Psi is a (multiplicity x multiplicity) dense
matrix. This module never constructs Psi Psi^dagger (dimension x
dimension): every computation here routes through the small O_rest
instead, following the same operator @ psi -> psi.conj().T @ (...) pattern
already used by cosmobox.level0.symmetries.analyze_symmetry_in_subspaces
for its own per-subspace restriction (a different diagnostic purpose --
that function validates a symmetry, this module evaluates an arbitrary
observable's canonical expectation -- so the output types are kept
separate rather than shoehorning this lot's need into
SymmetrySectorDiagnostic).

Tr(rho O) is invariant under any internal unitary rotation Psi -> Psi V:
Tr((Psi V)^dagger O (Psi V)) / d = Tr(V^dagger O_rest V) / d
= Tr(O_rest V V^dagger) / d = Tr(O_rest) / d, by cyclicity and V V^dagger
= I. This is an exact algebraic identity, not an approximate property;
V08 confirms it numerically.

A group with SpectralLevelGroup.lower_bound_only=True has no defined
multiplet average: its true multiplicity may exceed the observed one, so
no scientific verdict may depend on any trace computed from it. Such a
group's status is "partial_subspace", never "complete_multiplet", and the
two canonical-vs-exploratory entry points below are mutually exclusive by
construction (each rejects the other's status) rather than merely
documented as such.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.degeneracy import SpectralLevelGroup

ORTHONORMALITY_TOLERANCE = 1e-8
HERMITICITY_TOLERANCE = 1e-8
IMAGINARY_PART_TOLERANCE = 1e-10

COMPLETE_MULTIPLET = "complete_multiplet"
PARTIAL_SUBSPACE = "partial_subspace"
_VALID_STATUSES = (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE)


# ---------------------------------------------------------------------------
# Spectral group state
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpectralGroupState:
    """Psi (dimension x multiplicity): orthonormal eigenvector columns for
    one spectral group, together with its complete/partial status.

    multiplicity is deliberately not stored as an independent field --
    it is always psi.shape[1] (the `multiplicity` property below), so it
    cannot diverge from the array it describes.

    This is a public type and is directly constructible (not only via
    extract_group_state below) -- so every invariant psi must satisfy is
    enforced here, in __post_init__, not merely by extract_group_state's
    own construction path: finite values, orthonormal columns, an
    independent complex128 copy (never a view onto the caller's array,
    and never sharing dtype/mutability with it), and a definitively
    non-writeable buffer (object.__setattr__ is required to install the
    controlled copy, since the dataclass is frozen).
    """

    psi: np.ndarray
    status: str

    def __post_init__(self) -> None:
        psi = np.asarray(self.psi, dtype=np.complex128)
        if psi.ndim != 2:
            raise ValueError(f"psi must be 2-D, got shape {psi.shape}")
        if psi.shape[1] == 0:
            raise ValueError("psi must have at least one column (non-empty group)")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {_VALID_STATUSES}, got {self.status!r}")
        if not np.all(np.isfinite(psi)):
            raise ValueError("psi contains non-finite values")

        gram = psi.conj().T @ psi
        orthonormality_defect = float(np.max(np.abs(gram - np.eye(gram.shape[0]))))
        if orthonormality_defect > ORTHONORMALITY_TOLERANCE:
            raise ValueError(
                f"psi is not orthonormal: max|Psi^dagger Psi - I| = {orthonormality_defect} "
                f"(tolerance {ORTHONORMALITY_TOLERANCE})"
            )

        psi = np.array(psi, copy=True)  # independent of self.psi's original buffer, whatever it was
        psi.setflags(write=False)
        object.__setattr__(self, "psi", psi)

    @property
    def multiplicity(self) -> int:
        return self.psi.shape[1]

    @property
    def is_complete(self) -> bool:
        return self.status == COMPLETE_MULTIPLET


def extract_group_state(eigenvectors: np.ndarray, group: SpectralLevelGroup) -> SpectralGroupState:
    """Slice Psi for one spectral group out of a full eigenvector matrix.

    status is derived from group.lower_bound_only -- it is never a
    parameter the caller can override. The finite-values, orthonormality,
    independent-copy, and read-only guarantees are all enforced by
    SpectralGroupState.__post_init__ itself (not duplicated here): this
    function is responsible only for the parts that require `group` and
    `eigenvectors` together -- index bounds and the multiplicity_observed
    cross-check -- before delegating construction.
    """
    if eigenvectors.ndim != 2:
        raise ValueError(f"eigenvectors must be 2-D, got shape {eigenvectors.shape}")
    if group.start_index < 0 or group.end_index_exclusive > eigenvectors.shape[1]:
        raise ValueError(
            f"group indices [{group.start_index}, {group.end_index_exclusive}) are out of range "
            f"for eigenvectors with {eigenvectors.shape[1]} columns"
        )

    psi = eigenvectors[:, group.start_index : group.end_index_exclusive]
    if psi.shape[1] != group.multiplicity_observed:
        raise ValueError(
            f"extracted {psi.shape[1]} columns but group.multiplicity_observed is "
            f"{group.multiplicity_observed}"
        )

    status = PARTIAL_SUBSPACE if group.lower_bound_only else COMPLETE_MULTIPLET
    return SpectralGroupState(psi=psi, status=status)


# ---------------------------------------------------------------------------
# Restricted operator
# ---------------------------------------------------------------------------


def build_restricted_operator(operator: sp.spmatrix, group_state: SpectralGroupState) -> np.ndarray:
    """O_rest = Psi^dagger O Psi, a (multiplicity, multiplicity) dense
    matrix. Never constructs Psi Psi^dagger (dimension x dimension).

    group_state.psi is already guaranteed finite and orthonormal by
    SpectralGroupState.__post_init__, and read-only -- but numpy's
    writeable flag can be reverted by a caller with array.setflags
    (write=True), same as OrientedPath's frozen dataclass can be bypassed
    with object.__setattr__ (see transporters.py's own bypass tests). The
    finite/orthonormal checks below are defense in depth against exactly
    that, not redundant restatements of an unbypassable guarantee.
    """
    if operator.shape[0] != operator.shape[1]:
        raise ValueError(f"operator must be square, got shape {operator.shape}")
    dimension = operator.shape[0]

    psi = group_state.psi
    if psi.shape[0] != dimension:
        raise ValueError(f"operator has dimension {dimension} but group_state.psi has {psi.shape[0]} rows")

    if not np.all(np.isfinite(psi)):
        raise ValueError("group_state.psi contains non-finite values")

    gram = psi.conj().T @ psi
    orthonormality_defect = float(np.max(np.abs(gram - np.eye(gram.shape[0]))))
    if orthonormality_defect > ORTHONORMALITY_TOLERANCE:
        raise ValueError(
            f"group_state.psi is not orthonormal: max|Psi^dagger Psi - I| = {orthonormality_defect} "
            f"(tolerance {ORTHONORMALITY_TOLERANCE})"
        )

    if not np.all(np.isfinite(operator.data)):
        raise ValueError("operator.data contains non-finite values")

    operator_psi = operator @ psi
    if not np.all(np.isfinite(operator_psi)):
        raise ValueError("operator @ psi produced non-finite values")

    return psi.conj().T @ operator_psi


def _hermitian_aware_normalized_trace(
    o_rest: np.ndarray, multiplicity: int, *, hermitian: bool, tolerance: float
) -> float | complex:
    """Tr(o_rest) / multiplicity. Shared by canonical_multiplet_expectation
    and exploratory_partial_subspace_mean -- the only difference between
    them is which group status they accept, not this arithmetic."""
    if hermitian:
        hermiticity_defect = float(np.max(np.abs(o_rest - o_rest.conj().T)))
        if hermiticity_defect > HERMITICITY_TOLERANCE:
            raise ValueError(
                f"O_rest is not Hermitian (max|O_rest - O_rest^dagger| = {hermiticity_defect}, "
                f"tolerance {HERMITICITY_TOLERANCE}) but hermitian=True was requested"
            )

    trace = complex(np.trace(o_rest)) / multiplicity
    if not (np.isfinite(trace.real) and np.isfinite(trace.imag)):
        raise ValueError(f"Tr(O_rest)/multiplicity is not finite: {trace}")

    if hermitian:
        if abs(trace.imag) > tolerance:
            raise ValueError(
                f"Tr(O_rest)/multiplicity has a non-negligible imaginary part {trace.imag} "
                f"(tolerance {tolerance}) but hermitian=True was requested"
            )
        return float(trace.real)
    return trace


# ---------------------------------------------------------------------------
# Canonical multiplet expectation (complete groups only)
# ---------------------------------------------------------------------------


def canonical_multiplet_expectation(
    operator: sp.spmatrix,
    group_state: SpectralGroupState,
    *,
    hermitian: bool,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> float | complex:
    """Tr(rho O) = Tr(O_rest) / d for a COMPLETE multiplet
    (rho = Psi Psi^dagger / d). Requires group_state.status ==
    "complete_multiplet"; raises ValueError otherwise -- use
    exploratory_partial_subspace_mean for a "partial_subspace" group.

    hermitian=True additionally checks O_rest ~= O_rest^dagger and that
    the resulting trace's imaginary part is negligible, then returns a
    real float. hermitian=False returns the raw complex value, for the
    dressed matter operator's off-diagonal (i != j) case, which is
    generally non-Hermitian.
    """
    if group_state.status != COMPLETE_MULTIPLET:
        raise ValueError(
            f"canonical_multiplet_expectation requires a '{COMPLETE_MULTIPLET}' group_state, "
            f"got '{group_state.status}'; use exploratory_partial_subspace_mean for "
            f"'{PARTIAL_SUBSPACE}' groups"
        )

    o_rest = build_restricted_operator(operator, group_state)
    return _hermitian_aware_normalized_trace(
        o_rest, group_state.multiplicity, hermitian=hermitian, tolerance=tolerance
    )


# ---------------------------------------------------------------------------
# Exploratory partial-subspace mean (partial groups only)
# ---------------------------------------------------------------------------


def exploratory_partial_subspace_mean(
    operator: sp.spmatrix,
    group_state: SpectralGroupState,
    *,
    hermitian: bool,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> float | complex:
    """Tr(O_rest) / (observed multiplicity) for a PARTIAL group
    (group_state.status == "partial_subspace", i.e. the underlying
    SpectralLevelGroup.lower_bound_only was True).

    This is explicitly NOT a canonical multiplet expectation: the group's
    true multiplicity may exceed the observed one, so this value carries
    no scientific verdict (docs/levels/level1/specification.md section 4)
    and must never be reported as a completed multiplet average. Requires
    group_state.status == "partial_subspace"; raises ValueError otherwise
    -- use canonical_multiplet_expectation for a "complete_multiplet"
    group.
    """
    if group_state.status != PARTIAL_SUBSPACE:
        raise ValueError(
            f"exploratory_partial_subspace_mean requires a '{PARTIAL_SUBSPACE}' group_state, "
            f"got '{group_state.status}'; use canonical_multiplet_expectation for "
            f"'{COMPLETE_MULTIPLET}' groups"
        )

    o_rest = build_restricted_operator(operator, group_state)
    return _hermitian_aware_normalized_trace(
        o_rest, group_state.multiplicity, hermitian=hermitian, tolerance=tolerance
    )
