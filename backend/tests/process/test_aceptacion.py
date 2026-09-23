"""H6 · pruebas 1 y 9 — A-46, P-19, RF-PROC-07, RF-PROC-09.

La primera es la que no se puede relajar nunca: **solo el autor humano
transiciona una escena a `aceptada`**. Es el ultimo cortafuegos de la
resistencia a inyeccion, y por eso el guardarrail vive en la puerta que escribe
el estado y no en el camino que alguien se acordo de pasar.

La segunda es su consecuencia: en `training_samples` solo entra texto aceptado
**y editado** por el autor. Entrenar sobre lo que el sistema escribio y nadie
toco amplifica la regresion a la media que la Capa 4 senala como el fallo
caracteristico de un modelo de lenguaje.

El punto ciego declarado se asume y pesa: los guardarrailes garantizan que la
transicion la dispare el autor, no que la haya leido antes de aprobarla.
"""

from __future__ import annotations

import asyncio

import pytest

from app.commons import errores
from app.commons.db.conexion import Conexion
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.novel import service as novel
from app.novel.models import EstadoDeEscena, ModoDeAceptacion
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.orquestador import CerrojoDeGeneracion
from tests.process import fabrica


def _escena_en_revision(base: Conexion, mundo: fabrica.MundoDelCiclo) -> int:
    """Una escena con borrador real, llevada hasta la puerta de la aceptacion."""
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    umbrales = fabrica.umbrales()
    asyncio.run(
        proceso.generar_borrador(
            base,
            umbrales,
            fabrica.ModeloDeLaboratorio(),
            PoolEnVuelo(umbrales.en_vuelo.total),
            CerrojoDeGeneracion(),
            brief.escena_id,
            process_schemas.PeticionDeBorrador(),
        )
    )
    novel.transicionar_escena(base, brief.escena_id, EstadoDeEscena.EN_REVISION)
    return brief.escena_id


def test_solo_el_autor_transiciona_una_escena_a_aceptada(base: Conexion) -> None:
    """P-19, RF-PROC-07. El defecto es `AUTOMATICA` para que nadie acepte por
    olvido: una regla que se cumple sola cuando alguien se acuerda no es una
    regla."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    escena_id = _escena_en_revision(base, mundo)

    with pytest.raises(errores.AceptacionSoloDelAutor):
        novel.transicionar_escena(base, escena_id, EstadoDeEscena.ACEPTADA)
    assert novel.obtener_escena(base, escena_id).estado is EstadoDeEscena.EN_REVISION

    novel.transicionar_escena(
        base,
        escena_id,
        EstadoDeEscena.ACEPTADA,
        modo_de_aceptacion=ModoDeAceptacion.HUMANA,
    )
    assert novel.obtener_escena(base, escena_id).estado is EstadoDeEscena.ACEPTADA


def test_la_api_generica_de_transicion_no_acepta(cliente: object) -> None:
    """La puerta de la aceptacion es una sola y esta en `process/`.

    Que `novel/` responda 403 y no 200 es lo que impide que un cliente cualquiera
    --o un agente con acceso HTTP-- salte el paso que la ontologia reserva al
    autor.
    """
    from fastapi.testclient import TestClient

    assert isinstance(cliente, TestClient)

    def crear(ruta: str, cuerpo: dict[str, object]) -> dict[str, object]:
        respuesta = cliente.post(f"/novel/{ruta}", json=cuerpo)
        assert respuesta.status_code == 201, (ruta, respuesta.text)
        return dict(respuesta.json())

    obra = crear("obra", {"premisa": "un puente recuerda", "genero": "cf"})
    parte = crear(
        "partes",
        {
            "obra_id": obra["id"],
            "orden": 1,
            "funcion_dramatica": "planteamiento",
            "punto_de_giro": "habla",
        },
    )
    capitulo = crear("capitulos", {"parte_id": parte["id"], "orden": 1})
    escena = crear("escenas", {"capitulo_id": capitulo["id"], "orden": 1})

    for destino in ("en_borrador", "en_revision"):
        assert (
            cliente.post(
                f"/novel/escenas/{escena['id']}/transicion", json={"destino": destino}
            ).status_code
            == 200
        )

    negada = cliente.post(f"/novel/escenas/{escena['id']}/transicion", json={"destino": "aceptada"})
    assert negada.status_code == 403
    assert negada.json()["codigo"] == "aceptacion_solo_del_autor"


def test_solo_entra_en_training_samples_texto_aceptado_y_editado(base: Conexion) -> None:
    """A-46, RF-PROC-09.

    No se pregunta al autor si edito: se mira quien dejo el texto que acepta.
    Una casilla se marca sola; una fila de `version` con origen `autor` no.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    escena_id = _escena_en_revision(base, mundo)

    sin_editar = proceso.aceptar_escena(
        base, escena_id, process_schemas.PeticionDeAceptacion(version=1)
    )
    assert sin_editar.entro_en_el_banco is False
    assert proceso.muestras_recogidas(base) == 0


def test_la_version_editada_por_el_autor_si_entra_en_el_banco(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    escena_id = _escena_en_revision(base, mundo)
    proceso.anotar_version_del_autor(base, escena_id, "Ilia cruzo, y el agua se callo.")

    aceptada = proceso.aceptar_escena(
        base, escena_id, process_schemas.PeticionDeAceptacion(version=2)
    )
    assert aceptada.entro_en_el_banco is True
    assert proceso.muestras_recogidas(base) == 1


def test_el_banco_es_append_only_y_no_se_lee_en_v1(base: Conexion) -> None:
    """RF-PROC-09. No hay ninguna funcion que devuelva una muestra.

    El recuento existe para poder verificar la regla, no para alimentar a nadie:
    el escalon 2 de la escalera de adaptacion se recoge desde el primer dia y se
    usa cuando haya volumen y metrica.
    """
    from app.process import repository

    lectores = [
        nombre
        for nombre in dir(repository)
        if "muestra" in nombre and nombre not in {"insertar_muestra", "contar_muestras"}
    ]
    assert lectores == []


def test_aceptar_una_version_que_no_existe_falla(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    escena_id = _escena_en_revision(base, mundo)

    with pytest.raises(errores.RecursoNoEncontrado):
        proceso.aceptar_escena(base, escena_id, process_schemas.PeticionDeAceptacion(version=99))
