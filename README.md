# gl-team-cli

CLI GitLab pour l'equipe, base sur [Typer](https://typer.tiangolo.com/) +
[Rich](https://rich.readthedocs.io/) + [python-gitlab](https://python-gitlab.readthedocs.io/).

## Installation

```bash
uv sync
```

## Configuration

Le CLI lit sa configuration depuis des variables d'environnement (voir
`.env.example`) :

```bash
cp .env.example .env
# editer .env avec ton token
export GITLAB_URL=https://gitlab.com
export GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
```

## Usage

```bash
uv run gl-team-cli --help
uv run gl-team-cli whoami
```

## Developpement

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

## Structure

```
src/gl_team_cli/
  __init__.py   # entry point (main())
  cli.py        # app Typer + commandes
  client.py     # construction du client python-gitlab
  config.py     # lecture de la configuration (env)
  console.py    # instances Rich Console partagees
tests/
```
