---
name: us-census-finder
description: Plan free 1940 and 1950 U.S. census finders from National Archives schedules, enumeration-district tools, and saved vendor indexes.
---

# U.S. census finder

Use `nea_archiver.nea_census.census_finder_plan`. Read [genealogy-public-api-pull](../genealogy-public-api-pull/SKILL.md) before any request. A finder plan is not a fetch and not an age exclusion.

## Pair with broad public search

When authorized to search externally, pair this skill with
[exa-public-search](../exa-public-search/SKILL.md). Generate the 1940 and
1950 finder plans first, then use the same bounded `execute_batch` runner
with the explicitly enabled Exa adapter for discovery. This does not enable
automated access to the census or genealogy platforms themselves.

1. Build a public identity card from reviewed source URLs: documented names
   and aliases, birthplace, dated residences and occupation. Keep candidate
   expansions separate from documented aliases. An adult residence is not
   evidence of census-era residence; an inferred birth range is not an input
   fact. Do not send private-lane names, relatives, addresses or record pointers.
2. Broaden discovery across full name, documented aliases, spelling variants,
   census year, publicly documented place and independent biographical context.
   Use both general web queries and archive-specific queries when useful;
   do not require every result to match the recipient's current stage name.
   Record a fixed budget and explicit external-emission labels. Reuse matching
   cached queries and retain failed/empty results instead of resetting them.
3. Review one returned candidate source at a time. Record its role as an
   identity lead, index transcription, original schedule or unrelated namesake.
   A broad search result and an authority/index match do not establish a
   person match. Preserve conflicts and independently corroborate identity.
4. For a plausible schedule candidate, follow the declared public NARA path
   or review a user-owned saved image. Keep enumeration district, sheet, line,
   original name, index spelling, reported age, image provenance and identity
   confidence together. Stop at login, CAPTCHA or access restrictions.
5. Only a reviewed, identity-matched schedule age may reach
   `census_age_excludes_reference`. A missing 1940/1950 result does not prove
   the person was unborn, deceased or absent. People born after the census
   need another dated-age source; do not manufacture a census candidate.

Report search yield separately from schedule matches and accepted age bounds.
For NEA closure the combined search remains within the 40-query cap; a broader
search does not relax the identity or original-image requirements.

If census discovery lacks an identity-matched schedule, use the paired
[person-record source layers](../exa-public-search/references/person-records.md)
for memorials, obituaries, cemeteries, historical archives and public vital
records within the same budget. Check birth-record jurisdiction and year
coverage before interpreting a missing index or seeking a certificate.

1940 and 1950 Ancestry census listings are vendor transcriptions of National Archives population schedules. Prefer the public schedule path:

1. 1950 name index: `https://1950census.archives.gov/`. Account not required. A hit is an index lead. Record the original schedule before treating the index spelling as the name.
2. 1940 finding aid: `https://www.archives.gov/research/census/1940`. There is no keyless 1940 person API. Use an enumeration district, then the schedule series.
3. National Archives Catalog: `nara_catalog_request`. It describes series. It does not return a named person. Leave `nara_catalog_adapter` disabled unless a caller supplies the callback.
4. Enumeration district: `https://stevemorse.org/census/unified.html`, with name, year, state, and county filled by hand.
5. FamilySearch census collection: wiki and developer terms only. Do not automate a login.
6. Ancestry: private research may cite a user-owned saved index row. Do not log in or scrape Ancestry. Keep index spelling variants distinct from the original. Public examples must be synthetic and must not include private census claims.

For private research, preserve schedule fields and match confidence locally. Reported age is not an exact birth date. Use `census_age_excludes_reference` only with a reviewed age. Synthetic example: a person reported age20 in1940 supports a different bound from a person reported age29 in1940. A missing finder result stays unresolved. Publish only independently reviewed public facts; private census claims remain in the private vault.

## Agentic-loop finders

Call `genealogist_search_plan` for one person, then one provider, then stop and read the page. The closure batch attaches these rows as `genealogist_finders`. Every row has `automated_access: false`.

| Provider | What the loop may do | What it must not do |
| --- | --- | --- |
| Chronicling America | Open the keyless JSON URL for `name` plus `obituary` and read at most five hits | Treat a name hit as the same person |
| Steve Morse | Open the unified census form with year, state, and county | Submit scripted lookups across a cohort |
| FamilySearch | Follow a public wiki or a user-saved record link | Log in or walk a tree automatically |
| Masters of Traditional Arts | Open the fellow's directory biography and copy a printed lifespan only after the NEA name matches | Infer sex or a missing death |
| Find a Grave | Open one user-saved memorial | Crawl memorials or merge an identity from a similar name |

Birth wording goes through `nea_archiver.nea_classification.identify_subject_birth`. It keeps a year that follows "born," including a year in the biography lead, and drops a relative's birth, a decade such as "1950s," and an event that was merely "born" in a later year. Approximate wording stays muted. A reported age at death is a bound. It is not a gerontology validation and not a ranking claim.
