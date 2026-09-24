"""`PolicyEngine`: lo que antes decidía el autor humano (`definitions.md` Capa 5).

Adopta o descarta un hecho, acepta o devuelve un capítulo, y detiene la generación. **Cada
decisión deja una fila en el audit log** con la regla aplicada, la entrada y el resultado
(RF-POL-01): si nadie puede reconstruir por qué se adoptó un hecho, la automatización ha
cambiado un juicio por un misterio.

`policy/` no importa `canon/`, `quality/` ni `guardrail/`: recibe lo que decide por
`Protocol` estructurales y veredictos propios, y así el grafo de importación no crece.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.tiempo import ahora
from app.policy import repository
from app.policy.repository import DecisionRegistrada

__all__ = [
    "DecisionCapitulo",
    "DecisionRegistrada",
    "PolicyEngine",
    "Veredicto",
    "decisiones",
]


class HechoADecidir(Protocol):
    @property
    def hecho_id(self) -> str: ...

    @property
    def enunciado(self) -> str: ...

    @property
    def fragmento_soporte(self) -> str: ...


class CoincidenciaARegistrar(Protocol):
    @property
    def palabra(self) -> str: ...

    @property
    def nivel(self) -> str: ...

    @property
    def inicio(self) -> int: ...

    @property
    def fin(self) -> int: ...


class Veredicto(BaseModel):
    """Resultado de un validador, tal como lo necesita la decisión sobre el capítulo."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    pasa: bool
    cierra_el_paso: bool
    valor: float | None = None


AccionCapitulo = Literal["aceptar", "devolver", "agotar", "detener"]


class DecisionCapitulo(BaseModel):
    model_config = ConfigDict(frozen=True)

    accion: AccionCapitulo
    regla: str
    fallidos: list[str]
    detenida_por: str | None = None


def _normalizar(enunciado: str) -> str:
    return " ".join(enunciado.lower().split())


class PolicyEngine:
    def __init__(self, config: Config) -> None:
        self.config = config

    def _registrar(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        sujeto: str,
        sujeto_id: str,
        regla: str,
        entrada: dict[str, Any],
        resultado: str,
    ) -> None:
        repository.insertar_decision(
            con,
            novel_id=novel_id,
            sujeto=sujeto,
            sujeto_id=sujeto_id,
            regla=regla,
            entrada=json.dumps(entrada, ensure_ascii=False, default=str),
            resultado=resultado,
            momento=ahora(),
        )

    def decidir_hecho(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        texto: str,
        hecho: HechoADecidir,
        conocidos: Sequence[str],
    ) -> bool:
        """Adopta un hecho propuesto si está anclado en el texto y no repite uno vigente."""
        entrada = {"enunciado": hecho.enunciado, "fragmento": hecho.fragmento_soporte}
        if not hecho.enunciado.strip():
            regla, adoptar = "enunciado-vacio", False
        elif hecho.fragmento_soporte.strip() not in texto:
            regla, adoptar = "sin-fragmento-literal", False
        elif _normalizar(hecho.enunciado) in {_normalizar(c) for c in conocidos}:
            regla, adoptar = "duplicado-de-hecho-vigente", False
        else:
            regla, adoptar = "fragmento-literal-y-nuevo", True
        self._registrar(
            con,
            novel_id=novel_id,
            sujeto="hecho",
            sujeto_id=hecho.hecho_id,
            regla=regla,
            entrada=entrada,
            resultado="adoptar" if adoptar else "descartar",
        )
        return adoptar

    def decidir_capitulo(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        capitulo_id: str,
        intentos: int,
        veredictos: Sequence[Veredicto],
        reescrituras_por_guardrail: int,
    ) -> DecisionCapitulo:
        """Acepta, devuelve, agota o detiene.

        `intentos` son las reescrituras ya gastadas del capítulo; `reescrituras_por_guardrail`,
        las pasadas **consecutivas** con palabra vetada contando esta. El guardrail es un
        sublímite dentro del contador del capítulo (TO-014).
        """
        fallidos = [v.nombre for v in veredictos if v.cierra_el_paso and not v.pasa]
        orq = self.config.umbrales.orquestacion
        if not fallidos:
            decision = DecisionCapitulo(
                accion="aceptar", regla="todos-los-validadores-que-cierran-pasan", fallidos=[]
            )
        elif (
            "palabras_prohibidas" in fallidos
            and reescrituras_por_guardrail >= self.config.umbrales.guardrail.max_reescrituras
        ):
            decision = DecisionCapitulo(
                accion="detener",
                regla="palabra-prohibida-persistente",
                fallidos=fallidos,
                detenida_por="palabra-prohibida-persistente",
            )
        elif intentos >= orq.max_intentos_capitulo:
            decision = DecisionCapitulo(
                accion="agotar",
                regla="limite-de-intentos-agotado",
                fallidos=fallidos,
                detenida_por="limite-de-intentos-agotado",
            )
        else:
            decision = DecisionCapitulo(
                accion="devolver", regla="validador-que-cierra-falla", fallidos=fallidos
            )
        self._registrar(
            con,
            novel_id=novel_id,
            sujeto="capitulo",
            sujeto_id=capitulo_id,
            regla=decision.regla,
            entrada={
                "intentos": intentos,
                "reescrituras_por_guardrail": reescrituras_por_guardrail,
                "veredictos": [v.model_dump() for v in veredictos],
            },
            resultado=decision.accion,
        )
        return decision

    def registrar_coincidencias(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        capitulo_id: str,
        intento: int,
        coincidencias: Sequence[CoincidenciaARegistrar],
    ) -> None:
        """Toda coincidencia queda en su tabla y en el audit log (fila O-07)."""
        for c in coincidencias:
            repository.insertar_coincidencia(
                con,
                novel_id=novel_id,
                capitulo_id=capitulo_id,
                palabra=c.palabra,
                nivel=c.nivel,
                inicio=c.inicio,
                fin=c.fin,
                intento=intento,
            )
        if coincidencias:
            self._registrar(
                con,
                novel_id=novel_id,
                sujeto="capitulo",
                sujeto_id=capitulo_id,
                regla="palabra-prohibida",
                entrada={
                    "intento": intento,
                    "coincidencias": [
                        {"palabra": c.palabra, "nivel": c.nivel, "inicio": c.inicio}
                        for c in coincidencias
                    ],
                },
                resultado="devolver",
            )

    def registrar_detencion(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        generacion_id: str,
        motivo: str,
        detalle: dict[str, Any],
    ) -> None:
        self._registrar(
            con,
            novel_id=novel_id,
            sujeto="generacion",
            sujeto_id=generacion_id,
            regla=motivo,
            entrada=detalle,
            resultado="detener",
        )


def decisiones(con: sqlite3.Connection, *, novel_id: str) -> list[DecisionRegistrada]:
    """El audit log de una novela, en orden (pregunta 31)."""
    return repository.leer_decisiones(con, novel_id=novel_id)
