# Progreso — frontend de la demo

Fichero de retoma. Si la sesión se interrumpe, se sigue desde aquí.

## Estado

| Artefacto | Estado | Siguiente paso |
| --- | --- | --- |
| `specs/spec2-frontend.md` | `aprobada` (2026-09-24), ajustada al commit `7d389a7` | — |
| `specs/plan2-frontend.md` | `aprobada` (2026-09-24), ejecutado entero | — |
| `frontend/` | **terminado** (F01–F16) | Integración con el backend real: P49 de `plan1.md` |

## Pasos del plan

Ver la tabla de `specs/plan2-frontend.md` § 3.

| Paso actual | Estado | Intentos |
| --- | --- | --- |
| — | plan terminado | — |

**Sin bloqueos.** `Contexto-semilla-v2` (commit `7d389a7`: contrato 1.1.0 con
`BriefNovelaParcial` y `spec1.md` § 4.4) está fusionado en `frontend-demo` desde el
2026-09-24. Los antiguos B1 y B2 quedan dentro de F02, F07–F09 y F13–F15.

### Registro de pasos

| Paso | Hecho |
| --- | --- |
| F01 | Vite + React 18 + TS estricto, Vitest con jsdom, proxy `/api`, puerto 5173 fijo. Todas las dependencias aprobadas instaladas |
| F02 | Tipos generados desde `openapi.yaml` 1.1.0 con `npm run gen:api`; cliente `openapi-fetch` con `fetch` inyectable y `ProveedorCliente` |
| F03 | Ejemplos leídos de `openapi.yaml` en cada ejecución, `fetch` de prueba con registro de peticiones, render con proveedores y datos de lectura tipados con `satisfies` |
| F04 | Guardas de CA-14 sobre `src/`: sin `any`, sin importar de `tests/`, capas hacia abajo, sin cruces entre páginas y siempre por `index.ts`. Cada regla se prueba primero contra un caso que la viola (1 intento en rojo, por escapes) |
| F05 | Router con las cuatro rutas, redirección de `/novelas/:id`, `exigir`/`aProblema`/`ErrorDeApi` para `problem+json` y `AvisoProblema` en `shared/ui` |
| F06 | Progreso que sondea al `intervalo_sondeo_segundos` del recurso y para por `es_terminal`; enlace a la versión resultante; `detenida_por` tal cual |
| F07 | Raíz `lectura` con `data-estado`/`data-novel-id`/`data-version`, portada, índice con anclas y los diez capítulos en un solo documento, con los `data-testid` de CL-03 |
| F08 | Ficha de personajes y lugares con `ficha-personaje`/`ficha-lugar` y un `ficha-enlace-capitulo` por capítulo; la lectura solo está `lista` con la ficha cargada |
| F09 | `capitulo-modificado` en índice y cabecera solo si el backend dice `modificado`; selector de versión con `motivo` y capítulos cambiados, que abre la anterior entera |
| F10 | «Hechos de este capítulo» con `listarHechos`, panel de cambio que pide el análisis de impacto y solo regenera al confirmar; 409 con enlace a la generación viva (2 intentos en rojo: un fichero sin reescribir y una aserción ambigua) |
| F11 | Seleccionar texto dentro de `capitulo-texto` ofrece «Pedir cambio»; envía `fragmento` y muestra el `hecho_candidato` con la misma confirmación. Una selección que se sale del texto del capítulo no cuenta |
| F12 | «Descargar PDF» con `exportarVersion`: enlace a `descargarExport` si está disponible, «Volver a comprobar» sin sondeo si está en curso, aviso si falló, y la paridad si viene |
| F13 | Prueba que lee la tabla CL-03 de `spec1.md` y comprueba cada fila (número, padre, atributos, contenido); `lectura.css` con `@media print` (CL-04) y los controles marcados con `data-controles` |
| F14 | Formulario completo del brief serializado como `BriefNovelaParcial`; «Crear y generar» solo con `valido: true` vigente; `crearNovela` con el estrechamiento a `BriefNovela` y luego `lanzarGeneracion`; lista de novelas (2 intentos en rojo: tipos con `default` obligatorios y una aserción que contaba el sondeo del progreso) |
| F15 | Datos faltantes junto a su campo y en un resumen, contradicciones, fragmentos descartados y hechos extraídos; red de seguridad para `400` y `422`, con el `detail` en la cabecera del formulario |
| F16 | `frontend/README.md` con el arranque conjunto; `npm run build` en verde; el servidor de desarrollo sirve `/` y la lectura, y el proxy `/api` llega a `127.0.0.1:8000` (sin backend: `ECONNREFUSED`, como se espera) |

## Arranque conjunto

Detalle en `frontend/README.md`. Resumen:

1. **Backend**, en `127.0.0.1:8000` con un solo worker (`specs/plan1.md` § 9):
   `uv run --env-file ../.env uvicorn app.main:app --reload --port 8000` desde `backend/`, con
   `STORYMAKER_LECTURA_URL=http://127.0.0.1:5173` en `.env`.
2. **Frontend**, en `127.0.0.1:5173`: `cd frontend && npm install && npm run dev`. El proxy
   de Vite lleva `/api/*` a `http://127.0.0.1:8000/*`.
3. Opcional, para `render_visual`: `npx -y @playwright/mcp --port 8931`.
4. Comprobación: `http://127.0.0.1:5173/api/salud` devuelve el JSON de `GET /salud`.

**No probado contra el backend real**: `backend/` no existe todavía en esta rama. Todo lo
anterior está verificado con respuestas construidas a partir de los ejemplos del contrato. La
integración real es el P49 de `plan1.md`.

## Uso del browser MCP

**Configuración.** Claude Code lee los servidores MCP de ámbito de proyecto en **`.mcp.json`**
en la raíz del repositorio, no en `.claude/mcp.json`. Lo comprobé con `claude mcp --help`:
`list` y `get` hablan de «servidores de `.mcp.json`», y `claude mcp add -s project` escribió
en ese fichero. **`.mcp.json` es, por tanto, el «`.claude/mcp.json` o equivalente» del
alcance.** Declara el servidor `playwright` (`@playwright/mcp@0.0.82`, versión fijada) por
stdio, con `cmd /c npx` porque en Windows `npx` no se lanza directamente. Es otro uso distinto
del paso 3 del arranque conjunto: aquel es el Playwright MCP por HTTP que usa el backend para
`render_visual`, y este es el navegador del agente de desarrollo.

**Navegador: Edge.** Al reiniciar, el servidor aparecía cargado, pero `browser_navigate`
fallaba con «Chromium distribution 'chrome' is not found»: `@playwright/mcp` usa por defecto
el canal `chrome` y en esta máquina no hay Google Chrome, pero sí Microsoft Edge 153. Por
decisión del desarrollador se añade `--browser msedge` a los argumentos (opción válida en la
0.0.82, comprobado con `--help`). No descarga ningún navegador.

**Rediseño visual, dirección 1 «encuadernación clásica»** (elegida por el desarrollador).
Tokens en `src/shared/ui/tema.css`, importado desde `app/estilos.css`. Lo decorativo global
va en `@media screen`, para que la impresión, y con ella el PDF, no cambie. Sin backend, las
respuestas de `/api` se interceptaron solo en el navegador del MCP (`page.route`), con
datos de prueba, para ver los estados que pinta el contrato. Nada de eso entra en el código.
Capturas en `.playwright-mcp/`, sin versionar.

*Entrevista*, a 1280×900 y a 390×844:

- **Inspeccionado:** formulario vacío; «Validar» y la lista de novelas con el proxy caído
  (`500`, `AvisoProblema`); validación con datos faltantes, contradicción, fragmento
  descartado y hecho extraído; filas de elemento personalizado y de texto libre; foco con
  teclado en campo y botón; ancho del documento en móvil.
- **Detectado antes:**
  - El enlace de la cabecera usaba el azul del navegador.
  - Los `fieldset`, los botones y los controles eran los del sistema, sin foco propio.
  - Todos los campos iban a una columna de 46rem en escritorio.
  - El dato faltante solo se distinguía por el color del texto.
- **Detectado durante:**
  - El fondo de la `legend` tapaba el papel por encima del filete y dejaba una muesca
    clara. Se quitó, porque el navegador ya corta el borde detrás de la leyenda.
  - El `input` con dato faltante no se teñía y el `select` sí, porque ganaba el estilo
    global por orden de carga. Se subió la especificidad.
- **Cambiado:**
  - Cabecera en versalitas burdeos sobre doble filete dorado, y título con fleurón
    decorativo (`content: '❦' / ''`, sin texto para el lector de pantalla).
  - Cada grupo es una hoja con filete superior burdeos, y en escritorio los campos cortos
    van a dos columnas.
  - Dato faltante con barra lateral y campo marcado. Resultado de la validación por colores
    de estado.
  - «Validar» y «Crear y generar» rellenos; los botones secundarios, con filete burdeos.
  - En móvil, acciones a todo el ancho.
  - Sin desbordamiento horizontal a 390 px.
  - Contrastes medidos: texto de 7,6:1 a 14,2:1; borde de control, 3,7:1. El dorado
    (2,8:1) solo aparece en filetes y adornos.

*Progreso*, a 1280×900 y a 390×844:

- **Inspeccionado:** con el proxy caído (`AvisoProblema`), y con los ejemplos `enCurso` y
  `detenida` de `obtenerGeneracion` de `openapi.yaml`. A `detenida` se le añadió
  `version_resultante` para ver el enlace a la lectura.
- **Detectado:**
  - La página no tenía hoja propia, así que la `dl` salía con la sangría del navegador.
  - Una hoja de página con selectores `main > …` o `fieldset` sueltos se aplica también a
    las otras páginas, porque en la SPA el CSS sigue cargado al navegar.
- **Cambiado:**
  - `progreso.css` pinta los datos como un colofón: hoja con nombres en versalitas y
    separadores punteados. Estado y capítulos aceptados van en tamaño de titular.
  - «Leer la versión N» va como botón relleno.
  - En móvil, cada dato va bajo su nombre.
  - El `main` de progreso y el de la entrevista llevan una clase de página
    (`pagina-progreso`, `pagina-entrevista`) que acota sus selectores. Es solo una clase: no
    toca ningún `data-testid` ni ningún texto.

*Lectura*, a 1280×900 y a 390×844:

- **Inspeccionado:**
  - Una versión 2 de prueba con diez capítulos, los capítulos 3 y 7 modificados, textos
    largos y cortos, ficha, dos versiones y un hecho en el capítulo 3.
  - El flujo de cambio completo: hechos del capítulo → «Cambiar» → panel → análisis de
    impacto.
  - El PDF disponible con paridad comprobada, y la lectura con el proxy caído
    (`data-estado="error"`).
  - Medida de línea: unos 72 caracteres a 19 px en escritorio y 17 px en móvil.
  - La emulación `print`.
- **Detectado:**
  - El patrón `**/api/**` de `page.route` atrapaba también los módulos de Vite
    (`/src/shared/api/index.ts`) y la app no cargaba. Hay que interceptar
    `http://127.0.0.1:5173/api/**`. Es un aviso para quien vuelva a inspeccionar así.
  - La capitular flotaba fuera de los capítulos de una línea y empujaba los controles.
    Ahora se contiene con `display: flow-root`, que no añade nada al texto.
  - En móvil, el `select` de versión, con el motivo largo en la opción, desbordaba 52 px en
    horizontal. Se le quitó la anchura mínima.
  - En móvil, el numeral «VIII.» del índice se salía por la izquierda.
  - La portada pinta la ocasión con el valor del enum (`cumpleanos`). Es texto del
    contrato, no de estilo, así que no se tocó. Queda para la integración.
- **Cambiado:**
  - La portada es una cubierta con doble marco dorado, título burdeos, fleurón y
    dedicatoria en cursiva firmada en versalitas.
  - El índice va en numerales romanos con separadores punteados, y la ficha, en
    versalitas bajo un filete doble.
  - Los capítulos van en la medida de lectura (38rem), con interlineado de 1,75,
    capitular burdeos y fleurón entre capítulos.
  - La marca de cambios es una etiqueta en versalitas con los colores de aviso.
  - Los controles del capítulo quedan discretos bajo un filete. La petición de cambio es
    una hoja que sube del pie, en la medida del texto.
  - La barra de versión y PDF va en una línea.
  - Sin desbordamiento horizontal en ninguna pantalla.
- **Impresión:** el bloque `@media print` y las reglas base de portada, capítulo, texto y
  marca siguen idénticos (comprobado contra `HEAD`). Todo lo nuevo va en `@media screen`, o
  en controles con `data-controles`, que no se imprimen.
  - Con `print` emulado: texto a 16 px, título en negrita, sin capitular, sin marco y con
    los trece controles ocultos, igual que antes.
  - Los tokens sí cambian la tinta y el papel base, que pasan de `#1f1b16` sobre `#fbf8f3`
    a `#2b2118` sobre `#f8f3ea`. Es una diferencia mínima, que el P49 del backend verá en
    el render real.

**Interceptaciones olvidadas.** Tras la inspección, el navegador del MCP seguía mostrando la
novela de prueba sin backend, y parecía que la aplicación traía datos de ejemplo. No los trae:

- `src/` no importa nada de `tests/`, lo que ya vigila CA-14.
- El bundle de `npm run build` no contiene ni el título ni el identificador de prueba.
- La única coincidencia en `src/` es un comentario JSDoc de `shared/api/schema.d.ts`, que
  `gen:api` copia del ejemplo de `BriefNovela` de `openapi.yaml`. No es un dato en tiempo
  de ejecución.

La causa eran las rutas de `page.route` que quedaron registradas en la pestaña. Se quitaron
con `page.unrouteAll()`. Sin ellas, la lectura queda en `data-estado="error"` y la lista de
novelas de la entrevista muestra su `AvisoProblema`. **Regla para la próxima inspección:**
cerrar cada sesión con `page.unrouteAll()`, o cerrar la pestaña.

## Para la sesión del backend

- **RF-INTAKE-01 choca con el schema** (G1). Resuelto en el contrato 1.1.0 (TO-037) e
  incorporado.
- **Contrato de lectura**: el frontend implementa `spec1.md` § 4.4 tal cual, y su propuesta
  provisional queda retirada. Para el P49 del backend: la lectura se sirve en
  `http://127.0.0.1:5173`, que es el valor de `STORYMAKER_LECTURA_URL`.

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
  arreglo va al contrato —brief parcial para `validarBrief`, ya en 1.1.0 (TO-037)— y el
  frontend conserva una red de seguridad: pinta `datos_faltantes` venga en la respuesta que
  venga, y el `detail` de un `422` que no los traiga.
- **Del brief parcial al completo sin `as`**: para llamar a `crearNovela`, un
  estrechamiento de tipo que solo comprueba la presencia de los campos obligatorios del
  schema, y solo tras un `valido: true` del backend. Es el puente de tipos entre las dos
  formas de TO-037, no una regla de dominio.
- **La propuesta de `data-testid` del frontend se retira** en favor de `spec1.md` § 4.4.
  Diferían los nombres (`dedicatoria` → `portada-dedicatoria`, `marca-modificado` →
  `capitulo-modificado`), la forma (el número va en `data-capitulo`, no en el
  identificador) y faltaba la señal `data-estado`.
- **La impresión se prueba sobre la hoja, no sobre el render**: `jsdom` no evalúa
  `@media print`. El render impreso real lo comprueba el P49 del backend con Playwright.
- **Puerto del frontend fijo en 5173** (`strictPort`), para que `STORYMAKER_LECTURA_URL`
  no cambie entre arranques.
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
- **FA-01** (F01, decidido por el agente — revisar): se instalan en F01 todas las dependencias aprobadas, más tres que son parte de ellas y no añaden nada: `@testing-library/dom` (dependencia par de Testing Library) y los tipos `@types/react`, `@types/react-dom` y `@types/node`.
- **FA-02** (F02, decidido por el agente — revisar): `gen:api` usa un script propio (`scripts/generar-api.mjs`) sobre la API de `openapi-typescript` en vez de su CLI, para que la prueba de CA-01 compare con la misma función que escribe el fichero.
- **FA-03** (F05, decidido por el agente — revisar): los constructores de ruta viven en `shared/config/rutas.ts` (la skill FSD pone ahí las constantes de ruta), para que `AvisoProblema` de `shared/ui` enlace al progreso sin importar de `app/`. Un cuerpo de error que no es `problem+json` —un proxy caído— se pinta como `error-interno` con su status real, sin inventar detalle.
- **FA-04** (F10, decidido por el agente — revisar): el `oneOf` de `NuevaSolicitudCambio` se genera como `& (unknown | unknown)`, que no restringe nada. La regla «exactamente uno de `hecho_id` o `fragmento`» la garantiza el tipo `OrigenCambio` de `pages/lectura/model/`, no el tipo generado. No es insuficiencia del contrato: el backend lo valida.
- **FA-05** (F13, decidido por el agente — revisar): la prueba del contrato de lectura **lee la tabla CL-03 de `specs/spec1.md`** en cada ejecución en vez de copiarla, y falla si la tabla gana o pierde una fila que la prueba no cubra. Los controles interactivos llevan el atributo `data-controles`, que es lo que la hoja de impresión oculta. No es un `data-testid` y no forma parte del contrato de lectura.
- **FA-06** (F14, decidido por el agente — revisar): los tipos se generan con `defaultNonNullable: false`. `openapi-typescript` 7 hace obligatorio por defecto todo campo con `default` —`ElementoPersonalizado.origen`, `VozNarrativa.*`, `Capitulo.modificado`—, y en un cuerpo de petición eso contradice el contrato: el campo se puede omitir y lo pone el backend. En las respuestas, el frontend trata esos campos como opcionales.
- **Browser MCP del agente en `.mcp.json`** (decidido por el desarrollador, camino (a) del
  rediseño visual): el alcance y el layout de `CLAUDE.md` piden `.claude/mcp.json`, pero
  Claude Code lee los servidores de proyecto en `.mcp.json`, en la raíz (comprobado con
  `claude mcp --help`). Se crea ese fichero con `@playwright/mcp@0.0.82` fijado. Al integrar,
  el layout de `CLAUDE.md` debe decir `.mcp.json` en vez de `.claude/mcp.json ▸ previsto`.
  Es una dependencia de herramienta, no de la aplicación: no entra en `package.json`.
  Lanza **Edge** (`--browser msedge`), no Chrome, porque la máquina de desarrollo no tiene
  Chrome instalado (decidido por el desarrollador frente a instalar Chrome o el Chromium de
  Playwright).
