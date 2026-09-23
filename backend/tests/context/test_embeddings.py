"""El modelo de embeddings local, de verdad.

Esta prueba descarga y carga el artefacto declarado en `config/thresholds.yaml`.
Son gigas: no corre con el resto de la suite. Se pide a proposito con
`uv run pytest -m modelo`, y es la unica que cierra la afirmacion de que el
modelo cabe en la maquina del autor — el riesgo que el plan de H4 declara.
"""

from __future__ import annotations

import pytest

from app.context.embeddings import EmbebedorLocal
from tests.context import fabrica


@pytest.mark.modelo
def test_el_modelo_local_produce_vectores_de_la_dimension_declarada() -> None:
    umbrales = fabrica.umbrales()
    embebedor = EmbebedorLocal(umbrales)

    vectores = embebedor.vectorizar(
        ["Ilia cruzo el vado al anochecer.", "Baro cuenta monedas en la orilla."]
    )

    assert len(vectores) == 2
    for vector in vectores:
        assert len(vector) == umbrales.embeddings.dimension


@pytest.mark.modelo
def test_el_modelo_local_distingue_textos_parecidos_de_los_lejanos() -> None:
    """Un embebedor que devuelve vectores de la dimension correcta pero sin
    senal pasaria la prueba anterior y no serviria para recuperar nada."""
    embebedor = EmbebedorLocal(fabrica.umbrales())

    cerca, lejos, consulta = embebedor.vectorizar(
        [
            "Ilia cruzo el vado al anochecer.",
            "El contrato fiscal se firmo en el tercer trimestre.",
            "Ilia paso el rio de noche.",
        ]
    )
    assert _coseno(consulta, cerca) > _coseno(consulta, lejos)


def _coseno(uno: list[float], otro: list[float]) -> float:
    return sum(a * b for a, b in zip(uno, otro, strict=True))
