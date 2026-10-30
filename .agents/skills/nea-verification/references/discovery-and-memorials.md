# Discovery and memorial slices

Prioritize unresolved plausible competitors and known centenarians before broad memorial searches. Reuse reviewed cached pages and blocked access receipts. Read `nea_discovery.DEFAULT_PROVIDERS` and supply configuration for additional public archives, historical societies, newspapers or gerontology references rather than changing recipient-specific code.

Batch across recipients: select a bounded cohort sharing a blocker or source layer, submit multiple independent queries in each tool's supported batch, then adjudicate the returned documents in one review table. Read each cached document once and attach all relevant person/claim links. Skip the ordinary NEA biography query when its retrieval receipt already exists; keep separate death-statement searches available. Do not require a headstone or funeral notice for people already excluded by sound birth bounds. Keep network concurrency within provider limits even when adjudication is batched. Advance to deeper layers only for claims the earlier layer cannot resolve.

Keep query IDs and verification fingerprints stable across unchanged inputs. The query identity includes cutoff and an explicit `search_revision`; change that revision for a justified refresh or corrected alias. Preserve a prior failed/empty receipt instead of silently rerunning it every turn. Show batch yield (new exclusions, conflicts and unresolved leads) so subsequent work targets the remaining blockers.

Search by public recipient name with award year, art form, geography and aliases. Broaden only when the targeted query fails: obituary, official death statement, institutional memorial, cemetery interment, memorial directory, then archive catalogs. Use a small adversarial search for higher ages and ties before claiming closure. Store null results as search receipts, never exclusions.

An adapter requires an actual permitted search/API callback, terms URL, explicit enablement, rate limit, bounded retries and checkpoints. There is no assumed API for any memorial or genealogy provider. Authentication, CAPTCHA, paywall or robots restrictions produce manual leads. Do not automate genealogy-platform accounts; use supplied local snapshots.

Capture memorial ID, URL, reported dates, cemetery/location, interment event, inscriptions, relationship links and image attribution when available. Distinguish funeral-home cemetery statements, interment registers, directory entries and photographed headstones. Same-name matches need corroboration. An inaccessible photograph remains an unverified lead. Do not infer no grave from no directory result.

Identify dependency groups: copies, syndicated notices, vendor indexes and saved versions of one original do not become independent sources because they have different URLs. Link each accepted claim to what the source can and cannot support.
