from __future__ import annotations

from fractions import Fraction

import pytest

from cosmobox.level0.charges import double, doubled_external_charges, normalize_external_charges


def test_normalize_none_gives_all_zero() -> None:
    assert normalize_external_charges(3, None) == (Fraction(0), Fraction(0), Fraction(0))


def test_normalize_accepts_int_and_half_integer() -> None:
    result = normalize_external_charges(3, (1, Fraction(1, 2), Fraction(-1, 2)))
    assert result == (Fraction(1), Fraction(1, 2), Fraction(-1, 2))


def test_normalize_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        normalize_external_charges(3, (0, 0))


def test_normalize_rejects_bad_denominator() -> None:
    with pytest.raises(ValueError):
        normalize_external_charges(3, (Fraction(1, 3), 0, 0))


def test_double_integer_and_half_integer() -> None:
    assert double(Fraction(3)) == 6
    assert double(Fraction(1, 2)) == 1
    assert double(Fraction(-1, 2)) == -1


def test_double_rejects_bad_denominator() -> None:
    with pytest.raises(ValueError):
        double(Fraction(1, 3))


def test_doubled_external_charges() -> None:
    normalized = normalize_external_charges(3, (1, Fraction(1, 2), Fraction(-3, 2)))
    assert doubled_external_charges(normalized) == (2, 1, -3)
