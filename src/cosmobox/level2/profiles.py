"""Spectral coordinates, LOW/MID/HIGH regime aggregation, contrasts, and
threshold-free inter-S profile comparison primitives.

Lot L2-D1-METRICS-AND-PROFILE-PRIMITIVES. Definitions are exactly those
frozen by docs/levels/level2/spectral-regime-design.md (SS4, SS9-10) and
docs/levels/level2/profile-comparison-preregistration.md (SS3-8, SS11).
This module contains no physics: it evaluates coordinates, weighted means
and step-function integrals from data supplied by the caller. No
multiplet-to-multiplet inter-S matching is ever performed (FORBIDDEN by the
frozen preregistration); comparison is always through the common exact
partition of two independent step functions.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from cosmobox.level2.metrics import NUMERICALLY_UNRESOLVED, Available, classify_contrast

CONSTANT_PROFILE = "CONSTANT_PROFILE"
ZERO_PROFILE_VARIANCE = "ZERO_PROFILE_VARIANCE"
NO_EVALUABLE_SPECTRAL_WEIGHT = "NO_EVALUABLE_SPECTRAL_WEIGHT"
REGIME_MEAN_NOT_AVAILABLE = "REGIME_MEAN_NOT_AVAILABLE"

NOT_EVALUABLE = "NOT_EVALUABLE"
NO_RESOLVED_SPECTRAL_CONTRAST = "NO_RESOLVED_SPECTRAL_CONTRAST"
OPPOSITE_INTER_S_DIRECTION = "OPPOSITE_INTER_S_DIRECTION"
SAME_INTER_S_DIRECTION = "SAME_INTER_S_DIRECTION"


# ---------------------------------------------------------------------------
# Spectral coordinates (spectral-regime-design.md SS4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpectralInterval:
    """A complete multiplet's exact cumulative-population interval
    [start, end] subset of [0,1], and its midpoint q."""

    start: float
    end: float
    q_mid: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.start < self.end <= 1.0):
            raise ValueError(f"require 0 <= start < end <= 1, got start={self.start}, end={self.end}")
        if self.q_mid != (self.start + self.end) / 2:
            raise ValueError("q_mid must equal (start + end) / 2")

    @property
    def length(self) -> float:
        return self.end - self.start


def spectral_interval(n_before: int, multiplicity: int, dimension: int) -> SpectralInterval:
    """start = n_before/D, end = (n_before+multiplicity)/D, q = midpoint."""
    if dimension < 1:
        raise ValueError(f"dimension must be >= 1, got {dimension}")
    if multiplicity < 1:
        raise ValueError(f"multiplicity must be >= 1, got {multiplicity}")
    if n_before < 0:
        raise ValueError(f"n_before must be >= 0, got {n_before}")
    if n_before + multiplicity > dimension:
        raise ValueError(
            f"n_before + multiplicity must be <= dimension, got {n_before} + {multiplicity} > {dimension}"
        )
    start = n_before / dimension
    end = (n_before + multiplicity) / dimension
    return SpectralInterval(start, end, (start + end) / 2)


def build_spectral_partition(multiplicities: Sequence[int]) -> list[SpectralInterval]:
    """Contiguous intervals for a sequence of complete-multiplet
    multiplicities, in spectral order. sum(multiplicities) becomes D;
    coverage of exactly [0,1] with no gap or overlap follows by
    construction from the shared cumulative dimension."""
    if not multiplicities:
        raise ValueError("multiplicities must not be empty")
    dimension = sum(multiplicities)
    intervals: list[SpectralInterval] = []
    n_before = 0
    for multiplicity in multiplicities:
        intervals.append(spectral_interval(n_before, multiplicity, dimension))
        n_before += multiplicity
    if intervals[-1].end != 1.0:
        raise ValueError(f"partition must cover up to exactly 1.0, got {intervals[-1].end}")
    return intervals


def epsilon(energy: float, e_min: float, e_max: float) -> float:
    """(E - E_min) / (E_max - E_min). Requires a non-degenerate spectrum."""
    if not (math.isfinite(energy) and math.isfinite(e_min) and math.isfinite(e_max)):
        raise ValueError(f"energy, e_min, e_max must be finite, got {energy}, {e_min}, {e_max}")
    if not e_max > e_min:
        raise ValueError(f"e_max must be > e_min, got e_max={e_max}, e_min={e_min}")
    return (energy - e_min) / (e_max - e_min)


# ---------------------------------------------------------------------------
# LOW / MID / HIGH regimes (spectral-regime-design.md SS9-10)
# ---------------------------------------------------------------------------

LOW = "LOW"
MID = "MID"
HIGH = "HIGH"

REGIME_BOUNDS: dict[str, tuple[float, float]] = {
    LOW: (0.0, 1.0 / 3.0),
    MID: (1.0 / 3.0, 2.0 / 3.0),
    HIGH: (2.0 / 3.0, 1.0),
}


def regime_overlap_length(interval: SpectralInterval, regime: str) -> float:
    """Exact length of the intersection of `interval` with `regime`'s
    bounds. A multiplet crossing a regime boundary contributes to both
    regimes strictly by this intersection length -- never by reassigning
    its whole weight based on its midpoint."""
    if regime not in REGIME_BOUNDS:
        raise ValueError(f"regime must be one of {sorted(REGIME_BOUNDS)}, got {regime!r}")
    lo, hi = REGIME_BOUNDS[regime]
    overlap = min(interval.end, hi) - max(interval.start, lo)
    return max(0.0, overlap)


@dataclass(frozen=True, slots=True)
class GroupValue:
    """One complete multiplet's spectral interval and a scalar metric
    value for it (or None if that metric is NOT_AVAILABLE for this
    group -- never imputed)."""

    interval: SpectralInterval
    value: float | None


@dataclass(frozen=True, slots=True)
class RegimeMean:
    """Weighted mean of a metric over one regime, plus the fraction of that
    regime's total spectral weight that was actually evaluable. value is
    None (with a reason) only when no group contributes any evaluable
    weight to the regime."""

    value: float | None
    reason: str | None
    evaluable_weight_fraction: float

    def __post_init__(self) -> None:
        if (self.value is None) == (self.reason is None):
            raise ValueError("value is None if and only if reason is set")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"value must be finite when present, got {self.value}")
        if not (0.0 <= self.evaluable_weight_fraction <= 1.0 + 1e-12):
            raise ValueError(f"evaluable_weight_fraction must be in [0,1], got {self.evaluable_weight_fraction}")


def regime_mean(groups: Sequence[GroupValue], regime: str) -> RegimeMean:
    """bar X_R = sum_g w_g X_g / sum_g w_g, w_g = exact overlap length of g
    with `regime`, restricted to groups with an evaluable value (no
    imputation). evaluable_weight_fraction = evaluable weight / regime
    total weight (|R|)."""
    if regime not in REGIME_BOUNDS:
        raise ValueError(f"regime must be one of {sorted(REGIME_BOUNDS)}, got {regime!r}")
    lo, hi = REGIME_BOUNDS[regime]
    total_weight = hi - lo

    weighted_sum = 0.0
    evaluable_weight = 0.0
    for group in groups:
        weight = regime_overlap_length(group.interval, regime)
        if weight <= 0.0:
            continue
        if group.value is not None:
            weighted_sum += weight * group.value
            evaluable_weight += weight

    fraction = evaluable_weight / total_weight if total_weight > 0.0 else 0.0
    if evaluable_weight <= 0.0:
        return RegimeMean(None, NO_EVALUABLE_SPECTRAL_WEIGHT, fraction)
    return RegimeMean(weighted_sum / evaluable_weight, None, fraction)


# ---------------------------------------------------------------------------
# Contrasts (profile-comparison-preregistration.md SS5)
# ---------------------------------------------------------------------------


def _contrast(mean_a: RegimeMean, mean_b: RegimeMean) -> Available:
    if mean_a.value is None or mean_b.value is None:
        return Available(None, REGIME_MEAN_NOT_AVAILABLE)
    return Available(mean_a.value - mean_b.value, None)


def delta_hl(high: RegimeMean, low: RegimeMean) -> Available:
    """Delta^HL_X = bar X_HIGH - bar X_LOW. Primary contrast."""
    return _contrast(high, low)


def delta_ml(mid: RegimeMean, low: RegimeMean) -> Available:
    """Delta^ML_X = bar X_MID - bar X_LOW. Descriptive."""
    return _contrast(mid, low)


def delta_hm(high: RegimeMean, mid: RegimeMean) -> Available:
    """Delta^HM_X = bar X_HIGH - bar X_MID. Descriptive."""
    return _contrast(high, mid)


# ---------------------------------------------------------------------------
# Step-function profiles and their exact common partition
# (profile-comparison-preregistration.md SS3, SS8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProfilePiece:
    """One constant piece X(q) = value for q in [start, end) of a
    multiplicity-weighted step-function profile."""

    start: float
    end: float
    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.start < self.end <= 1.0):
            raise ValueError(f"require 0 <= start < end <= 1, got start={self.start}, end={self.end}")
        if not math.isfinite(self.value):
            raise ValueError(f"value must be finite, got {self.value}")

    @property
    def length(self) -> float:
        return self.end - self.start


def build_profile(intervals: Sequence[SpectralInterval], values: Sequence[float | None]) -> list[ProfilePiece]:
    """Step-function pieces from parallel (interval, value) sequences.
    Groups whose value is None (NOT_AVAILABLE) are dropped from the
    profile's domain -- never imputed, never interpolated across."""
    if len(intervals) != len(values):
        raise ValueError(f"intervals and values must have the same length, got {len(intervals)} and {len(values)}")
    pieces = [
        ProfilePiece(interval.start, interval.end, value)
        for interval, value in zip(intervals, values)
        if value is not None
    ]
    return sorted(pieces, key=lambda piece: piece.start)


def _validate_full_coverage(pieces: Sequence[ProfilePiece]) -> list[ProfilePiece]:
    if not pieces:
        raise ValueError("profile must contain at least one piece")
    ordered = sorted(pieces, key=lambda piece: piece.start)
    if ordered[0].start != 0.0 or ordered[-1].end != 1.0:
        raise ValueError(
            "profile must be evaluable on exactly [0,1] with no gap for this operation "
            f"(got domain [{ordered[0].start}, {ordered[-1].end}])"
        )
    for previous, current in zip(ordered, ordered[1:]):
        if current.start != previous.end:
            raise ValueError(
                f"profile pieces must be contiguous with no gap or overlap, got "
                f"[{previous.start},{previous.end}) then [{current.start},{current.end})"
            )
    return ordered


def common_breakpoints(pieces_a: Sequence[ProfilePiece], pieces_b: Sequence[ProfilePiece]) -> list[float]:
    """Exact union of both profiles' interval boundaries -- no
    interpolation, no smoothing, no multiplet matching."""
    points = {piece.start for piece in pieces_a} | {piece.end for piece in pieces_a}
    points |= {piece.start for piece in pieces_b} | {piece.end for piece in pieces_b}
    return sorted(points)


def _value_at(pieces: Sequence[ProfilePiece], q: float) -> float:
    for piece in pieces:
        if piece.start <= q < piece.end:
            return piece.value
    if pieces and q == pieces[-1].end:
        return pieces[-1].value
    raise ValueError(f"q={q} is not covered by the supplied profile")


def profile_mean(pieces: Sequence[ProfilePiece]) -> float:
    """integral_0^1 X(q) dq for a profile fully evaluable on [0,1]."""
    ordered = _validate_full_coverage(pieces)
    return sum(piece.length * piece.value for piece in ordered)


def _is_structurally_constant(pieces: Sequence[ProfilePiece]) -> bool:
    """True iff every piece carries exactly the same value. Mathematically
    equivalent, in exact arithmetic, to a zero functional variance -- but
    tested directly on the raw piece values instead of through a weighted
    sum of squared deviations, which can fail to land on exactly 0.0 purely
    from floating-point summation order even when every value is bit-for-
    bit identical. No tolerance of any kind is involved."""
    first_value = pieces[0].value
    return all(piece.value == first_value for piece in pieces)


# ---------------------------------------------------------------------------
# C_X_23, D_X_23 (profile-comparison-preregistration.md SS8)
# ---------------------------------------------------------------------------


def cross_profile_correlation(
    pieces_a: Sequence[ProfilePiece],
    pieces_b: Sequence[ProfilePiece],
) -> Available:
    """C_X^23: centered functional correlation between two profiles fully
    evaluable on [0,1], integrated over their exact common partition.
    NOT_AVAILABLE (CONSTANT_PROFILE) if profile A or profile B is
    structurally constant (see _is_structurally_constant) -- the exact,
    tolerance-free reading of "numerically zero" functional variance from
    profile-comparison-preregistration.md SS8. The L2-C1 numerical guards
    (NUMERICAL_GUARD_M_TT, NUMERICAL_GUARD_R_EFF) are never used here: they
    are frozen exclusively for resolving the sign of Delta_HL
    (classify_contrast), per numerical-guard-protocol.md SS10."""
    ordered_a = _validate_full_coverage(pieces_a)
    ordered_b = _validate_full_coverage(pieces_b)

    if _is_structurally_constant(ordered_a) or _is_structurally_constant(ordered_b):
        return Available(None, CONSTANT_PROFILE)

    mu_a = sum(piece.length * piece.value for piece in ordered_a)
    mu_b = sum(piece.length * piece.value for piece in ordered_b)
    var_a = sum(piece.length * (piece.value - mu_a) ** 2 for piece in ordered_a)
    var_b = sum(piece.length * (piece.value - mu_b) ** 2 for piece in ordered_b)

    breakpoints = common_breakpoints(ordered_a, ordered_b)
    covariance = 0.0
    for lo, hi in zip(breakpoints, breakpoints[1:]):
        length = hi - lo
        mid = (lo + hi) / 2
        value_a = _value_at(ordered_a, mid)
        value_b = _value_at(ordered_b, mid)
        covariance += length * (value_a - mu_a) * (value_b - mu_b)

    return Available(covariance / math.sqrt(var_a * var_b), None)


def cross_profile_distance(
    pieces_a: Sequence[ProfilePiece],
    pieces_b: Sequence[ProfilePiece],
) -> Available:
    """D_X^23: normalized functional distance between two profiles fully
    evaluable on [0,1]. NOT_AVAILABLE (ZERO_PROFILE_VARIANCE) iff the
    pooled-variance denominator is exactly zero, which holds iff BOTH
    profile A and profile B are structurally constant (a sum of two
    non-negative terms is zero iff each term is zero) -- see
    _is_structurally_constant. No D_max is ever introduced. The L2-C1
    numerical guards are never used here; see cross_profile_correlation."""
    ordered_a = _validate_full_coverage(pieces_a)
    ordered_b = _validate_full_coverage(pieces_b)

    if _is_structurally_constant(ordered_a) and _is_structurally_constant(ordered_b):
        return Available(None, ZERO_PROFILE_VARIANCE)

    mu_a = sum(piece.length * piece.value for piece in ordered_a)
    mu_b = sum(piece.length * piece.value for piece in ordered_b)
    var_a = sum(piece.length * (piece.value - mu_a) ** 2 for piece in ordered_a)
    var_b = sum(piece.length * (piece.value - mu_b) ** 2 for piece in ordered_b)
    pooled_variance = 0.5 * (var_a + var_b)

    breakpoints = common_breakpoints(ordered_a, ordered_b)
    squared_diff_integral = 0.0
    for lo, hi in zip(breakpoints, breakpoints[1:]):
        length = hi - lo
        mid = (lo + hi) / 2
        value_a = _value_at(ordered_a, mid)
        value_b = _value_at(ordered_b, mid)
        squared_diff_integral += length * (value_a - value_b) ** 2

    return Available(math.sqrt(squared_diff_integral / pooled_variance), None)


# ---------------------------------------------------------------------------
# Primary inter-S taxonomy (profile-comparison-preregistration.md SS11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InterSClassification:
    """Primary inter-S taxonomy verdict for one geometry and one primary
    metric, plus the descriptive per-S direction that produced it (never a
    verdict on its own)."""

    taxonomy: str
    direction_s2: str | None
    direction_s3: str | None

    def __post_init__(self) -> None:
        allowed = {NOT_EVALUABLE, NO_RESOLVED_SPECTRAL_CONTRAST, OPPOSITE_INTER_S_DIRECTION, SAME_INTER_S_DIRECTION}
        if self.taxonomy not in allowed:
            raise ValueError(f"taxonomy must be one of {sorted(allowed)}, got {self.taxonomy!r}")


def classify_inter_s(contrast_s2: Available, contrast_s3: Available, *, metric: str) -> InterSClassification:
    """NOT_EVALUABLE if either contrast is unavailable; else
    NO_RESOLVED_SPECTRAL_CONTRAST if either sign is numerically unresolved;
    else OPPOSITE_INTER_S_DIRECTION or SAME_INTER_S_DIRECTION by sign
    agreement. No multiplet-by-multiplet matching is involved: both
    contrasts are pre-aggregated regime contrasts for the same metric."""
    if contrast_s2.value is None or contrast_s3.value is None:
        return InterSClassification(NOT_EVALUABLE, None, None)

    direction_s2 = classify_contrast(contrast_s2.value, metric=metric)
    direction_s3 = classify_contrast(contrast_s3.value, metric=metric)

    if direction_s2 == NUMERICALLY_UNRESOLVED or direction_s3 == NUMERICALLY_UNRESOLVED:
        return InterSClassification(NO_RESOLVED_SPECTRAL_CONTRAST, direction_s2, direction_s3)
    if direction_s2 != direction_s3:
        return InterSClassification(OPPOSITE_INTER_S_DIRECTION, direction_s2, direction_s3)
    return InterSClassification(SAME_INTER_S_DIRECTION, direction_s2, direction_s3)
