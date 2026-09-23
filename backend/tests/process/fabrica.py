"""Mundo del ciclo: una obra con pasado consolidado y futuro declarado.

Las dos mitades importan, y son distintas. El **pasado** son escenas aceptadas y
consolidadas por el camino de siempre: el canon en `t` sale de ahi y no de
ninguna puerta trasera. El **futuro** son escenas `planificada` con su brief y
sus restricciones de destino, que es lo unico que el esquema declara de lo que
todavia no se ha escrito, y por tanto la unica superficie sobre la que la deriva
puede medir.

## Por que hay un modelo de laboratorio

`ModeloDeLaboratorio` no es un mock de produccion: vive aqui, en `tests/`, y el
comprobador de RD-07 solo mira `app/`. Existe porque la suite no puede llamar a
la API del proveedor --ni debe: una prueba que depende de la red no es una
prueba de regresion-- y porque lo que estas pruebas afirman no es que el modelo
escriba bien, sino que **alrededor** de la llamada pasen las cosas que tienen que
pasar: admision en el pool, registro de generacion, version con su trazabilidad
y nada ejecutado de lo que devuelva.

Es el motivo exacto por el que `commons/llm/cliente.py` declara el protocolo
`Generador`: para que la puerta que registra dependa del contrato y no del SDK.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import EstadoDePromesa, TipoDeHecho
from app.commons.config import Umbrales, cargar_umbrales
from app.commons.db.conexion import Conexion, abrir_conexion
from app.commons.db.migraciones import aplicar_migraciones
from app.commons.llm.cliente import RespuestaDelModelo
from app.novel import models as novel_models
from app.novel import schemas as novel_schemas
from app.novel import service as novel
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.models import TipoDeRestriccion
from tests.canon.fabrica import Mundo, mundo

# El futuro vive en su propio capitulo, el segundo de la parte. `escena_ordenada`
# ordena por parte, capitulo y escena, asi que todo lo que se crea ahi queda por
# detras de lo ya escrito sin tener que reservar huecos ni contar indices. Y
# ademas es lo que pasa de verdad: lo que falta por escribir es el capitulo
# siguiente.
ORDEN_DEL_CAPITULO_FUTURO = 2

TEXTO_GENERADO = (
    "Ilia cruzo el vado antes de que el agua subiera. La orilla norte seguia "
    "donde la habia dejado, y la llave de piedra pesaba mas que la noche."
)


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


def con_densidad_minima(base: Umbrales, minima: float) -> Umbrales:
    return base.model_copy(
        update={"deriva": base.deriva.model_copy(update={"densidad_declaracion_minima": minima})}
    )


class ModeloDeLaboratorio:
    """Un `Generador` determinista. Guarda lo que se le pidio."""

    def __init__(self, texto: str = TEXTO_GENERADO) -> None:
        self.texto = texto
        self.prompts: list[str] = []

    async def generar(
        self, mensajes: list[dict[str, Any]], sistema: str | None = None
    ) -> RespuestaDelModelo:
        del sistema
        self.prompts.append(str(mensajes[0]["content"]))
        return RespuestaDelModelo(
            texto=self.texto,
            modelo="modelo-de-laboratorio",
            tokens_de_entrada=len(self.prompts[-1]),
            tokens_de_salida=len(self.texto),
        )


class MundoDelCiclo:
    """Una obra con dos personajes, dos lugares, un artefacto y un plan."""

    def __init__(self, base: Conexion) -> None:
        self.base = base
        self.mundo: Mundo = mundo(base, escenas=1)
        self.ilia = self.mundo.ilia
        self.baro = self.mundo.baro
        self.vado = self.mundo.vado
        self.orilla = self.mundo.orilla
        self.llave = self.mundo.llave
        parte = novel.listar(base, novel_models.Parte)[0]
        self._capitulo_futuro = novel.crear_capitulo(
            base,
            novel_schemas.NuevoCapitulo(parte_id=parte.id, orden=ORDEN_DEL_CAPITULO_FUTURO),
        ).id
        self._futuras = 0

    # --- pasado: canon consolidado ---------------------------------------

    def escena_consolidada(
        self,
        hechos: list[canon_schemas.NuevoHechoCanonico] | None = None,
        promesas: list[str] | None = None,
    ) -> int:
        return self.mundo.escena_consolidada(hechos=hechos or [], promesas=promesas or [])

    def matar(self, personaje_id: int) -> int:
        """Un hecho de estado vital que saca al personaje del mundo."""
        return self.mundo.escena_consolidada(
            hechos=[self.mundo.hecho(TipoDeHecho.ESTADO_VITAL, sujeto=personaje_id, valor="muerto")]
        )

    def situar(self, personaje_id: int, lugar_id: int) -> int:
        return self.mundo.escena_consolidada(
            hechos=[self.mundo.hecho(TipoDeHecho.UBICACION, sujeto=personaje_id, lugar=lugar_id)]
        )

    def hecho_descriptivo(self, valor: str) -> int:
        escena = self.mundo.escena_consolidada(
            hechos=[self.mundo.hecho(TipoDeHecho.DESCRIPTIVO, sujeto=self.ilia, valor=valor)]
        )
        return canon.hechos_establecidos_en(self.base, escena)[0].id

    def promesa_pendiente(self, texto: str = "que el rio conteste") -> int:
        escena = self.mundo.escena_consolidada(hechos=[], promesas=[texto])
        return [
            promesa
            for promesa in canon.promesas_abiertas_en(self.base, escena)
            if canon.escena_de_apertura(self.base, promesa.id) == escena
        ][0].id

    def pagar(self, promesa_id: int) -> None:
        pago = self.mundo.escena_consolidada(hechos=[])
        canon.transicionar_promesa(self.base, promesa_id, EstadoDePromesa.PAGADA, pago)

    def hilo(self, nombre: str = "el peaje") -> int:
        return novel.crear_hilo_de_trama(
            self.base, novel_schemas.NuevoHiloDeTrama(nombre=nombre, tipo="principal")
        ).id

    def avanzar_hilo(self, hilo_id: int, escena_id: int) -> None:
        self.base.execute(
            "INSERT INTO escena_hilo (escena_id, hilo_id) VALUES (?, ?)", (escena_id, hilo_id)
        )

    # --- futuro: el plan --------------------------------------------------

    def escena_por_escribir(self) -> int:
        """Una escena `planificada`, en el capitulo que aun no se ha escrito."""
        self._futuras += 1
        return novel.crear_escena(
            self.base,
            novel_schemas.NuevaEscena(
                capitulo_id=self._capitulo_futuro,
                orden=self._futuras,
                objetivo="cruzar de vuelta",
            ),
        ).id

    def brief(
        self,
        escena_id: int,
        restricciones: list[process_schemas.NuevaRestriccion],
        estado_de_entrada: str = "Ilia llega al vado con la llave",
    ) -> process_schemas.BriefCompleto:
        return proceso.crear_brief(
            self.base,
            process_schemas.NuevoBrief(
                escena_id=escena_id,
                estado_de_entrada=estado_de_entrada,
                encargo="Ilia vuelve al vado y no sale con lo que traia.",
                restricciones=restricciones,
            ),
        )

    def encargar(
        self, restricciones: list[process_schemas.NuevaRestriccion]
    ) -> process_schemas.BriefCompleto:
        """Una escena por escribir, con su brief. El caso corriente."""
        return self.brief(self.escena_por_escribir(), restricciones)

    def fijar_hito(self, motivo: str = "plan inicial") -> Any:
        return proceso.fijar_hito(self.base, process_schemas.NuevoHito(motivo=motivo))


def mundo_del_ciclo(base: Conexion) -> MundoDelCiclo:
    return MundoDelCiclo(base)


# --- Restricciones de destino, en su forma cotejable ----------------------


def posicion(personaje_id: int, lugar_id: int) -> process_schemas.NuevaRestriccion:
    return process_schemas.NuevaRestriccion(
        tipo=TipoDeRestriccion.POSICION_DE_PERSONAJE,
        enunciado="termina en la orilla norte",
        personaje_id=personaje_id,
        lugar_id=lugar_id,
    )


def estado_final(personaje_id: int, valor: str = "vivo") -> process_schemas.NuevaRestriccion:
    return process_schemas.NuevaRestriccion(
        tipo=TipoDeRestriccion.ESTADO_FINAL,
        enunciado=f"termina {valor}",
        personaje_id=personaje_id,
        valor=valor,
    )


def revelacion(
    hecho_id: int | None = None, personaje_id: int | None = None
) -> process_schemas.NuevaRestriccion:
    return process_schemas.NuevaRestriccion(
        tipo=TipoDeRestriccion.REVELACION,
        enunciado="se sabra lo del puente",
        hecho_id=hecho_id,
        personaje_id=personaje_id,
    )


__all__ = [
    "ORDEN_DEL_CAPITULO_FUTURO",
    "TEXTO_GENERADO",
    "ModeloDeLaboratorio",
    "MundoDelCiclo",
    "base_nueva",
    "con_densidad_minima",
    "estado_final",
    "mundo_del_ciclo",
    "posicion",
    "revelacion",
    "umbrales",
]
