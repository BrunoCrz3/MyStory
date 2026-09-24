"""Proveedor `claude_code`: el CLI de Claude Code como subproceso, sin herramientas (I-04).

El subproceso es un doble (`tests/dobles/subproceso.py`) que guarda cómo se le llamó: se
prueba la orden, la entrada, la carpeta y el entorno que recibiría el CLI de verdad, y la
lectura de su salida JSON. La contención se comprueba con el corpus de inyección.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.commons.config import Config, ConfigInvalida, cargar_config
from app.commons.llm import (
    ClienteAnthropic,
    ClienteClaudeCode,
    ErrorModelo,
    FalloInfraestructura,
    Mensaje,
    Peticion,
    Recuento,
    SalidaInvalida,
    SalidaTruncada,
    crear_cliente,
)
from app.commons.llm.claude_code import ResultadoProceso, resolver_ejecutable
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.dobles.subproceso import LanzadorGuionizado, Llamada, resultado_cli
from tests.fixtures.inyecciones import CORPUS_INYECCION

CONFIG = cargar_config(RAIZ_REPO / "config")
EJECUTABLE = Path("C:/herramientas/claude/claude.exe")
ESQUEMA = {
    "type": "object",
    "properties": {"titulo": {"type": "string"}},
    "required": ["titulo"],
    "additionalProperties": False,
}

# Lo que convierte al CLI en un agente capaz de actuar sobre la máquina. Nada de esto puede
# aparecer en la orden, pase lo que pase en el texto de la novela.
BANDERAS_PROHIBIDAS = (
    "--allowedTools",
    "--allowed-tools",
    "--add-dir",
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "--mcp-config",
    "--plugin-dir",
    "--plugin-url",
    "--settings",
    "--agents",
    "--agent",
    "--chrome",
    "--continue",
    "--resume",
)


def _peticion(
    contenido: str = "Planifica.", *, esquema: dict[str, Any] | None = ESQUEMA
) -> Peticion:
    return Peticion(
        rol="planificador",
        system="Eres el planificador.",
        mensajes=[Mensaje(role="user", contenido=contenido)],
        esquema_salida=esquema,
        prompt="planner",
        hash_prompt="abc123",
    )


def _cliente(
    *respuestas: Any, config: Config = CONFIG, retardo_s: float = 0.0
) -> tuple[ClienteClaudeCode, LanzadorGuionizado]:
    lanzador = LanzadorGuionizado(respuestas=list(respuestas), retardo_s=retardo_s)
    return ClienteClaudeCode(config, ejecutable=EJECUTABLE, lanzador=lanzador), lanzador


async def _generar(cliente: ClienteClaudeCode, peticion: Peticion | None = None) -> Any:
    peticion = peticion or _peticion()
    return await cliente.generar(peticion, await cliente.contar_tokens(peticion))


def _valor(orden: list[str], bandera: str) -> str:
    return orden[orden.index(bandera) + 1]


@pytest.mark.anyio
async def test_contar_estima_con_margen_y_no_lanza_el_proceso() -> None:
    cliente, lanzador = _cliente()
    peticion = _peticion()
    recuento = await cliente.contar_tokens(peticion)

    cc = CONFIG.umbrales.modelo.claude_code
    caracteres = len(peticion.system) + len("Planifica.") + len(json.dumps(ESQUEMA))
    assert recuento.tokens_entrada == math.ceil(
        caracteres / cc.caracteres_por_token * cc.margen_estimacion
    )
    assert recuento.max_tokens == CONFIG.max_tokens("planificador")
    assert recuento.corresponde_a(peticion)
    assert lanzador.llamadas == []


@pytest.mark.anyio
async def test_generar_usa_modelo_effort_y_esquema_del_rol_y_lee_el_uso() -> None:
    salida = {"titulo": "El verano del Alondra"}
    cliente, lanzador = _cliente(resultado_cli(result="", structured_output=salida))
    respuesta = await _generar(cliente)

    [llamada] = lanzador.llamadas
    rol = CONFIG.modelos.roles.planificador
    assert llamada.orden[0] == str(EJECUTABLE)
    assert "-p" in llamada.orden
    assert _valor(llamada.orden, "--output-format") == "json"
    assert _valor(llamada.orden, "--model") == rol.id
    assert _valor(llamada.orden, "--effort") == rol.effort
    assert json.loads(_valor(llamada.orden, "--json-schema")) == ESQUEMA
    system = _valor(llamada.orden, "--system-prompt-file")
    assert llamada.ficheros_orden[system] == "Eres el planificador."
    assert llamada.entrada.decode("utf-8") == "Planifica."
    assert llamada.env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == str(CONFIG.max_tokens("planificador"))

    assert respuesta.datos == salida
    assert json.loads(respuesta.texto) == salida
    assert respuesta.modelo == rol.id
    assert respuesta.tokens_entrada == 10 + 2600
    assert respuesta.tokens_salida == 500
    assert respuesta.tokens_razonamiento == 120
    assert respuesta.coste_usd == 0.05


@pytest.mark.anyio
async def test_sin_esquema_devuelve_el_texto_y_no_pide_salida_estructurada() -> None:
    cliente, lanzador = _cliente(resultado_cli(result="Érase una vez."))
    respuesta = await _generar(cliente, _peticion(esquema=None))
    assert respuesta.texto == "Érase una vez." and respuesta.datos is None
    assert "--json-schema" not in lanzador.llamadas[0].orden


@pytest.mark.anyio
async def test_sin_coste_del_cli_se_usa_el_precio_de_config() -> None:
    cliente, _ = _cliente(resultado_cli(result="x", coste=None))
    respuesta = await _generar(cliente, _peticion(esquema=None))
    modelo = CONFIG.modelos.roles.planificador.id
    assert respuesta.coste_usd == CONFIG.coste_usd(modelo, 2610, 500)


@pytest.mark.anyio
@pytest.mark.parametrize("inyeccion", CORPUS_INYECCION)
async def test_el_texto_no_confiable_no_puede_dar_herramientas_ni_banderas(
    inyeccion: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "secreto-de-prueba")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    contenido = f"<texto_libre_no_confiable>{inyeccion}</texto_libre_no_confiable>"
    cliente, lanzador = _cliente(resultado_cli(structured_output={"titulo": "x"}))
    await _generar(cliente, _peticion(contenido))

    [llamada] = lanzador.llamadas
    orden = llamada.orden
    # Sin herramientas, sin MCP, sin personalizaciones, sin permisos y sin sesión.
    assert _valor(orden, "--tools") == ""
    assert _valor(orden, "--setting-sources") == ""
    assert _valor(orden, "--permission-mode") == "dontAsk"
    assert _valor(orden, "--permission-prompts") == "none"
    for bandera in (
        "--strict-mcp-config",
        "--safe-mode",
        "--disable-slash-commands",
        "--no-session-persistence",
    ):
        assert bandera in orden
    assert not any(a.split("=")[0] in BANDERAS_PROHIBIDAS for a in orden)
    # El texto no confiable solo viaja por la entrada estándar, nunca como argumento.
    assert all(inyeccion.strip() not in a for a in orden)
    assert inyeccion in llamada.entrada.decode("utf-8")
    # Carpeta de trabajo temporal, vacía, fuera del repositorio, y borrada al terminar.
    assert llamada.contenido_cwd == []
    assert RAIZ_REPO not in llamada.cwd.parents and llamada.cwd != RAIZ_REPO
    assert not llamada.cwd.exists()
    # Ni credenciales ni configuración del sistema en el entorno del subproceso.
    assert not any(k.startswith(("LANGFUSE_", "STORYMAKER_")) for k in llamada.env)
    assert "ANTHROPIC_API_KEY" not in llamada.env


def _codigo_raro(_: Llamada) -> ResultadoProceso:
    return ResultadoProceso(codigo=2, salida=b"no es json", errores=b"fallo")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("respuesta", "error"),
    [
        (
            resultado_cli(
                is_error=True,
                terminal_reason="api_error",
                result="API Error: Claude's response exceeded the 6000 output token maximum.",
            ),
            SalidaTruncada,
        ),
        (
            resultado_cli(is_error=True, api_error_status=529, result="Overloaded"),
            FalloInfraestructura,
        ),
        (resultado_cli(is_error=True, api_error_status=429, result="Rate"), FalloInfraestructura),
        (
            resultado_cli(is_error=True, terminal_reason="api_error", result="Connection error"),
            FalloInfraestructura,
        ),
        (resultado_cli(is_error=True, api_error_status=400, result="Bad"), ErrorModelo),
        (resultado_cli(stop_reason="refusal", result=""), ErrorModelo),
        (resultado_cli(result="no es json"), SalidaInvalida),
        (resultado_cli(result="[1, 2]"), SalidaInvalida),
        (_codigo_raro, FalloInfraestructura),
    ],
)
async def test_clasifica_los_fallos_del_cli(respuesta: Any, error: type[Exception]) -> None:
    cliente, _ = _cliente(respuesta)
    with pytest.raises(error) as info:
        await _generar(cliente)
    if error is ErrorModelo:
        assert type(info.value) is ErrorModelo


@pytest.mark.anyio
async def test_un_proceso_que_no_termina_a_tiempo_es_fallo_de_infraestructura() -> None:
    orquestacion = CONFIG.umbrales.orquestacion.model_copy(
        update={"timeout_llamada_segundos": 0.05}
    )
    config = CONFIG.model_copy(
        update={"umbrales": CONFIG.umbrales.model_copy(update={"orquestacion": orquestacion})}
    )
    cliente, _ = _cliente(config=config, retardo_s=1.0)
    with pytest.raises(FalloInfraestructura, match="timeout"):
        await _generar(cliente)


@pytest.mark.anyio
async def test_un_recuento_ajeno_o_varios_mensajes_se_rechazan() -> None:
    cliente, lanzador = _cliente()
    otra = _peticion("Otra cosa.")
    with pytest.raises(ValueError, match="recuento"):
        await cliente.generar(_peticion(), await cliente.contar_tokens(otra))
    varios = Peticion(
        rol="planificador",
        system="s",
        mensajes=[Mensaje(role="user", contenido="a"), Mensaje(role="assistant", contenido="b")],
        prompt="p",
        hash_prompt="h",
    )
    recuento = Recuento.de(varios, tokens_entrada=1, max_tokens=10)
    with pytest.raises(ErrorModelo, match="un solo mensaje"):
        await cliente.generar(varios, recuento)
    assert lanzador.llamadas == []


def test_resolver_ejecutable(tmp_path: Path) -> None:
    exe = tmp_path / "otro" / "claude.exe"
    exe.parent.mkdir()
    exe.write_text("")
    assert resolver_ejecutable({"STORYMAKER_CLAUDE_CODE": str(exe)}, lambda _: None) == exe

    # Un envoltorio .cmd de npm nunca se ejecuta: se usa el binario nativo que envuelve.
    shim = tmp_path / "npm" / "claude.CMD"
    nativo = tmp_path / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin"
    nativo.mkdir(parents=True)
    shim.write_text("")
    (nativo / "claude.exe").write_text("")
    assert resolver_ejecutable({}, lambda _: str(shim)) == nativo / "claude.exe"

    (nativo / "claude.exe").unlink()
    with pytest.raises(ErrorModelo, match="cmd"):
        resolver_ejecutable({}, lambda _: str(shim))
    with pytest.raises(ErrorModelo, match="no se encuentra"):
        resolver_ejecutable({}, lambda _: None)


def test_crear_cliente_elige_por_proveedor() -> None:
    api = CONFIG.model_copy(
        update={"modelos": CONFIG.modelos.model_copy(update={"proveedor": "api"})}
    )
    cc = CONFIG.model_copy(
        update={"modelos": CONFIG.modelos.model_copy(update={"proveedor": "claude_code"})}
    )
    assert isinstance(crear_cliente(api), ClienteAnthropic)
    assert isinstance(crear_cliente(cc), ClienteClaudeCode)


def test_un_proveedor_desconocido_no_arranca(tmp_path: Path) -> None:
    destino = tmp_path / "config"
    shutil.copytree(RAIZ_REPO / "config", destino)
    modelos = yaml.safe_load((destino / "models.yaml").read_text(encoding="utf-8"))
    modelos["proveedor"] = "otro"
    (destino / "models.yaml").write_text(yaml.safe_dump(modelos), encoding="utf-8")
    with pytest.raises(ConfigInvalida, match="proveedor"):
        cargar_config(destino)


def test_la_config_real_declara_un_proveedor_valido() -> None:
    assert CONFIG.modelos.proveedor in ("api", "claude_code")
