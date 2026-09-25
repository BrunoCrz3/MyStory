# Progreso del plan 4 — Lean

Fichero de reanudación de `specs/plan4-lean.md`. **Se actualiza al cerrar cada paso, en el
mismo commit que el paso.** Si la sesión se corta, se retoma leyendo solo esto y el paso que
indica.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan4-lean.md`, **aprobado** por el desarrollador el 2026-09-25 |
| Paso actual | L07 |
| Estado del paso | pendiente |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `lean-v1` (desde `Contexto-semilla-v2`) |
| Último commit de paso | L06 |

**Ajuste del desarrollador al aprobar** (2026-09-25):
- **L10**: exactamente el brief de incoherencia temporal que usará la evaluación, guardado en
  `ejemplos/evaluacion/`, y su resultado registrado (versión de código, traza, scores y coste)
  para que la evaluación lo reutilice sin regenerar si el código no cambia.
- El README dice que las pruebas de Lean exigen `lake` en todo entorno donde corra la suite.
- Push de `lean-v1` al cerrar cada paso importante.

## Coste real

Tope de parada: **100 USD** acumulados (plan 1, TO-048). Acumulado al empezar este plan:
**46,47 USD** (`specs/progreso.md` § Coste real).

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |

## Pasos cerrados

- **L01** — Migración `0016_evento_temporal`: `evento.anio`, `evento_personaje.edad` y la
  vigencia `version_desde`/`version_hasta` del evento, rellenada desde `version_capitulo`;
  `novel.eventos_de_version`, `retirar_eventos` y `revertir_eventos`, llamados junto a los de
  `canon`. Comprobado sobre una copia de `data/storymaker-demo.db`: en las versiones 1 y 3
  publicadas y en la 1 rechazada de la otra novela, eventos vigentes = eventos por
  `version_capitulo` (70, 72 y 72), sin momentos duplicados; la 2 rechazada ve los 70 de la 1,
  que es lo esperado tras revertirla. 504 pruebas.

- **L02** — El extractor devuelve `anio` y `edades` por evento y `excluyentes` (personaje, tipo,
  orden), todos obligatorios en el esquema y nulos o vacíos si el texto no los dice; el prompt
  lo ordena explícitamente. La aceptación los consolida; una edad de alguien ausente del
  evento, un valor negativo o un excluyente sin evento o sin personaje no entran, y el
  excluyente descartado deja `excluyente-sin-evento` en el audit log. 509 pruebas.

- **L03** — Proyecto Lake en `formal/lean/` (Lean 4.34.1, sin `require`): `Cronologia/Basico.lean`
  con los tipos y los cuatro predicados `Bool` (L-D05, L-D07) y `Cronologia/Ejemplo.lean` en
  verde (analepsis, evento sin año, edad antes del cumpleaños, exclusión del mismo año). Cuatro
  variantes con una violación fallan cada una solo en la línea de su teorema. `lake` se busca
  con `app/versioning/lean/toolchain.py` (L-D10), que ya lo encuentra en `~/.elan/bin` sin
  tocar el PATH. README: Lean es obligatorio donde corra la suite. Build del proyecto en frío,
  3,6 s.

- **L04** — `versioning/lean/generar.py`: `leer_cronologia` (eventos vigentes en la versión, con
  `hasta_numero` para el incremental; excluyentes de esos eventos; años de nacimiento) y
  `generar` (módulo `Cronologia.Hechos` con cuatro teoremas por evento y el índice línea →
  teorema). Propiedades con `hypothesis`: mismo fichero en cualquier orden de filas, sin
  Mathlib ni texto libre, índice completo. `novel` gana `personajes_por_id` y
  `excluyentes_de_version`.

- **L05** — `versioning/lean/ejecutar.py` (`verificar`: copia el proyecto con su `.lake`, escribe
  `Hechos.lean`, `lake build Cronologia.Hechos` con timeout, borra la copia) e `informe.py`
  (errores por línea → cuatro veredictos con evento, capítulo, momento, año y presentes; recuento
  de «sin comprobar»; un error fuera de los teoremas, un timeout o sin `lake` → las cuatro en
  rojo). Diez pruebas con `lake` real: una violación por invariante falla solo esa; analepsis,
  datos vacíos y mismo año en verde. `EventoVigente` gana `descripcion` para el informe (nunca
  entra en el fichero: la propiedad de A-91 la siembra). 529 pruebas.

- **L06** — Lean en el gate: `Publicador.lean` (puerto en `process/`, implementado en
  `versioning/` con `leer_cronologia` + `verificar`) y `Orquestador._lean`, con span `lean`
  (estado, duración, bytes, eventos) y los cuatro scores con `metadata = {"etapa": "gate"}`;
  corre con `formal.gate_activo` y sus veredictos entran en `GateEnRojo`. `Trazador.score` gana
  `metadata` (Langfuse `create_score` la admite). `lean_nacimiento` en el registro y en
  `verification.md` (O-66). Pruebas con `lake` real: candidata con violación rechazada y detalle
  con capítulo y personaje en el audit log; limpia publicada; gate apagado sin Lean;
  regeneración en rojo con la 1 intacta. 533 pruebas.

## Decisiones

| ID | Paso | Decisión | Porqué | Rastro |
| --- | --- | --- | --- | --- |
| A-01 | L01 | `version_desde` se añade con `ADD COLUMN` nula y dos triggers impiden insertar o dejar un evento sin ella | Reconstruir `evento` exige `DROP TABLE` con tres tablas que la referencian y las claves foráneas activas dentro de la transacción de la migración | TO-068 |
| A-03 | L03 | Los hechos se escriben con constructores explícitos (`Evento.mk id momento anio lugar presentes`), no con `{ campo := … }` | La instancia de estructura partida en varias líneas no parseó en 4.34.1; los constructores caben en una línea por evento y el generador no depende del sangrado | — |
| A-02 | L01 | En el relleno, lo escrito por una **regeneración** rechazada queda con intervalo vacío; una **primera** versión rechazada en el gate conserva sus eventos | Es lo que hizo TO-062 con los hechos: solo `rechazar_regeneracion` revierte; la primera versión rechazada no se revierte | TO-068 |

## Decisiones de L05

| ID | Paso | Decisión | Porqué | Rastro |
| --- | --- | --- | --- | --- |
| A-05 | L06 | Un solo método `Publicador.lean(db, novel_id, version, hasta_numero=None)` para gate e incremental, en vez de `lean` y `lean_incremental` | Es la misma ejecución sobre un prefijo; la etapa la pone el orquestador en el span y en los scores | — |
| A-04 | L05 | La prueba de RNF-09 admite un segundo proceso: `asyncio.create_subprocess_exec` en `versioning/lean/ejecutar.py` | Argumentos fijos (`lake build Cronologia.Hechos`) sobre un fichero sin texto libre; la salida del modelo sigue sin poder llegar a un proceso | TO-069 |

## Parada

Ninguna.
