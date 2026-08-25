from __future__ import annotations

import json
from pathlib import Path

import pytest

from aave.evidence import (
    EvidenceValidationError,
    build_claim_graph,
    build_public_preview,
    import_evidence_envelope,
    validate_evidence_envelope,
)


def make_envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "envelope_id": "SYNTH-001",
        "schema_version": "1.0",
        "recorded_at": "2026-08-24T00:00:00Z",
        "source_class": "family_held_artifact",
        "evidence_role": "documentary_record",
        "privacy_tier": "R2",
        "privacy_label": "private_family_only",
        "source_confidence": "private_artifact",
        "consent_scopes": ["private_research"],
        "subject_ids": ["person_synthetic_001"],
        "claim_ids": ["claim_synthetic_001"],
        "provenance": {
            "capture_method": "synthetic_fixture",
            "captured_at": "2026-08-24T00:00:00Z",
            "source_owner": "synthetic",
        },
        "details": {"summary": "Synthetic artifact only."},
    }
    payload.update(overrides)
    return payload


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_private_envelope_import_writes_withheld_public_preview(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    write_json(input_path, make_envelope())

    result = import_evidence_envelope(input_path, tmp_path / "out")

    preview = json.loads(result.public_preview_path.read_text(encoding="utf-8"))
    assert preview["public_release_eligible"] is False
    assert "details" not in preview
    assert result.private_envelope_path.name == "SYNTH-001.evidence.json"


def test_public_preview_requires_all_three_release_conditions() -> None:
    payload = make_envelope(
        privacy_tier="P0",
        privacy_label="public_ok",
        consent_scopes=["public_release"],
        public_summary="Approved synthetic summary.",
    )

    preview = build_public_preview(payload)

    assert preview["public_release_eligible"] is True
    assert preview["public_summary"] == "Approved synthetic summary."


def test_r4_envelope_cannot_grant_public_release() -> None:
    payload = make_envelope(
        privacy_tier="R4",
        privacy_label="raw_dna_never_export",
        consent_scopes=["private_research", "public_release"],
    )

    with pytest.raises(EvidenceValidationError, match="cannot grant public_release"):
        validate_evidence_envelope(payload)


def test_envelope_rejects_secret_and_raw_genotype_keys() -> None:
    payload = make_envelope(details={"access_token": "synthetic", "genotype": "AA"})

    with pytest.raises(EvidenceValidationError, match="prohibited secret/raw-genotype"):
        validate_evidence_envelope(payload)


def test_claim_graph_records_mixed_evidence_without_auto_promotion(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "evidence"
    evidence_directory.mkdir()
    supporting = make_envelope(envelope_id="SYNTH-SUPPORT")
    contradicting = make_envelope(envelope_id="SYNTH-CONTRADICT")
    write_json(evidence_directory / "support.evidence.json", supporting)
    write_json(evidence_directory / "contradict.evidence.json", contradicting)
    claims_path = tmp_path / "claims.json"
    write_json(
        claims_path,
        {
            "claims": [
                {
                    "claim_id": "claim_synthetic_001",
                    "statement": "A synthetic relationship is under review.",
                    "claim_type": "kinship",
                    "privacy_label": "private_family_only",
                    "review_status": "needs_review",
                    "subject_ids": ["person_synthetic_001"],
                    "limitations": ["Synthetic test only."],
                    "evidence_links": [
                        {"envelope_id": "SYNTH-SUPPORT", "relation": "supports"},
                        {
                            "envelope_id": "SYNTH-CONTRADICT",
                            "relation": "contradicts",
                        },
                    ],
                }
            ]
        },
    )

    result = build_claim_graph(evidence_directory, claims_path, tmp_path / "graph")

    graph = json.loads(result.output_path.read_text(encoding="utf-8"))
    claim_node = next(node for node in graph["nodes"] if node["node_type"] == "claim")
    assert graph["automatic_claim_promotion"] is False
    assert claim_node["evidence_state"] == "mixed_evidence"
    assert claim_node["conclusion"] == "human_review_required"


def test_claim_graph_rejects_missing_evidence_reference(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "evidence"
    evidence_directory.mkdir()
    claims_path = tmp_path / "claims.json"
    write_json(
        claims_path,
        {
            "claims": [
                {
                    "claim_id": "claim_synthetic_001",
                    "statement": "A synthetic statement.",
                    "claim_type": "historical",
                    "privacy_label": "private_family_only",
                    "review_status": "draft",
                    "subject_ids": [],
                    "limitations": [],
                    "evidence_links": [
                        {"envelope_id": "MISSING", "relation": "supports"}
                    ],
                }
            ]
        },
    )

    with pytest.raises(EvidenceValidationError, match="missing envelope_id"):
        build_claim_graph(evidence_directory, claims_path, tmp_path / "graph")
