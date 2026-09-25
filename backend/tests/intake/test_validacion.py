"""Validación del brief parcial (RF-INTAKE-01, RF-INTAKE-02, RNF-16, TO-037).

`validarBrief` acepta un `BriefNovelaParcial` y responde 200 con los `Dato faltante` y las
contradicciones; el sistema repregunta y nunca rellena. `crearNovela` exige el brief completo
(422) y rechaza el que se contradice con 400 `brief-invalido`.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.intake.validacion import OBLIGATORIOS, PREGUNTAS
from tests.conftest import Instancia, ValidarContrato
from tests.contrato.normalizar import cargar_contrato
from tests.fixtures.briefs import brief_ejemplo

TABLAS = ("obra", "brief_novela", "destinatario", "comprador", "audit_log")


@pytest.fixture
def cliente(instancia: Instancia) -> TestClient:
    """La app con los dobles: el brief de ejemplo lleva texto libre, y validarlo llama al
    `interviewer`, que en la suite nunca es el modelo real."""
    return instancia.cliente


def _validar(c: TestClient, cuerpo: dict[str, Any], validar: ValidarContrato) -> dict[str, Any]:
    r = c.post("/briefs/validacion", json=cuerpo)
    validar(r, "validarBrief")
    assert r.status_code == 200, r.text
    resultado: dict[str, Any] = r.json()
    return resultado


def _faltantes(resultado: dict[str, Any]) -> list[str]:
    return [d["campo"] for d in resultado["datos_faltantes"]]


def _requeridos(schema: dict[str, Any], raiz: dict[str, Any], prefijo: str = "") -> set[str]:
    """Las hojas obligatorias de un schema del contrato, con `[]` para los elementos."""
    if "$ref" in schema:
        nombre = schema["$ref"].rsplit("/", 1)[1]
        return _requeridos(raiz["components"]["schemas"][nombre], raiz, prefijo)
    rutas: set[str] = set()
    for campo, sub in schema.get("properties", {}).items():
        ruta = f"{prefijo}{campo}"
        destino = sub
        if "$ref" in sub:
            destino = raiz["components"]["schemas"][sub["$ref"].rsplit("/", 1)[1]]
        if destino.get("type") == "array" and "items" in destino:
            items = destino["items"]
            if "$ref" in items:
                rutas |= _requeridos(items, raiz, f"{ruta}[].")
            continue
        es_objeto = destino.get("type") == "object"
        if es_objeto and campo in schema.get("required", []):
            rutas |= _requeridos(destino, raiz, f"{ruta}.")
        elif campo in schema.get("required", []):
            rutas.add(ruta)
    return rutas


def test_los_obligatorios_son_los_required_del_contrato() -> None:
    contrato = cargar_contrato()
    brief = contrato["components"]["schemas"]["BriefNovela"]
    assert set(OBLIGATORIOS) == _requeridos(brief, contrato)
    assert set(PREGUNTAS) == set(OBLIGATORIOS)
    assert all(p.strip().endswith("?") for p in PREGUNTAS.values())


def test_un_brief_vacio_devuelve_un_dato_faltante_por_obligatorio(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    resultado = _validar(cliente, {}, validar_contra_contrato)
    assert resultado["valido"] is False
    raiz = [o for o in OBLIGATORIOS if "[]" not in o]
    assert sorted(_faltantes(resultado)) == sorted(raiz)
    assert all(d["pregunta_reintento"] for d in resultado["datos_faltantes"])


def test_sin_nombre_del_destinatario_es_dato_faltante_y_no_se_rellena(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo()
    del brief["destinatario"]["nombre"]
    resultado = _validar(cliente, brief, validar_contra_contrato)
    assert resultado["valido"] is False
    assert _faltantes(resultado) == ["destinatario.nombre"]
    assert resultado["datos_faltantes"][0]["pregunta_reintento"] == PREGUNTAS["destinatario.nombre"]


@pytest.mark.parametrize("vacio", ["", "   ", "\n\t"])
def test_un_campo_vacio_o_en_blanco_es_dato_faltante(
    vacio: str, cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo(tono=vacio)
    resultado = _validar(cliente, brief, validar_contra_contrato)
    assert _faltantes(resultado) == ["tono"]


def test_un_elemento_de_lista_incompleto_es_dato_faltante(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo()
    brief["elementos_personalizados"].append({"obligatorio": True})
    resultado = _validar(cliente, brief, validar_contra_contrato)
    assert _faltantes(resultado) == ["elementos_personalizados[2].enunciado"]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"destinatario": {"edad": "siete"}},
        {"ocasion": {"tipo": "bautizo"}},
        {"destinatario": {"edad": 300}},
    ],
)
def test_un_valor_mal_formado_sigue_siendo_422(
    cuerpo: dict[str, Any], cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    r = cliente.post("/briefs/validacion", json=cuerpo)
    validar_contra_contrato(r, "validarBrief")
    assert r.status_code == 422
    assert r.json()["type"] == "/problemas/peticion-invalida"


def test_edad_de_nino_con_tono_adulto_se_contradice_aunque_falten_campos(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    cuerpo = {"destinatario": {"edad": 7}, "tono": "adulto irónico"}
    resultado = _validar(cliente, cuerpo, validar_contra_contrato)
    [contradiccion] = resultado["contradicciones"]
    assert contradiccion["tipo"] == "edad-vs-tono"
    assert contradiccion["campos"] == ["destinatario.edad", "tono"]
    assert contradiccion["explicacion"]
    assert "genero" in _faltantes(resultado)


def test_edad_de_nino_con_genero_adulto_y_fecha_que_no_cuadra(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo(genero="terror gore")
    brief["destinatario"].update(edad=9, fecha_nacimiento="1992-01-01")
    tipos = {
        c["tipo"] for c in _validar(cliente, brief, validar_contra_contrato)["contradicciones"]
    }
    assert tipos == {"edad-vs-genero", "fecha-vs-edad"}


def test_un_identificador_con_forma_de_correo_no_pasa(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo()
    brief["comprador"]["identificador"] = "persona@ejemplo.invalid"
    resultado = _validar(cliente, brief, validar_contra_contrato)
    assert resultado["valido"] is False
    [contradiccion] = resultado["contradicciones"]
    assert contradiccion["campos"] == ["comprador.identificador"]
    assert contradiccion["tipo"] == "otra"


def test_el_brief_del_contrato_es_valido(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    resultado = _validar(cliente, brief_ejemplo(), validar_contra_contrato)
    assert resultado == {
        "valido": True,
        "datos_faltantes": [],
        "contradicciones": [],
        "fragmentos_sospechosos": [],
        "hechos_extraidos": [],
    }


def test_validar_no_crea_nada(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    recursos = cliente.app.state.recursos  # type: ignore[attr-defined]

    def contar() -> dict[str, int]:
        return {
            t: recursos.db.ejecutar_sync(
                lambda con, t=t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            )
            for t in TABLAS
        }

    antes = contar()
    _validar(cliente, {"destinatario": {"edad": 7}, "tono": "adulto"}, validar_contra_contrato)
    _validar(cliente, brief_ejemplo(), validar_contra_contrato)
    assert contar() == antes


def test_crear_novela_sin_nombre_es_422_y_con_contradiccion_es_400(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    incompleto = brief_ejemplo()
    del incompleto["destinatario"]["nombre"]
    r = cliente.post("/novelas", json=incompleto)
    validar_contra_contrato(r, "crearNovela")
    assert r.status_code == 422

    contradictorio = brief_ejemplo(tono="adulto irónico")
    contradictorio["destinatario"]["edad"] = 7
    contradictorio["destinatario"]["fecha_nacimiento"] = None
    r = cliente.post("/novelas", json=contradictorio)
    validar_contra_contrato(r, "crearNovela")
    assert r.status_code == 400
    problema = r.json()
    assert problema["type"] == "/problemas/brief-invalido"
    assert [c["tipo"] for c in problema["contradicciones"]] == ["edad-vs-tono"]
    assert cliente.get("/novelas").json()["total"] == 0


def test_crear_novela_con_un_campo_en_blanco_es_400_con_el_dato_faltante(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    r = cliente.post("/novelas", json=brief_ejemplo(genero="   "))
    validar_contra_contrato(r, "crearNovela")
    assert r.status_code == 400
    assert [d["campo"] for d in r.json()["datos_faltantes"]] == ["genero"]
