from __future__ import annotations

import pytest

from aave.cli import main


def test_cli_help_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Local-first archival validation tools" in captured.out
    assert "genome" in captured.out
    assert "integrations" in captured.out
    assert "evidence" in captured.out
    assert "claims" in captured.out
    assert "identity" not in captured.out
    assert "branch-policy" not in captured.out


def test_cli_integrations_help_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["integrations", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "archivebox" in captured.out
    assert "zotero" in captured.out
    assert "perma" in captured.out
    assert "static-site" in captured.out


@pytest.mark.parametrize("private_command", ["identity", "branch-policy"])
def test_cli_private_only_commands_are_not_available(
    private_command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([private_command, "--help"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
