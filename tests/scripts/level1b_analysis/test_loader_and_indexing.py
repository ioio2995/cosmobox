from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from cosmobox.level1.assembly import assemble_execution
from cosmobox.level1.matching import SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import HamiltonianIdentity, ScientificIdentity, SpectralGroupIdentity
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.serialization import serialize_result_record
from experiments.level1 import manifest as manifest_module
from experiments.level1 import planning as planning_module
from scripts.level1b_campaign.outputs import CaseRunValidation, load_case_records, write_case_success
from scripts.level1b_campaign.runner import CaseExecutionResult
from scripts.level1b_analysis import indexing as indexing_module
from scripts.level1b_analysis import loader as loader_module
from scripts.level1b_analysis.indexing import (
    CampaignArtifactIndex,
    IndexedSpectralGroup,
    SpectralGroupIndexError,
    UnresolvedFlavorLabelError,
    build_campaign_artifact_index,
)
from scripts.level1b_analysis.loader import CampaignLoadError, LoadedCase, load_validated_cases

REPO_COMMIT = "d" * 40

_FORBIDDEN_IMPORT_TOKENS = (
    "match_spectral_group",
    "evaluate_robustness",
    "compute_gamma_o",
    "run_single_case",
    "run_campaign",
    "launch_normative_campaign",
)


# ---------------------------------------------------------------------------
# Fixtures -- the real manifest (load_manifest, pure, no diagonalization)
# supplies genuine CampaignCaseSpec objects (real geometry/spin/sector/
# hamiltonian_parameters/seeds); build_campaign_plan is always
# monkeypatched to a small, controlled tuple derived from them, so no
# test ever touches all 11 real cases. Documents are small, fast,
# genuinely v2-schema-valid, built via the real results.py/
# serialization.py primitives -- never a diagonalization -- and written
# to disk via the real, already-accepted write_case_success.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_manifest() -> manifest_module.Manifest:
    return manifest_module.load_manifest()


@pytest.fixture(scope="module")
def real_plan(real_manifest: manifest_module.Manifest) -> tuple:
    return planning_module.build_campaign_plan(real_manifest)


def _case(real_plan: tuple, *, geometry: str = "triangle", spin: int = 1, hamiltonian_case_id: str = "reference"):
    return next(
        c for c in real_plan if c.geometry == geometry and c.spin == spin and c.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture
def triangle_s1(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=1)


@pytest.fixture
def triangle_s2(real_plan: tuple):
    return _case(real_plan, geometry="triangle", spin=2)


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: tuple) -> None:
    monkeypatch.setattr(loader_module, "build_campaign_plan", lambda manifest_arg: plan)


def build_result_record(*args, **kwargs):
    kwargs.setdefault("scientific_seed", 1001)
    kwargs.setdefault("solver_seed", 2002)
    return _build_result_record_impl(*args, **kwargs)


def _hamiltonian_identity(case) -> HamiltonianIdentity:
    return HamiltonianIdentity(
        J=case.hamiltonian_parameters.J,
        h_is_zero=True,
        t=case.hamiltonian_parameters.t,
        g_E=case.hamiltonian_parameters.g_E,
        K=case.hamiltonian_parameters.K,
    )


def _group(index: int, *, twice_T: int | None = 0, multiplicity: int = 1, status: str = COMPLETE_MULTIPLET, energy: float = -1.0):
    return SpectralGroupIdentity(
        status=status, multiplicity=multiplicity, twice_T=twice_T, spectral_window_group_index=index, representative_energy=energy
    )


def _document(
    case,
    group: SpectralGroupIdentity,
    *,
    record_kind: str,
    observable_kind: str,
    payload,
    path=None,
    flavor_component: str | None = None,
    normalization: str | None = None,
    geometry: str | None = None,
    spin: int | None = None,
    sector: str | None = None,
    hamiltonian: HamiltonianIdentity | None = None,
    scientific_seed: int | None = None,
    solver_seed: int | None = None,
    validation_rotation_seed: int | None = 0,
    campaign_id: str | None = None,
    manifest_fingerprint: str | None = None,
    repository_commit: str = REPO_COMMIT,
    manifest=None,
) -> dict:
    identity = ScientificIdentity(
        geometry=geometry if geometry is not None else case.geometry,
        spin=spin if spin is not None else case.spin,
        n_flavors=2,
        hamiltonian=hamiltonian if hamiltonian is not None else _hamiltonian_identity(case),
        sector=sector if sector is not None else case.sector_id,
        spectral_group=group,
        path=path,
        flavor_component=flavor_component,
        normalization=normalization,
    )
    record = build_result_record(
        identity,
        record_kind,
        observable_kind,
        payload,
        scientific_seed=scientific_seed if scientific_seed is not None else case.scientific_seed,
        solver_seed=solver_seed if solver_seed is not None else case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed if validation_rotation_seed == 0 else validation_rotation_seed,
    )
    return serialize_result_record(
        record,
        repository_commit=repository_commit,
        manifest_fingerprint=manifest_fingerprint if manifest_fingerprint is not None else manifest.fingerprint,
        campaign_id=campaign_id if campaign_id is not None else manifest.campaign_id,
    )


def _symmetry_document(case, group, observable_kind: str, label: SymmetryLabel, *, manifest, **kwargs) -> dict:
    identity_kwargs = {k: v for k, v in kwargs.items() if k not in ("scientific_seed", "solver_seed")}
    identity = ScientificIdentity(
        geometry=identity_kwargs.pop("geometry", case.geometry),
        spin=identity_kwargs.pop("spin", case.spin),
        n_flavors=2,
        hamiltonian=identity_kwargs.pop("hamiltonian", _hamiltonian_identity(case)),
        sector=identity_kwargs.pop("sector", case.sector_id),
        spectral_group=group,
        path=None,
        flavor_component=None,
        normalization=None,
    )
    record = build_result_record(
        identity,
        "symmetry_label",
        observable_kind,
        label,
        scientific_seed=kwargs.get("scientific_seed", case.scientific_seed),
        solver_seed=kwargs.get("solver_seed", case.solver_seed),
        validation_rotation_seed=case.validation_rotation_seed,
    )
    return serialize_result_record(
        record,
        repository_commit=kwargs.get("repository_commit", REPO_COMMIT),
        manifest_fingerprint=kwargs.get("manifest_fingerprint", manifest.fingerprint),
        campaign_id=kwargs.get("campaign_id", manifest.campaign_id),
    )


def _default_group_documents(case, group, *, manifest, twice_T_label: complex | None = 0.0, extra_observable: bool = True) -> list[dict]:
    """The three mandatory group-level symmetry labels for `group`, plus
    one ordinary observable record -- everything indexing.py requires,
    nothing more."""
    documents = [
        _symmetry_document(
            case, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(twice_T_label, 0.0)), manifest=manifest
        )
        if twice_T_label is not None
        else _symmetry_document(case, group, "flavor_casimir_label", SymmetryLabel(kind="unavailable", value=None), manifest=manifest),
        _symmetry_document(case, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=manifest),
        _symmetry_document(case, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=manifest),
    ]
    if extra_observable:
        documents.append(
            _document(case, group, record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.25, path=(0,), manifest=manifest)
        )
    return documents


def _write_case(output_dir: Path, case, documents: list[dict]) -> None:
    assembled, report = assemble_execution(documents)
    result = CaseExecutionResult(case_id=case.case_id, target_outcomes=(), documents=assembled, assembly_report=report)
    write_case_success(output_dir, result)


# ---------------------------------------------------------------------------
# 1/2/8/22. Nominal index, multiple groups, grouping by
# spectral_window_group_index, numeric SymmetryLabel reconstruction,
# group order.
# ---------------------------------------------------------------------------


def test_nominal_index_multiple_groups(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group0 = _group(0, twice_T=1, multiplicity=2, energy=-3.0)
    group1 = _group(1, twice_T=3, multiplicity=4, energy=-1.0)
    documents = _default_group_documents(triangle_s1, group0, manifest=real_manifest, twice_T_label=1.0) + _default_group_documents(
        triangle_s1, group1, manifest=real_manifest, twice_T_label=3.0
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)

    assert isinstance(index, CampaignArtifactIndex)
    assert len(index.cases) == 1
    assert len(index.groups) == 2
    assert [g.spectral_window_group_index for g in index.groups] == [0, 1]
    assert [g.documents.__len__() for g in index.groups] == [4, 4]

    first = index.groups[0]
    assert isinstance(first, IndexedSpectralGroup)
    assert first.match_key.multiplicity == 2
    assert first.match_key.twice_T == 1
    assert first.match_key.translation_label == SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))
    assert first.match_key.reflection_label == SymmetryLabel(kind="numeric", value=complex(2.0, 0.0))


# ---------------------------------------------------------------------------
# 3. Same index, divergent SpectralGroupIdentity across documents.
# ---------------------------------------------------------------------------


def test_group_index_with_divergent_identity_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group_a = _group(0, twice_T=1, multiplicity=2)
    group_b = _group(0, twice_T=1, multiplicity=3)  # same index, different multiplicity
    documents = _default_group_documents(triangle_s1, group_a, manifest=real_manifest, twice_T_label=1.0)
    documents.append(
        _document(triangle_s1, group_b, record_kind="raw_observable", observable_kind="C_TT_raw", payload=0.5, path=(0, 1), manifest=real_manifest)
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="disagree"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 4/5. Translation label missing / duplicated.
# ---------------------------------------------------------------------------


def test_missing_translation_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = [
        _symmetry_document(triangle_s1, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=real_manifest),
    ]
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="translation_character"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_duplicate_translation_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    # assembly.py's own AssemblyContradiction/dedup logic already forbids
    # two DIFFERENT-payload documents sharing the same scientific
    # identity from ever coexisting in a normally-written records.jsonl
    # (and silently merges two IDENTICAL ones) -- so a genuine duplicate
    # group-level label can only be constructed by writing raw JSON
    # directly, bypassing assemble_execution/write_case_success, exactly
    # like the schema_version/spectral_status adversarial tests below.
    group = _group(0, twice_T=1)
    documents = _default_group_documents(triangle_s1, group, manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _symmetry_document(triangle_s1, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(9.0, 0.0)), manifest=real_manifest)
    )
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))
    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )

    with pytest.raises(SpectralGroupIndexError, match="translation_character"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 6. Reflection label missing / duplicated.
# ---------------------------------------------------------------------------


def test_missing_reflection_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = [
        _symmetry_document(triangle_s1, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
    ]
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="reflection_character"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_duplicate_reflection_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = _default_group_documents(triangle_s1, group, manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _symmetry_document(triangle_s1, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(9.0, 0.0)), manifest=real_manifest)
    )
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))
    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )

    with pytest.raises(SpectralGroupIndexError, match="reflection_character"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 7. flavor_casimir_label missing / duplicated.
# ---------------------------------------------------------------------------


def test_missing_flavor_casimir_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = [
        _symmetry_document(triangle_s1, group, "translation_character", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=real_manifest),
    ]
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="flavor_casimir_label"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_duplicate_flavor_casimir_label_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = _default_group_documents(triangle_s1, group, manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _symmetry_document(triangle_s1, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=real_manifest)
    )
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))
    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )

    with pytest.raises(SpectralGroupIndexError, match="flavor_casimir_label"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 9/10. not_applicable / unavailable SymmetryLabel reconstruction.
# ---------------------------------------------------------------------------


def test_symmetry_label_reconstruction_not_applicable(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = [
        _symmetry_document(triangle_s1, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "translation_character", SymmetryLabel(kind="not_applicable", value=None), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=real_manifest),
    ]
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert index.groups[0].match_key.translation_label == SymmetryLabel(kind="not_applicable", value=None)


def test_symmetry_label_reconstruction_unavailable(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    documents = [
        _symmetry_document(triangle_s1, group, "flavor_casimir_label", SymmetryLabel(kind="numeric", value=complex(1.0, 0.0)), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "translation_character", SymmetryLabel(kind="unavailable", value=None), manifest=real_manifest),
        _symmetry_document(triangle_s1, group, "reflection_character", SymmetryLabel(kind="numeric", value=complex(2.0, 0.0)), manifest=real_manifest),
    ]
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert index.groups[0].match_key.translation_label == SymmetryLabel(kind="unavailable", value=None)


# ---------------------------------------------------------------------------
# 11/12. twice_T is None -- dedicated blocking error; flavor_casimir_label
# cross-check against twice_T.
# ---------------------------------------------------------------------------


def test_unresolved_twice_t_raises_dedicated_error(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=None)
    documents = _default_group_documents(triangle_s1, group, manifest=real_manifest, twice_T_label=None)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(UnresolvedFlavorLabelError, match="twice_T is null"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_unresolved_twice_t_is_a_spectral_group_index_error_subclass() -> None:
    assert issubclass(UnresolvedFlavorLabelError, SpectralGroupIndexError)


def test_flavor_casimir_label_mismatch_with_twice_t_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    group = _group(0, twice_T=1)
    # flavor_casimir_label claims twice_T=3, but the group's own twice_T is 1.
    documents = _default_group_documents(triangle_s1, group, manifest=real_manifest, twice_T_label=3.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="flavor_casimir_label"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 13/14/15. Provenance mismatches at the case-run level (campaign_id,
# manifest_fingerprint, repository_commit) surfaced as CampaignLoadError.
# The underlying per-field logic is already exhaustively tested in
# test_outputs.py -- these confirm loader.py's own wrapping only.
# ---------------------------------------------------------------------------


def test_wrong_campaign_id_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    for document in documents:
        document["campaign_id"] = "some-other-campaign"
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(CampaignLoadError):
        load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_wrong_manifest_fingerprint_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    for document in documents:
        document["manifest_fingerprint"] = "f" * 64
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(CampaignLoadError):
        load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_wrong_repository_commit_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(CampaignLoadError):
        load_validated_cases(real_manifest, tmp_path, repository_commit="e" * 40)


# ---------------------------------------------------------------------------
# 16. schema_version mismatch. Structurally unreachable via the normal
# write path (the v2 schema itself pins schema_version as a const), so
# validate_existing_case_run is monkeypatched to report the run valid,
# isolating loader.py's own additional check.
# ---------------------------------------------------------------------------


def _write_case_raw(output_dir: Path, case, documents: list[dict]) -> None:
    """Writes records.jsonl/run.json directly (bypassing write_case_success's
    own document-consistency re-validation), for the handful of adversarial
    tests that need a document disagreeing with itself on a field
    write_case_success would otherwise refuse to persist."""
    import hashlib

    case_dir = output_dir / "runs" / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(document, sort_keys=True, separators=(",", ":")) for document in documents]
    records_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    (case_dir / "records.jsonl").write_bytes(records_bytes)
    run_payload = {
        "case_id": case.case_id,
        "campaign_id": documents[0]["campaign_id"],
        "manifest_fingerprint": documents[0]["manifest_fingerprint"],
        "repository_commit": documents[0]["repository_commit"],
        "run_status": "success",
        "record_count": len(documents),
        "records_sha256": hashlib.sha256(records_bytes).hexdigest(),
        "errors": [],
    }
    (case_dir / "run.json").write_text(json.dumps(run_payload, sort_keys=True, indent=2), encoding="utf-8")


def test_wrong_schema_version_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    # load_case_records (real) reads exactly what write_case_success wrote;
    # tamper the on-disk schema_version afterward, then force
    # validate_existing_case_run to report the run as valid regardless, so
    # only loader.py's own schema_version check is exercised.
    case_dir = tmp_path / "runs" / triangle_s1.case_id
    tampered = [json.loads(line) for line in (case_dir / "records.jsonl").read_text().splitlines()]
    for document in tampered:
        document["schema_version"] = "some-other-schema-version"
    (case_dir / "records.jsonl").write_text("\n".join(json.dumps(d, sort_keys=True) for d in tampered) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )

    with pytest.raises(CampaignLoadError, match="schema_version"):
        load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 17/18/19/20. Document vs case cross-checks: geometry, spin, sector,
# HamiltonianIdentity, seeds, provenance.spectral_status.
# ---------------------------------------------------------------------------


def test_document_geometry_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _document(
            triangle_s1, _group(0, twice_T=1), record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.1,
            path=(0,), geometry="ring4", manifest=real_manifest,
        )
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="geometry"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_document_spin_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _document(
            triangle_s1, _group(0, twice_T=1), record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.1,
            path=(0,), spin=99, manifest=real_manifest,
        )
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="spin"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_document_sector_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _document(
            triangle_s1, _group(0, twice_T=1), record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.1,
            path=(0,), sector="some-other-sector", manifest=real_manifest,
        )
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="sector"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_document_hamiltonian_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    wrong_hamiltonian = HamiltonianIdentity(J=(99.0, 99.0, 99.0), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    documents.append(
        _document(
            triangle_s1, _group(0, twice_T=1), record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.1,
            path=(0,), hamiltonian=wrong_hamiltonian, manifest=real_manifest,
        )
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="hamiltonian"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_document_seeds_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0, extra_observable=False)
    documents.append(
        _document(
            triangle_s1, _group(0, twice_T=1), record_kind="raw_observable", observable_kind="C_QQ_raw", payload=0.1,
            path=(0,), scientific_seed=triangle_s1.scientific_seed + 1, manifest=real_manifest,
        )
    )
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    with pytest.raises(SpectralGroupIndexError, match="seeds"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


def test_document_spectral_status_mismatch_rejected(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    # ResultRecord.__post_init__ itself forbids constructing a mismatched
    # provenance.spectral_status -- tamper the already-serialized JSON
    # directly, exactly like a corrupted-on-disk-artifact scenario.
    documents[-1] = dict(documents[-1])
    documents[-1]["provenance"] = dict(documents[-1]["provenance"])
    documents[-1]["provenance"]["spectral_status"] = "partial_subspace"
    _write_case_raw(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))
    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )

    with pytest.raises(SpectralGroupIndexError, match="spectral_status"):
        build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)


# ---------------------------------------------------------------------------
# 21. Case order matches the plan.
# ---------------------------------------------------------------------------


def test_case_order_matches_plan(monkeypatch, real_manifest, triangle_s1, triangle_s2, tmp_path: Path) -> None:
    for case in (triangle_s2, triangle_s1):  # written in reverse order on disk
        documents = _default_group_documents(case, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
        _write_case(tmp_path, case, documents)
    _patch_plan(monkeypatch, (triangle_s1, triangle_s2))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    assert [c.case.case_id for c in index.cases] == [triangle_s1.case_id, triangle_s2.case_id]


# ---------------------------------------------------------------------------
# 23/24. No target_id anywhere in the index API; no forbidden call.
# ---------------------------------------------------------------------------


def test_no_target_id_field_anywhere_in_index_api() -> None:
    for cls in (LoadedCase, IndexedSpectralGroup, CampaignArtifactIndex):
        assert "target_id" not in {f.name for f in dataclasses.fields(cls)}


def test_indexing_module_never_imports_matching_or_orchestration_entry_points() -> None:
    for module in (indexing_module, loader_module):
        source = inspect.getsource(module)
        import_lines = "\n".join(line for line in source.splitlines() if line.startswith("import ") or line.startswith("from "))
        for token in _FORBIDDEN_IMPORT_TOKENS:
            assert token not in import_lines, f"{module.__name__} must never import {token!r}"


def test_index_never_writes_under_campaign_output_dir(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    case_dir = tmp_path / "runs" / triangle_s1.case_id
    before_run_json = (case_dir / "run.json").read_bytes()
    before_records = (case_dir / "records.jsonl").read_bytes()

    build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)

    assert (case_dir / "run.json").read_bytes() == before_run_json
    assert (case_dir / "records.jsonl").read_bytes() == before_records


# ---------------------------------------------------------------------------
# Deep immutability correctif (1B-9b correctif): every document exposed
# through LoadedCase.documents / IndexedSpectralGroup.documents must be
# unmodifiable at every nesting level, and mutating whatever the caller
# separately holds a reference to (before or after loading) must never
# alter the already-built LoadedCase/index.
# ---------------------------------------------------------------------------


def _loaded_documents(monkeypatch, real_manifest, case, tmp_path: Path, documents: list[dict]):
    _write_case(tmp_path, case, documents)
    _patch_plan(monkeypatch, (case,))
    loaded = load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    return loaded[0].documents


def test_top_level_document_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    assert isinstance(loaded_documents[0], MappingProxyType)
    with pytest.raises(TypeError):
        loaded_documents[0]["record_kind"] = "tampered"


def test_nested_identity_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    with pytest.raises(TypeError):
        loaded_documents[0]["identity"]["spin"] = 999


def test_nested_spectral_group_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    with pytest.raises(TypeError):
        loaded_documents[0]["identity"]["spectral_group"]["twice_T"] = 999


def test_hamiltonian_j_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    J = loaded_documents[0]["identity"]["hamiltonian"]["J"]
    assert isinstance(J, tuple)
    with pytest.raises(TypeError):
        J[0] = 999.0


def test_provenance_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    with pytest.raises(TypeError):
        loaded_documents[0]["provenance"]["scientific_seed"] = 0


def test_nested_payload_mutation_is_impossible(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    loaded_documents = _loaded_documents(monkeypatch, real_manifest, triangle_s1, tmp_path, documents)

    translation_document = next(
        d for d in loaded_documents if d["record_kind"] == "symmetry_label" and d["observable_kind"] == "translation_character"
    )
    assert isinstance(translation_document["payload"]["value"], MappingProxyType)
    with pytest.raises(TypeError):
        translation_document["payload"]["value"]["real"] = 999.0


def test_freeze_document_is_isolated_from_later_mutation_of_the_source() -> None:
    """Directly exercises loader._freeze_document's own isolation
    guarantee: it builds an entirely new, non-aliased structure, so
    mutating the original dict/list after freezing can never reach the
    frozen copy."""
    raw = {"identity": {"spin": 1, "nested": {"a": [1, 2, 3]}}, "record_kind": "raw_observable"}
    frozen = loader_module._freeze_document(raw)

    raw["identity"]["spin"] = 999
    raw["identity"]["nested"]["a"].append(4)
    raw["record_kind"] = "tampered"

    assert frozen["identity"]["spin"] == 1
    assert frozen["identity"]["nested"]["a"] == (1, 2, 3)
    assert frozen["record_kind"] == "raw_observable"


def test_loaded_case_documents_unaffected_by_mutating_the_original_source_list(
    monkeypatch, real_manifest, triangle_s1, tmp_path: Path
) -> None:
    """Same guarantee at the load_validated_cases/LoadedCase level: the
    list load_case_records "returns" is mutated by the test itself
    immediately after loading -- the already-built LoadedCase must be
    completely unaffected (no alias, no shared reference, of any kind)."""
    source_documents = list(
        _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    )
    monkeypatch.setattr(
        loader_module, "validate_existing_case_run", lambda *args, **kwargs: CaseRunValidation(is_valid=True, reason=None)
    )
    monkeypatch.setattr(loader_module, "load_case_records", lambda case_dir: source_documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    loaded = load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    original_spin = loaded[0].documents[0]["identity"]["spin"]
    original_count = len(loaded[0].documents)

    source_documents[0]["identity"]["spin"] = 999999
    source_documents[0]["record_kind"] = "tampered"
    source_documents.append({"tampered": True})

    assert loaded[0].documents[0]["identity"]["spin"] == original_spin
    assert loaded[0].documents[0]["record_kind"] != "tampered"
    assert len(loaded[0].documents) == original_count


def test_document_order_preserved_after_freezing(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    case_dir = tmp_path / "runs" / triangle_s1.case_id
    raw_order = [(d["record_kind"], d["observable_kind"]) for d in load_case_records(case_dir)]

    loaded = load_validated_cases(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    frozen_order = [(d["record_kind"], d["observable_kind"]) for d in loaded[0].documents]

    assert frozen_order == raw_order


def test_indexed_spectral_group_documents_are_also_deeply_frozen(monkeypatch, real_manifest, triangle_s1, tmp_path: Path) -> None:
    documents = _default_group_documents(triangle_s1, _group(0, twice_T=1), manifest=real_manifest, twice_T_label=1.0)
    _write_case(tmp_path, triangle_s1, documents)
    _patch_plan(monkeypatch, (triangle_s1,))

    index = build_campaign_artifact_index(real_manifest, tmp_path, repository_commit=REPO_COMMIT)
    group_document = index.groups[0].documents[0]
    assert isinstance(group_document, MappingProxyType)
    with pytest.raises(TypeError):
        group_document["identity"]["spin"] = 999


def test_loaded_case_rejects_non_frozen_documents_at_construction(triangle_s1) -> None:
    with pytest.raises(ValueError, match="MappingProxyType"):
        LoadedCase(case=triangle_s1, documents=({"not": "frozen"},))
