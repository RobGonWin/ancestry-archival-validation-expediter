"""Versioned evidence envelopes and human-reviewed claim graph generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EVIDENCE_SCHEMA_VERSION = "1.0"
EVIDENCE_ROLES = {
    "observation",
    "recollection",
    "documentary_record",
    "inference",
    "hypothesis",
}
PRIVACY_TIERS = {"R4", "R3", "R2", "R1", "P0"}
PRIVACY_LABELS = {
    "public_ok",
    "public_summary_only",
    "private_family_only",
    "expert_review_only",
    "do_not_share",
    "living_person_redacted",
    "raw_dna_never_export",
}
SOURCE_CONFIDENCE_LABELS = {
    "confirmed",
    "probable",
    "family_identified",
    "personal_recollection",
    "needs_review",
    "public_secondary",
    "private_artifact",
}
CONSENT_SCOPES = {"private_research", "expert_review", "public_release", "withheld"}
SOURCE_CLASSES = {
    "family_held_artifact",
    "account_capture",
    "user_export",
    "public_archive",
    "public_web_source",
    "research_instrument",
    "first_person_report",
}
CLAIM_RELATIONS = {"supports", "contradicts", "contextualizes"}
CLAIM_REVIEW_STATUSES = {"draft", "needs_review", "human_confirmed", "withdrawn"}

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVE_KEY_TERMS = {
    "access_token",
    "api_key",
    "cookie",
    "cookies",
    "genotype",
    "password",
    "raw_dna",
    "refresh_token",
    "session_token",
}


class EvidenceValidationError(ValueError):
    """Raised when an evidence envelope or claim file violates the local schema."""


@dataclass(frozen=True)
class EvidenceImportResult:
    """Paths written after a valid local evidence envelope import."""

    envelope_id: str
    private_envelope_path: Path
    public_preview_path: Path


@dataclass(frozen=True)
class ClaimGraphResult:
    """Summary of a deterministic claim graph build."""

    claim_count: int
    evidence_count: int
    edge_count: int
    output_path: Path


def validate_evidence_envelope(payload: dict[str, Any]) -> None:
    """Validate one local evidence envelope without performing network access."""
    errors: list[str] = []
    required_strings = (
        "envelope_id",
        "schema_version",
        "recorded_at",
        "source_class",
        "evidence_role",
        "privacy_tier",
        "privacy_label",
        "source_confidence",
    )
    for field_name in required_strings:
        field_value = payload.get(field_name)
        if not isinstance(field_value, str) or not field_value.strip():
            errors.append(f"{field_name} must be a non-empty string")

    _require_allowed_value(payload, "schema_version", {EVIDENCE_SCHEMA_VERSION}, errors)
    _require_allowed_value(payload, "source_class", SOURCE_CLASSES, errors)
    _require_allowed_value(payload, "evidence_role", EVIDENCE_ROLES, errors)
    _require_allowed_value(payload, "privacy_tier", PRIVACY_TIERS, errors)
    _require_allowed_value(payload, "privacy_label", PRIVACY_LABELS, errors)
    _require_allowed_value(
        payload,
        "source_confidence",
        SOURCE_CONFIDENCE_LABELS,
        errors,
    )

    consent_scopes = _require_string_list(payload, "consent_scopes", errors)
    _require_string_list(payload, "subject_ids", errors)
    _require_string_list(payload, "claim_ids", errors)
    invalid_scopes = sorted(set(consent_scopes) - CONSENT_SCOPES)
    if invalid_scopes:
        errors.append(f"consent_scopes contains invalid values: {invalid_scopes}")

    privacy_tier = payload.get("privacy_tier")
    if privacy_tier in {"R4", "R3"} and "public_release" in consent_scopes:
        errors.append(f"{privacy_tier} evidence cannot grant public_release consent")

    evidence_role = payload.get("evidence_role")
    source_confidence = payload.get("source_confidence")
    if evidence_role in {"inference", "hypothesis"} and source_confidence == "confirmed":
        errors.append("inferences and hypotheses cannot use confirmed source confidence")

    integrity_sha256 = payload.get("integrity_sha256")
    if integrity_sha256 is not None:
        if not isinstance(integrity_sha256, str) or not _SHA256_PATTERN.fullmatch(
            integrity_sha256.lower()
        ):
            errors.append("integrity_sha256 must be a 64-character hexadecimal digest")

    local_locator_ref = payload.get("local_locator_ref")
    if local_locator_ref is not None:
        if not isinstance(local_locator_ref, str) or not local_locator_ref.strip():
            errors.append("local_locator_ref must be a non-empty opaque string")
        elif Path(local_locator_ref).is_absolute() or ":\\" in local_locator_ref:
            errors.append("local_locator_ref must not expose an absolute local path")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    else:
        for field_name in ("capture_method", "captured_at", "source_owner"):
            field_value = provenance.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                errors.append(f"provenance.{field_name} must be a non-empty string")

    sensitive_key_paths = find_sensitive_key_paths(payload)
    if sensitive_key_paths:
        errors.append(
            "envelope contains prohibited secret/raw-genotype keys: "
            + ", ".join(sensitive_key_paths)
        )

    if errors:
        raise EvidenceValidationError("; ".join(errors))


def import_evidence_envelope(
    input_path: Path,
    output_directory: Path,
) -> EvidenceImportResult:
    """Validate and normalize a user-supplied local capture into the private vault format."""
    payload = load_json_object(input_path)
    validate_evidence_envelope(payload)

    envelope_id = str(payload["envelope_id"])
    output_directory.mkdir(parents=True, exist_ok=True)
    private_envelope_path = output_directory / f"{envelope_id}.evidence.json"
    public_preview_path = output_directory / f"{envelope_id}.public-preview.json"

    write_json(payload, private_envelope_path)
    write_json(build_public_preview(payload), public_preview_path)
    return EvidenceImportResult(
        envelope_id=envelope_id,
        private_envelope_path=private_envelope_path,
        public_preview_path=public_preview_path,
    )


def build_public_preview(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a deliberately minimal public preview from one private envelope."""
    is_public_release_eligible = (
        payload["privacy_tier"] == "P0"
        and payload["privacy_label"] == "public_ok"
        and "public_release" in payload["consent_scopes"]
    )
    preview: dict[str, Any] = {
        "envelope_id": payload["envelope_id"],
        "schema_version": payload["schema_version"],
        "public_release_eligible": is_public_release_eligible,
        "human_review_required": True,
    }
    if is_public_release_eligible:
        preview.update(
            {
                "recorded_at": payload["recorded_at"],
                "source_class": payload["source_class"],
                "evidence_role": payload["evidence_role"],
                "source_confidence": payload["source_confidence"],
                "public_summary": payload.get("public_summary", ""),
                "source_url": payload.get("source_url"),
            }
        )
    else:
        preview["withheld_reason"] = (
            "Evidence is not P0/public_ok with explicit public_release consent."
        )
    return preview


def build_claim_graph(
    evidence_directory: Path,
    claims_path: Path,
    output_directory: Path,
) -> ClaimGraphResult:
    """Build a claim/evidence graph while leaving conclusions to human review."""
    evidence_payloads = load_evidence_directory(evidence_directory)
    claims_payload = load_json_object(claims_path)
    claims = claims_payload.get("claims")
    if not isinstance(claims, list):
        raise EvidenceValidationError("claims file must contain a claims array")

    evidence_by_id = {str(item["envelope_id"]): item for item in evidence_payloads}
    if len(evidence_by_id) != len(evidence_payloads):
        raise EvidenceValidationError("duplicate envelope_id values were found")

    claim_nodes: list[dict[str, Any]] = []
    evidence_nodes = [
        {
            "node_id": envelope_id,
            "node_type": "evidence",
            "evidence_role": payload["evidence_role"],
            "privacy_tier": payload["privacy_tier"],
            "privacy_label": payload["privacy_label"],
        }
        for envelope_id, payload in sorted(evidence_by_id.items())
    ]
    edges: list[dict[str, str]] = []
    seen_claim_ids: set[str] = set()

    for claim in claims:
        validated_claim = validate_claim(claim, evidence_by_id)
        claim_id = validated_claim["claim_id"]
        if claim_id in seen_claim_ids:
            raise EvidenceValidationError(f"duplicate claim_id: {claim_id}")
        seen_claim_ids.add(claim_id)

        relation_counts = {relation: 0 for relation in sorted(CLAIM_RELATIONS)}
        for link in validated_claim["evidence_links"]:
            relation = link["relation"]
            relation_counts[relation] += 1
            edges.append(
                {
                    "from": link["envelope_id"],
                    "to": claim_id,
                    "relation": relation,
                }
            )

        claim_nodes.append(
            {
                "node_id": claim_id,
                "node_type": "claim",
                "statement": validated_claim["statement"],
                "claim_type": validated_claim["claim_type"],
                "privacy_label": validated_claim["privacy_label"],
                "review_status": validated_claim["review_status"],
                "subject_ids": validated_claim["subject_ids"],
                "limitations": validated_claim["limitations"],
                "relation_counts": relation_counts,
                "evidence_state": summarize_evidence_state(relation_counts),
                "conclusion": "human_review_required",
            }
        )

    graph_payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "generated_from_local_inputs": True,
        "automatic_claim_promotion": False,
        "nodes": [*claim_nodes, *evidence_nodes],
        "edges": sorted(edges, key=lambda edge: (edge["to"], edge["from"], edge["relation"])),
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "claim_graph.json"
    write_json(graph_payload, output_path)
    return ClaimGraphResult(
        claim_count=len(claim_nodes),
        evidence_count=len(evidence_nodes),
        edge_count=len(edges),
        output_path=output_path,
    )


def load_evidence_directory(evidence_directory: Path) -> list[dict[str, Any]]:
    """Load and validate normalized private envelopes in deterministic order."""
    payloads: list[dict[str, Any]] = []
    for evidence_path in sorted(evidence_directory.glob("*.evidence.json")):
        payload = load_json_object(evidence_path)
        validate_evidence_envelope(payload)
        payloads.append(payload)
    return payloads


def validate_claim(
    claim: object,
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate one claim and its explicit evidence relationships."""
    if not isinstance(claim, dict):
        raise EvidenceValidationError("each claim must be an object")
    for field_name in ("claim_id", "statement", "claim_type", "privacy_label", "review_status"):
        field_value = claim.get(field_name)
        if not isinstance(field_value, str) or not field_value.strip():
            raise EvidenceValidationError(f"claim.{field_name} must be a non-empty string")
    if claim["privacy_label"] not in PRIVACY_LABELS:
        raise EvidenceValidationError(
            f"claim privacy_label is invalid: {claim['privacy_label']}"
        )
    if claim["review_status"] not in CLAIM_REVIEW_STATUSES:
        raise EvidenceValidationError(
            f"claim review_status is invalid: {claim['review_status']}"
        )

    subject_ids = claim.get("subject_ids", [])
    limitations = claim.get("limitations", [])
    evidence_links = claim.get("evidence_links", [])
    if not _is_string_list(subject_ids):
        raise EvidenceValidationError("claim.subject_ids must be an array of strings")
    if not _is_string_list(limitations):
        raise EvidenceValidationError("claim.limitations must be an array of strings")
    if not isinstance(evidence_links, list):
        raise EvidenceValidationError("claim.evidence_links must be an array")

    normalized_links: list[dict[str, str]] = []
    for link in evidence_links:
        if not isinstance(link, dict):
            raise EvidenceValidationError("each evidence link must be an object")
        envelope_id = link.get("envelope_id")
        relation = link.get("relation")
        if envelope_id not in evidence_by_id:
            raise EvidenceValidationError(
                f"claim references missing envelope_id: {envelope_id}"
            )
        if relation not in CLAIM_RELATIONS:
            raise EvidenceValidationError(f"invalid claim relation: {relation}")
        normalized_links.append({"envelope_id": envelope_id, "relation": relation})

    return {
        **claim,
        "subject_ids": subject_ids,
        "limitations": limitations,
        "evidence_links": normalized_links,
    }


def summarize_evidence_state(relation_counts: dict[str, int]) -> str:
    """Summarize edge types without deciding whether the claim is true."""
    if relation_counts["supports"] and relation_counts["contradicts"]:
        return "mixed_evidence"
    if relation_counts["contradicts"]:
        return "contradiction_present"
    if relation_counts["supports"]:
        return "support_present"
    if relation_counts["contextualizes"]:
        return "context_only"
    return "no_evidence_links"


def find_sensitive_key_paths(value: object, prefix: str = "") -> list[str]:
    """Find secret and raw-genotype key names without inspecting semantic values."""
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child_value in value.items():
            key_text = str(key).lower()
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key_text in _SENSITIVE_KEY_TERMS:
                findings.append(child_prefix)
            findings.extend(find_sensitive_key_paths(child_value, child_prefix))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            findings.extend(find_sensitive_key_paths(child_value, child_prefix))
    return findings


def load_json_object(input_path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object from a local path."""
    with input_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise EvidenceValidationError(f"{input_path} must contain a JSON object")
    return payload


def write_json(data: object, output_path: Path) -> None:
    """Write stable, human-reviewable JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


def _require_allowed_value(
    payload: dict[str, Any],
    field_name: str,
    allowed_values: set[str],
    errors: list[str],
) -> None:
    field_value = payload.get(field_name)
    if isinstance(field_value, str) and field_value not in allowed_values:
        errors.append(f"{field_name} must be one of {sorted(allowed_values)}")


def _require_string_list(
    payload: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> list[str]:
    field_value = payload.get(field_name)
    if not _is_string_list(field_value):
        errors.append(f"{field_name} must be an array of strings")
        return []
    return field_value


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
