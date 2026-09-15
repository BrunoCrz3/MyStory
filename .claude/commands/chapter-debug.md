---
description: Reúne plan, contexto, incidencias y versiones de un capítulo y diagnostica qué le pasa.
argument-hint: <número de capítulo> [project_id]
allowed-tools: Bash(novela *), Bash(python -m novela *), Read, Grep, Glob
---

Diagnostica el capítulo **$1** del proyecto `${2:-demo}`.

Reúne, en este orden:

1. **El plan**: la entrada del capítulo $1 en `out/${2:-demo}/outline.json`
   (función dramática, POV, localizaciones, beats, `target_length`).
2. **Las incidencias**: `out/${2:-demo}/reports/chapter_0$1.json`, separando
   bloqueantes, mayores y menores, y con sus métricas.
3. **Las versiones**: `out/${2:-demo}/chapters/ch_0$1.versions.json`, para ver
   cuántas vueltas dio el bucle y con qué `origin` terminó.
4. **La traza**: las líneas de `out/${2:-demo}/trace.jsonl` con
   `"chapter": $1`, prestando atención a `attempt` y a `context_layers`.
5. **El texto final**: `out/${2:-demo}/chapters/ch_0$1.md`.

Después responde a estas cuatro preguntas, en este orden:

- ¿Cumple la longitud que pide su `target_length`?
- ¿Qué incidencias quedaron sin resolver y de qué validador vienen?
- ¿Se recortó alguna capa de contexto? Si falta L1, el Escritor no tenía el
  canon filtrado y eso explica casi cualquier incoherencia.
- ¿La causa está en el capítulo, en la escaleta o en el canon?

Termina con **una** acción concreta. Si la causa está en la escaleta o en el
canon, dilo explícitamente: reescribir el capítulo no arreglaría nada.

Para incidencias `CONT-*` con causa poco clara, delega en el subagente
`continuity-detective` en lugar de leerlo todo en esta ventana.
