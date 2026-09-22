"""H2 · prueba 6 — A-51, RF-NOVEL-06.

Sin novum con limites declarados y sin regla que lo acote, RF-QUA-01 no tiene
contra que medir la plausibilidad especulativa; sin punto de giro, un acto no es
un acto. Se comprueba en el servicio y no en el esquema porque «al menos una
regla» es una condicion sobre otra tabla, y un `CHECK` no la ve.

El punto ciego declarado de A-51 sigue abierto y se asume: exige que la
declaracion exista, no que sea la que hacia falta. Un limite trivial cumple
igual y deja a P-07 sin nada contra lo que medir.
"""

import pytest
from fastapi.testclient import TestClient

from app.commons import errores
from app.commons.db.conexion import Conexion
from app.novel import schemas, service


def test_un_novum_sin_regla_con_limites_no_valida(base: Conexion) -> None:
    sin_limites = schemas.NuevoNovum(
        nombre="la memoria del rio", mecanismo="el agua guarda voces", limites=""
    )
    with pytest.raises(errores.NovumSinLimites):
        service.crear_novum(base, sin_limites)

    novum = service.crear_novum(
        base,
        schemas.NuevoNovum(
            nombre="la memoria del rio",
            mecanismo="el agua guarda voces",
            limites="solo durante la crecida",
        ),
    )
    with pytest.raises(errores.NovumSinRegla):
        service.verificar_novum(base, novum.id)

    service.crear_regla_del_mundo(
        base,
        schemas.NuevaReglaDelMundo(
            novum_id=novum.id, enunciado="el rio solo habla en crecida", alcance="toda la obra"
        ),
    )
    service.verificar_novum(base, novum.id)


def test_un_acto_sin_punto_de_giro_no_valida(base: Conexion) -> None:
    with pytest.raises(errores.ActoIncompleto):
        service.crear_parte(
            base,
            schemas.NuevaParte(
                obra_id=_una_obra(base),
                orden=1,
                funcion_dramatica="planteamiento",
                punto_de_giro=None,
            ),
        )

    with pytest.raises(errores.ActoIncompleto):
        service.crear_parte(
            base,
            schemas.NuevaParte(
                obra_id=_una_obra(base),
                orden=2,
                funcion_dramatica="   ",
                punto_de_giro="el puente habla",
            ),
        )


def test_la_api_devuelve_el_error_de_dominio_del_novum(cliente: TestClient) -> None:
    respuesta = cliente.post("/novel/novums", json={"nombre": "n", "mecanismo": "m", "limites": ""})
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "novum_sin_limites"


def _una_obra(base: Conexion) -> int:
    existente = base.execute("SELECT id FROM obra").fetchone()
    if existente:
        return int(existente["id"])
    return service.crear_obra(
        base, schemas.NuevaObra(titulo="El vado", premisa="p", genero="cf")
    ).id
