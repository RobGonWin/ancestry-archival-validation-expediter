# Loop Engineering setup

This repository carries a conservative L1/report-only adaptation of Loop
Engineering. The reviewed upstream reference is pinned to commit
[`a6b41ab0351d67ffe3a77370a7f5807de7562ad6`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6).
The runtime references are pinned to `@cobusgreyling/loop@0.1.2` and
`@cobusgreyling/loop-mcp-server@1.2.0`.

No package was executed or installed while creating this configuration. An
MCP client launches the pinned package with `npx -y` only when the reviewed
repository configuration is trusted and the server is started. The MCP server
reads the public repository at `LOOP_PROJECT_ROOT=.`. No secret value is
configured here; operators must verify that the host does not expose ambient
secrets to the MCP process. Its eight enabled tools list patterns, skills and
state, read those resources, recommend a pattern, and estimate cost. No write
tool is enabled.

`gate.yaml` preserves the repository policy and adds the upstream
`loop-gate` keys. `maxFiles: 0` and `autoMergeAllowlist: []` force every
implementation or merge path to a human decision at L1.

## Local Codex

Open the repository as a trusted project and review `.codex/config.toml`
before enabling MCP. Invoke `$github-cloud-loop` for an L1 report. If Node,
`npx`, package download, or MCP startup is unavailable, stop and report that
the connector is unavailable; do not fall back to an unpinned package.

## Codex cloud

Keep `.codex/config.toml`, `AGENTS.md`, `LOOP.md`, `loop-constraints.md`,
`STATE.md`, and `gate.yaml` in the cloud checkout. Approve the project MCP
only in an environment permitted to fetch the pinned npm package. The task
remains read-only and must return its report in task output, not commit it.
Private AAVE material must not be copied into a cloud environment.

## GitHub Copilot cloud

`.github/agents/loop-readiness.agent.md` targets `github-copilot`, grants only
the built-in `read` and `search` tools, and allowlists the same eight MCP
tools. `.github/skills/github-cloud-loop/SKILL.md` is a byte-identical mirror
of the local `.agents/skills/` skill, and `.github/copilot-instructions.md`
supplies the durable privacy and human-gate rules. This is a repository
adaptation for GitHub Copilot; the Loop Engineering snapshot does not itself
provide this custom-agent frontmatter. The agent must not create or modify a
pull request during an L1 review.

If repository-level Copilot MCP settings are required instead of the custom
agent configuration, use this optional equivalent after human review:

```json
{
  "mcpServers": {
    "loop-engineering": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@cobusgreyling/loop-mcp-server@1.2.0"],
      "env": {"LOOP_PROJECT_ROOT": "."},
      "tools": [
        "loop_list_patterns",
        "loop_list_skills",
        "loop_list_state_files",
        "loop_get_pattern",
        "loop_get_skill",
        "loop_get_state",
        "loop_recommend_pattern",
        "loop_estimate_cost"
      ]
    }
  }
}
```

Do not add authentication values to committed configuration. If a host needs
credentials for an unrelated connector, configure them in the host's secret
store and keep that connector outside this report-only agent.

## Pinned Quick Links map

These links map the upstream Quick Links to this repository's pinned,
report-only posture. Commands are opt-in references and were not executed.

| Quick Link | Pinned mapping | L1 use |
| --- | --- | --- |
| `init` | [`loop init`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-init): `npx @cobusgreyling/loop@0.1.2 init . --pattern daily-triage --tool codex` | Not needed: this repository is already scaffolded. |
| `doctor` | [`loop doctor`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop): `npx @cobusgreyling/loop@0.1.2 doctor . --json` | Report health only. |
| `audit` | [`loop audit`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-audit): `npx @cobusgreyling/loop@0.1.2 audit . --suggest` | Suggestions only. |
| `sync` | [`loop sync`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-sync): `npx @cobusgreyling/loop@0.1.2 sync .` | Detect drift; do not rewrite state automatically. |
| `context` | [`loop context`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-context): `npx @cobusgreyling/loop@0.1.2 context --check --ledger <sanitized-ledger>` | Sanitized metadata only; never private evidence. |
| `cost` | [`loop cost`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-cost): `npx @cobusgreyling/loop@0.1.2 cost -p daily-triage -l L1 -c 1d` | Estimate before scheduling. |
| `gate` | [`loop gate`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-gate): `npx @cobusgreyling/loop@0.1.2 gate check --action commit --paths <reviewed-paths>` | Evaluates commit policy only; it neither authorizes nor performs a commit. |
| `worktree` | [`loop worktree`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-worktree): `npx @cobusgreyling/loop@0.1.2 worktree ...` | Disabled at L1 because no implementation is authorized. |
| `MCP` | [`loop-mcp-server`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/mcp-server): `npx -y @cobusgreyling/loop-mcp-server@1.2.0` | Eight read-only tools only. |
| `action` | [`loop-action`](https://github.com/cobusgreyling/loop-engineering/tree/a6b41ab0351d67ffe3a77370a7f5807de7562ad6/tools/loop-action): `uses: cobusgreyling/loop-engineering/tools/loop-action@a6b41ab0351d67ffe3a77370a7f5807de7562ad6` | Not enabled; existing pinned read-only CI remains authoritative. |

Harness Foundry, Outerloop, Goal Engineering, Memory Engineering, Fleet
Engineering, write-capable connectors, schedules, and upstream action
templates are outside this reviewed setup and remain disabled.

## AAVE privacy boundary

The connector may inspect only this public, synthetic repository. It may not
inspect a real AncestryDNA export, GEDCOM, DNA-match information, authenticated
browser state, family archive, or controlled output. AAVE still supports
user-owned Ancestry and GEDCOM exports offline; those files remain outside Git
and outside local or cloud MCP context.
