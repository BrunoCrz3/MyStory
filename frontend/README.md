# storyMaker — frontend

React 18 + TypeScript + Vite. Tres páginas: `entrevista`, `progreso` y `lectura`
(`specs/spec2-frontend.md`). El cliente de la API se genera desde `specs/openapi.yaml`.

## Arrancar frontend y backend juntos

El arranque completo —servidor Playwright MCP, backend y frontend, con sus variables— está en el
[README raíz](../README.md#arrancar-la-demo-en-windows), y el comando del servidor MCP, en
[`docs/browser-mcp.md` § El servidor](../docs/browser-mcp.md#el-servidor), que es su única fuente.
No es opcional: sin ese servidor ninguna versión se publica.

Lo propio del frontend:

```bash
cd frontend
npm install
npm run dev                 # puerto 5173 fijo: es el valor de STORYMAKER_LECTURA_URL
```

El frontend llama al backend por el proxy de Vite: `/api/*` → `http://127.0.0.1:8000/*`, así
que no hace falta CORS. **Comprobarlo**: `http://localhost:5173/api/salud` debe devolver el
JSON de `GET /salud`. Si devuelve 500 y la terminal de Vite dice `ECONNREFUSED 127.0.0.1:8000`,
el backend no está levantado.

## Recorrido de la demo

1. `http://localhost:5173/`: rellena el formulario —el ejemplo `BriefNovela` de
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
