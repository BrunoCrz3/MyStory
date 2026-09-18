---
description: Fase 3. Escribe el siguiente capítulo pendiente, o el que le indiques, con todo el ciclo de validación.
argument-hint: "[numero de capitulo | todos]"
---

# Escribir capítulo

Argumento recibido: `$ARGUMENTS`.

## Qué capítulo

- Sin argumento: el siguiente pendiente, es decir
  `novela/estado.json` → `capitulos_escritos` + 1.
- Un número: ese capítulo, aunque ya exista (regeneración).
- `todos`: todos los pendientes, **en orden y uno detrás de otro**, parando en
  cuanto uno escale al autor.

## Comprobaciones

1. Existen `novela/canon.md` y `novela/escaleta.json`. Si no: "Lanza
   `/nueva-novela` primero." y para.
2. El capítulo pedido está dentro del rango de la escaleta.
3. Todos los capítulos anteriores existen. Si falta alguno, no saltes: escribe
   ese primero.

## Ejecución

1. Si es el primer capítulo de la sesión:
   `python scripts/eventos.py --evento fase_inicio --fase redaccion`
2. Aplica la skill `escribir-capitulo` al capítulo.
3. Con `todos`: repite hasta agotar los pendientes o hasta un escalado.
4. Al acabar el último:
   `python scripts/eventos.py --evento fase_fin --fase redaccion`

## Al terminar

Muestra: capítulos escritos, capítulos que quedan, e incidencias menores
acumuladas. Si quedan capítulos, recuerda: "Lanza `/escribir` otra vez."
Si no queda ninguno: "Lanza `/entregar`."
