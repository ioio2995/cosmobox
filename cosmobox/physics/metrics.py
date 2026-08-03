from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from cosmobox.core.matrix import DiamondMatrix


class MetricsRecorder:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def capture(self, matrix: DiamondMatrix, step: int, geometry_energy: float) -> None:
        factors = matrix.factors()
        flux = matrix.fluxes()
        activity = matrix.activities()
        displacement = np.linalg.norm(matrix.positions - matrix.reference_positions, axis=1)
        resultant = np.sum(flux[:, None] * matrix.edge_units, axis=0)

        self.rows.append(
            {
                "step": step,
                "signed_flux_total": float(flux.sum()),
                "activity_total": float(activity.sum()),
                "hidden_activity": float(activity.sum() - abs(flux.sum())),
                "vector_resultant_norm": float(np.linalg.norm(resultant)),
                "factor_energy": float(0.5 * np.sum((1.0 - factors) ** 2)),
                "geometry_energy": float(geometry_energy),
                "mean_f": float(factors.mean()),
                "min_f": float(factors.min()),
                "max_node_displacement": float(displacement.max()),
                "mean_node_displacement": float(displacement.mean()),
            }
        )

    def write_csv(self, path: Path) -> None:
        if not self.rows:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.rows[0].keys())
            writer.writeheader()
            writer.writerows(self.rows)
