---
description: Fases 1 y 2. Crea el canon narrativo y la escaleta a partir de la premisa de config.json.
argument-hint: "[solo-canon | solo-escaleta]"
---

# Nueva novela

Argumento recibido: `$ARGUMENTS` (vacío = hacer las dos fases).

## Paso previo

1. Lee `config.json`. Si `premisa` sigue siendo el texto de marcador
   (`ESCRIBE AQUI TU PREMISA...`), **para** y pide al autor que la escriba.
2. Si ya existe `novela/canon.md` y el argumento no es `solo-escaleta`, avisa de
   que se va a sobrescribir y pide confirmación antes de seguir.
3. Genera el identificador de tirada con
   `python scripts/eventos.py --evento fase_inicio --fase canon`
   y anótalo: lo usarás durante toda la sesión.

## Fase 1 — Canon

Salvo que el argumento sea `solo-escaleta`:

1. Invoca al subagente `arquitecto`.
2. Muestra al autor el canon generado, resumido en 10 líneas: logline, tema,
   personajes con su deseo, y las reglas, límites y coste de la premisa especulativa.
3. **Pregunta si lo aprueba.** Si pide cambios, vuelve a invocar al `arquitecto`
   con las correcciones. Repite hasta que apruebe.
4. Al aprobar: `python scripts/eventos.py --evento fase_fin --fase canon` y
   commit según la skill `bitacora`.

## Fase 2 — Escaleta

Salvo que el argumento sea `solo-canon`:

1. `python scripts/eventos.py --evento fase_inicio --fase escaleta`
2. Invoca al subagente `escaletista`.
3. Ejecuta `python scripts/continuidad.py --escaleta`. Si hay incidencias
   bloqueantes, devuélveselas al `escaletista` y repite.
4. Muestra al autor una tabla de N filas: capítulo, título, POV, día, función,
   qué abre y qué cierra.
5. **Pregunta si la aprueba.** Si pide cambios, vuelve a invocar al `escaletista`.
6. Al aprobar: `python scripts/eventos.py --evento fase_fin --fase escaleta` y commit.

## Al terminar

Di al autor: "Canon y escaleta listos. Lanza `/escribir` para el capítulo 1."
