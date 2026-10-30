# Reproducing the public checkpoint

`python public_offline.py` replays competition-rank envelopes, exact-date arithmetic, population and award closure counts, all CSV cells, both full workbook population tables, and the six publication checksums. `pytest -q` exercises synthetic archival methods and rejects malformed sources and changed cells. No network or secret is used by these commands.

The workbook can be edited in Excel or the linked Google Sheet. Editing a date does not automatically regenerate source-bound rank envelopes. Review the claim, regenerate in the private research engine, export a new allowlisted projection, then rerun these checks and independent review before updating the public snapshot.

Workbook authoring: `node build_workbook.mjs data/public <preview-directory>` requires the Codex bundled `@oai/artifact-tool`. Authoring is separate from the dependency-free public verifier. Date cells are numeric Excel serials with a date format for Google Sheets compatibility.

Known gaps remain visible: missing source publication dates have not been inferred from URL paths. The link audit checks liveness only and records unavailable, restricted and unchecked URLs. The Ella Jenkins NEA statement returned410 at independent review; Smithsonian's memorial supports the accepted dates. Unknown image redistribution rights mean source links only. No original or screenshot image bytes are part of this public build.

The NEA files were extracted individually into this existing AAVE repository; no private research history was merged. The separate national-heritage-fellow-longevity-archiver-private installation supports full local images/PDFs, searchable indexed evidence, hash verification and an authenticated localhost viewer. It is not required to reproduce this public comparison.
