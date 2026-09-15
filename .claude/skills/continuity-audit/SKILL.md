---
name: continuity-audit
description: Usar al auditar la coherencia de un manuscrito generado, al investigar una incidencia CONT-* concreta o al ampliar el validador de continuidad.
---

# Auditoría de continuidad

El validador vive en `src/novela/validators/continuity.py`. Tiene una parte
determinista (el ledger) y una parte con juez LLM (voz, motivación, tensión).

## Catálogo de códigos CONT-*

| Código | Severidad | Qué detecta | Cómo reproducirlo en un test |
|---|---|---|---|
| `CONT-FACT-CONFLICT` | blocking | Dos hechos `vigente` con igual `(subject, predicate)` y distinto `value` | Inyecta dos `CanonFact` sin revocar el primero |
| `CONT-DEAD-ACTS` | blocking | Personaje con `estado_vital = muerto` que actúa después | Hecho de muerte en el capítulo *i*, nombre como sujeto en el *i+1* |
| `CONT-TIMELINE` | blocking | `story_time_start` de *i* anterior al `story_time_end` de *i-1* sin flashback declarado | Copia el plan y retrasa `story_time_start` |
| `CONT-LOCATION-IMPOSSIBLE` | blocking | Mismo POV en dos sitios con intervalos **solapados** y sin tránsito | Solapa los intervalos y cambia `location_ids` |
| `CONT-RULE-VIOLATION` | blocking | Una frase ejerce una capacidad que `speculative_premise.limits` prohíbe | Escribe una frase con las palabras significativas del límite |
| `CONT-NAME-DRIFT` | major | Nombre a distancia de edición ≤ 2 de una entidad canónica, con la misma inicial | «Nadya» frente a «Nadia» |
| `CONT-BEAT-MISSING` | major | Cobertura de beats por debajo de `continuity.beat_coverage_min` | Texto que no narra los beats del plan |
| `CONT-VOICE-DRIFT` | major | Lo emite el Juez LLM, no el código | Fixture del juez con la incidencia |

## Cómo consultar el ledger

```bash
novela continuity <pid>          # hechos vigentes, hilos abiertos y cronología
cat out/<pid>/ledger.json        # estado completo, incluidos los revocados
cat out/<pid>/reports/chapter_02.json   # incidencias y métricas del capítulo 2
```

Las métricas deterministas quedan siempre en `ValidationReport.metrics`:
`cont.fact_conflicts`, `cont.dead_acting`, `cont.timeline_inverted`,
`cont.location_impossible`, `cont.rule_violations`, `cont.name_drift`,
`cont.beat_coverage`, `cont.judge_issues`.

## Criterio de severidad

- **blocking**: el lector detectaría una imposibilidad factual. Fuerza
  reescritura y, tras `limits.max_rewrite_attempts`, escala el capítulo.
- **major**: el capítulo funciona pero incumple el plan o el canon en algo
  reparable con un parche local.
- **minor**: señal de calidad que se registra y no interrumpe.

Si dudas entre `blocking` y `major`, pregúntate si un lector atento cerraría el
libro. Si la respuesta es sí, es bloqueante.

## Al ampliar el validador

1. Añade el código a `DEFAULT_SEVERITY` en `validators/base.py`. Los códigos son
   una lista cerrada: no inventes uno nuevo sin actualizar también §5 del spec.
2. Escribe primero el test en `tests/test_continuity.py` con el caso que debe
   dispararlo **y** el caso que no debe.
3. Registra siempre una métrica, aunque no emitas incidencia: es lo que después
   permite calibrar.
4. Mantén la función por debajo de 50 líneas y sin escribir en el store.
5. Los umbrales llegan en `ContinuityCfg`, nunca codificados en el módulo.
