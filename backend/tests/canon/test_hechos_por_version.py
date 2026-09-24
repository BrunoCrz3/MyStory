"""`GET …/versiones/{version}/hechos` (RF-CANON-03): por vigencia, con `capitulos_usan` sacado
del puente `hecho_capitulo` y el filtro `?capitulo=` sobre quien **usa** el hecho."""

from __future__ import annotations

import uuid
from functools import partial
from typing import Any

from app.commons.llm import Peticion
from tests.conftest import Instancia, ValidarContrato
from tests.dobles.guiones import capitulo_aceptado_de, guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.extracciones import extraccion
from tests.process.test_orquestador import esperar

ELEMENTOS = [e["enunciado"] for e in brief_ejemplo()["elementos_personalizados"]]


def _extraer(peticion: Peticion, n: int, **kw: Any) -> dict[str, Any]:
    """Una extracción con un hecho propio del capítulo `n`: el doble escribe el mismo texto en
    todos, y un enunciado repetido lo descartaría el policy engine (A-24)."""
    salida = extraccion(capitulo_aceptado_de(peticion), elementos=ELEMENTOS, **kw)
    for hecho in salida["hechos_nuevos"]:
        hecho["enunciado"] = f"En el capítulo {n}: {hecho['fragmento_soporte']}"
    return salida


def publicada_con_uso(i: Instancia) -> str:
    """Una novela publicada donde el capítulo 7 usa el hecho que estableció el 2 (alias H2)."""
    guion_completo(i.modelo)
    guiones = [partial(_extraer, n=n) for n in range(1, 11)]
    guiones[6] = partial(_extraer, n=7, usados=["H2"])
    i.modelo.encolar("extractor", *guiones)
    novela = i.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = i.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(i.cliente, novela, gid, lambda g: g["es_terminal"])
    assert g["estado"] == "Publicada", g
    return str(novela)


def test_hechos_vigentes_de_la_version_con_quien_los_usa(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/hechos")
    validar_contra_contrato(r, "listarHechos")
    assert r.status_code == 200
    hechos = r.json()
    assert [h["capitulo_establece"] for h in hechos] == list(range(1, 11))
    assert all(h["estado"] == "adoptado" and h["origen"] == "extraccion" for h in hechos)
    assert all(h["fragmento_soporte"] for h in hechos)
    del_dos = hechos[1]
    assert 7 in del_dos["capitulos_usan"]


def test_filtrar_por_capitulo_devuelve_los_que_ese_capitulo_usa(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/hechos", params={"capitulo": 7})
    validar_contra_contrato(r, "listarHechos")
    usados = r.json()
    assert {h["capitulo_establece"] for h in usados} >= {2}
    assert all(7 in h["capitulos_usan"] for h in usados)
    assert not any(h["capitulo_establece"] == 3 for h in usados)


def test_version_o_novela_inexistente_es_404(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    for ruta, tipo in (
        (f"/novelas/{novela}/versiones/2/hechos", "version-no-encontrada"),
        (f"/novelas/{uuid.uuid4()}/versiones/1/hechos", "novela-no-encontrada"),
    ):
        r = instancia.cliente.get(ruta)
        validar_contra_contrato(r, "listarHechos")
        assert r.status_code == 404 and r.json()["type"] == f"/problemas/{tipo}"
    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/hechos", params={"capitulo": 0})
    assert r.status_code == 422
