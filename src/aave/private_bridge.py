"""Validate public-safe receipts produced at the private/public boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA_VERSION = "aave.public-projection-receipt.v1"
BOUNDARY_CONTRACT = "aave-private-public-boundary.v1"
PROJECTION_KINDS = {
    "archive_metadata",
    "evidence_metadata",
    "genome_summary_counts",
    "longitudinal_summary_counts",
    "multimodal_summary_counts",
}
CONTENT_FLAGS = {
    "direct_identifiers",
    "genotypes",
    "health_measurements",
    "local_paths",
    "personal_recollections",
    "private_values",
    "raw_artifacts",
    "source_artifact_hashes",
}
CANNOT_SUPPORT_CODES = {
    "artifact_authenticity",
    "biological_relationship",
    "claim_validation",
    "identity_verification",
    "medical_or_genetic_interpretation",
    "private_source_reconstruction",
}
REQUIRED_CANNOT_SUPPORT_CODES = {
    "claim_validation",
    "identity_verification",
    "medical_or_genetic_interpretation",
    "private_source_reconstruction",
}
TOP_LEVEL_FIELDS = {
    "boundary_contract",
    "cannot_support",
    "consent_scope",
    "contains",
    "human_reviewed",
    "privacy_label",
    "privacy_tier",
    "private_content_withheld",
    "producer",
    "projection_kind",
    "public_projection_sha256",
    "public_projection_item_count",
    "receipt_id",
    "schema_version",
    "source_schema",
}

_RECEIPT_ID_PATTERN = re.compile(r"^rct_[0-9a-f]{32}$")
_SCHEMA_ID_PATTERN = re.compile(r"^aave\.[a-z0-9][a-z0-9.-]{2,85}\.v[1-9][0-9]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class PublicProjectionReceiptError(ValueError):
    """Raised when a boundary receipt is not demonstrably public safe."""


def load_public_projection_receipt(input_path: Path) -> dict[str, Any]:
    """Load and validate one JSON receipt without reading referenced artifacts."""
    try:
        with input_path.open(encoding="utf-8") as input_file:
            payload = json.load(input_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PublicProjectionReceiptError("Receipt must be readable UTF-8 JSON.") from error

    if not isinstance(payload, dict):
        raise PublicProjectionReceiptError("Receipt must contain one JSON object.")
    validate_public_projection_receipt(payload)
    return payload


def validate_public_projection_receipt(payload: dict[str, Any]) -> None:
    """Validate a closed, metadata-only private-to-public projection receipt."""
    if not isinstance(payload, dict):
        raise PublicProjectionReceiptError("Receipt must be an object.")

    supplied_fields = set(payload)
    missing_fields = sorted(TOP_LEVEL_FIELDS - supplied_fields)
    unknown_fields = sorted(supplied_fields - TOP_LEVEL_FIELDS)
    if missing_fields:
        raise PublicProjectionReceiptError(f"Receipt is missing fields: {missing_fields}")
    if unknown_fields:
        raise PublicProjectionReceiptError("Receipt contains unknown fields.")

    _require_exact_value(payload, "schema_version", RECEIPT_SCHEMA_VERSION)
    _require_exact_value(payload, "boundary_contract", BOUNDARY_CONTRACT)
    _require_exact_value(payload, "producer", "aave-private")
    _require_exact_value(payload, "privacy_tier", "P0")
    _require_exact_value(payload, "privacy_label", "public_ok")
    _require_exact_value(payload, "consent_scope", "public_release")
    _require_exact_value(payload, "human_reviewed", True)
    _require_exact_value(payload, "private_content_withheld", True)

    _require_receipt_id(payload["receipt_id"])
    _require_schema_id(payload["source_schema"])

    projection_kind = payload["projection_kind"]
    if not isinstance(projection_kind, str) or projection_kind not in PROJECTION_KINDS:
        raise PublicProjectionReceiptError(
            f"projection_kind must be one of {sorted(PROJECTION_KINDS)}"
        )

    public_projection_sha256 = payload["public_projection_sha256"]
    if not isinstance(public_projection_sha256, str) or not _SHA256_PATTERN.fullmatch(
        public_projection_sha256
    ):
        raise PublicProjectionReceiptError(
            "public_projection_sha256 must be a lowercase SHA-256 digest."
        )

    public_projection_item_count = payload["public_projection_item_count"]
    if (
        isinstance(public_projection_item_count, bool)
        or not isinstance(public_projection_item_count, int)
        or not 0 <= public_projection_item_count <= 1_000_000
    ):
        raise PublicProjectionReceiptError(
            "public_projection_item_count must be an integer from 0 through 1000000."
        )

    contains = payload["contains"]
    if not isinstance(contains, dict):
        raise PublicProjectionReceiptError("contains must be an object.")
    if set(contains) != CONTENT_FLAGS:
        raise PublicProjectionReceiptError(
            f"contains must have exactly these fields: {sorted(CONTENT_FLAGS)}"
        )
    unsafe_flags = sorted(flag for flag, is_present in contains.items() if is_present is not False)
    if unsafe_flags:
        raise PublicProjectionReceiptError(
            "All private-content flags must be false: " + ", ".join(unsafe_flags)
        )

    cannot_support = payload["cannot_support"]
    if not isinstance(cannot_support, list) or not cannot_support:
        raise PublicProjectionReceiptError("cannot_support must be a non-empty array.")
    if not all(isinstance(code, str) for code in cannot_support):
        raise PublicProjectionReceiptError("cannot_support entries must be strings.")
    if len(cannot_support) != len(set(cannot_support)):
        raise PublicProjectionReceiptError("cannot_support entries must be unique.")
    invalid_codes = sorted(set(cannot_support) - CANNOT_SUPPORT_CODES)
    if invalid_codes:
        raise PublicProjectionReceiptError("cannot_support contains unsupported codes.")
    missing_codes = sorted(REQUIRED_CANNOT_SUPPORT_CODES - set(cannot_support))
    if missing_codes:
        raise PublicProjectionReceiptError(
            f"cannot_support is missing required codes: {missing_codes}"
        )


def _require_exact_value(payload: dict[str, Any], field_name: str, expected: object) -> None:
    if payload[field_name] != expected or type(payload[field_name]) is not type(expected):
        raise PublicProjectionReceiptError(f"{field_name} must equal {expected!r}.")


def _require_receipt_id(value: object) -> None:
    if not isinstance(value, str) or not _RECEIPT_ID_PATTERN.fullmatch(value):
        raise PublicProjectionReceiptError(
            "receipt_id must be `rct_` followed by exactly 32 lowercase hexadecimal characters."
        )


def _require_schema_id(value: object) -> None:
    if not isinstance(value, str) or not _SCHEMA_ID_PATTERN.fullmatch(value):
        raise PublicProjectionReceiptError("source_schema must be a versioned AAVE schema ID.")
