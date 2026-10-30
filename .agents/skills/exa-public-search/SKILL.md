---
name: exa-public-search
description: Search public sources with the Exa API using bounded, resumable batches and source provenance for research tasks.
---

# Exa public search

Use the repository's `nea_archiver.nea_exa.exa_search_adapter` with
`nea_archiver.nea_discovery.execute_batch`. Despite their historical module names,
these interfaces accept general public queries and do not require NEA records.
Reuse this runner rather than creating another retry or checkpoint loop.

Before enabling requests, establish the research question, public query scope,
query/result budget and stopping condition. Existing user authorization carries
forward. Read the current [terms](https://exa.ai/terms-of-service),
[search API](https://exa.ai/docs/reference/search) and
[rate limits](https://exa.ai/docs/admin/billing). The adapter is disabled by
default; enable it explicitly with an authorized `EXA_API_KEY` environment
variable. Never print the key or put it in a plan, query, checkpoint or commit.
A repository secret alone does not populate the local environment.

Alternatively, pass `api_key=authorized_key` when explicitly enabling the
adapter. This takes precedence over `EXA_API_KEY`; an explicit blank value
fails instead of silently using a different credential. The disabled adapter
ignores both sources. For a user-authorized local `.env`, read only that exact
file, select one `EXA_API_KEY` assignment case-insensitively (including
`exa_api_key`), and pass its value in memory. Reject missing or duplicate
assignments; never execute/source the file, search sibling folders for keys,
log the value, or copy the file into the repository. No automatic `.env`
discovery is performed by the adapter.

Each query row needs `query_id`, `provider="exa"`, `query` and `priority`;
set `query_is_external_emission=True`. Derive stable query IDs from provider,
query and research scope/revision. Record why a changed source or question
justifies a new revision; do not reset an exhausted batch to repeat unchanged
work. Check queries for private material before execution. Keep all response
caches and checkpoint files under ignored `local-vault/` paths.

From this repository with `PYTHONPATH=src`, execute reviewed query rows through:

```python
from pathlib import Path
from nea_archiver.nea_discovery import execute_batch
from nea_archiver.nea_exa import exa_search_adapter

# reviewed_queries and batch_limit come from the bounded public research plan.
adapter = exa_search_adapter(enabled=True, num_results=5)
results = execute_batch(
    reviewed_queries, {"exa": adapter},
    Path("local-vault/public-research/checkpoint.json"), limit=batch_limit,
)
```

For an offline plan, use `execute_batch` with `dry_run=True` and no enabled
adapter; no key is needed. Live calls are serial, at least one second apart,
with one attempt and at most ten results per query. An authorized host may
inject `transport=` to use its certificate store; preserve TLS verification
and sanitized errors. Retain provider/endpoint, timestamp, query, source URLs
and response hashes. Resume the same checkpoint; preserve empty and failed
results. Stop at the budget or an access/billing block.

Read the original sources before accepting claims. Search extracts are leads,
and multiple copies of one original are one evidence source. Report accepted
findings, contradictions, unresolved leads and batch yield. Apply the task's
own evidence rules: for NEA work, follow `nea-person-closure` and its 40-query
cap; other research is governed by its explicitly chosen budget. This skill
does not adjudicate ages, enable scheduled jobs or authorize publication.

For U.S. census discovery, pair with
[us-census-finder](../us-census-finder/SKILL.md): generate the finder plans,
search broadly using reviewed public identity context, and return candidate
URLs to the census workflow for original-image and identity review. Exa is
the discovery provider; it does not turn an extract into a census age or
enable automated genealogy-platform access.

For memorial, obituary, cemetery, archive and public birth-record discovery,
read [person-records](references/person-records.md). It pairs those source
layers with census discovery, distinguishes indexes from originals and
defines yield metrics without treating search coverage as person closure.
