from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import MatrixConfig

TETRA_DIRS = np.array(
    [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]],
    dtype=int,
)

FCC_BASIS = np.array(
    [[0, 0, 0], [0, 2, 2], [2, 0, 2], [2, 2, 0]],
    dtype=int,
)


@dataclass(slots=True)
class EdgeState:
    node_a: int
    node_b: int
    base_length: float
    deformation_factor: float
    stiffness: float
    external_drive: float = 0.0
    signed_flux: float = 0.0


class DiamondMatrix:
    def __init__(self, config: MatrixConfig):
        self.config = config
        self.reference_positions, self.edges = self._build_lattice(
            config.radius, config.cell_range
        )
        self.positions = self.reference_positions.copy()
        self.velocities = np.zeros_like(self.positions)

        vectors = self.reference_positions[self.edges[:, 1]] - self.reference_positions[self.edges[:, 0]]
        self.base_lengths = np.linalg.norm(vectors, axis=1)
        self.edge_units = vectors / self.base_lengths[:, None]
        self.c = float(self.base_lengths.mean())

        self.node_edges: list[list[int]] = [[] for _ in range(len(self.positions))]
        self.node_neighbors: list[list[int]] = [[] for _ in range(len(self.positions))]
        for edge_id, (u, v) in enumerate(self.edges):
            self.node_edges[u].append(edge_id)
            self.node_edges[v].append(edge_id)
            self.node_neighbors[u].append(v)
            self.node_neighbors[v].append(u)

        self.degrees = np.array([len(x) for x in self.node_neighbors], dtype=int)
        self.edges_state = [
            EdgeState(int(u), int(v), float(self.base_lengths[i]), 1.0, config.spring_k)
            for i, (u, v) in enumerate(self.edges)
        ]

    @staticmethod
    def _build_lattice(radius: float, cell_range: int) -> tuple[np.ndarray, np.ndarray]:
        points_set: set[tuple[int, int, int]] = set()
        sublattice: dict[tuple[int, int, int], int] = {}
        for ix in range(-cell_range, cell_range + 1):
            for iy in range(-cell_range, cell_range + 1):
                for iz in range(-cell_range, cell_range + 1):
                    origin = np.array([4 * ix, 4 * iy, 4 * iz], dtype=int)
                    for basis in FCC_BASIS:
                        a = tuple(origin + basis)
                        b = tuple(origin + basis + np.array([1, 1, 1]))
                        points_set.update((a, b))
                        sublattice[a] = 0
                        sublattice[b] = 1

        all_points = np.array(sorted(points_set), dtype=int)
        inside = np.linalg.norm(all_points.astype(float), axis=1) <= radius
        points_int = all_points[inside]
        point_to_index = {tuple(p): i for i, p in enumerate(points_int)}

        edges_set: set[tuple[int, int]] = set()
        for i, point in enumerate(points_int):
            directions = TETRA_DIRS if sublattice[tuple(point)] == 0 else -TETRA_DIRS
            for direction in directions:
                j = point_to_index.get(tuple(point + direction))
                if j is not None:
                    edges_set.add(tuple(sorted((i, j))))

        return points_int.astype(float), np.array(sorted(edges_set), dtype=int)

    def clear_inputs(self) -> None:
        for edge in self.edges_state:
            edge.external_drive = 0.0
            edge.signed_flux = 0.0

    def inject_flux(self, edge_id: int, signed_energy: float) -> None:
        edge = self.edges_state[edge_id]
        edge.signed_flux += float(signed_energy)
        edge.external_drive += abs(float(signed_energy))

    def factors(self) -> np.ndarray:
        return np.array([e.deformation_factor for e in self.edges_state], dtype=float)

    def activities(self) -> np.ndarray:
        return np.array([e.external_drive for e in self.edges_state], dtype=float)

    def fluxes(self) -> np.ndarray:
        return np.array([e.signed_flux for e in self.edges_state], dtype=float)
