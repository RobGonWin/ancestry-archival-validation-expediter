from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from aave.cli import main
from aave.research_program import validate_research_program


def build_manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "run_id": "synthetic-research-run",
        "question": "Does a synthetic cohort association replicate?",
        "objective": "Validate a synthetic research-program fixture.",
        "privacy": {
            "sensitivity_ceiling": "R4",
            "share_status": "do_not_share",
            "external_writes_allowed": False,
            "public_derivative_allowed": False,
            "case_data_in_final_chat": False,
        },
        "repository_context": {
            "expected_branch_base": "synthetic-private-branch",
            "observed_checkout": "synthetic-test-checkout",
            "trusted_head": "synthetic-head",
        },
        "data_and_evidence_allowlist": [
            {
                "lane": "synthetic_only",
                "path_scope": "synthetic/**",
                "allowed_content": "Synthetic metadata only.",
            }
        ],
        "always_blocked_inputs": ["Real private records and genotypes."],
        "evidence_roles": [
            "measured_observation",
            "owner_report",
            "hypothesis",
            "contradiction",
            "unknown",
        ],
        "required_controls": ["Independent replication."],
        "stop_conditions": ["Stop on any privacy-boundary failure."],
        "context_budget": {
            "objectives": 1,
            "bounded_transformations": 1,
            "maximum_attempts": 3,
            "external_writes": 0,
            "maximum_changed_files_before_rescope": 10,
            "case_evidence_policy": "Synthetic metadata only.",
        },
    }


def build_hypothesis() -> dict[str, object]:
    return {
        "hypothesis_id": "SYNTH-H01",
        "version": "1.0",
        "priority_order": 1,
        "rank_band": "A",
        "status": "confirmatory_ready",
        "title": "Synthetic cohort replication question",
        "origin_evidence_roles": ["hypothesis"],
        "falsifiable_statement": "A synthetic association meets a frozen criterion.",
        "explicit_falsifier": "The frozen criterion is not met in replication.",
        "candidate_universe": "One synthetic question fixed before results.",
        "primary_exposure": "Synthetic exposure",
        "primary_outcome": "Synthetic outcome",
        "time_zero": "Synthetic baseline",
        "target_population": "Synthetic cohort participants",
        "estimand": "Synthetic adjusted association",
        "eligibility": ["Synthetic inclusion rule"],
        "exclusions": [],
        "covariates": ["Synthetic prespecified covariate"],
        "model": "Prespecified synthetic regression model",
        "smallest_effect_of_interest": "Synthetic standardized effect of 0.10",
        "power_target": "At least 90 percent prospective power",
        "power_result": "prospective_power_completed_at_corrected_alpha",
        "power_status": "completed_adequate",
        "multiplicity_family": "One primary synthetic test",
        "alpha_or_fdr_method": "Holm family-wise error control",
        "population_structure_plan": "Not applicable to this synthetic non-genomic test",
        "relatedness_plan": "Exclude related synthetic records",
        "batch_plan": "Adjust for synthetic site and batch",
        "negative_controls": ["Synthetic negative-control outcome"],
        "sensitivity_analyses": ["Synthetic leave-one-site-out analysis"],
        "discovery_dataset_candidates": ["Synthetic cohort A"],
        "replication_dataset_candidates": ["Synthetic cohort B"],
        "participant_overlap_check": "verified_no_participant_overlap",
        "participant_overlap_status": "verified_none",
        "access_status": "verified",
        "replication_status": "independent_completed",
        "multiplicity_status": "locked_and_corrected",
        "analysis_status": "frozen_before_replication",
        "array_confirmation_status": "not_applicable",
        "contradictions": [],
        "unknowns": [],
        "cannot_support": "Cannot support diagnosis, causation, or an individual conclusion.",
        "cannot_support_categories": [
            "causation",
            "diagnosis",
            "individual_prediction",
            "leaderboard_ranking",
            "n_of_1_significance",
            "payout",
            "prize_qualification",
        ],
        "privacy_label": "R4",
        "share_status": "do_not_share",
        "access_verified_on": "2026-08-25",
        "source_urls": ["https://example.org/synthetic-study"],
        "license_or_terms_status": "verified_compatible",
    }


def build_register() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "run_id": "synthetic-research-run",
        "privacy_label": "R4",
        "share_status": "do_not_share",
        "status": "hypothesis_generation_only",
        "rank_bands": {
            "A": "confirmatory_ready",
            "B": "design_ready_but_access_power_or_replication_pending",
            "C": "exploratory_only",
            "D": "blocked",
        },
        "ranking_rule": {
            "method": "ordinal_hard_gate_then_priority",
            "positive_components": ["synthetic_reproducibility"],
            "penalties": ["synthetic_uncertainty"],
            "rule": "Synthetic hard gates control promotion.",
        },
        "evidence_basis": {
            "case_values_used": False,
            "raw_sources_opened": False,
            "basis": "Synthetic metadata only.",
            "limitation": "No case evidence is represented.",
        },
        "global_confirmatory_gates": ["Synthetic confirmatory gate"],
        "genome_specific_gates": ["Synthetic genome gate"],
        "hypotheses": [build_hypothesis()],
        "global_cannot_support": (
            "Cannot support diagnosis, causation, replication from a private case, "
            "prize qualification, or payout."
        ),
        "global_cannot_support_categories": [
            "causation",
            "diagnosis",
            "individual_prediction",
            "leaderboard_ranking",
            "n_of_1_significance",
            "payout",
            "prize_qualification",
        ],
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_fixture(
    tmp_path: Path,
    manifest: dict[str, object] | None = None,
    register: dict[str, object] | None = None,
    output_name: str = "verification",
):
    manifest_path = tmp_path / f"{output_name}-manifest.json"
    register_path = tmp_path / f"{output_name}-register.json"
    write_json(manifest_path, manifest or build_manifest())
    write_json(register_path, register or build_register())
    result = validate_research_program(
        manifest_path=manifest_path,
        register_path=register_path,
        output_directory=tmp_path / output_name,
        private_root=tmp_path,
        receipt_nonce=b"synthetic-fixed-nonce-32-bytes!",
    )
    receipt = json.loads(result.output_path.read_text(encoding="utf-8"))
    return result, receipt


def finding_codes(receipt: dict[str, object]) -> set[str]:
    findings = receipt["findings"]
    assert isinstance(findings, list)
    return {str(finding["code"]) for finding in findings}


def test_valid_synthetic_program_is_ready_only_for_independent_review(
    tmp_path: Path,
) -> None:
    result, receipt = validate_fixture(tmp_path)

    assert result.status == "ready_for_independent_review"
    assert result.schema_valid is True
    assert result.promotion_ready is True
    assert receipt["automated_checks_passed"] is True
    assert receipt["human_review_required"] is True
    assert receipt["publication_authorized"] is False
    assert receipt["submission_authorized"] is False
    assert receipt["prize_relevance_verified"] is False
    assert receipt["leaderboard_or_payout_guaranteed"] is False
    assert len(receipt["policy_sha256"]) == 64
    assert len(receipt["implementation_sha256"]) == 64


def test_receipt_is_path_free_and_does_not_replay_input_values(tmp_path: Path) -> None:
    _result, receipt = validate_fixture(tmp_path)
    receipt_text = json.dumps(receipt)

    assert str(tmp_path) not in receipt_text
    assert "Synthetic cohort replication question" not in receipt_text
    assert "SYNTH-H01" not in receipt_text
    assert "example.org" not in receipt_text
    assert receipt["privacy_tier"] == "R4"
    assert receipt["share_status"] == "do_not_share"


def test_fixed_nonce_produces_deterministic_receipt_and_content_binding(
    tmp_path: Path,
) -> None:
    _first_result, first_receipt = validate_fixture(tmp_path, output_name="first")
    _second_result, second_receipt = validate_fixture(tmp_path, output_name="second")
    assert first_receipt == second_receipt

    changed_register = build_register()
    hypotheses = changed_register["hypotheses"]
    assert isinstance(hypotheses, list)
    assert isinstance(hypotheses[0], dict)
    hypotheses[0]["title"] = "Changed synthetic title"
    _changed_result, changed_receipt = validate_fixture(
        tmp_path,
        register=changed_register,
        output_name="changed",
    )

    assert (
        first_receipt["input_bindings"]["register_canonical_sha256"]
        != changed_receipt["input_bindings"]["register_canonical_sha256"]
    )
    assert first_receipt["receipt_commitment_sha256"] != changed_receipt[
        "receipt_commitment_sha256"
    ]


def test_rank_a_pending_power_or_unknowns_blocks_promotion(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["power_result"] = "pending event counts"
    hypothesis["unknowns"] = ["Replication access unresolved"]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is True
    assert result.promotion_ready is False
    assert result.status == "blocked"
    assert "rank_a_confirmatory_gate_unresolved" in finding_codes(receipt)
    assert "rank_a_unknowns_present" in finding_codes(receipt)
    assert "rank_a_required_text_not_met" in finding_codes(receipt)


def test_missing_required_fields_and_duplicate_ranking_are_rejected(tmp_path: Path) -> None:
    register = build_register()
    first_hypothesis = register["hypotheses"][0]
    assert isinstance(first_hypothesis, dict)
    first_hypothesis.pop("model")
    register["hypotheses"].append(copy.deepcopy(first_hypothesis))

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert {
        "hypothesis_required_string_missing",
        "hypothesis_id_duplicate",
        "hypothesis_priority_duplicate",
    }.issubset(finding_codes(receipt))


def test_private_state_and_sensitive_keys_fail_closed(tmp_path: Path) -> None:
    manifest = build_manifest()
    privacy = manifest["privacy"]
    assert isinstance(privacy, dict)
    privacy["external_writes_allowed"] = True
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["genotype"] = "AA"

    result, receipt = validate_fixture(tmp_path, manifest=manifest, register=register)

    assert result.schema_valid is False
    assert {
        "manifest_external_writes_not_disabled",
        "forbidden_sensitive_key",
    }.issubset(finding_codes(receipt))


def test_adversarial_rank_a_semantics_and_camel_case_keys_are_rejected(
    tmp_path: Path,
) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis.update(
        {
            "power_result": "underpowered and unusable",
            "participant_overlap_check": "overlap detected",
            "access_verified_on": "access denied",
            "license_or_terms_status": "reuse prohibited",
            "cannot_support": "This supports diagnosis and causation",
            "fullName": "Synthetic Private Person",
            "apiKey": "synthetic-secret-value",
            "genotypeCall": "AA",
            "localPath": "C:/private/research.json",
        }
    )

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert {
        "hypothesis_unknown_field",
        "forbidden_sensitive_key",
        "forbidden_private_path_value",
        "hypothesis_cannot_support_contradictory",
        "rank_a_required_status_not_met",
        "rank_a_gate_text_contradictory",
    }.issubset(finding_codes(receipt))


def test_rank_a_array_call_requires_independent_confirmation(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["origin_evidence_roles"] = ["array_call"]
    hypothesis["reference_build"] = "GRCh38"
    hypothesis["orientation_status"] = "harmonized"
    hypothesis["array_confirmation_status"] = "not_applicable"

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is True
    assert result.promotion_ready is False
    assert "rank_a_array_confirmation_not_met" in finding_codes(receipt)


def test_unknown_array_role_alias_is_rejected(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["origin_evidence_roles"] = ["consumer_array_call"]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "hypothesis_origin_evidence_role_invalid" in finding_codes(receipt)


def test_passive_cannot_support_contradiction_is_rejected(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["cannot_support"] = "Diagnosis and causation are supported."

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "hypothesis_cannot_support_contradictory" in finding_codes(receipt)


def test_establishes_cannot_support_contradiction_is_rejected(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["cannot_support"] = (
        "This establishes diagnosis, causation, replication, prize qualification, "
        "leaderboard ranking, and payout."
    )

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "hypothesis_cannot_support_contradictory" in finding_codes(receipt)


def test_adjective_modified_establishes_claim_is_rejected(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["cannot_support"] = (
        "This establishes a clinical diagnosis, genetic causation, statistical replication, "
        "prize qualification, leaderboard ranking, and payout."
    )

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "hypothesis_cannot_support_contradictory" in finding_codes(receipt)


def test_unknown_top_level_and_nested_fields_are_rejected(tmp_path: Path) -> None:
    manifest = build_manifest()
    manifest["neutral_private_value"] = "Synthetic identity-bearing value"
    register = build_register()
    evidence_basis = register["evidence_basis"]
    assert isinstance(evidence_basis, dict)
    evidence_basis["neutral_private_value"] = "Synthetic identity-bearing value"

    result, receipt = validate_fixture(tmp_path, manifest=manifest, register=register)

    assert result.schema_valid is False
    assert {
        "manifest_unknown_field",
        "register_evidence_basis_unknown_field",
    }.issubset(finding_codes(receipt))


def test_nested_objects_in_global_gate_lists_are_rejected(tmp_path: Path) -> None:
    register = build_register()
    register["global_confirmatory_gates"] = [
        {"neutral_private_value": "Synthetic identity-bearing value"}
    ]
    register["genome_specific_gates"] = [
        {"neutral_private_value": "Synthetic identity-bearing value"}
    ]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "register_global_gate_list_invalid" in finding_codes(receipt)


def test_blank_global_and_genome_gate_strings_are_rejected(tmp_path: Path) -> None:
    register = build_register()
    register["global_confirmatory_gates"] = [""]
    register["genome_specific_gates"] = ["   "]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert "register_global_gate_list_invalid" in finding_codes(receipt)


def test_incomplete_manifest_schema_and_case_data_flag_are_rejected(
    tmp_path: Path,
) -> None:
    manifest = build_manifest()
    manifest["schema_version"] = "2.0"
    manifest["repository_context"] = {}
    manifest["context_budget"] = {}
    manifest["data_and_evidence_allowlist"] = [{}]
    privacy = manifest["privacy"]
    assert isinstance(privacy, dict)
    privacy["case_data_in_final_chat"] = True

    result, receipt = validate_fixture(tmp_path, manifest=manifest)

    assert result.schema_valid is False
    assert result.promotion_ready is False
    assert {
        "manifest_schema_version_invalid",
        "manifest_repository_context_required_value_missing",
        "manifest_context_budget_invalid",
        "manifest_allowlist_entry_required_value_missing",
        "manifest_case_data_not_disabled",
    }.issubset(finding_codes(receipt))


def test_https_source_url_with_query_is_rejected(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["source_urls"] = ["https://example.org/study?download=synthetic"]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert "hypothesis_source_url_not_clean" in finding_codes(receipt)


def test_output_must_remain_inside_explicit_private_root(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    private_root.mkdir()
    manifest_path = tmp_path / "manifest.json"
    register_path = tmp_path / "register.json"
    write_json(manifest_path, build_manifest())
    write_json(register_path, build_register())
    outside_output = tmp_path / "public" / "receipt"

    try:
        validate_research_program(
            manifest_path=manifest_path,
            register_path=register_path,
            output_directory=outside_output,
            private_root=private_root,
            receipt_nonce=b"synthetic-fixed-nonce-32-bytes!",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected output outside private root to be rejected")

    assert not outside_output.exists()


def test_existing_hardlinked_receipt_cannot_overwrite_outside_file(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    output_directory = private_root / "verification"
    output_directory.mkdir(parents=True)
    manifest_path = tmp_path / "manifest.json"
    register_path = tmp_path / "register.json"
    write_json(manifest_path, build_manifest())
    write_json(register_path, build_register())
    outside_file = tmp_path / "outside-receipt.json"
    outside_file.write_text("outside sentinel", encoding="utf-8")
    linked_receipt = output_directory / "research_validation_receipt.json"
    os.link(outside_file, linked_receipt)

    try:
        validate_research_program(
            manifest_path=manifest_path,
            register_path=register_path,
            output_directory=output_directory,
            private_root=private_root,
            receipt_nonce=b"synthetic-fixed-nonce-32-bytes!",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected hardlinked receipt destination to be rejected")

    assert outside_file.read_text(encoding="utf-8") == "outside sentinel"
    assert linked_receipt.read_text(encoding="utf-8") == "outside sentinel"


def test_rank_a_negative_gate_text_cannot_override_positive_statuses(
    tmp_path: Path,
) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["power_result"] = "not adequately powered"
    hypothesis["participant_overlap_check"] = "cohorts were not fully disjoint"
    hypothesis["access_verified_on"] = "access had not been granted"

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is True
    assert result.promotion_ready is False
    assert {
        "rank_a_required_text_not_met",
        "rank_a_access_date_invalid",
    }.issubset(finding_codes(receipt))


def test_email_signed_url_and_genotype_row_values_fail_closed(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["synthetic_rejection_values"] = [
        "analyst@example.org",
        "https://example.org/data?token=synthetic-token-value",
        "rs123 1 12345 AA",
    ]

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is False
    assert {
        "forbidden_email_value",
        "forbidden_signed_url",
        "forbidden_genotype_row",
    }.issubset(finding_codes(receipt))


def test_program_without_rank_a_remains_blocked(tmp_path: Path) -> None:
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["rank_band"] = "B"
    hypothesis["status"] = "design_ready"
    hypothesis["power_result"] = "pending cohort mapping"

    result, receipt = validate_fixture(tmp_path, register=register)

    assert result.schema_valid is True
    assert result.promotion_ready is False
    assert "no_confirmatory_ready_hypothesis" in finding_codes(receipt)


def test_cli_strict_returns_one_without_printing_paths_or_values(
    tmp_path: Path,
    capsys,
) -> None:
    manifest_path = tmp_path / "private-manifest.json"
    register_path = tmp_path / "private-register.json"
    register = build_register()
    hypothesis = register["hypotheses"][0]
    assert isinstance(hypothesis, dict)
    hypothesis["rank_band"] = "B"
    hypothesis["status"] = "design_ready"
    write_json(manifest_path, build_manifest())
    write_json(register_path, register)

    exit_code = main(
        [
            "research",
            "validate",
            "--manifest",
            str(manifest_path),
            "--register",
            str(register_path),
            "--out",
            str(tmp_path / "receipt"),
            "--private-root",
            str(tmp_path),
            "--strict",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Research validation status: blocked" in captured.out
    assert str(tmp_path) not in captured.out
    assert "Synthetic cohort replication question" not in captured.out
    assert captured.err == ""


def test_cli_malformed_input_fails_without_output_or_path_disclosure(
    tmp_path: Path,
    capsys,
) -> None:
    manifest_path = tmp_path / "secret-manifest.json"
    register_path = tmp_path / "secret-register.json"
    manifest_path.write_text("{not valid json", encoding="utf-8")
    write_json(register_path, build_register())
    output_directory = tmp_path / "receipt"

    exit_code = main(
        [
            "research",
            "validate",
            "--manifest",
            str(manifest_path),
            "--register",
            str(register_path),
            "--out",
            str(output_directory),
            "--private-root",
            str(tmp_path),
            "--strict",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert not output_directory.exists()
    assert str(tmp_path) not in captured.err
    assert "failed without exposing input paths or values" in captured.err


def test_cli_duplicate_casefolded_json_key_fails_without_receipt(
    tmp_path: Path,
    capsys,
) -> None:
    manifest_path = tmp_path / "duplicate-key-manifest.json"
    register_path = tmp_path / "register.json"
    manifest_path.write_text('{"run_id": "one", "RUN_ID": "two"}', encoding="utf-8")
    write_json(register_path, build_register())
    output_directory = tmp_path / "receipt"

    exit_code = main(
        [
            "research",
            "validate",
            "--manifest",
            str(manifest_path),
            "--register",
            str(register_path),
            "--out",
            str(output_directory),
            "--private-root",
            str(tmp_path),
            "--strict",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert not output_directory.exists()
    assert str(tmp_path) not in captured.err
    assert "failed without exposing input paths or values" in captured.err
