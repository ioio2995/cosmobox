"""Cross-S spectral group matching. Level1B lot 1B-6
(docs/levels/level1/specification.md section 12,
docs/decisions/decisions.md D018).

Groups are never matched by energy rank alone. A SpectralGroupMatchKey
identifies a group by geometry, Hamiltonian identity EXCLUDING the link
spin S, sector, complete/partial status, multiplicity, the flavor label
twice_T, and the translation/reflection symmetry labels -- reusing
existing 1B-2/1B-3/1B-4 primitives (build_flavor_casimir,
canonical_multiplet_expectation/exploratory_partial_subspace_mean,
build_restricted_operator, hamiltonian_commutator_defect) rather than
introducing new computations for quantities those already provide.

A symmetry label (translation or reflection) is the restricted character
chi_A = Tr(Psi^dagger U_A Psi) of a generator A -- but ONLY for a
generator that empirically belongs to the subgroup that actually leaves
the Hamiltonian invariant at this point (checked via
hamiltonian_commutator_defect, never assumed from the bare graph, per the
already-accepted V07 result). A generator outside that subgroup is
"not_applicable", never a numeric value. A generator that IS applicable
but whose restricted character fails its own validation (subspace
stability under U_A, unitarity of the restricted operator) is
"unavailable" -- a third, explicit state, never conflated with either
"not_applicable" or a bare None.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Sequence
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from .automorphisms import UnitaryAutomorphism, hamiltonian_commutator_defect
from .restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, SpectralGroupState, build_restricted_operator

SYMMETRY_TOLERANCE = 1e-8
FLAVOR_LABEL_TOLERANCE = 1e-8

NUMERIC = "numeric"
NOT_APPLICABLE = "not_applicable"
UNAVAILABLE = "unavailable"
_LABEL_KINDS = (NUMERIC, NOT_APPLICABLE, UNAVAILABLE)

EXACT_LABEL_MATCH = "exact_label_match"
AMBIGUOUS_CROSS_TRUNCATION_MATCH = "ambiguous_cross_truncation_match"
TARGET_GROUP_NOT_IN_WINDOW = "target_group_not_in_window"
STRUCTURALLY_NOT_APPLICABLE = "structurally_not_applicable"
_MATCH_STATUSES = (
    EXACT_LABEL_MATCH,
    AMBIGUOUS_CROSS_TRUNCATION_MATCH,
    TARGET_GROUP_NOT_IN_WINDOW,
    STRUCTURALLY_NOT_APPLICABLE,
)

_VALID_STATUSES = (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE)


# ---------------------------------------------------------------------------
# Symmetry labels
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SymmetryLabel:
    """A translation/reflection label: exactly one of three states, never
    collapsed into a bare None. "numeric" carries the restricted character
    chi_A; "not_applicable" means the generator does not belong to the
    Hamiltonian's symmetry subgroup at this point; "unavailable" means the
    generator is applicable but its character failed validation."""

    kind: str
    value: complex | None

    def __post_init__(self) -> None:
        if self.kind not in _LABEL_KINDS:
            raise ValueError(f"kind must be one of {_LABEL_KINDS}, got {self.kind!r}")
        if (self.kind == NUMERIC) != (self.value is not None):
            raise ValueError("value must be set if and only if kind == 'numeric'")
        if self.value is not None:
            value = complex(self.value)
            if not (math.isfinite(value.real) and math.isfinite(value.imag)):
                raise ValueError(f"value is not finite: {self.value}")


def compute_restricted_symmetry_label(
    hamiltonian: sp.spmatrix,
    unitary_automorphism: UnitaryAutomorphism,
    group_state: SpectralGroupState,
    *,
    tolerance: float = SYMMETRY_TOLERANCE,
) -> SymmetryLabel:
    """chi_A = Tr(Psi^dagger U_A Psi), accepted as a numeric label only if
    A empirically commutes with `hamiltonian` (hamiltonian_commutator_defect,
    1B-4) AND the restricted operator O_rest = Psi^dagger U_A Psi is itself
    unitary AND U_A Psi stays within span(Psi) (subspace stability) -- both
    checked WITHOUT ever constructing Psi Psi^dagger (dimension x
    dimension): the stability residual U_A Psi - Psi O_rest is computed
    directly from O_rest (already built via build_restricted_operator),
    at (dimension x multiplicity) cost.
    """
    if hamiltonian_commutator_defect(unitary_automorphism.unitary, hamiltonian) > tolerance:
        return SymmetryLabel(kind=NOT_APPLICABLE, value=None)

    psi = group_state.psi
    o_rest = build_restricted_operator(unitary_automorphism.unitary, group_state)

    stability_defect = float(np.linalg.norm(unitary_automorphism.unitary @ psi - psi @ o_rest, "fro"))
    identity = np.eye(o_rest.shape[0], dtype=np.complex128)
    unitarity_defect = float(np.linalg.norm(o_rest.conj().T @ o_rest - identity, "fro"))

    if stability_defect > tolerance or unitarity_defect > tolerance:
        return SymmetryLabel(kind=UNAVAILABLE, value=None)

    return SymmetryLabel(kind=NUMERIC, value=complex(np.trace(o_rest)))


def symmetry_labels_match(a: SymmetryLabel, b: SymmetryLabel, *, tolerance: float = SYMMETRY_TOLERANCE) -> bool:
    """Two labels correspond only if they share the same kind: two
    "not_applicable" labels agree (the generator is absent on both sides,
    consistently); two "unavailable" labels never agree (an unresolved
    computation proves nothing); two "numeric" labels agree within
    |a-b| <= tolerance * max(1, |a|, |b|)."""
    if a.kind != b.kind:
        return False
    if a.kind == NOT_APPLICABLE:
        return True
    if a.kind == UNAVAILABLE:
        return False
    return abs(a.value - b.value) <= tolerance * max(1.0, abs(a.value), abs(b.value))


# ---------------------------------------------------------------------------
# Flavor label (twice_T)
# ---------------------------------------------------------------------------


def compute_twice_T(casimir_expectation: float, *, tolerance: float = FLAVOR_LABEL_TOLERANCE) -> int | None:
    """Given c_T = Tr(rho T^2) (already computed by the caller via
    canonical_multiplet_expectation / exploratory_partial_subspace_mean on
    the flavor Casimir, hermitian=True), solve T(T+1) ~= c_T for the
    nearest admissible half-integer, stored exactly as twice_T = 2T.
    Returns None (label unavailable, exact matching impossible) if the
    residual |c_T - T(T+1)| exceeds `tolerance` or c_T < 0 (not a valid
    Casimir eigenvalue)."""
    if not math.isfinite(casimir_expectation) or casimir_expectation < 0:
        return None
    candidate_T = (-1.0 + math.sqrt(1.0 + 4.0 * casimir_expectation)) / 2.0
    twice_T = max(0, round(candidate_T * 2.0))
    resolved_T = twice_T / 2.0
    residual = abs(casimir_expectation - resolved_T * (resolved_T + 1.0))
    if residual > tolerance:
        return None
    return int(twice_T)


# ---------------------------------------------------------------------------
# Match key and outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpectralGroupMatchKey:
    """The scientific identity of a spectral group for cross-S matching.
    Energy rank is deliberately absent: it is used only to locate
    candidates and detect an incomplete window (match_spectral_group's own
    inputs), never as part of this identity."""

    geometry: str
    hamiltonian_identity_without_spin: Hashable
    sector_identity: Hashable
    status: str
    multiplicity: int
    twice_T: int
    translation_label: SymmetryLabel
    reflection_label: SymmetryLabel

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {_VALID_STATUSES}, got {self.status!r}")
        if self.multiplicity <= 0:
            raise ValueError(f"multiplicity must be > 0, got {self.multiplicity}")
        if self.twice_T < 0:
            raise ValueError(f"twice_T must be >= 0, got {self.twice_T}")
        if not isinstance(self.translation_label, SymmetryLabel):
            raise ValueError(f"translation_label must be a SymmetryLabel, got {type(self.translation_label)}")
        if not isinstance(self.reflection_label, SymmetryLabel):
            raise ValueError(f"reflection_label must be a SymmetryLabel, got {type(self.reflection_label)}")


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    status: str
    matched_group: SpectralGroupMatchKey | None

    def __post_init__(self) -> None:
        if self.status not in _MATCH_STATUSES:
            raise ValueError(f"status must be one of {_MATCH_STATUSES}, got {self.status!r}")
        if (self.status == EXACT_LABEL_MATCH) != (self.matched_group is not None):
            raise ValueError("matched_group must be set if and only if status == 'exact_label_match'")


def match_spectral_group(
    target: SpectralGroupMatchKey | None,
    candidates: Sequence[SpectralGroupMatchKey],
    *,
    structurally_applicable: bool,
    low_window_truncated: bool,
    tolerance: float = SYMMETRY_TOLERANCE,
) -> MatchOutcome:
    """Match `target` (a group already identified at S_high, or None if
    the manifest's targeted category was not found at all) against
    `candidates` (the groups available at S_low).

    A "complete_multiplet" target can only be compared against
    "complete_multiplet" candidates, and a "partial_subspace" target only
    against "partial_subspace" candidates (never mixed) -- both sides'
    labels must still agree exactly for exact_label_match, so a
    partial-vs-partial pairing CAN reach exact_label_match structurally;
    it is the caller's (robustness.py's) job to then treat that as
    exploratory only, never a definitive verdict, since these two
    concerns (matching ambiguity vs. group completeness) are never fused.

    low_window_truncated distinguishes, when zero exact candidates are
    found, "the target genuinely was not computed at S_low"
    (target_group_not_in_window) from "S_low's own window was truncated
    and may simply not have reached the target" (ambiguous_cross_
    truncation_match) -- the latter also covers an "unavailable" label on
    EITHER side (target or a comparable candidate): an unresolved
    computation proves nothing, on either side, so the target itself
    carrying an "unavailable" label is never reported as
    target_group_not_in_window (it is not absent, its identity simply
    cannot be established).

    A "partial_subspace" target or candidate can never produce
    exact_label_match, even when the observed labels coincide exactly:
    truncation means the group's true multiplicity may exceed the
    observed one, so its identity as a complete multiplet can never be
    proven -- any such correspondence is reported as ambiguous_cross_
    truncation_match instead (matching.py's own share of the "matching
    ambiguity vs. group completeness are never fused" rule; the other
    share is evaluate_robustness's downgrade of a genuinely-exact but
    partial match, which remains as defense in depth even though this
    function no longer produces one under normal use).
    """
    if not structurally_applicable:
        return MatchOutcome(STRUCTURALLY_NOT_APPLICABLE, None)
    if target is None:
        return MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, None)

    target_has_unavailable_label = target.translation_label.kind == UNAVAILABLE or target.reflection_label.kind == UNAVAILABLE

    comparable = [
        candidate
        for candidate in candidates
        if candidate.geometry == target.geometry
        and candidate.hamiltonian_identity_without_spin == target.hamiltonian_identity_without_spin
        and candidate.sector_identity == target.sector_identity
        and candidate.status == target.status
    ]
    candidates_have_unavailable_label = any(
        candidate.translation_label.kind == UNAVAILABLE or candidate.reflection_label.kind == UNAVAILABLE
        for candidate in comparable
    )
    has_unavailable_label = target_has_unavailable_label or candidates_have_unavailable_label

    exact = [
        candidate
        for candidate in comparable
        if candidate.multiplicity == target.multiplicity
        and candidate.twice_T == target.twice_T
        and symmetry_labels_match(candidate.translation_label, target.translation_label, tolerance=tolerance)
        and symmetry_labels_match(candidate.reflection_label, target.reflection_label, tolerance=tolerance)
    ]

    if target.status == PARTIAL_SUBSPACE and exact:
        return MatchOutcome(AMBIGUOUS_CROSS_TRUNCATION_MATCH, None)

    if len(exact) == 1:
        return MatchOutcome(EXACT_LABEL_MATCH, exact[0])
    if len(exact) > 1:
        return MatchOutcome(AMBIGUOUS_CROSS_TRUNCATION_MATCH, None)
    if low_window_truncated or has_unavailable_label:
        return MatchOutcome(AMBIGUOUS_CROSS_TRUNCATION_MATCH, None)
    return MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, None)
