# Registro de iteraciones — qué cambió, qué lo provocó y qué efecto tuvo

Log de decisiones con causa y efecto. No es un diario: aquí no se anota lo que se hizo un
día, sino lo que **cambió** en el sistema, **qué lo provocó** —un eval, un contraejemplo,
un cambio de alcance— y **qué efecto** tuvo. Una entrada sin causa o sin efecto no es una
entrada; es una nota.

No confundir con `docs/trade-offs.md`: allí se anota **por qué se eligió** una opción
frente a otras; aquí, **qué cambió** como consecuencia. Una decisión de `trade-offs.md`
suele producir una entrada aquí; lo contrario no siempre pasa.

El historial de git es la evidencia de este registro (`CLAUDE.md` § Contexto semilla), así
que cada entrada nombra el commit o los ficheros que la materializan.

---

## RI-001 — La ontología pasa del asistente de ciencia ficción a storyMaker

**Fecha:** 2026-09-23 · **Ficheros:** `docs/definitions.md`,
`docs/domain-knowledge.md`, `config/thresholds.yaml`

### Causa

Cambio de alcance, no un hallazgo del sistema. `docs/requerimientos/alcance-proyecto.md`
describe un producto distinto del que la ontología modelaba: un sistema agéntico que
genera novelas personalizadas para regalar, de diez capítulos, **sin humano en el bucle de
producción**, con verificación formal de la historia en Lean 4, verificación formal del
harness en TLA+ y observabilidad en Langfuse. La ontología describía un asistente de
escritura de ciencia ficción con autor humano decidiendo, generación por escena y
replanificación por deriva acumulada.

### Qué cambió

**Unidad de generación.** El `Capítulo` pasa a ser la unidad atómica de generación,
validación, checkpoint, regeneración y marca de cambio. Desaparecen `Escena`, `Beat` y
`Parte / Acto`.

**Entra el encargo.** La capa 1 gana un bloque de personalización —`Cliente`,
`Destinatario`, `Ocasión`, `Brief de novela`, `Elemento personalizado`, `Texto libre
aportado`, `Fragmento sospechoso`, `Dato faltante`, `Contradicción de brief`,
`Dedicatoria`— que antes no existía y que es la mitad del objetivo del producto.

**Sale la ciencia ficción y sale el autor humano.** Desaparecen `Novum`, `Término
canónico`, `Facción`, `Artefacto`, `Tema`, `Motivo`, `Objetivo`, `Estado epistémico`,
`Ironía dramática`, `Revelación` y las dimensiones `Plausibilidad especulativa` y `Sentido
de la maravilla`. El `Autor humano` deja de ser un rol: sus decisiones pasan al **policy
engine**, trazadas en el audit log. Los únicos humanos que quedan son el `Lector / Cliente`
y el `Revisor humano`.

**La deriva se sustituye por invalidación.** El vector de tres componentes y la
replanificación rodante se reducen a `Invalidación de restricción → Replanificación de
capítulos pendientes`, booleana y determinista.

**`Hallazgo` se fusiona en `Hecho`.** Un hallazgo era un hecho propuesto con otro nombre
porque lo tocaban dos actores; con la adopción automática hay uno solo.

**El canon pasa a ser la story bible.** `Hecho` gana relación N:M con los capítulos que lo
usan, más `origen` y `fragmento que lo sostiene`. `Evento` se refuerza como tabla de
cronología y gana el subtipo `Evento excluyente`; `Personaje` gana `fecha de nacimiento`.

**La calidad pasa a validadores.** De diecisiete dimensiones sin punto de ejecución a
diecinueve con validador, tipo, punto de ejecución y nombre de score, más dos aspiraciones
declaradas sin validador. Entra el guardrail de palabras prohibidas con sus tres niveles.

**Entran versionado, regeneración y observabilidad.** `Versión de novela`, `Solicitud de
cambio`, `Análisis de impacto`, `Regeneración dirigida`, `Checkpoint`, `Página de
novedades`, y la jerarquía `Sesión → Traza → Span → Score` con `Versión de prompt`.

Las decisiones de diseño que gobernaron estos cambios están pendientes de registrarse en
`docs/trade-offs.md` como TO-002 y siguientes.

> **Corrección (RI-003).** Esa promesa no se cumplió a tiempo y los identificadores se
> gastaron en otras decisiones: TO-002 fue la inversión de `CLAUDE.md`, TO-003 el PDF y
> TO-004 el multi-novela. Las decisiones de esta entrada quedaron finalmente registradas
> como **TO-005** (unidad capítulo), **TO-006** (invalidación en vez de deriva), **TO-007**
> (verificador de continuidad) y **TO-008** (tercer nivel del guardrail). El párrafo de
> arriba se deja tal cual, porque el registro cuenta lo que pasó y no lo que debería haber
> pasado.

### Efecto

**Medible y comprobado.** Las cuatro máquinas de estado coinciden una a una entre los dos
documentos —`Hecho`, `Promesa narrativa`, `Capítulo` y `Novela`—, que era el fallo que
`architecture.md` § Pendiente había registrado tres veces. Las diecinueve entidades del
`erDiagram` tienen tabla en el mapeo. El reparto por capa suma exactamente
`contexto.total`. No queda ninguna cifra en los dos documentos.

**Preguntas de competencia: de 21 a 30.** Al aplicar el criterio de cobertura aparecieron
seis clases sin pregunta que las necesitara —`Snapshot`, `Restricción de destino`, `Arco`,
`Hilo de trama`, `Regla del mundo` y las cuatro de verificación formal del harness—. El
criterio dice que eso es una pregunta que falta, no una clase que sobra, así que se
añadieron.

**Se aclaró una confusión que venía de antes.** El límite de 100.000 tokens del alcance es
**concurrencia** (`en_vuelo.total`), no ventana de contexto (`contexto.total`). Coinciden
en la cifra y no en el concepto; el fichero de umbrales ahora lo dice en ambos sitios.

**Cuatro artefactos quedan inconsistentes y no se tocaron**, por acotación explícita de la
tarea: `AGENTS.md` —cuyo § Requisitos técnicos y § Modelo de autoría siguen describiendo
el modo híbrido por escenas—, `docs/architecture.md` —features, agentes, skills y estados
de escena—, `docs/verification.md` —105 filas que referencian escenas, deriva, novum,
estado epistémico y autor humano— y la skill `presupuesto-de-contexto`. Además
`docs/specs/001-backend-v1/spec.md` sigue `aprobada` describiendo el sistema anterior.

**Dos conflictos abiertos que el alcance introduce y nadie ha resuelto.** El alcance sitúa
la documentación en un repositorio llamado **storyMaker** y este se llama **MyStory**. Y
su apartado opcional de login choca con `AGENTS.md` § Alcance, que prohíbe `user_id` y
`tenant_id` en cualquier tabla.

*Los dos se cerraron en RI-002: storyMaker y MyStory son el mismo repositorio, y las
cuentas quedan fuera de alcance.*

---

## RI-002 — El archivo de instrucciones se pone al día y cambia de sitio

**Fecha:** 2026-09-23 · **Ficheros:** `CLAUDE.md`, `AGENTS.md`,
`docs/definitions.md`

### Causa

RI-001 dejó la ontología describiendo storyMaker y el archivo de instrucciones describiendo
el sistema anterior: escena como unidad, modo híbrido entre las decisiones cerradas, una
sola obra por instancia y un stack cerrado que bloqueaba las herramientas que el alcance
exige. El archivo que un agente lee **antes** que ningún otro era el que mentía.

A la vez, el alcance § Claude Code convierte `CLAUDE.md` en entregable evaluable, y era una
línea con un import.

### Qué cambió

**`CLAUDE.md` pasa a ser el archivo completo** y `AGENTS.md` un stub de dieciséis líneas que
apunta a él sin duplicar ninguna regla (TO-002).

**El stack se abre a lo que el alcance exige**: SDK de Langfuse, Lean 4 con `lake`, TLA+
tools con TLC y Playwright, que además genera el PDF sin añadir un motor de render nuevo
(TO-003). `sqlite-vec` pasa de obligatorio a **opcional**: la recuperación funciona con
filtro relacional y la similitud solo ordena.

**Varias novelas por instancia** con `novel_id` en toda tabla de dominio, sin multiusuario
ni autenticación (TO-004). La idempotencia de escritura pasa de `scene_id` + `version` a
`novel_id` + `chapter_id` + `version`.

**El layout se rehace sobre nueve features** derivadas de las cinco capas —`intake`,
`novel`, `canon`, `context`, `quality`, `guardrail`, `process`, `policy`, `versioning`— más
`commons/`. Entran `formal/lean/`, `formal/tla/`, `ejemplos/`, `presentacion/`,
`.env.example` y `.claude/` con `mcp.json` y `commands/`. Desaparecen `findings/` y
`replanning/`, que la ontología ya había disuelto.

**El frontend pasa de tres páginas a dos**: `entrevista` y `lectura`. **El formato de
lectura queda decidido: web**, con el PDF de `/ejemplos/` exportado de ese mismo render; la
ontología lo dejaba abierto a propósito y ya no hace falta.

**Las reglas pasan de diez a dieciséis.** La 2 cambia de escena a capítulo; la 4 se parte en
dos casos —en desarrollo se pregunta al desarrollador, en producción el dato que falta
vuelve al entrevistador y nunca se inventa—. Entran seis nuevas: texto libre no confiable,
sin secretos en el repo, span por rol y score por validador, todo reintento con límite, la
versión anterior nunca se sobrescribe, y ninguna versión se publica sin el gate.

**`docs/definitions.md` gana un párrafo** en § Mapeo a la story bible con la regla de
`novel_id` y la idempotencia nueva. Es lo único que se tocó de la ontología.

### Efecto

**Comprobado.** `CLAUDE.md` queda en 296 líneas, por debajo del límite de 300 que él mismo
fija. Las dieciséis reglas están numeradas sin saltos. Ninguna ruta se cita como existente
sin serlo: las que no existen llevan **▸ previsto**. Ningún término de la ontología antigua
sobrevive, y los veintiséis términos de dominio que `CLAUDE.md` usa existen todos en
`docs/definitions.md`.

**Se retiró un nombre que sobrevivía por inercia.** «Autor humano» seguía usándose para el
humano que aprueba specs, reutilizando el nombre de un rol que la ontología había
eliminado. Pasa a ser **el desarrollador**, y el archivo dice explícitamente que en
producción quien decide es el policy engine.

**Los dos conflictos de RI-001 quedan cerrados.** storyMaker y MyStory son el mismo
repositorio. Las cuentas de usuario quedan fuera de alcance, así que el login opcional ya
no choca con nada: se añadiría como migración posterior.

**Sigue pendiente, y no se tocó**: `docs/architecture.md` —las nueve features, su tabla
clase a feature, los agentes, las skills del sistema y la orquestación sobre los estados de
capítulo—; `docs/verification.md`, que debería **convertirse** en la tabla de validadores
con punto de ejecución y score que pide el alcance §5, y que además necesita un validador
nuevo para la consulta de dominio que olvide acotar por `novel_id`; las cinco skills de
`.claude/skills/`; y `docs/specs/001-backend-v1/`, aprobada y obsoleta.

---

## RI-003 — Correcciones de la auditoría 001

**Fecha:** 2026-09-23 · **Ficheros:** `docs/definitions.md`,
`docs/domain-knowledge.md`, `CLAUDE.md`, `docs/trade-offs.md`, este registro y tres skills
de `.claude/skills/`

### Causa

La auditoría `docs/audits/001-coherencia-ontologia.md` contrastó los cuatro documentos
principales contra el alcance y entre sí, y encontró cinco fallos de coherencia. Esta
entrada recoge los que se corrigieron; los otros dos se difieren a las tareas que
regeneran `docs/architecture.md` y `docs/verification.md`.

No es un cambio de alcance como RI-001 ni una puesta al día como RI-002: es deuda de las
dos anteriores, encontrada al mirarlas juntas.

### Qué cambió

**El formato de lectura deja de estar pendiente** (hallazgo C5). `CLAUDE.md` daba la web
por decidida mientras `definitions.md` y `domain-knowledge.md` decían que seguía abierta.
Se cierra en los tres: **lectura web, y el PDF de `ejemplos/` es un export de ese mismo
render** (TO-009). Con ello **desaparece la clase `Página de novedades`**: qué capítulos
cambiaron ya vive en la marca del vínculo entre versión y capítulo, y presentarlo al abrir
el export es maquetación. El `origen` de la `Solicitud de cambio` deja de distinguir
formatos y pasa a registrar desde qué capítulo o fragmento se pidió.

**`Score` gana justificación y `Rúbrica` gana sus criterios** (hallazgo C6). El alcance §5b
pide «una puntuación por criterio y una justificación», y la ontología tenía las seis
dimensiones semánticas sueltas, sin nada que las atara a la rúbrica, y un `Score` que solo
llevaba valor. Ahora `Rúbrica` enumera los seis criterios del encargo —continuidad, tono,
arco, coherencia de personajes, ritmo e integración natural de la personalización— con la
dimensión que puntúa cada uno, y `Score` lleva justificación cuando el validador es
semántico.

**Las cinco decisiones que faltaban entran en `docs/trade-offs.md`** (hallazgo E1), como
**TO-005** a **TO-009**, más **TO-010** por la división de `Cliente`. Las cuatro primeras
se registran a posteriori y así lo declaran.

**Se corrige la promesa de identificadores de RI-001** sin borrarla: el párrafo original se
conserva y se le añade una nota que dice qué identificadores acabaron usándose y por qué.

**Las referencias rotas a `AGENTS.md` se reapuntan a `CLAUDE.md`** (hallazgo transversal) en
`docs/trade-offs.md`, este registro y las skills `backend-feature-slice`,
`plan-de-verificacion` y `sqlite-relacional`. Las que describen la propia decisión de vaciar
`AGENTS.md` —TO-002 entero, y RI-002— **no se tocan**: ahí `AGENTS.md` es el sujeto del que
se habla, no un puntero que seguir.

**`CLAUDE.md` gana la fila del alcance** en «Dónde está cada cosa», que además retira de esa
tabla la palabra «cliente».

### Efecto

**Tres de los cinco hallazgos quedan cerrados**: C5, C6 y E1. El transversal queda cerrado
en los cinco ficheros vigentes; lo que resta de él vive en `architecture.md` y
`verification.md`, que se regeneran aparte.

**Dos se difieren a propósito**, no por olvido: D5 —las nueve features de `CLAUDE.md` frente
a las siete de `architecture.md`— y el puntero de `CLAUDE.md` a `verification.md`. Los dos
se resuelven regenerando esos ficheros, y hacerlo aquí sería escribir dos veces.

**Queda una corrección a medias a propósito**: C12, las clases huérfanas. La división de
`Cliente` en `Comprador` y `Lector` (TO-010) y la eliminación de `Página de novedades`
tocan de lleno esa lista, así que la propuesta de preguntas de competencia se entrega
aparte y espera aprobación antes de aplicarse.

**Lo que la auditoría demostró de paso.** Los tres fallos de mayor alcance —referencias
rotas, features contradictorias y formato de lectura— nacieron todos de cambios correctos
aplicados sin barrer lo que arrastraban. Ninguno lo habría detectado la lectura del fichero
que se estaba editando; los tres salieron de mirar los ficheros juntos.

### Segunda tanda — C12 y C2/D4

Aprobada aparte, después de entregar la propuesta. Va en esta entrada y no en una nueva
porque la causa es la misma auditoría: partirla daría dos entradas con un solo origen.

**`Cliente` se parte en `Comprador` y `Lector`** (TO-010). `Comprador` paga y configura;
`Lector` lee la novela publicada y pide cambios, y es un **papel**, no una persona distinta:
lo ocupa el comprador o el destinatario. «Cliente» deja de ser término de la ontología. El
renombrado alcanza tablas de clases, relaciones, mapeo y nomenclatura de `definitions.md`,
las cajas y la prosa de `domain-knowledge.md`, `CLAUDE.md` —la feature `intake/` y la regla
11— y los dos comentarios de `config/thresholds.yaml` que se referían a este concepto.

**`Biblia de la obra` desaparece, fusionada en `Story bible`.** Su definición decía
literalmente «Es la story bible»: era el mismo concepto con dos nombres, justo lo que §
Convenciones prohíbe. Se conserva **story bible**, que es como lo llaman el alcance, el
resto de la ontología, `CLAUDE.md` y la feature `canon/`.

**Las preguntas de competencia pasan de 30 a 33**, y con ellas se cierran las clases
huérfanas que quedaban:

| Pregunta nueva | Clases que deja de dejar sueltas |
| --- | --- |
| 1 · ¿Qué comprador encargó esta novela, para qué destinatario, con qué ocasión y con qué dedicatoria? | `Comprador`, `Ocasión`, `Dedicatoria` |
| 10 · ¿Qué voz narrativa —persona y tiempo verbal— declara esta novela, y la respeta el capítulo N? | `Voz narrativa`, que sostenía `integridad_pov` sin que nadie la preguntara |
| 23 · ¿Qué lector pidió este cambio y desde qué capítulo de la lectura lo pidió? | `Lector` |

La 23 **no estaba en la propuesta aprobada**: la creó la propia corrección. Al partir
`Cliente`, `Lector` nacía como clase que ninguna pregunta necesitaba, es decir, como una
huérfana nueva puesta por la misma tarea que venía a quitarlas. Se añadió por el criterio
que el documento declara en § Convenciones, y se deja anotado aquí porque no fue aprobada.

Las tres preguntas nombran la clase literalmente, y no por rodeo, para que la cobertura se
pueda comprobar con un `grep` y no dependa de que alguien lea y juzgue.

### Efecto de la segunda tanda

**C12 y C2/D4 quedan cerrados.** No queda ninguna clase sin pregunta ni ningún nombre con
dos significados en los cuatro documentos. `CLAUDE.md` sigue en 296 líneas, los 21 bloques
Mermaid siguen pasando el verificador estructural, y la única aparición de «cliente» que
sobrevive es «el cliente tipado del OpenAPI», que no es este concepto.

**Lo que enseña la pregunta 23.** Dividir una clase para quitar una ambigüedad puede crear
una huérfana nueva, y el criterio de inclusión hay que volver a pasarlo **después** del
cambio, no solo antes. Es el mismo patrón que la auditoría encontró tres veces: un cambio
correcto que arrastra algo que nadie barre.

---

## RI-004 — `architecture.md` se rediseña sobre el alcance de storyMaker

**Fecha:** 2026-09-23 · **Ficheros:** `docs/architecture.md`, `docs/trade-offs.md`

### Causa

`architecture.md` era el último documento vivo que seguía describiendo el sistema anterior:
siete features con clases eliminadas, ocho agentes con un autor humano decidiendo, once
skills del sistema, una escalera de adaptación del modelo y una sección entera de cola de
trabajos. La auditoría 001 lo señaló dos veces —D5 y B1— y las dos se difirieron aquí a
propósito, porque corregirlas sobre el documento viejo habría sido escribir dos veces.

A diferencia de RI-001 y RI-002, este cambio **no arrastraba decisiones tomadas**: las
tomaba. De ahí que fuera precedido por una sesión de grill con las skills `grill-me` y
`grilling`, en cuatro rondas, que cerró dieciocho decisiones nuevas.

### Qué cambió

**El documento se reescribe entero**, de 841 a 954 líneas y de 10 diagramas nuevos. Las
secciones que desaparecen son las que describían el sistema anterior: § Adaptación del
modelo con su escalera de cuatro escalones y `training_samples`; § Cola de trabajos; la
tabla de once skills del sistema; los ocho agentes antiguos; y § Pendiente de llevar a la
ontología, entera.

**Se cierran los dos hallazgos diferidos de la auditoría 001.** D5: la tabla clase → feature
pasa de siete features con clases eliminadas a las nueve de `CLAUDE.md`, con las 60 clases de
la ontología repartidas y comprobadas una a una. B1: desaparece todo el texto de documentos
vivos y reexportación, y las catorce referencias a secciones de `AGENTS.md` pasan a
`CLAUDE.md`.

**Entran dieciocho decisiones nuevas**, TO-011 a TO-028, entre ellas: orquestación con código
propio en FastAPI porque es lo único que sostiene la correspondencia con la spec TLA+;
modelo por rol con el judge separado del editor para evitar el sesgo de autopreferencia; un
solo contador acumulativo de intentos; sin `sqlite-vec` en v1 porque la novela entera cabe
en la capa Recuperado; Lean bloqueante en el gate y con aviso incremental por capítulo;
correspondencia TLA+ ↔ código como dato comprobable por un test; y la story bible versionada
por vigencia.

**Dos secciones nuevas que el diseño necesitaba y no tenía**: § Presupuesto de tokens
concurrentes y § Memoria a corto y largo plazo.

### Efecto

**Una verificación cambió una decisión.** Al comprobar los identificadores de modelo contra
la documentación oficial en vez de contra memoria, resultó que `claude-opus-5` había pasado
a legacy y que su sustituto es **más barato**. La decisión que se iba a registrar era
incorrecta y se corrigió antes de escribirla.

**Dos preguntas del autor corrigieron errores míos.** El argumento de los falsos negativos
con que justifiqué no correr Lean por capítulo era malo —los invariantes son de seguridad y
una violación en un prefijo lo es en el total—, y de ahí salió el chequeo incremental. Y la
invariante de reanudación que formulé sobre «el texto se escribe una vez por versión» era
falsa, porque los reintentos producen varios borradores: lo que ocurre una vez es la
**aceptación**.

**Comprobado**: los 10 bloques Mermaid pasan el verificador estructural —no hay `mmdc` en la
máquina y se dice en el documento—; las 60 clases de la tabla de features existen
literalmente en `definitions.md`; los 12 estados usados existen en `domain-knowledge.md`; no
queda ninguna ruta citada como existente sin serlo; y no sobrevive ningún término de la
ontología anterior.

**Queda pendiente y no se tocó**: `docs/verification.md`, que se regenera aparte y que este
documento enlaza en vez de duplicar; `docs/definitions.md`, con tres cambios que este
rediseño destapó —el validador `paridad_pdf_web`, el punto de ejecución `export` y los
atributos de vigencia sobre `Hecho`—; y `CLAUDE.md`, con cinco rutas nuevas que su layout no
reserva.

**Lo que enseña este cambio.** Las tres decisiones de más alcance —orquestación, versionado
de la story bible y separación del judge— no estaban en la lista de trece que la tarea pedía
cerrar: salieron de tirar del hilo de las que sí estaban. Un interrogatorio por rondas
encuentra lo que una lista de preguntas no tiene.

---

## RI-005 — `CLAUDE.md` se reconcilia con `architecture.md`

**Fecha:** 2026-09-23 · **Ficheros:** `CLAUDE.md`, `docs/architecture.md`

### Causa

`CLAUDE.md` se escribió **antes** que `architecture.md` y, por tanto, antes del grill que
cerró dieciocho decisiones nuevas. Nada de lo que decía era falso, pero describía un
repositorio que ya no era el acordado: le faltaban tres rutas, dos comandos y un fichero de
configuración, y dos afirmaciones se habían quedado imprecisas.

Es el mismo patrón que la auditoría 001 encontró tres veces: **un cambio correcto aplicado
sin barrer lo que arrastraba**. Aquí la deuda se pagó antes de que la encontrara otra
auditoría, porque el rediseño de la arquitectura terminó con la lista de divergencias hecha.

### Qué cambió

**Diez divergencias**, seis ya listadas al cerrar la arquitectura y cuatro del repaso:

| Qué decía `CLAUDE.md` | Qué dice ahora |
| --- | --- |
| El layout no reservaba `mcp_server/`, `skills/`, `.claude/agents/` ni `config/models.yaml` | Los cuatro, con su marca ▸ previsto donde toca |
| § Comandos no tenía ni sincronización de prompts ni export de PDF | Los dos |
| `sqlite-vec` era «opcional» | **No se usa en v1** (TO-015), con el porqué: la novela entera cabe en la capa Recuperado |
| «Ventana declarada en `config/thresholds.yaml`» | **No es la ventana del proveedor**, que es mayor: es un tope nuestro (TO-019) |
| «Sistema, agentes, skills, **orquestación** y ciclo de cambio» | `architecture.md` ya no tiene § Orquestación: se repartió entre § Proceso de producción y § Hooks y policy engine |
| `.claude/skills/` eran «las skills» | Hay **dos bloques**: runtime en `backend/app/skills/` y desarrollo en `.claude/skills/` (TO-021) |
| El presupuesto de contexto no distinguía por rol | **La capa Invariante se compone y se presupuesta por rol**, porque no todos cargan las mismas skills de runtime |

**El ciclo de cambio gana cuatro reglas que le faltaban**: spec y plan **nacen en
`borrador`** y solo el desarrollador los mueve a `aprobada`; el interrogatorio previo a una
spec se hace con la skill **`grill-me`**; al cerrar un plan se actualizan también
**`verification.md` si cambió un validador** y el registro; y la obligación de dejar rastro
se generaliza de «todo cambio de **ontología**» a **todo cambio de decisión**, con entrada en
`trade-offs.md` **y** en el registro.

**Y se quitó una duplicación que acababa de introducir yo**: la regla de los dos rastros
llegó a estar escrita entera en los dos ficheros. La regla se quedó en `CLAUDE.md` y
`architecture.md` pasó a apuntarla y a aportar solo lo suyo: qué contiene cada entrada.

### Efecto

**`CLAUDE.md` se mantiene por debajo de 300 líneas: 299.** Entraron unas catorce líneas, así
que salieron otras tantas, y todas las que salieron estaban **duplicadas**: la justificación
de `guardrail/` como feature, la enumeración de la rodaja vertical y la regla de importación,
que viven en `architecture.md` § Anatomía de una feature y en la skill `backend-feature-slice`.
El límite hizo su trabajo: obligó a mirar qué sobraba en vez de dejar crecer el fichero.

**Comprobado**: las siete citas `§` cruzadas entre los dos documentos resuelven; ninguna ruta
se cita como existente sin serlo; las dieciséis reglas siguen numeradas sin saltos; no hay
cifras nuevas fuera de `config/thresholds.yaml`; y cada una de las reglas del ciclo aparece
**una sola vez** entre los dos ficheros.

**`AGENTS.md` no se tocó**, y es la comprobación de que TO-002 funciona: un stub sin reglas no
tiene con qué divergir.

**Se cierran los dos hallazgos que la auditoría 001 dejó diferidos.** D5 —las nueve features
de `CLAUDE.md` frente a las siete de `architecture.md`— y B1 —la prohibición de editar el
contexto semilla— quedaban a medias desde RI-004: la arquitectura ya se había rehecho, pero
faltaba el lado de `CLAUDE.md`. Ahora los dos están cerrados por los dos lados.
