# storyMaker

Genera novelas personalizadas para regalar, de principio a fin y sin humano en el bucle. Un
entrevistador recoge los datos del destinatario, un planificador fija el destino de cada
capítulo, un redactor los escribe, un editor los critica y una batería de validadores decide
si se publica.

- **Qué se construye y por qué**: `specs/spec1.md` y su contrato `specs/openapi.yaml`.
- **Cómo se construye**: `specs/plan1.md`, y dónde va la ejecución: `specs/progreso.md`.
- **Instrucciones para agentes**: `CLAUDE.md`.

## Requisitos

Python 3.12, [`uv`](https://docs.astral.sh/uv/), `git`, y Node 20+ para el servidor
Playwright MCP del export y la validación visual.

## Instalación

```bash
cp .env.example .env       # rellénalo: ANTHROPIC_API_KEY, LANGFUSE_*, STORYMAKER_*
cd backend
uv sync
```

`.env` nunca se commitea. Quién atiende las llamadas al modelo lo dice `proveedor` en
`config/models.yaml` (TO-040):

- `claude_code` (el valor actual): el CLI de Claude Code como subproceso, con la sesión ya
  iniciada en la máquina y **todas sus herramientas desactivadas**. No necesita clave. Si
  `claude` en el PATH es el envoltorio `.cmd` de npm, se usa el binario nativo que envuelve;
  si no se encuentra, indica su ruta en `STORYMAKER_CLAUDE_CODE`.
- `api`: la API de Claude con `ANTHROPIC_API_KEY`. Sin la clave el sistema arranca pero no
  genera.

Sin las variables de Langfuse genera igual y `GET /salud` dice `degradado`.

## Arranque

```bash
cd backend
uv run --env-file ../.env python -m app                          # 127.0.0.1:8000, un worker
uv run --env-file ../.env uvicorn app.main:app --reload --port 8000   # desarrollo
```

> **Un solo proceso y un solo worker.** El presupuesto de tokens en vuelo es un semáforo en
> proceso: arrancar con `--workers 2` o dos procesos sobre la misma base lo duplicaría en
> silencio. Por eso el backend toma un cerrojo sobre la base al arrancar, y un segundo
> proceso falla en voz alta. `python -m app` además se niega a escuchar fuera de la interfaz
> local sin `--permitir-red`, porque no hay autenticación.

Las migraciones se aplican solas al arrancar; también a mano:

```bash
uv run --env-file ../.env python -m app.commons.db.migrar
```

## Pruebas

```bash
cd backend
uv run pytest                    # toda la suite; no llama al modelo ni a Langfuse
uv run pytest tests/guardrail    # el guardrail tiene suite propia
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
```

La prueba de humo con el modelo real está excluida por defecto y cuesta dinero:
`uv run --env-file ../.env pytest -m real tests/humo -v`.
