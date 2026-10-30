"""Resumable search plans and bounded, explicitly enabled search-provider adapters."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DEFAULT_PROVIDERS = {
    "nea": '"{name}" site:arts.gov "heritage" born died',
    "nea_death_statement": '"{name}" site:arts.gov death memoriam',
    "traditional_arts": '"{name}" site:mastersoftraditionalarts.org',
    "funeral": '"{name}" obituary funeral birth death {year}',
    "funeral_directory": '"{name}" site:tributearchive.com/obituaries/',
    "findagrave": '"{name}" site:findagrave.com/memorial/',
    "billiongraves": '"{name}" site:billiongraves.com',
    "cemetery": '"{name}" cemetery burial {art_form}',
    "institutional": '"{name}" "National Heritage" centenarian obituary',
    "legacy_newspaper": '"{name}" obituary newspaper Legacy {geography}',
    "historical_archive": '"{name}" historical society digital library archive {geography}',
    "gerontology": '"{name}" longevity centenarian birth death',
    "public_genealogy_index": '"{name}" FamilySearch Ancestry birth death',
}


def discovery_queries(person: dict, providers: dict | None = None) -> list[dict]:
    """Plan public-name searches; exclude age-screened people from expensive discovery."""
    if person["status"] in {"verified_below_roma", "bounded_below_roma_at_cutoff"}:
        return []
    if person.get("privacy_label") != "public_ok":
        return []
    rows = []
    for source_priority, (provider, template) in enumerate((providers or DEFAULT_PROVIDERS).items()):
        if provider == "nea" and person.get("official_profile_retrieved"):
            continue
        query = template.format(name=person["name"], year=person["award_year"],
                                art_form=person.get("art_form", ""),
                                geography=person.get("geography", ""),
                                aliases=" ".join(person.get("aliases", [])))
        query_key = json.dumps([person["person_id"], provider, query, person.get("cutoff"),
                                person.get("search_revision", 1)], ensure_ascii=False)
        query_id = hashlib.sha256(query_key.encode()).hexdigest()[:24]
        rows.append({"query_id": query_id, "person_id": person["person_id"],
                     "provider": provider, "query": query, "priority": person["priority"],
                     "source_priority": source_priority,
                     "status": "manual_followup", "query_is_external_emission": True})
    return rows


@dataclass(frozen=True)
class SearchAdapter:
    """A host supplies an authorized API callback; no site has an invented API."""

    search: Callable[[str], list[dict]]
    terms_url: str
    enabled: bool = False
    minimum_interval_seconds: float = 1.0
    maximum_attempts: int = 2


class SearchProviderError(OSError):
    """Carry allowlisted diagnostics without provider text, URLs or credentials."""

    KINDS = frozenset({"access_block", "billing_block", "rate_limit", "http_error",
                       "tls_certificate", "tls_error", "dns_error", "network_permission",
                       "network_error", "timeout", "invalid_response"})

    def __init__(self, failure_kind: str, *, halt_batch: bool = False,
                 http_status: int | None = None):
        if failure_kind not in self.KINDS:
            raise ValueError("Unsupported search failure category")
        if http_status is not None and (type(http_status) is not int or not 100 <= http_status <= 599):
            raise ValueError("Invalid search HTTP status")
        super().__init__(failure_kind)
        self.failure_kind = failure_kind
        self.halt_batch = halt_batch
        self.http_status = http_status


def _failure_counts(results: dict) -> dict[str, int]:
    """Retain same-error counts even when successes interrupt the failure streak."""
    counts: dict[str, int] = {}
    for row in results.values():
        history = row.get("failure_history")
        if history is None:
            history = ([row] * row.get("attempts", 1)) if row.get("status") == "failed" else []
        for failure in history:
            identity = failure.get("failure_kind", failure.get("error", "unknown"))
            counts[identity] = counts.get(identity, 0) + 1
    return counts


def _save_checkpoint(path: Path, results: dict) -> None:
    """Atomically preserve every attempted query, including the halt receipt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def plan_cohorts(people: list[dict], *, cohort_size: int = 50,
                 reference_id: str | None = None) -> list[dict]:
    """Partition unresolved public recipient identities into stable review cohorts.

    This is a work plan, not fifty exclusions or fifty successful retrievals.
    Collective memberships without identified people remain separate blockers.
    """
    if isinstance(cohort_size, bool) or not isinstance(cohort_size, int) or cohort_size < 1:
        raise ValueError("Cohort size must be a positive integer")
    eligible = [person for person in people if person.get("privacy_label") == "public_ok"
                and person["status"] not in {"verified_below_roma", "bounded_below_roma_at_cutoff"}
                and person["person_id"] != reference_id]
    eligible.sort(key=lambda person: (person.get("priority", 0), person["person_id"]))
    cohorts = []
    for start in range(0, len(eligible), cohort_size):
        members = eligible[start:start + cohort_size]
        cohorts.append({"cohort_id": f"cohort-{start // cohort_size:03d}",
                        "person_ids": [person["person_id"] for person in members],
                        "people": [{key: person.get(key) for key in
                                    ("person_id", "name", "status", "profile_url", "priority")}
                                   for person in members],
                        "recipient_count": len(members), "adjudication_status": "planned"})
    return cohorts


def execute_batch(queries: list[dict], adapters: dict[str, SearchAdapter],
                  checkpoint_path: Path, *, limit: int = 20, dry_run: bool = False) -> dict:
    """Run serially (concurrency=1), rate-limit/retry and checkpoint each response.

    API callbacks must return source URLs and truthful retrieval metadata. Search
    hits remain leads; they never become age evidence automatically. Failed
    checkpoints are retained without retrying their queries. Three total
    failed attempts or three occurrences of the same error halt the batch,
    including across calls using this checkpoint.
    A provider access/billing/rate block halts immediately. Halted checkpoints
    require a separately reviewed access-state revision rather than an implicit reset.
    """
    if limit < 0:
        raise ValueError("Batch limit must be nonnegative")
    if len({row["query_id"] for row in queries}) != len(queries):
        raise ValueError("Query IDs must be unique within a batch")
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else {}
    results = dict(checkpoint)
    failure_counts = _failure_counts(results)
    failed_attempts = sum(failure_counts.values())
    if (any(row.get("batch_halt_reason") for row in results.values()) or failed_attempts >= 3
            or any(count >= 3 for count in failure_counts.values())):
        return results
    last_calls: dict[str, float] = {}
    pending = []
    for query in queries:
        previous = results.get(query["query_id"], {})
        adapter = adapters.get(query["provider"])
        if previous.get("status") in {"searched", "not_found", "failed"}:
            continue
        if previous.get("status") == "manual_followup" and not (adapter and adapter.enabled):
            continue
        pending.append(query)
    selected = sorted(pending, key=lambda row: (row["priority"], row.get("source_priority", 0),
                                               row["query_id"]))[:limit]
    for query in selected:
        query_id = query["query_id"]
        if results.get(query_id, {}).get("status") in {"searched", "not_found"}:
            continue
        adapter = adapters.get(query["provider"])
        if dry_run or not adapter or not adapter.enabled or not adapter.terms_url:
            results[query_id] = {**query, "status": "dry_run" if dry_run else "manual_followup"}
            if not dry_run:
                _save_checkpoint(checkpoint_path, results)
            continue
        if not 1 <= adapter.maximum_attempts <= 3 or adapter.minimum_interval_seconds < 0:
            raise ValueError("Adapter retry/rate limits invalid")
        # Keep actual execution order even when a checkpoint began as an offline plan.
        results.pop(query_id, None)
        failure_history = []
        for attempt in range(adapter.maximum_attempts):
            elapsed = time.monotonic() - last_calls.get(query["provider"], float("-inf"))
            time.sleep(max(0, adapter.minimum_interval_seconds - elapsed))
            last_calls[query["provider"]] = time.monotonic()
            try:
                hits = adapter.search(query["query"])
                content = json.dumps(hits, sort_keys=True, ensure_ascii=False).encode()
                results[query_id] = {**query, "status": "searched" if hits else "not_found",
                                     "hits": hits, "attempts": attempt + 1,
                                     "response_sha256": hashlib.sha256(content).hexdigest(),
                                     "terms_url": adapter.terms_url,
                                     "age_exclusion_authorized": False}
                if failure_history:
                    results[query_id]["failure_history"] = failure_history
                break
            except (OSError, ValueError) as error:
                failed_attempts += 1
                results[query_id] = {**query, "status": "failed", "error": type(error).__name__,
                                     "attempts": attempt + 1}
                if isinstance(error, SearchProviderError):
                    results[query_id]["failure_kind"] = error.failure_kind
                    if error.http_status is not None:
                        results[query_id]["http_status"] = error.http_status
                    if error.halt_batch:
                        results[query_id]["batch_halt_reason"] = "provider_block"
                diagnostic = {key: results[query_id][key] for key in
                              ("error", "failure_kind", "http_status") if key in results[query_id]}
                failure_history.append(diagnostic)
                results[query_id]["failure_history"] = failure_history
                identity = diagnostic.get("failure_kind", diagnostic["error"])
                failure_counts[identity] = failure_counts.get(identity, 0) + 1
                if failed_attempts >= 3:
                    results[query_id].setdefault("batch_halt_reason", "three_failed_attempts")
                if failure_counts[identity] >= 3:
                    results[query_id].setdefault("batch_halt_reason", "three_same_errors")
                if results[query_id].get("batch_halt_reason"):
                    break
        if not dry_run:
            _save_checkpoint(checkpoint_path, results)
        if results[query_id].get("batch_halt_reason"):
            break
    return results
