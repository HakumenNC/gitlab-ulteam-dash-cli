# gl-team-cli

CLI GitLab pour l'equipe, base sur [Typer](https://typer.tiangolo.com/) +
[Rich](https://rich.readthedocs.io/) + [python-gitlab](https://python-gitlab.readthedocs.io/).

## Installation

### Pour developper

```bash
uv sync
```

### En tant que commande globale (Ubuntu)

[uv](https://docs.astral.sh/uv/) installe le CLI dans un environnement isole
et place `gl-team-cli` dans le `PATH` (il telecharge Python >= 3.11 si besoin).

```bash
# 1. Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 2a. Installer depuis GitHub (branche par defaut, donc uniquement ce qui est pousse)
uv tool install git+https://github.com/HakumenNC/gitlab-ulteam-dash-cli.git

# 2b. ... ou depuis un clone local
git clone https://github.com/HakumenNC/gitlab-ulteam-dash-cli.git
cd gitlab-ulteam-dash-cli
uv tool install .

# 3. Verifier, et activer l'autocompletion (optionnel)
gl-team-cli --version
gl-team-cli --install-completion
```

Mise a jour :

```bash
uv tool upgrade gl-team-cli        # installe depuis GitHub
uv tool install --force .          # installe depuis un clone, apres git pull
```

> **Configuration** : une fois installe, le `.env` du depot n'est **pas** lu
> (voir [Configuration](#configuration)). Exporter les variables dans
> `~/.bashrc` a la place.

### Desinstallation

```bash
uv tool uninstall gl-team-cli
uv tool list                       # ne doit plus l'afficher
```

`uv tool uninstall` ne retire que le CLI. A nettoyer a la main si besoin :

- **Autocompletion** : `rm ~/.bash_completions/gl-team-cli.sh`, puis supprimer
  la ligne `source '.../.bash_completions/gl-team-cli.sh'` de `~/.bashrc`
  (sinon erreur a chaque ouverture de terminal).
- **Variables** : retirer les `export GITLAB_*` de `~/.bashrc` (et `~/.env` le
  cas echeant). Revoquer le token dans GitLab (*Preferences > Access tokens*)
  s'il ne sert plus.
- **Clone local** : `rm -rf gitlab-ulteam-dash-cli`.
- **uv lui-meme** :

  ```bash
  uv cache clean
  rm -rf "$(uv python dir)" "$(uv tool dir)"
  rm ~/.local/bin/uv ~/.local/bin/uvx
  ```

## Configuration

Le CLI lit sa configuration depuis les variables d'environnement, alimentees
au besoin par un fichier `.env` a la racine (charge automatiquement au
demarrage ; les variables deja exportees ont la priorite).

```bash
cp .env.example .env
# puis editer .env
```

> **Attention, CLI installe via `uv tool install`** : `load_dotenv()` cherche
> le `.env` en remontant depuis le dossier du module Python installe
> (`~/.local/share/uv/tools/...`), pas depuis le dossier courant. Le `.env` du
> depot est donc ignore. Exporter les variables dans `~/.bashrc` :
>
> ```bash
> export GITLAB_URL=https://gitlab.example.com
> export GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
> export GITLAB_TEAM_IDS=327,364
> ```

| Variable | Requis | Role |
|---|---|---|
| `GITLAB_TOKEN` | oui | Personal access token (scope `read_api` suffisant) |
| `GITLAB_URL` | non | Instance GitLab, defaut `https://gitlab.com` |
| `GITLAB_TEAM_IDS` | pour `team` | IDs des membres, separes par des virgules : `327,364` |

## Usage

```bash
uv run gl-team-cli --help
uv run gl-team-cli --version
```

| Commande | Effet |
|---|---|
| `whoami` | Verifier la connexion et afficher l'utilisateur authentifie |
| `activity <user_id>` | Dernieres activites (evenements) d'un utilisateur |
| `issues <user_id>` | Tickets ouverts assignes a un utilisateur |
| `dashboard <user_id>` | Activite et tickets cote a cote |
| `mrs <user_id>` | MR ouvertes assignees (gauche) et a relire (droite) |
| `team` | Choisir un membre (`GITLAB_TEAM_IDS`) puis la vue, au clavier |

Toutes les commandes d'affichage acceptent `--limit / -n` (defaut : 20) :

```bash
uv run gl-team-cli dashboard 327 -n 10
uv run gl-team-cli team          # menu interactif, fleches + Entree
```

Les colonnes **Cible** et **Titre** sont cliquables (liens OSC 8) et prefixees
par la reference GitLab : `#40` pour une issue, `!17` pour une merge request.

## Developpement

```bash
uv run python -m pytest -q      # cf. note ci-dessous
uv run ruff check src tests
uv run mypy src tests
```

> **Note** : utiliser `uv run python -m pytest`, pas `uv run pytest`. Sur
> certaines machines le second resout un autre venv et echoue avec des
> `ModuleNotFoundError` trompeurs.

## Structure

```
src/gl_team_cli/
  __init__.py      # point d'entree du script (main())
  cli.py           # app Typer + commandes (couche mince)
  client.py        # construction du client python-gitlab
  config.py        # lecture de la configuration (.env + env)
  console.py       # instances Rich Console partagees
  errors.py        # context manager gitlab_errors -> sortie CLI propre
  gitlab_data.py   # plomberie API : cache projet, reconstruction d'URLs
  prompts.py       # listes interactives questionary
  render.py        # construction des tableaux Rich
tests/
```

Les dependances entre modules sont acycliques :
`cli` -> `client` / `prompts` / `render` -> `gitlab_data`.
