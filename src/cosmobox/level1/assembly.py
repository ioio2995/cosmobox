"""Deterministic assembly of an execution's already-serialized Level1
result documents. Level1B lot 1B-7.

Operates ONLY on documents already produced by
serialization.serialize_result_record (already validated against
correlators-v2.schema.json) -- no scientific logic is introduced here.
Two documents sharing the same scientific identity (campaign, geometry,
spin, Hamiltonian, sector, spectral group, record_kind, observable_kind,
path, flavor component, normalization) with an IDENTICAL payload and
provenance are a harmless duplicate (deduplicated, counted); the same
identity with ANY difference is a contradiction (raised, never resolved
by last-write-wins or averaging).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass


class AssemblyContradiction(ValueError):
    """Two documents share the same scientific identity but differ in
    payload or provenance. Assembly never resolves this silently."""


@dataclass(frozen=True, slots=True)
class AssemblyReport:
    input_count: int
    output_count: int
    duplicate_count: int

    def __post_init__(self) -> None:
        for name, value in (
            ("input_count", self.input_count),
            ("output_count", self.output_count),
            ("duplicate_count", self.duplicate_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")
        if self.output_count + self.duplicate_count != self.input_count:
            raise ValueError(
                f"output_count ({self.output_count}) + duplicate_count ({self.duplicate_count}) "
                f"must equal input_count ({self.input_count})"
            )


def _hashable(value: object) -> object:
    if isinstance(value, dict):
        return tuple(sorted((key, _hashable(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    return value


def _identity_key(document: dict) -> tuple:
    """The scientific-identity part of the uniqueness key -- deliberately
    excludes schema_version/repository_commit/manifest_fingerprint (run
    metadata, not scientific identity) and payload/provenance (compared
    separately to distinguish a harmless duplicate from a contradiction).
    """
    identity = document["identity"]
    return (
        document["campaign_id"],
        identity["geometry"],
        identity["spin"],
        _hashable(identity["hamiltonian"]),
        identity["sector"],
        _hashable(identity["spectral_group"]),
        document["record_kind"],
        document["observable_kind"],
        _hashable(identity["path"]),
        identity["flavor_component"],
        identity["normalization"],
    )


def _sort_key(document: dict) -> tuple:
    """A fully orderable canonical key -- unlike _identity_key (which only
    needs to be hashable), sorting requires every component to compare
    safely against every other document's corresponding component, so
    nested structures and the None/tuple duality of `path` are normalized
    into homogeneously comparable forms (JSON strings, an explicit
    (present, value) pair for the optional path)."""
    identity = document["identity"]
    path = identity["path"]
    path_key = (0,) if path is None else (1, tuple(path))
    return (
        document["campaign_id"],
        identity["geometry"],
        identity["spin"],
        json.dumps(identity["hamiltonian"], sort_keys=True),
        identity["sector"],
        json.dumps(identity["spectral_group"], sort_keys=True),
        document["record_kind"],
        document["observable_kind"],
        path_key,
        identity["flavor_component"] or "",
        identity["normalization"] or "",
    )


def assemble_execution(documents: Sequence[dict]) -> tuple[tuple[dict, ...], AssemblyReport]:
    """Deduplicate and deterministically order an execution's already-
    serialized documents. Raises AssemblyContradiction if two documents
    share a scientific identity but differ in payload or provenance."""
    if not documents:
        raise ValueError("documents must be non-empty")

    kept: dict[tuple, dict] = {}
    duplicate_count = 0
    for document in documents:
        key = _identity_key(document)
        if key in kept:
            existing = kept[key]
            if existing["payload"] != document["payload"] or existing["provenance"] != document["provenance"]:
                raise AssemblyContradiction(
                    f"two records share the same scientific identity {key} but differ in payload or provenance"
                )
            duplicate_count += 1
            continue
        kept[key] = document

    ordered = tuple(sorted(kept.values(), key=_sort_key))
    report = AssemblyReport(input_count=len(documents), output_count=len(ordered), duplicate_count=duplicate_count)
    return ordered, report
