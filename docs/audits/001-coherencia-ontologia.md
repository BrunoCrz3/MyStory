# Auditoría 001 — Coherencia entre ontología, instrucciones y alcance

**Fecha:** 2026-09-23 · **Tipo:** solo lectura, no se corrigió nada ·
**Ficheros auditados:** `docs/definitions.md`, `docs/domain-knowledge.md`, `CLAUDE.md`,
`AGENTS.md`

**Contrastado contra:** `docs/requerimientos/alcance-proyecto.md`, `docs/trade-offs.md`,
`docs/registro-iteraciones.md`, `config/thresholds.yaml`, `docs/architecture.md`,
`docs/verification.md`, `.claude/`.

## Notas de método

- **`docs/alcance.md` no existe.** El alcance vive en
  `docs/requerimientos/alcance-proyecto.md` (197 líneas). Es la tercera tarea consecutiva
  que lo cita en la ruta equivocada; conviene decidir si se mueve o si se corrige la
  costumbre.
- **`mmdc` no está instalado** y `npx mmdc` falla. La comprobación D2 se hizo con un
  verificador estructural propio —tipo de diagrama, balance de corchetes y paréntesis,
  `subgraph`/`end`, estados con espacios sin declarar— sobre los 21 bloques. **No se ha
  renderizado ninguno**, así que D2 queda como parcial por método, no por hallazgo.
- Donde no hay evidencia, se marca como no cumplido. No se ha dado nada por bueno por
  inferencia.

---

## Bloque A — Decisiones que debían conservarse

| ID | Comprobación | Estado | Evidencia | Corrección propuesta |
| --- | --- | --- | --- | --- |
| A1 | FastAPI, Python 3.12, Pydantic v2, features + `commons/` | ✅ | `CLAUDE.md:26` «FastAPI (Python 3.12) … Pydantic v2 para todo contrato»; `:18`; `:126-134` rodaja vertical y regla de importación | — |
| A2 | React 18 + TypeScript estricto | ✅ | `CLAUDE.md:27`; `:136` «TypeScript estricto, sin `any`» | — |
| A3 | SQLite única persistencia, `sqlite-vec` opcional | ✅ | `CLAUDE.md:28` «`sqlite-vec` es **opcional**: la recuperación funciona con filtro relacional y la similitud vectorial solo la ordena»; `:118` | — |
| A4 | Límite de contexto referenciado y no copiado, con regla de concurrencia | ✅ | `CLAUDE.md:29` referencia `contexto.total`; `:64-67` «la suma de las llamadas simultáneas no lo supera nunca»; `config/thresholds.yaml:42` y `:82`. Barrido de cifras: ninguna copiada (ver D7) | — |
| A5 | Capas, degradación, conteo antes, fallo en voz alta | ✅ | `CLAUDE.md:48-70`; orden de degradación en `:59-62`; «falla en voz alta» en `:70` | — |
| A6 | Ciclo spec → plan → código con puertas y frontmatter | ✅ | `CLAUDE.md:220-244`; frontmatter en `:233-235` | — |
| A7 | Por debajo de 300 líneas | ✅ | `CLAUDE.md` = 296 líneas; `AGENTS.md` = 16 | — |

---

## Bloque B — Decisiones que debían cambiar

| ID | Comprobación | Estado | Evidencia | Corrección propuesta |
| --- | --- | --- | --- | --- |
| B1 | Repo canónico; sin prohibición de editar la semilla; sin documento vivo como autoridad; decisión registrada | ⚠️ | **En los cuatro ficheros, cumple**: `CLAUDE.md:171-176`, y `docs/trade-offs.md:14-57` (TO-001). **Fuera de ellos, no**: `architecture.md:760-761` sigue diciendo «`definitions.md` y `domain-knowledge.md` **no se editan aquí**: se cambian en el documento vivo y se reexportan»; también `:814-815`, `:826-828`; y `docs/specs/001-backend-v1/propuesta-medida-de-deriva.md:11,269` | Borrar esas cuatro zonas de `architecture.md`. La spec 001 ya está marcada obsoleta |
| B2 | `CLAUDE.md` completo y legible | ✅ | 296 líneas con catorce secciones; `AGENTS.md:1-16` es stub y no duplica reglas | — |
| B3 | Varias novelas con `novel_id`, sin auth ni multiusuario | ✅ | `CLAUDE.md:40-44`; `definitions.md:393` «Toda tabla de dominio lleva `novel_id` … Ninguna tabla lleva `user_id` ni `tenant_id`» | — |
| B4 | El modo híbrido ya no es decisión cerrada | ✅ | `CLAUDE.md:17-22` no lo menciona; barrido de «modo híbrido» en los cuatro ficheros: 0 apariciones | — |
| B5 | Sin autor humano en producción; humanos = cliente/lector, revisor, desarrollador | ✅ | `definitions.md:265-270` los tres; `:270` «El autor humano ha salido del bucle»; `CLAUDE.md:13` y `:285-286` | — |
| B6 | Langfuse, Lean 4, TLA+/TLC, PDF y browser MCP declarados | ✅ | `CLAUDE.md:31-38`. El PDF **no** es una librería de PDF sino `page.pdf()` de Playwright, decidido y justificado en `trade-offs.md:99-135` (TO-003) | — |
| B7 | Idempotencia `novel_id` + `chapter_id` + `version` | ✅ | `CLAUDE.md:132-133`; `definitions.md:393` | — |
| B8 | Las seis reglas nuevas | ✅ | `CLAUDE.md:268` texto libre · `:271` secretos · `:272` span y score · `:274` reintentos · `:276` versión anterior · `:278` gate con Lean | — |

---

## Bloque C — Ontología frente al alcance

| ID | Comprobación | Estado | Evidencia | Corrección propuesta |
| --- | --- | --- | --- | --- |
| C1 | Capítulo como unidad; escena y beat eliminados o justificados | ✅ | `definitions.md:35-41` § Modelo de generación; justificación explícita en `:37`; `domain-knowledge.md:53-69` árbol sin nivel intermedio | — |
| C2 | Destinatario, Comprador, Ocasión, Dedicatoria; Brief de novela ≠ Brief de capítulo; Elemento personalizado; Texto libre; Dato faltante; Contradicción de brief | ⚠️ | Todas presentes en `definitions.md:65-76`. Brief de novela vs Brief de capítulo separados y declarados en `:25` § Convenciones. **Pero el «Comprador» se llama `Cliente`** (`:67`) y ese nombre colisiona con `Lector / Cliente` (`:267`) — ver D4 | Renombrar uno de los dos, o declarar que son la misma persona en dos momentos |
| C3 | Sin conceptos de ciencia ficción | ✅ | Barrido de novum, facción, plausibilidad especulativa, sentido de la maravilla, término canónico: 0 apariciones. `Regla del mundo` sobrevive generalizada y justificada en `definitions.md:110` | — |
| C4 | Clases de canon mapeadas a tabla; hecho ↔ capítulos N:M; cronología; fecha de nacimiento; evento excluyente | ✅ | `definitions.md:389-441` § Mapeo. N:M en `:413` (`hecho_capitulo`); cronología en `:409-411` (`evento`, `evento_personaje`); `fecha_nacimiento` en `:405`; `evento_excluyente` en `:412`. Las 19 entidades del `erDiagram` tienen tabla | — |
| C5 | Versionado completo y formato de lectura decidido o marcado | ❌ | Versión, Solicitud, Análisis, Regeneración, Marca y Página de novedades: todas en `definitions.md:286-297`. **Pero el formato de lectura se contradice**: `definitions.md:295` «**El formato de lectura es una decisión pendiente**» y `domain-knowledge.md:437` «sigue sin decidirse», frente a `CLAUDE.md:35` «como la lectura es web» y `CLAUDE.md:144-147`, que ya describe la página de lectura | Propagar la decisión (web) a los dos documentos de ontología y dejar `Página de novedades` como no aplicable |
| C6 | Cada dimensión con validador, tipo, punto de ejecución y score; ≥3 programáticos; LLM-judge con la rúbrica; revisión humana; Lean con ≥2 invariantes; browser MCP | ⚠️ | Tabla completa en `definitions.md:183-203`: 19 dimensiones con las cuatro columnas. Programáticos: 8. Semánticos que cubren la rúbrica del alcance: `consistencia_factica`, `adecuacion_tono`, `cierre_arco`, `coherencia_personajes`, `ritmo`, `personalizacion_natural`. Revisión humana con la misma rúbrica: `:234`. Lean: tres invariantes (`lean_cronologia`, `lean_ubicacion`, `lean_edad`). Browser MCP: `render_visual`. **Faltan dos cosas que el alcance §5b pide explícitamente**: `Score` no tiene atributo de **justificación** (`:321` «Resultado de un validador asociado a una traza»), y la clase `Rúbrica` (`:234`) **no enumera sus criterios**, así que nada ata los seis del alcance a ella | Añadir `justificacion` a `Score` y enumerar los criterios en `Rúbrica` |
| C7 | Guardrail: tres niveles con el tercero justificado, normalización, límite, audit log y Langfuse | ✅ | `definitions.md:216-232`. Tercer nivel `perfil` definido en `:224` y justificado en `:226`. Normalización en `:220`. Límite en `:222`. «Toda coincidencia queda en el audit log y en Langfuse» en `:228` | — |
| C8 | Roles, policy engine, hooks, estados alineados con TLA+, TLA+ como validador del harness | ✅ | Roles en `definitions.md:243-249`; policy engine y los dos hooks en `:252-260`; estados en `:272-278`; TLA+ situado en Capa 5 con la frase «Lean verifica la **historia**; la especificación del harness verifica el **sistema**» en `:311`. Las cuatro máquinas coinciden 1:1 con `domain-knowledge.md` | — |
| C9 | Trazabilidad como sesión, traza, span, score y versión de prompt | ✅ | `definitions.md:315-323`; jerarquía dibujada en `domain-knowledge.md:439-462` | — |
| C10 | Contexto adaptado al capítulo | ✅ | `definitions.md:152-162` las siete capas; `Resumen de capítulo` en `:168`; story bible como capa Estado en `:156`; palabras prohibidas en el Anticontexto en `:159` y `domain-knowledge.md:243-244` | — |
| C11 | Tabla de nomenclatura dominio ↔ código ↔ SQLite ↔ Langfuse | ✅ | `definitions.md:443-474` | — |
| C12 | Preguntas de competencia: cubren el dominio, cada clase responde a una, cada pregunta es respondible | ⚠️ | 30 preguntas, `definitions.md:477-530`, cubriendo las 12 que el encargo exigía. **Seis clases no las necesita ninguna pregunta**: `Cliente`, `Ocasión`, `Dedicatoria`, `Voz narrativa`, `Página de novedades` y `Biblia de la obra`. El propio documento dice en `:19` que «una clase entra en el modelo solo si alguna pregunta de competencia la necesita», así que es una violación de su criterio declarado | Añadir pregunta o retirar clase. `Dedicatoria` y `Página de novedades` las exige el alcance, luego les falta pregunta; `Biblia de la obra` es una vista y puede declararse como tal |

---

## Bloque D — Coherencia interna

| ID | Comprobación | Estado | Evidencia | Corrección propuesta |
| --- | --- | --- | --- | --- |
| D1 | Todo término de los diagramas definido; todo ciclo de vida dibujado | ✅ | Los cuatro conceptos con ciclo de vida de `definitions.md` —`Estado de hecho`, `Estado de promesa`, estados de novela y de capítulo— tienen diagrama, y los estados coinciden **exactamente** en ambos ficheros | — |
| D2 | Todos los bloques Mermaid parsean | ⚠️ | 21 bloques: 15 `flowchart`, 4 `stateDiagram-v2`, 1 `erDiagram`, 1 `sequenceDiagram`. Verificador estructural: **0 problemas**. Pero `mmdc` no está instalado, así que **ninguno se ha renderizado** | Instalar `@mermaid-js/mermaid-cli` y renderizar antes de dar D2 por cerrado |
| D3 | Términos obsoletos, con y sin tilde | ✅ | Barrido de escena, beat, hallazgo, deriva, replanificación rodante, novum, autor humano, documento vivo, una sola obra, facción, estado epistémico, término canónico: las únicas apariciones son el verbo «derivar» y prosa que dice explícitamente que el concepto ya no existe (`CLAUDE.md:13,285`; `definitions.md:57,254,270`; `domain-knowledge.md:69,370`) | — |
| D4 | Un concepto, un nombre | ⚠️ | **`Cliente` tiene dos significados**: clase de Capa 1 (`definitions.md:67`, «quien encarga y paga la novela») y mitad de `Lector / Cliente` en Capa 5 (`:267`, «pide cambios sobre la novela publicada»). El documento prohíbe esto en `:25` | Decidir si son la misma persona y, si lo son, decirlo; si no, renombrar |
| D5 | Roles, estados y features de `CLAUDE.md` coinciden con la ontología | ❌ | Roles y estados: coinciden. **Las nueve features no**. `CLAUDE.md:74-89` declara `intake/`, `novel/`, `canon/`, `context/`, `quality/`, `guardrail/`, `process/`, `policy/`, `versioning/`, y remite en `:75` y `:205` a `architecture.md` § Anatomía de una feature — que sigue listando **siete** features (`architecture.md:142-151`), sin `intake/`, `guardrail/`, `policy/` ni `versioning/`, con `findings/` y `replanning/` que ya no existen, y repartiendo clases eliminadas (Escena, Beat, Novum, Facción, Hallazgo, Deriva) | Reescribir `architecture.md` § Anatomía de una feature. Hasta entonces el puntero de `CLAUDE.md` lleva a información falsa |
| D6 | Cada ruta citada existe o está marcada | ✅ | 16 marcas **▸ previsto** en `CLAUDE.md`. Comprobación automática: ninguna ruta inexistente sin marcar | — |
| D7 | Sin cifras copiadas fuera de `config/thresholds.yaml` | ✅ | Únicos números de tres o más dígitos en los cuatro ficheros: el puerto `8000` (`CLAUDE.md:152,217`), el propio límite de `300` líneas (`:293`), los identificadores `TO-002`/`TO-003` y las fechas de cabecera | — |
| D8 | Sin secretos, claves ni IDs reales | ✅ | Barrido de `sk-*`, `api_key`, `token=`, `password`, `secret=`, `bearer` y cadenas hex de 32: 0 coincidencias | — |

---

## Bloque E — Trazabilidad del proceso

| ID | Comprobación | Estado | Evidencia | Corrección propuesta |
| --- | --- | --- | --- | --- |
| E1 | `trade-offs.md` recoge las siete decisiones, con opciones, criterio y elección | ❌ | Solo hay cuatro: TO-001 canonicidad, TO-002 `CLAUDE.md`, TO-003 PDF, TO-004 multi-novela (`trade-offs.md:14,60,99,137`). Las cuatro tienen opciones, criterio y elección. **Faltan cinco**: unidad capítulo, modo híbrido simplificado (invalidación en vez de deriva), verificador de continuidad como validadores y no como rol, tercer nivel de palabras prohibidas, y formato de lectura. Agravante: `registro-iteraciones.md:69-70` promete que esas decisiones se registrarán «como TO-002 y siguientes», y esos identificadores se usaron después para otras cosas | Añadir TO-005…TO-009 y corregir la referencia adelantada de RI-001 |
| E2 | El registro tiene entradas causa → efecto, no un diario | ✅ | RI-001 (`:17`) y RI-002 (`:107`), ambas con Causa, Qué cambió y Efecto explícitos | — |

---

## Hallazgo transversal — el que más rompe

No cae dentro de ningún bloque del encargo, pero es el de mayor alcance y sale de la
decisión TO-002.

**Al vaciar `AGENTS.md`, unas cuarenta referencias del repositorio apuntan a secciones que
ya no existen.** `AGENTS.md` tiene hoy un único encabezado (`AGENTS.md:1`) y ninguna
sección. Siguen citándose `§ Presupuesto`, `§ Persistencia…`, `§ Requisitos técnicos`,
`§ Modelo de autoría`, `§ Alcance`, `§ Ciclo de cambio`, `§ Canonicidad y sincronía`,
`§ Comandos` y «regla 3/4/5/6/7 de `AGENTS.md`».

| Fichero | Referencias rotas | Ejemplos |
| --- | --- | --- |
| `docs/verification.md` | ~30 | `:117` «`AGENTS.md` § Presupuesto», `:132` «§ Persistencia…», `:154` «§ Alcance» |
| `docs/architecture.md` | 14 | `:12`, `:21`, `:412`, `:750` «§ Ciclo de cambio», `:761` «§ Canonicidad y sincronía» |
| `.claude/skills/` | 3 | `backend-feature-slice:106`, `plan-de-verificacion:27`, `sqlite-relacional:98` |
| `docs/trade-offs.md` | 3 | `:16` «Afecta a: `AGENTS.md` § Contexto semilla» — esa sección está hoy en `CLAUDE.md` |
| `docs/registro-iteraciones.md` | 2 | `:12` cita «`AGENTS.md` § Contexto semilla» como fuente de la regla de evidencia en git |
| `docs/specs/001-backend-v1/` | ~8 | ya marcada obsoleta |

Los dos últimos duelen más de lo que parece, porque `trade-offs.md` y
`registro-iteraciones.md` **sí** son documentos vigentes y recién escritos.

**Segundo puntero falso, en el mismo grupo.** `CLAUDE.md:207` promete que
`docs/verification.md` dice «qué valida cada validador, dónde corre y con qué score».
`verification.md` tiene **cero** apariciones de «punto de ejecución», «score», «Langfuse» y
«hook de»: sigue siendo la tabla `T/A/I/D/U` del sistema anterior.

---

## Matriz de cobertura del alcance

### Requisitos que afectan a la ontología o a las instrucciones

| § del alcance | Requisito | Dónde se soporta |
| --- | --- | --- |
| 1 | Entrevistador recoge nombre, edad, rasgos, recuerdos, género, tono, extensión | `definitions.md` § Bloque A: `Destinatario`, `Brief de novela`; rol `Entrevistador` |
| 1 | Palabras y temas vetados por el cliente | `Palabra prohibida` nivel `novela` |
| 1 | Detecta datos que faltan | `Dato faltante` |
| 1 | Detecta ≥1 tipo de contradicción (edad vs género o tono) | `Contradicción de brief`, con esos tipos nombrados |
| 1 | Texto libre tratado como no confiable | `Texto libre aportado`, `Fragmento sospechoso`; `CLAUDE.md` regla 11 |
| 1 | Brief estructurado y validado con schema | `Brief de novela` + validador `schema_valido` |
| 2 | Índice, ficha de personajes y lugares, portada con dedicatoria | `CLAUDE.md:144-147`; `Dedicatoria`; validador `render_visual` |
| 2 | Petición de cambio desde la página | `Solicitud de cambio` con atributo `origen` |
| 2 | Identificar capítulos que usan el hecho | `Uso de hecho` (N:M) + `Análisis de impacto` |
| 2 | Regenerar solo esos sin romper continuidad | `Regeneración dirigida` + gate completo |
| 2 | Marcar capítulos cambiados | `version_capitulo.modificado` |
| 2 | Página de novedades si PDF | `Página de novedades` — **condicionada a un formato que se contradice** (C5) |
| 2 | Conservar la versión anterior | `Versión de novela`; `CLAUDE.md` regla 15 |
| 3 | Tres roles mínimo + entrevistador | Cinco roles en `definitions.md:243-249` |
| 3 | `CLAUDE.md` como archivo de instrucciones | `CLAUDE.md`, 296 líneas |
| 3 | **Una skill reutilizable** | **Sin cobertura** en los cuatro ficheros |
| 3 | Dos hooks: validación y policy | `Hook de capítulo`, `Hook de policy` |
| 3 | Tools con schema validado | Validador `schema_valido` |
| 3 | Retries con límite | `Límite de reescrituras`, `Capitulo.intentos`; regla 14 |
| 3 | Tokens y coste por novela en Langfuse | `Sesión`, `Traza`, `Span` |
| 4 | Story bible en SQLite con uso por capítulo | `hecho` + `hecho_capitulo` |
| 4 | Tabla de cronología | `evento`, `evento_personaje`, `lugar` |
| 4 | Resúmenes por capítulo | `Resumen de capítulo` |
| 4 | Checkpoint por capítulo | `Checkpoint`; pregunta 25 |
| 5a | ≥3 validadores programáticos | Ocho |
| 5a | Validación visual por browser MCP | `render_visual`; `.claude/mcp.json` ▸ previsto |
| 5b | LLM-as-judge con rúbrica de seis criterios | Seis dimensiones semánticas, **pero la `Rúbrica` no los enumera** (C6) |
| 5b | Puntuación por criterio **y justificación** | **Sin cobertura**: `Score` no tiene justificación (C6) |
| 5b | Revisión humana con la misma rúbrica | `Revisor humano`; pregunta 24 |
| 5c | Fichero Lean generado desde la story bible | `definitions.md:206`; entradas verificadas en C4 |
| 5c | ≥2 invariantes | Tres: `lean_cronologia`, `lean_ubicacion`, `lean_edad` |
| 5c | Si falla, no se publica | `CLAUDE.md` regla 16; gate de publicación |
| 5d | Especificación del harness como máquina de estados | `Especificación del harness`; estados 1:1 |
| 5d | ≥3 invariantes de seguridad y ≥1 de liveness | `Invariante de seguridad`, `Propiedad de liveness` — clases presentes; **los enunciados concretos se difieren a `formal/*/README.md`**, aún inexistentes |
| 5d | Correspondencia especificación ↔ código | Atributo «correspondencia con el código» de `Especificación del harness` |
| 5d | Contraejemplos documentados | `Contraejemplo`; pregunta 30 |
| 5d | TLC sobre modelo pequeño | `config/thresholds.yaml` § `modelo_formal` |
| 6 | Sesión por novela, span por rol y tool, score por validador, prompt versionado | `definitions.md:315-323`; regla 13 |
| 7 | Palabras prohibidas en tres niveles | `Nivel de palabra prohibida`; tercero justificado |
| 7 | Normalización antes de comparar | `Normalización` |
| 7 | Límite de intentos y parada informada | `Límite de reescrituras`; regla 14 |
| 7 | Coincidencia en audit log y Langfuse | `definitions.md:228` |
| 7 | Máximo de 100.000 tokens concurrentes | `en_vuelo.total`; `CLAUDE.md:64-67` |
| Opcional | Login de usuarios | Declarado **fuera de alcance** en TO-004 y `CLAUDE.md:40-44` |

### Requisitos que no corresponden a estos documentos

Se listan para que no se pierdan. Ninguno es un fallo de la ontología ni de las
instrucciones; todos están **reservados en el layout** de `CLAUDE.md:77-104` salvo donde se
indica.

| § | Requisito | Estado |
| --- | --- | --- |
| 5 | Cinco briefs de prueba, uno adversarial y uno con incoherencia temporal | Fuera de estos documentos; sin reserva en el layout |
| 5 | Tabla de qué validador pasó por brief | Fuera; sería de `docs/verification.md` |
| 5 | Iteración de tuning documentada | Fuera; `docs/registro-iteraciones.md` es su sitio natural |
| 5c | Caso real en que Lean detecta lo que nadie más | Fuera; `formal/lean/` ▸ previsto |
| — | Novela de ejemplo en `/ejemplos/novela-ejemplo.pdf` | `ejemplos/` ▸ previsto |
| — | Vídeo de demo en `/presentacion/` | `presentacion/` ▸ previsto |
| — | Spec inicial, trade-offs, explainers, diagramas, registro, red-team | Reservados; trade-offs y registro **ya existen** |
| — | `.env.example` | ▸ previsto |
| — | `.claude/` commiteada con memoria, comandos y `mcp.json` | `skills/` existe; `commands/` y `mcp.json` ▸ previsto |
| — | Uso real del browser MCP documentado | `docs/browser-mcp.md` ▸ previsto |
| Opc. | Servidor MCP, linters de prosa, linter de edición manual, seguridad por agentes | Fuera; ninguno reservado |

---

## Resumen — los ❌ por gravedad

**1 · Cuarenta referencias rotas a secciones de `AGENTS.md`.**
Es lo más grave porque degrada en silencio: un agente que siga «ver `AGENTS.md` § Requisitos
técnicos» encuentra un stub de dieciséis líneas y se queda sin la regla, sin que nada
falle. Afecta a `docs/verification.md` (~30), `docs/architecture.md` (14),
`.claude/skills/` (3), `docs/trade-offs.md` (3) y `docs/registro-iteraciones.md` (2).
**Ficheros a tocar:** los cinco. En los dos últimos es un reemplazo trivial de `AGENTS.md`
por `CLAUDE.md`.

**2 · `CLAUDE.md` § Layout apunta a una tabla de features que contradice lo que él mismo
declara (D5).** Nueve features frente a las siete de `architecture.md:142-151`, que además
reparte clases eliminadas. Un agente que pregunte «¿de quién es esta clase?» recibe la
respuesta del sistema anterior. **Fichero a tocar:** `docs/architecture.md`.

**3 · El formato de lectura se contradice entre los cuatro ficheros auditados (C5).**
`CLAUDE.md:35` da la web por decidida; `definitions.md:295` y `domain-knowledge.md:437`
dicen que sigue pendiente. Bloquea decidir si `Página de novedades` existe.
**Ficheros a tocar:** `docs/definitions.md`, `docs/domain-knowledge.md`.

**4 · Faltan cinco decisiones en `docs/trade-offs.md` (E1).** Unidad capítulo, invalidación
en vez de deriva, verificador de continuidad, tercer nivel del guardrail y formato de
lectura. El alcance evalúa explícitamente los trade-offs, así que esto puntúa. Además
`registro-iteraciones.md:69-70` promete unos identificadores que ya se gastaron.
**Ficheros a tocar:** `docs/trade-offs.md`, `docs/registro-iteraciones.md`.

**5 · `CLAUDE.md:207` promete de `verification.md` algo que no contiene.** Cero
apariciones de score, punto de ejecución, Langfuse o hook. **Ficheros a tocar:**
`docs/verification.md`, que debería convertirse en la tabla de validadores.

Los ⚠️ que conviene no dejar pasar: `Score` sin justificación y `Rúbrica` sin criterios
(C6, los pide el alcance §5b literalmente), las seis clases huérfanas (C12), y la
ambigüedad de `Cliente` (C2/D4).

---

## Pendientes fuera de los cuatro ficheros

| Fichero | Qué le falta |
| --- | --- |
| `docs/architecture.md` | Las nueve features y su tabla clase → feature; los roles y agentes; las skills del sistema; la orquestación sobre estados de capítulo y de novela; § Pendiente de llevar a la ontología, obsoleta entera; las referencias a `AGENTS.md`; la regla de documento vivo de `:760-761` |
| `docs/verification.md` | Convertirse en la tabla de validadores con punto de ejecución y score. Sus 105 filas siguen hablando de escenas, deriva y autor humano. Necesita además una fila nueva: **la consulta de dominio que olvide acotar por `novel_id`** es un fallo silencioso y hoy nada lo caza |
| `.claude/skills/presupuesto-de-contexto` | Brief de capítulo en vez de escena; compresión de tres niveles |
| `.claude/skills/backend-feature-slice` | Las nueve features; referencia a `AGENTS.md` |
| `.claude/skills/sqlite-relacional` | `novel_id`, idempotencia nueva; referencia a `AGENTS.md` |
| `.claude/skills/sqlite-vec` | Pasa a uso opcional |
| `.claude/skills/feature-sliced-design` | Páginas de entrevista y lectura |
| `.claude/skills/plan-de-verificacion` | Referencia a `AGENTS.md` |
| `config/thresholds.yaml` | Nada bloqueante. `modelo_formal` y `guardrail` entraron con la reescritura; la mayoría de umbrales sigue en `null`, que es lo esperado hasta que haya corpus |
| `docs/specs/001-backend-v1/` | `aprobada` y obsoleta: describe el sistema anterior entero |
| Infraestructura | `.claude/mcp.json`, `.claude/commands/`, `.env.example`, `formal/`, `ejemplos/`, `presentacion/`, `docs/spec-inicial.md`, `docs/red-team.md`, `docs/browser-mcp.md`, `docs/explainers/` — todos reservados en el layout, ninguno creado |

---

## Estado de las correcciones

Añadido el 2026-09-23, después de aplicar la tarea de correcciones parciales. **El cuerpo
del informe de arriba no se ha tocado**: es el diagnóstico tal como se emitió.

### Corregido

| Hallazgo | Qué se hizo | Dónde |
| --- | --- | --- |
| **C5** · Formato de lectura contradictorio | Cerrado como **web, con el PDF como export** del mismo render. Se retira el «pendiente» de los dos documentos de ontología y se elimina la clase `Página de novedades`, cuyo dato ya vive en la marca del vínculo versión ↔ capítulo. El `origen` de la `Solicitud de cambio` deja de distinguir formatos | `definitions.md` § Versionado y regeneración; `domain-knowledge.md` § Solicitud de cambio; TO-009 |
| **C6** · `Score` sin justificación, `Rúbrica` sin criterios | `Score` lleva justificación cuando el validador es semántico. `Rúbrica` enumera los seis criterios del alcance §5b con la dimensión que puntúa cada uno, y declara que cada criterio se puntúa por separado | `definitions.md` § Capa 4 y § Capa 5 |
| **E1** · Faltaban cinco decisiones en trade-offs | Añadidas **TO-005** a **TO-009**, más **TO-010** por la división de `Cliente`. Las cuatro registradas a posteriori lo declaran en su cabecera | `docs/trade-offs.md` |
| **E1 bis** · Promesa de IDs incumplida en RI-001 | Corregida sin reescribir la historia: el párrafo original se conserva y lleva debajo una nota que dice qué identificadores se gastaron y cuáles acabaron siendo | `registro-iteraciones.md` RI-001 |
| **Transversal** · Referencias rotas a `AGENTS.md` | Reapuntadas a `CLAUDE.md` en los cinco ficheros vigentes de esta tarea: `trade-offs.md` (4), `registro-iteraciones.md` (1) y las skills `backend-feature-slice`, `plan-de-verificacion` y `sqlite-relacional` | — |
| **Punto 8** de la tarea | Fila `Alcance y requisitos del proyecto` en «Dónde está cada cosa». `CLAUDE.md` sigue en **296 líneas** | `CLAUDE.md` |

**Referencias a `AGENTS.md` que se dejaron a propósito.** No son punteros rotos: son el
sujeto del que se habla. TO-002 entero, la entrada RI-002, y los párrafos de «Efecto» de
RI-001 que describen qué estaba pendiente **en aquel momento**. Reescribirlos convertiría
el registro en una crónica de lo que debería haber pasado.

### Diferido

Dos de los cuatro se cerraron después; se dejan tachados para que el rastro no se pierda.

| Hallazgo | A qué tarea | Por qué |
| --- | --- | --- |
| ~~**D5**~~ | — | **Cerrado.** `architecture.md` rehizo la tabla clase → feature con las nueve features (RI-004) y `CLAUDE.md` se reconcilió con ella (RI-005) |
| ~~**B1**~~ | — | **Cerrado.** El texto de documentos vivos y reexportación desapareció con la reescritura de `architecture.md` (RI-004) |
| **Transversal** · Referencias a `AGENTS.md` | Regeneración de `docs/verification.md` | **A medias.** `architecture.md` quedó en **cero** al reescribirse (RI-004). Las 36 que quedan están todas en `verification.md`. Las de `trade-offs.md`, el registro y `CLAUDE.md` no cuentan: ahí `AGENTS.md` es el sujeto del que se habla, no un puntero |
| **Puntero falso de `CLAUDE.md:207`** · `verification.md` no contiene scores ni puntos de ejecución | Regeneración de `docs/verification.md` | El puntero será cierto cuando ese fichero se convierta en la tabla de validadores |

### Corregido en la segunda tanda

Aprobada aparte y aplicada después de la primera.

| Hallazgo | Qué se hizo | Dónde |
| --- | --- | --- |
| **C2/D4** · `Cliente` con dos significados | Partido en **`Comprador`** —paga y configura— y **`Lector`** —lee y pide cambios, papel que ocupa el comprador o el destinatario—. «Cliente» deja de ser término de la ontología. Renombrado en tablas de clases, relaciones, mapeo y nomenclatura, en los diagramas, en `CLAUDE.md` (feature `intake/` y regla 11) y en los dos comentarios de `config/thresholds.yaml` que sí se referían a este concepto | TO-010; los cuatro documentos y `thresholds.yaml` |
| **C12** · Clases huérfanas | Las seis, cerradas. `Página de novedades` desapareció con C5. **`Biblia de la obra` se fusiona en `Story bible`**: su definición decía literalmente «Es la story bible». Las cuatro restantes ganan pregunta: la **1** cubre `Comprador`, `Ocasión` y `Dedicatoria`; la **10**, `Voz narrativa`. Las preguntas pasan de **30 a 33** | `definitions.md` § Preguntas de competencia |
| **C12 bis** · Huérfana creada por la propia corrección | Al partir `Cliente`, `Lector` nacía sin ninguna pregunta que lo necesitara. Se añadió la **23**, que no estaba en la propuesta aprobada, y queda anotado en RI-003 | `definitions.md`; RI-003 |

Las tres preguntas nuevas **nombran la clase literalmente**, no por rodeo, para que la
cobertura se compruebe con un `grep` en vez de depender de que alguien lea y juzgue.

**Comprobado tras aplicar**: ninguna clase sin pregunta, ningún nombre con dos
significados, `CLAUDE.md` en 296 líneas, los 21 bloques Mermaid sin problemas
estructurales, y la única «cliente» superviviente es «el cliente tipado del OpenAPI», que
no es este concepto.

### Pendiente de aprobación

Nada. Los seis hallazgos de esta auditoría están cerrados o diferidos con destino.

### Sin cambio

`config/thresholds.yaml` no se tocó: la auditoría no le encontró nada bloqueante. Las
rutas reservadas del layout —`formal/`, `ejemplos/`, `presentacion/`, `.env.example`,
`.claude/mcp.json`, `.claude/commands/`, `docs/spec-inicial.md`, `docs/red-team.md`,
`docs/browser-mcp.md`, `docs/explainers/`— siguen sin crearse, marcadas **▸ previsto**.

### Nota de método, para la próxima auditoría

Los tres hallazgos de mayor alcance —referencias rotas, features contradictorias y formato
de lectura— nacieron de cambios correctos aplicados sin barrer lo que arrastraban, y
ninguno era visible leyendo el fichero que se estaba editando. Conviene que la regeneración
de `architecture.md` y `verification.md` termine con el mismo barrido cruzado que produjo
este informe, no con la lectura del fichero nuevo.
