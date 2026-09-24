"""Doble de `Trazador`: guarda cada traza, span y score para poder afirmar sobre ellos.

Valida los nombres igual que la implementación de producción, porque un doble más permisivo
dejaría pasar un span inventado que en producción fallaría.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from app.commons.llm import Peticion, Respuesta
from app.commons.observabilidad import AGENTE_DE_ROL, ContextoTraza, validar_nombre_span


@dataclass
class Registro:
    tipo: str
    nombre: str
    traza: str | None
    sesion: str | None
    padre: str | None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entrada: Any = None
    salida: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    tokens_razonamiento: int | None = None
    coste_usd: float | None = None
    latencia_s: float | None = None
    error: str | None = None


@dataclass
class ScoreRegistrado:
    nombre: str
    valor: float
    comentario: str | None
    traza: str | None


_traza: contextvars.ContextVar[str | None] = contextvars.ContextVar("traza", default=None)
_sesion: contextvars.ContextVar[str | None] = contextvars.ContextVar("sesion", default=None)
_padre: contextvars.ContextVar[str | None] = contextvars.ContextVar("padre", default=None)


class _Obs:
    def __init__(self, registro: Registro) -> None:
        self.registro = registro

    def actualizar(self, *, salida: Any = None, metadata: dict[str, Any] | None = None) -> None:
        if salida is not None:
            self.registro.salida = salida
        if metadata:
            self.registro.metadata.update(metadata)

    def registrar(self, respuesta: Respuesta) -> None:
        r = self.registro
        r.salida = respuesta.datos if respuesta.datos is not None else respuesta.texto
        r.tokens_entrada = respuesta.tokens_entrada
        r.tokens_salida = respuesta.tokens_salida
        r.tokens_razonamiento = respuesta.tokens_razonamiento
        r.coste_usd = respuesta.coste_usd
        r.latencia_s = respuesta.latencia_s

    def error(self, error: BaseException) -> None:
        self.registro.error = type(error).__name__


class RegistroTrazas:
    def __init__(self, degradado: bool = False) -> None:
        self._degradado = degradado
        self.trazas: list[Registro] = []
        self.spans: list[Registro] = []
        self.scores: list[ScoreRegistrado] = []
        self.cerrado = False

    @property
    def degradado(self) -> bool:
        return self._degradado

    @contextmanager
    def _abrir(self, registro: Registro) -> Iterator[_Obs]:
        ficha = _padre.set(registro.id)
        try:
            yield _Obs(registro)
        finally:
            _padre.reset(ficha)

    @contextmanager
    def traza(
        self, nombre: str, *, novel_id: str, metadata: dict[str, Any] | None = None
    ) -> Iterator[ContextoTraza]:
        validar_nombre_span(nombre)
        traza_id = f"tr-{uuid.uuid4().hex[:8]}"
        registro = Registro(
            tipo="traza",
            nombre=nombre,
            traza=traza_id,
            sesion=novel_id,
            padre=None,
            metadata=dict(metadata or {}),
        )
        self.trazas.append(registro)
        f1, f2 = _traza.set(traza_id), _sesion.set(novel_id)
        try:
            with self._abrir(registro):
                yield ContextoTraza(
                    traza_id=traza_id, url=f"https://langfuse.test/{traza_id}", id_local=traza_id
                )
        finally:
            _traza.reset(f1)
            _sesion.reset(f2)

    def _nuevo(self, tipo: str, nombre: str, entrada: Any, metadata: dict[str, Any]) -> Registro:
        registro = Registro(
            tipo=tipo,
            nombre=nombre,
            traza=_traza.get(),
            sesion=_sesion.get(),
            padre=_padre.get(),
            entrada=entrada,
            metadata=metadata,
        )
        self.spans.append(registro)
        return registro

    @contextmanager
    def span(
        self, nombre: str, *, entrada: Any = None, metadata: dict[str, Any] | None = None
    ) -> Iterator[_Obs]:
        validar_nombre_span(nombre)
        with self._abrir(self._nuevo("span", nombre, entrada, dict(metadata or {}))) as obs:
            yield obs

    @contextmanager
    def generacion(self, peticion: Peticion) -> Iterator[_Obs]:
        registro = self._nuevo(
            "generacion",
            AGENTE_DE_ROL[peticion.rol],
            peticion,
            {"prompt": peticion.prompt, "hash_prompt": peticion.hash_prompt},
        )
        with self._abrir(registro) as obs:
            yield obs

    def score(
        self,
        nombre: str,
        valor: float,
        *,
        comentario: str | None,
        traza_id: str | None = None,
    ) -> None:
        self.scores.append(
            ScoreRegistrado(nombre, float(valor), comentario, traza_id or _traza.get())
        )

    def cerrar(self) -> None:
        self.cerrado = True

    # Ayudas para las pruebas -------------------------------------------------------

    def nombres(self, tipo: str | None = None) -> list[str]:
        return [s.nombre for s in self.spans if tipo is None or s.tipo == tipo]

    def scores_de(self, nombre: str) -> list[ScoreRegistrado]:
        return [s for s in self.scores if s.nombre == nombre]
