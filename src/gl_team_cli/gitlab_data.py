"""Acces aux donnees GitLab qui demandent un peu de plomberie (cache projet, URLs)."""

from __future__ import annotations

from dataclasses import dataclass

import gitlab
from gitlab.base import RESTObject

# Types de commentaires GitLab : leur cible reelle (MR/Issue) est dans le
# sous-objet `note`, pas dans `target_iid`.
NOTE_TYPES = ("Note", "DiffNote", "DiscussionNote")


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    name: str
    web_url: str


ProjectCache = dict[int, ProjectInfo | None]


def get_project_info(
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


def build_target_url(
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

    project = get_project_info(gl, project_id, project_cache)
    if project is None:
        return None
    web_url = project.web_url

    target_type = getattr(event, "target_type", None)
    target_id = getattr(event, "target_id", None)
    target_iid = getattr(event, "target_iid", None)

    # Un commentaire (Note/DiffNote) pointe vers son "noteable" (MR/Issue),
    # dont l'iid se trouve dans le sous-objet `note`, pas dans target_iid.
    note = getattr(event, "note", None)
    if target_type in NOTE_TYPES and note:
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
