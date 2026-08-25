from __future__ import annotations

from pathlib import Path

SCRIPT_PATHS = [
    Path("scripts/run_pipeline.ps1"),
    Path("scripts/run_pipeline.bat"),
    Path("scripts/run_tests.ps1"),
    Path("scripts/export_public.ps1"),
    Path("scripts/export_expert_packet.ps1"),
]

ALLOWED_AAVE_COMMANDS = {
    "scan",
    "parse-gedcom",
    "link",
    "export",
    "inspect-archives",
    "packet",
}

FORBIDDEN_TERMS = {
    "archivebox",
    "zotero",
    "perma.cc",
    "snpedia",
    "ancestrydna",
    "api_key",
    "token",
    "invoke-webrequest",
    "invoke-restmethod",
    "curl",
    "wget",
    "selenium",
    "webdriver",
}


def test_windows_scripts_exist() -> None:
    for script_path in SCRIPT_PATHS:
        assert script_path.exists(), f"Missing script: {script_path}"


def test_windows_scripts_do_not_reference_forbidden_integrations() -> None:
    combined_text = "\n".join(
        script_path.read_text(encoding="utf-8").lower() for script_path in SCRIPT_PATHS
    )

    for forbidden_term in FORBIDDEN_TERMS:
        assert forbidden_term not in combined_text


def test_pipeline_script_uses_only_existing_aave_pipeline_commands() -> None:
    script_text = Path("scripts/run_pipeline.ps1").read_text(encoding="utf-8")

    for command_name in ALLOWED_AAVE_COMMANDS:
        if command_name in {"scan", "parse-gedcom", "link", "inspect-archives", "packet"}:
            assert f'"{command_name}"' in script_text

    assert '"public_redacted"' in script_text
    assert '"private_full"' in script_text
    assert '"expert_review_packet"' in script_text
