{# ---------------------------------------------------------------------------
   prompts/outliner.md — Escaletista: plan capítulo a capítulo.

   Variables Jinja2:
     bible         (StoryBible) canon aprobado, serializado
     chapter_count (int)        número exacto de capítulos a producir
     length_spec   (LengthSpec) tamaño objetivo por capítulo
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Canon aprobado

```json
{{ bible }}
```

## Tarea

Produce la escaleta de **exactamente {{ chapter_count }} capítulos**, ni uno más ni uno menos.
Cada capítulo mide {{ length_spec.target }} {{ length_spec.unit }}.

Dimensiona la ambición de cada capítulo al espacio real disponible.
{% if length_spec.unit == "lines" and length_spec.target <= 8 %}
Con {{ length_spec.target }} líneas por capítulo escribes una **trama mínima y cerrada**: un
solo hilo principal, dos personajes en escena, un único giro por capítulo y un final que
resuelve. No es el arranque de una saga. Todo lo que abras tienes que cerrarlo dentro de
{{ chapter_count }} capítulos.
{% endif %}

## Restricciones duras del Escaletista

1. `new_information` **no puede estar vacío en ninguna escena**: si una escena no aporta algo
   que el lector no sepa, el capítulo es relleno y se rechaza.
2. Todo hilo que abras en `threads_opened` debe aparecer en `threads_closed` de algún capítulo
   con número ≤ {{ chapter_count }}.
3. Dos capítulos consecutivos no pueden repetir a la vez función dramática, punto de vista y
   localización.
4. `story_time_start` y `story_time_end` avanzan de forma monótona salvo que declares
   explícitamente un flashback en `dramatic_function`.
5. `pov_character_id` y `location_ids` deben referirse a identificadores que existan en el canon.
6. Un solo punto de vista por capítulo.
7. `target_length` de cada capítulo vale exactamente:
   `{"unit": "{{ length_spec.unit }}", "target": {{ length_spec.target }}, "tolerance": {{ length_spec.tolerance }}}`.

## Formato de salida

Devuelve **exclusivamente** un objeto JSON con esta forma:

```json
{
  "chapters": [
    {
      "number": 1,
      "working_title": "string",
      "pov_character_id": "chr_1",
      "location_ids": ["loc_1"],
      "story_time_start": "string",
      "story_time_end": "string",
      "dramatic_function": "string",
      "goal": "string",
      "conflict": "string",
      "outcome": "string",
      "scenes": [{"id": "sc_1_1", "beats": ["string"], "new_information": ["string"]}],
      "threads_opened": ["th_1"],
      "threads_advanced": [],
      "threads_closed": [],
      "world_state_delta": ["string"],
      "hook": "string",
      "target_length": {"unit": "{{ length_spec.unit }}", "target": {{ length_spec.target }}, "tolerance": {{ length_spec.tolerance }}}
    }
  ]
}
```
