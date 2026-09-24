"""Validadores del hook de capítulo sobre el texto: `calidad_prosa` e `integridad_pov` (P30).

Deterministas y sin modelo, con las cifras de `prosa` y `calidad` de
`config/thresholds.yaml`. Cada uno agrega varias comprobaciones en un valor 0–1, que es la
fracción de comprobaciones en regla, y cada comprobación que falla deja su defecto.

- `calidad_prosa` (O-46…O-50, O-54): eco de n-gramas dentro del capítulo y con los
  anteriores, muletillas, clichés, adverbios en -mente, variación de la longitud de frase,
  metatexto o markdown filtrado, y truncado. Ortografía (O-53), descripciones repetidas
  (O-55) y deriva de estilo (O-56) no se miden todavía (A-69).
- `integridad_pov` (O-51, O-52): persona narrativa en la narración —el diálogo se excluye—,
  tiempo verbal cuando se declara presente, y accesos mentales de quien no es el POV con
  focalización interna.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Literal

from app.commons.config import Config
from app.commons.texto import plano
from app.quality.models import Defecto, ResultadoValidador

_LISTAS = Path(__file__).resolve().parents[1] / "listas"
_PALABRA = re.compile(r"\w+", re.UNICODE)
_FRASE = re.compile(r"[^.!?…]+[.!?…]+", re.UNICODE)
_ADVERBIO = re.compile(r"\b\w{3,}mente\b")
_NO_ADVERBIOS = frozenset({"demente", "clemente", "vehemente", "simiente"})
_MARKDOWN = re.compile(r"(^\s*#{1,6}\s|\*\*|`|^\s*[-*]\s)", re.MULTILINE)
_METATEXTO = re.compile(
    r"\b(aqui tienes|como modelo de lenguaje|como ia\b|espero que te guste|capitulo reescrito|"
    r"he corregido|version corregida)"
)
_INGLES = re.compile(r"\b(the|and|with|was|you|this|that)\b")
_CIERRE = re.compile(r"[.!?…»”\"')]\s*$")

_MARCAS_PERSONA = {
    "primera": re.compile(r"\b(yo|me|mi|mis|conmigo|nosotros|nosotras|nuestro|nuestra)\b"),
    "segunda": re.compile(r"\b(tu|tus|te|ti|contigo|vosotros|vosotras|os)\b"),
}
_PASADO = re.compile(r"\b\w+(?:ó|aron|ieron|aba|aban)\b", re.IGNORECASE)
_CONCIENCIA = (
    r"(?:no\s+)?(?:pensó|pensaba|sintió|sentía|supo|sabía|recordó|recordaba|temió|temía|"
    r"deseó|deseaba|imaginó|se preguntó|se dio cuenta)"
)

Persona = Literal["primera", "segunda", "tercera"]
Tiempo = Literal["presente", "pasado"]
Focalizacion = Literal["interna", "externa", "cero"]


@cache
def _lista(nombre: str) -> tuple[str, ...]:
    lineas = (_LISTAS / nombre).read_text(encoding="utf-8").splitlines()
    return tuple(plano(ln.strip()) for ln in lineas if ln.strip() and not ln.startswith("#"))


def _ngramas(texto: str, n: int) -> Counter[str]:
    palabras = _PALABRA.findall(plano(texto))
    return Counter(" ".join(palabras[i : i + n]) for i in range(len(palabras) - n + 1))


def _por_mil(veces: int, palabras: int) -> float:
    return veces * 1000 / max(palabras, 1)


def _con_score(config: Config, nombre: str, valor: float) -> tuple[bool, bool]:
    umbral: float | None = getattr(config.umbrales.calidad, nombre)
    pasa = valor >= umbral if umbral is not None else valor == 1.0
    return pasa, config.umbrales.medicion.cerrar_el_paso


def _defecto(
    dimension: str, descripcion: str, gravedad: Literal["baja", "media", "alta"]
) -> Defecto:
    return Defecto(dimension=dimension, gravedad=gravedad, descripcion=descripcion)


def calidad_prosa(config: Config, texto: str, *, anteriores: list[str]) -> ResultadoValidador:
    p = config.umbrales.prosa
    normal = plano(texto)
    palabras = len(_PALABRA.findall(normal))
    comprobaciones: list[tuple[str, str | None]] = []

    # Una cifra en null (fase de medición, A-03) deja su comprobación fuera del agregado.
    if (repeticion := p.repeticion_ngramas) is not None:
        propios = _ngramas(texto, p.longitud_ngrama)
        previos: Counter[str] = Counter()
        for anterior in anteriores:
            previos.update(_ngramas(anterior, p.longitud_ngrama))
        ecos = sorted(g for g, n in propios.items() if n + previos[g] > repeticion)
        comprobaciones.append(
            ("eco", f"eco de n-gramas repetidos más de {repeticion} veces: «{ecos[0]}» "
             f"y {len(ecos) - 1} más" if ecos else None)
        )  # fmt: skip

    for clave, fichero, umbral in (
        ("muletillas", "muletillas.txt", p.densidad_muletillas),
        ("clichés", "cliches.txt", p.densidad_cliches),
    ):
        if umbral is None:
            continue
        veces = sum(len(re.findall(rf"\b{re.escape(e)}\b", normal)) for e in _lista(fichero))
        densidad = _por_mil(veces, palabras)
        comprobaciones.append(
            (clave, f"{densidad:.1f} {clave} por cada 1.000 palabras; el máximo es {umbral}"
             if densidad > umbral else None)
        )  # fmt: skip

    if (maximo := p.densidad_adverbios) is not None:
        adverbios = [a for a in _ADVERBIO.findall(normal) if a not in _NO_ADVERBIOS]
        densidad = _por_mil(len(adverbios), palabras)
        comprobaciones.append(
            ("adverbios", f"{densidad:.1f} adverbios en -mente por cada 1.000 palabras; el "
             f"máximo es {maximo}" if densidad > maximo else None)
        )  # fmt: skip

    if (minimo := p.varianza_longitud_frase) is not None:
        largos = [n for f in _FRASE.findall(texto) if (n := len(_PALABRA.findall(f)))]
        cv = statistics.pstdev(largos) / statistics.mean(largos) if len(largos) > 1 else 1.0
        comprobaciones.append(
            ("longitud de frase", f"la longitud de frase varía {cv:.2f}; el mínimo es "
             f"{minimo}: prosa mecánica" if cv < minimo else None)
        )  # fmt: skip

    artefactos = [m.group(0).strip() for m in _MARKDOWN.finditer(texto)]
    artefactos += [m.group(0) for m in _METATEXTO.finditer(normal)]
    if len(_INGLES.findall(normal)) >= 5:
        artefactos.append("mezcla de idiomas")
    comprobaciones.append(
        ("metatexto", f"metatexto o artefactos del modelo: {', '.join(artefactos[:3])}"
         if artefactos else None)
    )  # fmt: skip
    comprobaciones.append(
        ("truncado", None if _CIERRE.search(texto) else "el texto acaba a mitad de frase: truncado")
    )

    defectos = [
        _defecto("calidad_prosa", descripcion, "media")
        for _, descripcion in comprobaciones
        if descripcion is not None
    ]
    valor = 1 - len(defectos) / len(comprobaciones)
    pasa, cierra = _con_score(config, "calidad_prosa", valor)
    return ResultadoValidador(
        nombre="calidad_prosa",
        tipo="programático",
        punto="hook de capítulo",
        pasa=pasa,
        valor=valor,
        cierra_el_paso=cierra,
        detalle="; ".join(d.descripcion for d in defectos)
        or f"las {len(comprobaciones)} comprobaciones de prosa en regla",
        defectos=defectos,
    )


def _narracion(texto: str) -> list[str]:
    """Las frases de narración: sin líneas de diálogo ni citas entre comillas."""
    frases: list[str] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea[0] in "—-–":
            continue
        linea = re.sub(r"«[^»]*»|“[^”]*”|\"[^\"]*\"", " ", linea)
        frases += [f.strip() for f in _FRASE.findall(linea + " ") if f.strip()]
    return frases


def integridad_pov(
    config: Config,
    texto: str,
    *,
    persona: Persona,
    tiempo_verbal: Tiempo,
    focalizacion: Focalizacion,
    pov: str,
    personajes: list[str],
) -> ResultadoValidador:
    frases = _narracion(texto)
    ajenas = [p for p in ("primera", "segunda") if p != persona]
    otros = [p for p in personajes if p and p != pov] if focalizacion == "interna" and pov else []
    accesos = [
        (nombre, re.compile(rf"\b{re.escape(nombre)}\s+{_CONCIENCIA}\b", re.IGNORECASE))
        for nombre in otros
    ]
    motivos: Counter[str] = Counter()
    inconsistentes = 0
    for frase in frases:
        normal = plano(frase)
        propios = [f"narración en {p} persona" for p in ajenas if _MARCAS_PERSONA[p].search(normal)]
        if tiempo_verbal == "presente" and _PASADO.search(frase):
            propios.append("narración en pasado con tiempo presente declarado")
        propios += [
            f"acceso mental de {nombre}, que no es el POV, con focalización interna"
            for nombre, patron in accesos
            if patron.search(frase)
        ]
        if propios:
            inconsistentes += 1
            motivos.update(propios)

    valor = 1.0 if not frases else 1 - inconsistentes / len(frases)
    defectos = [
        _defecto("integridad_pov", f"{motivo} en {veces} frases", "alta")
        for motivo, veces in motivos.most_common()
    ]
    pasa, cierra = _con_score(config, "integridad_pov", valor)
    return ResultadoValidador(
        nombre="integridad_pov",
        tipo="programático",
        punto="hook de capítulo",
        pasa=pasa,
        valor=valor,
        cierra_el_paso=cierra,
        detalle="; ".join(d.descripcion for d in defectos)
        or f"{len(frases)} frases de narración en {persona} persona y {tiempo_verbal}",
        defectos=defectos,
    )
