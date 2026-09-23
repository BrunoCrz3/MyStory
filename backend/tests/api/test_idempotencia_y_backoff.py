"""H8 · pruebas 3 y 4 — RI-05, RI-07.

Dos promesas de la interfaz que solo se ven cuando algo va mal:

- **Idempotencia por `escena_id` + `version`.** Un reintento de la
  consolidacion no puede consolidar dos veces. Si lo hiciera, el canon acabaria
  con el doble de hechos por un timeout de red, y ningun hecho diria de donde
  salio su copia.
- **Backoff exponencial con jitter.** Un limite de tasa del proveedor no es un
  defecto de la escena: es una espera. Y si todos los trabajos que lo reciben
  reintentan a la vez, la espera se vuelve cascada.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from anthropic import APIStatusError, AuthenticationError, RateLimitError
from fastapi.testclient import TestClient

from app.canon import service as canon
from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.commons.llm.cliente import RespuestaDelModelo, es_reintentable
from app.commons.reintentos import PoliticaDeReintentos
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.orquestador import CerrojoDeGeneracion
from tests.process import fabrica

# Cifras del escenario, no del sistema: el fichero de umbrales las tiene en
# `null` y la politica se pasa explicita para poder ejercitar el camino.
BASE_SEGUNDOS = 0.001
FACTOR = 2.0
MAX_INTENTOS = 3


def _respuesta(codigo: int) -> httpx.Response:
    return httpx.Response(codigo, request=httpx.Request("POST", "https://api.anthropic.com/v1"))


def _limite_de_tasa() -> RateLimitError:
    return RateLimitError("demasiadas peticiones", response=_respuesta(429), body=None)


# --- RI-05: idempotencia de la escritura en canon -------------------------


def _consolidar(cliente: TestClient, escena_id: int, ilia: int, texto: str) -> httpx.Response:
    return cliente.post(
        "/canon/consolidaciones",
        json={
            "escena_id": escena_id,
            "version": 1,
            "texto": texto,
            "hechos": [
                {
                    "texto": "Ilia cruza el agua",
                    "tipo": "descriptivo",
                    "sujeto_personaje_id": ilia,
                }
            ],
        },
    )


def test_los_endpoints_de_escritura_en_canon_son_idempotentes(cliente: TestClient) -> None:
    """RI-05, RF-CANON-08. La clave es `escena_id` + `version`."""
    obra = cliente.post(
        "/novel/obra", json={"premisa": "un puente recuerda", "genero": "cf"}
    ).json()
    parte = cliente.post(
        "/novel/partes",
        json={
            "obra_id": obra["id"],
            "orden": 1,
            "funcion_dramatica": "planteamiento",
            "punto_de_giro": "habla",
        },
    ).json()
    capitulo = cliente.post("/novel/capitulos", json={"parte_id": parte["id"], "orden": 1}).json()
    escena = cliente.post("/novel/escenas", json={"capitulo_id": capitulo["id"], "orden": 1}).json()
    ilia = cliente.post("/novel/personajes", json={"nombre": "Ilia"}).json()
    texto = "Ilia cruza el agua de noche."

    cliente.post(f"/process/escenas/{escena['id']}/versiones", json={"texto": texto})
    for destino in ("en_borrador", "en_revision"):
        cliente.post(f"/novel/escenas/{escena['id']}/transicion", json={"destino": destino})
    cliente.post(f"/process/escenas/{escena['id']}/aceptacion", json={"version": 1})

    primera = _consolidar(cliente, escena["id"], ilia["id"], texto)
    segunda = _consolidar(cliente, escena["id"], ilia["id"], texto)

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert primera.json()["snapshot"]["id"] == segunda.json()["snapshot"]["id"]

    hechos = cliente.get(f"/canon/escenas/{escena['id']}/hechos").json()
    assert len(hechos) == 1, "el reintento duplico el canon de la escena"


# --- RI-07: backoff exponencial con jitter --------------------------------


def test_el_backoff_es_exponencial_con_jitter() -> None:
    """La curva, con el azar fijado para poder mirarla.

    Sin jitter la espera es la potencia exacta. Con jitter es un valor entre
    cero y esa potencia --full jitter--, que es el esquema que mas dispersa los
    reintentos de una rafaga. Que se pueda fijar el azar no es una puerta
    trasera: es la unica forma de probar la forma de la curva y no el generador.
    """
    exacta = PoliticaDeReintentos(
        max_intentos=MAX_INTENTOS, base_segundos=BASE_SEGUNDOS, factor=FACTOR, jitter=False
    )
    esperas = [exacta.espera(intento) for intento in (1, 2, 3, 4)]
    assert esperas == [
        BASE_SEGUNDOS,
        BASE_SEGUNDOS * FACTOR,
        BASE_SEGUNDOS * FACTOR**2,
        BASE_SEGUNDOS * FACTOR**3,
    ]
    assert all(despues > antes for antes, despues in zip(esperas, esperas[1:], strict=False)), (
        "una curva que no crece no es backoff"
    )

    con_jitter = PoliticaDeReintentos(
        max_intentos=MAX_INTENTOS, base_segundos=BASE_SEGUNDOS, factor=FACTOR, jitter=True
    )
    assert con_jitter.espera(3, azar=0.0) == 0.0
    assert con_jitter.espera(3, azar=1.0) == exacta.espera(3)
    assert 0.0 < con_jitter.espera(3, azar=0.5) < exacta.espera(3)

    # Y el azar de verdad reparte: dos trabajos que fallan juntos no vuelven
    # juntos. Sin esto el jitter seria decorativo.
    muestras = {con_jitter.espera(3) for _ in range(20)}
    assert len(muestras) > 1


def test_sin_los_umbrales_declarados_no_se_reintenta() -> None:
    """`orquestacion` esta en `null` en v1: una llamada y su fallo sube.

    Es el mismo criterio que la fase de medicion. Y hacen falta las tres cifras:
    reintentar sin saber cuanto esperar es reintentar de inmediato, que es la
    cascada que el backoff existe para evitar.
    """
    declarada = PoliticaDeReintentos.declarada(fabrica.umbrales())
    assert declarada.activa is False
    assert declarada.quedan_intentos(1) is False
    assert declarada.espera(1) == 0.0

    a_medias = PoliticaDeReintentos(
        max_intentos=MAX_INTENTOS, base_segundos=None, factor=FACTOR, jitter=True
    )
    assert a_medias.activa is False


def test_el_tope_de_intentos_se_agota_y_el_fallo_sube() -> None:
    politica = PoliticaDeReintentos(
        max_intentos=MAX_INTENTOS, base_segundos=BASE_SEGUNDOS, factor=FACTOR, jitter=True
    )
    assert [politica.quedan_intentos(intento) for intento in (1, 2, 3, 4)] == [
        True,
        True,
        False,
        False,
    ]


def test_solo_se_reintenta_lo_transitorio() -> None:
    """Un 4xx no se arregla esperando.

    Un prompt que no cabe, una credencial mala o un modelo que no existe fallan
    igual al tercer intento, y gastar el tope en ellos es no tenerlo cuando de
    verdad haga falta. Quien lo decide es `commons/llm`: la feature que orquesta
    no tiene por que conocer el SDK.
    """
    assert es_reintentable(_limite_de_tasa()) is True
    assert (
        es_reintentable(APIStatusError("proveedor caido", response=_respuesta(503), body=None))
        is True
    )
    assert (
        es_reintentable(AuthenticationError("credencial mala", response=_respuesta(401), body=None))
        is False
    )
    assert es_reintentable(ValueError("un error nuestro")) is False


def test_un_limite_de_tasa_se_reintenta_y_la_generacion_sale_adelante(
    base: Conexion,
) -> None:
    """La politica, vista desde la puerta que llama al modelo.

    Y una cosa que no se ve en la curva: el presupuesto en vuelo **no se suelta
    entre intentos**. El trabajo sigue en vuelo mientras espera, porque
    devolverlo dejaria entrar a otro que tampoco va a pasar el limite de tasa.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    umbrales = _con_politica(fabrica.umbrales())
    pool = PoolEnVuelo(umbrales.en_vuelo.total)

    class ModeloConLimiteDeTasa(fabrica.ModeloDeLaboratorio):
        def __init__(self, fallos: int) -> None:
            super().__init__()
            self.fallos = fallos
            self.libre_durante_la_espera: list[int] = []

        async def generar(
            self, mensajes: list[dict[str, Any]], sistema: str | None = None
        ) -> RespuestaDelModelo:
            if self.fallos:
                self.fallos -= 1
                self.libre_durante_la_espera.append(pool.libre)
                raise _limite_de_tasa()
            return await super().generar(mensajes, sistema)

    modelo = ModeloConLimiteDeTasa(fallos=2)
    version = asyncio.run(
        proceso.generar_borrador(
            base,
            umbrales,
            modelo,
            pool,
            CerrojoDeGeneracion(),
            brief.escena_id,
            process_schemas.PeticionDeBorrador(),
        )
    )

    assert version.texto == fabrica.TEXTO_GENERADO
    assert len(modelo.prompts) == 1, "el intento bueno es uno, los otros dos no llegaron a texto"
    assert all(libre < pool.total for libre in modelo.libre_durante_la_espera)
    assert pool.libre == pool.total, "el presupuesto no volvio al pool al terminar"

    # Un solo registro de generacion: los intentos fallidos no generaron nada.
    assert len(proceso.registros_de(base, brief.escena_id)) == 1


def test_si_se_agotan_los_intentos_el_fallo_llega_al_autor(base: Conexion) -> None:
    """Escalar es un resultado valido; tragarse el error no lo es."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    umbrales = _con_politica(fabrica.umbrales())

    class ModeloQueSiempreFalla(fabrica.ModeloDeLaboratorio):
        async def generar(
            self, mensajes: list[dict[str, Any]], sistema: str | None = None
        ) -> RespuestaDelModelo:
            raise _limite_de_tasa()

    with pytest.raises(RateLimitError):
        asyncio.run(
            proceso.generar_borrador(
                base,
                umbrales,
                ModeloQueSiempreFalla(),
                PoolEnVuelo(umbrales.en_vuelo.total),
                CerrojoDeGeneracion(),
                brief.escena_id,
                process_schemas.PeticionDeBorrador(),
            )
        )

    assert proceso.registros_de(base, brief.escena_id) == []
    assert proceso.versiones_de(base, brief.escena_id) == []
    assert canon.inventario_del_canon(base)["hecho_canonico"] >= 0


def _con_politica(umbrales: Umbrales) -> Umbrales:
    orquestacion = umbrales.orquestacion
    return umbrales.model_copy(
        update={
            "orquestacion": orquestacion.model_copy(
                update={
                    "max_intentos_trabajo": MAX_INTENTOS,
                    "backoff": orquestacion.backoff.model_copy(
                        update={"base_segundos": BASE_SEGUNDOS, "factor": FACTOR}
                    ),
                }
            )
        }
    )
