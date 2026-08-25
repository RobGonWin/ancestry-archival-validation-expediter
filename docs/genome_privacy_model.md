# Genome Privacy Model

AAVE genome utilities are private, local-only helpers for user-owned raw DNA files.
They are not part of public archival exports by default.

## Allowed Local Inputs

- User-owned AncestryDNA raw-data text files.
- Local curated SNP whitelist JSON files.
- Local private output folders under a person-specific research directory.

## Public Boundaries

Public outputs must never include:

- Raw DNA files.
- Genotypes.
- Per-SNP allele calls.
- Medical, diagnostic, health, fitness, or longevity-deterministic claims.
- Third-party upload instructions or API calls.

The only public-safe genome output in this branch is a redacted summary such as:

- `genome_whitelist_checked: true`
- whitelist hit count
- missing/not-tested count
- a note that no genotype calls are included

## Private Outputs

`aave genome parse-ancestrydna` writes private outputs:

- `manifest.json`
- `snp_hits.json`
- `snp_missing.json`
- `genome_public_summary.json`
- `genome_audit.md`

`snp_hits.json` contains genotype calls and must remain private.

## Interpretation Rules

- Whitelist matches are educational references only.
- Missing rsIDs are `missing_or_not_tested`, not negative results.
- Consumer genotyping arrays are incomplete.
- Strand and reference-build caveats must be preserved.
- Expert review is required before any external use.
