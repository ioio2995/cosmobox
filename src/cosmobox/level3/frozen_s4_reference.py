"""Loader/adapter for the frozen Level3 S4 reference campaign
(results/level3/level3-s4-truncation-extension-v1/), the sole normative
source of S=4 data for the Level3 S5 campaign (lot L3-P).

Mirrors cosmobox.level3.frozen_reference (the Level2 loader, L3-I)
exactly, one layer up: every function here reads already-persisted,
already-versioned artifacts (frozen by lot L3-L,
results/level3/level3-s4-truncation-extension-v1/SHA256SUMS) and never
recomputes anything -- no cosmobox.level3.execution.run_case call, no
diagonalization, no Hamiltonian, anywhere in this module. Any missing
file, SHA-256 mismatch, schema failure, or provenance mismatch raises
FrozenS4ReferenceIntegrityError -- there is no fallback and no silent
recomputation path.

reconstruct_case_execution_result rebuilds a
cosmobox.level3.execution.CaseExecutionResult byte-faithful to the
persisted S=4 case-result artifact, suitable for
cosmobox.level3.execution.compare_spin_pair without any modification to
that module. c_tt_conn/rho_qq are deliberately left unreconstructed
(None), exactly as the Level2 loader does.

frozen_metric_comparison exposes the already-aggregated S3<->S4 values
(delta_hl_s4, direction_s4, t_x_34, c_x_34, d_x_34, ...) directly from
the frozen S4 campaign-summary.json -- these are the S4-side inputs the
S5 campaign-summary needs and must never recompute.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cosmobox.level2 import orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.metrics import Available
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec
from cosmobox.level3.serialization import validate_campaign_summary_document, validate_case_result_document

LEVEL3_S4_REFERENCE_CAMPAIGN_ID = "level3-s4-truncation-extension-v1"
LEVEL3_S4_REFERENCE_MANIFEST_FINGERPRINT = "3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba"
LEVEL3_S4_REFERENCE_REPOSITORY = "ioio2995/cosmobox"
LEVEL3_S4_REFERENCE_REPOSITORY_COMMIT = "ffb49da84111f778e45aa95b6d9e80b45d68f34c"
LEVEL3_S4_REFERENCE_FROZEN_PREREGISTRATION_COMMIT = "1c1d71f07dd6a7399b3965b2bb0acfa5c665991e"
"""Pinned literal identity of the frozen Level3 S4 campaign -- the same
values as experiments.level3.s5_manifest.Level3S4ReferenceIdentity's own
validated constants, duplicated deliberately rather than imported (this
module must be able to verify the manifest's own claims independently,
not merely trust them)."""

LEVEL3_S4_REFERENCE_GEOMETRIES = ("triangle", "ring4", "ring5")
LEVEL3_S4_REFERENCE_SPIN = 4
LEVEL3_S4_REFERENCE_DIMENSIONS: dict[str, int] = {"triangle": 168, "ring4": 572, "ring5": 2008}

_DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "results" / "level3" / LEVEL3_S4_REFERENCE_CAMPAIGN_ID
_SHA256SUMS_NAME = "SHA256SUMS"


class FrozenS4ReferenceIntegrityError(ValueError):
    """Raised for any missing file, SHA-256 mismatch, schema failure, or
    provenance mismatch in the frozen Level3 S4 reference. No fallback
    and no recomputation is ever attempted from this branch."""


def frozen_s4_reference_root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else _DEFAULT_ROOT


def _case_artifact_path(geometry: str, *, root: Path) -> Path:
    return root / "cases" / f"{geometry}-S{LEVEL3_S4_REFERENCE_SPIN}.json"


def verify_sha256sums(root: Path | None = None) -> None:
    """Reads SHA256SUMS (itself never hashed) and verifies every listed
    file hashes exactly as recorded. Raises FrozenS4ReferenceIntegrityError
    on a missing SHA256SUMS, a missing listed file, or any hash
    mismatch."""
    resolved_root = frozen_s4_reference_root(root)
    sums_path = resolved_root / _SHA256SUMS_NAME
    if not sums_path.exists():
        raise FrozenS4ReferenceIntegrityError(f"missing integrity record: {sums_path}")

    for line in sums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            expected_hash, raw_path = line.split(maxsplit=1)
        except ValueError:
            raise FrozenS4ReferenceIntegrityError(f"malformed SHA256SUMS line: {line!r}") from None
        relative_path = raw_path.lstrip(" *")
        target = resolved_root / relative_path
        if not target.exists():
            raise FrozenS4ReferenceIntegrityError(
                f"artifact listed in {sums_path} is missing on disk: {target}"
            )
        actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise FrozenS4ReferenceIntegrityError(
                f"SHA-256 mismatch for {target}: expected {expected_hash}, got {actual_hash} "
                "-- refusing to use a frozen Level3 S4 reference artifact whose bytes have changed"
            )


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FrozenS4ReferenceIntegrityError(f"missing frozen Level3 S4 reference artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FrozenS4ReferenceIntegrityError(
            f"frozen Level3 S4 reference artifact is not valid JSON: {path}: {exc}"
        ) from exc


def _verify_pinned_identity(document: dict, *, path: Path) -> None:
    """Checks every provenance key actually present on `document` against
    the pinned literal identity above -- different document types (the
    manifest snapshot vs. a case-result vs. the campaign-summary) carry
    different subsets of these keys, so only present keys are checked."""
    checks = (
        ("campaign_id", LEVEL3_S4_REFERENCE_CAMPAIGN_ID),
        ("manifest_fingerprint", LEVEL3_S4_REFERENCE_MANIFEST_FINGERPRINT),
        ("repository", LEVEL3_S4_REFERENCE_REPOSITORY),
        ("repository_commit", LEVEL3_S4_REFERENCE_REPOSITORY_COMMIT),
        ("frozen_preregistration_commit", LEVEL3_S4_REFERENCE_FROZEN_PREREGISTRATION_COMMIT),
    )
    for key, expected_value in checks:
        if key in document and document[key] != expected_value:
            raise FrozenS4ReferenceIntegrityError(
                f"{path}: {key}={document[key]!r} does not match the pinned frozen Level3 S4 reference "
                f"identity {expected_value!r}"
            )


def load_manifest_snapshot(*, root: Path | None = None) -> dict:
    """The frozen S4 manifest.json snapshot -- provenance-checked, never
    schema-validated here (it is a raw snapshot of Level3Manifest.raw,
    not itself a case-result/campaign-summary document)."""
    resolved_root = frozen_s4_reference_root(root)
    document = _load_json(resolved_root / "manifest.json")
    _verify_pinned_identity(document, path=resolved_root / "manifest.json")
    return document


def load_campaign_summary(*, root: Path | None = None) -> dict:
    """The frozen S4 campaign-summary.json -- schema-validated against
    schemas/level3/s4-campaign-summary-v1.schema.json (reused unchanged
    via cosmobox.level3.serialization) and provenance-checked."""
    resolved_root = frozen_s4_reference_root(root)
    path = resolved_root / "campaign-summary.json"
    document = _load_json(path)
    validate_campaign_summary_document(document)
    _verify_pinned_identity(document, path=path)
    geometries = {entry["geometry"] for entry in document["geometries"]}
    if geometries != set(LEVEL3_S4_REFERENCE_GEOMETRIES):
        raise FrozenS4ReferenceIntegrityError(
            f"{path}: geometries {sorted(geometries)} do not match the expected "
            f"{sorted(LEVEL3_S4_REFERENCE_GEOMETRIES)}"
        )
    return document


def load_case_result(geometry: str, *, root: Path | None = None) -> dict:
    """One frozen S4 case-result document -- schema-validated against
    schemas/level3/s4-case-result-v1.schema.json (reused unchanged),
    provenance-checked, and cross-checked for geometry/spin/dimension/
    full-spectrum invariants against the frozen L3-C/L3-I reference."""
    if geometry not in LEVEL3_S4_REFERENCE_DIMENSIONS:
        raise ValueError(
            f"geometry={geometry!r} is not one of the three frozen Level3 S4 reference cases "
            f"{sorted(LEVEL3_S4_REFERENCE_DIMENSIONS)}"
        )
    resolved_root = frozen_s4_reference_root(root)
    path = _case_artifact_path(geometry, root=resolved_root)
    document = _load_json(path)
    validate_case_result_document(document)
    _verify_pinned_identity(document, path=path)

    if document["geometry"] != geometry or document["spin"] != LEVEL3_S4_REFERENCE_SPIN:
        raise FrozenS4ReferenceIntegrityError(
            f"{path}: (geometry, spin)=({document['geometry']!r}, {document['spin']!r}) does not match "
            f"the requested ({geometry!r}, {LEVEL3_S4_REFERENCE_SPIN!r})"
        )
    expected_dimension = LEVEL3_S4_REFERENCE_DIMENSIONS[geometry]
    if document["dimension"] != expected_dimension:
        raise FrozenS4ReferenceIntegrityError(
            f"{path}: dimension={document['dimension']} does not match the frozen reference dimension "
            f"{expected_dimension}"
        )
    if document["full_spectrum"] is not True:
        raise FrozenS4ReferenceIntegrityError(f"{path}: full_spectrum must be true")
    if document["solver_method"] != "dense":
        raise FrozenS4ReferenceIntegrityError(f"{path}: solver_method must be 'dense'")
    if document["window_truncated"] is not False:
        raise FrozenS4ReferenceIntegrityError(f"{path}: window_truncated must be false")
    if document["partial_subspace_count"] != 0:
        raise FrozenS4ReferenceIntegrityError(f"{path}: partial_subspace_count must be 0")
    total_multiplicity = sum(entry["multiplicity"] for entry in document["multiplet_entries"])
    if total_multiplicity != document["dimension"]:
        raise FrozenS4ReferenceIntegrityError(
            f"{path}: multiplet multiplicities sum to {total_multiplicity}, expected dimension="
            f"{document['dimension']}"
        )
    return document


def verify_frozen_s4_reference(*, root: Path | None = None) -> None:
    """The single entry point a campaign runner should call before using
    any frozen S4 data: verifies SHA256SUMS, then loads and validates the
    manifest snapshot, the campaign-summary, and all three case-result
    artifacts. Raises FrozenS4ReferenceIntegrityError on the first
    failure -- never a partial, best-effort success."""
    verify_sha256sums(root=root)
    load_manifest_snapshot(root=root)
    load_campaign_summary(root=root)
    for geometry in LEVEL3_S4_REFERENCE_DIMENSIONS:
        load_case_result(geometry, root=root)


# ---------------------------------------------------------------------------
# Reconstruction: frozen S4 case-result JSON -> cosmobox.level3.execution.
# CaseExecutionResult, suitable for compare_spin_pair without modification.
# ---------------------------------------------------------------------------


def _available_from_payload(payload: dict) -> Available:
    return Available(payload["value"], payload["reason"])


def _reconstruct_multiplet_entries(document: dict) -> tuple[MultipletProfileEntry, ...]:
    """Rebuilds the scalar fields of every multiplet entry from the
    persisted document. c_tt_conn/rho_qq are deliberately left at their
    None default: orchestration.analyze_case_metric never reads them."""
    entries = []
    for raw_entry in document["multiplet_entries"]:
        entries.append(
            MultipletProfileEntry(
                energy=raw_entry["energy"],
                multiplicity=raw_entry["multiplicity"],
                epsilon=raw_entry["epsilon"],
                q_start=raw_entry["q_start"],
                q_end=raw_entry["q_end"],
                q_midpoint=raw_entry["q_midpoint"],
                m_tt=raw_entry["m_tt"],
                r_eff=_available_from_payload(raw_entry["r_eff"]),
                a_qq=raw_entry["a_qq"],
                m_qq=_available_from_payload(raw_entry["m_qq"]),
            )
        )
    return tuple(entries)


def reconstruct_case_execution_result(geometry: str, *, root: Path | None = None) -> CaseExecutionResult:
    """Rebuild a Level3 CaseExecutionResult for a frozen S=4 case,
    byte-faithful to the persisted artifact (load_case_result already
    schema-validates and provenance-checks it), suitable for
    cosmobox.level3.execution.compare_spin_pair. Never calls run_case,
    never recomputes C_TT_conn/rho_QQ, never touches the source file."""
    document = load_case_result(geometry, root=root)
    entries = _reconstruct_multiplet_entries(document)
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=LEVEL3_S4_REFERENCE_SPIN),
        dimension=document["dimension"],
        group_count=document["group_count"],
        entries=entries,
        m_tt_analysis=orchestration.analyze_case_metric(entries, "M_TT"),
        r_eff_analysis=orchestration.analyze_case_metric(entries, "R_eff"),
        a_qq_analysis=orchestration.analyze_case_metric(entries, "A_QQ"),
        m_qq_analysis=orchestration.analyze_case_metric(entries, "M_QQ"),
    )


# ---------------------------------------------------------------------------
# Already-aggregated S4 values, read directly (never recomputed).
# ---------------------------------------------------------------------------

_METRIC_JSON_KEY = {"M_TT": "m_tt", "R_eff": "r_eff", "A_QQ": "a_qq", "M_QQ": "m_qq"}


def frozen_metric_comparison(geometry: str, metric: str, *, root: Path | None = None) -> dict:
    """The already-aggregated S3<->S4 comparison for one geometry/metric
    (primary metrics carry delta_hl_s2/s3/s4, direction_s2/s3/s4,
    primary_s3_s4_taxonomy, t_x_23/t_x_34/r_delta_x, c_x_23/d_x_23/
    c_x_34/d_x_34/r_d_x; control metrics carry delta_hl_s2/s3/s4 only),
    read directly from the frozen S4 campaign-summary.json -- never
    recomputed from a reconstructed case."""
    if metric not in orchestration.ALL_METRICS:
        raise ValueError(f"metric must be one of {orchestration.ALL_METRICS}, got {metric!r}")
    if geometry not in LEVEL3_S4_REFERENCE_GEOMETRIES:
        raise ValueError(f"geometry must be one of {LEVEL3_S4_REFERENCE_GEOMETRIES}, got {geometry!r}")
    document = load_campaign_summary(root=root)
    for entry in document["geometries"]:
        if entry["geometry"] == geometry:
            return entry[_METRIC_JSON_KEY[metric]]
    raise FrozenS4ReferenceIntegrityError(f"geometry {geometry!r} not found in the frozen Level3 S4 campaign-summary")
