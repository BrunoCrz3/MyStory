"""`invencion_destinatario` (O-20, PO-1, D-13): ningún hecho personal sobre el destinatario
que no venga del brief o del texto libre.

El judge lista cada afirmación personal con su cita y dice dónde se apoya (la mitad
semántica: sabe que «cabezota» es «tozuda»). Aquí está la mitad programática, que coteja cada
una con el soporte —el brief entero y el texto libre saneado— por palabras con contenido
(`calidad.invencion_soporte_minimo`). **Cuenta como invención solo si las dos mitades
coinciden** en que no hay apoyo: el cotejo por palabras solo marcaba las paráfrasis, y el
judge solo puede equivocarse con lo que el brief dice con todas las letras (A-108). Una cita
que no está en el capítulo no cuenta: sería una invención del judge, no del texto. Cuenta
hasta `calidad.invencion_destinatario`, que es cero, y cierra el paso siempre.
"""

from __future__ import annotations

import re

from app.commons.config import Config
from app.commons.texto import plano
from app.quality.models import AfirmacionDestinatario, ContextoJudge, Defecto, ResultadoValidador
from app.quality.validadores.basicos import MARCADOR

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


# Lo mínimo de cita literal, sin marcadores, para que la cita ancle en el capítulo.
_LITERAL_MINIMO = 12


def _cita_en(fragmento: str, capitulo: str) -> bool:
    """Si la cita está en el capítulo. Un marcador (`[PROFESION_OCULTA]`) vale por el trozo que
    sustituye: el judge puede escribirlo en lugar del texto literal (TO-058), y el resto de la
    cita tiene que estar tal cual y en orden."""
    trozos = [_normal(t) for t in MARCADOR.split(fragmento)]
    if sum(len(t) for t in trozos) < _LITERAL_MINIMO:
        return False
    if len(trozos) == 1:
        return trozos[0] in capitulo
    patron = r".{1,200}?".join(re.escape(t) for t in trozos)
    return re.search(patron, capitulo) is not None


def invencion_destinatario(
    config: Config, afirmaciones: list[AfirmacionDestinatario], contexto: ContextoJudge
) -> ResultadoValidador:
    nombre = set(_PALABRA.findall(plano(contexto.destinatario)))
    soporte = _contenido(" ".join(contexto.soporte), nombre)
    capitulo = _normal(contexto.texto)
    minimo = config.umbrales.calidad.invencion_soporte_minimo
    inventadas = []
    for a in afirmaciones:
        if not a.fragmento.strip() or not _cita_en(a.fragmento, capitulo):
            continue
        if a.apoyo != "ninguno":
            continue
        palabras = _contenido(MARCADOR.sub(" ", a.afirmacion), nombre)
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
