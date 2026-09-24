"""Borradores de capítulo de prueba, con defectos inyectados a propósito."""

from __future__ import annotations

_FRASES = [
    "El viento del norte empujaba las nubes hacia la bahía mientras el día se apagaba despacio.",
    "Nadie en el pueblo recordaba un verano tan largo ni un mar tan quieto al amanecer.",
    "Las redes secaban al sol y los niños corrían descalzos entre las barcas varadas.",
    "Al fondo, la campana de la iglesia marcaba las horas sin prisa y sin testigos.",
]


def prosa(palabras: int, *, nombre: str = "Marta", extra: str = "") -> str:
    """Un texto de exactamente `palabras` palabras, en párrafos, que nombra a `nombre`.

    `extra` va al principio, dentro del recuento.
    """
    base: list[str] = []
    i = 0
    while len(base) < palabras:
        base += f"{nombre} miró el horizonte. {_FRASES[i % len(_FRASES)]}".split()
        i += 1
    todas = ([*extra.split(), *base] if extra else base)[:palabras]
    return "\n\n".join(" ".join(todas[j : j + 120]) for j in range(0, len(todas), 120))


def borrador(palabras: int = 1200, **kw: str) -> dict[str, str]:
    titulo = kw.pop("titulo", "La primera travesía")
    return {"titulo": titulo, "texto": prosa(palabras, **kw)}
