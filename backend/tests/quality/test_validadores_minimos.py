"""Validadores mínimos del hook de capítulo: `longitud` y `nombres_exactos` (O-02, O-03)."""

from __future__ import annotations

from app.commons.config import cargar_config
from app.commons.texto import contar_palabras
from app.quality.service import EntradaHookCapitulo, hook_capitulo
from app.quality.validadores.basicos import nombres_exactos
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.fixtures.borradores import prosa

CONFIG = cargar_config(RAIZ_REPO / "config")
CAP = CONFIG.umbrales.capitulo


def _entrada(texto: str) -> EntradaHookCapitulo:
    return EntradaHookCapitulo(
        titulo="Título", texto=texto, nombres=["Marta", "Tomás", "el Alondra", "Cádiz"]
    )


def _resultado(texto: str, nombre: str) -> tuple[bool, str]:
    (r,) = [v for v in hook_capitulo(CONFIG, _entrada(texto)) if v.nombre == nombre]
    return r.pasa, r.detalle


def test_contar_palabras() -> None:
    assert contar_palabras("Hola, ¿qué tal? Bien: sin-guion no cuenta doble.") == 8
    assert contar_palabras(prosa(1234)) == 1234


def test_longitud_dentro_y_fuera_del_rango() -> None:
    assert _resultado(prosa(CAP.longitud_min_palabras), "longitud")[0]
    assert _resultado(prosa(CAP.longitud_max_palabras), "longitud")[0]
    pasa, detalle = _resultado(prosa(CAP.longitud_min_palabras - 1), "longitud")
    assert not pasa and str(CAP.longitud_min_palabras - 1) in detalle
    assert not _resultado(prosa(CAP.longitud_max_palabras + 1), "longitud")[0]


def test_nombre_bien_escrito_pasa() -> None:
    assert _resultado(prosa(1100), "nombres_exactos")[0]


def test_nombre_del_destinatario_mal_escrito_falla() -> None:
    texto = prosa(1100, extra="Aquella tarde, su hermana llamó a Martha desde el muelle.")
    pasa, detalle = _resultado(texto, "nombres_exactos")
    assert not pasa
    assert "Martha" in detalle and "Marta" in detalle


def test_mismo_nombre_con_otro_acento_falla() -> None:
    texto = prosa(1100, extra="Por la noche, Tomas cerró la puerta.")
    assert not _resultado(texto, "nombres_exactos")[0]


def test_una_palabra_comun_al_principio_de_frase_no_es_un_nombre() -> None:
    texto = prosa(1100, extra="Marca el rumbo, dijo el patrón. Mares así no se ven.")
    assert _resultado(texto, "nombres_exactos")[0]


def test_cada_validador_dice_si_cierra_el_paso() -> None:
    resultados = hook_capitulo(CONFIG, _entrada(prosa(1100)))
    assert {r.nombre for r in resultados} == {"longitud", "nombres_exactos"}
    assert all(r.cierra_el_paso for r in resultados)


def test_una_palabra_comun_dentro_de_un_nombre_compuesto_no_es_un_nombre_mal_escrito() -> None:
    # Humo real del P27: con «El perro de Marta», «La bocana» y «Varadero de Remedios» en la
    # obra, cada «perro», «bocana» o «varadero» de la prosa suspendía el capítulo.
    nombres = ["Marta", "El perro de Marta", "La bocana", "Bar El Ancla", "Varadero de Remedios"]
    texto = (
        "Marta subió al varadero con el perro. Desde la bocana se veía el ancla oxidada "
        "del bar, y el varadero olía a brea."
    )
    r = nombres_exactos(texto, nombres)
    assert r.pasa, r.detalle


def test_un_nombre_que_tambien_es_palabra_comun_puede_ir_en_minuscula() -> None:
    # Humo real del P27: el perro se llamaba «Boya», y cada «boya» del mar suspendía el
    # capítulo. Poner en minúscula un nombre propio no es un error que el modelo cometa;
    # lo que comete es otra grafía o un casi-nombre, y eso se sigue cazando.
    r = nombres_exactos("Boya ladró. Marta miró la boya roja que cabeceaba.", ["Marta", "Boya"])
    assert r.pasa, r.detalle


def test_las_grafias_distintas_y_los_casi_nombres_siguen_fallando() -> None:
    nombres = ["Marta", "Tomás", "Varadero de Remedios"]
    for texto, culpable in (
        ("Aquella tarde Tomas volvió al puerto.", "Tomas"),
        ("Aquella tarde fue al Baradero de Remedios con prisa.", "Baradero"),
    ):
        r = nombres_exactos(texto, nombres)
        assert not r.pasa and culpable in r.detalle, texto
