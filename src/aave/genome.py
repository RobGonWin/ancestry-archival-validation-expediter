"""Private, local-only AncestryDNA whitelist parsing and SNP annotation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from aave.models import AncestryDnaParseResult, SnpCrossrefResult, SnpWhitelistEntry
from aave.utils import calculate_sha256

GENOME_PRIVACY_LABEL = "raw_dna_never_export"
NO_CALL_VALUES = {"0", "-", "--", "N", ""}


def parse_ancestrydna_file(
    input_path: Path,
    whitelist_path: Path,
    output_directory: Path,
) -> AncestryDnaParseResult:
    """Parse a local AncestryDNA raw file and emit whitelist-only private outputs."""
    if not input_path.exists():
        raise FileNotFoundError(f"AncestryDNA input file does not exist: {input_path}")
    if not whitelist_path.exists():
        raise FileNotFoundError(f"SNP whitelist file does not exist: {whitelist_path}")

    whitelist_entries = load_snp_whitelist(whitelist_path)
    whitelist_by_rsid = {entry.rsid.lower(): entry for entry in whitelist_entries}
    observed_by_rsid: dict[str, dict[str, str]] = {}
    duplicate_rsids: set[str] = set()
    header_comments: list[str] = []
    malformed_rows: list[dict[str, Any]] = []
    rows_read = 0

    with input_path.open("r", encoding="utf-8-sig", errors="replace") as input_file:
        for line_number, raw_line in enumerate(input_file, start=1):
            stripped_line = raw_line.strip()
            if not stripped_line:
                continue
            if stripped_line.startswith("#"):
                header_comments.append(stripped_line.lstrip("#").strip())
                continue

            fields = re.split(r"\s+", stripped_line)
            if is_header_row(fields):
                continue

            if len(fields) < 5:
                malformed_rows.append(
                    {
                        "line_number": line_number,
                        "reason": "Expected rsid, chromosome, position, allele1, allele2.",
                    }
                )
                continue

            rows_read += 1
            rsid, chromosome, position, allele1, allele2 = fields[:5]
            normalized_rsid = rsid.lower()
            if normalized_rsid not in whitelist_by_rsid:
                continue
            if normalized_rsid in observed_by_rsid:
                duplicate_rsids.add(normalized_rsid)
                continue

            observed_by_rsid[normalized_rsid] = {
                "rsid": rsid,
                "chromosome": chromosome,
                "position": position,
                "allele1": allele1,
                "allele2": allele2,
                "call_status": get_call_status(allele1, allele2),
                "observation_note": (
                    "Observed in local raw file; not clinically validated. "
                    "Interpretation is limited by consumer array, strand, "
                    "and reference-build caveats."
                ),
            }

    hits = build_snp_hits(whitelist_entries, observed_by_rsid)
    missing = build_snp_missing(whitelist_entries, observed_by_rsid)
    manifest = build_genome_manifest(
        input_path=input_path,
        whitelist_path=whitelist_path,
        header_comments=header_comments,
        rows_read=rows_read,
        malformed_rows=malformed_rows,
        duplicate_rsids=duplicate_rsids,
        hits=hits,
        missing=missing,
    )
    public_summary = build_public_summary(manifest)

    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(manifest, output_directory / "manifest.json")
    write_json(hits, output_directory / "snp_hits.json")
    write_json(missing, output_directory / "snp_missing.json")
    write_json(public_summary, output_directory / "genome_public_summary.json")
    write_genome_audit(
        output_path=output_directory / "genome_audit.md",
        manifest=manifest,
        hit_count=len(hits),
        missing_count=len(missing),
    )

    parse_result = AncestryDnaParseResult(
        rows_read=rows_read,
        malformed_row_count=len(malformed_rows),
        duplicate_rsid_count=len(duplicate_rsids),
        hit_count=len(hits),
        missing_count=len(missing),
        output_directory=output_directory,
    )
    return parse_result


def crossref_snp_hits(
    hits_path: Path,
    whitelist_path: Path,
    output_directory: Path,
) -> SnpCrossrefResult:
    """Annotate whitelist SNP hits with local curated educational metadata."""
    if not hits_path.exists():
        raise FileNotFoundError(f"SNP hits file does not exist: {hits_path}")
    if not whitelist_path.exists():
        raise FileNotFoundError(f"SNP whitelist file does not exist: {whitelist_path}")

    hits = load_json_list(hits_path)
    whitelist_entries = load_snp_whitelist(whitelist_path)
    whitelist_by_rsid = {entry.rsid.lower(): entry for entry in whitelist_entries}
    annotated_hits = []
    for hit in hits:
        rsid = str(hit.get("rsid", "")).lower()
        whitelist_entry = whitelist_by_rsid.get(rsid)
        annotated_hit = dict(hit)
        if whitelist_entry:
            annotated_hit.update(
                {
                    "gene": whitelist_entry.gene,
                    "label": whitelist_entry.label,
                    "category": whitelist_entry.category,
                    "source_url": whitelist_entry.source_url,
                    "evidence_note": whitelist_entry.evidence_note,
                    "limitations": whitelist_entry.limitations,
                    "public_summary_allowed": whitelist_entry.public_summary_allowed,
                    "interpretation_scope": (
                        "Educational metadata only; not medical, diagnostic, or deterministic."
                    ),
                }
            )
        annotated_hits.append(annotated_hit)

    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(annotated_hits, output_directory / "snp_hits_annotated.json")
    write_crossref_audit(output_directory / "snp_crossref_audit.md", annotated_hits)

    annotated_count = sum(1 for hit in annotated_hits if hit.get("source_url"))
    crossref_result = SnpCrossrefResult(
        hit_count=len(annotated_hits),
        annotated_count=annotated_count,
        output_directory=output_directory,
    )
    return crossref_result


def load_snp_whitelist(path: Path) -> list[SnpWhitelistEntry]:
    """Load a local curated SNP whitelist JSON or YAML file."""
    raw_data = load_structured_data(path)
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON/YAML list of SNP whitelist entries in {path}")

    entries: list[SnpWhitelistEntry] = []
    for raw_entry in raw_data:
        if not isinstance(raw_entry, dict):
            continue
        rsid = str(raw_entry.get("rsid", "")).strip()
        if not rsid:
            raise ValueError(f"Whitelist entry in {path} is missing `rsid`.")
        entries.append(
            SnpWhitelistEntry(
                rsid=rsid,
                gene=optional_string(raw_entry.get("gene")),
                label=optional_string(raw_entry.get("label")),
                category=optional_string(raw_entry.get("category")),
                source_url=optional_string(raw_entry.get("source_url")),
                evidence_note=optional_string(raw_entry.get("evidence_note")),
                limitations=optional_string(raw_entry.get("limitations")),
                public_summary_allowed=bool(raw_entry.get("public_summary_allowed", False)),
            )
        )

    sorted_entries = sorted(entries, key=lambda entry: entry.rsid.lower())
    return sorted_entries


def load_structured_data(path: Path) -> object:
    """Load local JSON or YAML structured data."""
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig")
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def build_snp_hits(
    whitelist_entries: list[SnpWhitelistEntry],
    observed_by_rsid: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Build private whitelist hit rows with observed local genotypes."""
    hits = []
    for entry in whitelist_entries:
        observed = observed_by_rsid.get(entry.rsid.lower())
        if not observed:
            continue
        hit = {
            "rsid": observed["rsid"],
            "chromosome": observed["chromosome"],
            "position": observed["position"],
            "allele1": observed["allele1"],
            "allele2": observed["allele2"],
            "call_status": observed["call_status"],
            "privacy_label": GENOME_PRIVACY_LABEL,
            "source_confidence": "private_artifact",
            "gene": entry.gene,
            "label": entry.label,
            "category": entry.category,
            "source_url": entry.source_url,
            "evidence_note": entry.evidence_note,
            "limitations": entry.limitations,
            "public_summary_allowed": entry.public_summary_allowed,
            "observation_note": observed["observation_note"],
            "interpretation_scope": "Private educational cross-reference only.",
        }
        hits.append(hit)
    return hits


def build_snp_missing(
    whitelist_entries: list[SnpWhitelistEntry],
    observed_by_rsid: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Build missing/not-tested rows without treating absence as a negative result."""
    missing = []
    for entry in whitelist_entries:
        if entry.rsid.lower() in observed_by_rsid:
            continue
        missing.append(
            {
                "rsid": entry.rsid,
                "gene": entry.gene,
                "label": entry.label,
                "category": entry.category,
                "status": "missing_or_not_tested",
                "privacy_label": GENOME_PRIVACY_LABEL,
                "note": "Not found in the local raw file; this is not a negative result.",
            }
        )
    return missing


def build_genome_manifest(
    input_path: Path,
    whitelist_path: Path,
    header_comments: list[str],
    rows_read: int,
    malformed_rows: list[dict[str, Any]],
    duplicate_rsids: set[str],
    hits: list[dict[str, Any]],
    missing: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a private parser manifest without copying raw DNA content."""
    manifest = {
        "input_filename": input_path.name,
        "input_sha256": calculate_sha256(input_path),
        "whitelist_filename": whitelist_path.name,
        "whitelist_sha256": calculate_sha256(whitelist_path),
        "privacy_label": GENOME_PRIVACY_LABEL,
        "raw_file_copied": False,
        "rows_read": rows_read,
        "hit_count": len(hits),
        "missing_count": len(missing),
        "malformed_row_count": len(malformed_rows),
        "duplicate_rsid_count": len(duplicate_rsids),
        "duplicate_rsids": sorted(duplicate_rsids),
        "header_metadata": extract_header_metadata(header_comments),
        "malformed_rows": malformed_rows,
        "limitations": [
            "Whitelist-only parser for local user-owned AncestryDNA files.",
            "Consumer genotyping arrays are incomplete and may use strand/build conventions.",
            "Observed genotypes are not clinically validated.",
            "No medical, diagnostic, health, or longevity-deterministic claims are made.",
            "Public exports must never include raw genotypes or the raw input file.",
        ],
    }
    return manifest


def build_public_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a genotype-free summary suitable for redacted public workflows."""
    public_summary = {
        "genome_whitelist_checked": True,
        "privacy_label": "public_summary_only",
        "raw_file_copied": False,
        "raw_genotypes_included": False,
        "hit_count": manifest["hit_count"],
        "missing_count": manifest["missing_count"],
        "malformed_row_count": manifest["malformed_row_count"],
        "summary_note": (
            "A private local raw DNA file was checked against a curated whitelist. "
            "This summary intentionally excludes raw genotypes and SNP-level calls."
        ),
    }
    return public_summary


def extract_header_metadata(header_comments: list[str]) -> dict[str, Any]:
    """Extract conservative metadata from AncestryDNA comment headers."""
    metadata: dict[str, Any] = {"comments": header_comments}
    for comment in header_comments:
        normalized = comment.lower()
        if "generated" in normalized or "date" in normalized:
            metadata.setdefault("generated_at", comment)
        if "array" in normalized or "chip" in normalized:
            metadata.setdefault("array_version", comment)
        if "converter" in normalized:
            metadata.setdefault("converter_version", comment)
        if "build" in normalized or "reference" in normalized:
            metadata.setdefault("reference_build_note", comment)
    return metadata


def is_header_row(fields: list[str]) -> bool:
    """Return whether a data line is the standard column header."""
    normalized_fields = [field.lower() for field in fields[:5]]
    return normalized_fields == ["rsid", "chromosome", "position", "allele1", "allele2"]


def get_call_status(allele1: str, allele2: str) -> str:
    """Return whether a genotype row has a called or no-call allele pair."""
    if allele1.upper() in NO_CALL_VALUES or allele2.upper() in NO_CALL_VALUES:
        return "no_call"
    return "observed"


def optional_string(value: object) -> str | None:
    """Normalize optional JSON values to strings."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a JSON list of dictionaries."""
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    rows = [row for row in raw_data if isinstance(row, dict)]
    return rows


def write_json(data: object, output_path: Path) -> None:
    """Write stable formatted JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_genome_audit(
    output_path: Path,
    manifest: dict[str, Any],
    hit_count: int,
    missing_count: int,
) -> None:
    """Write a conservative genome parser audit report."""
    lines = [
        "# Genome Audit",
        "",
        "This report describes a local whitelist-only AncestryDNA raw-data parse.",
        "It is private archival metadata, not medical, diagnostic, or health advice.",
        "",
        "## Summary",
        "",
        f"- Raw file copied: `{str(manifest['raw_file_copied']).lower()}`",
        f"- Rows read: {manifest['rows_read']}",
        f"- Whitelist hits: {hit_count}",
        f"- Missing or not tested: {missing_count}",
        f"- Malformed rows: {manifest['malformed_row_count']}",
        f"- Duplicate whitelist rsIDs: {manifest['duplicate_rsid_count']}",
        "",
        "## Privacy",
        "",
        "- Raw DNA files and genotypes must never be included in public exports.",
        "- `snp_hits.json` is private by default because it contains genotype calls.",
        "- `genome_public_summary.json` contains counts only and no genotype data.",
        "",
        "## Interpretation Limits",
        "",
        "- SNP whitelist matches are educational references only.",
        "- Missing rsIDs are reported as missing or not tested, never negative.",
        "- Consumer array data is incomplete and may require strand/build review.",
        "- No medical, diagnostic, health, or longevity-deterministic claims are made.",
    ]
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")


def write_crossref_audit(output_path: Path, annotated_hits: list[dict[str, Any]]) -> None:
    """Write a conservative SNP cross-reference audit report."""
    lines = [
        "# SNP Cross-Reference Audit",
        "",
        "This report annotates private SNP whitelist hits with local curated metadata.",
        "It does not scrape SNPedia or any other external website.",
        "",
        f"Annotated hits: {len(annotated_hits)}",
        "",
        "## Limits",
        "",
        "- Source URLs are references, not medical authority.",
        "- Use terms like associated with, reported in, and educational note.",
        "- Do not infer health, longevity, or biological relationship claims from these rows.",
        "- Do not publish genotype-containing outputs.",
    ]
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")
