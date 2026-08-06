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
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.lattice import Lattice

from .matter import build_dressed_matter_matrix
from .paths import make_oriented_path

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
