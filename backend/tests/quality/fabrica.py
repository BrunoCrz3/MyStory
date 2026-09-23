"""Mundo criticable: canon real detras y una escena todavia sin consolidar.

La escena que se critica no esta aceptada —se critica antes de aceptar—, asi que
el canon contra el que se contrasta lo dejan escenas anteriores, consolidadas
por el camino de siempre.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import EstatusDeHecho, TipoDeHecho
from app.commons.config import Umbrales, cargar_umbrales
from app.commons.db.conexion import Conexion, abrir_conexion
from app.commons.db.migraciones import aplicar_migraciones
from app.context import schemas as context_schemas
from app.context import service as contexto
from app.context.models import NivelDeCompresion
from app.novel import schemas as novel_schemas
from app.novel import service as novel
from app.quality import schemas as quality_schemas
from tests.canon.fabrica import Mundo, mundo

# Indice reservado para la escena en critica: siempre por detras del canon que
# dejan las escenas de fondo.
EN_CRITICA = 20


@contextmanager
def base_nueva() -> Iterator[Conexion]:
    with (
        tempfile.TemporaryDirectory() as carpeta,
        abrir_conexion(Path(carpeta) / "novel.db") as conexion,
    ):
        aplicar_migraciones(conexion)
        yield conexion


def umbrales() -> Umbrales:
    return cargar_umbrales()


def con_umbral_de_longitud(base: Umbrales, desviacion: float) -> Umbrales:
    return base.model_copy(
        update={
            "higiene": base.higiene.model_copy(update={"desviacion_longitud_escena": desviacion})
        }
    )


def con_fase_cerrada(base: Umbrales, umbral: float) -> Umbrales:
    """Todas las dimensiones con el mismo umbral, y la fase cerrada.

    No es una calibracion: es la unica forma de ejercitar el camino que v1 no
    recorre todavia. Que las catorce compartan valor lo deja claro.
    """
    calidad = dict.fromkeys(base.calidad.model_dump(), umbral)
    return base.model_copy(
        update={
            "calidad": base.calidad.model_copy(update=calidad),
            "medicion": base.medicion.model_copy(update={"cerrar_el_paso": True}),
            "higiene": base.higiene.model_copy(update={"desviacion_longitud_escena": 10.0}),
        }
    )


class MundoCriticable:
    def __init__(self, base: Conexion) -> None:
        self._base = base
        self._mundo: Mundo = mundo(base, escenas=2)
        self.escena_id = self._mundo.escena(EN_CRITICA)
        self.ilia = self._mundo.ilia
        self.baro = self._mundo.baro
        self.vado = self._mundo.vado
        self.orilla = self._mundo.orilla
        self.llave = self._mundo.llave
        # Una escena de fondo consolidada: sin canon no hay contra que contrastar.
        self._mundo.escena_consolidada(hechos=[])

    # --- canon de fondo ---------------------------------------------------

    def establecer(self, tipo: TipoDeHecho, **campos: Any) -> int:
        escena = self._mundo.escena_consolidada(hechos=[self._mundo.hecho(tipo, **campos)])
        return canon.hechos_establecidos_en(self._base, escena)[0].id

    def aprende(self, personaje_id: int, hecho_id: int) -> None:
        self._mundo.escena_consolidada(
            hechos=[],
            epistemicos=[
                canon_schemas.NuevoEstadoEpistemico(personaje_id=personaje_id, hecho_id=hecho_id)
            ],
        )

    def prohibir_revelacion_antes_de(self, hecho_id: int, escena_minima_id: int) -> None:
        self._mundo.escena_consolidada(
            hechos=[],
            revelaciones=[
                canon_schemas.NuevaRevelacion(
                    hecho_id=hecho_id,
                    destinatario="lector",
                    escena_minima_id=escena_minima_id,
                )
            ],
        )

    def escena_futura(self) -> int:
        return self._mundo.escena(EN_CRITICA + 1)

    # --- declaraciones de la obra ----------------------------------------

    def declarar_regla(self, enunciado: str) -> int:
        novum = novel.crear_novum(
            self._base,
            novel_schemas.NuevoNovum(
                nombre="la memoria del rio",
                mecanismo="el agua guarda voces",
                limites="solo durante la crecida",
            ),
        )
        return novel.crear_regla_del_mundo(
            self._base,
            novel_schemas.NuevaReglaDelMundo(
                novum_id=novum.id, enunciado=enunciado, alcance="toda la obra"
            ),
        ).id

    def declarar_voz_narrativa(self, persona: str, tiempo_verbal: str) -> None:
        novel.crear_voz_narrativa(
            self._base,
            novel_schemas.NuevaVozNarrativa(
                obra_id=1, persona=persona, tiempo_verbal=tiempo_verbal, focalizacion="interna"
            ),
        )

    def sembrar_dialogo_distinguible(self) -> None:
        """Dos voces con lexico separado, para que el clasificador ciego pueda."""
        voces = {
            self.ilia: [
                "Cruzar cuesta. Cruzar siempre cuesta y nadie lo cuenta.",
                "Cuesta cruzar de noche, cuesta mas volver.",
                "Nadie cuenta lo que cuesta cruzar el vado.",
                "Cruzo, cuesta, vuelvo: asi cada noche.",
            ],
            self.baro: [
                "Son doce monedas, ni una menos, y el peaje se paga antes.",
                "Doce monedas, siempre doce, y el peaje primero.",
                "El peaje son monedas, no favores. Doce.",
                "Monedas, peaje, cuentas claras. Doce monedas.",
            ],
        }
        dimension = umbrales().embeddings.dimension or 1
        for personaje, frases in voces.items():
            for frase in frases:
                contexto.indexar_fragmento(
                    self._base,
                    umbrales(),
                    context_schemas.NuevoFragmento(
                        escena_id=self._mundo.escena(0),
                        texto=frase,
                        nivel=NivelDeCompresion.ESCENA_LITERAL,
                        entidades=[context_schemas.Referencia(tipo="personaje", id=personaje)],
                        embedding=[0.1] * dimension,
                    ),
                )


def mundo_criticable(base: Conexion) -> MundoCriticable:
    return MundoCriticable(base)


def peticion(
    mundo_criticable: MundoCriticable,
    texto: str = "Ilia cruzo el vado, pero la puerta ya estaba abierta; por tanto entro.",
    version: int = 1,
    pov_personaje_id: int | None = None,
) -> quality_schemas.PeticionDeCritica:
    return quality_schemas.PeticionDeCritica(
        escena_id=mundo_criticable.escena_id,
        version=version,
        texto=texto,
        brief="Ilia vuelve al vado.",
        restriccion_de_destino="Termina dentro y sin la llave.",
        personajes_presentes=[mundo_criticable.ilia, mundo_criticable.baro],
        pov_personaje_id=pov_personaje_id or mundo_criticable.ilia,
    )


def puntuacion(informe: Any, dimension: str) -> Any:
    return next(p for p in informe.puntuaciones if p.dimension == dimension)


__all__ = [
    "EstatusDeHecho",
    "MundoCriticable",
    "base_nueva",
    "con_fase_cerrada",
    "con_umbral_de_longitud",
    "mundo_criticable",
    "peticion",
    "puntuacion",
    "umbrales",
]
