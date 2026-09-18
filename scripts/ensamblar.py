"""Concatena los capitulos en manuscrito.md. Determinista, sin criterio.

Codigos de salida: 0 si estan todos los capitulos de la escaleta; 2 si falta
alguno (lo dice en 'faltantes' y NO escribe el manuscrito); 3 error.
"""

import argparse
import re
from datetime import date

import medir
import nucleo


def _titulo_novela(canon: str, cfg: dict) -> str:
    for linea in canon.splitlines():
        if linea.startswith("# "):
            encontrado = re.match(r"#\s*Canon\s*[—–-]\s*(.+)", linea)
            if encontrado:
                return encontrado.group(1).strip()
            return linea[2:].strip()
    return cfg["proyecto"]


def _portada(cfg: dict, canon: str) -> list:
    secciones = nucleo.secciones_canon(canon)
    bloques = [f"# {_titulo_novela(canon, cfg)}", ""]
    bloques.append(f"*{cfg['proyecto']} — {date.today().isoformat()}*")
    bloques.append("")
    for etiqueta in ("Logline", "Sinopsis"):
        cuerpo = secciones.get(etiqueta, "").strip()
        if cuerpo:
            bloques.append(f"## {etiqueta}")
            bloques.append("")
            bloques.append(cuerpo)
            bloques.append("")
    return bloques


def main():
    parser = argparse.ArgumentParser(
        prog="ensamblar.py",
        description="Concatena los capitulos de novela/capitulos/ en un unico "
                    "manuscrito en Markdown.")
    parser.add_argument("--salida", default="manuscrito.md",
                        help="Ruta del fichero de salida (por defecto manuscrito.md).")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()
    escaleta = nucleo.cargar_escaleta()
    unidad = cfg["longitud"]["unidad"]

    planificados = sorted(c.get("n") for c in escaleta.get("capitulos", []))
    faltantes = [n for n in planificados if not nucleo.ruta_capitulo(n).exists()]

    if faltantes:
        nucleo.salir({
            "script": "ensamblar", "salida": args.salida,
            "capitulos": len(planificados) - len(faltantes),
            "unidad": unidad, "total": 0, "faltantes": faltantes,
        }, 2)

    canon = nucleo.leer_canon()
    partes = _portada(cfg, canon)
    total = 0

    for n in planificados:
        partes.append("---")
        partes.append("")
        partes.append(nucleo.ruta_capitulo(n).read_text(encoding="utf-8").strip())
        partes.append("")
        total += medir.medir(n, cfg)["medido"]

    partes.append("---")
    partes.append("")
    partes.append(f"*{len(planificados)} capitulos · {total} {unidad} en total.*")
    partes.append("")

    destino = nucleo.raiz() / args.salida
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")

    nucleo.salir({
        "script": "ensamblar", "salida": args.salida,
        "capitulos": len(planificados), "unidad": unidad,
        "total": total, "faltantes": [],
    }, 0)


if __name__ == "__main__":
    main()
