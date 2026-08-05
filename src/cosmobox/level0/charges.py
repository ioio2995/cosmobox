"""Shared handling of external charges q_i^ext, used by basis.py and gauge.py.

External charges (and, generally, any quantity that is an integer or a
half-integer -- matter charges Q_i included) are normalized to
``fractions.Fraction`` at the API boundary and doubled to a plain ``int``
(``2*value``) wherever exact integer arithmetic is wanted in a hot loop.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction


def double(value: Fraction) -> int:
    """Exact ``2*value`` as a plain int; raises if value is not a half-integer."""
    if value.denominator not in (1, 2):
        raise ValueError(f"{value} is not an integer or a half-integer (denominator must be 1 or 2)")
    return int(value * 2)


def normalize_external_charges(n_nodes: int, external_charges: Sequence[object] | None) -> tuple[Fraction, ...]:
    """Validate and normalize external charges to one Fraction per node (default: all zero)."""
    if external_charges is None:
        return tuple(Fraction(0) for _ in range(n_nodes))
    if len(external_charges) != n_nodes:
        raise ValueError(f"expected {n_nodes} external charges, got {len(external_charges)}")
    normalized = []
    for q in external_charges:
        fraction = Fraction(q)
        if fraction.denominator not in (1, 2):
            raise ValueError(f"external charge {q} must be an integer or a half-integer (denominator 1 or 2)")
        normalized.append(fraction)
    return tuple(normalized)


def doubled_external_charges(external_charges: Sequence[Fraction]) -> tuple[int, ...]:
    """Double an already-normalized sequence of external charges to plain ints."""
    return tuple(double(q) for q in external_charges)
