"""Recorre las cinco fases de una novela sin que nadie le hable.

Es la pieza que faltaba. Hasta ahora la generacion la dirigia el autor
conversando con Claude Code, siguiendo los comandos de `.claude/commands/` y
las skills de `.claude/skills/`. Este modulo hace ese mismo recorrido solo, para
que un boton de la web pueda lanzarlo.

QUE REUTILIZA Y QUE NO. No reimplementa ni una validacion. Importa los scripts
de `scripts/` y llama a sus funciones: `medir`, `repeticion` y `continuidad` a
traves de `informes.informe_capitulo()`, que ya ejecuta los tres y funde sus
incidencias con las del continuista; `informes.guardar()` para persistir;
`ensamblar` para el manuscrito; `eventos.registrar()` para el registro. Son
importaciones y no subprocesos a proposito: es el mismo codigo con el mismo
resultado, sin pagar un proceso nuevo por validacion.

Lo unico que pide a un modelo son los seis pasos creativos, y siempre a traves
de `runner.invocar()`.

EL COSTE SE REGISTRA COMO EVENTO. Despues de cada invocacion se escribe un
evento `invocacion` con el rol, el modelo, los cuatro contadores de token y el
coste que ha devuelto Claude Code. Eso es exactamente lo que SPEC 14.5 dejaba
previsto para el dia que existiera un envoltorio asi, y resuelve tres cosas de
una vez: el gasto queda en `events.jsonl` y sobrevive a un reinicio, la traza
de Langfuse se completa sola con sus generaciones, y la API puede desglosar el
coste por capitulo y por agente sin guardar nada aparte.

NADA EN MEMORIA. El progreso se deduce de los ficheros: si existe
`novela/canon.md` la fase 1 esta hecha, si existe `novela/escaleta.json` la 2,
y los capitulos escritos se cuentan en `novela/capitulos/`. Lo gastado se suma
de los eventos `invocacion` de la tirada. Reiniciar el servidor a mitad no
pierde el sitio: se retoma donde estaba.

Python 3.12, solo biblioteca estandar.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "server"))

import continuidad          # noqa: E402
import eventos              # noqa: E402
import informes             # noqa: E402
import medir                # noqa: E402
import nucleo               # noqa: E402
import repeticion           # noqa: E402
import runner               # noqa: E402

# Senales en disco, que es donde tiene que estar todo lo que deba sobrevivir a
# un reinicio. Nada de banderas en memoria.
SENAL_PARAR = "novela/.detener"
SENAL_TRABAJANDO = "novela/.generando"
FASES = ("canon", "escaleta", "redaccion", "revision", "entrega")


class Detenido(Exception):
    """El autor ha pedido parar. Se sube hasta generar(), que cierra limpio."""


class SinPresupuesto(Exception):
    """Se ha alcanzado el tope de gasto de la novela."""


# --------------------------------------------------------------------------
# Senales y estado, todo en ficheros
# --------------------------------------------------------------------------

def _ruta(nombre: str) -> Path:
    return nucleo.raiz() / nombre


def pedir_parada() -> None:
    ruta = _ruta(SENAL_PARAR)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("parar", encoding="utf-8")


def _limpiar_parada() -> None:
    ruta = _ruta(SENAL_PARAR)
    if ruta.exists():
        try:
            ruta.unlink()
        except OSError:
            pass


def _comprobar_parada() -> None:
    if _ruta(SENAL_PARAR).exists():
        raise Detenido("el autor ha pedido detener la generacion")


def generando() -> bool:
    """Si hay una generacion viva. Una y solo una a la vez."""
    ruta = _ruta(SENAL_TRABAJANDO)
    if not ruta.exists():
        return False
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = datos.get("pid")
    if not isinstance(pid, int):
        return False
    # Si el proceso ya no esta, la senal es basura de un reinicio: se ignora.
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return True
    return True


def _marcar_trabajando(tirada: str) -> None:
    ruta = _ruta(SENAL_TRABAJANDO)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"pid": os.getpid(), "tirada": tirada,
                                "desde": time.time()}), encoding="utf-8")


def _desmarcar() -> None:
    ruta = _ruta(SENAL_TRABAJANDO)
    if ruta.exists():
        try:
            ruta.unlink()
        except OSError:
            pass


def _eventos_de_tirada(cfg: dict, tirada: str = None) -> list:
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


def gastado(cfg: dict, tirada: str = None) -> float:
    """Lo que lleva costando esta novela, sumado de los eventos."""
    tirada = tirada or eventos.tirada_vigente(cfg)
    total = 0.0
    for ev in _eventos_de_tirada(cfg, tirada):
        if ev.get("evento") != "invocacion":
            continue
        try:
            total += float((ev.get("datos") or {}).get("total_cost_usd") or 0.0)
        except (TypeError, ValueError):
            pass
    return round(total, 6)


def estado_actual(cfg: dict = None) -> dict:
    """Por donde va la novela, deducido de los ficheros. Sin memoria."""
    cfg = cfg or nucleo.cargar_config()
    tirada = eventos.tirada_vigente(cfg)
    hechos = _eventos_de_tirada(cfg, tirada)
    fases_hechas = {e.get("fase") for e in hechos
                    if e.get("evento") == "fase_fin" and e.get("fase")}
    escritos = nucleo.capitulos_existentes()
    ultimo = next((e for e in reversed(hechos)
                   if e.get("evento") in ("capitulo_inicio", "borrador",
                                          "validacion", "reescritura",
                                          "parche", "capitulo_fin")), None)
    return {
        "tirada": tirada,
        "generando": generando(),
        "parada_pedida": _ruta(SENAL_PARAR).exists(),
        "canon": (nucleo.raiz() / "novela" / "canon.md").exists(),
        "escaleta": (nucleo.raiz() / "novela" / "escaleta.json").exists(),
        "capitulos_previstos": cfg.get("capitulos"),
        "capitulos_escritos": escritos,
        "capitulo_en_curso": (ultimo or {}).get("capitulo"),
        "fases_terminadas": sorted(fases_hechas),
        "gastado_usd": gastado(cfg, tirada),
        "tope_usd": runner.tope_usd(cfg),
        "escalado": any(e.get("evento") == "escalado" for e in hechos),
    }


# --------------------------------------------------------------------------
# Hablar con el modelo
# --------------------------------------------------------------------------

_JSON = re.compile(r"\{.*\}", re.S)


def _json_de(texto: str) -> dict:
    """Saca el objeto JSON de una respuesta que puede traer texto alrededor."""
    encontrado = _JSON.search(texto or "")
    if not encontrado:
        return {}
    try:
        return json.loads(encontrado.group(0))
    except json.JSONDecodeError:
        return {}


class Sesiones(dict):
    """session_id vigente de cada rol, para reanudar y reaprovechar la cache.

    Vive en memoria a proposito: es una optimizacion, no progreso. Si el
    servidor se reinicia se pierde la cache, no el sitio en la novela.
    """


def invocar(rol, prompt, cfg, sesiones, fase=None, capitulo=None, intento=None):
    """Una llamada al modelo, con su evento de coste. Levanta si no hay saldo."""
    _comprobar_parada()
    ya = gastado(cfg)
    tope = runner.tope_usd(cfg)
    if ya >= tope:
        raise SinPresupuesto(
            f"la novela lleva gastados {ya:.4f} USD y el tope es {tope:.2f} USD")

    resultado = runner.invocar(rol, prompt, cfg, sesiones.get(rol), ya)
    if resultado["session_id"]:
        sesiones[rol] = resultado["session_id"]

    # El coste va al registro pase lo que pase: si la llamada fallo a medias,
    # lo gastado se ha gastado igual.
    if resultado["coste_usd"] or resultado["ok"]:
        eventos.registrar("invocacion", fase=fase, capitulo=capitulo,
                          intento=intento, datos={
                              "rol": rol,
                              "model": resultado["modelo"],
                              "session_id": resultado["session_id"],
                              "id_generacion": f"{rol}-{time.time():.3f}",
                              "usage": resultado["tokens"],
                              "total_cost_usd": resultado["coste_usd"],
                              "cache_aprovechada": resultado["cache_aprovechada"],
                              "duracion_s": resultado["duracion_s"],
                          })
    if not resultado["ok"]:
        raise RuntimeError(f"{rol}: {resultado['error']}")
    return resultado


def _huella(ruta: Path):
    """Como esta un fichero ahora mismo, o None si no existe."""
    try:
        return hashlib.sha1(ruta.read_bytes()).hexdigest()
    except OSError:
        return None


def escribiendo(rol, prompt, cfg, sesiones, destino, que, avisar, **contexto):
    """Invoca a un rol que TIENE que dejar un fichero cambiado, y lo comprueba.

    Un paso que no escribe nada no da error por su cuenta: el modelo contesta
    que lo ha hecho y se queda tan ancho. Con alguien mirando se ve enseguida;
    desatendido, el orquestador sigue adelante creyendo que hay capitulo y
    envenena todo lo que viene detras. Asi que se compara el fichero antes y
    despues, y si no ha cambiado se repite una vez.

    Los dos desenlaces malos NO son el mismo y no se tratan igual:

      - El fichero no existe. Ahi no hay nada que validar ni que corregir, y
        seguir es imposible: se para con un motivo claro.
      - El fichero existe pero ha quedado igual. Eso no es un fallo de
        escritura, es un capitulo que no mejora, y para eso ya esta el bucle
        de validacion, que lo revalidara y acabara escalando si toca. Abortar
        aqui seria robarle su trabajo.
    """
    antes = _huella(destino)
    invocar(rol, prompt, cfg, sesiones, **contexto)
    ahora = _huella(destino)

    if ahora is None:
        # Solo aqui se reintenta. Repetir por un texto que no cambia seria
        # pagar otra invocacion a cambio de nada.
        avisar(f"El paso de {que} no ha dejado el fichero; se repite una vez.")
        invocar(rol, prompt, cfg, sesiones, **contexto)
        ahora = _huella(destino)
        if ahora is None:
            raise RuntimeError(
                f"{rol} no ha llegado a escribir {destino.name} en dos "
                f"intentos. La generacion no puede seguir sin eso.")

    if ahora == antes:
        avisar(f"El paso de {que} ha dejado el texto igual que estaba.")
        return False
    return True


# --------------------------------------------------------------------------
# El contexto que recibe cada rol
# --------------------------------------------------------------------------

def _bloque(titulo: str, cuerpo) -> str:
    """Un bloque del contexto, con un separador que no choque con Markdown.

    El canon trae sus propios encabezados `##`, asi que titular los bloques
    tambien con `##` dejaria al modelo sin saber donde acaba uno y empieza
    el siguiente.
    """
    if isinstance(cuerpo, (dict, list)):
        cuerpo = json.dumps(cuerpo, ensure_ascii=False, indent=2)
    return f"===== {titulo.upper()} =====\n\n{cuerpo}\n"


def _contexto_capitulo(n: int, cfg: dict) -> str:
    """Los siete bloques que el escritor exige, o no escribe y para.

    Es la misma lista del paso 1 de la skill `escribir-capitulo`. Se ensambla
    aqui porque `--restricted` no carga las skills del proyecto.
    """
    estado = nucleo.cargar_estado()
    escaleta = nucleo.cargar_escaleta()
    plan = next((c for c in escaleta.get("capitulos", [])
                 if c.get("n") == n), {})
    anterior = next((r for r in estado.get("resumenes", [])
                     if r.get("capitulo") == n - 1), {})
    partes = [
        _bloque("Canon de la novela", nucleo.leer_canon()),
        _bloque("Plan de este capitulo", plan),
        _bloque("Hechos ya establecidos", estado.get("hechos", [])),
        _bloque("Hilos abiertos", [h for h in estado.get("hilos", [])
                                   if h.get("estado") == "abierto"]),
        _bloque("Resumenes de los capitulos anteriores",
                estado.get("resumenes", [])),
        _bloque("Ultimas lineas literales del capitulo anterior",
                anterior.get("ultimas_lineas") or
                "(no hay capitulo anterior: este es el primero)"),
        _bloque("Frases prohibidas, ya usadas", estado.get("frases_usadas", [])),
        _bloque("Tamano objetivo", cfg.get("longitud")),
        _bloque("Tipos de apertura ya usados", estado.get("aperturas", [])),
    ]
    return "\n".join(partes)


# --------------------------------------------------------------------------
# Fase 1 y 2
# --------------------------------------------------------------------------

def fase_canon(cfg, sesiones, avisar):
    if (nucleo.raiz() / "novela" / "canon.md").exists():
        avisar("El canon ya estaba hecho, se reaprovecha.")
        return
    eventos.registrar("fase_inicio", fase="canon")
    avisar("Creando la biblia de la novela: personajes, mundo y reglas.")
    escribiendo("arquitecto",
                _bloque("Premisa", cfg.get("premisa"))
                + _bloque("Numero de capitulos", cfg.get("capitulos"))
                + _bloque("Tamano de cada capitulo", cfg.get("longitud"))
                + "\nEscribe `novela/canon.md` con los diez encabezados que "
                  "exige tu formato. No escribas ningun otro fichero.",
                cfg, sesiones, nucleo.raiz() / "novela" / "canon.md",
                "inventar el mundo", avisar, fase="canon")
    eventos.registrar("fase_fin", fase="canon", datos={"creado": True})


def fase_escaleta(cfg, sesiones, avisar):
    if (nucleo.raiz() / "novela" / "escaleta.json").exists():
        avisar("El plan de capitulos ya estaba hecho, se reaprovecha.")
        return
    eventos.registrar("fase_inicio", fase="escaleta")
    avisar(f"Planificando los {cfg.get('capitulos')} capitulos.")
    escribiendo("escaletista",
                _bloque("Canon aprobado", nucleo.leer_canon())
                + _bloque("Configuracion", {"capitulos": cfg.get("capitulos"),
                                            "longitud": cfg.get("longitud")})
                + "\nEscribe `novela/escaleta.json` con el plan completo. No "
                  "escribas ningun otro fichero.",
                cfg, sesiones, nucleo.raiz() / "novela" / "escaleta.json",
                "planificar los capitulos", avisar, fase="escaleta")

    revision = continuidad.modo_escaleta(cfg)
    graves = [i for i in revision.get("incidencias", [])
              if i.get("severidad") == "bloqueante"]
    if graves:
        avisar(f"El plan tenia {len(graves)} problema(s) de fondo; se corrige.")
        invocar("escaletista",
                _bloque("Problemas detectados en tu plan", graves)
                + "\nCorrigelos y vuelve a escribir `novela/escaleta.json`.",
                cfg, sesiones, fase="escaleta")
    eventos.registrar("fase_fin", fase="escaleta",
                      datos={"capitulos": cfg.get("capitulos")})


# --------------------------------------------------------------------------
# Fase 3: el bucle de capitulos
# --------------------------------------------------------------------------

def _validar(n, cfg, sesiones, intento, avisar):
    """Las cuatro validaciones, fundidas y persistidas. Devuelve el informe."""
    avisar(f"Comprobando el capitulo {n}: longitud, frases repetidas y "
           f"contradicciones.")
    estado = nucleo.cargar_estado()

    # Atajo barato del paso 1 de la skill: si la longitud esta fuera de norma,
    # no se gasta una lectura entera del continuista en algo ya perdido.
    longitud = medir.medir(n, cfg)
    continuista = None
    if longitud.get("en_norma"):
        mecanica = continuidad.modo_capitulo(n, cfg)
        respuesta = invocar(
            "continuista",
            _bloque("Canon", nucleo.leer_canon())
            + _bloque("Hechos establecidos", estado.get("hechos", []))
            + _bloque("Hilos abiertos", [h for h in estado.get("hilos", [])
                                         if h.get("estado") == "abierto"])
            + _bloque("Plan de este capitulo",
                      next((c for c in nucleo.cargar_escaleta().get("capitulos", [])
                            if c.get("n") == n), {}))
            + _bloque("Texto del capitulo", nucleo.cuerpo_capitulo(n))
            + _bloque("Comprobaciones mecanicas ya hechas, no las repitas",
                      mecanica)
            + "\nDevuelve solo tu JSON de incidencias. No escribas ficheros.",
            cfg, sesiones, fase="redaccion", capitulo=n, intento=intento)
        continuista = _json_de(respuesta["texto"])

    informe = informes.informe_capitulo(n, cfg, estado, continuista, intento)
    informes.guardar(informe, f"capitulo_{n:02d}.json")
    eventos.registrar("validacion", capitulo=n, intento=intento,
                      datos={"metricas": {
                                 "unidad": informe["metricas"]["longitud"].get("unidad"),
                                 "medido": informe["metricas"]["longitud"].get("medido"),
                                 "objetivo": informe["metricas"]["longitud"].get("objetivo"),
                                 "en_norma": informe["metricas"]["longitud"].get("en_norma"),
                                 **{k: v for k, v in informe["metricas"]["repeticion"].items()
                                    if k in ("solape", "frases_recicladas",
                                             "tipo_apertura")}},
                             "resumen": informe["resumen"]})
    return informe


def _escribir_capitulo(n, cfg, sesiones, avisar):
    """Un capitulo entero: borrador, validaciones, correcciones, pulido."""
    eventos.registrar("capitulo_inicio", capitulo=n)
    intento = 1
    maximo = int(cfg["validacion"].get("max_reescrituras", 3))

    avisar(f"Escribiendo el capitulo {n} de {cfg.get('capitulos')}.")
    escribiendo("escritor",
                _contexto_capitulo(n, cfg)
                + f"\nModo: borrador. Escribe "
                  f"`novela/capitulos/capitulo-{n:02d}.md` desde cero. No "
                  f"escribas ningun otro fichero.",
                cfg, sesiones, nucleo.ruta_capitulo(n),
                f"escribir el capitulo {n}", avisar,
                fase="redaccion", capitulo=n, intento=intento)
    eventos.registrar("borrador", capitulo=n, intento=intento)

    while True:
        informe = _validar(n, cfg, sesiones, intento, avisar)
        graves = [i for i in informe["incidencias"]
                  if i.get("severidad") == "bloqueante"]
        mayores = [i for i in informe["incidencias"]
                   if i.get("severidad") == "mayor"]

        if graves:
            if intento >= maximo:
                eventos.registrar("escalado", capitulo=n, intento=intento,
                                  datos={"incidencias": graves})
                avisar(f"El capitulo {n} sigue con {len(graves)} error(es) que "
                       f"hay que corregir tras {intento} intentos. Se para.")
                return False
            avisar(f"El capitulo {n} tiene {len(graves)} error(es) que hay que "
                   f"corregir. Se reescribe entero.")
            escribiendo("escritor",
                        _contexto_capitulo(n, cfg)
                        + _bloque("Texto actual", nucleo.cuerpo_capitulo(n))
                        + _bloque("Errores que hay que corregir", graves)
                        + f"\nModo: reescritura. Vuelve a escribir "
                          f"`novela/capitulos/capitulo-{n:02d}.md` entero "
                          f"resolviendo cada uno.",
                        cfg, sesiones, nucleo.ruta_capitulo(n),
                        f"reescribir el capitulo {n}", avisar,
                        fase="redaccion", capitulo=n, intento=intento)
            eventos.registrar("reescritura", capitulo=n, intento=intento)
            intento += 1
            continue

        if mayores:
            if intento >= maximo:
                avisar(f"Quedan {len(mayores)} aviso(s) menores en el capitulo "
                       f"{n}; se acepta asi para no dar mas vueltas.")
            else:
                avisar(f"El capitulo {n} tiene {len(mayores)} aviso(s); se "
                       f"retocan solo esos parrafos.")
                escribiendo("escritor",
                            _bloque("Texto actual", nucleo.cuerpo_capitulo(n))
                            + _bloque("Avisos, cada uno con su cita", mayores)
                            + f"\nModo: parche. Corrige SOLO esos parrafos de "
                              f"`novela/capitulos/capitulo-{n:02d}.md`. El "
                              f"resto debe salir igual.",
                            cfg, sesiones, nucleo.ruta_capitulo(n),
                            f"retocar el capitulo {n}", avisar,
                            fase="redaccion", capitulo=n, intento=intento)
                eventos.registrar("parche", capitulo=n, intento=intento)
                intento += 1
                continue    # un parche SIEMPRE se revalida
        break

    # Pulido y archivo.
    avisar(f"Puliendo la prosa del capitulo {n}.")
    invocar("estilista",
            _bloque("Texto del capitulo", nucleo.cuerpo_capitulo(n))
            + _bloque("Frases ya usadas que no puedes introducir",
                      nucleo.cargar_estado().get("frases_usadas", []))
            + _bloque("Tamano objetivo", cfg.get("longitud"))
            + f"\nPule `novela/capitulos/capitulo-{n:02d}.md` sin cambiar "
              f"hechos ni dialogo sustantivo.",
            cfg, sesiones, fase="redaccion", capitulo=n, intento=intento)

    # Tras el estilista se vuelve a medir SIEMPRE: es el fallo mas silencioso
    # del sistema, y por eso es invariante del repositorio.
    despues = medir.medir(n, cfg)
    if not despues.get("en_norma"):
        avisar(f"El pulido dejo el capitulo {n} fuera de tamano; se corrige.")
        invocar("estilista",
                _bloque("Texto actual", nucleo.cuerpo_capitulo(n))
                + _bloque("Tamano medido y esperado", despues)
                + "\nAjusta el tamano sin tocar los hechos.",
                cfg, sesiones, fase="redaccion", capitulo=n, intento=intento)
        despues = medir.medir(n, cfg)
    repeticion.analizar(n, cfg, nucleo.cargar_estado())

    avisar(f"Guardando lo que pasa en el capitulo {n} en el registro de hechos.")
    escribiendo("archivista",
                _bloque("Texto del capitulo", nucleo.cuerpo_capitulo(n))
                + _bloque("Estado actual", nucleo.cargar_estado())
                + f"\nActualiza `novela/estado.json` con lo que aporta el "
                  f"capitulo {n}. Eres el unico que escribe ese fichero.",
                cfg, sesiones, nucleo.raiz() / "novela" / "estado.json",
                f"anotar los hechos del capitulo {n}", avisar,
                fase="redaccion", capitulo=n, intento=intento)

    estado = nucleo.cargar_estado()
    eventos.registrar("capitulo_fin", capitulo=n, intento=intento,
                      datos={"hechos": len(estado.get("hechos", [])),
                             "hilos_abiertos": len([h for h in estado.get("hilos", [])
                                                    if h.get("estado") == "abierto"])})
    avisar(f"Capitulo {n} terminado en {intento} intento(s).")
    return True


def fase_redaccion(cfg, sesiones, avisar):
    previstos = int(cfg.get("capitulos") or 0)
    if not any(e.get("evento") == "fase_inicio" and e.get("fase") == "redaccion"
               for e in _eventos_de_tirada(cfg, eventos.tirada_vigente(cfg))):
        eventos.registrar("fase_inicio", fase="redaccion")
    for n in range(1, previstos + 1):        # en orden, nunca en paralelo
        if nucleo.ruta_capitulo(n).exists() and n in nucleo.capitulos_existentes():
            # Solo se salta si ya se cerro; si quedo a medias se rehace.
            cerrados = {e.get("capitulo") for e in _eventos_de_tirada(cfg)
                        if e.get("evento") == "capitulo_fin"}
            if n in cerrados:
                avisar(f"El capitulo {n} ya estaba escrito.")
                continue
        if not _escribir_capitulo(n, cfg, sesiones, avisar):
            return False
    eventos.registrar("fase_fin", fase="redaccion", datos={"capitulos": previstos})
    return True


# --------------------------------------------------------------------------
# Fases 4 y 5
# --------------------------------------------------------------------------

def fase_revision(cfg, sesiones, avisar):
    eventos.registrar("fase_inicio", fase="revision")
    avisar("Releyendo la novela entera en busca de contradicciones.")
    estado = nucleo.cargar_estado()
    respuesta = invocar(
        "revisor-global",
        _bloque("Canon", nucleo.leer_canon())
        + _bloque("Estado final", estado)
        + _bloque("Capitulos", {str(n): nucleo.cuerpo_capitulo(n)
                                for n in nucleo.capitulos_existentes()})
        + "\nDevuelve solo tu JSON de informe. No escribas ficheros.",
        cfg, sesiones, fase="revision")
    informe = informes.informe_global(cfg, estado, _json_de(respuesta["texto"]))
    informes.guardar(informe, "global.json")
    eventos.registrar("fase_fin", fase="revision",
                      datos={"incidencias": informe.get("resumen")})


def fase_entrega(cfg, avisar):
    eventos.registrar("fase_inicio", fase="entrega")
    avisar("Montando el manuscrito final.")
    # ensamblar.py no expone funcion: se invoca como proceso, que es como lo
    # invoca el camino conversacional. Su JSON de salida trae el recuento.
    completado = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "ensamblar.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RAIZ))
    try:
        resultado = json.loads(completado.stdout or "{}")
    except json.JSONDecodeError:
        resultado = {"error": (completado.stderr or "").strip()[:200]}
    if completado.returncode != 0:
        raise RuntimeError(
            f"no se ha podido montar el manuscrito: faltan los capitulos "
            f"{resultado.get('faltantes')}")
    eventos.registrar("fase_fin", fase="entrega",
                      datos={"capitulos": resultado.get("capitulos"),
                             "total": resultado.get("total"),
                             "unidad": resultado.get("unidad")})
    return resultado


# --------------------------------------------------------------------------
# El recorrido entero
# --------------------------------------------------------------------------

def generar(cfg: dict = None, avisar=None) -> dict:
    """Las cinco fases, en orden. Devuelve como ha acabado.

    `avisar` recibe frases en lenguaje llano para que la web pueda contar lo
    que esta pasando sin ensenar un volcado de log.
    """
    cfg = cfg or nucleo.cargar_config()
    avisar = avisar or (lambda mensaje: None)
    sesiones = Sesiones()
    _limpiar_parada()
    tirada = eventos.tirada_vigente(cfg)
    _marcar_trabajando(tirada)
    desenlace, motivo = "terminada", None
    try:
        fase_canon(cfg, sesiones, avisar)
        fase_escaleta(cfg, sesiones, avisar)
        if fase_redaccion(cfg, sesiones, avisar):
            fase_revision(cfg, sesiones, avisar)
            fase_entrega(cfg, avisar)
            avisar("Novela terminada.")
        else:
            desenlace, motivo = "escalada", (
                "un capitulo no ha salido bien tras los intentos permitidos")
    except Detenido as exc:
        desenlace, motivo = "detenida", str(exc)
        avisar("Generacion detenida. Lo hecho hasta ahora queda guardado.")
    except SinPresupuesto as exc:
        desenlace, motivo = "sin_presupuesto", str(exc)
        avisar(f"Se ha alcanzado el tope de gasto. {exc}. Lo hecho queda guardado.")
    except Exception as exc:                       # noqa: BLE001
        desenlace, motivo = "error", f"{type(exc).__name__}: {exc}"
        avisar(f"La generacion se ha parado por un problema: {exc}")
    finally:
        _desmarcar()
        _limpiar_parada()
    return {"desenlace": desenlace, "motivo": motivo, "tirada": tirada,
            **estado_actual(cfg)}


def main():
    parser = argparse.ArgumentParser(
        prog="orquestador.py",
        description="Recorre las cinco fases de una novela sin conversacion.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--generar", action="store_true",
                       help="Genera la novela entera con la premisa de config.json.")
    grupo.add_argument("--estado", action="store_true",
                       help="Dice por donde va, leyendo solo los ficheros.")
    grupo.add_argument("--detener", action="store_true",
                       help="Pide parar la generacion en curso.")
    args = parser.parse_args()

    if args.estado:
        nucleo.salir(estado_actual(), 0)
    if args.detener:
        pedir_parada()
        nucleo.salir({"script": "orquestador", "detencion": "pedida"}, 0)
    if generando():
        nucleo.salir({"script": "orquestador",
                      "error": "ya hay una generacion en marcha"}, 3)
    nucleo.salir(generar(avisar=lambda m: print(m, file=sys.stderr)), 0)


if __name__ == "__main__":
    main()
