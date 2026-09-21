# CLAUDE.md

@AGENTS.md

> La línea anterior carga AGENTS.md entero en contexto al arrancar Claude Code.
> AGENTS.md es la fuente canónica; este archivo solo añade lo específico de la
> implementación. No dupliques aquí lo que ya está allí.

---

## Stack

| Capa | Tecnología | Notas |
| --- | --- | --- |
| Backend | FastAPI (Python 3.12) | API asíncrona, Pydantic v2 para todo contrato de datos |
| Frontend | React 18 + TypeScript | Vite como bundler, sin framework de servidor |
| Persistencia | SQLite + `sqlite-vec` | Un único fichero `data/novel.db`, embeddings en la misma base |
| Modelo | Ventana de 100 000 tokens | Límite duro: ningún prompt puede superarlo |

## Layout del repositorio

```
backend/
  app/
    api/            # routers FastAPI, un módulo por recurso
    domain/         # entidades de la ontología (escena, hecho, promesa, hallazgo)
    canon/          # consolidación, snapshots, extracción, retcon
    context/        # ensamblado de contexto y presupuesto de tokens
    quality/        # críticos y verificadores
    db/             # esquema, migraciones, acceso a sqlite-vec
frontend/
  src/
    components/     # UI, un componente por archivo
    views/          # editor de escena, mapa de canon, panel de calidad
    api/            # cliente tipado contra el backend
docs/
  definitions.md        # contexto semilla: ontología del dominio
  domain-knowledge.md   # contexto semilla: diagramas Mermaid
  architecture.md       # sistema, agentes y skills, proceso
data/novel.db       # base de datos (no versionada)
```

## Presupuesto de contexto

El ensamblador reparte los 100 000 tokens por capa. Si una capa se pasa, se
comprime esa capa: nunca se roba presupuesto a otra ni se supera el total.

| Capa | Tokens | Origen |
| --- | --- | --- |
| Invariante | 6 000 | Premisa, guía de estilo, glosario canónico |
| Estructural | 4 000 | Brief de escena y restricción de destino |
| Estado | 18 000 | Snapshot derivado en t, nunca texto bruto |
| Local | 30 000 | Últimas escenas literales |
| Recuperado | 25 000 | `sqlite-vec`, filtrado por entidades del brief |
| Estilo | 8 000 | Muestras de voz de los personajes presentes |
| Anticontexto | 5 000 | Repeticiones, clichés vetados, revelaciones prohibidas |
| Margen | 4 000 | Reserva para la respuesta y el desbordamiento |

Regla: el contador de tokens se calcula **antes** de llamar al modelo, no después.
Un ensamblado que no cabe falla en voz alta; no se trunca en silencio.

## Base de datos

- Un solo fichero SQLite. Sin servidor, sin ORM pesado: SQL explícito.
- `sqlite-vec` para embeddings; tablas virtuales `vec0` junto a las tablas relacionales.
- La recuperación combina filtro relacional (entidades del brief) **y luego** similitud
  vectorial. Nunca similitud sola: devuelve fragmentos de tono parecido y estado irrelevante.
- Migraciones numeradas en `backend/app/db/migrations/`, aplicadas en orden, nunca editadas
  una vez commiteadas.
- `WAL` activado. Escrituras al canon siempre en transacción.

## Backend

- Un router por recurso en `app/api/`; la lógica vive en `domain/` y `canon/`, no en el router.
- Todo esquema de entrada y salida es un modelo Pydantic. Sin `dict` sueltos cruzando capas.
- Endpoints de escritura en el canon son idempotentes por `scene_id` + `version`.
- Las llamadas al modelo son asíncronas y con timeout explícito.
- Errores de dominio → excepciones propias mapeadas a HTTP en un handler central.

## Frontend

- React con TypeScript estricto. Sin `any`.
- Componentes funcionales y hooks; estado de servidor con TanStack Query.
- El cliente de `src/api/` se genera o se mantiene contra el OpenAPI de FastAPI: los tipos
  no se escriben a mano dos veces.
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

## Reglas de trabajo

1. Lee `AGENTS.md` y el contexto semilla (`docs/`) antes de tocar código de dominio.
   Los nombres de clases y estados del código son los de la ontología, sin excepciones.
2. No introduzcas dependencias nuevas sin justificarlo; el stack está cerrado (ver AGENTS.md).
3. No cambies el esquema de la base sin migración.
4. Escribe la prueba antes del arreglo cuando corrijas un bug.
5. Nada de mocks en el código de producción, ni siquiera temporales.
6. Si una tarea exige superar los 100 000 tokens, el diseño está mal: propón compresión,
   no una ventana mayor.

## Mantenimiento de este archivo

Si AGENTS.md y CLAUDE.md divergen, gana AGENTS.md. Los agentes que no leen
CLAUDE.md (Codex, Cursor, Copilot) solo ven AGENTS.md, así que toda decisión
compartida se escribe allí y este archivo se limita a lo técnico y local.

Mantén ambos por debajo de 200 líneas: por encima, el archivo consume contexto
y baja la adherencia.
