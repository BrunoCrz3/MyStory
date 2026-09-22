# AGENTS.md

Fuente canónica y única de instrucciones para cualquier agente que trabaje en este
repositorio. Claude Code la carga mediante el import `@AGENTS.md` de CLAUDE.md, que no
contiene nada más; Codex, Cursor, Copilot y Aider la leen de forma nativa.

Aquí vive **la regla**. El detalle vive en `docs/architecture.md` y en las skills de
`.claude/skills/`, y cada sección dice cuál le corresponde. Si alguno de los dos choca con
este archivo, manda este archivo.

---

## Requisitos técnicos

> **Estas decisiones ya están tomadas y no se renegocian dentro de una tarea:
> FastAPI para el backend, organizado por features con una carpeta `commons/`
> para lo compartido; React con TypeScript para el frontend; SQLite con
> `sqlite-vec` como única persistencia; la ventana de contexto que declara
> `config/thresholds.yaml`; y modo de autoría híbrido (estructura planificada por actos,
> escena descubierta). Si una tarea parece exigir cambiarlas, detente y pregunta:
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
> que es la fuente única de umbrales de todo el sistema. Este documento describe la
> política; los números se leen del fichero, nunca se copian a un documento ni se
> escriben sueltos en el código.

Las **siete capas** —Invariante, Estructural, Estado, Local, Recuperado, Estilo y
Anticontexto— más el **Margen**, con la fuente de cada una y dónde se lee su presupuesto:
skill `presupuesto-de-contexto`.

**Política de degradación.** Cuando el ensamblado no cabe se comprime en el orden
Recuperado → Estilo → Local → Estado, parando en cuanto quepa. La capa Invariante y
la restricción de destino **no se degradan nunca**: son lo que impide que la escena
deje de ser de esta novela o deje de ir adonde tiene que ir.

Regla: el contador de tokens se calcula **antes** de llamar al modelo, no después.
Un ensamblado que no cabe falla en voz alta; no se trunca en silencio.

---

## Layout del repositorio

```
AGENTS.md           # esta guía; CLAUDE.md no contiene más que su import
backend/            # ▸ previsto
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
frontend/           # ▸ previsto
  src/                # Feature-Sliced Design v2.1, empezando por el mínimo
    app/              # arranque, providers, router
    pages/            # editor de escena, mapa de canon, panel de calidad
    shared/           # UI kit, cliente tipado del backend, utilidades
docs/
  definitions.md        # contexto semilla: ontología del dominio
  domain-knowledge.md   # contexto semilla: diagramas Mermaid
  architecture.md       # sistema, agentes y skills, proceso, ciclo de cambio
  verification.md       # qué se verifica y con qué método
  specs/
    NNN-slug/
      spec.md           # qué se quiere y cómo se acepta; necesita aprobación
      plan.md           # cómo se implementa y qué pruebas van primero
config/thresholds.yaml  # fuente única de cifras y umbrales
data/novel.db       # ▸ previsto; base de datos, no versionada
.claude/skills/     # skills de agente (ver docs/architecture.md)
skills-lock.json    # origen y hash de las skills instaladas
```

**▸ previsto** es lo que este layout reserva y todavía no existe: no hay código hasta que
su plan esté aprobado (ver «Ciclo de cambio»). Una ruta que apunte ahí es destino, no
ubicación actual.

---

## Persistencia, backend y frontend

Las decisiones cerradas. El detalle operativo está en la skill que nombra cada bloque, y
cargarla **antes** de escribir no es opcional.

**Base de datos** — skills `sqlite-relacional` y, para `vec0`, `sqlite-vec`. Un solo
fichero SQLite, SQL explícito, sin servidor y sin ORM. Migraciones numeradas en
`backend/app/commons/db/migrations/`, aplicadas en orden y **nunca editadas** una vez
commiteadas. `WAL` activado; escrituras al canon siempre en transacción. La recuperación
combina filtro relacional por las entidades del brief **y luego** similitud vectorial:
nunca similitud sola, que devuelve fragmentos de tono parecido y estado irrelevante.

**Backend** — skill `backend-feature-slice`. Una feature por carpeta, rodaja vertical
completa (`router.py`, `schemas.py`, `models.py`, `service.py`, `repository.py`); la
feature es la unidad de cambio. La lógica en `service.py`, el SQL en `repository.py`, el
router solo traduce HTTP. `commons/` únicamente para lo que usan dos o más features, y
nada de dominio entra ahí. Una feature importa de `commons/` y del `service.py` de otra,
**nunca de su `repository.py`**, y sin ciclos. Todo esquema de entrada y salida es
Pydantic: sin `dict` sueltos cruzando capas. Escrituras al canon idempotentes por
`scene_id` + `version`. Llamadas al modelo asíncronas y con timeout explícito. Errores de
dominio a HTTP en un handler central.

**Frontend** — skill `feature-sliced-design`. React con TypeScript estricto, sin `any`.
Componentes funcionales y hooks; estado de servidor con TanStack Query. Feature-Sliced
Design v2.1: importaciones solo hacia capas inferiores y cada slice se consume por su
`index.ts`. Empezamos con `app/`, `pages/` y `shared/`; `features/` y `entities/` se crean
al extraer, no por adelantado. **`widgets/` no se usa** (`docs/architecture.md`
§ Precedencia). El cliente tipado vive en `frontend/src/shared/api/` y se deriva del
OpenAPI de FastAPI: los tipos no se escriben a mano dos veces. Sin lógica de dominio en el
frontend: el canon se decide en el backend.

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

Qué sección de cada documento responde a qué pregunta, y cómo se usan al escribir código:
`docs/architecture.md` § Frontera con el contexto semilla.

---

## Modelo de autoría

Híbrido: el esquema fija el destino por actos; la escena se descubre. Consecuencias
operativas para cualquier agente que genere o revise texto:

- El brief de escena es mínimo: estado de entrada más restricción de destino. No se
  planifican beats.
- Los hallazgos (hechos, promesas, motivos no previstos) se **extraen** tras aceptar la
  escena, no se declaran antes. Entran como `propuesto` hasta que el autor los adopta.
- El retcon es operación rutinaria: marca las escenas afectadas como `obsoleta` y encola
  su reescritura; no toca el resto de la obra.
- La replanificación es periódica, por umbral de deriva o al cerrar capítulo. Nunca en
  mitad de una escena.
- Una escena descubre *cómo*, no *hacia dónde*. Cambiar el destino exige replanificar.

---

## Dónde está cada cosa

| Necesitas | Ruta |
| --- | --- |
| Clases, atributos, relaciones, preguntas de competencia | `docs/definitions.md` |
| Jerarquías, grafos y máquinas de estado | `docs/domain-knowledge.md` |
| Sistema, agentes, skills, orquestación y ciclo de cambio | `docs/architecture.md` |
| Qué feature es dueña de cada clase | `docs/architecture.md` § Anatomía de una feature |
| Qué se verifica y con qué método | `docs/verification.md` |
| **Todos los números**: presupuesto por capa y umbrales | `config/thresholds.yaml` |
| Specs y planes de implementación | `docs/specs/NNN-slug/` |
| Skills de agente instaladas, con su origen y cuándo cargarlas | `.claude/skills/`, listadas en `docs/architecture.md` |
| Contrato de la API | `http://localhost:8000/openapi.json` |
| Canon vivo (solo vía servicios de `canon/`) | `data/novel.db` |

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

**Qué queda fuera de la cadena.** Erratas, formateo, renombrados sin cambio de
comportamiento y arreglo de un bug con prueba previa que lo reproduce; la excepción se
nombra en el mensaje del commit. También la documentación de `docs/` y los valores de
`config/`, que son el paso 1 y no el paso 4: la puerta que exige plan aprobado gobierna el
código, no lo que lo especifica. Todo lo demás —comportamiento, esquema, contrato de API
u ontología— pasa por las tres puertas.

Qué contiene cada artefacto, qué hay que preguntar antes de escribir una spec y qué se
actualiza al cerrar: `docs/architecture.md` § Ciclo de cambio del repositorio.

---

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
    para tocar la base, `presupuesto-de-contexto` para ensamblar un prompt. Una skill es
    referencia, no autoridad: si choca con esta guía, manda esta guía.

## Qué hacer ante una duda

Pregunta al autor humano en vez de decidir por tu cuenta cuando la duda afecte a:
la ontología, el destino de un acto, la adopción de un hallazgo conflictivo, el stack
o el presupuesto de contexto. Todo lo demás es tuyo.

## Mantenimiento de este archivo

Este es el único archivo de instrucciones: CLAUDE.md solo contiene `@AGENTS.md`, así que
toda decisión compartida se escribe aquí y ningún agente se queda fuera.

**Mantenlo por debajo de 300 líneas.** Por encima, el archivo consume contexto y baja la
adherencia. Si crece, mueve el detalle a `docs/architecture.md` o a la skill que
corresponda, y deja aquí la regla y el enlace.

El límite fue 200 y no se sostuvo: lo que queda —requisitos cerrados, layout, política de
contexto, puertas del ciclo y las diez reglas— no está duplicado en ningún otro sitio, y
bajar de 200 obligaba a sacar de aquí cosas que un agente necesita **antes** de abrir
otro documento. Lo que sí estaba duplicado ya se movió: la anatomía de las features y el
detalle del backend, la base y el frontend viven en sus skills, y el catálogo de skills,
el mapa del contexto semilla y el detalle de cada paso del ciclo, en
`docs/architecture.md`.
