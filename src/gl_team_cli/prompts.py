"""Listes interactives navigables au clavier (fleches haut/bas, Entree)."""

from __future__ import annotations

import gitlab
import questionary
import typer
from gitlab.base import RESTObject

from gl_team_cli.console import error_console

_INSTRUCTION = "(fleches pour naviguer, Entree pour valider)"


def team_members(gl: gitlab.Gitlab, team_ids: tuple[int, ...]) -> list[RESTObject]:
    """Resoudre les IDs de GITLAB_TEAM_IDS en objets utilisateur GitLab."""
    members: list[RESTObject] = []
    for user_id in team_ids:
        try:
            members.append(gl.users.get(user_id))
        except gitlab.GitlabError as exc:
            error_console.print(f"Utilisateur {user_id} introuvable, ignore : {exc}")
    return members


def select_member(members: list[RESTObject]) -> RESTObject:
    """Choisir un membre de l'equipe dans une liste navigable."""
    choices = [
        questionary.Choice(title=f"{m.name} (@{m.username}, ID {m.id})", value=m)
        for m in members
    ]
    member: RESTObject | None = questionary.select(
        "Choisis un membre de l'equipe :",
        choices=choices,
        instruction=_INSTRUCTION,
    ).ask()
    if member is None:  # Ctrl-C / Echap
        raise typer.Exit(code=1)
    return member


def select_view() -> str:
    """Choisir quoi afficher : `issues`, `activity` ou `dashboard`."""
    view: str | None = questionary.select(
        "Que veux-tu afficher ?",
        choices=[
            questionary.Choice(title="Tickets (issues)", value="issues"),
            questionary.Choice(title="Activite (events)", value="activity"),
            questionary.Choice(title="Les deux (dashboard)", value="dashboard"),
            questionary.Choice(title="Merge requests (assignees / a relire)", value="mrs"),
        ],
        instruction=_INSTRUCTION,
    ).ask()
    if view is None:  # Ctrl-C / Echap
        raise typer.Exit(code=1)
    return view
