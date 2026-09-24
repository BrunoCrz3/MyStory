"""Servidor HTTP local de la página `lectura` de prueba, en la ruta de CL-01 (P47b, P48).

`render_visual` y el export abren la lectura por URL, así que las pruebas sirven el HTML de
`pagina.py` —o una variante rota— desde un hilo, sobre `127.0.0.1` y un puerto libre. Con
`generador`, la página se construye al pedirla, como la del frontend, que lee la versión de la
API en ese momento: es lo que necesita el gate para pintar una candidata recién escrita.
"""

from __future__ import annotations

import http.server
import re
import threading
from collections.abc import Callable, Iterator
from urllib.parse import urlparse

import pytest

from app.versioning import lectura


class Paginas:
    """Sirve el HTML que cada prueba le da, en la ruta de CL-01."""

    def __init__(self) -> None:
        self.html: dict[str, str] = {}
        self.generador: Callable[[str, int], str] | None = None
        paginas = self

        class Manejador(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                cuerpo = paginas.html.get(self.path) or paginas.generar(self.path)
                self.send_response(200 if cuerpo is not None else 404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write((cuerpo or "no encontrada").encode("utf-8"))

            def log_message(self, *args: object) -> None:
                return

        self.servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.base = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def generar(self, ruta: str) -> str | None:
        encaje = re.fullmatch(r"/novelas/([^/]+)/versiones/(\d+)", ruta)
        if self.generador is None or encaje is None:
            return None
        return self.generador(encaje.group(1), int(encaje.group(2)))

    def servir(self, novela: str, version: int, html: str) -> None:
        self.html[urlparse(lectura.url(self.base, novela, version)).path] = html


@pytest.fixture
def paginas() -> Iterator[Paginas]:
    p = Paginas()
    yield p
    p.servidor.shutdown()
