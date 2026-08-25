# Optional Integrations

AAVE integrations are disabled by default. The current implementation writes
dry-run payload files only. It does not call ArchiveBox, Zotero, Perma.cc, or
GitHub Pages.

## Commands

```bash
aave integrations archivebox --out ./out/integrations
aave integrations zotero --manifest ./out/archive_manifest.json --out ./out/integrations
aave integrations perma --out ./out/integrations
aave integrations static-site --export-manifest ./out/public_export/export_manifest.json --out ./out/static_public
```

Each command writes JSON describing what would be prepared later. No network
request is made.

## Environment Variables

If a future connector is enabled, tokens must come from environment variables:

- `AAVE_ARCHIVEBOX_TOKEN`
- `AAVE_ZOTERO_API_KEY`
- `AAVE_ZOTERO_LIBRARY_ID`
- `AAVE_PERMA_API_KEY`

Do not store real tokens in config files, examples, tests, docs, or Git.

## Connector Status

| Connector | Current behavior |
| --- | --- |
| ArchiveBox | Writes `archivebox_dry_run.json`; no CLI or REST call. |
| Zotero | Writes `zotero_dry_run.json`; no API call. |
| Perma.cc | Writes `perma_dry_run.json`; no API call. |
| Static site | Writes public-safe metadata preview from an existing redacted export manifest. |
| OpenStreetMap | Documentation-only, manual public-context workflow; no connector or automated query. |
| Google Street View | Link or permitted embed only; no screenshot, download, stitching, tracing, or extraction. |
| Nextdoor | Private manual lead source only; no scraping, account automation, or member-content republication. |

## Safety Rules

- No connector is enabled by default.
- No connector may bypass login, CAPTCHA, paywall, DRM, or access controls.
- No connector may scrape private websites.
- No map or street-level source may be used to infer attendance, occupancy,
  ownership, kinship, or a past building condition.
- Any future Nominatim integration must follow the public service's rate,
  identification, attribution, caching, and no-confidential-data rules.
- No connector may upload raw DNA, genotypes, private notes, or living-person data.
- Static public output may use only `public_ok` and `public_summary_only` metadata rows.
- Dry-run must remain available for any future external connector.
