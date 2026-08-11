from __future__ import annotations

from level1c_response_helpers import build_group_documents

from scripts.level1c_response.response import _extract_unique_ctt_pairs, _extract_unique_rho_pairs


def test_ctt_extraction_basic() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, ctt_records=[(0, 1, 0.5), (1, 0, -0.25)])
    pairs, error = _extract_unique_ctt_pairs(documents)
    assert error is None
    assert pairs == {(0, 1): 0.5, (1, 0): -0.25}


def test_ctt_extraction_duplicate_pair_rejected() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, ctt_records=[(0, 1, 0.5), (0, 1, 0.6)])
    pairs, error = _extract_unique_ctt_pairs(documents)
    assert pairs is None
    assert "CTT_DUPLICATE_PAIR" in error


def test_ctt_extraction_non_finite_rejected() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, ctt_records=[(0, 1, float("inf"))])
    pairs, error = _extract_unique_ctt_pairs(documents)
    assert pairs is None
    assert "CTT_NON_FINITE_VALUE" in error


def test_ctt_extraction_ignores_diagonal_and_other_record_kinds() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, ctt_records=[(0, 0, 0.75), (0, 1, 0.5)])
    pairs, error = _extract_unique_ctt_pairs(documents)
    assert error is None
    assert pairs == {(0, 1): 0.5}


def test_rho_extraction_numeric() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, rho_records=[(0, 1, -0.5, None)])
    pairs, error = _extract_unique_rho_pairs(documents)
    assert error is None
    assert pairs == {(0, 1): (-0.5, None)}


def test_rho_extraction_null_preserved() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, rho_records=[(0, 1, None, "zero_local_charge_variance")])
    pairs, error = _extract_unique_rho_pairs(documents)
    assert error is None
    assert pairs == {(0, 1): (None, "zero_local_charge_variance")}


def test_rho_extraction_duplicate_pair_rejected() -> None:
    documents = build_group_documents(
        geometry="triangle", spin=2, group_index=0, rho_records=[(0, 1, -0.5, None), (0, 1, -0.5, None)]
    )
    pairs, error = _extract_unique_rho_pairs(documents)
    assert pairs is None
    assert "RHO_DUPLICATE_PAIR" in error


def test_rho_extraction_non_finite_rejected() -> None:
    documents = build_group_documents(geometry="triangle", spin=2, group_index=0, rho_records=[(0, 1, float("nan"), None)])
    pairs, error = _extract_unique_rho_pairs(documents)
    assert pairs is None
    assert "RHO_NON_FINITE_VALUE" in error
