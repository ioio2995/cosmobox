"""Non-fixture test helpers for the Level1C tracking test suite.

Deliberately NOT named conftest.py, for the exact same reason as
tests/scripts/level1c_baseline_gate/level1c_baseline_gate_helpers.py: a
plain `from conftest import ...` statement in a test module is a
REGULAR Python import keyed by the bare module name "conftest" in
sys.modules, which collides across sibling test directories collected
in the same pytest invocation.

_group_documents/write_level1c_case are deliberately independent
re-implementations of tests/scripts/level1c_baseline_gate/
level1c_baseline_gate_helpers.py's own fixture builders (not imported
across test directories): this is test-only fixture-construction code
with zero scientific content, and this module additionally needs to
attach EXTRA complete_multiplet groups not tied to any real manifest
target (to exercise CLASS_POOL with more than one candidate), which
level1c_baseline_gate_helpers.py's own writer does not need.
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
from experiments.level1c.manifest import J0_BASELINE, hamiltonian_case_id_for_j0
from experiments.level1c.planning import build_level1c_campaign_plan
from experiments.level1c.target_selection import TargetSelectionRecord
from scripts.level1c_baseline_gate.gate import GroupStructuralData

REPO_COMMIT = "79c0b8b8a5f2208acb6c4b8776ef6323ad8bbd98"

_GEOMETRY_NODE_COUNTS = {"triangle": 3, "ring5": 5}


def make_group_structural_data(
    group_index: int,
    *,
    multiplicity: int = 1,
    twice_T: int | None = 1,
    reflection: SymmetryLabel | None = None,
    translation: SymmetryLabel | None = None,
    representative_energy: float = 0.0,
) -> GroupStructuralData:
    """A pure, in-memory GroupStructuralData builder for CLASS_POOL/
    track_target_edge unit tests that never touch disk. Defaults to a
    fully-resolved NUMERIC reflection/translation label."""
    if reflection is None:
        reflection = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))
    if translation is None:
        translation = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))
    return GroupStructuralData(
        spectral_window_group_index=group_index,
        multiplicity=multiplicity,
        twice_T=twice_T,
        translation_label=translation,
        reflection_label=reflection,
        representative_energy=representative_energy,
        ctt_pairs={},
        rho_pairs={},
    )


def real_level1c_case_id(level1c_manifest, geometry: str, spin: int, hamiltonian_case_id: str) -> str:
    """The exact, real case_id build_level1c_campaign_plan(manifest)
    produces for (geometry, spin, hamiltonian_case_id) -- never a
    hand-picked fake id: load_and_verify_case_records requires every
    case_id to resolve to a real planned case."""
    return next(
        case.case_id
        for case in build_level1c_campaign_plan(level1c_manifest)
        if case.geometry == geometry and case.spin == spin and case.hamiltonian_case_id == hamiltonian_case_id
    )


def real_baseline_case_id(level1c_manifest, geometry: str, spin: int) -> str:
    return real_level1c_case_id(level1c_manifest, geometry, spin, hamiltonian_case_id_for_j0(J0_BASELINE))


def _symmetry_label_payload(label: SymmetryLabel) -> dict:
    if label.kind == "numeric":
        return {"kind": "numeric", "value": {"real": label.value.real, "imag": label.value.imag}}
    return {"kind": label.kind, "value": None}


def _hamiltonian_payload_for(hamiltonian_case_id: str, n_nodes: int) -> dict:
    """The exact J array build_level1c_campaign_plan itself builds for
    `hamiltonian_case_id`: J_uniform=1.0 everywhere except node 0, which
    carries the case's own J0 value (parsed back from the 'j0-<value>'
    naming convention -- valid for test fixtures only, never done in
    production code, which keeps J0 as a separate typed field)."""
    j0 = float(hamiltonian_case_id.removeprefix("j0-"))
    return {"J": [j0 if node == 0 else 1.0 for node in range(n_nodes)], "h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0}


def _group_documents(
    *, geometry: str, spin: int, repository_commit: str, manifest_fingerprint: str, campaign_id: str, group_index: int, data: GroupStructuralData, status: str = "complete_multiplet", hamiltonian_case_id: str = "j0-1.00"
) -> list[dict]:
    n_nodes = _GEOMETRY_NODE_COUNTS[geometry]
    spectral_group_payload = {
        "status": status,
        "multiplicity": data.multiplicity,
        "twice_T": data.twice_T,
        "spectral_window_group_index": group_index,
        "group_start_index": group_index * 2,
        "group_end_index_exclusive": group_index * 2 + max(data.multiplicity, 1),
        "representative_energy": data.representative_energy,
    }
    hamiltonian_payload = _hamiltonian_payload_for(hamiltonian_case_id, n_nodes)

    def _base_identity(path) -> dict:
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

    def _base_provenance() -> dict:
        return {
            "spectral_status": status,
            "source_type": "test_fixture",
            "source_module": "tests.scripts.level1c_tracking.level1c_tracking_helpers",
            "scientific_seed": 0,
            "solver_seed": 0,
            "validation_rotation_seed": None,
        }

    def _document(record_kind, observable_kind, payload) -> dict:
        return {
            "schema_version": "level1c-result-record-v1",
            "repository_commit": repository_commit,
            "manifest_fingerprint": manifest_fingerprint,
            "campaign_id": campaign_id,
            "identity": _base_identity(None),
            "provenance": _base_provenance(),
            "record_kind": record_kind,
            "observable_kind": observable_kind,
            "payload": payload,
        }

    return [
        _document("symmetry_label", "flavor_casimir_label", {"kind": "unavailable", "value": None} if data.twice_T is None else {"kind": "numeric", "value": {"real": float(data.twice_T), "imag": 0.0}}),
        _document("symmetry_label", "translation_character", _symmetry_label_payload(data.translation_label)),
        _document("symmetry_label", "reflection_character", _symmetry_label_payload(data.reflection_label)),
    ]


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
    target_group_data: dict[str, tuple[int, GroupStructuralData]],
    role_by_target: dict[str, str],
    extra_groups: dict[int, GroupStructuralData] | None = None,
) -> None:
    """Writes a schema-valid, self-consistent Level1C runs/<case_id>/
    {run.json,records.jsonl} pair from already-known GroupStructuralData
    -- never via run_level1c_case, never via any diagonalization.
    `target_group_data` drives target_selections (and therefore
    normative_case_valid) exactly like scripts.level1c_baseline_gate's
    own test helper; `extra_groups` additionally injects complete_
    multiplet structural groups that are NOT selected by any target --
    exercising SPECTRAL_STRUCTURE_PRODUCTION=ALL_COMPLETE_GROUPS_
    IN_PRODUCTION_WINDOW (section 20.6): CLASS_POOL is built from every
    complete group, not only ones a target happened to select."""
    documents: list[dict] = []
    seen_group_indices: set[int] = set()
    for target_id, (group_index, data) in target_group_data.items():
        if group_index in seen_group_indices:
            continue
        seen_group_indices.add(group_index)
        documents.extend(
            _group_documents(
                geometry=geometry, spin=spin, repository_commit=repository_commit,
                manifest_fingerprint=manifest_fingerprint, campaign_id=campaign_id, group_index=group_index, data=data,
                hamiltonian_case_id=hamiltonian_case_id,
            )
        )
    for group_index, data in (extra_groups or {}).items():
        if group_index in seen_group_indices:
            continue
        seen_group_indices.add(group_index)
        documents.extend(
            _group_documents(
                geometry=geometry, spin=spin, repository_commit=repository_commit,
                manifest_fingerprint=manifest_fingerprint, campaign_id=campaign_id, group_index=group_index, data=data,
                hamiltonian_case_id=hamiltonian_case_id,
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


def write_level1c_failed_case(
    output_dir: Path,
    *,
    case_id: str,
    geometry: str,
    spin: int,
    hamiltonian_case_id: str,
    manifest_fingerprint: str,
    campaign_id: str,
    repository_commit: str,
    run_status: str = "failed",
) -> None:
    """Writes a run.json only (no records.jsonl), mirroring
    scripts.level1c_campaign.outputs.write_case_failure -- for testing
    that a technically-failed perturbed case yields AMBIGUOUS tracking
    outcomes, never a silent exclusion."""
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
        run_status=run_status,
        target_selections=(),
        records_sha256=None,
        record_count=0,
        normative_case_valid=None,
    )
    case_dir = output_dir / "runs" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "run.json").write_bytes(canonical_json_bytes(to_json_dict(artifact)))
