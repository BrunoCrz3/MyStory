"""H6 · la rodaja por HTTP — RI-01, RI-02, RI-03.

Lo que se entrega es la API, asi que el ciclo se recorre por ella: fijar el
plan, encargar la escena, anotar la version del autor, aceptarla y medir la
deriva. La generacion del borrador no entra aqui --necesita el proveedor-- y
tiene sus propias pruebas contra el servicio.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _crear(cliente: TestClient, ruta: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    respuesta = cliente.post(ruta, json=cuerpo)
    assert respuesta.status_code == 201, (ruta, respuesta.status_code, respuesta.text)
    return dict(respuesta.json())


def _obra_con_dos_escenas(cliente: TestClient) -> tuple[int, int]:
    obra = _crear(cliente, "/novel/obra", {"premisa": "un puente recuerda", "genero": "cf"})
    parte = _crear(
        cliente,
        "/novel/partes",
        {
            "obra_id": obra["id"],
            "orden": 1,
            "funcion_dramatica": "planteamiento",
            "punto_de_giro": "habla",
        },
    )
    capitulo = _crear(cliente, "/novel/capitulos", {"parte_id": parte["id"], "orden": 1})
    primera = _crear(cliente, "/novel/escenas", {"capitulo_id": capitulo["id"], "orden": 1})
    segunda = _crear(cliente, "/novel/escenas", {"capitulo_id": capitulo["id"], "orden": 2})
    return int(primera["id"]), int(segunda["id"])


def test_el_ciclo_de_una_escena_se_recorre_por_la_api(cliente: TestClient) -> None:
    escrita, por_escribir = _obra_con_dos_escenas(cliente)
    personaje = _crear(cliente, "/novel/personajes", {"nombre": "Ilia"})

    # El plan declara el futuro: la escena que aun no se escribe lleva su
    # restriccion de destino, y el hito la fija con su motivo.
    _crear(
        cliente,
        "/process/briefs",
        {
            "escena_id": por_escribir,
            "estado_de_entrada": "Ilia vuelve con la llave",
            "restricciones": [
                {
                    "tipo": "estado_final",
                    "enunciado": "termina viva",
                    "personaje_id": personaje["id"],
                    "valor": "vivo",
                }
            ],
        },
    )
    _crear(cliente, "/process/esquema", {"motivo": "plan inicial del primer acto"})
    esquema = cliente.get("/process/esquema").json()
    assert esquema["restricciones_futuras"] == 1
    assert esquema["coincide_con_el_hito"] is True

    # La escena en curso: el orquestador dice que toca, el autor escribe y firma.
    assert cliente.get(f"/process/escenas/{escrita}/paso").json()["paso"] == "redactor"
    for destino in ("en_borrador", "en_revision"):
        cliente.post(f"/novel/escenas/{escrita}/transicion", json={"destino": destino})

    _crear(
        cliente,
        "/process/briefs",
        {
            "escena_id": escrita,
            "estado_de_entrada": "Ilia llega al vado de noche",
            "restricciones": [
                {
                    "tipo": "posicion_de_personaje",
                    "enunciado": "termina al otro lado",
                    "personaje_id": personaje["id"],
                }
            ],
        },
    )
    _crear(
        cliente,
        f"/process/escenas/{escrita}/versiones",
        {"texto": "Ilia cruzo el vado y no miro atras."},
    )
    aceptacion = cliente.post(f"/process/escenas/{escrita}/aceptacion", json={"version": 1})
    assert aceptacion.status_code == 200, aceptacion.text
    # La escena se acepta igual. No entra en el banco porque no hubo generacion
    # --el texto lo escribio el autor de cero-- y sin contexto ensamblado el
    # ejemplo no tiene entrada. El motivo viene con la respuesta.
    assert aceptacion.json()["entro_en_el_banco"] is False
    assert "contexto ensamblado" in aceptacion.json()["motivo"]

    assert cliente.get(f"/process/escenas/{escrita}/paso").json()["paso"] == "extractor"

    # Y la deriva se mide una vez, contra el canon en t.
    medicion = cliente.post(f"/process/escenas/{escrita}/deriva")
    assert medicion.status_code == 201, medicion.text
    vector = medicion.json()
    assert set(vector["componentes"]) == {
        "invalidacion",
        "canon_huerfano",
        "inviabilidad_pago",
    }
    assert vector["fiable"] is None, "sin umbral de densidad no se inventa la fiabilidad"
    assert all(pieza["umbral"] is None for pieza in vector["componentes"].values())

    recalculado = cliente.get(f"/process/escenas/{escrita}/deriva/recalculada").json()
    for componente, pieza in vector["componentes"].items():
        assert recalculado[componente]["numerador"] == pieza["numerador"]
        assert recalculado[componente]["denominador"] == pieza["denominador"]

    assert [medida["escena_id"] for medida in cliente.get("/process/deriva").json()] == [escrita]


def test_un_brief_sin_destino_responde_422(cliente: TestClient) -> None:
    _, por_escribir = _obra_con_dos_escenas(cliente)
    respuesta = cliente.post(
        "/process/briefs",
        json={"escena_id": por_escribir, "estado_de_entrada": "llega", "restricciones": []},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "brief_sin_restriccion_de_destino"


def test_medir_la_deriva_de_una_escena_no_aceptada_responde_409(cliente: TestClient) -> None:
    escrita, _ = _obra_con_dos_escenas(cliente)
    respuesta = cliente.post(f"/process/escenas/{escrita}/deriva")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "deriva_solo_de_escena_aceptada"


def test_el_contrato_de_process_esta_en_el_openapi(cliente: TestClient) -> None:
    """RI-03: el cliente tipado del frontend se deriva de aqui, no se escribe."""
    contrato = cliente.get("/openapi.json").json()
    rutas = set(contrato["paths"])
    assert {
        "/process/esquema",
        "/process/briefs",
        "/process/escenas/{escena_id}/paso",
        "/process/escenas/{escena_id}/aceptacion",
        "/process/escenas/{escena_id}/deriva",
        "/process/deriva",
    } <= rutas
    assert "VectorDeDeriva" in contrato["components"]["schemas"]
