from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.level1.manifest import Manifest, load_manifest
from experiments.level1.planning import build_campaign_plan
from experiments.level1c import manifest as level1c_manifest_module
from experiments.level1c.case_artifact import (
    Level1CCaseRunArtifact,
    canonical_json_bytes,
    required_targets_are_satisfied,
    to_json_dict,
)
from experiments.level1c.target_selection import TargetSelectionRecord
from scripts.level1b_analysis.indexing import CampaignArtifactIndex, build_campaign_artifact_index
from scripts.level1c_baseline_gate.gate import (
    HISTORICAL_REPOSITORY_COMMIT,
    GroupStructuralData,
    historical_group_structural_data,
)

REAL_HISTORICAL_OUTPUT_DIR = Path("/workspaces/level1b_campaign_output")
REPO_COMMIT = "79c0b8b8a5f2208acb6c4b8776ef6323ad8bbd98"

_GEOMETRY_NODE_COUNTS = {"triangle": 3, "ring5": 5}


@pytest.fixture(scope="session")
def historical_manifest() -> Manifest:
    return load_manifest()


@pytest.fixture(scope="session")
def historical_index(historical_manifest: Manifest) -> CampaignArtifactIndex:
    """Real, read-only, already-accepted Level1B historical archive --
    no diagonalization (build_campaign_artifact_index only loads and
    validates already-persisted JSON)."""
    return build_campaign_artifact_index(historical_manifest, REAL_HISTORICAL_OUTPUT_DIR, repository_commit=HISTORICAL_REPOSITORY_COMMIT)


@pytest.fixture(scope="session")
def historical_case_ids(historical_manifest: Manifest) -> dict[tuple[str, int], str]:
    result = {}
    for case in build_campaign_plan(historical_manifest):
        if case.hamiltonian_case_id == "reference" and case.geometry in ("triangle", "ring5") and case.spin in (2, 3):
            result[(case.geometry, case.spin)] = case.case_id
    return result


def real_historical_group_data(historical_index: CampaignArtifactIndex, case_id: str, group_index: int) -> GroupStructuralData:
    group = next(g for g in historical_index.groups if g.case_id == case_id and g.spectral_window_group_index == group_index)
    return historical_group_structural_data(group)


@pytest.fixture(scope="session")
def level1c_manifest() -> level1c_manifest_module.Level1CManifest:
    return level1c_manifest_module.load_manifest()


def _target_selection_record(target_id: str, role: str, group_index: int, twice_T: int) -> TargetSelectionRecord:
    return TargetSelectionRecord(
        target_id=target_id,
        role=role,
        selection_status="selected",
        spectral_window_group_index=group_index,
        selected_group_status="complete_multiplet",
        meets_normative_requirements=True,
    )


def _symmetry_label_payload(label) -> dict:
    if label.kind == "numeric":
        return {"kind": "numeric", "value": {"real": label.value.real, "imag": label.value.imag}}
    return {"kind": label.kind, "value": None}


def _group_documents(
    *, geometry: str, spin: int, repository_commit: str, manifest_fingerprint: str, campaign_id: str, group_index: int, data: GroupStructuralData
) -> list[dict]:
    n_nodes = _GEOMETRY_NODE_COUNTS[geometry]
    spectral_group_payload = {
        "status": "complete_multiplet",
        "multiplicity": data.multiplicity,
        "twice_T": data.twice_T,
        "spectral_window_group_index": group_index,
        "group_start_index": group_index * 2,
        "group_end_index_exclusive": group_index * 2 + max(data.multiplicity, 1),
        "representative_energy": data.representative_energy,
    }
    hamiltonian_payload = {"J": [1.0] * n_nodes, "h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0}

    def _base_identity(path, flavor_component=None, normalization=None) -> dict:
        return {
            "geometry": geometry,
            "spin": spin,
            "n_flavors": 2,
            "hamiltonian": hamiltonian_payload,
            "sector": "default",
            "spectral_group": spectral_group_payload,
            "path": list(path) if path is not None else None,
            "flavor_component": flavor_component,
            "normalization": normalization,
        }

    def _base_provenance() -> dict:
        return {
            "spectral_status": "complete_multiplet",
            "source_type": "test_fixture",
            "source_module": "tests.scripts.level1c_baseline_gate.conftest",
            "scientific_seed": 0,
            "solver_seed": 0,
            "validation_rotation_seed": None,
        }

    def _document(record_kind, observable_kind, payload, path=None) -> dict:
        return {
            "schema_version": "level1c-result-record-v1",
            "repository_commit": repository_commit,
            "manifest_fingerprint": manifest_fingerprint,
            "campaign_id": campaign_id,
            "identity": _base_identity(path),
            "provenance": _base_provenance(),
            "record_kind": record_kind,
            "observable_kind": observable_kind,
            "payload": payload,
        }

    documents = [
        _document("symmetry_label", "flavor_casimir_label", {"kind": "numeric", "value": {"real": float(data.twice_T), "imag": 0.0}}),
        _document("symmetry_label", "translation_character", _symmetry_label_payload(data.translation_label)),
        _document("symmetry_label", "reflection_character", _symmetry_label_payload(data.reflection_label)),
    ]
    for (i, j), value in data.ctt_pairs.items():
        documents.append(_document("raw_observable", "C_TT_conn", value, path=(i, j)))
    for (i, j), (value, null_reason) in data.rho_pairs.items():
        documents.append(_document("normalized_observable", "rho_QQ", {"value": value, "null_reason": null_reason}, path=(i, j)))
    return documents


def write_fake_level1c_baseline_case(
    output_dir: Path,
    *,
    case_id: str,
    geometry: str,
    spin: int,
    hamiltonian_case_id: str,
    manifest_fingerprint: str,
    campaign_id: str,
    repository_commit: str,
    target_group_data: dict[str, tuple[int, GroupStructuralData]],
    role_by_target: dict[str, str],
) -> None:
    """Writes a schema-valid, self-consistent Level1C runs/<case_id>/
    {run.json,records.jsonl} pair built entirely from already-known
    GroupStructuralData -- never via run_level1c_case, never via any
    diagonalization."""
    documents: list[dict] = []
    seen_group_indices: set[int] = set()
    for target_id, (group_index, data) in target_group_data.items():
        if group_index in seen_group_indices:
            continue
        seen_group_indices.add(group_index)
        documents.extend(
            _group_documents(
                geometry=geometry,
                spin=spin,
                repository_commit=repository_commit,
                manifest_fingerprint=manifest_fingerprint,
                campaign_id=campaign_id,
                group_index=group_index,
                data=data,
            )
        )

    target_selections = tuple(
        _target_selection_record(target_id, role_by_target[target_id], group_index, data.twice_T)
        for target_id, (group_index, data) in target_group_data.items()
    )

    records_bytes = b"".join(
        (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        for document in documents
    )
    records_sha256 = hashlib.sha256(records_bytes).hexdigest()

    artifact = Level1CCaseRunArtifact(
        schema_version="level1c-case-run-v1",
        campaign_id=campaign_id,
        manifest_fingerprint=manifest_fingerprint,
        repository_commit=repository_commit,
        case_id=case_id,
        geometry=geometry,
        spin=spin,
        hamiltonian_case_id=hamiltonian_case_id,
        sector_id="default",
        spectral_window=99,
        run_status="success",
        target_selections=target_selections,
        records_sha256=records_sha256,
        record_count=len(documents),
        normative_case_valid=required_targets_are_satisfied(target_selections),
    )

    case_dir = output_dir / "runs" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "records.jsonl").write_bytes(records_bytes)
    (case_dir / "run.json").write_bytes(canonical_json_bytes(to_json_dict(artifact)))
