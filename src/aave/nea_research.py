"""Replay reviewed NEA evidence over the canonical award-entry inventory.

No page text is silently converted into an adjudication. Human review records
bind a subject, claim and source hash; unresolved groups always block closure.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from aave.nea_classification import male_person_coverage
from aave.nea_dates import DEFAULT_CUTOFF, compare_age, parse_date_interval
from aave.nea_discovery import discovery_queries, execute_batch, plan_cohorts
from aave.nea_evidence import extract_page, inventory_local, require_private_destination

EXCLUDED = {"verified_below_roma", "bounded_below_roma_at_cutoff"}


def read_json(path: Path) -> dict:
    """Read a UTF-8 evidence object, with an actionable filename in errors."""
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read evidence file: {path.name}") from error
    return result


def write_json(path: Path, value: dict | list) -> None:
    """Replace a generated JSON receipt atomically after successful serialization."""
    serialized = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(path)


def stable_id(prefix: str, source_key: str) -> str:
    """Produce an opaque reproducible ID; identical names alone never merge people."""
    identifier = prefix + "-" + hashlib.sha256(source_key.encode()).hexdigest()[:20]
    return identifier


def ledger_sha256(path: Path) -> str:
    """Hash UTF-8 ledger bytes with LF endings so Git checkout conversion is harmless."""
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def verify_review(review: dict, profile: dict, repo: Path) -> list[str]:
    """Reject unsupported/mutated review claims; absent local caches remain explicit."""
    problems = []
    if not review.get("subject_reviewed") or not review.get("rationale"):
        problems.append("subject_attribution_not_reviewed")
    expected = review.get("source_sha256")
    evidence_file = review.get("evidence_file")
    if not expected and not (evidence_file and review.get("evidence_sha256")):
        problems.append("no_hash_bound_source")
    if evidence_file:
        source = (repo / evidence_file).resolve()
        if not source.is_relative_to((repo / "data").resolve()) or not source.is_file():
            problems.append("evidence_file_unavailable_or_outside_data")
        elif ((ledger_sha256(source) if review.get("evidence_hash_normalization") == "lf_text"
               else hashlib.sha256(source.read_bytes()).hexdigest()) != review.get("evidence_sha256")):
            problems.append("evidence_file_hash_mismatch")
        else:
            ledger = read_json(source)
            records = ledger.get("records", ledger.get("adjudications", []))
            source_row = next((row for row in records
                               if row.get("source_id", row.get("profile_url"))
                               == review.get("evidence_source_id")), None)
            if not source_row:
                problems.append("evidence_record_missing")
            elif any(review.get(key) and review[key] != source_row.get(field)
                     for key, field in [("birth", "birth_date"), ("death", "death_date"),
                                        ("death_not_after", "death_not_after")]):
                problems.append("review_dates_differ_from_evidence_record")
            elif (review.get("completed_age_years") is not None
                  and review["completed_age_years"] != source_row.get("reported_completed_age_years")):
                problems.append("review_age_differs_from_evidence_record")
    if expected and expected != profile.get("profile_sha256"):
        problems.append("review_hash_differs_from_retrieval_receipt")
    cache_relative = profile.get("local_ignored_cache")
    if cache_relative and expected:
        cache = (repo / cache_relative).resolve()
        if not cache.is_relative_to((repo / "local-vault").resolve()):
            problems.append("cache_path_outside_local_vault")
        elif cache.exists():
            content = cache.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                problems.append("cached_source_hash_mismatch")
            if review.get("excerpt"):
                text, _ = extract_page(content)
                if review["excerpt"] not in text:
                    problems.append("review_excerpt_missing_from_source")
    return problems


def adjudicate_person(person: dict, review: dict | None, cutoff: date) -> dict:
    """Apply reviewed dates/bounds; source quality and identity confidence stay separate."""
    result = {**person, "status": "insufficient_age_evidence", "priority": 0,
              "cutoff": cutoff.isoformat(),
              "sex": "unknown", "source_confidence": "needs_review",
              "identity_confidence": "official_award_identity",
              "future_lifespan": "not_inferred", "evidence_decision": None}
    if not review:
        result["blockers"] = ["No reviewed subject-linked age evidence; sex unclassified"]
        return result
    result.update(sex=review.get("sex", "unknown"),
                  source_confidence=review.get("source_confidence", "needs_review"),
                  identity_confidence=review.get("identity_confidence", "reviewed_subject_link"),
                  evidence_decision=review["decision_id"],
                  evidence_urls=review.get("source_urls", [person["profile_url"]]))
    if review.get("conflict"):
        result.update(status="identity_conflict", sex="unknown", blockers=[review["conflict"]])
        return result
    if review.get("disposition") == "muted_edge_case":
        result.update(status="muted_edge_case", blockers=[review.get("mute_reason", "Ambiguous edge case left unproven")])
        if review.get("birth"):
            result["birth"] = review["birth"]
        return result
    try:
        if review.get("birth"):
            birth = parse_date_interval(review["birth"])
            death_bound = review.get("death_not_after") if not review.get("death") else None
            endpoint = review.get("death") or death_bound
            death = parse_date_interval(endpoint) if endpoint else None
            result.update(compare_age(birth, death, cutoff))
            result.update(birth=review["birth"], death=review.get("death"))
            if death_bound:
                result.update(death_not_after=death_bound, completed_lifespan_documented=False)
                result["status"] = ("bounded_below_roma_at_cutoff" if result["status"] in EXCLUDED
                                    else "possible_competitor")
        elif review.get("completed_age_years") is not None:
            # A reported whole-year age bounds days to < the next birthday.
            years = review["completed_age_years"]
            if isinstance(years, bool) or not isinstance(years, int) or years < 0:
                raise ValueError("Reported completed age must be a nonnegative integer")
            if years < 107 and review.get("death_by_cutoff"):
                result.update(status="bounded_below_roma_at_cutoff",
                              upper_age_calendar=f"reported completed age {years}; < {years + 1} years")
        if result["status"] in EXCLUDED:
            result["priority"] = 2
            result["blockers"] = []
        else:
            result["blockers"] = ["Age evidence does not exclude exceeding the reference at cutoff"]
        if result.get("upper_age", [0])[0] >= 100 and result["status"] in EXCLUDED:
            result["known_centenarian"] = True
        if result.get("birth") and int(result["birth"][:4]) >= 1919:
            result["priority"] = 2
    except (ValueError, TypeError):
        result.update(status="identity_conflict", sex="unknown", blockers=["Invalid or contradictory date evidence"])
    if result["sex"] == "female" and result["status"] not in EXCLUDED:
        result["priority"] = 4
    return result


def ranking_closure(people: list[dict], groups: list[dict], reference_id: str) -> dict:
    """Universal closure requires a reference, a resolved universe, and no possible tie/higher."""
    candidates = [person for person in people if person["person_id"] != reference_id
                  and person.get("sex") != "female" and person["status"] not in EXCLUDED
                  and person.get("status") != "muted_edge_case"]
    references = [person for person in people if person["person_id"] == reference_id]
    reference_ready = bool(references and references[0]["status"] == "verified_equal_roma"
                           and references[0].get("sex") == "male")
    status = "established_as_of_cutoff" if reference_ready and not candidates and not groups else "not_established"
    muted = [person for person in people if person.get("status") == "muted_edge_case"
             and person["person_id"] != reference_id]
    all_person_candidates = [person for person in people if person["person_id"] != reference_id
                             and person["status"] not in EXCLUDED
                             and person.get("status") != "muted_edge_case"]
    if muted:
        status = "not_established"
    result = {"status": status, "reference_ready": reference_ready,
              "reference_id": reference_id,
              "all_person_status": "established_as_of_cutoff" if reference_ready and not all_person_candidates and not groups and not muted else "not_established",
              "all_person_unresolved_count": len(all_person_candidates),
              "unresolved_known_male": [p for p in candidates if p.get("sex") == "male"],
              "unresolved_sex_unknown": [p for p in candidates if p.get("sex") == "unknown"],
              "muted_edge_cases": muted,
              "unresolved_groups": groups, "coverage_is_not_confidence": True}
    return result


def resolve_inventory(repo: Path, cutoff: date = DEFAULT_CUTOFF) -> dict:
    """Replay additive reviews plus the preserved PR2 ledger, validating source bindings."""
    roster = read_json(repo / "data/nea-recipient-age-audit.json")
    prior = read_json(repo / "data/nea-person-age-bounds.json")
    profiles = read_json(repo / "data/nea-male-ranking-coverage.json")
    reviews = read_json(repo / "data/nea-research-reviews.json")
    profiles_by_url = {p["profile_url"]: p for p in profiles["entries"]}
    review_by_url = {p["profile_url"]: p for p in reviews["decisions"]}
    if len(review_by_url) != len(reviews["decisions"]):
        raise ValueError("Duplicate review for one award identity")
    group_by_url = {p["profile_url"]: p for p in reviews["collective_awards"]}
    old_by_url = {p["profile_url"]: p for p in prior["adjudications"]}
    people, groups, awards, decisions = [], [], [], []
    for entry in roster["entries"]:
        url = entry["profile_url"]
        award_id = stable_id("award", url)
        award = {**entry, "award_id": award_id, "person_ids": []}
        if url in group_by_url:
            collective = group_by_url[url]
            members = collective.get("members", [])
            membership_review = collective.get("membership_review", {})
            membership_errors = verify_review(membership_review, profiles_by_url.get(url, {}), repo)
            names = [member.get("name") for member in members]
            membership_complete = bool(collective.get("membership_complete") and members
                                       and all(names) and len(names) == len(set(names))
                                       and not membership_errors)
            for member in collective.get("members", []):
                member_id = stable_id("person", url + "#member:" + member["name"])
                person = {"person_id": member_id, "award_id": award_id,
                          "name": member["name"], "award_year": entry["award_year"],
                          "art_form": entry["art_form"], "profile_url": url,
                          "privacy_label": "public_ok"}
                review = member.get("age_review")
                if review:
                    review = dict(review)
                    errors = verify_review(review, profiles_by_url.get(url, {}), repo)
                    if errors:
                        review["conflict"] = "; ".join(errors)
                    decisions.append({**review, "person_id": member_id,
                                      "source_category": "official_profile",
                                      "claim_type": "historical_attained_age_screening",
                                      "observed_on": review.get("reviewed_on", "2026-10-23"),
                                      "validation_findings": errors})
                people.append(adjudicate_person(person, review, cutoff))
                award["person_ids"].append(member_id)
            unresolved = {"award_id": award_id, "name": entry["recipient_label"],
                          "profile_url": url, "status": "group_membership_unresolved",
                          "blockers": collective["blockers"], "priority": 3}
            if not membership_complete:
                groups.append(unresolved)
            award["kind"] = collective["kind"]
            awards.append(award)
            continue
        person_id = stable_id("person", url + "#recipient")
        person = {"person_id": person_id, "award_id": award_id,
                  "name": entry["recipient_label"], "award_year": entry["award_year"],
                  "art_form": entry["art_form"], "profile_url": url, "privacy_label": "public_ok"}
        person["official_profile_retrieved"] = bool(profiles_by_url.get(url, {}).get("retrieved"))
        review = review_by_url.get(url)
        if not review and url in old_by_url:
            old = old_by_url[url]
            review = {"decision_id": stable_id("decision", url + "#PR2"),
                      "subject_reviewed": True, "rationale": old["review_method"],
                      "source_confidence": "probable", "source_sha256": old.get("profile_sha256"),
                      "profile_url": url, "source_urls": old.get("sources", [url]),
                      "historical_ledger": "data/nea-person-age-bounds.json"}
            if old.get("birth_year"):
                review["birth"] = str(old["birth_year"])
            else:
                review.update(completed_age_years=old.get("reported_completed_age_years"),
                              death_by_cutoff=cutoff >= DEFAULT_CUTOFF,
                              evidence_file="data/nea-person-age-bounds.json",
                              evidence_sha256=ledger_sha256(repo / "data/nea-person-age-bounds.json"),
                              evidence_hash_normalization="lf_text",
                              evidence_source_id=url)
        if review:
            review = dict(review)
            errors = verify_review(review, profiles_by_url.get(url, {}), repo)
            if errors:
                review["conflict"] = "; ".join(errors)
            decisions.append({**review, "person_id": person_id, "validation_findings": errors,
                              "source_category": review.get("source_category", "official_profile"),
                              "claim_type": "historical_attained_age_screening",
                              "observed_on": review.get("reviewed_on", "2026-10-23")})
        result = adjudicate_person(person, review, cutoff)
        people.append(result)
        award.update(kind="individual", person_ids=[person_id])
        awards.append(award)
    reference_url = reviews["reference_profile_url"]
    reference_id = stable_id("person", reference_url + "#recipient")
    closure = ranking_closure(people, groups, reference_id)
    excluded = [p for p in people if p["status"] in EXCLUDED]
    exact = [p for p in people if p.get("completed_lifespan_documented")]
    ranked = sorted(exact, key=lambda p: tuple(p["upper_age"]), reverse=True)
    for person in ranked:
        person["rank_among_exact_date_adjudications"] = 1 + sum(
            tuple(other["upper_age"]) > tuple(person["upper_age"]) for other in exact)
        person["universal_rank"] = None
    excluded_ids = {person["person_id"] for person in excluded}
    excluded_awards = [award for award in awards if award["person_ids"]
                       and all(identifier in excluded_ids for identifier in award["person_ids"])
                       and not any(group["award_id"] == award["award_id"] for group in groups)]
    summary = {"award_entries": len(awards), "resolved_person_records": len(people),
               "individual_award_entries": sum(award["kind"] == "individual" for award in awards),
               "resolved_named_joint_awards": sum(award["kind"] != "individual" and bool(award["person_ids"]) for award in awards),
               "unresolved_collective_awards": len(groups), "excluded_award_entries": len(excluded_awards),
               "excluded_person_records": len(excluded),
               "new_exclusions_vs_pr2": len(excluded_awards) - prior["coverage"]["award_entries_with_individual_age_exclusion"],
               "reference_entries": int(closure["reference_ready"]),
               "unresolved_award_entries": len(awards) - len(excluded_awards) - int(closure["reference_ready"]),
               "award_entry_screening_percent": round(100 * (len(excluded_awards) + int(closure["reference_ready"])) / len(awards), 2),
               "male_person_denominator": None, "male_screening_percent": None,
               **male_person_coverage(people, reference_id),
               "person_universe_resolved": not groups,
               "profiles_retrieved": profiles["coverage"]["successfully_retrieved_profiles"],
               "exact_date_age_adjudications": len(exact),
               "memorial_discovery_is_separate": True}
    result = {"schema_version": "aave.nea-research.v1", "privacy_label": "private_family_only",
              "cutoff": cutoff.isoformat(), "summary": summary, "ranking": closure,
              "people": people, "awards": awards, "decisions": decisions,
              "ranked_exact_dates": ranked,
              "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [repo / "data" / name for name in ["nea-recipient-age-audit.json", "nea-person-age-bounds.json",
                                                     "nea-male-ranking-coverage.json", "nea-research-reviews.json"]]}}
    return result


def write_reports(result: dict, output: Path) -> None:
    """Write reproducible JSON/CSV proof matrices and explicit named follow-up blockers."""
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "nea-research-result.json", result)
    write_json(output / "nea-unresolved-competitors.json", result["ranking"])
    write_json(output / "nea-evidence-decisions.json", result["decisions"])
    rows = result["people"]
    fields = ["person_id", "name", "award_year", "birth", "death", "upper_age_calendar",
              "status", "sex", "source_confidence", "identity_confidence", "evidence_decision", "profile_url"]
    with (output / "nea-ranking-proof.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = result["summary"]
    lines = ["# NEA historical age-screening run", "", f"Cutoff: {result['cutoff']}. Ranking: **{result['ranking']['status']}**.",
             "", f"{summary['excluded_award_entries']} award entries excluded; {summary['reference_entries']} reference; "
             f"{summary['unresolved_award_entries']} unresolved. "
             f"{summary['unresolved_collective_awards']} collective awards need membership resolution.",
             "", "Male-person denominator and coverage percentage remain unknown. Coverage is not confidence.",
             "", "Wade Mainer is a confirmed male comparator; his universal second place is provisional and unassigned.",
             "", "## Exact-date comparisons", "", "| Person | Birth | Death | Attained age | Subset rank |", "| --- | --- | --- | --- | --- |"]
    for person in result["ranked_exact_dates"]:
        lines.append(f"| {person['name']} | {person['birth']} | {person['death']} | "
                     f"{person['upper_age_calendar']} | {person['rank_among_exact_date_adjudications']} |")
    lines.extend(["", "## Named unresolved people (known male or sex not adjudicated)", ""])
    for person in result["ranking"]["unresolved_known_male"] + result["ranking"]["unresolved_sex_unknown"]:
        lines.append(f"- [{person['name']}]({person['profile_url']}): {'; '.join(person['blockers'])}.")
    lines.extend(["", "## Unresolved collective awards", ""])
    for group in result["ranking"]["unresolved_groups"]:
        lines.append(f"- [{group['name']}]({group['profile_url']}): {'; '.join(group['blockers'])}.")
    lines.extend(["", "No unsuccessful search is an age exclusion. Reported dates are not vital-record age validation.", ""])
    (output / "nea-ranked-candidates.md").write_text("\n".join(lines), encoding="utf-8")


def register_cli(subparsers) -> None:
    """Add offline-first NEA actions to the existing CLI."""
    parser = subparsers.add_parser("nea", help="Replay NEA historical ranking and discovery evidence.")
    parser.add_argument("action", choices=["inventory", "ingest-local", "discover", "resolve", "rank", "report", "all"])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cutoff", type=date.fromisoformat, default=DEFAULT_CUTOFF)
    parser.add_argument("--local-root", type=Path, action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--cohort-size", type=int, default=50, help="Recipient identities per planned cohort.")
    parser.add_argument("--cohort-index", type=int, default=0, help="Zero-based cohort to prepare for discovery.")
    parser.add_argument("--providers", type=Path, help="JSON mapping of provider names to public query templates.")
    parser.add_argument("--offline", action="store_true", help="Explicit offline replay (also the default).")
    parser.add_argument("--dry-run", action="store_true", help="Calculate and print counts without filesystem writes.")


def run_cli(args) -> int:
    """Execute a local action; no provider/network credentials or implicit external calls."""
    repo = args.repo.resolve()
    if args.local_root:
        require_private_destination(args.out, repo)
    if args.limit < 0 or args.cohort_size < 1 or args.cohort_index < 0:
        raise ValueError("Batch limit/index must be nonnegative and cohort size positive")
    if args.action == "ingest-local":
        require_private_destination(args.out, repo)
        if not args.dry_run:
            receipt = inventory_local(args.local_root, args.out / "local-inventory.json", repo)
            print(json.dumps({"roots": len(receipt["roots"]), "privacy_label": "do_not_share"}))
        return 0
    result = resolve_inventory(repo, args.cutoff)
    cohorts = []
    if args.action in {"discover", "all"}:
        cohorts = plan_cohorts(result["people"], cohort_size=args.cohort_size,
                               reference_id=result["ranking"]["reference_id"])
        if (cohorts and args.cohort_index >= len(cohorts)) or (not cohorts and args.cohort_index):
            raise ValueError("Cohort index exceeds the unresolved recipient plan")
    print(json.dumps(result["summary"]))
    if args.dry_run:
        return 0
    if args.action == "inventory":
        write_json(args.out / "nea-award-inventory.json", result["awards"])
        return 0
    write_reports(result, args.out)
    if args.action in {"discover", "all"}:
        providers = read_json(args.providers) if args.providers else None
        selected_ids = set(cohorts[args.cohort_index]["person_ids"]) if cohorts else set()
        queries = [q for person in result["people"] if person["person_id"] in selected_ids
                   for q in discovery_queries(person, providers)]
        write_json(args.out / "nea-cohort-plan.json", cohorts)
        write_json(args.out / "nea-search-queue.json", queries)
        execute_batch(queries, {}, args.out / "nea-discovery-checkpoint.json", limit=args.limit)
    if args.action == "all" and args.local_root:
        inventory_local(args.local_root, args.out / "local-inventory.json", repo)
    return 0
