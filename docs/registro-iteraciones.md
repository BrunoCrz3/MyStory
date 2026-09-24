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

---

## RI-006 — La ontología recibe lo que la arquitectura destapó, y suelta lo que no era suyo

**Fecha:** 2026-09-23 · **Ficheros:** `docs/definitions.md`, `docs/domain-knowledge.md`,
`docs/architecture.md`, `docs/verification.md`, `config/thresholds.yaml`,
`config/models.yaml`, `CLAUDE.md`

### Causa

Rediseñar `architecture.md` (RI-004) dejó dos deudas en direcciones opuestas. Por un lado,
el diseño necesitaba tres cosas que la ontología no tenía: el validador `paridad_pdf_web`, el
punto de ejecución `export` y la vigencia por versión de TO-028. Por otro, la ontología
cargaba con detalle que no era vocabulario sino materialización: nombres de tabla, nombres de
span y de score, y la lista de transformaciones del guardrail.

Y la configuración seguía con valores en `null` que el grill ya había decidido.

### Qué cambió

**La ontología gana tres cosas y una cuarta que arrastran.** Entran la dimensión
`Paridad PDF ↔ web`, el quinto punto de ejecución `export` —el único que corre **después** de
publicar, sobre un artefacto derivado de una versión ya válida, y por eso no bloquea— y los
atributos de vigencia sobre `Hecho`.

La cuarta no estaba en el encargo y TO-028 la obligaba: **`Retconeado` pasa a estado
terminal**. El diagrama tenía la arista `Retconeado → Adoptado`, «nueva versión fijada», y
bajo vigencia eso es falso —el retcon cierra un hecho y abre otro, que es otra fila—.
`Retcon` gana además las dos filas de relación que le faltaban, `cierra` y `abre`, con su
cardinalidad: el linaje estaba en los atributos pero no en el grafo.

**Y una quinta, del repaso del autor**: el puente `hecho_capitulo` también se versiona. Un
capítulo puede dejar de mencionar un hecho al regenerarse sin que el hecho cambie, y sin
vigencia propia el análisis de impacto responde por la versión equivocada.

**La ontología suelta cuatro bloques.** Las 45 filas de § Mapeo y la materialización de
`StoryBible` se van a `architecture.md` § Story bible —la sección § Mapeo **desaparece
entera**, porque todo su contenido era schema—; las cinco transformaciones de
`Normalización` se van a § Hooks y policy; y las columnas SQLite y Langfuse de
§ Nomenclatura salen, que queda con dominio ↔ nombre de clase en código, que es el
vocabulario compartido.

**Lo que no se podía perder, no se perdió.** La columna Score **no es derivable** del nombre
en español en seis de las diecinueve dimensiones —«Ortografía exacta de nombres» es
`nombres_exactos`—, así que borrarla habría destruido información. Se aparcó, junto con la
columna Langfuse, en una sección **«Entrada para la regeneración»** dentro del propio
`docs/verification.md`, encabezada por la instrucción de consumirla y borrarla. Está en el
fichero que la va a usar, que es donde menos puede extraviarse.

**La configuración deja de estar a medias.** `max_intentos_capitulo: 3`,
`max_intentos_trabajo: 3` y `max_reescrituras: 2`, este último documentado como **sublímite y
no como contador**, que es lo que TO-014 decidió. Entran cuatro bloques: `modelo` con el
`max_tokens` por rol y el invariante que se comprueba al arrancar —`margen` ≥ `max_tokens` de
cada rol, porque con thinking adaptativo el razonamiento cuenta dentro—, `formal` con el
incremental activado y el timeout **en `null` a propósito**, `export` con la tolerancia de
recuento, y `config/models.yaml` nuevo. **Cada valor nombra la decisión que lo sostiene.**

**Y se corrige una mentira del fichero de umbrales**: el comentario decía que la ventana la
fija el proveedor. Los modelos elegidos tienen ventanas muy superiores; el tope es nuestro.

### Efecto

**Comprobado**: los 31 bloques Mermaid de los dos documentos pasan el verificador
estructural; las 60 clases que `architecture.md` reparte entre features siguen existiendo en
la ontología; no queda ninguna cifra duplicada fuera de `config/`; y **ningún identificador
de modelo aparece fuera de `config/models.yaml`**, que era el punto del encargo.

**`config/models.yaml` existe, así que la marca ▸ prevista se retiró de los cinco sitios** que
la llevaban, en `CLAUDE.md` y en `architecture.md`.

**Lo que enseña este cambio.** Las dos consecuencias de más peso —`Retconeado` terminal y la
vigencia del puente— no estaban en el encargo ni en TO-028: salieron de llevar la decisión al
diagrama y de que el autor preguntara por el linaje. Una decisión escrita en prosa parece
completa hasta que alguien intenta dibujarla.

**Sigue pendiente**: `docs/verification.md`, que tiene 36 referencias a `AGENTS.md`, sigue
hablando de escenas y deriva, y ahora además carga la sección aparcada que debe consumir.

---

## RI-007 — `docs/verification.md` se regenera sobre el alcance de storyMaker

**Fecha:** 2026-09-23 · **Ficheros:** `docs/verification.md`,
`.claude/skills/plan-de-verificacion/SKILL.md`, `docs/trade-offs.md`,
`docs/audits/001-coherencia-ontologia.md`

### Causa

`verification.md` era el último documento del sistema anterior. Sus 105 filas hablaban de
escenas, de deriva, de novum y de un autor humano que decidía; tenía **36 referencias a
secciones de `AGENTS.md`** que dejaron de existir con TO-002; y cargaba desde RI-006 la
sección «Entrada para la regeneración», con los nombres de score y de span que la ontología
soltó al quedarse solo con el vocabulario.

Además arrastraba el segundo hallazgo diferido de la auditoría 001: `CLAUDE.md` prometía que
este fichero dice «qué valida cada validador, dónde corre y con qué score», y el fichero
tenía **cero** apariciones de «score», «punto de ejecución», «Langfuse» y «hook de».

### Qué cambió

**El documento pasa de 105 filas a 228, repartidas en cuatro niveles.** Artefacto 97,
Proceso 47, **Obra** 64 y **Entregables** 20; 163 obligatorias, 64 recomendadas y una
exploratoria. Los dos niveles nuevos y la enmienda a la skill que los admite son TO-029.

**Cada fila gana cuatro columnas**: punto de ejecución —los cinco de la Capa 4 más
`CI/desarrollo`—, score en Langfuse, prioridad y coste. Y el documento abre con un **índice
de validadores con nombre** que apunta a las filas sin copiarlas: es la tabla de validadores
con su punto de ejecución que pide el alcance §5, y es la que `architecture.md` enlaza en vez
de duplicar (TO-018).

**Se conservan 44 filas de artefacto y 12 de proceso**, reescritas con la ontología nueva
—capítulo en vez de escena, `novel_id`, Comprador y Lector, story bible—. Once se
transforman y cambian de identificador porque cambian de significado, y **treinta y siete se
retiran**, cada una con su motivo trazado: la deriva entera (TO-006), el novum, el sentido de
la maravilla, `training_samples` y todo lo que presuponía un autor humano en producción.

**Lo que no tiene criterio de aprobado no desaparece: baja a § Lo que no se puede
verificar.** Mostrar frente a contar, carga expositiva y originalidad van ahí enteras;
curva de tensión y causalidad se quedan en las tablas con un proxy estructural —promesas
pendientes e hilos que avanzan— y solo su residuo estético baja. La consistencia epistémica
sobrevive como `O-33`, **sin parte programática**, porque la ontología no modela qué sabe
cada personaje: es una de las tres inconsistencias de personaje que el comprador nombra.

**El punto ciego del acuerdo crítico–autor se convierte en fila.** `P-85` mide el acuerdo
entre el `judge` y el `Revisor humano` criterio a criterio, y como los dos puntúan **por
capítulo**, una novela da diez parejas por criterio en vez de una. El residuo que queda
declarado es que las diez salen del mismo texto: miden acuerdo en esta novela, no en el
sistema.

**Cuatro validadores nuevos entran con score provisional** y dos más aparecieron al
generar: `invencion_destinatario` y `temas_excluidos` como obligatorios, `reglas_mundo` y
`legibilidad` como recomendados, y `estructura_edicion` y `regeneracion_fiel` porque seis
filas obligatorias del alcance —diez capítulos, títulos únicos, y las tres de la
regeneración— emitían un score que no existía. Los seis van marcados ⚠ y **su nombre no se
escribe en código** hasta que la ontología los ratifique: son PO-1 a PO-3 y PO-7 a PO-9 de
§ Propuestas de cambio.

**«Filas pendientes de ontología» deja de existir como sección.** Decía que
`definitions.md` lo edita otro y que este repositorio exporta; desde TO-001 eso es falso. En
su lugar hay **propuestas de cambio**, que es lo que son: cambios que este documento no hace
por su cuenta porque tocar la ontología lleva su propia entrada y su propio commit.

**La sección «Entrada para la regeneración» se consumió y se borró.** Los veinte nombres de
score están en el índice y en la columna Score; los catorce de span y traza, en las filas de
observabilidad `P-68` a `P-73`.

### Efecto

**Comprobado sobre el fichero generado**: las 228 referencias cruzadas de «Cubierto por» y
«Punto ciego» resuelven a una fila existente; los cuatro `NADIE` están los cuatro en
§ Puntos ciegos sin cubrir; cada requisito del alcance de la tabla de trazabilidad tiene al
menos una fila `obligatorio`; y no queda ningún término de la ontología antigua fuera del
sitio donde el término **es el sujeto** —la lista cerrada de `E-15` y la explicación de por
qué la spec 001 está obsoleta—.

**Las referencias a `AGENTS.md` pasan de 36 a una**, y esa una es legítima por el mismo
criterio que la auditoría 001 fijó para `trade-offs.md` y el registro: está en § Pendientes,
diciendo que la spec 001 cita `AGENTS.md` entre sus documentos de referencia. Es el sujeto
del que se habla, no un puntero.

**Los dos hallazgos que la auditoría 001 difirió a esta tarea quedan cerrados**, y el
puntero de `CLAUDE.md` § Dónde está cada cosa —«qué valida cada validador, dónde corre y con
qué score»— pasa a ser cierto.

**Lo que enseña este cambio.** Las dos dimensiones que más valen del documento nuevo no
salieron de barrer la ontología sino de leer lo que el cliente teme: `invencion_destinatario`
—un hecho personal inventado sobre una persona real, que la consistencia fáctica **no
detecta porque el canon lo absorbió al extraerlo**— y el reparto de los elementos
personalizados. Ninguna de las dos estaba en la Capa 4. Una ontología completa describe el
sistema que se diseñó; el catálogo de modos de fallo describe el que se va a usar.

**Sigue pendiente**: `docs/specs/001-backend-v1/` está `aprobada` y obsoleta, y el
frontmatter del ciclo de cambio **no tiene un estado para eso**. Hay que archivarla o añadir
el estado antes de escribir la primera línea de código, que es cuando la puerta se consulta.

---

## RI-008 — El repositorio se prepara para la spec del backend

**Fecha:** 2026-09-23 · **Ficheros:** `CLAUDE.md`, `docs/architecture.md`,
`docs/definitions.md`, `docs/domain-knowledge.md`, `docs/verification.md`,
`docs/requerimientos/alcance-proyecto.md`, `config/thresholds.yaml`, `.env.example`,
`.gitignore`, `specs/`, `docs/specs/_archivo/`

### Causa

La demo de backend y frontend es en dos días, y para escribir la spec había tres cosas que
estorbaban. Una spec `aprobada` que describe el sistema anterior y que cualquier agente
tomaría por trabajo pendiente. Una configuración con veintiocho umbrales en `null`, que
hace fallar el arranque en voz alta en cuanto alguien pida uno para cerrar el paso. Y doce
propuestas de ontología que `verification.md` había levantado sin aplicar, seis de ellas
sosteniendo filas obligatorias con un nombre de score que no existía.

### Qué cambió

**Las specs de v1 viven en `specs/`, y lo obsoleto no se borra.** La convención pasa de
`docs/specs/NNN-slug/spec.md` a `specs/specN.md` con su `planN.md` al lado, sin carpetas.
`docs/specs/001-backend-v1/` se movió a `docs/specs/_archivo/` con **`estado: archivada`**,
un cuarto estado del frontmatter que `CLAUDE.md` § Ciclo de cambio declara **no
implementable**. No se borró: el registro y `trade-offs.md` la citan, y borrarla dejaría sin
contexto a entradas que explican por qué el sistema es como es. `CLAUDE.md` se queda en
**299 líneas** absorbiendo el cambio en el párrafo del frontmatter, sin mover detalle.

**Diez de las doce propuestas de ontología se aplican.** `definitions.md` Capa 4 gana seis
dimensiones —`invencion_destinatario`, `temas_excluidos`, `reglas_mundo`, `legibilidad`,
`estructura_edicion` y `regeneracion_fiel`— y dos clases, `Defecto inyectado` y `Brief de
prueba`, con **dos preguntas de competencia nuevas** para que no nazcan huérfanas: las
preguntas pasan de 33 a 35. El `alcance` de una `Restricción de destino` deja de ser texto
libre y pasa a ser la lista explícita de entidades, promesas e hilos que toca, que es lo que
hace resoluble por consulta la invalidación. `architecture.md` declara que el backend escucha
solo en la interfaz local mientras no haya autenticación, y los dos mapas de validadores
—ontología y arquitectura— recogen los seis scores nuevos.

**PO-11 y PO-12 no se aplican y se dicen.** El coste de desplazamiento entre `Lugar` y el
estado epistémico de un personaje no son cambios mecánicos: cada uno decide qué dato entra
por el brief y qué extrae el extractor, y cada uno ensancha Lean o la extracción. Aplicarlos
a ojo para vaciar la lista habría sido peor que dejarlos abiertos.

**La configuración deja de tener umbrales en `null`.** Cuarenta y tres claves —las quince
nuevas y las veintiocho que estaban vacías— reciben valor, **todas marcadas
`[provisional — calibrar tras la demo]` y con el criterio con que se eligieron escrito al
lado**. Se fija además algo que faltaba y sin lo cual ningún umbral significaba nada: la
escala de los scores semánticos es 0.00–1.00. `legibilidad` es la excepción declarada, que
usa el índice INFLESZ y sube su exigencia con destinatarios menores de doce años.

**Quedan tres `null`, y ninguno cierra el paso.** `embeddings.version` y
`embeddings.dimension` están inactivos en v1 (C-1, TO-015) y no los lee nadie.
`formal.lean_timeout_segundos` sigue bloqueado porque **el gate de Lean queda fuera de la
demo**: no hay toolchain instalada, así que entra `formal.gate_activo: false`. La
consecuencia se declara en el propio fichero y en `verification.md`: con el gate apagado,
`lean_cronologia`, `lean_ubicacion` y `lean_edad` no se ejecutan y la demo publica versiones
sin demostración de cronología.

**C-1, C-2 y C-3 aplicadas.** El bloque de embeddings queda marcado inactivo, la cabecera de
`config/thresholds.yaml` deja de apuntar a `AGENTS.md`, y el alcance también.

**Secretos.** Se barrió el historial completo —179 commits— con los patrones de clave de
Anthropic, OpenAI, GitHub, AWS, Slack, Stripe, JWT y bloques PEM: **cero coincidencias
reales**. Lo único que aparece es `TU_CLAVE_AQUI` y referencias `${{ secrets.* }}` en un
`BUILD_SPEC.md` de la etapa anterior del repositorio. Se crean `.env.example` con los
**nombres** de las siete variables que el sistema leerá y sin un solo valor, y `.gitignore`,
que ignora `.env` y versiona la plantilla. Comprobado con `git check-ignore`.

### Efecto

**Comprobado**: `config/thresholds.yaml` parsea, las siete capas más el margen siguen
sumando `contexto.total`, y el invariante de arranque se cumple —`margen` = 6000 es mayor o
igual que el `max_tokens` de los seis roles, con el redactor y el editor justo en el límite—.
`.env` está ignorado y `.env.example` no. `CLAUDE.md` sigue en 299 líneas. Las marcas ⚠ de
`verification.md` desaparecen: eran seis y ahora son cero.

**Lo que enseña este cambio.** Las dos propuestas que no se aplicaron son las dos que
nacieron de un punto ciego y no de un requisito: `O-14` y `O-33` seguirán descubiertas
después de la demo, y eso está bien dicho en su fila. Las diez que sí se aplicaron eran
todas consecuencia de que el alcance pedía algo que la ontología no nombraba. Una ontología
se queda corta por donde el encargo aprieta, no por donde el diseño es elegante.

**Sigue pendiente**: PO-11 y PO-12; encender el gate de Lean cuando haya toolchain; y
calibrar los cuarenta y tres umbrales provisionales con el primer corpus, que es lo que
`medicion.cerrar_el_paso: false` está esperando.

---

## RI-009 — La spec del backend v1 y su contrato, escritos contrato primero

**Fecha:** 2026-09-24 · **Ficheros:** `specs/spec1.md`, `specs/openapi.yaml`,
`docs/trade-offs.md`

### Causa

Dos días para tener backend y frontend en pie. Con la spec 001 archivada, no había
especificación vigente que un plan pudiera ejecutar, y el frontend no tenía contra qué
construirse: cualquier trabajo que empezara antes de la spec habría que rehacerlo.

### Qué cambió

**Existe `specs/openapi.yaml`, y es la fuente.** Un OpenAPI 3.1 con **20 operaciones y 31
schemas**, con los campos, los códigos de error y los ejemplos. No es documentación que
sale del código: el backend lo implementa y **un test compara el OpenAPI que genera FastAPI
con este fichero**; si divergen, falla. El frontend genera su cliente tipado desde él, y por
eso puede empezar hoy sin esperar a una sola línea de backend.

**Existe `specs/spec1.md`**, una SRS inspirada en ISO/IEC/IEEE 29148 con **62 requisitos
funcionales en formato EARS**, cada uno con criterios Dado/Cuando/Entonces y marcado
**[demo]** o **[post-demo]**, agrupados por la feature que es dueña de sus clases; seis
requisitos de datos; dieciocho no funcionales; y **seis fases de construcción** que el plan
seguirá en orden, cada una con su criterio de terminado.

**Un grill de ocho preguntas cerró lo que `/docs` no resolvía**, y de ahí salen cinco
decisiones aprobadas por el desarrollador: **TO-030** worker asíncrono único en proceso con
la cola en SQLite; **TO-031** sondeo en vez de SSE; **TO-032** errores RFC 9457 con catálogo
cerrado y 409 sin `Idempotency-Key`; **TO-033** ninguna identidad, y las tres reglas de
privacidad que se derivan de que el brief lleva datos personales reales; y **TO-034** el
cliente del modelo probado con un `Protocol` cuyo doble vive en `tests/`.

**Y una sexta, TO-035, marcada «decidido por el agente — revisar»** con lo que se fijó sin
preguntar: la forma de los recursos, la paginación, el export como `POST` más `GET`, el
endpoint de validación de brief y la **tabla de trabajos**, que es la única pieza de
persistencia que la spec añade al modelo de `architecture.md`.

### Efecto

**Comprobado sobre el contrato**: parsea como YAML, las 20 operaciones tienen
`operationId` único, no hay ni un `$ref` roto, los 31 schemas están todos referenciados,
ningún parámetro de ruta queda sin declarar y no hay un solo `nullable:` —que es de
OpenAPI 3.0 y en 3.1 se escribe `type: [string, 'null']`—.

**La demo queda definida por exclusión, que es la parte útil**: entran F0 a F5 con la
regeneración dirigida completa y el export a PDF; sale el entrevistador conversacional, que
se recorta a formulario **conservando** la detección de datos faltantes y la contradicción
`edad-vs-tono` por reglas deterministas. El entrevistador sigue siendo requisito obligatorio
del alcance (RF-INTAKE-06), no un descarte.

**Lo que enseña este cambio.** La pregunta que más movió el diseño no fue ninguna de las de
arquitectura sino la de identidad: al responder «no hay ninguna» apareció que el brief lleva
datos personales reales a los prompts y a las trazas, que es un requisito de privacidad que
no estaba en ningún documento y que nadie había pedido. Preguntar quién llama obligó a
mirar qué viaja.

**Aprobadas el 2026-09-24 por Bruno Cruz.** `specs/spec1.md` pasa a `aprobada` y
**`specs/openapi.yaml` queda aprobado con ella**, en la misma fecha: el contrato es parte de
la spec y no un anexo, así que a partir de aquí cambiarlo es cambiar la spec. La versión del
contrato deja de ser `1.0.0-borrador` y pasa a `1.0.0`.

**Sigue pendiente**: `specs/plan1.md`, que nace en `borrador` y sin el cual no se escribe
una línea de código; y revisar TO-035, en particular si la tabla de trabajos es dominio o
materialización.

---

## RI-010 — El plan maestro del backend, de F0 a F5

**Fecha:** 2026-09-24 · **Ficheros:** `specs/plan1.md`, `specs/progreso.md`,
`docs/trade-offs.md`

### Causa

Con la spec 1 y su contrato aprobados, faltaba la tercera puerta del ciclo de cambio: sin
plan aprobado no se escribe código. Y el plan tenía que poder ejecutarlo un agente solo, de
principio a fin, reanudándose si la sesión se corta.

### Qué cambió

**Existe `specs/plan1.md`, en `borrador`**: 48 pasos numerados en seis fases, cada uno con
los requisitos que cubre, sus ficheros, la skill que se carga, las pruebas que se escriben
primero y un criterio de terminado ejecutable. Cada fase cierra con suite completa,
cobertura, `ruff`, `mypy`, conformidad con el contrato y una prueba de extremo a extremo; la
F1 añade el humo real opt-in con el brief de ejemplo.

**El test de conformidad nace en el primer paso** y tiene tres partes: comparación
estructural normalizada, una lista de operaciones pendientes que el último paso exige vacía,
y validación de cada respuesta de la suite contra el schema aprobado. Una meta-prueba de
mutaciones comprueba que la comparación puede fallar.

**Cuatro condiciones de parada, y solo cuatro**: falta la credencial al llegar al humo, una
decisión contradice la spec o el contrato, tres rojos seguidos en un paso, o el coste real
acumulado pasaría de 40 USD. Todo lo demás lo decide el agente y lo deja en
`specs/progreso.md` y, si es de diseño, con sus dos rastros.

**Existe `specs/progreso.md`**, el fichero de reanudación, y **TO-036** recoge las
veinticuatro decisiones de implementación del plan, marcadas para revisar.

### Efecto

**El plan destapó un choque entre la spec y el contrato**, que es lo más útil que ha dado:
RF-INTAKE-01 pide `200 valido:false` para un brief sin `destinatario.nombre`, y el schema
aprobado de `BriefNovela` hace ese campo obligatorio, así que el contrato obliga a un `422`.
El plan propone una lectura (D-01) y la deja **pendiente del desarrollador**: si no se
acepta, el P35 se detiene por la condición 2.

**Sigue pendiente**: aprobar el plan, decidir D-01 y revisar TO-035 y TO-036.

---

## RI-011 — El contrato cambia a 1.1.0 y la lectura tiene contrato

**Fecha:** 2026-09-24 · **Ficheros:** `specs/openapi.yaml`, `specs/spec1.md`,
`specs/plan1.md`, `specs/progreso.md`, `docs/architecture.md`, `docs/trade-offs.md`,
`CLAUDE.md`

### Causa

La revisión del plan 1 por el desarrollador. D-01 destapó que RF-INTAKE-01 no se podía
cumplir con el contrato aprobado —la sesión del frontend encontró el mismo fallo por su
lado—, y el plan dejaba en sus propias manos un contrato con el frontend que tenía que estar
en la spec.

### Qué cambió

**El contrato pasa a 1.1.0** (TO-037): `validarBrief` recibe un `BriefNovelaParcial` con
todos los campos opcionales y siete schemas nuevos; `crearNovela` sigue con el `BriefNovela`
completo; el ejemplo de `brief-invalido` deja de mostrar un dato faltante que el schema ya
no permite. Quedan 20 operaciones y 38 schemas, sin ningún `$ref` roto.

**La spec gana RF-INTAKE-01 reescrito**, con un segundo criterio —el mismo brief a crear da
`422`— y **§ 4.4, el contrato de lectura**: ruta, señal de carga, catorce selectores
`data-testid` con su cardinalidad y la hoja de impresión.

**El plan gana un paso, el P46**, que lleva ese contrato como dato comparado con la spec; el
P35 se reescribe sobre el brief parcial; el P49 pasa a ser el paso de integración con la
lectura real. Son 49 pasos.

**Las decisiones revisadas quedan escritas donde viven**: D-08 en el grafo de importación de
`architecture.md` —con cinco aristas más hacia `intake/` y `guardrail/` que la comprobación
destapó, todas sin ciclo—, D-09 en § Anatomía y en el layout de `CLAUDE.md`, D-22 en su
comando, y D-14 en la lista post-demo de `specs/progreso.md`.

### Efecto

**Comprobar el ciclo que pedía el desarrollador sacó más de lo que se buscaba.** La arista
`novel → intake` no creaba ciclo, pero al recorrer el plan paso a paso aparecieron cinco
dependencias más que el grafo no tenía: la capa Invariante necesita el brief, el Anticontexto
las palabras vetadas, la portada la dedicatoria. Sin la comprobación, la prueba de
importaciones del P02 habría fallado a mitad de la F1 por una arista que nadie había
decidido.

**Sigue pendiente**: aprobar el plan 1.

---

## RI-012 — F0 del plan 1: la fundación del backend

**Fecha:** 2026-09-24 · **Ficheros:** `backend/`, `config/thresholds.yaml`, `README.md`,
`docs/trade-offs.md` (TO-038)

### Causa

Primera fase del plan 1, aprobado por el desarrollador: sin fundación no hay nada sobre lo que
probar la generación.

### Qué cambió

Existe `backend/` con FastAPI y su `lifespan`: carga y valida `config/` con fallo en voz alta
nombrando la clave, aplica las migraciones con un runner que detecta una migración editada,
toma un cerrojo de instancia única, y crea el pool en vuelo FIFO, el trazador de Langfuse y el
cliente del modelo. Toda respuesta de error es `problem+json` del catálogo cerrado. `GET
/salud` cumple el contrato. La suite tiene el **test de conformidad con `specs/openapi.yaml`**
con su meta-prueba de mutaciones, las pruebas de arquitectura con las suyas y dos pruebas de
extremo a extremo con el proceso real. `config/thresholds.yaml` gana el timeout por llamada y
los precios por modelo.

### Efecto

**100 pruebas en verde, cobertura del 92 %**, `ruff` y `mypy --strict` limpios. Dos cosas que
solo aparecieron al ejecutar: el SDK de Anthropic 1.x va sobre `httpx2`, no sobre `httpx`, y
los casetes tienen que usar su transporte; y en Windows el proceso hijo escribe sus errores en
cp1252, así que las pruebas de extremo a extremo fuerzan UTF-8.


---

## RI-013 — El modelo se llama a través de Claude Code

**Fecha:** 2026-09-24 · **Ficheros:** `backend/app/commons/llm/{claude_code,fabrica}.py`,
`backend/app/main.py`, `config/models.yaml`, `config/thresholds.yaml`, `.env.example`,
`README.md`, `docs/architecture.md`, `specs/spec1.md`, `docs/verification.md`,
`docs/trade-offs.md` (TO-040)

### Causa

No hay clave de la API y el cierre de F1 exige una novela real. El desarrollador aprobó usar
la sesión de Claude Code de la máquina (I-04).

### Qué cambió

`ClienteModelo` tiene una segunda implementación que lanza el CLI de Claude Code sin
herramientas, sin MCP, sin personalizaciones, en una carpeta temporal vacía y con el texto
solo por la entrada estándar. `proveedor` en `config/models.yaml` la elige, y hoy vale
`claude_code`. El recuento previo pasa a ser una estimación con margen, el coste es nominal y
la salida estructurada se valida después. La spec, la arquitectura y las filas de
verificación afectadas lo dicen.

### Efecto

28 pruebas nuevas con un doble del subproceso, nueve de ellas con el corpus de inyección, y
una prueba real de contención: con la orden de producción, el CLI de verdad no leyó un fichero
canario, no escribió ni ejecutó nada aunque el texto se lo pedía. Dos datos que solo salieron
al probar en real: el CLI añade unos 2.600 tokens de entrada propios a cada llamada, y respeta
`CLAUDE_CODE_MAX_OUTPUT_TOKENS` cortando la respuesta y diciéndolo en el resultado.

---

## RI-014 — F1 del plan 1: una novela real de principio a fin

**Fecha:** 2026-09-24 · **Ficheros:** `backend/`, `config/thresholds.yaml`,
`ejemplos/brief-ejemplo.json`, `docs/trade-offs.md` (TO-039, TO-041), `docs/verification.md`
(O-02), `docs/architecture.md`

### Causa

Segunda fase del plan 1: generar una novela de diez capítulos de extremo a extremo, con
checkpoint, reanudación, gate mínimo y publicación inmutable, y demostrarlo con el modelo real.

### Qué cambió

Los pasos P11 a P27: guardrail, encargo y obra, máquina de estados como dato, prompts
versionados, canon, policy engine con audit log, ensamblado por capas, planificador, redactor
con sus hooks, extractor y aceptación, cola y worker, reintentos y topes, reanudación, gate y
publicación. El cierre añade el e2e de F1 con el backend como proceso real —incluida una
reanudación tras matar el proceso en el capítulo 5—, el humo real, el barrido de secretos y el
grabador de casetes. Las decisiones del agente quedan en TO-039 y TO-041; el proveedor
`claude_code`, en TO-040 y RI-013.

### Efecto

**288 pruebas en verde, cobertura del 96 %.** El humo real publicó la primera novela
(`data/storymaker-demo.db`, que reutilizan F4 y F5) en 27 minutos y 5,06 USD nominales.
Llegar a él costó tres intentos, y cada uno enseñó algo que la suite con dobles no podía ver:
el planificador necesitaba casi el doble de salida de la reservada; `nombres_exactos`
suspendía capítulos sanos porque los nombres de una novela son palabras comunes («Boya»,
«Varadero»); y la etiqueta de versión de prompt no cabía en Langfuse. Los casetes HTTP siguen
pendientes: solo se graban con `proveedor: api`, y no hay clave.
