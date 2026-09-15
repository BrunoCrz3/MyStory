"""Punto de entrada de modulo: `python -m novela ...`."""

from __future__ import annotations

from novela.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
