"""Validated loading of already-executed, immutable Level1B campaign
artifacts. Level1B lot 1B-9b (docs/governance/current-task.md).

load_validated_cases builds the manifest's own deterministic plan
(experiments.level1.planning.build_campaign_plan) exactly once, then for
every planned case reuses the already-accepted persistence primitives
(scripts.level1b_campaign.outputs.validate_existing_case_run/
load_case_records) unmodified -- it never parses records.jsonl with a
second, independent reader, never re-derives a run's validity, and never
writes to runs/<case_id>/ in any way.

All-or-nothing: if a single planned case does not have an exactly valid
existing run, load_validated_cases raises CampaignLoadError immediately,
before returning anything -- there is no partial analysis and no silent
skip. This module performs no scientific computation and no inter-S
matching; it only loads and cross-checks already-serialized documents
against the manifest and the plan they were produced from.

Deep immutability (1B-9b correctif): every document load_case_records
returns is recursively frozen (_freeze below) before it is ever attached
to a LoadedCase -- dict becomes types.MappingProxyType over a freshly
built dict never referenced anywhere else, list/tuple becomes tuple,
every scalar (str/int/float/bool/None) is returned unchanged. This never
touches records.jsonl, load_case_records, or any numeric value; it only
changes the in-memory container types a caller can observe through this
module's own API, so that no external mutation -- of the original
loaded object or of anything reachable through LoadedCase.documents --
can ever silently alter an already-built LoadedCase.

Deep immutability, second correctif: LoadedCase.__post_init__ (and
scripts.level1b_analysis.indexing.IndexedSpectralGroup's own, which
imports and reuses the exact same primitive) no longer accepts a
document merely because its ROOT happens to be a types.MappingProxyType
-- a forged, only-partially-frozen document (a MappingProxyType root
wrapping a still-mutable nested dict or list) is rejected by
_is_deeply_frozen below, never silently re-frozen on the caller's
behalf. Only a document that is deeply frozen at every level, exactly
as _freeze itself would have produced, is ever accepted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from experiments.level1.manifest import Manifest
from experiments.level1.planning import CampaignCaseSpec, build_campaign_plan

from scripts.level1b_campaign.outputs import load_case_records, validate_existing_case_run

FrozenDocument = Mapping[str, object]
"""A single v2 document, deeply frozen by _freeze -- a
types.MappingProxyType at every dict level, tuples wherever the source
JSON had a list, and unchanged scalars. Never a plain dict once it
reaches this type."""

_JSON_SCALAR_TYPES = (str, int, float, bool, type(None))


def _freeze(value: object) -> object:
    """Recursively converts a JSON-shaped value -- the only value space
    load_case_records (json.loads under the hood) can ever produce, plus
    tuple defensively -- into a deeply immutable equivalent: dict becomes
    a types.MappingProxyType over a freshly built dict that is never
    referenced anywhere else (so wrapping it is not merely cosmetic --
    there is no other live reference through which to mutate the
    underlying dict), list/tuple becomes tuple (whose own elements are
    themselves frozen, recursively), and every scalar is returned
    unchanged -- never transformed, never re-typed, never rounded."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, _JSON_SCALAR_TYPES):
        return value
    raise ValueError(f"cannot freeze value of type {type(value).__name__}: not a JSON-safe type")


def _freeze_document(document: dict) -> FrozenDocument:
    frozen = _freeze(document)
    if not isinstance(frozen, MappingProxyType):
        raise ValueError(f"document must be a dict at the top level, got {type(document)}")
    return frozen


def _is_deeply_frozen(value: object) -> bool:
    """The single source of truth for what "deeply frozen" means for a
    document exposed through this module's public API -- shared by
    LoadedCase and IndexedSpectralGroup (scripts.level1b_analysis.
    indexing) so their __post_init__ invariants can never silently
    drift apart into two different definitions.

    True iff `value` is built exclusively from the shapes _freeze itself
    ever produces: types.MappingProxyType (every key a str, every value
    itself deeply frozen, recursively), tuple (every element itself
    deeply frozen, recursively), or a bare JSON scalar
    (str/int/float/bool/None). A plain dict or list anywhere in the
    structure, or a non-str mapping key, makes this False -- including a
    types.MappingProxyType root whose OWN nested values are still plain,
    mutable dict/list (a "partially frozen" forgery is rejected, never
    silently re-frozen here: __post_init__ callers of this function
    raise on False, they never call _freeze on the caller's behalf).
    """
    if isinstance(value, MappingProxyType):
        return all(isinstance(key, str) and _is_deeply_frozen(item) for key, item in value.items())
    if isinstance(value, tuple):
        return all(_is_deeply_frozen(item) for item in value)
    return isinstance(value, _JSON_SCALAR_TYPES)


class CampaignLoadError(RuntimeError):
    """Raised whenever a planned case's existing run is not exactly
    valid, or a loaded document disagrees with the manifest on a field
    validate_existing_case_run does not itself check (schema_version).
    Always raised before any partial result is returned."""


@dataclass(frozen=True, slots=True)
class LoadedCase:
    """One planned case's own CampaignCaseSpec together with the exact,
    already-validated, already-canonically-ordered, deeply frozen
    documents from its runs/<case_id>/records.jsonl (via
    load_case_records, unmodified) -- never re-parsed, never re-ordered.
    documents are FrozenDocument (types.MappingProxyType at every dict
    level, tuples for every JSON array): __post_init__ itself refuses to
    accept anything else, so LoadedCase cannot be constructed -- by this
    module or by a caller -- with a mutable document."""

    case: CampaignCaseSpec
    documents: tuple[FrozenDocument, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case, CampaignCaseSpec):
            raise ValueError(f"case must be a CampaignCaseSpec, got {type(self.case)}")
        if not self.documents:
            raise ValueError(f"documents must be non-empty for case {self.case.case_id!r}")
        for index, document in enumerate(self.documents):
            if not _is_deeply_frozen(document):
                raise ValueError(
                    f"documents[{index}] for case {self.case.case_id!r} is not deeply frozen (a "
                    "types.MappingProxyType root is not enough -- every nested dict/list must also be "
                    "frozen, and every mapping key must be a str) -- construct LoadedCase only via "
                    "load_validated_cases, never with a partially frozen or forged document"
                )


def load_validated_cases(
    manifest: Manifest, campaign_output_dir: Path, *, repository_commit: str
) -> tuple[LoadedCase, ...]:
    """Build build_campaign_plan(manifest) exactly once, and for every
    planned case (in plan order) require validate_existing_case_run(...)
    .is_valid is True before ever calling load_case_records -- an
    invalid or missing run for even one planned case aborts the whole
    call with CampaignLoadError, never a partial LoadedCase tuple.

    Every loaded document's schema_version is additionally cross-checked
    against manifest.schema_version -- the one provenance field
    validate_existing_case_run does not itself verify (it already
    verifies campaign_id/manifest_fingerprint/repository_commit for
    every line).
    """
    if not repository_commit:
        raise ValueError("repository_commit must be non-empty")

    plan = build_campaign_plan(manifest)

    loaded_cases: list[LoadedCase] = []
    for case in plan:
        case_dir = campaign_output_dir / "runs" / case.case_id

        validation = validate_existing_case_run(
            case_dir,
            case_id=case.case_id,
            campaign_id=manifest.campaign_id,
            manifest_fingerprint=manifest.fingerprint,
            repository_commit=repository_commit,
        )
        if not validation.is_valid:
            raise CampaignLoadError(
                f"case {case.case_id!r} does not have an exactly valid existing run under {campaign_output_dir}: "
                f"{validation.reason}"
            )

        # load_case_records returns plain, mutable dicts -- frozen
        # immediately, before any other check, so nothing downstream
        # (including the schema_version check right below) ever holds a
        # reference to a mutable document.
        documents = tuple(_freeze_document(document) for document in load_case_records(case_dir))
        for index, document in enumerate(documents):
            if document["schema_version"] != manifest.schema_version:
                raise CampaignLoadError(
                    f"case {case.case_id!r} document {index} has schema_version "
                    f"{document['schema_version']!r}, expected manifest.schema_version "
                    f"{manifest.schema_version!r}"
                )

        loaded_cases.append(LoadedCase(case=case, documents=documents))

    return tuple(loaded_cases)
