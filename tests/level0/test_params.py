from __future__ import annotations

import math

import numpy as np
import pytest

from cosmobox.level0.params import HamiltonianParameters


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def test_valid_construction_does_not_raise() -> None:
    HamiltonianParameters(
        J=(1.0, -0.5, 0.0),
        h=(
            _hermitian_matrix(1.0, -1.0, 0.5j),
            _hermitian_matrix(0.0, 0.0, 0.0),
            _hermitian_matrix(2.0, 2.0, 1 + 1j),
        ),
        t=1.0,
        g_E=0.5,
        K=0.0,
    )


def test_rejects_non_hermitian_h_instead_of_symmetrizing() -> None:
    non_hermitian = np.array([[1.0, 1.0], [0.0, 1.0]], dtype=np.complex128)
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(0.0,), h=(non_hermitian,), t=0.0, g_E=0.0, K=0.0)


def test_rejects_h_with_wrong_shape() -> None:
    wrong_shape = np.zeros((3, 3), dtype=np.complex128)
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(0.0,), h=(wrong_shape,), t=0.0, g_E=0.0, K=0.0)


def test_rejects_h_that_is_not_an_ndarray() -> None:
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(0.0,), h=([[1, 0], [0, 1]],), t=0.0, g_E=0.0, K=0.0)


@pytest.mark.parametrize("bad_j", [math.inf, -math.inf, math.nan])
def test_rejects_non_finite_j(bad_j: float) -> None:
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(bad_j,), h=(_hermitian_matrix(0, 0, 0),), t=0.0, g_E=0.0, K=0.0)


@pytest.mark.parametrize("field", ["t", "g_E", "K"])
def test_rejects_non_finite_scalar(field: str) -> None:
    kwargs = {"J": (0.0,), "h": (_hermitian_matrix(0, 0, 0),), "t": 0.0, "g_E": 0.0, "K": 0.0}
    kwargs[field] = math.nan
    with pytest.raises(ValueError):
        HamiltonianParameters(**kwargs)


def test_rejects_complex_j() -> None:
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(1 + 1j,), h=(_hermitian_matrix(0, 0, 0),), t=0.0, g_E=0.0, K=0.0)


def test_hermiticity_within_tolerance_is_accepted() -> None:
    perturbation = 1e-13  # below HERMITICITY_TOLERANCE = 1e-12
    almost_hermitian = np.array([[1.0, 1.0], [1.0 + perturbation, 1.0]], dtype=np.complex128)
    HamiltonianParameters(J=(0.0,), h=(almost_hermitian,), t=0.0, g_E=0.0, K=0.0)  # must not raise


def test_hermiticity_deviation_above_tolerance_is_rejected() -> None:
    deviation = 1e-10  # above HERMITICITY_TOLERANCE = 1e-12
    not_quite_hermitian = np.array([[1.0, 1.0], [1.0 + deviation, 1.0]], dtype=np.complex128)
    with pytest.raises(ValueError):
        HamiltonianParameters(J=(0.0,), h=(not_quite_hermitian,), t=0.0, g_E=0.0, K=0.0)
