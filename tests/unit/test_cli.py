"""Unit tests for TraceWeaver CLI."""

from typer.testing import CliRunner

from traceweaver import __version__
from traceweaver.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Distributed trace correlator and causal event waterfall visualizer" in result.stdout


def test_cli_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"TraceWeaver version {__version__}" in result.stdout


def test_cli_version_flags() -> None:
    for flag in ["--version", "-v"]:
        result = runner.invoke(app, [flag])
        assert result.exit_code == 0
        assert f"TraceWeaver version {__version__}" in result.stdout
