"""Thin wrapper around python-gitlab's client construction."""

from __future__ import annotations

import gitlab
from gitlab.base import RESTObject

from gl_team_cli.config import Settings
from gl_team_cli.errors import gitlab_errors


def get_client(settings: Settings) -> gitlab.Gitlab:
    """Build an authenticated python-gitlab client."""
    return gitlab.Gitlab(url=settings.url, private_token=settings.token)


def client_and_settings() -> tuple[gitlab.Gitlab, Settings]:
    """Point d'entree commun des commandes : config lue puis client construit."""
    with gitlab_errors():
        settings = Settings.from_env()
        return get_client(settings), settings


def client_and_user(user_id: int | None = None) -> tuple[gitlab.Gitlab, RESTObject]:
    """Comme `client_and_settings`, mais resout aussi l'utilisateur cible.

    Sans `user_id`, c'est le proprietaire du token (`gl.auth()`) qui est vise.
    """
    gl, settings = client_and_settings()

    if user_id is None:
        with gitlab_errors(f"Erreur GitLab ({settings.url})"):
            gl.auth()
        assert gl.user is not None  # garanti par gl.auth() ci-dessus
        # `gl.user` est un CurrentUser, sans `.events` : on recharge le User
        # complet, comme pour les membres de l'equipe.
        user_id = gl.user.id

    with gitlab_errors(f"Utilisateur {user_id} introuvable"):
        return gl, gl.users.get(user_id)
