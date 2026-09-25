# storyMaker

Genera novelas personalizadas para regalar, de principio a fin y sin humano en el bucle. Un
entrevistador recoge los datos del destinatario, un planificador fija el destino de cada
capítulo, un redactor los escribe, un editor los critica y una batería de validadores decide
si se publica.

- **Qué se construye y por qué**: `specs/spec1.md` y su contrato `specs/openapi.yaml`.
- **Cómo se construye**: `specs/plan1.md` (backend) y `specs/plan2-frontend.md` (frontend), y
  dónde va la ejecución: `specs/progreso.md`.
- **Instrucciones para agentes**: `CLAUDE.md`.

## Requisitos

Python 3.12, [`uv`](https://docs.astral.sh/uv/), `git`, Node 20+ y Microsoft Edge. En Windows,
todos los comandos de este README son de **Git Bash**. Con `proveedor: claude_code` (el valor
actual), el CLI de Claude Code instalado y con la sesión iniciada.

**Qué navegador usa cada pieza:**

| Pieza | Navegador | Cómo se consigue |
| --- | --- | --- |
| Servidor Playwright MCP del backend (`render_visual`, en el gate) | **Edge** (`--browser msedge`) | El del sistema; no se instala nada |
| Browser MCP de Claude Code (`.mcp.json`, inspección en desarrollo) | **Edge** | El del sistema |
| Export a PDF (`page.pdf()`, A-123) | **Chromium de Playwright** | `uv run playwright install chromium`, una vez |

## Instalación

```bash
cp .env.example .env              # rellénalo siguiendo los comentarios de .env.example
cd backend
uv sync
uv run playwright install chromium   # el Chromium del export a PDF
cd ../frontend
npm install
```

`.env` nunca se commitea. **En una instalación nueva, `data/` empieza vacía** (o no existe): el
backend crea la carpeta y la base al arrancar y aplica las migraciones. Una ruta relativa en
`STORYMAKER_DB_PATH` cuelga de la raíz del repositorio, se arranque desde donde se arranque.

> **Nota: en el `.env`, las rutas de Windows se escriben con barras normales (`/`) o entre
> comillas simples**: `C:/ruta/claude.exe` o `'C:\ruta\claude.exe'`. El backend lee el `.env`
> con `uv run --env-file`, y si una línea no se puede leer, uv descarta el fichero entero con
> solo un warning. Por eso la app comprueba al arrancar (en su `lifespan`) que cada variable
> con valor en el `.env` llegó al entorno y, si falta alguna, falla con `EnvNoCargado` y dice
> cuáles (sin sus valores). Cubre `python -m app` y `uvicorn app.main:app --reload`; con
> `--reload`, uvicorn muestra el error y se queda esperando cambios. `python -m app --sin-env`
> salta la comprobación.

**En esta máquina, las URL van con `localhost`, no con `127.0.0.1`.** El servidor Playwright
MCP solo acepta el `Host` `localhost:8931`, y las dos URL del gate se escriben igual:

| Variable | Valor |
| --- | --- |
| `PLAYWRIGHT_MCP_URL` | `http://localhost:8931/mcp`, exactamente |
| `STORYMAKER_LECTURA_URL` | `http://localhost:5173`, el frontend de `npm run dev` |

Quién atiende las llamadas al modelo lo dice `proveedor` en `config/models.yaml` (TO-040):

- `claude_code` (el valor actual): el CLI de Claude Code como subproceso, con la sesión ya
  iniciada en la máquina y **todas sus herramientas desactivadas**. No necesita clave.
  **`STORYMAKER_CLAUDE_CODE` solo hace falta** si `claude` no está en el PATH del backend, o si
  lo que hay es el envoltorio `.cmd` de npm sin `claude.exe` al lado. Con el instalador nativo
  (`claude.exe` en el PATH) se deja vacía.
- `api`: la API de Claude con `ANTHROPIC_API_KEY`. Sin la clave el sistema arranca pero no
  genera.

Sin las variables de Langfuse genera igual y `GET /salud` dice `degradado`.

## Arrancar la demo en Windows

Tres terminales de Git Bash, desde la raíz del repositorio, en este orden.

**1. Servidor Playwright MCP** (el comando sale de `docs/browser-mcp.md` § El servidor, que es
la fuente):

```bash
npx -y @playwright/mcp@0.0.82 --headless --isolated --browser msedge --host 127.0.0.1 --port 8931
```

> **Sin este servidor no se publica ninguna versión.** El gate pinta cada versión candidata
> con `render_visual` antes de publicarla; sin servidor, la versión queda `rechazada` y la
> generación se detiene (RNF-19, A-114).

**2. Backend**, en `127.0.0.1:8000`:

```bash
cd backend
uv run --env-file ../.env python -m app
```

**3. Frontend**, en el puerto 5173:

```bash
cd frontend
npm run dev
```

Abre `http://localhost:5173/`. Comprobación: `http://localhost:5173/api/salud` devuelve el
`GET /salud` del backend, con `estado: ok` si Langfuse está configurado, que es la señal de que `.env` se cargó. El recorrido de la demo
está en `frontend/README.md` § Recorrido de la demo.

> **Un solo proceso y un solo worker.** El presupuesto de tokens en vuelo es un semáforo en
> proceso: arrancar con `--workers 2` o dos procesos sobre la misma base lo duplicaría en
> silencio. Por eso el backend toma un cerrojo sobre la base al arrancar, y un segundo
> proceso falla en voz alta. `python -m app` además se niega a escuchar fuera de la interfaz
> local sin `--permitir-red`, porque no hay autenticación.

Para desarrollo, con recarga: `uv run --env-file ../.env uvicorn app.main:app --reload --port
8000`. Las migraciones se aplican solas al arrancar; también a mano:
`uv run --env-file ../.env python -m app.commons.db.migrar`.

## Pruebas

```bash
cd backend
uv run pytest                    # toda la suite; no llama al modelo ni a Langfuse
uv run pytest tests/guardrail    # el guardrail tiene suite propia
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
```

Cada prueba usa una base temporal, y el backend con dobles de las pruebas de extremo a extremo
(`tests/e2e/app_con_dobles.py`), aunque se arranque a mano con el `.env` de la demo, escribe en
`data/storymaker-e2e.db` y nunca en la base de la demo. Las pruebas de `render_visual` real se
omiten si el servidor Playwright MCP no está en marcha.

La prueba de humo con el modelo real está excluida por defecto y gasta cuota del modelo:
`uv run --env-file ../.env pytest -m real tests/humo -v`.
