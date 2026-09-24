# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | P33 · `cierre_arco` en el gate |
| Estado del paso | `no-iniciado` |
| Intentos fallidos en el paso actual | 0 de 3 (el P32 cerró con 1) |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P32 |

## Coste real

Tope de parada: **40 USD** acumulados (plan § 1, condición 4; unidad y tope confirmados por
el desarrollador el 2026-09-24). Antes de cada ejecución
real: si `acumulado + coste.coste_maximo_novela > 40`, no se lanza.

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |
| 2026-09-24 | P27 | Humo 1 (`proveedor: claude_code`): el planificador se truncó con `max_tokens` 4000 y la novela quedó `Detenida` (error-interno). La generación registró 0 USD porque la llamada fallida no devuelve `usage`; **estimación nominal ≤ 0,40 USD** (Opus 5.5, hasta 4 × 4000 tokens de salida con los reintentos del CLI) | 0,40 | 0,40 |
| 2026-09-24 | P27 | Medición puntual en base temporal (planificador y dos redactor del capítulo 1, topes altos en memoria) para fijar I-02 | 0,41 | 0,81 |
| 2026-09-24 | P27 | Humo 2: capítulos 1 y 2 aceptados en el cuarto intento por un falso positivo de `nombres_exactos`; parado a mano en el capítulo 3 para no gastar ni pasar el tope de latencia. Base apartada como `data/storymaker-demo-intentos-p27.db` | 1,55 | 2,36 |
| 2026-09-24 | P27 | Humo 3, **verde**: novela publicada como versión 1, diez capítulos, 25 llamadas, 1.647 s (`coste_usd` de la generación, nominal) | 5,06 | 7,42 |

**Novela de humo** (se reutiliza en F4 y F5): base `data/storymaker-demo.db` (ruta absoluta al ejecutar desde `backend/`), `novel_id` `4e884416-fa5d-4f7a-b013-94554af5a29e`, versión 1 publicada. Traza: `https://us.cloud.langfuse.com/project/cmu5p7ovq02acad0d3x5caggq/traces/e296b4f51ef4012cc416f6b14fbd3a16`. Informe por llamada: `data/humo-20260924T163649.json`. Los intentos fallidos están en `data/storymaker-demo-intentos-p27.db`.

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

## Pendiente

- Siguiente: **P33 · `cierre_arco` en el gate**, y después el resto hasta el P49 en orden.
- Casetes HTTP (plan § 4.1, capa 2): **pendientes**; solo se graban con `proveedor: api` y no hay clave. El grabador y el reproductor existen (`tests/herramientas/casetes.py`).
- **`ejemplos/novela-ejemplo.pdf` — entregable obligatorio del alcance, pendiente del paso
  de integración P49.** Se genera contra la página `lectura` real del frontend. Si al llegar
  al P49 esa página no existe todavía, el PDF sigue aquí como **pendiente, no descartado**,
  con el comando exacto, y el plan no se da por cerrado hasta que esté commiteado.

## Post-demo

Lo que se decidió no hacer en la demo y **no se olvida**. No es trabajo de este plan.

| Qué | Por qué queda fuera | Decisión |
| --- | --- | --- |
| **Replanificación de capítulos pendientes** (invalidación de restricción de destino) | Sin RF en la spec 1; un defecto sistémico se trata como reescritura y queda registrado con su clasificación | D-14, aceptada por el desarrollador |
| El resto de la lista post-demo de la spec | Entrevistador conversacional, TLA+, servidor MCP, agente de seguridad, gate de Lean, SSE, PO-11 y PO-12 | `specs/spec1.md` § 7 Post-demo |

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
| A-31 | P19 | El hook de policy lo ejecuta process/ (process/hooks.py) y el de capítulo quality/; policy/ solo decide sobre sus veredictos | process/ es quien tiene arista a guardrail/; quality/ y policy/ no | TO-039 |
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
| A-43 | P23 | La latencia de una novela se mide desde trabajo.iniciada_en en reloj de pared | Sobrevive a un reinicio; cuenta también el tiempo caído, que es el lado conservador | TO-039 |

## Instrucciones pendientes

Lo que el desarrollador ha pedido durante la ejecución y todavía no se ha aplicado, con el
paso en que toca. **Esta lista manda sobre la memoria de la conversación**, que puede no estar.

| # | Instrucción | Cuándo | Estado |
| --- | --- | --- | --- |
| I-01 | **Test de humo con modelo real solo si la credencial está en el entorno.** Si lo está: apuntar aquí la ruta de la base de la novela, su coste y la URL de la traza en Langfuse. Si no: apuntarlo y **seguir con las fases siguientes**, porque la suite no depende de él. Esta instrucción sustituye a la condición de parada 1 del plan | Cierre de F1 (P26–P27) | **aplicada** con `proveedor: claude_code` (I-04): base, coste y traza en § Coste real y «Novela de humo» |
| I-02 | **En el test de humo, registrar por capítulo los tokens de salida y los de razonamiento reales** (`Respuesta.tokens_salida` y `tokens_razonamiento`, que viene de `usage.output_tokens_details.thinking_tokens`). Si algún capítulo sale truncado (`SalidaTruncada`) o se acerca a `max_tokens`, **ajustar `modelo.max_tokens_por_rol`** y reequilibrar `contexto.capas` para que sigan sumando 100.000 con `margen ≥ max_tokens` de cada rol; marcarlo como decisión del agente y continuar | Cierre de F1 (P27), solo si hay humo real | **aplicada**: tokens por llamada en `data/humo-20260924T163649.json`; ajustes A-58 y A-61 |
| I-03 | **Lean**: Lean 4 está instalado en la máquina del desarrollador y un `lake build` mínimo sin Mathlib, desde cero tras `lake clean`, tarda **2,6 segundos**. Fijar `formal.lean_timeout_segundos` con margen holgado, del orden de **10 veces** (≈ 26 s), y cambiar su marca de `[bloqueado]` a `[provisional — calibrar tras la demo]`. Activar `formal.gate_activo` y el chequeo incremental si el tiempo de la F5 lo permite; si no, dejarlo preparado y anotarlo aquí. En el shell de esta sesión `lean` y `lake` no estaban en el PATH de bash: buscarlos (p. ej. `~/.elan/bin`) antes de activar | F5 | pendiente |
| I-04 | **Cambio aprobado por el desarrollador el 2026-09-24: proveedor del modelo vía Claude Code, sin clave de API.** Contenido completo en § «I-04 · Cambio aprobado» más abajo. Se aplica **al cerrar la F1 y antes de empezar la F2**: dentro del P27, **antes** de ejecutar el humo real, porque sin él el humo no se ejecuta (no hay `ANTHROPIC_API_KEY`) | Cierre de F1 (P27), antes del humo | **aplicada** en el P27 (commit «P27: Añadir el proveedor claude_code…»); TO-040, RI-013 |
| I-05 | Un commit por paso, en imperativo; **push al cerrar cada fase** (`git push origin backend-v1`) | Cierre de cada fase | F0 y **F1 subidas** (F1 al cerrar el P27) |
| I-06 | Decisiones menores a `docs/trade-offs.md` marcadas «decidido por el agente — revisar». TO-038 recoge A-01…A-13; **TO-039 recoge A-14…A-51** (escrita en el P27); TO-040, A-52…A-57. Las de F2 en adelante, en una entrada por fase | Cierre de cada fase | TO-039 **aplicada** en el P27; vigente para las fases siguientes |
| I-07 | `specs/openapi.yaml` no se modifica; si un paso parece exigirlo, detenerse y explicarlo. Ninguna credencial en el repo ni en los logs; el código lee la configuración del entorno según `.env.example` | Siempre | vigente |
| I-08 | Al terminar la F5: actualizar la spec (requisitos cubiertos), `docs/verification.md` (filas que ya se ejecutan) y `docs/registro-iteraciones.md`; resumir qué funciona, qué no y qué queda post-demo | Cierre de F5 (P49) | pendiente |
| I-09 | `ejemplos/novela-ejemplo.pdf` es entregable obligatorio: si falta la página `lectura`, queda **pendiente del paso de integración P49, no descartado** | P49 | pendiente |

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

Vacío mientras no se active ninguna de las cuatro condiciones del plan § 1. Si se activa:
condición, paso, qué se intentó y qué se necesita del desarrollador.

## Cómo reanudar

Estado al escribir esto: **P32 cerrado, siguiente P33**. Rama `backend-v1`,
suite en verde (343 pruebas). Todo lo hecho hasta el P23 está subido a `origin/backend-v1`;
al cerrar la F1 se vuelve a subir (I-05).

```bash
git switch backend-v1
cd backend && uv sync
uv run pytest -q          # 343 pruebas en verde al cerrar P32
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
- Migraciones hasta `0010_calidad.sql`; la siguiente es `0011_saneamiento_brief.sql` (P36). Informe de crítica: `quality.registrar_informe` desde `process/capitulo._decidir_y_registrar`.

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
Del P27: el humo se lanza desde `backend/` con la base en **ruta absoluta** (una relativa se
resuelve desde el directorio de trabajo) — `uv run --env-file ../.env -- env
STORYMAKER_DB_PATH="$(cd .. && pwd -W)/data/storymaker-demo.db" PYTHONUTF8=1 pytest -m real
tests/humo/test_novela_real.py -v -s`, en segundo plano porque tarda ~30 min; un proceso hijo
con `stdout=PIPE` que nadie lee se bloquea al llenarse la tubería; la API de lectura de trazas
y scores de Langfuse devuelve 410 en esta organización (solo `v2/observations`), así que el
diagnóstico de un validador se hace en local; si se mata un humo, su trabajo queda `en-curso`
en la base y el siguiente arranque lo reanuda antes que cualquier novela nueva.
