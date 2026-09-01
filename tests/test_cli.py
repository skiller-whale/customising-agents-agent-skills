from pathlib import Path

from whalepage.cli import main


ROOT = Path(__file__).parent.parent


def test_build_command_writes_output(tmp_path: Path, capsys) -> None:
    output = tmp_path / "page.html"

    exit_code = main(
        ["build", str(ROOT / "examples" / "portfolio.md"), "--output", str(output)]
    )

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "Built" in capsys.readouterr().out


def test_check_command_does_not_write_output(capsys) -> None:
    exit_code = main(["check", str(ROOT / "examples" / "portfolio.md")])

    assert exit_code == 0
    assert "5 blocks" in capsys.readouterr().out
