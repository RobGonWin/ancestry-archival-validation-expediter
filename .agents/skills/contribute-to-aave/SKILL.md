---
name: contribute-to-aave
description: Prepare a scoped contribution to this AAVE public archival-evidence repository using synthetic examples, explicit provenance, and local verification.
---

# Contribute to AAVE

Read `AGENTS.md`, `CONTRIBUTING.md`, and `loop-constraints.md`. This skill is
only for contributions to this AAVE repository; it does not authorize an
upstream submission or any external write.

1. Define one archival, parser, documentation, or validation objective.
2. Work on a scoped `feat/`, `fix/`, `docs/`, `research/`, or `chore/` branch.
3. Use original code, public citations, and synthetic fixtures only. Never add
   real exports, account-derived records, family evidence, or recollections.
4. Preserve offline Ancestry-format compatibility by testing format behavior,
   not by bundling or reading a real export.
5. Document provenance, ambiguity, limitations, and claims the source cannot
   support.
6. Add tests for success, malformed input, and privacy-preserving failure
   behavior where applicable.
7. Run `pytest -q` and the strict AAVE privacy audit before requesting local
   review.

Do not treat a tool result as proof of identity, relationship, medical status,
or causation. Stop before publication, push, issue creation, or pull-request
creation unless a human separately authorizes that exact external action.
