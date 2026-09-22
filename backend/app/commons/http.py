"""Handler central de errores (RI-04, A-36).

No hay tabla de traduccion: cada `ErrorDeDominio` trae su propio codigo HTTP.
Asi una excepcion nueva no puede salir como 500 por olvido de registrarla.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.commons.errores import ErrorDeDominio


def registrar_manejadores(aplicacion: FastAPI) -> None:
    async def manejar_error_de_dominio(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, ErrorDeDominio)
        return JSONResponse(
            status_code=error.http,
            content={"codigo": error.codigo, "mensaje": error.mensaje},
        )

    aplicacion.add_exception_handler(ErrorDeDominio, manejar_error_de_dominio)
