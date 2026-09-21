---
name: presupuesto-de-contexto
description: Reparto de la ventana de 100 000 tokens entre las siete capas del contexto de una escena, con la fuente y el presupuesto de cada una, la regla de contar antes de llamar al modelo y fallar en voz alta, y la jerarquía de compresión. Cárgala antes de ensamblar un prompt, añadir o quitar contenido de una capa, escribir o cambiar el contador de tokens, decidir qué se comprime cuando algo no cabe, meter texto de escenas anteriores en el contexto, o diseñar la recuperación de fragmentos. Úsala también cuando aparezcan las palabras contexto, prompt, ventana, tokens, presupuesto, truncar, comprimir, resumen, snapshot, anticontexto o recuperación, y siempre que una tarea parezca necesitar más de 100 000 tokens — ahí es justo donde más falta hace.
---

# Presupuesto de contexto

La ventana de 100 000 tokens es un límite duro, no un objetivo. El ensamblador reparte ese
total por capas y cada capa responde a una pregunta distinta sobre la escena que se va a
escribir. El reparto existe porque sin él una sola capa se come la ventana: las escenas
literales siempre pueden crecer, y el resultado es un prompt lleno de prosa reciente y
vacío de estado del mundo.

## El reparto

| Capa | Tokens | Origen |
| --- | --- | --- |
| Invariante | 6 000 | Premisa, guía de estilo, glosario canónico |
| Estructural | 4 000 | Brief de escena y restricción de destino |
| Estado | 18 000 | Snapshot derivado en t, nunca texto bruto |
| Local | 30 000 | Últimas escenas literales |
| Recuperado | 25 000 | `sqlite-vec`, filtrado por entidades del brief |
| Estilo | 8 000 | Muestras de voz de los personajes presentes |
| Anticontexto | 5 000 | Repeticiones, clichés vetados, revelaciones prohibidas |
| Margen | 4 000 | Reserva para la respuesta y el desbordamiento |

Las siete capas más el margen suman exactamente 100 000. Que sumen es una propiedad que se
verifica, no una coincidencia: mantén el total como una constante única y deriva las
partes, en vez de repartir números sueltos por el código.

`docs/definitions.md` Capa 3 da estos mismos presupuestos en porcentaje y son orientativos;
el reparto operativo es el de esta tabla, que viene de `AGENTS.md`. Hay un desajuste
abierto en la capa Estructural (4 % real frente al 5 % declarado), anotado en
`docs/verification.md`. No lo resuelvas por tu cuenta.

## Las dos reglas que no se tocan

**1. El contador se calcula antes de llamar al modelo, no después.** Contar después es
descubrir el problema cuando ya has pagado la llamada y ya no puedes decidir qué sacrificar.

**2. Un ensamblado que no cabe falla en voz alta.** No se trunca en silencio. Un truncado
silencioso corta por donde caiga —normalmente el final, donde está el anticontexto y las
revelaciones prohibidas— y produce una escena que viola una regla que sí estaba en el
presupuesto. El fallo ruidoso es recuperable; el silencioso se descubre leyendo la novela.

**Si una capa se pasa, se comprime esa capa.** Nunca se le roba presupuesto a otra ni se
supera el total. Cada capa cubre un riesgo distinto: bajarle tokens al anticontexto para
meter más prosa reciente cambia un problema de continuidad por uno de repetición, sin que
nadie lo haya decidido.

Si una tarea parece exigir más de 100 000 tokens, el diseño está mal. Propón compresión,
no una ventana mayor.

## Qué va en cada capa

- **Invariante.** Lo que no cambia entre escenas. Si algo de aquí cambia en cada escena,
  pertenece a otra capa.
- **Estructural.** El brief es mínimo por diseño: estado de entrada más restricción de
  destino. No se planifican beats — la escena descubre *cómo*, no *hacia dónde*.
- **Estado.** Snapshot derivado en t, **nunca** el texto anterior. Es la diferencia entre
  18 000 tokens de estado del mundo y 18 000 tokens de prosa de la que el modelo tiene que
  inferirlo. Lo segundo desperdicia la capa y además se equivoca.
- **Local.** Las últimas escenas literales, para continuidad de prosa. Es la única capa
  donde el texto crudo está justificado: la voz se contagia de lo literal, no de un resumen.
- **Recuperado.** Filtro relacional por las entidades del brief **y después** similitud
  vectorial. Nunca similitud sola: devuelve fragmentos de tono parecido y estado
  irrelevante. Para el SQL y el `vec0`, carga `sqlite-relacional` y `sqlite-vec`.
- **Estilo.** Muestras de voz de los personajes presentes en la escena, no de todos.
- **Anticontexto.** Metáforas ya usadas, ecos, clichés vetados y revelaciones prohibidas.
  Es la capa que casi nadie modela y la que más mejora el resultado: el fallo
  característico de un modelo de lenguaje no es escribir mal, sino escribir correcto y
  genérico, y ninguna otra capa lo combate.

## Jerarquía de compresión

Lo lejano entra comprimido y lo cercano literal:

```
Resumen de acto      ~200 tokens
Resumen de capítulo  ~500 tokens
Resumen de escena    ~100 tokens
Escena literal      ~2000 tokens
```

Comprimir es bajar de resolución, no recortar por la mitad. Ante una capa que desborda,
sustituye elementos literales por su resumen del nivel superior antes de eliminar nada:
perder una escena entera cambia lo que el modelo sabe; resumirla solo cambia cuánto detalle
tiene.

## Ventana efectiva

La porción del contexto que el modelo realmente atiende no coincide con la ventana
nominal. Cabe no es lo mismo que se usa. Por eso el orden y la densidad importan, y por
eso `docs/verification.md` clasifica «la ventana efectiva cubre las siete capas» como una
afirmación que solo se establece por demostración, no por prueba.

## Trazabilidad

Todo ensamblado que llega al modelo se guarda con su modelo, prompt, contexto y semilla
vía `registrar-generacion`. Sin eso no se puede reproducir un ensamblado bueno ni
diagnosticar uno malo, y el presupuesto se vuelve imposible de ajustar con datos.
