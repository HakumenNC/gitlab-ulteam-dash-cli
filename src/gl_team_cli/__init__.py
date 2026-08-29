"""gl-team-cli: a Typer + Rich CLI for GitLab."""

from gl_team_cli.cli import __version__, app

__all__ = ["__version__", "app", "main"]


def main() -> None:
    app()
