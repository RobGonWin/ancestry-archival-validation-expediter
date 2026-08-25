# GitHub Publication Preflight

This repository may contain private family-history and DNA-adjacent working
files. Run a local privacy preflight before pushing, opening a pull request, or
preparing any public repository.

## Command

```bash
aave privacy-audit --repo . --out ./out/privacy_audit --strict
```

The command checks tracked Git path names only. It does not read sensitive file
contents. Strict mode exits with status `1` when any blocker or review item is
present.

Outputs:

- `privacy_audit.json`
- `privacy_audit_report.md`

## Publication Blockers

Do not publish or push public-facing branches when tracked paths include:

- raw DNA files
- genotype files
- secret or environment files
- private archive bundles
- generated local output folders

## Current Safe Framing

Use this repository framing:

```text
AAVE is a local-first archival validation toolkit for family-history and
longevity documentation, designed to preserve provenance, protect sensitive
data, and generate public/private research packets from user-owned genealogy
records, saved sources, and family-held artifacts.
```

Avoid:

- medical, diagnostic, health, or longevity-deterministic claims
- institutional endorsement claims
- raw DNA or genotype publication
- private family facts in public examples
- Ancestry, ArchiveBox, Zotero, Perma.cc, or browser automation claims beyond
  implemented dry-run behavior

## Suggested PR Checklist

- `python -m pytest -q`
- `python -m ruff check .`
- `aave privacy-audit --repo . --out ./out/privacy_audit --strict`
- Confirm public exports exclude living/potentially living people.
- Confirm public exports exclude raw DNA and genotypes.
- Confirm optional integrations remain dry-run unless explicitly enabled.
- Confirm README commands match implemented CLI behavior.
