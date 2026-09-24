"""Segunda implementación de `ClienteModelo`: el CLI de Claude Code como subproceso (I-04).

Aprobada por el desarrollador el 2026-09-24 porque no hay clave de la API: las llamadas usan
la sesión con la que ya se inició Claude Code en la máquina. Se elige con
`proveedor: claude_code` en `config/models.yaml` (TO-040).

**Contención, que es lo que no se negocia.** El texto de la novela lleva texto libre del
comprador, que es contenido no confiable (regla 11). El CLI es un agente capaz de leer,
escribir y ejecutar; aquí se le quita todo eso:

- `--tools ""`: ninguna herramienta integrada, ni ficheros, ni shell, ni red;
- `--strict-mcp-config` sin `--mcp-config`: ningún servidor MCP;
- `--safe-mode`, `--setting-sources ""` y `--disable-slash-commands`: ni hooks, ni skills,
  ni plugins, ni CLAUDE.md, ni permisos de los ficheros de configuración del usuario;
- `--permission-mode dontAsk` con `--permission-prompts none`: lo que pediría permiso se
  deniega sin preguntar a nadie;
- la carpeta de trabajo es una temporal **vacía**, nunca el repositorio, y se borra al
  terminar; el system va en un fichero de otra carpeta temporal;
- el texto de la petición viaja **solo por la entrada estándar**: ningún argumento contiene
  texto de la novela, así que nada de ella puede convertirse en una bandera;
- el entorno del subproceso no lleva las credenciales de Langfuse ni la configuración del
  sistema, y tampoco `ANTHROPIC_API_KEY`: este proveedor usa la sesión, no la clave;
- nunca se ejecuta el envoltorio `.cmd` de npm, cuyo paso por `cmd.exe` no escapa bien los
  argumentos: se resuelve el binario nativo o no se llama.

**Lo que cambia frente a la API** (docs/architecture.md § Proveedor del modelo): el recuento
previo es una estimación con margen, el coste es nominal y la salida estructurada se valida
después con Pydantic porque no hay modo estricto.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

import anyio
from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.llm.protocolo import (
    ErrorModelo,
    FalloInfraestructura,
    Peticion,
    Recuento,
    Respuesta,
    SalidaInvalida,
    SalidaTruncada,
)

VARIABLE_EJECUTABLE = "STORYMAKER_CLAUDE_CODE"
_NATIVO_NPM = Path("node_modules") / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
_REINTENTABLES = frozenset({408, 409, 429})
# Prefijos del entorno que el subproceso no necesita y no debe ver.
_ENTORNO_FUERA = ("LANGFUSE_", "STORYMAKER_", "ANTHROPIC_API_KEY")
# Lo que el CLI escribe cuando la salida llega a `CLAUDE_CODE_MAX_OUTPUT_TOKENS`.
_MARCA_TRUNCADO = "output token maximum"

CONTENCION: tuple[str, ...] = (
    "--tools",
    "",
    "--strict-mcp-config",
    "--safe-mode",
    "--setting-sources",
    "",
    "--disable-slash-commands",
    "--permission-mode",
    "dontAsk",
    "--permission-prompts",
    "none",
    "--no-session-persistence",
)


class ResultadoProceso(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: int
    salida: bytes
    errores: bytes


class Lanzador(Protocol):
    async def __call__(
        self, orden: Sequence[str], *, entrada: bytes, cwd: Path, env: Mapping[str, str]
    ) -> ResultadoProceso: ...


async def lanzar_proceso(
    orden: Sequence[str], *, entrada: bytes, cwd: Path, env: Mapping[str, str]
) -> ResultadoProceso:
    """El lanzador de producción: un proceso sin shell, con la entrada por stdin."""
    r = await anyio.run_process(list(orden), input=entrada, cwd=cwd, env=dict(env), check=False)
    return ResultadoProceso(codigo=r.returncode, salida=r.stdout, errores=r.stderr)


def resolver_ejecutable(
    entorno: Mapping[str, str], buscar: Callable[[str], str | None] = shutil.which
) -> Path:
    """El binario del CLI: el de `STORYMAKER_CLAUDE_CODE`, o el del PATH sin envoltorio .cmd."""
    explicito = entorno.get(VARIABLE_EJECUTABLE)
    if explicito:
        return Path(explicito)
    encontrado = buscar("claude")
    if encontrado is None:
        raise ErrorModelo(
            f"no se encuentra el CLI de Claude Code en el PATH ni en {VARIABLE_EJECUTABLE}"
        )
    ruta = Path(encontrado)
    if ruta.suffix.lower() in {".cmd", ".bat"}:
        nativo = ruta.parent / _NATIVO_NPM
        if not nativo.is_file():
            raise ErrorModelo(
                f"{ruta.name} es un envoltorio .cmd y no se ejecuta por cmd.exe; indica el "
                f"binario nativo en {VARIABLE_EJECUTABLE}"
            )
        return nativo
    return ruta


def _entorno_hijo(max_tokens: int) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_ENTORNO_FUERA)}
    # Tope de salida por llamada: el CLI no tiene `max_tokens` y sin esto usaría el del modelo.
    env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_tokens)
    return env


def _clasificar(datos: Mapping[str, Any]) -> ErrorModelo:
    mensaje = str(datos.get("result") or "")[:200]
    if _MARCA_TRUNCADO in mensaje:
        return SalidaTruncada(f"la respuesta llegó al tope de salida: {mensaje}")
    estado = datos.get("api_error_status")
    if isinstance(estado, int):
        if estado in _REINTENTABLES or estado >= 500:
            return FalloInfraestructura(f"el proveedor devolvió {estado}")
        return ErrorModelo(f"el proveedor rechazó la petición ({estado})")
    if datos.get("terminal_reason") == "api_error":
        return FalloInfraestructura(f"error de red o del proveedor: {mensaje}")
    return ErrorModelo(f"el CLI terminó con error: {mensaje}")


class ClienteClaudeCode:
    def __init__(
        self,
        config: Config,
        *,
        ejecutable: Path | None = None,
        lanzador: Lanzador = lanzar_proceso,
    ) -> None:
        self.config = config
        self.timeout_segundos = config.umbrales.orquestacion.timeout_llamada_segundos
        self._ejecutable = ejecutable
        self.lanzador = lanzador

    def _caracteres(self, peticion: Peticion) -> int:
        partes = [peticion.system, *(m.contenido for m in peticion.mensajes)]
        if peticion.esquema_salida is not None:
            partes.append(json.dumps(peticion.esquema_salida))
        return sum(len(p) for p in partes)

    async def contar_tokens(self, peticion: Peticion) -> Recuento:
        estimacion = self.config.umbrales.modelo.claude_code
        tokens = math.ceil(
            self._caracteres(peticion)
            / estimacion.caracteres_por_token
            * estimacion.margen_estimacion
        )
        return Recuento.de(
            peticion, tokens_entrada=tokens, max_tokens=self.config.max_tokens(peticion.rol)
        )

    def _orden(self, peticion: Peticion, fichero_system: Path) -> list[str]:
        if self._ejecutable is None:
            self._ejecutable = resolver_ejecutable(os.environ)
        rol = self.config.modelos.roles.de(peticion.rol)
        orden = [
            str(self._ejecutable),
            "-p",
            "--output-format",
            "json",
            "--model",
            rol.id,
            "--effort",
            rol.effort,
            "--system-prompt-file",
            str(fichero_system),
            *CONTENCION,
        ]
        if peticion.esquema_salida is not None:
            orden += ["--json-schema", json.dumps(peticion.esquema_salida, ensure_ascii=False)]
        return orden

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        if not recuento.corresponde_a(peticion):
            raise ValueError("el recuento no corresponde a esta petición: hay que contar antes")
        if len(peticion.mensajes) != 1 or peticion.mensajes[0].role != "user":
            raise ErrorModelo("el proveedor claude_code admite un solo mensaje de usuario")

        with (
            tempfile.TemporaryDirectory(prefix="storymaker-cc-") as trabajo,
            tempfile.TemporaryDirectory(prefix="storymaker-cc-system-") as entrada,
        ):
            fichero_system = Path(entrada) / "system.md"
            fichero_system.write_text(peticion.system, encoding="utf-8")
            orden = self._orden(peticion, fichero_system)
            inicio = time.monotonic()
            try:
                with anyio.fail_after(self.timeout_segundos):
                    resultado = await self.lanzador(
                        orden,
                        entrada=peticion.mensajes[0].contenido.encode("utf-8"),
                        cwd=Path(trabajo),
                        env=_entorno_hijo(recuento.max_tokens),
                    )
            except TimeoutError as e:
                raise FalloInfraestructura(
                    f"{peticion.rol}: timeout de {self.timeout_segundos} s del CLI"
                ) from e
            except OSError as e:
                raise ErrorModelo(f"no se pudo lanzar el CLI: {type(e).__name__}") from e
            latencia = time.monotonic() - inicio

        return self._respuesta(peticion, resultado, latencia)

    def _respuesta(
        self, peticion: Peticion, resultado: ResultadoProceso, latencia: float
    ) -> Respuesta:
        try:
            datos_cli: Any = json.loads(resultado.salida.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            raise FalloInfraestructura(
                f"{peticion.rol}: el CLI terminó con código {resultado.codigo} sin JSON"
            ) from e
        if not isinstance(datos_cli, dict):
            raise FalloInfraestructura(f"{peticion.rol}: salida del CLI inesperada")
        if datos_cli.get("is_error") or resultado.codigo != 0:
            raise _clasificar(datos_cli)
        if datos_cli.get("stop_reason") == "refusal":
            raise ErrorModelo(f"{peticion.rol}: el modelo rechazó la petición")

        texto = str(datos_cli.get("result") or "")
        datos: dict[str, Any] | None = None
        if peticion.esquema_salida is not None:
            estructurada = datos_cli.get("structured_output")
            if estructurada is None:
                try:
                    estructurada = json.loads(texto)
                except json.JSONDecodeError as e:
                    raise SalidaInvalida(f"{peticion.rol}: la salida no es JSON") from e
            if not isinstance(estructurada, dict):
                raise SalidaInvalida(f"{peticion.rol}: la salida no es un objeto JSON")
            datos = estructurada
            texto = json.dumps(estructurada, ensure_ascii=False)

        modelo = self.config.modelos.roles.de(peticion.rol).id
        uso: dict[str, Any] = datos_cli.get("usage") or {}
        entrada = sum(
            int(uso.get(k) or 0)
            for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        salida = int(uso.get("output_tokens") or 0)
        detalles = uso.get("output_tokens_details") or {}
        coste = datos_cli.get("total_cost_usd")
        return Respuesta(
            modelo=modelo,
            texto=texto,
            datos=datos,
            stop_reason=datos_cli.get("stop_reason"),
            tokens_entrada=entrada,
            tokens_salida=salida,
            tokens_razonamiento=detalles.get("thinking_tokens"),
            # Nominal: la sesión no se factura por llamada; es lo que costaría a precio de lista.
            coste_usd=float(coste)
            if isinstance(coste, int | float)
            else self.config.coste_usd(modelo, entrada, salida),
            latencia_s=latencia,
        )
