"""Normaliza dos documentos OpenAPI 3.1 para compararlos por estructura.

`specs/openapi.yaml` está escrito a mano y el OpenAPI de FastAPI sale de Pydantic: dicen lo
mismo con formas distintas. Este módulo los lleva a una forma común **sin perder nada que
cambie el contrato**. Solo se descartan claves de documentación; todo lo demás se compara
(`specs/plan1.md` § 4.2).
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
RUTA_CONTRATO = RAIZ_REPO / "specs" / "openapi.yaml"

CLAVES_DOCUMENTACION = frozenset(
    {"description", "summary", "example", "examples", "title", "contact", "license"}
)
METODOS = ("get", "post", "put", "patch", "delete")


def cargar_contrato() -> dict[str, Any]:
    with RUTA_CONTRATO.open(encoding="utf-8") as f:
        documento: dict[str, Any] = yaml.safe_load(f)
    return documento


def _resolver(nodo: Any, raiz: dict[str, Any], pila: tuple[str, ...] = ()) -> Any:
    """Sustituye cada `$ref` interno por su destino, recursivamente."""
    if isinstance(nodo, dict):
        if "$ref" in nodo:
            ref = nodo["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#/"):
                raise ValueError(f"$ref no interno: {ref!r}")
            if ref in pila:
                raise ValueError(f"$ref circular: {' -> '.join((*pila, ref))}")
            destino: Any = raiz
            for parte in ref[2:].split("/"):
                destino = destino[parte]
            hermanos = {k: v for k, v in nodo.items() if k != "$ref"}
            resuelto = _resolver(destino, raiz, (*pila, ref))
            if hermanos and isinstance(resuelto, dict):
                return {**resuelto, **_resolver(hermanos, raiz, pila)}
            return resuelto
        return {k: _resolver(v, raiz, pila) for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [_resolver(v, raiz, pila) for v in nodo]
    return nodo


def _es_nulo(schema: Any) -> bool:
    return isinstance(schema, dict) and schema.get("type") == "null" and len(schema) == 1


def _normalizar_schema(nodo: Any) -> Any:
    if isinstance(nodo, list):
        return [_normalizar_schema(v) for v in nodo]
    if not isinstance(nodo, dict):
        return nodo

    s = {k: _normalizar_schema(v) for k, v in nodo.items() if k not in CLAVES_DOCUMENTACION}

    # `default: null` no dice nada que `required` no diga ya.
    if "default" in s and s["default"] is None:
        del s["default"]

    # Pydantic escribe `anyOf: [X, {type: null}]`; el contrato, `type: [X, 'null']`.
    alternativas = s.get("anyOf")
    if isinstance(alternativas, list) and len(alternativas) == 2:
        nulos = [a for a in alternativas if _es_nulo(a)]
        otros = [a for a in alternativas if not _es_nulo(a)]
        if len(nulos) == 1 and isinstance(otros[0], dict) and isinstance(otros[0].get("type"), str):
            base = dict(otros[0])
            base["type"] = [base["type"], "null"]
            del s["anyOf"]
            s = {**base, **s}

    if isinstance(s.get("type"), list):
        s["type"] = sorted(s["type"])
    if isinstance(s.get("required"), list):
        s["required"] = sorted(s["required"])
    if isinstance(s.get("enum"), list):
        s["enum"] = sorted(s["enum"], key=repr)
    return s


def _normalizar_operacion(op: dict[str, Any]) -> dict[str, Any]:
    parametros = {}
    for p in op.get("parameters", []):
        parametros[f"{p['in']}:{p['name']}"] = {
            "required": bool(p.get("required", False)),
            "schema": _normalizar_schema(p.get("schema", {})),
        }

    cuerpo = None
    if "requestBody" in op:
        rb = op["requestBody"]
        cuerpo = {
            "required": bool(rb.get("required", False)),
            "content": {
                medio: _normalizar_schema(c.get("schema", {}))
                for medio, c in rb.get("content", {}).items()
            },
        }

    respuestas = {}
    for codigo, r in op.get("responses", {}).items():
        respuestas[str(codigo)] = {
            "content": {
                medio: _normalizar_schema(c.get("schema", {}))
                for medio, c in (r.get("content") or {}).items()
            },
            "headers": {
                nombre: _normalizar_schema(h.get("schema", {}))
                for nombre, h in (r.get("headers") or {}).items()
            },
        }

    return {
        "tags": sorted(op.get("tags", [])),
        "parameters": parametros,
        "requestBody": cuerpo,
        "responses": respuestas,
    }


def operaciones(documento: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Devuelve `{operationId: {metodo, ruta, ...forma normalizada}}`."""
    doc = copy.deepcopy(documento)
    resultado: dict[str, dict[str, Any]] = {}
    for ruta, item in doc.get("paths", {}).items():
        comunes = item.get("parameters", [])
        for metodo in METODOS:
            if metodo not in item:
                continue
            op = dict(item[metodo])
            op["parameters"] = [*comunes, *op.get("parameters", [])]
            op = _resolver(op, doc)
            op_id = op.get("operationId")
            if not op_id:
                raise ValueError(f"{metodo.upper()} {ruta} sin operationId")
            if op_id in resultado:
                raise ValueError(f"operationId duplicado: {op_id}")
            resultado[op_id] = {"metodo": metodo, "ruta": ruta, **_normalizar_operacion(op)}
    return resultado


def cabecera(documento: dict[str, Any]) -> dict[str, Any]:
    return {
        "openapi": documento.get("openapi"),
        "info": {
            "title": documento.get("info", {}).get("title"),
            "version": documento.get("info", {}).get("version"),
        },
        "servers": sorted(s["url"] for s in documento.get("servers", [])),
        "tags": sorted(t["name"] for t in documento.get("tags", [])),
    }


def _diferencias(a: Any, b: Any, ruta: str) -> Iterator[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        for clave in sorted(set(a) | set(b)):
            sub = f"{ruta}.{clave}"
            if clave not in a:
                yield f"{sub}: sobra en el generado"
            elif clave not in b:
                yield f"{sub}: falta en el generado"
            else:
                yield from _diferencias(a[clave], b[clave], sub)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            yield from _diferencias(x, y, f"{ruta}[{i}]")
    elif a != b:
        yield f"{ruta}: contrato={a!r} generado={b!r}"


def comparar(
    aprobado: dict[str, Any], generado: dict[str, Any], pendientes: frozenset[str]
) -> list[str]:
    """Lista de divergencias entre el contrato aprobado y el OpenAPI generado.

    Una operación en `pendientes` puede faltar en el generado, y no puede estar en él: al
    implementarla se saca de la lista.
    """
    problemas: list[str] = list(_diferencias(cabecera(aprobado), cabecera(generado), "cabecera"))
    ops_a = operaciones(aprobado)
    ops_g = operaciones(generado)

    for op_id in sorted(set(pendientes) - set(ops_a)):
        problemas.append(f"{op_id}: está en PENDIENTES y no existe en el contrato")
    for op_id in sorted(ops_g):
        if op_id not in ops_a:
            problemas.append(f"{op_id}: implementada y ausente del contrato")
        elif op_id in pendientes:
            problemas.append(f"{op_id}: implementada, hay que sacarla de PENDIENTES")
        else:
            problemas.extend(_diferencias(ops_a[op_id], ops_g[op_id], op_id))
    for op_id in sorted(ops_a):
        if op_id not in ops_g and op_id not in pendientes:
            problemas.append(f"{op_id}: no implementada y fuera de PENDIENTES")
    return problemas


def schema_de_respuesta(
    aprobado: dict[str, Any], op_id: str, codigo: int, medio: str
) -> dict[str, Any] | None:
    """Schema aprobado ya resuelto, para validar una respuesta concreta con jsonschema."""
    doc = copy.deepcopy(aprobado)
    for item in doc["paths"].values():
        for metodo in METODOS:
            op = item.get(metodo)
            if op and op.get("operationId") == op_id:
                respuesta = op["responses"].get(str(codigo))
                if respuesta is None:
                    raise AssertionError(f"{op_id} no declara el código {codigo} en el contrato")
                respuesta = _resolver(respuesta, doc)
                contenido = (respuesta.get("content") or {}).get(medio)
                if contenido is None:
                    if respuesta.get("content"):
                        raise AssertionError(
                            f"{op_id} {codigo}: el contrato no declara el medio {medio}"
                        )
                    return None
                schema: dict[str, Any] = contenido.get("schema", {})
                return schema
    raise AssertionError(f"{op_id} no existe en el contrato")
