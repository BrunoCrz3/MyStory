# Especificaciones Técnicas
## Agente generador de novelas de ciencia ficción

**Versión:** 1.0
**Estado:** Borrador para revisión
**Documento hermano:** `especificaciones_funcionales.md`

---

## 1. Principios de diseño

1. **Separar planificación de redacción.** El modelo escribe mejor cuando no tiene que inventar y recordar a la vez. Toda decisión estructural se toma antes de escribir prosa.
2. **Estado externo, no memoria del modelo.** La coherencia no se delega en la ventana de contexto: vive en una base de datos consultable y verificable.
3. **Generar, validar, corregir.** Ningún capítulo se da por bueno sin pasar por validadores automáticos.
4. **Contexto jerárquico y acotado.** El coste y la calidad se degradan con contextos enormes; se inyecta solo lo relevante, resumido en varios niveles.
5. **Idempotencia y reanudabilidad.** Cada paso es una transición de estado persistida; el sistema puede caerse y continuar donde estaba.
6. **Modelo intercambiable.** La lógica no depende de un proveedor concreto.

---

## 2. Arquitectura general

```
┌────────────────────────────────────────────────────────────┐
│                      Cliente (Web UI)                       │
└───────────────────────────┬────────────────────────────────┘
                            │ REST + SSE/WebSocket
┌───────────────────────────▼────────────────────────────────┐
│                      API (FastAPI)                          │
│   Proyectos · Artefactos · Jobs · Streaming · Export        │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│                  Orquestador (grafo de estados)             │
│   ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────┐   │
│   │ Arquitecto│→│ Escaletista│→│ Escritor │→│ Validadores  │   │
│   └──────────┘ └─────────┘ └────┬─────┘ └──────┬────────┘   │
│                    ▲             │   reescritura │           │
│                    └─────────────┴───────────────┘           │
│   ┌──────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│   │ Estilista │ │ Archivista   │ │ Revisor global         │  │
│   └──────────┘ └──────────────┘ └────────────────────────┘  │
└───────┬─────────────────┬──────────────────┬───────────────┘
        │                 │                  │
┌───────▼──────┐  ┌───────▼───────┐  ┌───────▼──────────────┐
│ PostgreSQL   │  │ pgvector      │  │ Proveedores LLM       │
│ + JSONB      │  │ (embeddings)  │  │ (abstracción)         │
└──────────────┘  └───────────────┘  └───────────────────────┘
        │
┌───────▼──────┐  ┌───────────────┐  ┌──────────────────────┐
│ Redis + cola │  │ Almacenamiento│  │ Observabilidad        │
│ (workers)    │  │ de objetos    │  │ (trazas + métricas)   │
└──────────────┘  └───────────────┘  └──────────────────────┘
```

### 2.1 Agentes (roles del orquestador)

| Agente | Entrada | Salida | Naturaleza |
|---|---|---|---|
| **Arquitecto** | Premisa + parámetros | Biblia narrativa (JSON) | LLM, temperatura alta |
| **Escaletista** | Biblia + N | Escaleta de N capítulos (JSON) | LLM, temperatura media |
| **Escritor** | Escaleta del capítulo + contexto | Prosa del capítulo | LLM, temperatura alta |
| **Archivista** | Prosa del capítulo | Hechos canónicos + resumen + actualización de estado | LLM, temperatura baja + código |
| **Validador de continuidad** | Capítulo + libro mayor | Lista de incidencias | Reglas + LLM juez |
| **Validador de repetición** | Capítulo + corpus previo | Métricas + incidencias | Puro código (determinista) |
| **Estilista** | Capítulo validado | Capítulo pulido | LLM, temperatura media |
| **Revisor global** | Novela completa | Informes y correcciones | LLM + código |

> Los agentes no son procesos independientes: son nodos de un grafo con estado compartido y persistido.

---

## 3. Modelo de datos

### 3.1 Entidades principales

```
Project 1───N Chapter 1───N SceneDraft
   │              │
   │              └──N ChapterVersion
   ├──1 StoryBible
   ├──1 Outline
   ├──N CanonFact
   ├──N OpenThread
   ├──N StyleArtifact   (frases/imágenes usadas)
   └──N Job
```

### 3.2 Esquemas JSON (resumidos)

**StoryBible**
```json
{
  "logline": "string",
  "theme": "string",
  "subgenre": "hard_sf",
  "tone": "contemplativo",
  "setting": {
    "era": "string",
    "locations": [{"id":"loc_1","name":"","description":"","rules":[""]}],
    "politics": "string",
    "economy": "string"
  },
  "speculative_premise": {
    "concept": "string",
    "rules": ["regla 1", "regla 2"],
    "limits": ["lo que NO puede hacer"],
    "cost": "qué precio tiene usarlo"
  },
  "characters": [{
    "id": "chr_1",
    "name": "",
    "role": "protagonista",
    "want": "", "need": "", "fear": "", "flaw": "",
    "voice": {"register":"", "tics":[""], "vocabulary":""},
    "arc": {"start":"", "midpoint":"", "end":""},
    "relationships": [{"with":"chr_2","type":"","tension":""}]
  }],
  "timeline_before_ch1": [{"when":"", "what":""}],
  "glossary": [{"term":"", "definition":"", "first_use_chapter": null}],
  "motifs": ["string"],
  "forbidden": ["temas vedados por el autor"]
}
```

**Outline / ChapterPlan**
```json
{
  "chapter_number": 1,
  "working_title": "",
  "pov_character_id": "chr_1",
  "location_ids": ["loc_1"],
  "story_time": {"start":"D0 08:00","end":"D0 14:00"},
  "dramatic_function": "detonante",
  "goal": "", "conflict": "", "outcome": "",
  "scenes": [{
    "id":"sc_1_1",
    "beats":["beat a","beat b"],
    "entering_state":"", "exiting_state":"",
    "new_information":["lo que el lector aprende aquí"]
  }],
  "threads_opened": ["thr_1"],
  "threads_advanced": [],
  "threads_closed": [],
  "world_state_delta": [{"entity":"chr_2","change":"herido"}],
  "hook": "",
  "target_words": 2500
}
```

**CanonFact**
```json
{
  "id": "fact_042",
  "subject": "chr_2",
  "predicate": "estado_vital",
  "value": "muerto",
  "chapter_established": 7,
  "scope": "global",
  "status": "vigente",
  "revoked_by": null,
  "evidence_span": "cita textual breve del capítulo",
  "confidence": 0.95
}
```

**OpenThread**
```json
{
  "id":"thr_1",
  "question":"¿Quién saboteó el reactor?",
  "opened_chapter":2,
  "planned_close_chapter":14,
  "closed_chapter":null,
  "status":"abierto",
  "importance":"principal"
}
```

**ChapterVersion**
```json
{
  "chapter_number": 5,
  "version": 3,
  "text": "…",
  "word_count": 2480,
  "origin": "generated|edited|mixed",
  "model": "…", "temperature": 0.9, "seed": 1234,
  "prompt_hash": "sha256:…",
  "validation": {"blocking":0,"major":1,"minor":4},
  "created_at": "…"
}
```

### 3.3 Persistencia
- **PostgreSQL** con columnas `JSONB` para biblia, escaleta y hechos; índices GIN sobre `subject`/`predicate` en `canon_fact`.
- **pgvector** para embeddings de escenas, párrafos e imágenes literarias.
- **Almacenamiento de objetos** para exportaciones y copias del manuscrito.
- **Redis** para colas de trabajo, bloqueos por proyecto y caché de prompts.

---

## 4. Gestión de contexto

El contexto que recibe el Escritor para el capítulo *i* se compone por capas, con presupuesto de tokens fijo:

| Capa | Contenido | Presupuesto orientativo |
|---|---|---|
| L0 — Sistema | Rol, estilo, restricciones duras | 5 % |
| L1 — Canon comprimido | Biblia filtrada: solo personajes, lugares y reglas implicados en el capítulo *i* | 20 % |
| L2 — Estado del mundo | Hechos canónicos vigentes relevantes + hilos abiertos | 15 % |
| L3 — Memoria media | Resúmenes de capítulos 1..i-2 (1 párrafo cada uno) | 15 % |
| L4 — Memoria inmediata | Resumen detallado de i-1 + **últimas 400–600 palabras literales** del capítulo anterior | 15 % |
| L5 — Recuperación | Top-k fragmentos recuperados por similitud semántica con los beats del capítulo *i* | 10 % |
| L6 — Plan | ChapterPlan completo del capítulo *i* | 10 % |
| L7 — Restricciones negativas | Frases, imágenes y estructuras prohibidas por reuso | 10 % |

Reglas:
- El **texto literal del final del capítulo anterior** es obligatorio: garantiza continuidad de tono y evita saltos bruscos.
- La **recuperación (RAG)** se hace sobre el propio manuscrito: se busca por entidad mencionada en el plan (`chr_2`, `loc_5`) y por similitud de beats, no por keywords sueltas.
- Los resúmenes son **jerárquicos**: escena → capítulo → acto. Al superar cierto número de capítulos, los más antiguos se colapsan a nivel de acto.
- Si el presupuesto se excede, se recorta por orden inverso de prioridad: L5 → L3 → L1.

---

## 5. Coherencia: diseño del validador

### 5.1 Extracción de hechos
Tras generar un capítulo, el **Archivista** ejecuta una llamada con salida estructurada (JSON Schema forzado, temperatura ≈ 0,1) que devuelve:
- hechos canónicos nuevos o modificados;
- hilos abiertos, avanzados o cerrados;
- entidades nuevas (personajes, lugares, tecnología, términos);
- marcas temporales de la escena;
- resumen del capítulo en tres niveles: una frase, un párrafo, escena a escena.

### 5.2 Comprobaciones deterministas (código, sin LLM)
| Comprobación | Método |
|---|---|
| Contradicción de hechos | Conflicto sobre la tupla `(subject, predicate)` con estado `vigente` y valores incompatibles |
| Personaje muerto que actúa | Grafo de estado vital vs. menciones de acción en capítulos posteriores |
| Cronología | Los intervalos `story_time` deben ser monótonos salvo `flashback = true` declarado |
| Ubicación imposible | Un personaje en dos localizaciones en el mismo intervalo sin tránsito narrado |
| Deriva de nombres | Distancia de edición y fonética sobre el registro de entidades; alerta si aparece una variante no canónica |
| Hilos huérfanos | Hilos con `status = abierto` al llegar al capítulo N |
| Beats no cubiertos | Cobertura semántica de cada beat del plan sobre el texto generado |
| Reglas especulativas | Coincidencia de patrones sobre las capacidades declaradas como prohibidas en `speculative_premise.limits` |

### 5.3 Comprobaciones con LLM juez
Para lo que no es reducible a reglas: consistencia de voz de personaje, motivación creíble, tensión sostenida, coherencia del subtexto temático. Se ejecuta con un prompt de auditoría, salida estructurada y **una rúbrica explícita**, sobre un modelo distinto o al menos una sesión distinta a la que escribió.

### 5.4 Bucle de corrección
```
draft → validar
  ├─ blocking > 0  → reescribir con el informe de incidencias inyectado (máx. 3 intentos)
  │                   → si persiste: marcar y escalar al autor
  ├─ major > 0     → parche quirúrgico (reescritura de los párrafos señalados)
  └─ solo minor    → estilista → aceptar
```
El prompt de reescritura recibe el texto anterior **y** la lista concreta de qué corregir; nunca se regenera a ciegas.

---

## 6. Anti-repetición: diseño del detector

Combina señales léxicas, semánticas y estructurales. Todas son deterministas y auditables.

| Señal | Implementación | Umbral inicial |
|---|---|---|
| **Solapamiento de n-gramas** | Jaccard sobre 4-gramas con stopwords filtradas, capítulo nuevo vs. cada capítulo previo | > 0,15 → incidencia |
| **Similitud semántica** | Coseno entre embeddings de capítulo y de escena | > 0,85 escena-escena → incidencia bloqueante |
| **Banco de imágenes** | El Archivista extrae metáforas y símiles a una tabla; se comparan por embedding | > 0,90 → prohibida |
| **Muletillas** | Frecuencia de trigramas no triviales en todo el manuscrito | > *m* apariciones → aviso |
| **Aperturas/cierres** | Clasificación del tipo de apertura (diálogo, descripción, acción, reflexión) y del gancho | No repetir el mismo tipo en 3 capítulos seguidos |
| **Diversidad léxica** | MTLD o TTR móvil por capítulo | Caída > 15 % respecto a la mediana → aviso |
| **Repetición estructural** | Secuencia de funciones dramáticas y de POV | Patrón idéntico en capítulos consecutivos → aviso |
| **Descripción redundante** | Embedding de cada descripción de entidad frente a descripciones previas de la misma entidad | > 0,88 → exigir información nueva |

**Realimentación:** las expresiones marcadas se acumulan en `StyleArtifact` y se inyectan en la capa L7 del contexto como lista de prohibiciones explícitas, más una instrucción de variar el patrón estructural. Este circuito cerrado es lo que evita la deriva hacia la monotonía en novelas largas.

---

## 7. Estrategia de prompting

### 7.1 Estructura común
Todos los prompts siguen el mismo esqueleto: rol y objetivo → canon relevante → estado actual → tarea concreta → restricciones duras → formato de salida → criterios de autoevaluación.

### 7.2 Notas por agente
- **Arquitecto:** pedir explícitamente límites y coste de la premisa especulativa. Una tecnología sin límites destruye el conflicto y es la principal fuente de incoherencias posteriores.
- **Escaletista:** obligar a declarar, por capítulo, la información nueva que recibe el lector. Si un capítulo no aporta información nueva, es relleno y debe replantearse.
- **Escritor:** prohibir explícitamente resumir lo ya ocurrido (fuente principal de repetición), exigir entrada tardía y salida temprana de escena, y fijar el capítulo en un único intervalo temporal salvo indicación contraria.
- **Archivista:** temperatura mínima, salida estructurada obligatoria, prohibido inferir lo que no está escrito.
- **Estilista:** autorizado a tocar ritmo y frase, prohibido alterar hechos, diálogo sustantivo o beats.

### 7.3 Parámetros de muestreo sugeridos

| Tarea | Temperatura | Top-p | Notas |
|---|---|---|---|
| Biblia | 0,95 | 0,95 | Divergencia deseable |
| Escaleta | 0,75 | 0,9 | Creatividad con estructura |
| Prosa | 0,85–0,95 | 0,95 | Con penalización de repetición si el proveedor la ofrece |
| Extracción de hechos | 0,0–0,1 | 1,0 | Salida estructurada |
| Validación | 0,2 | 1,0 | Determinismo |
| Estilo | 0,6 | 0,9 | Pulido conservador |

### 7.4 Versionado de prompts
Las plantillas viven en el repositorio, versionadas, con `prompt_hash` almacenado en cada `ChapterVersion`. Todo cambio de plantilla pasa por un banco de pruebas antes de promoverse.

---

## 8. Orquestación y ejecución

### 8.1 Máquina de estados del proyecto
```
DRAFT → BIBLE_GENERATING → BIBLE_REVIEW → BIBLE_APPROVED
      → OUTLINE_GENERATING → OUTLINE_REVIEW → OUTLINE_APPROVED
      → WRITING (bucle por capítulo) → GLOBAL_REVIEW → COMPLETED
                                    ↘ PAUSED / FAILED / CANCELLED
```
Por capítulo: `PLANNED → DRAFTING → VALIDATING → REWRITING → POLISHING → ARCHIVING → DONE`.

### 8.2 Concurrencia
- Los capítulos se escriben **secuencialmente**: el capítulo *i* depende del estado del mundo tras *i-1*. Paralelizarlos es la causa más habitual de incoherencia.
- Sí se paralelizan: embeddings, comprobaciones deterministas, extracción de hechos de capítulos ya cerrados y generación de artefactos de exportación.
- Un solo worker por proyecto, con bloqueo en Redis, evita condiciones de carrera sobre el libro mayor.

### 8.3 Resiliencia
- Cada transición se persiste antes y después de la llamada al modelo.
- Reintentos con retroceso exponencial ante errores transitorios; *circuit breaker* por proveedor.
- Respuestas del modelo que no validan contra el esquema JSON se reintentan con el error de validación inyectado; a los 3 fallos, se escala.
- Todo *job* es idempotente por `(project_id, chapter_number, step, attempt)`.

---

## 9. API (esbozo)

```
POST   /projects                          crear proyecto
GET    /projects/{id}                     estado y metadatos
POST   /projects/{id}/bible               generar biblia
PATCH  /projects/{id}/bible               editar biblia
POST   /projects/{id}/bible/approve       aprobar
POST   /projects/{id}/outline             generar escaleta
PATCH  /projects/{id}/outline             editar / reordenar
POST   /projects/{id}/outline/approve     aprobar
POST   /projects/{id}/write               iniciar o reanudar redacción
POST   /projects/{id}/pause               pausar
POST   /projects/{id}/chapters/{n}/regenerate   regenerar con instrucciones
PATCH  /projects/{id}/chapters/{n}        edición manual del autor
GET    /projects/{id}/continuity          panel de continuidad
GET    /projects/{id}/reports             informes de calidad
POST   /projects/{id}/export?format=epub  exportar
GET    /projects/{id}/stream              SSE: progreso y tokens en vivo
```

Toda operación larga devuelve `202` con un `job_id`; el progreso llega por SSE.

---

## 10. Stack propuesto

| Capa | Opción recomendada | Alternativas |
|---|---|---|
| Lenguaje | Python 3.12 | TypeScript |
| API | FastAPI + Pydantic v2 | NestJS |
| Orquestación | LangGraph o máquina de estados propia | Temporal, Prefect |
| Cola | Celery + Redis | RQ, Dramatiq, Temporal |
| BD | PostgreSQL 16 + pgvector | + SQLite en desarrollo |
| Embeddings | Modelo multilingüe de embeddings de calidad | Alternativa local (E5, BGE-M3) |
| LLM | Capa de abstracción propia sobre uno o varios proveedores | — |
| NLP determinista | spaCy (es), rapidfuzz, scikit-learn | — |
| Export | Pandoc (DOCX/PDF), EbookLib (EPUB) | — |
| Observabilidad | OpenTelemetry + Langfuse | Phoenix, Braintrust |
| Frontend | Next.js + editor tipo TipTap | — |

> Recomendación sobre la orquestación: si el equipo es pequeño, una máquina de estados propia sobre Celery es más depurable que un framework de agentes. El valor del sistema está en el modelo de estado y en los validadores, no en el framework.

---

## 11. Abstracción del proveedor de LLM

```python
class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict | None = None,
        seed: int | None = None,
    ) -> LLMResponse: ...
```
- Enrutado por tarea: modelo potente para biblia, escaleta y prosa; modelo más barato y rápido para extracción, resumen y comprobaciones.
- Registro de `input_tokens`, `output_tokens`, latencia y coste por llamada, agregados por proyecto.
- Caché por `hash(prompt + parámetros)` para evitar repetir llamadas idénticas en reintentos.

---

## 12. Presupuesto y coste

Estimación para una novela de 20 capítulos × 2.500 palabras (≈ 50.000 palabras):

| Concepto | Llamadas aprox. | Observación |
|---|---|---|
| Biblia | 2–4 | Incluye autocrítica |
| Escaleta | 3–6 | Incluye verificación de hilos |
| Prosa | 20 + reescrituras (~30 %) | ≈ 26 llamadas grandes |
| Archivado y resumen | 20–40 | Modelo barato |
| Validación LLM | 20–40 | Modelo barato |
| Estilo | 20 | Modelo medio |
| Revisión global | 5–10 | — |

Controles: presupuesto máximo por proyecto, estimación previa mostrada al autor, corte automático con aviso al superar el umbral, y métrica de coste por palabra final entregada.

---

## 13. Evaluación

### 13.1 Evaluación automática continua
- Conjunto de 10 premisas de referencia con N variable (3, 12, 30).
- Métricas: incidencias de continuidad por capítulo, similitud máxima entre capítulos, MTLD, cobertura de beats, reescrituras por capítulo, coste y latencia.
- Ejecución en cada cambio de plantilla de prompt o de modelo; comparación contra la línea base.

### 13.2 Evaluación humana
Rúbrica 1–5 sobre muestra estratificada de capítulos: coherencia, frescura, voz de personaje, ritmo, calidad de prosa, cierre satisfactorio. Al menos dos evaluadores, con acuerdo entre ellos medido.

### 13.3 Pruebas adversarias
Inyección deliberada de incoherencias (matar a un personaje y hacerlo hablar dos capítulos después, contradecir una regla tecnológica, duplicar una metáfora) para verificar que los validadores las detectan. Es la prueba que mejor predice la calidad real del sistema.

---

## 14. Seguridad y cumplimiento

- Aislamiento por proyecto y por usuario; autorización a nivel de fila.
- Cifrado en tránsito y en reposo.
- Filtro de entrada y de salida según políticas de contenido del proveedor.
- Registro de auditoría de quién generó, editó y exportó cada versión.
- Trazabilidad del origen del texto (generado / editado / mixto) para declaraciones de autoría.
- No se envían datos personales del autor a los proveedores de modelo más allá del contenido creativo estrictamente necesario.
- Retención y borrado configurables; borrado completo del proyecto a petición.

---

## 15. Riesgos técnicos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Deriva de coherencia en novelas largas | Alto | Estado externo + validación por capítulo + recuperación dirigida por entidad |
| Repetición estilística acumulada | Alto | Banco de frases e imágenes + restricciones negativas + métricas de diversidad |
| Contexto que crece sin control | Medio | Resúmenes jerárquicos + presupuesto de tokens + recorte por prioridad |
| Coste desbocado por reescrituras | Medio | Límite de intentos, parches quirúrgicos en lugar de regeneración completa, modelos baratos para tareas auxiliares |
| Escaleta demasiado rígida → prosa mecánica | Medio | Permitir desviación creativa controlada y registrada; el plan fija función, no frases |
| Final precipitado en N alto | Medio | Distribución de puntos de giro en función de N y verificación de cierre de hilos antes del último acto |
| Salidas que no validan contra el esquema | Bajo | Salida estructurada forzada + reintento con el error inyectado |
| Dependencia de un único proveedor | Medio | Capa de abstracción + pruebas con al menos dos modelos |

---

## 16. Plan de implementación

| Sprint | Entregable | Criterio de salida |
|---|---|---|
| 1 | Modelo de datos, API base, abstracción de LLM | Proyecto creable y persistente |
| 2 | Arquitecto + Escaletista con salida estructurada | Biblia y escaleta válidas para N arbitrario |
| 3 | Escritor + gestión de contexto por capas | Novela de 5 capítulos generada de extremo a extremo |
| 4 | Archivista + libro mayor de continuidad | Hechos e hilos extraídos y consultables |
| 5 | Validadores de continuidad y de repetición | Detección verificada con pruebas adversarias |
| 6 | Bucle de reescritura + estilista | Reducción medible de incidencias bloqueantes a cero |
| 7 | UI de revisión, edición y versionado | Autor capaz de intervenir en cualquier fase |
| 8 | Revisión global, informes y exportación | Novela de 20 capítulos que supera los criterios de aceptación |

---

## 17. Decisiones abiertas

1. ¿Modo desatendido permitido desde v1, o toda novela exige aprobación de biblia y escaleta?
2. ¿Los umbrales anti-repetición son globales o configurables por proyecto según el estilo buscado?
3. ¿El LLM juez debe ser de un proveedor distinto al escritor para reducir el sesgo de autoevaluación?
4. ¿Se permite reescritura retroactiva de capítulos ya aprobados cuando cambia el canon, o se congela lo aprobado?
5. ¿Multi-POV desde v1 o diferido a F4?
