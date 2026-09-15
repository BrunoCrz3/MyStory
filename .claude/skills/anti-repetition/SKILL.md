---
name: anti-repetition
description: Usar al calibrar umbrales de repetición, al investigar una incidencia REP-* o al diagnosticar prosa monótona en un manuscrito generado.
---

# Anti-repetición

El validador vive en `src/novela/validators/repetition.py` y es **100 %
determinista**: no llama al LLM. Ningún umbral está en ese módulo; todos llegan
en `RepetitionCfg` desde `config/profiles/`.

## Contrato que no se negocia

> Un umbral `null` desactiva **esa severidad**, no la comprobación.

La métrica se calcula siempre y se registra en `ValidationReport.metrics`. Es lo
que permite calibrar con datos en lugar de con impresiones.

## Las siete métricas

| Métrica | Qué mide | Umbral | Código |
|---|---|---|---|
| `rep.jaccard_max` | Solapamiento de n-gramas frente a cada capítulo previo, sin palabras vacías | `jaccard_blocking` / `jaccard_warning` | `REP-NGRAM` |
| `rep.cosine_max` | Similitud TF-IDF frente a cada capítulo previo | `cosine_scene_blocking` / `cosine_scene_warning` | `REP-COSINE` |
| `rep.image_cosine_max` | Reutilización de metáforas ya registradas | fijo, > 0,90 | `REP-IMAGE-REUSE` |
| `rep.trigram_max_repeats` | Muletillas en todo el manuscrito | `max_trigram_repeats` | `REP-NGRAM` |
| `rep.opening_repeated` | Tipo de apertura repetido en la ventana | `opening_type_window` | `REP-OPENING-TYPE` |
| `rep.sentence_openers_repeated` | Primeras tres palabras ya usadas | `forbid_reused_sentence_openers` | `REP-SENTENCE-OPENER` |
| `rep.mtld` y `rep.mtld_drop` | Diversidad léxica y su caída | `mtld_check`, `mtld_drop_max` | `REP-LEXICAL-DIVERSITY` |

Tipos de apertura reconocidos: `dialogo`, `reflexion`, `accion`, `descripcion`.

## Rangos sanos por perfil

- **`micro`** (3 capítulos de 4 líneas): jaccard y coseno **desactivados** como
  bloqueantes. Con 12 líneas de muestra total, cualquier umbral de novela larga
  produce falsos positivos constantes. Lo único fiable a esta escala es el tipo
  de apertura.
- **`full`** (novela real): `jaccard_blocking: 0.15`, `cosine_scene_blocking:
  0.85`. **Estos valores son un punto de partida razonable, no valores
  medidos.**

## Procedimiento de calibración

1. Genera dos o tres obras completas con el perfil `full`.
2. Recoge las métricas: `out/<pid>/reports/chapter_*.json` y
   `out/<pid>/reports/repetition.json`.
3. Ordena los valores de la métrica que quieras ajustar y mira la distribución,
   no el máximo.
4. Lee a mano los capítulos del percentil alto. ¿Repiten de verdad?
5. Sitúa el umbral bloqueante por encima del ruido observado y el de aviso justo
   por debajo. Si el bloqueante cae dentro de la nube de valores normales, el
   pipeline se pasará la vida reescribiendo.
6. Abre una issue con la plantilla `calibration.yml`, con las métricas pegadas.

## Advertencia sobre muestras pequeñas

Con menos de diez capítulos, la varianza de `jaccard_max` y `mtld` es mayor que
la señal. Un umbral calibrado sobre tres capítulos no mide repetición: mide qué
tres capítulos te tocaron. Por eso `micro` desactiva esas severidades en lugar de
bajarlas.

## Al diagnosticar prosa monótona

1. `rep.mtld` bajo y estable → vocabulario pobre: trabaja los prompts del
   Escritor y del Estilista, no los umbrales.
2. `rep.sentence_openers_repeated` alto → todas las frases empiezan por el
   sujeto: es un problema de sintaxis, no de léxico.
3. `rep.opening_repeated` recurrente → la escaleta repite función dramática;
   mira antes `OUT-REPEATED-FUNCTION`.
4. `rep.cosine_max` alto con `rep.jaccard_max` bajo → repite la *escena*, no las
   palabras. Eso se arregla en la escaleta.
