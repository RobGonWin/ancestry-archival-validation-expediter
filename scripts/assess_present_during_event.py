#!/usr/bin/env python3
"""Classify person-specific event-presence evidence without inferring attendance."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ALLOWED_CATEGORIES = {
    "complete_roster",
    "contemporaneous_named_report",
    "contradiction",
    "direct_record",
    "family_report",
    "first_person_report",
    "opportunity_context",
    "public_scene_context",
}
NON_PROOF_CATEGORIES = {"opportunity_context", "public_scene_context"}


class EvidenceError(ValueError):
    """Raised when an event-evidence packet is ambiguous or malformed."""


def _is_qualifying_direct(item: dict[str, Any]) -> bool:
    if not item.get("subject_specific") or not item.get("human_reviewed"):
        return False
    if item["category"] == "direct_record":
        return item.get("authenticated") is True
    if item["category"] == "complete_roster":
        return item.get("complete") is True
    return False


def assess_presence(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise EvidenceError("at least one evidence source is required")

    seen_ids: set[str] = set()
    counts: Counter[str] = Counter()
    direct: list[str] = []
    contradictions: list[str] = []
    contemporaneous: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    non_proof: list[str] = []

    for index, item in enumerate(sources):
        if not isinstance(item, dict):
            raise EvidenceError(f"sources[{index}] must be an object")
        source_id = item.get("id")
        category = item.get("category")
        if not isinstance(source_id, str) or not source_id or source_id in seen_ids:
            raise EvidenceError(f"sources[{index}] requires a unique id")
        if category not in ALLOWED_CATEGORIES:
            raise EvidenceError(f"{source_id} has invalid category")
        seen_ids.add(source_id)
        counts[category] += 1

        if category in NON_PROOF_CATEGORIES:
            url = item.get("source_url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                raise EvidenceError(f"{source_id} requires a public source_url")
            non_proof.append(source_id)
            continue

        if _is_qualifying_direct(item):
            direct.append(source_id)
        if (
            category == "contradiction"
            and item.get("subject_specific")
            and item.get("human_reviewed")
        ):
            contradictions.append(source_id)
        if (
            category == "contemporaneous_named_report"
            and item.get("subject_specific")
            and item.get("human_reviewed")
        ):
            contemporaneous.append(item)
        if category in {"first_person_report", "family_report"} and item.get(
            "subject_specific"
        ):
            reports.append(item)

    if direct and contradictions:
        status = "contested"
        basis = direct + contradictions
    elif direct:
        status = "confirmed"
        basis = direct
    elif contradictions:
        status = "contradicted"
        basis = contradictions
    else:
        candidate_sources = contemporaneous + reports
        independent_groups = {
            item.get("independent_group")
            for item in candidate_sources
            if item.get("independent_group")
        }
        if contemporaneous and len(independent_groups) >= 2:
            status = "supported"
            basis = [item["id"] for item in candidate_sources]
        elif reports:
            status = "reported"
            basis = [item["id"] for item in reports]
        else:
            status = "unknown"
            basis = []

    statements = {
        "confirmed": "Human-reviewed direct evidence identifies the subject at the event.",
        "supported": (
            "A reviewed contemporaneous named source and an independent report support "
            "presence."
        ),
        "reported": "Presence is reported but lacks qualifying independent corroboration.",
        "unknown": "Available material supplies scene or opportunity context only.",
        "contradicted": "Human-reviewed person-specific evidence contradicts presence.",
        "contested": (
            "Qualifying direct evidence and a qualifying contradiction coexist; resolve "
            "manually."
        ),
    }
    return {
        "schema_version": "aave.event-presence-assessment/1.0",
        "event_id": payload.get("event_id", "unnamed-event"),
        "event_date": payload.get("event_date"),
        "status": status,
        "basis_source_ids": basis,
        "non_proof_source_ids": non_proof,
        "category_counts": dict(sorted(counts.items())),
        "statement": statements[status],
        "guardrail": (
            "Census, kinship, geography, age overlap, and a public scene never prove "
            "attendance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON evidence packet with no direct identifiers")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = assess_presence(payload)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
