from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.assembly import AssemblyContradiction, AssemblyMetadataMismatch, AssemblyReport, assemble_execution
from cosmobox.level1.matching import compute_twice_T
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, SpectralGroupState, canonical_multiplet_expectation, extract_group_state
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity, build_spectral_group_identity
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.serialization import serialize_result_record

REPO_COMMIT = "b" * 40


def build_result_record(*args, **kwargs):
    """Shadows cosmobox.level1.results.build_result_record with fixed
    default seeds -- see tests/level1/test_results.py's own copy of this
    wrapper for the rationale."""
    kwargs.setdefault("scientific_seed", 1001)
    kwargs.setdefault("solver_seed", 2002)
    return _build_result_record_impl(*args, **kwargs)


def _document(
    *,
    spin: int = 2,
    payload: float = 0.5,
    campaign_id: str = "c1",
    observable_kind: str = "C_QQ_raw",
    repository_commit: str = REPO_COMMIT,
    manifest_fingerprint: str = "fp",
    spectral_window_group_index: int = 0,
    representative_energy: float = -1.0,
) -> dict:
    hamiltonian = HamiltonianIdentity(J=(1.0,), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    group = SpectralGroupIdentity(
        status=COMPLETE_MULTIPLET,
        multiplicity=2,
        twice_T=1,
        spectral_window_group_index=spectral_window_group_index,
        representative_energy=representative_energy,
    )
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


# ---------------------------------------------------------------------------
# spectral_window_group_index / representative_energy (Level1B lot 1B-8b,
# D022) -- the exact identity collision fixed by this sub-lot.
# ---------------------------------------------------------------------------


def test_two_groups_same_status_multiplicity_twice_t_different_index_assemble_without_contradiction() -> None:
    doc_group_0 = _document(spectral_window_group_index=0, representative_energy=-3.7791264446349917, payload=0.11)
    doc_group_1 = _document(spectral_window_group_index=1, representative_energy=-3.7309647726093322, payload=0.22)
    ordered, report = assemble_execution([doc_group_0, doc_group_1])
    assert len(ordered) == 2
    assert report.duplicate_count == 0


def test_same_index_and_energy_but_different_payload_still_raises_contradiction() -> None:
    doc_a = _document(spectral_window_group_index=0, representative_energy=-1.0, payload=0.5)
    doc_b = _document(spectral_window_group_index=0, representative_energy=-1.0, payload=0.9)
    with pytest.raises(AssemblyContradiction):
        assemble_execution([doc_a, doc_b])


def test_triangle_s2_j_break_regression_two_real_colliding_groups() -> None:
    """Reproduces the exact case that revealed the collision: two real,
    physically distinct complete multiplets (triangle S=2, j_break) share
    (status=complete_multiplet, multiplicity=2, twice_T=1) but differ in
    spectral_window_group_index and representative_energy -- must
    assemble without AssemblyContradiction. Energies are asserted
    relatively (group 0 strictly below group 1), never pinned to exact
    decimals."""
    lattice = build_lattice("triangle")
    n_nodes = len(lattice.nodes)
    report = build_basis(lattice, 2, 2)
    key_index = build_key_index(report.keys)
    J = tuple(1.5 if node == 0 else 1.0 for node in range(n_nodes))
    params = HamiltonianParameters(
        J=J, h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)), t=1.0, g_E=1.0, K=1.0
    )
    terms = build_hamiltonian_terms(lattice, 2, 2, report.keys, key_index, params)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, 2, 2, report, terms, params, spectrum_options=SpectrumOptions(n_eigenvalues=12)
    )
    groups = level0_report.spectrum.degeneracy.groups
    casimir = build_flavor_casimir(lattice, 2, 2, report.keys, key_index)

    assert len(groups) >= 2
    assert groups[0].multiplicity_observed == 2
    assert groups[1].multiplicity_observed == 2
    assert groups[0].representative_energy < groups[1].representative_energy

    state_0 = extract_group_state(eigenvectors, groups[0])
    state_1 = extract_group_state(eigenvectors, groups[1])
    twice_t_0 = compute_twice_T(canonical_multiplet_expectation(casimir, state_0, hermitian=True))
    twice_t_1 = compute_twice_T(canonical_multiplet_expectation(casimir, state_1, hermitian=True))
    assert twice_t_0 == 1
    assert twice_t_1 == 1

    identity_0 = build_spectral_group_identity(groups[0], state_0, spectral_window_group_index=0, twice_T=twice_t_0)
    identity_1 = build_spectral_group_identity(groups[1], state_1, spectral_window_group_index=1, twice_T=twice_t_1)
    assert identity_0.status == identity_1.status
    assert identity_0.multiplicity == identity_1.multiplicity
    assert identity_0.twice_T == identity_1.twice_T
    assert identity_0 != identity_1

    hamiltonian = HamiltonianIdentity(J=params.J, h_is_zero=True, t=params.t, g_E=params.g_E, K=params.K)
    scientific_identity_0 = ScientificIdentity(
        geometry="triangle", spin=2, n_flavors=2, hamiltonian=hamiltonian, sector="default",
        spectral_group=identity_0, path=None, flavor_component=None, normalization=None,
    )
    scientific_identity_1 = ScientificIdentity(
        geometry="triangle", spin=2, n_flavors=2, hamiltonian=hamiltonian, sector="default",
        spectral_group=identity_1, path=None, flavor_component=None, normalization=None,
    )
    record_0 = build_result_record(scientific_identity_0, "raw_observable", "C_QQ_raw", 0.11)
    record_1 = build_result_record(scientific_identity_1, "raw_observable", "C_QQ_raw", 0.22)
    doc_0 = serialize_result_record(record_0, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    doc_1 = serialize_result_record(record_1, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")

    ordered, report = assemble_execution([doc_0, doc_1])
    assert len(ordered) == 2
    assert report.duplicate_count == 0


def test_two_targets_resolving_to_the_same_group_produce_the_same_spectral_group_identity() -> None:
    """Two different manifest targets that both select the same physical
    group must produce IDENTICAL SpectralGroupIdentity -- identity
    belongs to the group, never to which target rule found it."""
    group = _level_group_for_assembly()
    state = _group_state_for_assembly()
    identity_via_target_a = build_spectral_group_identity(group, state, spectral_window_group_index=1, twice_T=1)
    identity_via_target_b = build_spectral_group_identity(group, state, spectral_window_group_index=1, twice_T=1)
    assert identity_via_target_a == identity_via_target_b


def _level_group_for_assembly() -> SpectralLevelGroup:
    return SpectralLevelGroup(
        start_index=2, end_index_exclusive=4, representative_energy=-1.5,
        min_energy=-1.51, max_energy=-1.49, multiplicity_observed=2, lower_bound_only=False,
    )


def _group_state_for_assembly() -> SpectralGroupState:
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(6, 2)) + 1j * rng.normal(size=(6, 2))
    q, _ = np.linalg.qr(raw)
    return SpectralGroupState(psi=q[:, :2], status=COMPLETE_MULTIPLET)


def test_ordering_by_spectral_window_group_index_overrides_lexicographic_field_order() -> None:
    """Group 1 is given a representative_energy that would sort BEFORE
    group 0's under naive field-order comparison, to prove the sort key
    orders by spectral_window_group_index first, not by whichever field
    happens to compare smaller."""
    doc_group_0 = _document(spectral_window_group_index=0, representative_energy=5.0, payload=0.1)
    doc_group_1 = _document(spectral_window_group_index=1, representative_energy=-5.0, payload=0.2)
    ordered, _ = assemble_execution([doc_group_1, doc_group_0])
    assert ordered[0]["identity"]["spectral_group"]["spectral_window_group_index"] == 0
    assert ordered[1]["identity"]["spectral_group"]["spectral_window_group_index"] == 1


def test_spectral_group_payload_includes_index_and_energy() -> None:
    doc = _document(spectral_window_group_index=3, representative_energy=-7.25)
    assert doc["identity"]["spectral_group"]["spectral_window_group_index"] == 3
    assert doc["identity"]["spectral_group"]["representative_energy"] == -7.25


def test_v2_document_missing_spectral_window_group_index_is_rejected() -> None:
    doc = _document()
    broken = dict(doc)
    broken["identity"] = dict(doc["identity"])
    broken["identity"]["spectral_group"] = dict(doc["identity"]["spectral_group"])
    del broken["identity"]["spectral_group"]["spectral_window_group_index"]
    with pytest.raises(ValueError, match="validate"):
        assemble_execution([broken])


def test_v1_schema_spectral_group_definition_is_unchanged() -> None:
    v1_path = Path(__file__).resolve().parents[2] / "schemas" / "level1" / "correlators-v1.schema.json"
    with v1_path.open() as handle:
        v1_schema = json.load(handle)
    schema_text = json.dumps(v1_schema)
    assert "spectral_window_group_index" not in schema_text
    assert "representative_energy" not in schema_text
