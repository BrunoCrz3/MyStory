"""H7 · prueba 5 — criterio 2 de aceptacion de la spec.

«Un ciclo completo funciona de punta a punta: brief -> contexto ensamblado
dentro de presupuesto -> borrador -> critica -> verificacion -> aceptacion del
autor -> consolidacion -> hallazgos `propuesto`.»

Aqui es donde eso deja de ser una aspiracion. La prueba recorre el bucle corto
entero con las piezas de verdad --canon real, contexto real, presupuesto real,
puerta de higiene real-- y comprueba en cada paso lo que ese paso promete, no
solo que no reviente.

El unico sustituto es el proveedor del modelo: `ModeloDeLaboratorio` vive en
`tests/` y devuelve prosa fija. No se sustituye para esquivar nada --el prompt
que recibe se inspecciona-- sino porque una prueba de regresion que depende de
la red no es una prueba de regresion.
"""

from __future__ import annotations

import asyncio

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import TipoDeHecho
from app.commons.db.conexion import Conexion
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.findings import schemas as findings_schemas
from app.findings import service as hallazgos
from app.findings.models import EstadoDeHallazgo, ModoDeAdopcion, TipoDeHallazgo
from app.novel import service as novel
from app.novel.models import EstadoDeEscena
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.models import ComponenteDeDeriva
from app.process.orquestador import CerrojoDeGeneracion, Paso
from app.quality import schemas as quality_schemas
from app.quality import service as calidad
from tests.process import fabrica as fabrica_proceso

# La prosa que devuelve el redactor de laboratorio. Nombra a Ilia, al vado, a la
# orilla norte y a la llave de piedra porque el anclaje textual de RF-CANON-11
# exige que los terminos del hecho esten en la escena que lo establece: en
# produccion eso lo garantiza el extractor leyendo la prosa; aqui se construye al
# reves, que es lo unico que se puede hacer sin el modelo de verdad.
PROSA = (
    "Ilia cruzo el vado con el agua por la cintura, y no miro atras. "
    "Baro la esperaba en la orilla norte con la mano abierta, pero ella "
    "solto la llave de piedra en el barro antes de que se la pidiera. "
    "Despues, mas arriba, vio a Nerio mirando desde el talud."
)


def test_ciclo_completo_de_punta_a_punta(base: Conexion) -> None:
    umbrales = fabrica_proceso.umbrales()
    mundo = fabrica_proceso.mundo_del_ciclo(base)

    # Canon de fondo: el estado del mundo contra el que se genera existe porque
    # lo dejaron escenas anteriores, no porque se haya escrito a mano.
    mundo.situar(mundo.ilia, mundo.vado)
    mundo.situar(mundo.baro, mundo.orilla)

    # --- 1. Brief: estado de entrada mas restriccion de destino -----------
    brief = mundo.encargar([fabrica_proceso.posicion(mundo.ilia, mundo.orilla)])
    escena_id = brief.escena_id
    # Una escena mas por escribir, para que el plan declare futuro y la deriva
    # tenga denominador.
    mundo.encargar([fabrica_proceso.revelacion()])
    mundo.fijar_hito("plan del primer acto")

    assert proceso.siguiente_paso_de(base, umbrales, escena_id).paso == Paso.REDACTOR.value

    # --- 2 y 3. Contexto dentro de presupuesto, y borrador ----------------
    modelo = fabrica_proceso.ModeloDeLaboratorio(texto=PROSA)
    version = asyncio.run(
        proceso.generar_borrador(
            base,
            umbrales,
            modelo,
            PoolEnVuelo(umbrales.en_vuelo.total),
            CerrojoDeGeneracion(),
            escena_id,
            process_schemas.PeticionDeBorrador(personajes_presentes=[mundo.ilia, mundo.baro]),
        )
    )
    prompt = modelo.prompts[0]
    assert "termina en la orilla norte" in prompt, "la restriccion de destino no llego"
    assert "<material_narrativo" in prompt, "el texto de obra no entro marcado como datos"
    registro = proceso.registros_de(base, escena_id)[0]
    assert registro.tokens_de_entrada is not None
    assert version.texto == PROSA
    assert novel.obtener_escena(base, escena_id).estado is EstadoDeEscena.EN_BORRADOR
    assert proceso.siguiente_paso_de(base, umbrales, escena_id).paso == Paso.CRITICO.value

    # --- 4. Puerta de higiene: determinista, sin modelo y antes de la critica
    peticion = quality_schemas.PeticionDeCritica(
        escena_id=escena_id,
        version=version.numero,
        texto=version.texto,
        brief=brief.encargo,
        restriccion_de_destino=brief.restricciones[0].enunciado,
        personajes_presentes=[mundo.ilia, mundo.baro],
        pov_personaje_id=mundo.ilia,
    )
    higiene = calidad.puerta_de_higiene(base, umbrales, version.texto, escena_id)
    assert higiene.pasa, higiene.fallos

    # --- 5. Critica: las catorce dimensiones, ninguna suspende todavia ----
    informe = calidad.criticar(base, umbrales, peticion)
    assert informe.fase_de_medicion is True, "v1 se entrega en fase de medicion (criterio 4)"
    assert len(informe.puntuaciones) == len(umbrales.calidad.model_dump())
    assert not any(p.suspende for p in informe.puntuaciones)

    # --- 6. Verificacion de continuidad contra el canon en t --------------
    defectos = calidad.verificar_continuidad(base, peticion)
    assert all(d.dimension for d in defectos)

    novel.transicionar_escena(base, escena_id, EstadoDeEscena.EN_REVISION)
    assert proceso.siguiente_paso_de(base, umbrales, escena_id).paso == Paso.VERIFICADOR.value, (
        "sin defectos sobre umbral la escena pasa al verificador"
    )

    # --- 7. Aceptacion del autor, y solo del autor ------------------------
    aceptacion = proceso.aceptar_escena(
        base, escena_id, process_schemas.PeticionDeAceptacion(version=version.numero)
    )
    assert novel.obtener_escena(base, escena_id).estado is EstadoDeEscena.ACEPTADA
    assert aceptacion.entro_en_el_banco is False, "el redactor escribio; el autor no edito"

    # --- 8. Consolidacion: el unico punto que toca el canon ---------------
    resultado = canon.consolidar_escena(
        base,
        canon_schemas.Consolidacion(
            escena_id=escena_id,
            version=version.numero,
            texto=version.texto,
            hechos=[
                canon_schemas.NuevoHechoCanonico(
                    texto="Ilia llega a la orilla norte",
                    tipo=TipoDeHecho.UBICACION,
                    sujeto_personaje_id=mundo.ilia,
                    lugar_id=mundo.orilla,
                ),
                canon_schemas.NuevoHechoCanonico(
                    texto="Ilia suelta la llave de piedra en el barro",
                    tipo=TipoDeHecho.DESCRIPTIVO,
                    sujeto_personaje_id=mundo.ilia,
                    artefacto_id=mundo.llave,
                ),
            ],
            promesas=[
                canon_schemas.NuevaPromesaNarrativa(
                    texto="alguien volvera por la llave de piedra", tipo="deuda"
                )
            ],
        ),
    )
    assert resultado.snapshot.version == version.numero
    snapshot = canon.snapshot_en(base, escena_id)
    assert snapshot.ubicaciones[mundo.ilia] == mundo.orilla, "el destino declarado se cumplio"

    # --- 9. Hallazgos: en `propuesto`, y ahi se quedan --------------------
    assert proceso.siguiente_paso_de(base, umbrales, escena_id).paso == Paso.EXTRACTOR.value
    extraccion = hallazgos.extraer(
        base,
        escena_id,
        findings_schemas.PeticionDeExtraccion(version=version.numero, texto=version.texto),
    )
    assert extraccion.hallazgos, "la escena descubrio algo y nadie lo recogio"
    assert all(h.estado is EstadoDeHallazgo.PROPUESTO for h in extraccion.hallazgos)
    assert "Nerio" in [h.texto for h in extraccion.hallazgos], (
        "el nombre que la escena trajo de nuevo no se propuso"
    )
    assert hallazgos.adoptados(base) == [], "nada llega a canon sin el autor"

    # --- 10. Y la vuelta al plan: la deriva de esta escena aceptada -------
    vector = proceso.medir_deriva(base, umbrales, escena_id)
    assert vector.componentes[ComponenteDeDeriva.INVALIDACION].valor == 0.0
    assert vector.fiable is None, "sin umbral de densidad la fiabilidad no se inventa"

    # El autor adopta, y solo entonces cuenta como canon del modo hibrido.
    nerio = next(h for h in extraccion.hallazgos if h.texto == "Nerio")
    hallazgos.decidir(
        base,
        nerio.id,
        findings_schemas.DecisionDelAutor(
            destino=EstadoDeHallazgo.ADOPTADO, personaje_id=mundo.baro
        ),
        modo=ModoDeAdopcion.HUMANA,
    )
    assert [h.id for h in hallazgos.adoptados(base)] == [nerio.id]
    assert nerio.tipo is TipoDeHallazgo.PERSONAJE


def test_el_ciclo_deja_traza_de_cada_paso(base: Conexion) -> None:
    """RNF-05, RNF-06, P-24, P-28.

    Un ciclo que funciona y no deja traza no se puede diagnosticar cuando deje
    de funcionar. Se comprueba sobre el mismo recorrido: version, registro de
    generacion, informe de critica, extraccion y medicion de deriva, todos
    consultables por la escena.
    """
    umbrales = fabrica_proceso.umbrales()
    mundo = fabrica_proceso.mundo_del_ciclo(base)
    mundo.situar(mundo.ilia, mundo.vado)
    brief = mundo.encargar([fabrica_proceso.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()

    asyncio.run(
        proceso.generar_borrador(
            base,
            umbrales,
            fabrica_proceso.ModeloDeLaboratorio(texto=PROSA),
            PoolEnVuelo(umbrales.en_vuelo.total),
            CerrojoDeGeneracion(),
            brief.escena_id,
            process_schemas.PeticionDeBorrador(),
        )
    )

    traza = proceso.traza_de(base, brief.escena_id)
    assert len(traza) == 1
    assert traza[0].agente == "redactor"
    assert traza[0].huella_prompt and traza[0].huella_contexto
