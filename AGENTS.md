# AGENTS.md

Fuente canónica y única de instrucciones para cualquier agente que trabaje en este
repositorio: requisitos técnicos, presupuesto de contexto, convenciones de código y
reglas de trabajo. Claude Code la carga mediante el import `@AGENTS.md` de CLAUDE.md,
que no contiene nada más; Codex, Cursor, Copilot y Aider la leen de forma nativa.

---

## Requisitos técnicos

> **Estas decisiones ya están tomadas y no se renegocian dentro de una tarea:
> FastAPI para el backend, organizado por features con una carpeta `commons/`
> para lo compartido; React con TypeScript para el frontend; SQLite con
> `sqlite-vec` como única persistencia; la ventana de contexto que declara
> `config/thresholds.yaml`;
> y modo de autoría híbrido (estructura planificada por actos, escena
> descubierta). Si una tarea parece exigir cambiarlas, detente y pregunta:
> no propongas alternativas ni introduzcas dependencias equivalentes.**

**Alcance: un solo autor y una sola obra por instancia.** No hay multiusuario ni
multiobra. Ninguna tabla lleva `user_id` ni `tenant_id`. No hay autenticación en v1.
Una segunda novela se resuelve levantando otra instancia con su propio fichero
`data/novel.db`, nunca añadiendo multi-tenancy al esquema. Si una tarea parece
requerirlo, detente y pregunta.

| Capa | Tecnología | Notas |
| --- | --- | --- |
| Backend | FastAPI (Python 3.12) | API asíncrona, Pydantic v2 para todo contrato de datos |
| Frontend | React 18 + TypeScript | Vite como bundler, sin framework de servidor |
| Persistencia | SQLite + `sqlite-vec` | Un único fichero `data/novel.db`, embeddings en la misma base |
| Modelo | Ventana declarada en `config/thresholds.yaml` (`contexto.total`) | Límite duro: ningún prompt puede superarlo |

Lo que esto excluye explícitamente: Postgres, pgvector, Pinecone, Chroma, Django,
Flask, Next.js, Vue, Redis, Celery y cualquier ORM que oculte el SQL.

---

## Presupuesto de contexto

El ensamblador reparte la ventana por capa. Si una capa se pasa, se comprime esa
capa: nunca se roba presupuesto a otra ni se supera el total.

> **Las cifras no están aquí.** El reparto por capa vive en `config/thresholds.yaml`,
> que es la fuente única de umbrales de todo el sistema. Este documento describe las
> capas y la política; los números se leen del fichero, nunca se copian a un documento
> ni se escriben sueltos en el código.

| Capa | Origen |
| --- | --- |
| Invariante | Premisa, guía de estilo, glosario canónico |
| Estructural | Brief de escena y restricción de destino |
| Estado | Snapshot derivado en t, nunca texto bruto |
| Local | Últimas escenas literales |
| Recuperado | `sqlite-vec`, filtrado por entidades del brief |
| Estilo | Muestras de voz de los personajes presentes |
| Anticontexto | Repeticiones, clichés vetados, revelaciones prohibidas |
| Margen | Reserva para la respuesta y el desbordamiento |

**Política de degradación.** Cuando el ensamblado no cabe se comprime en el orden
Recuperado → Estilo → Local → Estado, parando en cuanto quepa. La capa Invariante y
la restricción de destino **no se degradan nunca**: son lo que impide que la escena
deje de ser de esta novela o deje de ir adonde tiene que ir.

Regla: el contador de tokens se calcula **antes** de llamar al modelo, no después.
Un ensamblado que no cabe falla en voz alta; no se trunca en silencio.

---

## Layout del repositorio

```
backend/
  app/
    main.py         # monta los routers de cada feature
    novel/          # Capa 1: obra, partes, capítulos, escenas, personajes, lugares
    canon/          # Capa 2: hechos, snapshots, promesas, contradicciones, retcon
    context/        # Capa 3: ensamblado, presupuesto de tokens, recuperación
    quality/        # Capa 4: críticos y verificadores
    process/        # Capa 5: briefs, borradores, versiones, ciclo
    findings/       # modo híbrido: extracción y adopción de hallazgos
    replanning/     # modo híbrido: deriva y replanificación rodante
    commons/        # db y migraciones, cliente del modelo, errores, tokens
frontend/
  src/                # Feature-Sliced Design v2.1, empezando por el mínimo
    app/              # arranque, providers, router
    pages/            # editor de escena, mapa de canon, panel de calidad
    shared/           # UI kit, cliente tipado del backend, utilidades
docs/
  definitions.md        # contexto semilla: ontología del dominio
  domain-knowledge.md   # contexto semilla: diagramas Mermaid
  architecture.md       # sistema, agentes y skills, proceso
  verification.md       # qué se verifica y con qué método
  specs/
    NNN-slug/
      spec.md           # qué se quiere y cómo se acepta; necesita aprobación
      plan.md           # cómo se implementa y qué pruebas van primero
config/thresholds.yaml  # fuente única de cifras y umbrales
data/novel.db       # base de datos (no versionada)
.claude/skills/     # skills de agente (ver docs/architecture.md)
```

## Base de datos

- Un solo fichero SQLite. Sin servidor, sin ORM pesado: SQL explícito.
- `sqlite-vec` para embeddings; tablas virtuales `vec0` junto a las tablas relacionales.
- La recuperación combina filtro relacional (entidades del brief) **y luego** similitud
  vectorial. Nunca similitud sola: devuelve fragmentos de tono parecido y estado irrelevante.
- Migraciones numeradas en `backend/app/commons/db/migrations/`, aplicadas en orden, nunca editadas
  una vez commiteadas.
- `WAL` activado. Escrituras al canon siempre en transacción.

## Backend

- Una feature por carpeta, rodaja vertical completa: `router.py`, `schemas.py`,
  `models.py`, `service.py`, `repository.py`. La feature es la unidad de cambio.
- La lógica vive en `service.py`, el SQL en `repository.py`. El router solo traduce
  HTTP a llamadas del servicio.
- `commons/` es solo para lo que usan dos o más features. Nada de dominio entra ahí:
  si duda entre una feature y `commons/`, va a la feature.
- Una feature importa de `commons/` y del `service.py` de otra feature, nunca de su
  `repository.py`. Sin importaciones circulares: si dos features se necesitan mutuamente,
  falta una tercera o la frontera está mal puesta.
- Todo esquema de entrada y salida es un modelo Pydantic. Sin `dict` sueltos cruzando capas.
- Endpoints de escritura en el canon son idempotentes por `scene_id` + `version`.
- Las llamadas al modelo son asíncronas y con timeout explícito.
- Errores de dominio → excepciones propias mapeadas a HTTP en un handler central.

## Frontend

- React con TypeScript estricto. Sin `any`.
- Componentes funcionales y hooks; estado de servidor con TanStack Query.
- Estructura por **Feature-Sliced Design v2.1**: importaciones solo hacia capas inferiores
  (`app → pages → widgets → features → entities → shared`) y cada slice se consume por su
  `index.ts`. Empezamos con `app/`, `pages/` y `shared/`; `features/` y `entities/` se
  crean al extraer, no por adelantado. **`widgets/` no se usa**: FSD la desaconseja y aquí
  además está descartada (`docs/architecture.md` § Precedencia); sigue en la cadena porque
  es la de FSD, no la nuestra. Carga la skill `feature-sliced-design` antes de decidir
  dónde va un archivo.
- El cliente tipado vive en `shared/api/` y se genera o se mantiene contra el OpenAPI de
  FastAPI: los tipos no se escriben a mano dos veces.
- Sin lógica de dominio en el frontend: el canon se decide en el backend.

## Comandos

```bash
# backend
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run ruff check . && uv run ruff format .

# frontend
npm run dev
npm run test
npm run typecheck
```

---

## Contexto semilla

Dos documentos definen el dominio. Todo modelo de datos, endpoint, componente o
prompt de este repositorio deriva de ellos. Son lectura obligatoria antes de
tocar código de dominio.

| Documento | Ruta en repo | Documento vivo | Qué es |
| --- | --- | --- | --- |
| Definiciones | `docs/definitions.md` | [Ontología — Definiciones](https://claude.ai/code/artifact/6898a56e-53bf-4857-a4e0-1a24e6bea595) | Vocabulario: clases, atributos, relaciones, preguntas de competencia |
| Conocimiento de dominio | `docs/domain-knowledge.md` | [Árboles y grafos](https://claude.ai/code/artifact/5683a98e-0306-4219-b050-3c4a839e7d41) | Diagramas Mermaid: jerarquías, grafo de entidades, máquinas de estado |

**Canonicidad y sincronía.** El documento vivo manda; la copia en `docs/` es una
exportación para que los agentes trabajen sin red. Si ambos difieren, gana el documento
vivo y hay que reexportar. Ningún agente edita `docs/definitions.md` ni
`docs/domain-knowledge.md` por su cuenta: los cambios de ontología se hacen en el
documento vivo y se exportan. `docs/architecture.md` sí es editable en el repositorio:
no tiene documento vivo asociado.

### Qué sección responde a qué

| Necesitas | Documento | Sección |
| --- | --- | --- |
| Convenciones de notación y capas del modelo | Definiciones | Convenciones del modelo |
| Reglas del modo híbrido y sus clases | Definiciones | Modo de autoría: híbrido |
| Estructura de la obra y entidades narrativas | Definiciones | Capa 1 — Obra |
| Hechos, snapshots, promesas, retcon | Definiciones | Capa 2 — Canon y estado |
| Memorias, capas y presupuesto de contexto | Definiciones | Capa 3 — Contexto y memoria |
| Dimensiones de calidad y sus umbrales | Definiciones | Capa 4 — Calidad |
| Roles, artefactos y estados del ciclo | Definiciones | Capa 5 — Proceso |
| Esquema relacional y cardinalidades | Definiciones | Relaciones del dominio |
| Criterios de aceptación del modelo de datos | Definiciones | Preguntas de competencia |
| Visión general de las cinco capas | Dominio | Mapa de capas |
| Frontera planificado/descubrimiento y los dos bucles | Dominio | Modo híbrido |
| Jerarquía de contención y taxonomías | Dominio | Árbol estructural, Árbol de entidades |
| Aristas del grafo de entidades | Dominio | Grafo de entidades |
| Relación fábula ↔ discurso | Dominio | Fábula y discurso |
| Máquinas de estado de hecho, promesa y hallazgo | Dominio | Modelo de canon, Modo híbrido |
| Flujo de ensamblado del contexto | Dominio | Ensamblado del contexto |
| Ruta de un defecto y ciclo de producción | Dominio | Árbol de calidad, Ciclo de producción |

### Cómo usarlo

1. Las clases de dominio se nombran **igual** que en Definiciones, viva en la feature que
   viva cada una. Un
   nombre nuevo en el código sin entrada en la ontología es un error, no una mejora.
2. Las tablas y sus claves foráneas siguen la tabla «Relaciones del dominio», incluidas
   las cardinalidades.
3. Las máquinas de estado del documento de dominio se implementan tal cual: mismos
   estados, mismas transiciones. Ninguna transición extra sin actualizar antes el diagrama.
4. La lista de capas del contexto sale de «Capa 3»; su presupuesto, de
   `config/thresholds.yaml`. Los porcentajes que da la Capa 3 son orientativos y no
   mandan: donde no cuadren con el fichero, gana el fichero.
5. Antes de cerrar una tarea de dominio, comprueba que las preguntas de competencia
   afectadas siguen respondiéndose.

---

## Otras rutas

| Necesitas | Ruta |
| --- | --- |
| Sistema, agentes, skills y proceso | `docs/architecture.md` |
| Skills de agente instaladas | `.claude/skills/` |
| Anatomía de una feature del backend | `.claude/skills/backend-feature-slice/` |
| Estructura del frontend (FSD v2.1) | `.claude/skills/feature-sliced-design/` |
| Migraciones, esquema y transacciones | `.claude/skills/sqlite-relacional/` |
| Tablas `vec0`, KNN y serialización de vectores | `.claude/skills/sqlite-vec/` |
| Reparto de las siete capas de contexto | `.claude/skills/presupuesto-de-contexto/` |
| Todos los números: presupuesto por capa, umbrales de calidad y de deriva | `config/thresholds.yaml` |
| Contrato de la API | `http://localhost:8000/openapi.json` |
| Specs y planes de implementación | `docs/specs/NNN-slug/` |
| Obra, partes, capítulos, escenas, personajes | `backend/app/novel/` |
| Consolidación, snapshots, promesas, retcon | `backend/app/canon/` |
| Ensamblado de contexto y presupuesto | `backend/app/context/` |
| Críticos y verificadores de calidad | `backend/app/quality/` |
| Briefs, borradores, versiones, ciclo | `backend/app/process/` |
| Extracción y adopción de hallazgos | `backend/app/findings/` |
| Deriva y replanificación rodante | `backend/app/replanning/` |
| Código compartido entre features | `backend/app/commons/` |
| Esquema y migraciones | `backend/app/commons/db/migrations/` |
| Canon vivo (solo vía servicios de `canon/`) | `data/novel.db` |

---

## Modelo de autoría

Híbrido: el esquema fija el destino por actos; la escena se descubre. Consecuencias
operativas para cualquier agente que genere o revise texto:

- El brief de escena es mínimo: estado de entrada más restricción de destino. No se
  planifican beats.
- Los hallazgos (hechos, promesas, motivos no previstos) se **extraen** tras aceptar la
  escena, no se declaran antes. Entran como `provisional` hasta que el autor los adopta.
- El retcon es operación rutinaria: marca las escenas afectadas como `obsoleta` y encola
  su reescritura; no toca el resto de la obra.
- La replanificación es periódica, por umbral de deriva o al cerrar capítulo. Nunca en
  mitad de una escena.
- Una escena descubre *cómo*, no *hacia dónde*. Cambiar el destino exige replanificar.

---

## Skills de agente

Ojo con el nombre: aquí «skill» son capacidades que se cargan en el agente, no las
operaciones del backend que `docs/architecture.md` llama igual. Viven en
`.claude/skills/`, se versionan con el repositorio y su detalle (origen, actualización,
procedencia) está en `docs/architecture.md`.

- `backend-feature-slice` — colocar un archivo del backend, añadir un endpoint, decidir
  qué feature es dueña de una clase, resolver una importación entre features.
- `feature-sliced-design` — colocar un archivo del frontend, definir la API pública de un
  slice, resolver un cross-import, decidir si extraer a `features/` o `entities/`.
- `sqlite-relacional` — escribir una migración o cualquier SQL, crear o cambiar una tabla,
  traducir una cardinalidad o un estado de la ontología al esquema.
- `sqlite-vec` — crear o cambiar una tabla `vec0`, escribir una consulta KNN, serializar
  embeddings, elegir métrica de distancia o clave de partición.
- `presupuesto-de-contexto` — ensamblar un prompt, tocar el contador de tokens, decidir
  qué se comprime cuando algo no cabe en la ventana.
- `plan-de-verificacion` — construir o revisar el plan de verificación del proyecto.

Cárgala **antes** de escribir, no para justificar lo ya escrito. Una skill no sustituye al
contexto semilla ni levanta ninguna decisión de «Requisitos técnicos»: si lo que propone
choca con esta guía, manda esta guía.

---

## Ciclo de cambio

Cómo se cambia **este repositorio**. No confundir con el ciclo de producción de la
novela (Capa 5 de la ontología, feature `process/`): aquel genera escenas, este genera
código.

```
docs/*.md  →  docs/specs/NNN-slug/spec.md  →  docs/specs/NNN-slug/plan.md  →  código
              [aprobada]                      [aprobado]                      [TDD]
```

Cada corchete es una **puerta**, no una recomendación: sin el artefacto anterior
aprobado no se empieza el siguiente. Quien aprueba es siempre el autor humano.

**Estado de un artefacto.** Toda spec y todo plan abren con frontmatter. El agente lo
lee antes de continuar; si el estado no es `aprobada`, se detiene y lo dice.

```yaml
---
estado: borrador | en-revision | aprobada
aprobada-por: <autor humano>
fecha: <AAAA-MM-DD>
---
```

### 1. Actualizar la documentación de `docs/`

Los documentos de `docs/` —no `docs/specs/`, que es el paso siguiente—. Es la entrada
del ciclo y lo único que no necesita spec.

- `definitions.md` y `domain-knowledge.md` **no se editan aquí**: se cambian en el
  documento vivo y se reexportan (ver «Canonicidad y sincronía»). Un cambio de ontología
  empieza ahí, no en una spec.
- `architecture.md` sí se edita en el repositorio. Si un cambio toca la arquitectura, se
  actualiza **antes** de escribir la spec que se apoya en ella.
- Si al terminar un cambio la documentación queda desfasada, se corrige en el mismo
  commit. Documentación que miente es peor que no tenerla.

### 2. Crear o actualizar una spec (`docs/specs/`)

Una carpeta por cambio: `docs/specs/NNN-slug/spec.md`, numeración correlativa.

**Pregunta antes de escribirla.** Una spec no se adivina: es el punto del ciclo donde el
agente interroga al autor hasta que no queda ambigüedad. Como mínimo hay que dejar
resuelto qué comportamiento observable se espera, qué criterios de aceptación la dan por
cumplida, qué queda explícitamente fuera, y qué toca de ontología, esquema o contrato de
API. Si algo sigue abierto, la spec no está lista: no se pasa a plan con huecos.

Contenido mínimo: problema, comportamiento esperado, criterios de aceptación
verificables, fuera de alcance, impacto en ontología, esquema y API, y las preguntas de
competencia afectadas.

Actualizar una spec existente sigue el mismo camino: vuelve a `borrador` y necesita
aprobación otra vez antes de que su plan valga.

### 3. Plan de implementación

`docs/specs/NNN-slug/plan.md`, junto a su spec.

- **No se crea un plan si la spec no está `aprobada`.** Se comprueba leyendo su
  frontmatter, no de memoria.
- Contenido: pasos ordenados, features y ficheros que se tocan, migraciones necesarias,
  **la lista de pruebas que se van a escribir** y en qué orden, riesgos y criterio de
  terminado.
- Un plan que no se puede probar no es un plan: si no sabes qué prueba falla primero,
  falta diseño.

### 4. Crear o modificar código

- **No se escribe código si el plan no está `aprobado`.** Sin plan aprobado el agente se
  detiene y lo dice; no «adelanta» implementación.
- **TDD, sin excepciones**: la prueba primero, se comprueba que falla por la razón
  correcta, luego el código mínimo que la pasa, luego refactor. Escribir la prueba
  después no es TDD, es cobertura.
- Al cerrar: si el comportamiento resultó distinto del aprobado, se actualiza la spec y
  vuelve a aprobación; si cambió la estructura, se actualiza `architecture.md`. La spec
  describe lo que el código hace, no lo que se pensaba hacer.
- El commit que cierra un plan nombra su carpeta: `docs/specs/NNN-slug/`.

### Qué queda fuera de la cadena

Erratas, formateo, renombrados sin cambio de comportamiento y arreglo de un bug con
prueba previa que lo reproduce. La excepción se nombra en el mensaje del commit. Todo lo
demás —comportamiento, esquema, contrato de API u ontología— pasa por las tres puertas.

## Reglas para todos los agentes

1. Lee antes de escribir: contexto semilla (`docs/`), luego código. Los nombres de clases
   y estados del código son los de la ontología, sin excepciones.
2. El canon solo cambia al consolidar una escena aceptada. Un borrador rechazado no deja rastro.
3. Todo prompt al modelo declara su presupuesto de tokens por capa y falla si no cabe en
   la ventana de `config/thresholds.yaml`. Si una tarea exige superarla, el diseño está
   mal: propón compresión, no una ventana mayor.
4. Nunca inventes un hecho del mundo ni una clase del dominio: si falta, abre una pregunta al autor.
5. Cambios de esquema de base: migración numerada, nunca edición de una ya aplicada.
6. No introduzcas dependencias nuevas sin justificarlo: el stack está cerrado.
7. TDD: la prueba primero, siempre. Y no hay código sin plan aprobado ni plan sin spec
   aprobada (ver «Ciclo de cambio»).
8. Nada de mocks en el código de producción, ni siquiera temporales.
9. Commits pequeños, mensaje en imperativo, una intención por commit.
10. Carga la skill antes de escribir, no después: `backend-feature-slice` o
    `feature-sliced-design` para colocar un archivo, `sqlite-relacional` o `sqlite-vec`
    para tocar la base, `presupuesto-de-contexto` para ensamblar un prompt.

## Qué hacer ante una duda

Pregunta al autor humano en vez de decidir por tu cuenta cuando la duda afecte a:
la ontología, el destino de un acto, la adopción de un hallazgo conflictivo, el stack
o el presupuesto de contexto. Todo lo demás es tuyo.

## Mantenimiento de este archivo

Este es el único archivo de instrucciones: CLAUDE.md solo contiene `@AGENTS.md`, así que
toda decisión compartida se escribe aquí y ningún agente se queda fuera.

Mantenlo por debajo de 200 líneas: por encima, el archivo consume contexto y baja la
adherencia. Si crece, mueve el detalle a `docs/architecture.md` y deja aquí la regla.
