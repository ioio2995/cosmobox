from __future__ import annotations

import pytest

from experiments.level1.manifest import TargetGroupSpec
from scripts.level1c_baseline_gate.gate import (
    HistoricalGroupProofError,
    _target_could_explain_group,
    historical_group_index_for_required_target,
)

_FUNDAMENTAL = TargetGroupSpec(
    target_id="fundamental", selection_kind="fundamental", target_twice_T=None,
    selection_within_label=None, required_spectral_status="complete_multiplet", requires_inter_s_exact_match=False,
)
_FIRST_EXCITED = TargetGroupSpec(
    target_id="first_excited", selection_kind="first_excited", target_twice_T=None,
    selection_within_label=None, required_spectral_status="complete_multiplet", requires_inter_s_exact_match=True,
)


def _flavor_label(target_id: str, twice_T: int) -> TargetGroupSpec:
    return TargetGroupSpec(
        target_id=target_id, selection_kind="flavor_label", target_twice_T=twice_T,
        selection_within_label="lowest_representative_energy", required_spectral_status="complete_multiplet",
        requires_inter_s_exact_match=False,
    )


_RING5_TARGETS = (_FUNDAMENTAL, _FIRST_EXCITED, _flavor_label("T_max", 5), _flavor_label("T_3_2", 3))


# ---------------------------------------------------------------------------
# fundamental / first_excited: positional, no exclusion needed
# ---------------------------------------------------------------------------


def test_fundamental_is_always_index_0() -> None:
    assert historical_group_index_for_required_target("fundamental", [], _RING5_TARGETS) == 0


def test_first_excited_is_always_index_1() -> None:
    assert historical_group_index_for_required_target("first_excited", [], _RING5_TARGETS) == 1


# ---------------------------------------------------------------------------
# T_3_2 (flavor_label): proof by exclusion, matching the real ring5
# reference archive shape exactly (group 0/1 share twice_T=1, group 2
# has twice_T=3 -- confirmed by direct read of
# /workspaces/level1b_campaign_output/).
# ---------------------------------------------------------------------------


def test_t_3_2_proven_by_exclusion_matches_real_archive_shape() -> None:
    persisted_groups = [(0, 1), (1, 1), (2, 3)]
    assert historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS) == 2


def test_no_candidate_group_fails() -> None:
    persisted_groups = [(0, 1), (1, 1)]  # no group with twice_T == 3 at all
    with pytest.raises(HistoricalGroupProofError, match="no persisted group satisfies"):
        historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS)


def test_more_than_one_candidate_group_fails() -> None:
    """Two distinct, otherwise-unexplained groups both carry twice_T=3 --
    genuinely ambiguous, never resolved by picking either one."""
    persisted_groups = [(0, 1), (1, 1), (2, 3), (4, 3)]
    with pytest.raises(HistoricalGroupProofError, match="more than one persisted group satisfies"):
        historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS)


def test_group_explainable_by_another_target_is_excluded_from_candidacy() -> None:
    """A group at index 0 with twice_T=3 is structurally explained by
    'fundamental' (index==0) just as much as by 'T_3_2' (twice_T==3) --
    this is a genuine collision, so it can never be counted as a proven
    T_3_2 candidate, even though no OTHER group carries twice_T=3."""
    persisted_groups = [(0, 3), (1, 1)]
    with pytest.raises(HistoricalGroupProofError, match="no persisted group satisfies"):
        historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS)


def test_t_max_never_excluded_from_the_closed_set_even_though_never_compared() -> None:
    """T_max (twice_T=5) is never part of the gate's comparison scope,
    but it still participates internally in the exclusion proof as one
    of the possible causes -- if a persisted group had twice_T=5, it
    would correctly be attributed to T_max, never mistaken for T_3_2."""
    persisted_groups = [(0, 1), (1, 1), (2, 5), (3, 3)]
    assert historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS) == 3


def test_unknown_target_id_fails() -> None:
    with pytest.raises(HistoricalGroupProofError, match="no historical manifest target named"):
        historical_group_index_for_required_target("nonexistent", [(0, 1)], _RING5_TARGETS)


# ---------------------------------------------------------------------------
# _target_could_explain_group: the necessary-condition primitive itself
# ---------------------------------------------------------------------------


def test_fundamental_condition_is_purely_positional() -> None:
    assert _target_could_explain_group(_FUNDAMENTAL, 0, twice_T=99) is True
    assert _target_could_explain_group(_FUNDAMENTAL, 1, twice_T=0) is False


def test_first_excited_condition_is_purely_positional() -> None:
    assert _target_could_explain_group(_FIRST_EXCITED, 1, twice_T=99) is True
    assert _target_could_explain_group(_FIRST_EXCITED, 0, twice_T=0) is False


def test_flavor_label_condition_is_twice_t_only_never_positional() -> None:
    t_3_2 = _flavor_label("T_3_2", 3)
    assert _target_could_explain_group(t_3_2, group_index=999, twice_T=3) is True
    assert _target_could_explain_group(t_3_2, group_index=0, twice_T=1) is False


def test_no_unique_twice_t_heuristic_shortcut_exists() -> None:
    """The forbidden heuristic ('the unique persisted group with a
    matching twice_T is the target') would accept this scenario, since
    only one group carries twice_T=3 -- but it is explainable by
    'fundamental' too (index==0), so the rigorous exclusion proof
    correctly refuses it. This is the exact distinction the mandate
    requires never to be blurred."""
    persisted_groups = [(0, 3)]  # unique twice_T=3, but at index 0
    with pytest.raises(HistoricalGroupProofError):
        historical_group_index_for_required_target("T_3_2", persisted_groups, _RING5_TARGETS)
