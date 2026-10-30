"""Conservative rank envelopes for reviewed named recipients at a fixed cutoff."""

from __future__ import annotations

from aave.nea_research import EXCLUDED


def _age_envelope(person: dict, decision: dict) -> dict:
    """Keep screening caps separate from documented completed lifespans."""
    envelope = {"lower": [0, 0], "upper": None, "upper_exclusive": False,
                "basis": "unresolved_age"}
    if person.get("status") not in EXCLUDED | {"verified_equal_roma", "verified_above_roma"}:
        return envelope
    if person.get("completed_lifespan_documented") and person.get("upper_age"):
        envelope.update(lower=person["upper_age"], upper=person["upper_age"],
                        basis="exact_date_completed_lifespan")
    elif person.get("upper_age"):
        # A deceased-by marker may be a cap, so it supplies no lower endpoint.
        envelope.update(upper=person["upper_age"], basis="screening_upper_bound_only")
    elif decision.get("completed_age_years") is not None and decision.get("death_by_cutoff"):
        years = decision["completed_age_years"]
        if isinstance(years, bool) or not isinstance(years, int) or years < 0:
            raise ValueError("Invalid reviewed completed age")
        envelope.update(lower=[years, 0], upper=[years + 1, 0], upper_exclusive=True,
                        basis="reported_completed_whole_years")
    return envelope


def _definitely_older(other: dict, subject: dict) -> bool:
    """Compare a known lower endpoint with the subject's possible upper endpoint."""
    if subject["upper"] is None:
        return False
    lower, upper = tuple(other["lower"]), tuple(subject["upper"])
    is_older = lower > upper or (lower == upper and subject["upper_exclusive"])
    return is_older


def _possibly_older(other: dict, subject: dict) -> bool:
    """An unbounded person can intervene; exact ties never count as strictly older."""
    if other["upper"] is None:
        return True
    is_older = tuple(other["upper"]) > tuple(subject["lower"])
    return is_older


def build_individual_ranking(inventory: dict) -> dict:
    """Return possible competition ranks for every named person; exclude open groups.

    Input is a validated resolve_inventory replay. Rank is one plus the number
    strictly older, with shared ranks for ties. Conservative marginal envelopes
    can overlap and do not assert a complete order or independent vital validation.
    No file writes, retrieval, sex inference, or future lifespan projection occur.
    """
    decisions = {row["person_id"]: row for row in inventory["decisions"]}
    people = inventory["people"]
    identifiers = [person["person_id"] for person in people]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Named person identifiers must be unique")
    envelopes = {person["person_id"]: _age_envelope(
        person, decisions.get(person["person_id"], {})) for person in people}
    exact = [person for person in people
             if envelopes[person["person_id"]]["basis"] == "exact_date_completed_lifespan"]
    rows = []
    for person in people:
        identifier = person["person_id"]
        envelope = envelopes[identifier]
        others = [envelopes[key] for key in identifiers if key != identifier]
        best = 1 + sum(_definitely_older(other, envelope) for other in others)
        worst = 1 + sum(_possibly_older(other, envelope) for other in others)
        subset_rank = None
        if envelope["basis"] == "exact_date_completed_lifespan":
            subset_rank = 1 + sum(tuple(other["upper_age"]) > tuple(person["upper_age"])
                                  for other in exact)
        rows.append({"person_id": identifier, "name": person["name"],
                     "award_year": person["award_year"], "profile_url": person["profile_url"],
                     "status": person["status"], "age_envelope": envelope,
                     "possible_rank_best": best, "possible_rank_worst": worst,
                     "exact_date_subset_rank": subset_rank,
                     "evidence_decision": person.get("evidence_decision"),
                     "source_urls": person.get("evidence_urls", [person["profile_url"]])})
    rows.sort(key=lambda row: (row["possible_rank_best"], row["possible_rank_worst"],
                               row["name"].casefold(), row["person_id"]))
    unresolved = [row["person_id"] for row in rows if row["age_envelope"]["upper"] is None]
    report = {"schema_version": "aave.nea-individual-ranking.v1",
              "privacy_label": "private_family_only", "cutoff": inventory["cutoff"],
              "scope": "all_resolved_named_people_excluding_unresolved_collectives",
              "named_people": len(rows),
              "excluded_collective_awards": inventory["summary"]["unresolved_collective_awards"],
              "status": "not_established" if unresolved else "bounded_comparison_available",
              "complete_total_order_established": all(
                  row["possible_rank_best"] == row["possible_rank_worst"] for row in rows),
              "unresolved_person_ids": unresolved, "exact_date_subset_size": len(exact),
              "rank_definition": "1 + count strictly older; ties share competition rank",
              "limits": ["Ranges are conservative marginal envelopes, not an exact total order.",
                         "Screening caps are not ages at death or assertions of current survival.",
                         "A lower age of zero means no lower age used, not a claimed death in infancy.",
                         "Exact-date subset positions are not overall ranks.",
                         "No future lifespan or universal male rank is inferred."],
              "people": rows}
    return report
