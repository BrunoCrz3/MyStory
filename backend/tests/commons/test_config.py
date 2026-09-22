"""H1 · prueba 4 — A-41, RF-QUA-05, RNF-14.

Mientras un umbral este en null, el arranque falla en voz alta al pedirlo *para
cerrar el paso*. Medir y registrar sin suspender no es pedirlo: esa es la fase
de medicion que declara `config/thresholds.yaml`, y es por lo que v1 arranca.
"""

from pathlib import Path

import pytest

from app.commons import config, errores


def _escribir_umbrales(destino: Path, cerrar_el_paso: bool, consistencia: float | None) -> Path:
    plantilla = config.ruta_por_defecto_de_umbrales().read_text(encoding="utf-8")
    texto = plantilla.replace(
        "cerrar_el_paso: false", f"cerrar_el_paso: {'true' if cerrar_el_paso else 'false'}"
    )
    if consistencia is not None:
        texto = texto.replace("consistencia_factica: null", f"consistencia_factica: {consistencia}")
    fichero = destino / "thresholds.yaml"
    fichero.write_text(texto, encoding="utf-8")
    return fichero


def test_el_arranque_falla_si_falta_un_umbral_que_cierra_el_paso(tmp_path: Path) -> None:
    fichero = _escribir_umbrales(tmp_path, cerrar_el_paso=True, consistencia=None)
    umbrales = config.cargar_umbrales(fichero)

    with pytest.raises(errores.UmbralAusente) as detalle:
        config.verificar_arranque(umbrales)
    assert "consistencia_factica" in str(detalle.value)


def test_el_arranque_no_falla_por_un_umbral_null_en_fase_de_medicion(tmp_path: Path) -> None:
    fichero = _escribir_umbrales(tmp_path, cerrar_el_paso=False, consistencia=None)
    umbrales = config.cargar_umbrales(fichero)

    config.verificar_arranque(umbrales)

    assert umbrales.medicion.cerrar_el_paso is False


def test_pedir_un_umbral_nulo_para_cerrar_el_paso_falla_aunque_se_este_midiendo(
    tmp_path: Path,
) -> None:
    fichero = _escribir_umbrales(tmp_path, cerrar_el_paso=False, consistencia=None)
    umbrales = config.cargar_umbrales(fichero)

    with pytest.raises(errores.UmbralAusente):
        umbrales.para_cerrar_el_paso("calidad.consistencia_factica")


def test_el_arranque_falla_si_no_existe_el_fichero_de_umbrales(tmp_path: Path) -> None:
    with pytest.raises(errores.ConfiguracionInvalida):
        config.cargar_umbrales(tmp_path / "no_existe.yaml")


def test_los_umbrales_del_repositorio_se_leen_enteros() -> None:
    umbrales = config.cargar_umbrales()

    assert umbrales.contexto.total > 0
    assert set(umbrales.contexto.degradacion) <= set(umbrales.contexto.capas.model_dump())
    assert umbrales.medicion.cerrar_el_paso is False
