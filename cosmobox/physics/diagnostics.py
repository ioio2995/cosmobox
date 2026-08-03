"""Minimal energy and momentum measurements for the conservative engine.

Scope limited to what the free-boundary control-zero step needs
(docs/05_decisions/0001-moteur-conservatif-minimal.md, implementation
order steps 1-2): kinetic energy and total momentum. Front detection,
anisotropy and boundary-specific energy accounting are added in later
steps, not here.
"""
from __future__ import annotations

import numpy as np


def kinetic_energy(velocities: np.ndarray, node_mass: float) -> float:
    return float(0.5 * node_mass * np.sum(velocities**2))


def total_momentum(velocities: np.ndarray, node_mass: float) -> np.ndarray:
    return node_mass * velocities.sum(axis=0)
