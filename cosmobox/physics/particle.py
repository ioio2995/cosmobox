from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.core.config import ParticleConfig
from cosmobox.core.matrix import DiamondMatrix


@dataclass(slots=True)
class ParticleState:
    center_node: int
    energy: float
    chirality: int
    phase: int
    active: bool = True


class TetrahedralParticle:
    def __init__(self, state: ParticleState, cycle_edges: np.ndarray):
        self.state = state
        self.cycle_edges = np.asarray(cycle_edges, dtype=int)

    def inject(self, matrix: DiamondMatrix) -> None:
        if not self.state.active:
            return
        edge_id = int(self.cycle_edges[self.state.phase % 4])
        matrix.inject_flux(edge_id, self.state.energy * self.state.chirality)
        self.state.phase = (self.state.phase + self.state.chirality) % 4


def build_particles(matrix: DiamondMatrix, cfg: ParticleConfig) -> list[TetrahedralParticle]:
    if cfg.count < 2 or cfg.count % 2:
        raise ValueError("Le nombre de particules doit être pair et >= 2")

    interior = np.flatnonzero(matrix.degrees == 4)
    if len(interior) < cfg.count:
        raise ValueError("Pas assez de nœuds intérieurs de degré 4")

    radii = np.linalg.norm(matrix.reference_positions, axis=1)
    active_nodes = interior[np.argsort(radii[interior])][: cfg.count]
    particles: list[TetrahedralParticle] = []

    for index, node in enumerate(active_nodes):
        edge_ids = np.asarray(matrix.node_edges[int(node)], dtype=int)
        directions = []
        for edge_id in edge_ids:
            u, v = matrix.edges[edge_id]
            other = v if u == node else u
            directions.append(tuple((matrix.reference_positions[other] - matrix.reference_positions[node]).astype(int)))
        order = sorted(range(4), key=lambda i: directions[i])

        chirality = 1
        if cfg.chirality_mode == "opposed" and index % 2:
            chirality = -1
        elif cfg.chirality_mode not in {"aligned", "opposed"}:
            raise ValueError("chirality_mode doit valoir aligned ou opposed")

        particles.append(
            TetrahedralParticle(
                ParticleState(int(node), cfg.energy, chirality, index % 4),
                edge_ids[order],
            )
        )

    return particles
