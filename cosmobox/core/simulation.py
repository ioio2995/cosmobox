from __future__ import annotations

from .config import SimulationConfig
from .matrix import DiamondMatrix
from .mechanics import MechanicsEngine
from cosmobox.physics.metrics import MetricsRecorder
from cosmobox.physics.particle import TetrahedralParticle
from cosmobox.visualization.animation import AnimationRenderer


class Simulation:
    def __init__(self, config: SimulationConfig, matrix: DiamondMatrix, particles: list[TetrahedralParticle]):
        self.config = config
        self.matrix = matrix
        self.particles = particles
        self.mechanics = MechanicsEngine()
        self.metrics = MetricsRecorder()
        self.renderer = AnimationRenderer(config.render) if config.render.enabled else None

    def run(self) -> None:
        frame_stride = max(1, self.config.steps // max(self.config.render.frames - 1, 1))
        geometry_energy = 0.0

        for step in range(self.config.steps + 1):
            self.matrix.clear_inputs()
            for particle in self.particles:
                particle.inject(self.matrix)

            self.metrics.capture(self.matrix, step, geometry_energy)
            if self.renderer and (step % frame_stride == 0 or step == self.config.steps):
                self.renderer.capture(self.matrix, step)

            if step == self.config.steps:
                break

            self.mechanics.update_factors(self.matrix, self.config.particles)
            geometry_energy = self.mechanics.solve(self.matrix)
