"""EXP-0001 implementation, step 7A: linearized rigidity / null-mode
analysis, per docs review — answers whether the central-force-only
diamond lattice has infinitesimal zero-energy deformations beyond the
six rigid-body motions. No angular spring or extra coupling is added
here; a large null space is the expected discriminating result, not a
defect to silently fix.
"""
from __future__ import annotations

import csv

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.physics.rigidity import (
    Mode,
    RigidityAnalysis,
    analyze_modes,
    modes_to_table,
    rigid_rotation_basis,
    rigid_translation_basis,
    rigidity_matrix,
    stiffness_matrix,
    verify_rigid_motions_are_null,
    write_modes_table_csv,
)

# rank(B) and nullity(B) = 3N - rank(B), locked as reproducible
# results of this repo's lattice construction (no eigh needed — see
# the step-7A review, "verrouiller le comptage sur plusieurs tailles
# ... sans nécessairement diagonaliser le grand K").
_EXPECTED_RANK_AND_NULLITY = {
    (3.0, 3): (16, 35),
    (5.5, 5): (136, 125),
    (8.2, 7): (500, 379),
}

_STIFFNESS = 1.0
_NULL_TOLERANCE = 1e-6


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


@pytest.fixture(scope="module")
def K(matrix: DiamondMatrix) -> np.ndarray:
    B = rigidity_matrix(matrix.reference_positions, matrix.edges)
    return stiffness_matrix(B, _STIFFNESS)


@pytest.fixture(scope="module")
def translation_basis(matrix: DiamondMatrix) -> np.ndarray:
    return rigid_translation_basis(len(matrix.reference_positions))


@pytest.fixture(scope="module")
def rotation_basis(matrix: DiamondMatrix, translation_basis: np.ndarray) -> np.ndarray:
    return rigid_rotation_basis(matrix.reference_positions, translation_basis)


@pytest.fixture(scope="module")
def analysis(matrix: DiamondMatrix) -> RigidityAnalysis:
    return analyze_modes(
        matrix.reference_positions, matrix.edges, matrix.degrees, _STIFFNESS, _NULL_TOLERANCE
    )


# --- multi-size rank/nullity, locked as a reproducible result (no eigh) ---


@pytest.mark.parametrize("radius,cell_range", sorted(_EXPECTED_RANK_AND_NULLITY))
def test_rank_and_nullity_across_lattice_sizes(radius: float, cell_range: int) -> None:
    small_matrix = DiamondMatrix(MatrixConfig(radius=radius, cell_range=cell_range))
    B = rigidity_matrix(small_matrix.reference_positions, small_matrix.edges)
    rank_B = int(np.linalg.matrix_rank(B))
    n_dof = 3 * len(small_matrix.reference_positions)

    expected_rank, expected_nullity = _EXPECTED_RANK_AND_NULLITY[(radius, cell_range)]
    assert rank_B == expected_rank
    assert n_dof - rank_B == expected_nullity
    assert rank_B == len(small_matrix.edges)  # every bond-length constraint independent
    assert n_dof - rank_B > 6  # more null modes than the six rigid motions alone


# --- basis sanity ---


def test_translation_basis_is_orthonormal(translation_basis: np.ndarray) -> None:
    assert np.allclose(translation_basis @ translation_basis.T, np.eye(3), atol=1e-9)


def test_rotation_basis_is_orthonormal_and_orthogonal_to_translations(
    translation_basis: np.ndarray, rotation_basis: np.ndarray
) -> None:
    assert np.allclose(rotation_basis @ rotation_basis.T, np.eye(3), atol=1e-9)
    assert np.allclose(translation_basis @ rotation_basis.T, np.zeros((3, 3)), atol=1e-9)


# --- direct verification, not inferred from the eigen-decomposition ---


def test_rigid_motions_are_verified_null_directly_against_K(
    K: np.ndarray, translation_basis: np.ndarray, rotation_basis: np.ndarray
) -> None:
    residuals = verify_rigid_motions_are_null(K, translation_basis, rotation_basis)
    assert set(residuals) == {
        "translation_x", "translation_y", "translation_z",
        "rotation_x", "rotation_y", "rotation_z",
    }
    for name, residual in residuals.items():
        assert residual < 1e-8, f"{name}: ||K @ v|| = {residual}, expected ~0"


# --- rank / nullity consistency ---


def test_null_space_dimension_matches_rank_nullity_theorem(analysis: RigidityAnalysis) -> None:
    # nullity(K) == nullity(B) == n_dof - rank(B) for K = k * B.T @ B,
    # k > 0 — two independent computations (eigenvalue count vs. matrix
    # rank) that must agree, not the same fact stated twice.
    assert analysis.null_space_dimension == analysis.n_dof - analysis.rank_B


def test_null_space_contains_at_least_the_six_rigid_motions(analysis: RigidityAnalysis) -> None:
    assert analysis.null_space_dimension >= 6


def test_reports_internal_mechanisms_beyond_the_six_rigid_motions(analysis: RigidityAnalysis) -> None:
    # The measured result for this central-force-only, coordination-4
    # network: not asserting a specific count (that would presuppose an
    # answer), only that there is more null space than the six rigid
    # motions can account for — the discriminating observation itself.
    assert analysis.null_space_dimension > 6
    assert analysis.rank_B == analysis.n_edges  # every bond-length constraint is independent here


# --- basis-independent (subspace-level) invariants ---


def test_kernel_projector_agrees_with_direct_K_check_on_rigid_motions(analysis: RigidityAnalysis) -> None:
    # kernel_contains_rigid_subspace (||P0 @ v - v||) is a different
    # computation from verify_rigid_motions_are_null (||K @ v||); both
    # must independently confirm the rigid subspace lies in the kernel.
    for name, residual in analysis.kernel_rigid_subspace_residuals.items():
        assert residual < 1e-8, f"{name}: ||P0 @ v - v|| = {residual}, expected ~0"


def test_kernel_boundary_weight_fraction_is_a_valid_fraction(analysis: RigidityAnalysis) -> None:
    assert 0.0 <= analysis.kernel_boundary_weight_fraction <= 1.0 + 1e-9


def test_kernel_boundary_localization_range_is_consistent(analysis: RigidityAnalysis) -> None:
    minimum, maximum = analysis.kernel_boundary_localization_range
    assert -1e-9 <= minimum <= maximum <= 1.0 + 1e-9
    # The mean boundary weight fraction over the whole subspace must lie
    # within the extremal range achievable by a single vector in it.
    assert minimum - 1e-9 <= analysis.kernel_boundary_weight_fraction <= maximum + 1e-9


def test_kernel_spans_both_boundary_and_interior_localized_vectors(analysis: RigidityAnalysis) -> None:
    # For this lattice, the kernel is not purely a boundary artifact:
    # there exists a unit vector inside it supported almost entirely on
    # interior nodes (min close to 0), and one almost entirely on
    # boundary nodes (max close to 1).
    minimum, maximum = analysis.kernel_boundary_localization_range
    assert minimum < 0.1
    assert maximum > 0.9


# --- per-mode fields ---


def test_modes_have_well_formed_fields(analysis: RigidityAnalysis, matrix: DiamondMatrix) -> None:
    n_nodes = len(matrix.reference_positions)
    assert len(analysis.modes) == analysis.null_space_dimension
    for mode in analysis.modes:
        assert isinstance(mode, Mode)
        assert mode.relative_eigenvalue <= _NULL_TOLERANCE
        assert 0.0 < mode.participation_ratio <= 1.0 + 1e-9
        assert 0.0 <= mode.boundary_energy_fraction <= 1.0 + 1e-9
        assert 0.0 <= mode.rigid_translation_overlap <= 1.0 + 1e-9
        assert 0.0 <= mode.rigid_rotation_overlap <= 1.0 + 1e-9
        assert mode.rigid_translation_overlap + mode.rigid_rotation_overlap <= 1.0 + 1e-6
        assert mode.displacement.shape == (n_nodes, 3)


def test_modes_table_round_trips_through_csv(analysis: RigidityAnalysis, tmp_path) -> None:
    csv_path = tmp_path / "modes.csv"
    write_modes_table_csv(analysis.modes, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.DictReader(handle))

    expected = modes_to_table(analysis.modes)
    assert len(read_back) == len(expected)
    for read_row, expected_row in zip(read_back[::10], expected[::10]):
        assert float(read_row["eigenvalue"]) == pytest.approx(expected_row["eigenvalue"], abs=1e-15)
        assert float(read_row["participation_ratio"]) == pytest.approx(
            expected_row["participation_ratio"]
        )
