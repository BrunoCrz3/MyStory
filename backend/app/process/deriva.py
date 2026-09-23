"""La medida de la deriva (RF-PROC-08, RF-PROC-12, P-52, P-53).

**La deriva no mide si el texto se parece al plan: mide si el plan sigue
describiendo la obra.** Lo que una escena descubre --el *como*-- no cuenta
nunca; solo cuenta lo que deja sin sostener al *hacia donde*. Es un vector de
tres componentes, sin agregado escalar y sin similitud semantica.

Los tres se calculan contra el canon en `t` y contra lo unico que el esquema
declara del futuro, que es la `Restriccion de destino`. Es la consecuencia
directa de la regla de gobierno: nada se declara por adelantado salvo las
restricciones de destino.

## La forma debil, declarada

`Restriccion de destino` tiene `alcance` **sin contenido especificado** en la
ontologia, asi que no se puede saber que entidades toca cada restriccion. Sin
eso, «que ninguna restriccion futura recoge» no es decidible elemento a
elemento. Lo que si es decidible, y es lo que v1 cuenta, es el caso en que la
respuesta es **cierta**: un hilo o una promesa abiertos **despues** del ultimo
hito de plan no los recoge ninguna restriccion futura, porque todas se fijaron
antes de que existieran.

Es un subconjunto del numerador verdadero: cuenta de menos, nunca de mas. Y como
RF-PROC-12 guarda los ingredientes, el dia que `alcance` se especifique el
historico entero se recalcula sin regenerar nada.

Lo mismo con `inviabilidad_pago`: sin atribucion no se sabe que restriccion paga
que promesa, asi que se cuenta por palomar. Si hay `p` promesas pendientes y `c`
candidatas de pago vigentes, al menos `p - c` se quedan sin pagar. Es una cota
inferior, deterministra y sin modelo.

## Lo que esta medida no ve

Es enteramente estructural. Una novela que cumple todas sus restricciones de
destino y ha dejado de ser el libro que se queria escribir no mueve ni un
componente: es el punto ciego 7 de `verification.md`, que esta propuesta
delimita y no cierra. Un vector bajo no se lee como «la novela va bien».

Y el peligroso: un esquema que declara poco tiene el denominador diminuto, y uno
que no declara nada tiene deriva **cero para siempre**. La medida, a solas,
premia no planificar. El contrapeso es la densidad de declaracion, que por
debajo de su umbral hace que la medicion se reporte **no fiable** en vez de baja
(P-53).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.canon import service as canon
from app.canon.models import VALOR_VITAL_MUERTO, EstatusDeHecho
from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.findings import service as findings
from app.novel import service as novel
from app.process import repository
from app.process.models import (
    ComponenteDeDeriva,
    CuentaEn,
    Esquema,
    MotivoDeIngrediente,
    RestriccionDeDestino,
    TipoDeElemento,
    TipoDeRestriccion,
)

# Que version de la definicion produjo una fila. Sin esto, un historico con dos
# definiciones mezcladas no se puede leer.
DEFINICION_VERSION = 1


@dataclass(frozen=True)
class Proporcion:
    """Numerador y denominador por separado, siempre.

    Una proporcion sola no se puede recalcular si manana cambia la definicion
    del denominador, y eso es exactamente lo que RF-PROC-12 exige poder hacer.
    """

    numerador: int
    denominador: int

    @property
    def valor(self) -> float:
        """Denominador cero es cero, no indefinido.

        Un plan sin restricciones futuras no esta derivando: no dice nada. Que
        eso no se confunda con ir bien es trabajo de la densidad, no de aqui.
        """
        if self.denominador == 0:
            return 0.0
        return self.numerador / self.denominador


@dataclass(frozen=True)
class Ingrediente:
    componente: ComponenteDeDeriva
    tipo_elemento: TipoDeElemento
    elemento_id: int
    cuenta_en: CuentaEn
    motivo: MotivoDeIngrediente
    hecho_id: int | None = None


@dataclass(frozen=True)
class Medida:
    componentes: dict[ComponenteDeDeriva, Proporcion]
    densidad: Proporcion
    fiable: bool | None
    ingredientes: list[Ingrediente] = field(default_factory=list)


# --- Huella del plan ------------------------------------------------------


def huella_del_plan(restricciones: list[RestriccionDeDestino]) -> str:
    """Huella del conjunto de restricciones de destino que el esquema declara.

    Es el ancla del acumulado y el detector de edicion manual del plan: en v1
    editar el esquema a mano es la unica forma de replanificar, asi que cuando
    esta huella cambia es que alguien replanifico (RF-PROC-13).

    **Entran todas, escritas o no**, y no es un descuido. La propuesta hablaba
    del «conjunto de restricciones aun no escritas», pero ese conjunto se encoge
    por el simple hecho de escribir: con esa definicion, aceptar una escena
    moveria la huella igual que replanificar, y el hito dejaria de distinguir
    avanzar de cambiar de plan --que es lo unico para lo que sirve--. Lo que si
    mira solo lo no escrito es la medida, que es otra pregunta.

    No entra el `id`: lo que identifica al plan es lo que declara, no en que
    orden se insertaron sus filas. Asi, reescribir una restriccion identica no
    inventa un hito.
    """
    piezas = sorted(
        "|".join(
            (
                restriccion.tipo.value,
                restriccion.enunciado.strip(),
                restriccion.alcance or "",
                str(restriccion.personaje_id or ""),
                str(restriccion.lugar_id or ""),
                str(restriccion.hecho_id or ""),
                restriccion.valor or "",
            )
        )
        for restriccion in restricciones
    )
    return hashlib.sha256("\n".join(piezas).encode("utf-8")).hexdigest()


# --- Los tres componentes -------------------------------------------------


def medir(base: Conexion, umbrales: Umbrales, escena_id: int, hito: Esquema) -> Medida:
    """El vector completo tras aceptar `escena_id`, contra el canon en `t`.

    Es determinista: mismo canon en `t` y mismo `plan_hash` dan el mismo vector,
    siempre. Sin eso el historico no sirve para calibrar, que es para lo unico
    que v1 lo registra.
    """
    futuras = repository.restricciones_de_escenas_planificadas(base)

    ingredientes: list[Ingrediente] = []
    invalidacion = _invalidacion(base, escena_id, futuras, ingredientes)
    huerfano = _canon_huerfano(base, escena_id, hito, ingredientes)
    inviabilidad = _inviabilidad_de_pago(base, escena_id, futuras, ingredientes)
    densidad = Proporcion(
        numerador=len(futuras),
        denominador=repository.contar_escenas_planificadas(base),
    )

    minima = umbrales.deriva.densidad_declaracion_minima
    return Medida(
        componentes={
            ComponenteDeDeriva.INVALIDACION: invalidacion,
            ComponenteDeDeriva.CANON_HUERFANO: huerfano,
            ComponenteDeDeriva.INVIABILIDAD_PAGO: inviabilidad,
        },
        densidad=densidad,
        # Sin umbral declarado no hay juicio posible. `None` no es «fiable»: es
        # «nadie ha dicho todavia con que se compara», que es el estado de v1.
        fiable=None if minima is None else densidad.valor >= minima,
        ingredientes=ingredientes,
    )


def _invalidacion(
    base: Conexion,
    escena_id: int,
    futuras: list[RestriccionDeDestino],
    ingredientes: list[Ingrediente],
) -> Proporcion:
    """Restricciones futuras cuyo tipo declarado contradice el canon en `t`.

    Los tres tipos se corren aqui **al reves** que en la puerta de calidad: en
    vez de validar la salida de una escena escrita, se validan las restricciones
    no escritas contra el estado del mundo que ya existe.
    """
    muertos = personajes_muertos(base, escena_id)
    numerador = 0
    for restriccion in futuras:
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.INVALIDACION,
                tipo_elemento=TipoDeElemento.RESTRICCION_DESTINO,
                elemento_id=restriccion.id,
                cuenta_en=CuentaEn.DENOMINADOR,
                motivo=MotivoDeIngrediente.RESTRICCION_FUTURA_VIGENTE,
            )
        )
        motivo = contradice(base, restriccion, muertos, escena_id)
        if motivo is None:
            continue
        numerador += 1
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.INVALIDACION,
                tipo_elemento=TipoDeElemento.RESTRICCION_DESTINO,
                elemento_id=restriccion.id,
                cuenta_en=CuentaEn.NUMERADOR,
                motivo=motivo,
                hecho_id=restriccion.hecho_id,
            )
        )
    return Proporcion(numerador=numerador, denominador=len(futuras))


def contradice(
    base: Conexion, restriccion: RestriccionDeDestino, muertos: set[int], escena_id: int
) -> MotivoDeIngrediente | None:
    """Que precondicion de la restriccion ha dejado de ser posible, si alguna.

    Lo que **no** se comprueba, y conviene tenerlo escrito: que un personaje
    este hoy en un lugar distinto del que la restriccion pide **no** la
    invalida. Los personajes se mueven, y la ontologia no da topologia de
    `Lugar` con la que decidir que un desplazamiento es imposible. Lo que si
    invalida una posicion futura es que el personaje ya no pueda estar en
    ninguna parte.
    """
    if restriccion.hecho_id is not None:
        hecho = canon.obtener_hecho(base, restriccion.hecho_id)
        if hecho.estatus is EstatusDeHecho.REFUTADO:
            return MotivoDeIngrediente.HECHO_REFUTADO

    if restriccion.tipo is TipoDeRestriccion.POSICION_DE_PERSONAJE:
        if restriccion.personaje_id in muertos:
            return MotivoDeIngrediente.POSICION_IMPOSIBLE
        return None

    if restriccion.tipo is TipoDeRestriccion.ESTADO_FINAL:
        if restriccion.personaje_id in muertos and restriccion.valor != VALOR_VITAL_MUERTO:
            return MotivoDeIngrediente.ESTADO_FINAL_IMPOSIBLE
        return None

    # Revelacion. Se mira a quien se le iba a revelar: si ya lo sabe, la escena
    # que lo revelaba se quedo sin nada que revelar.
    #
    # El punto ciego esta declarado: con `destinatario` = lector no hay estado
    # epistemico del lector que consultar, asi que una revelacion ya filtrada al
    # lector no se detecta aqui.
    if restriccion.hecho_id is not None and restriccion.personaje_id is not None:
        sabidos = {
            epistemico.hecho_id
            for epistemico in canon.que_sabe(base, restriccion.personaje_id, escena_id)
        }
        if restriccion.hecho_id in sabidos:
            return MotivoDeIngrediente.REVELACION_YA_OCURRIDA
    return None


def _canon_huerfano(
    base: Conexion, escena_id: int, hito: Esquema, ingredientes: list[Ingrediente]
) -> Proporcion:
    """Canon abierto que el plan vigente no puede estar recogiendo.

    Denominador: todo el canon abierto en `t` --hilos de trama abiertos,
    promesas narrativas pendientes y hallazgos adoptados--. Numerador: los que
    aparecieron **despues** del ultimo hito de plan, que son los unicos de los
    que se puede afirmar con certeza que ninguna restriccion futura recoge.

    Un hallazgo adoptado cuenta desde la escena que lo revelo, no desde el dia
    en que el autor lo adopto: lo que el plan no pudo prever es que la escena lo
    descubriera, y adoptarlo tarde no lo vuelve previsible.
    """
    abiertos: list[tuple[TipoDeElemento, int, int]] = [
        (TipoDeElemento.HILO_DE_TRAMA, hilo.id, repository.apertura_de_hilo(base, hilo.id))
        for hilo in novel.hilos_abiertos(base)
    ]
    abiertos += [
        (
            TipoDeElemento.PROMESA_NARRATIVA,
            promesa.id,
            repository.apertura_de_promesa(base, promesa.id),
        )
        for promesa in canon.promesas_abiertas_en(base, escena_id)
    ]
    abiertos += [
        (
            TipoDeElemento.HALLAZGO,
            hallazgo.id,
            repository.posicion_de(base, hallazgo.escena_id),
        )
        for hallazgo in findings.adoptados(base)
    ]

    numerador = 0
    for tipo, elemento_id, apertura in abiertos:
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.CANON_HUERFANO,
                tipo_elemento=tipo,
                elemento_id=elemento_id,
                cuenta_en=CuentaEn.DENOMINADOR,
                motivo=MotivoDeIngrediente.CANON_ABIERTO,
            )
        )
        if apertura <= hito.posicion:
            continue
        numerador += 1
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.CANON_HUERFANO,
                tipo_elemento=tipo,
                elemento_id=elemento_id,
                cuenta_en=CuentaEn.NUMERADOR,
                motivo=MotivoDeIngrediente.ABIERTO_DESPUES_DEL_HITO,
            )
        )
    return Proporcion(numerador=numerador, denominador=len(abiertos))


def _inviabilidad_de_pago(
    base: Conexion,
    escena_id: int,
    futuras: list[RestriccionDeDestino],
    ingredientes: list[Ingrediente],
) -> Proporcion:
    """Promesas pendientes que no pueden pagarse con lo que el plan declara.

    `Promesa narrativa` tiene `escena de pago`, pero se rellena **al pagar**: es
    un hecho, no un plan. No hay ningun sitio donde diga donde se pensaba pagar,
    asi que la unica candidata que el esquema ofrece es una restriccion futura
    de tipo `revelacion` que siga vigente.

    Sin atribucion, se cuenta por palomar: cada candidata paga como mucho una
    promesa, luego al menos `pendientes - candidatas` se quedan sin pagar. Es
    mas debil que la definicion y es lo que hay; las candidatas se guardan como
    ingrediente para que el numerador se pueda recalcular.
    """
    pendientes = canon.promesas_abiertas_en(base, escena_id)
    muertos = personajes_muertos(base, escena_id)
    candidatas = [
        restriccion
        for restriccion in futuras
        if restriccion.tipo is TipoDeRestriccion.REVELACION
        and contradice(base, restriccion, muertos, escena_id) is None
    ]

    for promesa in pendientes:
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.INVIABILIDAD_PAGO,
                tipo_elemento=TipoDeElemento.PROMESA_NARRATIVA,
                elemento_id=promesa.id,
                cuenta_en=CuentaEn.DENOMINADOR,
                motivo=MotivoDeIngrediente.PROMESA_PENDIENTE,
            )
        )
    for candidata in candidatas:
        ingredientes.append(
            Ingrediente(
                componente=ComponenteDeDeriva.INVIABILIDAD_PAGO,
                tipo_elemento=TipoDeElemento.RESTRICCION_DESTINO,
                elemento_id=candidata.id,
                cuenta_en=CuentaEn.CANDIDATO,
                motivo=MotivoDeIngrediente.CANDIDATA_DE_PAGO,
            )
        )
    return Proporcion(
        numerador=max(0, len(pendientes) - len(candidatas)),
        denominador=len(pendientes),
    )


def personajes_muertos(base: Conexion, escena_id: int) -> set[int]:
    """Quien no puede aparecer ya en ninguna restriccion futura.

    Se mira el hecho vigente, no el snapshot: un personaje sin ningun hecho de
    estado vital tampoco aparece en `personajes_vivos`, y contarlo por muerto
    invalidaria media novela por no haberla contado todavia.
    """
    return {
        hecho.sujeto_personaje_id
        for hecho in canon.hechos_vigentes_en(base, escena_id)
        if hecho.valor == VALOR_VITAL_MUERTO and hecho.sujeto_personaje_id is not None
    }


# --- Recalculo desde los ingredientes (RF-PROC-12) ------------------------


def recalcular(ingredientes: list[Ingrediente]) -> dict[ComponenteDeDeriva, Proporcion]:
    """El vector, reconstruido **solo** desde los ingredientes guardados.

    Es la prueba de que el historico sirve para algo: si esto no diera lo mismo
    que las columnas, el dia que la definicion cambie habria que regenerar la
    obra entera para recalcularla, y regenerarla es justo lo que no se puede
    hacer.

    Cada componente se reconstruye como lo construyo `medir`. `inviabilidad_pago`
    no tiene numerador guardado porque no se puede atribuir: se deduce del
    palomar, con las candidatas que si estan guardadas.
    """

    def cuantos(componente: ComponenteDeDeriva, cuenta_en: CuentaEn) -> int:
        return len(
            [
                ingrediente
                for ingrediente in ingredientes
                if ingrediente.componente is componente and ingrediente.cuenta_en is cuenta_en
            ]
        )

    pendientes = cuantos(ComponenteDeDeriva.INVIABILIDAD_PAGO, CuentaEn.DENOMINADOR)
    candidatas = cuantos(ComponenteDeDeriva.INVIABILIDAD_PAGO, CuentaEn.CANDIDATO)
    return {
        ComponenteDeDeriva.INVALIDACION: Proporcion(
            numerador=cuantos(ComponenteDeDeriva.INVALIDACION, CuentaEn.NUMERADOR),
            denominador=cuantos(ComponenteDeDeriva.INVALIDACION, CuentaEn.DENOMINADOR),
        ),
        ComponenteDeDeriva.CANON_HUERFANO: Proporcion(
            numerador=cuantos(ComponenteDeDeriva.CANON_HUERFANO, CuentaEn.NUMERADOR),
            denominador=cuantos(ComponenteDeDeriva.CANON_HUERFANO, CuentaEn.DENOMINADOR),
        ),
        ComponenteDeDeriva.INVIABILIDAD_PAGO: Proporcion(
            numerador=max(0, pendientes - candidatas),
            denominador=pendientes,
        ),
    }
