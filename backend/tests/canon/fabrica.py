"""Mundo de prueba para canon: obra real, escenas reales, canon por consolidacion.

Nada entra en el canon por la puerta de atras. `escena_consolidada` acepta la
escena y la consolida, que es el unico camino que el sistema tiene, asi que las
pruebas ejercitan el mismo codigo que la produccion.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from itertools import count
from pathlib import Path

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import EstadoDePromesa, EstatusDeHecho, TipoDeHecho
from app.commons.db.conexion import Conexion, abrir_conexion
from app.commons.db.migraciones import aplicar_migraciones
from app.novel import schemas as novel_schemas
from app.novel import service as novel
from app.novel.models import EstadoDeEscena
from tests.novel.fabrica import transicionar

CAMINO_DEL_HECHO = {
    EstatusDeHecho.PROVISIONAL: (),
    EstatusDeHecho.IMPLICITO: (EstatusDeHecho.IMPLICITO,),
    EstatusDeHecho.CONFIRMADO: (EstatusDeHecho.CONFIRMADO,),
    EstatusDeHecho.RETCONEADO: (EstatusDeHecho.CONFIRMADO, EstatusDeHecho.RETCONEADO),
    EstatusDeHecho.REFUTADO: (EstatusDeHecho.CONFIRMADO, EstatusDeHecho.REFUTADO),
}


@contextmanager
def base_nueva() -> Iterator[Conexion]:
    """Base migrada y desechable, una por ejemplo de Hypothesis.

    Las fixtures de pytest son de funcion, no de ejemplo: reutilizarlas dentro
    de `@given` acumula estado entre ejemplos y convierte una propiedad en una
    secuencia. Cada ejemplo necesita su base.
    """
    with (
        tempfile.TemporaryDirectory() as carpeta,
        abrir_conexion(Path(carpeta) / "novel.db") as conexion,
    ):
        aplicar_migraciones(conexion)
        yield conexion


def aprende(
    personaje_id: int, hecho_id: int, certeza: str = "certeza"
) -> canon_schemas.NuevoEstadoEpistemico:
    return canon_schemas.NuevoEstadoEpistemico(
        personaje_id=personaje_id, hecho_id=hecho_id, certeza=certeza
    )


class Mundo:
    """Una obra con dos personajes, dos lugares y un artefacto."""

    def __init__(self, base: Conexion, escenas: int) -> None:
        self._base = base
        self._siguiente_orden = count(1)

        obra = novel.crear_obra(
            base,
            novel_schemas.NuevaObra(
                titulo="El vado",
                premisa="un puente recuerda",
                genero="cf",
                extension_objetivo=90000,
            ),
        )
        parte = novel.crear_parte(
            base,
            novel_schemas.NuevaParte(
                obra_id=obra.id, orden=1, funcion_dramatica="planteamiento", punto_de_giro="habla"
            ),
        )
        self._capitulo = novel.crear_capitulo(
            base, novel_schemas.NuevoCapitulo(parte_id=parte.id, orden=1)
        ).id

        self.ilia = novel.crear_personaje(base, novel_schemas.NuevoPersonaje(nombre="Ilia")).id
        self.baro = novel.crear_personaje(base, novel_schemas.NuevoPersonaje(nombre="Baro")).id
        self.vado = novel.crear_lugar(base, novel_schemas.NuevoLugar(nombre="El vado")).id
        self.orilla = novel.crear_lugar(base, novel_schemas.NuevoLugar(nombre="La orilla norte")).id
        self.llave = novel.crear_artefacto(
            base, novel_schemas.NuevoArtefacto(nombre="La llave de piedra")
        ).id

        # Las claves llevan el tipo: los `id` de personaje, lugar y artefacto son
        # secuencias independientes y el 1 de cada una es una entidad distinta.
        self._nombres: dict[tuple[str, int], str] = {
            ("sujeto_personaje_id", self.ilia): "Ilia",
            ("objeto_personaje_id", self.ilia): "Ilia",
            ("sujeto_personaje_id", self.baro): "Baro",
            ("objeto_personaje_id", self.baro): "Baro",
            ("lugar_id", self.vado): "El vado",
            ("lugar_id", self.orilla): "La orilla norte",
            ("artefacto_id", self.llave): "La llave de piedra",
        }
        self._escenas: list[int] = [self._escena_nueva() for _ in range(escenas)]
        self._consumidas = 0
        # La prosa con la que se consolido cada escena. En produccion la guarda
        # la memoria episodica; aqui hace falta porque el extractor la lee.
        self.textos: dict[int, str] = {}

    # --- escenas ----------------------------------------------------------

    def _escena_nueva(self) -> int:
        return novel.crear_escena(
            self._base,
            novel_schemas.NuevaEscena(
                capitulo_id=self._capitulo, orden=next(self._siguiente_orden), objetivo="cruzar"
            ),
        ).id

    def _siguiente_escena(self) -> int:
        if self._consumidas == len(self._escenas):
            self._escenas.append(self._escena_nueva())
        escena_id = self._escenas[self._consumidas]
        self._consumidas += 1
        return escena_id

    def escena(self, indice: int) -> int:
        while indice >= len(self._escenas):
            self._escenas.append(self._escena_nueva())
        return self._escenas[indice]

    def escena_consolidada(
        self,
        hechos: list[canon_schemas.NuevoHechoCanonico],
        promesas: list[str] | None = None,
        epistemicos: list[canon_schemas.NuevoEstadoEpistemico] | None = None,
        revelaciones: list[canon_schemas.NuevaRevelacion] | None = None,
        fecha_ficcional: str | None = None,
    ) -> int:
        escena_id = self._siguiente_escena()
        for paso in (
            EstadoDeEscena.EN_BORRADOR,
            EstadoDeEscena.EN_REVISION,
            EstadoDeEscena.ACEPTADA,
        ):
            transicionar(self._base, escena_id, paso)

        self.textos[escena_id] = self._texto_para(hechos, promesas or [])
        canon.consolidar_escena(
            self._base,
            canon_schemas.Consolidacion(
                escena_id=escena_id,
                version=1,
                texto=self.textos[escena_id],
                fecha_ficcional=fecha_ficcional,
                hechos=hechos,
                promesas=[
                    canon_schemas.NuevaPromesaNarrativa(texto=texto, tipo="setup")
                    for texto in (promesas or [])
                ],
                epistemicos=epistemicos or [],
                revelaciones=revelaciones or [],
            ),
        )
        return escena_id

    def _texto_para(
        self, hechos: list[canon_schemas.NuevoHechoCanonico], promesas: list[str]
    ) -> str:
        """El texto de la escena contiene lo que los hechos afirman.

        Es lo que hace que el anclaje de RF-CANON-11 pase: en produccion lo
        garantiza el extractor leyendo la escena; aqui se construye al reves.
        """
        piezas = ["Una escena del vado."]
        for hecho in hechos:
            piezas.append(hecho.texto)
            for columna in (
                "sujeto_personaje_id",
                "objeto_personaje_id",
                "lugar_id",
                "artefacto_id",
            ):
                entidad = getattr(hecho, columna)
                if entidad is not None:
                    piezas.append(self._nombres[(columna, entidad)])
        piezas.extend(promesas)
        return " ".join(piezas)

    # --- hechos -----------------------------------------------------------

    def hecho(
        self,
        tipo: TipoDeHecho,
        sujeto: int | None = None,
        lugar: int | None = None,
        artefacto: int | None = None,
        objeto: int | None = None,
        valor: str | None = None,
        sucede_a_hecho_id: int | None = None,
        estatus: EstatusDeHecho = EstatusDeHecho.CONFIRMADO,
    ) -> canon_schemas.NuevoHechoCanonico:
        def nombre(columna: str, entidad: int | None) -> str:
            return "" if entidad is None else self._nombres[(columna, entidad)]

        descripcion = " ".join(
            filtrado
            for filtrado in (
                nombre("sujeto_personaje_id", sujeto),
                tipo.value,
                valor or "",
                nombre("lugar_id", lugar),
                nombre("artefacto_id", artefacto),
                nombre("objeto_personaje_id", objeto),
            )
            if filtrado
        )
        return canon_schemas.NuevoHechoCanonico(
            texto=descripcion,
            tipo=tipo,
            estatus=estatus,
            sujeto_personaje_id=sujeto,
            lugar_id=lugar,
            artefacto_id=artefacto,
            objeto_personaje_id=objeto,
            valor=valor,
            sucede_a_hecho_id=sucede_a_hecho_id,
        )

    def hechos_que_mueven_el_mundo(self, paso: int) -> list[canon_schemas.NuevoHechoCanonico]:
        quien = self.ilia if paso % 2 == 0 else self.baro
        donde = self.vado if paso % 2 == 0 else self.orilla
        return [
            self.hecho(TipoDeHecho.UBICACION, sujeto=quien, lugar=donde),
            self.hecho(TipoDeHecho.POSESION, sujeto=quien, artefacto=self.llave),
        ]

    def hecho_en(self, estatus: EstatusDeHecho) -> int:
        escena_id = self.escena_consolidada(
            hechos=[
                self.hecho(
                    TipoDeHecho.DESCRIPTIVO,
                    sujeto=self.ilia,
                    valor="mira el agua",
                    estatus=EstatusDeHecho.PROVISIONAL,
                )
            ]
        )
        hecho_id = canon.hechos_establecidos_en(self._base, escena_id)[0].id
        for paso in CAMINO_DEL_HECHO[estatus]:
            canon.transicionar_hecho(self._base, hecho_id, paso)
        return hecho_id

    def hecho_nuevo(self, sucede_a_hecho_id: int) -> object:
        escena_id = self.escena_consolidada(
            hechos=[
                self.hecho(
                    TipoDeHecho.DESCRIPTIVO,
                    sujeto=self.ilia,
                    valor="si cruzo, pero de noche",
                    sucede_a_hecho_id=sucede_a_hecho_id,
                )
            ]
        )
        return canon.hechos_establecidos_en(self._base, escena_id)[0]

    # --- promesas, arcos e hilos -----------------------------------------

    def promesa_en(self, estado: EstadoDePromesa) -> tuple[int, int]:
        apertura = self.escena_consolidada(hechos=[], promesas=["que el rio conteste"])
        promesa = canon.promesas_abiertas_en(self._base, apertura)[0]
        pago = self.escena_consolidada(hechos=[])
        if estado is not EstadoDePromesa.PENDIENTE:
            canon.transicionar_promesa(self._base, promesa.id, estado, pago)
        return promesa.id, pago

    def un_arco_que_avanza_en(self, indice: int) -> int:
        arco = novel.crear_arco(self._base, novel_schemas.NuevoArco(nombre="el pacto")).id
        self._base.execute(
            "INSERT INTO arco_escena (arco_id, escena_id) VALUES (?, ?)",
            (arco, self.escena(indice)),
        )
        return arco

    def un_hilo_que_avanza_en(self, indice: int) -> int:
        hilo = novel.crear_hilo_de_trama(
            self._base, novel_schemas.NuevoHiloDeTrama(nombre="el peaje", tipo="principal")
        ).id
        self._base.execute(
            "INSERT INTO escena_hilo (escena_id, hilo_id) VALUES (?, ?)",
            (self.escena(indice), hilo),
        )
        return hilo


def mundo(base: Conexion, escenas: int = 4) -> Mundo:
    return Mundo(base, escenas)


def aceptar(base: Conexion, escena_id: int) -> None:
    """Lleva la escena hasta `aceptada` por el camino del diagrama."""
    for paso in (
        EstadoDeEscena.EN_BORRADOR,
        EstadoDeEscena.EN_REVISION,
        EstadoDeEscena.ACEPTADA,
    ):
        transicionar(base, escena_id, paso)
