"""Conservation analysis over a simulation run.

Deliberately separate from cosmobox.simulation.engine.StepDiagnostics:
the relative energy error `(E(t) - E(0)) / E(0)` is undefined for the
control-zero scenario (E(0) = 0), so it must not be baked into the
per-step diagnostics the engine always produces. It only makes sense
once a reference state (e.g. right after an injection) is chosen by the
caller.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.simulation.engine import LatticeState, StepDiagnostics


@dataclass(slots=True)
class ConservationReport:
    times: np.ndarray
    energy_absolute_error: np.ndarray
    energy_relative_error: np.ndarray | None
    momentum_drift: np.ndarray

    @property
    def max_energy_relative_error(self) -> float | None:
        if self.energy_relative_error is None:
            return None
        return float(np.max(np.abs(self.energy_relative_error)))

    @property
    def max_momentum_drift(self) -> float:
        return float(np.max(self.momentum_drift))


def analyze_conservation(
    history: list[tuple[LatticeState, StepDiagnostics]]
) -> ConservationReport:
    times = np.array([diag.time for _, diag in history])
    energies = np.array([diag.total_energy for _, diag in history])
    momenta = np.array([diag.momentum for _, diag in history])

    reference_energy = energies[0]
    reference_momentum = momenta[0]

    absolute_error = energies - reference_energy
    relative_error = None
    if reference_energy != 0.0:
        relative_error = absolute_error / reference_energy

    momentum_drift = np.linalg.norm(momenta - reference_momentum, axis=1)

    return ConservationReport(
        times=times,
        energy_absolute_error=absolute_error,
        energy_relative_error=relative_error,
        momentum_drift=momentum_drift,
    )
