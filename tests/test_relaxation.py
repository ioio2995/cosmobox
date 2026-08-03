"""EXP-0001 implementation, step 7B-2: interior relaxation under a
fixed, affinely-sheared boundary shell.

Per the step-7B-1 review: two boundary definitions are compared
(`degrees < 4` and `radius >= 0.85 * domain_radius`), a direct linear
block-solve reference is checked against the full nonlinear relaxation,
and the accommodation ratio rho(gamma) = E_relaxed / E_affine is
reported rather than assumed to vanish.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.elasticity import ElasticityConfig
from cosmobox.physics.relaxation import (
    ShearRelaxationRow,
    boundary_mask_by_degree,
    boundary_mask_by_radius,
    linear_relaxation,
    run_shear_relaxation_study,
    shear_relaxation_rows_to_table,
    write_shear_relaxation_table_csv,
)
from cosmobox.physics.rigidity import rigidity_matrix, stiffness_matrix
from cosmobox.physics.shear import affine_shear_displacement

_GAMMAS = np.array([1e-4, 2e-4, 5e-4, 1e-3])


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
def shear_direction(matrix: DiamondMatrix) -> np.ndarray:
    return affine_shear_displacement(matrix.reference_positions, from_axis=1, to_axis=0)


@pytest.fixture(
    scope="module",
    params=[
        ("degree", None),
        ("radius_0.85", 0.85),
    ],
    ids=["degree", "radius"],
)
def boundary(request: pytest.FixtureRequest, matrix: DiamondMatrix) -> tuple[str, np.ndarray]:
    name, alpha = request.param
    if alpha is None:
        return name, boundary_mask_by_degree(matrix.degrees)
    return name, boundary_mask_by_radius(matrix.reference_positions, matrix.config.radius, alpha)


def test_boundary_definitions_produce_nonempty_interior_and_boundary(
    boundary: tuple[str, np.ndarray]
) -> None:
    _, mask = boundary
    assert 0 < mask.sum() < len(mask)
    assert 0 < (~mask).sum() < len(mask)


def test_degree_and_radius_boundary_definitions_are_not_identical(matrix: DiamondMatrix) -> None:
    degree_mask = boundary_mask_by_degree(matrix.degrees)
    radius_mask = boundary_mask_by_radius(matrix.reference_positions, matrix.config.radius, 0.85)
    assert not np.array_equal(degree_mask, radius_mask)


def test_linear_relaxation_ratio_is_gamma_independent(
    K: np.ndarray, shear_direction: np.ndarray, boundary: tuple[str, np.ndarray]
) -> None:
    # A purely linear/quadratic system: both E_affine and E_relaxed
    # scale as gamma^2, so their ratio must not depend on gamma.
    _, mask = boundary
    ratios = []
    for gamma in _GAMMAS:
        displacement = gamma * shear_direction
        result = linear_relaxation(K, mask, displacement)
        affine_energy = 0.5 * displacement @ K @ displacement
        ratios.append(result.energy / affine_energy)
    assert np.allclose(ratios, ratios[0], rtol=1e-9)


def test_linear_relaxation_reduces_energy_but_does_not_vanish(
    K: np.ndarray, shear_direction: np.ndarray, boundary: tuple[str, np.ndarray]
) -> None:
    _, mask = boundary
    displacement = 1e-3 * shear_direction
    result = linear_relaxation(K, mask, displacement)
    affine_energy = 0.5 * displacement @ K @ displacement
    ratio = result.energy / affine_energy
    assert 0.0 < ratio < 1.0
    assert result.interior_mechanism_dimension >= 0


def test_nonlinear_relaxation_matches_linear_reference_at_small_gamma(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, K: np.ndarray, shear_direction: np.ndarray,
    boundary: tuple[str, np.ndarray],
) -> None:
    _, mask = boundary
    gamma = 1e-4
    displacement = gamma * shear_direction
    linear_result = linear_relaxation(K, mask, displacement)
    linear_ratio = linear_result.energy / (0.5 * displacement @ K @ displacement)

    rows = run_shear_relaxation_study(
        matrix.reference_positions, matrix.edges, elasticity, mask, shear_direction, np.array([gamma])
    )
    nonlinear_row = rows[0]
    assert nonlinear_row.converged
    assert nonlinear_row.status == "converged"
    assert nonlinear_row.ratio == pytest.approx(linear_ratio, rel=1e-3)


def test_relaxation_runs_converge_with_small_gradient_and_no_bond_collapse(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, shear_direction: np.ndarray,
    boundary: tuple[str, np.ndarray],
) -> None:
    _, mask = boundary
    rows = run_shear_relaxation_study(matrix.reference_positions, matrix.edges, elasticity, mask, shear_direction, _GAMMAS)
    assert len(rows) == len(_GAMMAS)
    for row in rows:
        assert isinstance(row, ShearRelaxationRow)
        assert row.converged
        assert row.status == "converged"
        assert row.gradient_norm < 1e-8
        assert 0 < row.iterations < 2000
        assert 0.0 < row.ratio < 1.0
        # Bond length should stay close to the rest length c, not
        # collapse toward 0 (a degenerate configuration).
        assert row.min_bond_length > 0.9 * matrix.c


def test_shear_relaxation_table_round_trips_through_csv(
    matrix: DiamondMatrix, elasticity: ElasticityConfig, shear_direction: np.ndarray,
    boundary: tuple[str, np.ndarray], tmp_path,
) -> None:
    _, mask = boundary
    rows = run_shear_relaxation_study(matrix.reference_positions, matrix.edges, elasticity, mask, shear_direction, _GAMMAS)

    csv_path = tmp_path / "shear_relaxation.csv"
    write_shear_relaxation_table_csv(rows, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = shear_relaxation_rows_to_table(rows)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back, expected):
        assert float(read_row["gamma"]) == pytest.approx(expected_row["gamma"])
        assert float(read_row["ratio"]) == pytest.approx(expected_row["ratio"])
