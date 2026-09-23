---
name: sqlite-relacional
description: Lado relacional de la persistencia de este repositorio: migraciones numeradas que nunca se editan, `WAL`, SQL explícito sin ORM, transacciones en toda escritura al canon, y cómo se traducen a esquema las cardinalidades y las máquinas de estado de la ontología. Cárgala antes de crear o cambiar una tabla, escribir una migración, escribir cualquier SQL, abrir una transacción, añadir una clave foránea o una restricción `unique`, modelar una relación N:M, o traducir un estado del dominio a una columna. Úsala también cuando aparezcan las palabras migración, esquema, tabla, clave foránea, cardinalidad, transacción, WAL, índice, `novel.db` o idempotencia. Es el complemento de `sqlite-vec`: aquella cubre `vec0`, KNN y embeddings; esta cubre todo lo demás de la misma base, incluida la frontera entre ambas.
---

# SQLite relacional

Un solo fichero, `data/novel.db`, sin servidor y sin ORM que oculte el SQL. La base es el
canon: no hay segunda fuente de verdad ni caché que sincronizar. Esa decisión compra algo
concreto — la recuperación filtra por entidades del brief (SQL) y ordena por similitud
(`vec0`) en la misma transacción, sin salir del proceso — y cobra a cambio disciplina en
el esquema, porque no hay migración automática que tape un modelo mal puesto.

## Migraciones

Numeradas, en `backend/app/commons/db/migrations/`, aplicadas en orden.

**Una migración commiteada no se edita nunca.** Si está mal, se corrige con una migración
nueva. Editarla deja bases divergentes que se ven idénticas: la tuya reconstruida desde
cero y la del compañero con la versión vieja aplicada. El error aparece semanas después y
en otro sitio.

Para cambiar el esquema: migración nueva, número siguiente, un cambio por migración. Lo
mismo vale para índices y para datos de arranque.

## Ajustes de conexión

- `WAL` activado. Permite leer mientras se escribe, que es justo el patrón de este
  sistema: el frontend consulta el canon mientras una tarea asíncrona consolida.
- Claves foráneas activadas explícitamente. SQLite las ignora por defecto, y un esquema
  con `REFERENCES` que no se aplican es documentación, no integridad.

## Transacciones

**Toda escritura al canon va en transacción**, y es idempotente por `scene_id` +
`version`. Consolidar una escena toca varias tablas —hechos, snapshot, estado epistémico,
promesas— y a medias deja un canon que afirma cosas que el texto no dice.

Un reintento no puede consolidar dos veces: la idempotencia es parte del contrato, no una
optimización.

## De la ontología al esquema

Las cardinalidades salen de la tabla «Relaciones del dominio» de `docs/definitions.md`, no
de lo que parezca cómodo. La traducción es mecánica:

| Cardinalidad | Esquema | Ejemplo del dominio |
| --- | --- | --- |
| 1:N | Clave foránea en el lado N | `Capítulo contiene Escena` |
| N:1 | Clave foránea en el sujeto | `Escena se narra desde Personaje` |
| 1:1 | Clave foránea **más** restricción `unique` | `Escena produce Snapshot`, `Brief encarga Escena` |
| N:M | Tabla puente, clave primaria compuesta | `Evento se narra en Escena`, `Personaje conoce Hecho` |

Dos casos que conviene no simplificar:

- **`Evento` ↔ `Escena` es N:M de verdad.** Una escena narra varios eventos y un evento se
  narra en varias escenas o en ninguna. Colapsarlo a 1:N hace imposibles la analepsis y la
  revelación diferida, que son el motivo de separar fábula y discurso.
- **`Personaje conoce Hecho` lleva la escena en la que lo aprende.** La tabla puente
  necesita esa tercera columna: sin ella no se responde «¿qué sabe este personaje en el
  capítulo 12 y desde cuándo?», que es una de las preguntas de competencia.

## Estados

Los estados de `Escena`, `Hecho canónico`, `Promesa narrativa` y `Hallazgo` están
dibujados en `docs/domain-knowledge.md`. Se implementan tal cual: mismos estados, mismas
transiciones, ninguna extra sin actualizar antes el diagrama.

En el esquema, una columna de estado lleva `CHECK` con la lista cerrada de valores. La
comprobación de *transiciones* válidas no es del esquema sino del `service.py` de la
feature dueña — SQLite no las expresa, y meterlas en triggers las esconde del sitio donde
se leen las reglas.

Dos estados salen sin arista de salida en los diagramas: `Rota` en Promesa y `Refutado` en
Hecho canónico. **Son terminales por diseño**, decidido en
`docs/specs/001-backend-v1/spec.md` §9.3 y RF-CANON-10: ninguno se revive, y si la trama
vuelve sobre ello se crea una entidad nueva que referencia a la anterior. Falta dibujar la
arista a `[*]` al reexportar la ontología; el esquema no espera a eso.

## Frontera con `sqlite-vec`

Las tablas virtuales `vec0` conviven con las relacionales en el mismo fichero. El orden de
consulta no es negociable:

1. Filtro relacional por las entidades declaradas en el brief.
2. Después, y solo sobre ese conjunto, similitud vectorial.

Nunca similitud sola. Devuelve fragmentos de tono parecido y estado irrelevante — prosa
que suena bien y contradice el canon, que es el fallo más caro de este sistema porque pasa
la lectura y no pasa la verificación.

Para todo lo que sea `vec0`, KNN, serialización de embeddings, métrica de distancia o
clave de partición, carga la skill `sqlite-vec`.

## Vetado

Sin ORM que oculte el SQL, sin Postgres, sin pgvector, sin Pinecone, sin Chroma, sin
Redis. El stack está cerrado en «Requisitos técnicos» de `CLAUDE.md` y no se renegocia
dentro de una tarea. Si una tarea parece exigirlo, detente y pregunta.
