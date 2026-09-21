# AGENTS.md

Fuente canónica de instrucciones para cualquier agente que trabaje en este
repositorio. Claude Code la carga mediante el import `@AGENTS.md` de CLAUDE.md;
Codex, Cursor, Copilot y Aider la leen de forma nativa.

---

## Decisiones técnicas cerradas

> **Estas decisiones ya están tomadas y no se renegocian dentro de una tarea:
> FastAPI para el backend, React con TypeScript para el frontend, SQLite con
> `sqlite-vec` como única persistencia, ventana de contexto de 100 000 tokens
> y modo de autoría híbrido (estructura planificada por actos, escena
> descubierta). Si una tarea parece exigir cambiarlas, detente y pregunta:
> no propongas alternativas ni introduzcas dependencias equivalentes.**

Lo que esto excluye explícitamente: Postgres, pgvector, Pinecone, Chroma, Django,
Flask, Next.js, Vue, Redis, Celery y cualquier ORM que oculte el SQL.

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

1. Las clases de `backend/app/domain/` se nombran **igual** que en Definiciones. Un
   nombre nuevo en el código sin entrada en la ontología es un error, no una mejora.
2. Las tablas y sus claves foráneas siguen la tabla «Relaciones del dominio», incluidas
   las cardinalidades.
3. Las máquinas de estado del documento de dominio se implementan tal cual: mismos
   estados, mismas transiciones. Ninguna transición extra sin actualizar antes el diagrama.
4. Las capas y porcentajes de contexto salen de «Capa 3»; el reparto en tokens está en CLAUDE.md.
5. Antes de cerrar una tarea de dominio, comprueba que las preguntas de competencia
   afectadas siguen respondiéndose.

---

## Otras rutas

| Necesitas | Ruta |
| --- | --- |
| Sistema, agentes, skills y proceso | `docs/architecture.md` |
| Umbrales de calidad y de deriva | `config/thresholds.yaml` |
| Contrato de la API | `http://localhost:8000/openapi.json` |
| Entidades del dominio | `backend/app/domain/` |
| Consolidación, snapshots, extracción, retcon | `backend/app/canon/` |
| Ensamblado de contexto y presupuesto | `backend/app/context/` |
| Críticos y verificadores de calidad | `backend/app/quality/` |
| Esquema y migraciones | `backend/app/db/migrations/` |
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

## Reglas para todos los agentes

1. Lee antes de escribir: contexto semilla, luego código.
2. El canon solo cambia al consolidar una escena aceptada. Un borrador rechazado no deja rastro.
3. Todo prompt al modelo declara su presupuesto de tokens por capa y falla si no cabe en 100 000.
4. Nunca inventes un hecho del mundo ni una clase del dominio: si falta, abre una pregunta al autor.
5. Cambios de esquema de base: migración numerada, nunca edición de una ya aplicada.
6. Commits pequeños, mensaje en imperativo, una intención por commit.

## Qué hacer ante una duda

Pregunta al autor humano en vez de decidir por tu cuenta cuando la duda afecte a:
la ontología, el destino de un acto, la adopción de un hallazgo conflictivo, el stack
o el presupuesto de contexto. Todo lo demás es tuyo.
