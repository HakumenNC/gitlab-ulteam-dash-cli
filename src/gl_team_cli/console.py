"""Shared Rich console instances."""

from __future__ import annotations

import io
import sys

from rich.console import Console

# Sur Windows, l'encodage par defaut de la console (souvent cp1252) fait
# planter tout affichage de caracteres non-ASCII (ex: les blocs pixel-art
# de rich-pixels). On force l'UTF-8 explicitement plutot que de compter
# sur PYTHONUTF8/chcp 65001 configures a la main par l'utilisateur.
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if isinstance(_stream, io.TextIOWrapper):
            _stream.reconfigure(encoding="utf-8", errors="replace")

console = Console()
error_console = Console(stderr=True, style="bold red")
