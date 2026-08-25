# Agent Skills compatibility

`.agents/skills/` is AAVE's canonical skill directory for compatible
ChatGPT/Codex and GitHub agent workflows. Each skill is a self-contained
`<skill-name>/SKILL.md` package. Product surfaces still decide whether and when
they discover or invoke a skill; the directory layout does not grant an agent
new permissions.

| Host | Repository use | Boundary |
| --- | --- | --- |
| ChatGPT/Codex | Discover the Agent Skills packages under `.agents/skills/` on compatible surfaces. | Follow `AGENTS.md`; a skill never authorizes external writes or private evidence access. |
| GitHub agents | Discover `.agents/skills/` as the shared repository skill source. The intentionally mirrored `.github/skills/github-cloud-loop/` package supports that cloud-specific Loop review. | AAVE-local contribution skills apply only to this repository and are not upstream contribution instructions. |
| elizaOS | Format-compatible with the prerelease `@elizaos/plugin-agent-skills@2.0.3-beta.7` loader when a compatible 2.x host is separately configured. | Documentation only; no Eliza runtime, dependency, plugin install, or remote catalog is included here. |

## Optional elizaOS host configuration

A future, compatible elizaOS 2.x host may point its local loader at this
repository with:

```text
SKILLS_DIR=.agents/skills
automatic local skill loading: true
remote catalog synchronization: false
```

Only `SKILLS_DIR` above is an environment variable specified by this
repository. The other two lines describe required host policy; a particular
host wrapper may use different configuration keys. Keep remote discovery,
installation, and catalog synchronization disabled.

The named plugin version is a prerelease compatibility target, not a runtime
certification. Before any runtime use, pin the exact dependency in an isolated
host outside this repository and run a synthetic-only smoke test. Do not load
private AAVE material, install a remote skill catalog, or sync skills from a
network source. This repository intentionally contains no runnable Eliza app.

## Skill inventory

- `context-loop`: bounded evidence research with sanitized state;
- `contribute-to-aave`: prepare a local AAVE-only contribution;
- `github-cloud-loop`: report-only Loop readiness;
- `graphify`: public/synthetic claim and provenance graphs;
- `public-release-audit`: privacy and release preflight;
- `research-source-audit`: public-source authority and claim limits; and
- `review-aave-contributions`: independent AAVE-only contribution review.

Review `SKILL.md` before use. No skill permits account login, Ancestry scraping,
private-vault reads, publication, rewards activity, or contributions to an
external project without a separate, explicit human authorization.
