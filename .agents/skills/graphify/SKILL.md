---
name: graphify
description: Build or review privacy-preserving AAVE claim and provenance graphs from public or synthetic evidence envelopes while preserving uncertainty and evidence roles.
---

# Graphify AAVE evidence

Read `loop-constraints.md` and require an explicit path allowlist. Never scan a
local evidence vault or the repository root by default.

1. Accept only reviewed public sources, synthetic fixtures, or opaque sanitized projections.
2. Keep typed nodes for source, evidence, claim, person-or-pseudonym,
   observation, recollection, inference, hypothesis, contradiction, and review.
3. Use explicit edges: `supports`, `contradicts`, `contextualizes`,
   `derived_from`, and `related_by_reviewed_record`.
4. Never convert marital, in-law, geographic, community, or population context
   into biological kinship or causation.
5. Preserve source role, confidence, privacy label, limitations, and human-review state.
6. Generate native claim graphs only from reviewed envelopes:

   ```powershell
   python -m aave claims build --evidence-dir <reviewed> --claims <claims.json> --out <ignored-output>
   ```

7. Validate stable sorting, dangling references, hashes, counts, and redaction.
8. Report contradictions and missing evidence; never auto-promote a claim to proved.
