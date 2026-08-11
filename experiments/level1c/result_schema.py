"""Validation against the dedicated Level1C result-record schema. Lot
1C-8b.

A thin wrapper mirroring cosmobox.level1.serialization.validate_document's
own pattern (lru_cache'd schema/validator, ValueError listing every
violation) but pointed at schemas/level1c/result-record-v1.schema.json --
never the Level1B schema, and never modifying it. No document-building
helper is provided here: constructing a real Level1C result document
(from an actual diagonalized case) is a future runner lot's job, out of
scope for this manifest/schema/planning lot.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "result-record-v1.schema.json"


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_result_record(document: dict) -> None:
    """Raises ValueError (never a bare jsonschema exception) listing
    every violation, not just the first -- mirrors cosmobox.level1.
    serialization.validate_document exactly."""
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against the Level1C result-record schema: {messages}")
