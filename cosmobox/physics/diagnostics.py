"""Energy, momentum and center-of-mass measurements for the conservative
engine.

Scope grows with the EXP-0001 implementation order
(docs/05_decisions/0001-moteur-conservatif-minimal.md): steps 1-2 needed
kinetic energy and total momentum; step 3 (compensated injection, free
boundary) adds center-of-mass position/velocity. All functions assume
the uniform node mass used by ConservativeLatticeEngine — they are not
weighted per-node averages and would need to change if per-node mass is
ever introduced. Front detection, anisotropy and boundary-specific
energy accounting (fixed/absorbing) are still out of scope.
"""
from __future__ import annotations

import numpy as np


def kinetic_energy(velocities: np.ndarray, node_mass: float) -> float:
    return float(0.5 * node_mass * np.sum(velocities**2))


def total_momentum(velocities: np.ndarray, node_mass: float) -> np.ndarray:
    return node_mass * velocities.sum(axis=0)


def center_of_mass_position(positions: np.ndarray) -> np.ndarray:
    return positions.mean(axis=0)


def center_of_mass_velocity(velocities: np.ndarray) -> np.ndarray:
    return velocities.mean(axis=0)
