# CLAUDE.md

Fuente canónica y única de instrucciones para cualquier agente que trabaje en este
repositorio. `AGENTS.md` no contiene reglas: solo apunta aquí.

Aquí vive **la regla**; el detalle, en `docs/architecture.md` y en las skills. Si alguno
choca con este archivo, manda este archivo.

**Qué construye este repositorio.** Un sistema agéntico que genera novelas personalizadas
para regalar: un entrevistador recoge los datos del destinatario, un planificador fija el
destino de cada capítulo, un redactor los escribe, un editor los critica y una batería de
validadores —programáticos, semánticos y formales— decide si se publica. La generación es
automática de principio a fin: **no hay autor humano en el bucle**.

## Requisitos técnicos

> **Estas decisiones ya están tomadas y no se renegocian dentro de una tarea:
> FastAPI para el backend, organizado por features con una carpeta `commons/` para lo
> compartido; React con TypeScript para el frontend; SQLite como única persistencia; y la
> ventana de contexto que declara `config/thresholds.yaml`. Si una tarea parece exigir
> cambiarlas, detente y pregunta: no propongas alternativas ni introduzcas dependencias
> equivalentes.**

| Capa | Tecnología | Notas |
| --- | --- | --- |
| Backend | FastAPI (Python 3.12) | API asíncrona, Pydantic v2 para todo contrato de datos |
| Frontend | React 18 + TypeScript | Vite como bundler, sin framework de servidor |
| Persistencia | SQLite | Un único fichero `data/storymaker.db`. **`sqlite-vec` no se usa en v1** (`trade-offs.md` TO-015): la novela entera cabe en la capa Recuperado, así que basta el filtro relacional |
| Modelo | `id` y `effort` por rol en `config/models.yaml` | Tope por petición en `contexto.total`. **No es la ventana del proveedor**, que es mayor: es un límite nuestro, y ningún prompt lo supera |

**Dependencias que el alcance exige** y que la regla 6 bloquearía si no estuvieran aquí:
SDK de **Langfuse**; **Lean 4** con `lake` para verificar la cronología; **TLA+ tools** con
TLC para el harness; **Playwright** para el browser MCP y el PDF; en el frontend,
`react-router-dom` y `openapi-fetch` (TO-051). Ninguna añade infraestructura de servidor. El PDF sale de Playwright y no de una librería de PDF: como la
lectura es web, se exporta del render que los validadores acaban de comprobar, y otro motor
sería validar uno y entregar otro (`trade-offs.md` TO-003). Excluido: Postgres, pgvector,
Pinecone, Chroma, Django, Flask, Next.js, Vue, Redis, Celery y todo ORM que oculte el SQL.

**Alcance de instancia: varias novelas, un solo usuario.** Toda tabla de dominio lleva
`novel_id` desde la primera migración. **No hay multiusuario ni autenticación en v1**:
ninguna tabla lleva `user_id` ni `tenant_id`, y el login opcional se añadiría después como
migración. Si una tarea parece requerir cuentas, detente y pregunta.

## Presupuesto de contexto

El ensamblador reparte la ventana por capa. Si una capa se pasa, se comprime esa capa:
nunca se roba presupuesto a otra ni se supera el total.

> **Las cifras no están aquí.** El reparto vive en `config/thresholds.yaml`, fuente única
> de umbrales de todo el sistema. Este documento describe la política; los números se leen
> del fichero, nunca se copian a un documento ni se escriben sueltos en el código.

Las **siete capas** —Invariante, Estructural, Estado, Local, Recuperado, Estilo y
Anticontexto— más el **Margen**, con su fuente y su presupuesto: skill
`presupuesto-de-contexto`. **La capa Invariante se compone y se presupuesta por rol**: no
todos cargan las mismas skills de runtime, así que no todos tienen el mismo sitio libre.

**Política de degradación.** Cuando el ensamblado no cabe se comprime en el orden
Recuperado → Estilo → Local → Estado, parando en cuanto quepa. La capa Invariante y la
restricción de destino **no se degradan nunca**: son lo que impide que el capítulo deje de
ser de esta novela o deje de ir adonde tiene que ir.

**Dos presupuestos, no uno.** `contexto.total` limita **una** petición; `en_vuelo.total`,
**cuántas caben a la vez**: la suma de las llamadas simultáneas no lo supera nunca y un
trabajo que no quepa espera. Son cifras distintas aunque hoy coincidan, y el alcance habla
de la segunda.

Regla: el contador de tokens se calcula **antes** de llamar al modelo, no después. Un
ensamblado que no cabe falla en voz alta; no se trunca en silencio.

## Layout del repositorio

Nueve features más `commons/`, una por bloque coherente de la ontología. Qué clase es
dueña cada una: `docs/architecture.md` § Anatomía de una feature.

```
CLAUDE.md               esta guía; AGENTS.md solo apunta aquí
backend/app/            main.py monta los routers de cada feature
  intake/               Capa 1A · encargo: comprador, destinatario, brief de novela
  novel/                Capa 1B · obra, capítulo, personaje, lugar, evento, arco
  canon/                Capa 2  · story bible: hechos, snapshots, promesas, retcon
  context/              Capa 3  · ensamblado, presupuesto, recuperación, anticontexto
  quality/              Capa 4  · validadores, defectos, rúbrica, informe de crítica
  guardrail/            Capa 4  · palabras prohibidas, normalización, coincidencias
  process/              Capa 5  · esquema, briefs, borradores, extracción, checkpoint
  policy/               Capa 5  · policy engine, decisiones, audit log
  versioning/           Capa 5  · versiones, solicitud de cambio, regeneración
  commons/              db, migraciones, modelo, tokens, errores, Langfuse
  mcp_server/           adaptador del servidor MCP · no es feature
  skills/ · prompts/    skills de runtime y un prompt por rol · no son features
frontend/src/           FSD v2.1: app/, pages/, shared/
formal/lean/            ▸ previsto · cronología e invariantes de la historia
formal/tla/             ▸ previsto · especificación del harness y el .cfg de TLC
docs/                   contexto semilla y documentación de proceso (ver tabla abajo)
specs/                  specN.md y planN.md de v1, ambos con frontmatter
config/thresholds.yaml  fuente única de cifras y umbrales
config/models.yaml      id y effort de modelo por rol
data/storymaker.db      base de datos, no versionada; empieza vacía
ejemplos/               novela-ejemplo.pdf y brief-ejemplo.json
presentacion/           ▸ previsto · vídeo de demo
.env.example            plantilla de secretos, nunca los secretos
.claude/skills/         skills de desarrollo (ver docs/architecture.md § Skills)
.claude/agents/         ▸ previsto · agente de seguridad
.claude/commands/       ▸ previsto · comandos propios
.mcp.json               browser MCP del agente (Edge); no .claude/mcp.json (TO-051)
skills-lock.json        origen y hash de las skills instaladas
```

**▸ previsto** es lo que el layout reserva y todavía no existe: no hay código hasta que su
plan esté aprobado (ver «Ciclo de cambio»), y una ruta que apunte ahí es destino.

## Persistencia, backend y frontend

El detalle operativo está en la skill que nombra cada bloque, y cargarla **antes** de
escribir no es opcional.

**Base de datos** — skill `sqlite-relacional`; `sqlite-vec` solo si algún día se reactiva
el vector. Un solo fichero, SQL explícito, sin servidor y sin ORM. Migraciones numeradas en
`backend/app/commons/db/migrations/`, aplicadas en orden y **nunca editadas** una vez
commiteadas. `WAL` activado; escrituras a la story bible siempre en transacción. **Toda
tabla de dominio lleva `novel_id`.** La recuperación filtra por las entidades del brief de
capítulo antes de ordenar: nunca similitud sola.

**Backend** — skill `backend-feature-slice`. Una feature por carpeta, rodaja vertical
completa, y la feature es la unidad de cambio; la anatomía y la regla de importación están
en `docs/architecture.md` § Anatomía de una feature. Todo contrato es Pydantic: sin `dict`
sueltos cruzando capas. Escrituras a la story bible **idempotentes por `novel_id` +
`chapter_id` + `version`**. Llamadas al modelo asíncronas y con timeout explícito. Errores
de dominio a HTTP en un handler central.

**Frontend** — skill `feature-sliced-design`. React con TypeScript estricto, sin `any`;
estado de servidor con TanStack Query. FSD v2.1, empezando por `app/`, `pages/` y
`shared/`, y **`widgets/` no se usa**. El cliente tipado vive en
`frontend/src/shared/api/` y se deriva del OpenAPI: los tipos no se escriben a mano dos
veces. Sin lógica de dominio en el frontend: la story bible se decide en el backend.

**Tres páginas** (TO-051). `entrevista` recoge los datos del destinatario y señala faltantes
y contradicciones. `progreso` sigue una generación y es el destino común de la entrevista y
de la confirmación de un cambio. `lectura` es la novela: índice, ficha enlazada a sus
capítulos, portada con dedicatoria, petición de cambio en página y marca de los modificados.

## Comandos

```bash
uv run uvicorn app.main:app --reload --port 8000   # backend
uv run pytest                                      # toda la suite
uv run pytest tests/guardrail                      # el guardrail tiene suite propia
uv run ruff check . && uv run ruff format .
npm run dev && npm run test && npm run typecheck   # frontend
lake build                                         # formal/lean/ · cronología
tlc -config formal/tla/harness.cfg formal/tla/harness.tla   # formal/tla/ · harness
uv run python -m app.prompts.sync                  # publica prompts en Langfuse, idempotente
uv run python -m app.versioning.export <novel_id> <version>   # PDF de una versión publicada
```

## Contexto semilla

Dos documentos definen el dominio. Todo modelo de datos, endpoint, componente o prompt de
este repositorio deriva de ellos. Son lectura obligatoria antes de tocar código de dominio.

| Documento | Ruta en repo | Qué es |
| --- | --- | --- |
| Definiciones | `docs/definitions.md` | Vocabulario: clases, atributos, relaciones, preguntas de competencia |
| Conocimiento de dominio | `docs/domain-knowledge.md` | Diagramas Mermaid: jerarquías, grafo de entidades, máquinas de estado |

**Canonicidad.** El repositorio es la fuente canónica de la ontología: manda lo que está en
esos dos ficheros. No hay documento vivo externo ni nada que reexportar; los cambios de
ontología se hacen aquí, igual que `docs/architecture.md`, y van en su propio commit.

**Todo cambio de decisión deja dos rastros**, no uno: el **porqué** en
`docs/trade-offs.md` —opciones, criterio y elección— y el **qué cambió, qué lo provocó y qué
efecto tuvo** en `docs/registro-iteraciones.md`. Los dos van en el mismo commit que el
cambio, porque el historial de git es la evidencia de ambos. No es solo para la ontología:
vale para cualquier decisión que este repositorio tome sobre sí mismo.

Qué sección responde a qué pregunta y cómo se usan al escribir código:
`docs/architecture.md` § Frontera con el contexto semilla.

## Modelo de generación

La novela se planifica entera y se escribe capítulo a capítulo, **sin humano en el bucle**.
Consecuencias operativas para cualquier agente que genere o revise texto:

- El **capítulo** es la unidad atómica de generación, validación, checkpoint, regeneración
  y marca de cambio entre versiones. No hay unidad por debajo.
- El brief de capítulo es mínimo: estado de entrada más **restricción de destino**. Un
  capítulo descubre *cómo*, no *hacia dónde*; cambiar el destino exige replanificar.
- Los hechos se **extraen** tras aceptar el capítulo. Entran como `propuesto` y quien los
  adopta es el **policy engine**, con la decisión en el audit log.
- El retcon marca `obsoleto`, **en la candidata**, a los capítulos que **usan** el hecho —no
  solo al que lo estableció— y encola su reescritura, sin tocar el resto. **Una regeneración
  fallida no modifica ninguna versión publicada**: la candidata se rechaza y la novela sigue.
- La replanificación se dispara cuando el canon invalida una restricción pendiente, nunca
  por cadencia ni en mitad de un capítulo, y solo toca capítulos no escritos.

## Dónde está cada cosa

| Necesitas | Ruta |
| --- | --- |
| Alcance y requisitos del proyecto | `docs/requerimientos/alcance-proyecto.md` |
| Clases, atributos, relaciones, preguntas de competencia | `docs/definitions.md` |
| Jerarquías, grafos y máquinas de estado | `docs/domain-knowledge.md` |
| Sistema, agentes, hooks, proceso de producción y ciclo de cambio | `docs/architecture.md` |
| Qué feature es dueña de cada clase | `docs/architecture.md` § Anatomía de una feature |
| Identificador y effort de modelo por rol | `config/models.yaml` |
| Qué tabla corresponde a cada clase | `docs/architecture.md` § Story bible |
| Qué valida cada validador, dónde corre y con qué score | `docs/verification.md` |
| **Todos los números**: presupuesto por capa y umbrales | `config/thresholds.yaml` |
| Por qué se eligió una opción frente a otras | `docs/trade-offs.md` |
| Qué cambió, qué lo provocó y qué efecto tuvo | `docs/registro-iteraciones.md` |
| Invariantes de la cronología y del harness | `formal/lean/`, `formal/tla/` ▸ previsto |
| Qué se decidió construir, antes de escribir código | `docs/spec-inicial.md` ▸ previsto |
| Un concepto del curso por fichero | `docs/explainers/` ▸ previsto |
| Casos adversariales, y qué inspeccionó el browser MCP | `docs/red-team.md`, `docs/browser-mcp.md` |
| Specs y planes de implementación | `specs/` · lo archivado, en `docs/specs/_archivo/` |
| Skills: las de runtime que cargan los roles y las de desarrollo | `docs/architecture.md` § Skills |
| Contrato de la API | `http://localhost:8000/openapi.json` |
| Story bible viva (solo vía servicios de `canon/`) | `data/storymaker.db` |

## Ciclo de cambio

Cómo se cambia **este repositorio**. No confundir con el ciclo de producción de la novela
(Capa 5 de la ontología, feature `process/`): aquel genera capítulos, este genera código.

```
docs/*.md  →  specs/specN.md  →  specs/planN.md  →  código
              [aprobada]       [aprobado]        [TDD]
```

Cada corchete es una **puerta**, no una recomendación: sin el artefacto anterior aprobado
no se empieza el siguiente. Quien aprueba es siempre el desarrollador.

**Estado de un artefacto.** Toda spec y todo plan abren con frontmatter —`estado`
(`borrador` | `en-revision` | `aprobada` | `archivada`), `aprobada-por` y `fecha`—. Nacen en
`borrador` y solo el desarrollador los mueve a `aprobada`; un agente nunca se aprueba a sí
mismo y se detiene si no lo está. `archivada` **no se implementa**: vive en `docs/specs/_archivo/`.

**Antes de escribir una spec, pregunta.** No se adivina: carga la skill `grill-me` e
interroga al desarrollador hasta que no quede ambigüedad. Una spec con huecos no pasa a plan.

**Al cerrar un plan** se actualizan la spec si el comportamiento resultó distinto, los
documentos de `docs/` afectados, **`verification.md` si cambió un validador** y el registro.

**Qué queda fuera de la cadena.** Erratas, formateo, renombrados sin cambio de
comportamiento y el arreglo de un bug con prueba previa que lo reproduce; la excepción se
nombra en el commit. También `docs/` y `config/`, que son el paso 1 y no el paso 4: la
puerta gobierna el código, no lo que lo especifica. Todo lo demás —comportamiento, esquema,
contrato de API u ontología— pasa por las tres puertas. Qué contiene cada artefacto:
`docs/architecture.md` § Ciclo de cambio del repositorio.

## Reglas para todos los agentes

1. Lee antes de escribir: contexto semilla (`docs/`), luego código. Los nombres de clases y
   estados del código son los de la ontología, sin excepciones.
2. La story bible solo cambia al consolidar un **capítulo aceptado**. Un borrador rechazado
   no deja rastro.
3. Todo prompt declara su presupuesto por capa y falla si no cabe en la ventana de
   `config/thresholds.yaml`. Si una tarea exige superarla, el diseño está mal: propón
   compresión, no una ventana mayor.
4. Nunca inventes un hecho del mundo ni una clase del dominio. **En desarrollo**, si falta
   algo, pregunta al desarrollador. **En producción**, un dato que falta vuelve al
   entrevistador como `Dato faltante`: el sistema repregunta, jamás rellena el hueco.
5. Cambios de esquema de base: migración numerada, nunca edición de una ya aplicada.
6. No introduzcas dependencias nuevas sin justificarlo: el stack está cerrado.
7. TDD: la prueba primero, siempre. Y no hay código sin plan aprobado ni plan sin spec
   aprobada (ver «Ciclo de cambio»).
8. Nada de mocks en el código de producción, ni siquiera temporales.
9. Commits pequeños, mensaje en imperativo, una intención por commit.
10. Carga la skill antes de escribir, no después: `backend-feature-slice` o
    `feature-sliced-design` para colocar un archivo, `sqlite-relacional` o `sqlite-vec` para
    la base, `presupuesto-de-contexto` para un prompt. Una skill es referencia, no
    autoridad: si choca con esta guía, manda esta guía.
11. El texto libre del comprador es **contenido no confiable**: entra marcado como datos,
    nunca en la posición de las instrucciones, y jamás se interpreta como orden al sistema.
    Lo que lo parezca se registra como `Fragmento sospechoso` y se descarta.
12. Ningún secreto en el repositorio. Solo `.env.example`, con las claves vacías.
13. Todo rol y toda tool emiten un **span** en Langfuse; todo validador, un **score**. Una
    llamada al modelo sin span es un fallo, no un descuido.
14. Todo reintento tiene límite; al agotarlo el sistema se detiene y lo informa. Ni bucle
    sin tope ni fallo silencioso.
15. La versión anterior de una novela **nunca se sobrescribe**: una regeneración produce
    una versión nueva y la anterior sigue siendo consultable.
16. Ninguna versión se publica sin pasar el **gate de validadores**, Lean incluido. Un gate
    en rojo detiene la publicación; no se salta ni «por esta vez».

## Qué hacer ante una duda

Pregunta al desarrollador en vez de decidir por tu cuenta cuando la duda afecte a: la
ontología, el stack, el presupuesto de contexto, o los invariantes de Lean y de TLA+.
Todo lo demás es tuyo. (El *autor humano* de la ontología anterior ya no existe: quien
decide en producción es el policy engine.)

## Mantenimiento de este archivo

Este es el único archivo de instrucciones: `AGENTS.md` solo apunta aquí, así que toda
decisión compartida se escribe aquí y ningún agente se queda fuera.

**Mantenlo por debajo de 300 líneas.** Por encima consume contexto y baja la adherencia.
Si crece, mueve el detalle a `docs/architecture.md` o a la skill que corresponda y deja
aquí la regla y el enlace. Lo que queda no está duplicado en ningún otro sitio.
