---
estado: archivada
aprobada-por:
fecha: 2026-09-22
archivada-el: 2026-09-23
archivada-porque: describe el sistema anterior (escenas, autor humano, deriva). No se implementa.
---

# Propuesta — la medida de `Deriva`

Cierra la pregunta abierta #1 de `verification.md` y desbloquea `RF-PROC-08` antes de H6.
**Es una propuesta, no un cambio**: `definitions.md` y `domain-knowledge.md` los edita el
autor desde el documento vivo (`AGENTS.md` § Canonicidad y sincronía). Aquí no se toca
ningún otro fichero.

---

## Lo que la ontología obliga a cambiar del diseño

El diseño pedido es correcto en su principio rector y en su estructura de vector. Tres
piezas chocan con reglas ya cerradas, y una propiedad propuesta codificaría un error.

### 1. Los beats no pueden ser elementos del plan

El diseño lista «beats» entre los elementos futuros. `AGENTS.md` § Modelo de autoría dice
**«no se planifican beats»**, y `definitions.md` clasifica `Beat` como *descubrimiento
libre*, con el texto generado como fuente de verdad. Un beat futuro no existe: no hay nada
que invalidar.

**Propuesta: se retiran.** No se pierde nada, porque lo que un beat aportaría al cálculo
—que la escena vaya a algún sitio— ya lo aporta su `Restricción de destino`.

### 2. Las precondiciones declaradas chocan con la regla de gobierno

El diseño quiere que los elementos futuros declaren precondiciones: entidades, estado,
ubicación, conocimiento, promesas abiertas. Pero `definitions.md` § Reglas de gobierno
cierra justo eso:

> Nada se declara por adelantado salvo las restricciones de destino; el resto del canon se
> extrae después de aceptar la escena.

Declarar precondiciones en los briefs futuros no es añadir un atributo: es **relajar el
modo de autoría híbrido**, que es una decisión de otra escala.

**Y no hace falta.** Tu propio principio rector lo resuelve: si la deriva mide el *hacia
dónde* y no el *cómo*, entonces la única superficie que puede derivar es exactamente la
que el esquema declara —la restricción de destino— y ninguna otra. El principio y la regla
de gobierno dicen lo mismo. La propuesta se ciñe a eso.

Lo que se pierde con la versión estrecha se enumera abajo, en «Viabilidad», y se propone
como atributo para *Filas pendientes de ontología*, no como parte de v1.

### 3. El «pago previsto» de una promesa no existe

`Promesa narrativa` tiene `escena de pago`, pero se rellena **al pagar**: es un hecho, no
un plan. `RF-CANON-13` lo confirma —toda escena que paga tiene apertura anterior— y la
pregunta de competencia 6 pregunta por las que *siguen sin pagar*. No hay ningún sitio
donde diga dónde se pensaba pagar.

**Propuesta:** el componente 3 no compara contra un pago previsto, sino contra la
existencia de **alguna** `Restricción de destino` futura de tipo `revelación` que pudiera
pagarla. Es más débil y es lo que hay.

### 4. «Desde la última replanificación» no tiene ancla en v1

`replanning/` queda fuera de v1 (spec §1.3), así que **no hay ninguna fila de
`Replanificación rodante` sobre la que anclar el acumulado**.

**Propuesta: el ancla es el `plan_hash`.** Una huella del conjunto de restricciones de
destino aún no escritas. Cambia cuando el autor edita el esquema a mano, que en v1 es la
única forma de replanificar. Es infraestructura de trazabilidad, no ontología —mismo
estatuto que el `Registro de generación`— y cuando entre `replanning/`, las filas de
`Replanificación rodante` se reconstruyen hacia atrás desde los cambios de huella.

### 5. La monotonía es falsa para dos de los tres componentes

La lista de propiedades pide «monótona entre replanificaciones». Eso es cierto de
`invalidación` y **falso por diseño** de los otros dos: pagar una promesa baja
`inviabilidad_pago`, y cerrar un hilo baja `canon_huérfano`. Son justo los movimientos que
la obra debe hacer para recoger su propio canon.

**Propuesta:** la monotonía se prueba solo sobre `invalidación`, y como control negativo se
prueba que los otros dos **sí** bajan cuando corresponde. Escribir la prueba como estaba
enunciada convertiría un acierto del sistema en un fallo.

---

## Texto propuesto para `definitions.md`

Sustituye la fila de `Deriva` en «Clases propias de este modo» y añade el bloque de prosa a
continuación de las reglas de gobierno.

**Fila:**

```markdown
| Deriva | Distancia acumulada entre lo escrito y el esquema vigente | medida (vector de tres componentes), umbral por componente, hito de plan desde el que se acumula |
```

**Prosa:**

```markdown
**Medida de la deriva.** La deriva no mide si el texto se parece al plan: mide si el plan
sigue describiendo la obra. Lo que una escena descubre —el *cómo*— no cuenta nunca; solo
cuenta lo que deja sin sostener al *hacia dónde*. Es un vector de tres componentes, sin
agregado escalar y sin similitud semántica:

- **Invalidación**: proporción de `Restricción de destino` aún no escritas cuyo tipo
  declarado contradice el canon vigente en `t` — un estado final ya imposible, una
  `Revelación` ya ocurrida o cuyo hecho fue refutado, un `Personaje` que no puede estar
  donde la restricción dice.
- **Canon huérfano**: `Hilo de trama` activos, `Promesa narrativa` pendientes y `Hallazgo`
  adoptados desde el último hito de plan que ninguna `Restricción de destino` futura
  recoge.
- **Inviabilidad de pago**: `Promesa narrativa` pendientes sin ninguna `Restricción de
  destino` futura que pudiera pagarlas, o cuya única candidata está invalidada.

Cada componente tiene su umbral y se compara por separado; superar uno dispara
`Replanificación rodante`. Los tres se calculan contra el canon en `t` y contra lo único
que el esquema declara del futuro, que es la restricción de destino: es la consecuencia
directa de «nada se declara por adelantado salvo las restricciones de destino».
```

---

## Viabilidad en v1

La superficie declarada del futuro es una sola —`Restricción de destino`— y de ella
dependen los tres componentes. No son tres huecos distintos: es el mismo, con tres efectos.

| Componente | ¿Calculable en v1? | Con qué |
| --- | --- | --- |
| **Invalidación** | **Sí, completo** | Los tres `tipo` de `Restricción de destino` son exactamente los tres que la pícara #5 ya sabe comprobar contra un `Snapshot de mundo`. Aquí se corren al revés: en vez de validar la salida de una escena escrita, se validan las restricciones no escritas contra el canon en `t` |
| **Canon huérfano** | **Parcial** | `Hilo de trama` activos, `Promesa narrativa` pendientes y `Hallazgo` adoptados se consultan ya (`RF-CANON-14`). Lo que falta es saber **qué entidades toca una restricción**: `alcance` existe pero su contenido no está especificado |
| **Inviabilidad de pago** | **Parcial** | Depende del mismo atributo. Sin él solo se puede contar promesas pendientes sin ninguna restricción futura de tipo `revelación`, sin saber si esa revelación es la suya |

**Propuesta para «Filas pendientes de ontología»:**

> Que `Restricción de destino` declare las entidades que toca. Hoy `alcance` existe sin
> contenido especificado. Mientras falte, `canon_huérfano` e `inviabilidad_pago` cuentan
> sobre el conjunto de restricciones futuras sin poder atribuir cuál recoge qué, y la
> deriva se queda en su forma débil.

**Una implicación de requisito que conviene ver ahora.** El componente 1 necesita que
existan restricciones de destino de escenas **aún no escritas**. `RF-PROC-01` crea un
`Brief de escena` con su restricción, pero nada obliga a materializarlas por adelantado. Si
el planificador solo crea el brief de la escena siguiente, el denominador es 1 y la medida
no dice nada. Si se aprueba esta propuesta, **`RF-PROC-01` necesita una frase**: el esquema
materializa las restricciones de destino de las escenas planificadas, no solo la de la
próxima.

---

## Modelo de datos del registro por escena

Sin migración todavía. Dos tablas, porque el requisito clave es que el histórico permita
recalcular **cualquier** definición futura sin regenerar nada: se guardan los ingredientes,
no solo el resultado.

**`deriva_medicion`** — una fila por escena aceptada.

| Columna | Qué guarda |
| --- | --- |
| `escena_id` | La escena aceptada tras la que se mide |
| `plan_hash` | Huella del conjunto de restricciones de destino no escritas. Es el ancla del acumulado y el detector de edición manual del plan |
| `invalidacion_num` / `invalidacion_den` | Numerador y denominador **por separado**: una proporción sola no se puede recalcular si cambia la definición del denominador |
| `canon_huerfano_num` / `canon_huerfano_den` | Ídem |
| `inviabilidad_num` / `inviabilidad_den` | Ídem |
| `definicion_version` | Qué versión de esta definición produjo la fila. Sin esto, un histórico mezclado no se puede leer |

**`deriva_ingrediente`** — N filas por medición. Es lo que hace el histórico recalculable.

| Columna | Qué guarda |
| --- | --- |
| `escena_id` | La medición a la que pertenece |
| `componente` | `invalidacion`, `canon_huerfano` o `inviabilidad_pago` |
| `tipo_elemento` | `restriccion_destino`, `hilo_trama`, `promesa_narrativa` o `hallazgo` |
| `elemento_id` | El id concreto |
| `motivo` | Qué precondición falla, o por qué está huérfano. Texto corto y enumerado, no prosa libre |
| `hecho_id` | El `Hecho canónico` que la contradice, cuando lo hay |

Con estas dos tablas, una definición nueva de la medida se recalcula sobre el histórico de
v1 con un `SELECT`: los elementos y sus motivos están, y lo único que cambia es cómo se
combinan.

---

## Propiedades a probar

Cinco, en el orden en que se escriben:

1. **Cero tras un hito de plan.** Recién cambiado el `plan_hash`, los tres componentes
   valen cero: el plan que el autor acaba de escribir describe la obra por construcción.
2. **No sube con una escena que cumple.** Una escena que satisface su restricción de
   destino y no establece hechos nuevos deja el vector igual. Es la prueba de que el
   descubrimiento del *cómo* no cuenta (`P-01`).
3. **Sube ante invalidación inyectada.** Con el fixture de abajo: matar al personaje que
   una restricción futura necesita mueve `invalidación` y nada más.
4. **Determinista.** Mismo canon en `t` y mismo `plan_hash` dan el mismo vector, siempre.
   Sin esto el histórico no vale para calibrar.
5. **Monótona solo `invalidación`**, entre hitos de plan y sin retcon de por medio. Y como
   control negativo: `canon_huérfano` **baja** cuando una escena cierra un hilo, e
   `inviabilidad_pago` **baja** cuando paga una promesa.

---

## Fixture de mutación de canon

Para calibrar después, y para la prueba 3. Cada mutación toca **un** componente y el resto
no se mueve: esa es la mitad del valor del fixture.

| Mutación | Qué debe mover |
| --- | --- |
| Matar a un `Personaje` que una restricción futura de tipo `posición de personaje` necesita | `invalidación` |
| Mover a ese personaje a un `Lugar` incompatible con la restricción | `invalidación` |
| Refutar el `Hecho canónico` que una restricción de tipo `revelación` iba a revelar | `invalidación` |
| Adoptar un `Hallazgo` que contradice una restricción de tipo `estado final` | `invalidación` |
| Abrir un `Hilo de trama` que ninguna restricción futura recoge | `canon_huérfano` |
| Abrir una `Promesa narrativa` sin ninguna restricción de tipo `revelación` futura | `inviabilidad_pago` |
| **Control negativo:** pagar una promesa pendiente | `inviabilidad_pago` **hacia abajo** |
| **Control negativo:** una escena que cumple su restricción sin hechos nuevos | nada |

---

## Plan de calibración: modo sombra

El umbral no se puede estimar y tampoco sale de mutar texto: sale de **tus decisiones**.

v1 registra el vector por escena aceptada y, además, **cuándo replanificas o editas briefs
a mano** —lo que en la práctica es cada cambio de `plan_hash`, con un motivo corto que
escribes tú—. Esas ediciones son las etiquetas: el umbral de un componente es el valor que
mejor separa «el autor replanificó en las siguientes `k` escenas» de «no lo hizo».

Tres consecuencias que conviene aceptar de antemano:

- **El umbral no existe hasta que haya suficientes ediciones.** Con dos o tres
  replanificaciones no hay nada que separar. `deriva.umbral` sigue en `null` y no dispara
  nada, que es lo que v1 ya hace.
- **Es un umbral tuyo, no del dominio.** Mide cuánta deriva toleras antes de mover el plan.
  Otro autor tendría otro, y eso está bien.
- **Va en `[histórico]` con etiquetas**, no en `[mutación]`: el fixture comprueba que la
  medida reacciona, no dónde hay que cortar.

---

## Puntos ciegos

**Deriva tonal o temática.** La medida es enteramente estructural. Una novela que cumple
todas sus restricciones de destino y ha dejado de ser el libro que querías escribir no
mueve ni un componente. Es exactamente el punto ciego **#7** de `verification.md` —«deriva
respecto a la premisa»—, y esta propuesta **no lo cierra**: lo delimita. Conviene no leer
un vector bajo como «la novela va bien».

**Plan poco declarado, y es el peligroso.** Un esquema que declara pocas restricciones
tiene un denominador diminuto, y uno que no declara ninguna tiene deriva **cero para
siempre**. La medida, tal cual, premia no planificar.

Contrapeso propuesto: una **densidad de declaración** que se registra junto al vector
—restricciones de destino declaradas por escena planificada aún no escrita— y que, por
debajo de su propio umbral, hace que la medición **se reporte como no fiable en vez de como
baja**. Una deriva de cero con densidad de cero no es una novela sana: es un plan que no
dice nada.

Esa densidad necesita su clave en `config/thresholds.yaml` y su fila en `verification.md`.
Va en el paso 2 si apruebas.

---

## Qué pasa si apruebas

Yo no toco `definitions.md` ni `domain-knowledge.md`. Tú pegas el texto de arriba en el
documento vivo y reexportas; cuando esté, propago a:

| Fichero | Qué cambia |
| --- | --- |
| `spec.md` | `RF-PROC-08` con el vector y el registro de ingredientes; `RF-PROC-01` con la frase de las restricciones materializadas por adelantado |
| `plan.md` | H6 con las pruebas de las cinco propiedades y el fixture; migración 006 con las dos tablas |
| `config/thresholds.yaml` | `deriva.medida` deja de ser `[bloqueado]`; tres umbrales por componente y el de densidad de declaración, todos en `null` |
| `verification.md` | `P-23` con validador y letra nuevos, punto ciego **#3** cerrado o estrechado, pregunta abierta **#1** a «Ya resueltas» con su fila, y la entrada de «Filas pendientes de ontología» sobre el `alcance` de `Restricción de destino` |

Ese paso usa la skill `plan-de-verificacion`, y te enseño el diff antes de cerrar nada.
