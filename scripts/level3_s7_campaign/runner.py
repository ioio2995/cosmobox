"""End-to-end Level3 S7 normative campaign runner (lot L3-AC).

Wires together every L3-AC building block (experiments.level3.s7_manifest,
scripts.level3_s7_campaign.provenance/planning/gates/outputs,
cosmobox.level3.s7_serialization, cosmobox.level3.execution.run_case/
compare_spin_pair, cosmobox.level3.frozen_reference (Level2),
cosmobox.level3.frozen_s4_reference (S4), cosmobox.level3.frozen_s5_reference
(S5), cosmobox.level3.frozen_s6_reference (S6)) into one ordered, explicit
function. No D1-D3 formula is ever called directly from here -- only
execution.run_case/compare_spin_pair, plus the serialization/gates/
outputs/provenance/planning/frozen-reference modules.

Order of operations (L3-AC mandate):
  1. load manifest
  2. refuse a campaign that already exists for this campaign_id
  3. resolve provenance (clean worktree + repository_commit, once) and
     verify branch matches the manifest
  4. verify the frozen Level2 reference (SHA256SUMS + schema + pinned
     provenance, all-or-nothing, before any S7 execution)
  5. verify the frozen Level3 S4 reference (SHA256SUMS + schema + pinned
     provenance, all-or-nothing, before any S7 execution)
  6. verify the frozen Level3 S5 reference (SHA256SUMS + schema + pinned
     provenance, all-or-nothing, before any S7 execution)
  7. verify the frozen Level3 S6 reference (SHA256SUMS + schema + pinned
     provenance, all-or-nothing, before any S7 execution)
  8. persist the campaign manifest snapshot
  9. plan exactly three frozen CaseSpec (planning.plan_campaign)
 10. run execution.run_case(spec) per case
 11. validate_case_result(result)     (gates)
 12. serialize case-result            (s7_serialization.case_result_payload)
 13. atomically persist case artifact (outputs.write_case_result)
 14. retain in-memory result for later geometry comparison
 15. after 3/3 cases, reconstruct each geometry's frozen S6 reference and
     call execution.compare_spin_pair -- never before all three S7 cases
     are persisted
 16. validate_campaign_completeness (3/3 cases, 3/3 comparisons)  (gates)
 17. verify all persisted case artifacts share provenance         (outputs)
 18. build campaign-summary (s7_serialization.campaign_summary_payload,
     self-validating, embeds all four pinned reference identities)
 19. atomically write campaign-summary.json                       (outputs)

NO_IMPLICIT_RESUME: run_campaign refuses outright (CampaignAlreadyExists)
if campaign-summary.json already exists for this campaign_id before doing
any work at all. outputs.write_campaign_manifest itself refuses
(CampaignManifestAlreadyExists) if manifest.json already exists.
write_case_result/write_campaign_summary each refuse an individual
overwrite on top of that.

This runner is fully implemented but MUST NOT be invoked against a real
S=7 case during lot L3-AC (REAL_S7_EXECUTION = FORBIDDEN for this lot).
Its correctness is demonstrated entirely by tests that monkeypatch
run_case or supply synthetic CaseExecutionResult objects
(tests/scripts/level3_s7_campaign/test_level3_s7_campaign_runner.py) --
no test in this lot calls run_campaign in a way that reaches a real
CaseSpec(..., spin=7) diagonalization.
"""

from __future__ import annotations

from pathlib import Path

from cosmobox.level3 import frozen_reference, frozen_s4_reference, frozen_s5_reference, frozen_s6_reference, s7_serialization
from cosmobox.level3.execution import CaseExecutionResult, SpinPairComparison, compare_spin_pair, run_case
from experiments.level3.s7_manifest import Level3S7Manifest, load_manifest

from . import gates, outputs, planning, provenance


class CampaignAlreadyExists(RuntimeError):
    """Raised by run_campaign when campaign-summary.json already exists
    for this campaign_id -- no implicit resume, no partial-run merging."""


def run_campaign(
    output_root: Path,
    *,
    manifest: Level3S7Manifest | None = None,
    repo_root: str | None = None,
) -> Path:
    """Run the full three-case Level3 S7 campaign and, once every
    structural gate passes, write campaign-summary.json. Returns the
    path to that file. Raises (never partially finalizes) if any step
    fails -- an interrupted or rejected campaign leaves no
    campaign-summary.json."""
    manifest = manifest if manifest is not None else load_manifest()

    summary_path = outputs.campaign_summary_path(output_root, manifest.campaign_id)
    if summary_path.exists():
        raise CampaignAlreadyExists(
            f"campaign-summary.json already exists at {summary_path}; refusing to run campaign "
            f"{manifest.campaign_id!r} again"
        )

    campaign_provenance = provenance.resolve_campaign_provenance(manifest, repo_root=repo_root)
    provenance.verify_branch_matches_manifest(campaign_provenance, repo_root=repo_root)

    # All-or-nothing verification of ALL FOUR frozen references
    # (SHA256SUMS, schema, pinned provenance) BEFORE any S7 execution. No
    # fallback, no recomputation: a failure here stops the campaign before
    # run_case is ever called.
    frozen_reference.verify_frozen_reference()
    frozen_s4_reference.verify_frozen_s4_reference()
    frozen_s5_reference.verify_frozen_s5_reference()
    frozen_s6_reference.verify_frozen_s6_reference()
    frozen_s6_campaign_summary = frozen_s6_reference.load_campaign_summary()

    outputs.write_campaign_manifest(output_root, manifest.campaign_id, manifest.raw)

    case_specs = planning.plan_campaign(manifest)

    case_results: list[CaseExecutionResult] = []
    for spec in case_specs:
        result = run_case(spec)
        gates.validate_case_result(result)

        document = s7_serialization.case_result_payload(
            result,
            campaign_id=campaign_provenance.campaign_id,
            manifest_fingerprint=campaign_provenance.manifest_fingerprint,
            repository=campaign_provenance.repository,
            repository_commit=campaign_provenance.repository_commit,
            branch=campaign_provenance.branch,
            frozen_preregistration_commit=campaign_provenance.frozen_preregistration_commit,
            numerical_guard_m_tt=manifest.numerical_guard_reference.guard_m_tt,
            numerical_guard_r_eff=manifest.numerical_guard_reference.guard_r_eff,
            numerical_guard_scope=manifest.numerical_guard_reference.guard_scope,
        )
        outputs.write_case_result(output_root, manifest.campaign_id, spec.geometry, spec.spin, document)
        case_results.append(result)

    # No normative comparison before all three S7 cases are persisted.
    geometry_comparisons: list[SpinPairComparison] = []
    for result in sorted(case_results, key=lambda r: r.spec.geometry):
        s6_reference = frozen_s6_reference.reconstruct_case_execution_result(result.spec.geometry)
        geometry_comparisons.append(compare_spin_pair(s6_reference, result))

    gates.validate_campaign_completeness(case_results, geometry_comparisons)

    outputs.verify_case_artifacts_share_provenance(
        output_root,
        manifest.campaign_id,
        [(spec.geometry, spec.spin) for spec in case_specs],
        manifest_fingerprint=campaign_provenance.manifest_fingerprint,
        repository_commit=campaign_provenance.repository_commit,
    )

    summary_document = s7_serialization.campaign_summary_payload(
        geometry_comparisons,
        frozen_s6_campaign_summary=frozen_s6_campaign_summary,
        campaign_id=campaign_provenance.campaign_id,
        manifest_fingerprint=campaign_provenance.manifest_fingerprint,
        repository=campaign_provenance.repository,
        repository_commit=campaign_provenance.repository_commit,
        branch=campaign_provenance.branch,
        frozen_preregistration_commit=campaign_provenance.frozen_preregistration_commit,
    )

    return outputs.write_campaign_summary(output_root, manifest.campaign_id, summary_document)
