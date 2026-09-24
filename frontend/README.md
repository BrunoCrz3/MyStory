# storyMaker — frontend

React 18 + TypeScript + Vite. Tres páginas: `entrevista`, `progreso` y `lectura`
(`specs/spec2-frontend.md`). El cliente de la API se genera desde `specs/openapi.yaml`.

## Arrancar frontend y backend juntos

Hacen falta dos terminales, y una tercera si se quiere `render_visual`. Los puertos son
fijos: el backend escucha en `127.0.0.1:8000` y el frontend en `127.0.0.1:5173`.

**1. Backend** (desde la raíz del repositorio; detalle en `specs/plan1.md` § 9). `backend/` lo
construye el plan 1 en su propia rama; hasta que se fusione, estos comandos se ejecutan allí:

```bash
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
# En .env: ANTHROPIC_API_KEY, LANGFUSE_* y STORYMAKER_LECTURA_URL=http://127.0.0.1:5173
cd backend
uv sync
uv run playwright install chromium
uv run --env-file ../.env uvicorn app.main:app --reload --port 8000
```

Un solo worker y solo en `127.0.0.1`: el backend no tiene autenticación (spec1 RNF-12).
`STORYMAKER_LECTURA_URL` es la URL de este frontend. Con ella, `render_visual` y el export a
PDF abren la página de lectura (`spec1.md` § 4.4).

**2. Frontend** (otra terminal):

```bash
cd frontend
npm install
npm run dev                 # http://127.0.0.1:5173
```

El frontend llama al backend por el proxy de Vite: `/api/*` → `http://127.0.0.1:8000/*`.
No hace falta CORS.

**3. Opcional, para `render_visual`** (otra terminal):

```bash
npx -y @playwright/mcp --port 8931
```

**Comprobarlo**: `http://127.0.0.1:5173/api/salud` debe devolver el JSON de `GET /salud`. Si
devuelve 500 y la terminal de Vite dice `ECONNREFUSED 127.0.0.1:8000`, el backend no está
levantado.

## Recorrido de la demo

1. `http://127.0.0.1:5173/`: rellena el formulario —el ejemplo `BriefNovela` de
   `specs/openapi.yaml` sirve de guía, con datos ficticios—, pulsa **Validar** y, con el
   brief completo, **Crear y generar**.
2. El progreso se actualiza solo al ritmo que marca el backend y se para al terminar.
3. **Leer la versión 1**: portada, índice, ficha y los diez capítulos.
4. Selecciona un fragmento de un capítulo y pulsa **Pedir cambio**, o abre **Hechos de este
   capítulo** y elige uno. Revisa qué capítulos cambian y pulsa **Confirmar y regenerar**.
5. Al publicarse la versión 2, los capítulos cambiados llevan **Modificado en esta versión**,
   y el selector de versión sigue abriendo la 1 entera.
6. **Descargar PDF**.

## Comandos

```bash
npm run dev          # servidor de desarrollo en 127.0.0.1:5173
npm run typecheck    # tsc estricto, sin emitir
npm run test         # Vitest con jsdom; no necesita el backend
npm run build        # typecheck + build de producción en dist/
npm run gen:api      # regenera src/shared/api/schema.d.ts desde specs/openapi.yaml
```

Si cambia `specs/openapi.yaml`, ejecuta `npm run gen:api`. Si no, la prueba de contrato
(`tests/shared/api/contrato.test.ts`) falla. La prueba del contrato de lectura
(`tests/pages/lectura/contrato-lectura.test.tsx`) lee la tabla CL-03 de `specs/spec1.md` en
cada ejecución, así que también falla si esa tabla cambia sin que la lectura la siga.

## Estructura

Feature-Sliced Design v2.1, solo con `app/`, `pages/` y `shared/`:

```
src/app/       proveedores, router y estilos globales
src/pages/     entrevista/, progreso/, lectura/ (con lectura.css y su @media print)
src/shared/    api/ (cliente generado y problem+json), config/ (rutas), ui/
tests/         pruebas y datos de prueba construidos desde los ejemplos del contrato
```

`tests/arquitectura.test.ts` hace cumplir las fronteras: sin `any`, sin importar de
`tests/`, capas hacia abajo, sin cruces entre páginas y siempre por `index.ts`.
