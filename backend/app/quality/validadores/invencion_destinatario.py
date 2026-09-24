"""`invencion_destinatario` (O-20, PO-1, D-13): ningún hecho personal sobre el destinatario
que no venga del brief o del texto libre.

El judge lista cada afirmación personal con su cita; aquí está la mitad programática, que
coteja cada una con el soporte —rasgos, recuerdos, elementos personalizados, texto libre
saneado— y **cuenta** las que no tienen apoyo. Una afirmación tiene apoyo si al menos
`calidad.invencion_soporte_minimo` de sus palabras con contenido están en el soporte. Una
cita que no está en el capítulo no cuenta: sería una invención del judge, no del texto.
Cuenta hasta `calidad.invencion_destinatario`, que es cero, y cierra el paso siempre.
"""

from __future__ import annotations

import re

from app.commons.config import Config
from app.commons.texto import plano
from app.quality.models import AfirmacionDestinatario, ContextoJudge, Defecto, ResultadoValidador

_PALABRA = re.compile(r"\w+")
# Palabras sin contenido, ya normalizadas (minúsculas y sin tildes, como `plano`).
_VACIAS = frozenset(
    {
        "a",
        "al",
        "algo",
        "ante",
        "con",
        "contra",
        "de",
        "del",
        "desde",
        "donde",
        "durante",
        "e",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "es",
        "esta",
        "estaba",
        "estar",
        "este",
        "esto",
        "fue",
        "ha",
        "hace",
        "han",
        "hasta",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "muy",
        "nada",
        "ni",
        "no",
        "nos",
        "o",
        "para",
        "pero",
        "por",
        "que",
        "se",
        "sea",
        "ser",
        "si",
        "sin",
        "sobre",
        "su",
        "sus",
        "tambien",
        "tenia",
        "tiene",
        "tu",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
    }
)


def _contenido(texto: str, ignorar: set[str]) -> set[str]:
    palabras = _PALABRA.findall(plano(texto))
    return {p for p in palabras if len(p) > 2 and p not in _VACIAS and p not in ignorar}


def _normal(texto: str) -> str:
    return re.sub(r"\s+", " ", plano(texto)).strip()


def invencion_destinatario(
    config: Config, afirmaciones: list[AfirmacionDestinatario], contexto: ContextoJudge
) -> ResultadoValidador:
    nombre = set(_PALABRA.findall(plano(contexto.destinatario)))
    soporte = _contenido(" ".join(contexto.soporte), nombre)
    capitulo = _normal(contexto.texto)
    minimo = config.umbrales.calidad.invencion_soporte_minimo
    inventadas = []
    for a in afirmaciones:
        if not a.fragmento.strip() or _normal(a.fragmento) not in capitulo:
            continue
        palabras = _contenido(a.afirmacion, nombre)
        if palabras and len(palabras & soporte) / len(palabras) < minimo:
            inventadas.append(a)
    cuenta = len(inventadas)
    return ResultadoValidador(
        nombre="invencion_destinatario",
        tipo="programático + semántico",
        punto="rol editor",
        pasa=cuenta <= config.umbrales.calidad.invencion_destinatario,
        valor=float(cuenta),
        cierra_el_paso=True,
        detalle="; ".join(f"«{a.afirmacion}»" for a in inventadas)
        or "ninguna afirmación sobre el destinatario sin apoyo en el brief",
        defectos=[
            Defecto(
                dimension="invencion_destinatario",
                gravedad="alta",
                descripcion=f"el capítulo afirma «{a.afirmacion}» y ni el brief ni el texto "
                f"libre lo dicen: «{a.fragmento}»",
            )
            for a in inventadas
        ],
    )
