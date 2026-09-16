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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("327,364", (327, 364)),
        (" 327 , 364 ", (327, 364)),
        ("327,,364,", (327, 364)),
        ("327", (327,)),
        ("", ()),
    ],
)
def test_from_env_team_ids(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: tuple[int, ...]
) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("GITLAB_TEAM_IDS", raw)
    assert Settings.from_env().team_ids == expected


def test_from_env_team_ids_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.delenv("GITLAB_TEAM_IDS", raising=False)
    assert Settings.from_env().team_ids == ()


def test_from_env_team_ids_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("GITLAB_TEAM_IDS", "327,abc")
    with pytest.raises(ConfigError):
        Settings.from_env()
