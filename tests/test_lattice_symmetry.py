"""Tests for cosmobox.core.symmetry, used by the step 6 orientation study
to validate lattice symmetries against the actual finite point set
rather than assume them from the infinite lattice's theoretical
point group.
"""
from __future__ import annotations

import numpy as np
import pytest

from cosmobox.core.config import MatrixConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.core.symmetry import lattice_symmetry_permutation, permutation_preserves_edges


@pytest.fixture(scope="module")
def matrix() -> DiamondMatrix:
    return DiamondMatrix(MatrixConfig(radius=5.5, cell_range=5))


def test_valid_symmetry_returns_a_permutation(matrix: DiamondMatrix) -> None:
    transform = np.diag([1.0, -1.0, -1.0])  # verified 180-degree rotation about x
    permutation = lattice_symmetry_permutation(matrix.reference_positions, transform)

    assert sorted(permutation.tolist()) == list(range(len(matrix.reference_positions)))
    # Direct definition check: transform @ ref[i] == ref[permutation[i]]
    for i in range(len(matrix.reference_positions)):
        assert np.allclose(transform @ matrix.reference_positions[i], matrix.reference_positions[permutation[i]])


def test_valid_symmetry_preserves_edges(matrix: DiamondMatrix) -> None:
    transform = np.diag([1.0, -1.0, -1.0])
    permutation = lattice_symmetry_permutation(matrix.reference_positions, transform)
    assert permutation_preserves_edges(matrix.edges, permutation)


def test_single_axis_sign_flip_is_not_a_symmetry_of_the_diamond_lattice(matrix: DiamondMatrix) -> None:
    # Unlike the double sign flips (180-degree rotations), a lone axis
    # flip does not preserve this two-sublattice structure.
    transform = np.diag([-1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="not an exact symmetry"):
        lattice_symmetry_permutation(matrix.reference_positions, transform)


def test_permutation_preserves_edges_detects_a_broken_permutation(matrix: DiamondMatrix) -> None:
    n = len(matrix.reference_positions)
    identity = np.arange(n)
    # Swapping two arbitrary, almost-certainly-non-equivalent nodes
    # should not preserve the edge set in general.
    broken = identity.copy()
    broken[0], broken[-1] = broken[-1], broken[0]
    assert not permutation_preserves_edges(matrix.edges, broken)


def test_rejects_wrong_shaped_transform(matrix: DiamondMatrix) -> None:
    with pytest.raises(ValueError, match="3x3"):
        lattice_symmetry_permutation(matrix.reference_positions, np.eye(2))


def test_rejects_non_orthogonal_transform(matrix: DiamondMatrix) -> None:
    non_orthogonal = np.diag([2.0, 1.0, 1.0])  # a scaling, not an isometry
    with pytest.raises(ValueError, match="orthogonal"):
        lattice_symmetry_permutation(matrix.reference_positions, non_orthogonal)


def test_rejects_a_transform_that_is_not_bijective_on_this_point_set() -> None:
    # A hand-built point set containing a duplicate site: both points
    # round to the same target under the identity transform, so the
    # induced mapping is not injective. Exercises the bijectivity check
    # directly rather than relying on finding a real degenerate case in
    # the full diamond lattice.
    duplicated_points = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    identity = np.eye(3)
    with pytest.raises(ValueError, match="bijection"):
        lattice_symmetry_permutation(duplicated_points, identity)
