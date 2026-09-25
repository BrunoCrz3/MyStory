"""Arranca el backend como proceso real para las pruebas de extremo a extremo."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx2

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto: int = s.getsockname()[1]
        return puerto


def entorno(db: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "LANGFUSE_"))}
    env["STORYMAKER_DB_PATH"] = str(db)
    env["STORYMAKER_E2E_DB_PATH"] = str(db)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


@contextmanager
def backend(
    env: dict[str, str], *, modulo: list[str] | None = None, espera_s: float = 30.0
) -> Iterator[tuple[str, subprocess.Popen[str]]]:
    """Lanza el backend y espera a que `/salud` responda. Lo mata al salir.

    La salida del proceso va a un fichero temporal y no a una tubería: una tubería que nadie
    lee se llena con los logs de acceso de un sondeo y bloquea al servidor al escribir.
    """
    puerto = puerto_libre()
    # `--sin-env`: la prueba construye su propio entorno y no carga el `.env` de la raíz.
    orden = [sys.executable, *(modulo or ["-m", "app", "--sin-env"]), "--port", str(puerto)]
    with tempfile.TemporaryFile() as registro:
        proceso = subprocess.Popen(
            orden,
            cwd=RAIZ_BACKEND,
            env=env,
            stdout=registro,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        base = f"http://127.0.0.1:{puerto}"
        try:
            limite = time.monotonic() + espera_s
            while True:
                if proceso.poll() is not None:
                    registro.seek(0)
                    salida = registro.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"el backend terminó al arrancar:\n{salida}")
                try:
                    if httpx2.get(f"{base}/salud", timeout=1).status_code == 200:
                        break
                except httpx2.HTTPError:
                    pass
                if time.monotonic() > limite:
                    raise TimeoutError("el backend no respondió a tiempo")
                time.sleep(0.2)
            yield base, proceso
        finally:
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait(timeout=10)
