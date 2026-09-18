"""Historial de intentos de cada capitulo: lo unico del proceso que hoy se
pierde.

QUE FALTABA Y QUE NO. El registro de eventos ya guarda, por intento, el numero
de intento, las metricas resumidas y el recuento de incidencias por severidad.
Y `novela/informes/capitulo_NN.json` guarda mucho mas: las metricas separadas
por validacion -longitud, repeticion, continuidad con sus siete
comprobaciones- y la lista completa de incidencias con severidad, tipo, detalle
y de que validador vino. Ese fichero hasta tiene un campo `intento`.

El problema es que los dos ficheros que importan se SOBRESCRIBEN en cada
intento: `novela/capitulos/capitulo-NN.md` y `novela/informes/capitulo_NN.json`
solo contienen el ultimo. Del intento 1 no queda nada, y sin el texto anterior
no hay forma de ensenar que cambio entre un intento y el siguiente.

QUE HACE ESTE MODULO. Congela los dos ficheros en `novela/intentos/` justo
cuando se registra la validacion de un intento, que es el instante exacto en
que ambos describen ese intento y no otro:

    novela/intentos/capitulo-01-intento-1.md     el texto tal como quedo
    novela/intentos/capitulo-01-intento-1.json   el informe de esa validacion

Se engancha en `eventos.registrar()`, igual que la exportacion a Langfuse, y
por la misma razon: es el unico sitio por el que pasa todo. Asi el historial se
guarda tanto si la novela la genera el orquestador web como si la genera el
autor hablando con Claude Code, sin tocar ni una skill ni un subagente.

El diff NO se guarda: se calcula al leer, comparando dos textos que ya estan en
disco. Guardar algo que se puede derivar es pedir que se desincronice.

Python 3.12, solo biblioteca estandar.
"""

import argparse
import difflib
import json
import re
from pathlib import Path

import nucleo

CARPETA = "novela/intentos"

# Eventos que cierran un intento y dejan su texto e informe cuajados en disco.
# 'validacion' llega despues de informes.py, que es quien escribe el informe.
EVENTO_DE_CIERRE = "validacion"
# El estilista cambia el texto DESPUES de la ultima validacion, asi que sin
# esto el ultimo intento del historial no coincidiria con el capitulo que el
# lector tiene delante, que es justo la comparacion que mas interesa.
EVENTO_DE_PULIDO = "capitulo_fin"
PULIDO = 0          # numero de intento reservado para la pasada del estilista

_PALABRAS = re.compile(r"\s+")


def _carpeta() -> Path:
    return nucleo.raiz() / CARPETA


def _nombre(capitulo: int, intento) -> str:
    if intento == PULIDO:
        return f"capitulo-{int(capitulo):02d}-pulido"
    return f"capitulo-{int(capitulo):02d}-intento-{int(intento)}"


# --------------------------------------------------------------------------
# Congelar
# --------------------------------------------------------------------------

def guardar(ev: dict) -> bool:
    """Congela texto e informe del intento que acaba de cerrarse.

    Se le pasa el evento ya construido. Devuelve True si ha guardado algo. No
    lanza nunca: perder el historial es una pena, pero no es motivo para tumbar
    una generacion que va bien.
    """
    try:
        evento = ev.get("evento")
        capitulo = ev.get("capitulo")
        if capitulo is None:
            return False
        if evento == EVENTO_DE_CIERRE:
            intento = ev.get("intento")
            if intento is None:
                return False
        elif evento == EVENTO_DE_PULIDO:
            intento = PULIDO
        else:
            return False

        texto = nucleo.ruta_capitulo(capitulo)
        if not texto.exists():
            return False

        destino = _carpeta()
        destino.mkdir(parents=True, exist_ok=True)
        base = _nombre(capitulo, intento)

        (destino / f"{base}.md").write_text(
            texto.read_text(encoding="utf-8"), encoding="utf-8")

        informe = (nucleo.raiz() / "novela" / "informes"
                   / f"capitulo_{int(capitulo):02d}.json")
        if informe.exists():
            (destino / f"{base}.json").write_text(
                informe.read_text(encoding="utf-8"), encoding="utf-8")
        return True
    except (OSError, ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Comparar dos textos
# --------------------------------------------------------------------------

def _trozos(antes: str, despues: str):
    """Parte dos lineas en trozos marcando cual cambia, para resaltar.

    Se compara por palabras y no por caracteres: resaltar medias palabras en
    un texto literario se lee fatal.
    """
    a, b = _PALABRAS.split(antes.strip()), _PALABRAS.split(despues.strip())
    cotejo = difflib.SequenceMatcher(None, a, b)
    izquierda, derecha = [], []
    for etiqueta, i1, i2, j1, j2 in cotejo.get_opcodes():
        if i2 > i1:
            izquierda.append({"texto": " ".join(a[i1:i2]),
                              "cambia": etiqueta != "equal"})
        if j2 > j1:
            derecha.append({"texto": " ".join(b[j1:j2]),
                            "cambia": etiqueta != "equal"})
    return izquierda, derecha


def comparar(antes: str, despues: str) -> dict:
    """Que cambio de un texto al siguiente, listo para pintar."""
    a = (antes or "").splitlines()
    b = (despues or "").splitlines()
    lineas = []
    nuevas = quitadas = cambiadas = 0
    for etiqueta, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if etiqueta == "equal":
            lineas += [{"estado": "igual", "texto": t} for t in b[j1:j2]]
        elif etiqueta == "replace":
            # Se emparejan de una en una mientras haya pareja; lo que sobra a
            # un lado es linea entera nueva o entera quitada.
            pares = min(i2 - i1, j2 - j1)
            for k in range(pares):
                izq, der = _trozos(a[i1 + k], b[j1 + k])
                lineas.append({"estado": "cambiada", "antes": izq, "despues": der})
                cambiadas += 1
            for t in a[i1 + pares:i2]:
                lineas.append({"estado": "quitada", "texto": t})
                quitadas += 1
            for t in b[j1 + pares:j2]:
                lineas.append({"estado": "anadida", "texto": t})
                nuevas += 1
        elif etiqueta == "delete":
            for t in a[i1:i2]:
                lineas.append({"estado": "quitada", "texto": t})
                quitadas += 1
        elif etiqueta == "insert":
            for t in b[j1:j2]:
                lineas.append({"estado": "anadida", "texto": t})
                nuevas += 1

    partes = []
    if cambiadas:
        partes.append(f"{cambiadas} linea{'s' if cambiadas != 1 else ''} reescrita"
                      f"{'s' if cambiadas != 1 else ''}")
    if nuevas:
        partes.append(f"{nuevas} nueva{'s' if nuevas != 1 else ''}")
    if quitadas:
        partes.append(f"{quitadas} eliminada{'s' if quitadas != 1 else ''}")
    return {"resumen": ", ".join(partes) if partes else "sin cambios en el texto",
            "hay_cambios": bool(partes), "lineas": lineas}


# --------------------------------------------------------------------------
# Leer el historial
# --------------------------------------------------------------------------

def _eventos_de(capitulo: int, ruta_eventos: Path) -> dict:
    """Modo y marca de tiempo de cada intento, sacados del registro."""
    modos, sellos = {}, {}
    if not ruta_eventos.exists():
        return {"modos": modos, "sellos": sellos}
    for linea in ruta_eventos.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if ev.get("capitulo") != capitulo:
            continue
        intento = ev.get("intento")
        if ev.get("evento") in ("borrador", "reescritura", "parche") and intento:
            modos[intento] = ev["evento"]
        if ev.get("evento") == EVENTO_DE_CIERRE and intento:
            sellos[intento] = ev.get("ts")
        if ev.get("evento") == EVENTO_DE_PULIDO:
            sellos[PULIDO] = ev.get("ts")
    return {"modos": modos, "sellos": sellos}


# Como llamar a cada cosa sin jerga, que esto acaba en pantalla.
NOMBRE_DE_MODO = {
    "borrador": "primera escritura",
    "reescritura": "reescrito entero",
    "parche": "retocado por partes",
}


def historial(capitulo: int, raiz: Path = None, eventos: Path = None) -> dict:
    """Todo lo que se sabe de como se llego al capitulo NN.

    `raiz` permite leer una novela archivada en archivo/<nombre>/ en vez de la
    que esta en curso.
    """
    base = Path(raiz) if raiz else nucleo.raiz() / "novela"
    carpeta = base / "intentos"
    registro = Path(eventos) if eventos else base / "events.jsonl"
    del_registro = _eventos_de(int(capitulo), registro)

    encontrados = []
    if carpeta.is_dir():
        for fichero in sorted(carpeta.glob(f"capitulo-{int(capitulo):02d}-*.md")):
            marca = fichero.stem.rsplit("-", 1)[-1]
            numero = PULIDO if fichero.stem.endswith("-pulido") else None
            if numero is None:
                try:
                    numero = int(marca)
                except ValueError:
                    continue
            encontrados.append((numero, fichero))
    # El pulido va el ultimo aunque su numero sea 0.
    encontrados.sort(key=lambda p: (p[0] == PULIDO, p[0]))

    salida, previo = [], None
    for numero, fichero in encontrados:
        try:
            texto = fichero.read_text(encoding="utf-8")
        except OSError:
            continue
        informe = {}
        ruta_informe = fichero.with_suffix(".json")
        if ruta_informe.exists():
            try:
                informe = json.loads(ruta_informe.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                informe = {}
        modo = ("pulido final" if numero == PULIDO
                else NOMBRE_DE_MODO.get(del_registro["modos"].get(numero),
                                        "primera escritura"))
        salida.append({
            "intento": numero,
            "es_pulido": numero == PULIDO,
            "como_se_hizo": modo,
            "cuando": del_registro["sellos"].get(numero),
            "texto": texto,
            "metricas": informe.get("metricas") or {},
            "incidencias": informe.get("incidencias") or [],
            "resumen": informe.get("resumen") or {},
            "por_origen": informe.get("por_origen") or {},
            "cambios": comparar(previo, texto) if previo is not None else None,
        })
        previo = texto

    return {"capitulo": int(capitulo), "intentos": salida,
            "total": len(salida),
            "reescrituras": max(len([i for i in salida if not i["es_pulido"]]) - 1, 0)}


def main():
    parser = argparse.ArgumentParser(
        prog="intentos.py",
        description="Historial de intentos de un capitulo: texto, metricas, "
                    "incidencias y que cambio entre un intento y el siguiente.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--capitulo", type=int, help="Numero de capitulo.")
    grupo.add_argument("--todos", action="store_true",
                       help="El historial de todos los capitulos en disco.")
    parser.add_argument("--raiz",
                        help="Carpeta de la novela, para leer una archivada. "
                             "Por defecto novela/.")
    parser.add_argument("--sin-texto", action="store_true",
                        help="Omite el texto completo: solo metricas y cambios.")
    args = parser.parse_args()

    capitulos = ([args.capitulo] if args.capitulo
                 else nucleo.capitulos_existentes())
    salida = [historial(c, args.raiz) for c in capitulos]
    if args.sin_texto:
        for h in salida:
            for i in h["intentos"]:
                i.pop("texto", None)
    nucleo.salir({"script": "intentos", "capitulos": salida}, 0)


if __name__ == "__main__":
    main()
