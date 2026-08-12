"""Atomic persistence for Level2 campaign artifacts.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. CASE_RESULT_PERSISTENCE =
NOT_IMPLEMENTED_IN_THIS_LOT (see cosmobox.level2.serialization's own
module docstring for the exact D2/D4 boundary this defers): only
campaign-summary.json's atomic write is implemented here.

Mirrors experiments/level1c/case_artifact.py::canonical_json_bytes'
canonical JSON convention (sort_keys, indent=2, ensure_ascii,
allow_nan=False, single trailing newline) and scripts/level1c_campaign/
outputs.py's atomic-write pattern (write to a sibling temp file, then
os.rename -- atomic on the same filesystem). Per docs/governance/
current-task.md, campaign artifacts live under `results/level2/...`,
never under `experiments/level2/` (which is library code only, .gitignore
already excludes `results/`).
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


def canonical_json_bytes(document: dict) -> bytes:
    """UTF-8, sort_keys, ensure_ascii, allow_nan=False, single trailing
    newline -- the same convention already used by
    experiments/level1c/case_artifact.py::canonical_json_bytes."""
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def atomic_write_json(path: Path, document: dict) -> None:
    """Write `document` to `path` atomically: serialize to a sibling
    temp file (same directory, so os.rename stays on one filesystem),
    fsync it, then rename over the destination. `path`'s parent
    directory is created if needed. The temp file is removed on any
    failure -- a partially written file is never left where a reader
    could mistake it for `path`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(document)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def campaign_output_dir(output_root: Path, campaign_id: str) -> Path:
    return Path(output_root) / campaign_id


def campaign_summary_path(output_root: Path, campaign_id: str) -> Path:
    return campaign_output_dir(output_root, campaign_id) / "campaign-summary.json"


def write_campaign_summary(output_root: Path, campaign_id: str, document: dict) -> Path:
    """Write campaign-summary.json atomically. Callers must only invoke
    this once campaign completeness has already been fully established
    (gates.validate_campaign_completeness) and `document` has already
    been schema-validated (serialization.campaign_summary_payload does
    this itself) -- this function performs no completeness or schema
    check of its own; it is a pure persistence primitive. Its mere
    existence on disk is the campaign's COMPLETE marker: a campaign that
    fails or is interrupted before this call leaves no
    campaign-summary.json at all."""
    path = campaign_summary_path(output_root, campaign_id)
    atomic_write_json(path, document)
    return path
