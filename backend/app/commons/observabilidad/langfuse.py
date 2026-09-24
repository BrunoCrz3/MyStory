"""La única implementación de producción de `Trazador`, sobre el SDK de Langfuse v4.

**Sin credenciales, degrada en vez de fallar** (spec § 2.4, D-10): el span existe igual y se
escribe en el log `storymaker.trazas`, y `GET /salud` dice `degradado`. Perder
observabilidad no debe costar una novela.

El log degradado lleva nombres, identificadores y tokens, **nunca el contenido**: la entrada
de un prompt contiene datos personales del destinatario (RNF-18), y un log de proceso no
tiene la retención controlada que se exigirá a Langfuse.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.commons.llm.protocolo import Peticion, Respuesta
from app.commons.observabilidad.protocolo import (
    AGENTE_DE_ROL,
    ContextoTraza,
    validar_nombre_span,
)

_log = logging.getLogger("storymaker.trazas")


class _ObservacionLangfuse:
    def __init__(self, observacion: Any | None, nombre: str, id_local: str) -> None:
        self._obs = observacion
        self._nombre = nombre
        self._id = id_local
        self._inicio = time.monotonic()

    def actualizar(self, *, salida: Any = None, metadata: dict[str, Any] | None = None) -> None:
        if self._obs is not None:
            self._obs.update(output=salida, metadata=metadata)

    def registrar(self, respuesta: Respuesta) -> None:
        uso = {"input": respuesta.tokens_entrada, "output": respuesta.tokens_salida}
        if respuesta.tokens_razonamiento is not None:
            uso["reasoning"] = respuesta.tokens_razonamiento
        if self._obs is not None:
            self._obs.update(
                output=respuesta.datos if respuesta.datos is not None else respuesta.texto,
                usage_details=uso,
                cost_details={"total": respuesta.coste_usd},
                metadata={"latencia_s": respuesta.latencia_s, "stop_reason": respuesta.stop_reason},
            )
        _log.info(
            "generacion %s [%s] modelo=%s entrada=%d salida=%d razonamiento=%s coste=%.4f",
            self._nombre,
            self._id,
            respuesta.modelo,
            respuesta.tokens_entrada,
            respuesta.tokens_salida,
            respuesta.tokens_razonamiento,
            respuesta.coste_usd,
        )

    def error(self, error: BaseException) -> None:
        if self._obs is not None:
            self._obs.update(level="ERROR", status_message=type(error).__name__)
        _log.warning("span %s [%s] falló: %s", self._nombre, self._id, type(error).__name__)


class TrazadorLangfuse:
    def __init__(self) -> None:
        publica = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        secreta = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
        host = os.environ.get("LANGFUSE_HOST", "").strip()
        self._cliente: Any | None = None
        if publica and secreta:
            from langfuse import Langfuse

            self._cliente = Langfuse(
                public_key=publica,
                secret_key=secreta,
                host=host or None,
                environment=os.environ.get("STORYMAKER_ENV", "").strip() or None,
            )
        else:
            _log.warning("Langfuse sin credenciales: trazas en modo degradado (solo log)")

    @property
    def degradado(self) -> bool:
        return self._cliente is None

    @contextmanager
    def traza(
        self, nombre: str, *, novel_id: str, metadata: dict[str, Any] | None = None
    ) -> Iterator[ContextoTraza]:
        validar_nombre_span(nombre)
        id_local = uuid.uuid4().hex
        _log.info("traza %s [%s] sesion=%s", nombre, id_local, novel_id)
        if self._cliente is None:
            yield ContextoTraza(traza_id=None, url=None, id_local=id_local)
            return
        from langfuse import propagate_attributes

        with (
            self._cliente.start_as_current_observation(
                as_type="span", name=nombre, metadata=metadata
            ) as raiz,
            propagate_attributes(session_id=novel_id, trace_name=nombre),
        ):
            traza_id = raiz.trace_id
            url: str | None
            try:
                url = self._cliente.get_trace_url(trace_id=traza_id)
            except Exception:
                url = None
            yield ContextoTraza(traza_id=traza_id, url=url, id_local=id_local)

    @contextmanager
    def span(
        self, nombre: str, *, entrada: Any = None, metadata: dict[str, Any] | None = None
    ) -> Iterator[_ObservacionLangfuse]:
        validar_nombre_span(nombre)
        id_local = uuid.uuid4().hex[:12]
        _log.info("span %s [%s]", nombre, id_local)
        if self._cliente is None:
            yield _ObservacionLangfuse(None, nombre, id_local)
            return
        with self._cliente.start_as_current_observation(
            as_type="tool" if nombre in ("consultar_story_bible",) else "span",
            name=nombre,
            input=entrada,
            metadata=metadata,
        ) as obs:
            yield _ObservacionLangfuse(obs, nombre, id_local)

    @contextmanager
    def generacion(self, peticion: Peticion) -> Iterator[_ObservacionLangfuse]:
        nombre = AGENTE_DE_ROL[peticion.rol]
        id_local = uuid.uuid4().hex[:12]
        metadata = {"prompt": peticion.prompt, "hash_prompt": peticion.hash_prompt}
        if self._cliente is None:
            yield _ObservacionLangfuse(None, nombre, id_local)
            return
        with self._cliente.start_as_current_observation(
            as_type="generation",
            name=nombre,
            input={
                "system": peticion.system,
                "mensajes": [m.model_dump() for m in peticion.mensajes],
            },
            metadata=metadata,
            version=peticion.hash_prompt,
        ) as obs:
            yield _ObservacionLangfuse(obs, nombre, id_local)

    def score(
        self,
        nombre: str,
        valor: float,
        *,
        comentario: str | None,
        traza_id: str | None = None,
    ) -> None:
        _log.info("score %s=%s", nombre, valor)
        if self._cliente is None:
            return
        destino = traza_id or self._cliente.get_current_trace_id()
        if destino is None:
            _log.warning("score %s sin traza a la que asociarse", nombre)
            return
        self._cliente.create_score(
            name=nombre, value=float(valor), trace_id=destino, comment=comentario
        )

    def cerrar(self) -> None:
        if self._cliente is not None:
            self._cliente.shutdown()
