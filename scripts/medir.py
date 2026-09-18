"""Mide la longitud de un capitulo en la unidad que diga config.json.

La unidad NO esta cableada: sale de config.json -> longitud.unidad, y puede ser
'lineas' o 'palabras'. Ver SPEC secciones 4.3 y 10.3.

Codigos de salida: 0 en norma; 2 fuera de norma o con lineas sin cierre de
frase; 3 error de ejecucion.
"""

import argparse
import math

import nucleo


def _rango(objetivo: int, tolerancia: float):
    """Rango admitido, redondeando hacia fuera. Con tolerancia 0.0 es exacto."""
    minimo = math.floor(objetivo * (1 - tolerancia))
    maximo = math.ceil(objetivo * (1 + tolerancia))
    return minimo, maximo


def medir(n: int, cfg: dict) -> dict:
    longitud = cfg["longitud"]
    unidad = longitud["unidad"]
    objetivo = longitud["objetivo"]
    minimo, maximo = _rango(objetivo, longitud["tolerancia"])

    ruta = nucleo.ruta_capitulo(n)
    incidencias = []

    if not ruta.exists():
        return {
            "script": "medir", "capitulo": n, "unidad": unidad,
            "objetivo": objetivo, "medido": 0, "minimo": minimo,
            "maximo": maximo, "lineas_sin_cierre": 0, "en_norma": False,
            "incidencias": [{
                "severidad": "bloqueante", "tipo": "capitulo_inexistente",
                "detalle": f"no existe {ruta.relative_to(nucleo.raiz()).as_posix()}",
            }],
        }

    lineas = nucleo.lineas_capitulo(n)

    if unidad == "lineas":
        # SPEC 4.3: una linea que no cierre frase no cuenta como linea valida.
        validas = [ln for ln in lineas if nucleo.cierra_frase(ln)]
        sin_cierre = [ln for ln in lineas if not nucleo.cierra_frase(ln)]
        medido = len(validas)
        for linea in sin_cierre:
            incidencias.append({
                "severidad": "bloqueante", "tipo": "linea_sin_cierre",
                "detalle": "la linea no termina en . ? ! … \" » o )",
                "ancla": linea,
            })
    else:
        medido = len(nucleo.palabras("\n".join(lineas)))
        sin_cierre = []

    dentro = minimo <= medido <= maximo
    if not dentro:
        incidencias.append({
            "severidad": "bloqueante", "tipo": "longitud",
            "detalle": (f"el capitulo mide {medido} {unidad} y la norma es "
                        f"de {minimo} a {maximo}"),
        })

    return {
        "script": "medir",
        "capitulo": n,
        "unidad": unidad,
        "objetivo": objetivo,
        "medido": medido,
        "minimo": minimo,
        "maximo": maximo,
        "lineas_sin_cierre": len(sin_cierre),
        "en_norma": dentro and not sin_cierre,
        "incidencias": incidencias,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="medir.py",
        description="Mide la longitud de un capitulo en la unidad de config.json.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--capitulo", type=int, help="Numero de capitulo a medir.")
    grupo.add_argument("--todos", action="store_true",
                       help="Mide todos los capitulos que hay en disco.")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()

    if args.todos:
        medidas = [medir(n, cfg) for n in nucleo.capitulos_existentes()]
        fuera = [m["capitulo"] for m in medidas if not m["en_norma"]]
        nucleo.salir({
            "script": "medir",
            "capitulos": medidas,
            "fuera_de_norma": fuera,
        }, 2 if fuera else 0)

    resultado = medir(args.capitulo, cfg)
    nucleo.salir(resultado, 0 if resultado["en_norma"] else 2)


if __name__ == "__main__":
    main()
