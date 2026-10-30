"""Add reviewed award-year members to the existing historical comparison.

This module performs local adjudication only. Discovery, age arithmetic and
rank envelopes remain in the existing NEA engine. Ensemble association never
confers an individual fellowship, and incomplete rosters always block closure.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date

from aave.nea_classification import classify_documented_sex
from aave.nea_ranking import build_individual_ranking
from aave.nea_research import EXCLUDED, adjudicate_person, stable_id


def evidence_classification(person: dict, review: dict) -> str:
    """Keep documentary precision separate from the outcome of an age screen."""
    if person.get("status") == "identity_conflict" or review.get("conflicts"):
        classification = "conflicted"
    elif not review or person.get("status") == "insufficient_age_evidence":
        classification = "unresolved"
    elif (review.get("inferred") or review.get("inference_basis")
          or str(review.get("date_precision", "")).startswith("inferred_")):
        classification = "inferred_probable"
    elif person.get("completed_lifespan_documented"):
        classification = "documented"
    else:
        classification = "bounded"
    return classification


def _association(award: dict, *, individual: bool) -> dict:
    association = {
        "award_id": award["award_id"], "profile_url": award["profile_url"],
        "award_year": award["award_year"], "label": award["name"],
        "relationship": "named_recipient" if individual else "award_year_collective_member",
        "individual_fellowship_asserted": individual,
    }
    return association


def _merge_person(people: dict, candidate: dict, review: dict, association: dict) -> None:
    """Deduplicate explicit IDs, preserving associations and conflicting evidence.

    Names alone never merge identities. Reusing an ID requires an identity
    rationale supplied by the caller's reviewed membership record.
    """
    identifier = candidate["person_id"]
    if identifier not in people:
        people[identifier] = candidate
        candidate["associations"] = []
        candidate["comparison_review"] = review
    current = people[identifier]
    current.setdefault("associated_reviews", []).append(review)
    if candidate.get("status") == "identity_conflict":
        current.update(status="identity_conflict", sex="unknown",
                       blockers=candidate.get("blockers", ["Conflicting linked identity evidence"]))
    for key in ("birth", "death"):
        if current.get(key) and candidate.get(key) and current[key] != candidate[key]:
            current.update(status="identity_conflict", sex="unknown",
                           blockers=[f"Conflicting {key} across linked group identities"])
    if association not in current["associations"]:
        current["associations"].append(association)
    current["aliases"] = sorted(set(current.get("aliases", []) + candidate.get("aliases", [])))
    if current.get("sex") == "unknown" and candidate.get("sex") in {"male", "female"} and current["status"] != "identity_conflict":
        current["sex"] = candidate["sex"]


SCREEN_FIELDS = ("source_url", "source_sha256", "excerpt", "rationale", "as_of",
                 "stated_max_age_years", "tolerance_years")
MIN_SCREEN_TOLERANCE_YEARS = 5


def _age_screen(award: dict, cutoff: date) -> dict | None:
    """Accept an opt-in group-wide age statement only if it excludes surpassing the reference.

    A screen never completes a roster: the award stays unenumerated and is reported
    separately. The oldest possible member is the stated maximum plus a mandatory
    tolerance, and the existing age arithmetic must conclusively exclude that person.
    """
    screen = award.get("collective_age_screen")
    if not isinstance(screen, dict) or any(screen.get(key) in (None, "") for key in SCREEN_FIELDS):
        return None
    stated, tolerance = screen["stated_max_age_years"], screen["tolerance_years"]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (stated, tolerance)):
        return None
    if stated <= 0 or tolerance < MIN_SCREEN_TOLERANCE_YEARS:
        return None
    try:
        as_of = date.fromisoformat(screen["as_of"])
    except (TypeError, ValueError):
        return None
    if as_of > cutoff:
        return None
    oldest_year = as_of.year - stated - tolerance - 1
    probe = adjudicate_person(
        {"profile_url": award["profile_url"]},
        {"decision_id": "collective-age-screen", "subject_reviewed": True, "rationale": screen["rationale"],
         "birth": f"{oldest_year}/{as_of.year}"}, cutoff)
    if probe["status"] not in EXCLUDED:
        return None
    return {"award_id": award["award_id"], "name": award["name"], "profile_url": award["profile_url"],
            "as_of": screen["as_of"], "stated_max_age_years": stated, "tolerance_years": tolerance,
            "oldest_possible_birth_year": oldest_year, "source_url": screen["source_url"],
            "roster_complete": False,
            "blockers": award.get("blockers") or ["Roster not enumerated; group-wide age statement only"]}


def _rank_population(people: list[dict], inventory: dict, open_awards: list[dict], scope: str,
                     age_screened: list[dict] | None = None) -> dict:
    replay = {"people": people, "decisions": [
        {**person.get("comparison_review", {}), "person_id": person["person_id"]}
        for person in people], "cutoff": inventory["cutoff"],
        "summary": {"unresolved_collective_awards": len(open_awards)}}
    ranking = build_individual_ranking(replay)
    ranking.update(scope=scope, population_size=len(people),
                   unresolved_collective_awards=open_awards,
                   age_screened_collective_awards=age_screened or [],
                   historical_population_complete=not open_awards and not age_screened,
                   universal_maximum_established=False)
    by_id = {person["person_id"]: person for person in people}
    for row in ranking["people"]:
        person = by_id[row["person_id"]]
        review = person.get("comparison_review", {})
        row.update(birth_evidence=person.get("birth"),
                   death_evidence=person.get("death") or ("Died by " + person["death_not_after"]
                                                         if person.get("death_not_after") else None),
                   sex=person.get("sex", "unknown"),
                   associations=person.get("associations", []),
                   evidence_classification=evidence_classification(person, review),
                   source_quality=person.get("source_confidence", "needs_review"),
                   inference_assumptions=review.get("assumptions", []),
                   evidence_conflicts=review.get("conflicts", []),
                   associated_reviews=person.get("associated_reviews", []))
    ranking["status"] = "conditional_comparison" if open_awards or age_screened else ranking["status"]
    ranking["limits"].extend([
        "Collective members are comparison subjects; ensemble awards do not confer individual fellowship.",
        "Unenumerated members have no person row and block a historical maximum even when identified people screen below the reference.",
        "Accepted baseline inferred screens retain their original assumptions.",
        "Age-screened boundaries rest on a group-wide published age statement with tolerance; their rosters remain unenumerated.",
    ])
    return ranking


def _fully_screened(award: dict, people: dict, open_urls: set[str]) -> bool:
    if award["profile_url"] in open_urls:
        return False
    admitted = [member for member in award.get("members", [])
                if member.get("membership_status") == "award_year"]
    for member in admitted:
        identifier = member.get("person_id") or stable_id(
            "person", award["profile_url"] + "#member:" + member["name"])
        if people[identifier]["status"] not in EXCLUDED:
            return False
    return bool(admitted)


def build_collective_comparisons(inventory: dict, awards: list[dict]) -> dict:
    """Replay validated memberships into expanded and known-male comparisons.

    The caller validates source bindings before passing award records. Membership
    status is time-specific. Later, historical and uncertain members are retained
    as leads, never silently added to the award-year population. No I/O occurs.
    """
    cutoff = date.fromisoformat(inventory["cutoff"])
    decisions = {row["person_id"]: row for row in inventory["decisions"]}
    people = {}
    for original in inventory["people"]:
        person = deepcopy(original)
        person["associations"] = [{"award_id": original["award_id"],
            "profile_url": original["profile_url"], "award_year": original["award_year"],
            "label": original["name"], "relationship": "named_recipient",
            "individual_fellowship_asserted": True}]
        person["comparison_review"] = decisions.get(person["person_id"], {})
        people[person["person_id"]] = person
    original_ids = set(people)
    open_awards, age_screened, deferred_members, association_count = [], [], [], 0
    seen_awards = set()
    for award in awards:
        if award["profile_url"] in seen_awards:
            raise ValueError("Duplicate collective award assignment")
        seen_awards.add(award["profile_url"])
        award = {**award, "award_id": stable_id("award", award["profile_url"])}
        uncertain = False
        admitted = 0
        for member in award.get("members", []):
            if member.get("membership_status") != "award_year":
                deferred_members.append({**member, "award_id": award["award_id"]})
                uncertain |= member.get("membership_status") in {None, "uncertain"}
                continue
            if not member.get("membership_evidence"):
                raise ValueError("Award-year membership requires reviewed evidence")
            identifier = member.get("person_id") or stable_id(
                "person", award["profile_url"] + "#member:" + member["name"])
            if identifier in people and not member.get("identity_evidence"):
                raise ValueError("Repeated identity requires explicit linkage evidence")
            review = member.get("age_review") or {}
            subject = {"person_id": identifier, "award_id": award["award_id"],
                       "name": member["name"], "aliases": member.get("aliases", []),
                       "award_year": award["award_year"], "profile_url": award["profile_url"],
                       "privacy_label": "private_family_only"}
            candidate = adjudicate_person(subject, review or None, cutoff)
            if candidate["status"] != "identity_conflict" and member.get("sex_evidence"):
                candidate["sex"] = classify_documented_sex(
                    member.get("documented_sex") or member.get("sex_classification"))
            _merge_person(people, candidate, review, _association(award, individual=False))
            association_count += 1
            admitted += 1
        if (not award.get("membership_complete") or uncertain or not admitted) \
                and (screened := _age_screen(award, cutoff)):
            age_screened.append(screened)
        elif not award.get("membership_complete") or uncertain or not admitted:
            open_awards.append({"award_id": award["award_id"], "name": award["name"],
                                "profile_url": award["profile_url"],
                                "blockers": award.get("blockers") or ["Award-year membership boundary remains unresolved"]})
    missing = [group for group in inventory.get("ranking", {}).get("unresolved_groups", [])
               if group["profile_url"] not in seen_awards]
    open_awards.extend(deepcopy(missing))
    expected = inventory.get("summary", {}).get("unresolved_collective_awards", 0)
    if not missing and len(seen_awards) < expected:
        open_awards.append({"name": "Untriaged collective awards", "profile_url": "untriaged",
                            "blockers": [f"Only {len(seen_awards)} of {expected} expected awards supplied"]})
    everyone = list(people.values())
    expanded = _rank_population(everyone, inventory, open_awards,
                                "named_recipients_plus_award_year_collective_members", age_screened)
    males = [person for person in everyone if person.get("sex") == "male"]
    male_report = _rank_population(males, inventory, open_awards, "reviewed_known_male_people", age_screened)
    male_report["sex_unknown_person_ids"] = [p["person_id"] for p in everyone if p.get("sex") == "unknown"]
    male_report["limits"].append("Known-male subset ranks exclude sex-unknown people; no universal male record is established.")
    added = [person for identifier, person in people.items() if identifier not in original_ids]
    open_urls = {award["profile_url"] for award in open_awards}
    screened_urls = {award["profile_url"] for award in age_screened}
    unresolved_urls = open_urls | screened_urls
    summary = {
        "collective_awards_triaged": len(awards),
        "collective_membership_boundaries_resolved": sum(award["profile_url"] not in unresolved_urls for award in awards),
        "collective_awards_fully_age_screened": sum(_fully_screened(award, people, unresolved_urls) for award in awards),
        "award_year_membership_associations": association_count,
        "new_deduplicated_people": len(added),
        "expanded_people": len(everyone),
        "new_people_screened_below_reference": sum(p["status"] in EXCLUDED for p in added),
        "new_people_with_unresolved_age": sum(p["status"] not in EXCLUDED for p in added),
        "documented_above_reference_person_ids": [p["person_id"] for p in everyone
                                                   if p["status"] == "verified_above_roma"],
        "identified_people_screened_below_reference": sum(p["status"] in EXCLUDED for p in everyone),
        "unresolved_membership_boundaries": len(open_awards),
        "boundaries_age_screened_without_complete_roster": len(age_screened),
        "deferred_membership_leads": len(deferred_members),
        "universal_maximum_established": False,
    }
    result = {"schema_version": "aave.nea-collective-comparison.v1",
              "privacy_label": "private_family_only", "cutoff": inventory["cutoff"],
              "summary": summary, "expanded": expanded, "male_only": male_report,
              "deferred_members": deferred_members}
    return result
