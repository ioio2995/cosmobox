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
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.level1.manifest import Manifest
from experiments.level1.planning import CampaignCaseSpec, build_campaign_plan

from scripts.level1b_campaign.outputs import load_case_records, validate_existing_case_run


class CampaignLoadError(RuntimeError):
    """Raised whenever a planned case's existing run is not exactly
    valid, or a loaded document disagrees with the manifest on a field
    validate_existing_case_run does not itself check (schema_version).
    Always raised before any partial result is returned."""


@dataclass(frozen=True, slots=True)
class LoadedCase:
    """One planned case's own CampaignCaseSpec together with the exact,
    already-validated, already-canonically-ordered documents from its
    runs/<case_id>/records.jsonl (via load_case_records, unmodified) --
    never re-parsed, never re-ordered."""

    case: CampaignCaseSpec
    documents: tuple[dict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case, CampaignCaseSpec):
            raise ValueError(f"case must be a CampaignCaseSpec, got {type(self.case)}")
        if not self.documents:
            raise ValueError(f"documents must be non-empty for case {self.case.case_id!r}")


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

        documents = load_case_records(case_dir)
        for index, document in enumerate(documents):
            if document["schema_version"] != manifest.schema_version:
                raise CampaignLoadError(
                    f"case {case.case_id!r} document {index} has schema_version "
                    f"{document['schema_version']!r}, expected manifest.schema_version "
                    f"{manifest.schema_version!r}"
                )

        loaded_cases.append(LoadedCase(case=case, documents=documents))

    return tuple(loaded_cases)
