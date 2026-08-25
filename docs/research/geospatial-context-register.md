# Public geospatial context protocol

Geospatial material is a context source, not a shortcut to proving a person,
relationship, event, residence, or memory. Public examples in this repository
must be synthetic or coarse enough to avoid exposing a living person's home or
private research target.

## Source boundaries

| Source | Permitted public workflow | Prohibited or private workflow | Evidence limit |
| --- | --- | --- | --- |
| OpenStreetMap | Manually cite a public feature or use a properly attributed map image when its data and tile licenses permit. Include `© OpenStreetMap contributors` and the ODbL link. | Do not copy another copyrighted map into OSM, expose confidential search terms, or omit attribution. | Present-day mapped features do not prove historic condition, occupancy, ownership, attendance, or kinship. |
| OSM Nominatim public service | No implemented connector. Any future use must identify the application, cache results, stay at or below one request per second, provide attribution, and avoid systematic queries. | No autocomplete, bulk geocoding, scraping, or personal/confidential query data. | A geocoder result is a location candidate, not a historical or identity finding. |
| Google Maps / Street View | Retain a dated link or use a permitted embed with required attribution. | No Street View screenshots, downloads, stitching, tracing/digitizing, offline copies, or automated image analysis/extraction. | Capture date and present appearance do not establish past conditions or who was present. |
| Nextdoor | Treat a manually viewed post as a restricted lead. Record only a private source pointer and independently verify any public claim. | No scraping, account automation, copying member posts, publishing member identities/addresses, or public screenshots without every required permission and obfuscation. | A neighborhood statement is not an authoritative record or consent to publication. |

Authoritative operating references:

- [OpenStreetMap Foundation attribution guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
- [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)
- [Google Geo Guidelines](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)
- [Nextdoor brand and screenshot guidelines](https://about.nextdoor.com/nextdoor-brand-use-guidelines/)

## Evidence envelope fields

A private geospatial source envelope should record:

- provider and stable link;
- observation date and, when supplied by the provider, imagery date;
- public/restricted classification and license/attribution requirement;
- geographic precision (`region`, `locality`, `street`, or `exact`);
- narrow claim supported and explicit `cannot_support` statements;
- whether a human independently reviewed the source;
- release decision separate from collection.

Exact coordinates, residence imagery, authenticated-community content, and
queries that reveal a private research subject remain restricted. A public
derivative should normally use a region or locality and link to the public
source rather than reproduce imagery.

## Claim-separation rule

Keep these nodes distinct:

```text
current public map feature
    -> may contextualize a locality
    -/> does not prove a historical address or building condition

dated street-level link
    -> may document visible conditions on that imagery date
    -/> does not prove occupancy, attendance, ownership, or kinship

private community lead
    -> may suggest a public-record search
    -/> does not become a public fact without independent corroboration
```

No agent may publish, upload, or submit geospatial material merely because it
was accessible in a signed-in browser session.
