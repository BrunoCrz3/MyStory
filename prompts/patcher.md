{# ---------------------------------------------------------------------------
   prompts/patcher.md — Parcheador: sustituye fragmentos por incidencias MAYORES.

   Variables Jinja2:
     context            (str)
     draft              (str)  texto anterior, íntegro
     issues             (list[Issue]) incidencias mayores
     length_instruction (str)
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Contexto

{{ context }}

## Texto actual

{{ draft }}

## Incidencias mayores a parchear

{% for item in issues %}
- **{{ item.code }}**: {{ item.message }}
{% if item.span %}  Fragmento a sustituir: «{{ item.span }}»{% endif %}
{% endfor %}

## Restricciones duras del Parcheador

1. Esto **no es una reescritura**. Sustituye únicamente los fragmentos señalados; el resto del
   capítulo debe salir idéntico, palabra por palabra.
2. {{ length_instruction }} El recuento no puede variar: un parche que cambia la longitud es un
   parche fallido.
3. El fragmento nuevo debe encajar en sintaxis y ritmo con las frases contiguas.
4. Regenerar el capítulo entero por una incidencia mayor está prohibido.

## Formato de salida

Devuelve **solo la prosa completa del capítulo ya parcheado**, sin marcas de edición.
