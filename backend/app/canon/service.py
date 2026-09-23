"""Reglas del canon. `canon/` es lo unico que escribe el canon, y solo al
consolidar una escena aceptada.

Tres invariantes viven aqui y no en el esquema, porque el esquema no los puede
expresar:

- **Un borrador rechazado no deja rastro** (A-27). Si lo dejara, cada iteracion
  fallida contaminaria el estado del mundo y la escena siguiente se generaria
  contra un canon que nadie escribio.
- **Las dos maquinas de estado.** Un `CHECK` cierra la lista de valores; de que
  estado se viene, no lo sabe.
- **El anclaje textual** (RF-CANON-11): un hecho cuyos terminos no estan en la
  escena que lo establece no se guarda. Es lo unico que ata el canon a la prosa.
"""

from __future__ import annotations

import unicodedata
from datetime import UTC, datetime

from app.canon import models, repository, schemas
from app.canon.models import EstadoDePromesa, EstatusDeHecho, TipoDeHecho
from app.commons.db.conexion import Conexion
from app.commons.errores import (
    CanonSoloAlAceptar,
    HechoSinAnclaje,
    PromesaPagadaAntesDeAbrirse,
    PromesaSinEscenaDePago,
    TransicionInvalida,
)
from app.novel import service as novel
from app.novel.models import EstadoDeEscena

LONGITUD_MINIMA_DE_TERMINO = 4


# --- Consolidacion: el unico punto que modifica el canon ------------------


def consolidar_escena(
    base: Conexion, datos: schemas.Consolidacion
) -> schemas.ResultadoDeConsolidacion:
    """RF-CANON-07, RF-CANON-08, RF-CANON-11."""
    escena = novel.obtener_escena(base, datos.escena_id)
    if escena.estado is not EstadoDeEscena.ACEPTADA:
        raise CanonSoloAlAceptar(
            f"la escena {datos.escena_id} esta en '{escena.estado.value}': el canon solo "
            "cambia al consolidar una escena aceptada"
        )

    existente = repository.obtener_snapshot(base, datos.escena_id)
    if existente is not None and existente.version == datos.version:
        # Idempotente por escena + version: reintentar no consolida dos veces.
        return _resultado_ya_guardado(base, datos.escena_id, existente)

    for hecho in datos.hechos:
        _exigir_anclaje(base, hecho, datos.texto)

    posicion = repository.posicion_de(base, datos.escena_id)
    return repository.escribir_consolidacion(base, datos, posicion)


def _resultado_ya_guardado(
    base: Conexion, escena_id: int, snapshot: models.SnapshotDeMundo
) -> schemas.ResultadoDeConsolidacion:
    hechos = repository.hechos_establecidos_en(base, escena_id)
    promesas = [
        repository.obtener_promesa(base, promesa.id)
        for promesa in repository.promesas_abiertas_en(
            base, repository.posicion_de(base, escena_id)
        )
        if repository.escena_con_rol(base, promesa.id, "abre") == escena_id
    ]
    epistemicos = [
        epistemico
        for hecho in hechos
        for epistemico in _epistemicos_del_hecho(base, hecho.id)
        if epistemico.escena_id == escena_id
    ]
    return schemas.ResultadoDeConsolidacion(
        snapshot=snapshot, hechos=hechos, promesas=promesas, epistemicos=epistemicos
    )


def _epistemicos_del_hecho(base: Conexion, hecho_id: int) -> list[models.EstadoEpistemico]:
    hecho = repository.obtener_hecho(base, hecho_id)
    posicion = repository.posicion_de(base, hecho.escena_id)
    return [
        epistemico
        for personaje in _personajes_con_conocimiento(base, hecho_id)
        for epistemico in repository.epistemicos_de(base, personaje, posicion)
        if epistemico.hecho_id == hecho_id
    ]


def _personajes_con_conocimiento(base: Conexion, hecho_id: int) -> list[int]:
    return [
        int(fila["personaje_id"])
        for fila in base.execute(
            "SELECT personaje_id FROM estado_epistemico WHERE hecho_id = ? ORDER BY id",
            (hecho_id,),
        )
    ]


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )
    return sin_tildes


def _exigir_anclaje(
    base: Conexion, hecho: schemas.NuevoHechoCanonico, texto_de_la_escena: str
) -> None:
    """RF-CANON-11, A-48.

    Se exigen dos cosas localizables en el texto: el nombre de cada entidad que
    el hecho referencia, y los terminos canonicos que el hecho nombra. Si el
    hecho no referencia nada —un `descriptivo` suelto—, basta con que alguna de
    sus palabras de contenido aparezca; si no aparece ninguna, el hecho no sale
    de esta escena y no hay razon para colgarlo de ella.

    El punto ciego esta declarado y se asume: esto comprueba presencia de
    terminos, no lo que el hecho afirma. Uno que invierte el sentido con las
    mismas palabras pasa.
    """
    aguja = _normalizar(texto_de_la_escena)

    referencias = {
        columna: valor
        for columna in (
            "sujeto_personaje_id",
            "objeto_personaje_id",
            "lugar_id",
            "artefacto_id",
        )
        if (valor := getattr(hecho, columna)) is not None
    }
    exigidos = repository.nombres_de_entidades(base, referencias)
    exigidos += [
        forma
        for forma in repository.formas_canonicas(base)
        if _normalizar(forma) in _normalizar(hecho.texto)
    ]

    if exigidos:
        ausentes = [termino for termino in exigidos if _normalizar(termino) not in aguja]
        if ausentes:
            raise HechoSinAnclaje(
                f"el hecho '{hecho.texto}' nombra {ausentes}, que no aparece en el texto "
                "de la escena que lo establece"
            )
        return

    palabras = [
        palabra for palabra in hecho.texto.split() if len(palabra) >= LONGITUD_MINIMA_DE_TERMINO
    ]
    if palabras and not any(_normalizar(palabra) in aguja for palabra in palabras):
        raise HechoSinAnclaje(
            f"ninguno de los terminos de '{hecho.texto}' —{palabras}— aparece en el texto "
            "de la escena que lo establece"
        )


def version_consolidada(base: Conexion, escena_id: int) -> int | None:
    snapshot = repository.obtener_snapshot(base, escena_id)
    return None if snapshot is None else snapshot.version


def inventario_del_canon(base: Conexion) -> dict[str, int]:
    return repository.inventario(base)


def posicion_de(base: Conexion, escena_id: int) -> int:
    """Posicion de la escena en el orden del discurso.

    La expone `canon/` porque es quien posee la vista `escena_ordenada`, y
    porque `t` —una posicion en el discurso, no una fecha del mundo ficcional—
    es un concepto del canon. Otras features la leen por aqui, nunca por el
    repositorio (RD-04).
    """
    return repository.posicion_de(base, escena_id)


def estado_de_escena(base: Conexion, escena_id: int) -> EstadoDeEscena:
    return novel.obtener_escena(base, escena_id).estado


# --- Ciclos de vida -------------------------------------------------------


def obtener_hecho(base: Conexion, hecho_id: int) -> models.HechoCanonico:
    return repository.obtener_hecho(base, hecho_id)


def obtener_promesa(base: Conexion, promesa_id: int) -> models.PromesaNarrativa:
    return repository.obtener_promesa(base, promesa_id)


def hechos_establecidos_en(base: Conexion, escena_id: int) -> list[models.HechoCanonico]:
    return repository.hechos_establecidos_en(base, escena_id)


def hechos_vigentes_en(base: Conexion, escena_id: int) -> list[models.HechoCanonico]:
    return repository.hechos_vigentes_en(base, repository.posicion_de(base, escena_id))


def transicionar_hecho(
    base: Conexion, hecho_id: int, destino: EstatusDeHecho
) -> models.HechoCanonico:
    """A-30, A-33, RF-CANON-02."""
    hecho = repository.obtener_hecho(base, hecho_id)
    if destino not in models.TRANSICIONES_DEL_HECHO[hecho.estatus]:
        raise TransicionInvalida(
            f"el hecho {hecho_id} esta en '{hecho.estatus.value}' y el diagrama no dibuja "
            f"una transicion a '{destino.value}'"
        )
    return repository.actualizar_estatus_de_hecho(base, hecho_id, destino)


def transicionar_promesa(
    base: Conexion,
    promesa_id: int,
    destino: EstadoDePromesa,
    escena_de_pago_id: int | None = None,
) -> models.PromesaNarrativa:
    """A-31, A-33, P-45, RF-CANON-05, RF-CANON-13."""
    promesa = repository.obtener_promesa(base, promesa_id)
    if destino not in models.TRANSICIONES_DE_LA_PROMESA[promesa.estado]:
        raise TransicionInvalida(
            f"la promesa {promesa_id} esta en '{promesa.estado.value}' y el diagrama no "
            f"dibuja una transicion a '{destino.value}'"
        )

    if destino in {EstadoDePromesa.PAGADA, EstadoDePromesa.SUBVERTIDA}:
        if escena_de_pago_id is None:
            raise PromesaSinEscenaDePago(
                f"pagar la promesa {promesa_id} exige decir en que escena se paga: sin eso "
                "no se puede comprobar que el setup es anterior"
            )
        apertura = repository.escena_con_rol(base, promesa_id, "abre")
        if apertura is None:
            raise PromesaPagadaAntesDeAbrirse(
                f"la promesa {promesa_id} no tiene escena de apertura registrada"
            )
        if repository.posicion_de(base, escena_de_pago_id) <= repository.posicion_de(
            base, apertura
        ):
            raise PromesaPagadaAntesDeAbrirse(
                f"la escena {escena_de_pago_id} no es posterior a la apertura {apertura}"
            )

    return repository.actualizar_estado_de_promesa(base, promesa_id, destino, escena_de_pago_id)


# --- `consultar-canon`: snapshot en t, epistemica y promesas abiertas -----


def snapshot_en(base: Conexion, escena_id: int) -> schemas.SnapshotDerivado:
    """RF-CANON-03. Derivado de los hechos vigentes, nunca texto bruto."""
    posicion = repository.posicion_de(base, escena_id)
    vigentes = repository.hechos_vigentes_en(base, posicion)
    guardado = repository.obtener_snapshot(base, escena_id)

    vivos: dict[int, str] = {}
    ubicaciones: dict[int, int] = {}
    posesiones: dict[int, int] = {}
    relaciones: list[schemas.Relacion] = []

    for hecho in vigentes:
        if hecho.tipo is TipoDeHecho.ESTADO_VITAL and hecho.sujeto_personaje_id is not None:
            vivos[hecho.sujeto_personaje_id] = hecho.valor or "vivo"
        elif (
            hecho.tipo is TipoDeHecho.UBICACION
            and hecho.sujeto_personaje_id is not None
            and hecho.lugar_id is not None
        ):
            ubicaciones[hecho.sujeto_personaje_id] = hecho.lugar_id
        elif (
            hecho.tipo is TipoDeHecho.POSESION
            and hecho.artefacto_id is not None
            and hecho.sujeto_personaje_id is not None
        ):
            posesiones[hecho.artefacto_id] = hecho.sujeto_personaje_id
        elif (
            hecho.tipo is TipoDeHecho.RELACION
            and hecho.sujeto_personaje_id is not None
            and hecho.objeto_personaje_id is not None
        ):
            relaciones.append(
                schemas.Relacion(
                    sujeto_personaje_id=hecho.sujeto_personaje_id,
                    objeto_personaje_id=hecho.objeto_personaje_id,
                    valor=hecho.valor,
                )
            )

    return schemas.SnapshotDerivado(
        escena_id=escena_id,
        fecha_ficcional=None if guardado is None else guardado.fecha_ficcional,
        personajes_vivos=sorted(
            personaje for personaje, estado in vivos.items() if estado != "muerto"
        ),
        ubicaciones=ubicaciones,
        posesiones=posesiones,
        relaciones=relaciones,
    )


def diferencias_entre_snapshots(
    antes: schemas.SnapshotDerivado, despues: schemas.SnapshotDerivado
) -> list[schemas.Cambio]:
    """P-39, RF-CANON-12. Incluye posesiones y relaciones."""
    cambios: list[schemas.Cambio] = []

    for personaje in set(antes.personajes_vivos) ^ set(despues.personajes_vivos):
        cambios.append(schemas.Cambio(tipo=TipoDeHecho.ESTADO_VITAL, sujeto_personaje_id=personaje))

    for personaje, lugar in despues.ubicaciones.items():
        if antes.ubicaciones.get(personaje) != lugar:
            cambios.append(
                schemas.Cambio(tipo=TipoDeHecho.UBICACION, sujeto_personaje_id=personaje)
            )

    for artefacto, poseedor in despues.posesiones.items():
        if antes.posesiones.get(artefacto) != poseedor:
            cambios.append(
                schemas.Cambio(
                    tipo=TipoDeHecho.POSESION,
                    sujeto_personaje_id=poseedor,
                    artefacto_id=artefacto,
                )
            )

    previas = {(r.sujeto_personaje_id, r.objeto_personaje_id, r.valor) for r in antes.relaciones}
    for relacion in despues.relaciones:
        clave = (relacion.sujeto_personaje_id, relacion.objeto_personaje_id, relacion.valor)
        if clave not in previas:
            cambios.append(
                schemas.Cambio(
                    tipo=TipoDeHecho.RELACION,
                    sujeto_personaje_id=relacion.sujeto_personaje_id,
                )
            )
    return cambios


def que_sabe(
    base: Conexion, personaje_id: int, hasta_escena_id: int
) -> list[models.EstadoEpistemico]:
    """RF-CANON-04 y pregunta de competencia 1."""
    return repository.epistemicos_de(
        base, personaje_id, repository.posicion_de(base, hasta_escena_id)
    )


def promesas_abiertas_en(base: Conexion, escena_id: int) -> list[models.PromesaNarrativa]:
    return repository.promesas_abiertas_en(base, repository.posicion_de(base, escena_id))


def escena_de_apertura(base: Conexion, promesa_id: int) -> int | None:
    return repository.escena_con_rol(base, promesa_id, "abre")


def escena_de_pago(base: Conexion, promesa_id: int) -> int | None:
    return repository.escena_con_rol(base, promesa_id, "paga")


# --- Contradicciones, estancamiento y retcon ------------------------------


def detectar_contradicciones(base: Conexion) -> list[models.Contradiccion]:
    """RF-CANON-06. La mitad enumerable, que es la que el esquema permite ver.

    Hoy detecta una sola familia: un personaje que actua despues de un hecho
    vigente que lo declara no vivo (P-37). Es poco, y es lo que `Hecho
    canonico.tipo` sin enumerar del todo deja detectar; lo que no hace es
    fingir que cubre las cuatro dimensiones.
    """
    ultima = repository.ultima_escena_consolidada(base)
    if ultima is None:
        return []
    _, posicion = ultima

    vigentes = repository.hechos_vigentes_en(base, posicion)
    muertos = {
        hecho.sujeto_personaje_id: hecho
        for hecho in vigentes
        if hecho.tipo is TipoDeHecho.ESTADO_VITAL and hecho.valor == "muerto"
    }
    for hecho in vigentes:
        muerte = muertos.get(hecho.sujeto_personaje_id)
        if muerte is None or hecho.id == muerte.id:
            continue
        if hecho.tipo is TipoDeHecho.DESCRIPTIVO:
            continue
        if repository.posicion_de(base, hecho.escena_id) < repository.posicion_de(
            base, muerte.escena_id
        ):
            continue
        repository.registrar_contradiccion(
            base, muerte.id, hecho.id, "personaje_no_vivo_que_actua", "alta"
        )
    return repository.contradicciones(base)


def estancados(
    base: Conexion,
    umbral_arco: int | None = None,
    umbral_hilo: int | None = None,
    umbral_promesa: int | None = None,
) -> schemas.InformeDeEstancamiento:
    """RF-CANON-14, P-44. Preguntas de competencia 6, 7 y 8.

    Los tres umbrales son `[historico]` y siguen en `null`. La consulta no falla
    por eso: mide, dice que no hay umbral declarado y deja la comparacion para
    cuando lo haya. Medir no es cerrar el paso (RF-QUA-05).
    """
    ultima = repository.ultima_escena_consolidada(base)
    actual, posicion = ultima if ultima is not None else (None, 0)
    declarados = None not in (umbral_arco, umbral_hilo, umbral_promesa)

    def lineas(
        filas: list[dict[str, object]], umbral: int | None
    ) -> list[schemas.LineaDeEstancamiento]:
        resultado = []
        for fila in filas:
            sin_avanzar = posicion - int(str(fila["ultima"]))
            resultado.append(
                schemas.LineaDeEstancamiento(
                    id=int(str(fila["id"])),
                    nombre=str(fila["nombre"]),
                    escenas_sin_avanzar=max(sin_avanzar, 0),
                    supera_umbral=None if umbral is None else sin_avanzar > umbral,
                )
            )
        return resultado

    return schemas.InformeDeEstancamiento(
        escena_actual_id=actual,
        umbrales_declarados=declarados,
        arcos=lineas(repository.avances(base, "arco_escena", "arco_id", "arco"), umbral_arco),
        hilos=lineas(repository.avances(base, "escena_hilo", "hilo_id", "hilo"), umbral_hilo),
        promesas=lineas(repository.promesas_pendientes_con_apertura(base), umbral_promesa),
    )


def simular_retcon(base: Conexion, hecho_id: int) -> schemas.SimulacionDeRetcon:
    """RF-CANON-09, A-34. v1 responde que escenas invalidaria; no las marca.

    No escribe nada: ni `retcon`, ni `obsoleta`, ni una fila de `retcon_escena`.
    Aplicarlo es el bucle largo, y queda fuera del corte de v1 (spec §1.3).
    """
    hecho = repository.obtener_hecho(base, hecho_id)
    entidades = {
        columna: valor
        for columna in (
            "sujeto_personaje_id",
            "objeto_personaje_id",
            "lugar_id",
            "artefacto_id",
        )
        if (valor := getattr(hecho, columna)) is not None
    }
    desde = repository.posicion_de(base, hecho.escena_id)
    escenas = repository.escenas_que_tocan(base, entidades, desde)
    if hecho.escena_id not in escenas:
        escenas = [hecho.escena_id, *escenas]
    return schemas.SimulacionDeRetcon(hecho_id=hecho_id, escenas_invalidadas=escenas)


def ahora() -> str:
    return datetime.now(UTC).isoformat()
