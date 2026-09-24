---
estado: aprobada
aprobada-por: Bruno Cruz
fecha: 2026-09-24
spec: specs/spec2-frontend.md (aprobada el 2026-09-24, ajustada el mismo día al commit 7d389a7)
contrato: specs/openapi.yaml 1.1.0 y specs/spec1.md § 4.4
progreso: specs/progreso-frontend.md
---

# Plan 2 — Frontend de la demo

Cómo se construye lo que especifica `specs/spec2-frontend.md` contra el contrato
`specs/openapi.yaml` **1.1.0** y el contrato de lectura de `specs/spec1.md` § 4.4. Pasos
pequeños, cada uno con **la prueba que se escribe primero**, su criterio de terminado **por
comando** y su commit. Se reanuda en frío desde `specs/progreso-frontend.md`.

> **Estado: aprobada** el 2026-09-24 por el desarrollador. El agente **comprueba el
> frontmatter antes del F01**, no de memoria. Se ejecuta de principio a fin sin pedir
> confirmación, salvo en las condiciones de parada.

---

## 0. Protocolo de ejecución

El mismo que `specs/plan1.md` § 0, adaptado al frontend. En **cada** paso:

1. **Leer `specs/progreso-frontend.md`.** El paso actual es el que dice ahí. Si está en
   `pruebas-escritas`, se retoma desde el punto 4.
2. **Cargar la skill `feature-sliced-design`** antes de colocar un fichero nuevo en `src/`.
3. **Escribir las pruebas del paso** y comprobar que **fallan por la razón correcta**: falta
   el componente, falta la ruta, el valor no coincide. Un error de configuración del propio
   test no cuenta. Anotar `pruebas-escritas`.
4. **Escribir el código mínimo** que las pone en verde, y refactorizar con la suite en verde.
5. **Ejecutar el criterio «Terminado»** del paso, que siempre incluye, desde `frontend/`:

   ```bash
   npm run typecheck && npm run test
   ```

6. **Actualizar `specs/progreso-frontend.md`**: paso cerrado, lo hecho, decisiones nuevas y
   siguiente paso.
7. **Commit** en imperativo con el identificador del paso (`F03: Añadir el fetch de
   prueba`). Un paso puede dar más de un commit, pero **nunca** un commit tiene dos pasos.

**Qué cuenta como intento.** Un ciclo «cambio de código → suite» que acaba en rojo
**después** de escribir las pruebas del paso. Los rojos esperados del punto 3 no cuentan.
El contador vive en el fichero de progreso y se reinicia al cerrar el paso.

**Decisiones del agente.** Todo lo que no sea una condición de parada lo decide el agente.
Cada decisión que no esté en este plan entra en `specs/progreso-frontend.md` § «Para integrar
en trade-offs y registro» con un identificador `FA-NN`, el paso y el porqué, marcada
**«decidido por el agente — revisar»**. `docs/trade-offs.md` y el registro no se tocan
desde esta sesión.

**Alcance de escritura.** Solo `frontend/` y `specs/*-frontend.md`. Los datos de prueba
viven en `frontend/tests/`, salen de los ejemplos de `specs/openapi.yaml` y, donde no hay
ejemplo, se tipan con `satisfies` contra los tipos generados. Datos siempre ficticios
(RNF-17).

## 1. Condiciones de parada

La ejecución se **detiene**, deja en `specs/progreso-frontend.md` § Parada qué condición es,
en qué paso, qué se intentó y qué hace falta, hace commit de ese fichero y avisa:

| # | Condición |
| --- | --- |
| S1 | La suite no se pone en verde tras **tres** intentos en el mismo paso |
| S2 | El contrato —`openapi.yaml` o `spec1.md` § 4.4— resulta insuficiente para una pantalla, o una prueba solo pasaría cambiándolo |
| S3 | El paso exige tocar algo fuera de `frontend/` o `specs/*-frontend.md` |
| S4 | Hace falta una dependencia que no está en `spec2-frontend.md` § 6 |
| S5 | `npm install` no instala una dependencia aprobada |

**Lo que no es parada**, y el agente resuelve y registra: un nombre local, un estilo, un
fallo intermitente de prueba —que se arregla, no se reintenta hasta que pase— o que el
backend no esté levantado: la suite no lo necesita.

---

## 2. Estructura resultante

```
frontend/
  package.json  vite.config.ts  tsconfig.json  index.html  README.md
  src/
    app/        main.tsx, providers (QueryClient), router, estilos globales
    pages/
      entrevista/   ui/, model/ (formulario ↔ brief parcial), api/
      progreso/     ui/, api/
      lectura/      ui/ (portada, índice, capítulo, ficha, cambio, versiones, pdf), api/,
                    lectura.css (con @media print)
    shared/
      api/      schema.d.ts (generado), cliente, problema (lectura de problem+json)
      ui/       piezas sin dominio: aviso de problema, carga
  tests/
    apoyo/      ejemplos del OpenAPI, fetch de prueba, render con proveedores
    datos/      respuestas construidas desde los ejemplos
    …           una prueba por paso, reflejando src/
```

Sin `widgets/`, `features/` ni `entities/`: fuera del cliente y del aviso de problema, que
son `shared/`, ningún código se usa hoy desde dos páginas (skill FSD § 2).

---

## 3. Pasos

| Paso | Qué | Prueba que se escribe primero | CA | Estado |
| --- | --- | --- | --- | --- |
| F01 | Andamio | `tests/app/arranque.test.tsx` | — | hecho |
| F02 | Cliente generado desde 1.1.0 | `tests/shared/api/contrato.test.ts` | CA-01 | hecho |
| F03 | Apoyo de pruebas | `tests/apoyo/apoyo.test.ts` | — | hecho |
| F04 | Guardas de arquitectura | `tests/arquitectura.test.ts` | CA-14 | hecho |
| F05 | Rutas y problema | `tests/app/rutas.test.tsx`, `tests/shared/api/problema.test.ts` | — | hecho |
| F06 | Progreso | `tests/pages/progreso/progreso.test.tsx` | CA-05 | hecho |
| F07 | Lectura: raíz, portada, índice, capítulos | `tests/pages/lectura/lectura.test.tsx` | CA-06, CA-08 | hecho |
| F08 | Lectura: ficha | `tests/pages/lectura/ficha.test.tsx` | CA-07 | hecho |
| F09 | Modificados y versiones | `tests/pages/lectura/versiones.test.tsx` | CA-12 | hecho |
| F10 | Cambio por hecho | `tests/pages/lectura/cambio-hecho.test.tsx` | CA-10, CA-11 | hecho |
| F11 | Cambio por fragmento | `tests/pages/lectura/cambio-fragmento.test.tsx` | CA-09 | hecho |
| F12 | PDF | `tests/pages/lectura/pdf.test.tsx` | CA-13 | pendiente |
| F13 | Contrato de lectura completo e impresión | `tests/pages/lectura/contrato-lectura.test.tsx` | CA-15, CA-16 | pendiente |
| F14 | Entrevista: formulario y crear | `tests/pages/entrevista/crear.test.tsx` | CA-04 | pendiente |
| F15 | Entrevista: resultado de validación | `tests/pages/entrevista/validacion.test.tsx` | CA-02, CA-03 | pendiente |
| F16 | Arranque conjunto | `npm run build` | — | pendiente |

**Desbloqueado el 2026-09-24.** Los antiguos B1 (brief parcial) y B2 (contrato de lectura)
ya no esperan a nadie: el commit `7d389a7` del backend está fusionado en `frontend-demo`.
B1 queda dentro de F02, F14 y F15; B2 dentro de F07–F09 y F13.

### F01 · Andamio

`frontend/` con Vite + React 18 + TypeScript (`strict`, `noUncheckedIndexedAccess`),
Vitest con `jsdom` y `@testing-library/jest-dom`, alias `@/` → `src/`, y proxy `/api` →
`http://127.0.0.1:8000` que quita el prefijo. Scripts `dev` (puerto 5173, `strictPort`),
`build`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`) y `gen:api`.

- **Prueba primero**: la aplicación monta y muestra el nombre del producto.
- **Terminado**: `npm install && npm run typecheck && npm run test`.

### F02 · Cliente generado desde 1.1.0

`npm run gen:api` ejecuta `openapi-typescript ../specs/openapi.yaml -o
src/shared/api/schema.d.ts`. `src/shared/api/cliente.ts` crea el cliente de `openapi-fetch`
con `baseUrl: '/api'` y admite inyectar `fetch`, que es la costura de las pruebas: en `src/`
no hay nada de prueba. `validarBrief` queda tipado con `BriefNovelaParcial` y `crearNovela`
con `BriefNovela`, tal como salen del contrato.

- **Prueba primero** (CA-01): genera los tipos en memoria con la API de `openapi-typescript`
  desde `specs/openapi.yaml` y los compara con el `schema.d.ts` commiteado; comprueba que
  `info.version` es `1.1.0`.
- **Terminado**: `npm run gen:api && git diff --exit-code src/shared/api/schema.d.ts &&
  npm run typecheck && npm run test`.

### F03 · Apoyo de pruebas

En `tests/apoyo/`: `ejemplos.ts` lee `specs/openapi.yaml` con `yaml` y devuelve un ejemplo
por ruta (`Generacion.enCurso`, `BriefNovela`, `BriefNovelaParcial`,
`NuevaSolicitudCambio.porHecho`…); `fetch-de-prueba.ts` enruta `método + ruta` a respuestas
y registra las peticiones; `render.tsx` monta con un `QueryClient` sin reintentos, un
`MemoryRouter` y el cliente con el `fetch` de prueba. En `tests/datos/`, las respuestas que
el contrato no trae como ejemplo (`Version`, `Capitulo[]`, `Portada`, `Ficha`, `Hecho[]`,
`SolicitudCambio`, `Exportacion`, `VersionResumen[]`), construidas con los identificadores
de los ejemplos.

- **Prueba primero**: el ejemplo `enCurso` se lee con `estado: Escribiendo`; el `fetch` de
  prueba devuelve la respuesta registrada, y un `404` `problem+json` para lo no registrado.
- **Terminado**: comando común.

### F04 · Guardas de arquitectura

- **Prueba primero** (CA-14), recorriendo `src/`: ningún `any` como tipo; ninguna
  importación de `tests/`; `shared/` no importa de `pages/` ni de `app/`; `pages/X` no
  importa de `pages/Y`; no existe `widgets/`; los imports entre capas pasan por `index.ts`.
- **Terminado**: comando común.

### F05 · Rutas y problema

`app/router` con las cuatro rutas de la spec § 4. `shared/api/problema.ts` convierte una
respuesta de error en un `Problema` tipado, y `shared/ui` lo pinta con `title`, `detail`,
el enlace a `generacion_id` y la `traza_langfuse_id`. `/novelas/:id` redirige a la versión
vigente o, si no hay, a la última generación.

- **Prueba primero**: cada ruta pinta su página; la redirección con y sin
  `version_vigente`; un `409` del ejemplo `Conflicto` se lee con su `generacion_id`.
- **Terminado**: comando común.

### F06 · Progreso

- **Prueba primero** (CA-05), con temporizadores falsos: `enCurso` muestra 3 de 10 y vuelve
  a pedir pasado su `intervalo_sondeo_segundos`; `detenida` muestra
  `limite-de-intentos-agotado` y no pide más; una `Publicada` enlaza a la lectura de
  `version_resultante`; una dirigida muestra `capitulos_a_regenerar`.
- **Terminado**: comando común.

### F07 · Lectura: raíz, portada, índice, capítulos

El elemento raíz `lectura` con `data-estado`, `data-novel-id` y `data-version` (CL-02);
`portada`, `portada-titulo` y `portada-dedicatoria`; `indice` con una `indice-entrada` por
capítulo; y un `capitulo` por capítulo con `capitulo-titulo` y `capitulo-texto`
(`spec1.md` CL-03). Todos los capítulos en el DOM a la vez (CL-01).

- **Prueba primero** (CA-06, CA-08): con una versión de diez capítulos, diez
  `indice-entrada` con `data-capitulo` que enlazan a `#capitulo-N`, y diez `capitulo` con
  `id="capitulo-N"`; `portada-titulo` y `portada-dedicatoria` con su texto, y la firma en la
  portada.
- **Terminado**: comando común.

### F08 · Lectura: ficha

`ficha` con `ficha-personaje` y `ficha-lugar` (`data-nombre`) y un `ficha-enlace-capitulo`
con `data-capitulo` por cada capítulo de la entrada.

- **Prueba primero** (CA-07): un personaje de los capítulos 2 y 7 tiene dos
  `ficha-enlace-capitulo` a `#capitulo-2` y `#capitulo-7`; los lugares igual.
- **Terminado**: comando común.

### F09 · Modificados y versiones

`capitulo-modificado` dentro de la `indice-entrada` y del `capitulo` **solo** si `modificado`
es `true`; selector de versión con `listarVersiones`.

- **Prueba primero** (CA-12): una versión 2 con 3 y 7 `modificado` tiene exactamente cuatro
  `capitulo-modificado`, en esas dos entradas y esos dos capítulos; el selector lista las
  versiones con su `motivo` y navega a la 1.
- **Terminado**: comando común.

### F10 · Cambio por hecho

- **Prueba primero** (CA-10, CA-11): «Hechos de este capítulo» en el 3 pide `listarHechos`
  con `capitulo=3`; elegir uno y escribir el enunciado envía exactamente el cuerpo del
  ejemplo `porHecho`; se muestran `hecho_afectado` y los capítulos afectados;
  `confirmarSolicitudCambio` **no** se llama hasta «Confirmar», y entonces se navega al
  progreso; un `409` muestra el enlace a su `generacion_id`. Los controles quedan dentro del
  `capitulo` y **fuera** de `capitulo-texto`.
- **Terminado**: comando común.

### F11 · Cambio por fragmento

- **Prueba primero** (CA-09): seleccionar texto dentro de `capitulo-texto` del capítulo 3
  muestra «Pedir cambio»; se envía el cuerpo del ejemplo `porFragmento`; se muestra
  `hecho_candidato` y se exige la misma confirmación. `capitulo-texto` sigue conteniendo
  solo `Capitulo.texto`.
- **Terminado**: comando común.

### F12 · PDF

- **Prueba primero** (CA-13): `disponible` ofrece el enlace a
  `/api/novelas/{id}/versiones/{v}/export`; `en-curso` ofrece «Volver a comprobar» y no hay
  más peticiones si no se pulsa; `fallido` lo dice; `paridad_pdf_web` se muestra si viene.
- **Terminado**: comando común.

### F13 · Contrato de lectura completo e impresión

Una sola prueba que recorre **toda** la tabla CL-03 de `spec1.md` § 4.4, fila a fila, sobre
una versión de diez capítulos con ficha y dos capítulos modificados; y `lectura.css` con sus
reglas `@media print` (CL-04). Los controles interactivos llevan una marca común de clase o
atributo que la hoja oculta al imprimir.

- **Prueba primero** (CA-15): `data-estado` pasa de `cargando` a `lista`, y es `error` ante
  un `404`; cada `data-testid` aparece tantas veces como dice la tabla, dentro de su padre,
  con sus atributos y su contenido; `capitulo-texto` es igual a `Capitulo.texto`.
  (CA-16): `lectura.css` contiene un bloque `@media print` que muestra todo `capitulo`, fija
  `break-before: page` en cada `capitulo` y oculta la marca de controles. `jsdom` no aplica
  medios, así que se comprueba la hoja, no el render. El render impreso lo comprueba el
  P49 del backend.
- **Terminado**: comando común.

### F14 · Entrevista: formulario y crear

`pages/entrevista/model/` convierte el estado del formulario en un `BriefNovelaParcial`:
listas una por línea, filas de elementos y textos libres, vacíos fuera. Para `crearNovela`,
un estrechamiento de tipo a `BriefNovela` que solo comprueba la presencia de los campos
obligatorios del schema, sin `as`. Es serialización, no dominio: no decide qué falta.

- **Prueba primero** (CA-04): rellenar el formulario con los valores del ejemplo
  `BriefNovela` y validar envía ese mismo objeto; con `valido: true`, «Crear y generar»
  llama a `crearNovela` y luego a `lanzarGeneracion` y navega al progreso; tras editar un
  campo, el botón vuelve a deshabilitarse. La lista de novelas enlaza a cada una.
- **Terminado**: comando común.

### F15 · Entrevista: resultado de validación

- **Prueba primero** (CA-02, CA-03): un formulario sin nombre envía un `BriefNovelaParcial`
  sin `destinatario.nombre`, y la `pregunta_reintento` del `200` aparece junto al campo; un
  `FragmentoSospechoso` sale como descartado; se pintan las contradicciones —también las de
  un `400 brief-invalido`— y los hechos extraídos. **Red de seguridad**: `datos_faltantes`
  junto a su campo vengan de un `200`, de un `400` o de un `422` que los traiga; un `422`
  sin ellos pinta su `detail` en la cabecera.
- **Terminado**: comando común.

### F16 · Arranque conjunto

`frontend/README.md` con cómo arrancar backend y frontend juntos: backend en
`127.0.0.1:8000` según `specs/plan1.md` § 9, frontend en `127.0.0.1:5173` con el proxy, y
`STORYMAKER_LECTURA_URL=http://127.0.0.1:5173` para que `render_visual` y el export
encuentren la lectura. El mismo resumen va en `specs/progreso-frontend.md`.

- **Terminado**: comando común y `npm run build`.

---

## 4. Riesgos

| Riesgo | Qué se hace |
| --- | --- |
| La selección de texto en `jsdom` es incompleta | F11 fija la selección con la API `Range` de `jsdom`; si no basta, la lectura de la selección se aísla en una función pequeña que se prueba sola |
| El `oneOf` de `NuevaSolicitudCambio` genera un tipo incómodo | Se usa tal cual lo genere `openapi-typescript`; si no admite los dos ejemplos, es S2 |
| `jsdom` no evalúa `@media print` | F13 comprueba la hoja; el render impreso real lo comprueba el P49 del backend con Playwright |
| La página `lectura` no cumple `spec1.md` § 4.4 al integrarla | F13 recorre la tabla entera; el P49 del backend corre `render_visual` contra la página real |
| El backend no está listo el día de la demo | F01–F16 se demuestran con el backend real en cuanto responda; sin él, solo las pruebas |
