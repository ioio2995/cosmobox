"""Minimal adapter between the existing Level0/Level1 spectral
infrastructure and the accepted Level2 primitives (metrics.py, profiles.py).

Lot L2-D2-LEVEL2-ADAPTER. Every function here is plumbing between already-
validated, already-accepted APIs: Level0's full-spectrum report and
degeneracy grouping (cosmobox.level0.reports, cosmobox.level0.degeneracy),
Level1's per-pair canonical multiplet expectations
(cosmobox.level1.restricted, cosmobox.level1.local_observables), and
Level2's own D1 primitives (cosmobox.level2.metrics, cosmobox.level2.profiles).
No new scientific convention, metric, or numerical tolerance is introduced.
No real Level2 geometry is diagonalized or consumed here -- this module only
defines how to route already-computed data through already-accepted
functions.

UNIT = complete spectral multiplet over the full spectrum
(spectral-regime-design.md SS2): a case with even a single incomplete
(partial_subspace) spectral group has no defined Level2 representation.
extract_complete_multiplets rejects such a case as a whole -- it never
filters, exploratorily averages, or renormalizes q over a reduced group set.
exploratory_partial_subspace_mean is never called anywhere in this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level0.lattice import Lattice
from cosmobox.level0.reports import Level0Report
from cosmobox.level1.local_observables import (
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, SpectralGroupState, extract_group_state
from cosmobox.level2 import metrics, profiles
from cosmobox.level2.metrics import Available, RhoQQEntry


class PartialSubspaceCaseRejected(ValueError):
    """Raised by extract_complete_multiplets when a case's spectrum
    contains at least one partial_subspace group. Per UNIT = complete
    spectral multiplet over the full spectrum, such a case has no defined
    Level2 representation: it is rejected as a whole, never filtered down
    to its complete groups, never exploratorily averaged, and never used
    to renormalize q over a reduced set."""


# ---------------------------------------------------------------------------
# 1. Extraction of complete multiplets (all-or-nothing per case)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompleteMultiplet:
    """One complete spectral group (Level0's own grouping) together with
    its extracted, orthonormal-basis state. Public and directly
    constructible: its own invariant (a complete_multiplet state whose
    multiplicity matches the group's) is enforced here, not only by
    extract_complete_multiplets's construction path."""

    group: SpectralLevelGroup
    state: SpectralGroupState

    def __post_init__(self) -> None:
        if not self.state.is_complete:
            raise ValueError(f"CompleteMultiplet requires a {COMPLETE_MULTIPLET!r} state, got {self.state.status!r}")
        if self.state.multiplicity != self.group.multiplicity_observed:
            raise ValueError(
                f"state.multiplicity ({self.state.multiplicity}) does not match "
                f"group.multiplicity_observed ({self.group.multiplicity_observed})"
            )


def extract_complete_multiplets(report: Level0Report, eigenvectors: np.ndarray) -> tuple[CompleteMultiplet, ...]:
    """Every spectral group of `report`'s computed spectrum, in spectral
    order, each with its extracted SpectralGroupState.

    Raises PartialSubspaceCaseRejected if any group is partial_subspace
    (SpectralLevelGroup.lower_bound_only), and ValueError if the observed
    multiplicities do not sum to exactly report.dimension (the case does
    not cover the full spectrum) -- both reject the whole case, never a
    silent partial result.
    """
    if report.spectrum.degeneracy is None:
        raise ValueError("report.spectrum.degeneracy is None -- no computed spectrum to extract multiplets from")

    groups = report.spectrum.degeneracy.groups
    if any(group.lower_bound_only for group in groups):
        raise PartialSubspaceCaseRejected(
            "at least one spectral group is partial_subspace (lower_bound_only=True); the whole "
            "Level2 case is rejected, per UNIT = complete spectral multiplet over the full spectrum"
        )

    total_multiplicity = sum(group.multiplicity_observed for group in groups)
    if total_multiplicity != report.dimension:
        raise ValueError(
            f"observed multiplicities sum to {total_multiplicity}, expected exactly "
            f"report.dimension={report.dimension} -- the case does not cover the full spectrum"
        )

    return tuple(CompleteMultiplet(group=group, state=extract_group_state(eigenvectors, group)) for group in groups)


# ---------------------------------------------------------------------------
# 5. Per-case local operators (built once, reused across every multiplet)
# ---------------------------------------------------------------------------


def build_case_operators(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys,
    key_index: dict[int, int],
) -> tuple[tuple[sp.spmatrix, ...], tuple[dict[str, sp.spmatrix], ...]]:
    """Q_i and {T_i^x, T_i^y, T_i^z} for every site of `lattice`, in
    lattice.nodes order, built exactly once. These operators are
    independent of any spectral group -- callers must build them once per
    case with this function and reuse the returned tuples across every
    multiplet; never rebuild them inside a per-group loop."""
    charge_operators = tuple(
        build_local_charge_operator(lattice, n_flavors, spin, keys, key_index, node) for node in lattice.nodes
    )
    flavor_generators = tuple(
        build_local_flavor_generators(lattice, n_flavors, spin, keys, key_index, node) for node in lattice.nodes
    )
    return charge_operators, flavor_generators


# ---------------------------------------------------------------------------
# 2. C_TT_conn assembly
# ---------------------------------------------------------------------------


def assemble_c_tt_conn(
    flavor_generators: Sequence[Mapping[str, sp.spmatrix]],
    group_state: SpectralGroupState,
) -> np.ndarray:
    """Complete N x N C_TT_conn matrix for one complete multiplet
    (i == j included), built exclusively via
    flavor_correlator_connected_group -- one call per ordered pair, no
    symmetry reconstruction, no pair selection. Directly compatible with
    cosmobox.level2.metrics.m_tt / r_eff.

    Requires group_state.status == "complete_multiplet": rejects a
    partial_subspace state explicitly, rather than letting
    flavor_correlator_connected_group silently dispatch into
    exploratory_partial_subspace_mean.
    """
    if group_state.status != COMPLETE_MULTIPLET:
        raise ValueError(
            f"assemble_c_tt_conn requires a {COMPLETE_MULTIPLET!r} group_state, got {group_state.status!r}"
        )
    n = len(flavor_generators)
    matrix = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            moment = flavor_correlator_connected_group(flavor_generators[i], flavor_generators[j], group_state)
            matrix[i, j] = moment.value
    return matrix


# ---------------------------------------------------------------------------
# 3. rho_QQ assembly
# ---------------------------------------------------------------------------


def assemble_rho_qq(
    charge_operators: Sequence[sp.spmatrix],
    group_state: SpectralGroupState,
) -> dict[tuple[int, int], RhoQQEntry]:
    """rho_QQ(i,j) for every ordered pair i != j of one complete multiplet,
    built exclusively via charge_correlator_connected_group (for C_QQ(i,j)
    and the diagonal C_QQ(i,i)/C_QQ(j,j) variances) and
    normalized_charge_correlator. value/null_reason are propagated exactly
    as returned -- never imputed, never replaced by zero.

    Requires group_state.status == "complete_multiplet": rejects a
    partial_subspace state explicitly, rather than letting
    charge_correlator_connected_group silently dispatch into
    exploratory_partial_subspace_mean.
    """
    if group_state.status != COMPLETE_MULTIPLET:
        raise ValueError(
            f"assemble_rho_qq requires a {COMPLETE_MULTIPLET!r} group_state, got {group_state.status!r}"
        )
    n = len(charge_operators)
    variances = [
        charge_correlator_connected_group(charge_operators[i], charge_operators[i], group_state).value
        for i in range(n)
    ]

    pairs: dict[tuple[int, int], RhoQQEntry] = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            connected_ij = charge_correlator_connected_group(charge_operators[i], charge_operators[j], group_state)
            normalized = normalized_charge_correlator(connected_ij.value, variances[i], variances[j])
            pairs[(i, j)] = RhoQQEntry(value=normalized.value, null_reason=normalized.null_reason)
    return pairs


# ---------------------------------------------------------------------------
# 4. Minimal per-case orchestration into D1 primitives
# ---------------------------------------------------------------------------


def spectrum_energy_bounds(report: Level0Report) -> tuple[float, float]:
    """(E_min, E_max) over the full computed spectrum -- the smallest and
    largest eigenvalue actually observed, i.e. the epsilon normalization
    anchor (spectral-regime-design.md SS4.1)."""
    eigenpairs = report.spectrum.eigenpairs
    if not eigenpairs:
        raise ValueError("report.spectrum has no eigenpairs to derive E_min/E_max from")
    energies = [pair.eigenvalue for pair in eigenpairs]
    return min(energies), max(energies)


@dataclass(frozen=True, slots=True)
class MultipletProfileEntry:
    """Per-multiplet D1 inputs/outputs, in spectral order: the raw
    (energy, multiplicity) Level0 already provides, the Level2 spectral
    coordinates derived from them, and the four D1 metrics computed from
    the assembled C_TT_conn matrix and rho_QQ pairs. No regime
    aggregation, no contrast, no C_X_23/D_X_23, no inter-S comparison --
    those remain the next lot's orchestration, on top of this per-case
    result."""

    energy: float
    multiplicity: int
    epsilon: float
    q_start: float
    q_end: float
    q_midpoint: float
    m_tt: float
    r_eff: Available
    a_qq: float
    m_qq: Available


def build_case_multiplet_profile(
    report: Level0Report,
    eigenvectors: np.ndarray,
    charge_operators: Sequence[sp.spmatrix],
    flavor_generators: Sequence[Mapping[str, sp.spmatrix]],
) -> tuple[MultipletProfileEntry, ...]:
    """One MultipletProfileEntry per complete spectral group of `report`,
    in spectral order. Rejects the whole case (via
    extract_complete_multiplets) if any group is partial_subspace or if
    the observed multiplicities do not cover report.dimension exactly.
    `charge_operators`/`flavor_generators` must already be built once for
    this case (build_case_operators) and are reused, unmodified, across
    every multiplet."""
    if len(charge_operators) != len(flavor_generators):
        raise ValueError(
            f"charge_operators has {len(charge_operators)} entries but flavor_generators has "
            f"{len(flavor_generators)}; both must describe the same N sites"
        )

    multiplets = extract_complete_multiplets(report, eigenvectors)
    e_min, e_max = spectrum_energy_bounds(report)
    n = len(charge_operators)

    entries = []
    for multiplet in multiplets:
        group = multiplet.group
        state = multiplet.state
        interval = profiles.spectral_interval(group.start_index, group.multiplicity_observed, report.dimension)
        c_tt_conn = assemble_c_tt_conn(flavor_generators, state)
        rho_qq_pairs = assemble_rho_qq(charge_operators, state)

        entries.append(
            MultipletProfileEntry(
                energy=group.representative_energy,
                multiplicity=group.multiplicity_observed,
                epsilon=profiles.epsilon(group.representative_energy, e_min, e_max),
                q_start=interval.start,
                q_end=interval.end,
                q_midpoint=interval.q_mid,
                m_tt=metrics.m_tt(c_tt_conn),
                r_eff=metrics.r_eff(c_tt_conn),
                a_qq=metrics.a_qq(rho_qq_pairs, n),
                m_qq=metrics.m_qq(rho_qq_pairs, n),
            )
        )
    return tuple(entries)
