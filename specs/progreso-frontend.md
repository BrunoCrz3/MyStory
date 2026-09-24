# Progreso — frontend de la demo

Fichero de retoma. Si la sesión se interrumpe, se sigue desde aquí.

## Estado

| Artefacto | Estado | Siguiente paso |
| --- | --- | --- |
| `specs/spec2-frontend.md` | `aprobada` (2026-09-24) | — |
| `specs/plan2-frontend.md` | `borrador` | El desarrollador lo aprueba |
| `frontend/` | no existe | Se escribe con el plan aprobado |

## Pasos del plan

Ver la tabla de `specs/plan2-frontend.md`. Ninguno empezado.

**Bloqueos**: B1 y B2 esperan a que el desarrollador avise del commit del backend en
`Contexto-semilla-v2` (brief parcial para `validarBrief` y contrato de lectura en
`spec1.md`). Hasta ese aviso no se hace el merge.

## Para la sesión del backend

- **RF-INTAKE-01 choca con el schema** (G1). Resuelto por el desarrollador: el backend
  separa un brief parcial para `validarBrief`. Se incorpora en B1.
- **Contrato de lectura para Playwright**: lo fija el backend en `spec1.md`. La propuesta
  provisional del frontend está en `spec2-frontend.md` § 4. Se incorpora en B2.

## Para integrar en trade-offs y registro

Decisiones de esta sesión, para pasar a `docs/trade-offs.md` y
`docs/registro-iteraciones.md` al fusionar. Numeración pendiente.

- **Tres páginas, no dos** (G2, decidido por el desarrollador): `entrevista`, `progreso` y
  `lectura`. `CLAUDE.md` § Persistencia, backend y frontend dice «Dos páginas» y debe pasar
  a decir tres, con `progreso` como destino común de la entrevista y de la confirmación de
  un cambio.
- **Dependencias del frontend aprobadas** (G3, decidido por el desarrollador): en ejecución
  `react-router-dom` y `openapi-fetch`, además de las del stack (`react`, `react-dom`,
  `@tanstack/react-query`); en desarrollo `openapi-typescript`, `vitest`, `jsdom`, Testing
  Library (`react`, `user-event`, `jest-dom`) y `yaml`, además de `vite`,
  `@vitejs/plugin-react` y `typescript`.
- **Validación del brief sin campos obligatorios** (G1, decidido por el desarrollador): el
  arreglo va al contrato —brief parcial para `validarBrief`— y el frontend conserva una red
  de seguridad: pinta `datos_faltantes` venga en la respuesta que venga, y el `detail` de un
  `422` que no los traiga.
- **Cliente generado con `openapi-typescript` + `openapi-fetch`**, frente a orval o
  `@hey-api/openapi-ts`: solo tipos y un `fetch` fino, sin plantillas de código que revisar.
- **Proxy de Vite `/api` → `127.0.0.1:8000`**, frente a CORS en el backend: no toca el
  backend y la instancia sigue escuchando solo en local.
- **Respuestas de prueba sin MSW**: un `fetch` de prueba inyectado en el cliente desde
  `tests/`, con los ejemplos leídos de `specs/openapi.yaml`.
- **El export no se sondea**: el contrato no da intervalo y no se escribe una cifra suelta;
  el lector vuelve a comprobar con un botón.
- **La descarga se construye con la ruta de `descargarExport`**, no con `url_descarga`, que
  es un `uri-reference` sin base definida.
