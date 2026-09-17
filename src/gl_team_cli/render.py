"""Construction des tableaux Rich a partir des objets GitLab."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import gitlab
from gitlab.base import RESTObject
from rich.columns import Columns
from rich.console import Group
from rich.markup import escape
from rich.rule import Rule
from rich.table import Table

from gl_team_cli.gitlab_data import (
    NOTE_TYPES,
    ProjectCache,
    build_target_url,
    get_project_info,
)

# New Caledonia Time (NCT), utilisee pour l'affichage des dates.
NCT = timezone(timedelta(hours=11))

# Largeur fixe des tableaux : garantit que les deux moities du dashboard
# restent alignees cote a cote.
#
# Deux tableaux cote a cote occupent 2 * TABLE_WIDTH + 2 (l'espacement de
# Columns), soit 178 colonnes ici. Ca tient dans un terminal plein ecran en
# 1920x1080, y compris avec les polices les plus larges (~185 colonnes).
TABLE_WIDTH = 88


def format_date(iso_date: str, tz: timezone = NCT) -> str:
    """Convertir une date ISO 8601 (UTC, renvoyee par l'API GitLab) vers `tz`."""
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return dt.astimezone(tz).strftime("%Y-%m-%d\n%H:%M:%S")


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


# (style Rich, symbole) par type de cible GitLab, pour le prefixe de la colonne Cible.
_REF_STYLE: dict[str, tuple[str, str]] = {
    "Issue": ("bold orange3", "#"),
    "MergeRequest": ("bold medium_purple", "!"),
}


def _target_prefix(event: RESTObject) -> str:
    """`#40 ` (issue) ou `!17 ` (MR) selon la cible de l'evenement (ou son commentaire)."""
    target_type = getattr(event, "target_type", None)
    if target_type in _REF_STYLE:
        iid = getattr(event, "target_iid", None)
        style, symbol = _REF_STYLE[target_type]
        return f"[{style}]{symbol}{iid}[/{style}] " if iid else ""

    note = getattr(event, "note", None)
    if target_type in NOTE_TYPES and note:
        noteable_type = note.get("noteable_type")
        noteable_iid = note.get("noteable_iid")
        if noteable_type in _REF_STYLE and noteable_iid:
            style, symbol = _REF_STYLE[noteable_type]
            return f"[{style}]{symbol}{noteable_iid}[/{style}] "
    return ""


def activity_table(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Table:
    events = user.events.list(per_page=limit, get_all=False)

    table = Table(
        title=f":hourglass: Dernieres activites de {user.username} (ID {user.id}) :hourglass:",
        style="cyan",
        show_lines=True,
        width=TABLE_WIDTH,
    )
    table.add_column("Date", header_style="bold orange3")
    table.add_column("Projet", header_style="bold orange3")
    table.add_column("Action", header_style="bold orange3")
    table.add_column("Cible", header_style="bold orange3")

    project_cache: ProjectCache = {}
    for event in events:
        target = _target_prefix(event) + escape(
            event.target_title or event.target_type or "-"
        )
        project_id: int | None = getattr(event, "project_id", None)
        project_name = "-"
        if project_id is not None:
            project_info = get_project_info(gl, project_id, project_cache)
            if project_info is not None:
                project_name = project_info.name
        url = build_target_url(gl, event, project_cache)
        # La colonne URL a ete supprimee : on rend "Cible" cliquable a la place.
        target_cell = f"[link={url}]{target}[/link]" if url else target
        table.add_row(
            format_date(event.created_at),
            project_name,
            _action_cell(event.action_name),
            target_cell,
        )
    return table


def issues_table(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Table:
    issue_list = gl.issues.list(
        assignee_id=user.id,
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

    table = Table(
        title=f":ticket: Derniers tickets assignes a {user.username} (ID {user.id}) :ticket:",
        style="cyan",
        show_lines=True,
        width=TABLE_WIDTH,
    )
    table.add_column("Créé le", header_style="bold orange3")
    table.add_column("Projet", header_style="bold orange3")
    table.add_column("Titre", header_style="bold orange3")
    table.add_column("Statut", header_style="bold orange3")
    table.add_column("Labels", header_style="bold orange3")

    project_cache: ProjectCache = {}
    for issue in issue_list:
        project_info = get_project_info(gl, issue.project_id, project_cache)
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
        # La colonne URL a ete supprimee : on rend "Titre" cliquable a la place.
        title_cell = (
            f"[link={issue.web_url}][bold orange3]#{issue.iid}[/bold orange3] "
            f"{escape(issue.title)}[/link]"
        )
        table.add_row(
            format_date(issue.created_at),
            project_name,
            title_cell,
            status_cell,
            labels_cell,
        )
    return table


def _merge_requests_table(
    gl: gitlab.Gitlab, user: RESTObject, limit: int, *, role: str, title: str
) -> Table:
    """Tableau des MR ouvertes ou `user` tient le role `assignee` ou `reviewer`."""
    mr_list = gl.mergerequests.list(
        # `assignee_id` / `reviewer_id` : un seul des deux selon le role demande.
        **{f"{role}_id": user.id},
        state="opened",
        with_labels_details=True,
        # Comme pour les issues : sans scope="all", l'API ne regarde que les
        # MR du proprietaire du token.
        scope="all",
        order_by="created_at",
        sort="desc",
        per_page=limit,
        get_all=False,
    )

    table = Table(
        title=title,
        style="cyan",
        show_lines=True,
        width=TABLE_WIDTH,
    )
    table.add_column("Créé le", header_style="bold orange3")
    table.add_column("Projet", header_style="bold orange3")
    table.add_column("Titre", header_style="bold orange3")
    table.add_column("Auteur", header_style="bold orange3")
    table.add_column("Statut", header_style="bold orange3")

    project_cache: ProjectCache = {}
    for mr in mr_list:
        project_info = get_project_info(gl, mr.project_id, project_cache)
        project_name = project_info.name if project_info is not None else "-"
        # La colonne URL a ete supprimee : on rend "Titre" cliquable a la place.
        title_cell = (
            f"[link={mr.web_url}][bold medium_purple]!{mr.iid}[/bold medium_purple] "
            f"{escape(mr.title)}[/link]"
        )
        if mr.draft:
            status_cell = "[yellow]draft[/yellow]"
        else:
            status_cell = f"[green]{mr.state}[/green]"
        table.add_row(
            format_date(mr.created_at),
            project_name,
            title_cell,
            escape(mr.author["username"]),
            status_cell,
        )
    return table


def mrs_assigned_table(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Table:
    return _merge_requests_table(
        gl,
        user,
        limit,
        role="assignee",
        title=":twisted_rightwards_arrows: Assignees",
    )


def mrs_review_table(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Table:
    return _merge_requests_table(
        gl,
        user,
        limit,
        role="reviewer",
        title=":eyes: A relire",
    )


def mrs_columns(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Group:
    """MR assignees (gauche) et MR a relire (droite), sous un titre commun.

    Le `Rule` porte l'identite de l'utilisateur, les titres des deux tables
    ne portent plus que leur role : pas de repetition sur trois lignes.
    """
    header = Rule(
        f"[bold]Merge requests de {escape(user.username)} (ID {user.id})[/bold]",
        style="cyan",
    )
    tables = Columns(
        [mrs_assigned_table(gl, user, limit), mrs_review_table(gl, user, limit)],
        padding=(0, 2),
        equal=True,
    )
    # Les "" sont des lignes vides : elles aerent le Rule au-dessus des tables.
    return Group("", header, "", tables, "")


def dashboard_columns(gl: gitlab.Gitlab, user: RESTObject, limit: int) -> Columns:
    """Activite et tickets d'un utilisateur, cote a cote."""
    left = activity_table(gl, user, limit)
    right = issues_table(gl, user, limit)
    return Columns([left, right], padding=(0, 2), equal=True)
