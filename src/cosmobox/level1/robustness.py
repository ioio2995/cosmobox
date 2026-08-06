"""gamma_O and closed-list robustness verdicts. Level1B lot 1B-6
(docs/levels/level1/specification.md sections 9 and 13,
docs/decisions/decisions.md D018).

gamma_O = |O_high - O_low| / max(|O_high|, |O_low|), null with
"normalization_denominator_below_floor" if the denominator is at or below
NORMALIZATION_FLOOR -- the floor decides the normalization is not
physically interpretable, it never substitutes an artificial value.

The binary verdict (robust/non_robust) is a SEPARATE, independently
well-defined computation from gamma_O: it compares the same difference
against max(0.05, 0.15 * amplitude), which stays meaningful even when
amplitude is at or below the floor (the relative term then vanishes and
the absolute 0.05 threshold alone governs) -- gamma_O being null never
forces the verdict to be indeterminate on its own. The verdict becomes
indeterminate only for a reason genuinely distinct from the arithmetic:
the match itself was not exact_label_match, or the matched groups are
partial_subspace (truncated_spectral_group) -- these two indeterminate
reasons are never fused (matching.py's own docstring makes the same
point from the matching side).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .local_observables import NORMALIZATION_FLOOR, NormalizedMoment
from .matching import EXACT_LABEL_MATCH, MatchOutcome
from .restricted import PARTIAL_SUBSPACE

ABSOLUTE_ROBUSTNESS_THRESHOLD = 0.05
RELATIVE_ROBUSTNESS_THRESHOLD = 0.15

ROBUST = "robust"
NON_ROBUST = "non_robust"
INDETERMINATE = "indeterminate"
_VERDICTS = (ROBUST, NON_ROBUST, INDETERMINATE)

TRUNCATED_SPECTRAL_GROUP = "truncated_spectral_group"


def compute_gamma_o(
    value_high: complex, value_low: complex, *, floor: float = NORMALIZATION_FLOOR
) -> NormalizedMoment:
    """gamma_O = |value_high - value_low| / max(|value_high|, |value_low|),
    null with "normalization_denominator_below_floor" if the denominator
    is <= floor. Never computes difference/floor as a substitute value."""
    difference = abs(value_high - value_low)
    amplitude = max(abs(value_high), abs(value_low))
    if amplitude <= floor:
        return NormalizedMoment(value=None, null_reason="normalization_denominator_below_floor")
    return NormalizedMoment(value=difference / amplitude, null_reason=None)


@dataclass(frozen=True, slots=True)
class RobustnessResult:
    verdict: str
    null_reason: str | None
    gamma_o: NormalizedMoment | None
    difference: float | None
    amplitude: float | None

    def __post_init__(self) -> None:
        if self.verdict not in _VERDICTS:
            raise ValueError(f"verdict must be one of {_VERDICTS}, got {self.verdict!r}")
        if self.verdict == INDETERMINATE and self.null_reason is None:
            raise ValueError("an indeterminate verdict must carry a null_reason")
        if self.verdict != INDETERMINATE and self.null_reason is not None:
            raise ValueError(f"null_reason must be None for a definitive verdict, got {self.null_reason!r}")
        if (self.difference is None) != (self.amplitude is None):
            raise ValueError("difference and amplitude must be set together or both None")
        if self.difference is not None:
            if not (math.isfinite(self.difference) and self.difference >= 0):
                raise ValueError(f"difference must be finite and >= 0, got {self.difference}")
            if not (math.isfinite(self.amplitude) and self.amplitude >= 0):
                raise ValueError(f"amplitude must be finite and >= 0, got {self.amplitude}")


def evaluate_robustness(
    match_outcome: MatchOutcome,
    value_high: complex,
    value_low: complex,
    *,
    floor: float = NORMALIZATION_FLOOR,
    absolute_threshold: float = ABSOLUTE_ROBUSTNESS_THRESHOLD,
    relative_threshold: float = RELATIVE_ROBUSTNESS_THRESHOLD,
) -> RobustnessResult:
    """The single entry point tying matching.py's MatchOutcome to a
    robustness verdict for one scalar observable of the closed list
    (gamma_O itself, or G_occ/rho_QQ/C_TT_conn/flavor_singular_value_ratio/
    path_phase_coherence once already computed elsewhere).

    match_outcome.status != exact_label_match: no pair was ever
    identified, so no difference/amplitude/gamma_o is computed at all --
    verdict=indeterminate, null_reason=match_outcome.status.

    match_outcome.matched_group.status == partial_subspace: both values
    ARE available (an exploratory difference/gamma_o is computed and
    reported), but no robust/non_robust verdict is ever produced --
    verdict=indeterminate, null_reason="truncated_spectral_group",
    deliberately distinct from an ambiguous-match null_reason.

    Otherwise: a genuine complete_multiplet-vs-complete_multiplet
    exact_label_match -- difference/amplitude/gamma_o computed, and the
    binary verdict applies max(absolute_threshold, relative_threshold *
    amplitude), frontier inclusive (robust at exact equality).
    """
    if match_outcome.status != EXACT_LABEL_MATCH:
        return RobustnessResult(
            verdict=INDETERMINATE, null_reason=match_outcome.status, gamma_o=None, difference=None, amplitude=None
        )

    difference = abs(value_high - value_low)
    amplitude = max(abs(value_high), abs(value_low))
    gamma_o = compute_gamma_o(value_high, value_low, floor=floor)

    if match_outcome.matched_group.status == PARTIAL_SUBSPACE:
        return RobustnessResult(
            verdict=INDETERMINATE,
            null_reason=TRUNCATED_SPECTRAL_GROUP,
            gamma_o=gamma_o,
            difference=difference,
            amplitude=amplitude,
        )

    threshold = max(absolute_threshold, relative_threshold * amplitude)
    verdict = ROBUST if difference <= threshold else NON_ROBUST
    return RobustnessResult(verdict=verdict, null_reason=None, gamma_o=gamma_o, difference=difference, amplitude=amplitude)
