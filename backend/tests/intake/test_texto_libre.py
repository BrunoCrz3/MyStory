"""Texto libre como contenido no confiable (RF-INTAKE-03, RNF-09, D-20).

Lo que parece una instrucción al sistema se detecta por patrones deterministas, se devuelve
como `Fragmento sospechoso`, se registra al crear la novela y **se retira antes** de que el
texto llegue a ningún modelo. El resto viaja siempre dentro del delimitador de datos.
"""

from __future__ import annotations

import pytest

from app.intake.saneamiento import sanear
from app.process.planificar import planificar
from tests.conftest import Entorno, Instancia, ValidarContrato
from tests.fixtures.briefs import INYECCION, brief_adversarial
from tests.fixtures.esquemas import esquema_valido
from tests.fixtures.inyecciones import CORPUS_INYECCION

LIMPIO = "Ondina aprendió a navegar con su abuela en Cádiz."


def test_una_instruccion_se_marca_y_se_retira_del_texto() -> None:
    texto = brief_adversarial()["textos_libres"][0]["contenido"]
    resultado = sanear(texto)
    [fragmento] = resultado.fragmentos
    assert INYECCION.rstrip(".") in fragmento.fragmento
    assert fragmento.motivo
    assert "Ignora" not in resultado.limpio
    assert LIMPIO in resultado.limpio and "café con canela" in resultado.limpio


@pytest.mark.parametrize("inyeccion", CORPUS_INYECCION)
def test_todo_el_corpus_de_inyeccion_se_marca(inyeccion: str) -> None:
    # Cada parte en su línea: una inyección sin punto final se llevaría la frase siguiente,
    # que es el lado conservador, pero aquí se comprueba que lo limpio sobrevive.
    resultado = sanear("\n".join([LIMPIO, inyeccion, "Le gusta el mar."]))
    assert resultado.fragmentos, inyeccion
    assert LIMPIO in resultado.limpio and "Le gusta el mar." in resultado.limpio


@pytest.mark.parametrize(
    "texto",
    [
        "Su abuelo decía que el sistema de mareas de la ría es único.",
        "Trabaja como ingeniera y le encanta seguir las instrucciones de montaje de muebles.",
        "Una vez ignoró a todo el mundo y se fue a nadar a las seis de la mañana.",
    ],
)
def test_un_texto_normal_no_se_marca(texto: str) -> None:
    assert sanear(texto).fragmentos == []


def test_validar_devuelve_el_fragmento_y_los_hechos_sin_mandar_la_instruccion(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    instancia.modelo.encolar(
        "entrevistador",
        {
            "hechos": [
                {"enunciado": "Ondina aprendió a navegar con su abuela", "fragmento": LIMPIO},
                {"enunciado": "Ondina escribe novelas de terror", "fragmento": "novela de terror"},
            ]
        },
    )
    r = instancia.cliente.post("/briefs/validacion", json=brief_adversarial())
    validar_contra_contrato(r, "validarBrief")
    resultado = r.json()
    assert [f["fragmento"] for f in resultado["fragmentos_sospechosos"]] == [INYECCION]
    # Solo se propone lo que el texto limpio sostiene literalmente, y como texto libre.
    assert resultado["hechos_extraidos"] == [
        {"enunciado": "Ondina aprendió a navegar con su abuela", "origen": "texto-libre"}
    ]

    [peticion] = [p for p in instancia.modelo.peticiones if p.rol == "entrevistador"]
    mensaje = peticion.mensajes[0].contenido
    assert "Ignora" not in mensaje and "Ignora" not in peticion.system
    dentro = mensaje.split("<texto_libre_no_confiable>", 1)[1].split("</texto_libre_no_confiable>")[
        0
    ]
    assert LIMPIO in dentro
    assert LIMPIO not in mensaje.replace(dentro, "")
    assert "extraer_hechos_texto_libre" in instancia.trazas.nombres()


def test_sin_texto_libre_no_se_llama_al_modelo(instancia: Instancia) -> None:
    brief = brief_adversarial()
    brief["textos_libres"] = []
    instancia.cliente.post("/briefs/validacion", json=brief)
    assert instancia.modelo.llamadas["entrevistador"] == 0


@pytest.mark.anyio
async def test_crear_registra_el_fragmento_y_ningun_modelo_lo_recibe(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_adversarial())
    [fila] = entorno.consultar(
        "SELECT fragmento, motivo FROM fragmento_sospechoso WHERE novel_id = ?", novela
    )
    assert fila["fragmento"] == INYECCION and fila["motivo"]
    [texto] = entorno.consultar("SELECT contenido FROM texto_libre WHERE novel_id = ?", novela)
    assert "Ignora" not in texto["contenido"] and LIMPIO in texto["contenido"]
    [brief] = entorno.consultar("SELECT contenido FROM brief_novela WHERE novel_id = ?", novela)
    assert "Ignora" not in brief["contenido"]

    entorno.modelo.encolar("planificador", esquema_valido(brief_adversarial()))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    for peticion in entorno.modelo.peticiones:
        assert "Ignora" not in peticion.system
        assert all("Ignora" not in m.contenido for m in peticion.mensajes)
