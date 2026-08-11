from __future__ import annotations

import math

import numpy as np
import pytest

from cosmobox.level2.metrics import (
    NEGATIVE,
    NO_NUMERIC_RHO_QQ_PAIR,
    NUMERICAL_GUARD_M_TT,
    NUMERICAL_GUARD_R_EFF,
    NUMERICALLY_UNRESOLVED,
    POSITIVE,
    ZERO_CTT_MATRIX,
    Available,
    RhoQQEntry,
    a_qq,
    classify_contrast,
    m_qq,
    m_tt,
    r_eff,
)

# ---------------------------------------------------------------------------
# Available
# ---------------------------------------------------------------------------


def test_available_rejects_value_and_reason_both_set():
    with pytest.raises(ValueError):
        Available(1.0, "some_reason")


def test_available_rejects_neither_value_nor_reason_set():
    with pytest.raises(ValueError):
        Available(None, None)


def test_available_rejects_non_finite_value():
    with pytest.raises(ValueError):
        Available(math.inf, None)


# ---------------------------------------------------------------------------
# M_TT
# ---------------------------------------------------------------------------


def test_m_tt_analytic_simple():
    matrix = np.array([[0.0, 3.0], [3.0, 0.0]])
    assert m_tt(matrix) == pytest.approx(3.0)


def test_m_tt_analytic_three_by_three():
    matrix = np.array(
        [
            [99.0, 1.0, 2.0],
            [1.0, 99.0, 0.0],
            [2.0, 0.0, 99.0],
        ]
    )
    # off-diag entries: 1,2,1,0,2,0 -> sum sq = 1+4+1+0+4+0 = 10, N(N-1)=6
    assert m_tt(matrix) == pytest.approx(math.sqrt(10.0 / 6.0))


def test_m_tt_invariant_under_simultaneous_row_column_permutation():
    rng = np.random.default_rng(0)
    matrix = rng.normal(size=(4, 4))
    np.fill_diagonal(matrix, rng.normal(size=4))
    permutation = [2, 0, 3, 1]
    permuted = matrix[np.ix_(permutation, permutation)]
    assert m_tt(matrix) == pytest.approx(m_tt(permuted))


def test_m_tt_ignores_diagonal():
    matrix_a = np.array([[0.0, 5.0], [5.0, 0.0]])
    matrix_b = np.array([[123.0, 5.0], [5.0, -456.0]])
    assert m_tt(matrix_a) == pytest.approx(m_tt(matrix_b))


def test_m_tt_rejects_n_below_2():
    with pytest.raises(ValueError):
        m_tt(np.array([[1.0]]))


def test_m_tt_rejects_non_square():
    with pytest.raises(ValueError):
        m_tt(np.zeros((2, 3)))


def test_m_tt_rejects_non_finite():
    matrix = np.array([[0.0, math.inf], [math.inf, 0.0]])
    with pytest.raises(ValueError):
        m_tt(matrix)


# ---------------------------------------------------------------------------
# R_eff
# ---------------------------------------------------------------------------


def test_r_eff_rank_one_matrix():
    vector = np.array([1.0, 2.0, 3.0])
    matrix = np.outer(vector, vector)
    result = r_eff(matrix)
    assert result.reason is None
    # a single nonzero singular value -> p_1 = 1 -> entropy = 0 -> r_eff = 1
    assert result.value == pytest.approx(1.0 / 3)


def test_r_eff_uniform_singular_spectrum_is_identity():
    matrix = np.eye(4) * 2.0
    result = r_eff(matrix)
    # N equal singular values -> maximal entropy -> r_eff = N -> R_eff = 1
    assert result.value == pytest.approx(1.0)


def test_r_eff_zero_matrix_is_not_available():
    result = r_eff(np.zeros((3, 3)))
    assert result.value is None
    assert result.reason == ZERO_CTT_MATRIX


def test_r_eff_invariant_under_nonzero_scale():
    rng = np.random.default_rng(1)
    matrix = rng.normal(size=(4, 4))
    base = r_eff(matrix)
    scaled = r_eff(matrix * 7.5)
    assert base.value == pytest.approx(scaled.value)


def test_r_eff_rejects_non_square():
    with pytest.raises(ValueError):
        r_eff(np.zeros((2, 3)))


# ---------------------------------------------------------------------------
# rho_QQ -- A_QQ, M_QQ
# ---------------------------------------------------------------------------


def _all_numeric_pairs(n: int, value: float = 0.5) -> dict[tuple[int, int], RhoQQEntry]:
    return {(i, j): RhoQQEntry(value, None) for i in range(n) for j in range(n) if i != j}


def test_a_qq_all_numeric():
    pairs = _all_numeric_pairs(3)
    assert a_qq(pairs, 3) == pytest.approx(1.0)


def test_a_qq_partially_numeric():
    pairs = _all_numeric_pairs(3)
    pairs[(0, 1)] = RhoQQEntry(None, "zero_local_charge_variance")
    # 5 numeric out of 6 ordered pairs
    assert a_qq(pairs, 3) == pytest.approx(5.0 / 6.0)


def test_a_qq_none_numeric():
    pairs = {key: RhoQQEntry(None, "zero_local_charge_variance") for key in _all_numeric_pairs(3)}
    assert a_qq(pairs, 3) == pytest.approx(0.0)


def test_a_qq_rejects_incomplete_pairs():
    pairs = _all_numeric_pairs(3)
    del pairs[(0, 1)]
    with pytest.raises(ValueError):
        a_qq(pairs, 3)


def test_m_qq_rms_without_null_imputation():
    pairs = _all_numeric_pairs(2, value=3.0)  # (0,1) and (1,0)
    pairs[(1, 0)] = RhoQQEntry(-4.0, None)
    result = m_qq(pairs, 2)
    # sqrt(mean(3^2, (-4)^2)) = sqrt((9+16)/2) = sqrt(12.5)
    assert result.value == pytest.approx(math.sqrt(12.5))
    assert result.reason is None


def test_m_qq_none_numeric_is_not_available():
    pairs = {key: RhoQQEntry(None, "zero_local_charge_variance") for key in _all_numeric_pairs(2)}
    result = m_qq(pairs, 2)
    assert result.value is None
    assert result.reason == NO_NUMERIC_RHO_QQ_PAIR


def test_rho_qq_entry_rejects_value_and_null_reason_both_set():
    with pytest.raises(ValueError):
        RhoQQEntry(1.0, "reason")


def test_rho_qq_entry_rejects_neither_set():
    with pytest.raises(ValueError):
        RhoQQEntry(None, None)


# ---------------------------------------------------------------------------
# classify_contrast -- M_TT guard
# ---------------------------------------------------------------------------


def test_classify_contrast_m_tt_zero_is_unresolved():
    assert classify_contrast(0.0, metric="M_TT") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_m_tt_at_positive_guard_is_unresolved():
    assert classify_contrast(NUMERICAL_GUARD_M_TT, metric="M_TT") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_m_tt_at_negative_guard_is_unresolved():
    assert classify_contrast(-NUMERICAL_GUARD_M_TT, metric="M_TT") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_m_tt_just_above_guard_is_positive():
    value = math.nextafter(NUMERICAL_GUARD_M_TT, math.inf)
    assert classify_contrast(value, metric="M_TT") == POSITIVE


def test_classify_contrast_m_tt_just_below_negative_guard_is_negative():
    value = math.nextafter(-NUMERICAL_GUARD_M_TT, -math.inf)
    assert classify_contrast(value, metric="M_TT") == NEGATIVE


# ---------------------------------------------------------------------------
# classify_contrast -- R_eff guard
# ---------------------------------------------------------------------------


def test_classify_contrast_r_eff_zero_is_unresolved():
    assert classify_contrast(0.0, metric="R_eff") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_r_eff_at_positive_guard_is_unresolved():
    assert classify_contrast(NUMERICAL_GUARD_R_EFF, metric="R_eff") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_r_eff_at_negative_guard_is_unresolved():
    assert classify_contrast(-NUMERICAL_GUARD_R_EFF, metric="R_eff") == NUMERICALLY_UNRESOLVED


def test_classify_contrast_r_eff_just_above_guard_is_positive():
    value = math.nextafter(NUMERICAL_GUARD_R_EFF, math.inf)
    assert classify_contrast(value, metric="R_eff") == POSITIVE


def test_classify_contrast_r_eff_just_below_negative_guard_is_negative():
    value = math.nextafter(-NUMERICAL_GUARD_R_EFF, -math.inf)
    assert classify_contrast(value, metric="R_eff") == NEGATIVE


def test_classify_contrast_rejects_unknown_metric():
    with pytest.raises(ValueError):
        classify_contrast(1.0, metric="A_QQ")


def test_classify_contrast_rejects_non_finite_delta():
    with pytest.raises(ValueError):
        classify_contrast(math.inf, metric="M_TT")
