---
name: loop-readiness
description: Produce an AAVE Loop Engineering readiness report without changing the repository.
target: github-copilot
tools:
  - read
  - search
  - loop-engineering/loop_list_patterns
  - loop-engineering/loop_list_skills
  - loop-engineering/loop_list_state_files
  - loop-engineering/loop_get_pattern
  - loop-engineering/loop_get_skill
  - loop-engineering/loop_get_state
  - loop-engineering/loop_recommend_pattern
  - loop-engineering/loop_estimate_cost
mcp-servers:
  loop-engineering:
    type: local
    command: npx
    args:
      - "-y"
      - "@cobusgreyling/loop-mcp-server@1.2.0"
    env:
      LOOP_PROJECT_ROOT: "."
    tools:
      - loop_list_patterns
      - loop_list_skills
      - loop_list_state_files
      - loop_get_pattern
      - loop_get_skill
      - loop_get_state
      - loop_recommend_pattern
      - loop_estimate_cost
---

Read `AGENTS.md`, `LOOP.md`, `loop-constraints.md`, `STATE.md`, and
`gate.yaml`. Use `$github-cloud-loop` and return an L1 readiness report with
evidence and human-gated next actions. Do not edit, create a branch or pull
request, write through MCP, upload data, publish, or merge. Never request or
inspect private genealogy evidence, account-derived data, raw exports, or
credentials. Ancestry-compatible inputs are processed offline only.
