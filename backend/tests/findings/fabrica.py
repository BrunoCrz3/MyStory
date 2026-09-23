"""Mundo con escenas consolidadas de las que se puede extraer.

Se apoya en la fabrica de `canon/`, que es la que consolida por el camino de
siempre: aqui no hay ninguna via que meta un hallazgo sin extraccion ni una
extraccion sin consolidacion, porque en produccion tampoco la hay.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import TipoDeHecho
from app.commons.config import Umbrales, cargar_umbrales
from app.commons.db.conexion import Conexion, abrir_conexion
from app.commons.db.migraciones import aplicar_migraciones
from app.findings import schemas as findings_schemas
from app.findings import service as hallazgos
from app.findings.models import EstadoDeHallazgo, ModoDeAdopcion
from app.novel import schemas as novel_schemas
from app.novel import service as novel
from tests.canon.fabrica import Mundo, mundo


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


class MundoConHallazgos:
    def __init__(self, base: Conexion) -> None:
        self.base = base
        self.mundo: Mundo = mundo(base, escenas=1)
        self.ilia = self.mundo.ilia
        self.baro = self.mundo.baro
        self.vado = self.mundo.vado
        self.orilla = self.mundo.orilla
        self.llave = self.mundo.llave

    def escena_con_hecho(self, valor: str) -> int:
        """Una escena aceptada y consolidada cuyo hecho afirma `valor`.

        El anclaje textual de RF-CANON-11 exige que los terminos del hecho esten
        en la prosa, y la fabrica de `canon/` construye el texto a partir del
        hecho para que eso se cumpla. Aqui interesa el enunciado: es lo que el
        extractor lee.
        """
        return self.mundo.escena_consolidada(
            hechos=[self.mundo.hecho(TipoDeHecho.DESCRIPTIVO, sujeto=self.ilia, valor=valor)]
        )

    def escena_sin_hechos(self) -> int:
        return self.mundo.escena_consolidada(hechos=[])

    def escena_planificada(self) -> int:
        """Sin consolidar: es la que la extraccion tiene que rechazar."""
        return self.mundo.escena(9)

    def hecho_de(self, escena_id: int) -> int:
        return canon.hechos_establecidos_en(self.base, escena_id)[0].id

    def declarar_motivo(self, nombre: str, forma: str) -> int:
        return novel.crear_motivo(
            self.base, novel_schemas.NuevoMotivo(nombre=nombre, forma=forma)
        ).id

    def registrar_aparicion(self, motivo_id: int, escena_id: int) -> None:
        self.base.execute(
            "INSERT INTO motivo_escena (motivo_id, escena_id) VALUES (?, ?)",
            (motivo_id, escena_id),
        )

    def extraer(
        self,
        escena_id: int,
        candidaturas: list[findings_schemas.Candidatura] | None = None,
        texto: str | None = None,
    ) -> findings_schemas.ResultadoDeExtraccion:
        """Extrae de la prosa con la que se consolido esa escena.

        Quien llama trae el texto, como en produccion: `findings/` no es dueno de
        la prosa. La fabrica lo recuerda para no tener que reconstruirlo.
        """
        return hallazgos.extraer(
            self.base,
            escena_id,
            findings_schemas.PeticionDeExtraccion(
                version=1,
                texto=texto if texto is not None else self.mundo.textos.get(escena_id, ""),
                candidaturas=candidaturas or [],
            ),
        )

    def decidir(
        self,
        hallazgo_id: int,
        destino: EstadoDeHallazgo,
        **destinos: int,
    ) -> object:
        """Como el autor: es el unico que puede, y la fabrica hace de autor."""
        return hallazgos.decidir(
            self.base,
            hallazgo_id,
            findings_schemas.DecisionDelAutor(destino=destino, **destinos),
            modo=ModoDeAdopcion.HUMANA,
        )

    def promesa_de(self, escena_id: int) -> int:
        return canon.promesas_abiertas_en(self.base, escena_id)[0].id

    def consolidacion(self, escena_id: int, texto: str) -> canon_schemas.Consolidacion:
        return canon_schemas.Consolidacion(escena_id=escena_id, version=1, texto=texto)


def mundo_con_hallazgos(base: Conexion) -> MundoConHallazgos:
    return MundoConHallazgos(base)


def candidatura(tipo: str, texto: str) -> findings_schemas.Candidatura:
    from app.findings.models import TipoDeHallazgo

    return findings_schemas.Candidatura(tipo=TipoDeHallazgo(tipo), texto=texto)


__all__ = [
    "MundoConHallazgos",
    "base_nueva",
    "candidatura",
    "mundo_con_hallazgos",
    "umbrales",
]
