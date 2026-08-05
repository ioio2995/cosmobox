"""Hamiltonian coupling parameters, H = H_dot + H_hop + H_E + H_B.

The full parameter set is defined up front (lot 4A) even though ``t`` and
``K`` are unused until hopping (4B) and the magnetic term (4C), so the
public API does not change shape across those lots.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

HERMITICITY_TOLERANCE = 1e-12


def _validate_real_finite(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


def _validate_hermitian_2x2(matrix: object, name: str) -> None:
    if not isinstance(matrix, np.ndarray):
        raise ValueError(f"{name} must be a numpy.ndarray, got {type(matrix).__name__}")
    if matrix.shape != (2, 2):
        raise ValueError(f"{name} must have shape (2, 2), got {matrix.shape}")
    if not np.allclose(matrix, matrix.conj().T, atol=HERMITICITY_TOLERANCE, rtol=0.0):
        raise ValueError(
            f"{name} must be Hermitian within {HERMITICITY_TOLERANCE}; "
            "a non-Hermitian h is a contract violation, not something to symmetrize silently"
        )


@dataclass(frozen=True, slots=True)
class HamiltonianParameters:
    J: tuple[float, ...]
    h: tuple[np.ndarray, ...]
    t: float
    g_E: float
    K: float

    def __post_init__(self) -> None:
        for index, value in enumerate(self.J):
            _validate_real_finite(value, f"J[{index}]")
        for index, matrix in enumerate(self.h):
            _validate_hermitian_2x2(matrix, f"h[{index}]")
        _validate_real_finite(self.t, "t")
        _validate_real_finite(self.g_E, "g_E")
        _validate_real_finite(self.K, "K")
