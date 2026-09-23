"""Critica y continuidad. Los dos agentes de lectura del ciclo corto.

`critico` y `verificador` corren **en paralelo** sobre la misma escena porque
solo leen (`architecture.md` § Paralelo y serie, RNF-09). Aqui eso se traduce en
algo mas simple de lo que suena: ninguna funcion de este modulo escribe fuera de
`quality/`, y el informe se guarda al final, de una vez.

**El registro de validadores es uno y el camino que lo recorre tambien.** Eso es
A-49: no existe una via que revalide «solo lo que fallo», asi que no hay nada
que olvidar tras una correccion. El punto ciego declarado se asume: garantiza
que se invoquen todos, no que cada uno reciba el texto corregido en vez de una
puntuacion en cache.
"""

from __future__ import annotations

from collections.abc import Callable

from app.commons import errores
from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.novel import models as novel_models
from app.novel import service as novel
from app.quality import continuidad, dimensiones, higiene, repository, schemas, voz
from app.quality.dimensiones import Aportacion
from app.quality.higiene import Fallo
from app.quality.models import NIVELES_LOCALES, AlcanceDelDefecto, InformeDeCritica

Validador = Callable[[Conexion, schemas.PeticionDeCritica], Aportacion]

# El registro. Anadir una dimension es anadir un validador aqui, y el camino
# unico lo recorre entero. No hay segunda lista.
VALIDADORES: tuple[Validador, ...] = (
    dimensiones.validar_continuidad,
    dimensiones.validar_voz_narrativa,
    dimensiones.validar_distintividad,
    dimensiones.validar_prosa,
    dimensiones.validar_carga_expositiva,
    dimensiones.validar_cumplimiento_del_brief,
    dimensiones.validar_lo_que_v1_no_puede_medir,
)


def verificar_continuidad(
    base: Conexion, peticion: schemas.PeticionDeCritica
) -> list[schemas.DefectoDetectado]:
    """`verificar-continuidad`, la skill del sistema que usa el `verificador`."""
    return continuidad.verificar(base, peticion)


def verificar_voz_narrativa(
    base: Conexion, peticion: schemas.PeticionDeCritica
) -> list[schemas.DefectoDetectado]:
    return voz.verificar(base, peticion)


# --- Puerta de higiene ----------------------------------------------------


def puerta_de_higiene(
    base: Conexion, umbrales: Umbrales, texto: str, escena_id: int
) -> schemas.ResultadoDeHigiene:
    """A-47, RF-QUA-06. Determinista, sin modelo y antes de la critica."""
    del escena_id
    fallos: list[str] = []
    no_evaluables: list[str] = []

    comprobaciones: tuple[tuple[Fallo, bool], ...] = (
        (Fallo.METATEXTO, higiene.metatexto(texto)),
        (Fallo.RECHAZO, higiene.rechazo(texto)),
        (Fallo.TRUNCAMIENTO, higiene.truncamiento(texto)),
        (Fallo.PLACEHOLDER, higiene.placeholder(texto)),
        (Fallo.IDIOMA, higiene.idioma_ajeno(texto)),
        (Fallo.FORMATO, higiene.formato_roto(texto)),
    )
    fallos += [fallo.value for fallo, ocurre in comprobaciones if ocurre]

    larga = higiene.longitud_fuera_de_objetivo(
        texto,
        _extension_objetivo(base),
        _escenas_de_la_obra(base),
        umbrales.higiene.desviacion_longitud_escena,
    )
    if larga is None:
        no_evaluables.append(Fallo.LONGITUD.value)
    elif larga:
        fallos.append(Fallo.LONGITUD.value)

    return schemas.ResultadoDeHigiene(pasa=not fallos, fallos=fallos, no_evaluables=no_evaluables)


def _extension_objetivo(base: Conexion) -> int | None:
    try:
        return novel.obtener_obra(base).extension_objetivo
    except errores.RecursoNoEncontrado:
        return None


def _escenas_de_la_obra(base: Conexion) -> int:
    return len(novel.listar(base, novel_models.Escena))


# --- Critica --------------------------------------------------------------


def criticar(
    base: Conexion, umbrales: Umbrales, peticion: schemas.PeticionDeCritica
) -> schemas.Critica:
    """RF-QUA-02 a RF-QUA-06. El unico camino que produce un `Informe de critica`."""
    resultado = puerta_de_higiene(base, umbrales, peticion.texto, peticion.escena_id)
    if not resultado.pasa:
        raise errores.BorradorNoHigienico(
            f"el borrador no pasa la puerta de higiene: {resultado.fallos}"
        )

    medidas: dict[str, dimensiones.Medida] = {}
    detectados: list[schemas.DefectoDetectado] = []
    for validador in VALIDADORES:
        aportacion = validador(base, peticion)
        medidas.update(aportacion.puntuaciones)
        detectados.extend(aportacion.defectos)

    declaradas = set(umbrales.calidad.model_dump())
    faltan = declaradas - set(medidas)
    if faltan:
        raise errores.DimensionSinValidador(
            f"ninguna validacion puntuo {sorted(faltan)}: el informe estaria incompleto"
        )

    fase_de_medicion = not umbrales.medicion.cerrar_el_paso
    puntuaciones = [
        _puntuar(nombre, medidas[nombre], umbrales, fase_de_medicion)
        for nombre in sorted(declaradas)
    ]
    defectos = [(detectado, alcance_de(detectado.dimension)) for detectado in detectados]

    informe_id = repository.guardar_informe(
        base,
        peticion,
        fase_de_medicion,
        repository.escenas_aceptadas(base),
        puntuaciones,
        defectos,
    )
    return _leer(base, informe_id)


def _puntuar(
    nombre: str, medida: dimensiones.Medida, umbrales: Umbrales, fase_de_medicion: bool
) -> schemas.Puntuacion:
    """RF-QUA-05.

    En fase de medicion no se compara con nada: el umbral no se pide, asi que un
    `null` no hace fallar el arranque y la puntuacion solo se registra. Quien
    acepta la escena es el autor, no el umbral (RF-PROC-07).
    """
    if fase_de_medicion:
        return schemas.Puntuacion(
            dimension=nombre,
            valor=medida.valor,
            umbral=None,
            suspende=False,
            motivo=medida.motivo,
        )
    umbral = umbrales.para_cerrar_el_paso(f"calidad.{nombre}")
    suspende = medida.valor is not None and medida.valor < umbral
    return schemas.Puntuacion(
        dimension=nombre,
        valor=medida.valor,
        umbral=umbral,
        suspende=suspende,
        motivo=medida.motivo,
    )


def _leer(base: Conexion, informe_id: int) -> schemas.Critica:
    informe = repository.obtener_informe(base, informe_id)
    return schemas.Critica(
        id=informe.id,
        escena_id=informe.escena_id,
        version=informe.version,
        fase_de_medicion=informe.fase_de_medicion,
        escenas_aceptadas=informe.escenas_aceptadas,
        puntuaciones=repository.puntuaciones_de(base, informe_id),
        defectos=repository.defectos_de(base, informe_id),
    )


# --- Clasificacion del defecto --------------------------------------------

# El nivel de aplicacion sale de la Capa 4 y se siembra en la migracion 005.
# Esta copia existe porque clasificar un defecto no deberia necesitar la base;
# que las dos digan lo mismo lo comprueba `test_los_niveles_del_codigo_y_de_la
# _migracion_coinciden`.
NIVEL_POR_DIMENSION: dict[str, str] = {
    "consistencia_factica": "Escena",
    "consistencia_temporal": "Obra",
    "consistencia_espacial": "Capítulo",
    "consistencia_epistemica": "Escena",
    "plausibilidad_especulativa": "Escena",
    "distintividad_de_voz": "Escena",
    "calidad_de_prosa": "Frase",
    "mostrar_vs_contar": "Escena",
    "integridad_de_pov": "Escena",
    "causalidad": "Capítulo",
    "ritmo": "Parte",
    "carga_expositiva": "Escena",
    "originalidad": "Obra",
    "cumplimiento_del_brief": "Escena",
}


def nivel_de(dimension: str) -> str:
    return NIVEL_POR_DIMENSION[dimension]


def alcance_de(dimension: str) -> AlcanceDelDefecto:
    """P-29, RF-QUA-04.

    La regla sale de la columna «Nivel» de la Capa 4 y no de un criterio propio:
    lo que se mide en la frase o en la escena se corrige reescribiendo en sitio;
    lo que se mide en la obra, la parte o el capitulo invalida la planificacion.

    El punto ciego declarado se asume y pesa: sin etiquetas del autor, cualquier
    clasificador mide acuerdo consigo mismo. Derivarla de la ontologia es lo mas
    cerca que se puede estar de no inventarsela.
    """
    return (
        AlcanceDelDefecto.LOCAL
        if nivel_de(dimension) in NIVELES_LOCALES
        else AlcanceDelDefecto.SISTEMICO
    )


# --- Historial ------------------------------------------------------------


def informes_de(base: Conexion, escena_id: int) -> list[InformeDeCritica]:
    return repository.informes_de(base, escena_id)


def comparar_con_anterior(base: Conexion, escena_id: int, version: int) -> list[schemas.Regresion]:
    """A-50, RF-QUA-08: ninguna correccion empeora lo que ya pasaba.

    El punto ciego declarado se asume y pesa: compara puntuaciones, y ninguna
    esta calibrada. Dos valores igual de arbitrarios no dicen si la escena
    mejoro; lo que si dicen es si la correccion movio hacia abajo algo que antes
    estaba mas arriba.
    """
    actual = repository.informe_de(base, escena_id, version)
    anterior = repository.informe_anterior(base, escena_id, version)
    if actual is None or anterior is None:
        return []

    antes = {p.dimension: p.valor for p in repository.puntuaciones_de(base, anterior.id)}
    ahora = {p.dimension: p.valor for p in repository.puntuaciones_de(base, actual.id)}

    regresiones: list[schemas.Regresion] = []
    for dimension, valor_anterior in antes.items():
        valor_nuevo = ahora.get(dimension)
        if valor_anterior is None or valor_nuevo is None or valor_nuevo >= valor_anterior:
            continue
        regresiones.append(
            schemas.Regresion(
                dimension=dimension,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                version_anterior=anterior.version,
            )
        )
    return regresiones
