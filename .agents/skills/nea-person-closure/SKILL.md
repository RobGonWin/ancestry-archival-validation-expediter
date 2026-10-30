---
name: nea-person-closure
description: Classify NEA people, screen early births, and plan a capped public census or genealogy batch without treating unknown sex as male.
---

# NEA person-level closure

Read [nea-verification](../nea-verification/SKILL.md). Use `nea_archiver.nea_census.plan_closure_batch` and `nea_archiver.nea_discovery.execute_batch`. Do not invent a second search runner.

For an explicitly enabled Exa provider, follow [exa-public-search](../exa-public-search/SKILL.md). It uses the same runner and checkpoints; the NEA limits and evidence rules below still apply.

For census discovery, pair the public identity and 1940/1950 finder plans with
the broad-search procedure in [us-census-finder](../us-census-finder/SKILL.md).
Review the original schedule and identity before promoting any Exa candidate
to a reported-age bound.

For the broader memorial, obituary, cemetery, archive and public birth-record
pass, use the [paired source layers](../exa-public-search/references/person-records.md)
and the NEA [discovery and memorial rules](../nea-verification/references/discovery-and-memorials.md).
Share the query budget across layers and preserve distinct source roles.

1. Reuse cached profiles and matching checkpoints. Cap the batch at 30 unresolved people and 40 new queries.
2. Classify sex only from an explicit reviewed label (`nea_archiver.nea_classification.classify_documented_sex`). Names and pronouns stay `unknown`.
3. Exclude a birth year at the cutoff only when January 1 of that year is still below the reference age. A missing search is not an exclusion.
4. Census and public genealogy: follow [us-census-finder](../us-census-finder/SKILL.md). Call `census_finder_plan` for 1940 and 1950 and `genealogist_search_plan` for Chronicling America, Steve Morse, FamilySearch, Masters of Traditional Arts, and a saved Find a Grave memorial. Take one provider for one person, then read the page. Do not log in or scrape account data. Use `identify_subject_birth` before a new search so a biography birth year is not missed and a relative's year is not kept.
5. Record year, enumeration district, sheet, line, original name, index variant, age, residence, relationships, image provenance and match confidence. Preserve spelling conflicts. Census age is not an exact vital date.
6. Keep time-specific relationships separate. Do not invent a death, divorce or marriage date. Do not treat the batch as a universal longevity rank.

Write decisions with source URL, subject match, date precision, source hash and conflicts. Stop when the cap or a blocked adapter is reached.
