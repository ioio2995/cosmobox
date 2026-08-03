from cosmobox.core.config import MatrixConfig, ParticleConfig, RenderConfig, SimulationConfig
from cosmobox.core.matrix import DiamondMatrix
from cosmobox.core.simulation import Simulation
from cosmobox.physics.particle import build_particles


def test_smoke():
    config = SimulationConfig(
        steps=5,
        matrix=MatrixConfig(radius=6.0, cell_range=5),
        particles=ParticleConfig(count=8),
        render=RenderConfig(enabled=False),
    )
    matrix = DiamondMatrix(config.matrix)
    particles = build_particles(matrix, config.particles)
    simulation = Simulation(config, matrix, particles)
    simulation.run()
    assert len(simulation.metrics.rows) == 6
    assert matrix.c > 0
    assert len(matrix.edges) > 0
