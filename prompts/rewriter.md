{# ---------------------------------------------------------------------------
   prompts/rewriter.md — Reescritor: corrige incidencias BLOQUEANTES.

   Variables Jinja2:
     context            (str)  contexto ensamblado
     draft              (str)  texto anterior, íntegro
     issues             (list[Issue]) incidencias concretas a corregir
     length_instruction (str)
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Contexto

{{ context }}

## Texto actual

{{ draft }}

## Incidencias que debes corregir

{% for item in issues %}
- **{{ item.code }}** ({{ item.severity }}): {{ item.message }}
{% if item.span %}  Fragmento señalado: «{{ item.span }}»{% endif %}
{% if item.evidence %}  Evidencia: {{ item.evidence }}{% endif %}
{% endfor %}

## Restricciones duras del Reescritor

1. **Prohibido regenerar a ciegas.** Corrige lo señalado y conserva todo lo que funciona:
   las frases no mencionadas en las incidencias se mantienen salvo que la corrección las
   arrastre necesariamente.
2. {{ length_instruction }}
3. No introduzcas hechos nuevos: una corrección no es una oportunidad para ampliar la trama.
4. Si dos incidencias se contradicen, prioriza la de severidad `blocking`.

## Formato de salida

Devuelve **solo la prosa corregida del capítulo completo**. Sin títulos, sin viñetas, sin
comentarios y sin marcar qué has cambiado.
