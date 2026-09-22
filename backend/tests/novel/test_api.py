"""H2 · prueba 5 — RF-NOVEL-01, RF-NOVEL-02, RF-NOVEL-03, RF-NOVEL-05.

«Terminado cuando se puede crear una obra entera por API y consultarla», dice el
plan, asi que la prueba va por HTTP y no por el servicio: lo que se entrega es
la API.

Las trece entidades narrativas son las que enumera RF-NOVEL-02. `Evento` y
`Objetivo` no estan en esa lista porque tienen requisito propio —RF-NOVEL-03 y
RF-NOVEL-05—, y aqui se crean con las demas.
"""

from typing import Any

from fastapi.testclient import TestClient

TRECE_ENTIDADES_NARRATIVAS = [
    ("personajes", {"nombre": "Ilia", "deseo": "cruzar", "rol_narrativo": "protagonista"}),
    ("arcos", {"nombre": "de la desconfianza al pacto", "estado_inicial": "sola"}),
    ("hilos-de-trama", {"nombre": "el peaje", "tipo": "principal", "pregunta_dramatica": "?"}),
    ("lugares", {"nombre": "El vado", "geografia": "garganta fluvial"}),
    ("facciones", {"nombre": "Los barqueros", "objetivo": "cobrar el paso"}),
    ("artefactos", {"nombre": "La llave de piedra", "propiedades": "no se moja"}),
    ("temas", {"nombre": "la deuda", "enunciado": "todo paso se cobra"}),
    ("motivos", {"nombre": "el hierro mojado", "forma": "olor"}),
    ("terminos-canonicos", {"forma": "vado", "definicion": "paso que recuerda"}),
    (
        "voces-narrativas",
        {"persona": "tercera", "tiempo_verbal": "pasado", "focalizacion": "interna"},
    ),
]


def test_el_arbol_estructural_respeta_la_jerarquia_de_contencion(cliente: TestClient) -> None:
    """RF-NOVEL-01."""
    obra = _crear(
        cliente,
        "obra",
        {"titulo": "El vado", "premisa": "un puente recuerda", "genero": "ciencia ficcion"},
    )
    parte = _crear(
        cliente,
        "partes",
        {
            "obra_id": obra["id"],
            "orden": 1,
            "funcion_dramatica": "planteamiento",
            "punto_de_giro": "el puente habla",
        },
    )
    capitulo = _crear(cliente, "capitulos", {"parte_id": parte["id"], "orden": 1})
    escena = _crear(
        cliente, "escenas", {"capitulo_id": capitulo["id"], "orden": 1, "objetivo": "cruzar"}
    )

    assert cliente.get("/novel/obra").json()["premisa"] == "un puente recuerda"
    assert cliente.get(f"/novel/escenas/{escena['id']}").json()["capitulo_id"] == capitulo["id"]

    # Un capitulo colgado de una parte inexistente no entra: la jerarquia es del
    # esquema, no de la buena voluntad de quien llama.
    respuesta = cliente.post("/novel/capitulos", json={"parte_id": 9999, "orden": 2})
    assert respuesta.status_code == 409


def test_las_trece_entidades_narrativas_se_crean_y_se_consultan(cliente: TestClient) -> None:
    """RF-NOVEL-02, mas `Evento` y `Objetivo` (RF-NOVEL-03, RF-NOVEL-05)."""
    obra = _crear(cliente, "obra", {"titulo": "El vado", "premisa": "p", "genero": "cf"})

    creadas: dict[str, dict[str, Any]] = {}
    for ruta, cuerpo in TRECE_ENTIDADES_NARRATIVAS:
        if ruta == "voces-narrativas":
            cuerpo = {**cuerpo, "obra_id": obra["id"]}
        creadas[ruta] = _crear(cliente, ruta, cuerpo)

    # Las tres que dependen de otra entidad.
    creadas["voces"] = _crear(
        cliente, "voces", {"personaje_id": creadas["personajes"]["id"], "lexico": "seco"}
    )
    novum = _crear(
        cliente,
        "novums",
        {
            "nombre": "la memoria del rio",
            "mecanismo": "el agua guarda voces",
            "limites": "solo durante la crecida",
        },
    )
    creadas["novums"] = novum
    creadas["reglas-del-mundo"] = _crear(
        cliente,
        "reglas-del-mundo",
        {
            "novum_id": novum["id"],
            "enunciado": "el rio solo habla en crecida",
            "alcance": "toda la obra",
        },
    )

    assert len(creadas) == 13, "las trece de RF-NOVEL-02"

    for ruta in creadas:
        listado = cliente.get(f"/novel/{ruta}")
        assert listado.status_code == 200, ruta
        assert [fila["id"] for fila in listado.json()] == [creadas[ruta]["id"]], ruta


def test_un_evento_se_registra_y_se_narra_en_una_escena(cliente: TestClient) -> None:
    """RF-NOVEL-03."""
    escena = _una_escena(cliente)
    evento = _crear(
        cliente, "eventos", {"que_ocurre": "la caida del puente", "momento_en_la_fabula": "ano 12"}
    )

    enlace = cliente.post(f"/novel/eventos/{evento['id']}/escenas/{escena['id']}")
    assert enlace.status_code == 201

    narrado_en = cliente.get(f"/novel/eventos/{evento['id']}/escenas").json()
    assert [fila["id"] for fila in narrado_en] == [escena["id"]]


def test_un_objetivo_se_registra_contra_su_personaje(cliente: TestClient) -> None:
    """RF-NOVEL-05."""
    _crear(cliente, "obra", {"titulo": "t", "premisa": "p", "genero": "cf"})
    personaje = _crear(cliente, "personajes", {"nombre": "Ilia", "deseo": "cruzar"})
    objetivo = _crear(
        cliente,
        "objetivos",
        {
            "personaje_id": personaje["id"],
            "enunciado": "llegar al otro lado",
            "alcance": "de_arco",
            "tipo": "deseo",
        },
    )
    assert objetivo["personaje_id"] == personaje["id"]

    listado = cliente.get("/novel/objetivos").json()
    assert [fila["enunciado"] for fila in listado] == ["llegar al otro lado"]


def test_la_escena_transiciona_por_la_api(cliente: TestClient) -> None:
    escena = _una_escena(cliente)
    respuesta = cliente.post(
        f"/novel/escenas/{escena['id']}/transicion", json={"destino": "en_borrador"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "en_borrador"

    invalida = cliente.post(
        f"/novel/escenas/{escena['id']}/transicion", json={"destino": "aceptada"}
    )
    assert invalida.status_code == 409
    assert invalida.json()["codigo"] == "transicion_invalida"


def _crear(cliente: TestClient, ruta: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    respuesta = cliente.post(f"/novel/{ruta}", json=cuerpo)
    assert respuesta.status_code == 201, (ruta, respuesta.status_code, respuesta.text)
    return dict(respuesta.json())


def _una_escena(cliente: TestClient) -> dict[str, Any]:
    obra = _crear(cliente, "obra", {"titulo": "t", "premisa": "p", "genero": "cf"})
    parte = _crear(
        cliente,
        "partes",
        {
            "obra_id": obra["id"],
            "orden": 1,
            "funcion_dramatica": "planteamiento",
            "punto_de_giro": "g",
        },
    )
    capitulo = _crear(cliente, "capitulos", {"parte_id": parte["id"], "orden": 1})
    return _crear(cliente, "escenas", {"capitulo_id": capitulo["id"], "orden": 1})
