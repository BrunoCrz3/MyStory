{# ---------------------------------------------------------------------------
   prompts/reviewer.md — Revisor global: fase 4 sobre el manuscrito completo.

   Variables Jinja2:
     manuscript (str)  manuscrito ensamblado
     ledger     (str)  estado del mundo final
     summaries  (str)  resúmenes por capítulo
     bible      (str)  canon
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Manuscrito

{{ manuscript }}

## Estado del mundo final

```json
{{ ledger }}
```

## Resúmenes por capítulo

```json
{{ summaries }}
```

## Tarea

Revisa la obra completa y produce:

1. Un **título de novela** que no sea el nombre de ningún capítulo ni una frase literal del texto.
2. Una **sinopsis** de un párrafo, sin destripar el final.
3. Un **título definitivo por capítulo**, concreto y sin numerar.
4. Las **correcciones** que quedan pendientes, con capítulo, fragmento y motivo.
5. Notas de **ritmo**: dónde se acelera y dónde se estanca la obra.

## Restricciones duras del Revisor

1. Las correcciones son accionables: qué está mal y qué hacer. Una impresión subjetiva no es
   una corrección.
2. No propongas correcciones que exijan cambiar el canon: eso es una decisión del autor.
3. Las claves de `chapter_titles` son el número de capítulo en forma de cadena: `"1"`, `"2"`…

## Formato de salida

Devuelve **exclusivamente** un objeto JSON con esta forma:

```json
{
  "novel_title": "string",
  "synopsis": "string",
  "chapter_titles": {"1": "string"},
  "corrections": [
    {"code": "CONT-BEAT-MISSING", "severity": "minor", "message": "string",
     "chapter": 1, "span": "string", "evidence": "string"}
  ],
  "pacing_notes": ["string"]
}
```
