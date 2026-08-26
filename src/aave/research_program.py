"""Fail-closed validation for private hypothesis research programs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

RESEARCH_VALIDATION_POLICY_VERSION = "1.0"
RESEARCH_VALIDATION_RECEIPT_NAME = "research_validation_receipt.json"
MAX_RESEARCH_JSON_BYTES = 2 * 1024 * 1024

_REQUIRED_EVIDENCE_ROLES = {
    "contradiction",
    "hypothesis",
    "measured_observation",
    "owner_report",
    "unknown",
}
_ALLOWED_ORIGIN_EVIDENCE_ROLES = {
    "ancestry_array_call",
    "appointment_evidence",
    "array_call",
    "clinical_record_fact",
    "contradiction",
    "family_held_artifact",
    "hypothesis",
    "inference",
    "measured_observation",
    "owner_report",
    "public_association_evidence",
    "public_record",
    "review_decision",
    "unknown",
}
_RANK_BANDS = {"A", "B", "C", "D"}
_EXPECTED_RANK_BANDS = {
    "A": "confirmatory_ready",
    "B": "design_ready_but_access_power_or_replication_pending",
    "C": "exploratory_only",
    "D": "blocked",
}
_MANIFEST_ALLOWED_FIELDS = {
    "schema_version",
    "run_id",
    "created_date",
    "status",
    "question",
    "objective",
    "non_goals",
    "repository_context",
    "privacy",
    "data_and_evidence_allowlist",
    "always_blocked_inputs",
    "evidence_roles",
    "allowed_tools",
    "context_budget",
    "required_controls",
    "intended_outputs",
    "validation_commands",
    "stop_conditions",
    "human_gates",
}
_MANIFEST_PRIVACY_ALLOWED_FIELDS = {
    "sensitivity_ceiling",
    "share_status",
    "external_writes_allowed",
    "public_derivative_allowed",
    "case_data_in_final_chat",
    "case_data_allowed",
    "synthetic_test_data_only",
}
_MANIFEST_REPOSITORY_CONTEXT_ALLOWED_FIELDS = {
    "expected_branch_base",
    "observed_checkout",
    "trusted_head",
    "exact_cleanliness",
}
_MANIFEST_ALLOWLIST_ENTRY_FIELDS = {"lane", "path_scope", "allowed_content"}
_MANIFEST_CONTEXT_BUDGET_ALLOWED_FIELDS = {
    "objectives",
    "bounded_transformations",
    "maximum_attempts",
    "external_writes",
    "maximum_changed_files_before_rescope",
    "case_evidence_policy",
}
_REGISTER_ALLOWED_FIELDS = {
    "schema_version",
    "run_id",
    "privacy_label",
    "share_status",
    "status",
    "evidence_basis",
    "rank_bands",
    "ranking_rule",
    "global_confirmatory_gates",
    "genome_specific_gates",
    "hypotheses",
    "global_cannot_support",
    "global_cannot_support_categories",
}
_EVIDENCE_BASIS_ALLOWED_FIELDS = {
    "case_values_used",
    "raw_sources_opened",
    "reviewed_envelope_values_opened",
    "basis",
    "limitation",
}
_RANKING_RULE_ALLOWED_FIELDS = {"method", "positive_components", "penalties", "rule"}
_HYPOTHESIS_REQUIRED_STRING_FIELDS = {
    "hypothesis_id",
    "version",
    "status",
    "title",
    "falsifiable_statement",
    "explicit_falsifier",
    "candidate_universe",
    "primary_exposure",
    "primary_outcome",
    "time_zero",
    "target_population",
    "estimand",
    "model",
    "smallest_effect_of_interest",
    "power_target",
    "power_result",
    "power_status",
    "multiplicity_family",
    "alpha_or_fdr_method",
    "population_structure_plan",
    "relatedness_plan",
    "batch_plan",
    "participant_overlap_check",
    "participant_overlap_status",
    "access_status",
    "replication_status",
    "multiplicity_status",
    "analysis_status",
    "array_confirmation_status",
    "cannot_support",
    "privacy_label",
    "share_status",
    "access_verified_on",
    "license_or_terms_status",
}
_HYPOTHESIS_REQUIRED_LIST_FIELDS = {
    "origin_evidence_roles",
    "eligibility",
    "exclusions",
    "covariates",
    "negative_controls",
    "sensitivity_analyses",
    "discovery_dataset_candidates",
    "replication_dataset_candidates",
    "contradictions",
    "unknowns",
    "source_urls",
    "cannot_support_categories",
}
_NONEMPTY_HYPOTHESIS_LIST_FIELDS = {
    "origin_evidence_roles",
    "eligibility",
    "covariates",
    "negative_controls",
    "sensitivity_analyses",
    "discovery_dataset_candidates",
    "replication_dataset_candidates",
    "source_urls",
    "cannot_support_categories",
}
_HYPOTHESIS_OPTIONAL_FIELDS = {
    "priority_order",
    "rank_band",
    "reference_build",
    "orientation_status",
    "effect_allele",
    "other_allele",
}
_HYPOTHESIS_ALLOWED_FIELDS = (
    _HYPOTHESIS_REQUIRED_STRING_FIELDS
    | _HYPOTHESIS_REQUIRED_LIST_FIELDS
    | _HYPOTHESIS_OPTIONAL_FIELDS
)
_REQUIRED_CANNOT_SUPPORT_CATEGORIES = {
    "causation",
    "diagnosis",
    "individual_prediction",
    "leaderboard_ranking",
    "n_of_1_significance",
    "payout",
    "prize_qualification",
}
_RANK_A_REQUIRED_STATUSES = {
    "power_status": "completed_adequate",
    "participant_overlap_status": "verified_none",
    "access_status": "verified",
    "replication_status": "independent_completed",
    "multiplicity_status": "locked_and_corrected",
    "analysis_status": "frozen_before_replication",
    "license_or_terms_status": "verified_compatible",
}
_RANK_A_REQUIRED_TEXT_VALUES = {
    "power_result": "prospective_power_completed_at_corrected_alpha",
    "participant_overlap_check": "verified_no_participant_overlap",
}
_FORBIDDEN_KEYS = {
    "access_token",
    "account_id",
    "address",
    "allele_call",
    "api_key",
    "cookie",
    "date_of_birth",
    "dob",
    "email",
    "family_id",
    "full_name",
    "gedcom_id",
    "genotype",
    "genotype_call",
    "local_path",
    "name",
    "password",
    "patient_id",
    "person_id",
    "phone",
    "private_key",
    "private_path",
    "provider_id",
    "raw_dna",
    "refresh_token",
    "session_token",
}
_FORBIDDEN_KEY_TOKENS = {
    "account",
    "address",
    "cookie",
    "email",
    "genotype",
    "name",
    "password",
    "patient",
    "person",
    "phone",
    "provider",
    "secret",
    "token",
}
_UNRESOLVED_MARKERS = {
    "blocked",
    "not_assessed",
    "pending",
    "to_be_identified",
    "to_be_verified",
    "unknown",
    "unresolved",
    "unverified",
}
_CONTRADICTORY_GATE_MARKERS = {
    "access denied",
    "inadequate power",
    "insufficient power",
    "overlap detected",
    "reuse prohibited",
    "underpowered",
    "unusable",
}
_PRIVATE_PATH_PATTERN = re.compile(
    (
        r"(?:\b[A-Za-z]:[\\/]|"
        r"\\\\[^\\]+\\[^\\]+|file://|/(?:home|Users|private/var)/)"
    ),
    re.IGNORECASE,
)
_LONG_DNA_PATTERN = re.compile(r"\b[ACGT]{40,}\b", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_SIGNED_URL_PATTERN = re.compile(
    r"https?://[^\s]+(?:X-Amz-Signature|sig=|signature=|token=)[^\s]*",
    re.IGNORECASE,
)
_GENOTYPE_ROW_PATTERN = re.compile(
    r"(?m)^\s*(?:rs\d+|\d+)\s+(?:[0-9XYMT]+)\s+\d+\s+[ACGTDI-]{1,4}\s*$",
    re.IGNORECASE,
)
_SAFE_LIMIT_VERB_PATTERN = re.compile(
    (
        r"\b(?:cannot|does not|do not|must not|never)\s+"
        r"(?:support(?:s|ed|ing)?|prov(?:e|es|ed|ing)|"
        r"establish(?:es|ed|ing)?|confirm(?:s|ed|ing)?|"
        r"guarantee(?:s|d|ing)?)\b"
    ),
    re.IGNORECASE,
)
_PROHIBITED_CLAIM_PATTERN = re.compile(
    (
        r"\b(?:support(?:s|ed|ing)?|prov(?:e|es|ed|ing)|"
        r"establish(?:es|ed|ing)?|confirm(?:s|ed|ing)?|"
        r"guarantee(?:s|d|ing)?)\b"
    ),
    re.IGNORECASE,
)
_PROHIBITED_PASSIVE_CLAIM_PATTERN = re.compile(
    (
        r"\b(?:an?\s+)?"
        r"(?:diagnosis|causation|replication|prize(?:\s+qualification)?|"
        r"leaderboard\s+ranking|ranking|payout)"
        r"(?:\s*(?:,|and|or)\s*(?:diagnosis|causation|replication|"
        r"prize(?:\s+qualification)?|leaderboard\s+ranking|ranking|payout))*"
        r"\s+(?:is|are|was|were|has\s+been|have\s+been)\s+"
        r"(?:(?:clearly|fully|strongly)\s+)?"
        r"(?:supported|proven|established|confirmed|guaranteed)\b"
    ),
    re.IGNORECASE,
)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ResearchProgramValidationError(ValueError):
    """Raised when private research inputs cannot be safely parsed."""


@dataclass(frozen=True)
class ResearchProgramValidationResult:
    """Summary of one local research-program validation run."""

    status: str
    schema_valid: bool
    promotion_ready: bool
    finding_count: int
    hypothesis_count: int
    output_path: Path


def validate_research_program(
    manifest_path: Path,
    register_path: Path,
    output_directory: Path,
    private_root: Path,
    receipt_nonce: bytes | None = None,
) -> ResearchProgramValidationResult:
    """Validate private research metadata and write a path-free private receipt.

    The receipt binds canonical JSON content. It never authorizes publication,
    submission, scientific promotion, prize qualification, or payment.
    """
    _validate_private_output_location(output_directory, private_root)
    manifest = _load_json_object(manifest_path)
    register = _load_json_object(register_path)
    findings: list[tuple[str, str]] = []

    _validate_manifest(manifest, findings)
    rank_counts = _validate_register(register, findings)
    _scan_forbidden_content(manifest, findings)
    _scan_forbidden_content(register, findings)

    manifest_run_id = manifest.get("run_id")
    register_run_id = register.get("run_id")
    if manifest_run_id != register_run_id:
        _add_finding(findings, "error", "run_id_mismatch")

    hypothesis_count = sum(rank_counts.values())
    if rank_counts["A"] == 0:
        _add_finding(findings, "blocker", "no_confirmatory_ready_hypothesis")

    schema_valid = not any(severity == "error" for severity, _code in findings)
    promotion_ready = schema_valid and not any(
        severity == "blocker" for severity, _code in findings
    )
    status = "ready_for_independent_review" if promotion_ready else "blocked"
    nonce = receipt_nonce if receipt_nonce is not None else secrets.token_bytes(16)
    if len(nonce) < 16:
        raise ResearchProgramValidationError("receipt nonce must contain at least 16 bytes")

    finding_summary = _summarize_findings(findings)
    checks_executed = [
        "private_manifest_schema",
        "private_register_schema",
        "run_binding",
        "privacy_and_share_state",
        "forbidden_key_and_path_scan",
        "hypothesis_rank_and_priority_uniqueness",
        "confirmatory_power_replication_access_gate",
        "genome_build_and_orientation_gate",
        "cannot_support_gate",
    ]
    policy_payload = {
        "policy_version": RESEARCH_VALIDATION_POLICY_VERSION,
        "checks": checks_executed,
        "maximum_input_bytes": MAX_RESEARCH_JSON_BYTES,
        "forbidden_keys": sorted(_FORBIDDEN_KEYS),
        "forbidden_key_tokens": sorted(_FORBIDDEN_KEY_TOKENS),
        "unresolved_markers": sorted(_UNRESOLVED_MARKERS),
        "contradictory_gate_markers": sorted(_CONTRADICTORY_GATE_MARKERS),
        "required_cannot_support_categories": sorted(
            _REQUIRED_CANNOT_SUPPORT_CATEGORIES
        ),
        "rank_a_required_statuses": _RANK_A_REQUIRED_STATUSES,
        "rank_a_required_text_values": _RANK_A_REQUIRED_TEXT_VALUES,
        "allowed_origin_evidence_roles": sorted(_ALLOWED_ORIGIN_EVIDENCE_ROLES),
        "manifest_allowed_fields": sorted(_MANIFEST_ALLOWED_FIELDS),
        "register_allowed_fields": sorted(_REGISTER_ALLOWED_FIELDS),
        "required_hypothesis_string_fields": sorted(_HYPOTHESIS_REQUIRED_STRING_FIELDS),
        "required_hypothesis_list_fields": sorted(_HYPOTHESIS_REQUIRED_LIST_FIELDS),
    }
    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "policy_version": RESEARCH_VALIDATION_POLICY_VERSION,
        "privacy_tier": "R4",
        "share_status": "do_not_share",
        "status": status,
        "schema_valid": schema_valid,
        "promotion_ready": promotion_ready,
        "automated_checks_passed": promotion_ready,
        "human_review_required": True,
        "publication_authorized": False,
        "submission_authorized": False,
        "prize_relevance_verified": False,
        "leaderboard_or_payout_guaranteed": False,
        "hypothesis_count": hypothesis_count,
        "rank_counts": rank_counts,
        "finding_count": len(findings),
        "findings": finding_summary,
        "checks_executed": checks_executed,
        "input_bindings": {
            "manifest_canonical_sha256": _canonical_sha256(manifest),
            "register_canonical_sha256": _canonical_sha256(register),
        },
        "policy_sha256": _canonical_sha256(policy_payload),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "receipt_nonce": nonce.hex(),
        "commitment_algorithm": "sha256(AAVE-RESEARCH-RECEIPT-v1 || nonce || canonical_receipt)",
        "non_proofs": [
            (
                "The receipt does not prove identity, authorship, consent, chronology, "
                "provenance, source authenticity, or scientific truth."
            ),
            (
                "The receipt does not establish diagnosis, causation, replication, "
                "statistical significance, clinical validity, or an individual outcome."
            ),
            (
                "The receipt does not establish prize eligibility, target-project relevance, "
                "acceptance, ranking, award, profit, or payout."
            ),
            (
                "Input hashes and this private nonce must not be published as a substitute "
                "for a separately reviewed clean-room release commitment."
            ),
        ],
    }
    canonical_receipt = _canonical_json(receipt)
    receipt["receipt_commitment_sha256"] = hashlib.sha256(
        b"AAVE-RESEARCH-RECEIPT-v1\x00" + nonce + canonical_receipt
    ).hexdigest()

    output_directory.mkdir(parents=True, exist_ok=True)
    _validate_private_output_location(output_directory, private_root)
    output_path = output_directory / RESEARCH_VALIDATION_RECEIPT_NAME
    _write_private_receipt(receipt, output_path, private_root)
    return ResearchProgramValidationResult(
        status=status,
        schema_valid=schema_valid,
        promotion_ready=promotion_ready,
        finding_count=len(findings),
        hypothesis_count=hypothesis_count,
        output_path=output_path,
    )


def _validate_manifest(
    manifest: dict[str, Any],
    findings: list[tuple[str, str]],
) -> None:
    _reject_unknown_fields(
        manifest,
        _MANIFEST_ALLOWED_FIELDS,
        findings,
        "manifest_unknown_field",
    )
    for field_name in ("run_id", "question", "objective"):
        if not _is_nonempty_string(manifest.get(field_name)):
            _add_finding(findings, "error", "manifest_required_string_missing")
    if manifest.get("schema_version") != "1.0":
        _add_finding(findings, "error", "manifest_schema_version_invalid")

    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict):
        _add_finding(findings, "error", "manifest_privacy_object_missing")
    else:
        _reject_unknown_fields(
            privacy,
            _MANIFEST_PRIVACY_ALLOWED_FIELDS,
            findings,
            "manifest_privacy_unknown_field",
        )
        if privacy.get("sensitivity_ceiling") != "R4":
            _add_finding(findings, "error", "manifest_privacy_tier_not_r4")
        if privacy.get("share_status") != "do_not_share":
            _add_finding(findings, "error", "manifest_share_status_not_do_not_share")
        if privacy.get("external_writes_allowed") is not False:
            _add_finding(findings, "error", "manifest_external_writes_not_disabled")
        if privacy.get("public_derivative_allowed") is not False:
            _add_finding(findings, "error", "manifest_public_derivative_not_disabled")
        if privacy.get("case_data_in_final_chat") is not False:
            _add_finding(findings, "error", "manifest_case_data_not_disabled")

    if not _is_nonempty_list(manifest.get("data_and_evidence_allowlist")):
        _add_finding(findings, "error", "manifest_required_control_list_missing")
    for field_name in ("always_blocked_inputs", "required_controls", "stop_conditions"):
        if not _is_nonempty_string_list(manifest.get(field_name)):
            _add_finding(findings, "error", "manifest_required_control_list_missing")

    for field_name in (
        "non_goals",
        "allowed_tools",
        "intended_outputs",
        "validation_commands",
        "human_gates",
    ):
        field_value = manifest.get(field_name)
        if field_value is not None and not _is_string_list(field_value):
            _add_finding(findings, "error", "manifest_optional_string_list_invalid")

    evidence_roles = manifest.get("evidence_roles")
    if not _is_string_list(evidence_roles):
        _add_finding(findings, "error", "manifest_evidence_roles_invalid")
    elif not _REQUIRED_EVIDENCE_ROLES.issubset(set(evidence_roles)):
        _add_finding(findings, "error", "manifest_evidence_role_separation_incomplete")

    repository_context = manifest.get("repository_context")
    if isinstance(repository_context, dict):
        _reject_unknown_fields(
            repository_context,
            _MANIFEST_REPOSITORY_CONTEXT_ALLOWED_FIELDS,
            findings,
            "manifest_repository_context_unknown_field",
        )
        for field_name in ("expected_branch_base", "observed_checkout", "trusted_head"):
            if not _is_nonempty_string(repository_context.get(field_name)):
                _add_finding(
                    findings,
                    "error",
                    "manifest_repository_context_required_value_missing",
                )
    else:
        _add_finding(findings, "error", "manifest_repository_context_invalid")

    context_budget = manifest.get("context_budget")
    if isinstance(context_budget, dict):
        _reject_unknown_fields(
            context_budget,
            _MANIFEST_CONTEXT_BUDGET_ALLOWED_FIELDS,
            findings,
            "manifest_context_budget_unknown_field",
        )
        if context_budget.get("objectives") != 1:
            _add_finding(findings, "error", "manifest_context_budget_invalid")
        if context_budget.get("bounded_transformations") != 1:
            _add_finding(findings, "error", "manifest_context_budget_invalid")
        maximum_attempts = context_budget.get("maximum_attempts")
        if not _is_positive_int(maximum_attempts) or maximum_attempts > 3:
            _add_finding(findings, "error", "manifest_context_budget_invalid")
        if context_budget.get("external_writes") != 0:
            _add_finding(findings, "error", "manifest_context_budget_invalid")
        maximum_changed_files = context_budget.get("maximum_changed_files_before_rescope")
        if not _is_positive_int(maximum_changed_files) or maximum_changed_files > 10:
            _add_finding(findings, "error", "manifest_context_budget_invalid")
        if not _is_nonempty_string(context_budget.get("case_evidence_policy")):
            _add_finding(findings, "error", "manifest_context_budget_invalid")
    else:
        _add_finding(findings, "error", "manifest_context_budget_invalid")

    allowlist_entries = manifest.get("data_and_evidence_allowlist")
    if isinstance(allowlist_entries, list):
        for entry in allowlist_entries:
            if not isinstance(entry, dict):
                _add_finding(findings, "error", "manifest_allowlist_entry_invalid")
                continue
            _reject_unknown_fields(
                entry,
                _MANIFEST_ALLOWLIST_ENTRY_FIELDS,
                findings,
                "manifest_allowlist_entry_unknown_field",
            )
            for field_name in _MANIFEST_ALLOWLIST_ENTRY_FIELDS:
                if not _is_nonempty_string(entry.get(field_name)):
                    _add_finding(
                        findings,
                        "error",
                        "manifest_allowlist_entry_required_value_missing",
                    )


def _validate_register(
    register: dict[str, Any],
    findings: list[tuple[str, str]],
) -> dict[str, int]:
    _reject_unknown_fields(
        register,
        _REGISTER_ALLOWED_FIELDS,
        findings,
        "register_unknown_field",
    )
    if register.get("schema_version") != "1.0":
        _add_finding(findings, "error", "register_schema_version_invalid")
    if not _is_nonempty_string(register.get("run_id")):
        _add_finding(findings, "error", "register_run_id_missing")
    if register.get("privacy_label") != "R4":
        _add_finding(findings, "error", "register_privacy_tier_not_r4")
    if register.get("share_status") != "do_not_share":
        _add_finding(findings, "error", "register_share_status_not_do_not_share")
    if register.get("status") != "hypothesis_generation_only":
        _add_finding(findings, "error", "register_status_not_hypothesis_generation_only")

    evidence_basis = register.get("evidence_basis")
    if not isinstance(evidence_basis, dict):
        _add_finding(findings, "error", "register_evidence_basis_missing")
    else:
        _reject_unknown_fields(
            evidence_basis,
            _EVIDENCE_BASIS_ALLOWED_FIELDS,
            findings,
            "register_evidence_basis_unknown_field",
        )
        for field_name in ("case_values_used", "raw_sources_opened"):
            if evidence_basis.get(field_name) is not False:
                _add_finding(findings, "error", "register_private_evidence_use_not_disabled")
        for field_name in ("basis", "limitation"):
            if not _is_nonempty_string(evidence_basis.get(field_name)):
                _add_finding(findings, "error", "register_evidence_basis_text_missing")

    rank_bands = register.get("rank_bands")
    if rank_bands != _EXPECTED_RANK_BANDS:
        _add_finding(findings, "error", "register_rank_bands_invalid")

    ranking_rule = register.get("ranking_rule")
    if not isinstance(ranking_rule, dict):
        _add_finding(findings, "error", "register_ranking_rule_invalid")
    else:
        _reject_unknown_fields(
            ranking_rule,
            _RANKING_RULE_ALLOWED_FIELDS,
            findings,
            "register_ranking_rule_unknown_field",
        )
        if ranking_rule.get("method") != "ordinal_hard_gate_then_priority":
            _add_finding(findings, "error", "register_ranking_rule_method_invalid")
        for field_name in ("positive_components", "penalties"):
            if not _is_nonempty_string_list(ranking_rule.get(field_name)):
                _add_finding(findings, "error", "register_ranking_rule_list_invalid")
        if not _is_nonempty_string(ranking_rule.get("rule")):
            _add_finding(findings, "error", "register_ranking_rule_text_invalid")

    for field_name in ("global_confirmatory_gates", "genome_specific_gates"):
        if not _is_nonempty_string_list(register.get(field_name)):
            _add_finding(findings, "error", "register_global_gate_list_invalid")

    global_cannot_support = register.get("global_cannot_support")
    if not _is_nonempty_string(global_cannot_support):
        _add_finding(findings, "error", "register_global_cannot_support_missing")
    else:
        normalized_limit = global_cannot_support.lower()
        for required_term in ("diagnosis", "causation", "replication", "prize", "payout"):
            if required_term not in normalized_limit:
                _add_finding(findings, "error", "register_global_cannot_support_incomplete")
        if _contains_prohibited_claim(global_cannot_support):
            _add_finding(findings, "error", "register_global_cannot_support_contradictory")

    global_cannot_support_categories = register.get("global_cannot_support_categories")
    if not _is_string_list(global_cannot_support_categories):
        _add_finding(findings, "error", "register_cannot_support_categories_invalid")
    elif not _REQUIRED_CANNOT_SUPPORT_CATEGORIES.issubset(
        set(global_cannot_support_categories)
    ):
        _add_finding(findings, "error", "register_cannot_support_categories_incomplete")

    hypotheses = register.get("hypotheses")
    rank_counts = {rank: 0 for rank in sorted(_RANK_BANDS)}
    if not isinstance(hypotheses, list) or not hypotheses:
        _add_finding(findings, "error", "register_hypotheses_missing")
        return rank_counts

    seen_ids: set[str] = set()
    seen_priorities: set[int] = set()
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, dict):
            _add_finding(findings, "error", "hypothesis_not_object")
            continue
        _validate_hypothesis(hypothesis, findings)
        hypothesis_id = hypothesis.get("hypothesis_id")
        if isinstance(hypothesis_id, str):
            normalized_hypothesis_id = hypothesis_id.casefold()
            if normalized_hypothesis_id in seen_ids:
                _add_finding(findings, "error", "hypothesis_id_duplicate")
            seen_ids.add(normalized_hypothesis_id)

        priority = hypothesis.get("priority_order")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 1:
            _add_finding(findings, "error", "hypothesis_priority_invalid")
        else:
            if priority in seen_priorities:
                _add_finding(findings, "error", "hypothesis_priority_duplicate")
            seen_priorities.add(priority)

        rank_band = hypothesis.get("rank_band")
        if rank_band in _RANK_BANDS:
            rank_counts[str(rank_band)] += 1
    return rank_counts


def _validate_hypothesis(
    hypothesis: dict[str, Any],
    findings: list[tuple[str, str]],
) -> None:
    unknown_fields = set(hypothesis) - _HYPOTHESIS_ALLOWED_FIELDS
    for _field_name in unknown_fields:
        _add_finding(findings, "error", "hypothesis_unknown_field")

    for field_name in _HYPOTHESIS_REQUIRED_STRING_FIELDS:
        if not _is_nonempty_string(hypothesis.get(field_name)):
            _add_finding(findings, "error", "hypothesis_required_string_missing")

    for field_name in _HYPOTHESIS_REQUIRED_LIST_FIELDS:
        field_value = hypothesis.get(field_name)
        if not _is_string_list(field_value):
            _add_finding(findings, "error", "hypothesis_required_list_invalid")
        elif field_name in _NONEMPTY_HYPOTHESIS_LIST_FIELDS and not field_value:
            _add_finding(findings, "error", "hypothesis_required_list_empty")

    rank_band = hypothesis.get("rank_band")
    if rank_band not in _RANK_BANDS:
        _add_finding(findings, "error", "hypothesis_rank_band_invalid")
        return
    if hypothesis.get("privacy_label") != "R4":
        _add_finding(findings, "error", "hypothesis_privacy_tier_not_r4")
    if hypothesis.get("share_status") != "do_not_share":
        _add_finding(findings, "error", "hypothesis_share_status_not_do_not_share")

    cannot_support_categories = hypothesis.get("cannot_support_categories")
    if _is_string_list(cannot_support_categories) and not (
        _REQUIRED_CANNOT_SUPPORT_CATEGORIES.issubset(set(cannot_support_categories))
    ):
        _add_finding(findings, "error", "hypothesis_cannot_support_categories_incomplete")
    cannot_support = hypothesis.get("cannot_support")
    if isinstance(cannot_support, str) and _contains_prohibited_claim(cannot_support):
        _add_finding(findings, "error", "hypothesis_cannot_support_contradictory")

    source_urls = hypothesis.get("source_urls")
    if _is_string_list(source_urls):
        if any(not source_url.startswith("https://") for source_url in source_urls):
            _add_finding(findings, "error", "hypothesis_source_url_not_https")
        if any(_url_has_disallowed_components(source_url) for source_url in source_urls):
            _add_finding(findings, "error", "hypothesis_source_url_not_clean")

    evidence_roles = hypothesis.get("origin_evidence_roles")
    if _is_string_list(evidence_roles):
        invalid_roles = set(evidence_roles) - _ALLOWED_ORIGIN_EVIDENCE_ROLES
        if invalid_roles:
            _add_finding(findings, "error", "hypothesis_origin_evidence_role_invalid")

    if rank_band != "A":
        return

    if hypothesis.get("status") != "confirmatory_ready":
        _add_finding(findings, "blocker", "rank_a_status_not_confirmatory_ready")
    for field_name in (
        "power_result",
        "participant_overlap_check",
        "access_verified_on",
        "license_or_terms_status",
    ):
        if _contains_unresolved_marker(hypothesis.get(field_name)):
            _add_finding(findings, "blocker", "rank_a_confirmatory_gate_unresolved")
    if hypothesis.get("unknowns") != []:
        _add_finding(findings, "blocker", "rank_a_unknowns_present")
    for field_name, required_status in _RANK_A_REQUIRED_STATUSES.items():
        if hypothesis.get(field_name) != required_status:
            _add_finding(findings, "blocker", "rank_a_required_status_not_met")
    for field_name, required_value in _RANK_A_REQUIRED_TEXT_VALUES.items():
        if hypothesis.get(field_name) != required_value:
            _add_finding(findings, "blocker", "rank_a_required_text_not_met")
    access_verified_on = hypothesis.get("access_verified_on")
    if not isinstance(access_verified_on, str) or not _ISO_DATE_PATTERN.fullmatch(
        access_verified_on
    ):
        _add_finding(findings, "blocker", "rank_a_access_date_invalid")

    gate_text = " ".join(
        str(hypothesis.get(field_name) or "")
        for field_name in (
            "power_result",
            "participant_overlap_check",
            "access_verified_on",
            "license_or_terms_status",
        )
    ).casefold()
    if any(marker in gate_text for marker in _CONTRADICTORY_GATE_MARKERS):
        _add_finding(findings, "blocker", "rank_a_gate_text_contradictory")

    evidence_roles = hypothesis.get("origin_evidence_roles", [])
    has_array_role = isinstance(evidence_roles, list) and any(
        role in {"array_call", "ancestry_array_call"} for role in evidence_roles
    )
    if has_array_role:
        if hypothesis.get("array_confirmation_status") != "independently_confirmed":
            _add_finding(findings, "blocker", "rank_a_array_confirmation_not_met")
        for field_name in ("reference_build", "orientation_status"):
            if not _is_nonempty_string(hypothesis.get(field_name)):
                _add_finding(findings, "blocker", "rank_a_genome_harmonization_missing")
            elif _contains_unresolved_marker(hypothesis.get(field_name)):
                _add_finding(findings, "blocker", "rank_a_genome_harmonization_unresolved")
    elif hypothesis.get("array_confirmation_status") != "not_applicable":
        _add_finding(findings, "blocker", "rank_a_array_confirmation_status_invalid")


def _scan_forbidden_content(
    value: object,
    findings: list[tuple[str, str]],
) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if _is_forbidden_key(str(key)):
                _add_finding(findings, "error", "forbidden_sensitive_key")
            _scan_forbidden_content(child_value, findings)
        return
    if isinstance(value, list):
        for child_value in value:
            _scan_forbidden_content(child_value, findings)
        return
    if isinstance(value, str):
        if _PRIVATE_PATH_PATTERN.search(value):
            _add_finding(findings, "error", "forbidden_private_path_value")
        if _LONG_DNA_PATTERN.search(value):
            _add_finding(findings, "error", "forbidden_long_dna_sequence")
        if _EMAIL_PATTERN.search(value):
            _add_finding(findings, "error", "forbidden_email_value")
        if _SIGNED_URL_PATTERN.search(value):
            _add_finding(findings, "error", "forbidden_signed_url")
        if _GENOTYPE_ROW_PATTERN.search(value):
            _add_finding(findings, "error", "forbidden_genotype_row")


def _contains_unresolved_marker(value: object) -> bool:
    normalized_value = str(value or "").casefold()
    return any(marker in normalized_value for marker in _UNRESOLVED_MARKERS)


def _summarize_findings(findings: list[tuple[str, str]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for finding in findings:
        counts[finding] = counts.get(finding, 0) + 1
    return [
        {"severity": severity, "code": code, "count": count}
        for (severity, code), count in sorted(counts.items())
    ]


def _add_finding(
    findings: list[tuple[str, str]],
    severity: str,
    code: str,
) -> None:
    findings.append((severity, code))


def _load_json_object(input_path: Path) -> dict[str, Any]:
    try:
        if input_path.is_symlink():
            raise ResearchProgramValidationError("research input must not be a symlink")
        if input_path.stat().st_size > MAX_RESEARCH_JSON_BYTES:
            raise ResearchProgramValidationError("research input exceeds the size limit")
        with input_path.open(encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonfinite_json_number,
            )
    except ResearchProgramValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ResearchProgramValidationError(
            "research input could not be read as a UTF-8 JSON object"
        ) from error
    if not isinstance(payload, dict):
        raise ResearchProgramValidationError("research input must contain a JSON object")
    return payload


def _write_private_receipt(
    payload: object,
    output_path: Path,
    private_root: Path,
) -> None:
    _validate_private_output_location(output_path.parent, private_root)
    if output_path.is_symlink():
        raise ResearchProgramValidationError("receipt destination must not be a link")
    if output_path.exists():
        output_stat = output_path.lstat()
        if _is_link_or_reparse_point(output_path) or output_stat.st_nlink != 1:
            raise ResearchProgramValidationError(
                "receipt destination must be a single-link regular file"
            )
        if not output_path.is_file():
            raise ResearchProgramValidationError("receipt destination must be a file")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=".aave-research-receipt-",
            suffix=".tmp",
            delete=False,
        ) as output_file:
            temporary_path = Path(output_file.name)
            json.dump(payload, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
            output_file.flush()
            os.fsync(output_file.fileno())
        _validate_private_output_location(output_path.parent, private_root)
        if output_path.is_symlink():
            raise ResearchProgramValidationError("receipt destination changed to a link")
        if output_path.exists() and output_path.lstat().st_nlink != 1:
            raise ResearchProgramValidationError(
                "receipt destination changed to a multi-link file"
            )
        os.replace(temporary_path, output_path)
        temporary_path = None
    except ResearchProgramValidationError:
        raise
    except OSError as error:
        raise ResearchProgramValidationError("private receipt could not be written") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_nonempty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


def _is_nonempty_string_list(value: object) -> bool:
    return _is_string_list(value) and bool(value) and all(item.strip() for item in value)


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _reject_unknown_fields(
    payload: dict[str, Any],
    allowed_fields: set[str],
    findings: list[tuple[str, str]],
    finding_code: str,
) -> None:
    for _field_name in set(payload) - allowed_fields:
        _add_finding(findings, "error", finding_code)


def _is_forbidden_key(key: str) -> bool:
    snake_case_key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    normalized_key = re.sub(r"[^a-z0-9]+", "_", snake_case_key.casefold()).strip("_")
    if normalized_key in _FORBIDDEN_KEYS:
        return True
    key_tokens = set(normalized_key.split("_"))
    return bool(key_tokens & _FORBIDDEN_KEY_TOKENS)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    normalized_keys: set[str] = set()
    for key, value in pairs:
        normalized_key = key.casefold()
        if normalized_key in normalized_keys:
            raise ResearchProgramValidationError("research input contains duplicate JSON keys")
        normalized_keys.add(normalized_key)
        payload[key] = value
    return payload


def _reject_nonfinite_json_number(value: str) -> None:
    raise ResearchProgramValidationError("research input contains a non-finite JSON number")


def _contains_prohibited_claim(value: str) -> bool:
    normalized_value = _SAFE_LIMIT_VERB_PATTERN.sub("limits", value)
    has_active_claim = _PROHIBITED_CLAIM_PATTERN.search(normalized_value)
    has_passive_claim = _PROHIBITED_PASSIVE_CLAIM_PATTERN.search(normalized_value)
    return bool(has_active_claim or has_passive_claim)


def _url_has_disallowed_components(value: str) -> bool:
    parsed_url = urlsplit(value)
    return bool(
        parsed_url.scheme != "https"
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    )


def _validate_private_output_location(output_directory: Path, private_root: Path) -> None:
    if _is_unc_path(output_directory) or _is_unc_path(private_root):
        raise ResearchProgramValidationError("private output must not use a UNC path")
    try:
        private_root_absolute = private_root.absolute()
        output_absolute = output_directory.absolute()
        if not private_root_absolute.is_dir():
            raise ResearchProgramValidationError("private root must be an existing directory")
        if output_absolute == private_root_absolute or not output_absolute.is_relative_to(
            private_root_absolute
        ):
            raise ResearchProgramValidationError("private output must be inside private root")

        current_path = output_absolute
        while True:
            if current_path.exists() and _is_link_or_reparse_point(current_path):
                raise ResearchProgramValidationError(
                    "private output path must not contain links or reparse points"
                )
            if current_path == private_root_absolute:
                break
            current_path = current_path.parent

        resolved_private_root = private_root_absolute.resolve(strict=True)
        resolved_output = output_absolute.resolve(strict=False)
        if not resolved_output.is_relative_to(resolved_private_root):
            raise ResearchProgramValidationError(
                "resolved private output must remain inside private root"
            )
    except ResearchProgramValidationError:
        raise
    except OSError as error:
        raise ResearchProgramValidationError(
            "private output boundary could not be verified"
        ) from error


def _is_unc_path(path: Path) -> bool:
    path_text = str(path)
    return path_text.startswith("\\\\") or path_text.startswith("//")


def _is_link_or_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    file_attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(file_attributes & reparse_flag)
