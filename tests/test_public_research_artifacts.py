from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _source_registry() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    payload = json.loads(
        (ROOT / "data" / "longevity-sources.json").read_text(encoding="utf-8")
    )
    sources = payload["sources"]
    return payload, {source["id"]: source for source in sources}


def test_longevity_registry_has_unique_bounded_sources() -> None:
    payload, by_id = _source_registry()
    sources = payload["sources"]

    assert payload["schema_version"] == "aave.public-source-register/1.1"
    assert len(by_id) == len(sources)

    for source in sources:
        assert source["id"]
        assert source["title"]
        assert source["source_type"]
        assert source["evidence_role"]
        assert source["urls"]
        assert source["supports"]
        assert source["cannot_support"]


def test_registry_covers_general_longevity_research_lanes() -> None:
    _, by_id = _source_registry()

    required = {
        "IDL-INED-CURRENT",
        "ABDELRAHEEM-ETAL-2026-SCOPING",
        "PERLS-ETAL-2002-SIBLINGS",
        "RUBY-ETAL-2018-ASSORTATIVE",
        "HIRATA-ETAL-2020-BIOMARKERS",
        "HASHIMOTO-ETAL-2026-CD4CTL",
        "DEELEN-ETAL-2019-LONGEVITY-GWAS",
        "GARAGNANI-ETAL-2021-SEMISUPER-WGS",
        "DING-ETAL-2023-PGS-PORTABILITY",
        "TANDY-CONNOR-ETAL-2018-DTC-QC",
        "CANDAL-PEDREIRA-ETAL-2025-BLUE-ZONES",
        "HANSEN-ETAL-2018-DENMARK-HOTSPOTS",
    }
    assert required <= set(by_id)

    immune_limits = " ".join(
        by_id["HASHIMOTO-ETAL-2026-CD4CTL"]["cannot_support"]
    ).lower()
    assert "causation" in immune_limits
    assert "cancer prevention" in immune_limits
    assert "consumer-genotype" in immune_limits


def test_longevity_register_defines_age_bands_and_separates_claims() -> None:
    text = (ROOT / "docs" / "research" / "longevity-source-register.md").read_text(
        encoding="utf-8"
    )

    assert "semi-supercentenarian` means ages 105 through 109 inclusive" in text
    assert "supercentenarian` means age 110 or older" in text
    assert "headlines are not causal evidence" in text
    assert "Pedigree/kinship proof and longevity\nmechanism research are separate" in text
    assert "Cluster\" here means a research grouping" in text


def test_geospatial_protocol_preserves_provider_and_evidence_boundaries() -> None:
    text = (
        ROOT / "docs" / "research" / "geospatial-context-register.md"
    ).read_text(encoding="utf-8")

    for required in (
        "© OpenStreetMap contributors",
        "No autocomplete, bulk geocoding, scraping",
        "No Street View screenshots, downloads, stitching",
        "No scraping, account automation, copying member posts",
        "does not prove occupancy, attendance, ownership, or kinship",
        "No agent may publish, upload, or submit geospatial material merely because it",
    ):
        assert required in text


def _generation_source_registry() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    payload = json.loads(
        (ROOT / "data" / "generation-cohort-sources.json").read_text(encoding="utf-8")
    )
    sources = payload["sources"]
    return payload, {source["id"]: source for source in sources}


def test_generation_registry_has_bounded_claims_and_required_lanes() -> None:
    payload, by_id = _generation_source_registry()
    sources = payload["sources"]

    assert payload["schema_version"] == "aave.generation-cohort-source-register/1.0"
    assert len(by_id) == len(sources)
    assert {
        "PEW-2023-GENERATION-METHOD",
        "CENSUS-2025-BIRTH-COHORTS",
        "MCCRINDLE-2025-BETA",
        "UN-WPP-2024-BIRTHS",
        "ACS-2024-B10001",
        "YOUNG-2004-BETTIE-VISIT",
        "PERLS-ETAL-2007-SUPER-FAMILY",
        "OUELLETTE-PERLS-2025-RACE100",
        "HOLT-LUNSTAD-ETAL-2010",
        "YATES-ETAL-2025-INFANT",
        "BAUER-LARKINA-2014",
        "BORRELLI-ETAL-2024-TRAUMA-AM",
        "CDC-ACES-2026",
    } <= set(by_id)

    for source in sources:
        assert source["urls"]
        assert source["supports"]
        assert source["cannot_support"]

    assert "complete attendee roster" in " ".join(
        by_id["YOUNG-2004-BETTIE-VISIT"]["cannot_support"]
    )
    assert "ACEs improve early memory" in " ".join(
        by_id["BORRELLI-ETAL-2024-TRAUMA-AM"]["cannot_support"]
    )


def test_generation_register_rejects_uniqueness_and_attendance_inference() -> None:
    text = (
        ROOT / "docs" / "research" / "generation-cohort-source-register.md"
    ).read_text(encoding="utf-8")

    for required in (
        "Earlier values such as “hundreds,” “low tens,” or “single digits” are Fermi estimates",
        "No complete global meeting registry was found",
        "ACEs therefore must not be used as an accuracy boost",
        "complete roster",
        "Census, kinship, geography, age overlap, and a public scene never prove attendance",
    ):
        assert required in text


def test_likely_cohort_tool_exposes_assumptions_and_generation_conventions() -> None:
    module = runpy.run_path(str(ROOT / "scripts" / "estimate_likely_cohort.py"))
    payload = json.loads(
        (ROOT / "examples" / "cohort-scenario.synthetic.json").read_text(encoding="utf-8")
    )

    result = module["estimate_scenario"](payload)

    assert result["estimate_type"] == "fermi_sensitivity_interval_not_registry_count"
    assert result["integer_display_interval"] == {"low": 0, "high": 1}
    assert [match["label"] for match in result["generation_matches"]] == ["Gen Z", "Gen Z"]
    assert any("assumption" in warning for warning in result["warnings"])
    assert "does not identify people" in result["statement"]


def test_likely_cohort_tool_rejects_memory_or_ace_accuracy_multipliers() -> None:
    module = runpy.run_path(str(ROOT / "scripts" / "estimate_likely_cohort.py"))
    payload = json.loads(
        (ROOT / "examples" / "cohort-scenario.synthetic.json").read_text(encoding="utf-8")
    )
    payload["factors"][0]["role"] = "memory_accuracy"

    with pytest.raises(module["ScenarioError"], match="prohibited numeric role"):
        module["estimate_scenario"](payload)


def test_event_presence_tool_keeps_report_separate_from_scene_context() -> None:
    module = runpy.run_path(str(ROOT / "scripts" / "assess_present_during_event.py"))
    payload = json.loads(
        (ROOT / "examples" / "event-presence-evidence.synthetic.json").read_text(
            encoding="utf-8"
        )
    )

    result = module["assess_presence"](payload)

    assert result["status"] == "reported"
    assert result["basis_source_ids"] == ["synthetic-first-person-report"]
    assert result["non_proof_source_ids"] == ["public-scene", "aggregate-opportunity"]
    assert "never prove attendance" in result["guardrail"]


def test_event_presence_confirmation_requires_reviewed_authenticated_direct_record() -> None:
    module = runpy.run_path(str(ROOT / "scripts" / "assess_present_during_event.py"))
    payload = {
        "event_id": "synthetic-event",
        "event_date": "2001-01-01",
        "sources": [
            {
                "id": "synthetic-direct",
                "category": "direct_record",
                "subject_specific": True,
                "human_reviewed": True,
                "authenticated": True,
            }
        ],
    }

    assert module["assess_presence"](payload)["status"] == "confirmed"
    payload["sources"][0]["authenticated"] = False
    assert module["assess_presence"](payload)["status"] == "unknown"


def test_pii_redaction_skill_is_cloud_mirrored_and_blocks_external_writes() -> None:
    local_skill = ROOT / ".agents" / "skills" / "pii-redaction" / "SKILL.md"
    cloud_skill = ROOT / ".github" / "skills" / "pii-redaction" / "SKILL.md"

    assert local_skill.read_bytes() == cloud_skill.read_bytes()
    text = " ".join(local_skill.read_text(encoding="utf-8").split())
    for required in (
        "named target issue",
        "full target commit SHA",
        "blocked_pending_explicit_human_authorization",
        "Do not install a Slop contribution skill",
        "upload a trace",
        "configure a wallet",
        "submit a pull request",
    ):
        assert required in text
