r"""La API HTTP y el servidor del frontend.

No decide nada sobre la novela: pregunta a los ficheros y al orquestador. Todo
lo que devuelve sale de `novela/` o de `archivo/<nombre>/`, nunca de una
variable que viva entre peticiones. Si se reinicia el servidor a mitad de una
generacion, el progreso se vuelve a leer del disco y no se pierde el sitio.

IDENTIDAD DE UNA NOVELA. La que se esta escribiendo es `actual` y vive en
`novela/`. Las terminadas viven en `archivo/<nombre>/` y su identificador es
esa carpeta. Empezar una novela nueva archiva la anterior antes de vaciar el
sitio, para no perderla.

UNA SOLA GENERACION A LA VEZ, y en segundo plano: `POST /api/novelas` contesta
en cuanto ha arrancado el hilo, y el progreso se sigue por `/eventos`, que lee
`events.jsonl` y va soltando lo nuevo.

Se arranca con un solo comando, que ya dice en que direccion abrirlo:

    .\.venv\Scripts\python.exe -m uvicorn server.api:app --port 8000

Dependencias: fastapi y uvicorn, las dos unicas del proyecto.
"""

import asyncio
import json
import re
import shutil
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "server"))

from fastapi import FastAPI, HTTPException            # noqa: E402
from fastapi.responses import FileResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles           # noqa: E402

import intentos                                       # noqa: E402
import nucleo                                         # noqa: E402
import orquestador                                    # noqa: E402
import runner                                         # noqa: E402

app = FastAPI(title="MyStory1", docs_url=None, redoc_url=None)
ESTATICOS = Path(__file__).resolve().parent / "static"

# Nombres llanos para la pantalla. Aqui, y no en el frontend, porque asi la API
# se puede leer sin traductor y hay un solo sitio que cambiar.
NOMBRE_FASE = {
    "canon": "Inventando el mundo",
    "escaleta": "Planificando los capitulos",
    "redaccion": "Escribiendo",
    "revision": "Releyendo la novela entera",
    "entrega": "Montando el manuscrito",
}
NOMBRE_AGENTE = {
    "arquitecto": "Quien inventa el mundo",
    "escaletista": "Quien planifica",
    "escritor": "Quien escribe",
    "continuista": "Quien busca contradicciones",
    "estilista": "Quien pule la prosa",
    "archivista": "Quien lleva el registro de hechos",
    "revisor-global": "Quien relee la novela entera",
}
# Que esta haciendo cada oficio, segun la fase y el capitulo. Se arma aqui y
# no en el navegador por la misma razon que los nombres de arriba: un solo
# sitio que cambiar, y la API se lee sin traductor.
TAREA_AGENTE = {
    "arquitecto": "Inventando el mundo de la novela",
    "escaletista": "Planificando los capitulos",
    "escritor": "Escribiendo el capitulo {cap}",
    "continuista": "Buscando contradicciones en el capitulo {cap}",
    "estilista": "Puliendo la prosa del capitulo {cap}",
    "archivista": "Anotando los hechos del capitulo {cap}",
    "revisor-global": "Releyendo la novela entera",
}


def _tarea(trabajo: dict) -> dict:
    """El trabajo en curso, dicho para una pantalla. None si no hay ninguno."""
    if not isinstance(trabajo, dict) or not trabajo.get("rol"):
        return None
    rol = trabajo["rol"]
    cap = trabajo.get("capitulo")
    plantilla = TAREA_AGENTE.get(rol, "Trabajando")
    tarea = plantilla.format(cap=cap) if "{cap}" in plantilla and cap else (
        plantilla if "{cap}" not in plantilla else "Trabajando")
    intento = trabajo.get("intento")
    if intento and intento > 1:
        tarea += f" (intento {intento})"
    return {"rol": rol, "agente": NOMBRE_AGENTE.get(rol, rol), "tarea": tarea,
            "desde": trabajo.get("desde")}


NOMBRE_SEVERIDAD = {
    "bloqueante": "Hay que corregirlo",
    "mayor": "Conviene corregirlo",
    "menor": "Aviso",
}


# --------------------------------------------------------------------------
# Donde vive cada novela
# --------------------------------------------------------------------------

def _carpeta_de(id_novela: str) -> Path:
    if id_novela == "actual":
        return RAIZ / "novela"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", id_novela or ""):
        raise HTTPException(400, "identificador de novela no valido")
    carpeta = RAIZ / "archivo" / id_novela
    if not carpeta.is_dir():
        raise HTTPException(404, "esa novela no existe")
    return carpeta


def _titulo_de(carpeta: Path) -> str:
    canon = carpeta / "canon.md"
    if canon.exists():
        for linea in canon.read_text(encoding="utf-8").splitlines():
            if linea.startswith("# "):
                encontrado = re.match(r"#\s*Canon\s*[-—–]\s*(.+)", linea)
                return (encontrado.group(1) if encontrado else linea[2:]).strip()
    return carpeta.name


def _sello(carpeta: Path) -> float:
    candidatos = [carpeta / "events.jsonl", carpeta / "canon.md", carpeta]
    for c in candidatos:
        if c.exists():
            return c.stat().st_mtime
    return 0.0


def _leer_eventos(carpeta: Path) -> list:
    return nucleo.leer_jsonl(carpeta / "events.jsonl")


def _capitulos_de(carpeta: Path) -> list:
    return nucleo.capitulos_existentes(carpeta / "capitulos")


def _texto_capitulo(carpeta: Path, n: int) -> str:
    ruta = carpeta / "capitulos" / f"capitulo-{int(n):02d}.md"
    if not ruta.exists():
        raise HTTPException(404, "ese capitulo todavia no existe")
    return ruta.read_text(encoding="utf-8")


def _estado_json(carpeta: Path) -> dict:
    ruta = carpeta / "estado.json"
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# --------------------------------------------------------------------------
# Listado y creacion
# --------------------------------------------------------------------------

@app.get("/api/novelas")
def listar_novelas():
    novelas = []
    actual = RAIZ / "novela"
    if (actual / "canon.md").exists() or _capitulos_de(actual):
        cfg = nucleo.cargar_config()
        novelas.append({
            "id": "actual",
            "titulo": _titulo_de(actual),
            "en_curso": True,
            "capitulos_escritos": len(_capitulos_de(actual)),
            "capitulos_previstos": cfg.get("capitulos"),
            "premisa": cfg.get("premisa"),
            "actualizada": _sello(actual),
        })
    archivo = RAIZ / "archivo"
    if archivo.is_dir():
        for carpeta in sorted(archivo.iterdir()):
            if not carpeta.is_dir():
                continue
            capitulos = _capitulos_de(carpeta)
            novelas.append({
                "id": carpeta.name,
                "titulo": _titulo_de(carpeta),
                "en_curso": False,
                "capitulos_escritos": len(capitulos),
                "capitulos_previstos": len(capitulos),
                "premisa": None,
                "actualizada": _sello(carpeta),
            })
    return {"novelas": novelas}


def _apodo(titulo: str) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "-",
                    (titulo or "novela").lower().replace("á", "a")
                    .replace("é", "e").replace("í", "i").replace("ó", "o")
                    .replace("ú", "u").replace("ñ", "n")).strip("-")
    return limpio or "novela"


def _archivar_actual() -> str:
    """Guarda la novela en curso en archivo/<nombre>/ antes de empezar otra."""
    actual = RAIZ / "novela"
    if not (actual / "canon.md").exists() and not _capitulos_de(actual):
        return None
    base = _apodo(_titulo_de(actual))
    destino = RAIZ / "archivo" / base
    sufijo = 2
    while destino.exists():
        destino = RAIZ / "archivo" / f"{base}-{sufijo}"
        sufijo += 1
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(actual, destino)
    manuscrito = RAIZ / "manuscrito.md"
    if manuscrito.exists():
        shutil.copy2(manuscrito, destino / "manuscrito.md")
    return destino.name


def _vaciar_actual() -> None:
    actual = RAIZ / "novela"
    for nombre in ("canon.md", "escaleta.json", "events.jsonl",
                   "langfuse-enviados.txt"):
        ruta = actual / nombre
        if ruta.exists():
            ruta.unlink()
    for sub in ("capitulos", "informes", "intentos"):
        carpeta = actual / sub
        if carpeta.is_dir():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
    (actual / "estado.json").write_text(
        json.dumps(nucleo.SEMILLA_ESTADO, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    manuscrito = RAIZ / "manuscrito.md"
    if manuscrito.exists():
        manuscrito.unlink()


def _guardar_peticion(premisa: str, capitulos: int, objetivo: int) -> dict:
    """Escribe en config.json SOLO las tres claves que pide la web.

    Quien decide cuales son esas tres es nucleo.actualizar_config(), que no
    acepta ninguna otra. Antes la regla estaba escrita aqui y repetida en el
    ciclo de mejora: bastaba con que alguien anadiese una linea en cualquiera
    de los dos sitios para saltarsela sin querer.
    """
    return nucleo.actualizar_config(premisa=premisa, capitulos=capitulos,
                                    objetivo=objetivo)


_hilo = None


@app.post("/api/novelas")
async def crear_novela(peticion: dict):
    """Arranca una novela y contesta en el acto: la generacion va detras."""
    global _hilo
    if orquestador.generando():
        raise HTTPException(409, "ya hay una novela generandose")

    premisa = (peticion.get("premisa") or "").strip()
    if len(premisa) < 20:
        raise HTTPException(400, "la premisa tiene que decir algo: al menos 20 letras")
    try:
        capitulos = int(peticion.get("capitulos") or 3)
        objetivo = int(peticion.get("objetivo") or 4)
    except (TypeError, ValueError):
        raise HTTPException(400, "el numero de capitulos y el tamano deben ser numeros")
    if not 1 <= capitulos <= 20:
        raise HTTPException(400, "el numero de capitulos tiene que estar entre 1 y 20")
    if not 1 <= objetivo <= 400:
        raise HTTPException(400, "el tamano tiene que estar entre 1 y 400")

    archivada = _archivar_actual()
    _vaciar_actual()
    cfg = _guardar_peticion(premisa, capitulos, objetivo)

    _hilo = threading.Thread(target=orquestador.generar, kwargs={"cfg": cfg},
                             daemon=True)
    _hilo.start()
    return {"id": "actual", "arrancada": True, "archivada": archivada,
            "capitulos": capitulos}


@app.post("/api/novelas/{id_novela}/detener")
def detener(id_novela: str):
    if id_novela != "actual":
        raise HTTPException(400, "solo se puede detener la novela en curso")
    orquestador.pedir_parada()
    return {"detencion": "pedida"}


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------

@app.get("/api/novelas/{id_novela}")
def ver_novela(id_novela: str):
    carpeta = _carpeta_de(id_novela)
    estado = _estado_json(carpeta)
    capitulos = _capitulos_de(carpeta)
    titulos = {}
    escaleta = carpeta / "escaleta.json"
    if escaleta.exists():
        try:
            plan = json.loads(escaleta.read_text(encoding="utf-8"))
            titulos = {c.get("n"): c.get("titulo")
                       for c in plan.get("capitulos", [])}
        except (OSError, json.JSONDecodeError):
            titulos = {}

    marcha = orquestador.estado_actual() if id_novela == "actual" else {}
    return {
        "id": id_novela,
        "titulo": _titulo_de(carpeta),
        "en_curso": id_novela == "actual",
        "generando": bool(marcha.get("generando")),
        "fases_terminadas": marcha.get("fases_terminadas", []),
        "capitulos": [{"n": n, "titulo": titulos.get(n) or f"Capitulo {n}"}
                      for n in capitulos],
        "capitulos_previstos": marcha.get("capitulos_previstos") or len(capitulos),
        "personajes": estado.get("entidades", []),
        "hechos": estado.get("hechos", []),
        "hilos_abiertos": orquestador.hilos_abiertos(estado),
        "hilos_cerrados": [h for h in estado.get("hilos", [])
                           if isinstance(h, dict)
                           and h.get("estado") != "abierto"],
        "resumenes": estado.get("resumenes", []),
        "gastado_usd": marcha.get("gastado_usd"),
        "invocaciones": marcha.get("invocaciones"),
        "max_invocaciones": marcha.get("max_invocaciones"),
    }


@app.get("/api/novelas/{id_novela}/capitulos/{n}")
def ver_capitulo(id_novela: str, n: int):
    carpeta = _carpeta_de(id_novela)
    historial = intentos.historial(n, raiz=carpeta)
    for intento in historial["intentos"]:
        for incidencia in intento["incidencias"]:
            incidencia["que_es"] = NOMBRE_SEVERIDAD.get(
                incidencia.get("severidad"), "Aviso")
    return {
        "id": id_novela,
        "capitulo": n,
        "texto": _texto_capitulo(carpeta, n),
        "historial": historial,
    }


@app.get("/api/novelas/{id_novela}/coste")
def ver_coste(id_novela: str):
    """Desglose por capitulo y por agente, sacado de los eventos."""
    carpeta = _carpeta_de(id_novela)
    por_capitulo, por_agente = {}, {}
    total = arranque = trabajo = 0.0
    con_cache = sin_cache = 0

    for ev in _leer_eventos(carpeta):
        if ev.get("evento") != "invocacion":
            continue
        datos = ev.get("datos") or {}
        try:
            coste = float(datos.get("total_cost_usd") or 0.0)
        except (TypeError, ValueError):
            coste = 0.0
        uso = datos.get("usage") or {}
        leido = int(uso.get("cache_read_input_tokens") or 0)
        total += coste
        if leido > 0:
            trabajo += coste
            con_cache += 1
        else:
            arranque += coste
            sin_cache += 1

        capitulo = ev.get("capitulo")
        clave = capitulo if capitulo is not None else 0
        fila = por_capitulo.setdefault(clave, {"capitulo": capitulo,
                                               "coste_usd": 0.0, "llamadas": 0})
        fila["coste_usd"] += coste
        fila["llamadas"] += 1

        rol = datos.get("rol") or "desconocido"
        agente = por_agente.setdefault(rol, {
            "rol": rol, "nombre": NOMBRE_AGENTE.get(rol, rol),
            "coste_usd": 0.0, "llamadas": 0, "tokens_escritos": 0})
        agente["coste_usd"] += coste
        agente["llamadas"] += 1
        agente["tokens_escritos"] += int(uso.get("output_tokens") or 0)

    # Reescrituras por capitulo y metricas, que van en la misma pantalla.
    reescrituras = {}
    for ev in _leer_eventos(carpeta):
        if ev.get("evento") in ("reescritura", "parche") and ev.get("capitulo"):
            reescrituras[ev["capitulo"]] = reescrituras.get(ev["capitulo"], 0) + 1

    for fila in por_capitulo.values():
        fila["coste_usd"] = round(fila["coste_usd"], 6)
        fila["reescrituras"] = reescrituras.get(fila["capitulo"], 0)
    for fila in por_agente.values():
        fila["coste_usd"] = round(fila["coste_usd"], 6)

    return {
        "id": id_novela,
        # Las novelas escritas conversando con Claude Code no dejan eventos
        # 'invocacion': su gasto vive en los transcripts, no en events.jsonl.
        # Vale mas decirlo que ensenar un cero que parece gratis.
        "hay_datos": bool(por_agente),
        "total_usd": round(total, 6),
        "arranque_usd": round(arranque, 6),
        "trabajo_usd": round(trabajo, 6),
        "llamadas_con_cache": con_cache,
        "llamadas_sin_cache": sin_cache,
        "por_capitulo": sorted(por_capitulo.values(),
                               key=lambda f: (f["capitulo"] is None,
                                              f["capitulo"] or 0)),
        "por_agente": sorted(por_agente.values(),
                             key=lambda f: -f["coste_usd"]),
        "max_invocaciones": runner.max_invocaciones(nucleo.cargar_config()),
    }


# --------------------------------------------------------------------------
# Progreso en vivo
# --------------------------------------------------------------------------

def _frase(ev: dict, previstos) -> str:
    """Un evento del registro, dicho en cristiano."""
    tipo = ev.get("evento")
    cap = ev.get("capitulo")
    datos = ev.get("datos") or {}
    if tipo == "fase_inicio":
        return NOMBRE_FASE.get(ev.get("fase"), ev.get("fase") or "")
    if tipo == "fase_fin":
        return f"Terminado: {NOMBRE_FASE.get(ev.get('fase'), ev.get('fase'))}"
    if tipo == "capitulo_inicio":
        de = f" de {previstos}" if previstos else ""
        return f"Empezando el capitulo {cap}{de}"
    if tipo == "borrador":
        return f"Escribiendo el capitulo {cap}"
    if tipo == "validacion":
        resumen = datos.get("resumen") or {}
        graves = resumen.get("bloqueante") or 0
        avisos = resumen.get("mayor") or 0
        if graves:
            return (f"El capitulo {cap} tiene {graves} error(es) que hay que "
                    f"corregir")
        if avisos:
            return f"El capitulo {cap} tiene {avisos} aviso(s) por revisar"
        return f"El capitulo {cap} ha pasado todas las comprobaciones"
    if tipo == "reescritura":
        return f"Reescribiendo entero el capitulo {cap}"
    if tipo == "parche":
        return f"Retocando algunos parrafos del capitulo {cap}"
    if tipo == "capitulo_fin":
        return f"Capitulo {cap} terminado"
    if tipo == "escalado":
        return (f"El capitulo {cap} no ha salido bien despues de varios "
                f"intentos. Hace falta que decidas tu.")
    if tipo == "invocacion":
        # Antes se ocultaban por ruidosas. Se ensenan porque son justo lo que
        # deja ver que oficio ha intervenido y cuanto ha tardado.
        quien = NOMBRE_AGENTE.get(datos.get("rol"), datos.get("rol") or "")
        if not quien:
            return None
        if datos.get("error"):
            return f"{quien}: ha fallado la llamada"
        segundos = datos.get("duracion_s")
        cuanto = f" en {round(float(segundos))} s" if segundos else ""
        return f"{quien} ha terminado su parte{cuanto}"
    if tipo == "commit":
        return None
    return None


@app.get("/api/novelas/{id_novela}/eventos")
async def progreso(id_novela: str):
    """Progreso en vivo. Relee events.jsonl y va soltando lo nuevo."""
    if id_novela != "actual":
        raise HTTPException(400, "solo la novela en curso tiene progreso en vivo")
    carpeta = RAIZ / "novela"

    async def flujo():
        vistos = 0
        ocioso = 0
        while True:
            cfg = nucleo.cargar_config()
            previstos = cfg.get("capitulos")
            marcha = orquestador.estado_actual(cfg)
            # Solo la tirada que se esta mirando. El fichero guarda todas las
            # generaciones que ha habido, y soltarlas enteras mezclaba en la
            # misma bitacora capitulos de novelas distintas.
            todos = [e for e in _leer_eventos(carpeta)
                     if e.get("tirada") == marcha["tirada"]]
            nuevos = todos[vistos:]
            vistos = len(todos)
            for ev in nuevos:
                frase = _frase(ev, previstos)
                if not frase:
                    continue
                yield "data: " + json.dumps(
                    {"tipo": "paso", "texto": frase, "evento": ev.get("evento"),
                     "capitulo": ev.get("capitulo"), "ts": ev.get("ts")},
                    ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps(
                {"tipo": "estado",
                 "trabajando": _tarea(marcha.get("trabajando")),
                 "terminada": "entrega" in (marcha.get("fases_terminadas") or []),
                 **{k: marcha[k] for k in
                    ("generando", "gastado_usd", "invocaciones",
                     "max_invocaciones", "capitulos_escritos",
                     "capitulo_en_curso", "fases_terminadas", "escalado",
                     "reescrituras", "parches")}},
                ensure_ascii=False) + "\n\n"
            if not marcha["generando"]:
                ocioso += 1
                # Se dan dos vueltas de gracia por si el hilo aun no ha
                # escrito su marca; despues se cierra el flujo.
                if ocioso > 2:
                    yield "data: " + json.dumps(
                        {"tipo": "fin"}, ensure_ascii=False) + "\n\n"
                    return
            else:
                ocioso = 0
            await asyncio.sleep(1.5)

    return StreamingResponse(flujo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/api/configuracion")
def configuracion():
    """Los valores actuales, para rellenar el formulario por defecto."""
    cfg = nucleo.cargar_config()
    return {"premisa": cfg.get("premisa"),
            "capitulos": cfg.get("capitulos"),
            "objetivo": (cfg.get("longitud") or {}).get("objetivo"),
            "unidad": (cfg.get("longitud") or {}).get("unidad"),
            "max_invocaciones": runner.max_invocaciones(cfg)}


# --------------------------------------------------------------------------
# El frontend
# --------------------------------------------------------------------------

@app.get("/")
def portada():
    return FileResponse(ESTATICOS / "index.html")


app.mount("/", StaticFiles(directory=str(ESTATICOS)), name="static")
