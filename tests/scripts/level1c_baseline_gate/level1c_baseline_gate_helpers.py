"""Non-fixture test helpers for the Level1C baseline gate test suite.

Deliberately NOT named conftest.py: pytest's own conftest.py per-
directory mechanism only namespaces FIXTURES safely across sibling test
directories -- a plain `from conftest import ...` statement in a test
module is a REGULAR Python import keyed by the bare module name
"conftest" in sys.modules, which collides across directories once more
than one test directory with its own conftest.py is collected in the
same pytest invocation (e.g. alongside tests/scripts/level1c_campaign/
conftest.py). Non-fixture helpers therefore live here, under a globally
unique module name, and are imported directly by test files; only
pytest fixtures live in this directory's conftest.py.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.level1c.case_artifact import (
    Level1CCaseRunArtifact,
    canonical_json_bytes,
    required_targets_are_satisfied,
    to_json_dict,
)
from experiments.level1c.manifest import J0_BASELINE, hamiltonian_case_id_for_j0
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.target_selection import TargetSelectionRecord
from scripts.level1b_analysis.indexing import CampaignArtifactIndex
from scripts.level1c_baseline_gate.gate import GroupStructuralData, historical_group_structural_data

REAL_HISTORICAL_OUTPUT_DIR = Path("/workspaces/level1b_campaign_output")
REPO_COMMIT = "79c0b8b8a5f2208acb6c4b8776ef6323ad8bbd98"

_GEOMETRY_NODE_COUNTS = {"triangle": 3, "ring5": 5}


def real_historical_group_data(historical_index: CampaignArtifactIndex, case_id: str, group_index: int) -> GroupStructuralData:
    group = next(g for g in historical_index.groups if g.case_id == case_id and g.spectral_window_group_index == group_index)
    return historical_group_structural_data(group)


def real_level1c_baseline_case_id(level1c_manifest, geometry: str, spin: int) -> str:
    """The exact, real case_id build_level1c_campaign_plan(manifest)
    produces for the J0=1 baseline of (geometry, spin) -- never a
    hand-picked fake id: load_level1c_baseline_case (1C-8d-fix) requires
    every baseline case_id to resolve to a real planned case."""
    baseline_hamiltonian_case_id = hamiltonian_case_id_for_j0(J0_BASELINE)
    return next(
        case.case_id
        for case in build_level1c_campaign_plan(level1c_manifest)
        if case.geometry == geometry and case.spin == spin and case.hamiltonian_case_id == baseline_hamiltonian_case_id
    )


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
            "source_module": "tests.scripts.level1c_baseline_gate.level1c_baseline_gate_helpers",
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
