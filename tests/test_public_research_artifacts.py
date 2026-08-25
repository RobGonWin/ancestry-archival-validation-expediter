from __future__ import annotations

import json
from pathlib import Path


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
