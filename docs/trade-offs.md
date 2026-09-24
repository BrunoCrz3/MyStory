# Trade-offs — decisiones de diseño con sus alternativas

Cada decisión de diseño relevante de este proyecto, explicada como decisión y no como
hecho consumado: qué opciones había sobre la mesa, con qué criterio se eligió y qué se
eligió. Lo que aquí se decide se aplica luego en `CLAUDE.md`, en el contexto semilla
(`docs/definitions.md`, `docs/domain-knowledge.md`) o en `docs/architecture.md`; este
documento guarda el porqué, no la regla operativa.

No confundir con `docs/registro-iteraciones.md`: allí se anota **qué cambió** tras un eval
o un contraejemplo; aquí se anota **por qué se eligió** una opción frente a otras.

---

## TO-001 — Canonicidad del contexto semilla

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `CLAUDE.md` § Contexto
semilla, `docs/definitions.md`, `docs/domain-knowledge.md`

### Problema

La ontología —`definitions.md` y `domain-knowledge.md`— vivía en dos sitios a la vez: un
documento vivo externo (artefacto de claude.ai) y una copia exportada en `docs/`. Hacía
falta decidir cuál de los dos manda, porque de ello depende si un agente puede editar la
ontología dentro del repositorio o solo leerla.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. El documento vivo manda** (statu quo) | La ontología se edita en el artefacto externo y se reexporta a `docs/`; ningún agente toca los dos ficheros. | Edición cómoda y visual; un único autor humano controla la puerta de entrada. | El cambio no deja rastro en git: el historial solo ve el resultado exportado, sin causa ni momento. Riesgo permanente de desincronía. Un agente no puede cerrar una tarea de ontología sin intervención manual fuera del repo. |
| **B. El repositorio manda** | La ontología se edita en `docs/`, en el repositorio, como `architecture.md`; el documento vivo deja de ser autoridad. | El cambio queda en un commit, con fecha, autor, diff y mensaje. Desaparece la desincronía porque solo hay una copia. Un agente puede completar el ciclo entero. | Se pierde la edición visual del artefacto. El cuidado de la ontología pasa a depender de la disciplina de commits. |
| **C. Repositorio canónico con espejo publicado** | Se edita en `docs/` y se republica el artefacto como vista de solo lectura. | Conserva la vista cómoda sin ambigüedad de autoridad. | Añade un paso de publicación a cada cambio, que es justo el paso que falla y produce desincronía. Coste sin beneficio para la evaluación. |

### Criterio

El proyecto se evalúa sobre el repositorio, y uno de los entregables exigidos es un
**registro de iteraciones**: un log de decisiones con causa y efecto, no un diario. El
historial de git es la evidencia natural de ese registro. Un cambio de ontología que
ocurre fuera del repositorio no produce esa evidencia. A eso se suma el criterio de
mantener **una sola fuente por dato**, que es el mismo que ya rige para las cifras
(`config/thresholds.yaml`) y para las instrucciones de agente (`CLAUDE.md`).

### Elección

**Opción B.** El repositorio es la fuente canónica de `docs/definitions.md` y
`docs/domain-knowledge.md`. Los documentos vivos externos dejan de mandar y dejan de
citarse en el archivo de instrucciones, hoy `CLAUDE.md` § Contexto semilla.

### Consecuencias

- Un agente **puede** editar los dos documentos del contexto semilla, dentro del ciclo de
  cambio que corresponda, sin pedir reexportación.
- Todo cambio de ontología deja entrada en `docs/registro-iteraciones.md` y va en su
  propio commit, con el registro actualizado en ese mismo commit.
- Los pasajes de `docs/architecture.md` y de `docs/specs/` que difieren la ontología al
  documento vivo quedan obsoletos y se reescriben cuando se toque la ontología.

---

## TO-002 — CLAUDE.md pasa a ser el archivo de instrucciones completo

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `CLAUDE.md`, `AGENTS.md`

### Problema

Las instrucciones vivían enteras en `AGENTS.md` y `CLAUDE.md` era una línea con un import.
El alcance § Claude Code convierte `CLAUDE.md` en entregable evaluable —«debe estar cuidado
y ser legible: es parte del examen»—, así que quien lo abriera para evaluarlo encontraba
una sola línea.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Statu quo** | `AGENTS.md` completo, `CLAUDE.md` con `@AGENTS.md`. | Codex, Cursor y Aider reciben las instrucciones de forma nativa, sin resolver imports. | El fichero que el alcance evalúa está vacío de contenido. |
| **B. Invertir** | `CLAUDE.md` completo, `AGENTS.md` un stub que apunta a él. | El fichero evaluado es el que lleva las reglas. Claude Code resuelve el import al revés sin coste. | Las herramientas que leen `AGENTS.md` de forma nativa no siguen una referencia en prosa: dejan de recibir las instrucciones automáticamente. |
| **C. Duplicar** | Los dos completos, mantenidos en paralelo. | Ninguna herramienta se queda fuera. | Dos copias de la misma regla divergen, y la que se queda vieja es la que alguien acaba leyendo. |

### Criterio

Cuál de los dos ficheros va a leer quien tenga que juzgar el proyecto, y cuál es el riesgo
que no se puede mitigar con disciplina. La divergencia de (C) no se mitiga: es estructural.

### Elección

**Opción B.** `CLAUDE.md` es la fuente canónica de instrucciones; `AGENTS.md` queda como
stub explícito que nombra el fichero y ordena abrirlo, sin duplicar ni una regla.

### Consecuencias

- Se acepta que un agente que no resuelva imports necesita abrir un fichero más. Es
  asumible porque este proyecto se trabaja con Claude Code.
- El stub **no** se deja vacío: dice qué es el proyecto, dónde están las reglas y por qué
  no están ahí.
- El límite de 300 líneas se hereda tal cual, ahora sobre `CLAUDE.md`.

---

## TO-003 — El PDF se genera con Playwright, no con una librería de PDF

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `CLAUDE.md` § Requisitos
técnicos, `.claude/mcp.json`

### Problema

El alcance exige entregar la novela de ejemplo como PDF en `/ejemplos/` aunque el formato
de lectura elegido sea web, y la regla 6 cierra el stack: meter una librería de PDF hay que
justificarlo.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. WeasyPrint** | HTML y CSS a PDF, desde Python. | Buena tipografía, control fino por CSS de impresión. | Dependencia nueva, y en Windows arrastra GTK y Pango como bibliotecas nativas. Es un motor de render distinto del que valida el browser MCP. |
| **B. ReportLab** | Construcción programática del PDF. | Sin dependencias nativas. | Hay que rehacer a mano el índice navegable y los enlaces de la ficha a los capítulos, que el alcance exige. No reutiliza nada de la lectura web. |
| **C. `page.pdf()` de Playwright** | Impresión desde el mismo navegador que ya se usa para validar. | No añade ninguna dependencia: el browser MCP del alcance §5a ya obliga a tener Playwright. El PDF sale del render que los validadores acaban de comprobar. Los enlaces internos salen gratis. | Descargar Chromium en CI. El control tipográfico es el de la impresión del navegador. |

### Criterio

Cuál añade menos superficie nueva, y cuál garantiza que lo que se entrega es lo que se
validó. El segundo criterio decide: con (A) o (B) se valida un motor de render y se entrega
otro, y ningún validador cubre esa grieta.

### Elección

**Opción C.** El PDF se exporta con `page.pdf()` desde el mismo render de la lectura web.

### Consecuencias

- `playwright` entra como dependencia de Python y Chromium se descarga en CI.
- El browser MCP de `.claude/mcp.json` y el exportador de PDF comparten motor; un cambio en
  la hoja de estilo de la lectura afecta a los dos a la vez, que es lo que se busca.
- Si algún día la lectura dejara de ser web, esta decisión se reabre.

---

## TO-004 — Varias novelas por instancia, sin multiusuario

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `CLAUDE.md` § Requisitos
técnicos, `docs/definitions.md` § Mapeo a la story bible

### Problema

La guía anterior fijaba «un solo autor y una sola obra por instancia», y resolvía la
segunda novela levantando otra instancia con su propio fichero. El alcance describe una
plataforma que lista novelas, las versiona y las sirve: varias por instancia.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Una novela por instancia** (statu quo) | Cada novela, su fichero y su proceso. | Esquema más simple, sin columna de partición. | `list_novels` y el historial de versiones dejan de tener sentido. Levantar un proceso por regalo no es una plataforma. |
| **B. `novel_id` desde la primera migración** | Toda tabla de dominio parte por novela. | Una sola instancia sirve todo. La columna está antes de que haya datos que migrar. | Toda consulta de dominio ha de acotar por `novel_id`, y olvidarlo es un fallo silencioso. |
| **C. Añadirlo cuando haga falta** | Empezar sin él y migrar después. | Menos trabajo ahora. | Obliga a reescribir todas las tablas y todas las consultas a la vez, con datos dentro. |

### Criterio

El coste de (C) no es lineal: crece con lo que ya se haya escrito. Una columna de partición
se pone antes de tener datos o no se pone.

### Elección

**Opción B**, con las cuentas **fuera de alcance**: `novel_id` en toda tabla de dominio,
y ninguna tabla lleva `user_id` ni `tenant_id`.

### Consecuencias

- La idempotencia de escritura a la story bible pasa a `novel_id` + `chapter_id` +
  `version`.
- El login del apartado opcional del alcance, si se hace, entra como migración posterior y
  no se anticipa con columnas vacías.
- Hace falta un validador que cace la consulta de dominio que no acota por `novel_id`; hoy
  no existe y queda anotado para `docs/verification.md`.

---

## TO-005 — El capítulo es la unidad atómica; desaparecen escena, beat y acto

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`,
`docs/domain-knowledge.md` · **Registrada a posteriori** (auditoría 001, hallazgo E1)

### Problema

La ontología anterior hacía de la `Escena` la unidad atómica, con `Beat` por debajo y
`Parte / Acto` por encima. El alcance opera sobre capítulos: el checkpoint es por capítulo,
el hook de validación es por capítulo, la regeneración es por capítulo y la marca de cambio
entre versiones es por capítulo.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Conservar la escena como subdivisión opcional** | El capítulo es la unidad de proceso; la escena sigue existiendo dentro. | No se pierde el grano fino de tiempo y lugar que la escena llevaba. | Un nivel sin estado, sin presupuesto y sin validador propios. Ninguna pregunta de competencia lo necesita, y el criterio de inclusión lo deja fuera. |
| **B. Eliminarla** | Solo obra y capítulo. Lo que la escena aportaba —POV, lugar, momento— sube al capítulo. | Un nivel menos que mantener, y coincide con lo que el alcance opera. | Hay que garantizar que el grano temporal fino no se pierde. |

### Criterio

¿Hay alguna operación del alcance que opere sobre ese nivel? Si no la hay, la clase no
entra: es el criterio de inclusión que el propio documento declara.

### Elección

**Opción B.** Se eliminan `Escena`, `Beat` y `Parte / Acto`. La función dramática que
justificaría el acto pasa a ser atributo del `Capítulo`, que es donde el validador de cierre
del arco la necesita.

### Consecuencias

- El grano temporal y espacial no se pierde: nunca lo llevaba la escena, que es discurso,
  sino el `Evento`, que es fábula y conserva momento, lugar y participantes. La relación
  `Evento ↔ Capítulo` sigue siendo N:M, así que un capítulo que salta de lugar o de momento
  se sigue modelando.
- A la longitud de capítulo que declara `config/thresholds.yaml` no cabría una subdivisión
  con presupuesto propio aunque se quisiera.

---

## TO-006 — Invalidación de restricción en vez de deriva vectorial

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`,
`config/thresholds.yaml` · **Registrada a posteriori** (auditoría 001, hallazgo E1)

### Problema

La ontología anterior medía la distancia entre lo escrito y el plan con un vector de tres
componentes —invalidación, canon huérfano, inviabilidad de pago—, cada uno con su umbral, y
disparaba una replanificación rodante al superarlos. Con diez capítulos planificados de una
vez y generados en una sola corrida, hacía falta decidir si eso seguía teniendo sentido.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Conservar el vector y la replanificación rodante** | Tres componentes, tres umbrales, cadencia periódica. | Detecta tres formas distintas de que el plan deje de describir la obra. | Los tres umbrales se calibraban con etiquetas de cuándo el autor replanificaba, y **el autor humano ya no está en el bucle**: no hay quien etiquete. Tres umbrales permanentemente en `null` no disparan nada. |
| **B. Reducir a invalidación booleana** | ¿Queda alguna restricción de destino pendiente que el canon ya ha vuelto imposible? Sí o no. | Determinista, sin umbral, calculable desde el primer día. | Pierde las señales de canon huérfano e inviabilidad de pago. |
| **C. Conservar el vector con umbrales fijados a ojo** | Mismo modelo, números inventados. | Dispara algo. | Un umbral que nadie puede justificar es peor que no tenerlo: da falsa confianza y nadie sabe cuándo está mal puesto. |

### Criterio

¿Se puede calibrar, y puede dispararse, en este alcance? Una medida que nadie puede
calibrar no dispara nada: es peso muerto con aspecto de rigor.

### Elección

**Opción B.** Entra `Invalidación de restricción`, booleana y determinista, y
`Replanificación de capítulos pendientes`, disparada por ella y nunca por cadencia.

### Consecuencias

- Desaparece la clase `Deriva` y el bloque `deriva:` de `config/thresholds.yaml`.
- Los dos componentes que se pierden presuponían un horizonte largo donde las promesas se
  acumulan; con diez capítulos, el validador `cierre_arco` cubre lo que importa de ellos.
- La replanificación solo toca capítulos aún no escritos, nunca uno ya aceptado.

---

## TO-007 — El verificador de continuidad es un grupo de validadores, no un rol

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`
· **Registrada a posteriori** (auditoría 001, hallazgo E1)

### Problema

La ontología anterior tenía un rol `Verificador de continuidad` que contrastaba la escena
contra el canon. El alcance nombra cuatro roles —entrevistador, planner, writer y
editor/critic— y hacía falta decidir si la continuidad merecía un quinto.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Rol LLM propio** | Un agente que lee el capítulo y juzga si contradice el canon. | Puede cazar contradicciones parafraseadas que ninguna consulta ve. | Gasta del presupuesto de tokens concurrentes, añade un juicio no calibrado, y duplica peor lo que Lean ya **demuestra**. |
| **B. Conjunto de validadores programáticos** | La continuidad se decide contra datos estructurados: hechos en la story bible por SQL, cronología en Lean. | Determinista y barato. Lo que decide es demostrable, no opinable. | La contradicción parafraseada se le escapa; queda para la parte semántica de `consistencia_factica`. |

### Criterio

Se prefiere el validador programático aunque cubra la afirmación a medias: media cobertura
barata y determinista vale más que cobertura entera que depende de un juicio.

### Elección

**Opción B.** `Verificador de continuidad` deja de ser `Rol` y pasa a nombrar el grupo de
validadores programáticos del hook de capítulo.

### Consecuencias

- Los roles quedan en cinco: entrevistador, planificador, redactor, editor/crítico y
  extractor.
- La parte que un rol LLM habría cubierto no se pierde del todo: vive en el componente
  semántico de `consistencia_factica`, que sí puntúa el editor.

---

## TO-008 — `perfil` como tercer nivel de palabras prohibidas

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`,
`config/thresholds.yaml` · **Registrada a posteriori** (auditoría 001, hallazgo E1)

### Problema

El alcance §7 exige tres niveles de listas de palabras prohibidas pero solo nombra dos:
globales y por novela. Había que definir el tercero.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Por género** | Una lista por género literario. | Fácil de derivar del brief. | El género no predice qué léxico molesta: una novela de aventuras para un niño y otra para un adulto comparten género y no vocabulario. |
| **B. Por perfil del destinatario** | Derivada de `Destinatario.edad` y `Ocasión.tipo`. | El sistema la calcula solo, y es la que el comprador no puede enumerar. Cierra sobre texto ya escrito la contradicción edad↔tono que el brief solo detecta antes. | Hay que mantener la tabla de perfiles. |
| **C. Por nombres reales del texto libre** | Extraer del texto libre los nombres que no deben aparecer. | Muy específica de cada encargo. | Es lo que ya hace el nivel `novela`: sería el mismo nivel con otro nombre. |

### Criterio

¿Cuál de los tres no puede enumerar el comprador y el sistema sí puede derivar solo? Un
nivel que el comprador ya cubre no añade protección.

### Elección

**Opción B**, con los tres niveles nombrados `global`, `perfil` y `novela`.

### Consecuencias

- Sin este nivel, una novela infantil quedaría protegida exactamente igual que una para
  adultos: solo por la lista global de insultos.
- Los tres niveles se aplican en conjunto y gana el más restrictivo.

---

## TO-009 — El formato de lectura es web, y el PDF es un export de ella

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`,
`docs/domain-knowledge.md`, `CLAUDE.md` · **Sustituye** a la decisión provisional de dejar
la ontología válida para los dos formatos (auditoría 001, hallazgo C5)

### Problema

El alcance §2 ofrece dos formatos de entrega, web o PDF interactivo, y exige el PDF en
`/ejemplos/` en cualquier caso. La ontología se escribió sirviendo a los dos y dejando la
decisión pendiente, lo que dejó a `CLAUDE.md` afirmando que la lectura era web mientras los
dos documentos de ontología decían que seguía sin decidirse.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Web, con el PDF como export** | La novela se lee en el frontend; el PDF sale del mismo render. | El frontend React ya está en el stack. La petición de cambio en página es la experiencia que el alcance describe como más rica. El PDF entregado es lo que el browser MCP acaba de validar. | Hay que construir la lectura web, no solo la entrevista. |
| **B. PDF interactivo** | Se entrega el PDF; el frontend queda solo para la entrevista. | Menos frontend. | La petición de cambio se va a un formulario o CLI, fuera del documento. Cada versión necesita su página de novedades. La validación visual por browser MCP pierde su objeto natural. |
| **C. Dejarlo abierto** (statu quo) | La ontología sirve a los dos. | No hay que decidir. | Es lo que produjo la contradicción del hallazgo C5. Una indecisión declarada se arrastra a la implementación. |

### Criterio

Cuál de los dos aprovecha lo que ya está decidido, y cuál garantiza que lo entregado es lo
validado. Ambos apuntan a (A): el frontend existe, y el export del render validado cierra
la grieta entre lo que se comprueba y lo que se manda.

### Elección

**Opción A.** Lectura web; el PDF de `ejemplos/novela-ejemplo.pdf` se exporta de ese render
con `page.pdf()` (TO-003).

### Consecuencias

- **`Página de novedades` se elimina de la ontología.** Qué capítulos cambiaron ya vive en
  la marca del vínculo entre versión y capítulo; presentarlo al abrir el export es
  maquetación, no vocabulario del dominio. Resuelve además una de las clases huérfanas que
  la auditoría 001 detectó en C12.
- El `origen` de la `Solicitud de cambio` deja de distinguir formatos y pasa a registrar
  desde qué capítulo o fragmento se pidió.
- Si algún día la entrega dejara de ser web, esta decisión y TO-003 se reabren juntas.

---

## TO-010 — «Cliente» se divide en Comprador y Lector

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/definitions.md`,
`docs/domain-knowledge.md` · **Origen:** auditoría 001, hallazgos C2 y D4

### Problema

`Cliente` nombraba dos cosas a la vez: la clase de Capa 1 «quien encarga y paga la novela»
y la mitad de `Lector / Cliente` en Capa 5, «quien pide cambios sobre la novela publicada».
La ontología prohíbe expresamente que un nombre tenga dos significados.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Declarar que son la misma persona** | Una sola clase `Cliente` que paga y luego lee. | Una clase menos. | Es falso en el caso normal: el regalo lo lee el destinatario, y el alcance contempla que sea él quien pida cambios. |
| **B. Dividir en `Comprador` y `Lector`** | `Comprador` paga y configura; `Lector` lee y pide cambios, y puede ser el comprador o el destinatario. | Refleja lo que pasa de verdad y deja `Cliente` fuera del vocabulario. | Dos clases donde había una y media. |

### Criterio

Un nombre con dos significados obliga a cada lector a resolver la ambigüedad por contexto,
y tarde o temprano alguien la resuelve al revés.

### Elección

**Opción B.** `Comprador` para quien paga y configura; `Lector` para quien lee y pide
cambios. **«Cliente» deja de ser término de la ontología.**

### Consecuencias

- `Lector` no es una clase nueva de persona sino un papel: lo ocupa el `Comprador` o el
  `Destinatario`, y quién lo ocupa en cada novela es un dato, no una decisión del modelo.
- Fuera de la ontología, «cliente» sigue siendo palabra corriente del castellano y no hay
  que perseguirla: «el cliente tipado del OpenAPI» o «el cliente del modelo» no son este
  concepto.

---

## TO-011 — Petición de cambio del lector: el hecho es canónico, el fragmento es atajo

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/architecture.md`, feature `versioning/`

### Problema

El alcance §2 permite al lector «seleccionar un fragmento **o un hecho**» y pedir un cambio. El `Análisis de impacto` solo sabe trabajar sobre un `Hecho`.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Solo fragmento** | El lector marca texto y el sistema infiere el hecho. | La interacción más natural. | La inferencia no tiene validador: si resuelve al hecho equivocado, se regeneran los capítulos equivocados y nada lo detecta. |
| **B. Solo hecho** | La ficha expone los hechos y el lector edita uno. | Determinista de punta a punta. | Obliga al lector a traducir «esto no me suena» a «este hecho». |
| **C. Las dos, (A) resolviendo a (B)** | El fragmento propone un hecho candidato y el lector confirma. | Conserva la interacción natural sin inferencia silenciosa. | Un paso más de confirmación. |

### Criterio

Dónde cae la ambigüedad. Con (A) la resuelve un modelo sin nadie que lo compruebe; con (C) la resuelve el lector con un clic.

### Elección

**Opción C.** Flujo: selección → hecho candidato → **confirmación del lector** → `Análisis de impacto` sobre la relación `usa` → retcon → regeneración dirigida → gate completo → versión nueva, conservando la anterior.

---

## TO-012 — Orquestación: código propio en FastAPI

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/architecture.md`, feature `process/`

### Problema

El harness necesita un bucle que decida qué rol corre a continuación. Hay cuatro formas de obtenerlo y el alcance §5d condiciona la elección.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Código propio** | Máquina de estados en FastAPI, llamadas con el SDK `anthropic`. | La máquina de estados es nuestra, que es lo que permite demostrar la correspondencia con la spec TLA+. | Hay que escribir el bucle. |
| **B. Tool Runner del SDK** | `client.beta.messages.tool_runner` automatiza petición → tool → bucle. | Menos código. | Habría que especificar en TLA+ un bucle que no controlamos. |
| **C. Claude Agent SDK** | El harness de Claude Code como librería. | Trae tools y gestión de contexto. | Tools de fichero, bash y sandbox que este sistema no necesita y que la resistencia a inyección tendría que cerrar. |
| **D. Managed Agents** | Anthropic aloja el bucle y el sandbox. | Nada que desplegar. | Ídem, y la spec TLA+ pierde su objeto. |

### Criterio

El alcance §5d exige que el README explique qué estado o transición del código implementa cada acción de la especificación. Esa correspondencia solo se sostiene si la máquina de estados es propia.

### Elección

**Opción A**, con el SDK `anthropic` para las llamadas y `strict: true` en las tools, que es lo que da el «schema validado» del alcance §3.

---

## TO-013 — Modelo por rol

**Fecha:** 2026-09-23 · **Estado:** decidida por el autor · **Afecta a:** `config/models.yaml` ▸ previsto, `docs/architecture.md`

### Problema

Cinco roles con exigencias distintas y un tope de coste implícito. Además, el LLM-as-judge no puede correr en el mismo modelo que el Redactor sin arrastrar sesgo de autopreferencia.

### Verificación previa

Los identificadores se comprobaron contra la documentación oficial, no contra memoria ni contra la tabla cacheada de la skill `claude-api`. **`claude-opus-5` ha pasado a legacy**: lo sustituye `claude-opus-5-5`, que además es más barato —$4/$20 frente a $5/$25—. La comprobación cambió la decisión.

### Elección

| Rol | Modelo | Effort |
| --- | --- | --- |
| Entrevistador | `claude-sonnet-5` | medium |
| Planificador | `claude-opus-5-5` | medium |
| Redactor | `claude-opus-5-5` | high |
| Editor (corrección) | `claude-opus-5-5` | high |
| Judge (puntuación) | `claude-sonnet-5` | high |
| Extractor | `claude-sonnet-5` | low |

**El judge se separa del Editor.** Puntuar y corregir son dos cosas y solo la primera arrastra el sesgo: la corrección no lo hace porque su salida vuelve a pasar por los validadores. Se descartó subir el judge a `claude-fable-5-1` —$10/$50 en cada capítulo— y bajar el Redactor a Sonnet, que sería degradar el producto para arreglar un problema de medición.

### Consecuencias

- **Punto ciego declarado**: el judge es menos capaz que el Redactor. Lo cubre la comparación con el revisor humano, que existe exactamente para eso.
- `id` y `effort` por rol viven en `config/models.yaml` ▸ previsto. `max_tokens` es una cifra del presupuesto y se queda en `config/thresholds.yaml`.

---

## TO-014 — Un solo contador de intentos por capítulo

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `config/thresholds.yaml`, `formal/tla/` ▸ previsto

### Problema

Hay dos fuentes de reescritura —fallo de validador y coincidencia de palabra prohibida— y el peor caso y la invariante TLA+ dependen de cómo se cuenten.

### Opciones

| Opción | Peor caso por capítulo | Invariante TLA+ |
| --- | --- | --- |
| **A. Contadores independientes** | 6 generaciones | Dos variables y su producto |
| **B. Uno acumulativo** | **4 generaciones** | Una desigualdad sobre un contador |
| **C. Guardrail anidado en cada intento** | 9 generaciones | Dos variables anidadas |

### Criterio

El peor caso acota el gasto y la forma de la invariante determina lo que TLC tiene que explorar.

### Elección

**Opción B.** Peor caso **4 generaciones por capítulo, 40 por novela**. `guardrail.max_reescrituras: 2` deja de ser contador y pasa a **sublímite**: dos pasadas consecutivas sin limpiar el texto detienen la generación e informan, sin esperar al tercer intento, porque un modelo que no quita una palabra en dos pasadas no la va a quitar en la tercera. Un contador, dos condiciones de parada.

Cifras, las tres `[decisión]`: `max_intentos_capitulo: 3`, `max_reescrituras: 2`, `max_intentos_trabajo: 3`.

---

## TO-015 — Sin `sqlite-vec` en v1

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `config/thresholds.yaml`, feature `context/`

### Criterio

El dato decide. Diez capítulos de 1.000–1.500 palabras son unos 25.000 tokens; la capa Recuperado tiene 30.000 de presupuesto. **La novela entera cabe.** Un índice vectorial existe para elegir qué traer cuando no cabe todo.

### Elección

Solo filtro relacional. La skill `sqlite-vec` se queda instalada y el bloque `embeddings` se marca como no usado en v1, de modo que reactivarlo sea **quitar una restricción** y no tomar una decisión nueva.

### Consecuencias

**Caber no es enviar.** La capa Recuperado sigue filtrando por las entidades del brief de capítulo: mandar la novela entera en cada llamada chocaría con el tope de tokens concurrentes, que es compartido por todas las novelas de la instancia.

---

## TO-016 — Lean: gate bloqueante más aviso incremental

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `formal/lean/` ▸ previsto, `config/thresholds.yaml`

### Problema

El alcance §5c exige que un fallo de Lean impida publicar. Queda abierto si además corre antes, por capítulo.

### Criterio

Los invariantes son de seguridad: una violación en un prefijo de la cronología lo es también en la novela completa. Detectarla en el capítulo 3 en vez de al terminar el 10 ahorra siete capítulos de trabajo.

### Elección

El **gate de publicación** es lo único que bloquea, sobre la cronología completa. Además corre un **chequeo incremental por capítulo, no bloqueante**, sobre la cronología hasta `t`, que emite `Score` de aviso y entra en el informe de crítica.

### Consecuencias

- **El fichero generado no importa Mathlib.** Es una restricción de diseño del generador, no una preferencia: es lo que mantiene el build en segundos.
- **El timeout queda en `null` hasta medirlo.** No hay toolchain Lean en la máquina de desarrollo y la estimación de coste es razonada, no medida. Claves nuevas: `formal.lean_timeout_segundos`, `formal.lean_incremental`.
- Lean es dependencia de **toolchain**, no de Python: se declara en el README y en CI, no en `pyproject.toml`.

---

## TO-017 — Opcionales: servidor MCP de solo lectura y agente de seguridad

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `backend/app/mcp_server/` ▸ previsto, `.claude/agents/` ▸ previsto

### Elección

Se implementan dos de los ocho opcionales del alcance.

| Opcional | Decisión | Motivo |
| --- | --- | --- |
| Servidor MCP de solo lectura | **Sí**, con FastMCP como plugin del FastAPI existente | Sus cinco tools son consultas que la story bible ya responde; no añade infraestructura |
| Agente de seguridad | **Sí**, en `.claude/agents/`, salida a `docs/security-report.md` | Único opcional que produce evidencia evaluable aparte, y cubre un punto ciego real: hoy nadie prueba la resistencia a inyección del texto libre |
| Linters de prosa | No | `calidad_prosa` ya mide lo mismo con validador propio |
| Linter de edición manual | No | Presupone una edición manual que no está en el flujo |
| Tools de escritura sobre MCP | No | Requiere el servidor y añade superficie de escritura sin necesidad |
| Invariantes Lean adicionales, spec TLA+ del MCP | No | Profundizan donde ya hay cobertura |

El login ya quedó fuera en TO-004.

---

## TO-018 — La tabla de validadores vive en `verification.md`

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/verification.md`, `docs/architecture.md`

### Criterio

El alcance §5 pide la tabla como entregable de `/docs` y `verification.md` existe para eso. Duplicarla en `architecture.md` crearía la tercera copia, y una de las tres se quedaría vieja.

### Elección

Tres documentos, tres papeles: `definitions.md` Capa 4 define **qué mide** cada dimensión; `verification.md` dice **cómo se comprueba y qué pasa si falla**; `architecture.md` lleva solo el **diagrama de puntos de ejecución** y el enlace.

---

## TO-019 — Capítulos en serie; paralelo solo en lo de solo lectura

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** feature `process/`, `config/thresholds.yaml`

### Hechos que deciden

**Uno**, `contexto.total` y `en_vuelo.total` valen lo mismo: una llamada que use la ventana entera agota el pool, así que el paralelismo entre capítulos es 1 por aritmética. **Dos**, y anterior: el contexto del capítulo N incluye el snapshot al cierre de N−1, de modo que generarlos en paralelo es **semánticamente imposible**, no solo caro.

### Elección

Capítulos estrictamente en serie. En paralelo, solo los validadores programáticos del hook, que no llaman al modelo y no tocan el pool.

### Consecuencias

- **El pool es guardarraíl, no planificador.** Admisión FIFO estricta; un trabajo cuya estimación supera `en_vuelo.total` **falla al encolarse** en vez de esperar un hueco que no va a existir.
- El pool es **compartido entre las novelas de la misma instancia**, y la admisión FIFO es lo que lo reparte.
- **Corrección pendiente en `config/thresholds.yaml`**: el comentario dice que «la ventana la fija el proveedor». Con 1M de contexto real en los modelos elegidos, los 100.000 son un tope nuestro.

---

## TO-020 — Correspondencia TLA+ ↔ código como dato comprobable

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `formal/tla/` ▸ previsto, feature `process/`

### Opciones

| Opción | En qué consiste | En contra |
| --- | --- | --- |
| **A. Tabla en prosa en el README** | Alguien escribe qué acción corresponde a qué función. | Se queda vieja en silencio: es el fallo que la auditoría 001 encontró tres veces. |
| **B. Convención de nombres** | Cada acción TLA+ se llama igual que su transición en el código. | Lo detecta un humano leyendo, o no lo detecta nadie. |
| **C. Tabla de transiciones como dato** | El orquestador declara `(estado, condición) → estado` como dato; un test lo compara con el `.tla`. | Hay que mantener el extractor. |

### Elección

**Opción C con B como convención**, y la tabla del README **generada** desde ese dato. Un test falla si divergen, lo que convierte «la spec corresponde al código» de afirmación a comprobación.

### Consecuencias

- **Restricción sobre el `.tla`**: debe exponer los nombres de acción y sus pares origen → destino de forma extraíble trivialmente, para que el test no tenga que interpretar TLA+.
- Un módulo, las dos máquinas —`Novela` y `Capitulo`— dentro, porque la transición `Escribiendo → Detenida` las acopla.
- La validación por trazas de ejecución contra la spec queda como complemento para `verification.md`.

---

## TO-021 — La skill reutilizable del alcance es `personalizacion-natural`

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `backend/app/skills/` ▸ previsto, feature `context/`

### Problema

El alcance §3 exige «una skill reutilizable» como parte del harness. Las ocho de `.claude/skills/` son de desarrollo: ninguna corre en producción. La primera propuesta —`consultar-story-bible`— se rechazó porque es una **tool con schema**, no una skill.

### Criterio

Tres condiciones: que sea **método y no datos**, que la carguen **varios roles**, y que exista un **validador que mida si cargarla sirvió de algo**. Se consideraron *adecuación del tono* —subcaso de la elegida— y *evitar prosa genérica* —solo dos roles—.

### Elección

**`personalizacion-natural`**, en `backend/app/skills/personalizacion-natural/SKILL.md`, formato Agent Skill sin code execution.

- **El nombre coincide con el score `personalizacion_natural` que la mide**, por la regla «un concepto, un nombre en cada ámbito»: es lo que permite leer un eval y saber qué prompt tocar.
- **No va en `.claude/skills/`**: eso es documentación para el agente que escribe código; esta corre en producción y se empaqueta con el backend. `backend/app/skills/` es hermana de las features y no es una feature —sin router, sin clases—, la misma excepción declarada que `mcp_server/`.
- **Contenido**: qué distingue un elemento tejido de uno insertado; el reparto entre capítulos, que es donde más se falla; las tres formas reconocibles de personalización forzada. **No contiene datos de ninguna novela.**
- **La carga el harness en la capa Invariante**, donde la Capa 3 sitúa la memoria procedural, y **solo en los tres roles que la usan**: Planificador, Redactor y Editor.

### Consecuencias

- **La capa Invariante deja de ser idéntica para todos los roles**: se compone y se presupuesta por rol.
- Nunca se degrada, porque la Invariante no se degrada, y su versión forma parte de la `Versión de prompt`, así que un cambio en la skill es atribuible en los evals.
- **Punto ciego declarado**: la frontera entre método y rúbrica no es nítida. La skill dice **qué hacer**; la rúbrica dice **cómo se puntúa** —escala, anclas y pesos— y vive solo en el prompt del judge, para que el Redactor no optimice contra ella. **Ninguna ancla numérica aparece nunca en la skill.** Nada detecta esa deriva salvo leer la skill.

---

## TO-022 — Mapa de features: las nueve, y ningún opcional añade una

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/architecture.md`, `CLAUDE.md`

### Elección

Se confirman las nueve features de `CLAUDE.md` más `commons/`. Ninguno de los dos opcionales aprobados añade feature.

- El **servidor MCP** no es dueño de ninguna clase: expone por otro protocolo lo que los `service.py` ya resuelven. Va en `backend/app/mcp_server/` como **adaptador**, sin `models.py` ni `repository.py`, declarado como **excepción explícita** a «una feature es dueña de clases» para que la regla no se erosione por costumbre.
- El **agente de seguridad** no es runtime: es un agente de desarrollo sobre el repo y la API, vive en `.claude/agents/` ▸ previsto y su salida es `docs/security-report.md`.
- Se mantiene el nombre de sección «Anatomía de una feature», que `CLAUDE.md` cita literalmente en dos sitios.

---

## TO-023 — Alcance de la spec TLA+: infraestructura abstraída, reanudación en `Init`

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `formal/tla/` ▸ previsto

### Problema

Dos cosas que la spec tiene que resolver y que se confundieron al principio: el tercer contador —`max_intentos_trabajo`, de fallo de infraestructura— y la reanudación desde checkpoint que el alcance §5d exige, junto a una liveness que dice que toda generación termina.

### Elección, en dos mitades

**El contador de infraestructura se abstrae, y la abstracción se declara en el `.tla`.** Un 429 reintentado no mueve ningún estado del capítulo; modelarlo multiplicaría el espacio que TLC explora sin añadir propiedad que demostrar. Lo que sí hay que demostrar —que agotar los intentos lleva a `Detenida` y que `Detenida` es terminal— se demuestra igual. **Una abstracción declarada es honesta; una omisión silenciosa no.**

**La reanudación se modela en el predicado `Init`, no como acción.** `Detenida` es el fin deliberado tras agotar intentos; una caída de infraestructura no es `Detenida`, es que el proceso desaparece en mitad de `Escribiendo`. Por eso no hay arista entre ellos. El `.tla` describe **una ejecución que empieza en cualquier estado válido**: capítulos `1..k` en `Aceptado`, checkpoint en `k`, y el capítulo `k+1` —el que estuviera a medias— **normalizado a `Pendiente`**.

### Consecuencias

- TLC explora **todos** los puntos de caída posibles, no uno elegido a mano.
- La invariante «la reanudación no duplica ni pierde capítulos» se formula en dos mitades: el conjunto de aceptados es siempre un **prefijo contiguo** —eso descarta perder uno—, y **la aceptación de un capítulo ocurre a lo sumo una vez por versión** —eso descarta duplicarlo—. No se formula sobre la escritura del texto: los reintentos producen varios borradores en la misma versión, y eso es correcto.
- La **fairness se declara solo sobre las acciones internas**: con una acción externa, la liveness quedaría condicionada a una hipótesis sobre el mundo y no sobre el harness.
- La normalización de `k+1` a `Pendiente` **aparece en la tabla de transiciones de TO-020** como la función que implementa `Init`.
- **Residuo declarado**: ninguna traza individual exhibe caída→reanudación. Se demuestra que toda reanudación válida es correcta, no que la reanudación ocurra.

---

## TO-024 — Prompts: el repo es la fuente, Langfuse recibe cada versión

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/architecture.md`, CI

### Problema

El alcance §6 pide «los prompts versionados en Langfuse, de forma que la iteración de tuning muestre qué versión produjo cada resultado». Gestionarlos en Langfuse los saca del ciclo de cambio del repositorio y hace que el arranque dependa de la red.

### Elección

**Híbrido.** El repo es la fuente; un **comando idempotente de sincronización** publica cada prompt en la gestión de prompts de Langfuse como versión nueva, etiquetada con el hash de git; cada generación se vincula a esa versión. Sin red, el backend usa el fichero local.

### Consecuencias, que son los guardarraíles

- **La sincronización corre en CI y a mano antes de cada eval, nunca al arrancar.** Si corriera al arrancar, el arranque volvería a depender de la red.
- **Es idempotente por hash**: solo publica si ese hash no está ya, o cada ejecución crearía una versión nueva idéntica y el historial dejaría de significar nada.
- **El span registra el hash del fichero realmente usado**, no solo el identificador de versión de Langfuse. Si discrepan —sincronización fallida, despliegue a medias— la discrepancia es detectable en vez de silenciosa. Sin esto, el sistema puede atribuir un resultado a un prompt que no lo produjo, que es justo el fallo que el versionado existe para impedir.
- **La ejecución de evals comprueba antes de empezar que el hash de cada prompt existe en Langfuse, y falla si no.** Sin esa puerta, un eval de tuning local quedaría mal atribuido.

---

## TO-025 — El PDF se exporta bajo demanda, una vez por versión

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** feature `versioning/`

### Elección

El **gate valida el render** en cada publicación; **generar el fichero PDF no ocurre en el gate**. El PDF se pide por endpoint o por comando, siempre sobre una versión ya publicada, se genera **una vez por versión** y se guarda, porque las versiones son inmutables.

### Criterio

Generar el PDF no aporta nada a la decisión de publicar y añade segundos de Chromium a cada versión, incluidas las regeneraciones por cambio del lector, que pueden ser muchas.

### Consecuencias

- En el momento de generarlo corre **`paridad_pdf_web`**, que comprueba que el PDF contiene lo mismo que la web.
- `ejemplos/novela-ejemplo.pdf` se genera así una vez y se commitea.

---

## TO-026 — `render_visual` corre vía Playwright MCP en el gate

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** feature `versioning/`, `.claude/mcp.json` ▸ previsto

### Problema

El alcance pide dos cosas que se parecen y no son la misma: §5a, un validador de runtime que valida visualmente **vía browser MCP** y devuelve el fallo al rol correspondiente; §Claude Code, que `.claude/mcp.json` tenga un browser MCP para que **Claude Code** inspeccione la lectura y que ese uso se documente en `/docs`.

### Opciones para el validador del gate

| Opción | Tipo | Coste | Cumple §5a |
| --- | --- | --- | --- |
| **A. Script Playwright directo** | Programático | Segundos, cero tokens | No literalmente: no usa el browser MCP |
| **B. Harness como cliente del Playwright MCP, llamadas guionizadas** | Programático | Segundos, cero tokens | Sí |
| **C. Agente LLM que navega** | No programático | Tokens por publicación | Sí, pero un juicio de modelo en una puerta bloqueante |

### Elección

**Opción B para el gate; opción C, en desarrollo, para `docs/browser-mcp.md`.** (B) es programático, cuesta cero tokens y usa el browser MCP de forma literal; el proceso servidor en la ruta es asumible porque el despliegue en producción está fuera de alcance. (C) queda descartada para el gate porque un juicio de modelo ahí significa que una publicación puede fallar por razones que nadie puede reproducir.

### Enrutado del fallo

La regla es determinista y se decide **consultando la story bible primero**:

| Síntoma | Comprobación | Destino |
| --- | --- | --- |
| Falta la dedicatoria, falta una entrada del índice | ¿Está el dato en la story bible? **No** | Problema de datos: vuelve al rol dueño del dato |
| Ídem | ¿Está el dato? **Sí**, pero no se renderiza | Bug de maquetación: **detiene la generación con informe** |
| Solapamiento, desborde, enlace roto | — | Bug de maquetación: detiene con informe |

Un bug de maquetación **no consume intentos de capítulo**: reintentar no lo arregla, porque el defecto está en el código y no en el texto.

### Consecuencias

- **Residuo declarado**: el vocabulario de aserciones queda acotado por las tools que exponga el servidor Playwright MCP. Cada aserción declara qué tool le da la evidencia, y la que no se pueda expresar **se declara no cubierta** en vez de debilitarse en silencio o colarse por un canal lateral.
- Un script comprueba lo que alguien enumeró: un fallo visual no previsto —contraste ilegible, solapamiento en móvil— no lo caza ninguna de las tres opciones automáticas. Eso es lo que cubre (C) en desarrollo, y por eso no es decoración del entregable sino el complemento real del punto ciego.

---

## TO-027 — La entrevista es híbrida: formulario para lo estructurado, conversación para lo que no cabe en un campo

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** feature `intake/`, página `entrevista`

### Opciones

| Opción | En qué consiste | En contra |
| --- | --- | --- |
| **A. Conversacional multivuelta** | El Entrevistador lleva el diálogo entero. | Los campos cerrados —edad, ocasión, tono, extensión— se normalizan mal y `schema_valido` falla tarde y muchas veces. |
| **B. Formulario guiado** | El frontend pide todos los campos; el modelo solo extrae del texto libre. | Los recuerdos y las anécdotas no caben en un campo. |
| **C. Híbrida** | Formulario para lo estructurado, conversación para lo demás. | Dos caminos que mantener. |

### Elección

**Opción C.** El `Brief de novela` se valida contra el schema **campo a campo según se rellena**, así que el `Dato faltante` es una consulta trivial y no una inferencia.

### Consecuencias

- **La detección de contradicciones se parte en dos.** Reglas **deterministas** entre campos —edad frente a tono, edad frente a género—, que son las que el alcance §1 nombra; y detección **semántica** por el Entrevistador para lo que surge del texto libre y de los recuerdos.
- El formulario recoge también **las palabras y temas prohibidos del nivel `novela`**, que el comprador declara en la configuración.

---

## TO-028 — La story bible se versiona por vigencia, no por instantánea

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/architecture.md` § Story bible, feature `canon/`, `docs/definitions.md` (pendiente)

### Problema

«La versión anterior se conserva siempre» se había entendido solo sobre el **texto**. Si un retcon sobrescribe el `Hecho` en su sitio, la versión anterior queda sin la base que la sostiene y se rompen tres cosas a la vez: Lean no se puede volver a ejecutar sobre ella porque su cronología ya no existe, `query_story_bible` no puede responder por versión, y la marca de capítulos modificados pierde la referencia contra la que comparar.

### Opciones

| Opción | En qué consiste | A favor | En contra |
| --- | --- | --- | --- |
| **A. Instantánea por versión** | Cada versión copia entera la story bible que la sostiene. | Consultar es trivial: se lee la copia. | La duplicación crece con cada regeneración. Y **pierde el linaje**: `Retcon` ya es una clase con `hecho antiguo` y `hecho nuevo`, y bajo instantánea ese vínculo solo se recupera diferenciando dos copias. |
| **B. Vigencia por versión** | `Hecho` lleva `version_desde` y `version_hasta`; el retcon cierra el viejo y abre el nuevo. | Sin duplicación, linaje explícito, y las tres cosas rotas se arreglan con una cláusula `WHERE`. | Toda consulta tiene que llevar la versión, y olvidarla falla en silencio. |

### Criterio

Cuál de las dos conserva el **linaje** del retcon, que la ontología ya modela. `Estado de hecho` tiene `retconeado` y `refutado`: un hecho no se borra, cambia de estado. El modelo ya iba hacia la vigencia.

### Elección

**Opción B.** `version_desde` y `version_hasta` sobre `Hecho` y sobre el puente `hecho_capitulo`, que es lo que sostiene el análisis de impacto.

### Consecuencias

- **La trampa, nombrada**: una consulta que olvide la versión devuelve «lo vigente» en silencio, que es el mismo fallo que olvidar `novel_id`. **`novel_id` y `version` son parámetros obligatorios de toda consulta de dominio, sin valor por defecto**, y eso es comprobable: va a `verification.md` como validador candidato junto al de `novel_id`.
- Una regeneración **no borra nada**: la versión nueva sustituye a la anterior como vigente, y la anterior queda consultable entera —texto, capítulos y hechos—. Los capítulos que el retcon marca `Obsoleto` lo quedan **para la versión nueva**, no para la anterior.
- `version_desde` y `version_hasta` son **atributos nuevos de `Hecho`**. Aplicados a la ontología en RI-006.

### Ampliación (RI-006)

Al llevar la decisión a la ontología aparecieron dos consecuencias que esta entrada no había desarrollado, y las dos son parte de la misma elección:

**El uso también se versiona.** No basta con versionar el `Hecho`: el puente `hecho_capitulo` lleva su propio `version_desde` y `version_hasta`, porque un capítulo puede dejar de mencionar un hecho al regenerarse sin que el hecho cambie. Sin eso, «qué capítulos usaban este hecho en la versión 2» devuelve los de la versión vigente, y tanto el análisis de impacto como la marca de capítulos modificados responden por la versión equivocada. **Invariante**: la vigencia de una fila de `hecho_capitulo` está contenida en la de su `hecho`.

**`Retconeado` pasa a ser estado terminal.** El ciclo de vida de `Hecho` tenía la arista `Retconeado → Adoptado`, «nueva versión fijada». Bajo vigencia eso es falso: el retcon **cierra** el hecho viejo y **abre otro**, que es una fila distinta, y el vínculo entre ambos lo guarda `Retcon` —que gana dos filas de relación con su cardinalidad, `cierra` y `abre`—. Resucitar el viejo destruiría el linaje, que es el mismo argumento por el que `Refutado` ya era terminal.

**Y una regla que se deriva de las dos**: el `Estado de hecho` describe **la versión vigente, no la historia**, así que toda consulta por versión se resuelve con la vigencia y **nunca con el estatus**. En la versión anterior, un hecho que hoy está `retconeado` seguía siendo verdad.

---

## TO-029 — El plan de verificación gana dos niveles: Obra y Entregables

**Fecha:** 2026-09-23 · **Estado:** decidida · **Afecta a:** `docs/verification.md`, `.claude/skills/plan-de-verificacion/SKILL.md`

### Problema

La skill `plan-de-verificacion` clasifica toda afirmación en dos niveles y su paso 3 es
binario: *artefacto* si lo que puede fallar es el código, *proceso* si lo que puede fallar
es el comportamiento del agente. Al regenerar `verification.md` sobre el alcance de
storyMaker, esa partición deja dos conjuntos de afirmaciones sin sitio.

El primero es la novela. «La prosa repite n-gramas», «el último capítulo paga las promesas
abiertas» y «ningún hecho personal sobre el destinatario está inventado» no son
comportamiento del agente: son propiedades del **producto** que alguien de fuera va a leer,
y se establecen con evidencias distintas —un `SELECT` sobre el canon, una rúbrica, una
demostración en Lean— de las que establecen que el harness reanuda sin duplicar capítulos.
Mezclarlos en «proceso» produce una tabla donde el lector no encuentra su pregunta.

El segundo son los entregables. El alcance evalúa explícitamente el PDF de ejemplo, la
documentación de `/docs`, el vídeo, `.claude/` y `.env.example`. Ningún validador de código
ni de salida los mira, y un proyecto sin ellos no aprueba.

### Opciones

| Opción | A favor | En contra |
| --- | --- | --- |
| Dejar dos niveles y meter obra y entregables en «proceso» | No toca la skill | 84 de las 228 filas quedan en un cajón que no responde a la pregunta que encabeza la tabla. La distinción entre «el agente se porta bien» y «la novela está bien» es justo la que el alcance evalúa por separado |
| Cuatro niveles, enmendando la skill | Cada tabla responde una pregunta; el lector busca primero su nivel | La skill deja de ser la de dos niveles con la que se generó el documento anterior |
| Cuatro niveles sin tocar la skill | Rápido | El documento dejaría de derivar de su método, que es lo único que impide que un plan de verificación sea una lluvia de ideas ordenada |

### Criterio

Un plan de verificación vale por su método, no por su longitud: si el documento se separa
de la skill, la próxima regeneración no tiene de dónde salir. Y el método no se rompe al
añadir un nivel —los seis principios, las letras `T/A/I/D/U` y el catálogo cerrado siguen
valiendo igual—; lo que se rompía era una partición pensada para un sistema que no entrega
nada a un tercero.

### Elección

**Cuatro niveles, y se enmienda la skill.** El paso 3 pasa a ser una tabla de cuatro:
*Artefacto*, *Proceso*, **Obra** —el artefacto que el sistema produce para un tercero— y
**Entregables** —el repositorio frente a su encargo—. Los dos nuevos se declaran opcionales:
**Obra** hace falta en cuanto lo producido es el producto y no un efecto sobre el estado del
sistema; **Entregables**, cuando el encargo exige artefactos del repositorio.

La plantilla del documento gana las dos secciones, y las columnas nuevas de
`verification.md` —punto de ejecución, score en Langfuse, prioridad y coste— **no** entran
en la skill: son de este proyecto, no del método. La skill ya admitía columnas propias, y el
`verification.md` anterior lo demostraba con tres.

### Consecuencias

El documento se lee por pregunta y no por origen del fallo: «¿es correcto el código?»,
«¿se comporta el harness?», «¿es correcta la novela?», «¿está entregado lo que se pidió?».

La partición no es gratis: la frontera entre Proceso y Obra hay que decidirla fila a fila, y
hay casos que admiten las dos lecturas —`P-01`, que el capítulo no altere su restricción de
destino, es comportamiento del redactor y es propiedad del capítulo—. La regla que se aplicó:
**si la afirmación se puede comprobar leyendo la novela publicada, es Obra**; si hace falta
mirar cómo se produjo, es Proceso.

Y la skill queda con un método que otro proyecto puede no necesitar entero. Se declara ahí
mismo: los dos niveles nuevos son condicionales, y un sistema que no entrega nada a un
tercero sigue teniendo un plan de dos tablas.

---

## TO-030 — Un worker asíncrono único en proceso, con la cola en SQLite

**Fecha:** 2026-09-24 · **Estado:** decidida · **Afecta a:** `specs/spec1.md` RF-PROC-01 a RF-PROC-03, feature `process/`

### Problema

Generar diez capítulos en serie dura minutos, no segundos, así que no cabe dentro de una
petición HTTP. Y el stack está cerrado: no hay Redis ni Celery, y añadirlos sería
renegociar `CLAUDE.md` § Requisitos técnicos por comodidad.

### Opciones

| Opción | A favor | En contra |
| --- | --- | --- |
| `BackgroundTasks` de FastAPI | Una línea | Muere con la respuesta. No hay nada que reanudar ni nada que consultar |
| `asyncio.create_task` suelto | Sobrevive a la respuesta | Muere con el proceso y no deja estado: la reanudación de TO-023 sería imposible |
| **Worker asíncrono único en proceso, con tabla de trabajos en SQLite** | Sobrevive al reinicio, da el checkpoint gratis y serializa por novela | Hay que escribirlo, y obliga a prohibir más de un worker de uvicorn |

### Criterio

Lo que decide no es la elegancia sino la reanudación: el alcance §4 exige checkpoint por
capítulo y TO-023 la modela en el predicado `Init`. Una cola que no sobrevive al proceso
convierte ese requisito en literatura.

### Elección

**Worker asíncrono único**, arrancado en el `lifespan`, que reclama trabajos con una
actualización condicional atómica —un solo `UPDATE ... WHERE estado = 'pendiente'` que gana
un único consumidor—. Al arrancar, `orquestador.estado_inicial` lee el checkpoint y reanuda.

### Consecuencias

**Arrancar con más de un worker de uvicorn queda prohibido y documentado en el README.** No
es una recomendación: el pool de `en_vuelo.total` es un semáforo **en proceso**, y dos
procesos lo duplicarían en silencio sin que ninguna métrica lo delatara. Es el punto ciego
#5 de `verification.md` visto desde el otro lado.

La prueba que lo cierra es concreta y va en F1: **matar el proceso a mitad del capítulo 5
—incluido un reinicio por `--reload`— y comprobar que al rearrancar continúa por el 5**, sin
duplicar ni perder capítulos.

Y se gana algo que no se buscaba: la serialización por novela de TO-019 sale del diseño en
vez de tener que imponerse, porque un consumidor único no puede escribir dos capítulos a la
vez.

---

## TO-031 — El progreso se consulta por sondeo, no por eventos del servidor

**Fecha:** 2026-09-24 · **Estado:** decidida · **Afecta a:** `specs/openapi.yaml`, `specs/spec1.md` RF-PROC-05

### Problema

Una generación de minutos necesita que el frontend muestre progreso. Las dos formas
habituales son sondear un recurso o abrir un `text/event-stream`, y la elección tiene que
poder expresarse en el contrato, porque de ahí sale el cliente tipado.

### Opciones

| Opción | A favor | En contra |
| --- | --- | --- |
| **Sondeo de un recurso `Generacion`** | Tipado por el generador de cliente sin escribir nada a mano; trivial de servir | Latencia de hasta un intervalo; peticiones que no traen novedad |
| SSE | Empuje inmediato, sin peticiones vacías | OpenAPI 3.1 lo **describe**, pero ningún generador produce de ahí un cliente útil |
| Las dos | Lo mejor de cada una | Dos caminos que mantener en la semana en que hay dos días |

### Criterio

`CLAUDE.md` § Persistencia, backend y frontend dice que el cliente tipado se deriva del
OpenAPI y que **los tipos no se escriben a mano dos veces**. SSE obliga a escribir el
parseo de eventos a mano, así que rompe la regla justo en la parte del frontend que más
cambia.

### Elección

**Sondeo**, y SSE a post-demo. El recurso `Generacion` lleva **su propio
`intervalo_sondeo_segundos`** en vez de un `Retry-After` en un 200, y un booleano
**`es_terminal`** que dice cuándo dejar de preguntar.

### Consecuencias

El cliente **no deduce la terminalidad del nombre del estado**, que es la forma habitual de
que un frontend se quede sondeando para siempre cuando se añade un estado nuevo. El
contrato lo dice y el backend lo calcula.

El coste del sondeo es irrelevante aquí y conviene decir por qué, para que no se lea como
descuido: una instancia, un usuario, un intervalo de segundos y una generación de minutos.
En otro contexto la cuenta saldría al revés.

---

## TO-032 — Errores RFC 9457 con catálogo cerrado, y 409 sin `Idempotency-Key`

**Fecha:** 2026-09-24 · **Estado:** decidida · **Afecta a:** `specs/openapi.yaml`, `commons/` handler central

### Problema

`verification.md` `A-36` exige un handler central de errores, pero nadie había fijado qué
devuelve. Y `POST /generaciones` es la petición cara del sistema: la que más fácil se
dispara dos veces y la que peor se perdona.

### Opciones

| Opción | A favor | En contra |
| --- | --- | --- |
| **RFC 9457 `problem+json`, catálogo cerrado** | `type` discriminable, campos de contexto, estándar | Hay que sobrescribir el 422 de FastAPI |
| `{"detail": "..."}` de FastAPI | Cero trabajo | El frontend acaba parseando prosa para decidir |
| Envoltorio propio | Control total | Reinventa un estándar que ya existe |

### Elección

**RFC 9457 con catálogo cerrado de doce tipos**, y **el 422 de validación de FastAPI
sobrescrito** para que también sea `problem+json`: toda respuesta de error tiene la misma
forma, sin excepciones, y el test de conformidad lo cubre.

Para la petición repetida, **409 `generacion-en-curso`** con el `generacion_id` vivo en el
cuerpo, **sin cabecera `Idempotency-Key`**. Una solicitud de cambio que llegue con una
generación en curso devuelve el mismo 409 con el mismo tipo.

### Consecuencias

El catálogo va **cerrado** a propósito: uno abierto degenera en un campo de texto en dos
semanas, y entonces vuelve a no poder discriminarse.

Se rechaza `Idempotency-Key` porque la idempotencia del sistema ya está donde los documentos
la ponen —la escritura a la story bible por `novel_id` + `chapter_id` + `version`— y esa es
la que protege del trabajo duplicado de verdad. Añadir una segunda en HTTP sería un
mecanismo nuevo para un problema que una instancia de un usuario no tiene.

Y se prefiere 409 a devolver un `202` con la generación en curso, que parecería más amable:
un `202` silencioso ante un segundo clic esconde que no se ha lanzado nada, y «no se ha
lanzado nada nuevo» es justo lo que hay que saber antes de esperar diez minutos.

---

## TO-033 — No hay identidad, y el brief lleva datos personales

**Fecha:** 2026-09-24 · **Estado:** decidida · **Afecta a:** `specs/openapi.yaml`, `specs/spec1.md` § 2.2 y § 6.1

### Problema

`Comprador` y `Lector` son clases de la ontología con identificador, pero TO-004 deja las
cuentas fuera y `A-53` prohíbe `user_id` en cualquier tabla. ¿De dónde sale la identidad de
quien llama?

### Opciones

| Opción | En contra |
| --- | --- |
| **De ningún sitio: el `Comprador` es un dato del brief** | Quien conoce el UUID lee la novela |
| Cabecera `X-Comprador-Id` | Autenticación a medias: da apariencia de aislamiento sin la garantía |
| Cookie de sesión | Igual, y además mete por la puerta de atrás el `user_id` prohibido |

### Elección

**Ninguna identidad.** El `Lector` ya está definido como «un papel, no una persona
distinta», así que no hay principal que autenticar; y `Comprador.identificador` entra en el
cuerpo del brief como dato. Quien conoce el UUID de la novela la lee, y eso es la
consecuencia declarada de no tener cuentas, no un descuido: lo contiene el arranque en la
interfaz local de PO-4.

### Consecuencias, que son de privacidad

**El brief contiene datos personales reales del destinatario** —nombre, edad, rasgos,
recuerdos— y esos datos **viajan en los prompts y quedan en las trazas de Langfuse**. Tres
reglas salen de ahí, y van a la spec como RNF-16 a RNF-18:

1. `Comprador.identificador` es una cadena **opaca**: nunca un correo ni un nombre.
2. Todos los briefs de ejemplo, de prueba y de documentación usan **datos ficticios**.
3. **La retención de las trazas queda como pregunta abierta** post-demo. Declararla es lo
   que impide que se convierta en una decisión por omisión.

---

## TO-034 — El cliente del modelo se prueba con un `Protocol` y un doble que vive en `tests/`

**Fecha:** 2026-09-24 · **Estado:** decidida · **Afecta a:** `commons/llm/`, `tests/`

### Problema

`CLAUDE.md` regla 8 prohíbe mocks en `backend/app/`, «ni siquiera temporales». Y el
redactor no se puede llamar de verdad en cada prueba: cuesta dinero, tarda y no es
determinista.

### Elección, en tres capas

1. **Costura por `Protocol`** en `commons/llm/`, con **una sola** implementación de
   producción. El doble vive en **`tests/dobles/`** y se inyecta con el override de
   dependencias de FastAPI. No hay mock en el código de producción porque el doble no está
   en él: la regla se cumple por dónde vive el fichero, no por cómo se llama.
2. **Casetes grabados** de respuestas reales, que cubren la serialización y el conteo de
   tokens —que es donde un doble escrito a mano miente—.
3. **Un test en vivo** marcado `@pytest.mark.real`, **excluido de CI**, para pasarlo a mano
   antes de una demo.

### Consecuencias

Los casetes **se graban solo si la credencial está en el entorno**; si no está, esa capa
queda pendiente y **no bloquea** al resto, que es lo que permite que alguien clone el repo y
tenga la suite verde sin credenciales.

Y se graban **con las cabeceras de autenticación eliminadas**, pasando el escaneo de
secretos antes de cualquier commit. Un casete es una respuesta HTTP grabada: es exactamente
el sitio por donde una clave entra en un repositorio sin que nadie la escriba a mano.

---

## TO-035 — Decisiones de la API tomadas por el agente al escribir la spec 1

**Fecha:** 2026-09-24 · **Estado:** **decidido por el agente — revisar** · **Afecta a:** `specs/openapi.yaml`, `specs/spec1.md`

### Qué se decidió sin preguntar

El grill de la spec 1 se limitó a ocho preguntas por la restricción de tiempo. Lo que sigue
se fijó eligiendo la opción recomendada, y se marca para que se revise antes de aprobar la
spec, no después de implementarla.

| Decisión | Qué se eligió | Por qué |
| --- | --- | --- |
| Forma de los recursos | `/novelas/{novel_id}` como raíz, con `generaciones`, `versiones`, `versiones/{n}/capitulos`, `ficha`, `portada`, `hechos`, `solicitudes-cambio` y `export` colgando | Sigue las relaciones de contención de la ontología: todo cuelga de la novela porque nada existe sin ella |
| Paginación | `GET /novelas` pagina con `limite` y `desplazamiento`; **`listarCapitulos` no pagina** | Paginar los capítulos obligaría al lector a esperar entre uno y otro. Diez capítulos son unos cientos de kilobytes |
| Export | `POST` para generar y `GET` para descargar, en la misma ruta | Un `GET` que tarda diez segundos y genera un fichero miente sobre lo que es. El `POST` repetido devuelve `200` con lo que ya hay, porque las versiones son inmutables |
| Validación del brief | Endpoint propio `POST /briefs/validacion` que **no crea nada** | El formulario necesita validar antes de decidir si crea. Y `valido: false` va en un `200`, porque un brief incompleto es el resultado normal de la primera pasada, no un error de la petición |
| Tabla de trabajos | Se añade una tabla de trabajos que no está en `architecture.md` § Story bible | La exige TO-030. Es materialización del `Checkpoint`, no una clase nueva de la ontología, y por eso no toca `definitions.md` |
| Estado de la generación | `Generacion.estado` reutiliza `EstadoNovela` en vez de un enum propio | Un enum paralelo tendría que mantenerse sincronizado con la máquina de estados y se desincronizaría |

### Qué hay que revisar

Lo que más pesa es la **tabla de trabajos**: es la única pieza de persistencia que esta spec
añade al modelo de `architecture.md`, y si se decide que es dominio y no materialización,
entra en la ontología con su clase y su pregunta de competencia.
