---
estado: aprobada
aprobada-por: el desarrollador, en la conversación del 2026-09-25 («aprobado»)
fecha: 2026-09-25
spec: specs/spec4-lean.md
contrato: specs/openapi.yaml (no cambia)
progreso: specs/progreso-lean.md
---

# Plan 4 — Verificación formal de la cronología con Lean

Cómo se construye lo que especifica `specs/spec4-lean.md`, aprobada el 2026-09-25 con las
decisiones TO-064 a TO-067. Un solo plan de once pasos, escrito para que un agente lo
ejecute de forma autónoma de principio a fin y pueda reanudarlo en frío desde
`specs/progreso-lean.md`. Las reglas son las de `specs/plan1.md` § 0 y § 1; aquí se repiten
solo donde cambian.

> **Estado: aprobada** por el desarrollador el 2026-09-25. El agente **comprueba el
> frontmatter antes del L01**, no de memoria, y se detiene si no dice `aprobada`.

---

## 0. Protocolo de ejecución

El de `specs/plan1.md` § 0, sin cambios: leer progreso → cargar la skill del paso → pruebas
primero y verlas fallar por la razón correcta (`pruebas-escritas`) → código mínimo → «Hecho
cuando» más el invariante global → actualizar progreso y, si hubo decisión, sus dos rastros
en el mismo commit → commit pequeño con el número del paso (`L03: Añadir el proyecto Lake de
la cronología`). **Nunca** un commit con dos pasos.

- **Rama**: `lean-v1`, creada en el L01 desde `Contexto-semilla-v2`. Nunca `main`.
- **Directorio**: los comandos se ejecutan desde `backend/` salvo que digan otra cosa.
- **Progreso**: `specs/progreso-lean.md` se crea en el L01 con la misma forma que
  `specs/progreso.md` (Estado, Coste real, Pasos cerrados, Decisiones, Parada).
- **Decisiones del agente**: `A-NN` en progreso; si son de diseño, `TO-NNN` marcada
  **«decidido por el agente — revisar»** y entrada en el registro, en el mismo commit
  (`specs/plan1.md` § 0.3). Las que este plan ya fija están en § 3 y entran como **TO-068**
  con el commit del L01.

### 0.1 Invariante global

```bash
uv run pytest            # suite completa, verde; excluye -m real
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
```

Desde el L03 la suite incluye pruebas que ejecutan `lake build` (§ 4.2). **Lean es
dependencia declarada del stack** (`CLAUDE.md` § Requisitos técnicos), así que esas pruebas
no se saltan en silencio: si `lake` no se encuentra, fallan con un mensaje que dice dónde se
buscó.

### 0.2 Intentos

Como `specs/plan1.md` § 0.2: al tercer rojo en el mismo paso, tras escribir las pruebas, el
agente se detiene.

## 1. Condiciones de parada

Las cuatro de `specs/plan1.md` § 1, adaptadas. Ante cualquiera, el agente escribe
`specs/progreso-lean.md` § Parada, hace commit de ese fichero y se detiene.

| # | Condición | Cómo se detecta |
| --- | --- | --- |
| 1 | **Una ejecución real necesita la credencial o el proveedor y no está** | Al llegar al L09 o al L10, `config/models.yaml` pide un proveedor sin credencial en el entorno |
| 2 | **Una decisión contradice la spec, exige cambiar `specs/openapi.yaml` o un nombre nuevo en la ontología** | Más allá de lo que TO-064 a TO-067 ya añadieron. Nombres de columna (`anio`) no son ontología |
| 3 | **Tres rojos en el mismo paso** | Contador de § 0.2 |
| 4 | **El coste acumulado de llamadas reales superaría 100 USD** | Antes de cada ejecución real: si `46,47 + lo gastado en este plan + coste.coste_maximo_novela > 100`, no se lanza. Hoy caben las dos (L09 ≈ 1 USD de extracción, L10 ≤ 15 USD) |

**No son parada**, y el agente los resuelve y registra: que el build de Lean sea lento
(§ 8), que la re-extracción de la copia no encuentre nada, o que B2 no llegue a Lean
(spec § 3.11: se documenta y se construye el caso provocado).

## 2. Dependencias

**Ninguna de Python.** Lean 4 y Lake ya están en `CLAUDE.md` § Requisitos técnicos y en la
máquina (I-03: Lean 4.34.1, Lake 5.0.0, en `~/.elan/bin`). El proyecto Lake **no declara
`require`**: ni Mathlib ni Batteries (A-91). `hypothesis`, ya en el grupo dev, sirve para las
propiedades del generador.

## 3. Decisiones que fija este plan

| ID | Decisión | Porqué |
| --- | --- | --- |
| L-D01 | El generador y el ejecutor viven en `backend/app/versioning/lean/` (`generar.py`, `ejecutar.py`, `informe.py`) | `architecture.md` pone el gate en `versioning/`, que ya importa `novel/` para leer eventos y personajes |
| L-D02 | El incremental entra por el `Publicador` de `process/service.py` con un método nuevo, `lean_incremental`, implementado en `versioning/` | `process/` no puede importar `versioning/` (el grafo va al revés); es el mismo patrón que `render_visual` |
| L-D03 | Las consultas de eventos por versión viven en `novel/repository.py` con `novel_id` y `version` obligatorios y el predicado de vigencia semiabierto de `canon` (`desde ≤ v < hasta`) | TO-066 copia TO-028; mismo predicado, misma prueba de arquitectura (`test_parametros_de_dominio`) |
| L-D04 | Retirar y revertir eventos: `novel.retirar_eventos` y `novel.revertir_eventos`, llamados justo al lado de `canon.retirar_capitulo` (orquestador) y `canon.revertir_version` (`rechazar_regeneracion`), en la misma transacción | Una candidata rechazada no deja eventos vigentes en ninguna otra versión (TO-062) |
| L-D05 | Tipos Lean: identificadores `Nat` sintéticos; `anio`, `lugar` y `nacimiento` como `Option Nat`; presentes como `List (Nat × Option Nat)` (personaje, edad declarada). Solo el **año** de `fecha_nacimiento` entra | Sin Mathlib todo cabe en `Nat` y `Option`; la edad con un año de holgura no necesita mes ni día (TO-064) |
| L-D06 | Un teorema por evento e invariante (`ubicacion_e017`, `cronologia_e017`, `edad_e017`, `nacimiento_e017`), enunciado como `pred eventos e017 = true := by decide` | El nombre del teorema fallido identifica evento e invariante; con ~75 eventos son ~300 teoremas pequeños |
| L-D07 | Aritmética sin resta: edad ok ⇔ `edad + nac = anio ∨ edad + nac + 1 = anio`; nacimiento ok ⇔ `nac ≤ anio`; exclusión ok ⇔ `¬ (x.anio < e.anio)` | La resta de `Nat` trunca a cero y escondería un año anterior al nacimiento |
| L-D08 | El generador devuelve el fichero **y** un índice `línea → (invariante, evento, capítulo, personajes)`; el ejecutor traduce cada `error:` de `lake build` por su línea | El detalle del `GateEnRojo` nombra evento y capítulo sin volver a razonar en Python lo que Lean ya decidió |
| L-D09 | Cada ejecución copia `formal/lean/` a un directorio temporal, escribe allí `Cronologia/Hechos.lean` y construye el target `Cronologia.Hechos`; se borra al terminar | Dos ejecuciones no se pisan y el árbol versionado no se ensucia |
| L-D10 | `lake` se busca en `PATH` y después en `~/.elan/bin`; si no está, veredicto rojo `toolchain-ausente` en el gate y aviso en el incremental | I-03: en el shell de bash de la máquina no estaba en el `PATH` |
| L-D11 | `Trazador.score` gana `metadata` opcional; el incremental puntúa con `{"etapa": "incremental", "capitulo": n}` y el gate con `{"etapa": "gate"}` | Mismo nombre de score en las dos etapas, distinguibles en Langfuse (spec § 3.8) |
| L-D12 | `lean_nacimiento` es **O-66** en `verification.md` y entra en `quality/registro.py` como `formal-Lean` del gate | Es la O siguiente; un validador sin fila no existe |
| L-D13 | La migración `0016` rellena la vigencia de los eventos existentes desde `version_capitulo` y `version_novela`, y su prueba compara, sobre una copia de `data/storymaker-demo.db`, eventos vigentes contra eventos por `version_capitulo` en cada versión publicada | Es la única forma de saber que el relleno es correcto con datos reales |
| L-D14 | Las ejecuciones reales van a `tests/humo/` con `@pytest.mark.real`: `test_lean_copia_real.py` (L09) y `test_lean_b2_real.py` (L10). El brief B2 es ficticio y vive en `tests/fixtures/brief_b2.json` | Como el humo del plan 1; ningún dato personal real |

## 4. Estrategia de pruebas

### 4.1 Sin modelo real

Igual que el plan 1 (`ModeloGuionizado`, `RegistroTrazas`). Las extracciones nuevas llevan
fixture propio en `tests/fixtures/extracciones.py`: una con año, edad y una muerte
explícitas, y otra sin ninguna, para afirmar los nulos.

### 4.2 Pruebas con Lean

`tests/formal/` ejecuta `lake build` de verdad sobre ficheros generados. Son lentas en
segundos, no en minutos (I-03: 2,6 s en frío), y van en la suite normal. Para no pagar el
arranque en cada prueba, un fixture de sesión copia el proyecto una vez y cada prueba escribe
su `Hechos.lean`. **Nada de dobles de Lean**: un validador formal probado contra un doble no
prueba nada.

### 4.3 Estructura nueva de `tests/`

```
tests/formal/            test_proyecto.py · test_generar.py · test_ejecutar.py
tests/novel/             test_eventos_por_version.py
tests/process/           test_extraccion_temporal.py · test_lean_incremental.py
tests/versioning/        test_gate_lean.py
tests/commons/db/        test_migracion_0016.py
tests/humo/              test_lean_copia_real.py · test_lean_b2_real.py
```

## 5. Migración

`backend/app/commons/db/migrations/0016_evento_temporal.sql`, **una sola** y sin editar las
anteriores:

- `evento.anio INTEGER` (nulo permitido, `CHECK (anio IS NULL OR anio >= 0)`);
- `evento_personaje.edad INTEGER` (nulo permitido, `CHECK (edad IS NULL OR edad >= 0)`);
- `evento.version_desde INTEGER` y `evento.version_hasta INTEGER`, con el mismo `CHECK` que
  `hecho`, rellenadas en la propia migración (L-D13) y con un índice
  `(novel_id, version_desde, version_hasta)`;
- `evento_excluyente` no cambia: hereda la vigencia de su evento.

Cómo se garantiza que ningún evento nuevo nace sin versión lo decide el L01 con la skill
`sqlite-relacional` (reconstruir la tabla o `ADD COLUMN` más prueba de que ningún
`INSERT` la omite), y queda como `A-NN`.

## 6. Estructura resultante

```
formal/lean/
  lakefile.toml · lean-toolchain         sin require
  Cronologia/Basico.lean                 tipos y los cuatro predicados decidibles
  Cronologia/Ejemplo.lean                cronología fija de ejemplo: `lake build` en verde
backend/app/versioning/lean/
  generar.py                             story bible de una versión → (texto, índice)
  ejecutar.py                            copia, escribe, `lake build` con timeout
  informe.py                             salida de Lake + índice → cuatro VeredictoGate
backend/app/commons/db/migrations/0016_evento_temporal.sql
```

## 7. Pasos

Formato: **Cubre · Skill · Ficheros · Pruebas primero · Hecho cuando.**

#### L01 · Migración 0016 y vigencia de los eventos

- **Cubre** RF-LEAN-07, TO-066, spec § 5.9 · **Skill** `sqlite-relacional`,
  `backend-feature-slice`
- **Ficheros** `0016_evento_temporal.sql`; `novel/repository.py` (`insertar_evento` con
  `version`, `anio`, edades; `eventos_de_version`; `retirar_eventos`; `revertir_eventos`);
  `novel/service.py`; `process/aceptar.py` y `process/orquestador.py`
  (`_preparar_reescritura`); `versioning/service.py` (`rechazar_regeneracion`). Crea la rama,
  `specs/progreso-lean.md` y TO-068.
- **Pruebas primero**
  - `test_migracion_0016`: sobre una copia de `data/storymaker-demo.db` en `tmp_path`, tras
    migrar, para cada versión publicada, eventos vigentes = eventos de sus capítulos por
    `version_capitulo`, y ningún `momento` duplicado; ningún evento sin `version_desde`.
  - Una regeneración con dobles cierra los eventos del capítulo sustituido en la versión
    nueva y la versión anterior conserva los suyos.
  - Una regeneración rechazada deja sus eventos con intervalo vacío y reabre los cerrados.
  - `test_parametros_de_dominio` sigue en verde con las funciones nuevas.
- **Hecho cuando** `uv run pytest tests/commons/db tests/novel tests/versioning tests/arquitectura -v`

#### L02 · El extractor devuelve año, edad y eventos excluyentes

- **Cubre** RF-LEAN-06, TO-064, TO-065, spec § 5.10 · **Skill** `presupuesto-de-contexto`,
  `backend-feature-slice`
- **Ficheros** `process/schemas.py` (`EventoExtraido.anio`, presentes con edad opcional,
  `Extraccion.excluyentes` con personaje, tipo y `orden` del evento); `prompts/extractor.md`
  («solo si el texto lo dice explícitamente; si no, nulo»; muerte o partida **definitiva**
  explícitas); `process/aceptar.py` y `novel/` para consolidar; `tests/fixtures/extracciones.py`.
- **Pruebas primero**
  - La extracción con año, edad y muerte explícitas queda en `evento.anio`,
    `evento_personaje.edad` y `evento_excluyente`.
  - La extracción sin ellos deja nulos y ninguna fila en `evento_excluyente`.
  - Un excluyente que cita un `orden` inexistente o un personaje desconocido no se
    consolida y deja rastro en el audit log (no inventa el evento).
  - El presupuesto del rol extractor sigue cabiendo con el esquema nuevo (prueba existente de
    presupuesto por rol).
- **Hecho cuando** `uv run pytest tests/process tests/context tests/prompts -v`. Publicar el
  prompt en Langfuse (`app.prompts.sync`, que no tiene modo en seco) va en el L08, al activar.

#### L03 · Proyecto Lake de la cronología

- **Cubre** A-91, spec § 3.4 y § 3.5 · **Skill** — (Lean; `backend-feature-slice` para la
  prueba)
- **Ficheros** `formal/lean/lakefile.toml`, `lean-toolchain` (la versión instalada),
  `Cronologia/Basico.lean` (estructuras, los cuatro predicados `Bool` de L-D05 y L-D07),
  `Cronologia/Ejemplo.lean`, `tests/formal/test_proyecto.py`, fixture de sesión en
  `tests/formal/conftest.py`.
- **Pruebas primero**
  - `lake build` sobre el proyecto versionado termina en verde (`Ejemplo.lean` cubre una
    analepsis, un evento sin año y una edad declarada correcta).
  - Cuatro variantes escritas a mano, una por invariante, con **una** violación: el build
    falla y el error cae en la línea del teorema de ese evento.
  - Ningún `.lean` del proyecto contiene `import Mathlib` ni `require` en el `lakefile`.
- **Hecho cuando** `lake build` desde `formal/lean/` y `uv run pytest tests/formal/test_proyecto.py -v`

#### L04 · Generador determinista

- **Cubre** RF-LEAN-01, A-90, A-91, regla 11, spec § 5.1 y § 5.2 · **Skill**
  `backend-feature-slice`
- **Ficheros** `versioning/lean/generar.py`, `tests/formal/test_generar.py`.
- **Pruebas primero**
  - Propiedad (`hypothesis`): la misma story bible da el mismo texto byte a byte; permutar
    el orden de inserción de filas no lo cambia.
  - El fichero no contiene ninguna descripción, nombre de personaje ni de lugar de la base
    (se siembran cadenas marcadas y se buscan), ni `import Mathlib`.
  - Solo entran los eventos vigentes en la versión pedida; con `hasta_numero`, solo los de
    capítulos hasta ese número (para el incremental).
  - El índice cubre cada teorema generado y apunta a evento y capítulo reales.
- **Hecho cuando** `uv run pytest tests/formal/test_generar.py -v`

#### L05 · Ejecutor e informe

- **Cubre** RF-LEAN-02, O-13, O-14, O-15, O-66, spec § 5.3 a § 5.5 y § 5.7 · **Skill**
  `backend-feature-slice`
- **Ficheros** `versioning/lean/ejecutar.py` (subproceso asíncrono con
  `formal.lean_timeout_segundos`, L-D09, L-D10), `versioning/lean/informe.py`,
  `tests/formal/test_ejecutar.py`.
- **Pruebas primero**, con story bibles sintéticas en una base temporal y `lake` real:
  - una por invariante con una violación: falla **solo** el veredicto de esa invariante, y
    su detalle nombra evento, capítulo y personaje;
  - analepsis (evento narrado después con año anterior): los cuatro en verde;
  - evento sin año, personaje sin nacimiento, edad no declarada: verde y recuento de «sin
    comprobar» correcto en el detalle;
  - mismo año en nacimiento y en exclusión: verde;
  - timeout (valor diminuto por configuración de la prueba) y `lake` inexistente: los cuatro
    en rojo con motivo `timeout` o `toolchain-ausente`, nunca excepción.
- **Hecho cuando** `uv run pytest tests/formal -v`

#### L06 · Lean en el gate de publicación

- **Cubre** RF-LEAN-03, RF-LEAN-05, P-64, P-82, regla 16, spec § 5.6 y § 5.8 · **Skill**
  `backend-feature-slice`
- **Ficheros** `process/service.py` (`Publicador.lean`), `process/orquestador.py` (`_cerrar`:
  los veredictos de Lean se suman a los del gate cuando `formal.gate_activo`),
  `versioning/service.py`, `quality/registro.py` (`lean_nacimiento`, L-D12),
  `commons/observabilidad/` (`metadata` en `score`, L-D11, y el doble), 
  `tests/versioning/test_gate_lean.py`.
- **Pruebas primero** (con `gate_activo: true` en la configuración de la prueba):
  - candidata con una violación: `GateEnRojo`, candidata `rechazada`, detalle con la
    invariante y el evento, audit log con el fallo; en una regeneración, la versión
    publicada intacta con su hash;
  - candidata limpia: publica;
  - con `gate_activo: false`, Lean no corre y no hay scores `lean_*`;
  - un span `lean` y cuatro scores con `etapa = gate` en `RegistroTrazas`.
- **Hecho cuando** `uv run pytest tests/versioning tests/process tests/quality tests/e2e -v`

#### L07 · Chequeo incremental por capítulo

- **Cubre** RF-LEAN-04, P-81, TO-016, spec § 5.7 · **Skill** `backend-feature-slice`
- **Ficheros** `process/orquestador.py` (tras la transacción que acepta un capítulo, fuera
  de ella), `versioning/service.py` (`lean_incremental`), `policy/` para la entrada del audit
  log, `tests/process/test_lean_incremental.py`.
- **Pruebas primero**
  - un capítulo aceptado con una violación: cuatro scores `etapa = incremental`, entrada en
    el audit log, y el capítulo sigue `Aceptado` y la generación sigue;
  - `lake` ausente o timeout en el incremental: aviso, sin excepción ni cambio de estado;
  - con `lean_incremental: false`, no corre.
- **Hecho cuando** `uv run pytest tests/process tests/e2e -v`

#### L08 · Medir el timeout y activar el gate

- **Cubre** spec § 3.9, § 3.12, § 5.11 · **Skill** — (`config/` es paso 1 de la cadena)
- **Qué se hace**: generar el fichero de la versión con más eventos de la base de la demo
  (tras migrar una copia), `lake clean` y cronometrar tres `lake build` en frío; fijar
  `formal.lean_timeout_segundos` ≈ 10 × la mediana, con la medida en el comentario
  `[provisional — calibrar tras la demo]`; `formal.gate_activo: true`; publicar el prompt
  del extractor (`uv run python -m app.prompts.sync`); `GET /salud` dice
  `gate_lean_activo: true` (prueba existente, actualizada).
- **Hecho cuando** la suite en verde con la configuración real y la medida anotada en
  progreso y en `config/thresholds.yaml`.

#### L09 · Datos reales en una copia de la versión 3

- **Cubre** spec § 3.10, TO-067 · **Skill** `presupuesto-de-contexto` (el extractor corre de
  verdad)
- **Ficheros** `tests/humo/test_lean_copia_real.py` (`@pytest.mark.real`).
- **Qué se hace**: comprobar el tope de coste (§ 1, condición 4); copiar
  `data/storymaker-demo.db` a `tmp_path`, migrar, volver a extraer con el extractor real los
  capítulos de la versión 3 publicada de la novela de la demo **en la copia**, reemplazando
  solo sus filas de eventos, y pasar el generador y `lake build`. La base real no se abre en
  escritura (la prueba lo afirma comparando su hash antes y después).
- **Hecho cuando** la prueba termina —verde o con violaciones— y su resultado está en
  progreso y en `docs/red-team.md` (eventos con año, sin comprobar, violaciones y si alguna
  es real). Un rojo de Lean aquí **no** es rojo de la prueba: es un hallazgo.

#### L10 · El caso B2

- **Cubre** RF-LEAN-08, P-83, TO-067, spec § 3.11 y § 5.12 · **Skill** —
- **Ficheros** `ejemplos/evaluacion/brief-b2-incoherencia-temporal.json` —**exactamente** el
  brief que usará la evaluación, ficticio: el destinatario conoce a alguien en un año anterior
  al nacimiento que el mismo brief declara—, `ejemplos/evaluacion/resultado-b2.json` y
  `tests/humo/test_lean_b2_real.py`. (Ajuste del desarrollador al aprobar: sustituye a
  `tests/fixtures/brief_b2.json` de L-D14.)
- **Qué se hace**: comprobar el tope de coste; generar la novela B2 completa con el gate
  activo sobre una base temporal; registrar coste en progreso. **El resultado se guarda para
  que la evaluación lo reutilice sin regenerar** mientras el código no cambie: commit de
  código con que se generó, traza de Langfuse, scores de todos los validadores, veredictos
  del gate, versión, coste y desenlace, en `ejemplos/evaluacion/resultado-b2.json`.
- **Tres desenlaces, todos documentados en `docs/red-team.md`**:
  1. Lean rechaza la versión y el resto del gate y de los validadores de capítulo estaban en
     verde: **caso real**.
  2. Otro validador lo caza antes (o la entrevista lo para): se documenta quién y por qué, y
     se construye el caso **provocado**: la misma story bible con el año del evento que el
     texto sí dice, inyectado en una copia, donde solo Lean falla.
  3. El texto no llega a decir el año o la edad (la incoherencia no entra en la story bible):
     igual que 2, con la causa.
- **Hecho cuando** el desenlace está escrito con traza, versión, evento, salida de
  `lake build` y veredictos del resto, etiquetado «real» o «provocado».

#### L11 · Cierre

- **Cubre** spec § 3.12 y `CLAUDE.md` § Ciclo de cambio (al cerrar un plan)
- **Documentos**: `docs/verification.md` (O-13, O-14, O-15 con su nuevo enunciado, O-66,
  P-81, P-82, P-83 → `D`, A-90, A-91 ejecutándose; se retira el párrafo «el gate de Lean está
  apagado»); `docs/architecture.md` § Lean (timeout medido, cuatro scores, diagrama);
  `specs/spec1.md` (RF-EXP-03 deja de ser `[post-demo]`); la spec 4 si algo resultó
  distinto; `specs/progreso.md` § Post-demo (Lean hecho); `docs/registro-iteraciones.md`.
- **Hecho cuando** el invariante global en verde, `lake build` en verde, progreso con el plan
  cerrado, y commit y **push** de la rama `lean-v1`.

## 8. Riesgos

| Riesgo | Qué lo contiene |
| --- | --- |
| `by decide` se vuelve lento con ~300 teoremas | L08 lo mide; si pasa de 30 s en frío, se agrupan teoremas por capítulo manteniendo el índice por evento. `native_decide` solo como `A-NN` con sus dos rastros |
| El relleno de la vigencia no cuadra con alguna versión | La prueba del L01 sobre la copia real lo detecta antes de tocar nada más |
| El extractor inventa años o muertes pese al prompt | Las pruebas del L02 cubren el esquema; el L09 lo mide con texto real y lo documenta |
| La salida de Lake cambia de formato entre versiones | `lean-toolchain` fija la versión; el informe falla en rojo si no reconoce un error, nunca en verde |
| B2 no llega a Lean | Spec § 3.11: caso provocado etiquetado como tal |
| Añadir Lean al gate alarga cada publicación | Segundos (I-03); el span `lean` lo mide en cada ejecución |

## 9. Trazabilidad

| Requisito | Pasos |
| --- | --- |
| RF-LEAN-01 | L04 |
| RF-LEAN-02 | L03, L05 |
| RF-LEAN-03 | L06 |
| RF-LEAN-04 | L07 |
| RF-LEAN-05 | L06, L07 |
| RF-LEAN-06 | L02 |
| RF-LEAN-07 | L01 |
| RF-LEAN-08 | L10 |
| Timeout medido y gate activo | L08 |
| Copia de la versión 3 | L09 |
| Documentos de cierre | L11 |
