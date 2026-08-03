"""Static affine shear energy test for EXP-0001 step 7B-1 (no dynamics,
no relaxation — this is the first, purely static sub-step, to run
before step 7B-2/7B-3).

Applies a small affine shear `x' = x + gamma * y` to every node
(unrelaxed: no minimization, no engine run) and measures the resulting
unrelaxed bond energy as a function of `gamma`, fit to
`E(gamma) = a2*gamma^2 + a3*gamma^3 + a4*gamma^4` (no constant/linear
term — `E(0) = 0` exactly since `gamma=0` is the undisplaced lattice).
The question this answers: is `a2` (the linear-elasticity shear
stiffness) strictly positive, or does it vanish because the shear
direction lies entirely inside the linearized kernel characterized in
cosmobox.physics.rigidity?

Mathematical note on `project_out_kernel`: for a symmetric PSD `K`,
writing any direction `u = u_kernel + u_perp` (kernel component plus its
orthogonal complement), `u.T @ K @ u == u_perp.T @ K @ u_perp` exactly,
because `K @ u_kernel = 0` and `u_kernel` is orthogonal to
`Im(K) = ker(K)^perp` (K symmetric). So the *quadratic* coefficient
`a2` is provably identical whether it is measured from the raw shear
direction or its kernel-projected version — projecting out the kernel
does not change `a2`, it only removes the part of the raw direction
that contributes nothing to the quadratic energy. Both are computed
here so that fact is verified numerically, not just asserted; the
projected direction remains useful for step 7B-3 (its magnitude/shape
differs from the raw one, which matters for anything beyond `a2`, e.g.
comparing displacement magnitudes at fixed physical energy).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.physics.elasticity import ElasticityConfig, bond_energy


def affine_shear_displacement(reference_positions: np.ndarray, from_axis: int, to_axis: int) -> np.ndarray:
    """Flat `(3N,)` unit-gamma shear generator: `x'[to_axis] =
    x[to_axis] + gamma * x[from_axis]` (e.g. `x' = x + gamma*y` for
    `from_axis=1, to_axis=0`), to be scaled by `gamma` and reshaped by
    the caller (see `shear_energy_curve`).
    """
    displacement = np.zeros_like(reference_positions)
    displacement[:, to_axis] = reference_positions[:, from_axis]
    return displacement.ravel()


def exact_quadratic_coefficient(K: np.ndarray, direction: np.ndarray) -> float:
    """The exact linearized quadratic-energy coefficient
    `0.5 * direction @ K @ direction` (K from
    cosmobox.physics.rigidity.stiffness_matrix) — not an approximation,
    a direct evaluation of the same quadratic form the nonlinear
    `bond_energy` reduces to as `gamma -> 0`. Used to check that a
    `ShearEnergyCurve.quadratic_coefficient` fit over a finite gamma
    range is not biased by the cubic/quartic terms.
    """
    return float(0.5 * direction @ K @ direction)


def project_out_kernel(direction: np.ndarray, projector: np.ndarray) -> np.ndarray:
    """`direction` with its component inside the linearized kernel
    (`projector` from cosmobox.physics.rigidity.kernel_projector)
    removed.
    """
    return direction - projector @ direction


@dataclass(slots=True)
class ShearEnergyCurve:
    gammas: np.ndarray
    energies: np.ndarray
    quadratic_coefficient: float
    cubic_coefficient: float
    quartic_coefficient: float


def shear_energy_curve(
    reference_positions: np.ndarray,
    edges: np.ndarray,
    elasticity: ElasticityConfig,
    direction: np.ndarray,
    gammas: np.ndarray,
) -> ShearEnergyCurve:
    """Unrelaxed elastic energy `E(gamma) = bond_energy(reference_positions
    + gamma * direction, ...)` for each `gamma`, fit to
    `a2*gamma^2 + a3*gamma^3 + a4*gamma^4`. `direction` is a flat
    `(3N,)` displacement generator (e.g. from
    `affine_shear_displacement`, raw or kernel-projected) — the caller
    decides which one to test.
    """
    n_nodes = len(reference_positions)
    reshaped_direction = direction.reshape(n_nodes, 3)
    energies = np.array(
        [
            bond_energy(reference_positions + gamma * reshaped_direction, edges, elasticity)
            for gamma in gammas
        ]
    )
    design = np.column_stack([gammas**2, gammas**3, gammas**4])
    coefficients, *_ = np.linalg.lstsq(design, energies, rcond=None)
    a2, a3, a4 = coefficients
    return ShearEnergyCurve(
        gammas=gammas,
        energies=energies,
        quadratic_coefficient=float(a2),
        cubic_coefficient=float(a3),
        quartic_coefficient=float(a4),
    )
