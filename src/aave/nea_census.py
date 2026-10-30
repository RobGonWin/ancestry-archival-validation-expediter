"""Public census and genealogy leads for the person-closure batch.

Name-level 1940 and 1950 schedules are not exposed by a free keyless person
API. The key-required National Archives Catalog API can describe record series. Ancestry,
FamilySearch, funeral homes and Find a Grave stay reviewable URL plans until
an enabled adapter is supplied. A failed or skipped search is not an exclusion.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from aave.nea_dates import DEFAULT_CUTOFF, attained_age
from aave.nea_discovery import DEFAULT_PROVIDERS, SearchAdapter, discovery_queries

REFERENCE_AGE = (107, 307)

NARA_CATALOG_TERMS = "https://www.archives.gov/research/catalog/help/api"
NARA_CATALOG_ENDPOINT = "https://catalog.archives.gov/api/v2/records/search"
CENSUS_YEARS = (1940, 1950)

CLOSURE_PROVIDERS = {
    "nara_catalog": '"{name}" {year} census population schedule',
    "census_index_lead": '"{name}" {year} census enumeration district',
    "familysearch_public": '"{name}" site:familysearch.org/ark:',
    "ancestry_public_lead": '"{name}" public Ancestry tree person',
    "findagrave": DEFAULT_PROVIDERS["findagrave"],
    "funeral": DEFAULT_PROVIDERS["funeral"],
}


def nara_catalog_request(name: str, census_year: int) -> dict:
    """Plan a key-required catalog search; this does not execute a request."""
    parameters = urlencode({"q": f"{name} {census_year} census population schedules"})
    request = {
        "provider": "nara_catalog",
        "method": "GET",
        "url": NARA_CATALOG_ENDPOINT + "?" + parameters,
        "terms_url": NARA_CATALOG_TERMS,
        "requires_account": False,
        "api_key_required": True,
        "api_key_header": "x-api-key",
        "automated_access": False,
        "terms_review_required": True,
        "note": "NARA requires an assigned key. Its terms and getting-started guide conflict on saving responses; resolve that conflict before enabling cached retrieval.",
        "returns_named_person": False,
        "result_role": "series_or_description_lead",
    }
    return request


def census_finder_plan(name: str, census_year: int, *, state: str = "", county: str = "") -> list[dict]:
    """Plan the public finders that sit behind a 1940 or 1950 Ancestry census listing.

    The catalog request describes the schedule series. The 1950 NARA site is the
    free official name index. Steve Morse locates an enumeration district when
    the name index is missing or spelled differently. FamilySearch and Ancestry
    stay manual: both may require an account, and Ancestry is not automated.
    """
    if census_year not in CENSUS_YEARS:
        raise ValueError("This finder covers the released 1940 and 1950 population schedules")
    if census_year == 1950:
        name_index = {
            "provider": "nara_1950_name_search",
            "url": "https://1950census.archives.gov/",
            "terms_url": "https://www.archives.gov/research/census/1950",
            "requires_account": False,
            "automated_access": False,
            "returns_named_person": True,
            "result_role": "official_name_index_lead",
            "note": "Free NARA name search of the 1950 schedules. Ancestry's 1950 listing is a separate transcription of these schedules.",
        }
    else:
        name_index = {
            "provider": "nara_1940_research_guide",
            "url": "https://www.archives.gov/research/census/1940",
            "terms_url": "https://www.archives.gov/research/census/1940",
            "requires_account": False,
            "automated_access": False,
            "returns_named_person": False,
            "result_role": "schedule_finding_aid",
            "note": "No keyless 1940 person API. Ancestry's 1940 name index is a vendor transcription of the same NARA schedules.",
        }
    plan = [
        {**name_index, "name": name, "census_year": census_year, "state": state, "county": county},
        {**nara_catalog_request(name, census_year), "finder": "nara_catalog",
         "name": name, "census_year": census_year, "state": state, "county": county},
        {"provider": "steve_morse_ed_finder", "url": "https://stevemorse.org/census/unified.html",
         "terms_url": "https://stevemorse.org/", "method": "GET", "requires_account": False,
         "automated_access": False, "returns_named_person": False,
         "result_role": "enumeration_district_finder", "name": name, "census_year": census_year,
         "state": state, "county": county},
        {"provider": "familysearch_census_collection",
         "url": "https://www.familysearch.org/en/wiki/United_States_Census",
         "terms_url": "https://www.familysearch.org/developers/", "requires_account": True,
         "automated_access": False, "returns_named_person": False, "result_role": "collection_lead",
         "name": name, "census_year": census_year, "state": state, "county": county,
         "note": "Some FamilySearch census images require a free account. Do not automate login."},
        {"provider": "ancestry_census_index", "url": None, "requires_account": True,
         "automated_access": False, "returns_named_person": False,
         "result_role": "vendor_index_equivalent", "name": name, "census_year": census_year,
         "state": state, "county": county,
         "note": "Use a user-owned saved Ancestry index row, or the public NARA finder for the same schedule. Do not log in or scrape Ancestry."},
    ]
    return plan


def genealogist_search_plan(name: str, *, birth_year: int | None = None) -> list[dict]:
    """Plan public genealogist and obituary finders an agent loop can follow one at a time.

    Every row is a lead. None is an age fact until a person reads the returned page.
    Login, account, and bulk-scrape paths stay closed.
    """
    if not name.strip():
        raise ValueError("A genealogist search needs a person name")
    year_term = str(birth_year) if birth_year else ""
    obituary_query = " ".join(part for part in (name, year_term, "obituary") if part)
    newspaper_parameters = urlencode({
        "proxtext": obituary_query,
        "format": "json",
        "rows": 5,
    })
    plan = [
        {"provider": "chronicling_america",
         "url": "https://chroniclingamerica.loc.gov/search/pages/results/?" + newspaper_parameters,
         "terms_url": "https://chroniclingamerica.loc.gov/about/",
         "requires_account": False, "automated_access": False, "returns_named_person": False,
         "result_role": "newspaper_lead", "name": name, "birth_year": birth_year,
         "note": "Keyless newspaper JSON. Read one result, then stop. A name hit is not an identity match."},
        {"provider": "stevemorse_census",
         "url": "https://stevemorse.org/census/unified.html",
         "terms_url": "https://stevemorse.org/",
         "requires_account": False, "automated_access": False, "returns_named_person": False,
         "result_role": "enumeration_district_lead", "name": name, "birth_year": birth_year,
         "note": "Fill year, state, and county by hand. Use with census_finder_plan."},
        {"provider": "familysearch_wiki",
         "url": "https://www.familysearch.org/en/wiki/United_States_Census",
         "terms_url": "https://www.familysearch.org/developers/",
         "requires_account": True, "automated_access": False, "returns_named_person": False,
         "result_role": "collection_lead", "name": name, "birth_year": birth_year,
         "note": "Use a public or user-saved record. Do not automate login."},
        {"provider": "masters_traditional_arts",
         "url": "http://www.mastersoftraditionalarts.org/",
         "terms_url": "http://www.mastersoftraditionalarts.org/",
         "requires_account": False, "automated_access": False, "returns_named_person": False,
         "result_role": "biography_lead", "name": name, "birth_year": birth_year,
         "note": "Directory biography. Confirm the NEA fellow before using a printed lifespan."},
        {"provider": "findagrave_memorial",
         "url": None, "requires_account": False, "automated_access": False,
         "returns_named_person": False, "result_role": "memorial_lead",
         "name": name, "birth_year": birth_year,
         "note": "Open a user-saved memorial page. Do not crawl Find a Grave."},
    ]
    return plan


def earliest_birth_from_reported_age(census_year: int, reported_age: int) -> date:
    """Earliest birth consistent with a completed age on the April 1 census date.

    Age 20 on April 1, 1940 was born after April 1, 1919 and on or before April 1, 1920.
    """
    if census_year not in CENSUS_YEARS:
        raise ValueError("Reported-age bounds are defined for the 1940 and 1950 censuses")
    if isinstance(reported_age, bool) or not isinstance(reported_age, int) or reported_age < 0:
        raise ValueError("Census age must be a nonnegative integer")
    earliest = date(census_year - reported_age - 1, 4, 2)
    return earliest


def census_age_excludes_reference(census_year: int, reported_age: int,
                                  cutoff: date = DEFAULT_CUTOFF) -> bool:
    """True when even the earliest birth implied by the reported age stays below the reference.

    A census age is not an exact birth date. It can still show that the person
    could not have reached the reference age by the cutoff.
    """
    upper_age = attained_age(earliest_birth_from_reported_age(census_year, reported_age), cutoff)
    excludes_reference = upper_age < REFERENCE_AGE
    return excludes_reference


def nara_catalog_adapter(search=None, *, enabled: bool = False) -> SearchAdapter:
    """Disabled until a caller supplies an authorized callback."""
    def unavailable(_query: str) -> list[dict]:
        raise ValueError("NARA catalog adapter is not enabled")

    adapter = SearchAdapter(search=search or unavailable, terms_url=NARA_CATALOG_TERMS,
                            enabled=enabled and search is not None)
    return adapter


def census_schedule_lead(observation: dict) -> dict:
    """Normalize a reviewed schedule or an access receipt. Ages are not exact births."""
    lead = {
        "census_year": observation.get("census_year"),
        "enumeration_district": observation.get("enumeration_district"),
        "sheet": observation.get("sheet"),
        "line": observation.get("line"),
        "original_name": observation.get("original_name"),
        "index_variant": observation.get("vendor_name"),
        "reported_age": observation.get("reported_age"),
        "residence": observation.get("residence"),
        "household_relationships": observation.get("household_relationships", []),
        "image_provenance": observation.get("image_provenance"),
        "identity_match_confidence": observation.get("identity_status", "needs_review"),
        "access_state": observation.get("access_state", "reviewed_local_copy"),
        "establishes_exact_vital_dates": False,
        "transcription_conflict": bool(
            observation.get("original_name") and observation.get("vendor_name")
            and observation["original_name"] != observation["vendor_name"]),
    }
    return lead


def prioritize_people(people: list[dict], preferred_names: list[str] | None = None) -> list[dict]:
    """Cohort-D names first, then early or missing birth years. Sex unknown is not male."""
    preferred = {name.casefold() for name in (preferred_names or [])}

    def sort_key(person: dict) -> tuple:
        birth = person.get("birth") or ""
        birth_year = int(birth[:4]) if len(birth) >= 4 and birth[:4].isdigit() else None
        early_or_missing = birth_year is None or birth_year < 1920
        return (person["name"].casefold() not in preferred, not early_or_missing,
                person.get("award_year") or 9999, person["person_id"])

    ordered = sorted(people, key=sort_key)
    return ordered


def plan_closure_batch(people: list[dict], *, person_limit: int = 30,
                       query_limit: int = 40, preferred_names: list[str] | None = None) -> dict:
    """Cap unresolved public people and fresh queries before any network call."""
    if person_limit < 1 or query_limit < 1:
        raise ValueError("Closure batch limits must be positive")
    open_people = [person for person in people
                   if person.get("privacy_label") == "public_ok"
                   and person.get("status") not in {"verified_below_roma", "bounded_below_roma_at_cutoff"}]
    selected = prioritize_people(open_people, preferred_names)[:person_limit]
    queries = []
    for person in selected:
        for row in discovery_queries(person, CLOSURE_PROVIDERS):
            if len(queries) >= query_limit:
                break
            queries.append(row)
        if len(queries) >= query_limit:
            break
    plan = {"person_limit": person_limit, "query_limit": query_limit,
            "people_selected": len(selected), "queries": queries,
            "query_count": len(queries),
            "known_male_selected": sum(person.get("sex") == "male" for person in selected),
            "sex_unknown_selected": sum(person.get("sex") != "male" and person.get("sex") != "female"
                                        for person in selected),
            "network_calls": 0,
            "census_finders": [row for person in selected
                               for year in CENSUS_YEARS
                               for row in census_finder_plan(person["name"], year)],
            "genealogist_finders": [row for person in selected
                                    for row in genealogist_search_plan(person["name"])]}
    plan["census_finder_count"] = len(plan["census_finders"])
    return plan
