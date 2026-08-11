"""T_3_2_HISTORICAL_MAPPING_PROOF (1C-8d, mandate section requested
explicitly by ChatGPT's audit). Read-only against the real, already-
accepted Level1B historical archive -- no diagonalization, no
heuristic 'unique twice_T means target' shortcut anywhere in this
file or in the code it exercises.
"""

from __future__ import annotations

from scripts.level1c_baseline_gate.gate import (
    _target_could_explain_group,
    historical_group_index_for_required_target,
)


def _persisted_groups_for_case(historical_index, case_id: str) -> list[tuple[int, int | None]]:
    return sorted(
        (group.spectral_window_group_index, group.spectral_group_identity.twice_T)
        for group in historical_index.groups
        if group.case_id == case_id
    )


def test_t_3_2_historical_mapping_proof_ring5_s2(historical_index, historical_manifest, historical_case_ids) -> None:
    case_id = historical_case_ids[("ring5", 2)]
    persisted_groups = _persisted_groups_for_case(historical_index, case_id)
    targets = historical_manifest.target_groups["ring5"]

    # Exclusion trace, reported explicitly (T_3_2_HISTORICAL_MAPPING_PROOF).
    trace = {
        group_index: [target.target_id for target in targets if _target_could_explain_group(target, group_index, twice_T)]
        for group_index, twice_T in persisted_groups
    }
    print("ring5 S2 persisted groups:", persisted_groups)
    print("ring5 S2 exclusion trace:", trace)

    assert persisted_groups == [(0, 1), (1, 1), (2, 3)]
    assert trace[0] == ["fundamental"]
    assert trace[1] == ["first_excited"]
    assert trace[2] == ["T_3_2"]

    proven_index = historical_group_index_for_required_target("T_3_2", persisted_groups, targets)
    assert proven_index == 2


def test_t_3_2_historical_mapping_proof_ring5_s3(historical_index, historical_manifest, historical_case_ids) -> None:
    case_id = historical_case_ids[("ring5", 3)]
    persisted_groups = _persisted_groups_for_case(historical_index, case_id)
    targets = historical_manifest.target_groups["ring5"]

    trace = {
        group_index: [target.target_id for target in targets if _target_could_explain_group(target, group_index, twice_T)]
        for group_index, twice_T in persisted_groups
    }
    print("ring5 S3 persisted groups:", persisted_groups)
    print("ring5 S3 exclusion trace:", trace)

    assert persisted_groups == [(0, 1), (1, 1), (2, 3)]
    assert trace[0] == ["fundamental"]
    assert trace[1] == ["first_excited"]
    assert trace[2] == ["T_3_2"]

    proven_index = historical_group_index_for_required_target("T_3_2", persisted_groups, targets)
    assert proven_index == 2


def test_fundamental_first_excited_positional_proof_triangle(historical_index, historical_manifest, historical_case_ids) -> None:
    for spin in (2, 3):
        case_id = historical_case_ids[("triangle", spin)]
        persisted_groups = _persisted_groups_for_case(historical_index, case_id)
        targets = historical_manifest.target_groups["triangle"]
        assert historical_group_index_for_required_target("fundamental", persisted_groups, targets) == 0
        assert historical_group_index_for_required_target("first_excited", persisted_groups, targets) == 1
