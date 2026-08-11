from __future__ import annotations

import math

import pytest

from cosmobox.level2.metrics import NEGATIVE, NUMERICALLY_UNRESOLVED, POSITIVE, Available
from cosmobox.level2.profiles import (
    CONSTANT_PROFILE,
    HIGH,
    LOW,
    MID,
    NO_EVALUABLE_SPECTRAL_WEIGHT,
    NO_RESOLVED_SPECTRAL_CONTRAST,
    NOT_EVALUABLE,
    OPPOSITE_INTER_S_DIRECTION,
    REGIME_MEAN_NOT_AVAILABLE,
    SAME_INTER_S_DIRECTION,
    ZERO_PROFILE_VARIANCE,
    GroupValue,
    ProfilePiece,
    RegimeMean,
    build_profile,
    build_spectral_partition,
    classify_inter_s,
    common_breakpoints,
    cross_profile_correlation,
    cross_profile_distance,
    delta_hl,
    delta_hm,
    delta_ml,
    epsilon,
    regime_mean,
    regime_overlap_length,
    spectral_interval,
)

# ---------------------------------------------------------------------------
# Spectral coordinates
# ---------------------------------------------------------------------------


def test_spectral_interval_basic():
    interval = spectral_interval(n_before=2, multiplicity=3, dimension=10)
    assert interval.start == pytest.approx(0.2)
    assert interval.end == pytest.approx(0.5)
    assert interval.q_mid == pytest.approx(0.35)


def test_spectral_interval_rejects_overflow():
    with pytest.raises(ValueError):
        spectral_interval(n_before=8, multiplicity=3, dimension=10)


def test_build_spectral_partition_sums_exactly_to_one():
    intervals = build_spectral_partition([2, 1, 3, 4])
    assert intervals[0].start == 0.0
    assert intervals[-1].end == 1.0
    assert sum(interval.length for interval in intervals) == pytest.approx(1.0)


def test_build_spectral_partition_is_contiguous_no_gap_no_overlap():
    intervals = build_spectral_partition([1, 2, 1])
    for previous, current in zip(intervals, intervals[1:]):
        assert previous.end == current.start


def test_epsilon_basic():
    assert epsilon(5.0, e_min=0.0, e_max=10.0) == pytest.approx(0.5)
    assert epsilon(0.0, e_min=0.0, e_max=10.0) == pytest.approx(0.0)
    assert epsilon(10.0, e_min=0.0, e_max=10.0) == pytest.approx(1.0)


def test_epsilon_rejects_degenerate_spectrum():
    with pytest.raises(ValueError):
        epsilon(1.0, e_min=1.0, e_max=1.0)


# ---------------------------------------------------------------------------
# Regime overlap and weighted means
# ---------------------------------------------------------------------------


def test_regime_overlap_multiplet_crossing_one_third():
    interval = spectral_interval(n_before=2, multiplicity=3, dimension=10)  # [0.2, 0.5)
    low_overlap = regime_overlap_length(interval, LOW)  # [0, 1/3)
    mid_overlap = regime_overlap_length(interval, MID)  # [1/3, 2/3)
    assert low_overlap == pytest.approx(1.0 / 3.0 - 0.2)
    assert mid_overlap == pytest.approx(0.5 - 1.0 / 3.0)
    assert low_overlap + mid_overlap == pytest.approx(interval.length)
    assert regime_overlap_length(interval, HIGH) == pytest.approx(0.0)


def test_regime_overlap_multiplet_crossing_two_thirds():
    interval = spectral_interval(n_before=5, multiplicity=3, dimension=10)  # [0.5, 0.8)
    mid_overlap = regime_overlap_length(interval, MID)
    high_overlap = regime_overlap_length(interval, HIGH)
    assert mid_overlap == pytest.approx(2.0 / 3.0 - 0.5)
    assert high_overlap == pytest.approx(0.8 - 2.0 / 3.0)
    assert mid_overlap + high_overlap == pytest.approx(interval.length)
    assert regime_overlap_length(interval, LOW) == pytest.approx(0.0)


def test_regime_overlap_fully_inside_regime():
    interval = spectral_interval(n_before=0, multiplicity=2, dimension=10)  # [0, 0.2)
    assert regime_overlap_length(interval, LOW) == pytest.approx(interval.length)
    assert regime_overlap_length(interval, MID) == pytest.approx(0.0)


def test_regime_mean_weighted_by_exact_overlap():
    # group A entirely inside LOW: [0, 0.2), value 10
    group_a = GroupValue(spectral_interval(0, 2, 10), 10.0)
    # group B straddling LOW/MID: [0.2, 0.5), value 40
    group_b = GroupValue(spectral_interval(2, 3, 10), 40.0)
    result = regime_mean([group_a, group_b], LOW)
    # LOW = [0, 1/3): group_a contributes weight 0.2 (full), group_b contributes weight (1/3 - 0.2)
    weight_a = 0.2
    weight_b = 1.0 / 3.0 - 0.2
    expected = (weight_a * 10.0 + weight_b * 40.0) / (weight_a + weight_b)
    assert result.value == pytest.approx(expected)
    assert result.reason is None
    assert result.evaluable_weight_fraction == pytest.approx((weight_a + weight_b) / (1.0 / 3.0))


def test_regime_mean_excludes_not_available_groups_without_imputation():
    group_available = GroupValue(spectral_interval(0, 2, 10), 5.0)
    group_unavailable = GroupValue(spectral_interval(2, 3, 10), None)
    result = regime_mean([group_available, group_unavailable], LOW)
    assert result.value == pytest.approx(5.0)
    # only group_available's weight (0.2) out of the regime's total weight (1/3) is evaluable
    assert result.evaluable_weight_fraction == pytest.approx(0.2 / (1.0 / 3.0))


def test_regime_mean_no_evaluable_weight_is_not_available():
    group_unavailable = GroupValue(spectral_interval(0, 2, 10), None)
    result = regime_mean([group_unavailable], LOW)
    assert result.value is None
    assert result.reason == NO_EVALUABLE_SPECTRAL_WEIGHT


def test_regime_mean_rejects_unknown_regime():
    group = GroupValue(spectral_interval(0, 2, 10), 1.0)
    with pytest.raises(ValueError):
        regime_mean([group], "VERY_HIGH")


# ---------------------------------------------------------------------------
# Contrasts
# ---------------------------------------------------------------------------


def _mean(value: float) -> RegimeMean:
    return RegimeMean(value, None, 1.0)


def _unavailable_mean() -> RegimeMean:
    return RegimeMean(None, NO_EVALUABLE_SPECTRAL_WEIGHT, 0.0)


def test_delta_hl_basic():
    result = delta_hl(_mean(7.0), _mean(2.0))
    assert result.value == pytest.approx(5.0)
    assert result.reason is None


def test_delta_ml_basic():
    result = delta_ml(_mean(3.0), _mean(2.0))
    assert result.value == pytest.approx(1.0)


def test_delta_hm_basic():
    result = delta_hm(_mean(7.0), _mean(3.0))
    assert result.value == pytest.approx(4.0)


def test_delta_hl_not_available_when_regime_missing():
    result = delta_hl(_unavailable_mean(), _mean(2.0))
    assert result.value is None
    assert result.reason == REGIME_MEAN_NOT_AVAILABLE


# ---------------------------------------------------------------------------
# Profiles: construction, no imputation/matching, exact common partition
# ---------------------------------------------------------------------------


def test_build_profile_drops_not_available_groups_without_matching():
    intervals = build_spectral_partition([2, 3, 5])
    values: list[float | None] = [1.0, None, 3.0]
    pieces = build_profile(intervals, values)
    assert len(pieces) == 2
    assert pieces[0].value == pytest.approx(1.0)
    assert pieces[1].value == pytest.approx(3.0)
    # the dropped middle group leaves a real domain gap -- no interpolation across it
    assert pieces[0].end != pieces[1].start


def test_build_profile_rejects_mismatched_lengths():
    intervals = build_spectral_partition([1, 1])
    with pytest.raises(ValueError):
        build_profile(intervals, [1.0])


def test_common_breakpoints_of_different_partitions():
    pieces_a = [ProfilePiece(0.0, 0.4, 1.0), ProfilePiece(0.4, 1.0, 2.0)]
    pieces_b = [ProfilePiece(0.0, 0.7, 5.0), ProfilePiece(0.7, 1.0, 6.0)]
    assert common_breakpoints(pieces_a, pieces_b) == [0.0, 0.4, 0.7, 1.0]


def test_cross_profile_correlation_rejects_non_covering_profile():
    pieces_a = [ProfilePiece(0.0, 0.5, 1.0)]  # gap on [0.5, 1)
    pieces_b = [ProfilePiece(0.0, 1.0, 1.0)]
    with pytest.raises(ValueError):
        cross_profile_correlation(pieces_a, pieces_b)


# ---------------------------------------------------------------------------
# C_X_23
# ---------------------------------------------------------------------------

_IDENTICAL_A = [ProfilePiece(0.0, 0.5, 1.0), ProfilePiece(0.5, 1.0, 3.0)]
_IDENTICAL_B = [ProfilePiece(0.0, 0.5, 1.0), ProfilePiece(0.5, 1.0, 3.0)]
_AFFINE_INVERSE_B = [ProfilePiece(0.0, 0.5, 3.0), ProfilePiece(0.5, 1.0, 1.0)]
_CONSTANT_A = [ProfilePiece(0.0, 1.0, 5.0)]


def test_cross_profile_correlation_identical_profiles_is_plus_one():
    result = cross_profile_correlation(_IDENTICAL_A, _IDENTICAL_B)
    assert result.value == pytest.approx(1.0)


def test_cross_profile_correlation_affine_inverse_is_minus_one():
    result = cross_profile_correlation(_IDENTICAL_A, _AFFINE_INVERSE_B)
    assert result.value == pytest.approx(-1.0)


def test_cross_profile_correlation_constant_profile_is_not_available():
    result = cross_profile_correlation(_CONSTANT_A, _IDENTICAL_B)
    assert result.value is None
    assert result.reason == CONSTANT_PROFILE


def test_cross_profile_correlation_uses_guard_tolerance_when_supplied():
    # a profile whose variance is nonzero (representable, not swallowed by
    # floating-point rounding) but whose standard deviation sits below a
    # supplied guard must be treated as constant only once that guard is
    # passed -- never by inventing an implicit tolerance.
    tiny = 1e-9
    noisy = [ProfilePiece(0.0, 0.5, 5.0), ProfilePiece(0.5, 1.0, 5.0 + tiny)]
    result_no_guard = cross_profile_correlation(noisy, _IDENTICAL_B)
    assert result_no_guard.reason is None  # exact-zero test: nonzero variance is not exactly 0

    result_with_guard = cross_profile_correlation(noisy, _IDENTICAL_B, zero_variance_tolerance=tiny)
    assert result_with_guard.value is None
    assert result_with_guard.reason == CONSTANT_PROFILE


# ---------------------------------------------------------------------------
# D_X_23
# ---------------------------------------------------------------------------


def test_cross_profile_distance_identical_profiles_is_zero():
    result = cross_profile_distance(_IDENTICAL_A, _IDENTICAL_B)
    assert result.value == pytest.approx(0.0)


def test_cross_profile_distance_zero_denominator_is_not_available():
    constant_b = [ProfilePiece(0.0, 1.0, 9.0)]
    result = cross_profile_distance(_CONSTANT_A, constant_b)
    assert result.value is None
    assert result.reason == ZERO_PROFILE_VARIANCE


def test_cross_profile_distance_no_d_max_field_introduced():
    result = cross_profile_distance(_IDENTICAL_A, _AFFINE_INVERSE_B)
    assert not hasattr(result, "d_max")


# ---------------------------------------------------------------------------
# Inter-S taxonomy
# ---------------------------------------------------------------------------


def _resolved(value: float) -> Available:
    return Available(value, None)


def _not_available() -> Available:
    return Available(None, REGIME_MEAN_NOT_AVAILABLE)


def test_classify_inter_s_not_evaluable_when_either_side_missing():
    result = classify_inter_s(_not_available(), _resolved(1.0), metric="M_TT")
    assert result.taxonomy == NOT_EVALUABLE
    assert result.direction_s2 is None
    assert result.direction_s3 is None


def test_classify_inter_s_no_resolved_contrast_when_either_side_unresolved():
    result = classify_inter_s(_resolved(0.0), _resolved(1.0), metric="M_TT")
    assert result.taxonomy == NO_RESOLVED_SPECTRAL_CONTRAST
    assert result.direction_s2 == NUMERICALLY_UNRESOLVED
    assert result.direction_s3 == POSITIVE


def test_classify_inter_s_opposite_direction():
    result = classify_inter_s(_resolved(1.0), _resolved(-1.0), metric="M_TT")
    assert result.taxonomy == OPPOSITE_INTER_S_DIRECTION
    assert result.direction_s2 == POSITIVE
    assert result.direction_s3 == NEGATIVE


def test_classify_inter_s_same_direction():
    result = classify_inter_s(_resolved(1.0), _resolved(2.0), metric="R_eff")
    assert result.taxonomy == SAME_INTER_S_DIRECTION
    assert result.direction_s2 == POSITIVE
    assert result.direction_s3 == POSITIVE


def test_classify_inter_s_covers_full_taxonomy_space():
    covered = {
        classify_inter_s(_not_available(), _resolved(1.0), metric="M_TT").taxonomy,
        classify_inter_s(_resolved(0.0), _resolved(1.0), metric="M_TT").taxonomy,
        classify_inter_s(_resolved(1.0), _resolved(-1.0), metric="M_TT").taxonomy,
        classify_inter_s(_resolved(1.0), _resolved(2.0), metric="M_TT").taxonomy,
    }
    assert covered == {NOT_EVALUABLE, NO_RESOLVED_SPECTRAL_CONTRAST, OPPOSITE_INTER_S_DIRECTION, SAME_INTER_S_DIRECTION}
