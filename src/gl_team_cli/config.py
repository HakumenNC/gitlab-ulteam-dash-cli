"""Configuration for the GitLab connection.

Values are read from environment variables (optionally loaded from a
`.env` file if `python-dotenv` is installed and used by the caller):

- GITLAB_URL:  base URL of the GitLab instance (default: https://gitlab.com)
- GITLAB_TOKEN: personal/project access token used to authenticate
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    url: str
    token: str

    @classmethod
    def from_env(cls) -> Settings:
        url = os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/")
        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise ConfigError(
                "GITLAB_TOKEN is not set. Export a GitLab personal access "
                "token, e.g.:\n"
                "  export GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx"
            )
        return cls(url=url, token=token)
