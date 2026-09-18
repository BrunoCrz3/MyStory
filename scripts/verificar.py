"""Autocomprobacion de la instalacion: las 11 comprobaciones de SPEC 10.7.

A diferencia del resto de scripts, este imprime texto legible, no JSON.

Codigos de salida: 0 si todo correcto; 1 si hay algun fallo.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# En Windows la consola no es UTF-8 por defecto. verificar.py no importa
# nucleo (comprueba los scripts desde fuera), asi que lo fuerza por su cuenta.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        try:
            _flujo.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

AGENTES = ["arquitecto", "escaletista", "escritor", "continuista",
           "estilista", "archivista", "revisor-global"]
SKILLS = ["escribir-capitulo", "validar-capitulo", "bitacora"]
COMANDOS = ["nueva-novela", "escribir", "estado", "entregar"]
SCRIPTS = ["nucleo", "eventos", "medir", "repeticion", "continuidad",
           "informes", "ensamblar", "verificar", "observabilidad",
           "retroalimentar", "intentos"]
SERVIDOR = ["runner.py", "orquestador.py", "api.py",
            "static/index.html", "static/estilos.css", "static/app.js"]
# El ciclo de mejora automatica (seccion 16.9). Sus dos ficheros de memoria
# -iteraciones.jsonl y bitacora.md- y las carpetas prompts/ y tiradas/ no
# entran: los crea el ciclo al ejecutarse, como events.jsonl.
CICLO = ["ciclo.py", "linea-base.json", "premisas.json"]
EJECUTABLES = [s for s in SCRIPTS if s != "nucleo"]

INVENTARIO = (
    ["SPEC.md", "README.md", "CLAUDE.md", "config.json", ".gitignore",
     "requirements-opcional.txt"]
    + [f".claude/agents/{a}.md" for a in AGENTES]
    + [f".claude/skills/{s}/SKILL.md" for s in SKILLS]
    + [f".claude/commands/{c}.md" for c in COMANDOS]
    + [f"scripts/{s}.py" for s in SCRIPTS]
    + [f"server/{s}" for s in SERVIDOR]
    + [f"ciclo/{c}" for c in CICLO]
    + ["ciclo-mejora.md", ".vscode/settings.json", "novela/estado.json"]
)

FICHEROS_PROHIBIDOS = ["requirements.txt", "pyproject.toml", "setup.py",
                       "Makefile", "Dockerfile", "docker-compose.yml",
                       ".mcp.json", ".env", ".env.example", "package.json"]
# .venv/ dejo de estar prohibida cuando el autor pidio la interfaz web: el
# servidor necesita fastapi y uvicorn, que no estan en la biblioteca estandar.
# Siguen siendo las dos unicas dependencias, y solo las usa server/. Los
# scripts de scripts/ siguen sin ninguna, y la comprobacion 9 lo vigila.
CARPETAS_PROHIBIDAS = ["src", "tests"]

# Las cadenas se construyen por trozos a proposito: asi este fichero puede
# buscarlas sin contenerlas, y la comprobacion 9 no se delata a si misma.
PATRONES_PROHIBIDOS = [
    "im" + "port " + "req" + "uests",
    "im" + "port " + "htt" + "px",
    "anthro" + "pic",
    "open" + "ai",
    "API" + "_KEY",
    "os" + ".environ",
    "pip" + " install",
]

# observabilidad.py es el UNICO script al que se le permite leer variables de
# entorno, porque es el unico que habla con Langfuse y las credenciales solo
# pueden venir de ahi. Sigue sujeto a todos los demas patrones: si alguna vez
# contiene una clave literal o una dependencia externa, la comprobacion salta.
EXENCIONES = {"observabilidad": {"os" + ".environ"}}

CLAVES_ESTADO = ["aperturas", "capitulos_escritos", "cierres", "entidades",
                 "frases_usadas", "hechos", "hilos", "resumenes", "tirada"]

resultados = []


def anota(ok: bool, mensaje: str):
    resultados.append((ok, mensaje))
    print(f"[{'OK' if ok else 'FALLO'}]    {mensaje}")


def _frontmatter(ruta: Path) -> dict:
    """Lee el frontmatter YAML sin dependencias: solo claves de primer nivel."""
    texto = ruta.read_text(encoding="utf-8")
    bloque = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", texto, re.DOTALL)
    if not bloque:
        return {}
    campos = {}
    for linea in bloque.group(1).splitlines():
        par = re.match(r"([A-Za-z_-]+):\s*(.*)", linea)
        if par:
            campos[par.group(1)] = par.group(2).strip().strip('"\'')
    return campos


def comprobar_python():
    version = ".".join(str(p) for p in sys.version_info[:3])
    anota(sys.version_info >= (3, 12), f"Python {version}")


def comprobar_inventario():
    faltan = [f for f in INVENTARIO if not (RAIZ / f).exists()]
    total = len(INVENTARIO)
    if faltan:
        anota(False, f"{total - len(faltan)}/{total} ficheros del inventario "
                     f"presentes; faltan: {', '.join(faltan)}")
    else:
        anota(True, f"{total}/{total} ficheros del inventario presentes")


def comprobar_prohibidos():
    sobran = [f for f in FICHEROS_PROHIBIDOS if (RAIZ / f).exists()]
    sobran += [f"{c}/" for c in CARPETAS_PROHIBIDAS if (RAIZ / c).is_dir()]
    if sobran:
        anota(False, f"{len(sobran)} ficheros prohibidos: {', '.join(sobran)}")
    else:
        anota(True, "0 ficheros prohibidos")


def comprobar_config():
    ruta = RAIZ / "config.json"
    if not ruta.exists():
        anota(False, "config.json: no existe")
        return
    try:
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        anota(False, f"config.json no es JSON valido: {exc}")
        return
    problemas = []
    for clave in ("proyecto", "idioma", "premisa", "capitulos", "longitud",
                  "validacion", "git", "eventos"):
        if clave not in cfg:
            problemas.append(f"falta '{clave}'")
    if isinstance(cfg.get("capitulos"), bool) or not isinstance(cfg.get("capitulos"), int):
        problemas.append("'capitulos' no es un entero")
    longitud = cfg.get("longitud", {})
    if longitud.get("unidad") not in ("lineas", "palabras"):
        problemas.append("'longitud.unidad' no es 'lineas' ni 'palabras'")
    if not isinstance(longitud.get("objetivo"), int):
        problemas.append("'longitud.objetivo' no es un entero")
    if not isinstance(longitud.get("tolerancia"), (int, float)):
        problemas.append("'longitud.tolerancia' no es un numero")
    anota(not problemas, "config.json valido" if not problemas
          else f"config.json: {'; '.join(problemas)}")


def comprobar_estado():
    ruta = RAIZ / "novela" / "estado.json"
    if not ruta.exists():
        anota(False, "novela/estado.json: no existe")
        return
    try:
        estado = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        anota(False, f"novela/estado.json no es JSON valido: {exc}")
        return
    faltan = [c for c in CLAVES_ESTADO if c not in estado]
    anota(not faltan, "novela/estado.json valido" if not faltan
          else f"novela/estado.json: faltan las claves {', '.join(faltan)}")


def comprobar_agentes():
    fallos = []
    for nombre in AGENTES:
        ruta = RAIZ / ".claude" / "agents" / f"{nombre}.md"
        if not ruta.exists():
            fallos.append(f"{nombre}: no existe")
            continue
        campos = _frontmatter(ruta)
        if "name" not in campos or "description" not in campos:
            fallos.append(f"{nombre}: frontmatter sin name o description")
        elif campos["name"] != nombre:
            fallos.append(f"{nombre}: el name del frontmatter es '{campos['name']}'")
    correctos = len(AGENTES) - len(fallos)
    anota(not fallos,
          f"{correctos}/{len(AGENTES)} subagentes con frontmatter correcto"
          + (f"; {'; '.join(fallos)}" if fallos else ""))


def comprobar_skills():
    fallos = []
    for nombre in SKILLS:
        ruta = RAIZ / ".claude" / "skills" / nombre / "SKILL.md"
        if not ruta.exists():
            fallos.append(f"{nombre}: no existe")
            continue
        campos = _frontmatter(ruta)
        if "name" not in campos or "description" not in campos:
            fallos.append(f"{nombre}: frontmatter sin name o description")
    correctas = len(SKILLS) - len(fallos)
    anota(not fallos,
          f"{correctas}/{len(SKILLS)} skills con frontmatter correcto"
          + (f"; {'; '.join(fallos)}" if fallos else ""))


def comprobar_comandos():
    fallos = []
    for nombre in COMANDOS:
        ruta = RAIZ / ".claude" / "commands" / f"{nombre}.md"
        if not ruta.exists():
            fallos.append(f"{nombre}: no existe")
            continue
        if "description" not in _frontmatter(ruta):
            fallos.append(f"{nombre}: frontmatter sin description")
    correctos = len(COMANDOS) - len(fallos)
    anota(not fallos,
          f"{correctos}/{len(COMANDOS)} comandos con frontmatter correcto"
          + (f"; {'; '.join(fallos)}" if fallos else ""))


def comprobar_dependencias():
    hallazgos = []
    for nombre in SCRIPTS:
        ruta = RAIZ / "scripts" / f"{nombre}.py"
        if not ruta.exists():
            continue
        texto = ruta.read_text(encoding="utf-8")
        permitidos = EXENCIONES.get(nombre, set())
        for patron in PATRONES_PROHIBIDOS:
            if patron in texto and patron not in permitidos:
                hallazgos.append(f"{nombre}.py contiene '{patron}'")
    anota(not hallazgos,
          "scripts sin dependencias externas ni claves" if not hallazgos
          else "; ".join(hallazgos))


def comprobar_ejecutables():
    fallos = []
    for nombre in EJECUTABLES:
        ruta = RAIZ / "scripts" / f"{nombre}.py"
        if not ruta.exists():
            fallos.append(f"{nombre}.py: no existe")
            continue
        try:
            proceso = subprocess.run(
                [sys.executable, str(ruta), "--help"],
                capture_output=True, text=True, encoding="utf-8", timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            fallos.append(f"{nombre}.py: no arranca ({exc})")
            continue
        if proceso.returncode != 0:
            fallos.append(f"{nombre}.py --help sale con codigo {proceso.returncode}")
    nucleo_py = RAIZ / "scripts" / "nucleo.py"
    if not nucleo_py.exists():
        fallos.append("nucleo.py: no existe")
    correctos = len(EJECUTABLES) - len([f for f in fallos if "nucleo" not in f])
    anota(not fallos,
          f"{correctos}/{len(EJECUTABLES)} scripts ejecutables"
          + (f"; {'; '.join(fallos)}" if fallos else ""))


def comprobar_git():
    try:
        proceso = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(RAIZ), capture_output=True, text=True,
            encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError):
        anota(False, "git: no esta disponible en el PATH")
        return
    if proceso.returncode != 0 or proceso.stdout.strip() != "true":
        anota(False, "git: la carpeta no es un repositorio. Ejecuta: git init")
        return
    anota(True, "git disponible y la carpeta es un repositorio")


def main():
    parser = argparse.ArgumentParser(
        prog="verificar.py",
        description="Comprueba que el generador de novelas esta bien construido: "
                    "inventario, formatos, scripts y repositorio.")
    parser.parse_args()

    comprobar_python()
    comprobar_inventario()
    comprobar_prohibidos()
    comprobar_config()
    comprobar_estado()
    comprobar_agentes()
    comprobar_skills()
    comprobar_comandos()
    comprobar_dependencias()
    comprobar_ejecutables()
    comprobar_git()

    correctas = sum(1 for ok, _ in resultados if ok)
    fallos = len(resultados) - correctas
    print()
    print(f"{len(resultados)} comprobaciones, {correctas} correctas, "
          f"{fallos} fallo{'s' if fallos != 1 else ''}.")
    print(f"VEREDICTO: {'CORRECTO' if fallos == 0 else 'REVISAR'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
