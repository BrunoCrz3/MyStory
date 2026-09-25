# Progreso del plan 4 — Lean

Fichero de reanudación de `specs/plan4-lean.md`. **Se actualiza al cerrar cada paso, en el
mismo commit que el paso.** Si la sesión se corta, se retoma leyendo solo esto y el paso que
indica.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan4-lean.md`, **aprobado** por el desarrollador el 2026-09-25 |
| Paso actual | L02 |
| Estado del paso | pendiente |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `lean-v1` (desde `Contexto-semilla-v2`) |
| Último commit de paso | L01 |

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

## Decisiones

| ID | Paso | Decisión | Porqué | Rastro |
| --- | --- | --- | --- | --- |
| A-01 | L01 | `version_desde` se añade con `ADD COLUMN` nula y dos triggers impiden insertar o dejar un evento sin ella | Reconstruir `evento` exige `DROP TABLE` con tres tablas que la referencian y las claves foráneas activas dentro de la transacción de la migración | TO-068 |
| A-02 | L01 | En el relleno, lo escrito por una **regeneración** rechazada queda con intervalo vacío; una **primera** versión rechazada en el gate conserva sus eventos | Es lo que hizo TO-062 con los hechos: solo `rechazar_regeneracion` revierte; la primera versión rechazada no se revierte | TO-068 |

## Parada

Ninguna.
