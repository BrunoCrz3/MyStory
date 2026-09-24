# Browser MCP

Cómo usa este repositorio el servidor Playwright MCP: en el **gate**, como cliente guionizado
que decide si una versión se publica (`render_visual`, TO-026, TO-045), y **en desarrollo**,
con Claude Code contra el mismo servidor para inspeccionar lo que ninguna aserción prevé
(`architecture.md` § `render_visual` en el gate).

## El servidor

```bash
npx -y @playwright/mcp@0.0.82 --headless --isolated --browser msedge --host 127.0.0.1 --port 8931
```

- **Versión fijada** (0.0.82): las aserciones dependen del formato de texto de las tools, y una
  versión nueva puede cambiarlo sin avisar.
- `--isolated`: perfil en memoria, sin cookies ni caché entre ejecuciones.
- `--browser msedge`: el navegador de la máquina de desarrollo; en CI, `chrome` o el Chromium
  de `playwright install`.
- **La URL es `http://localhost:8931/mcp`, no `127.0.0.1`**: el servidor rechaza cualquier
  `Host` distinto de `localhost:8931` («Access is only allowed at localhost:8931»). Es lo que va
  en `PLAYWRIGHT_MCP_URL`.

Sin `PLAYWRIGHT_MCP_URL` y `STORYMAKER_LECTURA_URL`, el gate usa `SinNavegador`, que falla con
el motivo: **sin validación visual no se publica ninguna versión** (RNF-19, A-114).

## El gate: qué tool da la evidencia de cada aserción

El harness abre una sesión por versión, navega a `STORYMAKER_LECTURA_URL` +
`/novelas/{novel_id}/versiones/{version}` (CL-01), sondea `data-estado` hasta `lista` o
`error` dentro de `render_visual.espera_lista_segundos` (CL-02), extrae el DOM con **una**
llamada a `browser_evaluate` que usa los selectores de `app/versioning/lectura.py`, lee la
consola y cierra la pestaña. La lista es el dato `ASERCIONES` de
`app/versioning/render_visual.py`; una prueba falla si una aserción no declara su tool.

| Aserción | Tool MCP | Qué afirma |
| --- | --- | --- |
| `estado` | `browser_navigate`, `browser_evaluate` | CL-02: la raíz llega a `data-estado = lista` dentro de la espera; `error` falla |
| `selectores` | `browser_evaluate` | CL-03: cada `data-testid` con su cardinalidad, dentro de su contenedor, y la raíz con la novela y la versión pedidas |
| `indice` | `browser_evaluate` | Una entrada y un capítulo por capítulo, en orden y con su título; cada enlace resuelve a `#capitulo-{n}`; la marca de modificado es exacta |
| `ficha` | `browser_evaluate` | Cada personaje y lugar de la ficha, con un enlace a cada capítulo donde aparece, y cada enlace resuelve |
| `portada` | `browser_evaluate` | La portada muestra el título y la dedicatoria |
| `consola` | `browser_console_messages` (`level: error`) | Sin errores de consola, incluidas las excepciones no capturadas |
| `desbordes` | `browser_evaluate` | Ninguna caja del contrato ni el documento son más anchos que su contenedor |

**Enrutado del fallo** (A-80, O-10). Cada hallazgo se clasifica consultando antes la story
bible de la versión: si el dato **no está** —un capítulo sin título, una portada sin
dedicatoria—, es `datos` y nombra al rol dueño; si **está y no se pinta**, es `maquetacion`.
Los dos detienen la generación con la versión `rechazada` (A-113, A-116) y ninguno gasta
intentos de capítulo: el gate no reescribe capítulos. La clasificación y la tool quedan en el
detalle del score y en el audit log.

**Lo que se descubrió al guionizarlo**, y está recogido en el código:

- `browser_evaluate` devuelve el resultado como JSON bajo `### Result`, en texto, sin contenido
  estructurado.
- `browser_console_messages` da una cabecera con el total de errores; una excepción no
  capturada sale **sin** el prefijo `[ERROR]` que llevan los `console.error`. Filtrar por el
  prefijo la dejaba pasar: se cuenta por la cabecera.
- Una página sin favicon provoca un 404 a `/favicon.ico` que sale como error de consola. La
  página de prueba declara `<link rel="icon" href="data:,">`; el frontend tiene el suyo.

## Residuo declarado

Lo que ninguna aserción del gate caza y por qué:

- **Contraste, legibilidad y maquetación en móvil** (A-101). Ninguna tool da una medida
  determinista de «se lee bien»; `browser_take_screenshot` da la imagen, no el juicio.
- **Desbordes dentro de un contenedor con `overflow` distinto de `visible`**: un texto cortado
  por `overflow: hidden` no desborda la caja y la aserción no lo ve.
- **Capítulos plegados**: la página muestra los capítulos plegados en pantalla (CL-04), así que
  el texto de un capítulo no se mide visualmente; se comprueba que está en el DOM, y el export
  a PDF, con medios `print`, lo compara palabra a palabra (`paridad_pdf_web`).

## Inspección en desarrollo

Pendiente del paso de integración P49: se hace con Claude Code contra el mismo servidor y la
página `lectura` real del frontend, y aquí se anota qué se inspeccionó, qué se detectó y qué
cambió. Hasta entonces, las pruebas de `tests/versioning/test_render_visual.py` pintan la
página de prueba de `tests/fixtures/lectura/`, que cumple el contrato.
