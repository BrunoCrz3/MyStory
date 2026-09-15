---
name: sf-prose
description: Usar al escribir o ajustar las plantillas del Escritor, Reescritor o Estilista, y al juzgar la calidad de la prosa de ciencia ficción que produce el pipeline.
---

# Prosa de ciencia ficción

Las plantillas viven en `prompts/`. Heredan de `_base.md` y se renderizan con
Jinja2. La cabecera de cada fichero declara las variables que consume.

## Principios

1. **Exposición integrada en la acción.** Nadie explica a otro lo que ambos ya
   saben. Si hace falta que el lector sepa algo, que lo descubra porque alguien
   lo usa, lo rompe o lo esconde.
2. **Entrada tardía, salida temprana.** Empieza la escena lo más tarde posible y
   córtala en cuanto haya ocurrido lo que tenía que ocurrir.
3. **Concreción sensorial.** Objetos, texturas, temperaturas, ruidos. El detalle
   concreto hace verosímil lo especulativo; la abstracción lo vuelve folleto.
4. **Prohibido resumir lo ya narrado.** Es la primera causa de repetición y la
   razón de que exista la capa L7 de prohibiciones.
5. **El límite antes que la maravilla.** Lo interesante de una tecnología es lo
   que no puede hacer: ahí está el conflicto.
6. **Una voz por personaje.** Léxico, longitud de frase y lo que cada uno evita
   decir. El Estilista pule sin homogeneizar.
7. **Un solo intervalo temporal por capítulo**, salvo que el plan declare otra
   cosa.

## Clichés del género a evitar

- El cuenco de estrellas, el silencio sepulcral del espacio, el frío que cala
  los huesos a través del traje.
- La IA que descubre que tiene sentimientos y lo anuncia en voz alta.
- El científico que explica su propio invento a un colega que ya lo conoce.
- «No teníamos forma de saberlo» y demás anticipaciones que matan la tensión.
- El terminal que parpadea en rojo justo cuando conviene.
- Nombres de tecnología en mayúsculas con guion que no significan nada.
- El final que revela que todo era una simulación.

## Al escribir una plantilla

- Declara en la cabecera las variables Jinja2 que consume.
- Separa **restricciones duras** (numeradas, verificables) de **formato de
  salida**.
- La instrucción de longitud NO se escribe a mano: llega en
  `{{ length_instruction }}`, generada por `agents/base.py::length_instruction`.
  Es el único punto del sistema que traduce `LengthSpec` a lenguaje natural.
- Las prohibiciones literales llegan en `{{ forbidden_phrases }}` y
  `{{ forbidden_openings }}` desde los `StyleArtifact` del Archivista.
- El Reescritor recibe el texto **y** las incidencias concretas: tiene prohibido
  regenerar a ciegas.
- El Parcheador sustituye fragmentos y deja el resto idéntico palabra por
  palabra. Si cambia la longitud, el parche ha fallado.
- El Estilista no toca ningún hecho y no puede alterar el recuento de unidades.

## Al juzgar la prosa

Distingue lo que juzga el Juez LLM de lo que ya cubren los validadores:

- El Juez evalúa voz, motivación, cobertura de beats y tensión.
- La longitud, la repetición y la continuidad de hechos las cubren los
  validadores deterministas. Duplicarlas en el Juez solo produce ruido.
