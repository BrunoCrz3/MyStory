"""El único camino al modelo (RNF-08, RF-CTX-02).

`LlamadorModelo.llamar()` cuenta la petición, comprueba que cabe en `contexto.total`, pide
hueco en el pool, abre el span del rol y llama. Ningún módulo fuera de `commons/llm/` habla
con el `ClienteModelo` directamente: lo comprueba la prueba de arquitectura.
"""

from __future__ import annotations

from app.commons.config import Config
from app.commons.llm.pool import PoolEnVuelo
from app.commons.llm.protocolo import ClienteModelo, ErrorModelo, Peticion, Respuesta
from app.commons.observabilidad.protocolo import Trazador


class ContextoNoCabe(ErrorModelo):
    """El ensamblado supera `contexto.total` después de degradar. Falla en voz alta, sin
    llamar al modelo y sin truncar."""


class LlamadorModelo:
    def __init__(
        self, config: Config, cliente: ClienteModelo, pool: PoolEnVuelo, trazador: Trazador
    ) -> None:
        self.config = config
        self.cliente = cliente
        self.pool = pool
        self.trazador = trazador

    async def contar(self, peticion: Peticion) -> int:
        """Tokens de entrada de una petición, con el contador del proveedor."""
        return (await self.cliente.contar_tokens(peticion)).tokens_entrada

    async def llamar(self, peticion: Peticion) -> Respuesta:
        recuento = await self.cliente.contar_tokens(peticion)
        total = self.config.umbrales.contexto.total
        if recuento.estimacion > total:
            raise ContextoNoCabe(
                f"{peticion.rol}: la petición ocupa {recuento.tokens_entrada} tokens más "
                f"{recuento.max_tokens} de salida y el límite por petición es {total}"
            )
        async with self.pool.reservar(recuento.estimacion):
            with self.trazador.generacion(peticion) as observacion:
                try:
                    respuesta = await self.cliente.generar(peticion, recuento)
                except BaseException as e:
                    observacion.error(e)
                    raise
                observacion.registrar(respuesta)
        return respuesta
