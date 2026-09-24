"""Handler central: toda respuesta de error sale como `application/problem+json`."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic.json_schema import models_json_schema

from app.commons.errores.excepciones import CATALOGO, ErrorDominio, ErrorInterno, PeticionInvalida
from app.commons.errores.problema import Problema

MEDIO = "application/problem+json"
_REF = "#/components/schemas/{model}"
_log = logging.getLogger("storymaker.errores")

_DESCRIPCIONES = {
    400: "El brief no es válido como encargo.",
    404: "El recurso no existe.",
    409: "La operación choca con el estado actual.",
    422: "La petición no cumple el schema.",
    500: "Fallo no previsto.",
}


def problemas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    """`responses=` de una ruta: cada código con cuerpo `Problema` en `problem+json`."""
    return {
        codigo: {
            "description": _DESCRIPCIONES.get(codigo, "Error."),
            "content": {MEDIO: {"schema": {"$ref": _REF.format(model="Problema")}}},
        }
        for codigo in codigos
    }


def _respuesta(error: ErrorDominio, request: Request) -> JSONResponse:
    extensiones = {k: v for k, v in error.extensiones.items() if v is not None}
    traza = getattr(request.state, "traza_langfuse_id", None)
    if traza and "traza_langfuse_id" not in extensiones:
        extensiones["traza_langfuse_id"] = traza
    problema = Problema.model_validate(
        {
            "type": f"/problemas/{error.slug}",
            "title": error.titulo,
            "status": error.status,
            "detail": error.detalle,
            "instance": request.url.path,
            **extensiones,
        }
    )
    return JSONResponse(problema.cuerpo(), status_code=error.status, media_type=MEDIO)


def _detalle_validacion(exc: RequestValidationError) -> str:
    partes = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
        partes.append(f"{'.'.join(loc) or 'cuerpo'}: {err.get('msg', 'inválido')}")
    return "; ".join(partes)


def registrar_errores(app: FastAPI) -> None:
    async def dominio(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, ErrorDominio)
        return _respuesta(exc, request)

    async def validacion(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        return _respuesta(PeticionInvalida(_detalle_validacion(exc)), request)

    async def interno(request: Request, exc: Exception) -> JSONResponse:
        # Se registra el tipo, no el mensaje: puede contener datos del brief.
        _log.error("error no previsto en %s: %s", request.url.path, type(exc).__name__)
        return _respuesta(ErrorInterno(), request)

    app.add_exception_handler(ErrorDominio, dominio)
    app.add_exception_handler(RequestValidationError, validacion)
    app.add_exception_handler(Exception, interno)
    _instalar_openapi(app)


def _instalar_openapi(app: FastAPI) -> None:
    """Quita el 422 genérico de FastAPI y publica `Problema` como componente."""

    def generar() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        doc = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            routes=app.routes,
            servers=app.servers,
            tags=app.openapi_tags,
        )
        for item in doc.get("paths", {}).values():
            for op in item.values():
                respuestas = op.get("responses", {})
                r422 = respuestas.get("422", {})
                esquema = r422.get("content", {}).get("application/json", {}).get("schema", {})
                if esquema.get("$ref", "").endswith("/HTTPValidationError"):
                    del respuestas["422"]
        componentes = doc.setdefault("components", {}).setdefault("schemas", {})
        for nombre in ("HTTPValidationError", "ValidationError"):
            componentes.pop(nombre, None)
        _, definiciones = models_json_schema([(Problema, "serialization")], ref_template=_REF)
        componentes.update(definiciones.get("$defs", {}))
        if not componentes:
            del doc["components"]["schemas"]
        app.openapi_schema = doc
        return doc

    app.openapi = generar  # type: ignore[method-assign]


__all__ = ["CATALOGO", "problemas", "registrar_errores"]
