from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class MatrixConfig:
    radius: float = 8.2
    cell_range: int = 7
    spring_k: float = 5.0
    node_mass: float = 1.0
    damping: float = 1.2
    dt: float = 0.025
    geometry_substeps: int = 5


@dataclass(slots=True)
class ParticleConfig:
    count: int = 44
    energy: float = 1.0
    chirality_mode: str = "opposed"
    beta: float = 0.0055
    relaxation: float = 0.038
    compatibility: float = 0.11
    min_factor: float = 0.90


@dataclass(slots=True)
class RenderConfig:
    enabled: bool = False
    frames: int = 100
    fps: int = 20
    rotate: bool = False
    visual_amplification: float = 5.0
    format: str = "gif"


@dataclass(slots=True)
class SimulationConfig:
    steps: int = 500
    output_dir: Path = Path("output")
    matrix: MatrixConfig = field(default_factory=MatrixConfig)
    particles: ParticleConfig = field(default_factory=ParticleConfig)
    render: RenderConfig = field(default_factory=RenderConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "SimulationConfig":
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            steps=int(data.get("steps", 500)),
            output_dir=Path(data.get("output_dir", "output")),
            matrix=MatrixConfig(**data.get("matrix", {})),
            particles=ParticleConfig(**data.get("particles", {})),
            render=RenderConfig(**data.get("render", {})),
        )
