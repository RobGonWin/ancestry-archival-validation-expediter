# Pair public person-record sources

Use this reference when a public-person research question needs census,
memorial, archival or vital-record discovery. Pair with
[us-census-finder](../../us-census-finder/SKILL.md) for schedules and
[genealogy-public-api-pull](../../genealogy-public-api-pull/SKILL.md) for
declared archive routes. Search through the existing Exa adapter and runner;
this reference does not enable a provider's account or record API.

Build queries from reviewed public names, documented aliases and dated place
or occupation context. Label uncertain alias expansions as candidates. Reuse
cached queries and originals before allocating a shared fresh-query budget
across the layers below. Add new queries for missing source layers or new
identity evidence, rather than resetting an exhausted batch.

| Layer | Useful discovery routes | Review before accepting an age |
| --- | --- | --- |
| Official biography | Awarding institution, commemorations, death statements; for traditional artists, NEA and Masters of Traditional Arts | Is the age or birth wording about the subject? Career duration, founding dates and relatives' ages are separate claims. |
| Obituary or memorial | Funeral-home originals, funeral-home-backed Tribute Archive notices, Legacy, newspaper and institutional memorials | Match occupation, place and independently documented identity. Preserve publication, death and service dates separately; identify syndicated copies. |
| Burial | Find a Grave, BillionGraves, official cemetery directories and interment registers | A directory, register, photographed inscription and funeral notice have different roles. Record memorial/interment identifiers and image attribution; do not merge namesakes or invent a death from a search hit. |
| Census | NARA schedules, enumeration districts and supplied local index records | Keep the original image, district, sheet, line, reported age and supported identity match together. An index alone does not establish the schedule fact. |
| Birth or other vital record | Public civil registers, historical birth indexes, state or municipal archives; supplied authorized records | Check jurisdiction, record type, year coverage and public-access eligibility first. An index is not a certificate; a certificate for a namesake is not an identity match. Do not order restricted records or submit eligibility documents as part of public discovery. |
| Historical context | State historical societies, digital libraries, archive catalogs and public oral histories | Finding aids identify collections; inspect the relevant accessible original for a subject age. Do not assign collection dates to the person. |
| Genealogy index | Public search-engine discovery of FamilySearch/Ancestry records, or user-supplied local exports | Discovery does not authorize automated platform access. Preserve index/original distinctions and stop at login or other restrictions. |
| Longevity reference | Appropriate historical or gerontology references when the person and question warrant them | Preserve the source's scope and status; an archival age bound is not independent longevity validation. |

For each candidate, record the source URL, retrieval receipt/hash, original or
derivative role, subject-match evidence, date precision, dependencies,
contradictions and access state. A missing memorial does not show that someone
is living; a missing census does not show that someone was unborn. Public
search results can contain irrelevant sensitive identifiers: do not copy them
into research summaries or use them to expand the private case.

Report fresh and reused queries, unique candidate URLs, originals reviewed,
identity-matched records, accepted age bounds, conflicts and blocked routes
separately. Multiple URLs can represent one original. Do not report a source
coverage percentage without a defined, justified denominator. Count an
unresolved lead as unresolved even when every planned query has completed.


## Tiered age correction and ranking replay

Use this pass when a cutoff cap appears for a known deceased subject, a new
memorial contradicts a row, or a user requests an updated comparison. Zero
unresolved screening ages does not mean every lifespan is documented.

1. **Tier A — Direct age evidence:** official biographies, dated interviews,
   obituary originals, funeral notices, openly accessible death certificates
   and institutional memorials. Wikipedia and Wikidata can lead to cited
   originals; inspect those originals before changing a reviewed date. A page
   edit, infobox or search snippet alone cannot silently overwrite a ledger.
2. **Tier B — Historical records:** original 1940/1950 or publicly released
   earlier census schedules, NARA finding aids, Library of Congress, state
   archives, university collections and period newspapers. Pair a program's
   exact title, year, edition and page with its roster and relevant dated
   biographies. A recording lineup or festival appearance is not automatically
   the award-year membership. Catalog dates are not subject ages.
3. **Tier C — Genealogy and memorial cross-references:** use the access routes
   below to find underlying records. Preserve tree/index spellings alongside
   originals; tree assertions and duplicated memorials do not create independent
   corroboration. Multiple dates from one obituary remain one date origin.

Prefer exact dates, then documented birth year or age on a known date, original
census age with supported identity, dated events explicitly stating subject age,
then source-linked one-sided bounds with independently reviewed assumptions.
Leave unresolved when no defensible bound exists. Do not derive a DOB from a
career duration, a relative's age, a group founding or an approximate age.
Only a conservative source-constrained bound conclusively below Roma supports
an inferred exclusion. Keep documented, bounded, inferred_probable, conflicted
and unresolved separate. Missing search results never establish an age ceiling.

Match identity using several available attributes: name/aliases, award year,
occupation, geography, family context and chronology. Do not transmit private
relative information. Preserve source URL, retrieval date, hash representation,
original/indexed spelling, image or memorial ID, page/line, date precision,
source dependencies, accepted fields and rejected interpretations. A listing
is not a verified grave photograph; a memorial namesake is not the artist.
Retain relevant earlier memorial evidence, including McKiver, without assigning
relatives' ages to the subject or substituting a historical lineup for a roster.

A dated announcement of death can establish `death_not_after`; it cannot supply
an exact death date. Keep publication, death and funeral/service dates distinct.
Bind corrections to a subject-specific reviewed ledger row and its normalized
hash; preserve superseded decisions and contradictions. Validate birth, death
AND death-not-after against that row. Reject conflicting identities or dates
before replay. Do not fill an unknown date from a generated table.

Rebuild individual and collective comparisons from the same corrected reviews,
then regenerate the comment table and companion from those artifacts. Verify
input hashes, fixed cutoff, person versus award denominators, association scope,
date precision, lower/upper ages and possible-place ranges. Candidate display
row is not lifespan rank. Exact-date subset ordering is not an unconditional
population ordering. Cap-only rows are not survival claims. Keep unnamed group
members outside a supposedly complete person ranking; keep universal ranking
unresolved while membership boundaries remain open. Publish only within the
user's separately authorized scope. Use synthetic tests for correction binding,
publication-date ceilings and deterministic table selection.

## Provider access checklist

These are candidate access routes, not enabled adapters or verified current API
entitlements. Before a new automated request, inspect the provider's current
official documentation, terms, license, authentication and rate limits; record
the permitted endpoint and approval state. Use the existing disabled-by-default
Exa adapter for authorized public discovery. Public visibility alone does not
authorize record retrieval or platform automation. No login automation, CAPTCHA
bypass or indiscriminate scraping.

| Provider/source | Route to evaluate before retrieval | Evidence gate |
| --- | --- | --- |
| Public FamilySearch records | Public discovery leads, supplied saved records, or a future explicitly implemented official connector after access review | No automated account access under this workflow; inspect the authorized original schedule/certificate and identity. |
| WikiTree | Public profile leads; evaluate official developer documentation for an explicitly enabled future API adapter | Profile assertion versus cited original remains distinct; preserve profile ID and dependency chain. No assumed API permission. |
| Publicly shared family trees | Explicitly supplied local export or reviewed permitted public material | Preserve owner/source assertions, redact living/private relatives; reject circular copied-tree corroboration. |
| FamilyTreeNow-style directories | Only a specifically permitted route after current terms review | Default disabled; no presumed public API, bulk people search or private-relative transmission. |
| Saved Ancestry/GEDCOM | User-owned local saved pages and exports through existing local parsers | Preserve IDs and citations; no Ancestry login/API automation or inferred biological relationships. |
| Find a Grave / BillionGraves | Reviewed manual public record, user-saved material, or an explicitly implemented permitted official API if available to this use | Preserve memorial/image IDs and image attribution; listing, inscription and verified photograph have separate roles. |
| Cemetery registries | Review jurisdiction's official catalog/open-data API and license for the exact dataset | Preserve register/interment identifiers and coverage; no assumed photo or exact identity. |
| Tribute Archive / funeral homes | Inspect permitted public original or authorized saved record; evaluate any API entitlement before implementation | Identify funeral-home origin and syndicated dependencies. Respect retention/reproduction restrictions; factual receipts can exclude tribute walls and living relatives. |
| NARA / LOC / state or university archives | Use declared official archive routes in genealogy-public-api-pull after endpoint/terms review | Catalog/finding aid is a locator until the underlying age-bearing original is inspected. |

If a PDF is oversized or a fetch fails, use the authorized Chrome session to
inspect the original or an openly accessible archive/mirror. Record which copy
and pages were actually inspected. Do not claim an embedded video, unavailable
insert or linked PDF was read merely because its catalog loaded. Stop at an
access challenge and record the exact custodian/document request needed.
