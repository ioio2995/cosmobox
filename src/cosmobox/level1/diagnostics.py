"""Normative diagnostics of a restricted operator O_rest = Psi^dagger O Psi.

Level1B lot 1B-5 (docs/levels/level1/specification.md section 10,
docs/levels/level1/implementation-design.md section 6.3). Builds on lot
1B-3's restricted.build_restricted_operator -- O_rest is supplied already
constructed, never recomputed here.

Both build_hermitian_restricted_diagnostics and
build_non_hermitian_restricted_diagnostics accept a group_state of EITHER
status ("complete_multiplet" or "partial_subspace"), with no separate
gating: a diagnostic reports properties of the already-constructed O_rest
matrix itself, not a canonical multiplet average or a scientific verdict
(unlike restricted.canonical_multiplet_expectation /
exploratory_partial_subspace_mean, whose OUTPUT IS the multiplet average
and which therefore does gate). status is carried explicitly on every
returned diagnostics object instead. A diagnostic built from a
"partial_subspace" group_state is EXPLORATORY: the group's true
multiplicity may exceed the observed one, and no definitive scientific
verdict may be drawn from it (docs/levels/level1/specification.md
section 4) -- callers must check .status before treating any of these
fields as conclusive.

Frozen exclusions for the non-Hermitian case (specification.md section
10): no complex eigenvalues of a non-normal matrix, no eigenvectors, no
Schur decomposition, no spectral radius, no pseudospectrum -- only trace,
singular values (via SVD), and the Frobenius norm. np.linalg.eigvalsh is
the only spectral API used anywhere in this module, and only for the
Hermitian case (real eigenvalues, no eigenvectors returned to the
caller); V20 confirms via static AST inspection that no forbidden
spectral API is ever called here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .restricted import COMPLETE_MULTIPLET, HERMITICITY_TOLERANCE, IMAGINARY_PART_TOLERANCE, PARTIAL_SUBSPACE, SpectralGroupState

_VALID_STATUSES = (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE)

NUMERICAL_IDENTITY_ATOL = 1e-10
NUMERICAL_IDENTITY_RTOL = 1e-8


def _validate_restricted_operator(o_rest: np.ndarray, group_state: SpectralGroupState) -> np.ndarray:
    """Shared precondition check for both diagnostic builders below:
    o_rest must be a 2-D, square, finite array whose shape matches
    group_state.multiplicity exactly. Returns a controlled complex128
    conversion, not a view sharing dtype/mutability with the caller's array.
    """
    o_rest = np.asarray(o_rest)
    if o_rest.ndim != 2:
        raise ValueError(f"o_rest must be 2-D, got shape {o_rest.shape}")
    if o_rest.shape[0] != o_rest.shape[1]:
        raise ValueError(f"o_rest must be square, got shape {o_rest.shape}")
    if group_state.multiplicity == 0:
        raise ValueError("group_state.multiplicity must be nonzero")
    expected_shape = (group_state.multiplicity, group_state.multiplicity)
    if o_rest.shape != expected_shape:
        raise ValueError(
            f"o_rest has shape {o_rest.shape}, expected {expected_shape} from group_state.multiplicity"
        )
    if not np.all(np.isfinite(o_rest)):
        raise ValueError("o_rest contains non-finite values")
    return np.asarray(o_rest, dtype=np.complex128)


# ---------------------------------------------------------------------------
# Hermitian diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HermitianRestrictedDiagnostics:
    """Diagnostics of a Hermitian O_rest: trace, real ordered eigenvalues,
    min/max/spectral_range, Frobenius norm, Hermiticity defect.

    status is carried explicitly and is never lost: a "partial_subspace"
    instance is EXPLORATORY -- its true multiplicity may exceed the
    observed one, and none of its fields may be reported as a definitive
    scientific verdict (only a "complete_multiplet" instance may be).
    """

    status: str
    trace: float
    eigenvalues: tuple[float, ...]
    minimum: float
    maximum: float
    spectral_range: float
    frobenius_norm: float
    hermiticity_defect: float

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {_VALID_STATUSES}, got {self.status!r}")

        for name, value in (
            ("trace", self.trace),
            ("minimum", self.minimum),
            ("maximum", self.maximum),
            ("spectral_range", self.spectral_range),
            ("frobenius_norm", self.frobenius_norm),
            ("hermiticity_defect", self.hermiticity_defect),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")

        if not self.eigenvalues:
            raise ValueError("eigenvalues must be non-empty")
        for index, value in enumerate(self.eigenvalues):
            if not math.isfinite(value):
                raise ValueError(f"eigenvalues[{index}] is not finite: {value}")
        for index in range(1, len(self.eigenvalues)):
            if self.eigenvalues[index] < self.eigenvalues[index - 1]:
                raise ValueError("eigenvalues must be sorted ascending")

        if self.minimum != self.eigenvalues[0]:
            raise ValueError(f"minimum ({self.minimum}) must equal eigenvalues[0] ({self.eigenvalues[0]})")
        if self.maximum != self.eigenvalues[-1]:
            raise ValueError(f"maximum ({self.maximum}) must equal eigenvalues[-1] ({self.eigenvalues[-1]})")

        expected_range = self.maximum - self.minimum
        if not np.isclose(self.spectral_range, expected_range, atol=NUMERICAL_IDENTITY_ATOL, rtol=NUMERICAL_IDENTITY_RTOL):
            raise ValueError(
                f"spectral_range ({self.spectral_range}) does not match maximum - minimum ({expected_range})"
            )

        if self.hermiticity_defect < 0:
            raise ValueError(f"hermiticity_defect must be >= 0, got {self.hermiticity_defect}")

        expected_trace = sum(self.eigenvalues)
        if not np.isclose(self.trace, expected_trace, atol=NUMERICAL_IDENTITY_ATOL, rtol=NUMERICAL_IDENTITY_RTOL):
            raise ValueError(f"trace ({self.trace}) does not match sum(eigenvalues) ({expected_trace})")

        expected_frobenius_squared = sum(value * value for value in self.eigenvalues)
        if not np.isclose(
            self.frobenius_norm**2, expected_frobenius_squared, atol=NUMERICAL_IDENTITY_ATOL, rtol=NUMERICAL_IDENTITY_RTOL
        ):
            raise ValueError(
                f"frobenius_norm^2 ({self.frobenius_norm**2}) does not match sum(eigenvalues^2) "
                f"({expected_frobenius_squared})"
            )


def build_hermitian_restricted_diagnostics(
    o_rest: np.ndarray, group_state: SpectralGroupState
) -> HermitianRestrictedDiagnostics:
    """Diagnostics for a Hermitian O_rest. Raises ValueError if O_rest is
    not (numerically) Hermitian -- this function never silently reports
    eigenvalues/min/max for an operator that is not actually Hermitian.

    group_state may be "complete_multiplet" or "partial_subspace" -- both
    are accepted; the resulting status field must be checked by the
    caller before treating any field as a definitive scientific result
    ("partial_subspace" is exploratory only).
    """
    o_rest = _validate_restricted_operator(o_rest, group_state)

    hermiticity_defect = float(np.linalg.norm(o_rest - o_rest.conj().T, "fro"))
    if hermiticity_defect > HERMITICITY_TOLERANCE:
        raise ValueError(
            f"O_rest is not Hermitian (||O_rest - O_rest^dagger||_F = {hermiticity_defect}, "
            f"tolerance {HERMITICITY_TOLERANCE})"
        )

    eigenvalues = np.linalg.eigvalsh(o_rest)  # real, ascending; no eigenvectors ever returned to the caller

    raw_trace = complex(np.trace(o_rest))
    if abs(raw_trace.imag) > IMAGINARY_PART_TOLERANCE:
        raise ValueError(
            f"trace(O_rest) has a non-negligible imaginary part {raw_trace.imag} "
            f"(tolerance {IMAGINARY_PART_TOLERANCE}) for a supposedly Hermitian O_rest"
        )

    frobenius_norm = float(np.linalg.norm(o_rest, "fro"))

    return HermitianRestrictedDiagnostics(
        status=group_state.status,
        trace=float(raw_trace.real),
        eigenvalues=tuple(float(value) for value in eigenvalues),
        minimum=float(eigenvalues[0]),
        maximum=float(eigenvalues[-1]),
        spectral_range=float(eigenvalues[-1] - eigenvalues[0]),
        frobenius_norm=frobenius_norm,
        hermiticity_defect=hermiticity_defect,
    )


# ---------------------------------------------------------------------------
# Non-Hermitian diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NonHermitianRestrictedDiagnostics:
    """Diagnostics of a possibly non-Hermitian O_rest: complex trace,
    real non-negative ordered singular values, Frobenius norm.

    Deliberately excludes eigenvalues, eigenvectors, and any Schur-based
    quantity (specification.md section 10) -- there is no field here
    that could ever hold a complex eigenvalue of a non-normal matrix.

    status is carried explicitly; a "partial_subspace" instance is
    EXPLORATORY only, and none of its fields may be reported as a
    definitive scientific verdict.
    """

    status: str
    trace: complex
    singular_values: tuple[float, ...]
    frobenius_norm: float

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {_VALID_STATUSES}, got {self.status!r}")

        trace = complex(self.trace)
        if not (math.isfinite(trace.real) and math.isfinite(trace.imag)):
            raise ValueError(f"trace is not finite: {self.trace}")

        if not self.singular_values:
            raise ValueError("singular_values must be non-empty")
        for index, value in enumerate(self.singular_values):
            if not math.isfinite(value):
                raise ValueError(f"singular_values[{index}] is not finite: {value}")
            if value < 0:
                raise ValueError(f"singular_values[{index}] must be >= 0, got {value}")
        for index in range(1, len(self.singular_values)):
            if self.singular_values[index] > self.singular_values[index - 1]:
                raise ValueError("singular_values must be sorted descending")

        if not math.isfinite(self.frobenius_norm) or self.frobenius_norm < 0:
            raise ValueError(f"frobenius_norm must be finite and >= 0, got {self.frobenius_norm}")

        expected_frobenius_squared = sum(value * value for value in self.singular_values)
        if not np.isclose(
            self.frobenius_norm**2, expected_frobenius_squared, atol=NUMERICAL_IDENTITY_ATOL, rtol=NUMERICAL_IDENTITY_RTOL
        ):
            raise ValueError(
                f"frobenius_norm^2 ({self.frobenius_norm**2}) does not match sum(singular_values^2) "
                f"({expected_frobenius_squared})"
            )


def build_non_hermitian_restricted_diagnostics(
    o_rest: np.ndarray, group_state: SpectralGroupState
) -> NonHermitianRestrictedDiagnostics:
    """Diagnostics for a possibly non-Hermitian O_rest, using only
    np.trace, np.linalg.svd(..., compute_uv=False), and
    np.linalg.norm(..., "fro") -- never eigenvalues, eigenvectors, Schur
    decomposition, spectral radius, or pseudospectrum.

    group_state may be "complete_multiplet" or "partial_subspace" -- both
    are accepted; "partial_subspace" results are exploratory only.
    """
    o_rest = _validate_restricted_operator(o_rest, group_state)

    trace = complex(np.trace(o_rest))
    singular_values = np.linalg.svd(o_rest, compute_uv=False)
    frobenius_norm = float(np.linalg.norm(o_rest, "fro"))

    return NonHermitianRestrictedDiagnostics(
        status=group_state.status,
        trace=trace,
        singular_values=tuple(float(value) for value in singular_values),
        frobenius_norm=frobenius_norm,
    )
