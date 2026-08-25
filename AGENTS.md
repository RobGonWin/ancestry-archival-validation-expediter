# Repository instructions

This is a public, synthetic-only genealogy and evidence-provenance toolkit.

## Non-negotiable boundaries

- Never add raw DNA, genotypes, private trees, authenticated screenshots,
  family media, residence details, credentials, health data, or real
  living-person records.
- Never paste personal recollections into issues, tests, fixtures, logs, or
  graph labels.
- Do not infer biological kinship, inherited longevity, cognition, diagnosis,
  or causation from geographic, social, marital, or population context.
- Preserve source conflicts and uncertainty; do not optimize them away.
- Do not automate publication, uploads, payments, wallets, issue creation, or
  upstream pull requests.
- Ancestry-compatible parsers may be developed with synthetic fixtures only;
  never use a real account export in tests, examples, logs, or commits.

## Working method

1. Read `LOOP.md`, `loop-constraints.md`, `STATE.md`, and the invoked skill.
2. Declare one bounded objective and an explicit path allowlist.
3. Use public sources or synthetic fixtures only.
4. Add the narrow claim a source supports and a `cannot_support` field.
5. Run `pytest -q` and `python -m aave privacy-audit --repo . --out .audit --strict`.
6. Use an independent checker for material source, privacy, or schema changes.
7. Keep committed state sanitized and stop before any external write.

`main` is stable. Work on `feat/`, `fix/`, `docs/`, `research/`, `chore/`, or
`release/` branches and target `main` with a reviewed pull request.
