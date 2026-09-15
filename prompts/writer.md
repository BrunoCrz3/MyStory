{# ---------------------------------------------------------------------------
   prompts/writer.md — Escritor: prosa del capítulo i.

   Variables Jinja2:
     context             (str)  contexto ensamblado, capas L1–L6 (§8)
     plan                (str)  ChapterPlan del capítulo, serializado
     length_instruction  (str)  instrucción de longitud generada por código (§7.2)
     forbidden_openings  (list[str]) tipos de apertura ya usados
     forbidden_phrases   (list[str]) frases e imágenes ya usadas (capa L7)
     previous_tail       (str)  cola literal del capítulo anterior
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Contexto

{{ context }}

{% if previous_tail %}
## Cómo terminaba el capítulo anterior (literal)

{{ previous_tail }}

Continúa desde ahí en tono y tensión. No lo repitas ni lo resumas.
{% endif %}

## Plan del capítulo

```json
{{ plan }}
```

## Restricciones duras del Escritor

1. {{ length_instruction }}
2. **Prohibido resumir lo ya ocurrido.** Es la principal fuente de repetición. El lector ya
   estuvo ahí.
{% if forbidden_openings %}
3. Prohibido abrir con estos tipos de apertura, ya usados recientemente:
   {{ forbidden_openings | join(", ") }}.
{% endif %}
{% if forbidden_phrases %}
4. Prohibidas literalmente estas frases e imágenes, ya utilizadas en la obra:
{% for phrase in forbidden_phrases %}
   - «{{ phrase }}»
{% endfor %}
{% endif %}
5. **Entrada tardía y salida temprana**: empieza la escena lo más tarde que puedas y córtala
   en cuanto haya ocurrido lo que tenía que ocurrir.
6. El capítulo transcurre en un **único intervalo temporal**, salvo que el plan indique lo
   contrario en `dramatic_function`.
7. La exposición va integrada en la acción. Nadie explica a otro lo que ambos ya saben.
8. Concreción sensorial: objetos, texturas, temperaturas. Nada de abstracciones de relleno.
9. No uses el nombre de ninguna entidad con una grafía distinta de la del canon.

## Formato de salida

Devuelve **solo la prosa del capítulo**. Sin título, sin encabezados, sin viñetas, sin
numeración, sin líneas en blanco intermedias y sin comentarios sobre el texto.
