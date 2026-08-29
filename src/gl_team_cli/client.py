"""Thin wrapper around python-gitlab's client construction."""

from __future__ import annotations

import gitlab

from gl_team_cli.config import Settings


def get_client(settings: Settings) -> gitlab.Gitlab:
    """Build an authenticated python-gitlab client."""
    gl = gitlab.Gitlab(url=settings.url, private_token=settings.token)
    return gl
