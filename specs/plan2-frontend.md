---
estado: borrador
aprobada-por:
fecha: 2026-09-24
spec: specs/spec2-frontend.md (aprobada el 2026-09-24)
progreso: specs/progreso-frontend.md
---

# Plan 2 — Frontend de la demo

Cómo se construye lo que especifica `specs/spec2-frontend.md`. Pasos pequeños, cada uno
con **la prueba que se escribe primero**, su criterio de terminado **por comando** y un
commit.

> **Estado: borrador.** No se escribe código hasta que el desarrollador lo mueva a
> `aprobado`. Aprobado, se ejecuta de principio a fin sin pedir confirmación, salvo en las
> condiciones de parada.

---

## Reglas de ejecución

1. **TDD en cada paso.** Se escribe la prueba, se comprueba que falla **por la razón
   correcta** —el componente o la función no existen, no un error de configuración— y
   después el código mínimo que la pasa.
2. **Terminado = comando en verde.** Todo paso termina con, desde `frontend/`:

   ```bash
   npm run typecheck && npm run test
   ```

   y los comandos adicionales que diga el paso. Un paso no está terminado por inspección.
3. **Un commit por paso**, mensaje en imperativo, con el identificador del paso (`F03`).
4. **Tras cada commit se actualiza `specs/progreso-frontend.md`** en ese mismo commit: paso
   hecho, siguiente paso y cualquier decisión nueva en «Para integrar en trade-offs y
   registro».
5. **Solo se tocan `frontend/` y `specs/*-frontend.md`.** Ni `CLAUDE.md`, ni `docs/`, ni
   `specs/openapi.yaml`, ni `specs/spec1.md`, ni el backend.
6. **Los datos de prueba viven en `frontend/tests/`** y salen de los ejemplos de
   `specs/openapi.yaml`; donde no hay ejemplo, se tipan con `satisfies` contra los tipos
   generados. Datos ficticios siempre (RNF-17).

## Condiciones de parada

La ejecución se **detiene**, deja el motivo en `specs/progreso-frontend.md` y avisa al
desarrollador cuando:

| # | Condición |
| --- | --- |
| S1 | `typecheck` o `test` siguen en rojo tras **tres** intentos de arreglo dentro del mismo paso |
| S2 | El contrato resulta insuficiente para una pantalla, o una prueba solo pasaría cambiándolo |
| S3 | El paso exige tocar algo fuera de `frontend/` o `specs/*-frontend.md` |
| S4 | Hace falta una dependencia que no está en `spec2-frontend.md` § 6 |
| S5 | Se llega a un paso **bloqueado** (B1, B2) sin que el desarrollador haya avisado del commit del backend |
| S6 | `git merge Contexto-semilla-v2` da un conflicto fuera de `frontend/` o `specs/*-frontend.md`, o el contrato incorporado cambia algo más que lo anunciado |
| S7 | `npm install` falla o una dependencia aprobada no instala en la versión esperada |

---

## Estructura resultante

```
frontend/
  package.json  vite.config.ts  tsconfig.json  index.html  README.md
  src/
    app/        main.tsx, providers (QueryClient), router, estilos globales
    pages/
      entrevista/   ui/, model/ (formulario → brief), api/
      progreso/     ui/, api/
      lectura/      ui/ (portada, índice, capítulo, ficha, cambio, versiones, pdf), api/, model/
    shared/
      api/      schema.d.ts (generado), cliente, problema (lectura de problem+json)
      ui/       piezas sin dominio: aviso de problema, carga
  tests/
    apoyo/      ejemplos del OpenAPI, fetch de prueba, render con proveedores
    datos/      respuestas construidas desde los ejemplos
    …           una prueba por paso, reflejando src/
```

Sin `widgets/`, `features/` ni `entities/`: ningún código se usa hoy desde dos páginas
salvo el cliente y el aviso de problema, que son `shared/` (skill FSD § 2).

---

## Pasos

| Paso | Qué | Prueba que se escribe primero | CA | Estado |
| --- | --- | --- | --- | --- |
| F01 | Andamio | `tests/app/arranque.test.tsx` | — | pendiente |
| F02 | Cliente generado | `tests/shared/api/contrato.test.ts` | CA-01 | pendiente |
| F03 | Apoyo de pruebas | `tests/apoyo/apoyo.test.ts` | — | pendiente |
| F04 | Guardas de arquitectura | `tests/arquitectura.test.ts` | CA-14 | pendiente |
| F05 | Rutas y problema | `tests/app/rutas.test.tsx`, `tests/shared/api/problema.test.ts` | — | pendiente |
| F06 | Progreso | `tests/pages/progreso/progreso.test.tsx` | CA-05 | pendiente |
| F07 | Lectura: portada, índice, capítulos | `tests/pages/lectura/lectura.test.tsx` | CA-06, CA-08 (sin `data-testid`) | pendiente |
| F08 | Lectura: ficha | `tests/pages/lectura/ficha.test.tsx` | CA-07 | pendiente |
| F09 | Modificados y versiones | `tests/pages/lectura/versiones.test.tsx` | CA-12 | pendiente |
| F10 | Cambio por hecho | `tests/pages/lectura/cambio-hecho.test.tsx` | CA-10, CA-11 | pendiente |
| F11 | Cambio por fragmento | `tests/pages/lectura/cambio-fragmento.test.tsx` | CA-09 | pendiente |
| F12 | PDF | `tests/pages/lectura/pdf.test.tsx` | CA-13 | pendiente |
| F13 | Entrevista: formulario y crear | `tests/pages/entrevista/crear.test.tsx` | CA-04 | pendiente |
| F14 | Entrevista: resultado de validación | `tests/pages/entrevista/validacion.test.tsx` | CA-03, CA-02 (red de seguridad) | pendiente |
| F15 | Arranque conjunto | `npm run build` | — | pendiente |
| **B1** | Incorporar el brief parcial | `tests/pages/entrevista/validacion.test.tsx` ampliada | CA-02 | **bloqueado**: commit del backend |
| **B2** | Incorporar el contrato de lectura | `tests/pages/lectura/contrato-lectura.test.tsx` | CA-08 | **bloqueado**: commit del backend |

F01–F15 no dependen del contrato de validación nuevo ni de los `data-testid`: ninguna
prueba de esos pasos busca por `data-testid`, sino por rol y texto accesible.

### F01 · Andamio

`frontend/` con Vite + React 18 + TypeScript (`strict`, `noUncheckedIndexedAccess`,
`noImplicitAny`), Vitest con `jsdom` y `@testing-library/jest-dom`, alias `@/` → `src/`,
proxy `/api` → `http://127.0.0.1:8000` con reescritura del prefijo. Scripts `dev`, `build`,
`typecheck` (`tsc --noEmit`), `test` (`vitest run`) y `gen:api`.

- **Prueba primero**: la aplicación monta y muestra el nombre del producto.
- **Terminado**: `npm install && npm run typecheck && npm run test`.

### F02 · Cliente generado

`npm run gen:api` ejecuta `openapi-typescript ../specs/openapi.yaml -o
src/shared/api/schema.d.ts`. `src/shared/api/cliente.ts` crea el cliente de `openapi-fetch`
con `baseUrl: '/api'` y admite inyectar `fetch`, que es la costura de las pruebas: no hay
nada de prueba en `src/`.

- **Prueba primero** (CA-01): genera los tipos en memoria con la API de `openapi-typescript`
  desde `specs/openapi.yaml` y los compara con el `schema.d.ts` commiteado.
- **Terminado**: `npm run gen:api && git diff --exit-code src/shared/api/schema.d.ts &&
  npm run typecheck && npm run test`.

### F03 · Apoyo de pruebas

En `tests/apoyo/`: `ejemplos.ts` lee `specs/openapi.yaml` con `yaml` y devuelve un ejemplo
por ruta (`Generacion.enCurso`, `BriefNovela`, `NuevaSolicitudCambio.porHecho`…);
`fetch-de-prueba.ts` enruta `método + ruta` a respuestas y registra las peticiones;
`render.tsx` monta con `QueryClient` sin reintentos, `MemoryRouter` y el cliente con el
`fetch` de prueba. En `tests/datos/` las respuestas que el contrato no trae como ejemplo
(`Version`, `Capitulo[]`, `Portada`, `Ficha`, `Hecho[]`, `SolicitudCambio`, `Exportacion`,
`VersionResumen[]`), construidas con los identificadores de los ejemplos.

- **Prueba primero**: el ejemplo `enCurso` se lee con `estado: Escribiendo`; el `fetch` de
  prueba devuelve la respuesta registrada y un `404` `problem+json` para lo no registrado.
- **Terminado**: comando común.

### F04 · Guardas de arquitectura

- **Prueba primero** (CA-14), recorriendo `src/`: ningún `any` como tipo; ninguna
  importación de `tests/`; `shared/` no importa de `pages/` ni `app/`; `pages/X` no importa
  de `pages/Y`; nadie importa de `widgets/`; los imports entre capas pasan por `index.ts`.
- **Terminado**: comando común.

### F05 · Rutas y problema

`app/router` con las cuatro rutas de la spec § 4. `shared/api/problema.ts` convierte una
respuesta de error en un `Problema` tipado, y `shared/ui` lo pinta con `title`, `detail`,
enlace a `generacion_id` y `traza_langfuse_id`. `/novelas/:id` redirige a la versión
vigente, o a la última generación si no la hay.

- **Prueba primero**: cada ruta pinta su página; la redirección con y sin
  `version_vigente`; un `409` del ejemplo `Conflicto` se lee con su `generacion_id`.
- **Terminado**: comando común.

### F06 · Progreso

- **Prueba primero** (CA-05) con temporizadores falsos: `enCurso` muestra 3 de 10 y pide
  de nuevo pasado su `intervalo_sondeo_segundos`; `detenida` muestra
  `limite-de-intentos-agotado` y no pide más; una `Publicada` enlaza a la lectura de
  `version_resultante`; una dirigida muestra `capitulos_a_regenerar`.
- **Terminado**: comando común.

### F07 · Lectura: portada, índice, capítulos

- **Prueba primero**: con una versión de diez capítulos, el índice tiene diez enlaces a
  `#capitulo-N` y cada capítulo está en su ancla (CA-06); la portada muestra título,
  dedicatoria y firma (CA-08, sin `data-testid`).
- **Terminado**: comando común.

### F08 · Lectura: ficha

- **Prueba primero** (CA-07): un personaje de los capítulos 2 y 7 enlaza a `#capitulo-2` y
  `#capitulo-7`; los lugares igual.
- **Terminado**: comando común.

### F09 · Modificados y versiones

- **Prueba primero** (CA-12): versión 2 con 3 y 7 `modificado`; solo esas dos entradas del
  índice y esas dos cabeceras llevan «Modificado en esta versión»; el selector lista las
  versiones con su `motivo` y navega a la 1.
- **Terminado**: comando común.

### F10 · Cambio por hecho

- **Prueba primero** (CA-10, CA-11): «Hechos de este capítulo» en el 3 pide `listarHechos`
  con `capitulo=3`; elegir uno y escribir el enunciado envía exactamente el cuerpo del
  ejemplo `porHecho`; se muestran `hecho_afectado` y los capítulos afectados;
  `confirmarSolicitudCambio` **no** se llama hasta «Confirmar», y entonces se navega al
  progreso; un `409` muestra el enlace a su `generacion_id`.
- **Terminado**: comando común.

### F11 · Cambio por fragmento

- **Prueba primero** (CA-09): seleccionar texto del capítulo 3 muestra «Pedir cambio»; se
  envía el cuerpo del ejemplo `porFragmento`; se muestra `hecho_candidato` y se exige la
  misma confirmación.
- **Terminado**: comando común.

### F12 · PDF

- **Prueba primero** (CA-13): `disponible` ofrece el enlace a
  `/api/novelas/{id}/versiones/{v}/export`; `en-curso` ofrece «Volver a comprobar» y no
  hay más peticiones sin pulsarlo; `fallido` lo dice; `paridad_pdf_web` se muestra si viene.
- **Terminado**: comando común.

### F13 · Entrevista: formulario y crear

`pages/entrevista/model/` convierte el estado del formulario en el cuerpo de la petición:
listas una por línea, filas de elementos y textos libres, opcionales vacíos fuera. Es
serialización, no dominio: no decide qué falta.

- **Prueba primero** (CA-04): rellenar el formulario con los valores del ejemplo
  `BriefNovela` y validar envía ese mismo objeto; con `valido: true`, «Crear y generar»
  llama a `crearNovela` y luego a `lanzarGeneracion` y navega al progreso; tras editar un
  campo, el botón vuelve a deshabilitarse. La lista de novelas enlaza a cada una.
- **Terminado**: comando común.

### F14 · Entrevista: resultado de validación

- **Prueba primero** (CA-03 y la red de seguridad de CA-02): un `FragmentoSospechoso` sale
  como descartado; contradicciones y hechos extraídos se pintan; `datos_faltantes` se pintan
  junto a su campo vengan de un `200`, de un `400 brief-invalido` o de un `422` que los
  traiga; un `422` sin ellos pinta su `detail` en la cabecera.
- **Terminado**: comando común.

### F15 · Arranque conjunto

`frontend/README.md` con cómo arrancar backend y frontend juntos y qué puerto usa cada uno,
y el mismo resumen en `specs/progreso-frontend.md`.

- **Terminado**: comando común y `npm run build`.

### B1 · Incorporar el brief parcial — bloqueado

**Solo** cuando el desarrollador avise del commit del backend.
`git merge Contexto-semilla-v2`, `npm run gen:api` y adaptar el tipo del cuerpo de
`validarBrief` al brief parcial.

- **Prueba primero** (CA-02 completo): un formulario sin nombre se valida —ya no rompe el
  tipo— y la `pregunta_reintento` del `200` aparece junto al campo; la red de seguridad de
  F14 sigue en verde.
- **Terminado**: comando común y `git diff --exit-code src/shared/api/schema.d.ts` tras
  regenerar.

### B2 · Incorporar el contrato de lectura — bloqueado

Tras el mismo merge: ajustar la URL de lectura, los `data-testid` y la hoja `@media print` a
la lista que fije `specs/spec1.md`, y la spec 2 § 4 si difiere.

- **Prueba primero** (CA-08 completo): cada `data-testid` de `spec1.md` existe en la
  lectura con una versión de diez capítulos; la hoja de impresión oculta navegación,
  paneles y botones.
- **Terminado**: comando común.

---

## Riesgos

| Riesgo | Qué se hace |
| --- | --- |
| La selección de texto en `jsdom` es incompleta | F11 fija la selección con la API `Range` de `jsdom`; si no basta, la lectura de la selección se aísla en una función pequeña que se prueba sola |
| El `oneOf` de `NuevaSolicitudCambio` genera un tipo incómodo | Se usa tal cual lo genere `openapi-typescript`; si no admite los dos ejemplos, es S2 |
| El merge de B1 trae más cambios de contrato de los anunciados | S6: se detiene y se explica, no se adapta a ciegas |
| El backend no está listo el día de la demo | F01–F15 son demostrables con el backend real en cuanto responda; sin él, solo las pruebas |
