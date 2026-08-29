import pytest

from gl_team_cli.config import ConfigError, Settings


def test_from_env_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_from_env_defaults_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.delenv("GITLAB_URL", raising=False)
    settings = Settings.from_env()
    assert settings.url == "https://gitlab.com"
    assert settings.token == "glpat-test"


def test_from_env_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/")
    settings = Settings.from_env()
    assert settings.url == "https://gitlab.example.com"
