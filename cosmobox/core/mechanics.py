from __future__ import annotations

import numpy as np

from .matrix import DiamondMatrix
from .config import ParticleConfig


class MechanicsEngine:
    def update_factors(self, matrix: DiamondMatrix, cfg: ParticleConfig) -> None:
        factors = matrix.factors()
        activity = matrix.activities()

        compat = np.zeros(len(matrix.edges), dtype=float)
        counts = np.zeros(len(matrix.edges), dtype=float)
        for edge_ids in matrix.node_edges:
            if len(edge_ids) < 2:
                continue
            ids = np.asarray(edge_ids, dtype=int)
            local_mean = float(factors[ids].mean())
            compat[ids] += local_mean - factors[ids]
            counts[ids] += 1.0

        compat = np.divide(compat, counts, out=np.zeros_like(compat), where=counts > 0)
        factors += -cfg.beta * activity + cfg.compatibility * compat + cfg.relaxation * (1.0 - factors)
        factors = np.clip(factors, cfg.min_factor, 1.02)

        for i, factor in enumerate(factors):
            matrix.edges_state[i].deformation_factor = float(factor)

    def solve(self, matrix: DiamondMatrix) -> float:
        target = matrix.base_lengths * matrix.factors()
        energy = 0.0

        for _ in range(matrix.config.geometry_substeps):
            p0 = matrix.positions[matrix.edges[:, 0]]
            p1 = matrix.positions[matrix.edges[:, 1]]
            delta = p1 - p0
            lengths = np.linalg.norm(delta, axis=1)
            safe = np.maximum(lengths, 1e-12)
            direction = delta / safe[:, None]
            extension = lengths - target

            stiffness = np.array([e.stiffness for e in matrix.edges_state], dtype=float)
            edge_forces = stiffness[:, None] * extension[:, None] * direction

            forces = np.zeros_like(matrix.positions)
            np.add.at(forces, matrix.edges[:, 0], edge_forces)
            np.add.at(forces, matrix.edges[:, 1], -edge_forces)

            acceleration = forces / matrix.config.node_mass - matrix.config.damping * matrix.velocities
            matrix.velocities += matrix.config.dt * acceleration
            matrix.velocities -= matrix.velocities.mean(axis=0)
            matrix.positions += matrix.config.dt * matrix.velocities
            matrix.positions -= matrix.positions.mean(axis=0) - matrix.reference_positions.mean(axis=0)

            energy = float(0.5 * np.sum(stiffness * extension**2))

        return energy
