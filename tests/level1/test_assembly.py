from __future__ import annotations

import pytest

from cosmobox.level1.assembly import AssemblyContradiction, AssemblyMetadataMismatch, AssemblyReport, assemble_execution
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity, build_result_record
from cosmobox.level1.serialization import serialize_result_record

REPO_COMMIT = "b" * 40


def _document(
    *,
    spin: int = 2,
    payload: float = 0.5,
    campaign_id: str = "c1",
    observable_kind: str = "C_QQ_raw",
    repository_commit: str = REPO_COMMIT,
    manifest_fingerprint: str = "fp",
) -> dict:
    hamiltonian = HamiltonianIdentity(J=(1.0,), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    group = SpectralGroupIdentity(status=COMPLETE_MULTIPLET, multiplicity=2, twice_T=1)
    identity = ScientificIdentity(
        geometry="triangle", spin=spin, n_flavors=2, hamiltonian=hamiltonian, sector="default",
        spectral_group=group, path=None, flavor_component=None, normalization=None,
    )
    record = build_result_record(identity, "raw_observable", observable_kind, payload)
    return serialize_result_record(record, repository_commit=repository_commit, manifest_fingerprint=manifest_fingerprint, campaign_id=campaign_id)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_assemble_execution_deduplicates_identical_documents() -> None:
    doc = _document()
    ordered, report = assemble_execution([doc, dict(doc)])
    assert len(ordered) == 1
    assert report == AssemblyReport(input_count=2, output_count=1, duplicate_count=1)


def test_assemble_execution_counts_multiple_duplicates() -> None:
    doc = _document()
    ordered, report = assemble_execution([doc, dict(doc), dict(doc)])
    assert len(ordered) == 1
    assert report.duplicate_count == 2


def test_assemble_execution_distinct_identities_are_not_deduplicated() -> None:
    doc_a = _document(spin=2)
    doc_b = _document(spin=3)
    ordered, report = assemble_execution([doc_a, doc_b])
    assert len(ordered) == 2
    assert report.duplicate_count == 0


# ---------------------------------------------------------------------------
# Contradiction
# ---------------------------------------------------------------------------


def test_assemble_execution_rejects_contradictory_payload() -> None:
    doc_a = _document(payload=0.5)
    doc_b = _document(payload=0.9)
    with pytest.raises(AssemblyContradiction):
        assemble_execution([doc_a, doc_b])


def test_assemble_execution_never_last_write_wins() -> None:
    doc_a = _document(payload=0.5)
    doc_b = _document(payload=0.9)
    try:
        assemble_execution([doc_a, doc_b])
        pytest.fail("expected AssemblyContradiction")
    except AssemblyContradiction:
        pass
    # confirm order of arguments does not silently pick one value
    try:
        assemble_execution([doc_b, doc_a])
        pytest.fail("expected AssemblyContradiction")
    except AssemblyContradiction:
        pass


def test_assemble_execution_rejects_contradictory_provenance() -> None:
    doc_a = _document()
    doc_b = dict(doc_a)
    doc_b["provenance"] = dict(doc_a["provenance"])
    doc_b["provenance"]["source_type"] = "SomethingElse"
    with pytest.raises(AssemblyContradiction):
        assemble_execution([doc_a, doc_b])


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_assemble_execution_output_order_is_deterministic_regardless_of_input_order() -> None:
    doc_a = _document(spin=2, observable_kind="C_QQ_raw")
    doc_b = _document(spin=3, observable_kind="C_QQ_raw")
    doc_c = _document(spin=1, observable_kind="C_TT_raw")

    ordered_1, _ = assemble_execution([doc_a, doc_b, doc_c])
    ordered_2, _ = assemble_execution([doc_c, doc_b, doc_a])
    ordered_3, _ = assemble_execution([doc_b, doc_c, doc_a])

    assert ordered_1 == ordered_2 == ordered_3


def test_assemble_execution_orders_by_canonical_key_not_insertion() -> None:
    doc_high_spin = _document(spin=3)
    doc_low_spin = _document(spin=1)
    ordered, _ = assemble_execution([doc_high_spin, doc_low_spin])
    assert ordered[0]["identity"]["spin"] == 1
    assert ordered[1]["identity"]["spin"] == 3


# ---------------------------------------------------------------------------
# Report / edge cases
# ---------------------------------------------------------------------------


def test_assembly_report_rejects_inconsistent_counts() -> None:
    with pytest.raises(ValueError, match="output_count"):
        AssemblyReport(input_count=2, output_count=1, duplicate_count=0)


def test_assembly_report_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        AssemblyReport(input_count=-1, output_count=0, duplicate_count=0)


def test_assemble_execution_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        assemble_execution([])


def test_assemble_execution_report_matches_output() -> None:
    doc_a = _document(spin=2)
    doc_b = _document(spin=3)
    ordered, report = assemble_execution([doc_a, doc_a, doc_b])
    assert report.input_count == 3
    assert report.output_count == len(ordered) == 2
    assert report.duplicate_count == 1


# ---------------------------------------------------------------------------
# Metadata homogeneity -- never assemble documents from different runs
# ---------------------------------------------------------------------------


def test_assemble_execution_rejects_repository_commit_mismatch() -> None:
    doc_a = _document(repository_commit="a" * 40)
    doc_b = _document(repository_commit="c" * 40)
    with pytest.raises(AssemblyMetadataMismatch, match="repository_commit"):
        assemble_execution([doc_a, doc_b])


def test_assemble_execution_rejects_manifest_fingerprint_mismatch() -> None:
    doc_a = _document(manifest_fingerprint="fp1")
    doc_b = _document(manifest_fingerprint="fp2")
    with pytest.raises(AssemblyMetadataMismatch, match="manifest_fingerprint"):
        assemble_execution([doc_a, doc_b])


def test_assemble_execution_rejects_campaign_id_mismatch() -> None:
    doc_a = _document(campaign_id="c1")
    doc_b = _document(campaign_id="c2")
    with pytest.raises(AssemblyMetadataMismatch, match="campaign_id"):
        assemble_execution([doc_a, doc_b])


def test_assemble_execution_rejects_schema_version_mismatch() -> None:
    doc_a = _document()
    doc_b = dict(doc_a)
    doc_b["schema_version"] = "level1-correlators-v1"  # forged, would also fail schema validation
    with pytest.raises(ValueError):
        assemble_execution([doc_a, doc_b])


def test_assemble_execution_never_deduplicates_across_different_commits() -> None:
    # Same scientific identity and payload, but a different repository_commit
    # -- must never be silently deduplicated into one output record.
    doc_a = _document(repository_commit="a" * 40)
    doc_b = _document(repository_commit="c" * 40)
    with pytest.raises(AssemblyMetadataMismatch):
        assemble_execution([doc_a, doc_b])


# ---------------------------------------------------------------------------
# Input validation -- assemble_execution does not just trust its inputs
# ---------------------------------------------------------------------------


def test_assemble_execution_rejects_non_dict_document() -> None:
    doc = _document()
    with pytest.raises(ValueError, match="dict"):
        assemble_execution([doc, "not a document"])  # type: ignore[list-item]


def test_assemble_execution_rejects_document_missing_required_field_without_keyerror() -> None:
    doc = _document()
    broken = dict(doc)
    del broken["identity"]
    with pytest.raises(ValueError) as excinfo:
        assemble_execution([broken])
    assert not isinstance(excinfo.value, KeyError)


def test_assemble_execution_rejects_document_failing_schema_validation() -> None:
    doc = _document()
    broken = dict(doc)
    broken["identity"] = dict(doc["identity"])
    broken["identity"]["geometry"] = "not_a_real_geometry"
    with pytest.raises(ValueError, match="validate"):
        assemble_execution([broken])
