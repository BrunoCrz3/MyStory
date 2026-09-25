"""Dónde está la toolchain de Lean (L-D10).

Lean es dependencia de toolchain, no de Python (`architecture.md` § Lean): se busca `lake` en
el `PATH` y, si no está, en `~/.elan/bin`, que es donde lo deja `elan` y donde no siempre llega
el `PATH` de un shell (I-03). Si no aparece, quien llama decide: el gate falla y el chequeo
incremental avisa.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.commons.db.conexion import RAIZ_REPO

PROYECTO_LEAN = RAIZ_REPO / "formal" / "lean"


def buscar_lake() -> Path | None:
    """La ruta de `lake`, o `None` si no está instalado."""
    en_path = shutil.which("lake")
    if en_path is not None:
        return Path(en_path)
    elan = Path.home() / ".elan" / "bin"
    for nombre in ("lake.exe", "lake"):
        candidato = elan / nombre
        if candidato.is_file():
            return candidato
    return None


def donde_se_busco() -> str:
    return f"PATH y {Path.home() / '.elan' / 'bin'}"
