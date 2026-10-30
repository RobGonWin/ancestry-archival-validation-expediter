"""Validate cohort assignments and membership/age citation hashes before replay."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from aave.nea_evidence import extract_page
from aave.nea_research import read_json


def _validate_source(source: dict, repo: Path, audit: dict) -> None:
    expected = source.get("source_sha256")
    if not source.get("source_url") or not re.fullmatch(r"[0-9a-f]{64}", expected or ""):
        raise ValueError("Source requires an original URL and SHA-256")
    cache_name = source.get("local_ignored_cache")
    if not cache_name:
        audit["source_receipts_without_local_cache"].append(source["source_url"])
        return
    cache = (repo / cache_name).resolve()
    if not cache.is_relative_to((repo / "local-vault").resolve()):
        raise ValueError("Source cache must remain within local-vault")
    if not cache.is_file():
        audit["source_receipts_without_local_cache"].append(source["source_url"])
        return
    content = cache.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError(f"Source hash mismatch: {source['source_url']}")
    audit["cached_sources_hash_verified"] += 1


def _validate_citation(citation: dict, sources: list[dict], repo: Path, audit: dict) -> None:
    source = next((source for source in sources
                   if source.get("source_url") == citation.get("source_url")
                   and source.get("source_sha256") == citation.get("source_sha256")), None)
    if source is None:
        raise ValueError("Citation does not match a registered cohort source")
    excerpt = citation.get("excerpt")
    if not excerpt or not citation.get("rationale"):
        raise ValueError("Citation requires subject attribution and an excerpt")
    cache_name = source.get("local_ignored_cache")
    if cache_name and (cache := repo / cache_name).is_file():
        content = cache.read_bytes()
        if cache.suffix.lower() == ".pdf":
            text_cache = (repo / source.get("extracted_text_cache", "")).resolve()
            if not text_cache.is_relative_to((repo / "local-vault").resolve()) or not text_cache.is_file():
                raise ValueError("PDF citation requires a hash-bound reviewed text extraction")
            content = text_cache.read_bytes()
            if hashlib.sha256(content).hexdigest() != source.get("extracted_text_sha256"):
                raise ValueError("PDF extracted-text hash mismatch")
        text = extract_page(content)[0] if cache.suffix.lower() in {".html", ".htm"} else content.decode("utf-8", errors="replace")
        if source.get("hash_scope") == "web_tool_rendered_original_document":
            text = re.sub(r"(?m)^L\d+(?:@P\d+(?:-\d+)?)?:\s*", "", text)
        if " ".join(excerpt.split()) not in " ".join(text.split()):
            visual = citation.get("visual_review", {})
            rendered = (repo / visual.get("rendered_cache", "")).resolve()
            has_visual_review = (visual.get("quote_verified_in_render") is True and visual.get("page")
                and rendered.is_relative_to((repo / "local-vault").resolve()) and rendered.is_file())
            if not has_visual_review or hashlib.sha256(rendered.read_bytes()).hexdigest() != visual.get("rendered_sha256"):
                raise ValueError(f"Citation excerpt missing from cached original: {citation['source_url']}")
            audit["visually_reviewed_citation_transcriptions"] += 1
        else:
            audit["citation_excerpts_verified"] += 1


def load_reviewed_awards(repo: Path, files: list[Path]) -> tuple[list[dict], dict]:
    """Require exact coverage of the canonical 36 unresolved award identities.

    Raw-byte and rendered-original text hashes retain their declared scope.
    Missing original caches remain explicit offline-replay limitations; altered
    cached bytes, source substitutions and missing attribution are fatal.
    """
    canonical = read_json(repo / "data/nea-research-reviews.json")
    expected = {row["profile_url"] for row in canonical["collective_awards"] if not row.get("membership_complete")}
    roster = {row["profile_url"]: row for row in read_json(repo / "data/nea-recipient-age-audit.json")["entries"]}
    profile_hashes = {row["profile_url"]: row["profile_sha256"]
                      for row in read_json(repo / "data/nea-male-ranking-coverage.json")["entries"]}
    awards = [award for file in files for award in read_json(file)["awards"]]
    urls = [award["profile_url"] for award in awards]
    if len(urls) != len(set(urls)) or set(urls) != expected:
        raise ValueError("Cohorts must cover each canonical unresolved collective exactly once")
    audit = {"cached_sources_hash_verified": 0, "citation_excerpts_verified": 0,
             "visually_reviewed_citation_transcriptions": 0,
             "source_receipts_without_local_cache": [], "canonical_awards_verified": len(awards)}
    for award in awards:
        url = award["profile_url"]
        if award["award_year"] != roster[url]["award_year"]:
            raise ValueError("Collective award year differs from canonical inventory")
        if not award.get("membership_rationale"):
            raise ValueError("Collective needs an explicit membership-boundary review")
        sources = list(award["sources"])
        for member in award.get("members", []):
            sources.extend((member.get("age_review") or {}).get("sources", []))
        official = next((source for source in sources if source["source_url"] == url), None)
        if not official or official["source_sha256"] != profile_hashes[url]:
            raise ValueError("Official profile differs from canonical retrieval receipt")
        unique_sources = {(source["source_url"], source["source_sha256"]): source for source in sources}
        sources = list(unique_sources.values())
        for source in sources:
            _validate_source(source, repo, audit)
        for member in award.get("members", []):
            _validate_citation(member["membership_evidence"], sources, repo, audit)
            if member.get("sex_evidence"):
                _validate_citation({**member["sex_evidence"], "rationale": "Reviewed explicit sex label"},
                                   sources, repo, audit)
            review = member.get("age_review")
            if not review:
                continue
            if not review.get("subject_reviewed") or not review.get("decision_id") or not review.get("rationale"):
                raise ValueError("Age review requires explicit subject attribution")
            source = next((source for source in sources if source["source_sha256"] == review.get("source_sha256")), None)
            if not source:
                raise ValueError("Age review not bound to a registered source hash")
            _validate_citation({**review, "source_url": source["source_url"]}, sources, repo, audit)
            for role in ("death_evidence", "sex_evidence"):
                if nested := review.get(role):
                    _validate_citation({"source_url": source["source_url"],
                        "source_sha256": source["source_sha256"], "rationale": review["rationale"],
                        **nested}, sources, repo, audit)
        if screen := award.get("collective_age_screen"):
            _validate_citation(screen, sources, repo, audit)
    audit["source_receipts_without_local_cache"] = sorted(set(audit["source_receipts_without_local_cache"]))
    return awards, audit
