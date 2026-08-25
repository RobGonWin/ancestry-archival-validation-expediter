# Ancestry Archival Validation Expediter (AAVE)

AAVE is a local-first Python toolkit for organizing genealogy records, archive
metadata, citations, evidence envelopes, and human-reviewed claim graphs. It
keeps observation, documentary record, recollection, inference, hypothesis,
contradiction, and review decisions distinct.

This public repository contains code, synthetic fixtures, and public-source
research notes only. It contains no raw DNA or genotype data, authenticated
account captures, family media, residence imagery, private trees, personal
recollections, or living-person records.

## Capabilities

- scan local archival material into stable metadata manifests;
- parse GEDCOM person and family links without inferring relationships;
- link sources conservatively and preserve ambiguous matches for review;
- generate public-redacted, controlled, and expert-review metadata packets;
- validate evidence envelopes and build typed support/contradiction graphs;
- validate closed-schema public projection receipts from separately reviewed
  private pipelines without reading private source artifacts;
- parse a user-owned AncestryDNA text export offline against an explicit local
  SNP whitelist, with genotype-bearing outputs kept outside Git;
- inspect saved archive and ZIP metadata without crawling or extraction; and
- run a path-based publication preflight before sharing.

## Quick start

Python 3.12 or newer is required.

```powershell
python -m pip install -e . pytest
pytest -q
python -m aave --help
python -m aave privacy-audit --repo . --out .\audit --strict
python -m aave bridge validate-receipt --input .\examples\private-pipeline-receipt.synthetic.json
```

All examples are synthetic. Put real material in an ignored local vault and
review every derivative before release.

## Private/public integration boundary

Public AAVE accepts only a small, pre-reviewed P0 receipt describing an
already public-safe projection. It never ingests private health timelines,
genotype bundles, source images, raw-source hashes, local paths, or record
values. See
[`docs/private-pipeline-integration.md`](docs/private-pipeline-integration.md)
for the closed receipt contract and its limitations.

## Ancestry compatibility

AAVE accepts standard GEDCOM exports and provides a local
`genome parse-ancestrydna` command for a user-owned AncestryDNA text export.
The parser performs no login, scraping, match lookup, medical interpretation,
or network request. It never commits or uploads the input. Generated hit files
remain controlled local artifacts and are blocked by the release boundary.

```powershell
python -m aave genome parse-ancestrydna `
  --input C:\path\outside\the\repo\ancestry-export.txt `
  --whitelist .\examples\genome-snp-list.example.json `
  --out C:\path\outside\the\repo\controlled-output
```

## Evidence rules

- A source that confirms an event does not prove a particular person attended.
- A geographic community or family-social cluster does not prove kinship.
- A marital or in-law relation is never converted into a biological edge.
- Population longevity findings are context, not family or genetic evidence.
- Contradictions and uncertain dates remain visible.

The public longevity registry in
[`docs/research/longevity-source-register.md`](docs/research/longevity-source-register.md)
includes historical age-validation work, international longevity studies,
geographic-cluster research, familial aggregation, immune and biomarker
studies, and genetics/SNP limitations. Robert D. Young's work and U.S.
population heterogeneity remain bounded parts of that broader register.

The public geospatial protocol in
[`docs/research/geospatial-context-register.md`](docs/research/geospatial-context-register.md)
supports attributed, present-day context without turning a map, street image,
or community lead into proof of residence, attendance, kinship, or a historical
condition.

## Repository workflow

`main` is the stable integration branch. Use short-lived `feat/`, `fix/`,
`docs/`, `research/`, `chore/`, or `release/` branches. A `research/` branch
may contain public citations and synthetic fixtures only.

Repository-local skills are available under `.agents/skills/`: `$graphify`,
`$context-loop`, `$research-source-audit`, `$public-release-audit`, and
`$github-cloud-loop`, plus AAVE-local `$contribute-to-aave` and
`$review-aave-contributions` workflows. The cloud Loop skill is mirrored under
`.github/skills/` for GitHub Copilot cloud. `.agents/skills/` is the canonical
cross-agent skill source; see
[`docs/AGENT_SKILLS_COMPATIBILITY.md`](docs/AGENT_SKILLS_COMPATIBILITY.md).
The pinned, read-only Loop MCP setup supports local Codex, Codex cloud, and a
GitHub Copilot custom agent; see
[`docs/LOOP_ENGINEERING_SETUP.md`](docs/LOOP_ENGINEERING_SETUP.md).
Automation is report-only by default; it never publishes, uploads evidence,
or opens upstream pull requests without a separate human decision. Offline
Ancestry export support does not grant any agent access to an Ancestry account.

## License and contributions

AAVE is licensed under the [MIT License](LICENSE). Contributors retain
copyright in their work and submit it under the same MIT terms; see
[CONTRIBUTING.md](CONTRIBUTING.md) for the rights, originality, testing, and
synthetic/public-only requirements.

The Slop track map is an informational compatibility assessment only. AAVE is
not submitted to, affiliated with, eligible for, or promised rewards by
Slop.cash or any named track, and no upstream contribution is planned or
authorized. See [`docs/SLOP_TRACK_MAPPING.md`](docs/SLOP_TRACK_MAPPING.md).
