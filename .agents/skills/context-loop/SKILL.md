---
name: context-loop
description: Run a bounded, privacy-preserving AAVE research loop with an explicit context manifest, evidence-role classification, skeptic pass, validation, checkpoint, and stop conditions. Use for ancestry, archive, longevity-cluster, memorabilia, or DNA-context investigations.
---

# Run an AAVE context loop

Read `LOOP.md`, `loop-constraints.md`, `loop-budget.md`, `STATE.md`, and
`docs/CONTEXT_LOOP_PROTOCOL.md` before acting.

For one research question at a time:

1. Declare the question, allowed evidence lanes, privacy ceiling, tools,
   deliverable, validation commands, and stop conditions.
2. Build a minimal context manifest. Prefer hashes, opaque IDs, citations, and
   reviewed summaries over raw files. Never load the full DNA export merely
   because it is available.
3. Classify each input as observation, public record, family-held artifact,
   recollection, inference, hypothesis, contradiction, or review decision.
4. Execute one bounded transformation or search. Record null results and
   failed searches instead of silently widening scope.
5. Run a skeptic pass for alternative relationships, source dependence,
   circular genealogy, contamination, living-person risk, and chronology.
6. Validate schemas, hashes, claim edges, branch policy, tests, and the
   publication boundary.
7. Checkpoint inputs, outputs, decisions, unresolved questions, and a trusted
   head/hash where available.
8. Stop before external sharing, a privacy downgrade, an unsupported
   biological or longevity inference, or a materially different question.

Stop on the third failed attempt, the third occurrence of the same error, or
any run that cannot demonstrate verifiable progress.

An anecdote remains a recollection even when a public source corroborates part
of its scene. Corroboration and identification are separate graph edges.
