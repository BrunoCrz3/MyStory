# BUILD SPEC — Harness multiagente generador de novelas de CF
## Documento de construcción para ejecución one-shot con Claude Code

**Versión:** 1.0
**Tipo:** Especificación ejecutable (no descriptiva)
**Documentos fuente:** `especificaciones_funcionales.md`, `especificaciones_tecnicas.md`, `flujo_agente_novela.drawio`
**Destinatario:** Claude Code, en un repositorio vacío

---

## 0. Cómo usar este documento

### 0.1 Prompt de arranque

Coloca este fichero en la raíz del repositorio vacío y lanza:

```
Lee BUILD_SPEC.md completo antes de escribir una sola línea de código.
Implementa el proyecto exactamente como se especifica, en el orden de la sección 17.
El entregable es el inventario cerrado de la sección 21: ni un fichero menos.
Trabaja sobre el repositorio git siguiendo la sección 22 (rama, commits, CI, PR).
No pidas confirmación entre pasos: ejecuta el plan entero.
Al terminar, ejecuta `make verify` y no des la tarea por hecha hasta que pase en verde.
Si algo del spec es ambiguo, aplica el valor por defecto de la sección 20 y anótalo en DECISIONS.md.
```

### 0.2 Reglas de ejecución para el agente constructor

1. **Este documento manda sobre tus preferencias.** Si conoces un patrón mejor, impleméntalo solo si no contradice una decisión de la sección 2.
2. **Nada de red durante los tests.** Todo el pipeline debe poder ejecutarse de extremo a extremo offline con el proveedor `FakeLLM`. Esto es un requisito duro, no una comodidad.
3. **Escribe los tests antes de dar por cerrado cada módulo**, no al final del proyecto.
4. **No inventes dependencias.** La lista de la sección 2.2 es cerrada.
5. **No uses secretos reales en ningún fichero.** Únicamente nombres de variables de entorno (`ANTHROPIC_API_KEY`) y valores tipo `TU_CLAVE_AQUI` en los ejemplos.
6. **Todo fichero que generes debe compilar y pasar `ruff` y `mypy` en modo estricto.**

### 0.3 Definición de terminado

`make verify` ejecuta, en este orden, y todo debe pasar:

```
python scripts/check_inventory.py   # todos los ficheros de la §21 existen y no están vacíos
ruff check . && ruff format --check .
mypy src/
pytest -q                           # tests unitarios + integración con FakeLLM
python -m novela demo               # pipeline completo offline
test -f out/demo/manuscrito.md
```

Y además:
- El fichero `out/demo/manuscrito.md` debe contener **exactamente 3 capítulos, cada uno con exactamente 4 líneas de prosa**.
- El inventario de la **sección 21** debe estar completo: `make inventory` en verde.
- El repositorio debe quedar como describe la **sección 22**: rama de trabajo, historial de commits limpio, CI definida y PR abierta.
- `make verify` debe pasar **sin red y sin clave de API**. Si algo falla por falta de credenciales, la implementación es incorrecta.

---

## 1. Qué se construye

Un harness en Python que orquesta seis agentes LLM y cuatro validadores deterministas para producir una novela de ciencia ficción coherente y no repetitiva, a partir de una premisa y un número de capítulos, con el manuscrito final en Markdown y PDF.

**En el alcance de esta construcción:**
- Pipeline completo de las cinco fases del diagrama de flujo.
- CLI operativa.
- Persistencia en SQLite con artefactos espejados a disco.
- Proveedor LLM real (Anthropic) + proveedor falso determinista para tests.
- Validadores de continuidad y repetición con perfiles de umbral.
- Exportación a Markdown y PDF.
- Skills de Claude Code que acompañan al repositorio.

**Fuera del alcance de esta construcción:**
- Interfaz web, API HTTP, autenticación, multiusuario.
- PostgreSQL y pgvector (se usa SQLite + vectorización local; el interfaz queda preparado para sustituirlos).
- EPUB y DOCX (solo se deja el punto de extensión).

---

## 2. Decisiones cerradas

### 2.1 Arquitectura

| Decisión | Valor | Motivo |
|---|---|---|
| Orquestación | Máquina de estados propia, síncrona, sobre funciones puras | Depurable y trazable; ningún framework de agentes |
| Concurrencia | Capítulos **estrictamente secuenciales** | El capítulo *i* depende del estado del mundo tras *i-1* |
| Estado | SQLite + artefactos JSON/MD en disco | El canon vive fuera del contexto del modelo |
| Escritura del estado | **Solo el Archivista escribe**, en una transacción por capítulo | Evita carreras y hace el libro mayor reconstruible |
| Salidas estructuradas | JSON validado con Pydantic v2, con reintento inyectando el error de validación | Nunca se parsea prosa con regex |
| Determinismo | `FakeLLM` con fixtures + semilla fija | Tests reproducibles y offline |
| Idempotencia | Cada paso se identifica por `(project_id, chapter, step, attempt)` | Reanudable tras fallo |

### 2.2 Stack (lista cerrada)

```
python = "^3.12"
pydantic = "^2.7"
typer = "^0.12"          # CLI
rich = "^13"             # salida en consola
pyyaml = "^6"
jinja2 = "^3.1"          # plantillas de prompt
anthropic = "^0.34"      # proveedor LLM directo
httpx = "^0.27"          # proveedor OpenRouter (API compatible con OpenAI)
scikit-learn = "^1.5"    # TF-IDF y coseno (vectorización local, sin red)
rapidfuzz = "^3"         # distancia de edición para deriva de nombres
numpy = "^2"

[dev]
pytest, pytest-cov, ruff, mypy
```

Nada más. Sin LangChain, sin LangGraph, sin SQLAlchemy, sin FastAPI, sin Celery.

### 2.3 Convenciones

- Español en prompts, documentación y contenido generado; inglés en código, nombres de símbolos y mensajes de log.
- Tipado estricto en todo `src/`.
- Ninguna función con más de un nivel de responsabilidad: los agentes no validan, los validadores no escriben, el orquestador no construye prompts.

---

## 3. Parámetros configurables

### 3.1 Principio de diseño

**Todo el comportamiento parametrizable del sistema vive en ficheros YAML editables, nunca en el código.** El usuario debe poder cambiar el número de capítulos, el tamaño de capítulo, los modelos, los umbrales y los límites de gasto abriendo un fichero de texto y guardándolo, sin tocar Python y sin reinstalar nada.

El número de capítulos y el tamaño de capítulo **no son constantes, son configuración**. El tamaño se expresa con **unidad + valor**, porque el modo de pruebas mide en líneas y el modo real mide en palabras. Ningún módulo debe asumir "palabras".

Los cuatro ficheros de configuración del sistema:

| Fichero | Quién lo edita | Versionado | Propósito |
|---|---|---|---|
| `config/default.yaml` | Mantenedores, vía PR | Sí | Valores por defecto del proyecto |
| `config/profiles/{micro,full}.yaml` | Mantenedores, vía PR | Sí | Umbrales de calidad por tamaño de obra |
| **`novela.yaml`** | **El usuario, libremente** | **No** (gitignored) | **Fichero de configuración principal: es el que se toca en el día a día** |
| `out/<pid>/config.yaml` | El usuario o la CLI | No | Configuración efectiva de un proyecto concreto, modificable a mitad de obra |

`novela.example.yaml` sí se versiona: es la plantilla comentada desde la que se genera `novela.yaml`.

### 3.2 `config/default.yaml`

```yaml
project:
  language: es
  seed: 20260915

novel:
  chapters: 3                      # N — modificable en cualquier momento
  length:
    unit: lines                    # lines | words
    target: 4                      # tamaño objetivo por capítulo
    tolerance: 0                   # desviación admitida (0 = exacto, en unidad)
  subgenre: hard_sf
  tone: contemplativo
  pov: tercera_limitada
  tense: pasado
  structure: tres_actos
  hardness: plausible
  forbidden: []

profile: micro                     # micro | full

llm:
  provider: fake                   # fake | anthropic | openrouter
  models:
    architect:  {name: "claude-sonnet-4-6", temperature: 0.95, max_tokens: 4000}
    outliner:   {name: "claude-sonnet-4-6", temperature: 0.75, max_tokens: 4000}
    writer:     {name: "claude-sonnet-4-6", temperature: 0.90, max_tokens: 4000}
    rewriter:   {name: "claude-sonnet-4-6", temperature: 0.80, max_tokens: 4000}
    stylist:    {name: "claude-sonnet-4-6", temperature: 0.60, max_tokens: 4000}
    archivist:  {name: "claude-haiku-4-5", temperature: 0.10, max_tokens: 3000}
    judge:      {name: "claude-haiku-4-5", temperature: 0.20, max_tokens: 2000}
    reviewer:   {name: "claude-sonnet-4-6", temperature: 0.40, max_tokens: 4000}

  # Solo se usa con provider: openrouter. Ver §24.
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    app_title: "novela-agent"
    app_referer: "https://github.com/<usuario>/novela-agent"
    require_parameters: true       # no enrutar a proveedores sin las capacidades pedidas
    allow_fallbacks: false         # para roles de prosa: consistencia > disponibilidad
    data_collection: deny
    provider_order: []             # vacío = enrutado automático

limits:
  max_rewrite_attempts: 3
  max_schema_retries: 3
  max_cost_usd: 5.00
  context_token_budget: 30000

approval:
  bible: auto                      # auto | manual
  outline: auto
  final: auto
```

### 3.3 Perfiles de umbral — `config/profiles/`

El perfil desacopla las heurísticas de calidad del tamaño de la obra. **Aplicar umbrales de novela larga a capítulos de 4 líneas produce falsos positivos constantes**; por eso el perfil `micro` existe.

`profiles/micro.yaml` — para el modo de 3 capítulos × 4 líneas:
```yaml
repetition:
  ngram_size: 3
  jaccard_blocking: null           # desactivado: muestra insuficiente
  jaccard_warning: 0.40
  cosine_scene_blocking: null      # desactivado
  cosine_scene_warning: 0.92
  max_trigram_repeats: 2
  mtld_check: false
  opening_type_window: 3           # sí activo: 3 capítulos, 3 aperturas distintas
  forbid_reused_sentence_openers: true
continuity:
  llm_judge: true
  beat_coverage_min: 0.80
context:
  literal_tail_units: 2            # últimas 2 líneas del capítulo anterior
  mid_summaries: false             # con N=3 no hace falta memoria media
  rag_top_k: 0                     # RAG desactivado
```

`profiles/full.yaml` — para novelas reales:
```yaml
repetition:
  ngram_size: 4
  jaccard_blocking: 0.15
  jaccard_warning: 0.10
  cosine_scene_blocking: 0.85
  cosine_scene_warning: 0.78
  max_trigram_repeats: 3
  mtld_check: true
  mtld_drop_max: 0.15
  opening_type_window: 3
  forbid_reused_sentence_openers: true
continuity:
  llm_judge: true
  beat_coverage_min: 0.90
context:
  literal_tail_units: 600          # últimas 600 palabras
  mid_summaries: true
  rag_top_k: 5
```

### 3.4 Regla de sustitución de parámetros

Cambiar de `3 capítulos × 4 líneas` a `24 capítulos × 2500 palabras` debe requerir **exclusivamente** editar `novela.yaml`:

```yaml
novel:
  chapters: 24
  length:
    unit: words
    target: 2500
    tolerance: 500
profile: full
```

O, de forma equivalente, desde la CLI:

```bash
novela config set novel.chapters 24
novela config set novel.length.unit words
novela config set novel.length.target 2500
novela config set novel.length.tolerance 500
novela config set profile full
```

Ambas vías escriben en el mismo sitio y producen el mismo resultado. `novela config set` conserva los comentarios del YAML al reescribirlo.

Si hay que tocar código para esto, la implementación es incorrecta. Incluye un test que lo verifique (§16, T-09).

### 3.5 Definición de "línea"

Cuando `unit == lines`:
- Una línea es una **frase completa terminada en salto de línea** (`\n`).
- Las líneas en blanco no cuentan.
- El título del capítulo no cuenta.
- Prohibidas viñetas, numeración y encabezados dentro del cuerpo.
- El contador canónico es `novela.validators.length.count_units(text, unit)` y **ningún otro sitio cuenta líneas o palabras por su cuenta**.

### 3.6 `novela.yaml` — el fichero que el usuario cambia

Es el fichero de configuración principal. Se genera con `novela config init`, que copia `novela.example.yaml` **conservando todos los comentarios**. Contiene únicamente las claves que el usuario quiera sobrescribir: lo que no aparezca se hereda de `config/default.yaml`.

Requisitos de `novela.example.yaml`:

```yaml
# ─────────────────────────────────────────────────────────────
# novela.yaml — configuración de usuario
# Todo lo que no esté aquí se hereda de config/default.yaml
# Los cambios se aplican en la siguiente ejecución. No hace falta reinstalar.
# Valida los cambios con:  novela config validate
# ─────────────────────────────────────────────────────────────

novel:
  # Número de capítulos de la novela. Entero entre 3 y 60.
  chapters: 3

  length:
    # Unidad de medida del capítulo: "lines" (pruebas) o "words" (producción).
    unit: lines
    # Tamaño objetivo por capítulo, en la unidad de arriba.
    target: 4
    # Desviación admitida. 0 = longitud exacta.
    tolerance: 0

# Perfil de umbrales de calidad: "micro" para capítulos muy cortos,
# "full" para novela real. Ver config/profiles/.
profile: micro

llm:
  # "fake" no consume red ni dinero. "anthropic" usa ANTHROPIC_API_KEY del entorno.
  provider: fake

limits:
  # Corte de seguridad de gasto por proyecto, en dólares.
  max_cost_usd: 5.00
```

Cada clave lleva un comentario que explica qué hace, qué valores admite y qué consecuencia tiene cambiarla. Un fichero de configuración sin comentarios obliga a leer el código, que es justo lo que se quiere evitar.

### 3.7 Precedencia

De menor a mayor prioridad, resuelta en `config.py` en un único punto:

```
1. config/default.yaml                (base)
2. config/profiles/<profile>.yaml     (umbrales del perfil seleccionado)
3. novela.yaml                        (usuario)
4. out/<pid>/config.yaml              (configuración del proyecto, si existe)
5. Variables de entorno NOVELA__*     (ej. NOVELA__NOVEL__CHAPTERS=5)
6. Flags de la CLI                    (ej. --chapters 5)
```

Reglas:
- La fusión es **profunda por clave**, no sustitución de bloques enteros.
- `novela config show --resolved` imprime la configuración efectiva con el origen de cada clave. Es la herramienta de diagnóstico cuando algo no toma el valor esperado.
- Ningún módulo lee YAML ni `os.environ` por su cuenta: todos reciben el objeto `Config` ya resuelto.

### 3.8 Cambiar la configuración a mitad de proyecto

La configuración se relee en **cada invocación de la CLI**. No hay estado en memoria entre comandos ni procesos que reiniciar. Editar `novela.yaml` o `out/<pid>/config.yaml` y volver a lanzar el comando basta.

Qué hace el sistema cuando un parámetro cambia con el proyecto ya iniciado:

| Parámetro cambiado | Comportamiento obligatorio |
|---|---|
| `novel.chapters` **antes** de aprobar la escaleta | Se regenera la escaleta con el nuevo N |
| `novel.chapters` **después** de aprobar la escaleta | El sistema **no trunca ni improvisa**: avisa, propone redistribución y exige `novela outline <pid> --regenerate` o confirmación explícita |
| `novel.length.*` con capítulos ya escritos | Los capítulos existentes se marcan `stale`; `novela status` los lista; se regeneran solo si el usuario lo pide |
| `profile` | Efecto inmediato en la siguiente validación; los capítulos ya aprobados no se revalidan salvo `novela review <pid> --revalidate` |
| `llm.provider` o modelos | Efecto inmediato en la siguiente llamada; queda registrado en `trace.jsonl` |
| `limits.max_cost_usd` | Efecto inmediato en la siguiente comprobación de presupuesto |
| `project.seed` | Rompe la reproducibilidad de lo ya generado; el sistema avisa y lo anota en `config.changelog.jsonl` |

Toda modificación efectiva queda registrada en `out/<pid>/config.changelog.jsonl` con marca de tiempo, clave, valor anterior y valor nuevo. `config.snapshot.yaml` conserva de forma **inmutable** la configuración del momento de creación, para poder auditar qué produjo cada capítulo.

### 3.9 Validación de la configuración

`config.py` define un modelo Pydantic con `extra="forbid"`. Consecuencias obligatorias:

- Una clave mal escrita **falla de forma ruidosa**, no se ignora en silencio. `novel.chapter: 5` debe producir: `ConfigError: clave desconocida 'novel.chapter' en novela.yaml (¿querías decir 'novel.chapters'?)`.
- Rangos validados: `chapters` entre 3 y 60, `target` > 0, `tolerance` ≥ 0, `unit` en `{lines, words}`, `profile` debe existir como fichero en `config/profiles/`.
- Coherencia cruzada: con `unit: lines` y `target < 3`, aviso de que el capítulo no puede sostener una estructura dramática; con `unit: words` y `profile: micro`, aviso de que los umbrales están desactivados y la detección de repetición no protegerá la obra.
- `novela config validate` comprueba todo lo anterior sin ejecutar nada y devuelve código de salida 0 o 1. Se ejecuta también al inicio de cualquier comando que genere contenido.

---

## 4. Estructura del repositorio

```
novela-agent/
├── BUILD_SPEC.md
├── DECISIONS.md                  # lo genera Claude Code: decisiones tomadas por defecto
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── Makefile
├── pyproject.toml
├── inventory.yaml                # manifiesto de entregables verificable (§21)
├── novela.example.yaml           # plantilla comentada del fichero de usuario (versionada)
├── novela.yaml                   # CONFIGURACIÓN DEL USUARIO — editable, NO versionada
├── .gitignore
├── .env.example                  # ANTHROPIC_API_KEY / OPENROUTER_API_KEY = TU_CLAVE_AQUI
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # offline, sin secretos
│   │   └── nightly-real.yml      # manual, usa secreto de repositorio
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.yml
│   │   ├── feature.yml
│   │   └── calibration.yml
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── scripts/
│   ├── check_inventory.py        # valida inventory.yaml contra el árbol real
│   └── make_fixtures.py          # regenera fixtures del FakeLLM
├── CLAUDE.md                     # memoria de proyecto de Claude Code (§25.2)
├── .claude/
│   ├── settings.json             # permisos y hooks compartidos (§25.5)
│   ├── skills/
│   │   ├── narrative-canon/SKILL.md
│   │   ├── continuity-audit/SKILL.md
│   │   ├── anti-repetition/SKILL.md
│   │   ├── sf-prose/SKILL.md
│   │   └── manuscript-export/SKILL.md
│   ├── agents/                   # subagentes (§25.4)
│   │   ├── spec-auditor.md
│   │   ├── fixture-smith.md
│   │   ├── validator-engineer.md
│   │   ├── prompt-smith.md
│   │   ├── threshold-calibrator.md
│   │   └── continuity-detective.md
│   ├── commands/                 # slash commands (§25.6)
│   │   ├── verify.md
│   │   ├── spec-check.md
│   │   ├── calibrate.md
│   │   ├── chapter-debug.md
│   │   └── fixtures-check.md
│   └── hooks/                    # scripts invocados por settings.json
│       ├── block-secrets.sh
│       ├── format-python.sh
│       ├── validate-config.sh
│       └── session-start.sh
├── config/
│   ├── default.yaml
│   └── profiles/
│       ├── micro.yaml
│       └── full.yaml
├── prompts/
│   ├── _base.md                  # bloque común: rol, canon, restricciones, formato
│   ├── architect.md
│   ├── outliner.md
│   ├── writer.md
│   ├── rewriter.md
│   ├── patcher.md
│   ├── stylist.md
│   ├── archivist.md
│   ├── judge.md
│   └── reviewer.md
├── fixtures/
│   └── llm/                      # respuestas deterministas del FakeLLM
│       ├── architect.json
│       ├── outliner.json
│       ├── writer_ch1.json ... writer_ch3.json
│       ├── archivist_ch1.json ... archivist_ch3.json
│       ├── judge_clean.json
│       └── reviewer.json
├── src/novela/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── store.py
│   ├── errors.py
│   ├── llm/
│   │   ├── base.py               # Protocol LLMClient + tipos
│   │   ├── anthropic_client.py
│   │   ├── fake.py
│   │   └── router.py             # elige modelo por rol de agente
│   ├── context/
│   │   ├── builder.py            # capas L0–L7 y presupuesto
│   │   ├── summarizer.py
│   │   └── retrieval.py          # TF-IDF local; interfaz lista para pgvector
│   ├── agents/
│   │   ├── base.py               # ciclo prompt → llamada → parseo → reintento
│   │   ├── architect.py
│   │   ├── outliner.py
│   │   ├── writer.py
│   │   ├── stylist.py
│   │   ├── archivist.py
│   │   └── reviewer.py
│   ├── validators/
│   │   ├── base.py               # Issue, Severity, ValidationReport
│   │   ├── length.py
│   │   ├── bible.py
│   │   ├── outline.py
│   │   ├── repetition.py
│   │   └── continuity.py
│   ├── orchestrator/
│   │   ├── states.py             # enums de estado de proyecto y de capítulo
│   │   ├── chapter_loop.py       # fase 3 del diagrama
│   │   └── pipeline.py           # fases 0–5
│   ├── export/
│   │   ├── assembler.py          # → manuscrito.md
│   │   └── pdf.py                # → manuscrito.pdf
│   └── observability/
│       ├── trace.py              # JSONL de cada llamada
│       └── cost.py
├── tests/
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_length.py
│   ├── test_repetition.py
│   ├── test_continuity.py
│   ├── test_context_builder.py
│   ├── test_chapter_loop.py
│   ├── test_pipeline_e2e.py
│   └── test_reconfigure.py
└── out/                          # proyectos generados (gitignored salvo .gitkeep)
    └── <project_id>/
        ├── project.db
        ├── bible.json
        ├── outline.json
        ├── chapters/ch_01.md …
        ├── ledger.json
        ├── reports/
        ├── trace.jsonl
        └── manuscrito.md / manuscrito.pdf
```

---

## 5. Contratos de datos (`src/novela/models.py`)

Todos son modelos Pydantic v2 con `model_config = ConfigDict(extra="forbid")`.

```python
# ---------- configuración ----------
class LengthSpec(BaseModel):
    unit: Literal["lines", "words"]
    target: int = Field(gt=0)
    tolerance: int = Field(ge=0)

    def bounds(self) -> tuple[int, int]:
        return (self.target - self.tolerance, self.target + self.tolerance)


# ---------- canon ----------
class Character(BaseModel):
    id: str  # chr_1
    name: str
    role: str
    want: str
    need: str
    fear: str
    flaw: str
    voice: str
    arc_start: str
    arc_mid: str
    arc_end: str


class SpeculativePremise(BaseModel):
    concept: str
    rules: list[str] = Field(min_length=1)
    limits: list[str] = Field(min_length=1)  # obligatorio: sin límites no hay conflicto
    cost: str


class Location(BaseModel):
    id: str
    name: str
    description: str


class StoryBible(BaseModel):
    logline: str
    theme: str
    characters: list[Character] = Field(min_length=2, max_length=8)
    locations: list[Location] = Field(min_length=1)
    speculative_premise: SpeculativePremise
    timeline_before: list[str]
    glossary: dict[str, str]
    motifs: list[str]


# ---------- plan ----------
class Scene(BaseModel):
    id: str
    beats: list[str] = Field(min_length=1)
    new_information: list[str] = Field(min_length=1)  # si está vacío, el capítulo es relleno


class ChapterPlan(BaseModel):
    number: int = Field(ge=1)
    working_title: str
    pov_character_id: str
    location_ids: list[str]
    story_time_start: str
    story_time_end: str
    dramatic_function: str
    goal: str
    conflict: str
    outcome: str
    scenes: list[Scene] = Field(min_length=1)
    threads_opened: list[str]
    threads_advanced: list[str]
    threads_closed: list[str]
    world_state_delta: list[str]
    hook: str
    target_length: LengthSpec


class Outline(BaseModel):
    chapters: list[ChapterPlan]


# ---------- estado del mundo ----------
class CanonFact(BaseModel):
    id: str
    subject: str  # chr_1, loc_2, world
    predicate: str  # estado_vital, ubicacion, posee, sabe
    value: str
    chapter_established: int
    status: Literal["vigente", "revocado"] = "vigente"
    revoked_by: str | None = None
    evidence: str = Field(max_length=200)


class OpenThread(BaseModel):
    id: str
    question: str
    opened_chapter: int
    planned_close_chapter: int
    closed_chapter: int | None = None
    status: Literal["abierto", "cerrado"] = "abierto"
    importance: Literal["principal", "secundario"]


class ChapterSummary(BaseModel):
    number: int
    one_line: str
    paragraph: str
    by_scene: list[str]


class StyleArtifact(BaseModel):
    id: str
    kind: Literal["metafora", "imagen", "apertura", "cierre", "muletilla"]
    text: str
    chapter: int


# ---------- capítulo ----------
class ChapterVersion(BaseModel):
    number: int
    version: int
    title: str
    text: str
    unit_count: int
    origin: Literal["generated", "rewritten", "patched", "polished", "edited"]
    model: str
    temperature: float
    seed: int | None
    prompt_hash: str
    created_at: datetime


# ---------- validación ----------
class Severity(StrEnum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"


class Issue(BaseModel):
    code: str  # CONT-DEAD-ACTS, REP-NGRAM, LEN-OUT-OF-RANGE…
    severity: Severity
    message: str  # accionable: qué está mal y qué hacer
    chapter: int | None = None
    span: str | None = None
    evidence: str | None = None


class ValidationReport(BaseModel):
    issues: list[Issue]
    metrics: dict[str, float] = {}

    @property
    def blocking(self) -> list[Issue]: ...
    @property
    def major(self) -> list[Issue]: ...
```

**Códigos de incidencia obligatorios** (usar exactamente estos identificadores):

| Código | Severidad por defecto | Detector |
|---|---|---|
| `LEN-OUT-OF-RANGE` | blocking | length |
| `LEN-FORBIDDEN-FORMAT` | blocking | length (viñetas, encabezados) |
| `BIB-NO-LIMITS` | blocking | bible |
| `BIB-CONTRADICTION` | blocking | bible |
| `OUT-WRONG-COUNT` | blocking | outline |
| `OUT-THREAD-UNCLOSED` | blocking | outline |
| `OUT-FILLER-CHAPTER` | major | outline |
| `OUT-REPEATED-FUNCTION` | major | outline |
| `CONT-FACT-CONFLICT` | blocking | continuity |
| `CONT-DEAD-ACTS` | blocking | continuity |
| `CONT-TIMELINE` | blocking | continuity |
| `CONT-LOCATION-IMPOSSIBLE` | blocking | continuity |
| `CONT-RULE-VIOLATION` | blocking | continuity |
| `CONT-NAME-DRIFT` | major | continuity |
| `CONT-BEAT-MISSING` | major | continuity |
| `CONT-VOICE-DRIFT` | major | continuity (juez LLM) |
| `REP-NGRAM` | según perfil | repetition |
| `REP-COSINE` | según perfil | repetition |
| `REP-IMAGE-REUSE` | major | repetition |
| `REP-OPENING-TYPE` | major | repetition |
| `REP-SENTENCE-OPENER` | minor | repetition |
| `REP-LEXICAL-DIVERSITY` | minor | repetition |

---

## 6. Capa LLM

### 6.1 `llm/base.py`

```python
class LLMResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: int


class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> LLMResponse: ...
```

### 6.2 `llm/fake.py` — requisito crítico

`FakeLLM` resuelve cada llamada leyendo `fixtures/llm/<key>.json`, donde `key` se deriva del rol del agente y del número de capítulo. Debe:

- Ser **totalmente determinista** y no tocar la red.
- Permitir inyectar fallos programados para probar los bucles: `FakeLLM(fail_plan={"writer_ch2": ["invalid_json", "too_long"]})` hace que la primera llamada devuelva JSON inválido y la segunda un capítulo de longitud incorrecta, obligando al harness a reintentar y reescribir.
- Devolver contenidos coherentes entre sí: las fixtures del Archivista deben corresponder al texto de las fixtures del Escritor. Genera las fixtures tú mismo con contenido de CF verosímil, 3 capítulos de 4 líneas.

**Sin este componente no hay tests reproducibles.** Constrúyelo antes que el cliente real.

### 6.3 `llm/anthropic_client.py`

Cliente real con reintentos (retroceso exponencial: 1s, 2s, 4s), timeout de 120s, y registro del coste en `observability/cost.py`. La clave se lee de `os.environ["ANTHROPIC_API_KEY"]`; si no existe, error claro que indique copiar `.env.example`. **Nunca escribir la clave en logs ni en `trace.jsonl`.**

### 6.4 Proveedor OpenRouter

Especificado por completo en la **§24**. El cliente `llm/openrouter_client.py` implementa el mismo `LLMClient` Protocol; nada fuera de `llm/` cambia al pasar de Anthropic a OpenRouter.

### 6.5 Parseo de salida estructurada

`agents/base.py` implementa un único ciclo reutilizable:

```
render prompt (Jinja2)
→ llamar LLM
→ extraer JSON (tolerar ```json ... ```)
→ validar contra el modelo Pydantic
→ si falla: reintentar hasta max_schema_retries inyectando el error de validación literal en el mensaje
→ si agota reintentos: SchemaRetryExhausted
```

---

## 7. Agentes

Cada agente es una clase con un único método público `run(...)`. Ninguno escribe en el store; devuelven objetos y el orquestador persiste.

| Agente | Fichero | Entrada | Salida | Modelo (rol) |
|---|---|---|---|---|
| Arquitecto | `agents/architect.py` | premisa, parámetros | `StoryBible` | `architect` |
| Escaletista | `agents/outliner.py` | `StoryBible`, N, `LengthSpec` | `Outline` | `outliner` |
| Escritor | `agents/writer.py` | contexto ensamblado | texto del capítulo | `writer` |
| Reescritor | `agents/writer.py::rewrite` | texto + `list[Issue]` | texto corregido | `rewriter` |
| Parcheador | `agents/writer.py::patch` | texto + issues mayores | texto con párrafos sustituidos | `rewriter` |
| Estilista | `agents/stylist.py` | texto validado | texto pulido | `stylist` |
| Archivista | `agents/archivist.py` | texto final del capítulo + canon | `ArchivistOutput` | `archivist` |
| Juez | `agents/archivist.py::judge` o módulo propio | capítulo + canon | `list[Issue]` | `judge` |
| Revisor global | `agents/reviewer.py` | manuscrito + ledger | informes, títulos, sinopsis | `reviewer` |

`ArchivistOutput` agrupa: `facts: list[CanonFact]`, `threads: list[OpenThread]`, `summary: ChapterSummary`, `style_artifacts: list[StyleArtifact]`, `new_entities: list[str]`.

### 7.1 Requisitos de las plantillas de prompt

Todas heredan de `prompts/_base.md` y se renderizan con Jinja2. Variables disponibles documentadas en la cabecera de cada fichero.

**`architect.md`** debe exigir explícitamente que `speculative_premise.limits` y `cost` estén rellenos y sean sustantivos. Una tecnología sin límites destruye el conflicto y es la primera causa de incoherencias aguas abajo.

**`outliner.md`** debe exigir `new_information` no vacío en cada escena, y recibir `{{ chapter_count }}` y `{{ length_spec }}` para dimensionar la ambición de cada capítulo al tamaño real disponible. Con 3 capítulos de 4 líneas, el prompt debe pedir explícitamente una trama mínima y cerrada, no el arranque de una saga.

**`writer.md`** debe incluir, como restricciones duras:
- `{{ length_instruction }}` generada por código a partir de `LengthSpec` (§7.2).
- Prohibido resumir lo ya ocurrido (principal fuente de repetición).
- Prohibido abrir con el mismo tipo de apertura listado en `{{ forbidden_openings }}`.
- Lista literal de frases e imágenes prohibidas `{{ forbidden_phrases }}` (capa L7).
- Entrada tardía y salida temprana de escena.
- El capítulo transcurre en un único intervalo temporal salvo que el plan indique lo contrario.

**`rewriter.md`** recibe el texto anterior **y** la lista concreta de incidencias. Prohibido regenerar a ciegas: debe corregir lo señalado conservando lo que funciona.

**`archivist.md`**: temperatura mínima, salida JSON estricta, y una instrucción explícita de **no inferir nada que no esté escrito en el capítulo**. Cada `CanonFact` lleva `evidence` con una cita breve del texto.

**`judge.md`**: rúbrica explícita con los códigos `CONT-VOICE-DRIFT`, `CONT-BEAT-MISSING`, coherencia de motivación y tensión. Devuelve `list[Issue]` en JSON.

### 7.2 Instrucción de longitud generada por código

```python
def length_instruction(spec: LengthSpec) -> str:
    if spec.unit == "lines":
        return (
            f"Escribe EXACTAMENTE {spec.target} líneas de prosa. "
            "Cada línea es una frase completa terminada en salto de línea. "
            "No uses títulos, viñetas, numeración ni líneas en blanco intermedias."
        )
    low, high = spec.bounds()
    return f"Escribe entre {low} y {high} palabras de prosa continua en párrafos."
```

Este es el único punto del sistema donde se traduce configuración de tamaño a lenguaje natural.

---

## 8. Constructor de contexto (`context/builder.py`)

```python
def build_chapter_context(
    *, bible: StoryBible, plan: ChapterPlan, ledger: Ledger,
    summaries: list[ChapterSummary], previous_text: str | None,
    style_artifacts: list[StyleArtifact], profile: Profile, budget: int,
) -> ChapterContext
```

Capas y prioridad de recorte:

| Capa | Contenido | % presupuesto | Prioridad de recorte |
|---|---|---|---|
| L0 | Rol y restricciones duras | 5 | nunca |
| L1 | Canon **filtrado**: solo personajes, lugares y reglas referenciados en `plan` | 20 | 3.ª |
| L2 | `CanonFact` vigentes de esas entidades + hilos abiertos | 15 | nunca |
| L3 | Resúmenes de 1…i-2 (si `profile.context.mid_summaries`) | 15 | 2.ª |
| L4 | Resumen de i-1 + **cola literal** de `literal_tail_units` | 15 | nunca |
| L5 | RAG top-k (si `rag_top_k > 0`) | 10 | 1.ª |
| L6 | `ChapterPlan` completo del capítulo i | 10 | nunca |
| L7 | Prohibiciones derivadas de `StyleArtifact` | 10 | nunca |

Notas de implementación:
- El filtrado de L1 es por identificadores presentes en `plan`, no por búsqueda de texto.
- La cola literal se corta por unidad configurada (líneas o palabras), reutilizando `count_units`.
- Estimación de tokens: `len(text) / 3.5`, suficiente y sin dependencias.
- `ChapterContext` expone `.system`, `.user` y `.debug` (desglose por capa, que se vuelca a `trace.jsonl`).

---

## 9. Validadores

### 9.1 `validators/length.py`
- `count_units(text, unit) -> int` — contador canónico del sistema.
- Verifica rango contra `LengthSpec.bounds()` → `LEN-OUT-OF-RANGE`.
- Verifica formato prohibido con regex (`^#`, `^[-*•]`, `^\d+\.`) → `LEN-FORBIDDEN-FORMAT`.

### 9.2 `validators/bible.py`
- `limits` o `cost` vacíos o triviales (< 15 caracteres) → `BIB-NO-LIMITS`.
- Dos personajes con el mismo `role` y `want` → `BIB-CONTRADICTION`.
- Referencias cruzadas rotas (`pov_character_id` inexistente) → `BIB-CONTRADICTION`.

### 9.3 `validators/outline.py`
- `len(chapters) != config.novel.chapters` → `OUT-WRONG-COUNT` (bloqueante, sin excepciones).
- Numeración 1…N sin huecos.
- Hilo abierto sin `closed_chapter` ≤ N → `OUT-THREAD-UNCLOSED`.
- Escena con `new_information` vacío → `OUT-FILLER-CHAPTER`.
- Misma `dramatic_function` + mismo POV + misma localización en capítulos consecutivos → `OUT-REPEATED-FUNCTION`.

### 9.4 `validators/repetition.py` — 100 % determinista, sin LLM

| Comprobación | Implementación | Umbral |
|---|---|---|
| Solapamiento n-gramas | Jaccard sobre n-gramas de tamaño `profile.ngram_size`, stopwords españolas filtradas, contra cada capítulo previo | `jaccard_blocking` / `jaccard_warning`; si es `null`, la comprobación no emite esa severidad |
| Similitud semántica | `TfidfVectorizer` + coseno por escena o capítulo | `cosine_scene_*` |
| Reutilización de imágenes | Coseno entre `StyleArtifact` de tipo metáfora/imagen y las del capítulo nuevo | > 0,90 → `REP-IMAGE-REUSE` |
| Muletillas | Frecuencia de trigramas no triviales en todo el manuscrito | `max_trigram_repeats` |
| Tipo de apertura | Clasificación por reglas (diálogo si empieza por `—` o comillas; acción si el verbo principal va en primera posición; descripción; reflexión) | No repetir dentro de `opening_type_window` |
| Arranque de frase repetido | Primeras 3 palabras de cada frase frente a las ya registradas | `forbid_reused_sentence_openers` |
| Diversidad léxica | MTLD si `mtld_check` | `mtld_drop_max` |

Contrato: **un umbral `null` desactiva esa severidad, no la comprobación**. La métrica se sigue calculando y se registra en `ValidationReport.metrics` para poder calibrar.

### 9.5 `validators/continuity.py`

Parte determinista (SQL/estructuras sobre el ledger):
- Conflicto en `(subject, predicate)` con dos valores vigentes incompatibles → `CONT-FACT-CONFLICT`.
- `estado_vital == muerto` y el personaje aparece como sujeto de acción en un capítulo posterior → `CONT-DEAD-ACTS`.
- `story_time_start` de *i* anterior al `story_time_end` de *i-1* sin `flashback` declarado → `CONT-TIMELINE`.
- Mismo personaje en dos `location_id` en intervalos solapados sin tránsito narrado → `CONT-LOCATION-IMPOSSIBLE`.
- Aparición de capacidades listadas en `speculative_premise.limits` → `CONT-RULE-VIOLATION`.
- Nombre con distancia de edición ≤ 2 respecto a una entidad canónica pero distinto de ella (rapidfuzz) → `CONT-NAME-DRIFT`.
- Cobertura de beats: fracción de beats del plan detectados por similitud TF-IDF ≥ `beat_coverage_min`, si no → `CONT-BEAT-MISSING`.

Parte con juez LLM: voz de personaje, motivación y tensión. **El juez debe invocarse con un `system` distinto y sin el texto del prompt del Escritor en contexto**, para reducir el sesgo de autoevaluación.

---

## 10. Orquestador

### 10.1 Estados (`orchestrator/states.py`)

```python
class ProjectState(StrEnum):
    (
        DRAFT,
        BIBLE_GENERATING,
        BIBLE_REVIEW,
        BIBLE_APPROVED,
    )
    (
        OUTLINE_GENERATING,
        OUTLINE_REVIEW,
        OUTLINE_APPROVED,
    )
    WRITING, GLOBAL_REVIEW, COMPLETED, PAUSED, FAILED


class ChapterState(StrEnum):
    (
        PLANNED,
        DRAFTING,
        VALIDATING,
        REWRITING,
        PATCHING,
    )
    POLISHING, ARCHIVING, DONE, ESCALATED
```

Cada transición se persiste **antes y después** de la llamada al LLM. El proceso debe poder morir en cualquier punto y reanudarse con `novela write <pid>` sin repetir trabajo hecho.

### 10.2 Bucle de capítulo (`orchestrator/chapter_loop.py`)

Implementa literalmente la fase 3 del diagrama:

```
for i in 1..N:
    ctx      = build_chapter_context(...)
    draft    = writer.run(ctx)
    attempt  = 0
    while True:
        rep  = repetition.validate(draft, corpus, profile)
        cont = continuity.validate(draft, ledger, plan, bible)
        length_rep = length.validate(draft, plan.target_length)
        report = merge(rep, cont, length_rep)

        if report.blocking:
            attempt += 1
            if attempt > limits.max_rewrite_attempts:
                mark(ChapterState.ESCALATED); raise Escalation(report)
            draft = writer.rewrite(draft, report.blocking, ctx)
            continue

        if report.major:
            draft = writer.patch(draft, report.major, ctx)
            continue          # revalida: el parche puede romper otra cosa

        break

    polished = stylist.run(draft, ctx)
    assert length.validate(polished, plan.target_length).blocking == []   # el estilista no puede alterar la longitud
    arch = archivist.run(polished, bible, ledger)
    store.commit_chapter(i, polished, arch)     # transacción única
```

Detalles obligatorios:
- El parche **revalida**, no cae directo al estilista.
- Tras el estilista se revalida la longitud: es el fallo más común y silencioso.
- `store.commit_chapter` es la **única** escritura del estado del mundo, y es atómica.
- Toda llamada LLM se registra en `trace.jsonl` con rol, modelo, tokens, coste, latencia, `prompt_hash` e intento.

### 10.3 Pipeline (`orchestrator/pipeline.py`)

Fases 0–5 del diagrama. Los puntos de control respetan `approval.*`: en `auto` continúan tras validar; en `manual` dejan el proyecto en estado `*_REVIEW` y devuelven el control a la CLI.

Corte por presupuesto: antes de cada llamada se comprueba `cost.total() < limits.max_cost_usd`; si se supera, `PAUSED` con mensaje explícito.

---

## 11. CLI (`src/novela/cli.py`, Typer)

```bash
novela init "premisa…" [--chapters 3] [--profile micro] [--config config/default.yaml]
novela bible   <pid> [--approve] [--regenerate]
novela outline <pid> [--approve] [--regenerate]
novela write   <pid> [--from 1] [--to 3]
novela review  <pid>
novela export  <pid> --format md,pdf
novela run     <pid> --auto            # fases 1→5 sin intervención
novela status  <pid>
novela continuity <pid>                # panel: hechos vigentes, hilos, cronología
novela cost    <pid>
novela config init                     # crea novela.yaml desde novela.example.yaml
novela config show [--resolved]        # config efectiva con el origen de cada clave
novela config get <clave>
novela config set <clave> <valor>      # reescribe novela.yaml conservando comentarios
novela config validate                 # valida sin ejecutar nada; código de salida 0 o 1
novela demo                            # proyecto de ejemplo con FakeLLM, offline
```

`novela demo` es el comando de verificación: crea el proyecto `demo`, usa `provider: fake` y `profile: micro`, ejecuta el pipeline completo y deja `out/demo/manuscrito.md` con 3 capítulos de 4 líneas. Debe tardar menos de 10 segundos y no tocar la red.

Salida en consola con `rich`: tabla de progreso por capítulo, incidencias coloreadas por severidad, y resumen final con coste y tiempos.

---

## 12. Exportación

`export/assembler.py` concatena las `ChapterVersion` vigentes y produce `manuscrito.md`:

```markdown
# <título de la novela>

> <logline>

---

## Capítulo 1 — <título>

<4 líneas de prosa>

## Capítulo 2 — <título>
…
```

`export/pdf.py`: intenta Pandoc si está en el PATH; si no, genera el PDF con una función de respaldo mínima o informa con claridad de que falta Pandoc **sin romper el pipeline** (el Markdown ya es el entregable canónico). Anexos en `out/<pid>/reports/`: `continuity.json`, `repetition.json`, `pacing.json`, `bible.json`, `outline.json`, `ledger.json`.

---

## 13. Skills de Claude Code

Crea estas cinco skills en `.claude/skills/`. Cada `SKILL.md` lleva frontmatter YAML con `name` y `description`, y un cuerpo breve y operativo (menos de 200 líneas). No son documentación del proyecto: son instrucciones para el agente que trabajará sobre este repositorio después.

| Skill | `description` (criterio de activación) | Contenido |
|---|---|---|
| **narrative-canon** | Usar al crear o editar la biblia narrativa, personajes, reglas del mundo o glosario | Checklist de un canon sólido; regla de que toda tecnología necesita límites y coste; formato de `CanonFact`; cómo promover un cambio al canon sin romper capítulos escritos |
| **continuity-audit** | Usar al auditar coherencia, al investigar una incidencia `CONT-*` o al ampliar el validador de continuidad | Catálogo de los códigos `CONT-*`, cómo reproducir cada uno con un test, cómo consultar el ledger, criterio para clasificar severidad |
| **anti-repetition** | Usar al calibrar umbrales, investigar incidencias `REP-*` o diagnosticar prosa monótona | Explicación de cada métrica, rangos sanos por perfil, procedimiento de calibración con `metrics` del `ValidationReport`, advertencia sobre muestras pequeñas |
| **sf-prose** | Usar al escribir o editar prompts del Escritor, Reescritor o Estilista, o al juzgar calidad de prosa de CF | Principios de prosa de CF: exposición integrada en la acción, entrada tardía/salida temprana, concreción sensorial, prohibición de resumir lo ya narrado; lista de clichés del género a evitar |
| **manuscript-export** | Usar al ensamblar el manuscrito o generar PDF/DOCX/EPUB | Estructura canónica del Markdown, front matter, invocación de la skill pública `pdf` para la generación, checklist previo a entrega |

**Skills públicas que el repositorio aprovecha** (no hay que crearlas, solo referenciarlas desde `manuscript-export`): `pdf` para la generación de PDF y `docx` si más adelante se añade salida Word. Anota en el README que `skill-creator` es la vía para mantener las cinco anteriores.

---

## 14. Observabilidad

`trace.jsonl` — una línea por llamada LLM:

```json
{"ts":"…","project":"demo","chapter":1,"role":"writer","attempt":0,
 "model":"…","temperature":0.9,"seed":20260915,"prompt_hash":"sha256:…",
 "input_tokens":0,"output_tokens":0,"cost_usd":0.0,"latency_ms":0,
 "context_layers":{"L1":420,"L2":180,"L4":95,"L6":310,"L7":40}}
```

`novela cost <pid>` agrega por rol y por capítulo. Prohibido registrar la clave de API o el prompt completo (solo su hash y el desglose de capas).

---

## 15. Manejo de errores

| Situación | Comportamiento |
|---|---|
| JSON inválido del modelo | Reintento con el error de validación inyectado, hasta `max_schema_retries`, luego `SchemaRetryExhausted` |
| Incidencia bloqueante irresoluble | `ChapterState.ESCALATED`, proyecto `PAUSED`, informe en consola y en `reports/` |
| Presupuesto superado | `PAUSED` antes de la llamada, nunca después |
| Fallo de red | Reintento con retroceso exponencial; tras 3 fallos, `PAUSED` con estado íntegro |
| Fixture ausente en `FakeLLM` | Error inmediato y explícito con la clave esperada (nunca respuesta silenciosa por defecto) |
| Pandoc ausente | Aviso, se omite el PDF, el pipeline continúa |

Jerarquía en `errors.py`: `NovelaError` → `ConfigError`, `SchemaRetryExhausted`, `ValidationEscalation`, `BudgetExceeded`, `ProviderError`.

---

## 16. Tests y criterios de aceptación

| ID | Test | Debe verificar |
|---|---|---|
| T-01 | `test_length.py` | `count_units` cuenta líneas y palabras correctamente; ignora blancos y título; detecta viñetas |
| T-02 | `test_models.py` | `SpeculativePremise` sin `limits` no valida; `LengthSpec.bounds()` correcto |
| T-03 | `test_repetition.py` | Dos textos casi idénticos disparan `REP-NGRAM` en perfil `full` y **no** en `micro`; la métrica se registra en ambos |
| T-04 | `test_continuity.py` | Inyectar un personaje muerto que actúa dispara `CONT-DEAD-ACTS`; cronología invertida dispara `CONT-TIMELINE`; regla violada dispara `CONT-RULE-VIOLATION` |
| T-05 | `test_context_builder.py` | Con presupuesto reducido se recorta L5 antes que L3, y L3 antes que L1; L2, L4, L6 y L7 nunca se recortan |
| T-06 | `test_chapter_loop.py` | Con `FakeLLM(fail_plan=…)`: un bloqueante fuerza reescritura; tres fallos escalan; un mayor fuerza parche **y revalidación** |
| T-07 | `test_pipeline_e2e.py` | `novela demo` produce `manuscrito.md` con exactamente 3 capítulos de 4 líneas, sin red, en menos de 10 s |
| T-08 | `test_pipeline_e2e.py` | El ledger final tiene ≥ 1 `CanonFact` por capítulo y 0 hilos abiertos |
| T-09 | `test_reconfigure.py` | Cambiando solo el YAML a `chapters: 5, unit: words, target: 120, tolerance: 20, profile: full`, el pipeline produce 5 capítulos de 100–140 palabras. **Ningún cambio de código** |
| T-10 | `test_config.py` | Los umbrales `null` desactivan severidad pero no el cálculo de la métrica |
| T-11 | `test_config.py` | Precedencia: `novela.yaml` pisa a `default.yaml`, el proyecto pisa a `novela.yaml`, el entorno pisa al proyecto y el flag de CLI gana a todos |
| T-12 | `test_config.py` | Una clave desconocida (`novel.chapter`) lanza `ConfigError` con sugerencia; `chapters: 100` y `unit: paragraphs` fallan la validación de rango |
| T-13 | `test_reconfigure.py` | Editar `novela.yaml` entre dos invocaciones cambia el comportamiento sin reiniciar nada; cambiar `chapters` con escaleta aprobada avisa y no trunca |
| T-14 | `test_openrouter.py` | El cuerpo de la petición se construye bien con `httpx.MockTransport`: modelo con namespace, `response_format.json_schema.strict`, `provider.require_parameters`, cabeceras de atribución. Ninguna llamada real |
| T-15 | `test_openrouter.py` | Degradación por capacidad: si el modelo no soporta `json_schema` se cae a `json_object` y luego a modo prompt + reparación, y queda registrado en `trace.jsonl`. Un 404 de "no endpoints support" produce `ProviderError` con mensaje accionable |

**Cobertura mínima:** 80 % en `src/novela/validators/` y `src/novela/orchestrator/`.

T-09 es el test que demuestra que la parametrización pedida está bien resuelta. Si falla, la arquitectura tiene el tamaño acoplado y hay que corregirla, no ajustar el test.

---

## 17. Orden de implementación

0. `git checkout -b feat/harness-v1`. Andamiaje del repositorio: `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example`, `LICENSE`, `inventory.yaml`, `scripts/check_inventory.py`, `.github/` completo. Primer commit: `chore: scaffold repository and CI`.
1. `pyproject.toml`, `Makefile`, `.env.example`, estructura de directorios, `ruff` y `mypy` configurados.
2. `config.py` + YAMLs + perfiles. **Tests T-10 en verde.**
3. `models.py`. **T-02 en verde.**
4. `errors.py`, `store.py` (SQLite + espejo a disco), `observability/`.
5. `llm/base.py` + `llm/fake.py` + fixtures completas de los 3 capítulos. Sin esto no avances.
6. `validators/length.py` → **T-01**; `validators/repetition.py` → **T-03**; `validators/continuity.py` → **T-04**; `bible.py` y `outline.py`.
7. `prompts/` completos + `agents/base.py` con el ciclo de reintento.
8. Agentes: architect, outliner, writer (+rewrite, +patch), stylist, archivist, judge, reviewer.
9. `context/builder.py` + summarizer + retrieval. **T-05.**
10. `orchestrator/chapter_loop.py`. **T-06.**
11. `orchestrator/pipeline.py` + `cli.py` + `novela demo`. **T-07, T-08.**
12. `export/`. 
13. Clientes reales, al final porque el pipeline ya funciona sin ellos: `llm/anthropic_client.py`, `llm/capabilities.py` y `llm/openrouter_client.py` (§24). **T-14, T-15.**
14. Harness de Claude Code (§25): `CLAUDE.md`, las cinco skills, los seis subagentes, los cinco slash commands, `settings.json` y los cuatro scripts de hook.
15. `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` y `DECISIONS.md`.
16. `inventory.yaml` completo y `make inventory` en verde.
17. `make verify` en verde.
18. Commit final, `git push -u origin feat/harness-v1` y apertura de la PR con la plantilla rellena (§22.6).

Cada paso del 1 al 17 termina en un commit propio siguiendo Conventional Commits (§22.3). No acumules el trabajo en un único commit gigante: el historial es parte del entregable.

---

## 18. Antipatrones prohibidos

- Contar líneas o palabras fuera de `validators/length.py`.
- Cualquier constante `3` o `4` referida a capítulos o longitud en el código. Todo viene de config.
- Escribir en el ledger desde un agente o un validador.
- Paralelizar la generación de capítulos.
- Parsear salidas del modelo con expresiones regulares en lugar de JSON + Pydantic.
- Regenerar un capítulo completo cuando solo hay incidencias mayores.
- Umbrales de repetición codificados en el módulo de repetición.
- Leer YAML, `os.environ` o flags de CLI fuera de `config.py`. Todos los módulos reciben un `Config` ya resuelto.
- Ignorar en silencio una clave desconocida del fichero de configuración.
- Cachear la configuración entre invocaciones: se relee siempre, para que editar el fichero surta efecto sin reiniciar.
- Meter el prompt completo en los logs.
- Tests que requieran red o clave de API.
- Capturar excepciones de forma genérica y continuar en silencio.

---

## 19. Contenido de `DECISIONS.md`

Claude Code lo genera al terminar, con una entrada por cada punto de la sección 20 donde haya aplicado un valor por defecto, más cualquier desviación del spec, con su justificación en dos líneas.

---

## 20. Puntos abiertos y valores por defecto aplicados

Estos son los puntos que el spec no fija de forma definitiva. **Implementa el valor por defecto y anótalo**; son las decisiones que conviene revisar antes de pasar a producción.

| # | Punto abierto | Valor por defecto para esta construcción | Por qué importa |
|---|---|---|---|
| 1 | Proveedor y modelos concretos | Los de `config/default.yaml`, con `provider: fake` activo | El cliente real no debe bloquear la construcción ni los tests |
| 2 | ¿El juez debe ser un modelo distinto al Escritor? | Sí: `judge` usa un modelo más pequeño y sesión limpia | Reduce el sesgo de autoevaluación, pero encarece si se sube de gama |
| 3 | Reescritura retroactiva al cambiar el canon | **Congelar lo aprobado**: si cambia el canon, se marcan los capítulos afectados y se pide confirmación explícita | Es la decisión nº 4 que quedó abierta en el spec técnico; afecta al modelo de datos |
| 4 | Definición de "línea" | Frase completa terminada en `\n`, blancos no cuentan | Con capítulos de 4 líneas, cualquier ambigüedad aquí rompe la validación |
| 5 | Embeddings | TF-IDF local (scikit-learn) | Sin red, determinista, suficiente para `micro`; sustituible por un `EmbeddingProvider` real en `full` |
| 6 | Multi-POV | No en esta versión: un POV por capítulo, declarado en el plan | Añadir multi-POV exige registro de conocimiento por personaje |
| 7 | Idioma de salida | Español fijo; el campo existe en config pero solo se prueba `es` | Los validadores usan stopwords españolas |
| 8 | Persistencia | SQLite; interfaz `Store` abstracta para permitir Postgres después | Postgres + pgvector no aporta nada en esta fase |
| 9 | Tope de coste | 5 USD por proyecto | Con `micro` y `fake` es irrelevante; con `full` es la salvaguarda principal |
| 10 | Autoría y trazabilidad | `ChapterVersion.origin` distingue generado / reescrito / parcheado / pulido / editado | Necesario para declaraciones de autoría en publicación |

### Lo que recomiendo decidir antes de escalar a novela completa

- **Política de reescritura retroactiva** (punto 3): es la que más condiciona el modelo de datos si luego quieres editar el canon a mitad de obra.
- **Calibración real de umbrales** (punto 5 y §9.4): los valores de `full.yaml` son un punto de partida razonable, no valores medidos. Genera dos o tres novelas reales y ajusta con las `metrics` que ya quedan registradas en cada `ValidationReport`.
- **Presupuesto y enrutado de modelos**: el Archivista y el Juez se invocan tantas veces como el Escritor; bajarlos de gama es donde está el ahorro sin pérdida de calidad.

---

## 21. Inventario de entregables

Esta sección es el contrato de entrega. **Nada se da por hecho hasta que todos estos ficheros existen, no están vacíos y cumplen su criterio de aceptación.**

### 21.1 Inventario verificable por máquina

Crea `inventory.yaml` en la raíz con la lista completa de rutas, y `scripts/check_inventory.py`, que:

1. Lee `inventory.yaml`.
2. Comprueba que cada ruta existe.
3. Comprueba que ningún fichero está vacío ni contiene marcadores `TODO`, `FIXME` o `pass  # placeholder`.
4. Comprueba que los contadores por grupo coinciden con los declarados.
5. Sale con código 1 y lista de faltantes si algo no cuadra.

```yaml
# inventory.yaml (estructura)
version: 1
groups:
  - name: meta
    expected: 10
    files: [README.md, CONTRIBUTING.md, ...]
  - name: github
    expected: 7
    files: [...]
  # …
```

`make inventory` invoca ese script. Forma parte de `make verify`.

### 21.2 Grupo META — raíz del repositorio (11 ficheros)

| Ruta | Criterio de aceptación |
|---|---|
| `README.md` | Instalación, `make demo` en 3 comandos, tabla de parámetros configurables, cómo pasar de `micro` a `full`, badge de CI |
| `BUILD_SPEC.md` | Este documento, versionado en el repo |
| `DECISIONS.md` | Una entrada por cada punto de la §20 aplicado por defecto + desviaciones |
| `CONTRIBUTING.md` | Convención de commits, cómo correr tests, cómo añadir un validador nuevo, cómo calibrar umbrales |
| `CHANGELOG.md` | Formato Keep a Changelog, con la entrada `0.1.0` de esta construcción |
| `LICENSE` | MIT salvo indicación contraria |
| `Makefile` | Targets: `install`, `demo`, `test`, `lint`, `typecheck`, `inventory`, `verify`, `clean` |
| `pyproject.toml` | Dependencias exactas de §2.2, config de ruff y mypy estricto, entrypoint `novela` |
| `inventory.yaml` | Manifiesto completo y coherente con este inventario |
| `.gitignore` | Cubre `out/`, `.env`, `*.db`, cachés, `.venv` |
| `CLAUDE.md` | Memoria de proyecto de Claude Code: reglas permanentes, comandos, mapa del repo y punteros al spec (§25.2). Menos de 150 líneas |

### 21.3 Grupo GITHUB (7 ficheros)

| Ruta | Criterio de aceptación |
|---|---|
| `.github/workflows/ci.yml` | Corre offline, sin secretos, en push y PR (§22.4) |
| `.github/workflows/nightly-real.yml` | `workflow_dispatch` manual, usa secreto de repositorio, nunca en PR de forks |
| `.github/ISSUE_TEMPLATE/bug.yml` | Pide comando, perfil, extracto de `trace.jsonl` y código de incidencia |
| `.github/ISSUE_TEMPLATE/feature.yml` | Pide qué fase del pipeline afecta |
| `.github/ISSUE_TEMPLATE/calibration.yml` | Plantilla específica para ajuste de umbrales: métrica, valores observados, perfil |
| `.github/pull_request_template.md` | Checklist de §22.6 |
| `.github/CODEOWNERS` | Al menos una entrada `*` con el responsable |

### 21.4 Grupo CONFIG (4 ficheros)

| Ruta | Criterio de aceptación |
|---|---|
| `config/default.yaml` | Idéntico a §3.2, con `chapters: 3`, `unit: lines`, `target: 4`, `profile: micro` |
| `config/profiles/micro.yaml` | Idéntico a §3.3 |
| `config/profiles/full.yaml` | Idéntico a §3.3 |
| `novela.example.yaml` | Fichero de usuario comentado de §3.6; cada clave con su explicación, valores admitidos y consecuencia de cambiarla. `novela config init` lo copia a `novela.yaml` conservando comentarios |

### 21.5 Grupo PROMPTS (10 ficheros)

`prompts/_base.md`, `architect.md`, `outliner.md`, `writer.md`, `rewriter.md`, `patcher.md`, `stylist.md`, `archivist.md`, `judge.md`, `reviewer.md`.

Criterio común: cabecera con la lista de variables Jinja2 que consume, sección de restricciones duras, y sección de formato de salida. Los que devuelven JSON incluyen el esquema esperado literal.

### 21.6 Grupo FIXTURES (mínimo 10 ficheros)

`fixtures/llm/`: `architect.json`, `outliner.json`, `writer_ch1..3.json`, `archivist_ch1..3.json`, `judge_clean.json`, `reviewer.json`.

Criterio de aceptación, y es el más fácil de incumplir: **las fixtures deben ser coherentes entre sí**. Los hechos del Archivista tienen que corresponder al texto del Escritor del mismo capítulo, la escaleta tiene que referenciar personajes que existen en la biblia, y los tres capítulos tienen que tener exactamente 4 líneas. Si las fixtures son incoherentes, los tests pasan pero no prueban nada.

### 21.7 Grupo SRC (37 módulos)

| Subgrupo | Ficheros | Criterio |
|---|---|---|
| Núcleo | `__init__.py`, `__main__.py`, `cli.py`, `config.py`, `models.py`, `store.py`, `errors.py` | §5, §11, §15 |
| LLM | `llm/base.py`, `anthropic_client.py`, `openrouter_client.py`, `capabilities.py`, `fake.py`, `router.py`, `__init__.py` | §6, §24 |
| Contexto | `context/builder.py`, `summarizer.py`, `retrieval.py`, `__init__.py` | §8 |
| Agentes | `agents/base.py`, `architect.py`, `outliner.py`, `writer.py`, `stylist.py`, `archivist.py`, `reviewer.py`, `__init__.py` | §7 |
| Validadores | `validators/base.py`, `length.py`, `bible.py`, `outline.py`, `repetition.py`, `continuity.py`, `__init__.py` | §9 |
| Orquestador | `orchestrator/states.py`, `chapter_loop.py`, `pipeline.py`, `__init__.py` | §10 |
| Exportación | `export/assembler.py`, `pdf.py`, `__init__.py` | §12 |
| Observabilidad | `observability/trace.py`, `cost.py`, `__init__.py` | §14 |

Criterio transversal: `mypy --strict` limpio, sin `Any` sin justificar, y ninguna función de más de 50 líneas en los validadores y el orquestador.

### 21.8 Grupo TESTS (10 ficheros)

`tests/test_config.py`, `test_models.py`, `test_length.py`, `test_repetition.py`, `test_continuity.py`, `test_context_builder.py`, `test_chapter_loop.py`, `test_pipeline_e2e.py`, `test_reconfigure.py`, `test_openrouter.py`.

Criterio: cubren T-01…T-15 de §16, cobertura ≥ 80 % en `validators/` y `orchestrator/`, y **ninguno requiere red ni clave de API**.

### 21.9 Grupo SKILLS (5 ficheros)

`.claude/skills/{narrative-canon,continuity-audit,anti-repetition,sf-prose,manuscript-export}/SKILL.md`.

Criterio: frontmatter YAML con `name` y `description` accionable (la `description` describe *cuándo* activarla, no qué es), cuerpo de menos de 200 líneas, contenido operativo según la tabla de §13.

### 21.10 Grupo HARNESS DE CLAUDE CODE (16 ficheros)

Detallado en la **§25**: 6 subagentes en `.claude/agents/`, 5 slash commands en `.claude/commands/`, `.claude/settings.json` y 4 scripts de hook en `.claude/hooks/`. Las 5 skills se cuentan aparte en §21.9.

### 21.11 Grupo SCRIPTS (3 ficheros)

| Ruta | Criterio de aceptación |
|---|---|
| `scripts/check_inventory.py` | Valida `inventory.yaml` contra el árbol real (§21.1) |
| `scripts/make_fixtures.py` | Regenera las fixtures del `FakeLLM` de forma coherente entre agentes |
| `scripts/assert_demo_output.py` | Verifica que `out/demo/manuscrito.md` tiene exactamente 3 capítulos de 4 líneas; usa `count_units`, no su propio contador |

### 21.12 Resumen de recuento

| Grupo | Ficheros |
|---|---|
| Meta | 11 |
| GitHub | 7 |
| Harness de Claude Code (§25) | 16 |
| Config | 4 |
| Prompts | 10 |
| Fixtures | 10 |
| Src | 37 |
| Tests | 10 |
| Skills | 5 |
| Scripts | 3 |
| **Total mínimo** | **113** |

### 21.13 Entregables que NO son ficheros

| Entregable | Verificación |
|---|---|
| Rama `feat/harness-v1` con historial de commits por paso | `git log --oneline` muestra ≥ 15 commits con prefijo convencional |
| CI en verde en GitHub Actions | Badge del README apuntando al workflow |
| PR abierta con la plantilla rellena | Enlace incluido en la respuesta final |
| `make verify` en verde en local | Salida pegada en la descripción de la PR |
| Tag `v0.1.0` | Creado tras el merge, con notas tomadas del CHANGELOG |

---

## 22. Trabajo en GitHub

### 22.1 Repositorio

- Nombre sugerido: `novela-agent`.
- Rama por defecto: `main`, protegida: no se admiten pushes directos, la PR requiere CI en verde.
- Rama de esta construcción: `feat/harness-v1`.

### 22.2 Qué se versiona y qué no

| Se versiona | No se versiona |
|---|---|
| Todo `src/`, `tests/`, `config/`, `prompts/`, `fixtures/`, `.claude/skills/`, `scripts/`, `.github/` | `out/` salvo `out/.gitkeep` |
| `.env.example` con `ANTHROPIC_API_KEY=TU_CLAVE_AQUI` y `OPENROUTER_API_KEY=TU_CLAVE_AQUI` | `.env` real, siempre |
| `novela.example.yaml` (plantilla comentada) | `novela.yaml` (configuración local de cada usuario) |
| `inventory.yaml`, `Makefile`, `pyproject.toml`, documentación | `*.db`, `trace.jsonl`, `.venv/`, cachés de ruff, mypy y pytest |

Regla dura: **ninguna clave, token ni valor de credencial entra en el repositorio**, ni siquiera en fixtures, tests o ejemplos de documentación. Solo nombres de variable y marcadores tipo `TU_CLAVE_AQUI`. Activa el secret scanning del repositorio; si alguna vez se filtra una clave, se rota, no basta con borrar el commit.

Las fixtures del `FakeLLM` sí se versionan: son parte de la suite de tests y garantizan reproducibilidad.

### 22.3 Convención de commits

Conventional Commits, un commit por paso de §17:

```
chore: scaffold repository and CI
feat(config): add profile system with micro and full thresholds
feat(models): add pydantic contracts for bible, outline and ledger
feat(llm): add deterministic FakeLLM with programmable failures
feat(validators): add length, repetition and continuity validators
feat(agents): add architect, outliner and writer agents
feat(orchestrator): add chapter loop with rewrite and patch cycles
feat(cli): add novela demo end-to-end command
docs(skills): add five Claude Code skills
test: add T-09 reconfiguration test
```

Cada commit debe dejar el repositorio en estado compilable. Los commits que cierran un test del §16 lo citan en el cuerpo: `Closes T-06.`

### 22.4 CI — `.github/workflows/ci.yml`

Dispara en `push` a cualquier rama y en `pull_request` a `main`.

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python 3.12
      - install (pip install -e ".[dev]")
      - run: python scripts/check_inventory.py
      - run: ruff check . && ruff format --check .
      - run: mypy src/
      - run: pytest -q --cov=src/novela --cov-fail-under=80
      - run: python -m novela demo
      - run: python scripts/assert_demo_output.py     # 3 capítulos, 4 líneas cada uno
      - upload-artifact: out/demo/manuscrito.md
```

Requisitos no negociables de este workflow:
- **Sin secretos.** Todo corre con `provider: fake`. Si la CI necesitara una clave, la arquitectura estaría mal.
- Tiempo total por debajo de 3 minutos.
- El manuscrito de la demo se sube como artefacto: permite revisar en la PR qué prosa produce el pipeline sin ejecutarlo en local.

### 22.5 CI con modelo real — `.github/workflows/nightly-real.yml`

Solo `workflow_dispatch` (manual). Usa el secreto de repositorio correspondiente al proveedor configurado (`ANTHROPIC_API_KEY` u `OPENROUTER_API_KEY`), ejecuta una novela `micro` con proveedor real y publica el manuscrito y el informe de coste como artefactos. Nunca se dispara en PRs de forks. Tope de gasto vía `limits.max_cost_usd`.

Esta separación importa: la CI de cada commit debe ser gratuita y determinista; la validación con modelo real es un evento deliberado y con presupuesto.

### 22.6 Plantilla de PR

```markdown
## Qué hace
<resumen en 3 líneas>

## Checklist
- [ ] `make verify` en verde en local (pega la salida)
- [ ] `make inventory` en verde: los 113 ficheros del §21 existen
- [ ] CI en verde
- [ ] `out/demo/manuscrito.md` tiene 3 capítulos de 4 líneas
- [ ] Ningún secreto, clave ni `.env` añadido
- [ ] DECISIONS.md actualizado con los valores por defecto aplicados
- [ ] CHANGELOG.md actualizado
- [ ] Ningún número mágico de capítulos o longitud en el código

## Artefacto de la demo
<enlace al artefacto de CI>
```

### 22.7 Etiquetas e issues

Etiquetas mínimas: `fase-1-canon`, `fase-2-escaleta`, `fase-3-redaccion`, `fase-4-revision`, `fase-5-export`, `validador`, `calibracion`, `coste`, `prompt`, `skill`.

Las incidencias de calidad narrativa se abren con la plantilla `calibration.yml` e incluyen siempre las `metrics` del `ValidationReport`, no impresiones subjetivas. Es lo que permite ajustar umbrales con datos.

### 22.8 Releases

`v0.1.0` tras el merge de esta construcción. Contenido de las notas: alcance del harness, limitaciones conocidas (perfil `micro` sin calibrar, sin EPUB/DOCX, sin API HTTP) y los puntos abiertos de §20 pendientes de decidir.

---

## 23. Inventario de outputs en ejecución

Lo anterior es lo que produce la *construcción*. Esto es lo que produce cada *ejecución* del pipeline, en `out/<project_id>/`.

| Fichero | Fase que lo genera | Contenido | Esquema |
|---|---|---|---|
| `project.db` | 0 | SQLite: estado, versiones, hechos, hilos, artefactos de estilo | interno |
| `config.snapshot.yaml` | 0 | Copia **inmutable** de la config efectiva al crear el proyecto | §3 |
| `config.yaml` | 0 | Configuración del proyecto, **editable a mitad de obra** | §3.6 |
| `config.changelog.jsonl` | todas | Registro de cada cambio de configuración: clave, valor anterior, valor nuevo, marca de tiempo | §3.8 |
| `bible.json` | 1 | Canon aprobado | `StoryBible` |
| `reports/bible_validation.json` | 1 | Incidencias del validador de biblia | `ValidationReport` |
| `outline.json` | 2 | Plan de los N capítulos | `Outline` |
| `reports/outline_validation.json` | 2 | Incidencias de escaleta | `ValidationReport` |
| `chapters/ch_01.md … ch_NN.md` | 3 | Texto final de cada capítulo | Markdown |
| `chapters/ch_NN.versions.json` | 3 | Historial de versiones del capítulo | `list[ChapterVersion]` |
| `ledger.json` | 3 | Estado del mundo acumulado | hechos, hilos, entidades, cronología |
| `summaries.json` | 3 | Resúmenes en 3 niveles por capítulo | `list[ChapterSummary]` |
| `style_artifacts.json` | 3 | Frases, imágenes y aperturas ya usadas | `list[StyleArtifact]` |
| `reports/chapter_NN.json` | 3 | Incidencias y métricas por capítulo | `ValidationReport` |
| `reports/continuity.json` | 4 | Auditoría final: hilos, cronología, arcos | informe |
| `reports/repetition.json` | 4 | Expresiones más repetidas y métricas globales | informe |
| `reports/pacing.json` | 4 | Longitud, densidad de diálogo y tensión por capítulo | informe |
| `reports/corrections.json` | 4 | Correcciones propuestas con capítulo, span y motivo | `list[Issue]` |
| **`manuscrito.md`** | 5 | **Entregable canónico**: novela completa | Markdown §12 |
| `manuscrito.pdf` | 5 | Derivado vía Pandoc; opcional si falta Pandoc | PDF |
| `trace.jsonl` | todas | Una línea por llamada LLM | §14 |
| `cost.json` | todas | Coste agregado por rol y capítulo | §14 |

Reglas sobre estos outputs:

- `manuscrito.md` es la **fuente canónica**; PDF, DOCX y EPUB son derivados y nunca se editan directamente.
- Todo el directorio `out/` está en `.gitignore`. Para compartir un resultado se adjunta como artefacto de CI o como release asset, no como commit.
- `trace.jsonl` no contiene prompts completos ni claves: solo hashes, métricas y desglose de capas de contexto.
- Un proyecto debe poder reconstruirse por completo desde `config.snapshot.yaml` + `bible.json` + `outline.json` + las fixtures o el proveedor real con la misma semilla. Si no es reproducible, falta trazabilidad en algún punto.

---

## 24. Proveedor OpenRouter

### 24.1 Qué cambia y qué no

OpenRouter expone una API compatible con la de OpenAI en `https://openrouter.ai/api/v1/chat/completions`. Cambiar de proveedor afecta **exclusivamente** a `src/novela/llm/`. Agentes, validadores, orquestador, contexto y exportación no se tocan: si alguno de ellos necesita cambios, la abstracción de §6.1 está rota.

Lo que sí cambia respecto a un proveedor único:

1. Los identificadores de modelo llevan espacio de nombres: `anthropic/claude-sonnet-4.5`, `openai/gpt-5.2`, `meta-llama/…`.
2. El forzado de JSON depende del modelo **y del proveedor concreto que atienda la petición**, no solo del modelo.
3. El coste no es una tabla fija: depende de a quién se enrute la petición.
4. Una misma petición puede atenderla un proveedor distinto en cada llamada.

El punto 4 es el que tiene consecuencias narrativas y lo trata §24.6.

### 24.2 Configuración

```yaml
llm:
  provider: openrouter
  models:
    architect:  {name: "anthropic/claude-sonnet-4.5", temperature: 0.95, max_tokens: 4000}
    outliner:   {name: "anthropic/claude-sonnet-4.5", temperature: 0.75, max_tokens: 4000}
    writer:     {name: "anthropic/claude-sonnet-4.5", temperature: 0.90, max_tokens: 4000}
    rewriter:   {name: "anthropic/claude-sonnet-4.5", temperature: 0.80, max_tokens: 4000}
    stylist:    {name: "anthropic/claude-sonnet-4.5", temperature: 0.60, max_tokens: 4000}
    archivist:  {name: "openai/gpt-5.2-mini",         temperature: 0.10, max_tokens: 3000}
    judge:      {name: "google/gemini-2.5-flash",     temperature: 0.20, max_tokens: 2000}
    reviewer:   {name: "anthropic/claude-sonnet-4.5", temperature: 0.40, max_tokens: 4000}
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    app_title: "novela-agent"
    app_referer: "https://github.com/<usuario>/novela-agent"
    require_parameters: true
    allow_fallbacks: false
    data_collection: deny
    provider_order: []
```

Poder mezclar familias de modelos por rol es la ventaja real de OpenRouter en este harness: el Escritor pide calidad de prosa, el Archivista pide extracción estructurada barata y el Juez pide criterio independiente. Que el Juez sea de otra familia que el Escritor refuerza además lo que pide §9.5 sobre sesgo de autoevaluación.

### 24.3 Cliente — `llm/openrouter_client.py`

Implementa `LLMClient` con `httpx`. Petición:

```
POST {base_url}/chat/completions
Authorization: Bearer $OPENROUTER_API_KEY
HTTP-Referer: {app_referer}          # opcional, atribución
X-OpenRouter-Title: {app_title}      # opcional, atribución

{
  "model": "anthropic/claude-sonnet-4.5",
  "messages": [{"role": "system", ...}, {"role": "user", ...}],
  "temperature": 0.9,
  "max_tokens": 4000,
  "response_format": {                       # solo si el rol exige JSON
    "type": "json_schema",
    "json_schema": {"name": "story_bible", "strict": true, "schema": {...}}
  },
  "provider": {
    "require_parameters": true,
    "allow_fallbacks": false,
    "data_collection": "deny"
  }
}
```

Notas de implementación:
- El `system` de `LLMClient.complete` se traduce a un mensaje con `role: "system"`, no a un parámetro aparte.
- El esquema JSON se deriva de los modelos Pydantic con `model_json_schema()`. Añade `description` a los campos clave: mejora notablemente la conformidad.
- La clave se lee de `os.environ["OPENROUTER_API_KEY"]` y nunca se registra.
- `seed` se envía solo si el modelo lo admite; **no se asume determinismo** (§24.7).

### 24.4 Capacidades y degradación — `llm/capabilities.py`

`require_parameters: true` evita que la petición acabe en un proveedor que no soporta lo que pides, pero entonces puede no haber ningún endpoint disponible y la respuesta será un 404 del tipo "no endpoints found that support…". Hay que preverlo, no descubrirlo en producción.

El módulo consulta `GET {base_url}/models`, cachea en disco el campo `supported_parameters` por modelo (TTL 24 h) y expone:

```python
def supports(model: str, parameter: str) -> bool | None   # None = desconocido
```

Cadena de degradación para los roles que exigen JSON (Arquitecto, Escaletista, Archivista, Juez, Revisor):

| Nivel | Estrategia | Cuándo |
|---|---|---|
| 1 | `response_format: json_schema` con `strict: true` | El modelo declara soportar `structured_outputs` |
| 2 | `response_format: json_object` + esquema descrito en el prompt | Soporta JSON pero no esquema estricto |
| 3 | Solo prompt + extracción tolerante + reintento con el error de validación | No declara ninguno |

Reglas duras:
- **La validación Pydantic se aplica igual en los tres niveles.** La degradación afecta a cómo se pide el JSON, nunca a cómo se comprueba.
- El nivel usado se registra en `trace.jsonl` por llamada. Si el Archivista cae a nivel 3 de forma sistemática, es señal de que el modelo elegido para ese rol no sirve.
- Los modelos de razonamiento pueden anteponer texto al JSON: el extractor debe localizar el primer objeto JSON balanceado, no asumir que la respuesta empieza por `{`.

### 24.5 Coste

OpenRouter devuelve el uso y el coste en la propia respuesta, sin parámetros adicionales. Consecuencias para `observability/cost.py`:

- **Prohibido codificar tarifas por modelo.** El coste se lee de la respuesta; con proveedor Anthropic directo se calcula con la tabla, y ambos caminos alimentan la misma métrica.
- Se guarda el `id` de generación de cada llamada en `trace.jsonl`; permite auditar después vía `GET {base_url}/generation?id=…`.
- El corte por `limits.max_cost_usd` funciona igual, pero con OpenRouter el coste real por llamada puede variar entre ejecuciones idénticas. `novela cost` debe mostrar coste observado, no estimado.

### 24.6 Consistencia de proveedor: el riesgo narrativo

Este es el punto que no se ve hasta que la novela sale rara. Si dos capítulos consecutivos los atiende un proveedor distinto del mismo modelo, pueden variar la tokenización, el tratamiento de la temperatura y matices de estilo. En una tarea de 24 capítulos con voz sostenida, eso se nota.

Medidas obligatorias:

- Para los roles de prosa (`writer`, `rewriter`, `stylist`): `allow_fallbacks: false` y, si se conoce, `provider_order` fijo. **Mejor fallar y reintentar que escribir el capítulo 12 con otro proveedor.**
- Para los roles estructurados (`archivist`, `judge`): `allow_fallbacks: true` es aceptable; ahí prima la disponibilidad.
- El proveedor efectivo que atendió cada llamada se registra en `trace.jsonl`. Si el informe de repetición o de voz se dispara en un capítulo concreto, lo primero que hay que mirar es si cambió el proveedor.
- Las temperaturas de §7.3 están calibradas para modelos Claude. Al cambiar de familia hay que recalibrarlas: no son portables, aunque el número sea el mismo.

### 24.7 Determinismo

`seed` no está garantizado en OpenRouter: depende del modelo y del proveedor. Consecuencia arquitectónica: **la reproducibilidad de los tests sigue dependiendo exclusivamente del `FakeLLM`**, nunca del proveedor real. Ningún test del §16 puede depender de que dos llamadas idénticas a OpenRouter devuelvan lo mismo.

### 24.8 Errores

| Situación | Tratamiento |
|---|---|
| 401 | `ProviderError`: clave ausente o inválida; indicar la variable `OPENROUTER_API_KEY` |
| 402 | `ProviderError`: créditos insuficientes; el proyecto pasa a `PAUSED` sin perder trabajo |
| 404 "no endpoints found that support…" | `ProviderError` accionable: qué parámetro se pidió, qué modelo, y sugerir bajar de nivel de degradación o cambiar el modelo del rol |
| 429 | Retroceso exponencial (1s, 2s, 4s) y después `PAUSED` |
| 5xx del proveedor de destino | Reintento; si `allow_fallbacks: true`, OpenRouter puede reencaminar y hay que registrarlo |
| Respuesta vacía o truncada | Tratar como fallo de esquema y reintentar dentro de `max_schema_retries` |

### 24.9 Privacidad

`data_collection: deny` evita el enrutado a proveedores que se reservan el derecho a usar los datos para entrenar. Es especialmente relevante aquí porque el contenido enviado es obra creativa del autor. Déjalo activado por defecto y documenta en el README que relajarlo amplía el conjunto de proveedores disponibles y suele abaratar, a cambio de esa cesión.

### 24.10 Verificación

- `make verify` sigue pasando **sin red y sin clave**: T-14 y T-15 usan `httpx.MockTransport`.
- Comprobación manual de humo, una sola vez:
  `OPENROUTER_API_KEY=… novela config set llm.provider openrouter && novela run demo --auto`
- El workflow `nightly-real.yml` admite ambos proveedores mediante una entrada de `workflow_dispatch` y el secreto correspondiente.

---

## 25. Harness de Claude Code

### 25.1 Dos harnesses, no uno

En este proyecto conviven dos sistemas de agentes y **no deben mezclarse**:

| | Harness A — **runtime** | Harness B — **construcción** |
|---|---|---|
| Qué es | El pipeline Python que genera novelas | Claude Code trabajando sobre este repositorio |
| Agentes | Arquitecto, Escaletista, Escritor, Estilista, Archivista, Juez, Revisor (§7) | Subagentes de `.claude/agents/` (§25.4) |
| Memoria larga | SQLite + `bible.json`, `ledger.json`, `summaries.json` (§26.3) | `CLAUDE.md`, `BUILD_SPEC.md`, `DECISIONS.md`, `inventory.yaml` (§26.4) |
| Memoria corta | Capas L0–L7 del contexto de capítulo (§8) | Ventana de la sesión de Claude Code |
| Modelos | Configurables en `novela.yaml` (§3, §24) | Los de la sesión de Claude Code |
| Vive en | `src/novela/` | `.claude/` y raíz |

Confundirlos produce errores caros: meter lógica del pipeline en una skill, o pedirle a un subagente que haga lo que debe hacer un validador determinista. **Regla:** todo lo que deba ejecutarse en producción sin Claude Code presente va en `src/`. `.claude/` solo contiene ayudas para quien desarrolla el repositorio.

### 25.2 `CLAUDE.md` — memoria de proyecto

Fichero en la raíz, cargado automáticamente en cada sesión. Menos de 150 líneas: es contexto que se paga en **todas** las sesiones, así que lo que no sea permanente no va aquí.

Contenido obligatorio:

```markdown
# novela-agent

Harness multiagente que genera novelas de CF. Spec completo en BUILD_SPEC.md.

## Comandos
- `make verify`   — obligatorio antes de cualquier commit
- `make demo`     — pipeline completo offline (3 capítulos de 4 líneas)
- `make inventory`— comprueba los 113 ficheros del inventario

## Reglas permanentes
- Los capítulos se generan SECUENCIALMENTE. Nunca paralelizar.
- Contar líneas o palabras SOLO en `validators/length.py::count_units`.
- Ningún número mágico de capítulos o longitud en el código: todo viene de config.
- Solo el Archivista escribe en el estado del mundo.
- Los tests nunca usan red ni clave de API.
- Nunca commitear `.env`, claves ni `out/`.

## Mapa
- Contratos de datos → BUILD_SPEC.md §5
- Validadores → §9    · Bucle de capítulo → §10
- Configuración → §3  · OpenRouter → §24

@docs/especificaciones_tecnicas.md
```

La última línea usa la sintaxis de importación para traer documentación extensa solo cuando hace falta, sin inflar el fichero base.

**Criterio de mantenimiento:** si tienes que repetirle algo a Claude Code por tercera vez, deja de repetirlo y escríbelo aquí o en una skill. Si es una regla siempre aplicable, `CLAUDE.md`. Si es un procedimiento para una tarea concreta, skill.

### 25.3 Skills — `.claude/skills/`

Las cinco de §13. Tres niveles de carga: el `name` y la `description` se cargan al arrancar (barato), el cuerpo solo cuando la skill se activa, y los ficheros auxiliares solo bajo demanda. Consecuencias de diseño:

- La `description` decide si la skill se activa: debe decir **cuándo** usarla, en tercera persona, no qué es.
- El cuerpo por debajo de ~5.000 tokens. Lo largo (catálogos, tablas de referencia, ejemplos) va en ficheros aparte dentro de la carpeta de la skill.
- `name` en kebab-case.

### 25.4 Subagentes — `.claude/agents/`

Ficheros Markdown con frontmatter YAML; el cuerpo es el prompt de sistema del subagente. Reciben ese prompt y poco más del contexto de la sesión padre, lo que los convierte en la herramienta principal de **aislamiento de contexto**: la exploración ocurre en su ventana, no en la tuya.

Reglas para los seis de este repositorio:
- La `description` empieza por "Use this agent when…" para que el agente principal sepa delegar.
- `tools` mínimo imprescindible. Un auditor que no puede escribir no puede romper lo que audita.
- `model` explícito: es donde está el control de coste.
- Un solo trabajo por subagente y una definición de "hecho" clara, porque el padre solo recibe el resultado.

| Fichero | Propósito | `tools` | `model` |
|---|---|---|---|
| `spec-auditor.md` | Contrastar la implementación contra una sección concreta del BUILD_SPEC y listar desviaciones. Solo lectura | `Read, Grep, Glob` | `sonnet` |
| `fixture-smith.md` | Generar y verificar la coherencia cruzada de las fixtures del `FakeLLM` (§21.6) | `Read, Write, Edit, Bash` | `sonnet` |
| `validator-engineer.md` | Implementar o extender un validador junto con su test, siguiendo §9 y la tabla de códigos de §5 | `Read, Write, Edit, Bash, Grep` | `sonnet` |
| `prompt-smith.md` | Escribir y ajustar plantillas de `prompts/` según §7.1, sin tocar código | `Read, Write, Edit` | `sonnet` |
| `threshold-calibrator.md` | Leer las `metrics` de los `ValidationReport` de `out/` y proponer umbrales para `full.yaml`. Solo lectura y cálculo | `Read, Grep, Glob, Bash` | `haiku` |
| `continuity-detective.md` | Investigar una incidencia `CONT-*` concreta en un manuscrito generado y explicar su causa raíz. Solo lectura | `Read, Grep, Glob` | `sonnet` |

Los dos que más ahorran contexto en la práctica son `spec-auditor` y `continuity-detective`: ambos leen mucho y devuelven poco, que es exactamente el perfil que conviene delegar.

### 25.5 Hooks — `.claude/settings.json`

Los hooks ejecutan lógica determinista alrededor de eventos del ciclo de vida. Lo que no puede quedar al criterio del modelo, va aquí. Se ejecutan con tus permisos: trátalos como código, mantenlos cortos y sin secretos en el cuerpo.

| Evento | Matcher | Script | Qué hace |
|---|---|---|---|
| `PreToolUse` | `Read\|Edit\|Write` | `block-secrets.sh` | Sale con código 2 si la ruta es `.env`, `*.key` o `out/*.db`. El código 2 bloquea la llamada antes de ejecutarse y devuelve el motivo al modelo |
| `PostToolUse` | `Edit\|Write` | `format-python.sh` | `ruff format` y `ruff check --fix` sobre los `.py` modificados |
| `PostToolUse` | `Edit\|Write` | `validate-config.sh` | Si el fichero tocado es `novela.yaml` o `config/**`, ejecuta `novela config validate` |
| `SessionStart` | — | `session-start.sh` | Imprime rama, último commit, estado de `make inventory` y capítulos `stale` pendientes |

El primero es el más importante: hace estructuralmente imposible que una clave acabe leída o escrita por accidente, en lugar de confiar en que el modelo recuerde la regla.

### 25.6 Slash commands — `.claude/commands/`

Procedimientos que repites. Cinco para este repositorio:

| Comando | Qué hace |
|---|---|
| `/verify` | Ejecuta `make verify` y resume solo los fallos, sin volcar la salida entera |
| `/spec-check <sección>` | Lanza `spec-auditor` contra esa sección del BUILD_SPEC |
| `/calibrate <perfil>` | Lanza `threshold-calibrator` sobre los informes de `out/` |
| `/chapter-debug <n>` | Reúne plan, contexto, incidencias y versiones del capítulo n y diagnostica |
| `/fixtures-check` | Lanza `fixture-smith` para verificar coherencia entre fixtures |

### 25.7 Permisos

En `.claude/settings.json`, lista de permitidos explícita para lo repetitivo y seguro (`make *`, `pytest *`, `ruff *`, `git status`, `git diff`) y denegados para lo destructivo (`rm -rf *`, `git push --force *`, cualquier cosa que lea `.env`). Lo personal va en `settings.local.json`, que no se versiona.

### 25.8 Plugins y MCP

**Plugins** (`.claude-plugin/plugin.json`): permiten empaquetar skills, subagentes, comandos y hooks como una unidad instalable. **No forman parte de la v0.1.** Cuando el harness se estabilice y quieras compartirlo entre proyectos o con el equipo, empaquetar `.claude/` como plugin es el paso natural; anótalo como trabajo de v0.2.

**MCP** (`.mcp.json`): opcional. Un servidor de GitHub puede ayudar a gestionar PRs e issues desde la sesión. Requisito duro: **la construcción no puede depender de ningún MCP**. Si `make verify` necesita un servidor MCP levantado, la arquitectura está mal.

---

## 26. Gestión de contexto y memoria

### 26.1 Principio

Ninguna información crítica vive en una ventana de contexto. Las ventanas se compactan, se limpian y se pierden; los ficheros no. Esto aplica igual a los dos harnesses, y es la misma idea que sostiene el diseño del pipeline: **el canon vive fuera del modelo**.

Pregunta de decisión, siempre la misma: *¿esto tiene que sobrevivir a un `/compact`, a un reinicio o a un fallo a mitad del capítulo 14?* Si la respuesta es sí, va a fichero.

### 26.2 Inventario de memoria del runtime — largo plazo

| Artefacto | Contenido | Escribe | Lee | Caducidad |
|---|---|---|---|---|
| `bible.json` | Canon: mundo, personajes, reglas | Arquitecto (vía orquestador) | Constructor de contexto (L1), validadores | Nunca; solo cambia con aprobación explícita |
| `outline.json` | Plan de los N capítulos | Escaletista | Constructor (L6), validador de escaleta | Nunca; regenerable bajo confirmación |
| `ledger.json` | Hechos vigentes, hilos, entidades, cronología | **Solo el Archivista** | Constructor (L2), validador de continuidad | Acumulativo; los hechos se revocan, no se borran |
| `summaries.json` | Resumen por capítulo en 3 niveles | Archivista | Constructor (L3, L4) | Acumulativo |
| `style_artifacts.json` | Frases, metáforas, aperturas ya usadas | Archivista | Constructor (L7), validador de repetición | Acumulativo; es la memoria anti-repetición |
| `chapters/ch_NN.md` | Prosa final | Orquestador | Constructor (L4, cola literal), ensamblador | Versionado |
| `config.snapshot.yaml` | Configuración de creación | CLI | Auditoría | Inmutable |
| `trace.jsonl` | Una línea por llamada LLM | Todos los agentes | `novela cost`, diagnóstico | Append-only |

### 26.3 Inventario de memoria del runtime — corto plazo

Lo que entra en la ventana del Escritor para un capítulo, y qué se sacrifica primero cuando no cabe (§8):

| Capa | Fuente | Se recorta |
|---|---|---|
| L2 estado del mundo, L4 resumen y cola literal, L6 plan, L7 prohibiciones | `ledger.json`, `summaries.json`, capítulo anterior, `style_artifacts.json` | **Nunca** |
| L1 canon filtrado | `bible.json`, filtrado por entidades del plan | 3.º |
| L3 memoria media | `summaries.json` de 1…i-2 | 2.º |
| L5 recuperación | Índice vectorial del manuscrito | 1.º |

La cola literal del capítulo anterior es innegociable: es lo que sostiene la continuidad de tono entre capítulos, y es lo primero que la gente elimina cuando quiere ahorrar tokens.

### 26.4 Inventario de memoria de Claude Code — largo plazo

| Artefacto | Qué guarda | Cuándo se consulta |
|---|---|---|
| `CLAUDE.md` | Reglas permanentes, comandos, mapa del repo | Cada sesión, automáticamente |
| `BUILD_SPEC.md` | La especificación completa | Bajo demanda, por sección |
| `docs/especificaciones_*.md` | Contexto de diseño y requisitos | Importado desde `CLAUDE.md` cuando hace falta |
| `DECISIONS.md` | Decisiones tomadas y su motivo | Al retomar trabajo o cuestionar una decisión |
| `inventory.yaml` | Qué ficheros deben existir | `make inventory`, cada verificación |
| `.claude/skills/*/SKILL.md` | Procedimientos para tareas concretas | Cuando la tarea coincide con la `description` |
| `.claude/agents/*.md` | Prompts de sistema de los subagentes | Al delegar |
| `trace.jsonl` y `out/**/reports/` | Evidencia empírica para calibrar | Al ajustar umbrales |
| Historial de git y CHANGELOG | Qué cambió y por qué | Al investigar una regresión |

### 26.5 Inventario de memoria de Claude Code — corto plazo

| Mecanismo | Uso |
|---|---|
| Ventana de la sesión | Trabajo en curso; volátil por definición |
| Subagentes | Aislar exploraciones costosas: leen mucho, devuelven poco, y el ruido no entra en la ventana principal |
| Hook `SessionStart` | Reinyecta el estado mínimo (rama, commit, inventario, capítulos `stale`) al arrancar |
| `/clear` entre tareas grandes | Empezar limpio cuesta menos que arrastrar contexto irrelevante |

### 26.6 Qué va dónde

| Si la información es… | Va a… |
|---|---|
| Una regla siempre aplicable | `CLAUDE.md` |
| Un procedimiento para una tarea concreta | Una skill |
| Una decisión de diseño y su motivo | `DECISIONS.md` |
| Una restricción que no puede depender del criterio del modelo | Un hook |
| Una exploración costosa que devuelve poco | Un subagente |
| Un dato del mundo narrativo | El ledger, vía Archivista |
| Algo que solo importa en esta conversación | La ventana; que se pierda está bien |

### 26.7 Antipatrones de contexto

- Meter el BUILD_SPEC entero en `CLAUDE.md`: se paga en cada sesión y no se usa entero casi nunca.
- Pedirle al modelo que "recuerde" una regla en lugar de escribirla en fichero o convertirla en hook.
- Usar un subagente para algo que devuelve tanto texto como consumió: no ahorra nada.
- Confiar en la ventana para el estado del mundo narrativo: es exactamente el fallo que este proyecto existe para evitar.
- Skills con `description` que explica qué son en lugar de cuándo usarlas: no se activan nunca.
- Hooks largos o lentos: se ejecutan constantemente y bloquean el flujo.
