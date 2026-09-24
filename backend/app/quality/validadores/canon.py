"""Validadores del hook de capítulo que cotejan el borrador con el canon y el plan (P29).

Son la mitad **programática** de lo que dicen sus filas de `docs/verification.md`: lo que se
decide con datos, sin modelo. Reciben los datos ya leídos —hechos, reglas, alcance— porque
el hook corre fuera del pool y de la base (`architecture.md` § Paralelo y serie).

- `consistencia_factica` (O-26, O-27, O-28): la edad presente de un personaje en el borrador
  contra la de los hechos vigentes. La contradicción implícita sube al judge.
- `cumplimiento_brief` (O-30, O-42): el borrador nombra los personajes y lugares del alcance
  de su restricción de destino, y no adelanta a quien el plan presenta en un capítulo
  posterior.
- `reglas_mundo` (O-29): las reglas de exclusión de entidad —«el abuelo nunca aparece»— por
  nombre. Las de forma —«nada de violencia»— no son una consulta y se declaran no
  comprobables.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.texto import plano
from app.quality.models import Defecto, ResultadoValidador

_UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}  # fmt: skip
_DECENAS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
    "ochenta": 80, "noventa": 90, "cien": 100,
}  # fmt: skip
_NUMERO = r"(\d{1,3}|[a-záéíóúñ]+(?: y [a-záéíóúñ]+)?)"
# Solo la edad en presente: «cuando tenía doce años» es una analepsis, no una contradicción.
_EDAD = re.compile(rf"\b(?:tiene|cumple|sus|con)\s+{_NUMERO}\s+años\b", re.IGNORECASE)
_FRASE = re.compile(r"[^.!?\n]+[.!?]?")
_EXCLUSION = (
    re.compile(
        r"^\s*(?P<sujeto>.+?)\s+(?:nunca|no|jamás)\s+(?:aparece|aparecen|sale|salen)\b", re.I
    ),
    re.compile(
        r"^\s*(?:nunca|no|jamás)\s+(?:aparece|aparecen|debe aparecer)\s+(?P<sujeto>.+?)\.?$", re.I
    ),
)
_ARTICULOS = frozenset({"el", "la", "los", "las", "un", "una", "su", "sus"})


class EntidadPrevista(BaseModel):
    """Un personaje o lugar que el plan presenta por primera vez en un capítulo posterior."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    capitulo: int


def numero_en_texto(palabra: str) -> int | None:
    """Un número escrito en cifra o en letra, hasta cien."""
    palabra = plano(palabra.strip())
    if palabra.isdigit():
        return int(palabra)
    if palabra in _UNIDADES:
        return _UNIDADES[palabra]
    if palabra in _DECENAS:
        return _DECENAS[palabra]
    decena, _, unidad = palabra.partition(" y ")
    if decena in _DECENAS and unidad in _UNIDADES and _UNIDADES[unidad] < 10:
        return _DECENAS[decena] + _UNIDADES[unidad]
    return None


def _nucleo(nombre: str) -> str:
    """El nombre sin artículo inicial: «el puerto» se busca como «puerto»."""
    partes = nombre.split()
    while len(partes) > 1 and partes[0].lower() in _ARTICULOS:
        partes = partes[1:]
    return " ".join(partes)


def _aparece(nombre: str, texto: str, *, plural: bool = False) -> bool:
    nucleo = re.escape(plano(_nucleo(nombre)))
    sufijo = r"(?:e?s)?" if plural else ""
    return re.search(rf"\b{nucleo}{sufijo}\b", plano(texto)) is not None


def _edades(frase: str) -> list[int]:
    return [n for m in _EDAD.finditer(frase) if (n := numero_en_texto(m.group(1))) is not None]


def _con_score(config: Config, nombre: str, valor: float) -> tuple[bool, bool]:
    """Pasa si llega a su umbral de `calidad`; cierra el paso solo fuera de medición (A-03)."""
    umbral: float | None = getattr(config.umbrales.calidad, nombre)
    pasa = valor >= umbral if umbral is not None else valor == 1.0
    return pasa, config.umbrales.medicion.cerrar_el_paso


def consistencia_factica(
    config: Config, texto: str, *, hechos: list[str], nombres: list[str]
) -> ResultadoValidador:
    canon: dict[str, int] = {}
    for hecho in hechos:
        for nombre in nombres:
            if _aparece(nombre, hecho) and (edades := _edades(hecho)):
                canon.setdefault(nombre, edades[0])
    defectos: list[Defecto] = []
    for m in _FRASE.finditer(texto):
        frase = m.group(0)
        for nombre, edad in canon.items():
            if not _aparece(nombre, frase):
                continue
            for otra in _edades(frase):
                if otra != edad:
                    defectos.append(
                        Defecto(
                            dimension="consistencia_factica",
                            gravedad="alta",
                            descripcion=(
                                f"{nombre} tiene {otra} años en el borrador y {edad} en el "
                                f"canon: «{frase.strip()[:160]}»"
                            ),
                            localizacion=f"carácter {m.start()}",
                        )
                    )
    valor = 0.0 if defectos else 1.0
    pasa, cierra = _con_score(config, "consistencia_factica", valor)
    return ResultadoValidador(
        nombre="consistencia_factica",
        tipo="programático + semántico",
        punto="hook de capítulo",
        pasa=pasa,
        valor=valor,
        cierra_el_paso=cierra,
        detalle="; ".join(d.descripcion for d in defectos)
        or f"sin contradicciones con {len(canon)} edades del canon",
        defectos=defectos,
    )


def cumplimiento_brief(
    config: Config,
    texto: str,
    *,
    alcance: list[dict[str, str]],
    previstas: list[EntidadPrevista],
) -> ResultadoValidador:
    entidades = [a["nombre"] for a in alcance if a.get("tipo") in ("personaje", "lugar")]
    defectos = [
        Defecto(
            dimension="cumplimiento_brief",
            gravedad="media",
            descripcion=f"la restricción de destino toca «{e}» y el borrador no lo nombra",
        )
        for e in entidades
        if not _aparece(e, texto)
    ]
    defectos += [
        Defecto(
            dimension="cumplimiento_brief",
            gravedad="media",
            descripcion=(
                f"«{p.nombre}» aparece antes de tiempo: el plan lo presenta en el "
                f"capítulo {p.capitulo}"
            ),
        )
        for p in previstas
        if _aparece(p.nombre, texto)
    ]
    comprobaciones = len(entidades) + len(previstas)
    valor = 1.0 if comprobaciones == 0 else 1 - len(defectos) / comprobaciones
    pasa, cierra = _con_score(config, "cumplimiento_brief", valor)
    return ResultadoValidador(
        nombre="cumplimiento_brief",
        tipo="programático",
        punto="hook de capítulo",
        pasa=pasa,
        valor=valor,
        cierra_el_paso=cierra,
        detalle="; ".join(d.descripcion for d in defectos)
        or f"el borrador nombra las {len(entidades)} entidades de su restricción de destino",
        defectos=defectos,
    )


def _sujeto_excluido(regla: str) -> str | None:
    for patron in _EXCLUSION:
        if m := patron.match(regla):
            return _nucleo(m.group("sujeto").strip())
    return None


def reglas_mundo(texto: str, *, reglas: list[str]) -> ResultadoValidador:
    defectos: list[Defecto] = []
    no_comprobables: list[str] = []
    for regla in reglas:
        sujeto = _sujeto_excluido(regla)
        if sujeto is None:
            no_comprobables.append(regla)
            continue
        singular = re.sub(r"(?:e?s)$", "", sujeto) if sujeto.endswith("s") else sujeto
        if _aparece(singular, texto, plural=True):
            defectos.append(
                Defecto(
                    dimension="reglas_mundo",
                    gravedad="alta",
                    descripcion=f"la regla «{regla}» se viola: el borrador nombra «{sujeto}»",
                )
            )
    detalle = "; ".join(d.descripcion for d in defectos) or "ninguna regla del mundo violada"
    if no_comprobables:
        detalle += "; no comprobables por nombre: " + "; ".join(no_comprobables)
    return ResultadoValidador(
        nombre="reglas_mundo",
        tipo="programático",
        punto="hook de capítulo",
        pasa=not defectos,
        valor=0.0 if defectos else 1.0,
        cierra_el_paso=True,
        detalle=detalle,
        defectos=defectos,
    )
