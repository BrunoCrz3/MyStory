"""Persistencia de los informes de validacion en novela/informes/.

Es la UNICA puerta de escritura de `novela/informes/`. Ningun otro script y
ningun agente escribe ahi, por el mismo motivo por el que solo `eventos.py`
escribe `events.jsonl`: un punto de entrada unico es lo que permite cambiar el
formato en un solo sitio.

No calcula nada por su cuenta: importa `medir`, `repeticion` y `continuidad` y
guarda lo que ellos devuelven, mas las incidencias de juicio que le pasa el
orquestador (el subagente `continuista` por capitulo, el `revisor-global` al
cerrar). Cada incidencia queda etiquetada con el validador que la produjo.

Las metricas se guardan SIEMPRE, dispare o no una incidencia: un informe sin
incidencias sigue siendo un informe, y la serie de metricas limpias es
justamente lo que permite calibrar los umbrales (SPEC 19.2, punto 2).

Uso:

    python scripts/informes.py --capitulo 2 [--continuista <fichero.json>] [--intento 3]
    python scripts/informes.py --todos [--continuista-dir <carpeta>]
    python scripts/informes.py --global [--revisor <fichero.json>]

Codigos de salida: 0 sin incidencias; 1 mayores o menores; 2 alguna
bloqueante; 3 error de ejecucion.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import continuidad
import eventos
import medir
import nucleo
import repeticion

ESQUEMA = 1

ORIGENES = ("medir", "repeticion", "continuidad", "continuista")


def carpeta() -> Path:
    """novela/informes/ — se crea si no existe."""
    destino = nucleo.raiz() / "novela" / "informes"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _ahora() -> str:
    marca = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    return marca.replace("+00:00", "Z")


def _resumen(incidencias: list) -> dict:
    return {sev: sum(1 for i in incidencias if i.get("severidad") == sev)
            for sev in ("bloqueante", "mayor", "menor")}


def _codigo(resumen: dict) -> int:
    if resumen["bloqueante"]:
        return 2
    if resumen["mayor"] or resumen["menor"]:
        return 1
    return 0


def _etiquetar(incidencias: list, origen: str) -> list:
    """Copia cada incidencia anadiendole de que validador viene."""
    etiquetadas = []
    for incidencia in incidencias or []:
        copia = dict(incidencia)
        copia["origen"] = origen
        etiquetadas.append(copia)
    return etiquetadas


def _leer_json(ruta: str, que: str) -> dict:
    fichero = Path(ruta)
    if not fichero.is_absolute():
        fichero = nucleo.raiz() / fichero
    if not fichero.exists():
        nucleo.salir({"script": "informes",
                      "error": f"no existe el fichero de {que}: {ruta}"}, 3)
    try:
        return json.loads(fichero.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        nucleo.salir({"script": "informes",
                      "error": f"el fichero de {que} no es JSON valido: {exc}"}, 3)


def informe_capitulo(n: int, cfg: dict, estado: dict,
                     continuista: dict = None, intento: int = None) -> dict:
    """Ejecuta los tres validadores deterministas sobre el capitulo n y funde
    su salida con la del continuista, si se ha proporcionado."""
    longitud = medir.medir(n, cfg)
    repeticion_cap = repeticion.analizar(n, cfg, estado)
    continuidad_cap = continuidad.modo_capitulo(n, cfg)

    incidencias = (
        _etiquetar(longitud["incidencias"], "medir")
        + _etiquetar(repeticion_cap["incidencias"], "repeticion")
        + _etiquetar(continuidad_cap["incidencias"], "continuidad")
        + _etiquetar((continuista or {}).get("incidencias", []), "continuista")
    )

    resumen = _resumen(incidencias)
    return {
        "esquema": ESQUEMA,
        "tipo": "capitulo",
        "capitulo": n,
        "generado": _ahora(),
        "tirada": eventos.tirada_vigente(cfg),
        "intento": intento,
        "metricas": {
            "longitud": {k: v for k, v in longitud.items()
                         if k not in ("script", "incidencias")},
            "repeticion": repeticion_cap["metricas"],
            "continuidad": {"comprobaciones": continuidad_cap["comprobaciones"],
                            **continuidad_cap.get("metricas", {})},
        },
        "incidencias": incidencias,
        "resumen": resumen,
        "por_origen": {origen: sum(1 for i in incidencias
                                   if i["origen"] == origen)
                       for origen in ORIGENES},
        "continuista_incluido": continuista is not None,
    }


def informe_global(cfg: dict, estado: dict, revisor: dict = None) -> dict:
    """Informe del manuscrito completo: continuidad, repeticion y ritmo."""
    continuidad_global = continuidad.modo_global(cfg)
    repeticion_global = repeticion.analizar_global(cfg, estado)
    capitulos = nucleo.capitulos_existentes()
    longitudes = [medir.medir(n, cfg) for n in capitulos]

    # Las incidencias de repeticion en modo global vienen agrupadas por
    # capitulo: se aplanan conservando de cual proceden.
    repeticion_planas = []
    for capitulo in repeticion_global["capitulos"]:
        for incidencia in capitulo["incidencias"]:
            copia = dict(incidencia)
            copia["capitulo"] = capitulo["capitulo"]
            repeticion_planas.append(copia)

    incidencias = (
        _etiquetar(continuidad_global["incidencias"], "continuidad")
        + _etiquetar(repeticion_planas, "repeticion")
        + _etiquetar((revisor or {}).get("incidencias", []), "revisor-global")
    )
    resumen = _resumen(incidencias)

    return {
        "esquema": ESQUEMA,
        "tipo": "global",
        "generado": _ahora(),
        "tirada": eventos.tirada_vigente(cfg),
        "capitulos": capitulos,
        "continuidad": continuidad_global,
        "repeticion": repeticion_global,
        "ritmo": (revisor or {}).get("ritmo"),
        "veredicto": (revisor or {}).get("veredicto"),
        "correcciones_propuestas": (revisor or {}).get("correcciones_propuestas", []),
        "titulos": (revisor or {}).get("titulos"),
        "sinopsis": (revisor or {}).get("sinopsis"),
        "metricas": {
            "longitud": {
                "unidad": cfg["longitud"]["unidad"],
                "objetivo": cfg["longitud"]["objetivo"],
                "por_capitulo": [{k: v for k, v in m.items()
                                  if k not in ("script", "incidencias")}
                                 for m in longitudes],
                "total": sum(m["medido"] for m in longitudes),
                "fuera_de_norma": [m["capitulo"] for m in longitudes
                                   if not m["en_norma"]],
            },
        },
        "incidencias": incidencias,
        "resumen": resumen,
        "revisor_incluido": revisor is not None,
    }


def metricas_planas(informe: dict) -> dict:
    """Las metricas de un informe, en un solo diccionario.

    Es lo que viaja en el evento `validacion` y de ahi a los scores de
    Langfuse. Existe porque los dos caminos la construian por su cuenta y no
    construian lo mismo: el orquestador escogia a mano siete claves -y dejaba
    fuera monotonia y diversidad, que la seccion 12.8 del SPEC promete que
    viajan siempre- mientras que retroalimentar.py mandaba el bloque entero.
    La consecuencia era que una tirada en vivo y la misma tirada resubida a
    posteriori daban paneles distintos.
    """
    metricas = dict(informe["metricas"].get("repeticion") or {})
    longitud = informe["metricas"].get("longitud") or {}
    metricas.update({k: v for k, v in longitud.items()
                     if k in ("unidad", "medido", "objetivo", "en_norma")})
    continuidad = dict(informe["metricas"].get("continuidad") or {})
    continuidad.pop("comprobaciones", None)     # es una lista, no una metrica
    metricas.update(continuidad)
    return metricas


def guardar(payload: dict, nombre: str) -> Path:
    destino = carpeta() / nombre
    destino.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return destino


def _relativa(ruta: Path) -> str:
    return ruta.relative_to(nucleo.raiz()).as_posix()


def main():
    parser = argparse.ArgumentParser(
        prog="informes.py",
        description="Guarda en novela/informes/ el resultado completo de una "
                    "validacion: todas las metricas y todas las incidencias.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--capitulo", type=int, help="Numero de capitulo.")
    grupo.add_argument("--todos", action="store_true",
                       help="Regenera el informe de todos los capitulos en disco.")
    grupo.add_argument("--global", dest="completo", action="store_true",
                       help="Informe del manuscrito completo.")
    parser.add_argument("--continuista",
                        help="Fichero JSON con la salida del subagente continuista.")
    parser.add_argument("--continuista-dir",
                        help="Con --todos: carpeta con ficheros capitulo_NN.json "
                             "del continuista.")
    parser.add_argument("--revisor",
                        help="Con --global: fichero JSON con el informe del "
                             "subagente revisor-global.")
    parser.add_argument("--intento", type=int,
                        help="Numero de intento al que corresponde la validacion.")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()
    estado = nucleo.cargar_estado()

    if args.completo:
        revisor = _leer_json(args.revisor, "revisor-global") if args.revisor else None
        informe = informe_global(cfg, estado, revisor)
        ruta = guardar(informe, "global.json")
        nucleo.salir({
            "script": "informes", "escrito": _relativa(ruta),
            "tipo": "global", "capitulos": informe["capitulos"],
            "resumen": informe["resumen"],
            "revisor_incluido": informe["revisor_incluido"],
        }, _codigo(informe["resumen"]))

    if args.todos:
        escritos = []
        peor = 0
        for n in nucleo.capitulos_existentes():
            continuista = None
            if args.continuista_dir:
                candidato = Path(args.continuista_dir) / f"capitulo_{n:02d}.json"
                if not candidato.is_absolute():
                    candidato = nucleo.raiz() / candidato
                if candidato.exists():
                    continuista = _leer_json(str(candidato), "continuista")
            informe = informe_capitulo(n, cfg, estado, continuista, args.intento)
            ruta = guardar(informe, f"capitulo_{n:02d}.json")
            escritos.append({"capitulo": n, "escrito": _relativa(ruta),
                             "resumen": informe["resumen"],
                             "continuista_incluido": informe["continuista_incluido"]})
            peor = max(peor, _codigo(informe["resumen"]))
        nucleo.salir({"script": "informes", "tipo": "capitulo",
                      "informes": escritos}, peor)

    continuista = _leer_json(args.continuista, "continuista") if args.continuista else None
    informe = informe_capitulo(args.capitulo, cfg, estado, continuista, args.intento)
    ruta = guardar(informe, f"capitulo_{args.capitulo:02d}.json")
    nucleo.salir({
        "script": "informes", "escrito": _relativa(ruta),
        "tipo": "capitulo", "capitulo": args.capitulo,
        "resumen": informe["resumen"], "por_origen": informe["por_origen"],
        "continuista_incluido": informe["continuista_incluido"],
    }, _codigo(informe["resumen"]))


if __name__ == "__main__":
    main()
