"""Ejecutor de Lean (RF-LEAN-02, L-D09, L-D10).

Copia `formal/lean/` a un directorio temporal, escribe allí `Cronologia/Hechos.lean` y
construye ese módulo con `lake build` dentro de `formal.lean_timeout_segundos`. La copia se
borra al terminar: dos ejecuciones no se pisan y el árbol versionado no se ensucia.

Timeout, toolchain ausente o un error que no casa con ningún teorema son **rojo**, nunca
excepción ni verde: quien llama decide si eso bloquea (gate) o avisa (incremental).
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.process.service import VeredictoGate
from app.versioning.lean import informe
from app.versioning.lean.generar import Cronologia, generar
from app.versioning.lean.toolchain import PROYECTO_LEAN, buscar_lake, donde_se_busco

EstadoLean = Literal["demostrado", "fallos", "timeout", "toolchain-ausente", "error"]


class ResultadoLean(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: EstadoLean
    veredictos: list[VeredictoGate]
    duracion_segundos: float
    bytes_fichero: int
    eventos: int


def _copiar_proyecto(destino: Path) -> Path:
    """Copia el proyecto con su `.lake` si existe: `Basico` ya compilado ahorra el grueso del
    build, y Lake recompila lo que no cuadre con sus trazas."""
    proyecto = destino / "lean"
    shutil.copytree(PROYECTO_LEAN, proyecto, ignore=shutil.ignore_patterns("Hechos.*"))
    return proyecto


async def verificar(c: Cronologia, *, timeout: float) -> ResultadoLean:
    """Genera el fichero de `c`, lo construye y devuelve los cuatro veredictos."""
    fichero = generar(c)
    tamano = len(fichero.texto.encode("utf-8"))
    inicio = time.monotonic()

    def resultado(estado: EstadoLean, veredictos: list[VeredictoGate]) -> ResultadoLean:
        return ResultadoLean(
            estado=estado,
            veredictos=veredictos,
            duracion_segundos=round(time.monotonic() - inicio, 3),
            bytes_fichero=tamano,
            eventos=len(c.eventos),
        )

    lake = buscar_lake()
    if lake is None:
        return resultado(
            "toolchain-ausente",
            informe.fallo_total(f"toolchain-ausente: no se encontró `lake` en {donde_se_busco()}"),
        )
    directorio = Path(tempfile.mkdtemp(prefix="storymaker-lean-"))
    try:
        proyecto = _copiar_proyecto(directorio)
        (proyecto / "Cronologia" / "Hechos.lean").write_text(
            fichero.texto, encoding="utf-8", newline="\n"
        )
        proceso = await asyncio.create_subprocess_exec(
            str(lake),
            "build",
            "Cronologia.Hechos",
            cwd=proyecto,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            salida_bytes, _ = await asyncio.wait_for(proceso.communicate(), timeout=timeout)
        except TimeoutError:
            proceso.kill()
            await proceso.wait()
            return resultado(
                "timeout",
                informe.fallo_total(
                    f"timeout: `lake build` no terminó en {timeout} s "
                    "(formal.lean_timeout_segundos)"
                ),
            )
        salida = salida_bytes.decode("utf-8", errors="replace")
        if proceso.returncode == 0:
            return resultado("demostrado", informe.veredictos(c, fichero, salida))
        if not informe.lineas_con_error(salida):
            return resultado(
                "error", informe.fallo_total(f"error: `lake build` falló: {salida[-800:]}")
            )
        veredictos = informe.veredictos(c, fichero, salida)
        return resultado("fallos", veredictos)
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
