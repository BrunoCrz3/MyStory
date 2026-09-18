"""Sube a Langfuse una tirada ya ejecutada, sin volver a generar nada.

Tres fuentes, en este orden:

  1. novela/events.jsonl, que es la fuente local de verdad. De ahi salen la
     traza, las fases, los capitulos, los intentos y los scores tal como se
     midieron en su momento.
  2. Los informes actuales de novela/informes/, para que los capitulos ya
     escritos tengan tambien las metricas que se anadieron despues de
     generarlos (monotonia, diversidad, cobertura de beats).
  3. Los transcripts de Claude Code, que son el UNICO sitio donde existe el
     desglose de tokens por invocacion. De ahi salen las generaciones: rol del
     subagente, modelo y los cuatro tipos de token.

Sobre el coste. Los transcripts NO guardan total_cost_usd, asi que este script
no lo inventa: envia el modelo y los cuatro contadores de token y deja que
Langfuse aplique su tarifa. Por eso una invocacion con la cache caliente sale
muy por debajo de la primera: la diferencia esta en los contadores reales, no
en una estimacion. Si algun dia una invocacion trae su coste, el campo
total_cost_usd del evento manda sobre el calculo.

Este script NO escribe en novela/events.jsonl. Los transcripts son una fuente
externa, y el registro local debe seguir contando solo lo que hizo el pipeline.
Reejecutarlo es inocuo: los identificadores son deterministas y la ingesta de
Langfuse hace upsert.

Python 3.12, solo biblioteca estandar.
"""

import argparse
import json
import pathlib
import re
from collections import Counter

import nucleo
import observabilidad as ob

# Un capitulo en la descripcion del subagente: "Borrador del capitulo 2".
_CAPITULO = re.compile(r"cap[ií]tulos?\s*0*(\d+)", re.IGNORECASE)


# --------------------------------------------------------------------------
# Localizacion de los transcripts de Claude Code
# --------------------------------------------------------------------------

def carpeta_transcripts(ruta: str = None):
    """Carpeta de transcripts de este proyecto, o None si no se encuentra.

    Claude Code guarda cada proyecto en ~/.claude/projects/<slug>, donde el
    slug es la ruta absoluta con los separadores convertidos en guiones.
    """
    if ruta:
        elegida = pathlib.Path(ruta).expanduser()
        return elegida if elegida.is_dir() else None
    base = pathlib.Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    slug = re.sub(r"[:\\/]", "-", str(nucleo.raiz()))
    for candidata in base.iterdir():
        if candidata.is_dir() and candidata.name.lower() == slug.lower():
            return candidata
    return None


def _invocaciones_de(fichero: pathlib.Path, rol: str, descripcion: str) -> list:
    """Una entrada por mensaje del modelo con uso declarado.

    Se emite una generacion por llamada real, no una por subagente: es lo que
    deja ver que la primera llamada crea la cache y las siguientes la leen.
    """
    salida = []
    try:
        texto = fichero.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return salida
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            fila = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if fila.get("type") != "assistant":
            continue
        mensaje = fila.get("message") or {}
        uso = mensaje.get("usage") or {}
        if not uso:
            continue
        salida.append({
            "ts": fila.get("timestamp"),
            "rol": rol,
            "descripcion": descripcion,
            "model": mensaje.get("model"),
            "session_id": fila.get("sessionId"),
            "id_generacion": fila.get("requestId") or fila.get("uuid"),
            "usage": {
                "input_tokens": uso.get("input_tokens") or 0,
                "output_tokens": uso.get("output_tokens") or 0,
                "cache_creation_input_tokens":
                    uso.get("cache_creation_input_tokens") or 0,
                "cache_read_input_tokens":
                    uso.get("cache_read_input_tokens") or 0,
            },
        })
    return salida


def leer_invocaciones(carpeta: pathlib.Path) -> list:
    """Todas las llamadas al modelo de todos los subagentes del proyecto.

    El rol sale de <agente>.meta.json, que es donde Claude Code guarda el
    agentType: escritor, continuista, estilista, archivista, arquitecto,
    escaletista o revisor-global.
    """
    if carpeta is None:
        return []
    invocaciones = []
    for meta in sorted(carpeta.glob("*/subagents/*.meta.json")):
        try:
            datos = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        transcript = meta.with_name(meta.name.replace(".meta.json", ".jsonl"))
        if not transcript.exists():
            continue
        invocaciones.extend(_invocaciones_de(
            transcript,
            datos.get("agentType") or "modelo",
            datos.get("description") or ""))
    return sorted(invocaciones, key=lambda i: i["ts"] or "")


# --------------------------------------------------------------------------
# Situar cada invocacion en el punto del pipeline donde ocurrio
# --------------------------------------------------------------------------

def _contextos(eventos: list) -> list:
    """Linea de tiempo (ts, tirada, fase, capitulo, intento) del pipeline.

    Una invocacion pertenece al ultimo punto del pipeline anterior a ella. Es
    la unica correlacion posible: los transcripts no guardan el numero de
    intento, pero si la hora, y el registro local dice que se estaba haciendo
    a esa hora.
    """
    linea = []
    fase = capitulo = intento = None
    for ev in sorted(eventos, key=lambda e: e.get("ts") or ""):
        tipo = ev.get("evento")
        if tipo == "fase_inicio":
            fase, capitulo, intento = ev.get("fase"), None, None
        elif tipo == "fase_fin":
            fase, capitulo, intento = ev.get("fase"), None, None
        elif tipo == "capitulo_inicio":
            fase, capitulo, intento = "redaccion", ev.get("capitulo"), None
        elif tipo in ob.EVENTOS_DE_INTENTO:
            fase, capitulo, intento = ("redaccion", ev.get("capitulo"),
                                       ev.get("intento"))
        elif tipo == "capitulo_fin":
            fase, capitulo, intento = ("redaccion", ev.get("capitulo"),
                                       ev.get("intento"))
        linea.append({"ts": ev.get("ts"), "tirada": ev.get("tirada"),
                      "fase": fase, "capitulo": capitulo, "intento": intento})
    return linea


def _situar(linea: list, invocacion: dict) -> dict:
    """Contexto vigente en el momento de la invocacion."""
    marca = invocacion.get("ts") or ""
    vigente = None
    for punto in linea:
        if (punto["ts"] or "") <= marca:
            vigente = punto
        else:
            break
    if vigente is None:
        return {}
    contexto = dict(vigente)
    # La descripcion del subagente manda sobre la hora si nombra un capitulo:
    # es un dato explicito y la correlacion temporal solo una inferencia.
    encontrado = _CAPITULO.search(invocacion.get("descripcion") or "")
    if encontrado:
        contexto["capitulo"] = int(encontrado.group(1))
        contexto["fase"] = contexto["fase"] or "redaccion"
    return contexto


def _intento_siguiente(eventos: list, capitulo, marca: str):
    """Numero del proximo intento de ese capitulo a partir de esa hora.

    El escritor produce el borrador ANTES de que se registre el evento
    'borrador': sus llamadas caen en el hueco entre capitulo_inicio y el
    intento que ellas mismas generan. Mirar hacia delante las devuelve al
    intento al que de verdad pertenecen, que es lo que permite ver de un
    vistazo cuantas reescrituras necesito cada capitulo.
    """
    candidatos = [e for e in eventos
                  if e.get("evento") in ob.EVENTOS_DE_INTENTO
                  and e.get("capitulo") == capitulo
                  and (e.get("ts") or "") >= (marca or "")]
    if not candidatos:
        return None
    return min(candidatos, key=lambda e: e.get("ts") or "").get("intento")


def eventos_de_invocacion(eventos: list, invocaciones: list) -> list:
    """Convierte cada llamada al modelo en un evento 'invocacion' del esquema."""
    linea = _contextos(eventos)
    salida = []
    for inv in invocaciones:
        contexto = _situar(linea, inv)
        if not contexto.get("tirada"):
            continue
        if (contexto.get("capitulo") is not None
                and contexto.get("intento") is None):
            contexto["intento"] = _intento_siguiente(
                eventos, contexto["capitulo"], inv.get("ts"))
        salida.append({
            "ts": inv["ts"],
            "tirada": contexto["tirada"],
            "evento": "invocacion",
            "fase": contexto.get("fase"),
            "capitulo": contexto.get("capitulo"),
            "intento": contexto.get("intento"),
            "datos": {
                "rol": inv["rol"],
                "model": inv["model"],
                "session_id": inv["session_id"],
                "id_generacion": inv["id_generacion"],
                "usage": inv["usage"],
            },
            "esquema": 1,
        })
    return salida


# --------------------------------------------------------------------------
# Metricas actuales de los capitulos ya escritos
# --------------------------------------------------------------------------

def eventos_de_metricas(cfg: dict, eventos: list) -> list:
    """Un evento 'validacion' sintetico por capitulo con las metricas de hoy.

    Los capitulos escritos antes de que existieran monotonia, diversidad y
    cobertura de beats no tienen esos scores en su historico. Se recalculan
    desde los scripts para que el panel los muestre igualmente.
    """
    try:
        import informes
    except ImportError:
        return []
    estado = nucleo.cargar_estado()
    # El capitulo se atribuye a la tirada que lo cerro.
    tiradas = {}
    for ev in eventos:
        if ev.get("evento") == "capitulo_fin" and ev.get("capitulo") is not None:
            tiradas[ev["capitulo"]] = (ev.get("tirada"), ev.get("ts"))
    salida = []
    for capitulo in nucleo.capitulos_existentes():
        tirada, sello = tiradas.get(capitulo, (None, None))
        if not tirada:
            continue
        try:
            informe = informes.informe_capitulo(capitulo, cfg, estado)
        except (SystemExit, OSError, KeyError, ValueError):
            continue
        metricas = dict(informe["metricas"].get("repeticion") or {})
        metricas.update(informe["metricas"].get("longitud") or {})
        continuidad = dict(informe["metricas"].get("continuidad") or {})
        continuidad.pop("comprobaciones", None)
        metricas.update(continuidad)
        salida.append({
            "ts": sello, "tirada": tirada, "evento": "validacion",
            "fase": "redaccion", "capitulo": capitulo,
            "intento": None,
            "datos": {"metricas": metricas, "resumen": informe["resumen"]},
            "esquema": 1,
        })
    return salida


# --------------------------------------------------------------------------
# Envio
# --------------------------------------------------------------------------

def _resumen(eventos: list, generaciones: list) -> dict:
    tokens = Counter()
    roles = Counter()
    modelos = Counter()
    for ev in generaciones:
        datos = ev["datos"]
        roles[datos["rol"]] += 1
        if datos.get("model"):
            modelos[datos["model"]] += 1
        for clave, valor in datos["usage"].items():
            tokens[clave] += valor
    capitulos = sorted({e.get("capitulo") for e in generaciones
                        if e.get("capitulo")})
    return {
        "eventos_del_pipeline": len(eventos),
        "generaciones": len(generaciones),
        "tokens": dict(tokens),
        "por_rol": dict(roles),
        "modelos": dict(modelos),
        "capitulos_con_generaciones": capitulos,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="retroalimentar.py",
        description="Sube a Langfuse una tirada ya ejecutada leyendo "
                    "events.jsonl, los informes y los transcripts de Claude "
                    "Code. No regenera nada y no escribe en events.jsonl.")
    parser.add_argument("--tirada",
                        help="Solo esta tirada. Por defecto, todas.")
    parser.add_argument("--transcripts",
                        help="Carpeta de transcripts de Claude Code. Por "
                             "defecto se localiza sola en ~/.claude/projects.")
    parser.add_argument("--sin-generaciones", action="store_true",
                        help="No leer los transcripts: sube solo el pipeline.")
    parser.add_argument("--sin-metricas-actuales", action="store_true",
                        help="No recalcular las metricas de los capitulos ya "
                             "escritos.")
    parser.add_argument("--simular", action="store_true",
                        help="Muestra lo que se enviaria y no envia nada.")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()
    eventos = ob.leer_eventos(cfg, args.tirada)
    if not eventos:
        nucleo.salir({"script": "retroalimentar",
                      "error": "no hay eventos que subir en events.jsonl"}, 3)

    generaciones = []
    aviso = None
    if not args.sin_generaciones:
        carpeta = carpeta_transcripts(args.transcripts)
        if carpeta is None:
            aviso = ("no se han encontrado los transcripts de Claude Code: "
                     "se sube el pipeline sin generaciones")
        else:
            generaciones = eventos_de_invocacion(
                eventos, leer_invocaciones(carpeta))

    sinteticos = ([] if args.sin_metricas_actuales
                  else eventos_de_metricas(cfg, eventos))

    completos = sorted(eventos + generaciones + sinteticos,
                       key=lambda e: e.get("ts") or "")
    texto_ok = ob.enviar_texto(cfg)
    lote = []
    for ev in completos:
        lote.extend(ob.construir(cfg, ev, completos, texto_ok))

    # Cada evento reafirma la traza de su tirada, asi que en una subida masiva
    # salen cientos de trace-create identicos. El id de un item es el hash de su
    # cuerpo, de modo que quedarse con el primero de cada id no pierde nada y
    # recorta el envio a una fraccion.
    vistos = set()
    unicos = []
    for item in lote:
        if item["id"] in vistos:
            continue
        vistos.add(item["id"])
        unicos.append(item)
    lote = unicos

    informe = _resumen(eventos, generaciones)
    informe.update({
        "script": "retroalimentar",
        "metricas_recalculadas": len(sinteticos),
        "items_de_ingesta": len(lote),
        "trazas": sorted({ob.id_traza(cfg, e.get("tirada")) for e in completos}),
    })
    if aviso:
        informe["aviso"] = aviso

    if args.simular:
        informe["enviado"] = False
        informe["detalle"] = "simulacion: no se ha enviado nada"
        nucleo.salir(informe, 0)

    diagnostico = ob.diagnostico()
    if not diagnostico["activo"]:
        informe["enviado"] = False
        informe["detalle"] = diagnostico["detalle"]
        informe["variables_ausentes"] = diagnostico["variables_ausentes"]
        nucleo.salir(informe, 3)

    # Se envia por tandas: un lote unico de miles de items es fragil y la API
    # lo rechazaria por tamano.
    enviados = 0
    fallidos = 0
    for inicio in range(0, len(lote), 100):
        ob.encolar(lote[inicio:inicio + 100])
        if ob.flush():
            enviados += len(lote[inicio:inicio + 100])
        else:
            fallidos += len(lote[inicio:inicio + 100])

    informe["enviado"] = fallidos == 0
    informe["items_enviados"] = enviados
    informe["items_fallidos"] = fallidos
    informe["detalle"] = ("todo enviado" if not fallidos else
                          "envio incompleto: ver novela/langfuse.log")
    nucleo.salir(informe, 0 if not fallidos else 3)


if __name__ == "__main__":
    main()
