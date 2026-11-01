import pytest
from typer.testing import CliRunner

from gl_team_cli.cli import RENDERERS, app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutraliser le `.env` du poste : les tests pilotent os.environ eux-memes."""
    monkeypatch.setattr("gl_team_cli.cli.load_env", lambda: None)
    for var in ("GITLAB_TOKEN", "GITLAB_URL", "GITLAB_TEAM_IDS"):
        monkeypatch.delenv(var, raising=False)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "gl-team-cli" in result.output


@pytest.mark.parametrize(
    "command", ["whoami", "activity", "issues", "dashboard", "mrs", "me", "team"]
)
def test_command_is_wired(command: str) -> None:
    """Chaque commande est enregistree et son --help s'affiche sans toucher au reseau."""
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0


def test_renderers_cover_select_view_values() -> None:
    """Le dict de vues de `team` couvre exactement les valeurs proposees par le prompt."""
    assert set(RENDERERS) == {"issues", "activity", "dashboard", "mrs"}


def test_missing_token_exits_1() -> None:
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 1


def test_team_without_team_ids_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    result = runner.invoke(app, ["team"])
    assert result.exit_code == 1


def test_me_without_token_exits_1() -> None:
    result = runner.invoke(app, ["me"])
    assert result.exit_code == 1
