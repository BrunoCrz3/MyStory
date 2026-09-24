"""Casetes: grabar y reproducir el tráfico HTTP del cliente de producción (plan § 4.1, capa 2).

El grabador envuelve el transporte real de `httpx2` y escribe cada interacción en un JSON de
`tests/casetes/`. **Solo conserva las cabeceras de una lista cerrada**: la autenticación no
llega nunca al fichero, ni por olvido ni por una cabecera nueva del SDK. El reproductor es un
`httpx2.MockTransport` que devuelve esas respuestas en orden, para que el cliente de
producción se pruebe con su serialización real y sin red.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx2

# Lista blanca, no negra: lo que no está aquí no se graba.
CABECERAS_GRABABLES = frozenset({"content-type", "anthropic-version", "request-id"})


def _cabeceras(cabeceras: httpx2.Headers) -> dict[str, str]:
    return {k.lower(): v for k, v in cabeceras.items() if k.lower() in CABECERAS_GRABABLES}


def _cuerpo(contenido: bytes) -> Any:
    if not contenido:
        return None
    texto = contenido.decode("utf-8", errors="replace")
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


def _bytes(cuerpo: Any) -> bytes:
    if cuerpo is None:
        return b""
    if isinstance(cuerpo, str):
        return cuerpo.encode("utf-8")
    return json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")


class TransporteGrabador(httpx2.AsyncBaseTransport):
    """Deja pasar cada petición al transporte interno y graba el par petición-respuesta."""

    def __init__(self, interno: httpx2.AsyncBaseTransport, destino: Path) -> None:
        self.interno = interno
        self.destino = destino
        self.interacciones: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        respuesta = await self.interno.handle_async_request(request)
        contenido = await respuesta.aread()
        self.interacciones.append(
            {
                "peticion": {
                    "metodo": request.method,
                    "ruta": request.url.path,
                    "cabeceras": _cabeceras(request.headers),
                    "cuerpo": _cuerpo(request.content),
                },
                "respuesta": {
                    "estado": respuesta.status_code,
                    "cabeceras": _cabeceras(respuesta.headers),
                    "cuerpo": _cuerpo(contenido),
                },
            }
        )
        # Se escribe tras cada interacción: si la ejecución real se corta, lo pagado queda.
        self.destino.parent.mkdir(parents=True, exist_ok=True)
        self.destino.write_text(
            json.dumps(self.interacciones, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # El cuerpo ya está descomprimido: se devuelve sin `content-encoding` ni longitud vieja.
        cabeceras = [
            (k, v)
            for k, v in respuesta.headers.items()
            if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
        ]
        return httpx2.Response(
            respuesta.status_code, headers=cabeceras, content=contenido, request=request
        )

    async def aclose(self) -> None:
        await self.interno.aclose()


def reproductor(casete: Path) -> httpx2.MockTransport:
    """Devuelve las respuestas del casete en orden y falla si la petición no es la grabada."""
    interacciones: list[dict[str, Any]] = json.loads(casete.read_text(encoding="utf-8"))
    pendientes = iter(interacciones)

    def responder(request: httpx2.Request) -> httpx2.Response:
        try:
            grabada = next(pendientes)
        except StopIteration:
            raise AssertionError(
                f"petición no grabada: {request.method} {request.url.path}"
            ) from None
        esperada = grabada["peticion"]
        if (request.method, request.url.path) != (esperada["metodo"], esperada["ruta"]):
            raise AssertionError(
                f"se esperaba {esperada['metodo']} {esperada['ruta']} y llegó "
                f"{request.method} {request.url.path}"
            )
        r = grabada["respuesta"]
        return httpx2.Response(r["estado"], headers=r["cabeceras"], content=_bytes(r["cuerpo"]))

    return httpx2.MockTransport(responder)
