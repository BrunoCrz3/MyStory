---
estado: en-revision
aprobada-por:
fecha: 2026-09-25
---

# Spec 4 — Verificación formal de la cronología con Lean

Mini-spec de RF-EXP-03 (`specs/spec1.md` § 3.10), el único requisito de Lean que quedó
`[post-demo]`. Aquí no se redefine vocabulario: es el de `docs/definitions.md`; la
arquitectura, la de `docs/architecture.md` § Verificación formal; las aserciones, las de
`docs/verification.md` (A-90, A-91, O-13, O-14, O-15, P-81, P-82, P-83).

> **Estado: en revisión.** Las tres preguntas de § 7 están respondidas por el desarrollador
> (2026-09-25) e incorporadas. Las decisiones están en TO-064 a TO-067 y en RI-037, y la
> ontología ya está actualizada en `docs/definitions.md`. No hay plan hasta que la apruebe.

---

## 1. Problema

El alcance (§ 5c) pide generar desde la story bible un fichero Lean con los hechos
temporales, demostrar al menos dos invariantes con `lake build`, no publicar si falla
—devolviendo el fallo al editor— y enseñar un caso real que solo Lean detecta. Hoy la
toolchain está (Lean 4.34.1, Lake 5.0.0 en `~/.elan/bin`, I-03) y el timeout tiene valor
provisional (26 s), pero **no hay generador** y `formal.gate_activo` está en `false`: la demo
publica versiones sin demostración de cronología.

**Lo que la story bible real contiene hoy** (base de la demo, comprobado el 2026-09-25):

| Dato que Lean necesita | Estado |
| --- | --- |
| `evento.momento` | Siempre relleno: capítulo × 100 + orden (A-35). Es el **orden de narración** |
| Lugar y personajes presentes | `evento.lugar_id` y `evento_personaje` |
| `personaje.fecha_nacimiento` | Solo el destinatario, copiada del brief |
| Año de la historia del evento | **No existe** |
| Edad declarada en un evento | **No existe** |
| `evento_excluyente` | Tabla creada, **0 filas**: nadie la escribe |
| Versión del evento | **No existe**: una regeneración añade eventos sin cerrar los del capítulo sustituido (momentos duplicados en el capítulo 5 de la novela regenerada) |

## 2. Objetivo

Que ninguna versión se publique sin que Lean demuestre las cuatro invariantes sobre **su**
cronología, que el fallo llegue al editor con el evento culpable nombrado, y que el caso del
brief de incoherencia temporal de la evaluación quede documentado como el que solo Lean
detecta.

## 3. Alcance

**Dentro**

1. **Ontología y esquema** (TO-064, TO-065, TO-066; ya en `docs/definitions.md`). Migración
   `0016`:
   - `evento.anio` (entero, nulo si el texto no lo dice) y `evento_personaje.edad` (entero,
     nulo si el texto no la dice);
   - `evento.version_desde` y `evento.version_hasta`, con el patrón de vigencia del `Hecho`
     (TO-028). La migración rellena los eventos existentes a partir de `version_capitulo`;
     una regeneración cierra los eventos del capítulo sustituido y abre los del nuevo; la
     reversión de una candidata rechazada (TO-062) revierte también sus eventos. Toda
     consulta de eventos lleva `novel_id` y `version`, sin valor por defecto.
2. **Extractor.** Su esquema de salida gana `anio` por evento, `edad` por personaje presente
   y una lista de eventos excluyentes (personaje y tipo `muerte` | `partida`). Los tres
   **solo cuando el texto lo dice explícitamente**; el prompt lo ordena y los tres son
   opcionales en el esquema, así que un hueco es un nulo y nunca un valor supuesto. El
   cambio pasa por `presupuesto-de-contexto`.
3. **Generador determinista** `.lean` desde la story bible de una versión (`novel_id`,
   `version`): lee los eventos vigentes en esa versión, ordenados por `(momento, id)`, con
   sus personajes, edades, lugar, año, eventos excluyentes y fechas de nacimiento. Misma
   story bible, mismo fichero byte a byte (A-90). **Sin Mathlib** ni ninguna dependencia de
   Lake (A-91). **Los textos libres no entran** en el fichero: los identificadores Lean son
   sintéticos (`e017`, `p3`, `l2`), el tipo `Option Nat` lleva los huecos, y un comentario
   de cabecera enlaza cada identificador con su UUID. El texto del comprador nunca llega al
   compilador (regla 11).
4. **Un proyecto Lake fijo** en `formal/lean/` con los tipos y los predicados decidibles
   escritos a mano, y un módulo de hechos que el generador escribe en un directorio temporal
   por ejecución (copia del proyecto), nunca en el árbol versionado. Una ejecución no pisa a
   otra.
5. **Cuatro invariantes**, cada una una familia de teoremas con **un teorema por evento**
   (o por par de eventos en la ubicación), cerrados con `by decide`, para que el nombre del
   teorema que falla identifique el evento. **Dos ordenaciones, cada una para lo suyo**: el
   `momento` solo en la ubicación, el `año` en las otras tres. Ninguna invariante compara un
   orden con el otro, así que **una analepsis no es una incoherencia**.

   | Score | Aserción | Orden | Enunciado |
   | --- | --- | --- | --- |
   | `lean_ubicacion` | O-14 | narración (`momento`) | Ningún personaje está en dos lugares distintos en el mismo `momento` |
   | `lean_cronologia` | O-13 | historia (`año`) | Ningún personaje participa en un evento de año **estrictamente posterior** al de un evento excluyente suyo |
   | `lean_edad` | O-15 | historia (`año`) | Si un evento declara la edad de un personaje con fecha de nacimiento, esa edad es `año − año de nacimiento` o uno menos (sin día ni mes en el evento, el cumpleaños puede no haber llegado) |
   | `lean_nacimiento` | O nueva | historia (`año`) | Ningún personaje participa en un evento de año **anterior** al de su nacimiento; para el destinatario, la fecha de nacimiento del brief |

   Un dato vacío (evento sin año, personaje sin nacimiento, edad no declarada) hace la
   comprobación **vacuamente cierta** para ese evento. El informe cuenta cuántos eventos
   quedaron sin comprobar por invariante: una demostración sobre nada no se presenta como
   demostración. Mismo año en la exclusión o en el nacimiento no es violación: sin más
   precisión, no se puede afirmar.
6. **Gate de publicación**: con `formal.gate_activo: true`, `versioning` genera el fichero de
   la candidata, ejecuta `lake build` con `formal.lean_timeout_segundos` y devuelve cuatro
   `VeredictoGate`. Un teorema fallido, un error de compilación, un timeout o una toolchain
   ausente hacen fallar el gate: la candidata queda `rechazada`, la generación sale por
   `GateEnRojo` con el detalle traducido (invariante, capítulo, evento y personaje), que es el
   camino por el que el resto del gate ya vuelve al editor, y ninguna versión publicada
   cambia (TO-062, regla 16).
7. **Chequeo incremental por capítulo** (TO-016, P-81): con `formal.lean_incremental: true`,
   tras consolidar un capítulo aceptado se verifica la cronología hasta él. Es un **aviso**:
   emite los cuatro scores con `etapa = incremental`, deja una entrada en el audit log y no
   cambia el estado de nada. Un fallo de toolchain en el incremental también es aviso,
   nunca excepción.
8. **Scores en Langfuse** (regla 13): los cuatro, 0–1 con 1 = demostrado, en la traza de la
   generación con el detalle como comentario, y un span `lean` por ejecución con duración,
   tamaño del fichero y eventos sin comprobar. `lean_nacimiento` entra en el registro de
   validadores (`quality/registro.py`) y en `verification.md` con una O nueva.
9. **Medir `lean_timeout_segundos`** con el fichero real más grande, desde cero
   (`lake clean`), y fijarlo con el criterio de I-03 (≈ 10 × lo medido), anotando la medida.
10. **Prueba sobre datos reales en una copia** (TO-067): se copia la base, se vuelven a
    extraer con el extractor nuevo los capítulos de la versión 3 publicada de la novela de la
    demo **en la copia**, y se pasa Lean. La story bible real no se toca (regla 2). Lo que
    salga se documenta, sea verde o rojo.
11. **El caso real que se presenta es el del brief B2** de la evaluación (`verification.md`
    § Evaluación: el destinatario conoce a alguien en un año anterior a la fecha de
    nacimiento que el mismo brief declara). Se genera una novela real con ese brief, con el
    gate activo, y se documenta en `docs/red-team.md` la versión, el evento, la salida de
    `lake build` y los veredictos del resto de validadores sobre la misma versión. Las reglas
    de la entrevista solo cruzan edad y fecha de nacimiento, no los años de los recuerdos,
    así que B2 no se detiene antes de escribir. Antes de lanzar se comprueba el tope de
    coste de `specs/progreso.md`. **Si hace falta construir un caso a mano** —porque B2 no
    llega a Lean o porque otro validador lo caza antes—, se dice así y el caso construido se
    presenta **marcado como provocado**.
12. `GET /salud` pasa a decir `gate_lean_activo: true`. Se actualizan `verification.md`,
    `architecture.md` § Lean (el timeout ya no es `null`), `registro-iteraciones.md`, la lista
    post-demo de `specs/progreso.md` y la marca `[post-demo]` de RF-EXP-03.

**Fuera**

- Demostraciones generales para cualquier cronología (alcance § 7): se comprueban
  cronologías concretas.
- Coste de desplazamiento entre lugares (PO-11): sigue siendo punto ciego de O-14.
- Fechas con día y mes: el evento solo lleva año (TO-064).
- Volver a extraer las versiones publicadas en la base real: solo en la copia.
- TLA+ (§ 5d), que es otra spec.

## 4. Requisitos

**RF-LEAN-01** · Dado `(novel_id, version)`, el sistema deberá generar un fichero `.lean`
determinista, sin importaciones fuera de `formal/lean/` ni texto libre de la base, con solo
los eventos vigentes en esa versión.

**RF-LEAN-02** · El sistema deberá declarar las invariantes `lean_ubicacion`,
`lean_cronologia`, `lean_edad` y `lean_nacimiento` con un teorema por evento o par, y
comprobarlas con `lake build` dentro de `formal.lean_timeout_segundos`.

**RF-LEAN-03** · Con `formal.gate_activo: true`, el gate no deberá publicar una candidata
cuyo `lake build` falle, exceda el timeout o no pueda ejecutarse, y el detalle del
`GateEnRojo` deberá nombrar invariante, capítulo, evento y personaje de cada teorema fallido.

**RF-LEAN-04** · Con `formal.lean_incremental: true`, tras aceptar un capítulo el sistema
deberá comprobar la cronología hasta él y registrar el resultado como aviso sin bloquear.

**RF-LEAN-05** · Toda ejecución de Lean deberá emitir un span y los cuatro scores en Langfuse.

**RF-LEAN-06** · El extractor deberá devolver año, edad y eventos excluyentes solo cuando el
texto los declare explícitamente, y nulo en otro caso.

**RF-LEAN-07** · Todo evento deberá llevar vigencia por versión, y una regeneración deberá
cerrar los eventos del capítulo sustituido sin tocar los de la versión anterior.

**RF-LEAN-08** · El caso del brief B2 deberá quedar documentado como el caso que solo Lean
detecta, o, si no llega a Lean, con su motivo y un caso marcado como provocado (P-83).

## 5. Criterios de aceptación

1. Prueba basada en propiedades: dos generaciones sobre la misma story bible dan el mismo
   fichero; reordenar filas en la base no lo cambia (A-90).
2. Inspección automática: el fichero generado no contiene `import Mathlib` ni ningún texto
   libre de la base (A-91, regla 11).
3. Una story bible sintética por invariante con **una** violación hace fallar exactamente
   el teorema de ese evento; la misma sin violación compila (O-13, O-14, O-15, O nueva).
4. Una analepsis —un evento narrado después con un año anterior— compila en verde.
5. Un evento sin año, o una edad no declarada, no hace fallar nada y sale en el recuento de
   «sin comprobar».
6. El gate con Lean en rojo rechaza la candidata y la versión publicada sigue intacta con su
   hash (P-64, TO-062); con Lean en verde, publica.
7. Timeout y toolchain ausente hacen fallar el gate y solo avisan en el incremental (P-81).
8. Un fallo de Lean llega al detalle del `GateEnRojo` y al audit log con evento y capítulo
   (P-82).
9. Tras la migración `0016`, cada versión de la base de la demo tiene exactamente los eventos
   de sus capítulos y ningún momento duplicado; una regeneración cierra los eventos
   sustituidos.
10. El extractor, ante un capítulo sin años ni edades ni muertes explícitas, devuelve nulos
    y ninguna exclusión (prueba con el doble del modelo ya existente).
11. `lean_timeout_segundos` lleva la medida real anotada; `gate_activo: true`.
12. La copia de la versión 3 está documentada, y el caso B2 está en `docs/red-team.md` y en
    `verification.md` (P-83 pasa a `D`), con la etiqueta «real» o «provocado» según lo que
    ocurra.

## 6. Riesgos

- **`by decide` con decenas de eventos**: con unos 75 eventos y un teorema por par en la
  ubicación son unos miles de teoremas pequeños. Si el build se dispara, se agrupan por
  personaje o por momento; `native_decide` no se usa sin decirlo.
- **Lean demuestra lo que la story bible contiene** (O-13): un año que el extractor no
  registra no participa. El recuento de «sin comprobar» lo hace visible.
- **B2 puede no llegar a Lean**: el redactor puede suavizar la incoherencia o un validador
  semántico cazarla en el capítulo. Si pasa, es un resultado y se documenta; el caso
  provocado queda de red.
- **Un falso positivo del extractor** (una muerte que no lo era) haría fallar el gate. Se
  acepta: el fallo vuelve al editor con el evento nombrado, y es más barato que publicar un
  muerto que reaparece.

## 7. Preguntas al desarrollador — respondidas el 2026-09-25

**P1 · Año y edad.** Sí: `año` opcional en `Evento` y `edad` opcional por personaje
presente, extraídos solo si el texto los dice explícitamente; si faltan, Lean no comprueba
nada sobre ellos. Invariante nueva de nacimiento. Dos ordenaciones separadas: `momento` para
la ubicación, `año` para la cronología; una analepsis no es una incoherencia. → TO-064.

**P2 · Eventos excluyentes.** Sí, solo cuando el texto indique explícitamente una muerte o
una partida definitiva. → TO-065.

**P3 · Caso real.** Sí a la prueba sobre una copia de la versión 3, sin tocar la story bible
real; el caso real que se presenta es el del brief B2 de la evaluación, y un caso construido
a mano se marca como provocado. → TO-067.

**Además**: la migración `0016` liga `evento` a la versión como los hechos de TO-028, para no
depender de que el generador filtre. → TO-066. Se aceptan los identificadores sintéticos,
un teorema por evento, `GateEnRojo` con timeout o error de toolchain como fallo, y el chequeo
por capítulo solo como aviso.
