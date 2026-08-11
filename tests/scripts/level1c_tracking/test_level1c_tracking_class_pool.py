from __future__ import annotations

from cosmobox.level1.matching import SymmetryLabel

from level1c_tracking_helpers import _group_documents, make_group_structural_data

from scripts.level1c_tracking.tracking import build_class_pool, extract_complete_groups


def test_extract_complete_groups_excludes_partial_subspace() -> None:
    data0 = make_group_structural_data(0, twice_T=1)
    data1 = make_group_structural_data(1, twice_T=2)
    records = _group_documents(
        geometry="triangle", spin=2, repository_commit="0" * 40, manifest_fingerprint="fp", campaign_id="level1c-j0-response-v1",
        group_index=0, data=data0,
    ) + _group_documents(
        geometry="triangle", spin=2, repository_commit="0" * 40, manifest_fingerprint="fp", campaign_id="level1c-j0-response-v1",
        group_index=1, data=data1, status="partial_subspace",
    )
    groups = extract_complete_groups(records)
    assert [group.spectral_window_group_index for group in groups] == [0]


def test_extract_complete_groups_deterministic_ascending_order() -> None:
    records = []
    for index in (3, 1, 2):
        data = make_group_structural_data(index, twice_T=index)
        records.extend(
            _group_documents(
                geometry="ring5", spin=3, repository_commit="0" * 40, manifest_fingerprint="fp", campaign_id="level1c-j0-response-v1",
                group_index=index, data=data,
            )
        )
    groups = extract_complete_groups(records)
    assert [group.spectral_window_group_index for group in groups] == [1, 2, 3]


NUMERIC_LABEL = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))
OTHER_NUMERIC_LABEL = SymmetryLabel(kind="numeric", value=complex(2.0, 0.0))
NOT_APPLICABLE_LABEL = SymmetryLabel(kind="not_applicable", value=None)
UNAVAILABLE_LABEL = SymmetryLabel(kind="unavailable", value=None)


def test_build_class_pool_unique_match() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    candidate = make_group_structural_data(5, twice_T=1, reflection=NUMERIC_LABEL)
    other = make_group_structural_data(6, twice_T=2, reflection=NUMERIC_LABEL)
    result = build_class_pool(baseline, (candidate, other))
    assert result.pool == (candidate,)
    assert result.unresolved_candidates == ()


def test_build_class_pool_wrong_twice_t_excluded() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    wrong = make_group_structural_data(5, twice_T=3, reflection=NUMERIC_LABEL)
    result = build_class_pool(baseline, (wrong,))
    assert result.pool == ()
    assert result.unresolved_candidates == ()


def test_build_class_pool_wrong_reflection_excluded() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    wrong = make_group_structural_data(5, twice_T=1, reflection=OTHER_NUMERIC_LABEL)
    result = build_class_pool(baseline, (wrong,))
    assert result.pool == ()
    assert result.unresolved_candidates == ()


def test_build_class_pool_translation_mismatch_never_excludes() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL, translation=NUMERIC_LABEL)
    candidate = make_group_structural_data(5, twice_T=1, reflection=NUMERIC_LABEL, translation=NOT_APPLICABLE_LABEL)
    result = build_class_pool(baseline, (candidate,))
    assert result.pool == (candidate,)


def test_build_class_pool_energy_and_index_never_discriminate() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL, representative_energy=-100.0)
    candidate = make_group_structural_data(999, twice_T=1, reflection=NUMERIC_LABEL, representative_energy=1e6)
    result = build_class_pool(baseline, (candidate,))
    assert result.pool == (candidate,)


def test_build_class_pool_multiple_candidates() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    candidate_a = make_group_structural_data(5, twice_T=1, reflection=NUMERIC_LABEL)
    candidate_b = make_group_structural_data(6, twice_T=1, reflection=NUMERIC_LABEL)
    result = build_class_pool(baseline, (candidate_a, candidate_b))
    assert result.pool == (candidate_a, candidate_b)


def test_build_class_pool_clean_empty() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    result = build_class_pool(baseline, ())
    assert result.pool == ()
    assert result.unresolved_candidates == ()


def test_build_class_pool_candidate_twice_t_unresolved_is_unresolved_not_excluded() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    candidate = make_group_structural_data(5, twice_T=None, reflection=NUMERIC_LABEL)
    result = build_class_pool(baseline, (candidate,))
    assert result.pool == ()
    assert result.unresolved_candidates == (candidate,)


def test_build_class_pool_candidate_reflection_unresolved_is_unresolved_not_excluded() -> None:
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    candidate = make_group_structural_data(5, twice_T=1, reflection=UNAVAILABLE_LABEL)
    result = build_class_pool(baseline, (candidate,))
    assert result.pool == ()
    assert result.unresolved_candidates == (candidate,)


def test_build_class_pool_twice_t_mismatch_takes_priority_over_reflection_unresolved() -> None:
    """A candidate whose twice_T is definitively resolved and different
    from the baseline's is excluded outright, regardless of its own
    reflection resolution -- twice_T alone already proves it cannot
    match (section 8 only protects components that remain genuinely
    undetermined)."""
    baseline = make_group_structural_data(0, twice_T=1, reflection=NUMERIC_LABEL)
    candidate = make_group_structural_data(5, twice_T=3, reflection=UNAVAILABLE_LABEL)
    result = build_class_pool(baseline, (candidate,))
    assert result.pool == ()
    assert result.unresolved_candidates == ()
