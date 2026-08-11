"""Local charge and flavor observables, and their two-site correlators, on a pure state.

Level1B lot 1B-2. Q_i and T_i^a are built as explicit linear combinations
of level1.matter.build_dressed_matter_matrix on the empty (zero-length)
path at node i -- the same O_ii^{alpha,beta}[empty] = c^dagger_{i,alpha}
c_{i,beta} operator already validated by lot 1B-1 (V04). No new
fermionic/Jordan-Wigner composition is introduced, and this is not a
second definition of the SU(2) generators: the Pauli-matrix coefficients
below are the same standard convention already used by
cosmobox.level0.symmetries, applied as numeric weights on an
already-validated operator -- proven consistent by
test_local_flavor_generators_sum_to_the_global_generators (sum_i T_i^a ==
the existing global T^a, exactly).

Scope: pure states only (a single normalized ket). Degenerate multiplets,
mixed states (rho = Pi/d), restricted operators, orbit covariance,
inter-S matching, and JSON serialization are lot 1B-3+ and out of scope
here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.lattice import Lattice

from .matching import FLAVOR_LABEL_TOLERANCE
from .matter import build_dressed_matter_matrix
from .paths import make_oriented_path
from .restricted import (
    COMPLETE_MULTIPLET,
    IMAGINARY_PART_TOLERANCE,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
)

NORMALIZATION_FLOOR = 1e-12
EXPECTATION_TOLERANCE = 1e-10
NORM_TOLERANCE = 1e-8

FLAVOR_COMPONENTS: tuple[str, ...] = ("x", "y", "z")

# Standard Pauli matrices -- same convention as cosmobox.level0.symmetries'
# (private there); duplicated here as local constants rather than imported,
# matching the project's established practice for small, standard values
# (e.g. hamiltonian._row_for_key/_assemble_csr duplicated in symmetries.py
# and matter.py). This is not a second *definition*: the values are
# identical, and consistency with the existing global generators is
# verified directly by a test, not merely assumed.
_PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_PAULI: dict[str, np.ndarray] = {"x": _PAULI_X, "y": _PAULI_Y, "z": _PAULI_Z}


# ---------------------------------------------------------------------------
# Operator construction
# ---------------------------------------------------------------------------


def build_local_charge_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys,
    key_index: dict[int, int],
    node: int,
) -> sp.csr_matrix:
    """Q_i = sum_alpha c^dagger_{i,alpha} c_{i,alpha} - 1. n_flavors == 2 only (D006)."""
    if n_flavors != 2:
        raise ValueError(f"Q_i is only defined for n_flavors == 2 (M=2, per D006), got {n_flavors}")

    zero_path = make_oriented_path(lattice, (node,))
    dim = len(keys)
    total = sp.csr_matrix((dim, dim), dtype=np.complex128)
    for alpha in range(n_flavors):
        total = total + build_dressed_matter_matrix(
            lattice, n_flavors, spin, keys, key_index, zero_path, alpha, alpha
        )
    identity = sp.identity(dim, format="csr", dtype=np.complex128)
    return (total - identity).tocsr()


def build_local_flavor_generator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys,
    key_index: dict[int, int],
    node: int,
    component: str,
) -> sp.csr_matrix:
    """T_i^a = 1/2 sum_{alpha,beta} sigma^a_{alpha,beta} c^dagger_{i,alpha} c_{i,beta}."""
    if n_flavors != 2:
        raise ValueError(f"T_i^{component} is only defined for n_flavors == 2 (M=2, per D006), got {n_flavors}")
    if component not in _PAULI:
        raise ValueError(f"component must be one of {sorted(_PAULI)}, got {component!r}")

    pauli = _PAULI[component]
    zero_path = make_oriented_path(lattice, (node,))
    dim = len(keys)
    total = sp.csr_matrix((dim, dim), dtype=np.complex128)
    for alpha in range(n_flavors):
        for beta in range(n_flavors):
            coeff = 0.5 * pauli[alpha, beta]
            if coeff == 0:
                continue
            total = total + coeff * build_dressed_matter_matrix(
                lattice, n_flavors, spin, keys, key_index, zero_path, alpha, beta
            )
    return total.tocsr()


def build_local_flavor_generators(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys,
    key_index: dict[int, int],
    node: int,
) -> dict[str, sp.csr_matrix]:
    """{"x": T_i^x, "y": T_i^y, "z": T_i^z}."""
    return {
        component: build_local_flavor_generator(lattice, n_flavors, spin, keys, key_index, node, component)
        for component in FLAVOR_COMPONENTS
    }


# ---------------------------------------------------------------------------
# Two-site products -- i == j is a valid, required case (C_QQ(i,i) is the
# rho_QQ denominator's variance).
# ---------------------------------------------------------------------------


def local_charge_product(operator_i: sp.csr_matrix, operator_j: sp.csr_matrix) -> sp.csr_matrix:
    """Q_i Q_j. i == j is allowed and expected (needed for C_QQ(i,i))."""
    return (operator_i @ operator_j).tocsr()


def local_flavor_dot_product(
    generators_i: dict[str, sp.csr_matrix], generators_j: dict[str, sp.csr_matrix]
) -> sp.csr_matrix:
    """sum_a T_i^a T_j^a. i == j is allowed and expected."""
    total: sp.csr_matrix | None = None
    for component in FLAVOR_COMPONENTS:
        term = generators_i[component] @ generators_j[component]
        total = term if total is None else total + term
    return total.tocsr()


# ---------------------------------------------------------------------------
# Expectation values and moments on a pure state
# ---------------------------------------------------------------------------


def expectation_value(operator: sp.csr_matrix, psi: np.ndarray, *, tolerance: float = EXPECTATION_TOLERANCE) -> float:
    """<psi|operator|psi> for a Hermitian operator on a normalized pure state.

    Contract enforced here, not left to the caller: psi must be a 1-D
    array whose length matches operator's dimension, and must be
    normalized (||psi|| ~= 1, tolerance NORM_TOLERANCE). raw_moment and
    connected_moment both route through this single function, so psi's
    shape/normalization is checked exactly once per call, not re-verified
    ad hoc by each caller.

    Raises ValueError (never a bare assert) if the shape, the
    normalization, or the resulting expectation value's imaginary part is
    inconsistent with a Hermitian operator on a genuine pure state.
    """
    if operator.shape[0] != operator.shape[1]:
        raise ValueError(f"operator must be square, got shape {operator.shape}")
    dimension = operator.shape[0]

    psi = np.asarray(psi, dtype=np.complex128)
    if psi.ndim != 1 or psi.shape[0] != dimension:
        raise ValueError(f"psi must be a 1-D array of length {dimension}, got shape {psi.shape}")

    norm = float(np.linalg.norm(psi))
    if not math.isfinite(norm) or abs(norm - 1.0) > NORM_TOLERANCE:
        raise ValueError(f"psi must be normalized (||psi|| ~= 1, tolerance {NORM_TOLERANCE}), got ||psi||={norm}")

    value = complex(np.vdot(psi, operator @ psi))
    if not (math.isfinite(value.real) and math.isfinite(value.imag)):
        raise ValueError(f"<psi|O|psi> is not finite: {value}")
    if abs(value.imag) > tolerance:
        raise ValueError(
            f"<psi|O|psi> has a non-negligible imaginary part {value.imag} (tolerance {tolerance}); "
            "the operator is expected to be Hermitian on this pure state"
        )
    return float(value.real)


def raw_moment(
    operator_i: sp.csr_matrix, operator_j: sp.csr_matrix, psi: np.ndarray, *, tolerance: float = EXPECTATION_TOLERANCE
) -> float:
    """<psi| operator_i @ operator_j |psi>. i == j is allowed."""
    product = (operator_i @ operator_j).tocsr()
    return expectation_value(product, psi, tolerance=tolerance)


def connected_moment(
    operator_i: sp.csr_matrix, operator_j: sp.csr_matrix, psi: np.ndarray, *, tolerance: float = EXPECTATION_TOLERANCE
) -> float:
    """<O_i O_j> - <O_i><O_j>, all three terms evaluated on the SAME psi."""
    raw = raw_moment(operator_i, operator_j, psi, tolerance=tolerance)
    expectation_i = expectation_value(operator_i, psi, tolerance=tolerance)
    expectation_j = expectation_value(operator_j, psi, tolerance=tolerance)
    return raw - expectation_i * expectation_j


# ---------------------------------------------------------------------------
# Named spec quantities
# ---------------------------------------------------------------------------


def charge_correlator_raw(
    charge_i: sp.csr_matrix, charge_j: sp.csr_matrix, psi: np.ndarray, *, tolerance: float = EXPECTATION_TOLERANCE
) -> float:
    """<Q_i Q_j>. i == j is allowed."""
    return raw_moment(charge_i, charge_j, psi, tolerance=tolerance)


def charge_correlator_connected(
    charge_i: sp.csr_matrix, charge_j: sp.csr_matrix, psi: np.ndarray, *, tolerance: float = EXPECTATION_TOLERANCE
) -> float:
    """C_QQ(i,j). i == j is allowed and required for the rho_QQ denominator."""
    return connected_moment(charge_i, charge_j, psi, tolerance=tolerance)


def flavor_correlator_raw(
    generators_i: dict[str, sp.csr_matrix],
    generators_j: dict[str, sp.csr_matrix],
    psi: np.ndarray,
    *,
    tolerance: float = EXPECTATION_TOLERANCE,
) -> float:
    """C_TT_raw(i,j) = sum_a <T_i^a T_j^a>. i == j is allowed."""
    return sum(
        raw_moment(generators_i[component], generators_j[component], psi, tolerance=tolerance)
        for component in FLAVOR_COMPONENTS
    )


def flavor_correlator_connected(
    generators_i: dict[str, sp.csr_matrix],
    generators_j: dict[str, sp.csr_matrix],
    psi: np.ndarray,
    *,
    tolerance: float = EXPECTATION_TOLERANCE,
) -> float:
    """C_TT_conn(i,j) = sum_a [<T_i^a T_j^a> - <T_i^a><T_j^a>]. i == j is allowed."""
    return sum(
        connected_moment(generators_i[component], generators_j[component], psi, tolerance=tolerance)
        for component in FLAVOR_COMPONENTS
    )


# ---------------------------------------------------------------------------
# null-aware normalized moment (internal representation, pre-serialization)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizedMoment:
    """A normatively `null` value carries an explicit reason, never a bare
    zero. This is the internal, pre-serialization representation -- mapping
    it onto schemas/level1/correlators-v1.schema.json's {"value": ...,
    "null_reason": ...} fields is lot 1B-5's job, out of scope here."""

    value: float | None
    null_reason: str | None

    def __post_init__(self) -> None:
        if (self.value is None) != (self.null_reason is not None):
            raise ValueError("value is None if and only if null_reason is set")


def _clamp_small_negative_variance(variance: float, *, floor: float) -> float:
    """A variance must be non-negative. A value in [-floor, 0) is numerical
    noise (from expectation_value's own tolerance) and is clamped to
    exactly 0.0. Anything more negative than -floor is a genuine
    inconsistency and is returned unchanged, for the caller to reject."""
    if -floor <= variance < 0.0:
        return 0.0
    return variance


def normalized_charge_correlator(
    connected_ij: float, variance_i: float, variance_j: float, *, floor: float = NORMALIZATION_FLOOR
) -> NormalizedMoment:
    """rho_QQ(i,j) = C_QQ(i,j) / sqrt(C_QQ(i,i) * C_QQ(j,j)).

    Validated rule: clamp a small negative variance (|v| <= floor) to
    zero, then return null with reason "zero_local_charge_variance" if
    EITHER (clamped) variance is <= floor. "normalization_denominator_
    below_floor" is never produced for rho_QQ specifically: with both
    variances non-negative and individually floor-controlled, a
    below-floor product without an individually-below-floor factor cannot
    occur, so that branch would be mathematically redundant here.
    """
    variance_i = _clamp_small_negative_variance(variance_i, floor=floor)
    variance_j = _clamp_small_negative_variance(variance_j, floor=floor)

    if variance_i < 0.0 or variance_j < 0.0:
        raise ValueError(
            f"a variance more negative than -floor is not numerical noise: "
            f"variance_i={variance_i}, variance_j={variance_j}, floor={floor}"
        )

    if variance_i <= floor or variance_j <= floor:
        return NormalizedMoment(value=None, null_reason="zero_local_charge_variance")

    return NormalizedMoment(value=connected_ij / math.sqrt(variance_i * variance_j), null_reason=None)


# ---------------------------------------------------------------------------
# Multiplet generalization (Level1B lot 1B-8a, docs/decisions/decisions.md
# D020). The functions above are pure-state only and are unchanged by this
# section: for a degenerate spectral group, <A> is not a single ket's
# expectation value but the canonical mixed-state trace (complete_multiplet)
# or the exploratory partial-window mean (partial_subspace), already
# defined generically by restricted.canonical_multiplet_expectation /
# exploratory_partial_subspace_mean and already used the same way by
# flavor.build_flavor_correlator_matrix for raw_G. This section extends the
# identical prescription to the charge/flavor two-site correlators, which
# had no multiplet-generalized producer until now.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupMoment:
    """A scalar moment computed from a SpectralGroupState's own canonical
    (complete_multiplet) or exploratory (partial_subspace) prescription.
    status is carried alongside value, never left implicit, so a
    partial-group result can never be silently mistaken for a canonical
    complete-multiplet average downstream -- the same pattern
    FlavorCorrelatorMatrix already established for raw_G. Carries no null
    reason and no verdict: this is a value-and-provenance-status pair
    only, not a normative judgment."""

    value: float
    status: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value):
            raise ValueError(f"value must be finite, got {self.value}")
        if self.status not in (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE):
            raise ValueError(
                f"status must be one of ({COMPLETE_MULTIPLET!r}, {PARTIAL_SUBSPACE!r}), got {self.status!r}"
            )


def _group_expectation(
    operator: sp.csr_matrix, group_state: SpectralGroupState, *, tolerance: float = IMAGINARY_PART_TOLERANCE
) -> float:
    """<A>_group: canonical_multiplet_expectation for a complete_multiplet
    group_state, exploratory_partial_subspace_mean for a partial_subspace
    one -- dispatched on group_state.is_complete, never a second,
    independently-maintained status check. hermitian=True always: every
    operator this is called with (Q_i, T_i^a, and a product of two such
    operators, same site or different) is Hermitian -- different-site
    charge/flavor generators are particle-number-conserving bilinears and
    therefore commute, so their product is Hermitian too, the same
    assumption already relied on by the pure-state functions above.
    Neither this function nor its callers ever construct Psi Psi^dagger or
    read group_state.psi directly: group_state is passed through opaquely
    to restricted.py, which alone routes through Psi^dagger (.) Psi."""
    expectation = canonical_multiplet_expectation if group_state.is_complete else exploratory_partial_subspace_mean
    return expectation(operator, group_state, hermitian=True, tolerance=tolerance)


def charge_correlator_raw_group(
    charge_i: sp.csr_matrix,
    charge_j: sp.csr_matrix,
    group_state: SpectralGroupState,
    *,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> GroupMoment:
    """<Q_i Q_j>_group. i == j is allowed and expected (group-level variance)."""
    value = _group_expectation(local_charge_product(charge_i, charge_j), group_state, tolerance=tolerance)
    return GroupMoment(value=value, status=group_state.status)


def charge_correlator_connected_group(
    charge_i: sp.csr_matrix,
    charge_j: sp.csr_matrix,
    group_state: SpectralGroupState,
    *,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> GroupMoment:
    """<Q_i Q_j>_group - <Q_i>_group <Q_j>_group. i == j is allowed and
    required for the group-level rho_QQ denominator (see
    normalized_charge_correlator, called by the caller with this
    function's .value as connected_ij/variance_i/variance_j -- not
    duplicated here, per D020)."""
    raw = _group_expectation(local_charge_product(charge_i, charge_j), group_state, tolerance=tolerance)
    expectation_i = _group_expectation(charge_i, group_state, tolerance=tolerance)
    expectation_j = _group_expectation(charge_j, group_state, tolerance=tolerance)
    return GroupMoment(value=raw - expectation_i * expectation_j, status=group_state.status)


def flavor_correlator_raw_group(
    generators_i: dict[str, sp.csr_matrix],
    generators_j: dict[str, sp.csr_matrix],
    group_state: SpectralGroupState,
    *,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> GroupMoment:
    """sum_a <T_i^a T_j^a>_group. i == j is allowed."""
    value = _group_expectation(local_flavor_dot_product(generators_i, generators_j), group_state, tolerance=tolerance)
    return GroupMoment(value=value, status=group_state.status)


def flavor_correlator_connected_group(
    generators_i: dict[str, sp.csr_matrix],
    generators_j: dict[str, sp.csr_matrix],
    group_state: SpectralGroupState,
    *,
    tolerance: float = IMAGINARY_PART_TOLERANCE,
) -> GroupMoment:
    """sum_a (<T_i^a T_j^a>_group - <T_i^a>_group <T_j^a>_group).

    The subtraction is performed INSIDE the sum over components a, exactly
    like flavor_correlator_connected above -- never as
    (sum_a <T_i^a T_j^a>_group) - (sum_a <T_i^a>_group)(sum_a <T_j^a>_group),
    which would introduce undefined cross-component terms."""
    total = 0.0
    for component in FLAVOR_COMPONENTS:
        raw_component = _group_expectation(
            (generators_i[component] @ generators_j[component]).tocsr(), group_state, tolerance=tolerance
        )
        expectation_i = _group_expectation(generators_i[component], group_state, tolerance=tolerance)
        expectation_j = _group_expectation(generators_j[component], group_state, tolerance=tolerance)
        total += raw_component - expectation_i * expectation_j
    return GroupMoment(value=total, status=group_state.status)


# ---------------------------------------------------------------------------
# T(T+1) sum rule validation (Level1B lot 1C-3b,
# docs/governance/current-task.md). Consumes already-computed C_TT_conn
# values for a single spectral group (diagonal from 1C-3a's new
# per-site production, off-diagonal from the pre-existing D021 pair
# production) -- never recomputes a correlator, never touches C_TT_raw.
# ---------------------------------------------------------------------------

FLAVOR_TOTAL_SUM_TOLERANCE = FLAVOR_LABEL_TOLERANCE
"""Reused verbatim from matching.py, never redefined: compute_twice_T
already compares a computed quantity against the SAME target formula
T(T+1) using this exact absolute-residual tolerance (matching.py's own
docstring: "residual |c_T - T(T+1)| exceeds tolerance"). This check is
the same comparison against the same right-hand side, only with the
left-hand side built by summing already-computed C_TT_conn values
(at most N*(N-1) off-diagonal plus N diagonal terms, N<=5 in the current
campaign) instead of a single Casimir expectation call -- worst-case
accumulated slack from summing up to 25 terms, each already bounded by
existing frozen per-term tolerances (canonical_multiplet_expectation's
own IMAGINARY_PART_TOLERANCE=1e-10 truncation, empirically <=1e-14 in
practice per the accepted 1C-2a audit), stays comfortably under 1e-8.
The tighter 1e-10 "analytic" tolerance used elsewhere (e.g. V11) is
deliberately NOT reused here: it was frozen for a single direct
value-vs-constant comparison, not a multi-term sum, and applying it here
would risk spurious failures from legitimate accumulated floating noise
across many summed terms."""


@dataclass(frozen=True, slots=True)
class FlavorTotalSumValidation:
    """Result of validating sum_i C_TT_conn(i,i) + sum_{i!=j} C_TT_conn(i,j)
    == T(T+1) for one spectral group. `applicable` is False (and every
    other field is None) whenever the group is not a genuine
    complete_multiplet with a resolved twice_T label -- T is not an exact
    quantum number for a partial_subspace group (D018/1B-4), so no
    verdict, exact or otherwise, is ever produced for one; this is a
    normal, expected scientific outcome, never an exception."""

    applicable: bool
    measured: float | None
    expected: float | None
    residual: float | None
    is_valid: bool | None

    def __post_init__(self) -> None:
        fields = (self.measured, self.expected, self.residual, self.is_valid)
        if not self.applicable:
            if any(field is not None for field in fields):
                raise ValueError("a non-applicable FlavorTotalSumValidation must carry no measured/expected/residual/is_valid")
            return
        if any(field is None for field in fields):
            raise ValueError("an applicable FlavorTotalSumValidation must carry measured, expected, residual, and is_valid")
        if not (math.isfinite(self.measured) and math.isfinite(self.expected) and math.isfinite(self.residual)):
            raise ValueError(f"measured/expected/residual must be finite, got {self.measured}, {self.expected}, {self.residual}")
        if self.expected < 0:
            raise ValueError(f"expected must be >= 0 (T(T+1) for T >= 0), got {self.expected}")
        if self.residual < 0:
            raise ValueError(f"residual must be >= 0, got {self.residual}")
        if not isinstance(self.is_valid, bool):
            raise ValueError(f"is_valid must be a bool, got {type(self.is_valid)}")


def validate_flavor_total_sum(
    status: str,
    twice_T: int | None,
    diagonal_values: Mapping[int, float],
    off_diagonal_values: Mapping[tuple[int, int], float],
    *,
    tolerance: float = FLAVOR_TOTAL_SUM_TOLERANCE,
) -> FlavorTotalSumValidation:
    """Validates the exact Casimir sum rule for one already-processed
    spectral group. `diagonal_values` maps each site to its already-
    computed C_TT_conn(i,i); `off_diagonal_values` maps each ORDERED pair
    (i,j), i!=j, to its already-computed C_TT_conn(i,j) -- both orders
    are summed exactly as serialized (D021), never divided by two and
    never reconstructed from a single orbit-averaged representative.
    C_TT_raw is never accepted here: the sum rule holds exactly for the
    CONNECTED correlator only, because <T_i^a>_group = 0 for a genuine
    complete_multiplet (Schur), making C_TT_conn(i,i) == C_TT_raw(i,i)
    there -- but this identity is never assumed on the input, only on
    the fact that the caller passed C_TT_conn values.

    Not applicable (and no verdict of any kind) unless status is exactly
    "complete_multiplet" and twice_T resolved to a real int -- never a
    silent best-effort attempt on a partial_subspace group. Completeness
    of the input mappings is checked ONLY on this applicable path (1C-3b
    corrective, docs/governance/current-task.md): `diagonal_values` must
    be non-empty, and `off_diagonal_values` must carry EXACTLY the
    N*(N-1) ordered pairs implied by `diagonal_values`'s own site set --
    a missing direction, a missing pair, a foreign site, or a diagonal
    pair (i,i) smuggled into off_diagonal_values all raise ValueError,
    since a coincidentally-matching sum over an incomplete or
    inconsistent corpus would otherwise be indistinguishable from a
    genuine confirmation of the sum rule. This is a structural
    incoherence of the CALL, never a scientific outcome -- it is
    reported by raising, never by is_valid=False, which stays reserved
    for a structurally complete corpus whose physical sum simply misses
    T(T+1) beyond tolerance."""
    if status != COMPLETE_MULTIPLET or twice_T is None:
        return FlavorTotalSumValidation(applicable=False, measured=None, expected=None, residual=None, is_valid=None)

    if isinstance(twice_T, bool) or not isinstance(twice_T, int) or twice_T < 0:
        raise ValueError(f"twice_T must be a non-negative int when applicable, got {twice_T!r}")

    sites = set(diagonal_values.keys())
    if not sites:
        raise ValueError("diagonal_values must not be empty for an applicable (complete_multiplet) group")

    expected_off_diagonal_pairs = {(i, j) for i in sites for j in sites if i != j}
    actual_off_diagonal_pairs = set(off_diagonal_values.keys())
    if actual_off_diagonal_pairs != expected_off_diagonal_pairs:
        missing = sorted(expected_off_diagonal_pairs - actual_off_diagonal_pairs)
        unexpected = sorted(actual_off_diagonal_pairs - expected_off_diagonal_pairs)
        raise ValueError(
            "off_diagonal_values must carry exactly the N*(N-1) ordered pairs implied by diagonal_values's site "
            f"set {sorted(sites)} -- missing={missing}, unexpected={unexpected} (a diagonal pair (i,i), a foreign "
            "site, or a one-directional pair all surface here)"
        )

    for value in (*diagonal_values.values(), *off_diagonal_values.values()):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"every C_TT_conn value must be a finite number, got {value!r}")

    resolved_T = twice_T / 2.0
    expected = resolved_T * (resolved_T + 1.0)
    measured = sum(diagonal_values.values()) + sum(off_diagonal_values.values())
    residual = abs(measured - expected)
    return FlavorTotalSumValidation(
        applicable=True, measured=measured, expected=expected, residual=residual, is_valid=residual <= tolerance
    )
