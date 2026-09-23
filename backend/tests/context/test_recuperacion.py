"""H4 · pruebas 7, 9 y 10 — A-10, A-42, RF-CTX-07, RF-CTX-09, RF-CTX-10.

Nunca similitud sola. Devuelve fragmentos de tono parecido y estado
irrelevante: prosa que suena bien y contradice el canon, que es el fallo mas
caro de este sistema porque pasa la lectura y no pasa la verificacion.
"""

from __future__ import annotations

import pytest

from app.commons import errores
from app.context import schemas
from app.context import service as contexto
from app.context.models import NivelDeCompresion
from tests.context import fabrica


def test_la_recuperacion_filtra_por_entidades_antes_de_ordenar_por_similitud(
    base_indexada,
) -> None:
    """A-10, RF-CTX-07.

    El punto ciego declarado se asume: comprueba el orden de las dos etapas, no
    la calidad del filtro. Un brief con pocas entidades declaradas deja pasar
    casi todo y la similitud vuelve a mandar.
    """
    base, creado, escenas, _umbrales, dimension = base_indexada

    # El mas parecido a la consulta, pero de otro personaje: no debe salir.
    ajeno = fabrica.indexar(
        base,
        escenas[0],
        "Baro cuenta monedas en la orilla norte.",
        [schemas.Referencia(tipo="personaje", id=creado.baro)],
        semilla=0.4,
        dimension=dimension,
    )
    # Menos parecido, pero de la entidad del brief: debe salir.
    propio = fabrica.indexar(
        base,
        escenas[1],
        "Ilia mira la puerta cerrada del vado.",
        [schemas.Referencia(tipo="personaje", id=creado.ilia)],
        semilla=0.9,
        dimension=dimension,
    )

    recuperados = contexto.recuperar_fragmentos(
        base,
        entidades=[schemas.Referencia(tipo="personaje", id=creado.ilia)],
        consulta=fabrica.vector(0.4, dimension),
        maximo=10,
    )

    identificadores = [fragmento.id for fragmento in recuperados]
    assert propio in identificadores
    assert ajeno not in identificadores, "la similitud no puede saltarse el filtro"


def test_sin_entidades_declaradas_la_recuperacion_no_devuelve_nada(base_indexada) -> None:
    """La otra mitad de «nunca similitud sola»: sin filtro no hay recuperacion."""
    base, _creado, _escenas, _umbrales, dimension = base_indexada

    assert (
        contexto.recuperar_fragmentos(
            base, entidades=[], consulta=fabrica.vector(0.4, dimension), maximo=10
        )
        == []
    )


def test_la_recuperacion_ordena_por_similitud_dentro_del_filtro(base_indexada) -> None:
    base, creado, escenas, _umbrales, dimension = base_indexada
    de_ilia = schemas.Referencia(tipo="personaje", id=creado.ilia)

    lejano = fabrica.indexar(base, escenas[0], "lejano", [de_ilia], 0.95, dimension)
    cercano = fabrica.indexar(base, escenas[1], "cercano", [de_ilia], 0.41, dimension)

    recuperados = contexto.recuperar_fragmentos(
        base, entidades=[de_ilia], consulta=fabrica.vector(0.4, dimension), maximo=10
    )
    orden = [fragmento.id for fragmento in recuperados]
    assert orden.index(cercano) < orden.index(lejano)


def test_la_jerarquia_de_compresion_expone_los_cuatro_niveles(base_indexada) -> None:
    """RF-CTX-09. Es de lo que tira la degradacion de la capa Local."""
    base, creado, escenas, _umbrales, dimension = base_indexada

    assert [nivel.value for nivel in NivelDeCompresion] == [
        "resumen_de_acto",
        "resumen_de_capitulo",
        "resumen_de_escena",
        "escena_literal",
    ]

    for nivel in NivelDeCompresion:
        fabrica.indexar(
            base,
            escenas[0],
            f"contenido en nivel {nivel.value}",
            [schemas.Referencia(tipo="personaje", id=creado.ilia)],
            semilla=0.3,
            dimension=dimension,
            nivel=nivel,
        )

    disponibles = contexto.niveles_disponibles(base, escenas[0])
    assert set(disponibles) == set(NivelDeCompresion)

    # Comprimir es bajar de resolucion, no recortar: el literal se sustituye por
    # el resumen de la misma escena, no se tira.
    literal = contexto.fragmentos_de(base, escenas[0], NivelDeCompresion.ESCENA_LITERAL)
    resumido = contexto.bajar_de_resolucion(base, literal)
    assert resumido, "hay resumen al que bajar"
    assert all(pieza.nivel is NivelDeCompresion.RESUMEN_DE_ESCENA for pieza in resumido)


def test_un_cambio_de_modelo_de_embeddings_falla_al_arrancar_y_pide_reindexar(
    base_indexada,
) -> None:
    """A-42, RF-CTX-10.

    Vectores de modelos distintos no son comparables. Mezclarlos no produce un
    error: produce una recuperacion que devuelve lo que no toca y nadie sabe por
    que.

    El punto ciego declarado se asume: compara lo declarado con lo almacenado.
    Un proveedor que cambie los pesos bajo la misma version pasa la comprobacion
    y devuelve otros vecinos.
    """
    base, _creado, _escenas, umbrales, _dimension = base_indexada

    contexto.verificar_indice(base, umbrales)

    otro = umbrales.model_copy(
        update={
            "embeddings": umbrales.embeddings.model_copy(update={"version": "BAAI/bge-m3@otra"})
        }
    )
    with pytest.raises(errores.IndiceDesactualizado) as detalle:
        contexto.verificar_indice(base, otro)
    mensaje = str(detalle.value).lower()
    assert "reindexar" in mensaje

    otro_modelo = umbrales.model_copy(
        update={
            "embeddings": umbrales.embeddings.model_copy(update={"modelo": "multilingual-e5-large"})
        }
    )
    with pytest.raises(errores.IndiceDesactualizado):
        contexto.verificar_indice(base, otro_modelo)


def test_cada_fila_de_embedding_guarda_con_que_se_genero(base_indexada) -> None:
    base, _creado, _escenas, umbrales, _dimension = base_indexada

    filas = base.execute("SELECT embedding_model, embedding_version FROM fragmento").fetchall()
    assert filas
    for fila in filas:
        assert fila["embedding_model"] == umbrales.embeddings.modelo
        assert fila["embedding_version"] == umbrales.embeddings.version


def test_un_vector_de_otra_dimension_no_entra(base_indexada) -> None:
    base, creado, escenas, _umbrales, dimension = base_indexada

    with pytest.raises(errores.DimensionDeEmbeddingInvalida):
        contexto.indexar_fragmento(
            base,
            _umbrales,
            schemas.NuevoFragmento(
                escena_id=escenas[0],
                texto="corto",
                nivel=NivelDeCompresion.ESCENA_LITERAL,
                entidades=[schemas.Referencia(tipo="personaje", id=creado.ilia)],
                embedding=fabrica.vector(0.5, dimension - 1),
            ),
        )


def test_la_dimension_de_vec0_es_la_declarada_en_thresholds(base_indexada) -> None:
    """La cifra esta en el DDL y en el fichero porque el DDL no puede leerlo.

    Que no se separen no puede quedar en la buena intencion: una tabla `vec0`
    creada con otra dimension acepta vectores de otro tamano y la recuperacion
    deja de significar nada.
    """
    base, _creado, _escenas, umbrales, _dimension = base_indexada
    from app.context import repository

    assert repository.dimension_declarada_en_vec0(base) == umbrales.embeddings.dimension
