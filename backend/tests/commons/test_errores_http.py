"""H1 · prueba 3 — A-36, RI-04.

El punto ciego de A-36 es que una excepcion nueva sin entrada en el mapa sale
como 500. Por eso el handler no lleva mapa: cada error de dominio declara su
propio codigo HTTP y el handler lo lee.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.commons import errores
from app.commons.http import registrar_manejadores


def _aplicacion_que_lanza(error: Exception) -> TestClient:
    aplicacion = FastAPI()
    registrar_manejadores(aplicacion)

    @aplicacion.get("/lanza")
    def lanza() -> None:
        raise error

    return TestClient(aplicacion, raise_server_exceptions=False)


def test_un_error_de_dominio_sale_por_el_handler_central_con_su_http() -> None:
    cliente = _aplicacion_que_lanza(
        errores.RecursoNoEncontrado("no existe la escena 7", codigo="escena_no_encontrada")
    )
    respuesta = cliente.get("/lanza")

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "escena_no_encontrada"
    assert cuerpo["mensaje"] == "no existe la escena 7"


def test_cada_error_de_dominio_lleva_su_propio_codigo_http() -> None:
    esperados = {
        errores.RecursoNoEncontrado: 404,
        errores.ConflictoDeEstado: 409,
        errores.PresupuestoExcedido: 422,
        errores.TransicionInvalida: 409,
    }
    for clase, http in esperados.items():
        cliente = _aplicacion_que_lanza(clase("mensaje"))
        assert cliente.get("/lanza").status_code == http, clase.__name__


def test_ninguna_feature_lanza_httpexception() -> None:
    """RI-04: un HTTPException en un servicio ata la logica al transporte."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2] / "app"
    culpables = [
        str(fichero.relative_to(raiz))
        for fichero in raiz.rglob("*.py")
        if "HTTPException" in fichero.read_text(encoding="utf-8")
        and fichero.name not in {"http.py"}
    ]
    assert culpables == []
