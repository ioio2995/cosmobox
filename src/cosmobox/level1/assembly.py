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

from .serialization import validate_document

_METADATA_FIELDS = ("schema_version", "repository_commit", "manifest_fingerprint", "campaign_id")


class AssemblyContradiction(ValueError):
    """Two documents share the same scientific identity but differ in
    payload or provenance. Assembly never resolves this silently."""


class AssemblyMetadataMismatch(ValueError):
    """Documents in the same execution must share identical run metadata
    (schema_version, repository_commit, manifest_fingerprint, campaign_id).
    A mismatch means these documents do not belong to the same execution
    and must never be silently assembled -- and never deduplicated --
    together, even if their scientific identity happens to coincide."""


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


def _check_metadata_homogeneity(documents: Sequence[dict]) -> None:
    reference = {field: documents[0][field] for field in _METADATA_FIELDS}
    for document in documents[1:]:
        for field in _METADATA_FIELDS:
            if document[field] != reference[field]:
                raise AssemblyMetadataMismatch(
                    f"document metadata diverges on {field!r}: {reference[field]!r} != {document[field]!r} "
                    "-- documents from different executions/commits/manifests are never assembled together"
                )


def assemble_execution(documents: Sequence[dict]) -> tuple[tuple[dict, ...], AssemblyReport]:
    """Deduplicate and deterministically order an execution's already-
    serialized documents. Every document is independently validated
    against the v2 schema first (assemble_execution does not merely trust
    that its input came from serialize_result_record) -- any structural
    problem, including one that would otherwise surface as a bare
    KeyError while extracting keys below, is reported as an explicit
    ValueError instead. Raises AssemblyMetadataMismatch if documents
    disagree on run metadata (schema_version/repository_commit/
    manifest_fingerprint/campaign_id), and AssemblyContradiction if two
    documents share a scientific identity but differ in payload or
    provenance."""
    if not documents:
        raise ValueError("documents must be non-empty")

    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"documents[{index}] must be a dict, got {type(document)}")
        try:
            validate_document(document)
        except ValueError:
            raise
        except Exception as error:  # pragma: no cover -- defense against any non-ValueError schema-library failure
            raise ValueError(f"documents[{index}] failed structural validation: {error}") from error

    _check_metadata_homogeneity(documents)

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
