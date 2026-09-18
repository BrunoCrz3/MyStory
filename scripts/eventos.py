"""Registro de sucesos del pipeline: la UNICA puerta de escritura de
novela/events.jsonl.

Ningun otro script y ninguna otra herramienta escribe ese fichero. Esa regla es
lo que permite que Langfuse se enchufe en un solo sitio: la funcion registrar()
de este fichero. Ver SPEC secciones 14.4 y 14.6.

Python 3.12, solo biblioteca estandar. Este fichero no habla por red ni lee
variables de entorno: delega las dos cosas en scripts/observabilidad.py, que es
el unico modulo del sistema que hace ambas, y cuyo fallo nunca se propaga.
"""

import argparse
import json
from datetime import datetime, timezone

import nucleo
import observabilidad

ESQUEMA = 1

EVENTOS = [
    "fase_inicio", "fase_fin", "capitulo_inicio", "borrador", "validacion",
    "reescritura", "parche", "capitulo_fin", "escalado", "commit",
    # 'invocacion' registra UNA llamada a modelo con su desglose de tokens.
    # Es el unico evento que produce una 'generation' en Langfuse. Ver SPEC 14.6.
    "invocacion",
]

FASES = ["canon", "escaleta", "redaccion", "revision", "entrega"]

# Eventos que pertenecen al bucle de redaccion: si no se pasa --fase, se les
# asigna esta, tal como muestra el fichero de ejemplo de SPEC 14.2.
EVENTOS_DE_REDACCION = [
    "capitulo_inicio", "borrador", "validacion", "reescritura", "parche",
    "capitulo_fin", "escalado",
]


def _ruta_eventos(cfg: dict):
    return nucleo.raiz() / cfg["eventos"].get("fichero", "novela/events.jsonl")


def _ahora() -> str:
    marca = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    return marca.replace("+00:00", "Z")


def _nueva_tirada() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M")


def tirada_vigente(cfg: dict) -> str:
    """Deduce el identificador de tirada leyendo la ultima linea del registro.

    Si el fichero no existe, o si el ultimo evento cierra la fase de entrega,
    se abre una tirada nueva. En cualquier otro caso se reutiliza la ultima.
    """
    ruta = _ruta_eventos(cfg)
    if not ruta.exists():
        return _nueva_tirada()
    ultima = None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            ultima = linea
    if ultima is None:
        return _nueva_tirada()
    try:
        previo = json.loads(ultima)
    except json.JSONDecodeError:
        return _nueva_tirada()
    if previo.get("evento") == "fase_fin" and previo.get("fase") == "entrega":
        return _nueva_tirada()
    return previo.get("tirada") or _nueva_tirada()


def _construir(cfg, evento, fase, capitulo, intento, datos) -> dict:
    if fase is None and evento in EVENTOS_DE_REDACCION:
        fase = "redaccion"
    return {
        "ts": _ahora(),
        "tirada": tirada_vigente(cfg),
        "evento": evento,
        "fase": fase,
        "capitulo": capitulo,
        "intento": intento,
        "datos": datos if isinstance(datos, dict) else {},
        "esquema": ESQUEMA,
    }


def _escribir_linea(cfg: dict, ev: dict) -> None:
    ruta = _ruta_eventos(cfg)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fichero:
        fichero.write(json.dumps(ev, ensure_ascii=False) + "\n")


def registrar(evento, fase=None, capitulo=None, intento=None, datos=None) -> dict:
    """Construye el evento, lo escribe como una linea JSON y lo devuelve.

    PUNTO DE EXTENSION UNICO: el envio a Langfuse entra aqui y solo aqui.

    El orden importa. Primero se escribe en disco, que es la fuente de verdad, y
    solo despues se intenta exportar. observabilidad.exportar() no lanza nunca:
    si Langfuse esta caido, si no hay red o si faltan las variables de entorno,
    devuelve False, lo anota en novela/langfuse.log y la generacion sigue.
    """
    cfg = nucleo.cargar_config()
    ev = _construir(cfg, evento, fase, capitulo, intento, datos)
    _escribir_linea(cfg, ev)          # fuente de verdad: siempre, y primero
    observabilidad.exportar(ev)       # destino adicional: nunca obligatorio
    return ev


def _argumentos():
    parser = argparse.ArgumentParser(
        prog="eventos.py",
        description="Registra un suceso del pipeline en novela/events.jsonl. "
                    "Es la unica puerta de escritura de ese fichero.")
    parser.add_argument("--evento", choices=EVENTOS,
                        help="Tipo de suceso a registrar.")
    parser.add_argument("--fase", choices=FASES,
                        help="Fase del pipeline (obligatoria en fase_inicio y fase_fin).")
    parser.add_argument("--capitulo", type=int,
                        help="Numero de capitulo, en los eventos de capitulo.")
    parser.add_argument("--intento", type=int,
                        help="Numero de intento dentro del capitulo, empezando en 1.")
    parser.add_argument("--datos",
                        help="Cadena JSON con metricas o detalles del evento.")
    parser.add_argument("--tirada-actual", action="store_true",
                        help="Imprime el identificador de tirada vigente y sale.")
    return parser.parse_args()


def main():
    args = _argumentos()
    cfg = nucleo.cargar_config()

    if args.tirada_actual:
        nucleo.salir({"script": "eventos", "tirada": tirada_vigente(cfg)}, 0)

    if not args.evento:
        nucleo.salir(
            {"script": "eventos",
             "error": "falta --evento (o usa --tirada-actual)"}, 3)

    if args.evento in ("fase_inicio", "fase_fin") and not args.fase:
        nucleo.salir(
            {"script": "eventos",
             "error": f"el evento '{args.evento}' exige --fase"}, 3)

    datos = {}
    if args.datos:
        try:
            datos = json.loads(args.datos)
        except json.JSONDecodeError as exc:
            nucleo.salir(
                {"script": "eventos",
                 "error": f"--datos no es JSON valido: {exc}"}, 3)
        if not isinstance(datos, dict):
            nucleo.salir(
                {"script": "eventos",
                 "error": "--datos debe ser un objeto JSON"}, 3)

    if not cfg["eventos"].get("activo", True):
        nucleo.salir({"script": "eventos", "activo": False,
                      "detalle": "eventos.activo es false: no se registra nada"}, 0)

    try:
        ev = registrar(args.evento, args.fase, args.capitulo, args.intento, datos)
    except OSError as exc:
        nucleo.salir(
            {"script": "eventos",
             "error": f"no se ha podido escribir el registro: {exc}"}, 3)

    nucleo.salir(ev, 0)


if __name__ == "__main__":
    main()
