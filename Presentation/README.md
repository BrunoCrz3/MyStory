# Presentación

Material de la presentación de la propuesta: la presentación que se expone y los anexos técnicos
que la respaldan. Es el entregable para quien evalúa el proyecto; el detalle vivo sigue en el
repositorio (`docs/`, `specs/`, `formal/`), y donde un anexo y el repositorio no coincidan, manda
el repositorio.

## Contenido

| Fichero | Qué es |
| --- | --- |
| `Propuesta · Novelas personalizadas con un harness agéntico (1).pptx` | La presentación: 18 diapositivas con notas del orador, fechada el 25/09/2026 |
| `Anexos/anexo-diagramas-arquitectura.pdf` | Anexo A · Diagramas de arquitectura (15 páginas) |
| `Anexos/anexo-trazas-langfuse.pdf` | Anexo B · Trazas de Langfuse (8 páginas) |
| `Anexos/Anexo-Resultados-completos-de-la-evaluación.pdf` | Anexo C · Resultados completos de la evaluación (7 páginas) |
| `Anexos/anexo-analisis-economico.pdf` | Análisis económico extendido (10 páginas) |

El sufijo `(1)` forma parte del nombre con que se subió el fichero: es la versión vigente, que
sustituyó a la anterior sin sufijo (historial de git de esta carpeta).

### La presentación

Sigue el orden del alcance (`docs/requerimientos/alcance-proyecto.md`):

| Diapositivas | Sección | Qué cuenta |
| --- | --- | --- |
| 1 | Portada | Propuesta, fecha y ponente |
| 2 | 01 · El problema y el cliente | Quién compra, para qué ocasiones y por qué fallan el escritor a medida, las plantillas y la IA sin control |
| 3 | 02 · Configuración y lectura | La entrevista que detecta faltantes y contradicciones; la lectura web con índice, ficha, portada con dedicatoria, petición de cambio y PDF |
| 4–6 | 03 · Arquitectura del harness | El bucle de seis roles, por qué una máquina de estados propia y no un agente autónomo, y las piezas que lo hacen fiable: contexto por capas, story bible versionada, tools con schema, los dos hooks, el policy engine y la skill `personalizacion-natural` |
| 7 | 04 · Validación | Programáticos, semánticos (judge y revisión humana) y Lean: qué comprueba cada uno y dónde actúa |
| 8–10 | 05 · Evaluación y observabilidad | Cinco ejecuciones representativas de las 15 reales, el caso real que solo detectó Lean (brief B2) y las trazas de Langfuse |
| 11 | 06 · Guardrails | Palabras vetadas con normalización, un falso positivo real, datos personales y prompt injection |
| 12–14 | 07 · Propuesta económica | Coste unitario y margen a 69 USD por novela, el proyecto de desarrollo por fases (500 h, 48.000 USD) y la sensibilidad a tokens y revisiones |
| 15 | 08 · Demo | Una petición de cambio del lector: solo se reescribe el capítulo afectado y la versión anterior se conserva |
| 16 | 09 · Riesgos y siguientes pasos | Tres riesgos con su mitigación y el plan hasta el piloto |
| 17–18 | Cierre | Contacto y portada de los anexos |

Las notas del orador llevan el guion y el tiempo de cada bloque.

### Los anexos

- **A · Diagramas de arquitectura.** Vista del sistema, mapa de features del backend, bucle de
  generación de un capítulo, ensamblado del contexto y presupuesto de tokens, máquinas de estado,
  esquema conceptual de la story bible en SQLite, regeneración dirigida, gate de publicación con
  los puntos donde corre cada validador, y observabilidad. Fuente: `docs/architecture.md` y
  `docs/domain-knowledge.md`.
- **B · Trazas de Langfuse.** Una generación real de diez capítulos (24/09/2026): resumen, árbol de
  spans, coste y latencia por rol, scores por validador, vista del proyecto con los prompts
  versionados, y lo que la observabilidad enseñó. Los costes son nominales: con el proveedor
  `claude_code` se registra lo que costaría la llamada a la API (TO-055).
- **C · Resultados de la evaluación.** Las 15 ejecuciones reales, todas con el modelo de verdad:
  resumen y metodología, validadores por ejecución, cobertura de los cinco briefs de evaluación,
  qué enseñaron los fallos y limitaciones. Fuente: `docs/evaluacion-preliminar.md` y
  `docs/caso-lean.md`.
- **Análisis económico extendido.** Coste de tokens, infraestructura y operación por novela,
  precio de venta y posicionamiento, margen, sensibilidad y recuperación del proyecto, con las
  fuentes consultadas.

La diapositiva 18 nombra más anexos de los que hay en esta carpeta. Los demás están en el
repositorio: el red-team en `docs/red-team.md`, el plan de verificación en `docs/verification.md`
y la cronología en Lean en `formal/lean/`. La especificación TLA+ del harness (`formal/tla/`)
todavía está prevista.

## Idioma

**Todo el material está en español**, igual que el resto del repositorio. Es coherente con lo que
presenta:

- el producto escribe novelas en español, y parte del sistema depende de ello: el guardrail
  normaliza plurales, diminutivos y acentos del español y trata la ñ como letra propia (A-15 de
  `docs/trade-offs.md`);
- la ontología, las specs, el código de dominio y los estados que muestra la interfaz usan los
  nombres en español (`CLAUDE.md` regla 1), así que las diapositivas y los anexos citan los mismos
  nombres que se ven en el repositorio y en la demo;
- la propuesta económica toma como referencia el mercado español: tarifas de perfiles de IA en
  euros (convertidas a USD) y comisiones de pago con tarjeta en España.

**Se mantienen en inglés** los términos técnicos que la disciplina usa así y que el curso nombra
así: *harness*, *story bible*, *hook*, *policy engine*, *guardrail*, *judge* (*LLM-as-judge*),
*span*, *tracing*, *context management*, *prompt injection*, *prompt caching*. También los
nombres de componentes y validadores tal como aparecen en el código (`cierre_arco`,
`render_visual`, `lean_nacimiento`).

**Una diferencia con el repositorio**: la diapositiva 4 nombra los roles en inglés, como en el
alcance, y el repositorio los nombra en español:

| Diapositiva | Repositorio |
| --- | --- |
| Interviewer | entrevistador |
| Planner | planificador |
| Writer | redactor |
| Editor | editor |
| Judge | judge |
| Extractor | extractor |

## Lo que no está aquí

- **El vídeo de la demo.** El alcance lo pide en `/presentacion/`, o enlazado desde el `README.md`
  si supera el límite de tamaño de GitHub; `CLAUDE.md` lo tiene reservado como previsto. Esta
  carpeta se llama `Presentation/`: cuando se suba el vídeo conviene decidir cuál de los dos
  nombres se queda.
- **La novela de ejemplo**: está en `ejemplos/novela-ejemplo.pdf`, con el brief que la generó en
  `ejemplos/brief-ejemplo.json`.
