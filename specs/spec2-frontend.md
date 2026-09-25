---
estado: aprobada
aprobada-por: Bruno Cruz
fecha: 2026-09-24
contrato: specs/openapi.yaml 1.1.0 y specs/spec1.md § 4.4 (contrato de lectura)
modificada: 2026-09-24 · ajuste al commit 7d389a7 del backend, pedido por el desarrollador
---

# Spec 2 — Frontend de la demo

Mini-spec del frontend de la demo de storyMaker. Aquí no se redefine nada: el vocabulario
es el de `docs/definitions.md`, y la forma de cada dato es la de `specs/openapi.yaml`, que
**no se modifica desde esta spec**.

> **Estado: aprobada** el 2026-09-24 por el desarrollador, con las respuestas de § 7. No
> hay código hasta que `specs/plan2-frontend.md` esté aprobado (`CLAUDE.md` § Ciclo de
> cambio).
>
> **Ajustada el 2026-09-24 a petición del desarrollador**, al incorporar el commit `7d389a7`
> del backend: `validarBrief` recibe `BriefNovelaParcial` (contrato 1.1.0, TO-037), y el
> contrato de lectura deja de ser propuesta de esta spec y pasa a ser `spec1.md` § 4.4, que
> el frontend implementa tal cual. Afecta a § 2, § 4 P1, § 4 «Contrato de lectura», § 5 y
> § 7.

---

## 1. Problema

El backend v1 (`specs/spec1.md`) se construye en paralelo contra `specs/openapi.yaml`, y la
demo necesita recorrer el ciclo entero desde el navegador: encargar una novela, ver cómo se
genera, leerla, pedir un cambio y descargarla. Hoy `frontend/` no existe.

## 2. Alcance

**Dentro.** Seis pantallas o funciones, todas sobre operaciones que ya están en el contrato:

| # | Qué | Operaciones del contrato | Alcance § |
| --- | --- | --- | --- |
| P1 | **Entrevista**: formulario del brief y texto libre | `validarBrief` (`BriefNovelaParcial`), `crearNovela` (`BriefNovela`), `lanzarGeneracion`, `listarNovelas` | §1 |
| P2 | **Progreso** de una generación, inicial o dirigida | `obtenerGeneracion`, `listarGeneraciones` | §3, §6 |
| P3 | **Lectura**: índice navegable, portada con dedicatoria, ficha de personajes y lugares enlazada a sus capítulos | `obtenerNovela`, `obtenerVersion`, `listarCapitulos`, `obtenerPortada`, `obtenerFicha` | §2 |
| P4 | **Petición de cambio** desde la lectura, por fragmento o por hecho, con confirmación | `listarHechos`, `crearSolicitudCambio`, `confirmarSolicitudCambio` | §2 |
| P5 | **Capítulos modificados** respecto a la versión anterior, y acceso a versiones anteriores | `listarVersiones`, `obtenerVersion` | §2 |
| P6 | **Descarga del PDF** de la versión leída | `exportarVersion`, `descargarExport` | §2 |

**Fuera.** El entrevistador conversacional (RF-INTAKE-06, post-demo); SSE; autenticación;
`obtenerSalud` más allá de mostrarla si responde; edición del hecho candidato propuesto (el
contrato solo permite confirmarlo); descartar una solicitud (no hay operación); la página
de «novedades» del PDF, que maqueta el backend; y cualquier estilo más allá de legible.

## 3. Stack y reglas

- **React 18 + TypeScript estricto**, sin `any`; **Vite**; **TanStack Query** para todo el
  estado de servidor.
- **Feature-Sliced Design v2.1** con `app/`, `pages/` y `shared/`. Sin `widgets/`. Sin
  `entities/` ni `features/` salvo que la regla de extracción de la skill se cumpla.
- **Cliente tipado generado desde `specs/openapi.yaml`** en `frontend/src/shared/api/`. Los
  tipos no se escriben a mano: se regeneran con un comando, y una prueba falla si el
  fichero generado no coincide con el contrato.
- **Ninguna lógica de dominio en el frontend.** El frontend muestra lo que el backend
  decide: el sondeo se para por `es_terminal`, no por el nombre del estado; la marca
  `modificado` se lee, no se calcula; los datos faltantes y las contradicciones se pintan,
  no se detectan; el análisis de impacto se muestra, no se deduce.
- **Pruebas sin backend.** Las respuestas de prueba se construyen a partir de los ejemplos
  de `specs/openapi.yaml` y viven **solo en `frontend/tests/`**. Donde el contrato no trae
  ejemplo, se construyen en `tests/` tipadas con los tipos generados (`satisfies`), de modo
  que `typecheck` rompe si se apartan del contrato. Ningún fichero de `src/` importa de
  `tests/`, y una prueba lo comprueba.
- **Sin cifras sueltas.** El intervalo de sondeo lo da el recurso `Generacion`. El export
  no trae intervalo, así que no se sondea: el lector vuelve a comprobar con un botón.

## 4. Comportamiento

### Rutas

| Ruta | Página | Qué hace |
| --- | --- | --- |
| `/` | `entrevista` | Formulario, y debajo las novelas existentes (`listarNovelas`) con enlace a su lectura o a su generación |
| `/novelas/:novel_id/generaciones/:generacion_id` | `progreso` | Sondea `obtenerGeneracion` |
| `/novelas/:novel_id` | `lectura` | Redirige al progreso de la generación no terminal (`es_terminal: false`), inicial o dirigida, aunque haya versión vigente; si no la hay, a la versión vigente; sin versión vigente, a la última generación (RI-043) |
| `/novelas/:novel_id/versiones/:version` | `lectura` | La novela en esa versión; cada capítulo en el ancla `#capitulo-N` |

El backend llega por un **proxy de Vite** en `/api` → `http://127.0.0.1:8000`, así que el
frontend no depende de CORS y el backend no se toca.

### P1 · Entrevista

1. El formulario cubre todos los campos de `BriefNovela`. Las listas —rasgos, recuerdos,
   temas excluidos, palabras prohibidas, reglas del mundo— se escriben una por línea; los
   `ElementoPersonalizado` y los `TextoLibre` se añaden y quitan como filas. **El
   formulario se serializa siempre como `BriefNovelaParcial`**, y un campo vacío no se
   envía: es el backend quien lo devuelve como `Dato faltante`.
2. **Validar** llama a `validarBrief` y pinta, sin reinterpretarlos: cada `DatoFaltante`
   junto a su campo con su `pregunta_reintento`, cada `ContradiccionBrief` con sus campos y
   su explicación, cada `FragmentoSospechoso` como descartado y los `hechos_extraidos`.
3. **Crear y generar** solo se habilita cuando la última validación devolvió
   `valido: true` y el formulario no ha cambiado desde entonces. Llama a `crearNovela` con
   ese mismo brief como `BriefNovela` y, con el `201`, a `lanzarGeneracion`, y navega al
   progreso. El paso de parcial a completo es un **estrechamiento de tipo** que comprueba
   solo la presencia de los campos que el schema exige, para que TypeScript lo acepte sin
   `as`; no decide nada que no haya decidido ya `valido: true`, y si falla se pinta como
   error, no se corrige.
4. Un `400 brief-invalido` pinta sus `contradicciones` igual que el paso 2. **Red de
   seguridad** (G1): `datos_faltantes` se pintan junto a su campo vengan en la respuesta que
   vengan —`200`, `400` o `422`—, y un `422` que no los traiga pinta su `detail` en la
   cabecera del formulario. Todo otro error se pinta desde su `Problema`: `title`, `detail` y, si viene, el
   enlace a la `generacion_id` o la `traza_langfuse_id`.

### P2 · Progreso

1. Sondea `obtenerGeneracion` cada `intervalo_sondeo_segundos` y **deja de sondear cuando
   `es_terminal` es `true`**.
2. Muestra estado, capítulo actual, aceptados sobre total, intentos del capítulo actual,
   checkpoint, tokens y coste; en una dirigida, `capitulos_a_regenerar`.
3. En `Publicada`, enlaza a la lectura de `version_resultante`. En `Detenida`, muestra
   `detenida_por` tal cual, sin enlace a lectura nueva.

### P3 · Lectura

1. **Portada** de `obtenerPortada`: título, destinatario, ocasión, dedicatoria y firma.
2. **Índice** de `obtenerVersion`: una entrada por `CapituloIndice`, enlazada a su ancla.
3. **Capítulos** de `listarCapitulos`, en orden, con título y texto.
4. **Ficha** de `obtenerFicha`: personajes y lugares con su descripción y un enlace a cada
   capítulo de su lista `capitulos`.

### P4 · Petición de cambio

1. **Por fragmento.** Al seleccionar texto dentro de un capítulo aparece «Pedir cambio»; el
   panel muestra el fragmento, pide el `enunciado_nuevo` y envía `crearSolicitudCambio` con
   `fragmento` y `capitulo_origen` = el capítulo donde está la selección.
2. **Por hecho.** Cada capítulo ofrece «Hechos de este capítulo» (`listarHechos` con
   `capitulo`); elegir uno pide el `enunciado_nuevo` y envía con `hecho_id`.
3. **Confirmación, en los dos caminos.** La respuesta se muestra sin tocar: el
   `hecho_candidato` o el `hecho_afectado`, y `analisis_impacto.capitulos_afectados` como
   enlaces. **Nada se regenera hasta pulsar «Confirmar»**, que llama a
   `confirmarSolicitudCambio` y navega al progreso de la generación dirigida. «Cancelar»
   cierra el panel.
4. Un `409 generacion-en-curso` se muestra con enlace al progreso de su `generacion_id`.

### P5 · Capítulos modificados

1. Cada entrada del índice y cada cabecera de capítulo con `modificado: true` lleva la marca
   «Modificado en esta versión».
2. Un selector de versión (`listarVersiones`) muestra cada versión con su `motivo` y sus
   `capitulos_modificados`, y navega a ella: **la anterior sigue siendo legible entera**.

### P6 · PDF

«Descargar PDF» llama a `exportarVersion`. Con `disponible`, ofrece el enlace a
`descargarExport` de esa versión; con `en-curso`, dice que se está generando y ofrece
«Volver a comprobar»; con `fallido`, lo dice. Muestra `paridad_pdf_web` si viene.

### Contrato de lectura (`spec1.md` § 4.4)

`render_visual` y el export del backend abren **este** render con Playwright. Lo que
necesitan está fijado en **`specs/spec1.md` § 4.4, CL-01…CL-05**, y el frontend lo implementa
**tal cual**. La lista no se copia aquí, porque copiarla sería tener dos. Cambiarla es cambiar
`spec1.md`. Lo que eso obliga a hacer en la página `lectura`:

- **CL-01.** La ruta `/novelas/:novel_id/versiones/:version` pinta **la versión entera en un
  solo documento**: portada, índice, ficha y todos los capítulos a la vez en el DOM. Ningún
  capítulo se carga bajo demanda.
- **CL-02.** El elemento raíz `lectura` lleva `data-estado` = `cargando`, `lista` o `error`,
  y `lista` solo cuando han llegado versión, capítulos, portada y ficha.
- **CL-03.** Todos los `data-testid` de la tabla, con sus atributos y su anidamiento.
  `capitulo-texto` contiene **solo** `Capitulo.texto`: los controles de petición de cambio
  van fuera de él, dentro del `capitulo`.
- **CL-04.** Hoja `@media print`: todos los `capitulo` visibles, cada uno en página nueva, y
  los controles interactivos —navegación, selector de versión, petición de cambio, PDF— sin
  imprimir.

## 5. Criterios de aceptación

Todos se comprueban con `npm run test` y `npm run typecheck` en `frontend/`, sin backend.

| # | Dado / Cuando / Entonces |
| --- | --- |
| CA-01 | *Dado* `specs/openapi.yaml`, *cuando* se regenera el cliente, *entonces* el fichero generado coincide byte a byte con el commiteado |
| CA-02 | *Dado* un formulario sin nombre, *cuando* se valida, *entonces* se envía un `BriefNovelaParcial` sin `destinatario.nombre`, la `pregunta_reintento` del `DatoFaltante` del `200` aparece junto a ese campo y «Crear y generar» sigue deshabilitado. *Dado* un `422` sin `datos_faltantes`, *entonces* su `detail` aparece en la cabecera del formulario |
| CA-03 | *Dado* un texto libre con un fragmento sospechoso, *cuando* se valida, *entonces* aparece marcado como descartado |
| CA-04 | *Dado* un brief válido (el ejemplo del contrato), *cuando* se crea y genera, *entonces* se llaman `crearNovela` y `lanzarGeneracion` en ese orden y se navega al progreso |
| CA-05 | *Dado* el ejemplo `enCurso`, *cuando* se abre el progreso, *entonces* se muestra 3 de 10 y se vuelve a pedir; *dado* el ejemplo `detenida`, *entonces* se muestra `limite-de-intentos-agotado` y no se vuelve a pedir |
| CA-06 | *Dado* una versión con diez capítulos, *cuando* se abre la lectura, *entonces* hay diez `indice-entrada` con su `data-capitulo`, cada una enlaza a `#capitulo-N`, y diez `capitulo` con `id="capitulo-N"` |
| CA-07 | *Dado* una ficha con un personaje en los capítulos 2 y 7, *entonces* hay enlaces a `#capitulo-2` y `#capitulo-7` |
| CA-08 | *Dado* una portada, *entonces* `portada-titulo` y `portada-dedicatoria` contienen `Portada.titulo` y `Dedicatoria.texto`, y la firma se muestra en la portada |
| CA-09 | *Dado* el ejemplo `porFragmento`, *cuando* el lector selecciona texto del capítulo 3 y pide el cambio, *entonces* se envía ese cuerpo, se muestran el hecho candidato y los capítulos afectados, y **no** se llama a `confirmarSolicitudCambio` hasta pulsar «Confirmar» |
| CA-10 | *Dado* el ejemplo `porHecho`, *cuando* el lector elige un hecho del capítulo 3, *entonces* se envía ese cuerpo y se exige la misma confirmación |
| CA-11 | *Dado* un `409 generacion-en-curso` (el ejemplo del contrato), *entonces* se muestra con enlace a su `generacion_id` |
| CA-12 | *Dado* una versión 2 con los capítulos 3 y 7 `modificado`, *entonces* solo esas dos `indice-entrada` y esos dos `capitulo` contienen `capitulo-modificado`, y el selector permite abrir la versión 1 |
| CA-13 | *Dado* un export `disponible`, *entonces* hay un enlace a `/api/novelas/{id}/versiones/{v}/export`; *dado* `en-curso`, *entonces* hay «Volver a comprobar» y no hay sondeo |
| CA-14 | Ningún fichero de `src/` importa de `tests/`, ni usa `any`, ni importa de una capa superior o de otra página |
| CA-15 | *Dado* una versión de diez capítulos con ficha, *cuando* carga, *entonces* `lectura` pasa de `data-estado="cargando"` a `lista` con `data-novel-id` y `data-version`, y cada fila de la tabla CL-03 de `spec1.md` se cumple en número, anidamiento, atributos y contenido; *dado* un `404`, *entonces* `data-estado="error"` |
| CA-16 | La hoja de estilos de la lectura tiene reglas `@media print` que muestran todo `capitulo`, lo empiezan en página nueva y ocultan los controles interactivos (CL-04) |

## 6. Impacto

**Ontología, esquema y API: ninguno desde esta spec.** No se añade clase, estado ni campo,
y ni `specs/openapi.yaml` ni `spec1.md` se tocan desde aquí: el cambio a 1.1.0 y el contrato
de lectura los hizo el backend (TO-037). **Preguntas de competencia que la demo hace visibles**: 1,
3, 4, 11, 20, 21, 22, 28, 29 y 32 (`docs/definitions.md` § Preguntas de competencia).

**Dependencias nuevas** (regla 6), todas en `frontend/package.json` y ninguna de servidor:

| Dependencia | Por qué |
| --- | --- |
| `react`, `react-dom`, `vite`, `@vitejs/plugin-react`, `typescript` | El stack fijado |
| `@tanstack/react-query` | El stack fijado para el estado de servidor |
| `react-router-dom` | Las rutas de § 4; es una librería de cliente, no un framework de servidor |
| `openapi-typescript` (dev) | Genera los tipos desde `specs/openapi.yaml` |
| `openapi-fetch` | Cliente `fetch` de ~6 kB tipado por esos tipos; las funciones salen del contrato |
| `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom` (dev) | Pruebas de componente sin navegador |
| `yaml` (dev) | Leer los ejemplos de `specs/openapi.yaml` desde `tests/` |

Sin MSW: las respuestas de prueba se sirven con un `fetch` de prueba inyectado en el
cliente, que vive en `tests/`.

## 7. Preguntas de grill

Tres, con la opción que recomendaba en primer lugar y **la respuesta del desarrollador**
debajo de cada una.

**G1 · El contrato no deja validar un brief al que le falta un campo obligatorio.**
RF-INTAKE-01 dice que un brief sin `destinatario.nombre` devuelve `200` con un
`DatoFaltante`. Pero `validarBrief` recibe un `BriefNovela`, que exige `nombre` y `edad`
(`required`, `minLength: 1`): omitirlo o mandarlo vacío es un `422 peticion-invalida`, cuyo
`Problema` solo trae `detail` en prosa. Para los campos obligatorios, la entrevista **no
puede** señalar el faltante junto a su campo con lo que dice el contrato. No lo cambio
desde aquí.

- **(a) Recomendada.** El frontend pinta `datos_faltantes` venga de donde venga —el `200`,
  el `400` o un `422` que los traiga, porque `Problema` admite el campo— y, si un `422` no
  los trae, pinta su `detail` en la cabecera del formulario. Funciona con cualquier
  decisión del backend y no toca el contrato. Además, se avisa a la sesión del backend de la
  contradicción entre RF-INTAKE-01 y el schema.
- (b) Se pide cambiar el contrato: `validarBrief` recibe un `BriefNovela` parcial. Es lo
  correcto a largo plazo, pero cambia `spec1.md` y el backend, y no es de esta sesión.
- (c) El frontend comprueba los obligatorios antes de enviar. Es lógica de dominio en el
  frontend y duplica lo que decide el backend: la descarto.

> **Respuesta: (b), con (a) como red de seguridad.** La sesión del backend separa en el
> contrato un brief parcial para `validarBrief` —que responde `200` con `datos_faltantes`—
> del `BriefNovela` completo para `crearNovela`. Cuando avise de su commit se incorpora con
> `git merge Contexto-semilla-v2` y se regenera el cliente. El frontend sigue pintando
> `datos_faltantes` venga en la respuesta que venga y, si un `422` no los trae, su `detail`.

**G2 · ¿Tres páginas o dos?** `CLAUDE.md` § Persistencia, backend y frontend dice «Dos
páginas: `entrevista` y `lectura`», y tú pides además el progreso. El progreso se llega a
abrir desde dos sitios, la entrevista y la confirmación de un cambio en la lectura.

- **(a) Recomendada.** Tres páginas FSD: `entrevista`, `progreso` y `lectura`. Queda en
  «Para integrar» que `CLAUDE.md` pase a decir tres.
- (b) Dos páginas, y el progreso como `features/seguir-generacion` que montan las dos. Es
  más fiel al texto, pero crea una capa solo para no crear una página.

> **Respuesta: (a).** Tres páginas. `CLAUDE.md` no se toca desde aquí: el cambio queda en
> «Para integrar» de `specs/progreso-frontend.md`.

**G3 · ¿Apruebas las dependencias de § 6?** La regla 6 dice que el stack está cerrado, y
fuera de las fijadas añado `react-router-dom`, `openapi-fetch` y las de desarrollo.

- **(a) Recomendada.** Sí, tal como están.
- (b) Sin `react-router-dom`: navegación a mano por `location.hash`. Una dependencia menos,
  pero rutas con parámetros escritas y probadas a mano.

> **Respuesta: (a).** Dependencias aprobadas tal como están en § 6, y anotadas en «Para
> integrar».

**Contrato de lectura para Playwright.** Lo fija el backend en `specs/spec1.md` § 4.4.
**Incorporado el 2026-09-24** (commit `7d389a7`). La propuesta provisional de esta spec
—`dedicatoria`, `indice-capitulo-N`, `capitulo-N`, `ficha-enlace-capitulo-N`,
`marca-modificado`— **difería** en los nombres y en la forma (el número va en
`data-capitulo`, no en el identificador) y no tenía la señal `data-estado`. Queda sustituida
por la de `spec1.md`.

**G1, incorporado el 2026-09-24** en el mismo commit: `validarBrief` recibe
`BriefNovelaParcial` y `crearNovela` el `BriefNovela` completo. El `400 brief-invalido` ya
no trae `datos_faltantes` en su ejemplo; la red de seguridad se mantiene igual.
