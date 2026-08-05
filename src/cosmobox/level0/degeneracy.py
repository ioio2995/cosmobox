"""Degeneracy-aware grouping of an already-computed spectrum.

analyze_spectral_degeneracies takes a sorted-ascending sequence of
eigenvalues (as already produced by reports.py's direct/dense/sparse
paths) and groups adjacent eigenvalues that agree within a scale-adjusted
tolerance into SpectralLevelGroup entries. It does not touch the
Hamiltonian, the basis, or any operator -- it is a pure post-processing
step on numbers already computed elsewhere.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_DEGENERACY_TOLERANCE = 1e-10


@dataclass(frozen=True, slots=True)
class SpectralLevelGroup:
    start_index: int
    end_index_exclusive: int
    representative_energy: float  # mean(eigenvalues[start:end])
    min_energy: float
    max_energy: float
    multiplicity_observed: int
    lower_bound_only: bool
    """True only for the last group when the diagonalization window ended
    exactly at this group's boundary and did not cover the full Hilbert
    space -- the group's true multiplicity could be larger than observed.
    Never true for any group followed by another distinct group, since a
    higher group above it proves this group's manifold is complete."""

    def __post_init__(self) -> None:
        if self.start_index < 0:
            raise ValueError(f"start_index must be >= 0, got {self.start_index}")
        if self.end_index_exclusive <= self.start_index:
            raise ValueError(
                f"end_index_exclusive ({self.end_index_exclusive}) must be > "
                f"start_index ({self.start_index})"
            )
        if self.multiplicity_observed != self.end_index_exclusive - self.start_index:
            raise ValueError(
                f"multiplicity_observed ({self.multiplicity_observed}) does not match "
                f"end_index_exclusive - start_index ({self.end_index_exclusive - self.start_index})"
            )
        for name, value in (
            ("representative_energy", self.representative_energy),
            ("min_energy", self.min_energy),
            ("max_energy", self.max_energy),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")
        if not (self.min_energy <= self.representative_energy <= self.max_energy):
            raise ValueError(
                f"representative_energy ({self.representative_energy}) must lie within "
                f"[min_energy, max_energy] = [{self.min_energy}, {self.max_energy}]"
            )


@dataclass(frozen=True, slots=True)
class DegeneracyReport:
    tolerance: float
    ground_multiplicity_observed: int
    first_distinct_energy: float | None
    first_distinct_gap: float | None  # groups[1].representative_energy - groups[0].representative_energy
    groups: tuple[SpectralLevelGroup, ...]
    window_truncated: bool
    """True when fewer eigenvalues were computed than the Hilbert space
    dimension -- i.e. the analysis only saw a partial window of the
    spectrum. Independent of lower_bound_only, which is specifically about
    the top group's manifold possibly being incomplete."""

    def __post_init__(self) -> None:
        if isinstance(self.tolerance, bool) or not (math.isfinite(self.tolerance) and self.tolerance > 0):
            raise ValueError(f"tolerance must be a positive finite number, got {self.tolerance!r}")
        if self.ground_multiplicity_observed < 1:
            raise ValueError(f"ground_multiplicity_observed must be >= 1, got {self.ground_multiplicity_observed}")
        if len(self.groups) == 0:
            raise ValueError("groups must not be empty")
        if self.groups[0].start_index != 0:
            raise ValueError(f"groups[0].start_index must be 0, got {self.groups[0].start_index}")
        for previous, current in zip(self.groups, self.groups[1:]):
            if current.start_index != previous.end_index_exclusive:
                raise ValueError("groups must be contiguous and sorted by index")
        if self.ground_multiplicity_observed != self.groups[0].multiplicity_observed:
            raise ValueError(
                f"ground_multiplicity_observed ({self.ground_multiplicity_observed}) does not match "
                f"groups[0].multiplicity_observed ({self.groups[0].multiplicity_observed})"
            )
        if len(self.groups) >= 2:
            expected_energy = self.groups[1].representative_energy
            expected_gap = self.groups[1].representative_energy - self.groups[0].representative_energy
            if self.first_distinct_energy != expected_energy:
                raise ValueError(
                    f"first_distinct_energy ({self.first_distinct_energy}) does not match "
                    f"groups[1].representative_energy ({expected_energy})"
                )
            if self.first_distinct_gap != expected_gap:
                raise ValueError(
                    f"first_distinct_gap ({self.first_distinct_gap}) does not match "
                    f"groups[1].representative_energy - groups[0].representative_energy ({expected_gap})"
                )
        elif self.first_distinct_energy is not None or self.first_distinct_gap is not None:
            raise ValueError(
                "first_distinct_energy and first_distinct_gap must both be None when there is only one group"
            )
        for index, (previous, current) in enumerate(zip(self.groups, self.groups[1:])):
            if not (previous.max_energy < current.min_energy):
                raise ValueError(
                    f"groups[{index}] and groups[{index + 1}] have overlapping or non-increasing energy ranges: "
                    f"max_energy={previous.max_energy}, next min_energy={current.min_energy}"
                )


def _same_group(previous: float, current: float, tolerance: float) -> bool:
    scale = max(1.0, abs(previous), abs(current))
    return abs(current - previous) <= tolerance * scale


def analyze_spectral_degeneracies(
    eigenvalues: Sequence[float],
    *,
    dimension: int,
    tolerance: float = DEFAULT_DEGENERACY_TOLERANCE,
) -> DegeneracyReport:
    """Group a sorted-ascending sequence of already-computed eigenvalues.

    `dimension` is the full Hilbert space dimension the eigenvalues were
    drawn from (not necessarily len(eigenvalues), when the spectral window
    is smaller than the full space) -- it is only used to determine
    window_truncated and the last group's lower_bound_only.
    """
    if isinstance(tolerance, bool) or not (math.isfinite(tolerance) and tolerance > 0):
        raise ValueError(f"tolerance must be a positive finite number, got {tolerance!r}")
    if dimension < 1:
        raise ValueError(f"dimension must be >= 1, got {dimension}")

    values = [float(value) for value in eigenvalues]
    n = len(values)
    if n < 1:
        raise ValueError("eigenvalues must contain at least one value")
    if n > dimension:
        raise ValueError(f"got {n} eigenvalues, which exceeds dimension={dimension}")

    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise ValueError(f"eigenvalue at index {index} is not finite: {value}")
    for index in range(1, n):
        if values[index] < values[index - 1]:
            raise ValueError(f"eigenvalues must be sorted ascending; violated at index {index}")

    boundaries = [0]
    for index in range(1, n):
        if not _same_group(values[index - 1], values[index], tolerance):
            boundaries.append(index)
    boundaries.append(n)

    groups = tuple(
        SpectralLevelGroup(
            start_index=start,
            end_index_exclusive=end,
            representative_energy=sum(values[start:end]) / (end - start),
            min_energy=values[start],
            max_energy=values[end - 1],
            multiplicity_observed=end - start,
            lower_bound_only=(end == n and n < dimension),
        )
        for start, end in zip(boundaries, boundaries[1:])
    )

    first_distinct_energy = groups[1].representative_energy if len(groups) >= 2 else None
    first_distinct_gap = (
        groups[1].representative_energy - groups[0].representative_energy if len(groups) >= 2 else None
    )

    return DegeneracyReport(
        tolerance=tolerance,
        ground_multiplicity_observed=groups[0].multiplicity_observed,
        first_distinct_energy=first_distinct_energy,
        first_distinct_gap=first_distinct_gap,
        groups=groups,
        window_truncated=(n < dimension),
    )
