from __future__ import annotations

import argparse
import json
from pathlib import Path

from cosmobox.core.config import SimulationConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.core.simulation import Simulation
from cosmobox.physics.particle import build_particles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cosmobox — réseau diamant déformable")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--animate", action="store_true")
    parser.add_argument("--rotate", action="store_true")
    parser.add_argument("--visual-amplification", type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = SimulationConfig.from_yaml(args.config)
    if args.animate:
        config.render.enabled = True
    if args.rotate:
        config.render.rotate = True
    if args.visual_amplification is not None:
        config.render.visual_amplification = args.visual_amplification

    matrix = DiamondMatrix(config.matrix)
    particles = build_particles(matrix, config.particles)
    simulation = Simulation(config, matrix, particles)
    simulation.run()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    simulation.metrics.write_csv(config.output_dir / "history.csv")

    if simulation.renderer:
        suffix = config.render.format
        simulation.renderer.save(matrix, config.output_dir / f"cosmobox.{suffix}")

    summary = {
        "nodes": len(matrix.positions),
        "edges": len(matrix.edges),
        "c": matrix.c,
        "particles": len(particles),
        **simulation.metrics.rows[-1],
    }
    (config.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
