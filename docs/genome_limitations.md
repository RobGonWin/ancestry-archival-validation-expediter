# Genome Limitations

AAVE genome support is a local archival cross-reference workflow. It is not a
medical, diagnostic, health, or longevity prediction system.

## Scope

The parser supports AncestryDNA-style tabular raw files with these columns:

```text
rsid chromosome position allele1 allele2
```

Only rsIDs listed in a local curated whitelist are written to `snp_hits.json`.
The full raw file is not copied to the output directory.

## SNPedia-Style References

Curated whitelist entries may include SNPedia or literature URLs as educational
references. AAVE does not scrape SNPedia, does not call external APIs, and does
not treat URLs as medical authority.

The YAML form is supported through `examples/snpedia_keys.example.yaml`.
These are local curated keys, not API credentials.

Use careful language:

- associated with
- reported in
- educational note
- hypothesis-generating only

Avoid deterministic language:

- causes
- proves
- diagnoses
- guarantees
- rules out

## Consumer Array Caveats

Consumer genotyping files are limited by:

- array coverage
- no-calls
- possible strand orientation issues
- reference-build differences
- chip version differences
- lack of clinical validation

Whole-genome sequencing may be more comprehensive, but it still requires expert
interpretation and careful privacy handling.
