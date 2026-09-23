"""Reglas de dominio de `novel/`. Es donde vive la regla, no en el router.

Dos cosas que el esquema no puede decir y por eso estan aqui:

- **Las transiciones de `Escena`.** SQLite cierra la lista de estados con un
  `CHECK`, pero no sabe de que estado se viene. Ponerlo en un trigger lo
  escondería del sitio donde se leen las reglas.
- **Las condiciones de A-51.** «Al menos una regla del mundo» es una condicion
  sobre otra tabla, y un `CHECK` no la ve.
"""

from __future__ import annotations

from app.commons.db.conexion import Conexion
from app.commons.errores import (
    AceptacionSoloDelAutor,
    ActoIncompleto,
    NovumSinLimites,
    NovumSinRegla,
    TransicionInvalida,
)
from app.novel import models, repository, schemas
from app.novel.models import EstadoDeEscena, EstadoDeHilo, ModoDeAceptacion


def obtener[E: models.Entidad](base: Conexion, modelo: type[E], identificador: int) -> E:
    """Relectura sin regla propia; el servicio sigue siendo la unica puerta."""
    return repository.obtener(base, modelo, identificador)


def listar[E: models.Entidad](base: Conexion, modelo: type[E]) -> list[E]:
    return repository.listar(base, modelo)


# --- Arbol estructural ----------------------------------------------------


def crear_obra(base: Conexion, datos: schemas.NuevaObra) -> models.Obra:
    return repository.insertar_obra(base, datos)


def obtener_obra(base: Conexion) -> models.Obra:
    return repository.obtener_la_obra(base)


def crear_parte(base: Conexion, datos: schemas.NuevaParte) -> models.Parte:
    """A-51, RF-NOVEL-06: un acto sin funcion dramatica ni punto de giro no es
    un acto, es un monton de capitulos."""
    if not _declarado(datos.funcion_dramatica):
        raise ActoIncompleto("una Parte / Acto necesita su funcion dramatica declarada")
    if not _declarado(datos.punto_de_giro):
        raise ActoIncompleto("una Parte / Acto necesita el punto de giro que la cierra")
    return repository.insertar_parte(base, datos)


def crear_capitulo(base: Conexion, datos: schemas.NuevoCapitulo) -> models.Capitulo:
    return repository.insertar_capitulo(base, datos)


def crear_escena(base: Conexion, datos: schemas.NuevaEscena) -> models.Escena:
    return repository.insertar_escena(base, datos)


def obtener_escena(base: Conexion, escena_id: int) -> models.Escena:
    return repository.obtener(base, models.Escena, escena_id)


def transicionar_escena(
    base: Conexion,
    escena_id: int,
    destino: EstadoDeEscena,
    *,
    modo_de_aceptacion: ModoDeAceptacion = ModoDeAceptacion.AUTOMATICA,
) -> models.Escena:
    """A-29, RF-NOVEL-04. Ninguna transicion fuera del diagrama.

    Y una que el diagrama dibuja pero nadie automatico puede dar: la de
    `aceptada` (RF-PROC-07, P-19). El guardarrail vive aqui, en la unica puerta
    que escribe el estado de una escena, y no en el orquestador: una regla que
    solo se cumple en el camino que alguien se acordo de pasar no es un
    guardarrail, es una costumbre.
    """
    escena = obtener_escena(base, escena_id)
    if destino not in models.TRANSICIONES[escena.estado]:
        raise TransicionInvalida(
            f"la escena {escena_id} esta en '{escena.estado.value}' y el diagrama no "
            f"dibuja una transicion a '{destino.value}'"
        )
    if destino is EstadoDeEscena.ACEPTADA and modo_de_aceptacion is not ModoDeAceptacion.HUMANA:
        raise AceptacionSoloDelAutor(
            f"la escena {escena_id} solo pasa a 'aceptada' por decision del autor humano: "
            "ningun agente ni el orquestador pueden darla"
        )
    return repository.actualizar_estado_de_escena(base, escena_id, destino)


def crear_beat(base: Conexion, datos: schemas.NuevoBeat) -> models.Beat:
    return repository.insertar_beat(base, datos)


# --- Entidades narrativas -------------------------------------------------


def crear_personaje(base: Conexion, datos: schemas.NuevoPersonaje) -> models.Personaje:
    return repository.insertar_personaje(base, datos)


def crear_voz(base: Conexion, datos: schemas.NuevaVoz) -> models.Voz:
    return repository.insertar_voz(base, datos)


def crear_arco(base: Conexion, datos: schemas.NuevoArco) -> models.Arco:
    return repository.insertar_arco(base, datos)


def crear_hilo_de_trama(base: Conexion, datos: schemas.NuevoHiloDeTrama) -> models.HiloDeTrama:
    return repository.insertar_hilo_de_trama(base, datos)


def transicionar_hilo(base: Conexion, hilo_id: int, destino: EstadoDeHilo) -> models.HiloDeTrama:
    """Abre o cierra un hilo de trama.

    No hay maquina de estados que comprobar: la ontologia no dibuja ninguna para
    `Hilo de trama`, asi que se admite cualquiera de los dos valores en cualquier
    orden. Un hilo se puede reabrir, y eso es una decision del autor.
    """
    repository.obtener(base, models.HiloDeTrama, hilo_id)
    return repository.actualizar_estado_de_hilo(base, hilo_id, destino)


def hilos_abiertos(base: Conexion) -> list[models.HiloDeTrama]:
    """Los que `canon_huerfano` cuenta. Sin `estado` declarado cuenta abierto."""
    return [
        hilo
        for hilo in repository.listar(base, models.HiloDeTrama)
        if hilo.estado != EstadoDeHilo.CERRADO.value
    ]


def crear_lugar(base: Conexion, datos: schemas.NuevoLugar) -> models.Lugar:
    return repository.insertar_lugar(base, datos)


def crear_faccion(base: Conexion, datos: schemas.NuevaFaccion) -> models.Faccion:
    return repository.insertar_faccion(base, datos)


def crear_artefacto(base: Conexion, datos: schemas.NuevoArtefacto) -> models.Artefacto:
    return repository.insertar_artefacto(base, datos)


def crear_novum(base: Conexion, datos: schemas.NuevoNovum) -> models.Novum:
    """A-51: los limites se declaran al crear el novum.

    La otra mitad —al menos una regla del mundo— no se puede exigir aqui: la
    regla apunta al novum y necesita su id. La comprueba `verificar_novum`.
    """
    if not _declarado(datos.limites):
        raise NovumSinLimites(
            f"el novum '{datos.nombre}' no declara limites, y sin ellos RF-QUA-01 no "
            "tiene contra que medir la plausibilidad especulativa"
        )
    return repository.insertar_novum(base, datos)


def crear_regla_del_mundo(
    base: Conexion, datos: schemas.NuevaReglaDelMundo
) -> models.ReglaDelMundo:
    return repository.insertar_regla_del_mundo(base, datos)


def verificar_novum(base: Conexion, novum_id: int) -> models.Novum:
    """A-51, RF-NOVEL-06: todo `Novum` impone al menos una `Regla del mundo`."""
    novum = repository.obtener(base, models.Novum, novum_id)
    if repository.contar_reglas_del_novum(base, novum_id) == 0:
        raise NovumSinRegla(f"el novum '{novum.nombre}' no impone ninguna Regla del mundo")
    return novum


def crear_termino_canonico(
    base: Conexion, datos: schemas.NuevoTerminoCanonico
) -> models.TerminoCanonico:
    return repository.insertar_termino_canonico(base, datos)


def crear_tema(base: Conexion, datos: schemas.NuevoTema) -> models.Tema:
    return repository.insertar_tema(base, datos)


def crear_motivo(base: Conexion, datos: schemas.NuevoMotivo) -> models.Motivo:
    return repository.insertar_motivo(base, datos)


def crear_voz_narrativa(base: Conexion, datos: schemas.NuevaVozNarrativa) -> models.VozNarrativa:
    return repository.insertar_voz_narrativa(base, datos)


def crear_evento(base: Conexion, datos: schemas.NuevoEvento) -> models.Evento:
    return repository.insertar_evento(base, datos)


def crear_objetivo(base: Conexion, datos: schemas.NuevoObjetivo) -> models.Objetivo:
    return repository.insertar_objetivo(base, datos)


# --- Fabula y discurso ----------------------------------------------------


def narrar_evento_en_escena(base: Conexion, evento_id: int, escena_id: int) -> None:
    """RF-NOVEL-03. Se comprueba que existan los dos extremos antes de enlazar."""
    repository.obtener(base, models.Evento, evento_id)
    repository.obtener(base, models.Escena, escena_id)
    repository.enlazar_evento_con_escena(base, evento_id, escena_id)


def escenas_donde_se_narra(base: Conexion, evento_id: int) -> list[models.Escena]:
    repository.obtener(base, models.Evento, evento_id)
    return repository.escenas_donde_se_narra(base, evento_id)


def _declarado(valor: str | None) -> bool:
    return bool(valor and valor.strip())
