{# ---------------------------------------------------------------------------
   prompts/judge.md — Juez: rúbrica de voz, motivación y tensión.

   Variables Jinja2:
     chapter_number (int)
     chapter_text   (str)
     plan           (str)   ChapterPlan del capítulo
     voices         (str)   voces declaradas de los personajes en escena
     (más las de _base.md)

   El Juez se invoca con un `system` distinto del Escritor y SIN el prompt del
   Escritor en contexto, para reducir el sesgo de autoevaluación (§9.5).
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Capítulo {{ chapter_number }}

{{ chapter_text }}

## Plan que debía cumplir

```json
{{ plan }}
```

## Voces declaradas en el canon

```json
{{ voices }}
```

## Rúbrica

Evalúa **solo** estos cuatro ejes y emite una incidencia por cada fallo concreto:

| Eje | Código | Severidad | Cuándo se emite |
|---|---|---|---|
| Voz de personaje | `CONT-VOICE-DRIFT` | `major` | Un personaje habla o piensa fuera de la voz que declara el canon |
| Cobertura de beats | `CONT-BEAT-MISSING` | `major` | Un beat del plan no ocurre en la página |
| Motivación | `CONT-VOICE-DRIFT` | `major` | Un personaje actúa contra su `want`/`need` sin que el texto lo justifique |
| Tensión | `CONT-BEAT-MISSING` | `major` | El capítulo cumple el plan pero no hay conflicto activo en escena |

Reglas de la evaluación:

1. No juzgues gusto literario, ritmo ni calidad de la prosa: de eso se ocupa el Estilista.
2. No emitas incidencias sobre longitud, repetición ni continuidad de hechos: las cubren los
   validadores deterministas y duplicarlas produce ruido.
3. Cada incidencia cita el fragmento concreto en `span`. Sin fragmento, no hay incidencia.
4. Si el capítulo cumple la rúbrica, devuelve la lista vacía. No inventes fallos por cumplir.

## Formato de salida

Devuelve **exclusivamente** un objeto JSON con esta forma:

```json
{
  "issues": [
    {"code": "CONT-VOICE-DRIFT", "severity": "major", "message": "qué está mal y qué hacer",
     "chapter": {{ chapter_number }}, "span": "fragmento literal", "evidence": "voz declarada"}
  ]
}
```
