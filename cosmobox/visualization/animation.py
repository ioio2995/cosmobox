from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import numpy as np

from cosmobox.core.config import RenderConfig
from cosmobox.core.matrix import DiamondMatrix


class AnimationRenderer:
    def __init__(self, cfg: RenderConfig):
        self.cfg = cfg
        self.snapshots: list[dict] = []

    def capture(self, matrix: DiamondMatrix, step: int) -> None:
        self.snapshots.append(
            {
                "step": step,
                "positions": matrix.positions.copy(),
                "f": matrix.factors().copy(),
                "activity": matrix.activities().copy(),
                "flux": matrix.fluxes().copy(),
            }
        )

    def save(self, matrix: DiamondMatrix, output: Path) -> None:
        if not self.snapshots:
            return

        fig = plt.figure(figsize=(9, 8))
        ax = fig.add_subplot(111, projection="3d")
        ax.set_box_aspect((1, 1, 1))
        limit = float(np.max(np.abs(matrix.reference_positions))) * 1.15
        ax.set(xlim=(-limit, limit), ylim=(-limit, limit), zlim=(-limit, limit))

        first = self.snapshots[0]["positions"]
        segments = np.stack((first[matrix.edges[:, 0]], first[matrix.edges[:, 1]]), axis=1)
        collection = Line3DCollection(segments, alpha=0.65)
        ax.add_collection3d(collection)
        status = ax.text2D(0.02, 0.96, "", transform=ax.transAxes)
        cmap = plt.get_cmap("viridis")

        def update(index: int):
            snapshot = self.snapshots[index]
            positions = matrix.reference_positions + self.cfg.visual_amplification * (
                snapshot["positions"] - matrix.reference_positions
            )
            segments = np.stack((positions[matrix.edges[:, 0]], positions[matrix.edges[:, 1]]), axis=1)
            collection.set_segments(segments)

            contraction = np.clip(1.0 - snapshot["f"], 0.0, None)
            normalized = contraction / max(float(contraction.max()), 1e-12)
            colors = cmap(normalized)
            active = snapshot["activity"] > 0
            colors[~active, 3] = 0.18 + 0.5 * normalized[~active]
            colors[active, 3] = 1.0
            colors[active, :3] = np.where(
                (snapshot["flux"][active] >= 0)[:, None],
                np.array([0.95, 0.35, 0.12]),
                np.array([0.15, 0.55, 0.95]),
            )
            collection.set_color(colors)
            collection.set_linewidth(0.25 + 3.5 * normalized + 1.4 * active.astype(float))

            displacement = np.linalg.norm(snapshot["positions"] - matrix.reference_positions, axis=1)
            status.set_text(
                f"cycle {snapshot['step']}\n"
                f"contraction max. : {contraction.max():.4f}\n"
                f"déplacement réel max. : {displacement.max():.4f}"
            )
            ax.set_title("Cosmobox — réseau diamant déformable")
            if self.cfg.rotate:
                ax.view_init(elev=24, azim=35 + 360 * index / max(len(self.snapshots), 1))
            return collection, status

        animation = FuncAnimation(fig, update, frames=len(self.snapshots), interval=1000 / max(self.cfg.fps, 1))
        output.parent.mkdir(parents=True, exist_ok=True)
        if self.cfg.format == "gif":
            animation.save(output, writer=PillowWriter(fps=self.cfg.fps))
        else:
            animation.save(output, writer=FFMpegWriter(fps=self.cfg.fps, bitrate=2400))
        plt.close(fig)
