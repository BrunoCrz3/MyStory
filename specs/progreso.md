# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | — (plan cerrado: P49 fue el último) |
| Estado del paso | **plan 1 cerrado**: F0 a F5 hechas, `PENDIENTES` vacía y `ejemplos/novela-ejemplo.pdf` commiteado |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P49 |

## Coste real

Tope de parada: **100 USD** acumulados (plan § 1, condición 4). Lo subió el desarrollador de
40 a 100 el 2026-09-25 (TO-048): con `proveedor: claude_code` el coste es **nominal** —no se
factura— y el límite real es el de uso de su plan. Antes de cada ejecución real: si
`acumulado + coste.coste_maximo_novela > 100`, no se lanza. El tope por novela,
`coste.coste_maximo_novela`, pasa de 8 a **15 USD** (TO-049, decisión del desarrollador, 2026-09-25):
con el acumulado actual (30,31 USD), la novela del paso de integración cabe con margen (45,31 ≤ 100).

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |
| 2026-09-24 | P27 | Humo 1 (`proveedor: claude_code`): el planificador se truncó con `max_tokens` 4000 y la novela quedó `Detenida` (error-interno). La generación registró 0 USD porque la llamada fallida no devuelve `usage`; **estimación nominal ≤ 0,40 USD** (Opus 5.5, hasta 4 × 4000 tokens de salida con los reintentos del CLI) | 0,40 | 0,40 |
| 2026-09-24 | P27 | Medición puntual en base temporal (planificador y dos redactor del capítulo 1, topes altos en memoria) para fijar I-02 | 0,41 | 0,81 |
| 2026-09-24 | P27 | Humo 2: capítulos 1 y 2 aceptados en el cuarto intento por un falso positivo de `nombres_exactos`; parado a mano en el capítulo 3 para no gastar ni pasar el tope de latencia. Base apartada como `data/storymaker-demo-intentos-p27.db` | 1,55 | 2,36 |
| 2026-09-24 | P27 | Humo 3, **verde**: novela publicada como versión 1, diez capítulos, 25 llamadas, 1.647 s (`coste_usd` de la generación, nominal) | 5,06 | 7,42 |
| 2026-09-24 | P38 | Humo adversarial opcional (base temporal): **ninguna de las 18 peticiones llevó la instrucción inyectada**, pero la novela se detuvo en el capítulo 1 porque el judge se truncaba con `max_tokens` 3000 (A-92) | 1,55 | 8,97 |
| 2026-09-24 | P38 | Humo adversarial 2 (judge calibrado): otra vez ninguna petición con la instrucción; se detuvo en el capítulo 1 por `limite-de-intentos-agotado`. La base temporal se perdió en la rotación de pytest; sospecha fundada: `invencion_destinatario` sin la edad, la ocasión ni la relación del comprador en su soporte (arreglado, A-98) | 2,39 | 11,36 |
| 2026-09-24 | P38 | Humo adversarial 3 (con el soporte del brief entero): sin la instrucción en ninguna petición, y otra vez detenido en el capítulo 1; el informe muestra que `invencion_destinatario` marca paráfrasis de los rasgos del brief y detalles de trama (se arregla aparte, A-108) | 2,79 | 14,15 |
| 2026-09-24 | P44 | Regeneración real «el perro se llama Nala» sobre la novela del humo: reescribió y aceptó los capítulos 1 a 4 y se detuvo en el 6 por `ContextoNoCabe` del extractor (A-110); la base de demo se restaura desde `data/storymaker-demo-antes-f4.db` | 3,01 | 17,16 |
| 2026-09-24 | P38 | Humo adversarial 4 (con A-108): **verde**, novela real publicada y ninguna de sus 40 peticiones con la instrucción inyectada | 7,03 | 24,19 |
| 2026-09-24 | P44 | Regeneración real 2 sobre la novela del humo (con A-110): reescribió y aceptó los capítulos 1, 2, 3, 4 y 6, y el gate la detuvo por `cierre_arco` —promesas abiertas por los capítulos reescritos que los no afectados nunca pagan—; base restaurada a la versión 1 | 2,90 | 27,09 |
| 2026-09-25 | TO-047 | Regeneración real única sobre una **copia** de la novela del humo (`data/storymaker-demo-promesas-to047.db`), cambiando el hecho del velero de botella (capítulos 3 y 9): **1.821 s** (30 min). El 3 pasó a la primera; `cierre_arco` devolvió el 9 dos veces y lo aceptó al tercer intento; ninguna promesa pendiente de los reescritos. El gate la rechazó por dos promesas que la versión 1 ya dejaba sin pagar (se publicó en el P27, antes de `cierre_arco`) y por `render_visual` sin servidor MCP: ajeno al arreglo, no se repite. Informe `data/humo-regeneracion-promesas-20260925T000733.json`; la base de demo no se tocó | 3,22 | 30,31 |
| 2026-09-25 | Ensayo de la demo | Novela nueva desde cero con el brief de ejemplo (`STORYMAKER_ENV=demo`, base `data/storymaker-demo.db`, `novel_id` `53322d11-ab22-4269-ac83-2796a3ce6462`): diez capítulos aceptados en **2.708 s** (45 min), 866.571 tokens estimados; **detenida** por el gate (`cierre_arco`: promesa abierta en el capítulo 10) y con `[NOMBRE_ANONIMIZADO]` en el capítulo 10 (TO-056). Traza `3917b170a6f125ff32b02ce60b7c7ae9` | 5,96 | 36,27 |
| 2026-09-25 | Ensayo de la demo | Segunda novela desde cero, mismo brief, con TO-056…TO-058 (`novel_id` `9a9970e0-b5c9-415f-8eec-c952cccd6335`): **publicada** como versión 1, *Soltar amarras*, en **2.780 s** (46 min), 842.096 tokens estimados; `render_visual` real en verde; tres capítulos con una corrección del editor contada (TO-057). Traza `7d6ea3fa38ca33b8c163466a0d0706a6` | 6,04 | 42,31 |
| 2026-09-25 | Ensayo de la demo | Regeneración dirigida «el casco, azul marino en vez de blanco» (capítulos 5 y 6), con `max_intentos_capitulo: 5` (TO-059): el 5 se reescribió y se aceptó; el 6 **agotó sus cinco intentos** por `cierre_arco` del reescrito, porque el extractor citó como reabierta, no pagada, la promesa de las velas que el 6 pagaba en la versión 1. **1.669 s** (28 min), 581.021 tokens estimados; novela `Detenida`, versión 1 intacta. Traza `cd0b2ccfe7cc3f7277db354f2ff06ff6` | 3,63 | 45,94 |
| 2026-09-25 | TO-058 | Tres llamadas al judge fuera de una generación, con trazador local, para demostrar `invencion_destinatario` y `temas_excluidos` | no medido | 45,94 |
| 2026-09-25 | Ensayo de la demo | Tras TO-062 (la regeneración fallida dejó la 2 `rechazada` y la novela publicada; estado de *Soltar amarras* corregido): regeneración «Tomás navegó de joven y el mar le da respeto» (solo el capítulo 7), **publicada como versión 3 sobre la 1** en **250 s**, 89.960 tokens estimados; el 7 marcado, la 1 entera y con su hash, la 2 fuera del selector; PDF de la 3 con paridad en verde. Traza `74636d6a439c2ba5297aa12b69e29407` | 0,53 | 46,47 |

**Novela de humo** (se reutiliza en F4 y F5; **no migró** a la máquina Windows: `data/` empezó vacía y `data/storymaker-demo.db` es ahora la base del ensayo de la demo): base `data/storymaker-demo.db`, `novel_id` `4e884416-fa5d-4f7a-b013-94554af5a29e`, versión 1 publicada. Traza: `https://us.cloud.langfuse.com/project/cmu5p7ovq02acad0d3x5caggq/traces/e296b4f51ef4012cc416f6b14fbd3a16`. Informe por llamada: `data/humo-20260924T163649.json`. Los intentos fallidos están en `data/storymaker-demo-intentos-p27.db`.

## Hecho

Un renglón por paso cerrado: paso, qué quedó y hash del commit.

- **P01** — Esqueleto (pyproject, crear_app, lifespan), test de conformidad estructural con PENDIENTES y meta-prueba de 8 mutaciones; 12 pruebas
- **P02** — Comprobadores estáticos: grafo de importación leído de architecture.md, hojas intake/guardrail, sin dobles, sin dependencias excluidas, RD-02 en repositorios; 8 meta-pruebas
- **P03** — commons/config: modelos Pydantic estrictos de thresholds.yaml y models.yaml, suma de capas, margen >= max_tokens por rol, nulos según cerrar_el_paso, gate Lean sin timeout, judge != redactor; el lifespan aborta con la clave culpable; 25 pruebas nuevas
- **P04** — commons/errores: una excepción por type del catálogo, handler central problem+json (dominio, 422 reescrito, 500 sin detalles), OpenAPI sin el 422 genérico y con Problema idéntico al del contrato; commons/esquemas.opcional() para opcionales sin nulo
- **P05** — commons/db: conectar() con WAL y FK en toda conexión, transaccion() con BEGIN IMMEDIATE, BaseDatos con una conexión por unidad de trabajo en hilo; runner de migraciones con hash que falla si se edita una aplicada, atómico por migración; lifespan migra al arrancar; prueba RD-01 sobre toda migración; cada prueba con base temporal y sin credenciales
- **P06** — commons/llm: Protocol ClienteModelo, Peticion inmutable con huella, Recuento atado a la petición, ClienteAnthropic (SDK 1.8 sobre httpx2, timeout de config, max_retries=0, effort y salida estructurada por output_config.format, thinking adaptativo, 429/5xx/timeout como FalloInfraestructura, max_tokens como SalidaTruncada, thinking_tokens de usage); precios y timeout en thresholds.yaml; doble ModeloGuionizado en tests/dobles
- **P07** — commons/llm/pool: semáforo por peso en proceso, FIFO estricto, rechazo inmediato de lo que no cabe, liberación ante excepción y cancelación; propiedad con hypothesis sobre la suma en vuelo
- **P08** — commons/observabilidad: Protocol Trazador con nombres de span cerrados (6 agentes, 3 tools, puntos del proceso), TrazadorLangfuse sobre langfuse 4.15 (sesión por novela con propagate_attributes, generation con usage y coste, create_score) que degrada a log sin contenido si faltan credenciales; commons/llm/llamar: LlamadorModelo cuenta, rechaza lo que supera contexto.total sin llamar, reserva pool y abre el span; doble RegistroTrazas; prueba de arquitectura del único camino al modelo
- **P09** — GET /salud conforme al contrato (estado degradado sin Langfuse, pool, flags de config); Recursos del lifespan con inyección de dobles; lanzador python -m app que rechaza interfaces no locales y fija un worker; cerrojo de instancia con transacción EXCLUSIVE en un fichero hermano de la base
- **P10** — Cierre de F0: e2e con proceso real (/salud por HTTP contra el contrato; arranque con umbral nulo sale con error que nombra la clave), comprobador de cobertura contra config (92,2 % frente a 70 %), README con arranque y la advertencia de un solo worker; TO-038 y RI-012. Bloque de cierre en verde: 100 pruebas, ruff, mypy, conformidad
- **P11** — guardrail/: Guardrail con las cinco normalizaciones a los dos lados (tokenización con posiciones en el original, raíces con plural y diminutivos), niveles global (lista), perfil (edad y ocasión) y novela, gana el más específico, expresiones de varias palabras; suite propia de 17 pruebas incluida la de cada transformación apagada
- **P12** — Migraciones 0001_obra, 0002_encargo, 0003_palabra_prohibida; intake/ con BriefNovela y sus objetos idénticos al contrato y su persistencia; guardrail/ guarda el nivel novela; novel/ con POST, GET y listado de /novelas conformes al contrato (201 con Location, 404 novela-no-encontrada, paginación, 422 sin crear nada), sin ninguna llamada al modelo; aislamiento por novel_id
- **P13** — process/transiciones: las dos máquinas como dato (18 acciones) con aplicar() que rechaza lo que no está; pruebas que comparan la tabla con los stateDiagram de domain-knowledge.md, con la tabla de architecture.md y con los enum del contrato, más una propiedad con hypothesis
- **P14** — app/prompts/: un prompt por rol (texto libre y brief siempre como datos), cargador con hash de blob de git sobre el contenido leído (coincide con git hash-object), sync idempotente por hash a Langfuse con etiqueta git-<hash>; skill de runtime personalizacion-natural sin cifras ni rúbrica, cargada por planner, writer y editor; la rúbrica solo en el prompt del judge
- **P15** — Migraciones 0004_estructura_obra (capítulo por versión, personajes, lugares, fábula, esquema) y 0005_canon (hecho y uso con vigencia semiabierta, triggers RD-05, promesas, snapshot, resumen, índices); canon/ consolida en la transacción de quien acepta, idempotente por capítulo, con hechos propuestos que el policy decide, sin fragmento literal no se proponen; consultas por vigencia; novel/ crea filas de capítulo
- **P16** — Migraciones 0006_audit_log (triggers que abortan UPDATE y DELETE) y 0007_coincidencia; PolicyEngine decide hechos (anclado, no vacío, no duplicado) y capítulos (aceptar, devolver, agotar, detener con el sublímite del guardrail), registra coincidencias y detenciones, una fila de audit log por decisión; entradas por Protocol para no crear aristas nuevas
- **P17** — context/ensamblador: siete capas por piezas, conteo con el contador del proveedor antes de llamar, compresión solo de la capa que desborda (resumen y luego fuera, por prioridad), degradación total en el orden de config, Invariante y Estructural no degradables, Invariante presupuestada por rol con su skill, texto libre en etiqueta de no confiable y escape de etiquetas; context/fuentes: recuperado filtrado por entidades antes de ordenar, anticontexto de n-gramas repetidos, ContadorProveedor con caché; novel/ sirve los capítulos aceptados de una versión
- **P18** — process/planificar: esquema estricto por output_config.format (conversor Pydantic → JSON Schema cerrado), validación de schema y de dominio (número de capítulos, destinatario exacto, POV, lugares y alcances existentes, títulos únicos, obligatorios repartidos), reintento con el motivo hasta el límite y detención, score schema_valido por intento; persiste título, reparto, restricciones, briefs de capítulo y filas Pendiente en una transacción; context/service con las piezas de Invariante y Anticontexto
- **P19** — process/capitulo: ciclo escribir → hook de policy (schema_valido, palabras_prohibidas con coincidencias en tabla y audit log) → hook de capítulo (longitud, nombres_exactos en quality/) → decisión del policy engine → reescritura con el informe; cada cambio de estado por la tabla de transiciones; dos pasadas con palabra vetada detienen; agotar a max_intentos; score por validador ejecutado; consumo acumulado por capítulo; context/piezas_redactor con las siete capas
- **P20** — process/aceptar: extracción estructurada después de aceptar (alias H1/P1 para hechos y promesas conocidos, reintento acotado), y una transacción que aplica Aceptar, guarda texto y palabras, consolida canon con el policy decidiendo cada hecho (duplicados descartados), resumen, snapshot, eventos con personajes y lugar, elementos aparecidos; aceptar dos veces es transicion-invalida sin llamar al extractor; un borrador rechazado no deja rastro
- **P21** — Migración 0008_trabajo (trabajo con índice único parcial de un vivo por novela, checkpoint); process/cola: encolar comprueba generación viva (409 con el id vivo), transición Planificar, estimación contra el pool (422 trabajo-no-cabe-en-pool) y responde 202 con Location; reclamar con UPDATE condicional atómico; Generacion idéntico al contrato con es_terminal e intervalo de sondeo de config; listar y obtener; /salud cuenta trabajos en cola; opcional() omite None al serializar
- **P22** — process/orquestador: por cada trabajo una traza en la sesión de la novela; Planificar → planificador → FijarEsquema → ciclo y aceptación de cada capítulo con checkpoint en la transacción de aceptar → CerrarEscritura; detenciones registradas en audit log; consumo acumulado por variable de contexto; process/worker: único, en el lifespan, reclama atómicamente, duerme hasta que encolar le avisa y se para con el lifespan; transición Detener desde Planificando añadida a los diagramas y la tabla
- **P23** — commons/llm/llamar: reintento de fallos de infraestructura en contar y generar con retroceso exponencial y jitter (reloj y azar inyectables), max_intentos_trabajo reintentos tras la primera llamada, contador propio en Consumo.reintentos_infra que no gasta intentos del capítulo; orquestador: topes coste_maximo_novela y latencia_maxima_novela tras planificar y tras cada capítulo, fallos de infraestructura agotados y ContextoNoCabe detienen con error-interno e informe en audit log; intentos_infra en el trabajo
- **P24** — Reanudación: el worker devuelve a `pendiente` al arrancar los trabajos `en-curso` (UPDATE … RETURNING, sin copia); `Orquestador.estado_inicial` normaliza a `Pendiente` los capítulos en Escribiendo, Validando o Reescribiendo sin tocar sus intentos; un corte entre guardar y fijar el esquema no replanifica; `CerrarEscritura` solo desde Escribiendo; propiedad con hypothesis (uno o dos cortes en redactor o extractor): aceptados en prefijo, mismo `capitulo_id`, un snapshot por capítulo, un solo trabajo; 237 pruebas
- **P25** — Migración 0009_version (version_novela, version_capitulo, triggers de inmutabilidad también sobre título, texto y palabras de un capítulo publicado); versioning/ con gate F1 (`estructura_edicion`, `elementos_obligatorios`, score por validador), publicar con hash SHA-256 del contenido canónico y `modificado` por fila distinta (D-05), y las cuatro rutas de lectura; puerto `Publicador` en process/service.py inyectado desde el lifespan; el orquestador publica en una transacción (Publicar + Conservar) y deja `version_resultante`; gate en rojo → DevolverAlEditor + Detener; el guion del doble declara los elementos del brief; 245 pruebas
- **P26** — `ejemplos/brief-ejemplo.json` (el `example` de `BriefNovela`, con prueba de igualdad); `tests/humo/test_novela_real.py` marcado `real` sobre `STORYMAKER_DB_PATH` que se salta con motivo si falta la credencial; `tests/herramientas/casetes.py` con `TransporteGrabador` (lista blanca de cabeceras) y `reproductor`; `tests/arquitectura/test_sin_secretos.py` sobre lo versionado y los casetes, con meta-pruebas; 254 pruebas
- **P27** — Cierre de F1: e2e con proceso real (novela por HTTP y reanudación tras matar el proceso en el capítulo 5; el arnés escribe la salida del hijo en fichero para no bloquear); proveedor `claude_code` contenido (I-04, TO-040); etiqueta de prompt al límite de Langfuse; `nombres_exactos` sin falsos positivos por palabras comunes (A-60); topes calibrados en real (A-58, A-59, A-61); TO-039 y TO-041; humo real verde; 288 pruebas, cobertura 96 %
- **P28** — Migración 0010_calidad (`informe_critica`, `defecto`, `score`; sin tabla `validador`, A-62); `quality/registro.py` con los 26 validadores del índice, comprobado contra `verification.md` leído del fichero; `registrar_informe` en la transacción de la decisión del policy engine, que falla si un resultado no corre donde dice el registro; `informes_de_capitulo` y `ultimo_informe`; 296 pruebas
- **P29** — `quality/validadores/canon.py`: `consistencia_factica` (edad en presente contra hechos vigentes y el brief, números en cifra y en letra), `cumplimiento_brief` (alcance nombrado, sin adelantar entidades que el plan presenta después) y `reglas_mundo` (exclusión de entidad por nombre, con plural; las de forma, no comprobables); `process/` les pasa hechos, reglas, alcance y previstas; la prueba de `/salud` con cola deja de ser una carrera; 307 pruebas
- **P30** — `quality/validadores/texto.py`: `calidad_prosa` (eco de 5-gramas con los capítulos anteriores, muletillas y clichés contra listas cerradas en `quality/listas/`, adverbios, variación de longitud de frase, metatexto/markdown, truncado; cifras en null se omiten) e `integridad_pov` (persona fuera del diálogo, tiempo si se declara presente, accesos mentales de otro personaje con focalización interna); `hook_capitulo` asíncrono con los siete validadores en hilos concurrentes (`en_paralelo`), probado con una barrera de siete y con el pool a 0 durante el hook; 323 pruebas
- **P31** — `quality/judge.py`: `SalidaJudge` (seis `Puntuacion` 0–1 con justificación, más afirmaciones sobre el destinatario y temas excluidos para el P37), `evaluar_judge` con `schema_valido` y un resultado por criterio con tipo y punto del registro; `context.piezas_judge` (borrador en Local como no confiable, temas excluidos, último capítulo marcado); `process/judge.juzgar` llama con `roles.judge` y deja un score por criterio con su justificación como comentario; 336 pruebas
- **P32** — Ciclo por intento: redactor → hook de policy (si falla, se decide sin judge ni editor) → hook de capítulo → judge → si falla algo que cierra, `process/editor.corregir` (contrato en `quality/editor.py`, piezas en `context.piezas_editor` con informe y anticontexto) → el corregido vuelve a pasar policy, capítulo y judge → decisión; defecto sistémico del editor al audit log (`defecto-sistemico-como-local`, D-14); prompt del editor con la clasificación; dobles con judge y editor por defecto (`guion_revision`); 343 pruebas
- **P33** — `versioning/gate.py` con `estructura_edicion`, `elementos_obligatorios` y `cierre_arco` (mitad programática: promesas pendientes al cierre ≤ `continuidad.promesas_pendientes_al_cerrar`); el gate en rojo registra en el audit log las transiciones `DevolverAlEditor` y `Detener`; pruebas con una promesa sin pagar (no publica) y pagada por alias `P1` (publica); 345 pruebas
- **P34** — Cierre de F2: `tests/e2e/test_f2.py` (capítulo 3 corto en borrador y en corrección, vuelve al redactor y se acepta; la traza de la generación tiene los nueve scores de los hooks, los seis del judge con justificación y los tres del gate); TO-042 y RI-015; bloque § 4.5 con N = 2 en verde (346 pruebas, cobertura 96,2 %); F2 subida
- **P35** — `BriefNovelaParcial` y sus seis parciales, `DatoFaltante`, `ContradiccionBrief`, `FragmentoSospechoso`, `ResultadoValidacionBrief` idénticos al contrato; `intake/validacion.py` con los obligatorios derivados de `BriefNovela` (comparados con los `required` del contrato) y una pregunta de reintento por obligatorio; `intake/reglas.py` (edad-vs-tono, edad-vs-genero, fecha-vs-edad, identificador con forma de correo); `POST /briefs/validacion`; `crearNovela` responde 400 `brief-invalido` antes de escribir; `validarBrief` fuera de PENDIENTES; 363 pruebas
- **P36** — Migración 0011 (`fragmento_sospechoso`); `intake/saneamiento.py` con `patrones.txt` (expresión, tabulador, motivo) por frase y línea; `intake/extraccion.py` (tool `extraer_hechos_texto_libre`, rol entrevistador, texto saneado dentro de `<texto_libre_no_confiable>`, solo hechos con fragmento literal); `validarBrief` devuelve fragmentos y hechos; `registrar_brief` guarda el brief saneado y los fragmentos; comprobador `violaciones_ejecucion` con meta-prueba; corpus de inyección entero detectado; 381 pruebas
- **P37** — `quality/validadores/{invencion_destinatario,temas_excluidos}.py` sobre los campos del judge; `ContextoJudge` (soporte: rasgos, recuerdos, elementos, texto libre saneado, premisa y dedicatoria); `evaluar_judge` los añade como `editor` y `juzgar` emite sus scores; `calidad.invencion_soporte_minimo: 0.5`; los dos cuentan hasta cero y cierran siempre; 388 pruebas
- **P38** — Cierre de F3: `tests/e2e/test_f3.py` (brief adversarial por HTTP: validar devuelve el fragmento, crear lo registra, y ninguna petición de toda la generación con dobles lo contiene; el texto libre restante solo dentro de su delimitador); `tests/humo/test_adversarial_real.py` (opcional real); judge calibrado a 10000 (A-92); TO-043 y RI-016; bloque § 4.5 con N = 3 en verde (389 pruebas, cobertura 96,4 %); F3 subida. Segundo humo adversarial, con el judge calibrado, lanzado al cerrar: su resultado se anota aparte
- **P39** — `canon/router.py` y `canon/schemas.py` (`HechoVigente` idéntico al `Hecho` del contrato); `GET …/versiones/{version}/hechos` por vigencia, con `?capitulo=` sobre `capitulos_usan` del puente; 404 `novela-no-encontrada` y `version-no-encontrada`; `listarHechos` fuera de PENDIENTES; 392 pruebas
- **P40** — Migración 0012 (`solicitud_cambio`, `analisis_impacto`, `retcon`); `versioning/solicitud.py` e `impacto.py`: la solicitud por hecho se registra con su análisis (capítulos que usan el hecho más el que lo estableció; hechos derivados de esos capítulos) sin crear trabajo ni llamar al modelo; 409 con generación viva, 404 `hecho-no-encontrado`; `NuevaSolicitudCambio` con su `oneOf`; router `regeneracion` aparte; `crearSolicitudCambio` y `obtenerSolicitudCambio` fuera de PENDIENTES; 398 pruebas
- **P41** — `versioning/candidato.py` (Jaccard sobre tokens normalizados contra el `fragmento_soporte` de los hechos que usa el capítulo de origen; a igual similitud, el establecido antes); `regeneracion.similitud_hecho_candidato: 0.5` provisional y sección `regeneracion` obligatoria; la solicitud por fragmento guarda el candidato, su análisis y queda pendiente de confirmación; sin candidato no propone nada; 402 pruebas
- **P42** — `canon/retcon.py` (cierra usos y hecho viejo en v+1, abre el nuevo en v+1, fila de `retcon`); `versioning/confirmar.py`: en una transacción, retcon, `Obsoletar` solo los capítulos del análisis en la versión publicada, `encolar` una generación `dirigida` con `capitulos_a_regenerar` y solicitud `confirmada`; `POST …/confirmacion` 202 con Location; confirmar dos veces es 409; `Detener` desde `Regenerando` en diagrama, tabla y código; el orquestador entra en `Regenerando` y se detiene hasta el P43; 406 pruebas
- **P43** — Camino `Regenerando` del orquestador: fila nueva en la versión objetivo solo para los afectados (la vieja se queda `Obsoleto`), canon de la fila vieja retirado desde esa versión salvo lo que usa un no afectado, aviso del cambio al redactor, `CerrarRegeneracion`, gate y publicación; snapshot derivado por versión; `regeneracion_fiel` en el gate desde la versión 2 (cambian exactamente los obsoletos y la anterior conserva su hash); la solicitud queda `aplicada` con su versión; `versioning/huella.py`; 410 pruebas
- **P44** — Cierre de F4: `tests/e2e/test_f4.py` («el perro se llama Nala» por HTTP: versión 2 con los capítulos 2 y 7 reescritos, los otros ocho idénticos byte a byte, la 1 entera con su hash y su hecho viejo, solicitud `aplicada`); `es_terminal` según la cola (A-109); `tests/humo/test_regeneracion_real.py`; TO-044 y RI-017; bloque § 4.5 con N = 4 en verde (413 pruebas, cobertura 96,4 %); F4 subida. La regeneración real sobre la novela del humo se detuvo una vez por el contexto del extractor (arreglado aparte, A-110) y se relanzó sobre la base restaurada: su resultado se anota aparte
- **P45** — `versioning/ficha.py` (personajes y lugares con los capítulos donde aparecen en esa versión, por eventos, POV y lugar del capítulo; descripción de rol y deseo o de atmósfera y geografía) y `portada.py` (título de la versión, dedicatoria, destinatario, ocasión); `novel.apariciones`; `obtenerFicha` y `obtenerPortada` fuera de PENDIENTES; la ficha de la versión 1 y la de la 2 difieren tras una regeneración; 416 pruebas
- **P46** — `versioning/lectura.py`: ruta, estados de `data-estado` y los 14 selectores de CL-03 como un único dato, comparado con la tabla de la spec leída del fichero; `url()` y `selector()`; prueba de arquitectura: `data-testid` solo en `lectura.py`; `tests/fixtures/lectura/pagina.py` genera la página de prueba desde una versión publicada (con `@media print` y opciones para romperla); `STORYMAKER_LECTURA_URL` en `.env.example`; 420 pruebas

- **P47a** — contrato 1.2.0 (TO-045): migración `0013_estado_version.sql` (`estado` con `CHECK`, existentes `publicada`, trigger que solo admite `candidata → publicada | rechazada`); `Version.estado`; `novel.version_vigente` y `listarVersiones` solo con publicadas; puerto `Publicador` con `proponer`, `gate`, `render_visual`, `publicar` y `rechazar`; `versioning/render_visual.py` con el puerto y `SinNavegador` (A-114); el orquestador escribe la candidata, corre el gate completo sobre ella y publica o rechaza en la transacción que detiene; `crear_app(render_visual=…)`; doble `tests/dobles/render.py`; `VERSION_API` 1.2.0; 428 pruebas
- **P47b** — `versioning/render_visual.py`: cliente guionizado del servidor Playwright MCP (0.0.82, `--headless --isolated --browser msedge`, URL con `localhost`) sobre la candidata: navega, sondea `data-estado`, extrae el DOM con una llamada a `browser_evaluate` usando los selectores de `lectura.py` y lee `browser_console_messages`; `evaluar` puro con siete aserciones (`ASERCIONES`, cada una con su tool), clasificación datos/maquetación consultando la story bible; `render_de_entorno` elige `RenderVisualMCP` o `SinNavegador`; umbrales `render_visual.*`; `docs/browser-mcp.md`; dependencia `mcp`; 449 pruebas (5 contra el servidor MCP real)
- **P48** — migración `0014_exportacion.sql` (una fila por versión; `disponible` inmutable por trigger); `versioning/export.py`: `page.pdf()` de Playwright (Chromium) sobre la lectura tras esperar a `lista` y emular `print`, del mismo render se lee el DOM para la paridad; `POST …/export` → `202` y generación en segundo plano, `200` si ya existe; `GET` → PDF o `404 export-no-disponible`; solo versiones `publicadas`; saneo al arrancar; CLI `python -m app.versioning.export <novel_id> <version>` (D-22); `versioning/paridad.py` con `pypdf`: capítulos y títulos por página, dedicatoria e índice antes del primero, palabras por capítulo dentro de tolerancia y enlaces internos (A-103), con su score; `export.timeout_segundos`; `PENDIENTES` vacía; dependencias `playwright` y `pypdf`; 459 pruebas
- **P49** — `tests/e2e/test_f5.py`: backend como proceso con dobles y `render_visual` real (servidor MCP y una página de lectura que lee la API al pedirla, como el frontend): el gate pinta la candidata y la publica; ficha y portada por HTTP; export con paridad; `test_conformidad_completa` (`PENDIENTES` vacía). Integración con la página `lectura` real del frontend (rama `frontend-demo`, `npm run dev`): `render_visual` en verde tras corregir el parser de consola y declarar A-124; `ejemplos/novela-ejemplo.pdf` con la CLI sobre la novela del humo (49 páginas, 124 enlaces, paridad en verde). I-03: `lean_timeout_segundos` = 26. Documentos de cierre: spec § 8.1, `verification.md`, `architecture.md`, `browser-mcp.md`, TO-046, RI-019; 462 pruebas
## Pendiente

- ~~Hueco conocido de F4, visto en real~~ **resuelto** tras el plan (TO-047, RI-020): el desarrollador aceptó la propuesta ampliada a cuatro reglas —destino del redactor, reapertura por alias, reconciliación y devolución al redactor por `cierre_arco`—. Probado con dobles y con una regeneración real sobre una copia de la novela del humo (hecho del velero de botella, capítulos 3 y 9; 1.821 s, 3,22 USD): el 3 pasó a la primera, `cierre_arco` devolvió el 9 dos veces y lo aceptó al tercer intento, y la versión 2 no tiene promesas pendientes de los capítulos reescritos. El gate la rechazó por las dos promesas que la versión 1 ya dejaba sin pagar —se publicó en el P27, antes de que existiera `cierre_arco`— y por `render_visual` sin servidor MCP; las dos causas son ajenas al arreglo y no se repitió (§ Coste real).
- **La novela del humo no se usa en la demo** (decisión del desarrollador, 2026-09-25). **Hecho**: la novela de la demo es *Soltar amarras* (`data/storymaker-demo.db`, `novel_id` `9a9970e0-b5c9-415f-8eec-c952cccd6335`), generada desde cero en el ensayo con el código actual: versión 1 publicada, la 2 rechazada (regeneración fallida, TO-062) y la 3 publicada sobre la 1 (RI-033 a RI-035). La del humo no migró a la máquina Windows.
- Casetes HTTP (plan § 4.1, capa 2): **pendientes**; solo se graban con `proveedor: api` y no hay clave. El grabador y el reproductor existen (`tests/herramientas/casetes.py`).
- ~~**Frontend**: regenerar el cliente desde el contrato 1.2.0 (I-10) y servir un favicon (A-124)~~ **hecho** en la integración de la demo (TO-050).

### Resumen al cerrar el plan (I-08)

- **Funciona**, con la suite en verde (462 pruebas, e2e por fase): entrevista y brief con datos faltantes, contradicciones y texto libre saneado; planificación, escritura, hooks, judge y editor, aceptación por el policy engine con audit log; story bible por versión con vigencia y retcon; regeneración dirigida que solo reescribe lo afectado; versión candidata con el gate completo, `render_visual` real incluido; lectura por versión con ficha y portada; export a PDF con paridad; observabilidad con spans y scores; proveedor `claude_code` sin clave de API.
- **No funciona o no está**: los casetes HTTP. (El gate de Lean se activó después, con el plan 4.) El hueco de promesas en la regeneración dirigida se arregló después del cierre (TO-047); una regeneración real lo confirma, aunque no publica porque la versión 1 del humo trae dos promesas sin pagar.
- **Post-demo**: la tabla de abajo y los cuatro RF `[post-demo]` de la spec (RF-INTAKE-06, RF-CANON-05, RF-QUA-08, RF-EXP-03).

### Después del plan

- **TO-047** — Promesas en la regeneración dirigida (decisión del desarrollador; arreglo de RF-VER-08 con TDD): migración `0015_promesa_por_version.sql` (apertura y pago como vínculos `promesa_capitulo`, estado derivado por las filas de la versión); `canon.promesas_vivas` con el alias común a redactor y extractor; el brief del capítulo reescrito lleva las promesas que conserva como restricción de destino; `Extraccion.promesas_reabiertas`; `cierre_arco` sobre el capítulo reescrito antes de consolidar, que lo devuelve a su redactor como intento fallido (A-125…A-132); `tests/process/test_regeneracion_promesas.py` y el e2e de F4 con el caso real

## Post-demo

Lo que queda después de la demo, **priorizado** (decisión del desarrollador, 2026-09-25). Los tres
primeros bloques son lo que el alcance exige para aprobar; el resto, por orden.

### 1. Lo que el alcance exige para aprobar

1. **Evaluaciones con resultados medibles.**
   - Los cinco briefs de prueba B1–B5, incluidos el adversarial y el de incoherencia temporal,
     corridos con el modelo real.
   - La **tabla brief × validador**, con un score por celda.
   - La **revisión humana comparada con el judge**, criterio a criterio.
   - La **iteración de tuning documentada** con antes, después y la versión de prompt de cada
     lado (E-11). RI-021 cambió `writer` y `extractor` sin esa tabla: es la primera candidata.
2. ~~**Lean.**~~ **Hecho** con la spec 4 y el plan 4 (`specs/progreso-lean.md`):
   - RF-EXP-03: el fichero Lean se genera desde la story bible de cada versión.
   - `formal.gate_activo: true`, con el timeout medido (20 s, L08).
   - El caso real que solo detecta Lean: el brief B2 (`docs/red-team.md` RT-004).
3. **TLA+.**
   - La especificación del harness en `formal/tla/harness.tla` y TLC con su `harness.cfg`.
   - El test de correspondencia con la tabla de transiciones de `process/transiciones.py`.
   - El mapeo en el README.

### 2. Después

| # | Qué | Por qué queda fuera | Decisión |
| --- | --- | --- | --- |
| 4 | **Entrevistador conversacional** | La entrevista de la demo es un formulario con validación del backend | `specs/spec1.md` § 7 |
| 5 | **Replanificación de capítulos pendientes** (invalidación de restricción de destino) | Sin RF en la spec 1; un defecto sistémico se trata como reescritura y queda registrado con su clasificación | D-14, aceptada por el desarrollador |
| 6 | **Validador «toda promesa pagada tiene su apertura en una fila vigente anterior al pago»** (O-41, el antiguo P-45) | Cierra el hueco de la regla 3 de TO-047. Hasta que exista es el punto ciego #16 de `docs/verification.md` | Decisión del desarrollador (TO-047 § Decisiones posteriores) |
| 7 | **Casetes HTTP** (plan § 4.1, capa 2) | Solo se graban con `proveedor: api` y no hay clave. El grabador y el reproductor existen | — |
| 8 | **`proveedor` en `GET /salud`** (contrato 1.3.0), para rotular tokens y coste como estimados solo con `claude_code` | La demo los rotula siempre como estimados | Decisión del desarrollador (TO-055) |
| 9 | **Las 4 vulnerabilidades moderadas de `npm audit`** del frontend | Sin `npm audit fix --force`: rompería dependencias antes de la demo | Revisión de seguridad post-demo |
| 10 | **Retención de trazas en Langfuse** | Política de cuánto se guardan las trazas de las novelas | — |
| 11 | **Auditoría 002** | Sucesora de `docs/audits/001-coherencia-ontologia.md`, sobre el estado tras la demo | — |
| 12 | **Exceso de filas `obligatorio` en `docs/verification.md`** | Hay más filas obligatorias de las que la demo puede cubrir; hay que revisar cuáles lo son de verdad | — |
| 13 | **`disk I/O error` intermitente en `tests/e2e/test_f1.py`** al leer la base justo después de matar el proceso, en Windows | Visto una vez; pasa en las repeticiones (RI-027) | Decisión del desarrollador, 2026-09-25 |
| 14 | **Unificar la dirección de todos los scores** (por ejemplo, 1 = cumple) para Langfuse y la tabla brief × validador: hoy `invencion_destinatario` y `temas_excluidos` son recuentos con 0 = bien | Cambiaría los scores de Langfuse a mitad de ensayo; la dirección está declarada en `docs/verification.md` | Decisión del desarrollador (TO-058) |
| 15 | **Resolver el proveedor del modelo con el administrador de la organización**: que excluya o acote la política de anonimización para este uso, o que la organización o el curso proporcionen una clave para `proveedor: api` | Con `claude_code`, las instrucciones de privacidad de la organización llegan a los subprocesos y anonimizan nombres ficticios (RT-002) | Decisión del desarrollador (TO-061) |
| 16 | ~~Una regeneración detenida deja la novela `Detenida`~~ **resuelto** (TO-062): la candidata queda `rechazada`, la novela sigue publicada y la solicitud siguiente parte de la vigente. **Queda el punto 2 de la decisión**: marcar la solicitud como fallida con su motivo visible en la lectura, que exige el contrato 1.3.0 (`fallida` en `SolicitudCambio.estado`, un campo de motivo y listar las solicitudes de una novela) | Cambio de contrato | Decisión del desarrollador (TO-062): post-demo |
| 17 | **El extractor puede no reconocer como pagada una promesa que el capítulo reescrito tiene que pagar** (la cita como reabierta), y el capítulo se agota aunque el texto la resuelva. **Remedio decidido**: indicarle al extractor, de forma explícita, qué promesas debe cerrar ese capítulo y pedirle que confirme, una por una, si el texto las resuelve | TO-047 regla 1 descansa en dos lecturas del extractor que pueden discrepar. Visto en el ensayo (RI-033) y otra vez en la demo: el capítulo 6 de una regeneración dirigida se agotó en cinco intentos con el judge dando 0,93–1,00 a `cierre_arco` en cada uno (RT-005). El argumento anterior, que darle las marcas `[pagar]` lo sesgaría, sigue siendo el riesgo que hay que medir: la confirmación tiene que poder decir que no. Pasa por spec y plan | Decisión del desarrollador, 2026-09-25 |
| 18 | **Comprobar los scores por validador en la interfaz de Langfuse**: la API de scores devuelve 410 en esta organización (v1 y v2) | Las observaciones v2 sí confirman sesión, entorno, spans por rol y `hash_prompt`. Lo comprueba el desarrollador en la interfaz (anotado en el README) | Decisión del desarrollador, 2026-09-25 |
| 19 | **Rellenar `Version.motivo` en las versiones nuevas** con el enunciado de la solicitud que las aplica: hoy va siempre vacío y el selector de la lectura no dice por qué cambió una versión | El contrato lo define («en una regeneración, el enunciado de la solicitud»); una versión publicada es inmutable, así que solo aplica a las siguientes | Decisión del desarrollador, 2026-09-25 (RI-035) |
| 20 | **Que un retcon solo cierre el hecho antiguo al publicarse su versión**, con la vigencia por versión de TO-028, para **eliminar la excepción de `Retconeado`** (hoy vuelve a `Adoptado` si se rechaza la candidata que lo retconeó) | TO-062 revierte el canon de una candidata rechazada y necesita esa excepción; si el cierre solo ocurre al publicar, no hay nada que revertir y `Retconeado` vuelve a ser terminal sin excepciones | Decisión del desarrollador, 2026-09-25 (TO-062) |
| 21 | **Un tope agotado después de aceptar el último capítulo impide publicar lo ya escrito**: `coste.latencia_maxima_novela` se comprueba tras el capítulo 10 y detiene la generación antes del gate, y la novela queda `Detenida` sin transición para reanudarla. Debería dejar terminar el gate sobre los capítulos aceptados | Visto en la demo: diez capítulos aceptados y ninguna versión a los 3.933 s (RI-042). Pasa por spec y plan | Decisión del desarrollador, 2026-09-25 (TO-070) |
| 22 | **Un tope agotado se informa como `error-interno`** en lugar de con un motivo propio visible para el usuario: el progreso no dice que se acabó el tiempo o el presupuesto | El catálogo de errores no tiene motivo para los topes de coste y latencia; el detalle solo está en el audit log. Pasa por spec y plan | Decisión del desarrollador, 2026-09-25 (TO-070) |
| 23 | **Nombres de validador duplicados en el audit log y en Langfuse**: `cierre_arco` es a la vez el criterio `arco` del judge (semántico, no cierra el paso) y la comprobación del registro de promesas (programática, cierra el paso); la segunda pasaría a llamarse, por ejemplo, `promesas_pagadas`. Revisar también `consistencia_factica` (el criterio `continuidad` del judge y el validador de canon, ambos en el mismo veredicto) y `schema_valido` (dos veces en cada veredicto del hook de capítulo, de roles distintos) | Con el mismo nombre, el audit log muestra `cierre_arco` 0,97 y a continuación `cierre_arco` 0,0 sin decir que son dos validadores distintos (RT-005). Cambia nombres de score en Langfuse, el registro de validadores y `docs/verification.md`, así que pasa por spec y plan; afecta a la comparación con los scores ya emitidos (TO-058) | Decisión del desarrollador, 2026-09-25 |
| 24 | El resto de la lista post-demo de la spec: servidor MCP propio, agente de seguridad, SSE, PO-11 y PO-12 | — | `specs/spec1.md` § 7 |

## Decisiones

Las que fija el plan son D-01 a D-24 (plan § 3, registradas como TO-036). Las que tome el
agente durante la ejecución van aquí como `A-NN`, con paso, decisión, porqué y dónde quedó
registrada.

| Id | Paso | Decisión | Porqué | Registro |
| --- | --- | --- | --- | --- |
| — | plan | D-01 resuelta con un cambio de contrato: `BriefNovelaParcial` para validar, `BriefNovela` para crear; contrato 1.1.0 | Aprobado por el desarrollador | TO-037 |
| — | plan | D-08, D-09, D-14 y D-22 aceptadas; D-08 con seis aristas nuevas comprobadas sin ciclo | Aprobado por el desarrollador | TO-036, `docs/architecture.md` |
| — | plan | Contrato de lectura en la spec § 4.4 y paso P46 que lo lleva como dato | Pedido por el desarrollador | TO-037 |
| A-01 | P02 | De otra feature solo se importa `service`; `commons/`, `prompts/` y `skills/` son importables desde cualquier feature y no importan ninguna | La skill dice que `service.py` es lo único importable; `prompts/` es infraestructura de contenido (D-09) | TO-038 al cerrar F0 |
| A-02 | P02 | Consultas sin `novel_id` —listar todas las novelas, reclamar el siguiente trabajo— se declaran en `CONSULTAS_TRANSVERSALES` del repositorio | RD-02 no tiene excepción escrita y listar novelas la necesita | TO-038 |
| A-03 | P03 | Todo umbral con score (calidad salvo invencion_destinatario y temas_excluidos) solo cierra el paso con `medicion.cerrar_el_paso: true` y admite null en medición; los booleanos y los que cuentan hasta cero cierran siempre y no admiten null | `thresholds.yaml` no decía si los programáticos con score dependen de la fase de medición; se eligió la lectura que deja salir novelas mientras se calibra | TO-038 |
| A-04 | P04 | `Problema` lleva sus propias formas `DatoFaltanteProblema` y `ContradiccionProblema`; `intake/` tendrá las clases de la ontología | `commons/` no puede importar `intake/` ni contener clases de la ontología | TO-038 |
| A-05 | P04 | Los 404 de rutas inexistentes y los 405 siguen siendo los de Starlette | El catálogo es cerrado y ninguna operación del contrato los produce | TO-038 |
| A-06 | P05 | La tabla de control del runner se llama `_migracion` y es la única sin `novel_id`: las tablas que empiezan por `_` son del runner, no de dominio | RD-01 habla de tablas de dominio | TO-038 |
| A-07 | P06 | `orquestacion.timeout_llamada_segundos: 300` en thresholds.yaml, provisional | RNF-05 exige timeout explícito y RNF-14 que la cifra viva en config | TO-038 |
| A-08 | P06 | Salida estructurada con `output_config.format` (json_schema) en vez de tool forzada | Opus 5.5 devuelve 400 con `tool_choice` forzado y no admite desactivar el thinking (skill claude-api) | TO-038 |
| A-09 | P06 | Precios: claude-opus-5-5 4/20 y claude-sonnet-5 2/10 USD por millón, de la tabla de la skill claude-api cacheada el 2026-06-24 | D-18; la documentación en red no se consultó | TO-038 |
| A-10 | P06 | Se añade `xhigh` a los effort admitidos | Los modelos actuales lo aceptan y models.yaml podría usarlo | TO-038 |
| A-11 | P08 | Sin Langfuse, `traza_langfuse_id` es null, nunca un id inventado; el log degradado no lleva contenido de prompts | Un id falso haría creer que hay traza consultable; el contenido tiene datos personales (RNF-18) | TO-038 |
| A-12 | P08 | La lista cerrada de spans añade a los agentes y tools de architecture.md los puntos del proceso (generacion, capitulo, hook_policy, hook_capitulo, rol_editor, consolidar, gate_publicacion, publicar, validar_brief, export) | architecture.md fija los de rol y tool pero no los de estructura de la traza | TO-038 |
| A-13 | P09 | El cerrojo de instancia es un SQLite `<base>.instancia` con `BEGIN EXCLUSIVE` abierta mientras vive el proceso | El sistema operativo lo libera si el proceso muere: no deja cerrojos huérfanos y funciona en Windows | TO-038 |
| A-14 | P11 | Los cortes de edad del nivel perfil (11 y 17) van a `guardrail.perfil` de thresholds.yaml; las palabras, a `guardrail/listas/` | RNF-14: las cifras en config; las listas son datos del guardrail | TO-039 |
| A-15 | P11 | La ñ no se trata como acento | `año` y `ano` son palabras distintas en español | TO-039 |
| A-16 | P12 | `brief_novela.contenido` guarda el BriefNovela validado entero y las tablas del Bloque A son su desglose consultable, escritos en la misma transacción | La API devuelve el brief tal como llegó; las tablas sostienen las consultas de la story bible | TO-039 |
| A-17 | P13 | La tabla de acciones de architecture.md gana la columna Máquina y nombra las seis transiciones de la novela que el diagrama dibujaba sin nombre (FijarEsquema, CerrarEscritura, DevolverAlEditor, Conservar, Regenerar, CerrarRegeneracion) | Escribiendo→Validando existe en las dos máquinas; sin la columna, la tabla es ambigua | TO-039 |
| A-18 | P14 | Los prompts de sistema son texto fijo por rol, sin huecos: todo dato de la novela llega en el mensaje de usuario, por capas y marcado como datos | Así ningún prompt contiene un dato de novela y el hash identifica el prompt, no la novela | TO-039 |
| A-19 | P14 | La versión en Langfuse se etiqueta `git-<hash>` y sync la busca por esa etiqueta | Es lo que hace la sincronización idempotente sin guardar estado local | TO-039 |
| A-20 | P15 | Las lecturas de canon/ hacen JOIN por SQL con `capitulo` para devolver números; canon/ no importa novel/ y el snapshot lo arma con los presentes y ubicaciones que pasa process/ | La story bible es una vista sobre tablas de canon/ y novel/; la regla de importación es de módulos | TO-039 |
| A-21 | P15 | Un hecho descartado se cierra con version_hasta = version_desde, intervalo vacío | Así la vigencia lo excluye de toda versión sin filtrar por estatus (TO-028) | TO-039 |
| A-22 | P15 | La marca de consolidado de un capítulo es su snapshot: si existe, consolidar no escribe | Idempotencia por capítulo y versión sin tabla extra | TO-039 |
| A-23 | P16 | policy/ recibe hechos y coincidencias por Protocol estructural y los resultados de validadores como Veredicto propio | Evita aristas policy → canon, guardrail y quality, que el grafo de architecture.md no tiene | TO-039 |
| A-24 | P16 | Un hecho que repite el enunciado de uno vigente se descarta con la regla duplicado-de-hecho-vigente | El extractor tiende a reproponer lo ya sabido y el canon no debe duplicarse | TO-039 |
| A-25 | P17 | El system de cada llamada es el prompt del rol más sus skills; todo dato de la novela va en el mensaje de usuario dentro de <capa> y el texto libre dentro de <texto_libre_no_confiable>, con < y > escapados | RNF-09 y D-18 sin ambigüedad: nada de la novela puede cerrar una etiqueta | TO-039 |
| A-26 | P17 | El límite de entrada de una petición es contexto.total menos contexto.capas.margen | El margen es la reserva de respuesta y cubre max_tokens de todo rol (RF-CTX-05) | TO-039 |
| A-27 | P17 | `prosa.longitud_ngrama: 5` en thresholds.yaml; el anticontexto veta los n-gramas que ya aparecen dos veces | El comentario de repeticion_ngramas hablaba de 5-gramas sin que la cifra estuviera en config | TO-039 |
| A-28 | P18 | El conversor de salida estructurada quita longitudes, rangos y títulos y marca obligatoria toda propiedad; lo quitado se comprueba al validar con el mismo modelo Pydantic | La salida estructurada admite un subconjunto de JSON Schema; la validación posterior es schema_valido | TO-039 |
| A-29 | P18 | La lectura de la story bible para un rol se envuelve en el span consultar_story_bible en vez de ofrecer la tool al modelo | El orquestador entrega el contexto ya ensamblado; el span deja la lectura en la traza | TO-039 |
| A-30 | P18 | Aristas process → novel y process → intake añadidas al grafo de architecture.md | La prueba de importaciones las cazó; el orquestador crea capítulos y lee el brief, y no hay ciclo | TO-039 |
| A-31 | P19 | El hook de policy lo ejecuta process/ (process/hooks.py, hoy `process/hook_policy.py`, TO-060) y el de capítulo quality/; policy/ solo decide sobre sus veredictos | process/ es quien tiene arista a guardrail/; quality/ y policy/ no | TO-039 |
| A-32 | P19 | El contador de intentos cuenta las reescrituras hechas: al agotar no se suma la que ya no se hace | Un capítulo agotado muestra las reescrituras gastadas, igual que el ejemplo Detenida del contrato | TO-039 |
| A-33 | P19 | La capa Local lleva todos los capítulos anteriores por recencia y el ensamblador los resume o los quita al desbordar; Recuperado excluye solo el capítulo anterior | Así no hace falta una cifra de cuántos capítulos literales entran: manda el presupuesto de la capa | TO-039 |
| A-34 | P20 | El extractor cita hechos y promesas conocidos por alias cortos (H1, P1) que el código traduce a identificadores | Copiar UUID es frágil para un modelo; un alias que no existe se ignora | TO-039 |
| A-35 | P20 | El momento de un evento es número de capítulo × 100 + su orden en el capítulo | Sin analepsis en v1 la fábula sigue al discurso; basta un orden total para Lean | TO-039 |
| A-36 | P21 | Una generación inexistente en una novela existente responde 404 novela-no-encontrada con el generacion_id en las extensiones | El catálogo es cerrado y no tiene generacion-no-encontrada | TO-039 |
| A-37 | P21 | La estimación de un trabajo al encolar es contexto.total: el tamaño de su llamada más grande, margen incluido | architecture.md § Presupuesto dice que la estimación es el contexto ensamblado, y ninguno supera ese total | TO-039 |
| A-38 | P21 | `orquestacion.intervalo_sondeo_segundos: 3` en thresholds.yaml | Es una cifra del contrato de sondeo (TO-031) y RNF-14 la quiere en config | TO-039 |
| A-39 | P22 | Transición Detener desde Planificando, añadida a domain-knowledge.md, architecture.md y la tabla | Materializa D-23, aprobada con el plan: el planificador que agota sus intentos detiene la novela, y el diagrama no la dibujaba | TO-039 |
| A-40 | P22 | El worker espera a un evento que encolar dispara, en vez de sondear la base con una espera fija | Evita una cifra de sondeo y no gasta consultas en vacío | TO-039 |
| A-41 | P22 | Tokens y coste se acumulan por trabajo en una variable de contexto que el llamador rellena en cada llamada | Dos novelas a la vez no mezclan sus cuentas y ningún servicio tiene que pasarlas a mano | TO-039 |
| A-42 | P23 | Coste, latencia y reintentos de infraestructura agotados detienen con detenida_por = error-interno y el motivo en el audit log | El catálogo cerrado no tiene un tipo propio para ellos y no se inventa uno | TO-039 |
| A-44 | P24 | Reanudar no reinicia los `intentos` del capítulo que se normaliza a `Pendiente` | Un proceso que cae una y otra vez en el mismo capítulo sigue acotado por `max_intentos_capitulo` (regla 14) | TO-039 |
| A-45 | P24 | Si la novela está en `Planificando` y el esquema ya existe, no se replanifica: solo `FijarEsquema`; `CerrarEscritura` solo si la novela sigue en `Escribiendo` | Son los dos cortes entre transacciones del orquestador; replanificar duplicaría el esquema y cerrar dos veces es transición inválida | TO-039 |
| A-46 | P24 | Los huérfanos se devuelven a la cola al arrancar el worker, no en cada reclamación | Solo es seguro con un único proceso por base, que garantiza el cerrojo de instancia (A-13) | TO-039 |
| A-47 | P25 | Gate en rojo en F1: DevolverAlEditor y Detener en la misma transacción, `detenida_por = error-interno` y los validadores fallidos en el audit log | En F1 no hay editor que corrija la novela entera y todo reintento tiene límite; el P32 lo sustituye por la corrección | TO-039 |
| A-48 | P25 | El gate y la publicación se inyectan en el orquestador por el puerto `Publicador` de process/service.py; un capítulo inexistente en una versión responde 404 `version-no-encontrada` con `capitulo` | versioning → process ya existe y la arista inversa sería un ciclo; el catálogo de problemas es cerrado | TO-039 |
| A-49 | P25 | `listar_versiones` va en `CONSULTAS_TRANSVERSALES` de versioning/repository.py: filtra por `novel_id` pero no por `version` | El historial mira todas las versiones a la vez | TO-039 |
| A-50 | P26 | El barrido de secretos busca en todo fichero versionado claves con forma de clave (`sk-ant-…`, `sk-lf-…`, `pk-lf-…`) y los valores de las variables secretas de `.env.example` (nombre con KEY, SECRET, TOKEN o PASSWORD); los nombres de cabecera `x-api-key` y `authorization`, solo en los casetes | Las palabras sueltas aparecen legítimamente en el plan y en las skills, y las variables no secretas (`STORYMAKER_ENV`) tienen valores que el repo contiene | TO-039 |
| A-51 | P26 | El grabador de casetes conserva solo una lista blanca de cabeceras (`content-type`, `anthropic-version`, `request-id`) y vive en `tests/herramientas/casetes.py` | Una lista negra dejaría pasar una cabecera de autenticación nueva del SDK | TO-039 |
| A-52 | P27 | `proveedor` en `config/models.yaml`, valor actual `claude_code` | No es una cifra; es del mismo tipo que el identificador de modelo | TO-040 |
| A-53 | P27 | Recuento previo con `claude_code` = caracteres ÷ `modelo.claude_code.caracteres_por_token` × `margen_estimacion`, sin sumar los ~2.600 tokens propios del CLI | El presupuesto gobierna lo que enviamos; sumar el sobrecoste a cada pieza la inflaría | TO-040 |
| A-54 | P27 | Tope de salida con `CLAUDE_CODE_MAX_OUTPUT_TOKENS`; «output token maximum» en el resultado es `SalidaTruncada` | El CLI no tiene `max_tokens`; comprobado en real | TO-040 |
| A-55 | P27 | Coste = `total_cost_usd` del CLI (nominal), o precios de config si no viene | Cuenta la caché y la llamada auxiliar del CLI | TO-040 |
| A-56 | P27 | El binario sale de `STORYMAKER_CLAUDE_CODE` o del PATH; un `.cmd` se sustituye por su `claude.exe` o se rechaza | `cmd.exe` no escapa bien los argumentos | TO-040 |
| A-57 | P27 | Se pasa `--json-schema` y se valida después con Pydantic | Guía la forma; la garantía es `schema_valido` | TO-040 |
| A-58 | P27 | `max_tokens_por_rol` medido (I-02): planificador 12000, redactor y editor 9000, extractor 6000; judge sin tocar hasta medirlo (P31). `contexto.capas.margen` 6000 → 12000, cediendo estado 18000 → 14000 y anticontexto 10000 → 8000; recuperado intacto | El planificador sacó 7.725 tokens y se truncaba con 4.000; el redactor 4.911. Recuperado no se toca porque TO-015 descansa en que la novela entera cabe en él | TO-041 |
| A-59 | P27 | `coste.latencia_maxima_novela` 1800 → 3600 | 55–75 s por llamada medidos con `claude_code`; treinta minutos detendrían una novela sana | TO-041 |
| A-60 | P27 | `nombres_exactos` no marca una diferencia solo de mayúsculas, y solo toma como forma de nombre las palabras en mayúscula del nombre declarado | El humo real suspendía capítulos por «boya» (el perro se llama Boya) y «varadero» («Varadero de Remedios»); un modelo no escribe un nombre propio en minúscula, y lo que sí hace —otra grafía, un casi-nombre— se sigue cazando. Residuo declarado en O-02 | TO-041 |
| A-61 | P27 | Segunda calibración con la novela completa: redactor y editor 16000, extractor 8000, margen 16000 (estado 12000, anticontexto 6000), `margen_estimacion` 1,35 | Redactor hasta 8.149 y dos topes de 9.000 alcanzados (el CLI reintenta dentro del turno); extractor 4.955; la estimación quedaba un 5–7 % por debajo en prompts de ~20.000 | TO-041 |
| A-62 | P28 | Sin tabla `validador`: el registro vive en `quality/registro.py` y una prueba lo compara con el índice de `verification.md` | Es un catálogo sin novela; una tabla sin `novel_id` rompería RD-01 y la prueba del P05 | TO-042 |
| A-63 | P28 | `informe_critica` no es única por (capítulo, intento) y se ordena por intento y orden de inserción | Una reanudación tras un corte entre aceptar y extraer reescribe con el mismo intento (A-44); la propiedad de reanudación lo cazó | TO-042 |
| A-64 | P29 | La mitad programática de `consistencia_factica` coteja la edad en presente («tiene/cumple/sus/con N años») de cada personaje con los hechos vigentes y con la edad del brief | Es la contradicción enumerable que los hechos extraídos sí contienen; la edad en pasado es analepsis, no contradicción | TO-042 |
| A-65 | P29 | `cumplimiento_brief` coteja el borrador (no hay snapshot de salida antes de extraer): que nombre las entidades del alcance y que no adelante a una entidad cuya primera aparición en el plan es posterior y que el canon no ha nombrado | El hook corre antes de la extracción; la fila O-30 hablaba del snapshot de salida | TO-042 |
| A-66 | P29 | O-31 (personaje ausente en el snapshot anterior que actúa) no se implementa | El plan del P29 no lo pide y, sin la lista de entradas en escena del brief, marcaría toda reaparición legítima | TO-042 |
| A-67 | P29 | La prueba de `trabajos_en_cola` corre sin worker | Con worker, el trabajo se reclama a veces antes de contar: era una carrera, no un fallo del código | TO-042 |
| A-68 | P30 | El hook de capítulo es asíncrono y corre cada validador en un hilo (`anyio.to_thread`) dentro de un grupo de tareas | Son síncronos y deterministas; en hilos corren a la vez sin bloquear el bucle ni pedir hueco en el pool | TO-042 |
| A-69 | P30 | O-53 (ortografía), O-55 (descripciones repetidas) y O-56 (deriva de estilo) no se miden todavía | Sin diccionario en el stack cerrado y sin registro de descripciones; el plan del P30 no los pide | TO-042 |
| A-70 | P30 | Las listas cerradas de muletillas y clichés viven en `quality/listas/` como datos versionados | Mismo criterio que las listas del guardrail (D-21): son datos, no código | TO-042 |
| A-71 | P30 | `integridad_pov` coteja el tiempo verbal solo cuando se declara presente | Detectar presente en una narración en pasado sin analizador morfológico daría más falsos positivos que aciertos | TO-042 |
| A-72 | P31 | El contrato y la evaluación del judge viven en `quality/judge.py`; el ensamblado y la llamada, en `process/judge.py`, con las piezas en `context.piezas_judge` | `quality/` no tiene arista a `context/`; `process/` sí, y es quien orquesta | TO-042 |
| A-73 | P31 | El criterio «arco» emite el score `cierre_arco` en cada capítulo; el gate usará el del último (D-15) | El registro tiene un solo score para el arco y D-15 lo asigna al judge | TO-042 |
| A-74 | P31 | Un criterio semántico sin umbral en `calidad` pasa siempre y deja su score | Sin cifra no hay con qué suspender; la fase de medición es justo para reunirla | TO-042 |
| A-75 | P32 | El editor se llama cuando falla algo que cierra el paso, venga del hook de capítulo o del judge; el corregido vuelve a pasar los tres puntos, judge incluido, y es lo que decide el policy engine | La prueba del plan (el editor arregla la longitud) exige que corrija defectos del hook; «todos los validadores» incluye al judge | TO-042 |
| A-76 | P32 | Si el hook de policy falla no corren ni judge ni editor | Lo barato primero: no se paga un juicio sobre un borrador sin schema o con una palabra vetada, y el guardrail tiene su propio sublímite | TO-042 |
| A-77 | P32 | Los defectos que solo puntúan (fase de medición) quedan en el informe pero no provocan llamada al editor | RF-QUA-07: puntúan y no suspenden; una corrección por cada defecto sin umbral calibrado multiplicaría las llamadas | TO-042 |
| A-78 | P32 | Un informe por intento con los resultados del borrador que se decide (el corregido si hubo editor); la traza guarda también los del borrador antes de corregir | La tabla no admite otra decisión que aceptar, devolver, agotar o detener, y la migración 0010 ya está commiteada | TO-042 |
| A-79 | P33 | El gate en rojo sigue deteniendo tras `DevolverAlEditor` (A-47): el editor corrige capítulos, y arreglar un fallo del gate exige reescribir capítulos aceptados con retcon (F4, P42–P43) | Sin retcon, «corregir» la novela en el gate dejaría un canon que no cuadra con el texto; queda para cuando exista la regeneración dirigida | TO-042 |
| A-80 | P33 | El gate corre solo la mitad programática de `cierre_arco`; la semántica es el «arco» del judge en cada capítulo | `versioning/` no tiene arista a `quality/`, y con la medición cerrada el judge ya suspende el último capítulo antes del gate | TO-042 |
| A-81 | P35 | Las contradicciones de edad usan el corte `guardrail.perfil.edad_maxima_adolescente` y listas cortas de marcadores de tono y género en `intake/reglas.py` | La cifra ya está en config (RNF-14) y una lista auditable es lo que pide una regla determinista; lo que no capture lo mide `adecuacion_tono` | TO-043 |
| A-82 | P35 | Un `comprador.identificador` con forma de correo es una contradicción de tipo `otra` sobre ese campo | El contrato no tiene patrón para el identificador ni un tipo propio, y no se edita (RNF-16) | TO-043 |
| A-83 | P35 | Los faltantes de una lista se nombran con su índice (`elementos_personalizados[2].enunciado`) y una lista ausente no obliga a nada | El formulario necesita saber qué elemento repreguntar; los elementos de una lista que no llega no existen | TO-043 |
| A-84 | P35 | `commons.esquemas.opcional(enum=[…])` quita el `const` que Pydantic genera para un `Literal` de un solo valor | El contrato escribe `origen: enum [texto-libre]` y la conformidad compara la forma exacta | TO-043 |
| A-85 | P36 | Los hechos del texto libre se devuelven en la validación como propuestos y no se persisten; al canon solo entran los de capítulos aceptados | La respuesta del contrato no lleva estado y la novela aún no existe al validar; adoptar es del policy engine sobre capítulos (RF-CANON) | TO-043 |
| A-86 | P36 | Sin tablas `dato_faltante` ni `contradiccion_brief` en la migración 0011 | Validar no crea nada y crear rechaza el brief que los tiene: ninguna novela persistida llega a tenerlos | TO-043 |
| A-87 | P36 | La petición del entrevistador la arma `intake/` con el prompt del rol y una sola capa de datos, sin el ensamblador | `intake/` es hoja y no puede importar `context/`; el tamaño lo acotan las longitudes máximas del brief y el llamador rechaza lo que no cabe | TO-043 |
| A-88 | P36 | El saneamiento parte por línea y por signo final seguido de espacio, y descarta la frase entera que casa | Un punto dentro de una palabra (`.env`) no puede partir la instrucción; descartar de más es el lado conservador | TO-043 |
| A-89 | P36 | El único proceso que el código puede lanzar es `anyio.run_process` en `commons/llm/claude_code.py` | RNF-09 prohíbe ejecutar la salida del modelo; el CLI recibe argumentos propios y la petición por stdin | TO-043 |
| A-90 | P37 | Una afirmación sobre el destinatario tiene apoyo si al menos `calidad.invencion_soporte_minimo` (0,5) de sus palabras con contenido están en el brief o el texto libre | D-13 pide un cotejo determinista y RNF-14 la cifra en config; la mitad tolera que el capítulo lo cuente con otras palabras | TO-043 |
| A-91 | P37 | Una afirmación o un tema cuya cita no está en el capítulo no cuenta como invención; un tema que el brief no excluye tampoco | Sería una invención del judge, no del texto; y el validador solo mide lo que el comprador vetó | TO-043 |
| A-92 | P38 | `max_tokens_por_rol.judge` 3000 → 10000 | El humo adversarial real mostró que el judge se truncaba siempre (salida medida 5.017) y agotaba el capítulo | TO-041 |
| A-93 | P39 | `canon/` comprueba por SQL que la novela y la versión publicada existen (`obra`, `version_novela`) | Como el JOIN con `capitulo` de A-20: `canon/` solo importa `commons/`, y el plan pone la ruta en `canon/router.py` | TO-044 |
| A-94 | P40 | Una solicitud inexistente responde 404 `novela-no-encontrada` con el motivo en `detail` | El catálogo es cerrado y no tiene `solicitud-no-encontrada` (como A-36) | TO-044 |
| A-95 | P40 | El análisis añade el capítulo que estableció el hecho a los que lo usan, y marca como derivados los hechos que establecen los capítulos afectados | El que establece también lo cuenta; y lo que se reescribe puede cambiar lo que esos capítulos establecieron | TO-044 |
| A-96 | P40 | Sin tabla `contradiccion_canon` en la migración 0012 | Ningún paso del plan 1 la escribe | TO-044 |
| A-97 | P41 | A igual similitud, el candidato es el hecho establecido antes; `hecho_candidato` devuelve su enunciado y la solicitud guarda su id | El original es el que se quiere cambiar; el contrato lo tipa como texto y la confirmación necesita el id | TO-044 |
| A-98 | P41 | El soporte de `invencion_destinatario` es el brief entero —edad en cifra y en letra, fecha de nacimiento, ocasión, quién regala, firma— más el texto libre saneado | La edad o «su hermana» vienen del brief; sin ellas el validador, que cierra siempre, contaba como invención lo que el comprador dijo | TO-044 |
| A-99 | P42 | El hecho nuevo del retcon nace `adoptado` con `origen: brief` y sin fragmento; la fila de `retcon` dice de dónde viene | Lo pide el comprador, como el brief, y `origen` no admite otro valor sin tocar la ontología | TO-044 |
| A-100 | P42 | Transición `Detener` desde `Regenerando`, en `domain-knowledge.md`, `architecture.md` y la tabla | Una regeneración que agota un capítulo tiene que poder detenerse (regla 14, RF-PROC-08); no es un estado ni un nombre nuevo, como A-39 | TO-044 |
| A-101 | P42 | El retcon cierra en v+1 los usos abiertos del hecho viejo antes de cerrarlo | RD-05: un uso no puede sobrevivir a su hecho; en v+1 los capítulos reescritos usarán el nuevo | TO-044 |
| A-102 | P43 | Antes de reescribir un capítulo, su fila vieja deja de usar hechos desde la versión nueva y cierra los que estableció si ninguna otra fila abierta los usa | Lo que siga usando un capítulo no afectado no puede cerrarse (RD-05) ni debe: su texto no cambia | TO-044 |
| A-103 | P43 | La regeneración crea una fila nueva en la versión objetivo; la de la versión publicada se queda `Obsoleto` y `Reencolar` no se usa | D-05 y la inmutabilidad: reencolar la fila vieja sería reescribir un capítulo publicado | TO-044 |
| A-104 | P43 | El snapshot se deriva siempre para la versión que se lee: presentes y ubicaciones guardados, hechos por vigencia | D-12 ya lo define como derivado; sin esto, la reescritura del 7 leería el hecho retconeado en el snapshot del 6 | TO-044 |
| A-105 | P43 | El redactor de un capítulo reescrito recibe en la tarea qué hecho cambió (viejo y nuevo) | El contexto lleva el nuevo en el snapshot, pero sin el aviso el capítulo no sabe qué debe cambiar | TO-044 |
| A-106 | P43 | `regeneracion_fiel`: la versión nueva cambia exactamente los capítulos que la anterior tiene `Obsoleto`, y el hash de la anterior se recalcula igual | Es comprobable sin saber qué trabajo publica, y cubre las dos promesas de F4: nada más cambia y nada se pierde | TO-044 |
| A-108 | P43 | `invencion_destinatario` cuenta solo si el judge dice que la afirmación no tiene apoyo (campo `apoyo`) y el cotejo por palabras tampoco lo encuentra; el prompt del judge excluye la trama | El humo adversarial real marcaba paráfrasis de rasgos del brief («cabezota» por «tozuda») y detalles de trama, y el capítulo agotaba sus intentos | TO-044 |
| A-109 | P44 | `es_terminal` de una generación exige que el orquestador la haya cerrado (`estado_cola = terminado`), además de un estado terminal | Una regeneración recién encolada sobre una novela `Publicada` salía terminal antes de empezar; el e2e de F4 lo destapó | TO-044 |
| A-110 | P44 | Los hechos y promesas conocidos del extractor van en la capa Estado, no en la Estructural | Son estado del mundo y crecen con la novela; en la Estructural, que no se degrada, detuvieron la regeneración real con ContextoNoCabe | TO-044 |
| A-111 | P45 | Un personaje aparece en un capítulo si participa en un evento que narra o es su POV; un lugar, si lo es de un evento o del capítulo | El planificador fija POV y lugar aunque el extractor no los cite en un evento | TO-046 (F5) |
| A-112 | P47a | Las versiones que ya existían se marcan `publicada` en la migración 0013 | Pasaron el gate de su momento | TO-045 |
| A-113 | P47a | Una versión rechazada ocupa su número y la novela queda `Detenida`, sin intento siguiente | Es lo que ya hacía un gate en rojo (A-47, A-79); la vigente sigue siendo la anterior | TO-045 |
| A-114 | P47a | Sin servidor MCP configurado, `render_visual` falla con ese motivo | Es la implementación de producción, no un doble: sin navegador no se publica | TO-045 |
| A-115 | P47a | Una reanudación que encuentra la candidata ya escrita la reutiliza | La reanudación no duplica y el contenido de la candidata no cambia | TO-045 |
| A-116 | P47b | Un hallazgo de datos y uno de maquetación detienen igual la generación; la clase, el rol dueño y la tool van en el detalle del score y en el audit log | Todo gate en rojo detiene (A-47, A-79, A-113) y el gate no reescribe capítulos, así que ninguno gasta intentos | TO-046 (F5) |
| A-117 | P47b | Las pruebas contra el servidor MCP real se saltan, diciendo por qué, si no está en marcha en `STORYMAKER_PRUEBAS_MCP_URL` (por defecto `http://localhost:8931/mcp`); `evaluar` se prueba entero sin navegador | La suite no depende de un proceso externo; el paso exige correrlas con el servidor en marcha, y así se cerró | TO-046 (F5) |
| A-118 | P47b | Playwright MCP fijado a 0.0.82; los errores de consola se cuentan por la cabecera, no por el prefijo `[ERROR]` | El formato de texto de las tools es el contrato del harness; una excepción no capturada sale sin prefijo | TO-046 (F5) |
| A-119 | P48 | Un export `fallido` se relanza con el siguiente `POST`; uno `disponible` no se rehace nunca | Un fallo es de infraestructura o de paridad, no del contenido publicado; «una vez por versión» vale para el PDF entregado | TO-046 (F5) |
| A-120 | P48 | Un export `en-curso` que sobrevive a un reinicio pasa a `fallido` al arrancar | Corre en segundo plano en el mismo proceso: si el proceso cae, nadie lo termina | TO-046 (F5) |
| A-121 | P48 | Un PDF sin paridad queda `fallido` y no se sirve; se guarda en disco para el diagnóstico | Servirlo sería validar uno y entregar otro (TO-003) | TO-046 (F5) |
| A-122 | P48 | El export corre como tarea de fondo de la petición, fuera de la cola de trabajos | No llama al modelo ni consume presupuesto en vuelo; la cola es de generaciones | TO-046 (F5) |
| A-123 | P48 | El PDF sale del Chromium de Playwright y `render_visual` usa el navegador del servidor MCP (Edge en esta máquina): misma página, misma URL y mismo motor Chromium, pero dos procesos | «El mismo render» se sostiene por la página y el motor; `paridad_pdf_web` compara el PDF con el DOM del render del que sale | TO-046 (F5) |
| A-124 | P49 | El 404 de `/favicon.ico` no cuenta como error de consola en `render_visual` | El navegador lo pide por su cuenta y el contrato de lectura no lo incluye; la página real del frontend no sirve favicon. **Retirada**: el frontend sirve su favicon | TO-046 (F5), TO-050 |
| A-43 | P23 | La latencia de una novela se mide desde trabajo.iniciada_en en reloj de pared | Sobrevive a un reinicio; cuenta también el tiempo caído, que es el lado conservador | TO-039 |
| A-125 | TO-047 | Apertura y pago de una promesa son vínculos con filas de capítulo (`promesa_capitulo`); el estado se deriva de las filas de la versión | La fila nueva reabre o paga sin tocar lo que lee la anterior (regla 15) | TO-047 |
| A-126 | TO-047 | La reconciliación no escribe nada: una promesa está en una versión si una fila de la versión la abre o la paga | Es la regla 3 del desarrollador escrita como consulta | TO-047 |
| A-127 | TO-047 | `cierre_arco` corre sobre el capítulo reescrito al aceptarlo, antes de consolidar; el gate lo sigue pasando sobre la versión entera | Tras el gate la candidata es inmutable y una rechazada detiene (A-113); antes de consolidar, la extracción se descarta sin rastro | TO-047 |
| A-128 | TO-047 | Cuenta como pendiente del reescrito toda promesa nueva y toda que pagaba su fila anterior y él no paga | Los no afectados no cambian y los reescritos posteriores solo pagan lo que conservan | TO-047 |
| A-129 | TO-047 | El intento fallido lo decide el policy engine con un veredicto `cierre_arco` que cierra el paso, con el contador del capítulo | Mismas transiciones y mismo límite que un validador del hook de capítulo | TO-047 |
| A-130 | TO-047 | Una promesa «nueva» igual a una que el capítulo puede reabrir se reabre | Es la duplicación que la regla 2 evita | TO-047 |
| A-131 | TO-047 | El snapshot deriva las promesas abiertas para la versión que se lee | Como los hechos (A-104): el de un no afectado decía las promesas de la versión anterior | TO-047 |
| A-132 | TO-047 | Las promesas que conserva el reescrito van en la capa Estructural | Son destino, que no se degrada, y están acotadas por un capítulo | TO-047 |

## Instrucciones pendientes

Lo que el desarrollador ha pedido durante la ejecución y todavía no se ha aplicado, con el
paso en que toca. **Esta lista manda sobre la memoria de la conversación**, que puede no estar.

| # | Instrucción | Cuándo | Estado |
| --- | --- | --- | --- |
| I-01 | **Test de humo con modelo real solo si la credencial está en el entorno.** Si lo está: apuntar aquí la ruta de la base de la novela, su coste y la URL de la traza en Langfuse. Si no: apuntarlo y **seguir con las fases siguientes**, porque la suite no depende de él. Esta instrucción sustituye a la condición de parada 1 del plan | Cierre de F1 (P26–P27) | **aplicada** con `proveedor: claude_code` (I-04): base, coste y traza en § Coste real y «Novela de humo» |
| I-02 | **En el test de humo, registrar por capítulo los tokens de salida y los de razonamiento reales** (`Respuesta.tokens_salida` y `tokens_razonamiento`, que viene de `usage.output_tokens_details.thinking_tokens`). Si algún capítulo sale truncado (`SalidaTruncada`) o se acerca a `max_tokens`, **ajustar `modelo.max_tokens_por_rol`** y reequilibrar `contexto.capas` para que sigan sumando 100.000 con `margen ≥ max_tokens` de cada rol; marcarlo como decisión del agente y continuar | Cierre de F1 (P27), solo si hay humo real | **aplicada**: tokens por llamada en `data/humo-20260924T163649.json`; ajustes A-58 y A-61 |
| I-03 | **Lean**: Lean 4 está instalado en la máquina del desarrollador y un `lake build` mínimo sin Mathlib, desde cero tras `lake clean`, tarda **2,6 segundos**. Fijar `formal.lean_timeout_segundos` con margen holgado, del orden de **10 veces** (≈ 26 s), y cambiar su marca de `[bloqueado]` a `[provisional — calibrar tras la demo]`. Activar `formal.gate_activo` y el chequeo incremental si el tiempo de la F5 lo permite; si no, dejarlo preparado y anotarlo aquí. En el shell de esta sesión `lean` y `lake` no estaban en el PATH de bash: buscarlos (p. ej. `~/.elan/bin`) antes de activar | F5 | **aplicada en lo que cabe** en el P49: `lean_timeout_segundos` = 26 `[provisional]`; `gate_activo` sigue en `false` porque falta el generador Lean (RF-EXP-03, post-demo); `lean` y `lake` responden con `~/.elan/bin` en el PATH |
| I-04 | **Cambio aprobado por el desarrollador el 2026-09-24: proveedor del modelo vía Claude Code, sin clave de API.** Contenido completo en § «I-04 · Cambio aprobado» más abajo. Se aplica **al cerrar la F1 y antes de empezar la F2**: dentro del P27, **antes** de ejecutar el humo real, porque sin él el humo no se ejecuta (no hay `ANTHROPIC_API_KEY`) | Cierre de F1 (P27), antes del humo | **aplicada** en el P27 (commit «P27: Añadir el proveedor claude_code…»); TO-040, RI-013 |
| I-05 | Un commit por paso, en imperativo; **push al cerrar cada fase** (`git push origin backend-v1`) | Cierre de cada fase | F0 a **F5 subidas** (F5 al cerrar el P49) |
| I-06 | Decisiones menores a `docs/trade-offs.md` marcadas «decidido por el agente — revisar». TO-038 recoge A-01…A-13; **TO-039 recoge A-14…A-51** (escrita en el P27); TO-040, A-52…A-57. Las de F2 en adelante, en una entrada por fase | Cierre de cada fase | aplicada: TO-042 (F2), TO-043 (F3), TO-044 (F4), TO-045 (cambio de contrato) y TO-046 (F5) |
| I-07 | `specs/openapi.yaml` no se modifica (salvo los cambios aprobados: 1.1.0, TO-037; 1.2.0, TO-045); si un paso parece exigirlo, detenerse y explicarlo. Ninguna credencial en el repo ni en los logs; el código lee la configuración del entorno según `.env.example` | Siempre | vigente |
| I-08 | Al terminar la F5: actualizar la spec (requisitos cubiertos), `docs/verification.md` (filas que ya se ejecutan) y `docs/registro-iteraciones.md`; resumir qué funciona, qué no y qué queda post-demo | Cierre de F5 (P49) | **aplicada** en el P49 |
| I-09 | `ejemplos/novela-ejemplo.pdf` es entregable obligatorio: si falta la página `lectura`, queda **pendiente del paso de integración P49, no descartado** | P49 | **aplicada** en el P49 |
| I-10 | **El frontend debe regenerar su cliente tipado desde el contrato `specs/openapi.yaml` 1.2.0** (TO-045): `Version.estado` (`candidata`, `publicada`, `rechazada`); `obtenerVersion` sirve cualquier estado; `version_vigente`, `listarVersiones` y el export, solo `publicadas`. La lectura de una candidata es la que pinta `render_visual` | Al subir el cambio de contrato; lo aplica el frontend | **aplicada** en la integración de la demo: `schema.d.ts` regenerado, la prueba de contrato espera la 1.2.0, y dos pruebas nuevas abren una candidata por su URL y comprueban que el selector solo ofrece publicadas |

### I-04 · Cambio aprobado: proveedor del modelo vía Claude Code, sin clave de API

Texto del desarrollador (2026-09-24), que manda sobre cualquier resumen:

No hay clave de la API de Anthropic disponible. Las llamadas al modelo podrán hacerse a
través de Claude Code en modo no interactivo, usando la sesión con la que el desarrollador ya
ha iniciado sesión en esta máquina.

1. **Segunda implementación del `Protocol` de `commons/llm/`**, que invoca el CLI de Claude
   Code como subproceso: prompt por stdin, salida en JSON y modelo según `config/models.yaml`.
   Consultar `claude --help` para las opciones exactas; no suponerlas.
2. **Seguridad, obligatoria:** el subproceso se ejecuta **con todas las herramientas
   desactivadas** (sin lectura ni edición de ficheros, sin bash, sin red) y con una carpeta de
   trabajo temporal y vacía, nunca el repo. El texto libre del brief es contenido no
   confiable, y una inyección no puede poder actuar sobre la máquina. Test que lo compruebe
   con el corpus de inyección.
3. **Selección por configuración**: clave `modelo.proveedor` con valores `api` y
   `claude_code` en `config/thresholds.yaml` o en `config/models.yaml` (donde encaje con
   TO-017). La implementación de la API se mantiene intacta.
4. **Lo que cambia con este proveedor**, documentado:
   - el conteo de tokens previo a la llamada pasa a ser una estimación con margen, y el
     registro posterior usa los datos de uso que devuelva el CLI, si los devuelve;
   - el coste registrado en Langfuse es nominal;
   - los schemas de las tools se validan en el backend con Pydantic sobre la salida, porque
     no hay modo `strict`; un fallo de schema cuenta como intento fallido.
   Reflejarlo en la spec (RNF afectados), en `docs/architecture.md` y en
   `docs/verification.md` (las filas de conteo de tokens, coste y schema estricto pasan a
   depender del proveedor).
5. **Pruebas**: la implementación nueva se prueba con un doble del subproceso en `tests/`, y
   el test de humo real puede ejecutarse con `modelo.proveedor: claude_code` sin ninguna clave.
6. Registrarlo en `docs/trade-offs.md` como **cambio de arquitectura aprobado por el
   desarrollador**, con el motivo y los costes (conteo estimado, coste nominal, límites del
   plan).

**Efecto sobre las condiciones de parada:** la condición 1 («la credencial del modelo no está
disponible») deja de aplicarse cuando `modelo.proveedor` es `claude_code`: en ese caso el humo
del P27 se ejecuta. Esto matiza I-01.

## Parada

**Resuelta** (2026-09-24). La condición 2 del P47 —`render_visual` tenía que pintar una versión
que la API no servía antes de publicarla— la resolvió el desarrollador con un **cambio de
contrato** en la línea de la opción A: la versión nace `candidata`, el gate completo corre
sobre ella y solo entonces pasa a `publicada` o a `rechazada` (TO-045, RI-018, contrato
1.2.0). El P47 se parte en P47a y P47b (`plan1.md`).

## Cómo reanudar

Estado al escribir esto: **plan 1 cerrado** (P49), fusionado con el frontend e **integración y ensayo de la demo terminados** (RI-023 a RI-035) en `Contexto-semilla-v2`, subida a
`origin/Contexto-semilla-v2`. No queda paso del plan: lo siguiente
es la lista priorizada de § Post-demo; el hueco de promesas ya se resolvió (TO-047). Para `render_visual` real, arrancar el
servidor MCP como dice `docs/browser-mcp.md`; sin él, ninguna versión se publica (A-114).

```bash
git switch Contexto-semilla-v2
cd backend && uv sync
uv run pytest -q
```

**Verificación de cada paso.** El script vivía fuera del repositorio; esto es lo que hace, y
hay que comprobar el **código de salida**, no la última línea: un `| tail` enmascaró una vez
un rojo y se commiteó (corregido en `96c65a1`).

```bash
cd backend
uv run ruff format . && uv run ruff check --fix .   && uv run mypy app tests   && uv run pytest -q -rf; echo "salida=$?"   # salida=0 o no hay commit
```

**Actualizar este fichero al cerrar un paso**: fila de «Estado» (paso actual, último commit),
un renglón en «Hecho», decisiones nuevas `A-NN` en «Decisiones», y todo en el mismo commit
del paso. Mensaje: `PNN: Verbo en imperativo…` más la línea `Co-Authored-By`.

**Dónde está cada pieza** (para no releer la conversación):

- Contrato y conformidad: `tests/contrato/` (`pendientes.py` es la lista que cada endpoint
  vacía; el P49 la exige vacía). Validación dinámica: fixture `validar_contra_contrato`.
- Fixtures: `instancia` (app con HTTP y los dos dobles), `entorno` (recursos sin HTTP);
  dobles en `tests/dobles/` (`ModeloGuionizado`, `RegistroTrazas`, `ContadorDeterminista`,
  `guiones.guion_completo`); datos en `tests/fixtures/` (brief del contrato, esquema,
  borradores, extracciones, `novela_planificada`).
- Generación: `process/cola.py` (encolar, `Generacion`), `process/worker.py`,
  `process/orquestador.py` (`_inicial`, `_detener`, `_comprobar_topes`, `_cerrar`),
  `process/capitulo.py` (ciclo), `process/aceptar.py` (extracción y transacción con
  checkpoint), `process/planificar.py`, `process/transiciones.py` (tabla).
- `_cerrar` corre el gate y publica (P25). La publicación es `versioning/service.Publicacion`,
  inyectada en `Worker` desde `main.py`; en pruebas, `entorno.orquestador()`.
- Migraciones hasta `0012_regeneracion.sql`; la siguiente es `0013_exportacion.sql` (P48). Informe de crítica: `quality.registrar_informe` desde `process/capitulo._decidir_y_registrar`.

**Notas del P24** (hecho; se conservan para el P27):

- Al arrancar, los trabajos `en-curso` (`cola.devolver_huerfanos`, hecho en P24) vuelven a
  `pendiente` para que el worker los retome; el orquestador ya salta los capítulos
  `Aceptado`.
- La reanudación **no es una transición**: `orquestador.estado_inicial` normaliza a
  `Pendiente` el capítulo que quedó en `Escribiendo`, `Validando` o `Reescribiendo`,
  escribiendo el estado directamente (no hay arista en la tabla, y es a propósito).
- La prueba de propiedad: para cualquier punto de corte, los aceptados son un prefijo
  contiguo y ninguno se acepta dos veces (`UNIQUE (novel_id, numero, version)` en `capitulo`).
- La prueba con proceso real (matar a mitad del capítulo 5) es del P27, con
  `tests/e2e/app_con_dobles.py` y `tests/e2e/proceso.py`.

**Trampas ya encontradas**: el SDK de Anthropic 1.x va sobre `httpx2` (casetes con
`httpx2.MockTransport`); Opus 5.5 no admite `tool_choice` forzado ni desactivar el thinking
(salida estructurada con `output_config.format`); en Windows los procesos hijo necesitan
`PYTHONUTF8=1`; las lambdas dentro de bucles disparan B023 (usar `functools.partial`);
hypothesis va sin `deadline` (perfil en `conftest.py`); un campo del contrato opcional y no
nulable se declara con `commons.esquemas.opcional()`, que lo omite si es `None`.
Del P27: el humo se lanza desde `backend/` —`uv run --env-file ../.env -- env PYTHONUTF8=1
pytest -m real tests/humo/test_novela_real.py -v -s`—, en segundo plano porque tarda ~30 min.
Ya no hace falta la ruta absoluta de la base: desde la integración de la demo, una
`STORYMAKER_DB_PATH` relativa cuelga de la raíz del repositorio. Si `.env` tiene una línea que
uv no sabe leer (una ruta de Windows con barras invertidas sin comillas), uv lo descarta
entero con un warning y el proceso arranca sin ninguna variable; un proceso hijo
con `stdout=PIPE` que nadie lee se bloquea al llenarse la tubería; la API de lectura de trazas
y scores de Langfuse devuelve 410 en esta organización (solo `v2/observations`), así que el
diagnóstico de un validador se hace en local; si se mata un humo, su trabajo queda `en-curso`
en la base y el siguiente arranque lo reanuda antes que cualquier novela nueva.
