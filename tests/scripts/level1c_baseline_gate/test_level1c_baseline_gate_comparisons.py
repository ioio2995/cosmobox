from __future__ import annotations

import math

import pytest

from cosmobox.level1.matching import SymmetryLabel
from scripts.level1c_baseline_gate.gate import (
    FAIL,
    PASS,
    GroupStructuralData,
    compare_ctt,
    compare_rho,
    compare_structural,
)

CTT_TOL = 1e-15
RHO_TOL = 1e-15


def _numeric_label(value: complex) -> SymmetryLabel:
    return SymmetryLabel(kind="numeric", value=value)


def _group(
    *,
    multiplicity=4,
    twice_T=1,
    translation=None,
    reflection=None,
    representative_energy=-1.0,
    ctt_pairs=None,
    rho_pairs=None,
) -> GroupStructuralData:
    return GroupStructuralData(
        spectral_window_group_index=0,
        multiplicity=multiplicity,
        twice_T=twice_T,
        translation_label=translation if translation is not None else _numeric_label(1.0 + 0j),
        reflection_label=reflection if reflection is not None else _numeric_label(1.0 + 0j),
        representative_energy=representative_energy,
        ctt_pairs=ctt_pairs if ctt_pairs is not None else {(0, 1): 0.25, (1, 0): 0.25},
        rho_pairs=rho_pairs if rho_pairs is not None else {(0, 1): (-0.5, None), (1, 0): (-0.5, None)},
    )


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------


def test_structural_exact_match_passes() -> None:
    status, reasons = compare_structural(_group(), _group())
    assert status == PASS
    assert reasons == ()


def test_multiplicity_mismatch_fails() -> None:
    status, reasons = compare_structural(_group(multiplicity=4), _group(multiplicity=2))
    assert status == FAIL
    assert any("MULTIPLICITY_MISMATCH" in reason for reason in reasons)


def test_twice_t_mismatch_fails() -> None:
    status, reasons = compare_structural(_group(twice_T=1), _group(twice_T=3))
    assert status == FAIL
    assert any("TWICE_T_MISMATCH" in reason for reason in reasons)


def test_translation_mismatch_fails() -> None:
    status, reasons = compare_structural(_group(translation=_numeric_label(1.0)), _group(translation=_numeric_label(-1.0)))
    assert status == FAIL
    assert any("TRANSLATION_LABEL_MISMATCH" in reason for reason in reasons)


def test_reflection_mismatch_fails() -> None:
    status, reasons = compare_structural(_group(reflection=_numeric_label(1.0)), _group(reflection=_numeric_label(-1.0)))
    assert status == FAIL
    assert any("REFLECTION_LABEL_MISMATCH" in reason for reason in reasons)


def test_representative_energy_mismatch_alone_still_passes() -> None:
    """representative_energy is OPTIONAL_DIAGNOSTIC -- never compared,
    never a cause of FAIL by itself."""
    status, reasons = compare_structural(_group(representative_energy=-5.0), _group(representative_energy=+5.0))
    assert status == PASS
    assert reasons == ()


def test_not_applicable_labels_agree() -> None:
    na = SymmetryLabel(kind="not_applicable", value=None)
    status, _ = compare_structural(_group(translation=na), _group(translation=na))
    assert status == PASS


def test_unavailable_labels_never_agree() -> None:
    unavailable = SymmetryLabel(kind="unavailable", value=None)
    status, reasons = compare_structural(_group(translation=unavailable), _group(translation=unavailable))
    assert status == FAIL
    assert any("TRANSLATION_LABEL_MISMATCH" in reason for reason in reasons)


# ---------------------------------------------------------------------------
# CTT
# ---------------------------------------------------------------------------


def test_ctt_exact_match_passes() -> None:
    status, max_abs_diff, reasons = compare_ctt(_group(), _group(), abs_tol=CTT_TOL)
    assert status == PASS
    assert max_abs_diff == 0.0
    assert reasons == ()


def test_ctt_diff_below_tolerance_passes() -> None:
    historical = _group(ctt_pairs={(0, 1): 0.25})
    current = _group(ctt_pairs={(0, 1): 0.25 + CTT_TOL / 2})
    status, max_abs_diff, _ = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == PASS
    assert max_abs_diff == pytest.approx(CTT_TOL / 2)


def test_ctt_diff_exactly_at_tolerance_passes() -> None:
    historical = _group(ctt_pairs={(0, 1): 0.25})
    current = _group(ctt_pairs={(0, 1): 0.25 + CTT_TOL})
    status, max_abs_diff, _ = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == PASS


def test_ctt_diff_above_tolerance_fails() -> None:
    historical = _group(ctt_pairs={(0, 1): 0.25})
    current = _group(ctt_pairs={(0, 1): 0.25 + CTT_TOL * 2})
    status, max_abs_diff, reasons = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == FAIL
    assert any("CTT_TOLERANCE_EXCEEDED" in reason for reason in reasons)


def test_ctt_pair_set_mismatch_fails() -> None:
    historical = _group(ctt_pairs={(0, 1): 0.25})
    current = _group(ctt_pairs={(0, 2): 0.25})
    status, max_abs_diff, reasons = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == FAIL
    assert max_abs_diff is None
    assert reasons == ("CTT_PAIR_SET_MISMATCH",)


def test_ctt_nonfinite_value_fails() -> None:
    historical = _group(ctt_pairs={(0, 1): float("nan")})
    current = _group(ctt_pairs={(0, 1): 0.25})
    status, max_abs_diff, reasons = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == FAIL
    assert reasons == ("CTT_NON_FINITE_VALUE",)


def test_ctt_infinite_value_fails() -> None:
    historical = _group(ctt_pairs={(0, 1): 0.25})
    current = _group(ctt_pairs={(0, 1): float("inf")})
    status, _, reasons = compare_ctt(historical, current, abs_tol=CTT_TOL)
    assert status == FAIL
    assert reasons == ("CTT_NON_FINITE_VALUE",)


# ---------------------------------------------------------------------------
# rho
# ---------------------------------------------------------------------------


def test_rho_numeric_exact_match_passes() -> None:
    historical = _group(rho_pairs={(0, 1): (-0.5, None)})
    current = _group(rho_pairs={(0, 1): (-0.5, None)})
    status, max_abs_diff, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == PASS
    assert max_abs_diff == 0.0


def test_rho_diff_at_tolerance_boundary_passes() -> None:
    historical = _group(rho_pairs={(0, 1): (-0.5, None)})
    current = _group(rho_pairs={(0, 1): (-0.5 + RHO_TOL, None)})
    status, _, _ = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == PASS


def test_rho_diff_above_tolerance_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (-0.5, None)})
    current = _group(rho_pairs={(0, 1): (-0.5 + RHO_TOL * 2, None)})
    status, _, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert any("RHO_TOLERANCE_EXCEEDED" in reason for reason in reasons)


def test_rho_null_null_same_reason_passes() -> None:
    historical = _group(rho_pairs={(0, 1): (None, "zero_local_charge_variance")})
    current = _group(rho_pairs={(0, 1): (None, "zero_local_charge_variance")})
    status, max_abs_diff, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == PASS
    assert max_abs_diff is None
    assert reasons == ()


def test_rho_null_null_different_reason_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (None, "zero_local_charge_variance")})
    current = _group(rho_pairs={(0, 1): (None, "normalization_denominator_below_floor")})
    status, _, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert any("RHO_NULL_REASON_MISMATCH" in reason for reason in reasons)


def test_rho_numeric_vs_null_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (-0.5, None)})
    current = _group(rho_pairs={(0, 1): (None, "zero_local_charge_variance")})
    status, _, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert any("RHO_NULLITY_MISMATCH" in reason for reason in reasons)


def test_rho_null_vs_numeric_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (None, "zero_local_charge_variance")})
    current = _group(rho_pairs={(0, 1): (-0.5, None)})
    status, _, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert any("RHO_NULLITY_MISMATCH" in reason for reason in reasons)


def test_rho_pair_set_mismatch_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (-0.5, None)})
    current = _group(rho_pairs={(0, 2): (-0.5, None)})
    status, max_abs_diff, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert max_abs_diff is None
    assert reasons == ("RHO_PAIR_SET_MISMATCH",)


def test_rho_nonfinite_value_fails() -> None:
    historical = _group(rho_pairs={(0, 1): (float("nan"), None)})
    current = _group(rho_pairs={(0, 1): (-0.5, None)})
    status, _, reasons = compare_rho(historical, current, abs_tol=RHO_TOL)
    assert status == FAIL
    assert any("RHO_NON_FINITE_VALUE" in reason for reason in reasons)
