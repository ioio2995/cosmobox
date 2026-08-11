"""Per-multiplet Level 2 metrics: M_TT, R_eff, A_QQ, M_QQ, and the numerical
zero-resolution guards for a HIGH-LOW spectral contrast.

Lot L2-D1-METRICS-AND-PROFILE-PRIMITIVES. Definitions are exactly those
frozen by docs/levels/level2/spectral-regime-design.md (SS6-7),
docs/levels/level2/profile-comparison-preregistration.md (SS10) and
docs/levels/level2/numerical-guard-protocol.md (SS8-9). This module
contains no physics: it is a pure, deterministic evaluation of matrices and
mappings supplied by the caller. No real Level2 multiplet data is produced
or consumed here.

NUMERICAL_GUARD_M_TT and NUMERICAL_GUARD_R_EFF are the frozen L2-C1
reproducibility guards. They resolve the sign of a HIGH-LOW contrast against
pipeline floating-point noise only; they are never a physical effect size,
a statistical significance threshold, or an inter-S matching criterion.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Frozen numerical zero-resolution guards (L2-C1, see
# docs/levels/level2/numerical-guard-protocol.md SS8 and
# docs/governance/current-task.md "Resultat L2-C1"). REPRODUCIBILITY_ONLY:
# never a physical effect size or significance threshold.
# ---------------------------------------------------------------------------

NUMERICAL_GUARD_M_TT: float = 1e-16
NUMERICAL_GUARD_R_EFF: float = 1e-15

_GUARD_BY_METRIC: dict[str, float] = {
    "M_TT": NUMERICAL_GUARD_M_TT,
    "R_eff": NUMERICAL_GUARD_R_EFF,
}

NUMERICALLY_UNRESOLVED = "NUMERICALLY_UNRESOLVED"
POSITIVE = "POSITIVE"
NEGATIVE = "NEGATIVE"

ZERO_CTT_MATRIX = "ZERO_CTT_MATRIX"
NO_NUMERIC_RHO_QQ_PAIR = "NO_NUMERIC_RHO_QQ_PAIR"


@dataclass(frozen=True, slots=True)
class Available:
    """A scalar that is either a finite numeric value, or explicitly
    NOT_AVAILABLE with a reason. Never a bare zero standing in for an
    absent value -- mirrors the null-aware pattern already established by
    cosmobox.level1.local_observables.NormalizedMoment."""

    value: float | None
    reason: str | None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.reason is None):
            raise ValueError("value is None if and only if reason is set")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"value must be finite when present, got {self.value}")


# ---------------------------------------------------------------------------
# M_TT -- off-diagonal RMS strength (spectral-regime-design.md SS6.1)
# ---------------------------------------------------------------------------


def _validate_square_finite_matrix(matrix: np.ndarray, *, min_n: int) -> np.ndarray:
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"matrix must be square 2-D, got shape {matrix.shape}")
    n = matrix.shape[0]
    if n < min_n:
        raise ValueError(f"matrix dimension must be >= {min_n}, got {n}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix must contain only finite entries")
    return matrix


def m_tt(matrix: np.ndarray) -> float:
    """sqrt( 1/(N(N-1)) * sum_{i!=j} |C_ij|^2 ). Off-diagonal only, N>=2."""
    matrix = _validate_square_finite_matrix(matrix, min_n=2)
    n = matrix.shape[0]
    off_diagonal_mask = ~np.eye(n, dtype=bool)
    sum_sq = float(np.sum(np.abs(matrix[off_diagonal_mask]) ** 2))
    return math.sqrt(sum_sq / (n * (n - 1)))


# ---------------------------------------------------------------------------
# R_eff -- normalized entropic effective rank (spectral-regime-design.md
# SS6.2)
# ---------------------------------------------------------------------------


def r_eff(matrix: np.ndarray) -> Available:
    """r_eff = exp(-sum p_k ln p_k) over singular-value weights p_k = s_k /
    sum(s), then R_eff = r_eff / N. NOT_AVAILABLE (ZERO_CTT_MATRIX) if
    sum(s) == 0, with no artificial epsilon added to any denominator."""
    matrix = _validate_square_finite_matrix(matrix, min_n=1)
    n = matrix.shape[0]
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    total = float(np.sum(singular_values))
    if total == 0.0:
        return Available(None, ZERO_CTT_MATRIX)
    weights = singular_values[singular_values > 0.0] / total
    entropy = float(-np.sum(weights * np.log(weights)))
    return Available(math.exp(entropy) / n, None)


# ---------------------------------------------------------------------------
# rho_QQ control diagnostics -- A_QQ, M_QQ (spectral-regime-design.md SS7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RhoQQEntry:
    """One ordered-pair rho_QQ(i,j) entry: a finite numeric value, or an
    explicit structural null (e.g. zero local charge variance). Decoupled
    from cosmobox.level1's own NormalizedMoment: Level2's primitives take
    plain data in, they do not reach into Level1 engine objects."""

    value: float | None
    null_reason: str | None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.null_reason is None):
            raise ValueError("value is None if and only if null_reason is set")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"value must be finite when present, got {self.value}")


def _validate_complete_ordered_pairs(pairs: Mapping[tuple[int, int], RhoQQEntry], n: int) -> None:
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    expected = {(i, j) for i in range(n) for j in range(n) if i != j}
    actual = set(pairs.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(
            f"pairs must carry exactly the {n * (n - 1)} ordered pairs for n={n} -- "
            f"missing={missing}, unexpected={unexpected}"
        )


def a_qq(pairs: Mapping[tuple[int, int], RhoQQEntry], n: int) -> float:
    """N_numeric / [N(N-1)] -- fraction of numeric rho_QQ ordered pairs."""
    _validate_complete_ordered_pairs(pairs, n)
    n_numeric = sum(1 for entry in pairs.values() if entry.value is not None)
    return n_numeric / (n * (n - 1))


def m_qq(pairs: Mapping[tuple[int, int], RhoQQEntry], n: int) -> Available:
    """sqrt( 1/N_numeric * sum_numeric |rho_QQ|^2 ). NOT_AVAILABLE
    (NO_NUMERIC_RHO_QQ_PAIR) if no pair is numeric. Never imputes nulls."""
    _validate_complete_ordered_pairs(pairs, n)
    numeric_values = [entry.value for entry in pairs.values() if entry.value is not None]
    if not numeric_values:
        return Available(None, NO_NUMERIC_RHO_QQ_PAIR)
    mean_sq = sum(value * value for value in numeric_values) / len(numeric_values)
    return Available(math.sqrt(mean_sq), None)


# ---------------------------------------------------------------------------
# Numerical zero-resolution classification (numerical-guard-protocol.md SS9,
# profile-comparison-preregistration.md SS7)
# ---------------------------------------------------------------------------


def classify_contrast(delta: float, *, metric: str) -> str:
    """POSITIVE / NEGATIVE / NUMERICALLY_UNRESOLVED for a HIGH-LOW-style
    contrast on `metric` in {"M_TT", "R_eff"}, using that metric's frozen
    guard. abs(delta) <= guard -> NUMERICALLY_UNRESOLVED (inclusive
    boundary, per numerical-guard-protocol.md SS9)."""
    if metric not in _GUARD_BY_METRIC:
        raise ValueError(f"metric must be one of {sorted(_GUARD_BY_METRIC)}, got {metric!r}")
    if not math.isfinite(delta):
        raise ValueError(f"delta must be finite, got {delta}")
    guard = _GUARD_BY_METRIC[metric]
    if abs(delta) <= guard:
        return NUMERICALLY_UNRESOLVED
    return POSITIVE if delta > 0.0 else NEGATIVE
