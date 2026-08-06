from __future__ import annotations

import pytest

from cosmobox.level1.local_observables import NORMALIZATION_FLOOR
from cosmobox.level1.matching import (
    AMBIGUOUS_CROSS_TRUNCATION_MATCH,
    EXACT_LABEL_MATCH,
    NUMERIC,
    STRUCTURALLY_NOT_APPLICABLE,
    TARGET_GROUP_NOT_IN_WINDOW,
    MatchOutcome,
    SpectralGroupMatchKey,
    SymmetryLabel,
    match_spectral_group,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from cosmobox.level1.robustness import (
    ABSOLUTE_ROBUSTNESS_THRESHOLD,
    INDETERMINATE,
    NON_ROBUST,
    RELATIVE_ROBUSTNESS_THRESHOLD,
    ROBUST,
    TRUNCATED_SPECTRAL_GROUP,
    RobustnessResult,
    compute_gamma_o,
    evaluate_robustness,
)


def _key(**overrides) -> SpectralGroupMatchKey:
    defaults = dict(
        geometry="triangle",
        hamiltonian_identity_without_spin="ref_j1",
        sector_identity="default",
        status=COMPLETE_MULTIPLET,
        multiplicity=2,
        twice_T=1,
        translation_label=SymmetryLabel(kind=NUMERIC, value=1 + 0j),
        reflection_label=SymmetryLabel(kind=NUMERIC, value=1 + 0j),
    )
    defaults.update(overrides)
    return SpectralGroupMatchKey(**defaults)


def _exact_match(**key_overrides) -> MatchOutcome:
    return MatchOutcome(EXACT_LABEL_MATCH, _key(**key_overrides))


# ---------------------------------------------------------------------------
# compute_gamma_o
# ---------------------------------------------------------------------------


def test_compute_gamma_o_real_hand_verified() -> None:
    moment = compute_gamma_o(3.0, 2.0)
    assert moment.null_reason is None
    assert moment.value == pytest.approx(1.0 / 3.0)


def test_compute_gamma_o_complex_hand_verified() -> None:
    moment = compute_gamma_o(1 + 1j, 1 + 0j)
    difference = abs((1 + 1j) - (1 + 0j))
    amplitude = max(abs(1 + 1j), abs(1 + 0j))
    assert moment.value == pytest.approx(difference / amplitude)


def test_compute_gamma_o_null_below_floor() -> None:
    moment = compute_gamma_o(1e-13, 5e-14, floor=NORMALIZATION_FLOOR)
    assert moment.value is None
    assert moment.null_reason == "normalization_denominator_below_floor"


def test_compute_gamma_o_never_computes_artificial_ratio_below_floor() -> None:
    # Deliberately construct values whose "naive" difference/floor ratio
    # would be enormous, to prove no artificial value is ever substituted.
    moment = compute_gamma_o(1e-13, -1e-13, floor=NORMALIZATION_FLOOR)
    assert moment.value is None


def test_compute_gamma_o_invariant_under_common_positive_rescaling() -> None:
    scale = 7.3
    base = compute_gamma_o(3.0, 2.0)
    scaled = compute_gamma_o(3.0 * scale, 2.0 * scale)
    assert scaled.value == pytest.approx(base.value)


def test_compute_gamma_o_bounded_by_two_away_from_floor() -> None:
    moment = compute_gamma_o(1000.0, -1000.0)  # maximally divergent, still well above floor
    assert moment.value <= 2.0 + 1e-12


# ---------------------------------------------------------------------------
# evaluate_robustness -- thresholds
# ---------------------------------------------------------------------------


def test_evaluate_robustness_absolute_threshold_dominates_and_is_robust() -> None:
    # amplitude small enough that 0.15*amplitude < 0.05: absolute threshold governs.
    high, low = 0.05, 0.05 + 0.04j
    amplitude = max(abs(high), abs(low))
    assert RELATIVE_ROBUSTNESS_THRESHOLD * amplitude < ABSOLUTE_ROBUSTNESS_THRESHOLD
    result = evaluate_robustness(_exact_match(), high, low)
    assert result.verdict == ROBUST
    assert result.null_reason is None


def test_evaluate_robustness_absolute_threshold_dominates_and_is_non_robust() -> None:
    high, low = 0.05, 0.05 + 0.06j
    amplitude = max(abs(high), abs(low))
    assert RELATIVE_ROBUSTNESS_THRESHOLD * amplitude < ABSOLUTE_ROBUSTNESS_THRESHOLD
    result = evaluate_robustness(_exact_match(), high, low)
    assert result.verdict == NON_ROBUST


def test_evaluate_robustness_relative_threshold_dominates_and_is_robust() -> None:
    # amplitude large enough that 0.15*amplitude > 0.05: relative threshold governs.
    high, low = 10.0, 8.6  # difference=1.4, amplitude=10, 0.15*10=1.5 > 0.05
    result = evaluate_robustness(_exact_match(), high, low)
    assert result.verdict == ROBUST


def test_evaluate_robustness_relative_threshold_dominates_and_is_non_robust() -> None:
    high, low = 10.0, 8.0  # difference=2.0, threshold=1.5
    result = evaluate_robustness(_exact_match(), high, low)
    assert result.verdict == NON_ROBUST


def test_evaluate_robustness_exact_boundary_is_robust() -> None:
    amplitude = 10.0
    threshold = max(ABSOLUTE_ROBUSTNESS_THRESHOLD, RELATIVE_ROBUSTNESS_THRESHOLD * amplitude)
    high = amplitude
    low = amplitude - threshold
    result = evaluate_robustness(_exact_match(), high, low)
    assert result.difference == pytest.approx(threshold)
    assert result.verdict == ROBUST


def test_evaluate_robustness_verdict_survives_gamma_o_being_null() -> None:
    # amplitude below floor: gamma_o is null, but the verdict rule (absolute
    # threshold 0.05 alone, since 0.15*amplitude is negligible) still applies.
    tiny = 1e-13
    result = evaluate_robustness(_exact_match(), tiny, -tiny)
    assert result.gamma_o.value is None
    assert result.gamma_o.null_reason == "normalization_denominator_below_floor"
    assert result.verdict in (ROBUST, NON_ROBUST)
    assert result.null_reason is None


# ---------------------------------------------------------------------------
# evaluate_robustness -- match outcome gating
# ---------------------------------------------------------------------------


def test_evaluate_robustness_ambiguous_match_is_indeterminate_with_no_pair() -> None:
    result = evaluate_robustness(MatchOutcome(AMBIGUOUS_CROSS_TRUNCATION_MATCH, None), 1.0, 1.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == AMBIGUOUS_CROSS_TRUNCATION_MATCH
    assert result.gamma_o is None
    assert result.difference is None
    assert result.amplitude is None


def test_evaluate_robustness_target_not_in_window_is_indeterminate() -> None:
    result = evaluate_robustness(MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, None), 1.0, 1.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == TARGET_GROUP_NOT_IN_WINDOW


def test_evaluate_robustness_structurally_not_applicable_is_indeterminate() -> None:
    result = evaluate_robustness(MatchOutcome(STRUCTURALLY_NOT_APPLICABLE, None), 1.0, 1.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == STRUCTURALLY_NOT_APPLICABLE


def test_evaluate_robustness_partial_subspace_match_is_indeterminate_but_exploratory_values_reported() -> None:
    outcome = _exact_match(status=PARTIAL_SUBSPACE)
    result = evaluate_robustness(outcome, 3.0, 2.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == TRUNCATED_SPECTRAL_GROUP
    # Exploratory values ARE computed and reported, unlike the ambiguous-match case.
    assert result.difference == pytest.approx(1.0)
    assert result.amplitude == pytest.approx(3.0)
    assert result.gamma_o.value == pytest.approx(1.0 / 3.0)


def test_evaluate_robustness_truncated_and_ambiguous_reasons_are_never_conflated() -> None:
    ambiguous = evaluate_robustness(MatchOutcome(AMBIGUOUS_CROSS_TRUNCATION_MATCH, None), 1.0, 1.0)
    truncated = evaluate_robustness(_exact_match(status=PARTIAL_SUBSPACE), 3.0, 2.0)
    assert ambiguous.null_reason != truncated.null_reason
    assert {ambiguous.null_reason, truncated.null_reason} == {
        AMBIGUOUS_CROSS_TRUNCATION_MATCH,
        TRUNCATED_SPECTRAL_GROUP,
    }


# ---------------------------------------------------------------------------
# RobustnessResult.__post_init__
# ---------------------------------------------------------------------------


def test_robustness_result_rejects_indeterminate_without_null_reason() -> None:
    with pytest.raises(ValueError, match="null_reason"):
        RobustnessResult(verdict=INDETERMINATE, null_reason=None, gamma_o=None, difference=None, amplitude=None)


def test_robustness_result_rejects_definitive_verdict_with_null_reason() -> None:
    with pytest.raises(ValueError, match="null_reason"):
        RobustnessResult(verdict=ROBUST, null_reason="oops", gamma_o=None, difference=0.0, amplitude=1.0)


def test_robustness_result_rejects_difference_without_amplitude() -> None:
    with pytest.raises(ValueError, match="together"):
        RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=None, difference=0.0, amplitude=None)


def test_robustness_result_rejects_negative_difference() -> None:
    with pytest.raises(ValueError, match="difference"):
        RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=None, difference=-1.0, amplitude=1.0)


def test_robustness_result_rejects_invalid_verdict() -> None:
    with pytest.raises(ValueError, match="verdict"):
        RobustnessResult(verdict="maybe", null_reason=None, gamma_o=None, difference=None, amplitude=None)


# ---------------------------------------------------------------------------
# End-to-end with the real match_spectral_group pipeline: partial_subspace
# can no longer reach exact_label_match, so evaluate_robustness never
# produces a robust/non_robust verdict for these cases either.
# ---------------------------------------------------------------------------


def test_partial_vs_partial_identical_labels_gives_no_robust_verdict() -> None:
    target = _key(status=PARTIAL_SUBSPACE)
    candidate = _key(status=PARTIAL_SUBSPACE)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH

    result = evaluate_robustness(outcome, 3.0, 2.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == AMBIGUOUS_CROSS_TRUNCATION_MATCH
    assert result.gamma_o is None
    assert result.difference is None
    assert result.amplitude is None


def test_complete_target_partial_candidate_gives_no_robust_verdict() -> None:
    target = _key(status=COMPLETE_MULTIPLET)
    candidate = _key(status=PARTIAL_SUBSPACE)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status != EXACT_LABEL_MATCH

    result = evaluate_robustness(outcome, 3.0, 2.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == outcome.status


def test_partial_target_complete_candidate_gives_no_robust_verdict() -> None:
    target = _key(status=PARTIAL_SUBSPACE)
    candidate = _key(status=COMPLETE_MULTIPLET)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status != EXACT_LABEL_MATCH

    result = evaluate_robustness(outcome, 3.0, 2.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == outcome.status


def test_evaluate_robustness_still_downgrades_a_manually_constructed_partial_match_outcome() -> None:
    # Defense in depth: even though match_spectral_group can no longer
    # produce this, a manually constructed MatchOutcome carrying a
    # partial_subspace matched_group must still be downgraded, never
    # promoted to a robust/non_robust verdict.
    outcome = MatchOutcome(EXACT_LABEL_MATCH, _key(status=PARTIAL_SUBSPACE))
    result = evaluate_robustness(outcome, 3.0, 2.0)
    assert result.verdict == INDETERMINATE
    assert result.null_reason == TRUNCATED_SPECTRAL_GROUP
    assert result.gamma_o.value == pytest.approx(1.0 / 3.0)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", [complex(float("nan"), 0.0), complex(0.0, float("nan")), complex(float("inf"), 0.0)])
def test_compute_gamma_o_rejects_non_finite_value_high(bad_value: complex) -> None:
    with pytest.raises(ValueError, match="value_high"):
        compute_gamma_o(bad_value, 1.0)


@pytest.mark.parametrize("bad_value", [complex(float("nan"), 0.0), complex(0.0, float("nan")), complex(float("inf"), 0.0)])
def test_compute_gamma_o_rejects_non_finite_value_low(bad_value: complex) -> None:
    with pytest.raises(ValueError, match="value_low"):
        compute_gamma_o(1.0, bad_value)


@pytest.mark.parametrize("bad_floor", [float("nan"), float("inf"), 0.0, -1e-12])
def test_compute_gamma_o_rejects_invalid_floor(bad_floor: float) -> None:
    with pytest.raises(ValueError, match="floor"):
        compute_gamma_o(1.0, 2.0, floor=bad_floor)


def test_evaluate_robustness_rejects_non_finite_value_high() -> None:
    with pytest.raises(ValueError, match="value_high"):
        evaluate_robustness(_exact_match(), float("nan"), 1.0)


def test_evaluate_robustness_rejects_non_finite_value_low() -> None:
    with pytest.raises(ValueError, match="value_low"):
        evaluate_robustness(_exact_match(), 1.0, complex(float("inf"), 0.0))


@pytest.mark.parametrize("bad_floor", [float("nan"), float("inf"), 0.0, -1.0])
def test_evaluate_robustness_rejects_invalid_floor(bad_floor: float) -> None:
    with pytest.raises(ValueError, match="floor"):
        evaluate_robustness(_exact_match(), 1.0, 2.0, floor=bad_floor)


@pytest.mark.parametrize("bad_threshold", [float("nan"), float("-inf"), -0.01])
def test_evaluate_robustness_rejects_invalid_absolute_threshold(bad_threshold: float) -> None:
    with pytest.raises(ValueError, match="absolute_threshold"):
        evaluate_robustness(_exact_match(), 1.0, 2.0, absolute_threshold=bad_threshold)


@pytest.mark.parametrize("bad_threshold", [float("nan"), float("-inf"), -0.01])
def test_evaluate_robustness_rejects_invalid_relative_threshold(bad_threshold: float) -> None:
    with pytest.raises(ValueError, match="relative_threshold"):
        evaluate_robustness(_exact_match(), 1.0, 2.0, relative_threshold=bad_threshold)
