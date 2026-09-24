"""Fuentes de las capas del contexto y el contador de producción.

**Recuperado sin `sqlite-vec` en v1** (TO-015): la capa filtra por las entidades del brief de
capítulo y solo después ordena (RF-CTX-04). Caber no es enviar: aunque la novela entera
cupiera, se sigue filtrando, porque mandarla completa en cada llamada chocaría con el tope
concurrente.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from collections import Counter

from app.commons.config import Config, Rol
from app.commons.llm import Mensaje, Peticion
from app.commons.llm.llamar import LlamadorModelo
from app.context.ensamblador import Pieza
from app.novel import service as novel


def _plano(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _menciona(parrafo: str, entidad: str) -> bool:
    patron = r"(?<!\w)" + re.escape(_plano(entidad)) + r"(?!\w)"
    return re.search(patron, _plano(parrafo)) is not None


def recuperar_fragmentos(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    entidades: list[str],
    antes_de: int,
    excluir: set[int],
    maximo: int,
) -> list[Pieza]:
    """Párrafos de capítulos anteriores que nombran alguna entidad del brief de capítulo.

    Primero el filtro —un párrafo sin ninguna entidad no entra, se parezca lo que se parezca—
    y después el orden: más entidades distintas primero, y a igualdad el más reciente.
    """
    entidades = [e for e in entidades if e.strip()]
    if not entidades:
        return []
    candidatos: list[tuple[int, int, int, str]] = []
    for capitulo in novel.capitulos_aceptados(con, novel_id=novel_id, version=version):
        if capitulo.numero >= antes_de or capitulo.numero in excluir:
            continue
        for orden, parrafo in enumerate(p.strip() for p in capitulo.texto.split("\n\n")):
            if not parrafo:
                continue
            nombradas = sum(1 for e in entidades if _menciona(parrafo, e))
            if nombradas:
                candidatos.append((nombradas, capitulo.numero, -orden, parrafo))
    candidatos.sort(reverse=True)
    return [
        Pieza(texto=parrafo, etiqueta=f"Del capítulo {numero}", prioridad=nombradas)
        for nombradas, numero, _, parrafo in candidatos[:maximo]
    ]


def expresiones_repetidas(textos: list[str], config: Config) -> list[str]:
    """N-gramas que ya aparecen al menos dos veces en la ventana: el anticontexto los veta."""
    n = config.umbrales.prosa.longitud_ngrama
    cuenta: Counter[str] = Counter()
    for texto in textos:
        palabras = re.findall(r"\w+", texto.lower())
        cuenta.update(" ".join(palabras[i : i + n]) for i in range(len(palabras) - n + 1))
    return sorted(g for g, veces in cuenta.items() if veces >= 2)


class ContadorProveedor:
    """El contador de producción: `messages.count_tokens` a través del llamador, con caché por
    rol y contenido para no volver a contar la misma capa en cada paso de degradación."""

    def __init__(self, llamador: LlamadorModelo) -> None:
        self.llamador = llamador
        self._cache: dict[tuple[str, str], int] = {}

    async def contar_texto(self, rol: Rol, texto: str) -> int:
        if not texto:
            return 0
        clave = (rol, hashlib.sha256(texto.encode("utf-8")).hexdigest())
        if clave not in self._cache:
            peticion = Peticion(
                rol=rol,
                system=".",
                mensajes=[Mensaje(role="user", contenido=texto)],
                prompt="recuento",
                hash_prompt="-",
            )
            self._cache[clave] = await self.llamador.contar(peticion)
        return self._cache[clave]

    async def contar_peticion(self, peticion: Peticion) -> int:
        return await self.llamador.contar(peticion)
