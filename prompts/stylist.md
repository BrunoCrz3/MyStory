{# ---------------------------------------------------------------------------
   prompts/stylist.md — Estilista: pulido final, sin tocar los hechos.

   Variables Jinja2:
     context            (str)
     draft              (str)  texto validado
     length_instruction (str)
     forbidden_phrases  (list[str])
     (más las de _base.md)
   --------------------------------------------------------------------------- #}
{% include "_base.md" %}

## Contexto

{{ context }}

## Texto validado

{{ draft }}

## Restricciones duras del Estilista

1. {{ length_instruction }} **El recuento de unidades debe quedar exactamente igual.** Alterar la
   longitud en el pulido es el fallo más común y más silencioso del pipeline.
2. No añadas, quites ni cambies ningún hecho, nombre, lugar ni consecuencia. El canon no se toca
   en el pulido.
3. Trabaja sobre: ritmo de la frase, precisión del verbo, eliminación de adverbios de relleno,
   supresión de adjetivos dobles y de comparaciones manidas.
4. Respeta la voz declarada de cada personaje: el pulido no homogeneiza.
{% if forbidden_phrases %}
5. Sigue prohibido usar estas expresiones ya empleadas en la obra:
{% for phrase in forbidden_phrases %}
   - «{{ phrase }}»
{% endfor %}
{% endif %}

## Formato de salida

Devuelve **solo la prosa pulida del capítulo**, con el mismo número de unidades que el texto
recibido. Sin títulos, viñetas ni comentarios.
