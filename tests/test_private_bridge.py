from __future__ import annotations

import json
from pathlib import Path

import pytest

from aave.cli import main
from aave.private_bridge import (
    PublicProjectionReceiptError,
    validate_public_projection_receipt,
)


def build_synthetic_receipt(**overrides: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": "aave.public-projection-receipt.v1",
        "boundary_contract": "aave-private-public-boundary.v1",
        "receipt_id": "rct_0123456789abcdef0123456789abcdef",
        "producer": "aave-private",
        "source_schema": "aave.synthetic-private-bundle.v1",
        "projection_kind": "multimodal_summary_counts",
        "privacy_tier": "P0",
        "privacy_label": "public_ok",
        "consent_scope": "public_release",
        "human_reviewed": True,
        "private_content_withheld": True,
        "public_projection_sha256": "a" * 64,
        "public_projection_item_count": 3,
        "contains": {
            "raw_artifacts": False,
            "private_values": False,
            "direct_identifiers": False,
            "local_paths": False,
            "source_artifact_hashes": False,
            "genotypes": False,
            "health_measurements": False,
            "personal_recollections": False,
        },
        "cannot_support": [
            "claim_validation",
            "identity_verification",
            "medical_or_genetic_interpretation",
            "private_source_reconstruction",
        ],
    }
    receipt.update(overrides)
    return receipt


def test_valid_synthetic_receipt() -> None:
    validate_public_projection_receipt(build_synthetic_receipt())


@pytest.mark.parametrize(
    "field_name",
    [
        "raw_artifacts",
        "private_values",
        "direct_identifiers",
        "local_paths",
        "source_artifact_hashes",
        "genotypes",
        "health_measurements",
        "personal_recollections",
    ],
)
def test_receipt_rejects_any_private_content_flag(field_name: str) -> None:
    receipt = build_synthetic_receipt()
    contains = dict(receipt["contains"])
    contains[field_name] = True
    receipt["contains"] = contains

    with pytest.raises(PublicProjectionReceiptError, match="must be false"):
        validate_public_projection_receipt(receipt)


def test_receipt_rejects_unknown_private_fields() -> None:
    sensitive_field_name = "private_name_from_invalid_input"
    receipt = build_synthetic_receipt(**{sensitive_field_name: "synthetic"})

    with pytest.raises(PublicProjectionReceiptError, match="unknown fields") as error_info:
        validate_public_projection_receipt(receipt)
    assert sensitive_field_name not in str(error_info.value)


def test_receipt_requires_public_release_classification() -> None:
    receipt = build_synthetic_receipt(privacy_tier="R4", privacy_label="do_not_share")

    with pytest.raises(PublicProjectionReceiptError, match="privacy_tier"):
        validate_public_projection_receipt(receipt)


def test_receipt_rejects_unreviewed_projection() -> None:
    receipt = build_synthetic_receipt(human_reviewed=False)

    with pytest.raises(PublicProjectionReceiptError, match="human_reviewed"):
        validate_public_projection_receipt(receipt)


def test_receipt_rejects_semantic_identifier() -> None:
    receipt = build_synthetic_receipt(receipt_id="synthetic-person-name-001")

    with pytest.raises(PublicProjectionReceiptError, match="exactly 32"):
        validate_public_projection_receipt(receipt)


def test_receipt_rejects_non_string_projection_kind_with_bounded_error() -> None:
    receipt = build_synthetic_receipt(projection_kind=["genome_summary_counts"])

    with pytest.raises(PublicProjectionReceiptError, match="projection_kind"):
        validate_public_projection_receipt(receipt)


def test_receipt_requires_medical_genetic_limitation() -> None:
    receipt = build_synthetic_receipt(
        projection_kind="genome_summary_counts",
        cannot_support=[
            "claim_validation",
            "identity_verification",
            "private_source_reconstruction",
        ],
    )

    with pytest.raises(PublicProjectionReceiptError, match="missing required codes"):
        validate_public_projection_receipt(receipt)


def test_receipt_requires_bounded_cannot_support_codes() -> None:
    receipt = build_synthetic_receipt(cannot_support=["identity_verification"])

    with pytest.raises(PublicProjectionReceiptError, match="missing required codes"):
        validate_public_projection_receipt(receipt)


def test_receipt_does_not_echo_unsupported_limitation_code() -> None:
    sensitive_code = "private_name_from_invalid_limitation"
    receipt = build_synthetic_receipt(
        cannot_support=[
            "claim_validation",
            "identity_verification",
            "medical_or_genetic_interpretation",
            "private_source_reconstruction",
            sensitive_code,
        ]
    )

    with pytest.raises(PublicProjectionReceiptError, match="unsupported codes") as error_info:
        validate_public_projection_receipt(receipt)
    assert sensitive_code not in str(error_info.value)


def test_cli_validates_receipt_without_printing_path_or_digest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt = build_synthetic_receipt()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    exit_code = main(["bridge", "validate-receipt", "--input", str(receipt_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert output.strip() == "Valid public projection receipt."
    assert receipt["receipt_id"] not in output
    assert str(receipt_path) not in output
    assert receipt["public_projection_sha256"] not in output
