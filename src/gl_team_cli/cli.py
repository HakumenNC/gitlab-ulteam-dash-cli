"""Entry point for the gl-team-cli Typer application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import gitlab
import typer
from gitlab.base import RESTObject
from rich.markup import escape
from rich.table import Table

from gl_team_cli.client import get_client
from gl_team_cli.config import ConfigError, Settings
from gl_team_cli.console import console, error_console

# New Caledonia Time (NCT), utilisee pour l'affichage des dates.
NCT = timezone(timedelta(hours=11))


def _format_date(iso_date: str, tz: timezone = NCT) -> str:
    """Convertir une date ISO 8601 (UTC, renvoyee par l'API GitLab) vers `tz`."""
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")

app = typer.Typer(
    name="gl-team-cli",
    help="CLI GitLab pour l'equipe, base sur Typer + Rich + python-gitlab.",
    no_args_is_help=True,
    add_completion=True,
)


__version__ = "0.1.0"


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


@app.command()
def whoami() -> None:
    """Verifier la connexion et afficher l'utilisateur GitLab authentifie."""
    try:
        settings = Settings.from_env()
        gl = get_client(settings)
        gl.auth()
    except ConfigError as exc:
        error_console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabAuthenticationError as exc:
        error_console.print(f"Authentification GitLab echouee : {exc}")
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabError as exc:
        error_console.print(f"Erreur GitLab ({settings.url}) : {exc}")
        raise typer.Exit(code=1) from exc

    user = gl.user
    assert user is not None  # garanti par gl.auth() ci-dessus

    table = Table(title="Utilisateur GitLab authentifie", show_header=False)
    table.add_row("Serveur", settings.url)
    table.add_row("Username", user.username)
    table.add_row("Nom", user.name)
    table.add_row("Email", user.email or "-")
    table.add_row("ID", str(user.id))
    console.print(table)


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    name: str
    web_url: str


ProjectCache = dict[int, ProjectInfo | None]


def _get_project_info(
    gl: gitlab.Gitlab, project_id: int, cache: ProjectCache
) -> ProjectInfo | None:
    """Recuperer nom + web_url d'un projet, mis en cache pour eviter les appels API repetes."""
    if project_id not in cache:
        try:
            project = gl.projects.get(project_id)
            cache[project_id] = ProjectInfo(name=project.name, web_url=project.web_url)
        except gitlab.GitlabError:
            cache[project_id] = None
    return cache[project_id]


# Pictos par type d'action, faute de pouvoir recuperer les icones de l'UI
# GitLab (celles-ci font partie de son bundle front-end, pas de l'API).
_ACTION_ICONS: dict[str, str] = {
    "opened": ":green_circle:",
    "closed": ":red_circle:",
    "reopened": ":large_yellow_circle:",
    "merged": ":twisted_rightwards_arrows:",
    "approved": ":white_check_mark:",
    "commented on": ":speech_balloon:",
    "pushed to": ":arrow_up:",
    "pushed new": ":sparkles:",
    "created": ":new:",
    "updated": ":pencil2:",
    "deleted": ":wastebasket:",
    "destroyed": ":wastebasket:",
    "joined": ":wave:",
    "left": ":door:",
    "accepted": ":white_check_mark:",
    "expired": ":hourglass_done:",
}
_DEFAULT_ACTION_ICON = ":small_blue_diamond:"


def _action_cell(action_name: str) -> str:
    icon = _ACTION_ICONS.get(action_name, _DEFAULT_ACTION_ICON)
    return f"{icon} {action_name}"


def _build_target_url(
    gl: gitlab.Gitlab, event: RESTObject, project_cache: ProjectCache
) -> str | None:
    """Reconstruire l'URL de la cible d'un evenement.

    L'API GitLab ne renvoie pas de champ `target_url` direct : il faut
    combiner le `web_url` du projet (recupere et mis en cache par projet)
    avec le type/iid de la cible.
    """
    project_id: int | None = getattr(event, "project_id", None)
    if project_id is None:
        return None

    project = _get_project_info(gl, project_id, project_cache)
    if project is None:
        return None
    web_url = project.web_url

    target_type = getattr(event, "target_type", None)
    target_id = getattr(event, "target_id", None)
    target_iid = getattr(event, "target_iid", None)

    # Un commentaire (Note/DiffNote) pointe vers son "noteable" (MR/Issue),
    # dont l'iid se trouve dans le sous-objet `note`, pas dans target_iid.
    note = getattr(event, "note", None)
    if target_type in ("Note", "DiffNote", "DiscussionNote") and note:
        noteable_type = note.get("noteable_type")
        noteable_iid = note.get("noteable_iid")
        anchor = f"#note_{target_id}" if target_id else ""
        if noteable_type == "MergeRequest" and noteable_iid:
            return f"{web_url}/-/merge_requests/{noteable_iid}{anchor}"
        if noteable_type == "Issue" and noteable_iid:
            return f"{web_url}/-/issues/{noteable_iid}{anchor}"
        return None

    if target_type == "MergeRequest" and target_iid:
        return f"{web_url}/-/merge_requests/{target_iid}"
    if target_type == "Issue" and target_iid:
        return f"{web_url}/-/issues/{target_iid}"
    if target_type == "Milestone" and target_iid:
        return f"{web_url}/-/milestones/{target_iid}"

    return web_url


@app.command()
def activity(
    user_id: Annotated[int, typer.Argument(help="ID numerique de l'utilisateur GitLab.")],
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Nombre d'evenements a afficher.")
    ] = 20,
) -> None:
    """Afficher les dernieres activites (evenements) d'un utilisateur."""
    try:
        settings = Settings.from_env()
        gl = get_client(settings)
        user = gl.users.get(user_id)
        events = user.events.list(per_page=limit, get_all=False)
    except ConfigError as exc:
        error_console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabGetError as exc:
        error_console.print(f"Utilisateur {user_id} introuvable : {exc}")
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabError as exc:
        error_console.print(f"Erreur GitLab : {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f":hourglass: Dernieres activites de {user.username} (ID {user_id}) :hourglass:",
        style="cyan",
        show_lines=True,
    )
    table.add_column("Date (NCT, UTC+11)", header_style="bold orange3")
    table.add_column("Projet", header_style="bold orange3")
    table.add_column("Action", header_style="bold orange3")
    table.add_column("Cible", header_style="bold orange3")
    table.add_column("URL", header_style="bold orange3")

    project_cache: ProjectCache = {}
    for event in events:
        target = event.target_title or event.target_type or "-"
        project_id: int | None = getattr(event, "project_id", None)
        project_name = "-"
        if project_id is not None:
            project_info = _get_project_info(gl, project_id, project_cache)
            if project_info is not None:
                project_name = project_info.name
        url = _build_target_url(gl, event, project_cache)
        url_cell = f"[link={url}]{url}[/link]" if url else "-"
        table.add_row(
            _format_date(event.created_at),
            project_name,
            _action_cell(event.action_name),
            target,
            url_cell,
        )

    console.print(table)


@app.command()
def issues(
    user_id: Annotated[int, typer.Argument(help="ID numerique de l'utilisateur GitLab.")],
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Nombre de tickets a afficher.")
    ] = 20,
) -> None:
    """Afficher les derniers tickets (issues) assignes a un utilisateur."""
    try:
        settings = Settings.from_env()
        gl = get_client(settings)
        user = gl.users.get(user_id)
        issue_list = gl.issues.list(
            assignee_id=user_id,
            state="opened",
            # Recupere name/color/text_color par label au lieu de simples
            # chaines, pour pouvoir reproduire leurs couleurs GitLab.
            with_labels_details=True,
            # Sans scope="all", l'API ne cherche que parmi les tickets crees
            # par le proprietaire du token (comportement par defaut de
            # l'endpoint global /issues), pas parmi tous ceux accessibles.
            scope="all",
            order_by="created_at",
            sort="desc",
            per_page=limit,
            get_all=False,
        )
    except ConfigError as exc:
        error_console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabGetError as exc:
        error_console.print(f"Utilisateur {user_id} introuvable : {exc}")
        raise typer.Exit(code=1) from exc
    except gitlab.GitlabError as exc:
        error_console.print(f"Erreur GitLab : {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f":ticket: Derniers tickets assignes a {user.username} (ID {user_id}) :ticket:",
        style="cyan",
        show_lines=True,
    )
    table.add_column("Date creation (NCT, UTC+11)", header_style="bold orange3")
    table.add_column("Projet", header_style="bold orange3")
    table.add_column("Titre", header_style="bold orange3")
    table.add_column("Statut", header_style="bold orange3")
    table.add_column("Labels", header_style="bold orange3")
    table.add_column("URL", header_style="bold orange3")

    project_cache: ProjectCache = {}
    for issue in issue_list:
        project_info = _get_project_info(gl, issue.project_id, project_cache)
        project_name = project_info.name if project_info is not None else "-"
        status_style = "green" if issue.state == "opened" else "red"
        status_cell = f"[{status_style}]{issue.state}[/{status_style}]"
        labels_cell = (
            " ".join(
                f"[{label['text_color']} on {label['color']}] {escape(label['name'])} [/]"
                for label in issue.labels
            )
            or "-"
        )
        url_cell = f"[link={issue.web_url}]{issue.web_url}[/link]"
        table.add_row(
            _format_date(issue.created_at),
            project_name,
            escape(issue.title),
            status_cell,
            labels_cell,
            url_cell,
        )

    console.print(table)


if __name__ == "__main__":
    app()
