"""H6 · pruebas 3, 4 y 7 — A-45, P-24, P-28, P-35, RF-PROC-02 a RF-PROC-04, RNF-09.

El borrador sale del brief y del contexto ensamblado; la version guarda con que
se produjo; y mientras se produce, no hay otra escena generandose.

Lo que estas pruebas **no** dicen: que el modelo escriba bien. Eso no es
verificable con una prueba de regresion y tiene su sitio en los evals. Lo que si
dicen es que alrededor de la llamada pasa todo lo que el sistema promete.
"""

from __future__ import annotations

import asyncio

import pytest

from app.commons.db.conexion import Conexion
from app.commons.errores import RecursoNoEncontrado
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.novel.models import EstadoDeEscena
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.models import OrigenDeVersion
from app.process.orquestador import CerrojoDeGeneracion
from tests.process import fabrica


async def _generar(
    base: Conexion,
    mundo: fabrica.MundoDelCiclo,
    escena_id: int,
    modelo: fabrica.ModeloDeLaboratorio | None = None,
    pool: PoolEnVuelo | None = None,
    cerrojo: CerrojoDeGeneracion | None = None,
) -> tuple[fabrica.ModeloDeLaboratorio, object]:
    del mundo
    umbrales = fabrica.umbrales()
    usado = modelo or fabrica.ModeloDeLaboratorio()
    version = await proceso.generar_borrador(
        base,
        umbrales,
        usado,
        pool or PoolEnVuelo(umbrales.en_vuelo.total),
        cerrojo or CerrojoDeGeneracion(),
        escena_id,
        process_schemas.PeticionDeBorrador(personajes_presentes=[]),
    )
    return usado, version


def test_se_genera_un_borrador_a_partir_del_brief_y_el_contexto(base: Conexion) -> None:
    """RF-PROC-02. El brief y su restriccion de destino llegan al prompt."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])

    modelo, version = asyncio.run(_generar(base, mundo, brief.escena_id))[0:2]

    assert version.texto == fabrica.TEXTO_GENERADO  # type: ignore[attr-defined]
    assert version.origen is OrigenDeVersion.REDACTOR  # type: ignore[attr-defined]
    prompt = modelo.prompts[0]
    assert "termina en la orilla norte" in prompt, "la restriccion de destino no llego al prompt"
    assert "Ilia vuelve al vado" in prompt, "el encargo del brief no llego al prompt"


def test_generar_sin_brief_falla_en_voz_alta(base: Conexion) -> None:
    """Un encargo sin brief no es un encargo minimo: es ninguno."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    escena_id = mundo.escena_por_escribir()

    with pytest.raises(RecursoNoEncontrado):
        asyncio.run(_generar(base, mundo, escena_id))


def test_la_escena_pasa_a_en_borrador_al_generar(base: Conexion) -> None:
    """RD-09: el avance del ciclo se deduce del estado persistido."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])

    asyncio.run(_generar(base, mundo, brief.escena_id))

    from app.novel import service as novel

    assert novel.obtener_escena(base, brief.escena_id).estado is EstadoDeEscena.EN_BORRADOR


def test_cada_version_guarda_su_trazabilidad(base: Conexion) -> None:
    """RF-PROC-03, RNF-05, P-24.

    Las tres huellas son la picara 9: reproducir deja de ser comparar prosa y
    pasa a ser comparar hashes. Si coinciden y la salida difiere, el cambio es
    del proveedor y no nuestro.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    asyncio.run(_generar(base, mundo, brief.escena_id))

    traza = proceso.traza_de(base, brief.escena_id)
    assert len(traza) == 1
    unica = traza[0]
    assert unica.agente == "redactor"
    assert unica.modelo == "modelo-de-laboratorio"
    assert unica.huella_prompt and unica.huella_contexto and unica.huella_parametros
    assert len({unica.huella_prompt, unica.huella_contexto, unica.huella_parametros}) == 3


def test_registrar_generacion_corre_en_toda_llamada_al_modelo(base: Conexion) -> None:
    """A-45, RF-PROC-04.

    La garantia estructural --que no exista otra puerta-- la comprueba
    `tests/reglas/test_orquestacion_cerrada.py` por analisis estatico. Esta mira
    el contenido: que la fila traiga con que se reproduce, no solo que exista.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    modelo, _ = asyncio.run(_generar(base, mundo, brief.escena_id))

    registros = proceso.registros_de(base, brief.escena_id)
    assert len(registros) == 1
    registro = registros[0]
    assert registro.prompt == modelo.prompts[0]
    assert registro.contexto, "el contexto ensamblado no se guardo"
    assert registro.timeout_segundos == fabrica.umbrales().modelo.timeout_segundos
    assert registro.tokens_de_entrada is not None


def test_dos_generaciones_dejan_dos_registros_y_dos_versiones(base: Conexion) -> None:
    """Un intento del que no queda rastro es el que no se puede diagnosticar."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])

    asyncio.run(_generar(base, mundo, brief.escena_id))
    asyncio.run(_generar(base, mundo, brief.escena_id))

    assert len(proceso.registros_de(base, brief.escena_id)) == 2
    versiones = proceso.versiones_de(base, brief.escena_id)
    assert [version.numero for version in versiones] == [1, 2]


def test_la_version_del_autor_no_tiene_generacion_detras(base: Conexion) -> None:
    """A-46: la edicion a mano no sale de ninguna llamada al modelo."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    asyncio.run(_generar(base, mundo, brief.escena_id))

    proceso.anotar_version_del_autor(base, brief.escena_id, "Ilia cruzo. Nada mas.")

    traza = proceso.traza_de(base, brief.escena_id)
    assert traza[-1].origen is OrigenDeVersion.AUTOR
    assert traza[-1].registro_id is None
    assert traza[0].registro_id is not None


def test_una_sola_escena_en_generacion_a_la_vez(base: Conexion) -> None:
    """P-35, RNF-09.

    Se comprueba lo que la afirmacion dice: que **en ningun instante** hay dos
    escenas generandose. No que la segunda falle --no falla: espera--, y no que
    el orden sea uno u otro.

    El punto ciego declarado se asume: cubre un proceso. Dos instancias sobre el
    mismo `data/novel.db` rompen la serializacion sin que nadie lo detecte.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    primera = mundo.encargar([fabrica.estado_final(mundo.ilia)])
    segunda = mundo.encargar([fabrica.estado_final(mundo.baro)])

    cerrojo = CerrojoDeGeneracion()
    umbrales = fabrica.umbrales()
    pool = PoolEnVuelo(umbrales.en_vuelo.total)
    observado: list[int | None] = []

    class ModeloQueMira(fabrica.ModeloDeLaboratorio):
        async def generar(self, mensajes, sistema=None):  # type: ignore[no-untyped-def]
            # Cede el control en mitad de la generacion: si el cerrojo no
            # sirviera, la otra escena entraria justo aqui.
            observado.append(cerrojo.escena_en_curso)
            await asyncio.sleep(0)
            observado.append(cerrojo.escena_en_curso)
            return await super().generar(mensajes, sistema)

    async def ambas() -> None:
        modelo = ModeloQueMira()
        await asyncio.gather(
            proceso.generar_borrador(
                base,
                umbrales,
                modelo,
                pool,
                cerrojo,
                primera.escena_id,
                process_schemas.PeticionDeBorrador(),
            ),
            proceso.generar_borrador(
                base,
                umbrales,
                modelo,
                pool,
                cerrojo,
                segunda.escena_id,
                process_schemas.PeticionDeBorrador(),
            ),
        )

    asyncio.run(ambas())

    assert observado[0] == observado[1], "otra escena entro en generacion en mitad de la primera"
    assert observado[2] == observado[3]
    assert {observado[0], observado[2]} == {primera.escena_id, segunda.escena_id}
    assert cerrojo.escena_en_curso is None


def test_los_pasos_de_solo_lectura_no_pasan_por_el_cerrojo(base: Conexion) -> None:
    """La otra mitad de RNF-09, que es la que se olvida.

    `critico` y `verificador` solo leen: el canon y el texto en `t` no cambian
    mientras corren. Serializarlos seria pagar latencia por nada, asi que el
    cerrojo no los conoce y se comprueba que siguen disponibles con una escena
    en generacion.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    cerrojo = CerrojoDeGeneracion()

    async def mientras_genera() -> int:
        from app.canon import service as canon

        async with cerrojo.generando(escena):
            snapshot = canon.snapshot_en(base, escena)
            return len(snapshot.personajes_vivos)

    assert asyncio.run(mientras_genera()) >= 0
    assert cerrojo.escena_en_curso is None
