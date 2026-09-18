"""Exportador a Langfuse: el unico sitio del sistema que habla por red.

Se engancha en un solo punto, la funcion registrar() de scripts/eventos.py.
Ningun subagente, ninguna skill y ningun otro script lo invoca.

TRANSPORTE. Las trazas y las observaciones van por OpenTelemetry a
`POST /api/public/otel/v1/traces`, en OTLP/HTTP con codificacion JSON. Los
scores van aparte, por `POST /api/public/ingestion` con eventos `score-create`.

Por que estan separados: la API de ingesta v3 se apaga en Langfuse Cloud el 16
de noviembre de 2026 para todo MENOS los scores, que siguen aceptandose por esa
via. Para trazas y observaciones, la documentacion senala OTLP como el camino de
la instrumentacion propia. Ver SPEC seccion 14.4.

Reglas que este modulo cumple sin excepcion:

  1. novela/events.jsonl sigue siendo la fuente local de verdad. Este modulo
     nunca la sustituye y nunca la desactiva.
  2. Un fallo de Langfuse JAMAS interrumpe la generacion. Todo va envuelto y lo
     que se rompe se anota en novela/langfuse.log y se sigue.
  3. Las CLAVES salen solo de variables de entorno del sistema y NUNCA se
     escriben en ningun sitio: ni en el log, ni en un error, ni en un
     diagnostico. Si falta alguna se dice cual por su nombre, sin su valor.
     El host de destino si se muestra, a proposito: no es un secreto, y sin
     el no se puede diagnosticar contra que servidor se esta trazando.
  4. Solo las claves apagan la exportacion. LANGFUSE_BASE_URL es opcional y
     tiene valor por defecto: una URL ausente no puede dejar la observabilidad
     muerta en silencio, que es como se pierde una novela entera de trazas.
  5. El estado se anuncia al arrancar la generacion, no al terminarla:
     anunciar() escribe una linea por stderr en fase_inicio y capitulo_inicio.
  6. Sin dependencias. Todo con urllib de la biblioteca estandar.

IDS DETERMINISTAS. Cada evento del pipeline es una invocacion separada de
`python scripts/eventos.py`: un proceso nuevo, sin memoria del anterior. Para
que el arbol anide, el id de traza (32 hex) y el de cada span (16 hex) se
derivan por hash de una clave legible, no de un contador en memoria. Asi el
mismo capitulo produce el mismo span id desde cualquier proceso.

Un span de OTLP viaja entero, con su inicio y su fin: no hay "update", y
reenviar un spanId ya ingerido duplica la observacion e infla el coste. De ahi
las tres reglas que gobiernan el envio:

  - El arbol se reconstruye completo desde el historico en cada envio, no se
    mandan trozos sueltos. Con decenas de eventos es gratis, y a cambio un
    envio perdido se recupera solo en el siguiente.
  - De ese arbol se emite SOLO lo que ya ha terminado. Una fase empezada o un
    capitulo en curso no viajan hasta que llega su evento de cierre, que es
    cuando se conoce su duracion. Por eso el panel va contando la novela en
    vivo, capitulo a capitulo, en vez de llenarse de spans de duracion cero
    que ya no se podrian corregir.
  - El registro local de lo enviado, novela/langfuse-enviados.txt, es lo unico
    que impide reenviar. Como esta en .gitignore y se pierde con cualquier
    clon nuevo, cuando falta se le pregunta al panel que tiene ya, en vez de
    mandarlo todo otra vez.

Python 3.12, solo biblioteca estandar.
"""

import atexit
import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import nucleo

# Lo unico que no se puede inventar son las claves. La URL si: sin ella el
# destino es el Langfuse de la region de EE. UU., que es donde vive el
# proyecto. Que faltara la URL apagaba la exportacion entera en silencio, y
# eso es justo lo que no debe pasar.
CLAVES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
VARIABLE_URL = "LANGFUSE_BASE_URL"
VARIABLES = CLAVES + (VARIABLE_URL,)
BASE_POR_DEFECTO = "https://us.cloud.langfuse.com"

TIEMPO_MAXIMO = 8          # segundos por envio: no bloquear la generacion
MAX_LOTE_BYTES = 900_000   # la API rechaza cuerpos por encima de 1 MB
RUTA_LOG = "novela/langfuse.log"
# Registro de spans ya enviados. Hace falta porque la ingesta por OTLP NO hace
# upsert por span id: reenviar un span crea otra observacion. Ver SPEC 14.4.
RUTA_ENVIADOS = "novela/langfuse-enviados.txt"
MAX_TEXTO = 20000          # tope del manuscrito que viaja como salida

RUTA_OTLP = "/api/public/otel/v1/traces"
RUTA_SCORES = "/api/public/ingestion"
RUTA_OBSERVACIONES = "/api/public/v2/observations"

EVENTOS_DE_INTENTO = ("borrador", "reescritura", "parche")

# La fase se llama 'entrega' en el pipeline y 'ensamblado' en el panel.
NOMBRES_FASE = {"canon": "canon", "escaleta": "escaleta",
                "redaccion": "redaccion", "revision": "revision",
                "entrega": "ensamblado"}

_pendientes = {"spans": [], "scores": []}
_registrado_atexit = False


# --------------------------------------------------------------------------
# Credenciales y configuracion
# --------------------------------------------------------------------------

def _credenciales() -> dict:
    """Lee las variables de entorno. Devuelve valores, ausencias y origen.

    Solo faltan las CLAVES: si no hay URL se usa BASE_POR_DEFECTO, asi que
    nunca es motivo de apagado. El valor de las claves no sale de aqui hacia
    un log ni hacia stdout: solo se usa para la cabecera de autorizacion.
    """
    valores = {v: (os.environ.get(v) or "").strip() for v in VARIABLES}
    del_entorno = bool(valores[VARIABLE_URL])
    if not del_entorno:
        valores[VARIABLE_URL] = BASE_POR_DEFECTO
    return {"valores": valores,
            "faltan": [v for v in CLAVES if not valores[v]],
            "url_del_entorno": del_entorno}


def _host(cred: dict) -> str:
    """Solo el host del destino. Se puede mostrar: no es un secreto, y saber
    contra que servidor se esta trazando es media diagnosis."""
    try:
        return urllib.parse.urlsplit(cred["valores"][VARIABLE_URL]).netloc or "?"
    except ValueError:
        return "?"


def _conf(cfg: dict) -> dict:
    obs = cfg.get("observabilidad") or {}
    lf = obs.get("langfuse") or {}
    return lf if isinstance(lf, dict) else {}


def activo(cfg: dict, cred: dict = None) -> bool:
    """Por defecto activo si las tres variables estan; inactivo si no."""
    cred = cred or _credenciales()
    if cred["faltan"]:
        return False
    valor = _conf(cfg).get("activo")
    return True if valor is None else bool(valor)


def entorno(cfg: dict) -> str:
    """Separa las trazas de prueba de las buenas en el panel de Langfuse."""
    return str(_conf(cfg).get("entorno") or "default")


def enviar_texto(cfg: dict) -> bool:
    """Si es False se envian metricas y metadatos, pero ningun texto de prosa
    ni de prompt. Por defecto True."""
    valor = _conf(cfg).get("enviar_texto")
    return True if valor is None else bool(valor)


def diagnostico() -> dict:
    """Estado de la integracion, sin revelar ni un caracter de las claves."""
    cfg = nucleo.cargar_config()
    cred = _credenciales()
    encendido = activo(cfg, cred)
    if encendido:
        detalle = "listo para enviar"
    elif cred["faltan"]:
        detalle = "faltan variables de entorno: " + ", ".join(cred["faltan"])
    else:
        detalle = "observabilidad.langfuse.activo es false"
    return {
        "script": "observabilidad",
        "transporte": "OTLP/HTTP JSON para trazas; score-create para scores",
        "host": _host(cred),
        "url_del_entorno": cred["url_del_entorno"],
        "claves_presentes": [v for v in CLAVES if v not in cred["faltan"]],
        "claves_ausentes": cred["faltan"],
        "activo": encendido,
        "enviar_texto": enviar_texto(cfg),
        "entorno": entorno(cfg),
        "detalle": detalle,
    }


def linea_estado() -> str:
    """Una linea que dice si se esta trazando y contra que host.

    Nunca lleva el valor de una clave. Si falta alguna se la nombra, que es
    lo unico accionable: el autor mira su entorno y la pone.
    """
    try:
        cfg = nucleo.cargar_config()
        cred = _credenciales()
    except SystemExit:
        return "[langfuse] INACTIVO: no se ha podido leer config.json"
    if cred["faltan"]:
        return ("[langfuse] INACTIVO: falta " + ", ".join(cred["faltan"])
                + " en el entorno. No se exporta nada; events.jsonl sigue "
                  "registrandolo todo.")
    if not activo(cfg, cred):
        return ("[langfuse] INACTIVO: observabilidad.langfuse.activo es false "
                "en config.json. events.jsonl sigue registrandolo todo.")
    origen = "del entorno" if cred["url_del_entorno"] else "por defecto"
    return (f"[langfuse] activo -> {_host(cred)} ({origen}), entorno "
            f"'{entorno(cfg)}', texto "
            f"{'si' if enviar_texto(cfg) else 'no'}")


def anunciar() -> None:
    """Escupe linea_estado() por stderr. No falla nunca y no toca stdout.

    Va por stderr a proposito: stdout de los scripts es JSON y tiene quien lo
    parsee. Y va al arrancar la generacion, no al final, porque de nada sirve
    enterarse de que no se estaba trazando cuando ya no hay nada que trazar.
    """
    try:
        print(linea_estado(), file=sys.stderr)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Registro local de fallos. Nunca contiene credenciales.
# --------------------------------------------------------------------------

def _anotar(mensaje: str) -> None:
    try:
        ruta = nucleo.raiz() / RUTA_LOG
        ruta.parent.mkdir(parents=True, exist_ok=True)
        marca = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with ruta.open("a", encoding="utf-8") as fichero:
            fichero.write(f"{marca} {mensaje}\n")
    except OSError:
        pass  # ni siquiera un fallo de log puede tumbar la generacion


def _ya_enviados() -> set:
    """Span ids que ya viajaron alguna vez."""
    ruta = nucleo.raiz() / RUTA_ENVIADOS
    if not ruta.exists():
        return set()
    try:
        return {l.strip() for l in ruta.read_text(encoding="utf-8").splitlines()
                if l.strip()}
    except OSError:
        return set()


def _marcar_enviados(ids) -> None:
    """Se apunta SOLO tras un envio correcto: si falla, se reintentara."""
    if not ids:
        return
    try:
        ruta = nucleo.raiz() / RUTA_ENVIADOS
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as fichero:
            for ident in ids:
                fichero.write(str(ident) + "\n")
    except OSError:
        pass


def nuevos(spans: list) -> list:
    """Descarta los spans que ya se enviaron en una ejecucion anterior."""
    vistos = _ya_enviados()
    salida, en_lote = [], set()
    for span in spans:
        ident = span.get("spanId")
        if ident in vistos or ident in en_lote:
            continue
        en_lote.add(ident)
        salida.append(span)
    return salida


def _motivo(exc: Exception) -> str:
    """Tipo del fallo y, si es HTTP, su codigo. Nunca la URL ni el cuerpo."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTPError {exc.code}"
    return type(exc).__name__


# --------------------------------------------------------------------------
# Identificadores y tiempos
# --------------------------------------------------------------------------

def _limpio(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(texto)).strip("-") or "x"


def _hex(clave: str, digitos: int) -> str:
    """Id hexadecimal estable derivado de una clave legible.

    OTLP exige 32 hex para la traza y 16 para el span. El hash da el mismo
    resultado en cualquier proceso, que es lo que permite anidar sin estado.
    """
    return hashlib.sha1(str(clave).encode("utf-8")).hexdigest()[:digitos]


def clave_traza(cfg: dict, tirada: str) -> str:
    return f"nov-{_limpio(cfg.get('proyecto', 'novela'))}-{_limpio(tirada)}"


def id_traza(cfg: dict, tirada: str) -> str:
    return _hex(clave_traza(cfg, tirada), 32)


def _id_span(clave: str) -> str:
    return _hex(clave, 16)


def _nanos(marca: str) -> str:
    """ISO-8601 con Z a nanosegundos unix, que es lo que pide OTLP."""
    if not marca:
        return "0"
    try:
        momento = datetime.fromisoformat(str(marca).replace("Z", "+00:00"))
    except ValueError:
        return "0"
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return str(int(momento.timestamp() * 1_000_000_000))


# --------------------------------------------------------------------------
# Atributos de OpenTelemetry
# --------------------------------------------------------------------------

def _valor(dato):
    if isinstance(dato, bool):
        return {"boolValue": dato}
    if isinstance(dato, int):
        return {"intValue": str(dato)}
    if isinstance(dato, float):
        return {"doubleValue": dato}
    if isinstance(dato, (list, tuple)):
        return {"arrayValue": {"values": [_valor(x) for x in dato]}}
    return {"stringValue": str(dato)}


def _atributos(pares: dict) -> list:
    return [{"key": clave, "value": _valor(dato)}
            for clave, dato in pares.items() if dato is not None]


def _texto(dato) -> str:
    """Los campos de entrada y salida viajan como texto en OTLP."""
    if isinstance(dato, str):
        return dato
    return json.dumps(dato, ensure_ascii=False, default=str)


def _span(traza: str, clave: str, nombre: str, tipo: str, inicio: str,
          fin: str, padre: str = None, atributos: dict = None,
          nivel: str = None, mensaje: str = None) -> dict:
    """Un span de OTLP con los atributos del modelo de datos de Langfuse."""
    attrs = {"langfuse.observation.type": tipo}
    if nivel:
        attrs["langfuse.observation.level"] = nivel
    if mensaje:
        attrs["langfuse.observation.status_message"] = mensaje
    attrs.update(atributos or {})
    span = {
        "traceId": traza,
        "spanId": _id_span(clave),
        "name": nombre,
        "kind": 1,
        "startTimeUnixNano": _nanos(inicio),
        "endTimeUnixNano": _nanos(fin or inicio),
        "attributes": _atributos(attrs),
        "status": {"code": 2, "message": mensaje} if nivel == "ERROR"
                  else {"code": 1},
    }
    if padre:
        span["parentSpanId"] = _id_span(padre)
    return span


# --------------------------------------------------------------------------
# Lectura del historico
# --------------------------------------------------------------------------

def leer_eventos(cfg: dict, tirada: str = None) -> list:
    """Todas las lineas de events.jsonl, opcionalmente de una sola tirada."""
    ruta = nucleo.raiz() / cfg["eventos"].get("fichero", "novela/events.jsonl")
    return [ev for ev in nucleo.leer_jsonl(ruta)
            if tirada is None or ev.get("tirada") == tirada]


def _agregados(eventos: list) -> dict:
    """Reescrituras, coste, duracion y modelos de una tirada completa."""
    reescrituras = sum(1 for e in eventos
                       if e.get("evento") in ("reescritura", "parche"))
    coste = 0.0
    modelos = []
    for e in eventos:
        if e.get("evento") != "invocacion":
            continue
        datos = e.get("datos") or {}
        try:
            coste += float(datos.get("total_cost_usd") or 0.0)
        except (TypeError, ValueError):
            pass
        modelo = datos.get("model") or datos.get("modelo")
        if modelo and modelo not in modelos:
            modelos.append(modelo)
    marcas = sorted(e["ts"] for e in eventos if e.get("ts"))
    duracion = None
    if len(marcas) >= 2:
        try:
            ini = datetime.fromisoformat(marcas[0].replace("Z", "+00:00"))
            fin = datetime.fromisoformat(marcas[-1].replace("Z", "+00:00"))
            duracion = round((fin - ini).total_seconds(), 1)
        except ValueError:
            duracion = None
    return {"reescrituras": reescrituras, "coste_usd": round(coste, 6),
            "modelos": modelos, "duracion_s": duracion,
            "inicio": marcas[0] if marcas else None,
            "fin": marcas[-1] if marcas else None}


def _version_prompt_escritor() -> str:
    ruta = nucleo.raiz() / ".claude" / "agents" / "escritor.md"
    if not ruta.exists():
        return "ausente"
    try:
        return _hex(ruta.read_text(encoding="utf-8"), 8)
    except OSError:
        return "ilegible"


def _perfil_umbrales(cfg: dict) -> str:
    val = cfg.get("validacion", {})
    return (f"ngrama{val.get('ngrama')}"
            f"-solape{val.get('max_solape_ngramas')}"
            f"-muletilla{val.get('max_muletilla_por_mil')}")


def _manuscrito() -> str:
    """El manuscrito entero, o el primer capitulo si es demasiado largo."""
    ruta = nucleo.raiz() / "manuscrito.md"
    if not ruta.exists():
        return ""
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(texto) <= MAX_TEXTO:
        return texto
    capitulos = nucleo.capitulos_existentes()
    if capitulos:
        try:
            return (nucleo.ruta_capitulo(capitulos[0]).read_text(encoding="utf-8")
                    + "\n\n[truncado: el manuscrito completo esta en manuscrito.md]")
        except OSError:
            pass
    return texto[:MAX_TEXTO]


# --------------------------------------------------------------------------
# Construccion del arbol de spans
# --------------------------------------------------------------------------

def _claves(traza_legible: str):
    """Fabricas de claves legibles. El hash las convierte en ids."""
    return {
        "raiz": f"{traza_legible}--raiz",
        "fase": lambda f: f"{traza_legible}--fase-{_limpio(f)}",
        "cap": lambda c: f"{traza_legible}--cap-{int(c):02d}",
        "int": lambda c, i: f"{traza_legible}--cap-{int(c):02d}--int-{int(i)}",
        "agente": lambda a: f"{traza_legible}--agente-{_limpio(a)}",
    }


def _padre_de(k, capitulo, intento, fase):
    if capitulo is not None and intento is not None:
        return k["int"](capitulo, intento)
    if capitulo is not None:
        return k["cap"](capitulo)
    if fase:
        return k["fase"](fase)
    return k["raiz"]


def _tramos(eventos: list) -> dict:
    """Inicio y fin de cada fase, capitulo e intento, leidos del historico."""
    fases, caps, intentos = {}, {}, {}
    ultimo = None
    for ev in sorted(eventos, key=lambda e: e.get("ts") or ""):
        tipo, ts = ev.get("evento"), ev.get("ts")
        ultimo = ts or ultimo
        fase, cap, it = ev.get("fase"), ev.get("capitulo"), ev.get("intento")
        if tipo == "fase_inicio" and fase:
            fases.setdefault(fase, {})["inicio"] = ts
        elif tipo == "fase_fin" and fase:
            fases.setdefault(fase, {})["fin"] = ts
            fases[fase]["salida"] = ev.get("datos")
        elif tipo == "capitulo_inicio" and cap is not None:
            caps.setdefault(cap, {})["inicio"] = ts
        elif tipo == "capitulo_fin" and cap is not None:
            caps.setdefault(cap, {}).update(
                {"fin": ts, "salida": ev.get("datos"), "intentos": it})
        elif tipo in EVENTOS_DE_INTENTO and cap is not None:
            clave = (cap, it or 1)
            intentos.setdefault(clave, {}).update(
                {"inicio": ts, "modo": tipo,
                 "entrada": (ev.get("datos") or {}).get("incidencias")})
            caps.setdefault(cap, {}).setdefault("inicio", ts)
        elif tipo == "validacion" and cap is not None and it is not None:
            intentos.setdefault((cap, it), {})["fin"] = ts
    return {"fases": fases, "capitulos": caps, "intentos": intentos,
            "ultimo": ultimo}


def _raiz(cfg, traza, k, eventos, agr, texto_ok):
    """El span raiz lleva los atributos de la traza: en OTLP no hay objeto
    traza aparte, se infiere de aqui."""
    entrada = {"capitulos": cfg.get("capitulos"),
               "longitud": cfg.get("longitud")}
    if texto_ok:
        entrada["premisa"] = cfg.get("premisa")
    tirada = next((e.get("tirada") for e in eventos if e.get("tirada")), None)
    atributos = {
        "langfuse.trace.name": cfg.get("proyecto") or "novela",
        "langfuse.trace.input": _texto(entrada),
        "langfuse.session.id": _limpio(cfg.get("proyecto") or "novela"),
        "langfuse.environment": entorno(cfg),
        "langfuse.trace.tags": [
            f"umbrales:{_perfil_umbrales(cfg)}",
            f"escritor:{_version_prompt_escritor()}",
            f"tirada:{tirada}",
        ] + [f"modelo:{m}" for m in agr["modelos"]],
        "langfuse.trace.metadata.tirada": tirada,
        "langfuse.trace.metadata.config_efectiva": _texto(
            {c: cfg.get(c) for c in ("proyecto", "idioma", "capitulos",
                                     "longitud", "validacion")}),
        "langfuse.trace.metadata.coste_total_usd": agr["coste_usd"],
        "langfuse.trace.metadata.duracion_total_s": agr["duracion_s"],
        "langfuse.trace.metadata.reescrituras_totales": agr["reescrituras"],
    }
    if texto_ok:
        salida = _manuscrito()
        if salida:
            atributos["langfuse.trace.output"] = salida
    return _span(traza, k["raiz"], cfg.get("proyecto") or "novela", "span",
                 agr["inicio"], agr["fin"], None, atributos)


def _comunes(cfg: dict, tirada: str) -> dict:
    """Atributos de traza que Langfuse v4 quiere repetidos en cada span.

    En v4 la traza es solo un grupo de observaciones: lo que vive unicamente
    en la raiz no se puede filtrar ni agregar desde sus hijos. Y como la raiz
    es lo ultimo que se cierra, sin esto la tirada en curso apareceria en el
    panel sin nombre y sin entorno hasta el final.
    """
    return {
        "langfuse.trace.name": cfg.get("proyecto") or "novela",
        "langfuse.session.id": _limpio(cfg.get("proyecto") or "novela"),
        "langfuse.environment": entorno(cfg),
        "langfuse.trace.metadata.tirada": tirada,
    }


def _agentes(eventos: list) -> dict:
    """Agrupa las invocaciones por ejecucion de subagente.

    Cada subagente es UNA observacion de tipo 'agent' con sus llamadas dentro,
    no un span generico: es lo que le da nodo propio en el grafo de agentes.
    """
    grupos = {}
    for ev in eventos:
        if ev.get("evento") != "invocacion":
            continue
        datos = ev.get("datos") or {}
        ident = datos.get("id_agente")
        if not ident:
            continue
        grupo = grupos.setdefault(ident, {
            "rol": datos.get("rol") or "modelo",
            "descripcion": datos.get("descripcion"),
            "capitulo": ev.get("capitulo"), "intento": ev.get("intento"),
            "fase": ev.get("fase"), "inicio": ev.get("ts"), "fin": ev.get("ts"),
            "llamadas": 0})
        grupo["llamadas"] += 1
        if (ev.get("ts") or "") < (grupo["inicio"] or ""):
            grupo["inicio"] = ev.get("ts")
        if (ev.get("ts") or "") > (grupo["fin"] or ""):
            grupo["fin"] = ev.get("ts")
    return grupos


def _generacion(traza, k, ev, texto_ok) -> dict:
    """Una llamada al modelo. Tokens y modelo se LEEN, nunca se estiman."""
    datos = ev.get("datos") or {}
    uso = datos.get("usage") or {}
    rol = datos.get("rol") or "modelo"

    detalle = {}
    for origen, destino in (("input_tokens", "input"),
                            ("output_tokens", "output"),
                            ("cache_creation_input_tokens",
                             "cache_creation_input_tokens"),
                            ("cache_read_input_tokens",
                             "cache_read_input_tokens")):
        if uso.get(origen) is not None:
            try:
                detalle[destino] = int(uso[origen] or 0)
            except (TypeError, ValueError):
                pass

    atributos = {
        "langfuse.observation.model.name": datos.get("model"),
        "langfuse.observation.usage_details": json.dumps(detalle),
        "langfuse.observation.metadata.capitulo": ev.get("capitulo"),
        "langfuse.observation.metadata.intento": ev.get("intento"),
        "langfuse.observation.metadata.rol": rol,
        "langfuse.observation.metadata.session_id": datos.get("session_id"),
        "langfuse.observation.metadata.cache_leida":
            bool(detalle.get("cache_read_input_tokens")),
        "langfuse.observation.metadata.cache_creada":
            bool(detalle.get("cache_creation_input_tokens")),
    }
    # El coste lo calcula Langfuse con el modelo y los tokens. Solo se manda
    # explicito si la invocacion trajo el suyo.
    if datos.get("total_cost_usd") is not None:
        try:
            atributos["langfuse.observation.cost_details"] = json.dumps(
                {"total": float(datos["total_cost_usd"])})
        except (TypeError, ValueError):
            pass
    if texto_ok:
        if datos.get("prompt"):
            atributos["langfuse.observation.input"] = _texto(datos["prompt"])
        if datos.get("respuesta"):
            atributos["langfuse.observation.output"] = _texto(datos["respuesta"])

    ident = datos.get("id_agente")
    padre = (k["agente"](ident) if ident
             else _padre_de(k, ev.get("capitulo"), ev.get("intento"),
                            ev.get("fase")))
    clave = f"{k['raiz']}--gen-{datos.get('id_generacion') or ev.get('ts')}"
    return _span(traza, clave, rol, "generation",
                 datos.get("inicio") or ev.get("ts"),
                 datos.get("fin") or ev.get("ts"), padre, atributos)


def construir_spans(cfg: dict, eventos: list, texto_ok: bool,
                    cerrar: bool = False) -> list:
    """Arbol de una tirada, en spans de OTLP. SOLO lo que ya ha terminado.

    Un span de OTLP viaja entero y Langfuse NO lo actualiza despues: reenviar
    el mismo spanId duplica la observacion e infla el coste. Por eso un tramo
    abierto (una fase empezada, un capitulo en curso) no se emite todavia: se
    emitira en el envio del evento que lo cierre, ya con su duracion real.
    Eso es lo que hace que el panel siga la tirada en vivo en lugar de
    llenarse de spans de duracion cero que nunca se podran corregir.

    Con cerrar=True se dan por terminados los tramos abiertos, tomando como
    fin la ultima marca del historico. Es para subir una tirada pasada, que
    por definicion ya no va a cerrar sus eventos.
    """
    if not eventos:
        return []
    tirada = next((e.get("tirada") for e in eventos if e.get("tirada")), None)
    legible = clave_traza(cfg, tirada)
    traza = id_traza(cfg, tirada)
    k = _claves(legible)
    agr = _agregados(eventos)
    tramos = _tramos(eventos)

    def cerrado(datos, respaldo=None):
        """Fin real del tramo, o None si sigue abierto."""
        if datos.get("fin"):
            return datos["fin"]
        return (respaldo or tramos["ultimo"]) if cerrar else None

    # La tirada termina cuando se cierra la fase de entrega: es el mismo
    # criterio con el que eventos.tirada_vigente() abre la siguiente.
    acabada = cerrar or any(e.get("evento") == "fase_fin"
                            and e.get("fase") == "entrega" for e in eventos)
    spans = [_raiz(cfg, traza, k, eventos, agr, texto_ok)] if acabada else []

    for fase, datos in tramos["fases"].items():
        fin = cerrado(datos)
        if fin is None:
            continue
        spans.append(_span(
            traza, k["fase"](fase), NOMBRES_FASE.get(fase, fase), "span",
            datos.get("inicio") or agr["inicio"], fin, k["raiz"],
            {"langfuse.observation.metadata.fase": fase,
             "langfuse.observation.output": _texto(datos.get("salida"))
             if datos.get("salida") else None}))

    for cap, datos in tramos["capitulos"].items():
        fin = cerrado(datos)
        if fin is None:
            continue
        spans.append(_span(
            traza, k["cap"](cap), f"capitulo {int(cap):02d}", "span",
            datos.get("inicio"), fin, k["fase"]("redaccion"),
            {"langfuse.observation.metadata.capitulo": cap,
             "langfuse.observation.metadata.intentos": datos.get("intentos"),
             "langfuse.observation.output": _texto(datos.get("salida"))
             if datos.get("salida") else None}))

    for (cap, intento), datos in tramos["intentos"].items():
        fin = cerrado(datos, datos.get("inicio"))
        if fin is None:
            continue
        spans.append(_span(
            traza, k["int"](cap, intento),
            f"intento {intento} ({datos.get('modo', 'borrador')})", "span",
            datos.get("inicio"), fin, k["cap"](cap),
            {"langfuse.observation.metadata.capitulo": cap,
             "langfuse.observation.metadata.intento": intento,
             "langfuse.observation.metadata.modo": datos.get("modo"),
             "langfuse.observation.input": _texto(datos["entrada"])
             if datos.get("entrada") else None}))

    for ident, grupo in _agentes(eventos).items():
        spans.append(_span(
            traza, k["agente"](ident), grupo["rol"], "agent",
            grupo["inicio"], grupo["fin"],
            _padre_de(k, grupo["capitulo"], grupo["intento"], grupo["fase"]),
            {"langfuse.observation.metadata.rol": grupo["rol"],
             "langfuse.observation.metadata.llamadas": grupo["llamadas"],
             "langfuse.observation.input": grupo.get("descripcion")}))

    for ev in eventos:
        tipo = ev.get("evento")
        datos = ev.get("datos") or {}
        if tipo == "invocacion":
            spans.append(_generacion(traza, k, ev, texto_ok))
        elif tipo == "validacion":
            # Una validacion juzga la calidad de un capitulo: en el modelo de
            # Langfuse eso es un 'evaluator', no un evento suelto.
            spans.append(_span(
                traza, f"{k['raiz']}--val-{ev.get('ts')}", "validacion",
                "evaluator", ev.get("ts"), ev.get("ts"),
                _padre_de(k, ev.get("capitulo"), ev.get("intento"),
                          ev.get("fase")),
                {"langfuse.observation.input": _texto(datos.get("metricas")),
                 "langfuse.observation.output": _texto(datos.get("resumen"))}))
        elif tipo == "escalado":
            spans.append(_span(
                traza, f"{k['raiz']}--esc-{ev.get('ts')}", "escalado", "event",
                ev.get("ts"), ev.get("ts"),
                _padre_de(k, ev.get("capitulo"), None, ev.get("fase")),
                {"langfuse.observation.output": _texto(datos)},
                nivel="ERROR", mensaje="escalado al autor"))
        elif tipo == "commit":
            spans.append(_span(
                traza, f"{k['raiz']}--commit-{ev.get('ts')}", "commit", "event",
                ev.get("ts"), ev.get("ts"), k["raiz"],
                {"langfuse.observation.output": _texto(datos)}))

    comunes = _atributos(_comunes(cfg, tirada))
    for span in spans:
        ya = {a["key"] for a in span["attributes"]}
        span["attributes"].extend(a for a in comunes if a["key"] not in ya)
    return spans


# --------------------------------------------------------------------------
# Scores
# --------------------------------------------------------------------------

_dir_capitulos = None


def usar_capitulos(ruta) -> None:
    """Mide los capitulos en otra carpeta, para subir una novela archivada."""
    global _dir_capitulos
    _dir_capitulos = ruta


def _lineas_utiles(capitulo) -> list:
    """Lineas de cuerpo del capitulo, con la misma regla que nucleo.

    Si el fichero no esta (por ejemplo, una tirada ya archivada cuyos
    capitulos se movieron), devuelve None en vez de cero: publicar un cero
    seria publicar un dato falso.
    """
    return nucleo.lineas_de(
        nucleo.carpeta_capitulos(_dir_capitulos)
        / f"capitulo-{int(capitulo):02d}.md")


def _aplanar(metricas: dict) -> dict:
    plano = {}
    for clave, valor in (metricas or {}).items():
        if clave == "monotonia_componentes" and isinstance(valor, dict):
            for sub, subvalor in valor.items():
                plano[f"monotonia_{sub}"] = subvalor
        elif clave == "muletilla_max" and isinstance(valor, dict):
            if valor.get("por_mil") is not None:
                plano["muletilla_por_mil"] = valor["por_mil"]
        else:
            plano[clave] = valor
    return plano


def construir_scores(cfg: dict, eventos: list) -> list:
    """Scores del span de cada capitulo: lo que permite comparar tiradas.

    Van por la API de ingesta con eventos score-create, que es la unica parte
    de esa API que sigue viva tras el 16 de noviembre de 2026.
    """
    if not eventos:
        return []
    tirada = next((e.get("tirada") for e in eventos if e.get("tirada")), None)
    legible = clave_traza(cfg, tirada)
    traza = id_traza(cfg, tirada)
    k = _claves(legible)
    ent = entorno(cfg)
    lote = []

    def anadir(observacion, nombre, valor, intento=None, sello=None):
        if isinstance(valor, bool):
            valor, tipo = (1 if valor else 0), "NUMERIC"
        elif isinstance(valor, (int, float)):
            tipo = "NUMERIC"
        elif isinstance(valor, str):
            valor, tipo = str(valor), "CATEGORICAL"
        else:
            return
        cuerpo = {"id": _hex(f"{observacion}{nombre}{intento}", 32),
                  "traceId": traza, "observationId": _id_span(observacion),
                  "name": nombre, "value": valor, "dataType": tipo,
                  "environment": ent}
        # Un score se identifica por id + nombre + FECHA del sello. Si el
        # sello fuera el reloj de cada envio, el mismo score reenviado al dia
        # siguiente entraria como uno nuevo en vez de sobrescribir. Con el
        # sello del evento que lo produjo, reenviarlo es siempre inocuo.
        lote.append({"id": _hex(f"sc{observacion}{nombre}{intento}", 32),
                     "type": "score-create",
                     "timestamp": sello or datetime.now(timezone.utc)
                     .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                     "body": cuerpo})

    for ev in eventos:
        cap = ev.get("capitulo")
        if cap is None:
            continue
        datos = ev.get("datos") or {}
        sello = ev.get("ts")
        if ev.get("evento") == "validacion":
            observacion = k["cap"](cap)
            for nombre, valor in _aplanar(datos.get("metricas")).items():
                anadir(observacion, nombre, valor, ev.get("intento"), sello)
            for sev in ("bloqueante", "mayor", "menor"):
                if sev in (datos.get("resumen") or {}):
                    anadir(observacion, f"incidencias_{sev}",
                           datos["resumen"][sev], ev.get("intento"), sello)
        elif ev.get("evento") == "capitulo_fin":
            observacion = k["cap"](cap)
            anadir(observacion, "intentos", ev.get("intento") or 1,
                   sello=sello)
            lineas = _lineas_utiles(cap)
            if lineas is not None:
                anadir(observacion, "palabras",
                       len(nucleo.palabras(" ".join(lineas))), sello=sello)
                anadir(observacion, "lineas", len(lineas), sello=sello)
        elif ev.get("evento") == "escalado":
            anadir(k["cap"](cap), "escalado", 1, sello=sello)
    return lote


# --------------------------------------------------------------------------
# Envio
# --------------------------------------------------------------------------

def _autorizacion(cred: dict) -> str:
    """La cabecera Basic. Las claves no salen de aqui hacia ningun otro sitio."""
    valores = cred["valores"]
    return "Basic " + base64.b64encode(
        f"{valores['LANGFUSE_PUBLIC_KEY']}:{valores['LANGFUSE_SECRET_KEY']}"
        .encode("utf-8")).decode("ascii")


def _consultar(cred: dict, ruta: str, parametros: dict):
    """GET a la API publica. Devuelve el JSON, o None si no se pudo preguntar.

    Es la unica lectura que hace este modulo. No participa en el envio: solo
    sirve para saber que hay ya en el panel antes de mandar nada.
    """
    url = (cred["valores"]["LANGFUSE_BASE_URL"].rstrip("/") + ruta + "?"
           + urllib.parse.urlencode(parametros))
    peticion = urllib.request.Request(url, method="GET")
    peticion.add_header("Authorization", _autorizacion(cred))
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except SystemExit:
        return None
    except Exception as exc:
        _anotar(f"consulta de lo ya ingerido fallida: {_motivo(exc)}")
        return None


def _ids_ingeridos(cred: dict, trazas) -> set:
    """Span ids que Langfuse ya tiene de esas trazas, o None si no contesta."""
    ids = set()
    for traza in sorted(t for t in trazas if t):
        cursor = None
        for _ in range(50):                  # tope: no pagina sin fin
            consulta = {"traceId": traza, "limit": 1000}
            if cursor:
                consulta["cursor"] = cursor
            datos = _consultar(cred, RUTA_OBSERVACIONES, consulta)
            if datos is None:
                return None
            filas = datos.get("data") or []
            ids.update(f.get("id") for f in filas if f.get("id"))
            cursor = (datos.get("meta") or {}).get("cursor")
            if not cursor or not filas:
                break
    return ids


def sembrar_enviados(trazas) -> bool:
    """Apunta como ya enviados los spans que el panel tiene de esas trazas.

    novela/langfuse-enviados.txt es lo unico que impide reenviar un span, y
    Langfuse NO deduplica: cada reenvio es otra observacion, y el coste del
    panel sube con ella. Pero ese fichero esta en .gitignore y no viaja con el
    repositorio, asi que se pierde con cualquier clon nuevo. Preguntar al
    panel lo reconstruye. Devuelve False si no se ha podido preguntar.
    """
    cfg = nucleo.cargar_config()
    cred = _credenciales()
    if not activo(cfg, cred):
        return False
    ids = _ids_ingeridos(cred, trazas)
    if ids is None:
        return False
    _marcar_enviados(ids)
    return True


def _peticion(cred: dict, ruta: str, cuerpo: dict, cabeceras: dict = None):
    url = cred["valores"]["LANGFUSE_BASE_URL"].rstrip("/") + ruta
    datos = json.dumps(cuerpo, ensure_ascii=False, default=str).encode("utf-8")
    peticion = urllib.request.Request(url, data=datos, method="POST")
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("Authorization", _autorizacion(cred))
    for clave, valor in (cabeceras or {}).items():
        peticion.add_header(clave, valor)
    with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as respuesta:
        return 200 <= respuesta.status < 300


def _envoltorio(cfg: dict, spans: list) -> dict:
    return {"resourceSpans": [{
        "resource": {"attributes": _atributos({
            "service.name": cfg.get("proyecto") or "novela",
            "deployment.environment.name": entorno(cfg)})},
        "scopeSpans": [{
            "scope": {"name": "mystory1.observabilidad", "version": "2"},
            "spans": spans}]}]}


def trocear(items: list, maximo: int = MAX_LOTE_BYTES) -> list:
    """Parte en tandas que quepan bajo el limite de tamano de la API."""
    tandas, actual, peso = [], [], 2
    for item in items:
        tamano = len(json.dumps(item, ensure_ascii=False,
                                default=str).encode("utf-8")) + 1
        if actual and peso + tamano > maximo:
            tandas.append(actual)
            actual, peso = [], 2
        actual.append(item)
        peso += tamano
    if actual:
        tandas.append(actual)
    return tandas


def flush() -> bool:
    """Envia lo pendiente. Se llama al terminar el proceso y no propaga nada.

    Sin este vaciado las ultimas trazas se perderian: el proceso de un evento
    dura milisegundos y termina antes de que convenga hablar por red.
    """
    global _pendientes
    spans = _pendientes["spans"]
    scores = _pendientes["scores"]
    if not spans and not scores:
        return True
    _pendientes = {"spans": [], "scores": []}
    try:
        cfg = nucleo.cargar_config()
        cred = _credenciales()
        if not activo(cfg, cred):
            return False
        if spans and not (nucleo.raiz() / RUTA_ENVIADOS).exists():
            # Sin registro local no se sabe que viajo ya. Se pregunta al panel
            # una vez y se vuelve a filtrar: reenviar no corrige nada, duplica.
            ids = _ids_ingeridos(cred, {s.get("traceId") for s in spans})
            if ids:
                _marcar_enviados(ids)
                spans = nuevos(spans)
        ok = True
        for tanda in trocear(spans):
            if _peticion(cred, RUTA_OTLP, _envoltorio(cfg, tanda),
                         {"x-langfuse-ingestion-version": "4"}):
                _marcar_enviados(s.get("spanId") for s in tanda)
            else:
                _anotar(f"OTLP: tanda de {len(tanda)} spans rechazada")
                ok = False
        for tanda in trocear(scores):
            if not _peticion(cred, RUTA_SCORES, {"batch": tanda}):
                _anotar(f"scores: tanda de {len(tanda)} rechazada")
                ok = False
        return ok
    except SystemExit:
        return False
    except Exception as exc:                     # nunca sube al orquestador
        _anotar(f"envio de {len(spans)} spans y {len(scores)} scores "
                f"fallido: {_motivo(exc)}")
        return False


def encolar(spans: list = None, scores: list = None) -> None:
    global _registrado_atexit
    if not spans and not scores:
        return
    _pendientes["spans"].extend(spans or [])
    _pendientes["scores"].extend(scores or [])
    if not _registrado_atexit:
        atexit.register(flush)
        _registrado_atexit = True


def _generaciones(eventos: list) -> list:
    """Las llamadas de los subagentes que ya han terminado, como eventos
    'invocacion' del esquema.

    Los transcripts de Claude Code son el UNICO sitio donde existe el
    desglose de tokens de cada llamada. Sin esto la traza en vivo no tendria
    ni una sola 'generation' y el panel daria coste cero hasta que alguien
    ejecutara retroalimentar.py al terminar la novela.

    Estas invocaciones NO se escriben en events.jsonl: el registro local
    cuenta lo que hizo el pipeline, y los transcripts son una fuente externa.
    Solo viajan a Langfuse. Ver SPEC 14.5.
    """
    try:
        import retroalimentar
    except ImportError:
        return []
    carpeta = retroalimentar.carpeta_transcripts()
    if carpeta is None:
        return []
    return retroalimentar.eventos_de_invocacion(
        eventos, retroalimentar.leer_invocaciones(carpeta,
                                                  solo_primer_plano=True))


def exportar(ev: dict) -> bool:
    """Punto de entrada que llama eventos.registrar(). No lanza nunca.

    Reconstruye el arbol entero de la tirada y emite lo que este evento haya
    cerrado: un span de OTLP viaja completo y no se actualiza despues.
    Devuelve True si quedo encolado.
    """
    try:
        cfg = nucleo.cargar_config()
        cred = _credenciales()
        if not activo(cfg, cred):
            return False
        eventos = leer_eventos(cfg, ev.get("tirada"))
        if not any(e.get("ts") == ev.get("ts") for e in eventos):
            eventos.append(ev)
        completos = sorted(eventos + _generaciones(eventos),
                           key=lambda e: e.get("ts") or "")
        # Solo lo que no haya viajado ya: sin este filtro, reconstruir el
        # arbol en cada evento multiplicaria cada span por el numero de
        # eventos de la tirada.
        encolar(nuevos(construir_spans(cfg, completos, enviar_texto(cfg))),
                construir_scores(cfg, eventos))
        return True
    except SystemExit:
        return False
    except Exception as exc:
        _anotar(f"evento '{ev.get('evento')}' no exportado: {_motivo(exc)}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog="observabilidad.py",
        description="Exportador a Langfuse por OpenTelemetry. Se engancha en "
                    "eventos.registrar(). Ejecutado a mano solo diagnostica, "
                    "y nunca muestra claves.")
    parser.add_argument("--estado", action="store_true",
                        help="Dice si la integracion esta activa y que variables "
                             "de entorno faltan, por su nombre y sin su valor.")
    parser.add_argument("--linea", action="store_true",
                        help="Lo mismo en una sola linea legible, la que se "
                             "imprime al arrancar cada generacion.")
    args = parser.parse_args()
    if args.linea:
        print(linea_estado())
        raise SystemExit(0)
    nucleo.salir(diagnostico(), 0)


if __name__ == "__main__":
    main()
