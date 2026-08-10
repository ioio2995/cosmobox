"""Non-fixture test helpers for the Level1C PHASE_R response test suite.

Deliberately NOT named conftest.py, for the same reason as the sibling
level1c_tracking_helpers.py / level1c_baseline_gate_helpers.py modules:
a plain `from conftest import ...` in a test module collides across
sibling test directories collected in the same pytest invocation.

_group_documents/write_level1c_case are deliberately independent
re-implementations of the sibling helper modules' own fixture builders
(not imported across test directories): this module additionally needs
to attach exact, possibly-duplicated raw_observable/normalized_observable
records to a group (to exercise PHASE_R's duplicate/non-finite/pair-set
discipline), which the sibling modules do not need.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cosmobox.level1.matching import SymmetryLabel
from experiments.level1c.case_artifact import (
    Level1CCaseRunArtifact,
    canonical_json_bytes,
    required_targets_are_satisfied,
    to_json_dict,
)
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.target_selection import TargetSelectionRecord

REPO_COMMIT = "79c0b8b8a5f2208acb6c4b8776ef6323ad8bbd98"
NUMERIC_LABEL = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))

_GEOMETRY_NODE_COUNTS = {"triangle": 3, "ring5": 5}


def real_level1c_case_id(level1c_manifest, geometry: str, spin: int, hamiltonian_case_id: str) -> str:
    return next(
        case.case_id
        for case in build_level1c_campaign_plan(level1c_manifest)
        if case.geometry == geometry and case.spin == spin and case.hamiltonian_case_id == hamiltonian_case_id
    )


def symmetry_label_payload(label: SymmetryLabel) -> dict:
    if label.kind == "numeric":
        return {"kind": "numeric", "value": {"real": label.value.real, "imag": label.value.imag}}
    return {"kind": label.kind, "value": None}


def make_target_selection(target_id: str, *, group_index: int | None = None, selected: bool = True, meets_normative: bool | None = True) -> dict:
    if not selected:
        return {
            "target_id": target_id,
            "selection_status": "ambiguous",
            "spectral_window_group_index": None,
            "selected_group_status": None,
            "meets_normative_requirements": None,
        }
    return {
        "target_id": target_id,
        "selection_status": "selected",
        "spectral_window_group_index": group_index,
        "selected_group_status": "complete_multiplet",
        "meets_normative_requirements": meets_normative,
    }


def make_run_document(target_selections: list[dict]) -> dict:
    return {"target_selections": target_selections}


def make_tracking_document(
    *,
    geometry: str = "triangle",
    spin: int = 2,
    baseline_case_id: str = "baseline-case",
    perturbed_case_id: str = "perturbed-case",
    baseline_hamiltonian_case_id: str = "j0-1.00",
    perturbed_hamiltonian_case_id: str = "j0-0.75",
    target_id: str = "fundamental",
    status: str = "TRACKED_ONE_TO_ONE",
    baseline_group_index: int | None = 0,
    baseline_multiplicity: int | None = 1,
    baseline_twice_T: int | None = 0,
    baseline_reflection_label: dict | None = None,
    candidate_group_index: int | None = 5,
    candidate_multiplicity: int | None = 1,
    candidate_twice_T: int | None = 0,
    candidate_reflection_label: dict | None = None,
) -> dict:
    return {
        "geometry": geometry,
        "spin": spin,
        "baseline_case_id": baseline_case_id,
        "perturbed_case_id": perturbed_case_id,
        "baseline_hamiltonian_case_id": baseline_hamiltonian_case_id,
        "perturbed_hamiltonian_case_id": perturbed_hamiltonian_case_id,
        "target_id": target_id,
        "status": status,
        "baseline_group_index": baseline_group_index,
        "baseline_multiplicity": baseline_multiplicity,
        "baseline_twice_T": baseline_twice_T,
        "baseline_reflection_label": symmetry_label_payload(NUMERIC_LABEL) if baseline_reflection_label is None else baseline_reflection_label,
        "candidate_group_index": candidate_group_index,
        "candidate_multiplicity": candidate_multiplicity,
        "candidate_twice_T": candidate_twice_T,
        "candidate_reflection_label": symmetry_label_payload(NUMERIC_LABEL) if candidate_reflection_label is None else candidate_reflection_label,
    }


def _hamiltonian_payload_for(hamiltonian_case_id: str, n_nodes: int) -> dict:
    j0 = float(hamiltonian_case_id.removeprefix("j0-"))
    return {"J": [j0 if node == 0 else 1.0 for node in range(n_nodes)], "h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0}


def build_group_documents(
    *,
    geometry: str,
    spin: int,
    group_index: int,
    multiplicity: int = 1,
    twice_T: int | None = 0,
    reflection: SymmetryLabel = NUMERIC_LABEL,
    translation: SymmetryLabel = NUMERIC_LABEL,
    ctt_records=(),
    rho_records=(),
    repository_commit: str = REPO_COMMIT,
    manifest_fingerprint: str = "fp",
    campaign_id: str = "level1c-j0-response-v1",
    hamiltonian_case_id: str = "j0-1.00",
    status: str = "complete_multiplet",
) -> list[dict]:
    """Builds the three symmetry_label documents for a group plus one
    raw_observable/C_TT_conn document per (i, j, value) in `ctt_records`
    and one normalized_observable/rho_QQ document per (i, j, value,
    null_reason) in `rho_records` -- both are plain sequences (never a
    dict), so a caller may deliberately include the same (i, j) twice to
    exercise the duplicate-pair rejection discipline."""
    n_nodes = _GEOMETRY_NODE_COUNTS[geometry]
    hamiltonian_payload = _hamiltonian_payload_for(hamiltonian_case_id, n_nodes)
    spectral_group_payload = {
        "status": status,
        "multiplicity": multiplicity,
        "twice_T": twice_T,
        "spectral_window_group_index": group_index,
        "group_start_index": group_index * 2,
        "group_end_index_exclusive": group_index * 2 + max(multiplicity, 1),
        "representative_energy": 0.0,
    }

    def _identity(path) -> dict:
        return {
            "geometry": geometry,
            "spin": spin,
            "n_flavors": 2,
            "hamiltonian": hamiltonian_payload,
            "sector": "default",
            "spectral_group": spectral_group_payload,
            "path": list(path) if path is not None else None,
            "flavor_component": None,
            "normalization": None,
        }

    def _provenance() -> dict:
        return {
            "spectral_status": status,
            "source_type": "test_fixture",
            "source_module": "tests.scripts.level1c_response.level1c_response_helpers",
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
            "identity": _identity(path),
            "provenance": _provenance(),
            "record_kind": record_kind,
            "observable_kind": observable_kind,
            "payload": payload,
        }

    documents = [
        _document("symmetry_label", "flavor_casimir_label", {"kind": "unavailable", "value": None} if twice_T is None else {"kind": "numeric", "value": {"real": float(twice_T), "imag": 0.0}}),
        _document("symmetry_label", "translation_character", symmetry_label_payload(translation)),
        _document("symmetry_label", "reflection_character", symmetry_label_payload(reflection)),
    ]
    for i, j, value in ctt_records:
        documents.append(_document("raw_observable", "C_TT_conn", value, path=(i, j)))
    for i, j, value, null_reason in rho_records:
        documents.append(_document("normalized_observable", "rho_QQ", {"value": value, "null_reason": null_reason}, path=(i, j)))
    return documents


def write_level1c_case(
    output_dir: Path,
    *,
    case_id: str,
    geometry: str,
    spin: int,
    hamiltonian_case_id: str,
    manifest_fingerprint: str,
    campaign_id: str,
    repository_commit: str,
    target_group_data: dict[str, tuple[int, dict]],
    role_by_target: dict[str, str],
) -> None:
    """Writes a self-consistent Level1C runs/<case_id>/{run.json,
    records.jsonl} pair. `target_group_data[target_id] = (group_index,
    build_group_documents_kwargs)` -- never via run_level1c_case, never
    via any diagonalization."""
    documents: list[dict] = []
    seen_group_indices: set[int] = set()
    for target_id, (group_index, params) in target_group_data.items():
        if group_index in seen_group_indices:
            continue
        seen_group_indices.add(group_index)
        documents.extend(
            build_group_documents(
                geometry=geometry,
                spin=spin,
                group_index=group_index,
                repository_commit=repository_commit,
                manifest_fingerprint=manifest_fingerprint,
                campaign_id=campaign_id,
                hamiltonian_case_id=hamiltonian_case_id,
                **params,
            )
        )

    target_selections = tuple(
        TargetSelectionRecord(
            target_id=target_id,
            role=role_by_target[target_id],
            selection_status="selected",
            spectral_window_group_index=group_index,
            selected_group_status="complete_multiplet",
            meets_normative_requirements=True,
        )
        for target_id, (group_index, _params) in target_group_data.items()
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
