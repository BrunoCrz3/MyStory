{# ---------------------------------------------------------------------------
   prompts/architect.md — Arquitecto: construye la biblia narrativa.

   Variables Jinja2:
     premise      (str)        premisa de partida dada por el usuario
     chapter_count(int)        número de capítulos previstos
     length_spec  (LengthSpec) tamaño objetivo por capítulo
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Tarea

A partir de esta premisa, construye la biblia narrativa completa:

> {{ premise }}

La obra tendrá {{ chapter_count }} capítulos de {{ length_spec.target }} {{ length_spec.unit }}
cada uno. Dimensiona el mundo a esa escala: un canon de saga para una obra de tres capítulos
produce una historia que no cabe en sí misma.

## Restricciones duras del Arquitecto

1. `speculative_premise.limits` es **obligatorio y sustantivo**. Cada límite dice qué NO puede
   hacer la tecnología. Una tecnología sin límites destruye el conflicto y es la primera causa
   de incoherencias en los capítulos posteriores. Nada de límites de trámite: si un límite no
   puede generar una escena, no es un límite.
2. `speculative_premise.cost` es **obligatorio y sustantivo**: qué se paga cada vez que se usa
   la tecnología, y quién lo paga.
3. Entre 2 y 8 personajes. Cada uno con `want` (lo que persigue) y `need` (lo que le falta)
   **distintos entre sí**: si coinciden, el personaje no tiene arco.
4. Dos personajes no pueden compartir rol y deseo: serían el mismo escrito dos veces.
5. Los identificadores siguen el patrón `chr_1`, `chr_2`… y `loc_1`, `loc_2`…
6. `motifs` son imágenes recurrentes concretas, no temas abstractos.

## Formato de salida

Devuelve **exclusivamente** un objeto JSON con esta forma:

```json
{
  "logline": "string",
  "theme": "string",
  "characters": [
    {"id": "chr_1", "name": "string", "role": "string", "want": "string", "need": "string",
     "fear": "string", "flaw": "string", "voice": "string",
     "arc_start": "string", "arc_mid": "string", "arc_end": "string"}
  ],
  "locations": [{"id": "loc_1", "name": "string", "description": "string"}],
  "speculative_premise": {
    "concept": "string",
    "rules": ["string"],
    "limits": ["string"],
    "cost": "string"
  },
  "timeline_before": ["string"],
  "glossary": {"término": "definición"},
  "motifs": ["string"]
}
```
