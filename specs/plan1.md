---
estado: borrador
aprobada-por:
fecha: 2026-09-24
spec: specs/spec1.md
contrato: specs/openapi.yaml
progreso: specs/progreso.md
---

# Plan 1 — Backend v1, fases F0 a F5

Cómo se construye lo que especifica `specs/spec1.md` (aprobada el 2026-09-24 y modificada
el mismo día con TO-037) contra el contrato `specs/openapi.yaml` **1.1.0** y el contrato de
lectura de la spec § 4.4. **Un solo plan para las seis fases**,
escrito para que un agente lo ejecute de forma autónoma de principio a fin, paso a paso, y
pueda reanudarlo en frío desde `specs/progreso.md`.

> **Estado: borrador.** No se escribe una línea de código hasta que el desarrollador lo mueva
> a `aprobada` (`CLAUDE.md` § Ciclo de cambio). El agente que lo ejecute **comprueba el
> frontmatter antes del P01**, no de memoria, y se detiene si no dice `aprobada`.

---

## 0. Protocolo de ejecución

Esto es lo que el agente hace en **cada** paso, sin excepción. Es el contrato entre el plan y
quien lo ejecuta.

1. **Leer `specs/progreso.md`.** El paso actual es el que dice ahí, no el que se recuerde.
   Si el estado del paso es `pruebas-escritas`, se retoma desde el punto 4.
2. **Cargar la skill** que el paso nombra, antes de abrir ningún fichero de código.
3. **Escribir las pruebas del paso** («Pruebas primero»). Ejecutarlas y **comprobar que
   fallan por la razón correcta** —falta el módulo, falta la ruta, el valor no coincide—, no
   por un error de importación del propio test. Anotar en progreso `pruebas-escritas`.
4. **Escribir el código mínimo** que las pone en verde. Refactorizar con la suite en verde.
5. **Ejecutar el criterio «Hecho cuando»** del paso **y** el invariante global (§ 0.1).
6. **Actualizar `specs/progreso.md`**: paso cerrado, lo hecho, decisiones nuevas, siguiente
   paso. Y en el mismo commit, los dos rastros si el paso tomó una decisión (§ 0.3).
7. **Commit** pequeño, en imperativo y con el número del paso: `P07: Añadir el pool en vuelo
   con admisión FIFO`. Un paso puede dar más de un commit; **nunca** un commit con dos pasos.

Se trabaja en una rama propia (`backend-v1`), nunca en `main`. Todos los comandos de este
plan se ejecutan **desde `backend/`** salvo que digan otra cosa.

### 0.1 Invariante global: el sistema siempre arranca

A partir del P01, **el criterio de cada paso incluye**, además del suyo:

```bash
uv run pytest            # la suite completa, verde; excluye -m real por configuración
uv run ruff check .
```

`tests/test_arranque.py` (P01) arranca la aplicación con su `lifespan` contra una base
temporal y pide `GET /salud` en cuanto esa ruta existe (P09). Si un paso lo pone en rojo, el
paso no está terminado. Ningún paso deja una migración a medias, una ruta declarada sin
implementar ni un import roto.

### 0.2 Qué cuenta como intento

Un **intento** es un ciclo «cambio de código → suite» que termina en rojo **después** de que
las pruebas del paso estén escritas. Los rojos esperados del punto 3 no cuentan. El contador
vive en progreso, se reinicia al cerrar el paso y **al tercer rojo el agente se detiene**
(§ 1, condición 3).

### 0.3 Qué decide el agente y cómo lo deja escrito

Todo lo que no sea una condición de parada lo decide el agente. Cada decisión que no esté ya
en este plan:

- entra en `specs/progreso.md` § Decisiones con un identificador `A-NN`, el paso y el porqué;
- si es de diseño —no una elección de nombre local—, deja **los dos rastros** de `CLAUDE.md`
  § Contexto semilla en el mismo commit: entrada `TO-NNN` en `docs/trade-offs.md` marcada
  **«decidido por el agente — revisar»** y entrada en `docs/registro-iteraciones.md`.

Las decisiones que este plan ya fija están en § 3 y se registran como **TO-036** con este
mismo commit.

---

## 1. Condiciones de parada

**Son cuatro y solo cuatro.** Ante cualquiera de ellas el agente deja escrito en
`specs/progreso.md` § Parada qué condición es, en qué paso, qué intentó y qué necesita del
desarrollador; hace commit de ese fichero, y **se detiene sin tocar nada más**.

| # | Condición | Cómo se detecta |
| --- | --- | --- |
| 1 | **La prueba de humo necesita la credencial del modelo y no está en el entorno** | `ANTHROPIC_API_KEY` vacía o ausente al llegar al P27. La suite normal **no** la necesita: sin ella, todo lo anterior al humo se hace igual |
| 2 | **Una decisión contradice la spec o exige cambiar `specs/openapi.yaml`** | Un criterio de la spec no se puede cumplir sin tocar el contrato, o el test de conformidad solo pasaría editando el fichero. También: cualquier cosa que exija un nombre nuevo en la ontología, porque la spec § 1.3 lo declara error |
| 3 | **La suite no se pone en verde tras 3 intentos en el mismo paso** | Contador de § 0.2 |
| 4 | **El coste acumulado de llamadas reales supera 40 USD** (unidad y tope confirmados por el desarrollador) | Contador en progreso § Coste real. **Es preventivo**: antes de lanzar una ejecución real, si `acumulado + coste.coste_maximo_novela` pasaría de 40, no se lanza y se para. El tope por novela de `config/thresholds.yaml` garantiza que ninguna ejecución individual se lo salte |

**`specs/openapi.yaml` no se edita nunca durante este plan**, ni para corregir una errata:
el frontend depende de él. Si una ruta no se puede expresar en FastAPI de forma que el
OpenAPI generado coincida, eso es la condición 2, no un motivo para ajustar el fichero.

**Lo que no es condición de parada**, y el agente resuelve y registra: una dependencia que no
instala a la primera, un umbral provisional que parece mal elegido, un fallo intermitente
—que se arregla, no se reintenta hasta que pase—, o que falte la página `lectura` del
frontend en F5 (§ 7, P49).

---

## 2. Dependencias

`CLAUDE.md` regla 6 cierra el stack. Estas son **todas** las que el plan introduce, con su
porqué; ninguna añade infraestructura de servidor. Cualquier otra es una decisión `A-NN` con
sus dos rastros.

| Paquete | Tipo | Paso | Por qué |
| --- | --- | --- | --- |
| `fastapi`, `uvicorn` | runtime | P01 | Stack cerrado |
| `pydantic` v2 | runtime | P01 | Stack cerrado: todo contrato de datos |
| `pyyaml` | runtime | P03 | Leer `config/*.yaml` |
| `anthropic` | runtime | P06 | Único cliente del proveedor; trae `httpx`, que es lo que usan los casetes |
| `langfuse` | runtime | P08 | Nombrado en `CLAUDE.md` § Requisitos técnicos |
| `playwright` | runtime | P48 | `page.pdf()` (TO-003) |
| `mcp` | runtime | P47 | Cliente del servidor Playwright MCP que exige TO-026 para `render_visual` |
| `pypdf` | runtime | P48 | **Leer** el PDF para `paridad_pdf_web`. No genera nada: el PDF sigue saliendo de Playwright, así que no se valida uno y se entrega otro |
| `pytest`, `pytest-cov` | dev | P01 | Suite y la cobertura mínima de `validadores.cobertura_tests_minima` |
| `hypothesis` | dev | P07 | Propiedades del pool, de la tabla de transiciones y del prefijo de aceptados |
| `jsonschema` | dev | P01 | Validar cada respuesta de la suite contra el schema aprobado (OpenAPI 3.1 es JSON Schema 2020-12) |
| `ruff`, `mypy`, `types-PyYAML` | dev | P01 | Lint, formato y el comprobador de tipos, en modo `strict` con el plugin de Pydantic |

**Descartadas a propósito**: `aiosqlite` (basta `sqlite3` de la biblioteca estándar en un
hilo, § 3 D-03), `pytest-asyncio` (el plugin de `anyio` ya viene con Starlette), `vcrpy`
(los casetes se graban y reproducen con `httpx.MockTransport`, que ya está), `schemathesis`,
`python-dotenv` (`uv run --env-file` carga el `.env`) y `pydantic-settings`.

**Toolchain fuera de Python**: Python 3.12, `uv`, `git`, Node 20+ para el servidor
Playwright MCP (F5) y el navegador de Playwright. Lean y TLC **no** se necesitan en este
plan (spec § 1.2 y RF-EXP-03).

---

## 3. Decisiones que fija este plan

Decididas por el agente al escribir el plan y registradas como TO-036. **D-01, D-08, D-09,
D-14 y D-22 ya las ha revisado el desarrollador**, y así lo dice cada fila; el resto sigue
en «revisar». Las que más pesan van primero.

| # | Decisión | Por qué |
| --- | --- | --- |
| **D-01** | **Resuelta con un cambio de contrato aprobado por el desarrollador (TO-037).** La validación acepta `BriefNovelaParcial` —los mismos campos que `BriefNovela`, todos opcionales, también los anidados— y responde `200` con los `Dato faltante` y las contradicciones; `crearNovela` sigue exigiendo el `BriefNovela` completo y un campo obligatorio ausente ahí es un `422`. La lectura del «campo vacío» que proponía el borrador **queda rechazada**. El contrato pasa a 1.1.0 | La spec pedía un `200` para un brief incompleto y el schema único lo hacía imposible; el frontend encontró el mismo fallo |
| D-02 | `pyproject.toml`, `uv.lock` y `tests/` viven en `backend/`; los comandos corren desde ahí. `config/` se lee desde la raíz del repositorio | Es lo que suponen los comandos de `CLAUDE.md` (`app.main:app`, `tests/guardrail`) |
| D-03 | SQLite con `sqlite3` de la biblioteca estándar, **una conexión por unidad de trabajo** salida de una única fábrica `conectar()`, y los repositorios síncronos llamados desde el servicio con `anyio.to_thread.run_sync` | RD-04 se cumple por construcción —no hay otra forma de abrir una conexión— y no añade `aiosqlite` |
| D-04 | La tabla de trabajos de RD-06 se llama `trabajo` y **es** el recurso `Generacion`: `generacion_id` es su clave. El estado del export vive en su propia tabla `exportacion` | Una tabla por concepto de la API; ninguna es clase de la ontología (TO-035) |
| D-05 | **Cada texto de capítulo aceptado es una fila nueva de `capitulo`**, y `version_capitulo (novel_id, version, numero) → capitulo_id` dice qué fila lee cada versión. Una regeneración solo crea filas para los capítulos reescritos | Los capítulos no afectados de la versión 2 **son la misma fila** que en la 1: el «idénticos byte a byte» de F4 sale por construcción, no por comparación |
| D-06 | Vigencia **semiabierta**: una fila es vigente en `v` si `version_desde ≤ v` y (`version_hasta` es nulo o `v < version_hasta`) | TO-028 no fijaba el borde, y un borde ambiguo es el mismo fallo silencioso que olvidar `version` |
| D-07 | La transacción de `Aceptar` la abre `process/` y pasa la conexión al `service.py` de cada dueña —`novel/`, `canon/`, `context/`, `policy/`—; ninguna escribe en tabla ajena | Una consolidación toca cinco features y tiene que ser una sola transacción (RF-CANON-01) sin romper la regla de importación |
| D-08 | **Aceptada por el desarrollador, con la condición de que no cree ciclo.** Las rutas `/novelas` son de `novel/` y usan `intake.service`. Al comprobar el ciclo aparecieron **cinco aristas más** que el plan necesitaba y el grafo no tenía: `novel → guardrail`, `context → intake`, `context → guardrail`, `quality → intake` y `versioning → intake`. **Comprobado sobre el grafo de `architecture.md` con las seis: es acíclico**, porque `intake/` y `guardrail/` solo importan de `commons/`. Ya están dibujadas en `architecture.md` | `Obra` es el recurso; la capa Invariante necesita el brief, el Anticontexto las palabras vetadas, `invencion_destinatario` el texto libre y la portada la dedicatoria. La prueba de importaciones del P02 hace fallar la suite si `intake/` o `guardrail/` llegan a importar otra feature |
| D-09 | **Aceptada por el desarrollador.** **`backend/app/prompts/` como tercera excepción declarada** junto a `mcp_server/` y `skills/`: un fichero por rol y el comando `sync`. Ya declarada en `architecture.md` § Anatomía y en el layout de `CLAUDE.md` | `CLAUDE.md` ya nombra `app.prompts.sync`; los prompts son memoria procedural que se versiona con git (TO-024) |
| D-10 | Sin credenciales de Langfuse, el trazador de producción **escribe cada span en el log estructurado** y `GET /salud` devuelve `degradado` | Spec § 2.4: perder observabilidad no cuesta una novela. No es un mock: es la misma implementación con un destino de respaldo, y el span existe (RNF-08) |
| D-11 | Lanzador `python -m app` que **se niega a escuchar fuera de la interfaz local** sin `--permitir-red` y fija un único worker; más un **cerrojo de instancia** sobre la base que hace fallar en voz alta al segundo proceso | RNF-12 y RF-PROC-03: dos procesos duplicarían el pool en silencio, y el README solo lo prohíbe; esto lo impide |
| D-12 | El `Snapshot` se **deriva** por SQL de los hechos vigentes y las promesas al cierre del capítulo; el `Resumen de capítulo` y el gancho los devuelve el `extractor` en la misma llamada | Un snapshot es derivado por definición, y así no se paga una llamada más por capítulo |
| D-13 | `invencion_destinatario` y `temas_excluidos` se piden al `judge` como campos estructurados adicionales de su única llamada, y la mitad programática de `invencion_destinatario` coteja cada afirmación contra el brief y el texto libre | Cero llamadas extra; el cotejo determinista es el que cuenta hasta cero |
| D-14 | **Aceptada por el desarrollador para la demo.** **La replanificación no se implementa**: no hay RF que la pida en la spec 1. Queda en la lista post-demo de `specs/progreso.md`. Un defecto clasificado sistémico se trata como reescritura y queda en el audit log con su clasificación | No construir lo que no está especificado; el dato queda para cuando haya spec |
| D-15 | `cierre_arco`: el gate corre la mitad programática (`continuidad.promesas_pendientes_al_cerrar`); la semántica es el criterio «Arco de la historia» de la rúbrica, puntuado por el `judge` en el último capítulo | `architecture.md` dice que el gate no llama al modelo |
| D-16 | `legibilidad` no se implementa | No tiene RF en la spec 1 |
| D-17 | Gate de publicación por fases: F1 corre `estructura_edicion` y `elementos_obligatorios`; F2 añade `cierre_arco`; F4, `regeneracion_fiel`; F5, `render_visual`. `lean_*` no corre mientras `formal.gate_activo` sea `false` | Cada fase publica con el gate más completo que puede ejecutar, y ninguna lo salta |
| D-18 | Los precios por modelo van a `config/thresholds.yaml` § `coste.precio_usd_por_millon`, **comprobados contra la documentación oficial** al escribirlos | `coste_usd` necesita una cifra y RNF-14 no deja escribirla en el código |
| D-19 | Hecho candidato desde un fragmento (RF-VER-07): similitud de Jaccard sobre tokens normalizados entre el fragmento y el `fragmento_soporte` de los hechos que **usa** el capítulo de origen; umbral en `config/thresholds.yaml` § `regeneracion.similitud_hecho_candidato`, provisional | Resuelve la pregunta abierta 4 de la spec sin embeddings (TO-015) |
| D-20 | Detección de `Fragmento sospechoso` por lista de patrones determinista y versionada en `intake/`. Residuo declarado: una inyección parafraseada la esquiva; la contiene igualmente que el texto libre entra siempre como datos | Auditable y sin modelo; la contención de verdad es RNF-09 |
| D-21 | Las listas `global` y `perfil` del guardrail son ficheros del repositorio en `guardrail/`; solo el nivel `novela` es tabla, con `novel_id` | RD-01: una lista global no pertenece a ninguna novela |
| D-22 | **Aceptada por el desarrollador.** El comando de export pasa a `python -m app.versioning.export <novel_id> <version>`; ya corregido en `CLAUDE.md` | Con varias novelas, la versión sola no identifica nada |
| D-23 | El planificador comparte el límite `orquestacion.max_intentos_capitulo` para su salida inválida; agotarlo detiene con `limite-de-intentos-agotado` | Todo reintento tiene límite (regla 14) y no hace falta una cifra nueva |
| D-24 | **Sustituida por la spec § 4.4 (TO-037)**: el contrato de lectura —ruta, señal de carga, selectores `data-testid` y hoja de impresión— ya no lo fija el plan sino la spec, y el frontend lo implementa tal cual. El backend lo lleva como dato en un único módulo (P46) y sus pruebas usan una página de prueba en `tests/fixtures/lectura/` que lo cumple | Era la única dependencia con el frontend fuera del OpenAPI, y una dependencia entre dos equipos no puede vivir en el plan de uno |

---

## 4. Estrategia de pruebas

### 4.1 Sin modelo real

**La suite normal no llama al modelo ni a Langfuse.** Tres capas (TO-034):

1. **Costura por `Protocol`.** `commons/llm/` define `ClienteModelo` y `commons/observabilidad/`
   define `Trazador`, cada uno con **una sola** implementación de producción. Los dobles
   viven en `tests/dobles/` —`ModeloGuionizado`, que devuelve salidas estructuradas de
   `tests/fixtures/` y cuenta tokens de forma determinista; y `RegistroTrazas`, que guarda
   los spans y scores para poder afirmar sobre ellos— y se inyectan con
   `app.dependency_overrides` o por la fábrica `crear_app(...)`.
2. **Casetes** en `tests/casetes/`: la implementación de producción, con su `httpx` real,
   contra un `httpx.MockTransport` que reproduce respuestas grabadas. Cubren serialización y
   conteo. **Se graban solo en el P26 y solo con credencial**; sin ella esa capa queda
   pendiente y no bloquea.
3. **Pruebas reales** marcadas `@pytest.mark.real`, excluidas por `addopts = -m "not real"`.
   Solo el humo del P26/P27 y las ejecuciones reales de los cierres de F4 y F5.

**Comprobación de que no hay dobles en producción** (P02): ningún módulo de `backend/app/`
importa `unittest.mock`, `tests` ni nada llamado `doble`, `fake`, `stub` o `mock`.

### 4.2 Test de conformidad con `specs/openapi.yaml`

Nace en el P01 y corre en toda la suite. Tres partes:

1. **Estructural.** Carga `specs/openapi.yaml` y `app.openapi()`, **normaliza los dos** y los
   compara:
   - resuelve todos los `$ref` y compara el schema efectivo, no el nombre del componente;
   - `anyOf: [X, {type: null}]` y `type: [X, 'null']` se igualan;
   - se ignoran **solo** claves de documentación: `description`, `summary`, `example`,
     `examples`, `title`, `contact`, `license`. Todo lo demás —métodos, rutas, `operationId`,
     parámetros, `required`, `enum`, formatos, mínimos y máximos, códigos de respuesta,
     tipos de medio, cabeceras `Location`, `tags`, `info.version`, `servers`— se compara.
2. **Incremental.** Una lista `PENDIENTES` con los `operationId` aún no implementados. Toda
   operación del app debe estar en el contrato y coincidir exactamente; toda operación del
   contrato debe estar implementada **o** en `PENDIENTES`. Cada paso que implementa un
   endpoint lo saca de la lista. **El P49 comprueba que la lista está vacía.**
3. **Dinámica.** Un fixture `validar_contra_contrato` que valida con `jsonschema` el cuerpo,
   el código y el tipo de medio de **cada respuesta** de las pruebas de API contra el schema
   aprobado para esa operación y ese código. Incluye los errores `problem+json` y el 422.

**Las dos formas del brief** (TO-037) se comprueban como cualquier otro schema, más dos
pruebas propias: `validarBrief` acepta un `BriefNovelaParcial` vacío (`{}`) con `200`, y
`crearNovela` rechaza ese mismo cuerpo con `422`. Si FastAPI generase un solo schema para
las dos, la comparación estructural fallaría.

**Meta-prueba**: una copia del contrato con una sola mutación —un `required` de menos, un
código de más, un `enum` cambiado— debe hacer fallar la comparación. Sin ella, un
normalizador demasiado generoso daría un test que no puede fallar.

Donde Pydantic no genera la forma exacta —el `oneOf` de `NuevaSolicitudCambio`, las
respuestas `problem+json`, las cabeceras— se usa `json_schema_extra`, `responses=` y
`openapi_extra` **en el código**. Nunca se toca el fichero aprobado.

### 4.3 Pruebas que atan documentos y código

Tres pruebas leen los documentos de `docs/` para que no se desincronicen en silencio:

- la tabla de transiciones de `process/` contra los `stateDiagram` de `docs/domain-knowledge.md`
  § Estados y la tabla de acciones de `docs/architecture.md` (P13);
- el registro de validadores de `quality/` contra el índice de `docs/verification.md` (P28);
- el catálogo de errores del código contra el `enum` de `Problema` en el contrato (P04).

### 4.4 Estructura de `tests/`

```
backend/tests/
  conftest.py           base temporal, app con dobles, validar_contra_contrato
  dobles/               ModeloGuionizado, RegistroTrazas, ContadorDeterminista
  fixtures/             briefs ficticios, esquemas, borradores defectuosos, lectura/
  casetes/              respuestas grabadas, sin cabeceras de autenticación
  contrato/             conformidad OpenAPI y su meta-prueba
  arquitectura/         importaciones, mocks, ORM, novel_id, parámetros obligatorios
  commons/  intake/  novel/  canon/  context/  quality/  guardrail/
  process/  policy/  versioning/   una carpeta por feature
  e2e/                  una prueba de extremo a extremo por fase, con dobles
  humo/                 @pytest.mark.real
  herramientas/         comprobar_cobertura.py
```

**Todos los briefs de prueba son ficticios** (RNF-17). El de ejemplo es el `example` de
`BriefNovela` en el contrato, copiado a `ejemplos/brief-ejemplo.json` en el P26.

### 4.5 Verificación de cierre de fase

Cada cierre ejecuta este bloque completo, más la prueba de extremo a extremo de su fase:

```bash
uv run pytest --cov=app --cov-report=json:../data/cobertura.json
uv run python tests/herramientas/comprobar_cobertura.py   # contra validadores.cobertura_tests_minima
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
uv run pytest tests/contrato -v
uv run pytest tests/e2e/test_fN.py -v                     # N = la fase
```

---

## 5. Migraciones

Numeradas en `backend/app/commons/db/migrations/`, aplicadas en orden al arrancar y con
`python -m app.commons.db.migrar`. El runner guarda el hash de cada una y **falla en voz alta
si una ya aplicada cambió**: es lo que hace ejecutable «nunca se editan» (RD-03).

| Migración | Paso | Tablas |
| --- | --- | --- |
| `0001_obra.sql` | P12 | `obra` (raíz: `novel_id`, `titulo`, `estado` con `CHECK`, `total_capitulos`, `creada_en`) |
| `0002_encargo.sql` | P12 | `comprador`, `destinatario`, `ocasion`, `brief_novela`, `elemento_personalizado`, `texto_libre`, `dedicatoria`, `regla_mundo`, `voz_narrativa` |
| `0003_palabra_prohibida.sql` | P12 | `palabra_prohibida` (nivel `novela`) |
| `0004_estructura_obra.sql` | P15 | `capitulo`, `personaje`, `lugar`, `arco`, `hilo_trama`, `evento`, `evento_personaje`, `evento_capitulo`, `evento_excluyente`, `restriccion_destino`, `brief_capitulo`, `elemento_capitulo` |
| `0005_canon.sql` | P15 | `hecho`, `hecho_capitulo` (con trigger de RD-05), `snapshot`, `promesa`, `resumen_capitulo` y los índices de `architecture.md` § Índices |
| `0006_audit_log.sql` | P16 | `audit_log` con triggers que abortan `UPDATE` y `DELETE` (RF-POL-02) |
| `0007_coincidencia.sql` | P16 | `coincidencia` |
| `0008_trabajo.sql` | P21 | `trabajo`, `checkpoint` |
| `0009_version.sql` | P25 | `version_novela`, `version_capitulo`, triggers de inmutabilidad (RNF-07) |
| `0010_calidad.sql` | P28 | `validador`, `informe_critica`, `defecto`, `score` |
| `0011_saneamiento_brief.sql` | P36 | `fragmento_sospechoso`, `dato_faltante`, `contradiccion_brief` |
| `0012_regeneracion.sql` | P40 | `solicitud_cambio`, `analisis_impacto`, `retcon`, `contradiccion_canon` |
| `0013_exportacion.sql` | P48 | `exportacion` |

Toda tabla lleva `novel_id NOT NULL` con clave foránea a `obra`, salvo `obra`, cuya clave
primaria es `novel_id`; ninguna lleva `user_id` ni `tenant_id`. La prueba del P05 lo exige de
toda migración presente y futura.

---

## 6. Estructura resultante

```
README.md                     P10 · arranque, un solo worker, brief de ejemplo, Langfuse
ejemplos/brief-ejemplo.json   P26
ejemplos/novela-ejemplo.pdf   P49
docs/browser-mcp.md           P47 · qué tool del MCP sostiene cada aserción y qué inspeccionó
backend/
  pyproject.toml  uv.lock  .python-version
  app/
    __main__.py               lanzador: interfaz local y un worker (D-11)
    main.py                   crear_app(), lifespan: config, migraciones, cerrojo, worker
    commons/  config/ db/ errores/ llm/ observabilidad/ salud.py
    intake/  novel/  canon/  context/  quality/  guardrail/  process/  policy/  versioning/
    prompts/                  un .md por rol y sync.py (D-09)
    skills/personalizacion-natural/SKILL.md
  tests/                      § 4.4
```

Cada feature con la anatomía de `backend-feature-slice`: `router.py` (si expone HTTP),
`schemas.py`, `models.py`, `service.py`, `repository.py`.

---

## 7. Pasos

Formato de cada paso: **Fase · Cubre · Skill · Ficheros · Pruebas primero · Hecho cuando.**
El «Hecho cuando» se suma siempre al invariante global de § 0.1.

### F0 — Fundación

#### P01 · Esqueleto del proyecto y test de conformidad

- **Fase** F0 · **Cubre** spec § 4 (contrato primero), § 6.2 · **Skill** `backend-feature-slice`
- **Ficheros** `backend/pyproject.toml` (dependencias de F0, `ruff`, `mypy --strict` con plugin
  de Pydantic, `pytest` con `addopts = -m "not real"` y el marcador `real`),
  `.python-version`, `app/__init__.py`, `app/main.py` con `crear_app()` y un `lifespan` vacío,
  metadatos `info`, `servers` y `tags` iguales al contrato; `tests/conftest.py`,
  `tests/contrato/normalizar.py`, `tests/contrato/test_conformidad_openapi.py`,
  `tests/test_arranque.py`.
- **Pruebas primero**
  - `test_conformidad_estructural`: con `PENDIENTES` = las 20 operaciones, no hay ninguna
    implementada que diverja y no sobra ninguna.
  - `test_meta_una_mutacion_hace_fallar_la_comparacion`, parametrizada sobre al menos seis
    mutaciones del contrato (§ 4.2).
  - `test_info_y_servers_coinciden`.
  - `test_la_app_arranca`: `TestClient` con `lifespan` entra y sale sin error.
- **Hecho cuando** `uv sync && uv run pytest tests/contrato tests/test_arranque.py && uv run mypy app tests`

#### P02 · Pruebas de arquitectura

- **Fase** F0 · **Cubre** `CLAUDE.md` reglas 6 y 8, RD-01, RD-02, filas A-24, A-26, A-37, A-83,
  A-84 · **Skill** `backend-feature-slice`
- **Ficheros** `tests/arquitectura/test_importaciones.py`, `test_sin_mocks.py`,
  `test_dependencias.py`, `test_parametros_de_dominio.py`.
- **Pruebas primero**, todas sobre `app/` por análisis estático (`ast`):
  - ninguna feature importa el `repository.py` de otra; el grafo de importación entre
    features no tiene ciclos, sus aristas son **exactamente** las del diagrama de
    `architecture.md` § Regla de importación —leído del fichero—, y `intake/` y `guardrail/`
    no importan ninguna otra feature (D-08);
  - ningún módulo de `app/` importa `unittest.mock`, `tests` ni nombres de doble (§ 4.1);
  - `uv.lock` no contiene ningún paquete de la lista excluida de `CLAUDE.md` (Postgres,
    ORM, Redis, Celery, Django, Flask…);
  - toda función pública de un `repository.py` recibe `novel_id` —y `version` si consulta
    tablas versionadas— como parámetro **obligatorio de palabra clave sin valor por defecto**.
    Con `app/` casi vacía estas pruebas pasan, y pasar vacías es lo esperado: vigilan los
    pasos siguientes.
  - Meta-prueba: un módulo de prueba escrito en `tmp_path` que viola cada regla hace fallar
    su comprobación.
- **Hecho cuando** `uv run pytest tests/arquitectura -v`

#### P03 · Configuración con fallo en voz alta

- **Fase** F0 · **Cubre** RNF-14, RNF-15, RF-CTX-05, RNF-01 · **Skill** `backend-feature-slice`,
  `presupuesto-de-contexto`
- **Ficheros** `app/commons/config/{modelos.py,cargar.py}`: modelos Pydantic de
  `thresholds.yaml` y `models.yaml`, ruta configurable por `STORYMAKER_CONFIG_DIR` con la
  raíz del repositorio por defecto. El `lifespan` carga la configuración y aborta si no vale.
- **Pruebas primero** (cada una sobre una copia modificada en `tmp_path`):
  - la configuración real del repositorio carga;
  - las siete capas más el margen suman exactamente `contexto.total`, y si no, falla;
  - `margen < max_tokens` de un rol → falla **nombrando el rol**;
  - con `medicion.cerrar_el_paso: true`, un umbral de `calidad` en `null` → falla **nombrando
    la clave** (`calidad.consistencia_factica`); con `false`, carga;
  - un umbral que cierra el paso siempre —`capitulo.longitud_min_palabras`— en `null` falla
    en ambos casos;
  - `formal.gate_activo: true` con `lean_timeout_segundos: null` → falla;
  - `roles.judge.id` igual a `roles.redactor.id` → falla (TO-013);
  - `test_arranque_falla_con_umbral_nulo`: el `lifespan` no llega a servir y el mensaje
    contiene la clave.
- **Hecho cuando** `uv run pytest tests/commons/test_config.py -v`

#### P04 · Errores `problem+json` y handler central

- **Fase** F0 · **Cubre** spec § 4.3, TO-032 · **Skill** `backend-feature-slice`
- **Ficheros** `app/commons/errores/{excepciones.py,handler.py}`: una excepción de dominio por
  `type` del catálogo, con su estado y sus extensiones; handler para ellas, para
  `RequestValidationError` (422 reescrito) y para cualquier otra (500 sin detalles internos,
  con `traza_langfuse_id`); el 422 por defecto de FastAPI se retira del OpenAPI.
- **Pruebas primero** (rutas de prueba montadas sobre una `crear_app()` en el test):
  - cada excepción produce su `status`, su `type` y `application/problem+json`;
  - un cuerpo inválido da 422 `peticion-invalida` con la forma de `Problema`;
  - una excepción no prevista da 500 `error-interno` y el cuerpo no contiene la traza de pila;
  - el conjunto de `type` del código es igual al `enum` de `Problema` en el contrato.
- **Hecho cuando** `uv run pytest tests/commons/test_errores.py tests/contrato -v`

#### P05 · Base de datos y runner de migraciones

- **Fase** F0 · **Cubre** RD-01, RD-03, RD-04 · **Skill** `sqlite-relacional`
- **Ficheros** `app/commons/db/{conexion.py,migrar.py,transaccion.py}`,
  `app/commons/db/migrations/` (vacía), ruta por `STORYMAKER_DB_PATH` con `data/storymaker.db`
  por defecto. El `lifespan` aplica las pendientes.
- **Pruebas primero**
  - toda conexión salida de `conectar()` tiene `journal_mode = wal` y `foreign_keys = 1`;
  - con migraciones de prueba en `tmp_path`: se aplican en orden, una segunda ejecución no
    hace nada, y **editar una ya aplicada hace fallar el runner** nombrando el fichero;
  - una transacción que lanza a medias no deja ninguna fila;
  - `test_toda_tabla_lleva_novel_id`: sobre las migraciones reales, toda tabla salvo la de
    control del runner tiene `novel_id NOT NULL`, y ninguna tiene `user_id` ni `tenant_id`.
- **Hecho cuando** `uv run pytest tests/commons/test_db.py -v && uv run python -m app.commons.db.migrar`

#### P06 · Cliente del modelo con conteo previo

- **Fase** F0 · **Cubre** RF-CTX-02 (contar antes), RNF-05, RF-PROC-09 (clasificación del
  fallo), TO-034 capas 1 y 2 · **Skill** `backend-feature-slice`, `claude-api`
- **Ficheros** `app/commons/llm/{protocolo.py,anthropic.py,errores.py}`. `ClienteModelo` expone
  `contar_tokens(peticion) -> Recuento` y `generar(peticion, recuento) -> Respuesta`. **Solo
  `contar_tokens` puede construir un `Recuento`**, así que no hay forma de llamar sin haber
  contado. La implementación usa `AsyncAnthropic` con timeout explícito y sin reintentos
  propios del SDK —los reintentos son nuestros—; `id`, `effort` y `max_tokens` salen de
  `config/`, y la salida estructurada va por tool con `strict: true`. Añade
  `coste.precio_usd_por_millon` a `config/thresholds.yaml` (D-18) comprobado en la
  documentación oficial. `tests/dobles/modelo.py` con `ModeloGuionizado`.
- **Pruebas primero**, contra `httpx.MockTransport`:
  - la petición lleva el `id`, el `effort` y el `max_tokens` del rol, y el timeout está fijado;
  - `generar` sin `Recuento` no compila para `mypy` y lanza en ejecución;
  - 429, 5xx y timeout se clasifican como `FalloInfraestructura`; un 400 no;
  - `usage` se traduce a tokens y a `coste_usd` con los precios de configuración;
  - el doble cumple el `Protocol` (comprobación estructural de `mypy` y un test).
- **Hecho cuando** `uv run pytest tests/commons/test_llm.py -v`

#### P07 · Pool en vuelo con admisión FIFO

- **Fase** F0 · **Cubre** RNF-02, RNF-03 · **Skill** `presupuesto-de-contexto`
- **Ficheros** `app/commons/llm/pool.py`: semáforo por peso, en proceso, compartido por toda la
  instancia, con `en_vuelo.total` de configuración y lectura de lo ocupado para `/salud`.
- **Pruebas primero**
  - propiedad (`hypothesis`): para cualquier secuencia de peticiones concurrentes, la suma en
    vuelo nunca supera el total;
  - FIFO estricto: una petición grande en cabeza no es adelantada por pequeñas que cabrían;
  - una estimación mayor que el total lanza `TrabajoNoCabeEnPool` **al pedirla**, sin esperar;
  - el peso se libera si la llamada lanza o se cancela.
- **Hecho cuando** `uv run pytest tests/commons/test_pool.py -v`

#### P08 · Observabilidad: sesión, traza, span y score

- **Fase** F0 · **Cubre** RF-OBS-01…04 (base), RNF-08, D-10 · **Skill** `backend-feature-slice`,
  `langfuse`
- **Ficheros** `app/commons/observabilidad/{protocolo.py,langfuse.py}` y
  `app/commons/llm/llamar.py`: `llamar_modelo(rol, peticion)` es **el único camino** al
  modelo —pasa por el pool, cuenta, abre el span del rol, llama y anota tokens, coste,
  latencia y hash del prompt—. `tests/dobles/trazador.py` con `RegistroTrazas`.
- **Pruebas primero**
  - con el doble: N llamadas producen N spans con el nombre del rol, tokens, coste y latencia;
  - un nombre de span que no sea uno de los seis roles o de las tools de `architecture.md`
    § Agentes se rechaza;
  - sin variables `LANGFUSE_*`, la implementación de producción no lanza, marca `degradado` y
    escribe el span en el log;
  - prueba de arquitectura: ningún módulo de `app/` fuera de `commons/llm/` llama al
    `ClienteModelo` directamente.
- **Hecho cuando** `uv run pytest tests/commons/test_observabilidad.py tests/arquitectura -v`

#### P09 · `GET /salud` y arranque seguro

- **Fase** F0 · **Cubre** RF-META-01, RNF-12, RF-PROC-03 (cerrojo), D-11 · **Skill**
  `backend-feature-slice`
- **Ficheros** `app/commons/salud.py` (router), `app/__main__.py`, cerrojo de instancia en
  `app/commons/db/`. Saca `obtenerSalud` de `PENDIENTES`.
- **Pruebas primero**
  - conformidad de `obtenerSalud` y respuesta válida contra `Salud`;
  - `gate_lean_activo` y `cerrar_el_paso` reflejan la configuración; `tokens_en_vuelo` y
    `tokens_en_vuelo_total` reflejan el pool; `estado` es `degradado` sin Langfuse;
  - el lanzador rechaza `--host 0.0.0.0` sin `--permitir-red` y fuerza un worker;
  - un segundo `lifespan` sobre la misma base falla en voz alta mientras el primero vive.
  - `test_arranque.py` pasa a pedir `GET /salud`.
- **Hecho cuando** `uv run pytest tests/commons/test_salud.py tests/contrato -v`

#### P10 · Cierre de F0

- **Pruebas primero** `tests/e2e/test_f0.py`: lanza `python -m app` como subproceso en un
  puerto libre y una base temporal, pide `/salud` por HTTP y la valida contra el contrato;
  lanza otro con un umbral de cierre en `null` y comprueba que sale con código distinto de
  cero y un mensaje que nombra la clave. Es el criterio de terminado de la spec § 7 F0.
- **Además** `README.md` con instalación y arranque (§ 9), y la advertencia de un solo worker.
- **Hecho cuando** el bloque de § 4.5 con `N = 0`, y a mano:
  `uv run --env-file ../.env python -m app` + `curl -s http://127.0.0.1:8000/salud`.

### F1 — Generación de extremo a extremo

#### P11 · Guardrail: normalización y niveles

- **Fase** F1 · **Cubre** RF-GUARD-01, RF-GUARD-02, D-21 · **Skill** `backend-feature-slice`
- **Ficheros** `app/guardrail/{normalizacion.py,service.py,models.py,listas/global.txt,
  listas/perfil.yaml}`. Sin tablas todavía: el nivel `novela` llega en el P12.
- **Pruebas primero** en `tests/guardrail/`, su suite propia:
  - la palabra vetada `imbécil` coincide con `Imbeciles`; `i-d-i-o-t-a` coincide con
    `idiota`; un diminutivo regular coincide;
  - **cada una de las cinco transformaciones, apagada, deja pasar su variante**: prueba que
    las cinco están activas y no solo una;
  - la normalización se aplica a los dos lados;
  - los niveles se combinan y gana el más restrictivo; `perfil` se deriva de
    `destinatario.edad` y `ocasion.tipo`;
  - una coincidencia devuelve la palabra, el nivel y la posición en el texto.
- **Hecho cuando** `uv run pytest tests/guardrail -v`

#### P12 · Encargo y obra: crear, listar y consultar novelas

- **Fase** F1 · **Cubre** RF-INTAKE-04, RF-INTAKE-05, RF-NOVEL-02, RF-NOVEL-03, RNF-10, RD-01 ·
  **Skill** `backend-feature-slice`, `sqlite-relacional`
- **Ficheros** migraciones `0001`–`0003`; `app/intake/` (`BriefNovela` idéntico al
  contrato, persistencia; `BriefNovelaParcial` llega en el P35), `app/novel/` (router de `/novelas`, `Obra`),
  `app/guardrail/repository.py` para el nivel `novela`. Saca `crearNovela`, `listarNovelas`
  y `obtenerNovela` de `PENDIENTES`.
- **Pruebas primero**
  - conformidad de las tres operaciones y validación dinámica de sus respuestas;
  - `POST /novelas` con el brief del contrato → `201`, `Location`, estado `Configurando`, y
    **el doble del modelo registra cero llamadas**;
  - un brief sin un campo obligatorio de `BriefNovela` → `422 peticion-invalida` y ninguna
    fila nueva: crear exige el brief completo (TO-037);
  - las palabras prohibidas del brief quedan como nivel `novela`, y las reglas del mundo
    asociadas a la novela;
  - `GET /novelas` pagina con `limite` y `desplazamiento`, de la más reciente a la más antigua;
  - `GET /novelas/{id}` inexistente → 404 `novela-no-encontrada`;
  - aislamiento: con dos novelas, cada consulta devuelve solo lo suyo.
- **Hecho cuando** `uv run pytest tests/intake tests/novel tests/contrato -v` y
  `curl -s -X POST http://127.0.0.1:8000/novelas -H 'Content-Type: application/json' -d @../ejemplos/brief-ejemplo.json`
  con el servidor en marcha (el JSON se crea en el P26; hasta entonces, el de `tests/fixtures/`).

#### P13 · Máquina de estados como tabla declarativa

- **Fase** F1 · **Cubre** RF-PROC-07, TO-020 · **Skill** `backend-feature-slice`
- **Ficheros** `app/process/transiciones.py`: las dos máquinas, `Capitulo` y `Novela`, como
  dato `(estado, acción) → estado`, y `aplicar(estado, accion)`. Si a una transición del
  diagrama de la novela le falta nombre de acción en `architecture.md` § Estados, se le da uno
  y se añade a esa tabla (documento, paso 1 del ciclo), con registro.
- **Pruebas primero**
  - los pares origen → destino de la tabla son **exactamente** los de los `stateDiagram` de
    `docs/domain-knowledge.md` § Estados, leídos del propio fichero;
  - los nombres de acción coinciden con la tabla de `docs/architecture.md`;
  - los estados son los `enum` `EstadoNovela` y `EstadoCapitulo` del contrato;
  - una transición que no está → `TransicionInvalida`, y el estado no cambia;
  - propiedad: desde `Pendiente`, ninguna secuencia de acciones válidas sale de los estados
    declarados.
- **Hecho cuando** `uv run pytest tests/process/test_transiciones.py -v`

#### P14 · Prompts, versión de prompt y skill de runtime

- **Fase** F1 · **Cubre** RF-OBS-05, TO-021, TO-024, D-09 · **Skill** `presupuesto-de-contexto`,
  `langfuse`
- **Ficheros** `app/prompts/{planner,writer,extractor,judge,editor,interviewer}.md`,
  `app/prompts/cargar.py` (devuelve texto y **hash de blob de git** calculado sobre el
  contenido realmente leído), `app/prompts/sync.py` (publica en Langfuse solo los hashes que
  no estén), `app/skills/personalizacion-natural/SKILL.md`. La excepción ya está declarada en
  `docs/architecture.md` § Anatomía (D-09).
- **Pruebas primero**
  - el hash coincide con `git hash-object` del fichero;
  - `sync` con el registro de prueba es idempotente: dos ejecuciones publican una vez;
  - la skill no contiene ninguna cifra ni ningún ancla de la rúbrica, y ni la skill ni los
    prompts de `writer` y `editor` contienen el texto de la rúbrica, que solo está en el del
    `judge`;
  - ningún prompt contiene un dato de novela: son plantillas con huecos tipados.
- **Hecho cuando** `uv run pytest tests/prompts -v`

#### P15 · Canon: consolidación, uso por capítulo y vigencia

- **Fase** F1 · **Cubre** RF-CANON-01…04, RNF-06, RD-02, RD-05, D-05, D-06, D-12 · **Skill**
  `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migraciones `0004` y `0005`; `app/canon/` y el `repository.py` de `novel/`
  para capítulos, personajes, lugares y eventos. `canon.service.consolidar(con, novel_id,
  chapter_id, version, extraccion)`, `hechos_vigentes(novel_id, version)`,
  `snapshot_al_cierre(novel_id, version, numero)`.
- **Pruebas primero**
  - consolidar escribe hechos, usos, promesas, snapshot y resumen en **una** transacción; si
    un paso falla no queda nada;
  - consolidar dos veces con la misma clave `novel_id + chapter_id + version` deja las mismas
    filas;
  - un hecho cuyo `fragmento_soporte` no aparece literal en el texto no se consolida;
  - un hecho retconeado en la versión 3 aparece al pedir la versión 1 (vigencia, no estatus);
  - una fila de `hecho_capitulo` fuera de la vigencia de su hecho la rechaza el trigger;
  - «qué capítulos usan este hecho en la versión v» usa el índice
    `(novel_id, hecho_id, version_desde, version_hasta)` (`EXPLAIN QUERY PLAN`).
- **Hecho cuando** `uv run pytest tests/canon tests/arquitectura -v`

#### P16 · Policy engine y audit log de solo escritura

- **Fase** F1 · **Cubre** RF-POL-01, RF-POL-02, RF-GUARD-03 (registro) · **Skill**
  `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migraciones `0006` y `0007`; `app/policy/`: `decidir_capitulo(...)` y
  `decidir_hecho(...)`, cada una con su regla nombrada y una fila de audit log.
- **Pruebas primero**
  - cada decisión deja exactamente una fila con regla, entrada y resultado;
  - `UPDATE` y `DELETE` sobre `audit_log` abortan por trigger;
  - prueba de arquitectura: ningún SQL de `app/` contiene `UPDATE audit_log` ni
    `DELETE FROM audit_log`;
  - un hecho `propuesto` con fragmento literal se adopta; sin él, se descarta; ambos quedan
    registrados.
- **Hecho cuando** `uv run pytest tests/policy -v`

#### P17 · Ensamblado de contexto por capas

- **Fase** F1 · **Cubre** RF-CTX-01…04, RNF-01, RNF-09, RNF-10 · **Skill**
  `presupuesto-de-contexto`
- **Ficheros** `app/context/{ensamblador.py,capas.py,recuperacion.py,service.py}`. Cada capa
  sale de su fuente; la Invariante se compone por rol; el recuento se hace con
  `contar_tokens` **antes** de devolver el prompt; la degradación sigue
  `contexto.degradacion`. El texto libre del comprador va siempre en un bloque delimitado
  como datos dentro del mensaje de usuario, **nunca** en el `system`.
- **Pruebas primero** (con `ContadorDeterminista` de `tests/dobles/`):
  - cada capa trae lo de su fuente y nada más;
  - Recuperado desbordado se comprime **solo él**, y la degradación para en cuanto cabe;
  - Invariante y restricción de destino no se degradan nunca: si no caben, falla;
  - tras degradar todo lo degradable y seguir sin caber, `ContextoNoCabe` y **cero llamadas
    al modelo**;
  - Recuperado filtra por las entidades del `BriefCapitulo` antes de ordenar: un fragmento de
    otra entidad no entra aunque se parezca más;
  - un hecho de otra novela nunca entra (RNF-10);
  - el texto libre no aparece en el `system` y aparece dentro del delimitador de datos.
- **Hecho cuando** `uv run pytest tests/context -v`

#### P18 · Planificador: el esquema de la obra

- **Fase** F1 · **Cubre** RF-NOVEL-01, D-23 · **Skill** `backend-feature-slice`,
  `presupuesto-de-contexto`
- **Ficheros** `app/process/planificar.py`, schemas del `Esquema` con su `RestriccionDestino`
  (tipo, alcance por identificadores, capítulo), persistencia en `novel/` y `process/`.
- **Pruebas primero** (el doble devuelve esquemas de `tests/fixtures/`):
  - un esquema válido crea `obra.capitulos` capítulos en `Pendiente`, cada uno con restricción
    y brief, y fija el título;
  - un esquema con otro número de capítulos, o con un alcance que nombra una entidad
    inexistente, falla `schema_valido` y se reintenta hasta el límite; agotado, la novela
    queda `Detenida` con `limite-de-intentos-agotado`;
  - la llamada abre el span `planner` y la tool `consultar_story_bible` el suyo.
- **Hecho cuando** `uv run pytest tests/process/test_planificar.py -v`

#### P19 · Redactor, hook de policy y hook de capítulo mínimo

- **Fase** F1 · **Cubre** RF-QUA-01, RF-QUA-02 (parcial: `longitud`, `nombres_exactos`),
  RF-GUARD-03, RF-NOVEL-04 (parcial), RF-OBS-03 · **Skill** `backend-feature-slice`
- **Ficheros** `app/process/escribir.py`, `app/quality/validadores/{schema_valido,
  palabras_prohibidas,longitud,nombres_exactos}.py`, `app/quality/service.py` con los dos
  hooks. Cada validador emite su score.
- **Pruebas primero**, una por defecto inyectado en `tests/fixtures/borradores/`:
  - borrador fuera de `capitulo.longitud_min_palabras..max` → falla `longitud`;
  - el nombre del destinatario mal escrito → falla `nombres_exactos`;
  - una palabra vetada → falla `palabras_prohibidas`, registra la coincidencia en audit log y
    en el trazador;
  - **dos pasadas consecutivas con palabra vetada** → generación `Detenida` con
    `palabra-prohibida-persistente`, sin tercer intento;
  - el hook de policy corre antes que el de capítulo, y si falla el de capítulo no corre;
  - un score por validador ejecutado.
- **Hecho cuando** `uv run pytest tests/quality tests/guardrail -v`

#### P20 · Extractor y aceptación

- **Fase** F1 · **Cubre** RF-PROC-10, RF-CANON-01, RF-CANON-04, D-07, D-12 · **Skill**
  `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** `app/process/{extraer.py,aceptar.py}`. `aceptar` abre la transacción y llama a
  `novel`, `canon`, `context`, `policy` y al checkpoint.
- **Pruebas primero**
  - el extractor corre **después** de aceptar y nunca antes: con el doble, el orden de spans
    es `writer`, validadores, `extractor`;
  - un borrador rechazado no deja ni hecho, ni resumen, ni snapshot, ni texto de capítulo;
  - los hechos entran `propuesto` y el policy los adopta o descarta con fila en audit log;
  - la aceptación de un capítulo ocurre a lo sumo una vez por versión (restricción `unique`).
- **Hecho cuando** `uv run pytest tests/process/test_aceptar.py tests/canon -v`

#### P21 · Cola de trabajos y endpoints de generación

- **Fase** F1 · **Cubre** RF-PROC-01, RF-PROC-02, RF-PROC-04, RF-PROC-05, RNF-03, RD-06, D-04 ·
  **Skill** `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migración `0008`; `app/process/{cola.py,router.py}`. Saca `lanzarGeneracion`,
  `listarGeneraciones` y `obtenerGeneracion` de `PENDIENTES`. Añade `trabajos_en_cola` a
  `/salud`. En este paso **no hay worker**: los trabajos quedan `pendiente`, que es un estado
  real y no un simulacro.
- **Pruebas primero**
  - `POST …/generaciones` → `202` en menos de un segundo, con `Location`, y fila en `trabajo`;
  - un segundo `POST` con uno vivo → `409 generacion-en-curso` con el `generacion_id` vivo y
    **ninguna fila nueva**;
  - con una configuración donde la estimación supera `en_vuelo.total` → `422
    trabajo-no-cabe-en-pool`;
  - `reclamar()`: dos reclamaciones simultáneas del mismo trabajo, exactamente una afecta a
    una fila;
  - `es_terminal` es `true` solo en `Publicada` y `Detenida`, e `intervalo_sondeo_segundos`
    es `null` exactamente entonces;
  - conformidad y validación dinámica de las tres operaciones.
- **Hecho cuando** `uv run pytest tests/process tests/contrato -v`

#### P22 · Orquestador y worker en el `lifespan`

- **Fase** F1 · **Cubre** RF-PROC-03, RF-PROC-07 (uso), RF-OBS-01, RF-OBS-02 · **Skill**
  `backend-feature-slice`
- **Ficheros** `app/process/{orquestador.py,worker.py}`: el orquestador lee el estado, consulta
  la tabla del P13 y ejecuta la acción; nada decide el paso siguiente fuera de la tabla. El
  worker reclama trabajos en bucle dentro del `lifespan` y se para con él. Una sesión de
  Langfuse por novela y una traza por generación. README: «un solo worker».
- **Pruebas primero** (app con dobles):
  - una generación con el doble recorre `Configurando → Planificando → Escribiendo` y deja los
    diez capítulos en `Aceptado` y la novela en `Validando`;
  - toda transición ejecutada está en la tabla; forzar una que no está falla sin mutar;
  - una sesión por novela, una traza por generación, un span por rol y por tool;
  - al cerrar el `lifespan` el worker termina sin dejar tareas colgadas.
- **Hecho cuando** `uv run pytest tests/process/test_orquestador.py -v`

#### P23 · Reintentos, agotamiento y topes de coste y latencia

- **Fase** F1 · **Cubre** RF-PROC-08, RF-PROC-09, RNF-04, RNF-13, RF-OBS-04 · **Skill**
  `backend-feature-slice`
- **Ficheros** `app/process/reintentos.py`; acumulados de tokens y coste por llamada, capítulo
  y novela en `trabajo` y `capitulo`.
- **Pruebas primero**
  - un 429 del doble se reintenta con retroceso exponencial y jitter (reloj inyectado), el
    capítulo se acepta y **sus `intentos` siguen en cero**;
  - agotar `max_intentos_trabajo` detiene e informa;
  - un capítulo que falla la validación `max_intentos_capitulo` veces queda `Agotado`, la
    novela `Detenida`, `detenida_por = limite-de-intentos-agotado`;
  - superar `coste.coste_maximo_novela` o `coste.latencia_maxima_novela` detiene e informa;
  - `tokens_consumidos` y `coste_usd` de la generación son la suma de sus llamadas.
- **Hecho cuando** `uv run pytest tests/process/test_reintentos.py -v`

#### P24 · Checkpoint y reanudación

- **Fase** F1 · **Cubre** RF-PROC-06, TO-023 · **Skill** `sqlite-relacional`
- **Ficheros** `app/process/orquestador.py` § `estado_inicial`.
- **Pruebas primero**
  - con 1–4 `Aceptado` y el 5 en `Escribiendo`, `estado_inicial` normaliza el 5 a
    `Pendiente`, el checkpoint queda en 4 y la generación sigue por el 5;
  - propiedad (`hypothesis`): para cualquier punto de corte, tras reanudar el conjunto de
    aceptados es un prefijo contiguo y ningún capítulo se acepta dos veces;
  - un trabajo `en-curso` huérfano al arrancar se retoma, no se duplica.
- **Hecho cuando** `uv run pytest tests/process/test_reanudacion.py -v`

#### P25 · Gate mínimo, publicación y lectura por versión

- **Fase** F1 · **Cubre** RF-VER-01, RF-VER-02, RF-VER-03, RF-NOVEL-05, RF-QUA-03 (parcial),
  RNF-07, D-05, D-17 · **Skill** `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migración `0009`; `app/versioning/`: gate con `estructura_edicion` y
  `elementos_obligatorios`, `publicar` con hash del contenido canónico; router de versiones y
  capítulos. Saca `listarVersiones`, `obtenerVersion`, `listarCapitulos` y `obtenerCapitulo`
  de `PENDIENTES`.
- **Pruebas primero**
  - con todos aceptados y el gate en verde se publica la versión 1 con su hash; la novela
    queda `Publicada` y la generación terminal con `version_resultante = 1`;
  - un elemento obligatorio que no aparece en ningún capítulo → no se publica;
  - `UPDATE` sobre una versión publicada o sus vínculos aborta; recalcular el hash da el mismo;
  - `modificado` es `false` en todos los capítulos de la versión 1;
  - las cuatro operaciones: conformidad, validación dinámica y 404 `version-no-encontrada`.
- **Hecho cuando** `uv run pytest tests/versioning tests/contrato -v`

#### P26 · Humo opt-in, casetes y escaneo de secretos

- **Fase** F1 · **Cubre** spec § 6.2 capas 2 y 3, RNF-11, RNF-17 · **Skill**
  `backend-feature-slice`
- **Ficheros** `ejemplos/brief-ejemplo.json` (el `example` de `BriefNovela`, ficticio);
  `tests/humo/test_novela_real.py` marcado `real`: crea la novela con ese brief, lanza la
  generación sobre la base `STORYMAKER_DB_PATH` —no temporal, para reutilizarla en F4 y F5—,
  sondea hasta terminal y comprueba `Publicada` con diez capítulos. Transporte grabador que
  escribe casetes **sin cabeceras de autenticación**. `tests/arquitectura/test_sin_secretos.py`.
- **Pruebas primero**
  - `test_sin_secretos`: ningún fichero versionado ni casete contiene `x-api-key`,
    `authorization`, `sk-ant-` ni el valor de una variable de `.env.example`; y un casete de
    prueba con una cabecera así hace fallar el test;
  - el humo **se salta con motivo explícito** si no hay credencial en una ejecución normal, y
    el P27 lo trata como condición de parada.
- **Hecho cuando** `uv run pytest tests/arquitectura/test_sin_secretos.py -v` y
  `uv run pytest -m real --collect-only tests/humo`

#### P27 · Cierre de F1

- **Pruebas primero** `tests/e2e/test_f1.py`, con dobles:
  - una novela completa de diez capítulos publicada como versión 1 por HTTP de principio a fin;
  - **prueba de reanudación con proceso real**: arranca `uvicorn` sobre una app de prueba con
    dobles (`tests/e2e/app_con_dobles.py`), sondea hasta `capitulo_actual = 5`, **mata el
    proceso**, rearranca sobre la misma base y comprueba que acaba publicada, que los
    aceptados 1–4 no se reescribieron (mismo `capitulo_id`) y que ninguno se aceptó dos veces.
- **Además**, **la prueba de humo real**:
  1. si `ANTHROPIC_API_KEY` no está en el entorno → **condición de parada 1**;
  2. si `acumulado + coste.coste_maximo_novela > 40` → **condición de parada 4**;
  3. `uv run python -m app.prompts.sync` (si hay Langfuse) y
     `uv run --env-file ../.env pytest -m real tests/humo -v`;
  4. anotar en progreso el coste real (`coste_usd` de la generación), la ruta de la base y el
     `novel_id`, y commitear los casetes tras pasar `test_sin_secretos`.
- **Hecho cuando** el bloque de § 4.5 con `N = 1` y el humo en verde.

### F2 — Calidad

#### P28 · Registro de validadores e informe de crítica

- **Fase** F2 · **Cubre** RF-OBS-03, RF-PROC-08 (informe consultable) · **Skill**
  `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migración `0010`; `app/quality/{registro.py,informe.py}`: cada validador
  declara nombre, tipo, punto de ejecución y score.
- **Pruebas primero**
  - los validadores registrados tienen el nombre, tipo y punto de ejecución de su fila en el
    índice de `docs/verification.md`, leído del fichero;
  - cada intento deja su `InformeCritica` con sus `Defecto`, y el del último intento de un
    capítulo `Agotado` sigue consultable.
- **Hecho cuando** `uv run pytest tests/quality -v`

#### P29 · Hook de capítulo: validadores contra el canon

- **Fase** F2 · **Cubre** RF-QUA-02 (`consistencia_factica` programática, `cumplimiento_brief`,
  `reglas_mundo`) · **Skill** `backend-feature-slice`
- **Ficheros** `app/quality/validadores/{consistencia_factica,cumplimiento_brief,
  reglas_mundo}.py`. Implementan lo que dicen sus filas de `docs/verification.md`
  (O-26…O-32, O-29, O-30, O-42), con los umbrales de `calidad`.
- **Pruebas primero**, un defecto inyectado por validador y un capítulo limpio que pasa los
  tres: un valor que contradice un hecho adoptado, una regla del mundo violada («el abuelo
  nunca aparece» y aparece), una restricción de destino incumplida.
- **Hecho cuando** `uv run pytest tests/quality -v`

#### P30 · Hook de capítulo: validadores de texto y paralelismo

- **Fase** F2 · **Cubre** RF-QUA-02 (`calidad_prosa`, `integridad_pov`, ejecución en paralelo
  fuera del pool) · **Skill** `backend-feature-slice`
- **Ficheros** `app/quality/validadores/{calidad_prosa,integridad_pov}.py`, con las cifras de
  `prosa` y `calidad`.
- **Pruebas primero**
  - un defecto inyectado por métrica de `prosa` y un cambio de persona narrativa;
  - los siete validadores del hook corren concurrentes (`anyio`) y **el pool no registra
    ningún token** mientras corren.
- **Hecho cuando** `uv run pytest tests/quality -v`

#### P31 · Judge: rúbrica de seis criterios

- **Fase** F2 · **Cubre** RF-QUA-04, RF-QUA-07, TO-013, D-15 · **Skill** `backend-feature-slice`,
  `presupuesto-de-contexto`
- **Ficheros** `app/quality/judge.py`, prompt del `judge` con la rúbrica.
- **Pruebas primero**
  - seis puntuaciones separadas, cada una con justificación no vacía; una salida sin alguna
    falla `schema_valido`;
  - la llamada usa `roles.judge` y no `roles.redactor`;
  - con `cerrar_el_paso: false` una puntuación bajo umbral **no** suspende pero deja score;
    con `true` suspende; un booleano suspende siempre;
  - un score por criterio en el trazador, con su justificación.
- **Hecho cuando** `uv run pytest tests/quality/test_judge.py -v`

#### P32 · Editor y orden completo de validación

- **Fase** F2 · **Cubre** RF-QUA-05, RF-NOVEL-04, D-14 · **Skill** `backend-feature-slice`
- **Ficheros** `app/quality/editor.py`; el ciclo pasa a policy → capítulo → judge → editor.
- **Pruebas primero**
  - el borrador corregido por el editor vuelve a pasar **todos** los validadores: con el doble,
    un editor que arregla la longitud pero introduce una palabra vetada hace fallar el hook de
    policy;
  - el orden de spans es `writer`, validadores, `judge`, `editor`;
  - un defecto sistémico se reescribe como uno local y queda registrado con su clasificación.
- **Hecho cuando** `uv run pytest tests/quality tests/process -v`

#### P33 · `cierre_arco` en el gate

- **Fase** F2 · **Cubre** RF-QUA-03 (`cierre_arco`), D-15, D-17 · **Skill** `backend-feature-slice`
- **Ficheros** `app/versioning/gate.py`.
- **Pruebas primero**: una promesa `Pendiente` al cerrar el último capítulo impide publicar; y
  el fallo del gate devuelve la novela a `Escribiendo` hacia el editor, como dice el diagrama.
- **Hecho cuando** `uv run pytest tests/versioning -v`

#### P34 · Cierre de F2

- **Pruebas primero** `tests/e2e/test_f2.py`: un capítulo defectuoso a propósito vuelve al
  redactor, se corrige y se acepta, y el `RegistroTrazas` contiene los scores de los
  validadores y los seis criterios del judge en la traza de esa generación.
- **Hecho cuando** el bloque de § 4.5 con `N = 2`.

### F3 — Intake

#### P35 · Validación del brief parcial

- **Fase** F3 · **Cubre** RF-INTAKE-01, RF-INTAKE-02, RNF-16, TO-037 · **Skill**
  `backend-feature-slice`
- **Ficheros** `app/intake/{schemas.py,validacion.py,reglas.py,router.py}`:
  `BriefNovelaParcial` y sus seis objetos parciales en `schemas.py`, idénticos al contrato
  1.1.0; la validación recorre el brief parcial contra la lista de obligatorios de
  `BriefNovela` —**derivada del propio modelo Pydantic**, no escrita a mano— y aplica las
  reglas deterministas entre campos. `crearNovela` responde `400 brief-invalido` con las
  contradicciones en las extensiones. Saca `validarBrief` de `PENDIENTES`.
- **Pruebas primero**
  - `{}` → `200 valido:false` con un `Dato faltante` por cada campo obligatorio de
    `BriefNovela`, cada uno con su pregunta de reintento;
  - un brief sin `destinatario.nombre` → `200 valido:false` con ese `Dato faltante`; **el
    sistema no rellena nada**;
  - un campo que llega vacío o solo con espacios también es `Dato faltante`;
  - un valor mal formado —`edad: "siete"`, `ocasion.tipo` fuera del `enum`— sigue siendo
    `422 peticion-invalida`;
  - `edad: 7` con un tono adulto → contradicción `edad-vs-tono`, por regla determinista, y
    se detecta aunque falten otros campos;
  - `comprador.identificador` con forma de correo → no pasa (RNF-16);
  - validar **no crea nada**: ninguna fila nueva;
  - el mismo brief sin `destinatario.nombre` enviado a `crearNovela` → `422`; uno completo
    con una contradicción → `400 brief-invalido`;
  - la lista de obligatorios que usa la validación es igual a la de `required` de
    `BriefNovela` y sus anidados **en el contrato**, leída del fichero;
  - conformidad de `validarBrief`, con `BriefNovelaParcial` como cuerpo.
- **Hecho cuando** `uv run pytest tests/intake tests/contrato -v`

#### P36 · Texto libre como contenido no confiable

- **Fase** F3 · **Cubre** RF-INTAKE-03, RNF-09, D-20 · **Skill** `backend-feature-slice`,
  `presupuesto-de-contexto`
- **Ficheros** migración `0011`; `app/intake/{saneamiento.py,patrones.txt,extraccion.py}`: los
  fragmentos sospechosos se registran y se retiran **antes** de pasar el texto al
  `interviewer`, que extrae hechos con la tool `extraer_hechos_texto_libre`.
- **Pruebas primero** (brief adversarial en `tests/fixtures/`):
  - «ignora las instrucciones anteriores» se devuelve como sospechoso, queda registrado y no
    entra en el brief;
  - con el doble, **ninguna petición al modelo contiene el fragmento**, y el resto del texto
    libre solo aparece dentro del delimitador de datos del mensaje de usuario;
  - los hechos extraídos vuelven `origen: texto-libre` y `propuesto`;
  - prueba de arquitectura: ningún camino de `app/` pasa salida del modelo a `eval`, `exec`,
    `subprocess` ni `os.system`.
- **Hecho cuando** `uv run pytest tests/intake -v`

#### P37 · `invencion_destinatario` y `temas_excluidos`

- **Fase** F3 · **Cubre** RF-QUA-06, D-13 · **Skill** `backend-feature-slice`
- **Ficheros** `app/quality/validadores/{invencion_destinatario,temas_excluidos}.py`, campos
  nuevos en la salida del `judge`.
- **Pruebas primero**
  - un capítulo que atribuye al destinatario un hecho personal ausente del brief y del texto
    libre → falla con cuenta 1 y la afirmación citada;
  - un tema excluido que aparece → falla aunque ninguna palabra vetada lo nombre;
  - ambos cierran el paso siempre, porque su umbral es cero.
- **Hecho cuando** `uv run pytest tests/quality -v`

#### P38 · Cierre de F3

- **Pruebas primero** `tests/e2e/test_f3.py`: el brief adversarial, validado por HTTP, devuelve
  el `Fragmento sospechoso`, queda registrado y descartado; generado con dobles, **ninguna**
  petición al modelo de toda la generación contiene la instrucción inyectada.
- **Opcional, real**: la misma generación con modelo real, **solo si**
  `acumulado + coste.coste_maximo_novela ≤ 40`; si no cabe, se anota como no ejecutada y no se
  para.
- **Hecho cuando** el bloque de § 4.5 con `N = 3`.

### F4 — Regeneración

#### P39 · Hechos por versión

- **Fase** F4 · **Cubre** RF-CANON-03 (endpoint) · **Skill** `backend-feature-slice`
- **Ficheros** `app/canon/router.py`. Saca `listarHechos` de `PENDIENTES`.
- **Pruebas primero**: `GET …/versiones/1/hechos` resuelve por vigencia; `?capitulo=7` devuelve
  solo los que usa el 7; `capitulos_usan` sale del puente; conformidad.
- **Hecho cuando** `uv run pytest tests/canon tests/contrato -v`

#### P40 · Solicitud de cambio por hecho y análisis de impacto

- **Fase** F4 · **Cubre** RF-VER-06, RF-VER-09 · **Skill** `sqlite-relacional`,
  `backend-feature-slice`
- **Ficheros** migración `0012`; `app/versioning/{solicitud.py,impacto.py,router.py}`. Saca
  `crearSolicitudCambio` y `obtenerSolicitudCambio` de `PENDIENTES`.
- **Pruebas primero**
  - un hecho establecido en el 2 y usado en el 7 → el análisis devuelve `[2, 7]`, sobre `usa`;
  - crear la solicitud **no regenera nada**: ningún trabajo nuevo, ninguna llamada;
  - con una generación viva → `409 generacion-en-curso`;
  - `hecho_id` inexistente → 404 `hecho-no-encontrado`; conformidad de las dos operaciones.
- **Hecho cuando** `uv run pytest tests/versioning tests/contrato -v`

#### P41 · Solicitud por fragmento

- **Fase** F4 · **Cubre** RF-VER-07, TO-011, D-19 · **Skill** `backend-feature-slice`
- **Ficheros** `app/versioning/candidato.py`; clave nueva
  `regeneracion.similitud_hecho_candidato` en `config/thresholds.yaml`, marcada provisional.
- **Pruebas primero**: un fragmento que coincide con el soporte de un hecho del capítulo de
  origen propone ese hecho como `hecho_candidato` y deja la solicitud
  `pendiente-de-confirmacion`; un fragmento sin candidato no propone nada; ninguno de los dos
  casos regenera.
- **Hecho cuando** `uv run pytest tests/versioning -v`

#### P42 · Confirmación, retcon y obsolescencia

- **Fase** F4 · **Cubre** RF-VER-08 (mitad canon), RF-CANON-05 parcial (el `Retcon` como
  mecanismo) · **Skill** `sqlite-relacional`
- **Ficheros** `app/canon/retcon.py`, `app/versioning/confirmar.py`. Saca
  `confirmarSolicitudCambio` de `PENDIENTES`.
- **Pruebas primero**
  - confirmar cierra el hecho viejo con `version_hasta = v+1` y abre el nuevo con
    `version_desde = v+1`, con su fila de `retcon`, en una transacción;
  - marca `Obsoleto` **solo** los capítulos del análisis y encola una generación `dirigida`
    con `capitulos_a_regenerar`; responde `202`;
  - la versión `v` sigue devolviendo el hecho viejo.
- **Hecho cuando** `uv run pytest tests/versioning tests/canon tests/contrato -v`

#### P43 · Regeneración dirigida y publicación de la versión nueva

- **Fase** F4 · **Cubre** RF-VER-08, RF-VER-02, RF-VER-03, D-05, D-17 · **Skill**
  `backend-feature-slice`, `presupuesto-de-contexto`
- **Ficheros** `app/process/orquestador.py` (camino `Regenerando`), validador
  `regeneracion_fiel` en el gate.
- **Pruebas primero**
  - solo se reescriben los capítulos obsoletos, con el snapshot recalculado para la versión
    objetivo;
  - la versión nueva apunta a **la misma fila de `capitulo`** para los no afectados;
  - `modificado` es `true` exactamente donde el texto cambió;
  - el hash de la versión anterior no cambia;
  - `regeneracion_fiel` falla si un capítulo no afectado cambiara o si la anterior no fuera
    consultable.
- **Hecho cuando** `uv run pytest tests/process tests/versioning -v`

#### P44 · Cierre de F4

- **Pruebas primero** `tests/e2e/test_f4.py`, con dobles: sobre una novela publicada donde el
  perro no tiene el nombre pedido, «el perro se llama Nala» produce la versión 2 con los
  capítulos afectados reescritos, **el resto idénticos byte a byte** (comparación del texto
  servido por HTTP) y la versión 1 consultable entera con su hash original.
- **Real**: el mismo cambio sobre la novela del humo, si el coste cabe (§ 1, condición 4).
- **Hecho cuando** el bloque de § 4.5 con `N = 4`.

### F5 — Salida

#### P45 · Ficha y portada

- **Fase** F5 · **Cubre** RF-VER-04, RF-VER-05 · **Skill** `backend-feature-slice`
- **Ficheros** `app/versioning/{ficha.py,portada.py}`. Saca `obtenerFicha` y `obtenerPortada`
  de `PENDIENTES`.
- **Pruebas primero**: la ficha de la versión 1 sale de la story bible **de la 1**, no de la
  vigente, con los capítulos donde aparece cada personaje y lugar (vía `evento_personaje` y
  `evento_capitulo`); la portada lleva la dedicatoria del brief; conformidad.
- **Hecho cuando** `uv run pytest tests/versioning tests/contrato -v`

#### P46 · Contrato de lectura como dato

- **Fase** F5 · **Cubre** spec § 4.4, CL-01…CL-05, TO-037 · **Skill** `backend-feature-slice`
- **Ficheros** `app/versioning/lectura.py`: la ruta, los estados de `data-estado` y la tabla
  de selectores `data-testid` de CL-03 como **un único dato** que usan `render_visual` y
  `paridad_pdf_web`; ningún selector aparece escrito fuera de este módulo.
  `STORYMAKER_LECTURA_URL` en `.env.example`. `tests/fixtures/lectura/`: una página estática
  generada desde una versión publicada que cumple el contrato, con su hoja `@media print`.
- **Pruebas primero**
  - la tabla de selectores del módulo es **igual** a la tabla CL-03 de `specs/spec1.md`,
    leída del fichero: si alguien cambia una sin la otra, la suite falla;
  - la ruta construida para `(novel_id, version)` es `/novelas/{novel_id}/versiones/{version}`
    sobre la URL base;
  - prueba de arquitectura: ningún módulo de `app/` fuera de `lectura.py` contiene la
    cadena `data-testid`;
  - la página de prueba cumple CL-01 a CL-04: un solo documento con todo, `data-estado` en
    `lista`, todos los selectores con su cardinalidad, `capitulo-modificado` solo donde
    `modificado` es `true`, y con medios `print` todos los capítulos visibles y los controles
    ocultos.
- **Hecho cuando** `uv run pytest tests/versioning/test_lectura.py tests/arquitectura -v`

#### P47 · `render_visual` con Playwright MCP

- **Fase** F5 · **Cubre** RF-QUA-03 (`render_visual`), CL-02, CL-03, CL-05, TO-026 · **Skill**
  `backend-feature-slice`
- **Ficheros** `app/versioning/render_visual.py` (cliente MCP guionizado contra
  `PLAYWRIGHT_MCP_URL`, con los selectores de `lectura.py`), `docs/browser-mcp.md` con qué
  tool del MCP da la evidencia de cada aserción.
- **Pruebas primero** (servidor MCP real, página de prueba):
  - espera a `data-estado = lista` antes de afirmar, y `error` falla el gate;
  - un selector ausente falla con el nombre del selector;
  - una página correcta pasa las cuatro aserciones: índice completo y resoluble, enlaces de la
    ficha, dedicatoria, sin errores de consola ni desbordes;
  - un enlace roto falla; si el dato no está en la story bible el fallo vuelve al rol dueño, y
    si está y no se pinta detiene como bug de maquetación **sin gastar intentos**;
  - cada aserción declara la tool MCP que le da la evidencia.
- **Hecho cuando** `uv run pytest tests/versioning/test_render_visual.py -v` con el servidor
  MCP en marcha (§ 9).

#### P48 · Export a PDF y paridad

- **Fase** F5 · **Cubre** RF-EXP-01, RF-EXP-02, TO-003, TO-025, D-22 · **Skill**
  `sqlite-relacional`, `backend-feature-slice`
- **Ficheros** migración `0013`; `app/versioning/{export.py,paridad.py}` y su `__main__` de
  línea de comandos con `<novel_id> <version>` (D-22). Emula medios `print` antes de
  `page.pdf()` (CL-04). Saca `exportarVersion` y `descargarExport` de `PENDIENTES`.
- **Pruebas primero**
  - `POST …/export` → `202` la primera vez y `200` con el mismo export después; el PDF se
    genera **una vez**;
  - `GET …/export` antes de estar → `404 export-no-disponible`; después, `application/pdf`;
  - el PDF se genera con medios `print`: sobre la página de prueba, los controles ocultos en
    impresión no aparecen en el texto del PDF;
  - `paridad_pdf_web` cuenta las palabras sobre `capitulo-texto` y pasa sobre la página de
    prueba; falla si falta un capítulo, un título,
    la dedicatoria o el índice, o si el recuento de palabras se sale de
    `export.tolerancia_recuento_palabras`;
  - conformidad de las dos operaciones.
- **Hecho cuando** `uv run pytest tests/versioning/test_export.py tests/contrato -v`

#### P49 · Cierre de F5 e integración con la lectura

- **Pruebas primero** `tests/e2e/test_f5.py`: sobre una novela publicada con dobles, ficha y
  portada por HTTP, gate con `render_visual` en verde y export con paridad. Y
  `test_conformidad_completa`: **`PENDIENTES` está vacía**.
- **Entrega**: `uv run --env-file ../.env python -m app.versioning.export <novel_id> 1` sobre
  la novela del humo, con la página `lectura` del frontend en `STORYMAKER_LECTURA_URL`, y se
  commitea `ejemplos/novela-ejemplo.pdf`. Antes, `render_visual` corre contra la página real:
  es la **prueba de integración** de que el frontend cumple la spec § 4.4.
- **Si la página `lectura` aún no existe, no es parada.** Se termina todo lo demás y
  `ejemplos/novela-ejemplo.pdf` se anota en `specs/progreso.md` § Pendiente como **pendiente
  del paso de integración P49**, con el comando exacto para generarlo. **No es un descarte**:
  es entregable obligatorio del alcance, y el plan no está cerrado hasta que el PDF esté
  commiteado.
- **Documentos al cerrar el plan** (`architecture.md` § Ciclo de cambio): la spec si algún
  comportamiento resultó distinto, `docs/verification.md` por los validadores implementados y
  los dejados fuera (D-16), y `docs/registro-iteraciones.md`. `architecture.md` ya recoge
  D-08 y D-09.
- **Hecho cuando** el bloque de § 4.5 con `N = 5`, `PENDIENTES` vacía y el PDF commiteado.
  Si el PDF queda pendiente de la lectura, la F5 se cierra y **el plan no**: el P49 sigue
  abierto en progreso hasta que el PDF exista.

---

## 8. Riesgos

| Riesgo | Qué lo contiene |
| --- | --- |
| El frontend ya generó su cliente con el contrato 1.0.0 | El cambio a 1.1.0 solo cambia el cuerpo de `validarBrief` y añade schemas; el frontend lo espera (TO-037) |
| La página `lectura` no cumple la spec § 4.4 al integrarla | El P46 fija la lista como dato comparado con la spec, y el P49 corre `render_visual` contra la página real antes de exportar |
| El OpenAPI de FastAPI no alcanza alguna forma del contrato | `json_schema_extra`, `responses=` y `openapi_extra`; si ni así, condición 2 |
| El normalizador de conformidad es demasiado generoso y no falla nunca | La meta-prueba de mutaciones del P01 |
| El coste real se dispara en el humo | Tope por novela de configuración, parada preventiva a 40 y reutilización de la misma novela en F4 y F5 |
| La página `lectura` no está cuando llega F5 | Página de prueba en `tests/` que cumple la spec § 4.4, y el PDF final como pendiente del P49, no como parada ni como descarte |
| Los validadores programáticos de F2 dan falsos positivos en cadena | `medicion.cerrar_el_paso: false` para los semánticos; los programáticos se prueban con un capítulo limpio además del defectuoso |
| `--reload` y el cerrojo de instancia chocan | El recargador tiene un solo proceso de app a la vez; la prueba de reanudación del P27 lo ejercita |
| Detectar inyecciones por patrones deja pasar paráfrasis | Residuo declarado en D-20; la contención real es RNF-09, que se prueba en el P36 |

---

## 9. Ejecutarlo en local

Desde la raíz del repositorio salvo que se diga otra cosa. En PowerShell de Windows, usa
`curl.exe` en lugar de `curl`, que ahí es un alias de otra cosa.

**Instalación**

```bash
cp .env.example .env              # y rellénalo: ANTHROPIC_API_KEY, LANGFUSE_*, STORYMAKER_*
                                  # STORYMAKER_LECTURA_URL: base del frontend, para F5
cd backend
uv sync
uv run playwright install chromium
```

**Migraciones** (también se aplican solas al arrancar)

```bash
uv run --env-file ../.env python -m app.commons.db.migrar
```

**Arranque** (solo en `127.0.0.1` y con un único worker)

```bash
uv run --env-file ../.env python -m app                          # o, en desarrollo:
uv run --env-file ../.env uvicorn app.main:app --reload --port 8000
npx -y @playwright/mcp --port 8931                               # para render_visual (F5), en otra terminal
```

**Pruebas**

```bash
uv run pytest                                  # suite completa, sin modelo real
uv run pytest tests/guardrail                  # suite propia del guardrail
uv run --env-file ../.env pytest -m real tests/humo -v   # humo real: cuesta dinero
```

**Generar una novela**

```bash
uv run --env-file ../.env python -m app.prompts.sync   # publica los prompts en Langfuse
curl -s -X POST http://127.0.0.1:8000/novelas \
  -H 'Content-Type: application/json' -d @../ejemplos/brief-ejemplo.json
# → anota novel_id
curl -s -X POST http://127.0.0.1:8000/novelas/<novel_id>/generaciones
# → anota generacion_id; sondea hasta es_terminal = true
curl -s http://127.0.0.1:8000/novelas/<novel_id>/generaciones/<generacion_id>
curl -s http://127.0.0.1:8000/novelas/<novel_id>/versiones/1/capitulos
uv run --env-file ../.env python -m app.versioning.export <novel_id> 1
```

**Verla en Langfuse.** Con `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` y `LANGFUSE_HOST` en
`.env`, abre `LANGFUSE_HOST` → *Sessions* y busca la sesión cuyo identificador es el
`novel_id`: contiene una traza por generación, cuyo id devuelve `traza_langfuse_id` en el
recurso `Generacion`. Dentro, un span por rol y por tool y un score por validador. Si
`GET /salud` dice `degradado`, las credenciales no llegaron y los spans están en el log del
proceso.

---

## 10. Trazabilidad

| Requisito | Pasos |
| --- | --- |
| RF-INTAKE-01, 02 | P12 (brief completo), P35 |
| RF-INTAKE-03 | P36, P38 |
| RF-INTAKE-04, 05 | P12 |
| RF-INTAKE-06 | post-demo, fuera de este plan |
| RF-PROC-01, 02, 04, 05 | P21 |
| RF-PROC-03 | P09, P21, P22 |
| RF-PROC-06 | P24, P27 |
| RF-PROC-07 | P13, P22 |
| RF-PROC-08, 09 | P23, P28 |
| RF-PROC-10 | P20 |
| RF-CTX-01…04 | P17 |
| RF-CTX-05 | P03 |
| RF-NOVEL-01 | P18 |
| RF-NOVEL-02, 03 | P12 |
| RF-NOVEL-04 | P19, P32 |
| RF-NOVEL-05 | P25 |
| RF-CANON-01, 02, 04 | P15, P20 |
| RF-CANON-03 | P15, P39 |
| RF-CANON-05 | post-demo; el mecanismo de retcon entra en P42 |
| RF-GUARD-01, 02 | P11 |
| RF-GUARD-03 | P16, P19 |
| RF-QUA-01 | P19 |
| RF-QUA-02 | P19, P29, P30 |
| RF-QUA-03 | P25, P33, P43, P47 |
| RF-QUA-04, 07 | P31 |
| RF-QUA-05 | P32 |
| RF-QUA-06 | P37 |
| RF-QUA-08 | post-demo |
| RF-POL-01, 02 | P16 |
| RF-VER-01…03 | P25, P43 |
| RF-VER-04, 05 | P45 |
| RF-VER-06, 09 | P40 |
| RF-VER-07 | P41 |
| RF-VER-08 | P42, P43, P44 |
| RF-EXP-01, 02 | P48, P49 |
| Spec § 4.4, CL-01…05 | P46, P47, P48, P49 |
| RF-EXP-03 | post-demo; P03 y P09 cubren el interruptor |
| RF-OBS-01, 02 | P08, P22 |
| RF-OBS-03 | P19, P28, P31 |
| RF-OBS-04 | P08, P23 |
| RF-OBS-05 | P14 |
| RF-META-01 | P09 |
| RD-01…06 | P05, P12, P15, P21, P02 |
| RNF-01 | P03, P17 |
| RNF-02, 03 | P07, P21 |
| RNF-04, 13 | P23 |
| RNF-05 | P06 |
| RNF-06 | P15 |
| RNF-07 | P25, P43 |
| RNF-08 | P08 |
| RNF-09 | P17, P36 |
| RNF-10 | P12, P17 |
| RNF-11 | P26 |
| RNF-12 | P09 |
| RNF-14, 15 | P03 |
| RNF-16, 17 | P35, P26 |
