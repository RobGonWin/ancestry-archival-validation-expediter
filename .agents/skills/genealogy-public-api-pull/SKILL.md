---
name: genealogy-public-api-pull
description: Corroborate genealogical and record-quality claims against free, programmatically accessible public archives using a pull-only discipline that never transmits private material or reveals a working research target.
---

# Genealogy public API pull

Corroboration runs against open archives with documented programmatic access. The subscription index is not one of them and is not used here.

## Pull, never push

- Retrieve reference and record data **inward**. Nothing about the private case goes outward.
- Never transmit a name, date, place, genotype, identifier, or vendor record pointer that originates in the private lane.
- A query leaks even when it carries no private field. A sequence of targeted lookups discloses the working research target. Prefer bulk or collection-level retrieval and filter locally; when a targeted lookup is unavoidable, record that the query itself was an emission.
- For routes permitting retention, cache responses locally with provider, endpoint, query, access timestamp, and content hash. Check provider restrictions first. If retention conflicts with the provider's terms, leave the route disabled and record the access limitation rather than silently discarding provenance or violating the terms.

## Declared routes

| Route | Access | Use |
| --- | --- | --- |
| National Archives Catalog API v2 | Assigned key required; `https://catalog.archives.gov/api/v2/records/search`, documented at `https://www.archives.gov/research/catalog/help/api` | Federal record metadata, census descriptions and district context; not a named-person census API |
| 1950 Census | `https://1950census.archives.gov/` | Free access to the most recent released enumeration |
| loc.gov API | `https://www.loc.gov/apis/` | Chronicling America moved here in 2025; newspaper corroboration of dates, residence, and events |
| IPUMS | `https://usa.ipums.org/usa/` and its developer API | Full-count microdata and linked-census crosswalks for aggregate work |
| FamilySearch developer API | `https://www.familysearch.org/developers/` | Record search under its own registered-application terms |
| WikiTree API | `https://github.com/wikitree/wikitree-api` | Open collaborative tree data, treated as an assertion source, not an authority |

Before using any route, record its terms, rate limit, attribution requirement, and whether registration is needed. Honour published rate limits; identify the application where the provider asks for it.

The NARA Catalog terms reviewed October 24, 2026 require `x-api-key` and state
that API content should not be cached, while the linked getting-started guide
shows saving responses. Resolve this conflict before enabling a cached Catalog
adapter. No Catalog request is authorized merely by generating a finder plan.
The public 1950 census website is a separate route and remains available for
manual name-index and original-schedule review without a Catalog key.

## Not declared, and why

- Subscription genealogy sites. Their terms do not permit programmatic extraction, and their supported export path is the GEDCOM the maintainer already holds. Use the broader AAVE project for supported local genealogy exports; tree ingestion is outside this focused project.
- Any authenticated session, of any provider, driven by automation.
- Any site whose terms are unread. An unread term is a blocked route.

## Corroboration discipline

1. State the claim to be corroborated and its current `verification_status`.
2. Search the public route on the claim's own terms, not on the vendor pointer.
3. Record the result as `corroborated`, `contradicted`, or `not_found`.
4. `not_found` is a result and is retained. Absence of documentation is not documentation of absence, and a negative search that is discarded silently inflates the apparent strength of everything that remains.
5. An index entry corroborates an index. Only the underlying image or an independent record corroborates the fact.

## Cannot support

- A public archive hit confirms that a record exists, not that its content is accurate.
- Two derivative indexes of one original are one source, not two.
- No route here establishes kinship, genetic relationship, ancestry origin, or presence at an event.
- Rate-limit compliance is not permission; permission comes from the provider's terms.
- Nothing here authorises transmitting private-lane material to any external service.
