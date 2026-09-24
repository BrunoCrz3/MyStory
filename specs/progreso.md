# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | P24 · Checkpoint y reanudación |
| Estado del paso | `no-iniciado` |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P23 |

## Coste real

Tope de parada: **40 USD** acumulados (plan § 1, condición 4; unidad y tope confirmados por
el desarrollador el 2026-09-24). Antes de cada ejecución
real: si `acumulado + coste.coste_maximo_novela > 40`, no se lanza.

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |
| — | — | — | 0 | 0 |

**Novela de humo** (se reutiliza en F4 y F5): base `—`, `novel_id` `—`.

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

## Pendiente

- Siguiente: **P24 · Checkpoint y reanudación**, y después el resto hasta el P49 en orden.
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
| A-43 | P23 | La latencia de una novela se mide desde trabajo.iniciada_en en reloj de pared | Sobrevive a un reinicio; cuenta también el tiempo caído, que es el lado conservador | TO-039 |

## Instrucciones pendientes

Lo que el desarrollador ha pedido durante la ejecución y todavía no se ha aplicado, con el
paso en que toca. **Esta lista manda sobre la memoria de la conversación**, que puede no estar.

| # | Instrucción | Cuándo | Estado |
| --- | --- | --- | --- |
| I-01 | **Test de humo con modelo real solo si la credencial está en el entorno.** Si lo está: apuntar aquí la ruta de la base de la novela, su coste y la URL de la traza en Langfuse. Si no: apuntarlo y **seguir con las fases siguientes**, porque la suite no depende de él. Esta instrucción sustituye a la condición de parada 1 del plan | Cierre de F1 (P26–P27) | pendiente. En el shell de esta sesión `ANTHROPIC_API_KEY` **no** estaba; las variables `LANGFUSE_*` sí |
| I-02 | **En el test de humo, registrar por capítulo los tokens de salida y los de razonamiento reales** (`Respuesta.tokens_salida` y `tokens_razonamiento`, que viene de `usage.output_tokens_details.thinking_tokens`). Si algún capítulo sale truncado (`SalidaTruncada`) o se acerca a `max_tokens`, **ajustar `modelo.max_tokens_por_rol`** y reequilibrar `contexto.capas` para que sigan sumando 100.000 con `margen ≥ max_tokens` de cada rol; marcarlo como decisión del agente y continuar | Cierre de F1 (P27), solo si hay humo real | pendiente |
| I-03 | **Lean**: Lean 4 está instalado en la máquina del desarrollador y un `lake build` mínimo sin Mathlib, desde cero tras `lake clean`, tarda **2,6 segundos**. Fijar `formal.lean_timeout_segundos` con margen holgado, del orden de **10 veces** (≈ 26 s), y cambiar su marca de `[bloqueado]` a `[provisional — calibrar tras la demo]`. Activar `formal.gate_activo` y el chequeo incremental si el tiempo de la F5 lo permite; si no, dejarlo preparado y anotarlo aquí. En el shell de esta sesión `lean` y `lake` no estaban en el PATH de bash: buscarlos (p. ej. `~/.elan/bin`) antes de activar | F5 | pendiente |
| I-04 | **Cambio aprobado por el desarrollador el 2026-09-24: proveedor del modelo vía Claude Code, sin clave de API.** Contenido completo en § «I-04 · Cambio aprobado» más abajo. Se aplica **al cerrar la F1 y antes de empezar la F2**: dentro del P27, **antes** de ejecutar el humo real, porque sin él el humo no se ejecuta (no hay `ANTHROPIC_API_KEY`) | Cierre de F1 (P27), antes del humo | pendiente |
| I-05 | Un commit por paso, en imperativo; **push al cerrar cada fase** (`git push origin backend-v1`) | Cierre de cada fase | F0 subida; F1 pendiente de push al cerrar |
| I-06 | Decisiones menores a `docs/trade-offs.md` marcadas «decidido por el agente — revisar». **TO-038 recoge A-01…A-13. A-14…A-43 están anotadas como TO-039 pero esa entrada todavía no existe**: escribirla, con su RI, en el cierre de F1 (P27) | P27 | pendiente |
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

Estado al escribir esto: **P23 cerrado (commit `17cb8bf`), siguiente P24**, rama `backend-v1`,
suite en verde (230 pruebas). Todo lo hecho hasta el P23 está subido a `origin/backend-v1`;
al cerrar la F1 se vuelve a subir (I-05).

```bash
git switch backend-v1
cd backend && uv sync
uv run pytest -q          # 230 pruebas en verde al cerrar P23
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
- `_cerrar` deja hoy la generación en `Validando` con el trabajo terminado: **el P25 lo
  sustituye** por gate (`estructura_edicion`, `elementos_obligatorios`) y publicación.
- Migraciones hasta `0008_trabajo.sql`; la siguiente es `0009_version.sql` (P25).

**Notas para el P24** (checkpoint y reanudación, RF-PROC-06, TO-023):

- Al arrancar, los trabajos `en-curso` (`repository.trabajos_huerfanos`) vuelven a
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
