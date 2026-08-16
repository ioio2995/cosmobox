"""End-to-end Level2 normative campaign runner.

Lot L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER. Wires together every already
-authorized L2-E/L2-E1 building block (experiments.level2.manifest,
scripts.level2_campaign.provenance/planning/gates/outputs,
cosmobox.level2.serialization, cosmobox.level2.execution.run_case/
compare_geometry) into one ordered, explicit function. No D1-D3 formula
is ever called directly from here -- only execution.run_case and
execution.compare_geometry, plus the serialization/gates/outputs/
provenance/planning modules already reviewed and accepted.

Order of operations (docs/governance/current-task.md, L2-E2 mandate):
  1. load manifest
  2. validate manifest        (load_manifest's own schema + dataclass validation)
  3. compute fingerprint      (Level2Manifest.fingerprint, already computed by load_manifest)
  4. require clean worktree   (provenance.resolve_campaign_provenance)
  5. resolve repository_commit ONCE (provenance.resolve_campaign_provenance)
  6. verify branch/manifest expectations (provenance.verify_branch_matches_manifest)
  7. plan exactly six frozen CaseSpec (planning.plan_campaign)
  8. run execution.run_case(spec) per case
  9. validate_case_result(result)     (gates)
 10. serialize case-result            (serialization.case_result_payload)
 11. atomically persist case artifact (outputs.write_case_result)
 12. retain in-memory result for later geometry comparison
 13. after 6/6 cases, group S=2/S=3 by geometry
 14. call execution.compare_geometry
 15. validate_campaign_completeness (6/6 cases, 3/3 comparisons)         (gates)
 16. verify all persisted case artifacts share provenance                (outputs)
 17. build campaign-summary (serialization.campaign_summary_payload, self-validating)
 18. atomically write campaign-summary.json                              (outputs)

NO_IMPLICIT_RESUME: run_campaign refuses outright (CampaignAlreadyExists)
if campaign-summary.json already exists for this campaign_id before doing
any work at all; write_case_result/write_campaign_summary each refuse an
individual overwrite on top of that (belt and suspenders, see
outputs.py's own docstring).
"""

from __future__ import annotations

from pathlib import Path

from cosmobox.level2 import serialization
from cosmobox.level2.execution import CaseExecutionResult, GeometryComparison, compare_geometry, run_case
from experiments.level2.manifest import Level2Manifest, load_manifest

from . import gates, outputs, planning, provenance


class CampaignAlreadyExists(RuntimeError):
    """Raised by run_campaign when campaign-summary.json already exists
    for this campaign_id -- no implicit resume, no partial-run merging."""


def run_campaign(
    output_root: Path,
    *,
    manifest: Level2Manifest | None = None,
    repo_root: str | None = None,
) -> Path:
    """Run the full six-case Level2 campaign and, once every structural
    gate passes, write campaign-summary.json. Returns the path to that
    file. Raises (never partially finalizes) if any step fails -- an
    interrupted or rejected campaign leaves no campaign-summary.json,
    per PARTIAL_CAMPAIGN_COMPLETE_STATUS = FORBIDDEN."""
    manifest = manifest if manifest is not None else load_manifest()

    summary_path = outputs.campaign_summary_path(output_root, manifest.campaign_id)
    if summary_path.exists():
        raise CampaignAlreadyExists(
            f"campaign-summary.json already exists at {summary_path}; refusing to run campaign {manifest.campaign_id!r} again"
        )

    campaign_provenance = provenance.resolve_campaign_provenance(manifest, repo_root=repo_root)
    provenance.verify_branch_matches_manifest(campaign_provenance, repo_root=repo_root)

    outputs.write_campaign_manifest(output_root, manifest.campaign_id, manifest.raw)

    case_specs = planning.plan_campaign(manifest)

    case_results: list[CaseExecutionResult] = []
    for spec in case_specs:
        result = run_case(spec)
        gates.validate_case_result(result)

        document = serialization.case_result_payload(
            result,
            campaign_id=campaign_provenance.campaign_id,
            manifest_fingerprint=campaign_provenance.manifest_fingerprint,
            repository_commit=campaign_provenance.repository_commit,
            branch=campaign_provenance.branch,
            frozen_preregistration_commit=campaign_provenance.frozen_preregistration_commit,
            numerical_guard_m_tt=manifest.numerical_guard_reference.guard_m_tt,
            numerical_guard_r_eff=manifest.numerical_guard_reference.guard_r_eff,
            numerical_guard_scope=manifest.numerical_guard_reference.guard_scope,
        )
        outputs.write_case_result(output_root, manifest.campaign_id, spec.geometry, spec.spin, document)
        case_results.append(result)

    results_by_geometry: dict[str, dict[int, CaseExecutionResult]] = {}
    for result in case_results:
        results_by_geometry.setdefault(result.spec.geometry, {})[result.spec.spin] = result

    geometry_comparisons: list[GeometryComparison] = [
        compare_geometry(results_by_geometry[geometry][2], results_by_geometry[geometry][3])
        for geometry in sorted(results_by_geometry)
    ]

    gates.validate_campaign_completeness(case_results, geometry_comparisons)

    outputs.verify_case_artifacts_share_provenance(
        output_root,
        manifest.campaign_id,
        [(spec.geometry, spec.spin) for spec in case_specs],
        manifest_fingerprint=campaign_provenance.manifest_fingerprint,
        repository_commit=campaign_provenance.repository_commit,
    )

    summary_document = serialization.campaign_summary_payload(
        geometry_comparisons,
        campaign_id=campaign_provenance.campaign_id,
        manifest_fingerprint=campaign_provenance.manifest_fingerprint,
        repository_commit=campaign_provenance.repository_commit,
        branch=campaign_provenance.branch,
        frozen_preregistration_commit=campaign_provenance.frozen_preregistration_commit,
    )

    return outputs.write_campaign_summary(output_root, manifest.campaign_id, summary_document)
