"""Servidor HTTP local de la página `lectura` de prueba, en la ruta de CL-01 (P47b, P48).

`render_visual` y el export abren la lectura por URL, así que las pruebas sirven el HTML de
`pagina.py` —o una variante rota— desde un hilo, sobre `127.0.0.1` y un puerto libre.
"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest

from app.versioning import lectura


class Paginas:
    """Sirve el HTML que cada prueba le da, en la ruta de CL-01."""

    def __init__(self) -> None:
        self.html: dict[str, str] = {}
        paginas = self

        class Manejador(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                cuerpo = paginas.html.get(self.path)
                self.send_response(200 if cuerpo is not None else 404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write((cuerpo or "no encontrada").encode("utf-8"))

            def log_message(self, *args: object) -> None:
                return

        self.servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.base = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def servir(self, novela: str, version: int, html: str) -> None:
        self.html[urlparse(lectura.url(self.base, novela, version)).path] = html


@pytest.fixture
def paginas() -> Iterator[Paginas]:
    p = Paginas()
    yield p
    p.servidor.shutdown()
