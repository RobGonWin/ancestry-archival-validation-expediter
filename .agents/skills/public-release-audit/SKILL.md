---
name: public-release-audit
description: Check an AAVE release candidate for tests, source-only history, prohibited evidence paths, private-repository residue, licenses, skill validity, and sanitized public content before any publication decision.
---

# Audit a public release

Operate read-only until a human approves publication.

1. Confirm the candidate was materialized without `.git` from an explicit allowlist.
2. Run `pytest -q` and `python -m aave privacy-audit --repo . --out .audit --strict`.
3. Inspect tracked paths and text for local paths, secrets, raw evidence, account captures, personal narratives, and non-public branch or remote names.
4. Validate every `SKILL.md` and check that workflow actions use full reviewed SHAs.
5. Confirm exactly one fresh root commit, only `main`, no LFS objects, no inherited unreachable objects, and no source-private remote.
6. Verify source citations, third-party licenses, and the repository's own license state.
7. Report blockers; do not weaken a gate or publish automatically.
