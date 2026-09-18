"""Exportador a Langfuse: el unico sitio del sistema que habla por red.

Se engancha en un solo punto, la funcion registrar() de scripts/eventos.py, tal
como anticipa SPEC seccion 14.4. Ningun subagente, ninguna skill y ningun otro
script lo invoca.

Reglas que este modulo cumple sin excepcion:

  1. novela/events.jsonl sigue siendo la fuente local de verdad. Este modulo
     nunca la sustituye y nunca la desactiva.
  2. Un fallo de Langfuse JAMAS interrumpe la generacion. Todo va envuelto y lo
     que se rompe se anota en novela/langfuse.log y se sigue.
  3. Las credenciales salen solo de variables de entorno del sistema y NUNCA se
     escriben en ningun sitio: ni en el log, ni en un error, ni en un
     diagnostico. Si falta alguna se dice cual por su nombre, sin su valor.
  4. Sin dependencias. El transporte es la API de ingesta de Langfuse por HTTP,
     con urllib de la biblioteca estandar.

Por que ids deterministas: cada evento del pipeline es una invocacion separada
de `python scripts/eventos.py`, un proceso nuevo sin memoria del anterior. Para
que los spans aniden (novela > fase > capitulo > intento > generacion) el id de
cada uno se deriva de sus campos, no de un contador en memoria. La API de
ingesta hace upsert por id, asi que el orden de llegada no importa.

Python 3.12, solo biblioteca estandar.
"""

import atexit
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

import nucleo

VARIABLES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")

TIEMPO_MAXIMO = 8          # segundos por envio: no bloquear la generacion
RUTA_LOG = "novela/langfuse.log"
MAX_TEXTO = 20000          # tope del manuscrito que viaja como salida

# Eventos que abren un intento dentro de un capitulo.
EVENTOS_DE_INTENTO = ("borrador", "reescritura", "parche")

_pendientes = []
_registrado_atexit = False


# --------------------------------------------------------------------------
# Credenciales y configuracion
# --------------------------------------------------------------------------

def _credenciales() -> dict:
    """Lee las tres variables de entorno. Devuelve valores y ausencias.

    El valor nunca sale de esta funcion hacia un log ni hacia stdout: solo se
    usa para construir la cabecera de autorizacion.
    """
    valores = {v: (os.environ.get(v) or "").strip() for v in VARIABLES}
    faltan = [v for v, dato in valores.items() if not dato]
    return {"valores": valores, "faltan": faltan}


def _conf(cfg: dict) -> dict:
    obs = cfg.get("observabilidad") or {}
    lf = obs.get("langfuse") or {}
    return lf if isinstance(lf, dict) else {}


def activo(cfg: dict, cred: dict = None) -> bool:
    """Por defecto activo si las tres variables estan; inactivo si no.

    Una clave explicita observabilidad.langfuse.activo manda sobre el defecto,
    pero sin credenciales no se puede enviar nada aunque se pida.
    """
    cred = cred or _credenciales()
    if cred["faltan"]:
        return False
    valor = _conf(cfg).get("activo")
    if valor is None:
        return True
    return bool(valor)


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
        detalle = ("faltan variables de entorno: "
                   + ", ".join(cred["faltan"]))
    else:
        detalle = "observabilidad.langfuse.activo es false"
    return {
        "script": "observabilidad",
        "variables_presentes": [v for v in VARIABLES if v not in cred["faltan"]],
        "variables_ausentes": cred["faltan"],
        "activo": encendido,
        "enviar_texto": enviar_texto(cfg),
        "detalle": detalle,
    }


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


def _motivo(exc: Exception) -> str:
    """Descripcion de un fallo sin URL, sin cabeceras y sin cuerpo.

    Se limita al tipo y, si es HTTP, al codigo. Asi es imposible que una clave
    o un host acaben en el log por la via de un mensaje de excepcion.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTPError {exc.code}"
    return type(exc).__name__


# --------------------------------------------------------------------------
# Identificadores deterministas
# --------------------------------------------------------------------------

def _limpio(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(texto)).strip("-") or "x"


def _corto(texto: str) -> str:
    return hashlib.sha1(str(texto).encode("utf-8")).hexdigest()[:16]


def id_traza(cfg: dict, tirada: str) -> str:
    return f"nov-{_limpio(cfg.get('proyecto', 'novela'))}-{_limpio(tirada)}"


def _id_fase(traza: str, fase: str) -> str:
    return f"{traza}--fase-{_limpio(fase)}"


def _id_capitulo(traza: str, capitulo) -> str:
    return f"{traza}--cap-{int(capitulo):02d}"


def _id_intento(traza: str, capitulo, intento) -> str:
    return f"{_id_capitulo(traza, capitulo)}--int-{int(intento)}"


def _padre(traza: str, ev: dict) -> str:
    """Span al que cuelga un evento: intento > capitulo > fase > traza."""
    cap, intento, fase = ev.get("capitulo"), ev.get("intento"), ev.get("fase")
    if cap is not None and intento is not None:
        return _id_intento(traza, cap, intento)
    if cap is not None:
        return _id_capitulo(traza, cap)
    if fase:
        return _id_fase(traza, fase)
    return None


# --------------------------------------------------------------------------
# Lectura del historico para los agregados de la traza
# --------------------------------------------------------------------------

def leer_eventos(cfg: dict, tirada: str = None) -> list:
    """Todas las lineas de events.jsonl, opcionalmente de una sola tirada."""
    ruta = nucleo.raiz() / cfg["eventos"].get("fichero", "novela/events.jsonl")
    if not ruta.exists():
        return []
    salida = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if tirada is None or ev.get("tirada") == tirada:
            salida.append(ev)
    return salida


def _agregados(eventos: list) -> dict:
    """Reescrituras, coste, duracion y modelos de una tirada completa.

    Se recalcula leyendo el fichero entero en cada evento. Con decenas de lineas
    es gratis, y a cambio la traza queda siempre coherente aunque un envio se
    haya perdido por falta de red.
    """
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
            "inicio": marcas[0] if marcas else None}


def _version_prompt_escritor() -> str:
    ruta = nucleo.raiz() / ".claude" / "agents" / "escritor.md"
    if not ruta.exists():
        return "ausente"
    try:
        return _corto(ruta.read_text(encoding="utf-8"))[:8]
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
            primero = nucleo.ruta_capitulo(capitulos[0]).read_text(encoding="utf-8")
            return (primero
                    + "\n\n[truncado: el manuscrito completo esta en manuscrito.md]")
        except OSError:
            pass
    return texto[:MAX_TEXTO]


# --------------------------------------------------------------------------
# Construccion del lote de ingesta
# --------------------------------------------------------------------------

def _item(tipo: str, cuerpo: dict, sello: str) -> dict:
    semilla = json.dumps(cuerpo, sort_keys=True, default=str)
    return {"id": _corto(tipo + semilla), "type": tipo,
            "timestamp": sello, "body": cuerpo}


def _traza(cfg: dict, ev: dict, eventos: list, texto_ok: bool) -> dict:
    """La traza de la novela: una por tirada, agrupadas por session_id."""
    traza = id_traza(cfg, ev.get("tirada"))
    agr = _agregados(eventos)
    cuerpo = {
        "id": traza,
        "name": cfg.get("proyecto") or "novela",
        # session_id = identificador de la novela, no de la tirada: asi varias
        # tiradas de la misma premisa quedan agrupadas y se pueden comparar.
        "sessionId": _limpio(cfg.get("proyecto") or "novela"),
        "timestamp": agr["inicio"] or ev.get("ts"),
        "tags": [
            f"umbrales:{_perfil_umbrales(cfg)}",
            f"escritor:{_version_prompt_escritor()}",
            f"tirada:{ev.get('tirada')}",
        ] + [f"modelo:{m}" for m in agr["modelos"]],
        "metadata": {
            "tirada": ev.get("tirada"),
            "config_efectiva": {k: cfg.get(k) for k in
                                ("proyecto", "idioma", "capitulos", "longitud",
                                 "validacion")},
            "coste_total_usd": agr["coste_usd"],
            "duracion_total_s": agr["duracion_s"],
            "reescrituras_totales": agr["reescrituras"],
        },
        "input": {"capitulos": cfg.get("capitulos"),
                  "longitud": cfg.get("longitud")},
    }
    if texto_ok:
        cuerpo["input"]["premisa"] = cfg.get("premisa")
        salida = _manuscrito()
        if salida:
            cuerpo["output"] = salida
    return cuerpo


def _scores_validacion(traza: str, ev: dict) -> list:
    """Todas las metricas del informe, dispare o no una incidencia, mas el
    recuento por severidad. Cuelgan del span del CAPITULO, que es lo que
    permite comparar una tirada con la siguiente."""
    cap = ev.get("capitulo")
    if cap is None:
        return []
    obs = _id_capitulo(traza, cap)
    datos = ev.get("datos") or {}
    metricas = datos.get("metricas") or {}
    resumen = datos.get("resumen") or {}

    plano = {}
    for clave, valor in metricas.items():
        if clave == "monotonia_componentes" and isinstance(valor, dict):
            for sub, subvalor in valor.items():
                plano[f"monotonia_{sub}"] = subvalor
        elif clave == "muletilla_max" and isinstance(valor, dict):
            if valor.get("por_mil") is not None:
                plano["muletilla_por_mil"] = valor["por_mil"]
        else:
            plano[clave] = valor

    items = []
    for nombre, valor in plano.items():
        if isinstance(valor, bool):
            items.append((nombre, 1 if valor else 0, "NUMERIC"))
        elif isinstance(valor, (int, float)):
            items.append((nombre, valor, "NUMERIC"))
        elif isinstance(valor, str):
            items.append((nombre, valor, "CATEGORICAL"))

    for sev in ("bloqueante", "mayor", "menor"):
        if sev in resumen:
            items.append((f"incidencias_{sev}", resumen[sev], "NUMERIC"))

    lote = []
    for nombre, valor, tipo in items:
        cuerpo = {"id": f"{obs}--sc-{_limpio(nombre)}-i{ev.get('intento')}",
                  "traceId": traza, "observationId": obs,
                  "name": nombre, "dataType": tipo,
                  "value": valor if tipo == "NUMERIC" else str(valor)}
        lote.append(_item("score-create", cuerpo, ev.get("ts")))
    return lote


def _scores_cierre(traza: str, ev: dict) -> list:
    """Intentos que necesito el capitulo, y palabras y lineas del texto final."""
    cap = ev.get("capitulo")
    if cap is None:
        return []
    obs = _id_capitulo(traza, cap)
    valores = {
        "intentos": ev.get("intento") or 1,
        "palabras": len(nucleo.palabras(nucleo.cuerpo_capitulo(cap))),
        "lineas": len(nucleo.lineas_capitulo(cap)),
    }
    return [_item("score-create", {
        "id": f"{obs}--sc-{nombre}", "traceId": traza, "observationId": obs,
        "name": nombre, "value": valor, "dataType": "NUMERIC"}, ev.get("ts"))
        for nombre, valor in valores.items()]


def _generacion(traza: str, ev: dict, texto_ok: bool) -> dict:
    """Una invocacion a modelo: cuelga del intento correspondiente.

    Los tokens y el modelo se LEEN del evento, no se estiman. El coste lo
    calcula Langfuse a partir del modelo y del desglose de tokens, de modo que
    una invocacion con la cache caliente sale muy por debajo de la primera. Si
    el evento trae total_cost_usd, ese valor manda sobre el calculo.
    """
    datos = ev.get("datos") or {}
    uso = datos.get("usage") or {}
    rol = datos.get("rol") or datos.get("agentType") or "modelo"

    detalle = {}
    for destino in ("input_tokens", "output_tokens",
                    "cache_creation_input_tokens", "cache_read_input_tokens"):
        if uso.get(destino) is not None:
            clave = {"input_tokens": "input", "output_tokens": "output"}.get(
                destino, destino)
            try:
                detalle[clave] = int(uso[destino] or 0)
            except (TypeError, ValueError):
                pass

    cuerpo = {
        "id": datos.get("id_generacion") or _corto(json.dumps(
            [ev.get("ts"), rol, ev.get("capitulo"), ev.get("intento")],
            default=str)),
        "traceId": traza,
        "name": rol,
        "startTime": datos.get("inicio") or ev.get("ts"),
        "endTime": datos.get("fin") or ev.get("ts"),
        "model": datos.get("model") or datos.get("modelo"),
        "usageDetails": detalle,
        "metadata": {
            "capitulo": ev.get("capitulo"),
            "intento": ev.get("intento"),
            "rol": rol,
            "session_id": datos.get("session_id"),
            "cache_leida": bool(detalle.get("cache_read_input_tokens")),
            "cache_creada": bool(detalle.get("cache_creation_input_tokens")),
        },
    }
    padre = _padre(traza, ev)
    if padre:
        cuerpo["parentObservationId"] = padre
    if datos.get("total_cost_usd") is not None:
        try:
            cuerpo["costDetails"] = {"total": float(datos["total_cost_usd"])}
        except (TypeError, ValueError):
            pass
    if texto_ok:
        if datos.get("prompt"):
            cuerpo["input"] = datos["prompt"]
        if datos.get("respuesta"):
            cuerpo["output"] = datos["respuesta"]
    return cuerpo


# La fase se llama 'entrega' en el pipeline y 'ensamblado' en el panel.
NOMBRES_FASE = {"canon": "canon", "escaleta": "escaleta",
                "redaccion": "redaccion", "revision": "revision",
                "entrega": "ensamblado"}


def construir(cfg: dict, ev: dict, eventos: list, texto_ok: bool) -> list:
    """Traduce UN evento del pipeline a items de ingesta de Langfuse."""
    traza = id_traza(cfg, ev.get("tirada"))
    sello = ev.get("ts")
    tipo = ev.get("evento")
    cap, intento, fase = ev.get("capitulo"), ev.get("intento"), ev.get("fase")
    datos = ev.get("datos") or {}

    lote = [_item("trace-create", _traza(cfg, ev, eventos, texto_ok), sello)]

    if tipo == "fase_inicio" and fase:
        lote.append(_item("span-create", {
            "id": _id_fase(traza, fase), "traceId": traza,
            "name": NOMBRES_FASE.get(fase, fase), "startTime": sello,
            "metadata": {"fase": fase}}, sello))

    elif tipo == "fase_fin" and fase:
        lote.append(_item("span-update", {
            "id": _id_fase(traza, fase), "traceId": traza,
            "name": NOMBRES_FASE.get(fase, fase), "endTime": sello,
            "output": datos}, sello))

    elif tipo == "capitulo_inicio" and cap is not None:
        lote.append(_item("span-create", {
            "id": _id_capitulo(traza, cap), "traceId": traza,
            "parentObservationId": _id_fase(traza, "redaccion"),
            "name": f"capitulo {int(cap):02d}", "startTime": sello,
            "metadata": {"capitulo": cap}}, sello))

    elif tipo in EVENTOS_DE_INTENTO and cap is not None:
        numero = intento or 1
        # El span del capitulo se reafirma por si el capitulo_inicio no llego:
        # la ingesta hace upsert, de modo que repetirlo es inocuo.
        lote.append(_item("span-create", {
            "id": _id_capitulo(traza, cap), "traceId": traza,
            "parentObservationId": _id_fase(traza, "redaccion"),
            "name": f"capitulo {int(cap):02d}", "startTime": sello}, sello))
        lote.append(_item("span-create", {
            "id": _id_intento(traza, cap, numero), "traceId": traza,
            "parentObservationId": _id_capitulo(traza, cap),
            "name": f"intento {numero} ({tipo})", "startTime": sello,
            "input": datos.get("incidencias"),
            "metadata": {"capitulo": cap, "intento": numero, "modo": tipo}},
            sello))

    elif tipo == "validacion":
        if cap is not None and intento is not None:
            lote.append(_item("span-update", {
                "id": _id_intento(traza, cap, intento), "traceId": traza,
                "endTime": sello, "output": datos}, sello))
        cuerpo = {"id": _corto(f"val{traza}{cap}{intento}{sello}"),
                  "traceId": traza, "name": "validacion", "startTime": sello,
                  "input": datos.get("metricas"), "output": datos.get("resumen")}
        padre = _padre(traza, ev)
        if padre:
            cuerpo["parentObservationId"] = padre
        lote.append(_item("event-create", cuerpo, sello))
        lote.extend(_scores_validacion(traza, ev))

    elif tipo == "capitulo_fin" and cap is not None:
        lote.append(_item("span-update", {
            "id": _id_capitulo(traza, cap), "traceId": traza,
            "name": f"capitulo {int(cap):02d}", "endTime": sello,
            "output": datos}, sello))
        lote.extend(_scores_cierre(traza, ev))

    elif tipo == "escalado" and cap is not None:
        lote.append(_item("span-update", {
            "id": _id_capitulo(traza, cap), "traceId": traza,
            "level": "ERROR", "statusMessage": "escalado al autor",
            "output": datos}, sello))
        lote.append(_item("score-create", {
            "id": f"{_id_capitulo(traza, cap)}--sc-escalado", "traceId": traza,
            "observationId": _id_capitulo(traza, cap), "name": "escalado",
            "value": 1, "dataType": "NUMERIC"}, sello))

    elif tipo == "invocacion":
        lote.append(_item("generation-create",
                          _generacion(traza, ev, texto_ok), sello))

    elif tipo == "commit":
        lote.append(_item("event-create", {
            "id": _corto(f"commit{traza}{sello}"), "traceId": traza,
            "name": "commit", "startTime": sello, "input": datos}, sello))

    return lote


# --------------------------------------------------------------------------
# Envio
# --------------------------------------------------------------------------

def _enviar(cred: dict, lote: list) -> bool:
    valores = cred["valores"]
    url = valores["LANGFUSE_BASE_URL"].rstrip("/") + "/api/public/ingestion"
    cuerpo = json.dumps({"batch": lote}, ensure_ascii=False,
                        default=str).encode("utf-8")
    autorizacion = base64.b64encode(
        f"{valores['LANGFUSE_PUBLIC_KEY']}:{valores['LANGFUSE_SECRET_KEY']}"
        .encode("utf-8")).decode("ascii")
    peticion = urllib.request.Request(url, data=cuerpo, method="POST")
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("Authorization", "Basic " + autorizacion)
    with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as respuesta:
        return 200 <= respuesta.status < 300


def flush() -> bool:
    """Envia lo pendiente. Se llama al terminar el proceso y no propaga nada.

    Sin este vaciado las ultimas trazas se perderian: el proceso de un evento
    dura milisegundos y termina antes de que convenga hablar por red.
    """
    global _pendientes
    if not _pendientes:
        return True
    lote, _pendientes = _pendientes, []
    try:
        cfg = nucleo.cargar_config()
        cred = _credenciales()
        if not activo(cfg, cred):
            return False
        if not _enviar(cred, lote):
            _anotar(f"lote de {len(lote)} items rechazado por el servidor")
            return False
        return True
    except SystemExit:
        return False
    except Exception as exc:                     # nunca sube al orquestador
        _anotar(f"lote de {len(lote)} items no enviado: {_motivo(exc)}")
        return False


def encolar(lote: list) -> None:
    global _registrado_atexit
    if not lote:
        return
    _pendientes.extend(lote)
    if not _registrado_atexit:
        atexit.register(flush)
        _registrado_atexit = True


def exportar(ev: dict) -> bool:
    """Punto de entrada que llama eventos.registrar(). No lanza nunca.

    Devuelve True si el evento ha quedado encolado para su envio.
    """
    try:
        cfg = nucleo.cargar_config()
        cred = _credenciales()
        if not activo(cfg, cred):
            return False
        eventos = leer_eventos(cfg, ev.get("tirada"))
        if not any(e.get("ts") == ev.get("ts") for e in eventos):
            eventos.append(ev)
        encolar(construir(cfg, ev, eventos, enviar_texto(cfg)))
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
        description="Exportador a Langfuse. Se engancha en eventos.registrar(). "
                    "Ejecutado a mano solo diagnostica, y nunca muestra claves.")
    parser.add_argument("--estado", action="store_true",
                        help="Dice si la integracion esta activa y que variables "
                             "de entorno faltan, por su nombre y sin su valor.")
    parser.parse_args()
    nucleo.salir(diagnostico(), 0)


if __name__ == "__main__":
    main()
