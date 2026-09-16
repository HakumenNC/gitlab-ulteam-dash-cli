"""Traduction des erreurs de configuration / GitLab en sortie CLI propre."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import gitlab
import typer

from gl_team_cli.config import ConfigError
from gl_team_cli.console import error_console


@contextmanager
def gitlab_errors(prefix: str = "Erreur GitLab") -> Iterator[None]:
    """Afficher l'erreur sur stderr et quitter avec le code 1 au lieu d'une traceback."""
    try:
        yield
    except ConfigError as exc:
        error_console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabAuthenticationError as exc:
        error_console.print(f"Authentification GitLab echouee : {exc}")
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabError as exc:
        error_console.print(f"{prefix} : {exc}")
        raise typer.Exit(code=1) from exc
