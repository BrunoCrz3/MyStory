---
estado: en-revision
aprobada-por:
fecha: 2026-09-21
---

# SRS 1 — Backend, primera versión

Especificación de requisitos de la primera versión del backend. Documento único: cubre
alcance, requisitos funcionales y no funcionales, interfaces, modelo de datos y criterios
de aceptación.

> **Estado: en revisión, no aprobada.** Las ocho preguntas de §9 están respondidas por el
> autor y sus decisiones ya están incorporadas al articulado. Queda **una sola cosa por
> confirmar: el corte de v1 de §1.3**. Según «Ciclo de cambio» de `AGENTS.md`, **no se
> puede escribir el plan de implementación hasta que esta spec esté `aprobada`**.

---

## 1. Introducción

### 1.1 Propósito

Definir qué debe hacer el backend en su primera versión para que un autor humano pueda
producir escenas de una novela con asistencia de modelos de lenguaje, manteniendo un
canon consistente y un presupuesto de contexto acotado.

### 1.2 Documentos de referencia

| Documento | Qué aporta a esta spec |
| --- | --- |
| `docs/definitions.md` | Vocabulario. Toda clase citada aquí sale de ahí |
| `docs/domain-knowledge.md` | Máquinas de estado y cardinalidades que el esquema implementa |
| `docs/architecture.md` | Features, agentes, skills, orquestación, memoria y tokens |
| `docs/verification.md` | Método de verificación de cada requisito |
| `AGENTS.md` | Requisitos técnicos cerrados; capas de contexto y política de degradación |
| `config/thresholds.yaml` | Fuente única de cifras: presupuesto por capa, umbrales de calidad y de deriva |

### 1.3 Alcance de la primera versión

**Dentro.** El bucle corto completo, de brief a canon consolidado, sobre una sola obra:

- Features `novel/`, `canon/`, `context/`, `quality/`, `process/`, `findings/`, `commons/`.
- Ensamblado de contexto con presupuesto y recuperación híbrida.
- Generación, crítica, verificación de continuidad, aceptación por el autor,
  consolidación y extracción de hallazgos.
- API REST completa sobre lo anterior, con su OpenAPI.

**Fuera.** Cada exclusión con su consecuencia, no solo su nombre:

| Fuera de v1 | Consecuencia asumida |
| --- | --- |
| Feature `replanning/`: deriva y replanificación rodante | El bucle largo no existe. El autor replanifica a mano editando el esquema |
| Propagación automática del retcon | v1 **responde** qué escenas quedarían invalidadas, pero no las marca `obsoleta` ni las reencola |
| Cola de trabajos persistida (`jobs`) | Los pasos se ejecutan de forma síncrona por endpoint. Ver RD-05 y §9.4 |
| Frontend | Esta spec es solo backend. El contrato lo fija el OpenAPI |
| Dimensiones de calidad marcadas `D` o `U` en `verification.md` | v1 no puntúa sentido de la maravilla, curva de tensión ni caracterización. Ver RF-QUA-02 |
| Escalones 3 y 4 de «Adaptación del modelo» | Sin fine-tune de modelo abierto ni embeddings propios |
| Multiobra, multiusuario y autenticación | Una obra por instancia. Una segunda novela es otro proceso con su propio `data/novel.db` |

**Por qué este corte.** v1 entrega el bucle que produce valor —una escena escrita, validada
y consolidada— y aplaza el que lo corrige a escala. Un bucle largo sobre un bucle corto que
todavía no funciona no tiene nada que replanificar.

### 1.4 Convenciones

Requisitos numerados y trazables: `RF-<feature>-nn` funcionales, `RNF-nn` no funcionales,
`RI-nn` de interfaz, `RD-nn` restricciones de diseño. La columna «Verifica» remite al
método de `docs/verification.md`. Las clases van con la grafía exacta de la ontología.

---

## 2. Descripción general

### 2.1 Perspectiva del producto

Proceso único FastAPI sobre un único fichero SQLite. Sin broker, sin caché externa, sin
servidor de base de datos. El backend orquesta a los agentes; los agentes no se invocan
entre sí. El cliente es el frontend, que no decide nada del canon.

### 2.2 Usuarios

| Usuario | Qué hace | Qué no puede hacer |
| --- | --- | --- |
| Autor humano | Define premisa y esquema, encarga escenas, acepta o rechaza, adopta hallazgos | — |
| Agentes | Generan, critican, verifican, extraen | Aceptar una escena, adoptar un hallazgo, escribir en el canon |
| Frontend | Lee y presenta, envía decisiones del autor | Resolver reglas de dominio |

### 2.3 Restricciones generales

Las de «Requisitos técnicos» de `AGENTS.md`, que no se renegocian: FastAPI sobre Python
3.12, SQLite con `sqlite-vec` como única persistencia, ventana de 100 000 tokens y modo de
autoría híbrido. Quedan excluidos Postgres, pgvector, Pinecone, Chroma, Redis, Celery y
cualquier ORM que oculte el SQL.

Y la de alcance, igual de cerrada: **un solo autor y una sola obra por instancia**, sin
multiusuario, sin multiobra y sin autenticación en v1. Una segunda novela es otra
instancia con su propio `data/novel.db`, nunca multi-tenancy en el esquema. De ahí salen
RNF-09, RNF-11, RNF-12 y RNF-13.

### 2.4 Supuestos y dependencias

- El proveedor del modelo expone una API con límites de tasa; v1 los absorbe con backoff.
- Los embeddings corren **en local**: la máquina del autor debe poder cargar el modelo.
- `config/thresholds.yaml` existe y es la fuente única de números (RNF-14). Los umbrales
  que hoy están en `null` se calibran con el histórico que v1 acumula; los que v1
  necesite antes de eso hacen fallar el arranque en voz alta, no se estiman.

---

## 3. Requisitos funcionales

### 3.1 `novel/` — estructura de la obra

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-NOVEL-01 | Crear y consultar `Obra`, `Parte`, `Capítulo` y `Escena` respetando la jerarquía de contención del árbol estructural | I |
| RF-NOVEL-02 | Crear y consultar las entidades narrativas: `Personaje`, `Voz`, `Arco`, `Hilo de trama`, `Lugar`, `Facción`, `Artefacto`, `Novum`, `Regla del mundo`, `Término canónico`, `Tema`, `Motivo`, `Voz narrativa` | I |
| RF-NOVEL-03 | Registrar `Evento` de la fábula y su relación N:M `se narra en` con `Escena`, mediante tabla puente | I |
| RF-NOVEL-04 | Una `Escena` expone su estado del ciclo: `planificada`, `en borrador`, `en revisión`, `aceptada`, `obsoleta`. **Ninguna transición fuera del diagrama de `domain-knowledge.md`** | A (model checking) |

### 3.2 `canon/` — verdad en el punto t

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-CANON-01 | Registrar `Hecho canónico` con su `Estatus de hecho` y la escena que lo establece | T |
| RF-CANON-02 | Implementar el ciclo de vida del hecho tal como lo dibuja `domain-knowledge.md`, sin transiciones extra | A (model checking) |
| RF-CANON-03 | Derivar `Snapshot de mundo` en un punto t: personajes vivos, ubicaciones, posesiones, relaciones, fecha ficcional. **Derivado, nunca texto bruto** | T |
| RF-CANON-04 | Mantener `Estado epistémico` por agente y hecho, con la escena en que lo aprende | T |
| RF-CANON-05 | Registrar `Promesa narrativa` con su estado y su ciclo de vida | A (model checking) |
| RF-CANON-06 | Detectar `Contradicción` entre hechos y exponerla con sus hechos implicados y gravedad | T |
| RF-CANON-07 | Consolidar una escena `aceptada`: **único punto que modifica el canon**. Un borrador rechazado no deja rastro | T (propiedades) |
| RF-CANON-08 | La consolidación es idempotente por `scene_id` + `version` y ocurre dentro de una transacción | T, A |
| RF-CANON-09 | Consultar qué escenas quedarían invalidadas por un `Retcon`, **sin aplicarlo** (ver §1.3) | T |
| RF-CANON-10 | `Refutado` y `Rota` son **terminales**: sin transición de salida. Si la trama vuelve sobre ello, se crea una entidad nueva que referencia a la anterior | A (model checking) |

### 3.3 `context/` — qué ve el modelo

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-CTX-01 | Ensamblar el contexto de una escena en siete capas, con las fuentes del diagrama «Ensamblado del contexto» | I |
| RF-CTX-02 | Repartir el presupuesto leyendo `config/thresholds.yaml`. Las siete capas más el margen suman exactamente el total declarado ahí. **Ninguna cifra en el código** | A |
| RF-CTX-03 | Contar los tokens **antes** de llamar al modelo | A (estático) |
| RF-CTX-04 | Un ensamblado que no cabe **lanza error**. Nunca trunca en silencio | T |
| RF-CTX-05 | Si una capa desborda, se comprime **esa** capa; nunca se roba presupuesto a otra ni se supera el total | T (propiedades) |
| RF-CTX-06 | Degradar en el orden Recuperado → Estilo → Local → Estado, parando en cuanto quepa. **Invariante y restricción de destino nunca se degradan** | T |
| RF-CTX-07 | Recuperar filtrando por las entidades del brief **y después** ordenar por similitud `vec0`. Nunca similitud sola | T, A |
| RF-CTX-08 | Construir el anticontexto con ventana deslizante de N escenas; N sale de `config/thresholds.yaml` | T |
| RF-CTX-09 | Exponer la jerarquía de compresión: resumen de acto, de capítulo, de escena y escena literal | I |
| RF-CTX-10 | Generar embeddings con modelo multilingüe local. Cada fila guarda `embedding_model` y `embedding_version`; al arrancar se compara con lo configurado y, si difiere, **falla en voz alta y exige reindexar** | T |
| RF-CTX-11 | El texto de obra y de canon entra en el prompt **marcado como datos**, delimitado y etiquetado como material narrativo, nunca en la posición de las instrucciones | T, A |

### 3.4 `quality/` — crítica y continuidad

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-QUA-01 | Verificar continuidad de un borrador contra el canon en t: fáctica, temporal, espacial y epistémica | T |
| RF-QUA-02 | Puntuar las dimensiones de calidad clasificadas `T` en `verification.md`. Las `D` y `U` quedan fuera de v1 | T |
| RF-QUA-03 | Emitir `Informe de crítica` con sus `Defecto`, cada uno ligado a la `Dimensión de calidad` que viola | T |
| RF-QUA-04 | Clasificar cada defecto como **local** o **sistémico** | T |
| RF-QUA-05 | Comparar cada puntuación con su umbral de `config/thresholds.yaml`. Sin fichero, el arranque falla en voz alta | T |

### 3.5 `process/` — ciclo y trazabilidad

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-PROC-01 | Crear `Brief de escena` con estado de entrada y `Restricción de destino`. **Mínimo: no se planifican beats** | I |
| RF-PROC-02 | Generar `Borrador` a partir del brief y el contexto ensamblado | T |
| RF-PROC-03 | Versionar el texto: cada `Versión` con su trazabilidad | T |
| RF-PROC-04 | `registrar-generacion` guarda modelo, prompt, contexto ensamblado y semilla **en toda llamada al modelo, sin excepción** | A |
| RF-PROC-05 | Orquestar el siguiente paso leyendo el estado de la escena, según la tabla de `architecture.md`. **Un agente no invoca a otro ni elige el siguiente paso** | A (estático) |
| RF-PROC-06 | Cortar el bucle al llegar al máximo de iteraciones de revisión por escena y **escalar al autor** | T |
| RF-PROC-07 | Solo el autor humano transiciona una escena a `aceptada`. Ningún agente puede | A (guardarraíles) |
| RF-PROC-08 | Registrar la **medida de deriva por escena** desde v1, aunque `replanning/` quede fuera: sin histórico no se puede calibrar el umbral después | T |
| RF-PROC-09 | Escribir en `training_samples`, **append-only y sin lectura en v1**: brief, contexto ensamblado, texto aceptado, si fue editado a mano y quién aceptó | T |
| RF-PROC-10 | **Ningún agente ejecuta instrucciones halladas en texto narrativo.** Una orden dentro de una escena es contenido de la novela, no una orden para el sistema | T (red-teaming) |

### 3.6 `findings/` — hallazgos del modo híbrido

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-FIND-01 | Tras consolidar, `Extracción` propone `Hallazgo`: hechos, promesas, motivos no previstos | T |
| RF-FIND-02 | Todo hallazgo entra como `provisional`. **Solo el autor lo adopta o lo descarta** | A |
| RF-FIND-03 | Implementar el ciclo de vida del hallazgo del diagrama, incluido `Conflictivo` | A (model checking) |
| RF-FIND-04 | La extracción es **el único punto de promoción** de memoria de corto a largo plazo | A |
| RF-FIND-05 | Ningún hallazgo llega al canon sin adopción explícita del autor, **incluido el que provenga de texto con instrucciones inyectadas**. Es el último cortafuegos | T, A |

---

## 4. Requisitos de interfaz

| Id | Requisito |
| --- | --- |
| RI-01 | API REST sobre HTTP con JSON, un router por feature, montados en `main.py` |
| RI-02 | Todo esquema de entrada y salida es un modelo Pydantic v2. Sin `dict` sueltos cruzando capas |
| RI-03 | OpenAPI publicado en `/openapi.json`; es el contrato del que deriva el cliente tipado |
| RI-04 | Errores de dominio mapeados a HTTP en un **handler central**, con excepciones propias |
| RI-05 | Endpoints de escritura en el canon idempotentes por `scene_id` + `version` |
| RI-06 | Las llamadas al modelo son asíncronas y con timeout explícito |
| RI-07 | Backoff exponencial con jitter ante límites de tasa del proveedor |

Superficie mínima por feature:

| Feature | Endpoints |
| --- | --- |
| `novel/` | CRUD de obra, partes, capítulos, escenas y entidades narrativas; consulta de eventos |
| `canon/` | Snapshot en t; hechos; estado epistémico; promesas abiertas; contradicciones; consolidar; simular retcon |
| `context/` | Ensamblar contexto de una escena; consultar presupuesto y reparto resultante |
| `quality/` | Verificar continuidad; puntuar borrador; consultar informe |
| `process/` | Crear brief; generar borrador; listar versiones; aceptar escena; consultar registro de generación |
| `findings/` | Listar hallazgos de una escena; adoptar; descartar |

---

## 5. Requisitos no funcionales

| Id | Requisito | Verifica |
| --- | --- | --- |
| RNF-01 | Ningún contexto ensamblado supera los 100 000 tokens, **nunca** | T (propiedades) |
| RNF-02 | Toda escritura al canon ocurre en transacción; `WAL` activado | A, I |
| RNF-03 | Migraciones numeradas, aplicadas en orden y **nunca editadas** tras commitear; el hash de lo aplicado se comprueba | I, T |
| RNF-04 | Las 21 preguntas de competencia se responden con el esquema vigente, una consulta por pregunta | T |
| RNF-05 | Toda versión es reproducible desde su registro de generación, salvo cambio del modelo por el proveedor | D |
| RNF-06 | La trayectoria de cada agente es consultable a posteriori | I |
| RNF-07 | Los nombres de las clases del código coinciden con los de la ontología, sin excepciones | A |
| RNF-08 | El lockfile no contiene ninguna dependencia vetada | A |
| RNF-09 | Una sola escena en generación a la vez. Dentro de ella, los pasos de solo lectura pueden correr en paralelo; los de escritura, no | T |
| RNF-10 | Un trabajo no arranca sin presupuesto de tokens en vuelo libre | T |
| RNF-11 | Ninguna tabla lleva `user_id` ni `tenant_id` | A, I |
| RNF-12 | v1 no tiene autenticación y la instancia escucha en `127.0.0.1` por defecto | I |
| RNF-13 | El pool de tokens en vuelo es un semáforo en proceso: no persiste ni se coordina con otras instancias | I |
| RNF-14 | `config/thresholds.yaml` es la **fuente única** de presupuesto por capa y de todo umbral. Ninguna cifra duplicada en documentos ni escrita suelta en el código; si falta un umbral que se necesita, el arranque falla en voz alta | A, I |

---

## 6. Restricciones de diseño

| Id | Restricción |
| --- | --- |
| RD-01 | Una feature por carpeta, rodaja vertical: `router.py`, `schemas.py`, `models.py`, `service.py`, `repository.py` |
| RD-02 | La lógica en `service.py`, el SQL en `repository.py`; el router solo traduce HTTP |
| RD-03 | `commons/` solo para lo que usan dos o más features. Ninguna clase de la ontología vive ahí |
| RD-04 | Una feature importa de `commons/` y del `service.py` de otra, **nunca de su `repository.py`**. Sin ciclos |
| RD-05 | v1 no persiste cola de trabajos: la máquina de estados existe, pero los pasos se ejecutan de forma síncrona y en proceso. El trabajo encolado es infraestructura y **no se ratifica en la ontología** |
| RD-06 | SQL explícito. Sin ORM |
| RD-07 | Nada de mocks en código de producción, ni temporales |
| RD-08 | **Contrato de agente cerrado**: recibe entrada, devuelve salida, y no conoce quién lo llama ni qué viene después. Ni espera, ni reintenta, ni consulta cola alguna |
| RD-09 | El avance del ciclo se deduce del **estado de la escena persistido**, no de variables en memoria ni de la pila de llamadas. Con RD-08, insertar una cola más adelante no toca a ningún agente |

---

## 7. Modelo de datos

El esquema implementa la tabla «Relaciones del dominio» de `definitions.md` **con sus
cardinalidades**, incluidas las propias del modo híbrido. Puntos que el esquema debe
hacer cumplir con restricciones, no con código:

- `Escena → Snapshot de mundo`, `Brief de escena → Escena` e `Informe de crítica →
  Borrador` son **1:1**: restricción `unique`.
- `Evento ↔ Escena` es **N:M**: tabla puente.
- `Escena → Hilo de trama`, `Escena → Promesa`, `Personaje → Hecho canónico` son N:M.
- Las cuatro máquinas de estado —`Escena`, `Hecho canónico`, `Promesa narrativa`,
  `Hallazgo`— se implementan tal cual, sin transiciones extra.
- Tablas virtuales `vec0` junto a las relacionales, en el mismo fichero.

**Dos estados sumidero sin salida declarada** en los diagramas de origen, que el esquema
no puede resolver por su cuenta: `Rota` en `Promesa narrativa` y `Refutado` en
`Hecho canónico`. Ver §9.3.

---

## 8. Criterios de aceptación

v1 se da por terminada cuando:

1. Las **21 preguntas de competencia** de `definitions.md` se responden con una consulta
   contra el esquema vigente, con la salvedad de la pregunta 4 (retcon), que v1 responde
   sin aplicar la invalidación.
2. Un ciclo completo funciona de punta a punta: brief → contexto ensamblado dentro de
   presupuesto → borrador → crítica → verificación → aceptación del autor → consolidación
   → hallazgos `provisional`.
3. Todas las filas de nivel artefacto de `verification.md` que caen dentro del alcance
   están cubiertas por su metodología.
4. Ningún ensamblado supera 100 000 tokens y ninguno se trunca en silencio.
5. `ruff`, el comprobador de tipos y la suite de pruebas pasan en CI.
6. La documentación queda al día en el mismo commit.

---

## 9. Decisiones y lo que queda abierto

Las ocho preguntas de la primera redacción están resueltas. Se conservan con su número
para que la trazabilidad no se pierda.

| # | Pregunta | Decisión | Dónde vive ahora |
| --- | --- | --- | --- |
| 9.1 | `config/thresholds.yaml` no existía | **Creado en esta spec.** Fuente única de umbrales de calidad, umbral de deriva y presupuesto por capa | `config/thresholds.yaml`, RNF-14 |
| 9.2 | Proveedor de embeddings | **Modelo multilingüe local**: `bge-m3`, alternativa `multilingual-e5-large` | RF-CTX-10, `architecture.md` § Embeddings y reindexado |
| 9.3 | Estados sumidero | **`Refutado` y `Rota` son terminales por diseño.** No se revive ninguno | RF-CANON-10, cambio de ontología pendiente |
| 9.4 | Presupuestos declarados dos veces | **Las cifras salen de los documentos.** Solo viven en `thresholds.yaml`, y ahí manda el valor en tokens, no el porcentaje de la Capa 3 | RF-CTX-02, RNF-14 |
| 9.5 | Alcance de v1 | `replanning/` sigue fuera, pero **la medida de deriva se registra por escena desde v1** | RF-PROC-08 |
| 9.6 | Cola de trabajos | **Síncrona y en proceso.** `Trabajo` no se ratifica: es infraestructura | RD-05, RD-08, RD-09 |
| 9.7 | Banco de ejemplos | **`training_samples` entra en v1**, append-only y sin lectura | RF-PROC-09 |
| 9.8 | Instrucciones inyectadas | **Sí, con tres reglas** de marcado, no ejecución y adopción por el autor | RF-CTX-11, RF-PROC-10, RF-FIND-05 |

### Lo único que queda por confirmar

**El corte de v1 de §1.3.** Todo lo demás está decidido; la spec permanece en
`en-revision` hasta que el autor confirme qué entra y qué no. En concreto sigue sin
ratificar dejar fuera `replanning/` y la propagación automática del retcon, sabiendo que
el autor replanifica a mano y que v1 solo *consulta* qué escenas quedarían invalidadas.

### Cambios de ontología que esta spec deja pendientes

No se pueden aplicar aquí: `definitions.md` y `domain-knowledge.md` son exportaciones de
documentos vivos y los edita el autor. Listados en `architecture.md` § «Pendiente de
llevar a la ontología» y repetidos aquí porque bloquean requisitos:

| Documento | Cambio | Bloquea |
| --- | --- | --- |
| `domain-knowledge.md` § Modelo de canon | `Refutado` → `[*]`: dibujar la arista de estado final | RF-CANON-02, RF-CANON-10 |
| `domain-knowledge.md` § Modelo de canon | `Rota` → `[*]`: dibujar la arista de estado final | RF-CANON-05, RF-CANON-10 |
| `definitions.md` Capa 3 | Quitar la columna «Presupuesto orientativo»; los números pasan a `thresholds.yaml` | RF-CTX-02 |

Mientras no se exporten, el model checking marcará `Refutado` y `Rota` como sumideros sin
salida declarada, y la Capa 3 seguirá dando porcentajes que contradicen al fichero.

### Decisiones abiertas que NO bloquean v1

- Si `Muestra de entrenamiento` entra en la ontología. v1 crea la tabla igualmente.
- Si la ventana de olvido del anticontexto se nombra como atributo de `Anticontexto`. El
  valor ya vive en `thresholds.yaml`.
- La definición de la medida de deriva. v1 la registra; el umbral se calibra con el
  histórico que v1 acumula, y hasta entonces `deriva.umbral` sigue en `null`.
