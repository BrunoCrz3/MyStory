"""Carga `config/` y comprueba lo que el arranque no puede dejar pasar (RNF-15)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.commons.config.modelos import ROLES, Config

RAIZ_REPO = Path(__file__).resolve().parents[4]
CONFIG_POR_DEFECTO = RAIZ_REPO / "config"


class ConfigInvalida(RuntimeError):
    """La configuración no permite arrancar. El mensaje nombra cada clave culpable."""


def directorio_config() -> Path:
    valor = os.environ.get("STORYMAKER_CONFIG_DIR", "").strip()
    return Path(valor) if valor else CONFIG_POR_DEFECTO


def _leer(ruta: Path) -> Any:
    try:
        return yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ConfigInvalida(f"falta el fichero de configuración {ruta}") from e


def _clave(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(p) for p in loc)


def cargar_config(directorio: Path | None = None) -> Config:
    directorio = directorio or directorio_config()
    crudo = {
        "umbrales": _leer(directorio / "thresholds.yaml"),
        "modelos": _leer(directorio / "models.yaml"),
    }
    try:
        config = Config.model_validate(crudo)
    except ValidationError as e:
        detalle = "; ".join(
            f"{_clave(err['loc'][1:])}: {err['msg']}" for err in e.errors(include_url=False)
        )
        raise ConfigInvalida(f"configuración inválida en {directorio}: {detalle}") from e

    problemas = _comprobar(config)
    if problemas:
        raise ConfigInvalida(f"configuración inválida en {directorio}: " + "; ".join(problemas))
    return config


def _comprobar(config: Config) -> list[str]:
    u = config.umbrales
    problemas: list[str] = []

    suma = sum(u.contexto.capas.model_dump().values())
    if suma != u.contexto.total:
        problemas.append(
            f"contexto.capas suma {suma} y contexto.total es {u.contexto.total}: deben coincidir"
        )

    margen = u.contexto.capas.margen
    for rol in ROLES:
        if config.max_tokens(rol) > margen:
            problemas.append(
                f"modelo.max_tokens_por_rol.{rol} ({config.max_tokens(rol)}) supera "
                f"contexto.capas.margen ({margen}): la respuesta se truncaría"
            )

    if u.medicion.cerrar_el_paso:
        for clave, valor in u.calidad.model_dump().items():
            if valor is None:
                problemas.append(
                    f"calidad.{clave} es null y medicion.cerrar_el_paso es true: "
                    "un umbral que cierra el paso no puede faltar"
                )

    if u.formal.gate_activo and u.formal.lean_timeout_segundos is None:
        problemas.append("formal.lean_timeout_segundos es null con formal.gate_activo en true")
    if u.formal.lean_incremental and u.formal.lean_timeout_segundos is None:
        problemas.append("formal.lean_timeout_segundos es null con formal.lean_incremental en true")

    precios = u.coste.precio_usd_por_millon
    for rol in ROLES:
        modelo = config.modelos.roles.de(rol).id
        if modelo not in precios:
            problemas.append(
                f"coste.precio_usd_por_millon.{modelo} falta: el rol {rol} no tendría coste"
            )

    if config.modelos.roles.judge.id == config.modelos.roles.redactor.id:
        problemas.append("roles.judge.id no puede ser el mismo modelo que roles.redactor (TO-013)")

    if u.contexto.capas.invariante <= 0 or u.contexto.capas.estructural <= 0:
        problemas.append("contexto.capas.invariante y estructural no pueden ser cero")
    return problemas
