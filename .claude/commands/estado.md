---
description: Dice por dónde va la novela: fase actual, capítulos escritos, hilos abiertos y últimos eventos.
---

# Estado de la novela

Solo lectura. No modifica nada, no invoca subagentes.

1. Lee `config.json`: proyecto, premisa, capítulos objetivo, unidad y tamaño.
2. Comprueba qué existe: `novela/canon.md`, `novela/escaleta.json`,
   ficheros en `novela/capitulos/`, `manuscrito.md`.
3. Lee `novela/estado.json`: `capitulos_escritos`, número de hechos, hilos
   abiertos con su título y capítulo de apertura, número de entidades, número
   de frases usadas.
4. Ejecuta `python scripts/medir.py --todos` y muestra qué capítulos están
   fuera de norma.
5. Muestra las últimas 10 líneas de `novela/events.jsonl` de forma legible:
   hora, evento, capítulo, intento.

## Salida

Un informe corto, en este orden:

```
Proyecto: MyStory1
Fase actual: redaccion
Capitulos: 2 de 3 escritos
Longitud: 4 lineas por capitulo, tolerancia 0.0
Fuera de norma: ninguno
Hilos abiertos: T01 (desde cap 1), T02 (desde cap 2)
Hechos registrados: 7
Ultimo evento: capitulo_fin cap 2, intento 2
Siguiente paso: /escribir
```

No inventes ningún dato: si un fichero no existe, dilo.
