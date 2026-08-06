"""Target-group selection. Level1B lot 1B-8.

Implements the four ways a manifest TargetGroupSpec.selection_kind picks
a spectral group out of one case's own diagonalization: this is a
preregistered scientific selection rule (per the 1B-8 mission), not an
orchestration convenience.

- fundamental: the lowest-energy group (rank 0). Energy rank is a
  legitimate selection criterion only for this category and
  first_excited below -- it is never used as a substitute for a
  flavor-label match. Never substituted for another group even when the
  fundamental group is partial_subspace.
- first_excited: the next distinct group above the fundamental (rank 1),
  when the window reaches it.
- flavor_label: selects by twice_T, computed via the already-validated
  cosmobox.level1.restricted (canonical_multiplet_expectation /
  exploratory_partial_subspace_mean) and cosmobox.level1.matching
  (compute_twice_T) primitives -- never by rank. A group present but
  partial_subspace is selected as exploratory, never promoted to
  complete. Multiple complete candidates are disambiguated by
  selection_within_label=="lowest_representative_energy" only when the
  manifest explicitly says so; a tie within the case's own degeneracy
  tolerance is reported ambiguous rather than broken by iteration order.
- structurally_not_applicable: declarative, selects nothing.

Translation/reflection labels are never used to choose a group here: the
manifest does not preregister an expected value for either, so per the
1B-8 mission they remain confirmation/matching-only (cosmobox.level1.
matching), computed downstream of selection, not by this module.

This module performs no diagonalization and no window construction: the
caller supplies the case's own SpectralLevelGroup/SpectralGroupState
sequences (already built from an executed Level0Report), extracted once
and shared across every target for that case.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import scipy.sparse as sp

from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level1.matching import FLAVOR_LABEL_TOLERANCE, compute_twice_T
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    SpectralGroupState,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
)

from .manifest import FIRST_EXCITED, FLAVOR_LABEL, FUNDAMENTAL, LOWEST_REPRESENTATIVE_ENERGY, TargetGroupSpec
from .manifest import STRUCTURALLY_NOT_APPLICABLE as _STRUCTURALLY_NOT_APPLICABLE_SELECTION_KIND

SELECTED = "selected"
AMBIGUOUS = "ambiguous"
NOT_IN_WINDOW = "not_in_window"
STRUCTURALLY_NOT_APPLICABLE = "structurally_not_applicable"
_SELECTION_STATUSES = (SELECTED, AMBIGUOUS, NOT_IN_WINDOW, STRUCTURALLY_NOT_APPLICABLE)


@dataclass(frozen=True, slots=True)
class TargetSelectionOutcome:
    """target_id mirrors the manifest's own TargetGroupSpec.target_id.
    group_index is set if and only if status == "selected", and indexes
    into the same `groups`/`group_states` sequences the caller passed to
    select_target_group. twice_T records the label actually computed for
    the selected/matched candidates when selection_kind == flavor_label
    (None otherwise) -- a transcription of what was found, not a second
    definition of compute_twice_T."""

    target_id: str
    status: str
    group_index: int | None
    twice_T: int | None

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id must be non-empty")
        if self.status not in _SELECTION_STATUSES:
            raise ValueError(f"status must be one of {_SELECTION_STATUSES}, got {self.status!r}")
        if (self.status == SELECTED) != (self.group_index is not None):
            raise ValueError("group_index must be set if and only if status == 'selected'")
        if self.group_index is not None and self.group_index < 0:
            raise ValueError(f"group_index must be >= 0, got {self.group_index}")
        if self.twice_T is not None and (isinstance(self.twice_T, bool) or self.twice_T < 0):
            raise ValueError(f"twice_T must be None or a non-negative int, got {self.twice_T!r}")


def _validate_matching_sequences(
    groups: Sequence[SpectralLevelGroup], group_states: Sequence[SpectralGroupState]
) -> None:
    if len(groups) == 0:
        raise ValueError("groups must not be empty")
    if len(groups) != len(group_states):
        raise ValueError(
            f"groups and group_states must have the same length, got {len(groups)} and {len(group_states)}"
        )


def _select_fundamental(target: TargetGroupSpec) -> TargetSelectionOutcome:
    return TargetSelectionOutcome(target_id=target.target_id, status=SELECTED, group_index=0, twice_T=None)


def _select_first_excited(
    target: TargetGroupSpec, groups: Sequence[SpectralLevelGroup]
) -> TargetSelectionOutcome:
    if len(groups) < 2:
        return TargetSelectionOutcome(target_id=target.target_id, status=NOT_IN_WINDOW, group_index=None, twice_T=None)
    return TargetSelectionOutcome(target_id=target.target_id, status=SELECTED, group_index=1, twice_T=None)


def _group_twice_T(
    flavor_casimir: sp.spmatrix, group_state: SpectralGroupState, *, flavor_label_tolerance: float
) -> int | None:
    if group_state.status == COMPLETE_MULTIPLET:
        casimir_expectation = canonical_multiplet_expectation(flavor_casimir, group_state, hermitian=True)
    else:
        casimir_expectation = exploratory_partial_subspace_mean(flavor_casimir, group_state, hermitian=True)
    return compute_twice_T(casimir_expectation, tolerance=flavor_label_tolerance)


def _select_flavor_label(
    target: TargetGroupSpec,
    groups: Sequence[SpectralLevelGroup],
    group_states: Sequence[SpectralGroupState],
    flavor_casimir: sp.spmatrix,
    *,
    degeneracy_tolerance: float,
    flavor_label_tolerance: float,
) -> TargetSelectionOutcome:
    complete_matches: list[int] = []
    partial_matches: list[int] = []
    for index, group_state in enumerate(group_states):
        twice_T = _group_twice_T(flavor_casimir, group_state, flavor_label_tolerance=flavor_label_tolerance)
        if twice_T != target.target_twice_T:
            continue
        if group_state.status == COMPLETE_MULTIPLET:
            complete_matches.append(index)
        else:
            partial_matches.append(index)

    if not complete_matches and not partial_matches:
        return TargetSelectionOutcome(
            target_id=target.target_id, status=NOT_IN_WINDOW, group_index=None, twice_T=target.target_twice_T
        )

    if complete_matches:
        if len(complete_matches) == 1:
            chosen = complete_matches[0]
        elif target.selection_within_label != LOWEST_REPRESENTATIVE_ENERGY:
            return TargetSelectionOutcome(
                target_id=target.target_id, status=AMBIGUOUS, group_index=None, twice_T=target.target_twice_T
            )
        else:
            energies = sorted((groups[index].representative_energy, index) for index in complete_matches)
            lowest_energy = energies[0][0]
            tied = [index for energy, index in energies if energy - lowest_energy <= degeneracy_tolerance]
            if len(tied) > 1:
                return TargetSelectionOutcome(
                    target_id=target.target_id, status=AMBIGUOUS, group_index=None, twice_T=target.target_twice_T
                )
            chosen = energies[0][1]
        return TargetSelectionOutcome(
            target_id=target.target_id, status=SELECTED, group_index=chosen, twice_T=target.target_twice_T
        )

    # Only partial (truncated-window) candidates share this label. A
    # complete SpectralLevelGroup's own contract (docs: lower_bound_only
    # is True for at most the trailing group) makes more than one partial
    # match structurally impossible in practice; the ambiguous fallback
    # below is defense in depth, not a reachable production path.
    if len(partial_matches) == 1:
        chosen = partial_matches[0]
    else:
        return TargetSelectionOutcome(
            target_id=target.target_id, status=AMBIGUOUS, group_index=None, twice_T=target.target_twice_T
        )
    return TargetSelectionOutcome(
        target_id=target.target_id, status=SELECTED, group_index=chosen, twice_T=target.target_twice_T
    )


def select_target_group(
    target: TargetGroupSpec,
    groups: Sequence[SpectralLevelGroup],
    group_states: Sequence[SpectralGroupState],
    *,
    flavor_casimir: sp.spmatrix | None = None,
    degeneracy_tolerance: float,
    flavor_label_tolerance: float = FLAVOR_LABEL_TOLERANCE,
) -> TargetSelectionOutcome:
    """Select the single spectral group matching `target` out of one
    case's own `groups` (from cosmobox.level0.degeneracy.DegeneracyReport.
    groups) and `group_states` (the corresponding
    cosmobox.level1.restricted.SpectralGroupState for each, same order,
    same length -- built once by the caller via extract_group_state and
    shared across every target of this case).

    `flavor_casimir` is required when target.selection_kind ==
    "flavor_label" (built once per case by the caller, via
    cosmobox.level0.symmetries.build_flavor_casimir) and ignored
    otherwise.
    """
    _validate_matching_sequences(groups, group_states)

    if target.selection_kind == _STRUCTURALLY_NOT_APPLICABLE_SELECTION_KIND:
        return TargetSelectionOutcome(
            target_id=target.target_id, status=STRUCTURALLY_NOT_APPLICABLE, group_index=None, twice_T=None
        )
    if target.selection_kind == FUNDAMENTAL:
        return _select_fundamental(target)
    if target.selection_kind == FIRST_EXCITED:
        return _select_first_excited(target, groups)
    if target.selection_kind == FLAVOR_LABEL:
        if flavor_casimir is None:
            raise ValueError("flavor_casimir is required when target.selection_kind == 'flavor_label'")
        if isinstance(degeneracy_tolerance, bool) or degeneracy_tolerance <= 0:
            raise ValueError(f"degeneracy_tolerance must be a positive number, got {degeneracy_tolerance!r}")
        return _select_flavor_label(
            target,
            groups,
            group_states,
            flavor_casimir,
            degeneracy_tolerance=degeneracy_tolerance,
            flavor_label_tolerance=flavor_label_tolerance,
        )
    raise ValueError(f"unknown selection_kind {target.selection_kind!r}")
