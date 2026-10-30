"""Evidence normalization, dependency grouping, and private local inventories."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

from aave.utils import calculate_sha256


class PageText(HTMLParser):
    """Extract visible text and declared source URLs without running page code."""

    def __init__(self) -> None:
        super().__init__()
        self.fragments: list[str] = []
        self.source_urls: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style"}:
            self.hidden_depth += 1
        if (tag == "link" and attributes.get("rel") == "canonical") or tag == "meta":
            if tag == "link" or attributes.get("property") == "og:url":
                url = attributes.get("href") or attributes.get("content", "")
                if url.startswith(("http://", "https://")):
                    self.source_urls.append(url)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, text: str) -> None:
        if not self.hidden_depth:
            self.fragments.append(text)


def extract_page(content: bytes) -> tuple[str, list[str]]:
    """Return normalized visible text and canonical URL hints; hints are not verified."""
    parser = PageText()
    parser.feed(content.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", " ".join(parser.fragments)).strip()
    return text, sorted(set(parser.source_urls))


def dependency_groups(evidence: list[dict]) -> list[list[str]]:
    """Group matching hashes or declared origins transitively; URLs alone add no independence."""
    groups: list[tuple[set[str], set[str]]] = []
    for row in evidence:
        keys = {str(row[key]) for key in ("content_sha256", "origin_id") if row.get(key)}
        identities = {row["evidence_id"]}
        remaining = []
        for group_keys, group_ids in groups:
            if keys & group_keys:
                keys |= group_keys
                identities |= group_ids
            else:
                remaining.append((group_keys, group_ids))
        # Repeat because a newly joined origin can connect an earlier group.
        changed = True
        while changed:
            changed = False
            for group_keys, group_ids in remaining[:]:
                if keys & group_keys:
                    keys |= group_keys
                    identities |= group_ids
                    remaining.remove((group_keys, group_ids))
                    changed = True
        groups = remaining + [(keys, identities)]
    return sorted([sorted(identities) for _, identities in groups])


def reconcile_memorial(person: dict, memorial: dict) -> dict:
    """Require explicit person linkage and corroborating identifiers; never infer a photo."""
    decision = dict(memorial)
    if memorial.get("person_id") != person["person_id"]:
        decision["match_status"] = "rejected_match"
    elif any(person.get(key) and memorial.get(key) and person[key] != memorial[key]
             for key in ("birth", "death")):
        decision["match_status"] = "identity_conflict"
    elif (memorial.get("identity_reviewed") is True
          and memorial.get("identity_evidence") and memorial.get("source_url")):
        decision["match_status"] = "verified_match"
    else:
        decision["match_status"] = "possible_match"
    decision["headstone_verified"] = bool(
        decision["match_status"] == "verified_match"
        and memorial.get("evidence_role") == "photographed_headstone"
        and memorial.get("image_reviewed") is True and memorial.get("image_source_url"))
    return decision


def census_observation(record: dict) -> dict:
    """Keep original readings, vendor spellings and review-labeled linkage separate."""
    result = dict(record)
    result["privacy_label"] = "do_not_share"
    result["identity_status"] = record.get("identity_status", "needs_review")
    result["transcription_conflict"] = bool(record.get("original_name")
        and record.get("vendor_name") and record["original_name"] != record["vendor_name"])
    result["cannot_support"] = ["exact birth date", "biological parentage", "universal ranking"]
    return result


def require_private_destination(path: Path, repo: Path) -> Path:
    """Fail closed: private extraction must remain inside this repository's ignored vault."""
    resolved = path.resolve()
    vault = (repo / "local-vault").resolve()
    if not resolved.is_relative_to(vault):
        raise ValueError("Private evidence output must be under local-vault")
    return resolved


def inventory_local(roots: list[Path], output: Path, repo: Path) -> dict:
    """Hash authorized local artifacts without copying originals; write only to local vault.

    HTML visible text stays private. Symlinks and genome formats are skipped.
    Missing/denied roots become explicit availability receipts.
    """
    output = require_private_destination(output, repo)
    receipts = []
    supported = {".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".ged"}
    for index, root in enumerate(roots):
        root_record = {"root_id": f"archive-{index:02d}", "artifacts": [], "errors": []}
        try:
            if not root.is_dir():
                raise FileNotFoundError("Requested archive not available")
            for path in sorted(root.rglob("*")):
                if path.is_symlink() or not path.is_file() or path.suffix.lower() not in supported:
                    continue
                if not path.resolve().is_relative_to(root.resolve()):
                    continue
                try:
                    digest = calculate_sha256(path)
                    artifact = {"artifact_id": digest[:24], "sha256": digest,
                                "local_path": str(path), "bytes": path.stat().st_size,
                                "format": path.suffix.lower(), "privacy_label": "do_not_share",
                                "modified_at": datetime.fromtimestamp(path.stat().st_mtime,
                                                                       UTC).isoformat(),
                                "modified_time_is_capture_date": False,
                                "evidence_role": "family_held_artifact"}
                    if path.suffix.lower() in {".html", ".htm"}:
                        text, urls = extract_page(path.read_bytes())
                        artifact.update(source_url_hints=urls, extracted_text=text)
                    root_record["artifacts"].append(artifact)
                except OSError as error:
                    root_record["errors"].append(type(error).__name__)
            root_record["availability"] = "inventoried"
        except OSError as error:
            root_record["availability"] = type(error).__name__
        receipts.append(root_record)
    result = {"schema_version": "aave.nea-local.v1", "privacy_label": "do_not_share",
              "public_export_authorized": False, "roots": receipts}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
