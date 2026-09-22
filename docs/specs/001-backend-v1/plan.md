---
estado: borrador
aprobada-por:
fecha: 2026-09-22
---

# Plan de implementación — Backend v1

Cómo se construye lo que especifica `spec.md`, aprobada el 2026-09-22. Pasos ordenados,
ficheros que se tocan, migraciones, **la prueba que falla primero en cada paso** y el
criterio de terminado.

> **Estado: borrador, no aprobado.** Según «Ciclo de cambio» de `AGENTS.md`, **no se
> escribe código hasta que este plan esté `aprobado`**, y quien aprueba es el autor.

---

## Por qué el orden es de abajo arriba

La tentación es un esqueleto que ande: cablear el ciclo entero con piezas falsas y
rellenarlas después. **Aquí no se puede**, y no por gusto: la regla 8 de `AGENTS.md`
prohíbe los mocks en código de producción, «ni siquiera temporales». Un ciclo cableado
con stubs es exactamente eso.

Así que se construye por capas de dependencia, y el ciclo de punta a punta —criterio 2 de
aceptación— no cierra hasta H7. A cambio, cada hito entrega algo que funciona de verdad y
ninguna prueba se escribe contra un andamio que luego hay que tirar.

**Dentro de cada hito, el orden es TDD sin excepción**: la prueba primero, se comprueba
que falla por la razón correcta, luego el código mínimo que la pasa, luego refactor.

---

## Secuencia

| Hito | Qué entrega | Migración | Cierra |
| --- | --- | --- | --- |
| H1 | `commons/`: base, migraciones, errores, tokens, cliente del modelo | 001 | RNF-02, RNF-03, RNF-08, RNF-12, RNF-14, RI-04 |
| H2 | `novel/`: la obra y sus entidades existen y tienen estado | 002 | RF-NOVEL-01 a 06, RNF-07, RNF-11 |
| H3 | `canon/`: la verdad en `t`, y consolidar | 003 | RF-CANON-01 a 15 |
| H4 | `context/`: ensamblado, presupuesto y recuperación híbrida | 004 | RF-CTX-01 a 12, RNF-01 |
| H5 | `quality/`: la puerta de higiene y el contraste contra canon | 005 | RF-QUA-01 a 09 |
| H6 | `process/`: briefs, versiones, orquestación, trazabilidad y deriva | 006 | RF-PROC-01 a 13, RNF-05, RNF-06, RNF-09, RNF-10, RNF-13 |
| H7 | `findings/`: extracción y adopción. **Aquí cierra el ciclo** | 007 | RF-FIND-01 a 05 |
| H8 | API completa y OpenAPI estable | — | RI-01 a 07 |
| H9 | Las 21 preguntas de competencia y la traza | — | RNF-04, criterio 3 |

**Las nueve restricciones de diseño (`RD-01` a `RD-09`) no tienen hito**: no se
entregan, se respetan en todos. La rodaja vertical, el SQL explícito, la regla de
importación y el contrato de agente cerrado los vigila CI en cada commit, no una prueba
al final. `RF-QUA-10` a `RF-QUA-13` tampoco aparecen: quedan fuera de v1 (§1.3).

---

## H1 · `commons/` — el suelo

**Ficheros.** `app/main.py`, `commons/db/conexion.py`, `commons/db/migraciones.py`,
`commons/db/migrations/001_base.sql`, `commons/errores.py`, `commons/http.py`,
`commons/tokens/contador.py`, `commons/llm/cliente.py`, `commons/config.py`.

**Migración 001.** La tabla de control de migraciones —número, nombre, hash, fecha— y las
cuatro tablas del árbol estructural: `obra`, `parte`, `capitulo`, `escena`.

**Pruebas, en este orden:**

1. `test_migraciones_se_aplican_en_orden_y_el_hash_cuadra` — falla primero porque no hay
   runner. Es la que protege la regla 5 de `AGENTS.md`: una migración commiteada no se
   edita (`A-19`, RNF-03).
2. `test_wal_esta_activado_en_la_conexion` (`A-18`, RNF-02).
3. `test_un_error_de_dominio_sale_por_el_handler_central_con_su_http` (`A-36`, RI-04).
4. `test_el_arranque_falla_si_falta_un_umbral_que_cierra_el_paso` — y su gemela,
   `test_el_arranque_no_falla_por_un_umbral_null_en_fase_de_medicion` (`A-41`, RF-QUA-05).
5. `test_el_contador_de_tokens_corre_antes_de_la_llamada` (`A-02`, RF-CTX-03).
6. `test_toda_llamada_al_modelo_lleva_timeout_explicito` (`A-35`, RI-06).

**Terminado cuando** `uv run pytest` pasa, `ruff` y el comprobador de tipos están en CI, y
el arranque lee `config/thresholds.yaml` sin ninguna cifra escrita en el código (`A-40`).

---

## H2 · `novel/` — la obra existe

**Ficheros.** `novel/router.py`, `schemas.py`, `models.py`, `service.py`, `repository.py`.

**Migración 002.** Entidades narrativas de la Capa 1 —incluidas `Evento` y `Objetivo`, que
entraron al homologar la ontología— y la tabla puente `evento_escena` para la relación N:M
`se narra en`.

**Pruebas, en este orden:**

1. `test_la_escena_no_admite_transiciones_fuera_del_diagrama` — model checking sobre los
   cinco estados. Falla primero porque no hay máquina. **La extracción no es un estado**
   (`A-29`, RF-NOVEL-04).
2. `test_las_cardinalidades_1_1_tienen_restriccion_unique` — `Escena→Snapshot`,
   `Brief→Escena`, `Informe→Borrador` (`A-21`, §7).
3. `test_evento_escena_es_n_m_con_tabla_puente` (`A-22`, RF-NOVEL-03).
4. `test_los_nombres_de_las_clases_coinciden_con_la_ontologia` — comprobador sobre los
   `models.py`, corre en CI (`A-23`, RNF-07).
5. `test_un_novum_sin_regla_con_limites_no_valida` y
   `test_un_acto_sin_punto_de_giro_no_valida` (`A-51`, RF-NOVEL-06).

**Terminado cuando** se puede crear una obra entera —partes, capítulos, escenas,
personajes, lugares, novum, reglas— por API y consultarla.

---

## H3 · `canon/` — la verdad en `t`

El hito más largo y el que más invariantes tiene. Quince requisitos.

**Ficheros.** La rodaja completa de `canon/`.

**Migración 003.** `hecho_canonico` con su `CHECK` de cinco valores —con `implícito`, sin
`descartado`—, `snapshot_mundo`, `estado_epistemico`, `promesa_narrativa` con su `CHECK`,
`revelacion`, `contradiccion`, `retcon`, y las siete relaciones que añadió la
homologación.

**Pruebas, en este orden:**

1. `test_un_borrador_rechazado_no_deja_rastro_en_el_canon` — pruebas basadas en
   propiedades. Va primero a propósito: es el invariante cuyo incumplimiento contamina
   todo lo demás y no se nota hasta mucho después (`A-27`, RF-CANON-07).
2. `test_solo_la_transicion_a_aceptada_escribe_en_el_canon` (`A-28`).
3. `test_consolidar_es_idempotente_por_scene_id_y_version` (`A-16`, RF-CANON-08).
4. `test_toda_escritura_al_canon_ocurre_en_transaccion` (`A-17`).
5. `test_el_ciclo_de_vida_del_hecho_no_admite_transiciones_extra` y su gemela para
   `Promesa narrativa` (`A-30`, `A-31`).
6. `test_refutado_y_rota_no_tienen_transicion_de_salida` (`A-33`, RF-CANON-10).
7. `test_el_snapshot_es_derivado_y_nunca_texto_bruto` (RF-CANON-03).
8. `test_todo_cambio_entre_snapshots_tiene_un_hecho_detras` (`P-39`, RF-CANON-12).
9. `test_una_promesa_pagada_tiene_escena_de_apertura_anterior` (`P-45`, RF-CANON-13).
10. `test_un_hecho_con_alcance_abierto_sigue_vigente_hasta_que_otro_lo_cierre`
    (`P-48`, RF-CANON-15).
11. `test_los_terminos_de_un_hecho_aparecen_en_la_escena_que_lo_establece`
    (`A-48`, RF-CANON-11).
12. `test_simular_un_retcon_no_marca_nada_obsoleto` — v1 responde, no aplica
    (RF-CANON-09, §1.3).

**Terminado cuando** se puede consolidar una escena aceptada, derivar el snapshot en `t` y
responder qué escenas quedarían invalidadas por un retcon sin aplicarlo.

---

## H4 · `context/` — qué ve el modelo

**Ficheros.** Rodaja de `context/`, más las skills del sistema `ensamblar-contexto`,
`recuperar-fragmentos`, `construir-anticontexto` y `muestrear-voz`.

**Migración 004.** Tablas virtuales `vec0` junto a las relacionales, y `embedding_model` y
`embedding_version` en cada fila de embedding.

**Pruebas, en este orden:**

1. `test_ningun_ensamblado_supera_contexto_total` — pruebas basadas en propiedades. Falla
   primero porque no hay ensamblador. Es el límite duro de `AGENTS.md` (`A-01`, RNF-01).
2. `test_un_ensamblado_que_no_cabe_lanza_error_y_no_trunca` (`A-03`, RF-CTX-04).
3. `test_si_una_capa_desborda_se_comprime_esa_capa_sin_robar_a_otra` (`A-04`, RF-CTX-05).
4. `test_la_degradacion_sigue_el_orden_y_para_en_cuanto_cabe` (`A-05`, RF-CTX-06).
5. `test_la_capa_invariante_y_la_restriccion_de_destino_nunca_se_degradan` (`A-06`).
6. `test_las_siete_capas_mas_el_margen_suman_el_total` (`A-07`, RF-CTX-02).
7. `test_la_recuperacion_filtra_por_entidades_antes_de_ordenar_por_similitud`
   (`A-10`, RF-CTX-07).
8. `test_el_texto_narrativo_entra_marcado_como_datos` (`A-11`, RF-CTX-11).
9. `test_un_cambio_de_modelo_de_embeddings_falla_al_arrancar_y_pide_reindexar`
   (`A-42`, RF-CTX-10).
10. `test_el_anticontexto_olvida_fuera_de_su_ventana` (RF-CTX-08) y
    `test_el_anticontexto_incluye_lo_ya_presentado_y_lo_ya_vigente` (`P-46`, RF-CTX-12).

**Terminado cuando** se ensambla el contexto de una escena dentro de presupuesto, con las
siete capas, y se puede consultar el reparto resultante por API.

---

## H5 · `quality/` — la puerta y el contraste

**Ficheros.** Rodaja de `quality/`, más las skills `medir-calidad` y
`verificar-continuidad`.

**Migración 005.** `informe_critica`, `defecto` y `dimension_calidad`.

**Pruebas, en este orden:**

1. `test_un_borrador_con_metatexto_del_modelo_no_entra_al_ciclo` — y sus hermanas para
   rechazo, truncamiento a mitad de frase, placeholder, mezcla de idiomas, formato roto y
   longitud fuera de objetivo. **Va primera de todo el hito** porque es determinista, vale
   milisegundos y protege el punto único de promoción: sin ella, «Aquí tienes la escena»
   acaba en el canon y en `training_samples` (`A-47`, RF-QUA-06).
2. `test_la_continuidad_detecta_un_hecho_que_contradice_el_canon` — los cuatro ejes, más
   los tres que entraron con la auditoría: personaje no vivo que actúa (`P-37`), artefacto
   que cambia de dueño sin escena (`P-38`), revelación por debajo de su escena mínima
   (`P-40`) y el olvido epistémico (`P-51`) (RF-QUA-01).
3. `test_el_borrador_respeta_la_persona_y_el_tiempo_verbal_de_voz_narrativa` y
   `test_una_escena_tiene_un_solo_pov` (`P-42`, RF-QUA-09).
4. `test_el_informe_liga_cada_defecto_a_la_dimension_que_viola` (RF-QUA-03).
5. `test_un_defecto_se_clasifica_como_local_o_sistemico` (RF-QUA-04).
6. `test_tras_corregir_se_reejecutan_todos_los_validadores` (`A-49`, RF-QUA-07).
7. `test_ninguna_correccion_empeora_una_dimension_que_ya_pasaba` (`A-50`, RF-QUA-08).
8. `test_en_fase_de_medicion_ninguna_puntuacion_suspende` — y que la fase sea consultable,
   no un silencio (criterio 4, § Puntos ciegos #15).

**Terminado cuando** un borrador pasa la puerta, recibe su informe con defectos
clasificados y ninguna puntuación suspende porque la fase está abierta.

---

## H6 · `process/` — el ciclo

**Ficheros.** Rodaja de `process/`, la máquina de estados del orquestador, el pool en
vuelo en `commons/tokens/`, y la skill `registrar-generacion`.

**Migración 006.** `brief_escena`, `restriccion_destino`, `borrador`, `version`,
`registro_generacion`, `training_samples` y las dos tablas de deriva: `deriva_medicion`
—numerador y denominador **por separado** de cada componente, densidad de declaración,
`plan_hash` y `definicion_version`— y `deriva_ingrediente`, que guarda qué elemento falla
y por qué. Separar numerador de denominador no es cosmético: una proporción sola no se
puede recalcular si mañana cambia la definición del denominador.

**Pruebas, en este orden:**

1. `test_solo_el_autor_transiciona_una_escena_a_aceptada` — guardarraíl. Falla primero y
   es el que no se puede relajar nunca: es el último cortafuegos de la resistencia a
   inyección (`P-19`, RF-PROC-07).
2. `test_el_orquestador_elige_el_siguiente_paso_leyendo_el_estado_de_la_escena` y
   `test_ningun_agente_invoca_a_otro` (`P-32`, RF-PROC-05).
3. `test_al_agotar_las_iteraciones_la_escena_se_queda_en_revision_y_escala`
   (`P-33`, RF-PROC-06).
4. `test_registrar_generacion_corre_en_toda_llamada_al_modelo` (`A-45`, RF-PROC-04).
5. `test_un_trabajo_no_arranca_sin_presupuesto_en_vuelo_libre`,
   `test_la_admision_es_fifo_y_nadie_adelanta` y
   `test_un_trabajo_que_no_cabe_entero_falla_al_encolarse` (`P-36`, RNF-10).
6. `test_solo_entra_en_training_samples_texto_aceptado_y_editado` — append-only y sin
   lectura en v1 (`A-46`, RF-PROC-09).
7. **La deriva, en cinco pruebas** (RF-PROC-08, RF-PROC-12, RF-PROC-13). La definición
   está cerrada desde el 2026-09-22, así que aquí ya se verifica la medida y no solo el
   registro:
   - `test_la_deriva_vale_cero_tras_un_hito_de_plan` — el plan que el autor acaba de
     escribir describe la obra por construcción.
   - `test_una_escena_que_cumple_su_restriccion_sin_hechos_nuevos_no_mueve_la_deriva` —
     es la prueba de que el descubrimiento del *cómo* no cuenta (`P-01`).
   - `test_matar_a_un_personaje_que_una_restriccion_futura_necesita_sube_invalidacion` —
     con el fixture de mutación de canon, que toca un componente y deja los otros dos
     quietos.
   - `test_la_deriva_es_determinista_para_el_mismo_canon_y_el_mismo_plan_hash` — sin esto
     el histórico no sirve para calibrar.
   - `test_solo_invalidacion_es_monotona` — y sus controles negativos:
     `canon_huerfano` **baja** al cerrar un hilo e `inviabilidad_pago` **baja** al pagar
     una promesa. Probar monotonía en los tres convertiría un acierto del sistema en un
     fallo.
8. `test_una_medicion_con_densidad_bajo_umbral_se_reporta_no_fiable` — no basta con que
   salga baja: un esquema que no declara nada tiene deriva cero para siempre
   (RF-PROC-08, `P-53`).
9. `test_los_ingredientes_bastan_para_recalcular_el_vector_sin_regenerar_nada` — se
   recalcula el vector desde `deriva_ingrediente` y tiene que dar lo mismo que la
   columna. Es la prueba que hace del histórico algo aprovechable (RF-PROC-12).
10. `test_un_borrador_no_satisface_el_destino_de_un_brief_posterior` (`P-41`, RF-PROC-11).

**Terminado cuando** el orquestador lleva una escena de `planificada` a `en revisión` sin
que ningún agente decida el paso siguiente.

---

## H7 · `findings/` — el ciclo cierra

**Ficheros.** Rodaja de `findings/` y la skill `extraer-hallazgos`.

**Migración 007.** `hallazgo` con su `CHECK` de cinco estados —empezando en `propuesto`,
nunca en `provisional`— y `extraccion`.

**Pruebas, en este orden:**

1. `test_un_hallazgo_entra_como_propuesto_y_solo_el_autor_lo_adopta` (`P-21`, RF-FIND-02,
   RF-FIND-05).
2. `test_el_ciclo_de_vida_del_hallazgo_incluye_conflictivo` (`A-32`, RF-FIND-03).
3. `test_la_consolidacion_es_el_unico_punto_de_promocion_a_memoria_larga`
   (RF-FIND-04).
4. `test_un_hallazgo_propuesto_no_entra_en_el_contexto_como_si_fuera_canon` — cubre el
   punto ciego declarado de `P-21`.
5. **`test_ciclo_completo_de_punta_a_punta`**: brief → contexto dentro de presupuesto →
   borrador → puerta de higiene → crítica → verificación → aceptación del autor →
   consolidación → hallazgos `propuesto`. Es el criterio 2 de aceptación y aquí es donde
   deja de ser una aspiración.

---

## H8 · API y contrato

**Ficheros.** Los `router.py` de las siete features, montados en `app/main.py`.

**Pruebas, en este orden:**

1. `test_el_openapi_expone_la_superficie_minima_de_cada_feature` — la tabla de §4.
2. `test_todo_esquema_de_entrada_y_salida_es_pydantic` — sin `dict` sueltos (`A-13`, RI-02).
3. `test_los_endpoints_de_escritura_en_canon_son_idempotentes` (RI-05).
4. `test_el_backoff_es_exponencial_con_jitter` (RI-07).

**Terminado cuando** `/openapi.json` es estable y de él se puede derivar el cliente tipado
del frontend, que queda fuera de v1.

---

## H9 · Las 21 preguntas y la traza

El hito que dice si el modelo de datos sirve para algo.

**Pruebas.** Una por pregunta de competencia, en `tests/competencia/`, contra el esquema
vigente. Las tres salvedades de §8 se prueban en su versión recortada: la 4 responde sin
aplicar, la 19 responde la medida acumulada y no el «toca replanificar», y la 21 queda
fuera de v1 entera (`A-43`, RNF-04).

Además:

- `test_todo_requisito_de_la_spec_se_cita_en_al_menos_una_fila_de_verificacion` — hoy
  fallan veinticuatro. Cerrarlos es parte de este hito (criterio 3).
- Pruebas de mutación sobre `canon/` y `context/` en CI nocturno: una suite que no detecta
  un bug introducido a propósito no prueba nada (`A-44`).

---

## Migraciones

Numeradas, aplicadas en orden y **nunca editadas** una vez commiteadas. Si un hito
necesita cambiar algo de una migración anterior, se escribe una nueva.

| Nº | Qué crea | Hito |
| --- | --- | --- |
| 001 | Control de migraciones y árbol estructural | H1 |
| 002 | Entidades narrativas, `Evento`, `Objetivo`, puente `evento_escena` | H2 |
| 003 | Canon completo y las siete relaciones nuevas | H3 |
| 004 | `vec0` y columnas de embedding | H4 |
| 005 | Informe de crítica, defecto, dimensión | H5 |
| 006 | Brief, borrador, versión, registro de generación, `training_samples` | H6 |
| 007 | Hallazgo y extracción | H7 |

---

## Riesgos

| Riesgo | Qué pasa si se materializa | Qué lo contiene |
| --- | --- | --- |
| **El esquema declara pocas restricciones de destino** | La deriva sale baja por no decir nada, y un plan que no declara ninguna la tiene en cero para siempre: la medida premia no planificar | La densidad de declaración, que marca la medición como no fiable en vez de como baja (`P-53`). Es contrapeso, no cura: si el plan no declara, no hay deriva que medir |
| **El `alcance` de `Restricción de destino` no dice qué entidades toca** | `canon_huérfano` e `inviabilidad_pago` cuentan sin poder atribuir qué restricción recoge qué promesa o qué hilo | Se implementan en su forma débil y el histórico guarda los ingredientes, así que los dos componentes se recalculan enteros el día que el atributo llegue |
| **`Hecho canónico.tipo` sin enumerar** | RF-QUA-01 se queda sin la mitad descriptiva: los ojos que cambian de color no los ve nadie | Se implementa la mitad enumerable y se deja la otra explícitamente fuera, no a medias y en silencio |
| **El anclaje textual no existe** | RF-CANON-11 comprueba presencia de términos, no significado. Es el punto ciego #1 | Se acepta el proxy y se documenta como tal; no se presenta como garantía |
| **El modelo de embeddings local no cabe en la máquina** | H4 se bloquea entero: sin embeddings no hay recuperación | Se detecta en H4 y no antes. Si pasa, la alternativa aprobada es `multilingual-e5-large` (§9.2) |
| **v1 se queda en fase de medición para siempre** | La capa de calidad nunca suspende y acaba siendo decorativa | El punto ciego #15 lo nombra; H5 exige que la fase sea consultable, no un silencio |
| **El hito H3 se come el calendario** | Quince requisitos y doce pruebas de invariante en un solo hito | Es el riesgo aceptado: partirlo dejaría el canon a medias, que es peor que tardar |

---

## Criterio de terminado

Los siete criterios de aceptación de `spec.md` §8, sin descuento. En particular:

- El ciclo completo de punta a punta funciona (criterio 2, prueba de H7).
- Las 21 preguntas de competencia se responden con el esquema vigente, con las tres
  salvedades declaradas (criterio 1, H9).
- La instancia **arranca en fase de medición y lo dice** (criterio 4, H5).
- Ningún ensamblado supera `contexto.total` ni se trunca en silencio, y ningún trabajo
  arranca sin presupuesto libre de `en_vuelo.total` (criterio 5, H4 y H6).

El commit que cierra este plan nombra su carpeta: `docs/specs/001-backend-v1/`.
