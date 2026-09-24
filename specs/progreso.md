# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | P12 · Encargo y obra: crear, listar y consultar novelas |
| Estado del paso | `no-iniciado` |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P11 |

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

## Pendiente

- Siguiente: **P12 · Encargo y obra: crear, listar y consultar novelas**, y después el resto hasta el P49 en orden.
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
