"""Loader/adapter for the frozen Level2 reference campaign
(results/level2/level2-energy-regime-v1/), the sole normative source of
S=2/S=3 data for the Level3 S4 campaign (lot L3-I).

Every function here reads already-persisted, already-versioned artifacts
(frozen by lot L3-H, results/level2/level2-energy-regime-v1/SHA256SUMS)
and never recomputes anything: no cosmobox.level2.execution.run_case call,
no diagonalization, no Hamiltonian, anywhere in this module. Any missing
file, SHA-256 mismatch, schema failure, or provenance mismatch raises
FrozenReferenceIntegrityError -- there is no fallback and no silent
recomputation path.

reconstruct_case_execution_result rebuilds a
cosmobox.level3.execution.CaseExecutionResult byte-faithful to the
persisted S=2/S=3 case-result artifact, suitable for
cosmobox.level3.execution.compare_spin_pair without any modification to
that module. c_tt_conn/rho_qq are deliberately left unreconstructed
(None): cosmobox.level2.orchestration.analyze_case_metric never reads
them, and this module has no reason to touch what the frozen artifact
already retains untouched on disk.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cosmobox.level2 import orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.metrics import Available
from cosmobox.level2.serialization import validate_campaign_summary_document, validate_case_result_document
from cosmobox.level3.execution import CaseExecutionResult, CaseSpec

LEVEL2_REFERENCE_CAMPAIGN_ID = "level2-energy-regime-v1"
LEVEL2_REFERENCE_MANIFEST_FINGERPRINT = "82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4"
LEVEL2_REFERENCE_REPOSITORY = "ioio2995/cosmobox"
LEVEL2_REFERENCE_REPOSITORY_COMMIT = "1feb03f41f9e73078efbc760dd2cba2b667e2ed0"
LEVEL2_REFERENCE_FROZEN_PREREGISTRATION_COMMIT = "2d4c859db7939da51ee7d919889a18f4c7e229ed"
"""Pinned literal identity of the frozen Level2 campaign -- the same
values as experiments.level3.manifest.Level2ReferenceIdentity's own
validated constants, duplicated deliberately rather than imported (this
module must be able to verify the manifest's own claims independently,
not merely trust them)."""

LEVEL2_REFERENCE_GEOMETRIES = ("triangle", "ring4", "ring5")
LEVEL2_REFERENCE_SPINS = (2, 3)
LEVEL2_REFERENCE_DIMENSIONS: dict[tuple[str, int], int] = {
    ("triangle", 2): 88,
    ("triangle", 3): 128,
    ("ring4", 2): 292,
    ("ring4", 3): 432,
    ("ring5", 2): 1000,
    ("ring5", 3): 1504,
}

_DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "results" / "level2" / LEVEL2_REFERENCE_CAMPAIGN_ID
_SHA256SUMS_NAME = "SHA256SUMS"


class FrozenReferenceIntegrityError(ValueError):
    """Raised for any missing file, SHA-256 mismatch, schema failure, or
    provenance mismatch in the frozen Level2 reference. No fallback and
    no recomputation is ever attempted from this branch."""


def frozen_reference_root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else _DEFAULT_ROOT


def _case_artifact_path(geometry: str, spin: int, *, root: Path) -> Path:
    return root / "cases" / f"{geometry}-S{spin}.json"


def verify_sha256sums(root: Path | None = None) -> None:
    """Reads SHA256SUMS (itself never hashed) and verifies every listed
    file hashes exactly as recorded. Raises FrozenReferenceIntegrityError
    on a missing SHA256SUMS, a missing listed file, or any hash
    mismatch."""
    resolved_root = frozen_reference_root(root)
    sums_path = resolved_root / _SHA256SUMS_NAME
    if not sums_path.exists():
        raise FrozenReferenceIntegrityError(f"missing integrity record: {sums_path}")

    for line in sums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            expected_hash, raw_path = line.split(maxsplit=1)
        except ValueError:
            raise FrozenReferenceIntegrityError(f"malformed SHA256SUMS line: {line!r}") from None
        relative_path = raw_path.lstrip(" *")
        target = resolved_root / relative_path
        if not target.exists():
            raise FrozenReferenceIntegrityError(
                f"artifact listed in {sums_path} is missing on disk: {target}"
            )
        actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise FrozenReferenceIntegrityError(
                f"SHA-256 mismatch for {target}: expected {expected_hash}, got {actual_hash} "
                "-- refusing to use a frozen Level2 reference artifact whose bytes have changed"
            )


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FrozenReferenceIntegrityError(f"missing frozen Level2 reference artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FrozenReferenceIntegrityError(f"frozen Level2 reference artifact is not valid JSON: {path}: {exc}") from exc


def _verify_pinned_identity(document: dict, *, path: Path) -> None:
    """Checks every provenance key actually present on `document` against
    the pinned literal identity above -- different document types (the
    manifest snapshot vs. a case-result vs. the campaign-summary) carry
    different subsets of these keys, so only present keys are checked."""
    checks = (
        ("campaign_id", LEVEL2_REFERENCE_CAMPAIGN_ID),
        ("manifest_fingerprint", LEVEL2_REFERENCE_MANIFEST_FINGERPRINT),
        ("repository", LEVEL2_REFERENCE_REPOSITORY),
        ("repository_commit", LEVEL2_REFERENCE_REPOSITORY_COMMIT),
        ("frozen_preregistration_commit", LEVEL2_REFERENCE_FROZEN_PREREGISTRATION_COMMIT),
    )
    for key, expected_value in checks:
        if key in document and document[key] != expected_value:
            raise FrozenReferenceIntegrityError(
                f"{path}: {key}={document[key]!r} does not match the pinned frozen Level2 reference "
                f"identity {expected_value!r}"
            )


def load_manifest_snapshot(*, root: Path | None = None) -> dict:
    """The frozen Level2 manifest.json snapshot -- provenance-checked,
    never schema-validated here (it is a raw snapshot of
    Level2Manifest.raw, not itself a case-result/campaign-summary
    document)."""
    resolved_root = frozen_reference_root(root)
    document = _load_json(resolved_root / "manifest.json")
    _verify_pinned_identity(document, path=resolved_root / "manifest.json")
    return document


def load_campaign_summary(*, root: Path | None = None) -> dict:
    """The frozen Level2 campaign-summary.json -- schema-validated
    against schemas/level2/campaign-summary-v1.schema.json (reused
    unchanged) and provenance-checked."""
    resolved_root = frozen_reference_root(root)
    path = resolved_root / "campaign-summary.json"
    document = _load_json(path)
    validate_campaign_summary_document(document)
    _verify_pinned_identity(document, path=path)
    geometries = {entry["geometry"] for entry in document["geometries"]}
    if geometries != set(LEVEL2_REFERENCE_GEOMETRIES):
        raise FrozenReferenceIntegrityError(
            f"{path}: geometries {sorted(geometries)} do not match the expected "
            f"{sorted(LEVEL2_REFERENCE_GEOMETRIES)}"
        )
    return document


def load_case_result(geometry: str, spin: int, *, root: Path | None = None) -> dict:
    """One frozen Level2 case-result document -- schema-validated against
    schemas/level2/case-result-v1.schema.json (reused unchanged),
    provenance-checked, and cross-checked for geometry/spin/dimension
    against the frozen L2-A1 reference dimensions."""
    if (geometry, spin) not in LEVEL2_REFERENCE_DIMENSIONS:
        raise ValueError(
            f"(geometry, spin)=({geometry!r}, {spin!r}) is not one of the six frozen Level2 reference cases "
            f"{sorted(LEVEL2_REFERENCE_DIMENSIONS)}"
        )
    resolved_root = frozen_reference_root(root)
    path = _case_artifact_path(geometry, spin, root=resolved_root)
    document = _load_json(path)
    validate_case_result_document(document)
    _verify_pinned_identity(document, path=path)

    if document["geometry"] != geometry or document["spin"] != spin:
        raise FrozenReferenceIntegrityError(
            f"{path}: (geometry, spin)=({document['geometry']!r}, {document['spin']!r}) does not match "
            f"the requested ({geometry!r}, {spin!r})"
        )
    expected_dimension = LEVEL2_REFERENCE_DIMENSIONS[(geometry, spin)]
    if document["dimension"] != expected_dimension:
        raise FrozenReferenceIntegrityError(
            f"{path}: dimension={document['dimension']} does not match the frozen L2-A1 reference "
            f"dimension {expected_dimension}"
        )
    return document


def verify_frozen_reference(*, root: Path | None = None) -> None:
    """The single entry point a campaign runner should call before using
    any frozen Level2 data: verifies SHA256SUMS, then loads and validates
    the manifest snapshot, the campaign-summary, and all six case-result
    artifacts. Raises FrozenReferenceIntegrityError on the first
    failure -- never a partial, best-effort success."""
    verify_sha256sums(root=root)
    load_manifest_snapshot(root=root)
    load_campaign_summary(root=root)
    for geometry, spin in LEVEL2_REFERENCE_DIMENSIONS:
        load_case_result(geometry, spin, root=root)


# ---------------------------------------------------------------------------
# Reconstruction: frozen case-result JSON -> cosmobox.level3.execution.
# CaseExecutionResult, suitable for compare_spin_pair without modification.
# ---------------------------------------------------------------------------


def _available_from_payload(payload: dict) -> Available:
    return Available(payload["value"], payload["reason"])


def _reconstruct_multiplet_entries(document: dict) -> tuple[MultipletProfileEntry, ...]:
    """Rebuilds the scalar fields of every multiplet entry -- q_start/
    q_end/q_midpoint/m_tt/r_eff/a_qq/m_qq/multiplicity/energy/epsilon --
    from the persisted document. c_tt_conn/rho_qq are deliberately left
    at their None default: orchestration.analyze_case_metric never reads
    them, and no primitive this module calls requires them."""
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


def reconstruct_case_execution_result(geometry: str, spin: int, *, root: Path | None = None) -> CaseExecutionResult:
    """Rebuild a Level3 CaseExecutionResult for a frozen S=2/S=3 Level2
    case, byte-faithful to the persisted artifact (load_case_result
    already schema-validates and provenance-checks it), suitable for
    cosmobox.level3.execution.compare_spin_pair. Never calls run_case,
    never recomputes C_TT_conn/rho_QQ, never touches the source file."""
    document = load_case_result(geometry, spin, root=root)
    entries = _reconstruct_multiplet_entries(document)
    return CaseExecutionResult(
        spec=CaseSpec(geometry=geometry, spin=spin),
        dimension=document["dimension"],
        group_count=document["group_count"],
        entries=entries,
        m_tt_analysis=orchestration.analyze_case_metric(entries, "M_TT"),
        r_eff_analysis=orchestration.analyze_case_metric(entries, "R_eff"),
        a_qq_analysis=orchestration.analyze_case_metric(entries, "A_QQ"),
        m_qq_analysis=orchestration.analyze_case_metric(entries, "M_QQ"),
    )


# ---------------------------------------------------------------------------
# Already-aggregated Level2 values, read directly (never recomputed).
# ---------------------------------------------------------------------------

_METRIC_JSON_KEY = {"M_TT": "m_tt", "R_eff": "r_eff", "A_QQ": "a_qq", "M_QQ": "m_qq"}


def frozen_metric_comparison(geometry: str, metric: str, *, root: Path | None = None) -> dict:
    """The already-aggregated Level2 comparison for one geometry/metric
    (primary metrics carry delta_hl_s2/delta_hl_s3/taxonomy/direction_s2/
    direction_s3/c_x_23/d_x_23; control metrics carry delta_hl_s2/
    delta_hl_s3/delta_ml_*/delta_hm_* only), read directly from the
    frozen campaign-summary.json -- never recomputed from a reconstructed
    case."""
    if metric not in orchestration.ALL_METRICS:
        raise ValueError(f"metric must be one of {orchestration.ALL_METRICS}, got {metric!r}")
    if geometry not in LEVEL2_REFERENCE_GEOMETRIES:
        raise ValueError(f"geometry must be one of {LEVEL2_REFERENCE_GEOMETRIES}, got {geometry!r}")
    document = load_campaign_summary(root=root)
    for entry in document["geometries"]:
        if entry["geometry"] == geometry:
            return entry[_METRIC_JSON_KEY[metric]]
    raise FrozenReferenceIntegrityError(f"geometry {geometry!r} not found in the frozen Level2 campaign-summary")
