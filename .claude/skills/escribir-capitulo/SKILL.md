---
name: escribir-capitulo
description: Procedimiento completo para escribir, validar, pulir, archivar y comitear UN capítulo de la novela. Úsalo siempre que haya que producir un capítulo, tanto el siguiente pendiente como uno que hay que regenerar tras la revisión global. No lo uses para el canon ni para la escaleta.
---

# Escribir un capítulo

Este procedimiento se aplica a **un solo capítulo**, identificado por su número
`NN` (dos dígitos, con cero a la izquierda). No empieces el capítulo i+1 hasta
que el i esté archivado.

Antes de nada: `intento = 1`.

## Paso 0 — Comprobaciones previas

1. Existen `novela/canon.md` y `novela/escaleta.json`. Si no, para: falta la fase 1 o la 2.
2. `NN` es el siguiente pendiente, o el autor ha pedido explícitamente regenerar ese.
3. Todos los capítulos anteriores existen en `novela/capitulos/`.
4. Registra el inicio:
   `python scripts/eventos.py --evento capitulo_inicio --capitulo NN`

## Paso 1 — Construir el contexto

Lee, en este orden, y quédate solo con lo que este capítulo necesita:

| Fuente | Qué extraes |
|---|---|
| `config.json` | `longitud.unidad`, `longitud.objetivo`, `longitud.tolerancia` |
| `novela/canon.md` | Personajes que salen en este capítulo, escenario, premisa especulativa completa (reglas, límites, coste), glosario, términos prohibidos, motivos recurrentes |
| `novela/escaleta.json` | El objeto del capítulo NN, entero |
| `novela/estado.json` → `hechos` | Todos, con su cita |
| `novela/estado.json` → `hilos` | Solo los de estado `abierto` |
| `novela/estado.json` → `resumenes` | Todos los de capítulos anteriores |
| `novela/estado.json` → `resumenes[NN-1].ultimas_lineas` | **Literales**, las pasas tal cual |
| `novela/estado.json` → `frases_usadas` | La lista completa: son frases prohibidas |
| `novela/estado.json` → `aperturas` | Los tipos ya usados, para no repetir recurso |

No resumas el canon "de memoria": léelo del fichero en esta misma ejecución.

## Paso 2 — Borrador

Invoca al subagente `escritor` en modo `borrador` con todo el contexto del paso 1.
Debe guardar `novela/capitulos/capitulo-NN.md`.

Registra: `python scripts/eventos.py --evento borrador --capitulo NN --intento <intento>`

## Paso 3 — Validación

Aplica la skill `validar-capitulo` sobre NN. Te devuelve el recuento de
incidencias por severidad y la lista completa.

## Paso 4 — ¿Hay incidencias bloqueantes?

**Sí →**
1. Invoca al `escritor` en modo `reescritura`, pasándole el borrador actual y la
   lista literal de incidencias bloqueantes (solo esas).
2. Registra:
   `python scripts/eventos.py --evento reescritura --capitulo NN --intento <intento>`
3. `intento = intento + 1`.
4. Si `intento` supera `config.json` → `validacion.max_reescrituras`: ve al paso 7.
5. Vuelve al paso 3.

**No →** sigue al paso 5.

## Paso 5 — ¿Hay incidencias mayores?

**Sí →**
1. Invoca al `escritor` en modo `parche` con la lista de incidencias mayores,
   cada una con su ancla literal.
2. Registra:
   `python scripts/eventos.py --evento parche --capitulo NN --intento <intento>`
3. **Vuelve al paso 3.** El parche se revalida siempre: corregir una cosa puede
   romper otra. No te saltes esto nunca.

**No →** sigue al paso 6. Las incidencias menores se anotan y no detienen nada.

## Paso 6 — Pulido y archivo

1. Invoca al subagente `estilista` sobre NN.
2. **Vuelve a medir la longitud**, sin excepción:
   `python scripts/medir.py --capitulo NN`
   Si se ha salido de norma, devuélveselo al `estilista` con la cifra exacta.
   Este es el fallo más silencioso del sistema.
3. Pasa `python scripts/repeticion.py --capitulo NN` una última vez: el estilista
   ha podido introducir una frase ya usada.
4. Invoca al subagente `archivista` sobre NN. Es el único que escribe
   `novela/estado.json`.
5. Registra:
   `python scripts/eventos.py --evento capitulo_fin --capitulo NN --intento <intento>`
6. Aplica la skill `bitacora` para el commit del capítulo.
7. Informa al autor en 3 líneas: título, cuántos intentos e incidencias menores
   que quedan anotadas.

## Paso 7 — Escalar al autor

Se llega aquí cuando se agotan los intentos. **Para. No sigas con el capítulo siguiente.**

1. Registra:
   `python scripts/eventos.py --evento escalado --capitulo NN --intento <intento>`
2. Deja el último borrador en disco sin borrarlo.
3. Dile al autor, en este formato:
   - Capítulo y título.
   - Las incidencias bloqueantes que no se han podido resolver, con su cita.
   - Qué has intentado en cada uno de los intentos.
   - Las tres opciones: (a) relajar el plan de ese capítulo en
     `novela/escaleta.json`, (b) ajustar el canon si la regla es imposible de
     cumplir, (c) aceptar el capítulo con la incidencia.
4. Espera su decisión. No decidas tú.

## Reglas que no se saltan

- El orden es sagrado: capítulo i antes que i+1.
- Un parche siempre se revalida.
- Tras el estilista siempre se mide la longitud.
- El contador de intentos cuenta reescrituras y parches juntos.
- Solo el archivista escribe el estado.
