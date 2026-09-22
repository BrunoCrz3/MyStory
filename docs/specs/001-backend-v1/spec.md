---
estado: aprobada
aprobada-por: Bruno Cruz
fecha: 2026-09-22
---

# SRS 1 — Backend, primera versión

Especificación de requisitos de la primera versión del backend. Documento único: cubre
alcance, requisitos funcionales y no funcionales, interfaces, modelo de datos y criterios
de aceptación.

> **Estado: aprobada** el 2026-09-22. Las tres decisiones del corte de §1.3 quedan
> ratificadas, incluida la tercera: **v1 se entrega en fase de medición**. El plan de
> implementación vive en `plan.md`, junto a este documento.

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
- Ensamblado de contexto con presupuesto por petición, presupuesto en vuelo y
  recuperación híbrida.
- Generación, crítica, verificación de continuidad, aceptación por el autor,
  consolidación y extracción de hallazgos.
- Las comprobaciones de continuidad que se resuelven con una consulta contra estado que
  el canon ya guarda: inventario, relaciones, revelaciones, promesas, arcos, hilos y
  alcance temporal. Son baratas y no esperan a ningún umbral.
- La puerta de higiene de salida, que es determinista y corre antes de la crítica.
- API REST completa sobre lo anterior, con su OpenAPI.

**v1 mide; no cierra el paso.** Es la consecuencia más importante del corte y conviene
leerla dos veces: los umbrales de `config/thresholds.yaml` están en `null` y solo se
pueden calibrar con escenas ya aceptadas, que v1 es quien produce. Así que v1 entrega el
bucle con `medicion.cerrar_el_paso` en `false`: el crítico puntúa y registra, y quien
decide sigue siendo el autor (RF-PROC-07). Lo que cierra esa fase es RF-QUA-13, y esa
queda fuera. **v1 acumula el corpus; v2 calibra y suspende.**

**Fuera.** Cada exclusión con su consecuencia, no solo su nombre:

| Fuera de v1 | Consecuencia asumida |
| --- | --- |
| Feature `replanning/`: deriva y replanificación rodante | El bucle largo no existe. El autor replanifica a mano editando el esquema |
| Propagación automática del retcon | v1 **responde** qué escenas quedarían invalidadas, pero no las marca `obsoleta` ni las reencola |
| Cola de trabajos persistida (`jobs`) | Los pasos se ejecutan de forma síncrona por endpoint. Ver RD-05 y §9.4 |
| Frontend | Esta spec es solo backend. El contrato lo fija el OpenAPI |
| Dimensiones de calidad marcadas `D` o `U` en `verification.md` | v1 no puntúa sentido de la maravilla, curva de tensión ni caracterización. Ver RF-QUA-02 |
| RF-QUA-10, firma dramática duplicada | Necesita un umbral de similitud que nadie puede poner sin corpus. La escena repetida se detecta leyendo |
| RF-QUA-11, analepsis señalizada | Depende de que la tabla puente `Evento`↔`Escena` se escriba de verdad, y en v1 se crea pero nada obliga a poblarla |
| RF-QUA-12, deriva de estilo | No hay línea base congelada hasta que haya escenas aceptadas. Es circular igual que los umbrales |
| RF-QUA-13, medida de precisión y cobertura de los validadores | Necesita el corpus de defectos inyectados que v1 hace posible. **Mientras siga fuera, la fase de medición no puede cerrarse** |
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
3.12, SQLite con `sqlite-vec` como única persistencia, la ventana de contexto declarada en
`config/thresholds.yaml` y modo de autoría híbrido. Quedan excluidos Postgres, pgvector,
Pinecone, Chroma, Redis, Celery y cualquier ORM que oculte el SQL.

Y la de alcance, igual de cerrada: **un solo autor y una sola obra por instancia**, sin
multiusuario, sin multiobra y sin autenticación en v1. Una segunda novela es otra
instancia con su propio `data/novel.db`, nunca multi-tenancy en el esquema. De ahí salen
RNF-09, RNF-11, RNF-12 y RNF-13.

### 2.4 Supuestos y dependencias

- El proveedor del modelo expone una API con límites de tasa; v1 los absorbe con backoff.
- Los embeddings corren **en local**: la máquina del autor debe poder cargar el modelo.
- `config/thresholds.yaml` existe y es la fuente única de números (RNF-14). No todos los
  `null` se rellenan igual y el fichero lo marca clave a clave: unos se calibran por
  mutación de texto sobre escenas ya aceptadas, otros por el histórico de la propia obra,
  y otros no se miden en absoluto porque son una decisión del autor sobre coste o
  tolerancia. Ninguno se estima.
- **v1 arranca en fase de medición.** El arranque en frío es circular: para calibrar hacen
  falta escenas aceptadas, y para aceptarlas por el ciclo hace falta la capa de calidad.
  Se rompe por donde la ontología ya lo permite —quien acepta es el autor, no el umbral
  (RF-PROC-07)—: con `medicion.cerrar_el_paso` en `false` el crítico puntúa y registra sin
  suspender, y al cabo de unas cuantas escenas hay corpus y distribución con los que
  calibrar. Es una fase declarada: ponerlo en `true` con umbrales en `null` hace fallar el
  arranque en voz alta.

---

## 3. Requisitos funcionales

### 3.1 `novel/` — estructura de la obra

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-NOVEL-01 | Crear y consultar `Obra`, `Parte`, `Capítulo` y `Escena` respetando la jerarquía de contención del árbol estructural | I |
| RF-NOVEL-02 | Crear y consultar las entidades narrativas: `Personaje`, `Voz`, `Arco`, `Hilo de trama`, `Lugar`, `Facción`, `Artefacto`, `Novum`, `Regla del mundo`, `Término canónico`, `Tema`, `Motivo`, `Voz narrativa` | I |
| RF-NOVEL-03 | Registrar `Evento` de la fábula y su relación N:M `se narra en` con `Escena`, mediante tabla puente | I |
| RF-NOVEL-04 | Una `Escena` expone su estado del ciclo: `planificada`, `en borrador`, `en revisión`, `aceptada`, `obsoleta`. **Ninguna transición fuera del diagrama de `domain-knowledge.md`**. La extracción es el paso que sigue a `aceptada`, no un estado | A (model checking) |
| RF-NOVEL-05 | Registrar `Objetivo` y su relación `desea / necesita` con `Personaje` | I |
| RF-NOVEL-06 | Todo `Novum` tiene al menos una `Regla del mundo` con límites declarados, y toda `Parte / Acto` su función dramática y su punto de giro. Sin eso, RF-QUA-01 no tiene contra qué medir la plausibilidad especulativa | I, T |

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
| RF-CANON-11 | Todo `Hecho canónico` consolidado registra la escena que lo establece, y sus términos y entidades son localizables en el texto de esa escena. **Es lo único que ata el canon a la prosa de la que salió** | T |
| RF-CANON-12 | Todo cambio entre dos `Snapshot de mundo` consecutivos está respaldado por un `Hecho canónico` de la escena que los separa. Incluye posesiones y relaciones | T (propiedades) |
| RF-CANON-13 | Toda escena que paga una `Promesa narrativa` tiene una escena de apertura anterior | T (propiedades) |
| RF-CANON-14 | Consultar qué `Arco`, `Hilo de trama` y `Promesa narrativa` llevan más escenas sin avanzar ni pagarse que las declaradas en `config/thresholds.yaml` | T |
| RF-CANON-15 | Un `Hecho canónico` con alcance temporal abierto sigue vigente hasta que otro lo cierre, y se puede consultar qué sigue abierto en `t` | T |

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
| RF-CTX-12 | El anticontexto incluye las entidades ya presentadas y los hechos ya vigentes en `t`, para que la escena no reintroduzca lo presentado ni recapitule lo sabido | T |

### 3.4 `quality/` — crítica y continuidad

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-QUA-01 | Verificar continuidad de un borrador contra el canon en t: fáctica, temporal, espacial y epistémica. La epistémica va **en los dos sentidos**: ni usar lo que no se sabe ni ignorar lo que sí. Incluye que ningún personaje ausente o no vivo actúe, que ningún `Artefacto` cambie de poseedor sin escena que lo establezca y que ninguna `Revelación` llegue por debajo de su escena mínima permitida | T |
| RF-QUA-02 | Puntuar las dimensiones de calidad clasificadas `T` en `verification.md`. Las `D` y `U` quedan fuera de v1 | T |
| RF-QUA-03 | Emitir `Informe de crítica` con sus `Defecto`, cada uno ligado a la `Dimensión de calidad` que viola | T |
| RF-QUA-04 | Clasificar cada defecto como **local** o **sistémico** | T |
| RF-QUA-05 | Comparar cada puntuación con su umbral de `config/thresholds.yaml`. Sin fichero, el arranque falla en voz alta. Un umbral en `null` solo lo hace fallar si se usa para **cerrar el paso**: con `medicion.cerrar_el_paso` en `false` la puntuación se registra en el `Informe de crítica` y decide el autor (RF-PROC-07) | T |
| RF-QUA-06 | **Puerta de higiene antes de la crítica.** Un borrador con metatexto del modelo, nota, rechazo, truncamiento a mitad de frase, placeholder sin rellenar, mezcla de idiomas, formato roto o longitud fuera de objetivo **no entra al ciclo**. Determinista, sin modelo y antes del punto único de promoción | T |
| RF-QUA-07 | Tras cada corrección se re-ejecutan **todos** los validadores, no solo el que falló | A |
| RF-QUA-08 | Ninguna corrección empeora una dimensión que ya pasaba: se compara contra el historial de `Versión` | T |
| RF-QUA-09 | El borrador respeta la persona y el tiempo verbal declarados en `Voz narrativa`, y la escena tiene un solo POV | T |
| RF-QUA-10 | Detectar la escena que repite la firma dramática de otra ya aceptada: mismos hilos avanzados, mismas promesas tocadas, mismos hechos establecidos. **Fuera de v1** (§1.3) | T |
| RF-QUA-11 | Toda escena que narra un `Evento` anterior al punto `t` del discurso lo señaliza. **Fuera de v1** (§1.3) | T |
| RF-QUA-12 | El estilo de un borrador no se aleja de la línea base congelada de escenas aceptadas más de lo declarado. **Fuera de v1** (§1.3) | T |
| RF-QUA-13 | Medir precisión y cobertura de cada validador sobre un corpus de defectos inyectados en escenas aceptadas. **Es lo que cierra la fase de medición**: sin esta medida ningún umbral se puede poner con criterio. **Fuera de v1** (§1.3) | T |

### 3.5 `process/` — ciclo y trazabilidad

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-PROC-01 | Crear `Brief de escena` con estado de entrada y `Restricción de destino`. **Mínimo: no se planifican beats.** El esquema materializa además las `Restricción de destino` de las escenas `planificada` aún no escritas, no solo la de la próxima: sin ellas la deriva no tiene denominador | I |
| RF-PROC-02 | Generar `Borrador` a partir del brief y el contexto ensamblado | T |
| RF-PROC-03 | Versionar el texto: cada `Versión` con su trazabilidad | T |
| RF-PROC-04 | `registrar-generacion` guarda modelo, prompt, contexto ensamblado y semilla **en toda llamada al modelo, sin excepción** | A |
| RF-PROC-05 | Orquestar el siguiente paso leyendo el estado de la escena, según la tabla de `architecture.md`. **Un agente no invoca a otro ni elige el siguiente paso** | A (estático) |
| RF-PROC-06 | Cortar el bucle al llegar al máximo de iteraciones de revisión por escena y **escalar al autor** | T |
| RF-PROC-07 | Solo el autor humano transiciona una escena a `aceptada`. Ningún agente puede | A (guardarraíles) |
| RF-PROC-08 | Registrar la **medida de deriva por escena aceptada** desde v1, aunque `replanning/` quede fuera. Es el vector de tres componentes de `definitions.md` § Medida de la deriva, con numerador y denominador **por separado**, más la densidad de declaración y el `plan_hash` vigente | T |
| RF-PROC-12 | Persistir los **ingredientes** de cada medición, no solo el vector: qué `Restricción de destino` queda invalidada y por qué `Hecho canónico`, qué `Hilo de trama`, `Promesa narrativa` y `Hallazgo` quedan huérfanos, y qué promesas son inviables. **Cualquier definición futura de la medida debe poder recalcularse sobre el histórico de v1 sin regenerar nada** | T |
| RF-PROC-13 | Registrar cada cambio del `plan_hash` con el motivo que escriba el autor. En v1 es la única forma de replanificar, y esas decisiones son las etiquetas con las que se calibran los umbrales de deriva | T |
| RF-PROC-09 | Escribir en `training_samples`, **append-only y sin lectura en v1**: brief, contexto ensamblado, texto aceptado, si fue editado a mano y quién aceptó | T |
| RF-PROC-10 | **Ningún agente ejecuta instrucciones halladas en texto narrativo.** Una orden dentro de una escena es contenido de la novela, no una orden para el sistema | T (red-teaming) |
| RF-PROC-11 | Un borrador no satisface la restricción de destino de un brief posterior ni paga una promesa antes de su escena de pago declarada: la escena descubre *cómo*, no *hacia dónde* | T (propiedades) |

### 3.6 `findings/` — hallazgos del modo híbrido

| Id | Requisito | Verifica |
| --- | --- | --- |
| RF-FIND-01 | Tras consolidar, `Extracción` propone `Hallazgo`: hechos, promesas, motivos no previstos | T |
| RF-FIND-02 | Todo hallazgo entra como `propuesto`. **Solo el autor lo adopta o lo descarta** | A |
| RF-FIND-03 | Implementar el ciclo de vida del hallazgo del diagrama, incluido `Conflictivo` | A (model checking) |
| RF-FIND-04 | La consolidación es **el único punto de promoción** de memoria de corto a largo plazo; la extracción ocurre dentro de ese punto y ningún otro camino escribe en memoria larga. Un hallazgo `propuesto` es memoria larga, no canon | A |
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
| RNF-01 | Ningún contexto ensamblado supera `contexto.total` de `config/thresholds.yaml`, **nunca** | T (propiedades) |
| RNF-02 | Toda escritura al canon ocurre en transacción; `WAL` activado | A, I |
| RNF-03 | Migraciones numeradas, aplicadas en orden y **nunca editadas** tras commitear; el hash de lo aplicado se comprueba | I, T |
| RNF-04 | Las 21 preguntas de competencia se responden con el esquema vigente, una consulta por pregunta, salvo las tres salvedades del criterio 1 de §8 | T |
| RNF-05 | Toda versión es reproducible desde su registro de generación, salvo cambio del modelo por el proveedor | D |
| RNF-06 | La trayectoria de cada agente es consultable a posteriori | I |
| RNF-07 | Los nombres de las clases del código coinciden con los de la ontología, sin excepciones | A |
| RNF-08 | El lockfile no contiene ninguna dependencia vetada | A |
| RNF-09 | Una sola escena en generación a la vez. Dentro de ella, los pasos de solo lectura pueden correr en paralelo; los de escritura, no | T |
| RNF-10 | Un trabajo no arranca sin presupuesto libre de `en_vuelo.total`. Admisión **FIFO estricta**: ninguno adelanta a otro aunque quepa, y un trabajo cuya estimación supera el pool entero falla en voz alta al encolarse | T |
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
- Las siete relaciones que la homologación de la ontología añadió tienen tabla o clave:
  `Novum impone Regla del mundo` (1:N), `Novum nombra Término canónico` (1:N),
  `Regla del mundo configura Facción` (N:M), `Facción disputa Artefacto` (N:M),
  `Artefacto genera deuda Promesa narrativa` (1:N),
  `Hecho canónico proyecta Snapshot de mundo` (N:M),
  `Hecho canónico visible para Estado epistémico` (1:N) y
  `Contradicción se resuelve con Retcon` (N:1).
- Las cuatro máquinas de estado —`Escena`, `Hecho canónico`, `Promesa narrativa`,
  `Hallazgo`— se implementan tal cual, sin transiciones extra. Sus enumerados salen de
  `definitions.md` y van a un `CHECK`, no a código: `Escena` tiene cinco estados y la
  extracción no es uno de ellos; `Estatus de hecho` tiene cinco valores, con `implícito` y
  sin `descartado`; `Estado de hallazgo` empieza en `propuesto`, nunca en `provisional`.
- `Refutado` y `Rota` son sumideros **por diseño** y así están ya dibujados: sin
  transición de salida y con arista al estado final (RF-CANON-10).
- Tablas virtuales `vec0` junto a las relacionales, en el mismo fichero.

---

## 8. Criterios de aceptación

v1 se da por terminada cuando:

1. Las **21 preguntas de competencia** de `definitions.md` se responden con una consulta
   contra el esquema vigente, con tres salvedades que salen del corte de §1.3:
   - **4** (¿qué escenas quedan invalidadas por un retcon?): se responde, pero v1 no
     aplica la invalidación.
   - **19** (¿cuánta deriva hay y toca replanificar?): v1 responde la medida acumulada
     (RF-PROC-08); el «toca replanificar» no tiene respuesta mientras `deriva.umbral`
     siga en `null` y `replanning/` esté fuera.
   - **21** (¿qué escenas quedan obsoletas tras la última replanificación?): sin bucle
     largo no hay replanificación que consultar. Queda fuera de v1 entera.
2. Un ciclo completo funciona de punta a punta: brief → contexto ensamblado dentro de
   presupuesto → borrador → crítica → verificación → aceptación del autor → consolidación
   → hallazgos `propuesto`.
3. Todas las filas de nivel artefacto de `verification.md` que caen dentro del alcance
   están cubiertas por su metodología, incluidas `A-47` a `A-51`. **Y al revés: todo
   requisito de esta spec aparece citado por su identificador en al menos una fila.**
   Hoy no se cumple —veinticuatro requisitos no se citan en ninguna—, y no siempre
   porque falte cobertura: muchas filas citan el documento de origen (`AGENTS.md`,
   `architecture.md`) en vez del requisito. Cerrar esa traza en los dos sentidos es lo
   que convierte este criterio en comprobable por script y no a ojo.
4. **La instancia arranca en fase de medición y lo dice.** `medicion.cerrar_el_paso` en
   `false`, las puntuaciones se registran en el `Informe de crítica` y ninguna suspende.
   Que la fase esté abierta es un dato consultable, no un silencio (§ Puntos ciegos #15
   de `verification.md`).
5. Ningún ensamblado supera `contexto.total` y ninguno se trunca en silencio; ningún
   trabajo arranca sin presupuesto libre de `en_vuelo.total`.
6. `ruff`, el comprobador de tipos y la suite de pruebas pasan en CI.
7. La documentación queda al día en el mismo commit.

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

### El corte de v1, ratificado

**El corte de §1.3 queda aprobado el 2026-09-22.** Eran tres decisiones y las tres van:

1. **Dejar fuera `replanning/` y la propagación automática del retcon**, sabiendo que el
   autor replanifica a mano y que v1 solo *consulta* qué escenas quedarían invalidadas.
2. **Los diecinueve requisitos que entraron con la auditoría de modos de fallo.** Trece
   dentro —los que se resuelven con una consulta contra estado que el canon ya guarda,
   más la puerta de higiene— y cuatro fuera: RF-QUA-10 a RF-QUA-13.
3. **Que v1 se entregue en fase de medición**, con `medicion.cerrar_el_paso` en `false`.
   Es la consecuencia de dejar RF-QUA-13 fuera: v1 acumula el corpus con el que después
   se calibran los umbrales, y hasta entonces ninguna puntuación suspende una escena.
   Cerrar la fase es el primer trabajo de v2, no un pendiente de v1.

### Cambios de ontología que esta spec deja pendientes

No se pueden aplicar aquí: `definitions.md` y `domain-knowledge.md` son exportaciones de
documentos vivos y los edita el autor. Listados en `architecture.md` § «Pendiente de
llevar a la ontología» y repetidos aquí porque bloquean requisitos:

**Los tres que bloqueaban requisitos ya están exportados**: las aristas finales de
`Refutado` y `Rota`, y la retirada de los porcentajes de la Capa 3. RF-CANON-02,
RF-CANON-05, RF-CANON-10 y RF-CTX-02 dejan de estar bloqueados.

Lo que sigue pendiente **limita** requisitos, no los bloquea:

| Qué falta en la ontología | Qué limita |
| --- | --- |
| El anclaje textual de un `Hecho canónico` a la escena que lo establece | RF-CANON-11 se queda en presencia de términos: comprueba que el hecho habla de la escena, no que diga lo que ella dice |
| Los valores de `Hecho canónico.tipo`, que hoy es un atributo sin enumerar | RF-QUA-01 no puede derivar tripletas (entidad, atributo, valor) y se queda sin la mitad descriptiva |
| `Muestra de entrenamiento` no está ratificada como clase | RF-PROC-09 crea la tabla igualmente; la fila `A-46` verifica algo que la ontología no nombra |
| Que `Restricción de destino` declare las entidades que toca: `alcance` existe sin contenido especificado | Los componentes `canon huérfano` e `inviabilidad de pago` de RF-PROC-08 cuentan sin poder atribuir qué restricción recoge qué promesa. RF-PROC-12 guarda los ingredientes, así que se recalculan enteros cuando llegue |

### Decisiones abiertas que NO bloquean v1

- Si `Muestra de entrenamiento` entra en la ontología. v1 crea la tabla igualmente.
- Si la ventana de olvido del anticontexto se nombra como atributo de `Anticontexto`. El
  valor ya vive en `thresholds.yaml`.
- **La medida de deriva ya no está abierta**: se definió el 2026-09-22 como el vector de
  tres componentes de `definitions.md` § Medida de la deriva. Lo que sigue abierto son sus
  tres umbrales, que se calibran en modo sombra con las veces que el autor replanifica
  (RF-PROC-13) y hasta entonces siguen en `null` sin disparar nada.
