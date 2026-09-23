"""H7 · la rodaja por HTTP — RI-01, RI-02, RI-04.

La puerta de la adopcion importa por HTTP y no solo por el servicio: si alguna
vez alguien automatiza al `extractor` contra la API, esta es la superficie que
ve. Lo que tiene que encontrar es una bandeja de propuestas y una firma.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _crear(cliente: TestClient, ruta: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    respuesta = cliente.post(ruta, json=cuerpo)
    assert respuesta.status_code == 201, (ruta, respuesta.status_code, respuesta.text)
    return dict(respuesta.json())


def _escena_aceptada(cliente: TestClient) -> tuple[int, int, str]:
    """Una escena consolidada por el camino de siempre, y su prosa."""
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
    escena = _crear(cliente, "/novel/escenas", {"capitulo_id": capitulo["id"], "orden": 1})
    ilia = _crear(cliente, "/novel/personajes", {"nombre": "Ilia"})

    prosa = "Cruzo el agua de noche. Ilia vio a Nerio esperando en el talud."
    _crear(
        cliente,
        "/process/briefs",
        {
            "escena_id": escena["id"],
            "estado_de_entrada": "Ilia llega al vado",
            "restricciones": [
                {"tipo": "estado_final", "enunciado": "termina viva", "personaje_id": ilia["id"]}
            ],
        },
    )
    _crear(cliente, f"/process/escenas/{escena['id']}/versiones", {"texto": prosa})
    for destino in ("en_borrador", "en_revision"):
        cliente.post(f"/novel/escenas/{escena['id']}/transicion", json={"destino": destino})
    assert (
        cliente.post(f"/process/escenas/{escena['id']}/aceptacion", json={"version": 1}).status_code
        == 200
    )
    consolidada = cliente.post(
        "/canon/consolidaciones",
        json={
            "escena_id": escena["id"],
            "version": 1,
            "texto": prosa,
            "hechos": [
                {
                    "texto": "Ilia cruza el agua",
                    "tipo": "descriptivo",
                    "sujeto_personaje_id": ilia["id"],
                }
            ],
        },
    )
    assert consolidada.status_code in {200, 201}, consolidada.text
    return int(escena["id"]), int(ilia["id"]), prosa


def test_la_extraccion_deja_la_bandeja_del_autor_por_la_api(cliente: TestClient) -> None:
    escena_id, _, prosa = _escena_aceptada(cliente)

    resultado = _crear(
        cliente, f"/findings/escenas/{escena_id}/extraccion", {"version": 1, "texto": prosa}
    )
    assert [h["estado"] for h in resultado["hallazgos"]] == ["propuesto"]
    assert resultado["hallazgos"][0]["texto"] == "Nerio"

    bandeja = cliente.get("/findings/hallazgos").json()
    assert [h["id"] for h in bandeja] == [resultado["hallazgos"][0]["id"]]
    assert cliente.get("/findings/hallazgos/adoptados").json() == []


def test_extraer_de_una_escena_sin_consolidar_responde_409(cliente: TestClient) -> None:
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
    escena = _crear(cliente, "/novel/escenas", {"capitulo_id": capitulo["id"], "orden": 1})

    respuesta = cliente.post(
        f"/findings/escenas/{escena['id']}/extraccion", json={"version": 1, "texto": "nada"}
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "extraccion_sin_consolidar"


def test_la_adopcion_pasa_por_la_puerta_del_autor(cliente: TestClient) -> None:
    """El endpoint **es** el autor, y adoptar exige decir en que se convierte."""
    escena_id, ilia, prosa = _escena_aceptada(cliente)
    resultado = _crear(
        cliente, f"/findings/escenas/{escena_id}/extraccion", {"version": 1, "texto": prosa}
    )
    hallazgo = resultado["hallazgos"][0]["id"]

    sin_destino = cliente.post(
        f"/findings/hallazgos/{hallazgo}/decision", json={"destino": "adoptado"}
    )
    assert sin_destino.status_code == 422
    assert sin_destino.json()["codigo"] == "adopcion_sin_destino"

    adoptado = cliente.post(
        f"/findings/hallazgos/{hallazgo}/decision",
        json={"destino": "adoptado", "personaje_id": ilia},
    )
    assert adoptado.status_code == 200
    assert adoptado.json()["estado"] == "adoptado"
    assert adoptado.json()["decidido_por"] == "autor_humano"

    fuera_del_diagrama = cliente.post(
        f"/findings/hallazgos/{hallazgo}/decision", json={"destino": "propuesto"}
    )
    assert fuera_del_diagrama.status_code == 409
    assert fuera_del_diagrama.json()["codigo"] == "transicion_invalida"
