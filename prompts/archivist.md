{# ---------------------------------------------------------------------------
   prompts/archivist.md — Archivista: extrae el estado del mundo del capítulo.

   Variables Jinja2:
     chapter_number (int)
     chapter_text   (str)   texto FINAL del capítulo
     bible          (str)   canon serializado
     ledger         (str)   estado del mundo acumulado, serializado
     plan           (str)   ChapterPlan del capítulo
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Capítulo {{ chapter_number }} (texto final)

{{ chapter_text }}

## Canon

```json
{{ bible }}
```

## Estado del mundo antes de este capítulo

```json
{{ ledger }}
```

## Restricciones duras del Archivista

1. **No infieras nada que no esté escrito en el capítulo.** Si el texto no lo dice, no ocurrió.
   Ni deducciones razonables, ni consecuencias probables, ni lo que anunciaba el plan: solo lo
   que está en la página.
2. Cada `CanonFact` lleva `evidence` con una **cita breve y literal** del capítulo (máximo 200
   caracteres). Un hecho sin cita literal es una invención.
3. Los hechos **se revocan, no se borran**. Si un hecho anterior deja de ser cierto, devuélvelo
   con `status: "revocado"` y `revoked_by` apuntando al identificador del hecho que lo sustituye.
4. `predicate` usa el vocabulario cerrado: `estado_vital`, `ubicacion`, `posee`, `sabe`, `relacion`.
5. Un hilo solo pasa a `cerrado` si el capítulo lo resuelve en la página.
6. `style_artifacts` recoge las metáforas, imágenes y el tipo de apertura **realmente usados**:
   es la memoria anti-repetición de los capítulos siguientes.

## Formato de salida

Devuelve **exclusivamente** un objeto JSON con esta forma:

```json
{
  "facts": [
    {"id": "f_1_loc", "subject": "chr_1", "predicate": "ubicacion", "value": "string",
     "chapter_established": 1, "status": "vigente", "revoked_by": null, "evidence": "cita literal"}
  ],
  "threads": [
    {"id": "th_1", "question": "string", "opened_chapter": 1, "planned_close_chapter": 3,
     "closed_chapter": null, "status": "abierto", "importance": "principal"}
  ],
  "summary": {
    "number": {{ chapter_number }},
    "one_line": "string",
    "paragraph": "string",
    "by_scene": ["string"]
  },
  "style_artifacts": [
    {"id": "sty_1_a", "kind": "metafora", "text": "string", "chapter": {{ chapter_number }}}
  ],
  "new_entities": ["string"]
}
```
