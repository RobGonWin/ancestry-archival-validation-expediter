---
name: nea-cohort-review
description: Prepare and review public NEA recipient cohorts with source-bound decisions, batched retrieval and optional Codex, Cursor, Claude or Grok Bot handoffs.
---

# NEA cohort review

Use this for many recipients sharing an evidence blocker. Read the canonical [verification workflow](../nea-verification/SKILL.md) and only the relevant slice reference.

The broader AAVE `agent-context prepare` command is not included here. Prepare a manually reviewed public-only cohort packet in ignored `local-vault/context`; do not invoke an unavailable CLI. Default cohorts contain 50 unresolved public identities; each researcher owns a disjoint subset. Keep collective membership blockers separate. The packet uses a field allowlist, not automatic text redaction: inspect it before external invocation.

Read [agent handoffs](references/agent-handoffs.md) for provider commands and Grok Bot limits.

For each cohort:
1. Reuse matching fingerprints, prior page captures, blocked access receipts and already resolved decisions.
2. Apply birth/cutoff bounds first. Group remaining people by blocker and source layer. Batch independent queries within the actual tool limit; the recipient count is distinct from the query budget.
3. Review hits in one table: person ID, identity evidence, source URL/role, date precision, dependency group, decision, blocker and next action. Nulls and rejected identities are outcomes, never exclusions.
4. Send only unresolved factual questions to the date/identity checker and independent skeptic. They review the same immutable context hash and source records; preserve dissent.
5. Accept source-bound decisions in the canonical ledger only after validation. Agent output never imports itself. Invalidate affected slices when evidence or cutoff changes.

Host tool calls, accounts and cloud Bots remain subject to project access boundaries. A skill is not permission to publish, message a Bot or upload private records.
