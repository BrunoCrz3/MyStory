"""Modulo compartido del generador de novelas.

No se ejecuta solo: los demas scripts de scripts/ lo importan.
Python 3.12, solo biblioteca estandar. Sin red, sin variables de entorno.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path


def _forzar_utf8() -> None:
    """En Windows la consola no es UTF-8 por defecto (suele ser cp1252) y los
    acentos del JSON saldrian rotos por stdout. Todos los scripts importan
    nucleo, asi que con forzarlo aqui queda cubierto el sistema entero."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            try:
                flujo.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


_forzar_utf8()

# Semilla de novela/estado.json: las 9 claves de la seccion 6.3 del SPEC.
SEMILLA_ESTADO = {
    "tirada": None,
    "capitulos_escritos": 0,
    "hechos": [],
    "hilos": [],
    "entidades": [],
    "resumenes": [],
    "frases_usadas": [],
    "aperturas": [],
    "cierres": [],
}

# Palabras vacias del espanol, ya normalizadas (sin tildes, en minuscula).
# Se usan para las muletillas (repeticion.py) y para los nombres propios
# (continuidad.py). Ver SPEC seccion 19.2, punto 4: este es el sitio donde
# se afina la deteccion de falsos positivos.
_VACIAS = """
a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas
aquello aquellos aqui asi aun aunque bajo bien cada casi como con contra cual
cuales cuando cuanto de del desde donde dos e el ella ellas ello ellos en entre
era eran eres es esa esas ese eso esos esta estaba estaban estan estar estas
este esto estos fue fueron fui ha habia han hasta hay la las le les lo los mas
me mi mientras mis misma mismo mucha mucho muy nada ni no nos nosotros nuestra
nuestro o os otra otras otro otros para pero poco por porque pues que quien
quienes se sea segun ser si sin sobre solo son su sus tambien tampoco tan tanto
te tiene tienen toda todas todo todos tras tu tus un una unas uno unos usted
ustedes va van vosotros voy y ya yo
"""

_CIERRES_FRASE = (".", "?", "!", "…", '"', "»", ")")


def raiz() -> Path:
    """Localiza la raiz del repositorio a partir de la ubicacion del script."""
    return Path(__file__).resolve().parent.parent


def vacias() -> set:
    """Conjunto de palabras vacias normalizadas."""
    return set(_VACIAS.split())


def salir(payload: dict, codigo: int):
    """Imprime el JSON en stdout y termina el proceso con el codigo dado."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(codigo)


def _error(mensaje: str, script: str = "nucleo"):
    salir({"script": script, "error": mensaje}, 3)


def cargar_config() -> dict:
    """Lee y valida config.json. Sale con codigo 3 si algo falta o no cuadra."""
    ruta = raiz() / "config.json"
    if not ruta.exists():
        _error("no existe config.json en la raiz del repositorio")
    try:
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(f"config.json no es JSON valido: {exc}")

    for clave in ("proyecto", "idioma", "premisa", "capitulos", "longitud",
                  "validacion", "git", "eventos"):
        if clave not in cfg:
            _error(f"config.json: falta la clave obligatoria '{clave}'")

    if not isinstance(cfg["capitulos"], int) or cfg["capitulos"] < 1:
        _error("config.json: 'capitulos' debe ser un entero positivo")

    longitud = cfg["longitud"]
    for clave in ("unidad", "objetivo", "tolerancia"):
        if clave not in longitud:
            _error(f"config.json: falta 'longitud.{clave}'")
    if longitud["unidad"] not in ("lineas", "palabras"):
        _error("config.json: 'longitud.unidad' debe ser 'lineas' o 'palabras'")

    return cfg


# Las UNICAS tres claves de config.json que se pueden cambiar por programa.
# La regla estaba escrita en CLAUDE.md y la cumplia quien se acordaba; aqui es
# la firma de la funcion la que la hace cumplir, y no hay otra puerta.
CLAVES_EDITABLES = ("premisa", "capitulos", "longitud.objetivo")


def actualizar_config(premisa: str = None, capitulos: int = None,
                      objetivo: int = None) -> dict:
    """Cambia en config.json solo las tres claves editables. Devuelve el todo.

    Lo que no se pasa no se toca, y no hay forma de pasar otra cosa: el resto
    del fichero -umbrales, git, eventos, observabilidad, servidor- se reescribe
    tal cual estaba y en el mismo orden, porque json.load conserva el orden de
    las claves y json.dump lo respeta.
    """
    ruta = raiz() / "config.json"
    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    if premisa is not None:
        cfg["premisa"] = str(premisa)
    if capitulos is not None:
        cfg["capitulos"] = int(capitulos)
    if objetivo is not None:
        cfg["longitud"] = dict(cfg.get("longitud") or {})
        cfg["longitud"]["objetivo"] = int(objetivo)
    ruta.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return cfg


def cargar_estado() -> dict:
    """Lee novela/estado.json. Si no existe, devuelve la semilla vacia."""
    ruta = raiz() / "novela" / "estado.json"
    if not ruta.exists():
        return json.loads(json.dumps(SEMILLA_ESTADO))
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(f"novela/estado.json no es JSON valido: {exc}")


def guardar_estado(estado: dict) -> None:
    """Escribe novela/estado.json con formato estable (indent=2, UTF-8)."""
    ruta = raiz() / "novela" / "estado.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def leer_jsonl(ruta) -> list:
    """Las lineas de un fichero JSONL, ya convertidas y sin las rotas.

    Habia seis copias de este bucle repartidas por el repositorio -eventos,
    informes, intentos, la API, el orquestador-, y las seis toleraban una
    linea mal formada de manera distinta. Un registro que se lee de seis
    maneras acaba contando seis historias.
    """
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Vale igual para los transcripts de Claude Code, que no son nuestros
        # y pueden traer cualquier cosa.
        return []
    filas = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue        # una linea rota no invalida el resto del registro
    return filas


def cargar_escaleta() -> dict:
    """Lee novela/escaleta.json. Sale con codigo 3 si no existe."""
    ruta = raiz() / "novela" / "escaleta.json"
    if not ruta.exists():
        _error("no existe novela/escaleta.json: falta la fase 2")
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(f"novela/escaleta.json no es JSON valido: {exc}")


def leer_canon() -> str:
    """Devuelve novela/canon.md como texto. Cadena vacia si aun no existe."""
    ruta = raiz() / "novela" / "canon.md"
    if not ruta.exists():
        return ""
    return ruta.read_text(encoding="utf-8")


def secciones_canon(texto: str) -> dict:
    """Parte el canon por encabezados '## '. Devuelve {titulo: cuerpo}."""
    secciones = {}
    actual = None
    acumulado = []
    for linea in texto.splitlines():
        if linea.startswith("## "):
            if actual is not None:
                secciones[actual] = "\n".join(acumulado).strip()
            actual = linea[3:].strip()
            acumulado = []
        elif actual is not None:
            acumulado.append(linea)
    if actual is not None:
        secciones[actual] = "\n".join(acumulado).strip()
    return secciones


def ruta_capitulo(n: int) -> Path:
    """novela/capitulos/capitulo-NN.md"""
    return raiz() / "novela" / "capitulos" / f"capitulo-{int(n):02d}.md"


def carpeta_capitulos(base=None) -> Path:
    """Donde viven los capitulos. Por defecto los de la novela en curso, pero
    vale cualquier base: una novela archivada, una tirada del ciclo de mejora."""
    return Path(base) if base else raiz() / "novela" / "capitulos"


def capitulos_existentes(base=None) -> list:
    """Lista ordenada de los numeros de capitulo presentes en disco."""
    carpeta = carpeta_capitulos(base)
    if not carpeta.is_dir():
        return []
    numeros = []
    for fichero in carpeta.glob("capitulo-*.md"):
        encontrado = re.fullmatch(r"capitulo-(\d+)", fichero.stem)
        if encontrado:
            numeros.append(int(encontrado.group(1)))
    return sorted(numeros)


def cuerpo_capitulo(n: int) -> str:
    """Texto del capitulo sin la linea de titulo ni las lineas vacias."""
    return "\n".join(lineas_capitulo(n))


def lineas_de(ruta) -> list:
    """Lineas de cuerpo no vacias de un fichero de capitulo, o None si no esta.

    Se descartan las vacias y las que abren con '#' (el titulo no cuenta para
    la longitud). Devuelve None -y no lista vacia- cuando el fichero no existe,
    porque no es lo mismo un capitulo de cero lineas que un capitulo ausente:
    publicar un cero por un fichero que se movio seria publicar un dato falso.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return None
    return [ln.strip() for ln in ruta.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def lineas_capitulo(n: int, base=None) -> list:
    """Lineas de cuerpo del capitulo n. Lista vacia si no existe."""
    return lineas_de(carpeta_capitulos(base) / f"capitulo-{int(n):02d}.md") or []


def palabras(texto: str) -> list:
    """Tokeniza en palabras, en minuscula, sin puntuacion, conservando
    tildes y la enye."""
    return re.findall(r"[0-9a-zà-ÿñ]+", texto.lower())


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes, sin puntuacion, espacios colapsados.
    Es la forma canonica para comparar frases y detectar reciclaje."""
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    plano = plano.replace("ñ", "n")
    plano = re.sub(r"[^0-9a-zñ]+", " ", plano)
    return re.sub(r"\s+", " ", plano).strip()


def ngramas(tokens: list, n: int) -> set:
    """Conjunto de n-gramas consecutivos, como tuplas."""
    if n < 1 or len(tokens) < n:
        return set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def cierra_frase(linea: str) -> bool:
    """True si la linea termina en un cierre de frase valido (SPEC 4.3)."""
    return linea.rstrip().endswith(_CIERRES_FRASE)


if __name__ == "__main__":
    print(json.dumps(
        {"script": "nucleo",
         "error": "nucleo.py es un modulo compartido: no se ejecuta solo"},
        ensure_ascii=False, indent=2))
    sys.exit(3)
