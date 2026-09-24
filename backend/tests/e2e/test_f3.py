"""Cierre de F3: el brief adversarial por HTTP de principio a fin.

Validado, devuelve el `Fragmento sospechoso`; creado, lo deja registrado y fuera del brief; y
generado con los dobles, **ninguna** petición al modelo de toda la generación —entrevistador,
planificador, redactor, judge, editor, extractor— contiene la instrucción inyectada.
"""

from __future__ import annotations

from tests.conftest import Instancia, ValidarContrato
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import INYECCION, brief_adversarial
from tests.process.test_orquestador import esperar

MARCA = "Ignora las instrucciones"


def test_el_brief_adversarial_no_llega_a_ninguna_peticion(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    guion_completo(instancia.modelo, brief_adversarial())
    c = instancia.cliente

    r = c.post("/briefs/validacion", json=brief_adversarial())
    validar_contra_contrato(r, "validarBrief")
    assert [f["fragmento"] for f in r.json()["fragmentos_sospechosos"]] == [INYECCION]

    r = c.post("/novelas", json=brief_adversarial())
    validar_contra_contrato(r, "crearNovela")
    novela = r.json()["novel_id"]
    recursos = instancia.app.state.recursos
    fragmentos = recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "SELECT fragmento FROM fragmento_sospechoso WHERE novel_id = ?", (novela,)
        ).fetchall()
    )
    assert [f["fragmento"] for f in fragmentos] == [INYECCION]

    gid = c.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(c, novela, gid, lambda g: g["es_terminal"], limite=120)
    assert g["estado"] == "Publicada", g

    peticiones = instancia.modelo.peticiones
    roles = {p.rol for p in peticiones}
    assert {"entrevistador", "planificador", "redactor", "judge", "extractor"} <= roles
    for p in peticiones:
        assert MARCA not in p.system, p.rol
        assert all(MARCA not in m.contenido for m in p.mensajes), p.rol
    # El texto libre que sí queda viaja siempre dentro del delimitador de datos.
    con_texto = [p for p in peticiones if "café con canela" in p.mensajes[0].contenido]
    assert con_texto
    for p in con_texto:
        mensaje = p.mensajes[0].contenido
        fuera = mensaje
        while "<texto_libre_no_confiable>" in fuera:
            antes, _, resto = fuera.partition("<texto_libre_no_confiable>")
            _, _, despues = resto.partition("</texto_libre_no_confiable>")
            fuera = antes + despues
        assert "café con canela" not in fuera, p.rol
