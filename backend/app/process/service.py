"""El ciclo de produccion: encargo, generacion, trazabilidad y deriva.

Tres reglas gobiernan este modulo, y ninguna es negociable:

1. **`registrar-generacion` corre en toda llamada al modelo, sin excepcion**
   (A-45, RF-PROC-04). La garantia no es acordarse de llamarla: es que exista
   **una sola puerta** que llame al modelo, y que esa puerta escriba la fila
   antes de devolver nada. `_generar_con_registro` es esa puerta, y
   `tests/reglas/test_orquestacion_cerrada.py` comprueba por analisis estatico
   que no hay otra.
2. **Solo el autor humano acepta una escena** (RF-PROC-07, P-19). El
   guardarrail esta en `novel/`, que es quien escribe el estado; aqui esta la
   puerta por la que el autor firma, y es la unica del sistema que pasa
   `ModoDeAceptacion.HUMANA`.
3. **El avance se deduce del estado persistido**, no de variables en memoria ni
   de la pila de llamadas (RD-09). Ninguna funcion de aqui guarda en que punto
   del ciclo va una escena: lo pregunta.

Lo que **no** hace v1 y conviene no buscar: no encola. La cola es sincrona y en
proceso (RD-05), y las dos condiciones de arriba son justo lo que hara que
insertarla mas adelante no toque a ningun agente.
"""

from __future__ import annotations

import hashlib
import json

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import VALOR_VITAL_MUERTO
from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.commons.errores import (
    BriefSinRestriccionDeDestino,
    DerivaSoloDeEscenaAceptada,
    PlanCambiadoSinHito,
    RecursoNoEncontrado,
)
from app.commons.llm.cliente import Generador
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.context import schemas as context_schemas
from app.context import service as contexto
from app.novel import service as novel
from app.novel.models import EstadoDeEscena, ModoDeAceptacion
from app.process import deriva, models, repository, schemas
from app.process.deriva import DEFINICION_VERSION
from app.process.models import (
    ComponenteDeDeriva,
    OrigenDeVersion,
    RestriccionDeDestino,
    TipoDeRestriccion,
)
from app.process.orquestador import CerrojoDeGeneracion, Paso, siguiente_paso
from app.quality import schemas as quality_schemas
from app.quality import service as quality
from app.quality.models import AlcanceDelDefecto

AGENTE_REDACTOR = "redactor"


# --- Esquema: los hitos de plan (RF-PROC-13) ------------------------------


def fijar_hito(base: Conexion, datos: schemas.NuevoHito) -> models.Esquema:
    """Registra el plan vigente con el motivo por el que el autor lo movio.

    En v1 editar el esquema a mano es la unica forma de replanificar, asi que
    cada fila de estas es una etiqueta del modo sombra: el umbral de un
    componente de deriva sera el valor que mejor separe «replanifico en las
    siguientes k escenas» de «no lo hizo». Sin motivo no hay etiqueta.
    """
    futuras = repository.restricciones_de_escenas_planificadas(base)
    return repository.insertar_hito(
        base,
        plan_hash=deriva.huella_del_plan(futuras),
        motivo=datos.motivo,
        posicion=repository.ultima_posicion_aceptada(base),
    )


def hitos(base: Conexion) -> list[models.Esquema]:
    return repository.hitos(base)


def esquema_declarado(base: Conexion) -> schemas.EsquemaDeclarado:
    """Que declara hoy el plan del futuro, y si alguien lo movio sin decirlo."""
    futuras = repository.restricciones_de_escenas_planificadas(base)
    huella = deriva.huella_del_plan(futuras)
    hito = repository.ultimo_hito(base)
    return schemas.EsquemaDeclarado(
        plan_hash=huella,
        restricciones_futuras=len(futuras),
        escenas_planificadas=repository.contar_escenas_planificadas(base),
        hito_vigente=None if hito is None else hito.id,
        coincide_con_el_hito=hito is not None and hito.plan_hash == huella,
    )


# --- Brief de escena (RF-PROC-01) -----------------------------------------


def crear_brief(base: Conexion, datos: schemas.NuevoBrief) -> schemas.BriefCompleto:
    """Minimo: estado de entrada mas restriccion de destino. Sin beats.

    `Beat` es descubrimiento libre y su fuente de verdad es el texto generado.
    Planificarlos aqui seria cambiar el modo de autoria desde un formulario.
    """
    novel.obtener_escena(base, datos.escena_id)
    if not datos.restricciones:
        raise BriefSinRestriccionDeDestino(
            f"el brief de la escena {datos.escena_id} no declara ninguna restriccion de "
            "destino: la escena descubriria tambien hacia donde va"
        )
    brief = repository.insertar_brief(base, datos)
    return _brief_completo(base, brief)


def brief_de(base: Conexion, escena_id: int) -> schemas.BriefCompleto:
    brief = repository.brief_de_escena(base, escena_id)
    if brief is None:
        raise RecursoNoEncontrado(f"la escena {escena_id} no tiene brief")
    return _brief_completo(base, brief)


def _brief_completo(base: Conexion, brief: models.BriefDeEscena) -> schemas.BriefCompleto:
    return schemas.BriefCompleto(
        id=brief.id,
        escena_id=brief.escena_id,
        estado_de_entrada=brief.estado_de_entrada,
        encargo=brief.encargo,
        restricciones=[
            schemas.NuevaRestriccion(
                tipo=restriccion.tipo,
                enunciado=restriccion.enunciado,
                alcance=restriccion.alcance,
                personaje_id=restriccion.personaje_id,
                lugar_id=restriccion.lugar_id,
                hecho_id=restriccion.hecho_id,
                valor=restriccion.valor,
            )
            for restriccion in repository.restricciones_de(base, brief.id)
        ],
    )


# --- La unica puerta que llama al modelo (A-45, RF-PROC-04) ---------------


async def _generar_con_registro(
    base: Conexion,
    umbrales: Umbrales,
    modelo: Generador,
    pool: PoolEnVuelo,
    *,
    agente: str,
    escena_id: int | None,
    ensamblado: context_schemas.ContextoEnsamblado,
    semilla: str | None,
) -> tuple[str, models.RegistroDeGeneracion]:
    """Pide texto al modelo y deja la fila que permite reproducirlo.

    Aqui pasan, en este orden, las cuatro cosas que el sistema promete:

    1. **Admision.** El trabajo no arranca sin presupuesto libre del pool en
       vuelo. La estimacion es el tamano del contexto ensamblado mas el margen,
       que es la reserva declarada para la respuesta: no se suma dos veces.
    2. **La llamada**, asincrona y con timeout explicito, que el cliente de
       `commons/` ya garantiza.
    3. **El registro**, con modelo, prompt, contexto y semilla, mas las tres
       huellas de la picara 9. Se escribe **siempre**, tambien cuando la salida
       no sirva: un intento fallido del que no queda rastro es el que no se
       puede diagnosticar.
    4. La devolucion del texto, que es prosa y se guarda como prosa. Nada de lo
       que devuelve el modelo se ejecuta ni se interpreta como instruccion.
    """
    estimacion = ensamblado.total + umbrales.contexto.capas.margen
    async with pool.admitir(estimacion):
        respuesta = await modelo.generar([{"role": "user", "content": ensamblado.prompt}])

    parametros = json.dumps(
        {
            "modelo": umbrales.modelo.id,
            "timeout_segundos": umbrales.modelo.timeout_segundos,
            "max_tokens": umbrales.contexto.capas.margen,
            "semilla": semilla,
        },
        sort_keys=True,
    )
    serializado = json.dumps(
        [pieza.model_dump(mode="json") for pieza in ensamblado.piezas], sort_keys=True
    )
    registro = repository.insertar_registro(
        base,
        schemas.NuevoRegistro(
            escena_id=escena_id,
            agente=agente,
            modelo=respuesta.modelo,
            prompt=ensamblado.prompt,
            contexto=serializado,
            semilla=semilla,
            huella_prompt=_huella(ensamblado.prompt),
            huella_contexto=_huella(serializado),
            huella_parametros=_huella(parametros),
            tokens_de_entrada=respuesta.tokens_de_entrada,
            tokens_de_salida=respuesta.tokens_de_salida,
            timeout_segundos=umbrales.modelo.timeout_segundos,
        ),
    )
    return respuesta.texto, registro


def _huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# --- Borrador y version (RF-PROC-02, RF-PROC-03) --------------------------


async def generar_borrador(
    base: Conexion,
    umbrales: Umbrales,
    modelo: Generador,
    pool: PoolEnVuelo,
    cerrojo: CerrojoDeGeneracion,
    escena_id: int,
    datos: schemas.PeticionDeBorrador,
) -> models.Version:
    """El `redactor`: brief mas contexto ensamblado, y sale una version.

    Corre bajo el cerrojo de generacion porque escribe sobre el borrador de la
    escena: una sola escena en generacion a la vez (RNF-09). Los pasos de solo
    lectura --critico, verificador, las skills de `context/`-- no pasan por
    aqui y siguen corriendo en paralelo.

    El agente recibe su entrada y devuelve su salida. No sabe quien lo llamo ni
    que viene despues, no espera, no reintenta y no consulta ninguna cola
    (RD-08): eso es lo que hara que insertar la cola no le toque.
    """
    brief = brief_de(base, escena_id)
    async with cerrojo.generando(escena_id):
        ensamblado = contexto.ensamblar(base, umbrales, _peticion_de_ensamblado(brief, datos))
        texto, registro = await _generar_con_registro(
            base,
            umbrales,
            modelo,
            pool,
            agente=AGENTE_REDACTOR,
            escena_id=escena_id,
            ensamblado=ensamblado,
            semilla=datos.semilla,
        )
        borrador = repository.insertar_borrador(base, brief.id, escena_id, texto, registro.id)
        version = repository.insertar_version(
            base, escena_id, texto, OrigenDeVersion.REDACTOR, borrador.id
        )
    escena = novel.obtener_escena(base, escena_id)
    if escena.estado is EstadoDeEscena.PLANIFICADA:
        novel.transicionar_escena(base, escena_id, EstadoDeEscena.EN_BORRADOR)
    return version


def _peticion_de_ensamblado(
    brief: schemas.BriefCompleto, datos: schemas.PeticionDeBorrador
) -> context_schemas.PeticionDeEnsamblado:
    """La restriccion de destino va entera y no se degrada nunca.

    La politica de recuperacion filtra por las entidades que el **brief**
    declara, no por similitud semantica generica: esta ultima trae fragmentos
    parecidos en tono e irrelevantes en estado.
    """
    entidades = [
        context_schemas.Referencia(tipo="personaje", id=personaje)
        for personaje in datos.personajes_presentes
    ]
    for restriccion in brief.restricciones:
        if restriccion.personaje_id is not None:
            entidades.append(
                context_schemas.Referencia(tipo="personaje", id=restriccion.personaje_id)
            )
        if restriccion.lugar_id is not None:
            entidades.append(context_schemas.Referencia(tipo="lugar", id=restriccion.lugar_id))

    return context_schemas.PeticionDeEnsamblado(
        escena_id=brief.escena_id,
        brief=brief.encargo or brief.estado_de_entrada,
        restriccion_de_destino="\n".join(
            restriccion.enunciado for restriccion in brief.restricciones
        ),
        entidades=entidades,
        personajes_presentes=datos.personajes_presentes,
        guia_de_estilo=datos.guia_de_estilo,
    )


def anotar_version_del_autor(base: Conexion, escena_id: int, texto: str) -> models.Version:
    """La edicion a mano. No sale de ninguna llamada al modelo y por eso no
    tiene borrador ni registro detras: es el autor escribiendo."""
    novel.obtener_escena(base, escena_id)
    return repository.insertar_version(base, escena_id, texto, OrigenDeVersion.AUTOR, None)


def versiones_de(base: Conexion, escena_id: int) -> list[models.Version]:
    return repository.versiones_de(base, escena_id)


def traza_de(base: Conexion, escena_id: int) -> list[schemas.VersionConTraza]:
    """RNF-05, RNF-06, P-24, P-28: la trayectoria, reconstruida.

    Que exista la traza no la hace legible: sin una consulta que la reconstruya
    nadie la mira hasta que hay un problema. Esta es esa consulta.
    """
    trazas: list[schemas.VersionConTraza] = []
    for version in repository.versiones_de(base, escena_id):
        registro = None
        if version.borrador_id is not None:
            borrador = repository.obtener_borrador(base, version.borrador_id)
            registro = repository.obtener_registro(base, borrador.registro_id)
        trazas.append(
            schemas.VersionConTraza(
                escena_id=version.escena_id,
                numero=version.numero,
                origen=version.origen,
                creada_en=version.creada_en,
                registro_id=None if registro is None else registro.id,
                agente=None if registro is None else registro.agente,
                modelo=None if registro is None else registro.modelo,
                huella_prompt=None if registro is None else registro.huella_prompt,
                huella_contexto=None if registro is None else registro.huella_contexto,
                huella_parametros=None if registro is None else registro.huella_parametros,
                semilla=None if registro is None else registro.semilla,
            )
        )
    return trazas


def registros_de(base: Conexion, escena_id: int) -> list[models.RegistroDeGeneracion]:
    return repository.registros_de(base, escena_id)


# --- Orquestacion (RF-PROC-05, RF-PROC-06) --------------------------------


def siguiente_paso_de(base: Conexion, umbrales: Umbrales, escena_id: int) -> schemas.PasoSugerido:
    """Lee el estado de la escena y devuelve lo que toca. Nada mas.

    Todo lo que entra en la decision sale de la base: el estado de la escena, el
    informe de critica vigente y cuantas iteraciones de revision lleva. No hay
    ninguna variable de proceso, y por eso reiniciar la instancia no pierde el
    punto del ciclo.

    **Que es un defecto «sobre umbral».** Uno cuya dimension suspende en el
    informe. En fase de medicion ninguna suspende, asi que no hay defectos sobre
    umbral y la escena pasa siempre al `verificador`: las rutas de defecto local
    y sistemico las abre el autor al leer el informe, no el umbral. Cuando la
    fase se cierre, la misma condicion vuelve a leerse tal cual, sin tocar esto.
    """
    escena = novel.obtener_escena(base, escena_id)
    informes = quality.informes_de(base, escena_id)
    critica = quality.ultima_critica(base, escena_id)
    tope = umbrales.orquestacion.max_iteraciones_revision

    paso = siguiente_paso(
        escena.estado,
        alcance_del_peor_defecto=_peor_alcance(critica),
        hay_informe=critica is not None,
        iteraciones_de_revision=len(informes),
        max_iteraciones_revision=tope,
    )
    return schemas.PasoSugerido(
        escena_id=escena_id,
        estado=escena.estado.value,
        paso=paso.value,
        iteraciones_de_revision=len(informes),
        max_iteraciones_revision=tope,
    )


def _peor_alcance(critica: quality_schemas.Critica | None) -> AlcanceDelDefecto | None:
    if critica is None:
        return None
    suspendidas = {
        puntuacion.dimension for puntuacion in critica.puntuaciones if puntuacion.suspende
    }
    alcances = {defecto.alcance for defecto in critica.defectos if defecto.dimension in suspendidas}
    if AlcanceDelDefecto.SISTEMICO in alcances:
        return AlcanceDelDefecto.SISTEMICO
    if AlcanceDelDefecto.LOCAL in alcances:
        return AlcanceDelDefecto.LOCAL
    return None


# --- Aceptacion y banco de ejemplos (RF-PROC-07, RF-PROC-09) --------------


def aceptar_escena(
    base: Conexion, escena_id: int, datos: schemas.PeticionDeAceptacion
) -> schemas.Aceptacion:
    """La firma del autor. Es la unica puerta del sistema que acepta una escena.

    Y la unica que escribe en `training_samples`, con la condicion de A-46: solo
    entra texto aceptado **y editado**, es decir, una version cuyo origen es el
    autor. No se pregunta si edito --una casilla se marca sola--: se mira quien
    dejo el texto que se acepta.

    **Que la muestra no entre nunca impide aceptar.** El banco es un
    recolector, no una puerta: quedarse sin ejemplo cuesta un ejemplo, y
    bloquear la aceptacion cuesta la escena. El motivo sale en la respuesta para
    que el autor sepa por que no entro y no tenga que deducirlo del recuento.
    """
    version = repository.version_numero(base, escena_id, datos.version)
    if version is None:
        raise RecursoNoEncontrado(f"la escena {escena_id} no tiene la version {datos.version}")

    novel.transicionar_escena(
        base,
        escena_id,
        EstadoDeEscena.ACEPTADA,
        modo_de_aceptacion=ModoDeAceptacion.HUMANA,
    )

    motivo = _por_que_no_entra_en_el_banco(base, escena_id, version)
    if motivo is not None:
        return schemas.Aceptacion(
            escena_id=escena_id,
            version=version.numero,
            entro_en_el_banco=False,
            motivo=motivo,
        )

    _guardar_muestra(base, escena_id, version)
    return schemas.Aceptacion(
        escena_id=escena_id,
        version=version.numero,
        entro_en_el_banco=True,
        motivo="texto aceptado y editado por el autor",
    )


def _por_que_no_entra_en_el_banco(
    base: Conexion, escena_id: int, version: models.Version
) -> str | None:
    """Las tres razones por las que una version aceptada no sirve de ejemplo.

    La primera es la regla (A-46); las otras dos son que falte la mitad del par
    entrada/salida. Un ejemplo sin el encargo ni el contexto del que salio no
    ensena nada: es una salida suelta.
    """
    if version.origen is not OrigenDeVersion.AUTOR:
        return (
            f"la version la dejo el {version.origen.value} y el autor no la edito: entrenar "
            "sobre la propia salida del sistema amplifica la regresion a la media"
        )
    if repository.brief_de_escena(base, escena_id) is None:
        return "la escena no tiene brief: sin el encargo, la muestra no tiene entrada"
    if not repository.registros_de(base, escena_id):
        return (
            "la escena no tiene ninguna generacion registrada: sin el contexto ensamblado, "
            "la muestra no tiene entrada"
        )
    return None


def _guardar_muestra(base: Conexion, escena_id: int, version: models.Version) -> None:
    brief = brief_de(base, escena_id)
    registros = repository.registros_de(base, escena_id)
    repository.insertar_muestra(
        base,
        schemas.NuevaMuestra(
            escena_id=escena_id,
            version_id=version.id,
            brief=brief.model_dump_json(),
            contexto=registros[-1].contexto,
            texto_aceptado=version.texto,
        ),
    )


def muestras_recogidas(base: Conexion) -> int:
    return repository.contar_muestras(base)


# --- Deriva (RF-PROC-08, RF-PROC-12) --------------------------------------


def medir_deriva(base: Conexion, umbrales: Umbrales, escena_id: int) -> schemas.VectorDeDeriva:
    """Mide y registra el vector tras aceptar una escena.

    Se exige un hito de plan vigente, y que la huella del plan de hoy coincida
    con la suya. Si no coincide, alguien movio el esquema sin decir por que: el
    acumulado se quedaria sin ancla y la etiqueta con la que se calibra el
    umbral, sin escribir (RF-PROC-13). Fallar aqui es barato; descubrirlo al
    calibrar, no.

    Es idempotente por escena: volver a medir sobre el mismo canon y el mismo
    plan reescribe la misma fila con el mismo contenido.
    """
    escena = novel.obtener_escena(base, escena_id)
    if escena.estado is not EstadoDeEscena.ACEPTADA:
        raise DerivaSoloDeEscenaAceptada(
            f"la escena {escena_id} esta en '{escena.estado.value}': la deriva se mide contra "
            "el canon en t, y el canon solo existe tras consolidar una escena aceptada"
        )

    hito = repository.ultimo_hito(base)
    if hito is None:
        raise PlanCambiadoSinHito(
            "no hay ningun hito de plan fijado: sin el, «desde la ultima replanificacion» "
            "no tiene ancla y la deriva no se puede acumular"
        )
    huella = deriva.huella_del_plan(repository.restricciones_de_escenas_planificadas(base))
    if huella != hito.plan_hash:
        raise PlanCambiadoSinHito(
            "el conjunto de restricciones de destino no coincide con el del ultimo hito: "
            "fija un hito nuevo con su motivo antes de medir"
        )

    medida = deriva.medir(base, umbrales, escena_id, hito)
    guardada = repository.guardar_medicion(base, escena_id, hito, _guardable(medida))
    return _vector(umbrales, guardada)


def deriva_de(base: Conexion, umbrales: Umbrales, escena_id: int) -> schemas.VectorDeDeriva:
    return _vector(umbrales, repository.obtener_medicion(base, escena_id))


def historico(base: Conexion, umbrales: Umbrales) -> list[schemas.VectorDeDeriva]:
    return [_vector(umbrales, medicion) for medicion in repository.mediciones(base)]


def recalcular_deriva(
    base: Conexion, escena_id: int
) -> dict[ComponenteDeDeriva, schemas.Componente]:
    """RF-PROC-12: el vector, reconstruido **solo** desde los ingredientes.

    Si esto no diera lo mismo que las columnas, el historico de v1 no serviria
    para el unico uso que tiene: recalcularlo con la definicion de manana.
    """
    ingredientes = [
        deriva.Ingrediente(
            componente=guardado.componente,
            tipo_elemento=guardado.tipo_elemento,
            elemento_id=guardado.elemento_id,
            cuenta_en=guardado.cuenta_en,
            motivo=guardado.motivo,
            hecho_id=guardado.hecho_id,
        )
        for guardado in repository.ingredientes_de(base, escena_id)
    ]
    return {
        componente: schemas.Componente(
            numerador=proporcion.numerador,
            denominador=proporcion.denominador,
            valor=proporcion.valor,
        )
        for componente, proporcion in deriva.recalcular(ingredientes).items()
    }


def _guardable(medida: deriva.Medida) -> schemas.MedidaGuardable:
    invalidacion = medida.componentes[ComponenteDeDeriva.INVALIDACION]
    huerfano = medida.componentes[ComponenteDeDeriva.CANON_HUERFANO]
    inviabilidad = medida.componentes[ComponenteDeDeriva.INVIABILIDAD_PAGO]
    return schemas.MedidaGuardable(
        invalidacion_num=invalidacion.numerador,
        invalidacion_den=invalidacion.denominador,
        canon_huerfano_num=huerfano.numerador,
        canon_huerfano_den=huerfano.denominador,
        inviabilidad_num=inviabilidad.numerador,
        inviabilidad_den=inviabilidad.denominador,
        densidad_num=medida.densidad.numerador,
        densidad_den=medida.densidad.denominador,
        fiable=medida.fiable,
        definicion_version=DEFINICION_VERSION,
        ingredientes=[
            schemas.IngredienteGuardado(
                componente=ingrediente.componente,
                tipo_elemento=ingrediente.tipo_elemento,
                elemento_id=ingrediente.elemento_id,
                cuenta_en=ingrediente.cuenta_en,
                motivo=ingrediente.motivo,
                hecho_id=ingrediente.hecho_id,
            )
            for ingrediente in medida.ingredientes
        ],
    )


def _vector(umbrales: Umbrales, medicion: models.Deriva) -> schemas.VectorDeDeriva:
    umbrales_por_componente = {
        ComponenteDeDeriva.INVALIDACION: umbrales.deriva.umbral.invalidacion,
        ComponenteDeDeriva.CANON_HUERFANO: umbrales.deriva.umbral.canon_huerfano,
        ComponenteDeDeriva.INVIABILIDAD_PAGO: umbrales.deriva.umbral.inviabilidad_pago,
    }
    crudos = {
        ComponenteDeDeriva.INVALIDACION: (medicion.invalidacion_num, medicion.invalidacion_den),
        ComponenteDeDeriva.CANON_HUERFANO: (
            medicion.canon_huerfano_num,
            medicion.canon_huerfano_den,
        ),
        ComponenteDeDeriva.INVIABILIDAD_PAGO: (
            medicion.inviabilidad_num,
            medicion.inviabilidad_den,
        ),
    }
    componentes: dict[ComponenteDeDeriva, schemas.Componente] = {}
    for componente, (numerador, denominador) in crudos.items():
        proporcion = deriva.Proporcion(numerador=numerador, denominador=denominador)
        umbral = umbrales_por_componente[componente]
        componentes[componente] = schemas.Componente(
            numerador=numerador,
            denominador=denominador,
            valor=proporcion.valor,
            umbral=umbral,
            # Con el umbral en null no dispara nada, y eso es lo que v1 hace:
            # registrar para poder calibrar despues. Ver `config/thresholds.yaml`.
            supera_el_umbral=None if umbral is None else proporcion.valor > umbral,
        )

    densidad = deriva.Proporcion(numerador=medicion.densidad_num, denominador=medicion.densidad_den)
    return schemas.VectorDeDeriva(
        escena_id=medicion.escena_id,
        plan_hash=medicion.plan_hash,
        definicion_version=medicion.definicion_version,
        componentes=componentes,
        densidad=schemas.Componente(
            numerador=densidad.numerador,
            denominador=densidad.denominador,
            valor=densidad.valor,
            umbral=umbrales.deriva.densidad_declaracion_minima,
        ),
        fiable=medicion.fiable,
        medido_en=medicion.medido_en,
    )


# --- Adelanto al plan (RF-PROC-11, P-41) ----------------------------------


def adelantos(base: Conexion, escena_id: int) -> list[RestriccionDeDestino]:
    """Restricciones de briefs **posteriores** que la escena ya satisface.

    La escena descubre *como*, no *hacia donde*. Satisfacer el destino de la
    N+k desde la N no es adelantar trabajo: es cambiar el plan desde dentro de
    una escena, que es justo lo que la replanificacion existe para hacer fuera.

    Es el mismo cotejo de la picara 5 corrido hacia adelante, sin modelo de por
    medio. Solo ve lo declarado --los tres `tipo` y sus columnas cotejables--:
    adelantar algo que el esquema no escribio no es detectable, y esta escrito.

    En v1 el resultado es informacion para el autor: con `replanning/` fuera, el
    orquestador escala y replanifica una persona.
    """
    snapshot = canon.snapshot_en(base, escena_id)
    establecidos = {hecho.id for hecho in canon.hechos_establecidos_en(base, escena_id)}
    muertos = deriva.personajes_muertos(base, escena_id)
    return [
        restriccion
        for restriccion in repository.restricciones_posteriores_a(base, escena_id)
        if _satisfecha(restriccion, snapshot, establecidos, muertos)
    ]


def _satisfecha(
    restriccion: RestriccionDeDestino,
    snapshot: canon_schemas.SnapshotDerivado,
    establecidos: set[int],
    muertos: set[int],
) -> bool:
    if restriccion.tipo is TipoDeRestriccion.POSICION_DE_PERSONAJE:
        if restriccion.personaje_id is None or restriccion.lugar_id is None:
            return False
        return snapshot.ubicaciones.get(restriccion.personaje_id) == restriccion.lugar_id

    if restriccion.tipo is TipoDeRestriccion.REVELACION:
        # La revelacion se adelanto si el hecho que iba a revelar lo establece ya
        # esta escena.
        return restriccion.hecho_id is not None and restriccion.hecho_id in establecidos

    # Estado final. Solo cuenta el irreversible, y la asimetria es deliberada:
    # que un personaje siga vivo hoy no adelanta un «termina vivo» --le quedan
    # todas las escenas para morirse--, mientras que muerto ya no vuelve, asi
    # que un «termina muerto` cumplido ahora se cumplio antes de tiempo.
    if restriccion.personaje_id is None or restriccion.valor != VALOR_VITAL_MUERTO:
        return False
    return restriccion.personaje_id in muertos


__all__ = [
    "Paso",
    "aceptar_escena",
    "adelantos",
    "anotar_version_del_autor",
    "brief_de",
    "crear_brief",
    "deriva_de",
    "esquema_declarado",
    "fijar_hito",
    "generar_borrador",
    "historico",
    "hitos",
    "medir_deriva",
    "muestras_recogidas",
    "recalcular_deriva",
    "registros_de",
    "siguiente_paso_de",
    "traza_de",
    "versiones_de",
]
