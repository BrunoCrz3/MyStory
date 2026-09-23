"""H6 · terminado cuando — RF-PROC-05, RD-05, RD-08, RD-09.

«El orquestador lleva una escena de `planificada` a `en revision` sin que ningun
agente decida el paso siguiente.»

Asi se lee esta prueba: el bucle pregunta a la maquina, ejecuta lo que dice y
vuelve a preguntar. **La maquina no ejecuta y el ejecutor no decide.** En v1 la
cola es sincrona y en proceso (RD-05), asi que quien invoca es quien llama a la
API --aqui, el bucle--; el dia que haya cola, el que escribe la fila. Ni uno ni
otro cambian nada de lo que el agente ve, que es lo que RD-08 promete.

Y el avance se lee de la base en cada vuelta, nunca de una variable del bucle
(RD-09): si el proceso muriera entre dos preguntas, la siguiente daria la misma
respuesta.
"""

from __future__ import annotations

import asyncio

from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.novel import service as novel
from app.novel.models import EstadoDeEscena
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.orquestador import CerrojoDeGeneracion, Paso
from app.quality import schemas as quality_schemas
from app.quality import service as quality
from tests.process import fabrica

MAXIMO_DE_VUELTAS = 6


def _redactar(base: Conexion, umbrales: Umbrales, escena_id: int) -> None:
    asyncio.run(
        proceso.generar_borrador(
            base,
            umbrales,
            fabrica.ModeloDeLaboratorio(),
            PoolEnVuelo(umbrales.en_vuelo.total),
            CerrojoDeGeneracion(),
            escena_id,
            process_schemas.PeticionDeBorrador(),
        )
    )


def _criticar(base: Conexion, umbrales: Umbrales, escena_id: int) -> None:
    brief = proceso.brief_de(base, escena_id)
    version = proceso.versiones_de(base, escena_id)[-1]
    quality.criticar(
        base,
        umbrales,
        quality_schemas.PeticionDeCritica(
            escena_id=escena_id,
            version=version.numero,
            texto=version.texto,
            brief=brief.encargo,
            restriccion_de_destino=brief.restricciones[0].enunciado,
        ),
    )
    novel.transicionar_escena(base, escena_id, EstadoDeEscena.EN_REVISION)


def test_el_orquestador_lleva_la_escena_de_planificada_a_en_revision(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    umbrales = fabrica.umbrales()

    # El ejecutor no sabe de estados: solo sabe hacer lo que le digan.
    ejecutores = {Paso.REDACTOR: _redactar, Paso.CRITICO: _criticar}

    recorrido: list[str] = []
    for _ in range(MAXIMO_DE_VUELTAS):
        sugerido = proceso.siguiente_paso_de(base, umbrales, brief.escena_id)
        recorrido.append(f"{sugerido.estado}->{sugerido.paso}")
        if sugerido.estado == EstadoDeEscena.EN_REVISION.value:
            break
        ejecutores[Paso(sugerido.paso)](base, umbrales, brief.escena_id)

    assert recorrido == [
        "planificada->redactor",
        "en_borrador->critico",
        "en_revision->verificador",
    ]
    assert novel.obtener_escena(base, brief.escena_id).estado is EstadoDeEscena.EN_REVISION


def test_el_recorrido_se_reconstruye_desde_la_base_y_no_desde_el_bucle(
    base: Conexion,
) -> None:
    """RD-09.

    Se pregunta dos veces seguidas sin ejecutar nada en medio: la respuesta es la
    misma porque sale del estado persistido. Si el avance viviera en el bucle,
    preguntar seria avanzar.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    umbrales = fabrica.umbrales()

    primera = proceso.siguiente_paso_de(base, umbrales, brief.escena_id)
    segunda = proceso.siguiente_paso_de(base, umbrales, brief.escena_id)

    assert primera == segunda
    assert primera.paso == Paso.REDACTOR.value
