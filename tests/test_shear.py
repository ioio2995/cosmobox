"""EXP-0001 implementation, step 7B-1: static affine shear energy test
(no relaxation, no dynamics — that's 7B-2/7B-3). Determines whether the
quadratic shear-energy coefficient a2 is strictly positive for the
x' = x + gamma*y shear on this central-force-only lattice.
"""
from __future__ import annotations

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.rigidity import analyze_modes, kernel_projector, rigidity_matrix, stiffness_matrix
from cosmobox.physics.shear import (
    affine_shear_displacement,
    exact_quadratic_coefficient,
    project_out_kernel,
    shear_energy_curve,
)

_GAMMAS = np.array([-1e-3, -5e-4, -2e-4, -1e-4, 1e-4, 2e-4, 5e-4, 1e-3])


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def elasticity(matrix: DiamondMatrix) -> ElasticityConfig:
    return ElasticityConfig(rest_length=matrix.c, stiffness=1.0)


@pytest.fixture(scope="module")
def K(matrix: DiamondMatrix) -> np.ndarray:
    B = rigidity_matrix(matrix.reference_positions, matrix.edges)
    return stiffness_matrix(B, 1.0)


@pytest.fixture(scope="module")
def raw_shear_direction(matrix: DiamondMatrix) -> np.ndarray:
    return affine_shear_displacement(matrix.reference_positions, from_axis=1, to_axis=0)


@pytest.fixture(scope="module")
def projector(matrix: DiamondMatrix) -> np.ndarray:
    analysis = analyze_modes(matrix.reference_positions, matrix.edges, matrix.degrees, stiffness=1.0)
    kernel_basis = np.array([mode.displacement.ravel() for mode in analysis.modes])
    return kernel_projector(kernel_basis)


@pytest.fixture(scope="module")
def projected_shear_direction(raw_shear_direction: np.ndarray, projector: np.ndarray) -> np.ndarray:
    return project_out_kernel(raw_shear_direction, projector)


def test_projected_direction_has_no_remaining_kernel_component(
    projected_shear_direction: np.ndarray, projector: np.ndarray
) -> None:
    residual = projector @ projected_shear_direction
    assert np.linalg.norm(residual) < 1e-9 * np.linalg.norm(projected_shear_direction)


def test_raw_shear_direction_has_a_large_kernel_component(
    raw_shear_direction: np.ndarray, projected_shear_direction: np.ndarray
) -> None:
    # Not a universal claim — specific to this shear pattern on this
    # lattice, and exactly the reason a2 is worth checking rather than
    # assumed: most of the raw generator's norm lies in the kernel.
    assert np.linalg.norm(projected_shear_direction) < 0.5 * np.linalg.norm(raw_shear_direction)


def test_quadratic_coefficient_is_identical_for_raw_and_projected_direction(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, raw_shear_direction: np.ndarray,
    projected_shear_direction: np.ndarray,
) -> None:
    # Mathematical identity (see physics/shear.py docstring): u.T @ K @ u
    # depends only on u's component outside the kernel, so a2 must be
    # the same whether measured from the raw or the projected direction
    # — this is not expected to reveal a *difference*, it verifies the
    # identity holds numerically for the actual nonlinear bond energy,
    # not just its quadratic approximation.
    raw_curve = shear_energy_curve(
        matrix.reference_positions, matrix.edges, elasticity, raw_shear_direction, _GAMMAS
    )
    projected_curve = shear_energy_curve(
        matrix.reference_positions, matrix.edges, elasticity, projected_shear_direction, _GAMMAS
    )
    assert raw_curve.quadratic_coefficient == pytest.approx(
        projected_curve.quadratic_coefficient, rel=1e-6
    )


def test_quadratic_shear_coefficient_is_strictly_positive(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, raw_shear_direction: np.ndarray
) -> None:
    curve = shear_energy_curve(
        matrix.reference_positions, matrix.edges, elasticity, raw_shear_direction, _GAMMAS
    )
    assert curve.quadratic_coefficient > 0.0


def test_energy_curve_is_consistent_with_zero_energy_at_zero_gamma(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, raw_shear_direction: np.ndarray
) -> None:
    # The fit deliberately excludes a constant term (E(0) = 0 is exact,
    # not fit) — verify that assumption is actually safe by fitting a
    # version *with* a constant term and checking it comes out ~0.
    curve = shear_energy_curve(
        matrix.reference_positions, matrix.edges, elasticity, raw_shear_direction, _GAMMAS
    )
    design_with_constant = np.column_stack(
        [np.ones_like(_GAMMAS), _GAMMAS**2, _GAMMAS**3, _GAMMAS**4]
    )
    coefficients, *_ = np.linalg.lstsq(design_with_constant, curve.energies, rcond=None)
    constant_term = coefficients[0]
    assert abs(constant_term) < 1e-6 * curve.energies.max()


def test_energy_is_symmetric_for_this_shear_pattern(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, raw_shear_direction: np.ndarray
) -> None:
    # Not assumed in general (that's why cubic/quartic terms are fit at
    # all) — checked directly: for this particular pattern, E(gamma) ==
    # E(-gamma) within numerical noise.
    curve = shear_energy_curve(
        matrix.reference_positions, matrix.edges, elasticity, raw_shear_direction, _GAMMAS
    )
    order = np.argsort(curve.gammas)
    gammas_sorted = curve.gammas[order]
    energies_sorted = curve.energies[order]
    assert np.allclose(energies_sorted, energies_sorted[::-1], rtol=1e-6)


def test_fitted_quadratic_coefficient_matches_the_exact_linearized_value(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, raw_shear_direction: np.ndarray,
    projected_shear_direction: np.ndarray, K: np.ndarray,
) -> None:
    # Confirms the finite-gamma fit isn't biased by the cubic/quartic
    # terms over the chosen gamma range, for both directions.
    for direction in (raw_shear_direction, projected_shear_direction):
        curve = shear_energy_curve(matrix.reference_positions, matrix.edges, elasticity, direction, _GAMMAS)
        exact = exact_quadratic_coefficient(K, direction)
        assert curve.quadratic_coefficient == pytest.approx(exact, rel=1e-6)
