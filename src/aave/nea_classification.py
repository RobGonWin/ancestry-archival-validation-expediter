"""Person-level sex, birth-bound, census and relationship screening.

Sex is taken only from an explicit reviewed label. A name or pronoun is not a
classification. A late birth year can exclude exceeding the reference age at
the cutoff without predicting a living person's eventual lifespan.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from aave.nea_dates import DEFAULT_CUTOFF, attained_age

REFERENCE_AGE = (107, 307)
DOCUMENTED_SEX = {"male": "male", "female": "female"}


def classify_documented_sex(label: str | None) -> str:
    """Return male or female only when the review states that label."""
    documented_sex = DOCUMENTED_SEX.get((label or "").strip().lower(), "unknown")
    return documented_sex


def birth_year_upper_bound(birth_year: int, cutoff: date = DEFAULT_CUTOFF) -> tuple[int, int]:
    """Maximum attained age if birth were January 1 of the reported year."""
    upper_age = attained_age(date(birth_year, 1, 1), cutoff)
    return upper_age


def _fold_letters(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character)).lower()


def identify_subject_birth(text: str, person_name: str, *, award_year: int | None = None) -> dict | None:
    """Find a birth year that follows "born" and belongs to the named person.

    A year before the word born, a decade such as "1950s," or a relative's birth
    is ignored. A birth in the opening biography is kept when the surname is
    farther back than the local window. Approximate wording stays muted.
    """
    tokens = re.findall(r"[A-Za-z]+", _fold_letters(person_name or ""))
    surname = tokens[-1] if tokens else ""
    bio_start = text.find(" Bio ")
    pattern = re.compile(
        r"\b(?:was born|born)\b(?:(?!\b(?:18|19|20)\d\d\b).){0,60}((?:18|19|20)\d\d)\b(?!s)",
        re.I)
    relative_words = re.compile(r"\b(son|daughter|mother|father|grandmother|grandfather)\b", re.I)
    approximate_words = re.compile(r"\b(about|around|probably|circa)\b", re.I)
    for match in pattern.finditer(text):
        window = " ".join(text[max(0, match.start() - 90):match.end()].split())
        before_born = window.lower().rsplit("born", 1)[0]
        if relative_words.search(before_born):
            continue
        in_biography_lead = bio_start >= 0 and bio_start <= match.start() <= bio_start + 500
        if surname and surname not in _fold_letters(window) and not in_biography_lead:
            continue
        if award_year and int(match.group(1)) == award_year and "born in " + str(award_year) not in window.lower():
            continue
        birth_year = int(match.group(1))
        approximate = bool(approximate_words.search(window))
        excludes_reference = (not approximate) and birth_year_excludes_reference(birth_year)
        if approximate:
            disposition = "muted_approximate"
        elif excludes_reference:
            disposition = "exclude_by_birth_year"
        else:
            disposition = "needs_death_or_census"
        return {"birth_year": birth_year, "excerpt": window[-140:], "approximate": approximate,
                "excludes_reference": excludes_reference, "disposition": disposition}
    return None


def birth_year_excludes_reference(birth_year: int, cutoff: date = DEFAULT_CUTOFF) -> bool:
    """True when even the earliest day of the year stays below the reference age."""
    excludes_reference = birth_year_upper_bound(birth_year, cutoff) < REFERENCE_AGE
    return excludes_reference


def reconcile_alias(explicit_same_person: bool) -> str:
    """Keep similar names distinct until a reviewed source links them."""
    linkage = "same_person" if explicit_same_person else "distinct_until_documented"
    return linkage


def genealogy_crosswalk(row: dict) -> dict:
    """Link public identifiers without treating a shared name as identity."""
    confidence = row.get("identity_match_confidence", "needs_review")
    if confidence not in {"verified_match", "probable", "possible_match", "rejected_match", "needs_review"}:
        confidence = "needs_review"
    linked = confidence in {"verified_match", "probable"}
    result = {
        "aave_person_id": row.get("aave_person_id"),
        "public_tree_person_id": row.get("public_tree_person_id"),
        "memorial_id": row.get("memorial_id"),
        "identity_match_confidence": confidence,
        "identifiers_may_be_cited_together": linked,
        "silent_identity_merge": False,
    }
    return result


def relationship_episode(record: dict) -> dict:
    """Keep a time-specific relationship without inventing its end."""
    episode = {
        "subject": record["subject"],
        "counterpart": record["counterpart"],
        "role": record["role"],
        "observed_context": record["observed_context"],
        "source_role": record["source_role"],
        "end_established": False,
        "divorce_or_death_inferred": False,
        "supports_longevity_rank": False,
        "supports_genetic_relationship": False,
    }
    return episode


def male_person_coverage(people: list[dict], reference_id: str) -> dict:
    """Separate known-male competitors from unresolved sex and collectives."""
    others = [person for person in people if person.get("person_id") != reference_id]
    excluded = {"verified_below_roma", "bounded_below_roma_at_cutoff"}
    open_people = [person for person in others if person.get("status") not in excluded]
    known_male = [person for person in open_people if person.get("sex") == "male"]
    sex_unknown = [person for person in open_people if person.get("sex") == "unknown"]
    summary = {
        "known_male_unresolved_count": len(known_male),
        "sex_unknown_unresolved_count": len(sex_unknown),
        "known_male_is_not_sex_unknown": True,
        "universal_male_rank_established": False,
    }
    return summary
