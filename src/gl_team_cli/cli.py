"""Entry point for the gl-team-cli Typer application."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer
from rich.table import Table

from gl_team_cli.client import client_and_settings, client_and_user
from gl_team_cli.config import load_env
from gl_team_cli.console import console, error_console
from gl_team_cli.errors import gitlab_errors
from gl_team_cli.prompts import select_member, select_view, team_members
from gl_team_cli.render import (
    activity_table,
    dashboard_columns,
    issues_table,
    mrs_columns,
)

app = typer.Typer(
    name="gl-team-cli",
    help="CLI GitLab pour l'equipe, base sur Typer + Rich + python-gitlab.",
    no_args_is_help=True,
    add_completion=True,
)

try:
    __version__ = version("gl-team-cli")
except PackageNotFoundError:  # execution depuis les sources, sans installation
    __version__ = "0.0.0+dev"

# Nombre de lignes par tableau, partage par toutes les commandes.
LimitOption = Annotated[int, typer.Option("--limit", "-n", help="Nombre de lignes par tableau.")]
UserIdArgument = Annotated[int, typer.Argument(help="ID numerique de l'utilisateur GitLab.")]

# Vues proposees par `team`, indexees par la valeur renvoyee par select_view().
RENDERERS = {
    "issues": issues_table,
    "activity": activity_table,
    "dashboard": dashboard_columns,
    "mrs": mrs_columns,
}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"gl-team-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Afficher la version et quitter.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """CLI GitLab pour l'equipe."""
    # Avant toute commande : le `.env` alimente os.environ, que lit Settings.
    load_env()


@app.command()
def whoami() -> None:
    """Verifier la connexion et afficher l'utilisateur GitLab authentifie."""
    gl, settings = client_and_settings()
    with gitlab_errors(f"Erreur GitLab ({settings.url})"):
        gl.auth()

    user = gl.user
    assert user is not None  # garanti par gl.auth() ci-dessus

    table = Table(title="Utilisateur GitLab authentifie", show_header=False)
    table.add_row("Serveur", settings.url)
    table.add_row("Username", user.username)
    table.add_row("Nom", user.name)
    table.add_row("Email", user.email or "-")
    table.add_row("ID", str(user.id))
    console.print(table)


@app.command()
def activity(user_id: UserIdArgument, limit: LimitOption = 20) -> None:
    """Afficher les dernieres activites (evenements) d'un utilisateur."""
    gl, user = client_and_user(user_id)
    with gitlab_errors():
        console.print(activity_table(gl, user, limit))


@app.command()
def issues(user_id: UserIdArgument, limit: LimitOption = 20) -> None:
    """Afficher les derniers tickets (issues) assignes a un utilisateur."""
    gl, user = client_and_user(user_id)
    with gitlab_errors():
        console.print(issues_table(gl, user, limit))


@app.command()
def dashboard(user_id: UserIdArgument, limit: LimitOption = 20) -> None:
    """Afficher activite et tickets d'un utilisateur, cote a cote."""
    gl, user = client_and_user(user_id)
    with gitlab_errors():
        console.print(dashboard_columns(gl, user, limit))


@app.command()
def mrs(user_id: UserIdArgument, limit: LimitOption = 20) -> None:
    """Afficher les MR assignees a un utilisateur et celles qu'il doit relire."""
    gl, user = client_and_user(user_id)
    with gitlab_errors():
        console.print(mrs_columns(gl, user, limit))


@app.command()
def team(limit: LimitOption = 20) -> None:
    """Choisir un membre de l'equipe (GITLAB_TEAM_IDS) et ce qu'on affiche pour lui."""
    gl, settings = client_and_settings()

    if not settings.team_ids:
        error_console.print(
            "GITLAB_TEAM_IDS n'est pas defini. Exemple :\n  export GITLAB_TEAM_IDS=327,364"
        )
        raise typer.Exit(code=1)

    members = team_members(gl, settings.team_ids)
    if not members:
        error_console.print("Aucun membre d'equipe valide trouve.")
        raise typer.Exit(code=1)

    member = select_member(members)
    view = select_view()

    with gitlab_errors():
        console.print(RENDERERS[view](gl, member, limit))


if __name__ == "__main__":
    app()
