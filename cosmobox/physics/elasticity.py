"""Harmonic bond energy and force law for the minimal lattice model.

Implements exactly `E_ij = 1/2 k (L_ij - c)^2` from
docs/research/0001-modele-minimal-reseau-au-repos.md §5.1 — a single
uniform rest length and stiffness, no deformation factor, no signed flux,
no damping. This module has no notion of a particle or of the lattice's
topology beyond the edge list it is handed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class ElasticityConfig:
    rest_length: float
    stiffness: float


def bond_vectors(positions: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return positions[edges[:, 1]] - positions[edges[:, 0]]


def bond_lengths(positions: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.linalg.norm(bond_vectors(positions, edges), axis=1)


def bond_energy(positions: np.ndarray, edges: np.ndarray, config: ElasticityConfig) -> float:
    extension = bond_lengths(positions, edges) - config.rest_length
    return float(0.5 * config.stiffness * np.sum(extension**2))


def bond_forces(positions: np.ndarray, edges: np.ndarray, config: ElasticityConfig) -> np.ndarray:
    """Per-node force array (N, 3), the negative gradient of `bond_energy`."""
    vectors = bond_vectors(positions, edges)
    lengths = np.linalg.norm(vectors, axis=1)
    safe_lengths = np.maximum(lengths, 1e-12)
    directions = vectors / safe_lengths[:, None]
    extension = lengths - config.rest_length
    edge_forces = config.stiffness * extension[:, None] * directions

    forces = np.zeros_like(positions)
    np.add.at(forces, edges[:, 0], edge_forces)
    np.add.at(forces, edges[:, 1], -edge_forces)
    return forces
