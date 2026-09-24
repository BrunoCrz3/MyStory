# Progreso — frontend de la demo

Fichero de retoma. Si la sesión se interrumpe, se sigue desde aquí.

## Estado

| Artefacto | Estado | Siguiente paso |
| --- | --- | --- |
| `specs/spec2-frontend.md` | `borrador` | El desarrollador responde G1–G3 y la aprueba |
| `specs/plan2-frontend.md` | no existe | Se escribe con la spec aprobada |
| `frontend/` | no existe | Se escribe con el plan aprobado |

## Pasos del plan

Aún no hay plan.

## Para la sesión del backend

- **RF-INTAKE-01 choca con el schema.** `validarBrief` recibe un `BriefNovela`, que exige
  `destinatario.nombre` y `edad`: un brief sin nombre es un `422`, no un `200` con
  `DatoFaltante`. Ver `spec2-frontend.md` G1.
- **Lo que el render de lectura ofrece a `render_visual` y al export**: URL
  `/novelas/{novel_id}/versiones/{version}` y los `data-testid` de `spec2-frontend.md` § 4.

## Para integrar en trade-offs y registro

Decisiones de esta sesión, para pasar a `docs/trade-offs.md` y
`docs/registro-iteraciones.md` al fusionar. Numeración pendiente.

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
