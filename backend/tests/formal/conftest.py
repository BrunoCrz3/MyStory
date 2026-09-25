"""Proyecto Lake de la cronología, copiado una vez por sesión (plan 4 § 4.2).

Nada de dobles de Lean: un validador formal probado contra un doble no prueba nada. Lean es
dependencia declarada del stack, así que sin `lake` estas pruebas **fallan**, no se saltan.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.versioning.lean.toolchain import PROYECTO_LEAN, buscar_lake, donde_se_busco


@dataclass(frozen=True)
class Lake:
    ejecutable: Path
    proyecto: Path

    def construir(self, modulo: str, texto: str) -> subprocess.CompletedProcess[str]:
        """Escribe `Cronologia/<modulo>.lean` en la copia y lo construye."""
        (self.proyecto / "Cronologia" / f"{modulo}.lean").write_text(
            texto, encoding="utf-8", newline="\n"
        )
        return subprocess.run(
            [str(self.ejecutable), "build", f"Cronologia.{modulo}"],
            cwd=self.proyecto,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            check=False,
        )


@pytest.fixture(scope="session")
def lake(tmp_path_factory: pytest.TempPathFactory) -> Lake:
    ejecutable = buscar_lake()
    if ejecutable is None:
        pytest.fail(f"las pruebas de Lean exigen `lake` instalado; se buscó en {donde_se_busco()}")
    copia = tmp_path_factory.mktemp("lean") / "proyecto"
    shutil.copytree(PROYECTO_LEAN, copia, ignore=shutil.ignore_patterns(".lake", "Hechos.lean"))
    r = subprocess.run(
        [str(ejecutable), "build"], cwd=copia, capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return Lake(ejecutable=ejecutable, proyecto=copia)
