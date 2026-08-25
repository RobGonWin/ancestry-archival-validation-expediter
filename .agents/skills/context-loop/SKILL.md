---
name: context-loop
description: Run a bounded AAVE research loop with public-source classification, a skeptic pass, deterministic validation, sanitized state, and explicit stop conditions.
---

# Run an AAVE context loop

Read `LOOP.md`, `loop-constraints.md`, `loop-budget.md`, and `STATE.md`.

1. State one question, allowed paths, evidence lanes, deliverable, checks, and stop conditions.
2. Build a minimal context manifest from citations, hashes, opaque IDs, and reviewed summaries.
3. Classify each item as observation, public record, recollection, inference,
   hypothesis, contradiction, or review decision.
4. Execute one bounded search or transformation and record null results.
5. Run a skeptic pass for source dependence, circularity, chronology, alternate relationships, and privacy risk.
6. Validate schemas, claim edges, tests, and publication boundaries.
7. Checkpoint only sanitized state.
8. Stop before external sharing, a privacy downgrade, or an unsupported inference.

Stop after three failed attempts or three occurrences of the same error.
