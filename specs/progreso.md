# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | P20 · Extractor y aceptación |
| Estado del paso | `no-iniciado` |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P19 |

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

## Pendiente

- Siguiente: **P20 · Extractor y aceptación**, y después el resto hasta el P49 en orden.
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

## Parada

Vacío mientras no se active ninguna de las cuatro condiciones del plan § 1. Si se activa:
condición, paso, qué se intentó y qué se necesita del desarrollador.

## Cómo reanudar

```bash
git switch backend-v1
cd backend && uv sync
uv run pytest          # debe estar en verde salvo el paso en curso
```

Después, ir al paso actual del plan. Si su estado es `pruebas-escritas`, las pruebas ya están
y se sigue por el código; si es `en-verde`, falta ejecutar su «Hecho cuando», actualizar
este fichero y hacer commit.
