from __future__ import annotations

import pytest

from cosmobox.level0.degeneracy import (
    DEFAULT_DEGENERACY_TOLERANCE,
    DegeneracyReport,
    SpectralLevelGroup,
    analyze_spectral_degeneracies,
)

# ---------------------------------------------------------------------------
# Basic grouping behavior
# ---------------------------------------------------------------------------


def test_all_distinct_eigenvalues_produce_singleton_groups() -> None:
    report = analyze_spectral_degeneracies([0.0, 1.0, 2.0, 3.0], dimension=4)
    assert len(report.groups) == 4
    assert all(group.multiplicity_observed == 1 for group in report.groups)
    assert report.ground_multiplicity_observed == 1
    assert report.first_distinct_energy == pytest.approx(1.0)
    assert report.first_distinct_gap == pytest.approx(1.0)


def test_exact_duplicates_form_one_group() -> None:
    report = analyze_spectral_degeneracies([0.0, 0.0, 0.0, 5.0], dimension=4)
    assert len(report.groups) == 2
    ground, excited = report.groups
    assert ground.start_index == 0
    assert ground.end_index_exclusive == 3
    assert ground.multiplicity_observed == 3
    assert ground.representative_energy == pytest.approx(0.0)
    assert ground.min_energy == pytest.approx(0.0)
    assert ground.max_energy == pytest.approx(0.0)
    assert excited.multiplicity_observed == 1
    assert report.ground_multiplicity_observed == 3
    assert report.first_distinct_gap == pytest.approx(5.0)


def test_near_degenerate_values_within_tolerance_are_grouped() -> None:
    tolerance = 1e-8
    report = analyze_spectral_degeneracies([1.0, 1.0 + 1e-9, 1.0 + 2e-9, 10.0], dimension=4, tolerance=tolerance)
    assert len(report.groups) == 2
    assert report.groups[0].multiplicity_observed == 3


def test_values_just_outside_tolerance_are_split() -> None:
    tolerance = 1e-10
    report = analyze_spectral_degeneracies([1.0, 1.0 + 1e-6, 10.0], dimension=3, tolerance=tolerance)
    assert len(report.groups) == 3
    assert report.first_distinct_gap > tolerance * max(1.0, 1.0)


def test_grouping_is_chained_not_anchored_to_first_element() -> None:
    # 0.0 -> 0.0 + tol/2 -> 0.0 + tol: each adjacent pair is within tolerance
    # of its neighbor, even though the first and last are not directly
    # within tolerance of each other. Chained grouping still merges them.
    tolerance = 1e-6
    step = tolerance / 2
    values = [0.0, step, 2 * step]
    report = analyze_spectral_degeneracies(values, dimension=3, tolerance=tolerance)
    assert len(report.groups) == 1
    assert report.groups[0].multiplicity_observed == 3


# ---------------------------------------------------------------------------
# lower_bound_only / window_truncated
# ---------------------------------------------------------------------------


def test_lower_bound_only_true_when_window_ends_inside_last_group() -> None:
    # Only 3 of a 100-dimensional space's eigenvalues were computed, and the
    # top group ends exactly at the window boundary -- its true multiplicity
    # could be larger than observed.
    report = analyze_spectral_degeneracies([0.0, 5.0, 5.0], dimension=100)
    assert report.window_truncated is True
    assert report.groups[-1].lower_bound_only is True
    assert report.groups[0].lower_bound_only is False


def test_lower_bound_only_false_when_full_space_was_diagonalized() -> None:
    report = analyze_spectral_degeneracies([0.0, 5.0, 5.0], dimension=3)
    assert report.window_truncated is False
    assert all(not group.lower_bound_only for group in report.groups)


def test_lower_bound_only_false_for_non_last_group_even_when_truncated() -> None:
    report = analyze_spectral_degeneracies([0.0, 0.0, 5.0], dimension=50)
    assert report.window_truncated is True
    assert report.groups[0].lower_bound_only is False
    assert report.groups[-1].lower_bound_only is True


# ---------------------------------------------------------------------------
# Single eigenvalue
# ---------------------------------------------------------------------------


def test_single_eigenvalue_produces_one_group_and_no_distinct_gap() -> None:
    report = analyze_spectral_degeneracies([3.5], dimension=10)
    assert len(report.groups) == 1
    assert report.ground_multiplicity_observed == 1
    assert report.first_distinct_energy is None
    assert report.first_distinct_gap is None
    assert report.groups[0].lower_bound_only is True


# ---------------------------------------------------------------------------
# Default tolerance
# ---------------------------------------------------------------------------


def test_default_tolerance_is_1e_minus_10() -> None:
    assert DEFAULT_DEGENERACY_TOLERANCE == 1e-10
    report = analyze_spectral_degeneracies([1.0, 2.0], dimension=2)
    assert report.tolerance == 1e-10


# ---------------------------------------------------------------------------
# analyze_spectral_degeneracies input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_tolerance", [0.0, -1e-10, float("inf"), float("nan"), True])
def test_rejects_bad_tolerance(bad_tolerance: float) -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([1.0], dimension=1, tolerance=bad_tolerance)


def test_rejects_non_positive_dimension() -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([1.0], dimension=0)


def test_rejects_empty_eigenvalues() -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([], dimension=5)


def test_rejects_more_eigenvalues_than_dimension() -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([1.0, 2.0, 3.0], dimension=2)


def test_rejects_non_finite_eigenvalue() -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([1.0, float("nan")], dimension=2)


def test_rejects_unsorted_eigenvalues() -> None:
    with pytest.raises(ValueError):
        analyze_spectral_degeneracies([2.0, 1.0], dimension=2)


# ---------------------------------------------------------------------------
# SpectralLevelGroup construction invariants
# ---------------------------------------------------------------------------


def test_spectral_level_group_rejects_empty_range() -> None:
    with pytest.raises(ValueError):
        SpectralLevelGroup(
            start_index=2,
            end_index_exclusive=2,
            representative_energy=0.0,
            min_energy=0.0,
            max_energy=0.0,
            multiplicity_observed=0,
            lower_bound_only=False,
        )


def test_spectral_level_group_rejects_mismatched_multiplicity() -> None:
    with pytest.raises(ValueError):
        SpectralLevelGroup(
            start_index=0,
            end_index_exclusive=3,
            representative_energy=0.0,
            min_energy=0.0,
            max_energy=0.0,
            multiplicity_observed=99,
            lower_bound_only=False,
        )


def test_spectral_level_group_rejects_representative_outside_bounds() -> None:
    with pytest.raises(ValueError):
        SpectralLevelGroup(
            start_index=0,
            end_index_exclusive=1,
            representative_energy=10.0,
            min_energy=0.0,
            max_energy=1.0,
            multiplicity_observed=1,
            lower_bound_only=False,
        )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_spectral_level_group_rejects_non_finite_energies(bad_value: float) -> None:
    with pytest.raises(ValueError):
        SpectralLevelGroup(
            start_index=0,
            end_index_exclusive=1,
            representative_energy=bad_value,
            min_energy=bad_value,
            max_energy=bad_value,
            multiplicity_observed=1,
            lower_bound_only=False,
        )


# ---------------------------------------------------------------------------
# DegeneracyReport construction invariants
# ---------------------------------------------------------------------------


def _group(start: int, end: int, energy: float) -> SpectralLevelGroup:
    return SpectralLevelGroup(
        start_index=start,
        end_index_exclusive=end,
        representative_energy=energy,
        min_energy=energy,
        max_energy=energy,
        multiplicity_observed=end - start,
        lower_bound_only=False,
    )


def test_degeneracy_report_rejects_empty_groups() -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=1,
            first_distinct_energy=None,
            first_distinct_gap=None,
            groups=(),
            window_truncated=False,
        )


def test_degeneracy_report_rejects_non_contiguous_groups() -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=1,
            first_distinct_energy=5.0,
            first_distinct_gap=5.0,
            groups=(_group(0, 1, 0.0), _group(2, 3, 5.0)),  # gap in indices
            window_truncated=False,
        )


def test_degeneracy_report_rejects_wrong_ground_multiplicity() -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=99,
            first_distinct_energy=None,
            first_distinct_gap=None,
            groups=(_group(0, 1, 0.0),),
            window_truncated=False,
        )


def test_degeneracy_report_rejects_mismatched_first_distinct_gap() -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=1,
            first_distinct_energy=5.0,
            first_distinct_gap=999.0,  # wrong -- should be 5.0
            groups=(_group(0, 1, 0.0), _group(1, 2, 5.0)),
            window_truncated=False,
        )


def test_degeneracy_report_rejects_distinct_energy_set_with_single_group() -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=1,
            first_distinct_energy=5.0,
            first_distinct_gap=5.0,
            groups=(_group(0, 1, 0.0),),
            window_truncated=False,
        )


def test_degeneracy_report_rejects_overlapping_energy_ranges() -> None:
    overlapping_second = SpectralLevelGroup(
        start_index=1,
        end_index_exclusive=2,
        representative_energy=0.0,  # overlaps groups[0]'s max_energy of 0.0
        min_energy=-1.0,
        max_energy=0.0,
        multiplicity_observed=1,
        lower_bound_only=False,
    )
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=1e-10,
            ground_multiplicity_observed=1,
            first_distinct_energy=0.0,
            first_distinct_gap=0.0,
            groups=(_group(0, 1, 0.0), overlapping_second),
            window_truncated=False,
        )


@pytest.mark.parametrize("bad_tolerance", [0.0, -1e-10, float("inf"), float("nan"), True])
def test_degeneracy_report_rejects_bad_tolerance(bad_tolerance: float) -> None:
    with pytest.raises(ValueError):
        DegeneracyReport(
            tolerance=bad_tolerance,
            ground_multiplicity_observed=1,
            first_distinct_energy=None,
            first_distinct_gap=None,
            groups=(_group(0, 1, 0.0),),
            window_truncated=False,
        )
