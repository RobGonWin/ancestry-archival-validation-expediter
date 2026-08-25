from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_PACKAGE = "@cobusgreyling/loop-mcp-server@1.2.0"
CLI_PACKAGE = "@cobusgreyling/loop@0.1.2"
UPSTREAM_REVISION = "a6b41ab0351d67ffe3a77370a7f5807de7562ad6"
MCP_TOOLS = (
    "loop_list_patterns",
    "loop_list_skills",
    "loop_list_state_files",
    "loop_get_pattern",
    "loop_get_skill",
    "loop_get_state",
    "loop_recommend_pattern",
    "loop_estimate_cost",
)
CLOUD_AGENT_TOOLS = ("read", "search") + tuple(
    f"loop-engineering/{tool}" for tool in MCP_TOOLS
)
INTEGRATION_FILES = (
    ".codex/config.toml",
    ".agents/skills/github-cloud-loop/SKILL.md",
    ".github/skills/github-cloud-loop/SKILL.md",
    ".github/agents/loop-readiness.agent.md",
    ".github/copilot-instructions.md",
    "docs/LOOP_ENGINEERING_SETUP.md",
)
ASSIGNED_CREDENTIAL = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
    r"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
)


def _yaml_list(text: str, key: str) -> tuple[str, ...]:
    section = text.split(f"{key}:\n", 1)[1]
    values: list[str] = []
    for line in section.splitlines():
        if not line.startswith("  - "):
            break
        values.append(line[4:].strip().strip("'\""))
    return tuple(values)


def test_loop_mcp_is_project_scoped_pinned_and_read_only() -> None:
    config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
    server = config["mcp_servers"]["loop-engineering"]

    assert server["command"] == "npx"
    assert server["args"] == ["-y", MCP_PACKAGE]
    assert server["env"] == {"LOOP_PROJECT_ROOT": "."}
    assert tuple(server["enabled_tools"]) == MCP_TOOLS


def test_cloud_agent_uses_read_search_and_exact_mcp_allowlist() -> None:
    agent = (ROOT / ".github" / "agents" / "loop-readiness.agent.md").read_text(
        encoding="utf-8"
    )

    assert "target: github-copilot" in agent
    expected_tools = "tools:\n" + "".join(
        f"  - {tool}\n" for tool in CLOUD_AGENT_TOOLS
    ) + "mcp-servers:"
    assert expected_tools in agent
    assert MCP_PACKAGE in agent
    for tool in MCP_TOOLS:
        assert f"      - {tool}\n" in agent
    for excluded in ("loop_gate_check", "loop_audit_score", "loop_check_breaker"):
        assert excluded not in agent


def test_loop_setup_documents_pins_quick_links_and_privacy_boundary() -> None:
    setup = (ROOT / "docs" / "LOOP_ENGINEERING_SETUP.md").read_text(encoding="utf-8")

    assert MCP_PACKAGE in setup
    assert CLI_PACKAGE in setup
    assert UPSTREAM_REVISION in setup
    for quick_link in (
        "init",
        "doctor",
        "audit",
        "sync",
        "context",
        "cost",
        "gate",
        "worktree",
        "MCP",
        "action",
    ):
        assert f"| `{quick_link}` |" in setup
    assert "exports offline" in setup
    assert "Not enabled" in setup
    assert "gate check --action commit" in setup
    assert "gate check --action report" not in setup


def test_loop_gate_is_upstream_compatible_and_escalates_all_changes() -> None:
    gate = (ROOT / "gate.yaml").read_text(encoding="utf-8")

    assert re.search(r"(?m)^version: 1$", gate)
    assert "maxFiles: 0" in gate
    assert "autoMergeAllowlist: []" in gate
    assert set(_yaml_list(gate, "deny_globs")) <= set(_yaml_list(gate, "denylist"))


def test_loop_integration_files_exist_without_assigned_credentials() -> None:
    for relative in INTEGRATION_FILES:
        path = ROOT / relative
        assert path.is_file(), relative
        assert ASSIGNED_CREDENTIAL.search(path.read_text(encoding="utf-8")) is None
    assert (
        ROOT / ".agents" / "skills" / "github-cloud-loop" / "SKILL.md"
    ).read_bytes() == (
        ROOT / ".github" / "skills" / "github-cloud-loop" / "SKILL.md"
    ).read_bytes()
