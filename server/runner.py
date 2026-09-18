"""El unico fichero del sistema que sabe como se invoca Claude Code.

Todo lo demas -el orquestador, la API, el frontend- pide texto a este modulo y
no tiene ni idea de que por debajo hay un `claude -p`. Si manana cambia la
forma de llamar al modelo, cambia este fichero y nada mas.

LAS CUATRO REGLAS, medidas por el autor y comprobadas aqui:

  1. `--output-format json` SIEMPRE. El coste, los cuatro contadores de token y
     el id de sesion se LEEN de la respuesta. No hay tabla de tarifas en este
     repositorio y no la va a haber: inventar el coste es peor que no darlo.
  2. `--restricted` SIEMPRE. Baja el contexto de arranque casi a la mitad y
     conserva las herramientas de leer y escribir, que es todo lo que necesitan
     los roles creativos. Los scripts deterministas los ejecuta el orquestador,
     no el modelo, asi que perder Bash no quita nada.
  3. NUNCA `--bare`. Exige ANTHROPIC_API_KEY y rompe la autenticacion por
     sesion del autor: ya fallo una vez con "Not logged in".
  4. Sesiones encadenadas. Se guarda el session_id de cada invocacion y la
     siguiente del mismo rol se reanuda con el. Medido en esta maquina:

         primera llamada  24.223 tokens de contexto creados, 0 leidos, 0,0513 USD
         reanudada           251 creados,          24.223 leidos, 0,0031 USD

     Dieciseis veces mas barato. La cache dura una hora, y de ahi que una
     novela deba generarse del tiron.

DOS COSAS MAS QUE HACEN FALTA EN WINDOWS:

  - El prompt viaja por stdin, no como argumento. La linea de comandos de
    Windows se corta en 32.767 caracteres y el contexto de un capitulo la
    revienta sin avisar.
  - `--restricted` ignora los ficheros de ajustes del proyecto, asi que
    `--agent escritor` NO encuentra a los subagentes de `.claude/agents/`.
    Comprobado: "not found. Available agents: claude, ...". Por eso el prompt
    del rol se lee de ese mismo fichero y se pasa con `--append-system-prompt`.
    La definicion del rol sigue viviendo en un unico sitio, que es lo que
    importa: el camino conversacional y el orquestado leen el mismo texto.

Este modulo no lanza excepciones hacia arriba y no lee variables de entorno:
el subproceso hereda el entorno tal cual, que es como la sesion de Claude Code
se autentica sola.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import nucleo  # noqa: E402  (despues de fijar la ruta)

# Roles que existen como subagente en .claude/agents/. El orquestador no puede
# pedir otra cosa.
ROLES = ("arquitecto", "escaletista", "escritor", "continuista",
         "estilista", "archivista", "revisor-global")

# Potente donde se escribe o se juzga prosa; pequeno donde se extraen datos.
# Se puede cambiar en config.json -> servidor.modelos.
MODELOS_POR_DEFECTO = {
    "arquitecto": "opus",
    "escaletista": "opus",
    "escritor": "opus",
    "estilista": "opus",
    "revisor-global": "opus",
    "continuista": "haiku",
    "archivista": "haiku",
}

MAX_INVOCACIONES_POR_DEFECTO = 120   # corta un bucle, no un presupuesto
ESPERA_MAXIMA_S = 900          # 15 minutos por invocacion
_FRONTMATTER = re.compile(r"^---.*?---\s*", re.S)


# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------

def _servidor(cfg: dict) -> dict:
    bloque = cfg.get("servidor")
    return bloque if isinstance(bloque, dict) else {}


def modelo_de(rol: str, cfg: dict) -> str:
    """Que modelo usa un rol. Configurable, con un valor razonable si falta."""
    modelos = _servidor(cfg).get("modelos")
    if isinstance(modelos, dict) and modelos.get(rol):
        return str(modelos[rol])
    return MODELOS_POR_DEFECTO.get(rol, "opus")


def max_invocaciones(cfg: dict) -> int:
    """Cuantas llamadas al modelo puede hacer una novela entera.

    No es un presupuesto: es el cortacircuitos que impide que un bucle de
    reintentos se quede llamando al modelo para siempre. El coste se sigue
    midiendo y registrando, pero no detiene nada.
    """
    try:
        valor = int(_servidor(cfg).get("max_invocaciones",
                                       MAX_INVOCACIONES_POR_DEFECTO))
    except (TypeError, ValueError):
        return MAX_INVOCACIONES_POR_DEFECTO
    return valor if valor > 0 else MAX_INVOCACIONES_POR_DEFECTO


def espera_maxima(cfg: dict) -> int:
    try:
        valor = int(_servidor(cfg).get("espera_maxima_s", ESPERA_MAXIMA_S))
    except (TypeError, ValueError):
        return ESPERA_MAXIMA_S
    return valor if valor > 0 else ESPERA_MAXIMA_S


def prompt_de_rol(rol: str) -> str:
    """El prompt del subagente, sin su frontmatter.

    Se lee de .claude/agents/<rol>.md, que es la misma definicion que usa el
    camino conversacional. Ni se copia ni se reescribe aqui.
    """
    ruta = RAIZ / ".claude" / "agents" / f"{rol}.md"
    if not ruta.exists():
        return ""
    return _FRONTMATTER.sub("", ruta.read_text(encoding="utf-8"), count=1).strip()


def ejecutable() -> str | None:
    """Ruta del binario de Claude Code, o None si no esta en el PATH."""
    return shutil.which("claude")


# --------------------------------------------------------------------------
# La invocacion
# --------------------------------------------------------------------------

def _vacio() -> dict:
    return {"input_tokens": 0, "output_tokens": 0,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


def _tokens(respuesta: dict) -> dict:
    uso = respuesta.get("usage") or {}
    salida = _vacio()
    for clave in salida:
        try:
            salida[clave] = int(uso.get(clave) or 0)
        except (TypeError, ValueError):
            pass
    return salida


def _fallo(rol, modelo, motivo, inicio, sesion=None, respuesta=None) -> dict:
    """Un resultado fallido, CON lo que la llamada haya costado ya.

    Hay dos clases de fallo y confundirlas sale caro. Si se rompe antes de
    llegar al modelo -no esta el binario, no hay saldo, no arranca- no se ha
    gastado nada y el coste es cero de verdad. Pero si Claude Code contesto y
    lo que falla es lo que contesto -is_error, o una herramienta denegada-, el
    trabajo ya esta hecho y facturado: devolver cero ahi es mentir.

    Y la mentira no se queda en el informe. El orquestador solo escribe el
    evento `invocacion` si hay coste o hay exito, el tope de gasto se calcula
    sumando esos eventos, y la pantalla de coste tambien. Un fallo caro que se
    declara gratis desaparece de las tres cosas a la vez, y una tirada que
    falle varias veces se puede comer el tope sin que nadie lo vea venir.
    """
    tokens = _tokens(respuesta) if respuesta else _vacio()
    coste = 0.0
    if respuesta:
        try:
            coste = float(respuesta.get("total_cost_usd") or 0.0)
        except (TypeError, ValueError):
            coste = 0.0
    return {"ok": False, "texto": "", "rol": rol, "modelo": modelo,
            "session_id": sesion, "coste_usd": coste, "tokens": tokens,
            "cache_aprovechada": tokens["cache_read_input_tokens"] > 0,
            "duracion_s": round(time.monotonic() - inicio, 1), "error": motivo}


def invocar(rol: str, prompt: str, cfg: dict = None,
            sesion: str = None) -> dict:
    """Una llamada a Claude Code con el prompt de un rol. No lanza nunca.

    `sesion` es el session_id devuelto por la llamada anterior de ESTE rol: si
    se pasa, se reanuda y la cache se reaprovecha. Quien lleva la cuenta de
    cuantas llamadas van es el orquestador: aqui no hay tope de ninguna clase.

    Devuelve siempre el mismo diccionario, con ok=False y `error` cuando algo
    sale mal. Quien llama decide si para o reintenta; este modulo no decide.
    """
    inicio = time.monotonic()
    cfg = cfg if cfg is not None else nucleo.cargar_config()
    modelo = modelo_de(rol, cfg)

    if rol not in ROLES:
        return _fallo(rol, modelo, f"rol desconocido: {rol}", inicio)

    binario = ejecutable()
    if not binario:
        return _fallo(rol, modelo,
                      "no se encuentra el ejecutable 'claude' en el PATH",
                      inicio)

    sistema = prompt_de_rol(rol)
    if not sistema:
        return _fallo(rol, modelo,
                      f"no existe .claude/agents/{rol}.md o esta vacio", inicio)

    # EL ORDEN IMPORTA, y se paga caro equivocarse. En Windows `claude` es un
    # shim .CMD que reenvia sus argumentos a traves de cmd.exe, y un argumento
    # multilinea -el prompt del rol lo es- rompe la lista: TODO lo que vaya
    # detras se pierde o se corrompe, sin aviso ni error. Medido:
    #
    #   --model haiku ANTES del prompt de sistema  -> usa haiku
    #   --model haiku DESPUES                      -> usa haiku Y opus
    #   --resume <id> DESPUES                      -> se ignora, sesion nueva
    #
    # Es decir: el fallo silencioso te cambia de modelo y te tira la cache a
    # la basura, y la factura lo nota antes que tu. Por eso
    # --append-system-prompt va SIEMPRE el ultimo, y nada va detras.
    orden = [binario, "--print",
             "--output-format", "json",
             "--restricted",                      # regla 2
             "--model", modelo,
             "--permission-mode", "acceptEdits"]  # escribe sin preguntar
    if sesion:
        orden += ["--resume", sesion]             # regla 4
    orden += ["--append-system-prompt", sistema]  # SIEMPRE el ultimo

    try:
        completado = subprocess.run(
            orden, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(RAIZ),
            timeout=espera_maxima(cfg))
    except subprocess.TimeoutExpired:
        return _fallo(rol, modelo,
                      f"la invocacion ha pasado de {espera_maxima(cfg)} s",
                      inicio, sesion)
    except OSError as exc:
        return _fallo(rol, modelo, f"no se ha podido ejecutar claude: {exc}",
                      inicio, sesion)

    crudo = (completado.stdout or "").strip()
    if not crudo:
        detalle = (completado.stderr or "").strip()[:300] or "sin salida"
        return _fallo(rol, modelo, f"claude no ha devuelto nada: {detalle}",
                      inicio, sesion)

    try:
        respuesta = json.loads(crudo)
    except json.JSONDecodeError:
        # Pasa cuando claude escribe un aviso antes del JSON, o cuando falla
        # de una forma que no contemplaba: el texto crudo es el diagnostico.
        return _fallo(rol, modelo,
                      f"la respuesta no es JSON: {crudo[:300]}", inicio, sesion)

    if respuesta.get("is_error"):
        return _fallo(rol, modelo,
                      str(respuesta.get("result") or "claude ha devuelto error")[:300],
                      inicio, respuesta.get("session_id") or sesion, respuesta)

    # Una herramienta denegada NO marca is_error: la llamada sale con exito y
    # el modelo te cuenta tan tranquilo lo que ha hecho, salvo la parte que no
    # pudo hacer. Medido: sin --permission-mode, el Write del capitulo queda
    # denegado, is_error es false y el fichero no existe. En una generacion
    # desatendida eso es lo peor que puede pasar, porque el orquestador sigue
    # adelante creyendo que hay capitulo. Aqui se convierte en fallo.
    denegados = respuesta.get("permission_denials") or []
    if denegados:
        herramientas = ", ".join(sorted({str(d.get("tool_name") or "?")
                                         for d in denegados}))
        return _fallo(rol, modelo,
                      f"la llamada no pudo usar {herramientas}: hacia falta "
                      f"aprobacion humana y esto corre solo",
                      inicio, respuesta.get("session_id") or sesion, respuesta)

    tokens = _tokens(respuesta)
    try:
        coste = float(respuesta.get("total_cost_usd") or 0.0)   # regla 1
    except (TypeError, ValueError):
        coste = 0.0

    return {
        "ok": True,
        "texto": respuesta.get("result") or "",
        "rol": rol,
        "modelo": modelo,
        "session_id": respuesta.get("session_id") or sesion,
        "coste_usd": coste,
        "tokens": tokens,
        # Sirve para la pantalla de coste: separa el arranque en frio del
        # trabajo real sin tener que adivinarlo despues.
        "cache_aprovechada": tokens["cache_read_input_tokens"] > 0,
        "duracion_s": round(time.monotonic() - inicio, 1),
        "error": None,
    }


# --------------------------------------------------------------------------
# Prueba de que esto funciona
# --------------------------------------------------------------------------

def _linea(titulo, r):
    print(f"  {titulo}")
    print(f"    texto       : {r['texto'][:70]!r}")
    print(f"    session_id  : {r['session_id']}")
    print(f"    modelo      : {r['modelo']}")
    print(f"    coste USD   : {r['coste_usd']:.6f}")
    t = r["tokens"]
    print(f"    tokens      : entrada {t['input_tokens']}, salida "
          f"{t['output_tokens']}, contexto creado "
          f"{t['cache_creation_input_tokens']}, leido de cache "
          f"{t['cache_read_input_tokens']}")
    print(f"    cache       : {'aprovechada' if r['cache_aprovechada'] else 'fria'}")
    print(f"    duracion    : {r['duracion_s']} s")
    if r["error"]:
        print(f"    ERROR       : {r['error']}")


def probar() -> int:
    """Tres invocaciones que demuestran las cuatro reglas."""
    cfg = nucleo.cargar_config()
    print(f"ejecutable    : {ejecutable()}")
    print(f"maximo de llamadas: {max_invocaciones(cfg)} por novela")
    print(f"modelos       : " + ", ".join(
        f"{r}={modelo_de(r, cfg)}" for r in ROLES))
    print()

    print("1) primera invocacion de un rol, cache fria")
    uno = invocar("continuista",
                  "No leas ningun fichero. Responde en una sola linea: "
                  "que rol tienes asignado.", cfg)
    _linea("resultado:", uno)
    if not uno["ok"]:
        return 1

    print()
    print("2) misma sesion reanudada: la cache debe leerse, no crearse")
    dos = invocar("continuista", "Responde solo con el numero 2.", cfg,
                  sesion=uno["session_id"])
    _linea("resultado:", dos)
    if not dos["ok"]:
        return 1

    print()
    print("3) un rol que escribe: se comprueba que Write funciona bajo --restricted")
    testigo = RAIZ / "novela" / "prueba-runner.txt"
    tres = invocar("escritor",
                   "Escribe el fichero novela/prueba-runner.txt con exactamente "
                   "una linea de texto: funciona. No escribas nada mas y no "
                   "toques ningun otro fichero.", cfg)
    _linea("resultado:", tres)
    escrito = testigo.exists()
    print(f"    fichero escrito: {escrito}")
    if escrito:
        print(f"    contenido      : {testigo.read_text(encoding='utf-8').strip()[:60]!r}")
        testigo.unlink()
        print("    (borrado: era solo la prueba)")

    print()
    ahorro = 0.0
    if uno["coste_usd"] > 0:
        ahorro = uno["coste_usd"] / max(dos["coste_usd"], 1e-9)
    print(f"RESUMEN: coste total de la prueba "
          f"{uno['coste_usd'] + dos['coste_usd'] + tres['coste_usd']:.4f} USD. "
          f"Reanudar salio {ahorro:.0f} veces mas barato que arrancar en frio.")
    return 0 if (uno["ok"] and dos["ok"] and tres["ok"] and escrito) else 1


def main():
    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="Unico punto de invocacion de Claude Code. Ejecutado a "
                    "mano solo sirve para probar que la invocacion funciona.")
    parser.add_argument("--probar", action="store_true",
                        help="Hace tres invocaciones reales y ensena el texto, "
                             "los tokens, el coste y el id de sesion.")
    args = parser.parse_args()
    if not args.probar:
        parser.print_help()
        raise SystemExit(0)
    raise SystemExit(probar())


if __name__ == "__main__":
    main()
