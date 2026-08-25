# Bounded-loop entry point

Default autonomy is **L1 / report-only**. A run may inspect allowlisted public
source or synthetic files, propose a patch, and execute deterministic local
checks. It may not publish, upload, change a privacy label, or write to an
external system.

1. Read `loop-constraints.md`, `loop-budget.md`, `STATE.md`, and the invoked skill.
2. Declare one objective, allowed paths, evidence roles, checks, and stop conditions.
3. Recheck source authority, license, date, and claim limits.
4. Execute one bounded local action.
5. Run tests and the public-release preflight.
6. Use maker/checker separation for material changes.
7. Record only sanitized status and stop.

Stop immediately on a privacy finding, provenance or licensing gap,
unreviewed external write, repeated failure, or lack of verifiable progress.
