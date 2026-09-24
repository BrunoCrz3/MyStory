"""Registro de validadores: nombre de score, tipo, punto de ejecución y filas que sostiene.

Es el índice de `docs/verification.md` § Índice de validadores con nombre, hecho código; una
prueba lo compara con el fichero para que no se desincronicen (plan § 4.3). Vive en código y
no en una tabla porque es un catálogo sin novela: una tabla sin `novel_id` rompería RD-01
(A-62). Incluye también los validadores que aún no corren: declarar el punto de ejecución de
todos es lo que permite comprobar que cada uno corre donde dice cuando llegue su paso.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.quality.models import ResultadoValidador


class Validador(BaseModel):
    model_config = ConfigDict(frozen=True)

    nombre: str
    etiqueta: str
    tipo: str
    punto: str
    filas: tuple[str, ...]


class ValidadorNoRegistrado(RuntimeError):
    """Un resultado con un nombre, tipo o punto que el registro no declara."""


def _v(nombre: str, etiqueta: str, tipo: str, punto: str, *filas: str) -> Validador:
    return Validador(nombre=nombre, etiqueta=etiqueta, tipo=tipo, punto=punto, filas=filas)


_P, _S, _PS = "programático", "semántico", "programático + semántico"
_HP, _HC, _ED, _GT = "hook de policy", "hook de capítulo", "rol editor", "gate de publicación"

REGISTRO: tuple[Validador, ...] = (
    _v("schema_valido", "Conformidad de schema", _P, _HP, "O-01"),
    _v(
        "palabras_prohibidas",
        "Ausencia de palabras prohibidas",
        _P,
        _HP,
        "O-05",
        "O-06",
        "O-07",
        "O-08",
    ),
    _v("nombres_exactos", "Ortografía exacta de nombres", _P, _HC, "O-02"),
    _v("longitud", "Longitud", _P, _HC, "O-03"),
    _v(
        "consistencia_factica",
        "Consistencia fáctica",
        _PS,
        _HC,
        "O-26",
        "O-27",
        "O-28",
        "O-31",
        "O-32",
    ),
    _v(
        "calidad_prosa",
        "Calidad de prosa",
        _P,
        _HC,
        "O-46",
        "O-47",
        "O-48",
        "O-49",
        "O-50",
        "O-53",
        "O-54",
        "O-55",
        "O-56",
    ),
    _v("integridad_pov", "Integridad de POV y voz narrativa", _P, _HC, "O-51", "O-52"),
    _v("cumplimiento_brief", "Cumplimiento del brief de capítulo", _P, _HC, "O-30", "O-42"),
    _v(
        "personalizacion_natural",
        "Integración natural de la personalización",
        _S,
        _ED,
        "O-17",
        "O-22",
    ),
    _v(
        "reconocibilidad",
        "Reconocibilidad del destinatario",
        "semántico + revisión humana",
        "rol editor · revisión",
        "O-12",
        "O-19",
    ),
    _v("adecuacion_tono", "Adecuación del tono", _S, _ED, "O-23", "O-24"),
    _v("coherencia_personajes", "Coherencia de personajes", _S, _ED, "O-33", "O-39"),
    _v("ritmo", "Ritmo entre capítulos", _S, _ED, "O-37", "O-38", "O-44", "O-45"),
    _v("lean_cronologia", "Consistencia temporal", "formal-Lean", _GT, "O-13"),
    _v("lean_ubicacion", "Consistencia espacial", "formal-Lean", _GT, "O-14"),
    _v("lean_edad", "Coherencia de edad", "formal-Lean", _GT, "O-15"),
    _v("elementos_obligatorios", "Cumplimiento de elementos obligatorios", _P, _GT, "O-04", "O-18"),
    _v("cierre_arco", "Cierre del arco", _PS, _GT, "O-34", "O-35", "O-36", "O-40", "O-41", "O-43"),
    _v("render_visual", "Render visual", _P, _GT, "O-09", "O-10", "O-59", "O-60", "A-106"),
    _v("paridad_pdf_web", "Paridad PDF ↔ web", _P, "export", "O-16"),
    _v("invencion_destinatario", "Invención sobre el destinatario", _PS, _ED, "O-20"),
    _v("temas_excluidos", "Temas excluidos", _S, _ED, "O-21"),
    _v("reglas_mundo", "Cumplimiento de reglas del mundo", _P, _HC, "O-29"),
    _v("legibilidad", "Legibilidad", _P, _ED, "O-25"),
    _v("estructura_edicion", "Estructura de la edición", _P, _GT, "O-57", "O-58"),
    _v(
        "regeneracion_fiel", "Fidelidad de la regeneración", _P, _GT, "O-61", "O-62", "O-63", "O-64"
    ),
)

_POR_NOMBRE = {v.nombre: v for v in REGISTRO}


def validador(nombre: str) -> Validador:
    try:
        return _POR_NOMBRE[nombre]
    except KeyError:
        raise ValidadorNoRegistrado(f"el validador {nombre!r} no está en el registro") from None


def comprobar(resultado: ResultadoValidador) -> None:
    """Falla en voz alta si el resultado no corre donde el registro dice (RF-OBS-03)."""
    v = validador(resultado.nombre)
    if (resultado.tipo, resultado.punto) != (v.tipo, v.punto):
        raise ValidadorNoRegistrado(
            f"{resultado.nombre}: tipo y punto {resultado.tipo!r}/{resultado.punto!r}; "
            f"el registro dice {v.tipo!r}/{v.punto!r}"
        )
