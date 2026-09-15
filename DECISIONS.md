# Decisiones

Registro de los valores por defecto aplicados de la §20 del `BUILD_SPEC.md` y de
las desviaciones respecto al spec, con su justificación.

---

## Parte 1 — Puntos abiertos de §20, con el valor por defecto aplicado

### 1. Proveedor y modelos concretos

**Aplicado:** los de `config/default.yaml`, con `provider: fake` activo.
El cliente real existe y está probado, pero ni la construcción ni los tests
dependen de él; `make verify` pasa sin red y sin clave.

### 2. ¿El juez debe ser un modelo distinto al Escritor?

**Aplicado:** sí. `judge` usa `claude-haiku-4-5` frente al `claude-sonnet-4-6`
del Escritor, y se invoca con un `system` propio y sin el prompt del Escritor en
contexto. Reduce el sesgo de autoevaluación a coste bajo. Con OpenRouter la
recomendación es ir más lejos y usar otra familia de modelos.

### 3. Reescritura retroactiva al cambiar el canon

**Aplicado:** congelar lo aprobado. Los hechos se revocan con `status:
"revocado"` y `revoked_by`, nunca se borran; los capítulos afectados se marcan
`stale` y `novela status` los lista; nada se regenera sin confirmación explícita.
Es la decisión que más condiciona el modelo de datos y conviene revisarla antes
de escalar.

### 4. Definición de "línea"

**Aplicado:** frase completa terminada en `\n`. Las líneas en blanco no cuentan y
el título del capítulo tampoco. Contador canónico único:
`validators/length.py::count_units`. Ningún otro módulo cuenta.

### 5. Embeddings

**Aplicado:** TF-IDF local con scikit-learn. Sin red, determinista y suficiente
para `micro`. `context/retrieval.py` define un `Protocol Index` para sustituirlo
por un proveedor de embeddings real o por pgvector sin tocar el constructor de
contexto.

### 6. Multi-POV

**Aplicado:** no en esta versión. Un punto de vista por capítulo, declarado en
`ChapterPlan.pov_character_id` y usado por el filtro de la capa L1. Añadir
multi-POV exigiría un registro de conocimiento por personaje.

### 7. Idioma de salida

**Aplicado:** español fijo. El campo `project.language` existe pero solo se
prueba `es`. Los validadores usan una lista de palabras vacías españolas en
`validators/repetition.py`.

### 8. Persistencia

**Aplicado:** SQLite, tras una clase base abstracta `Store` en `store.py`.
PostgreSQL y pgvector no aportan nada en esta fase y quedan detrás de esa
interfaz.

### 9. Tope de coste

**Aplicado:** 5 USD por proyecto (`limits.max_cost_usd`). Se comprueba **antes**
de cada llamada, nunca después. Con `micro` y `fake` es irrelevante; con `full` y
un proveedor real es la salvaguarda principal.

### 10. Autoría y trazabilidad

**Aplicado:** `ChapterVersion.origin` distingue `generated`, `rewritten`,
`patched`, `polished` y `edited`. Cada versión guarda modelo, temperatura,
semilla y hash de prompt, y el historial completo queda en
`chapters/ch_NN.versions.json`.

---

## Parte 2 — Decisiones tomadas donde el spec deja margen

### D-1. `LLMClient.complete` recibe `role` y `chapter`

**Spec:** §6.1 fija la firma del `Protocol` sin esos dos parámetros. §6.2 exige
que el `FakeLLM` derive la fixture «del rol del agente y del número de capítulo».

**Decisión:** añadir `role`, `chapter` y `json_schema` como parámetros opcionales
con valor por defecto. Sin ellos el `FakeLLM` no puede resolver la fixture, la
traza no puede etiquetar la llamada por rol y OpenRouter no puede forzar el
esquema. Los clientes reales los usan solo como metadatos.

### D-2. El Parcheador tiene etiqueta propia mediante un alias de rol

**Spec:** §7 asigna al Parcheador el modelo del rol `rewriter`, y §3.2 fija
`llm.models` con ocho roles, sin `patcher`.

**Decisión:** `config.ROLE_ALIASES = {"patcher": "rewriter"}`. El Parcheador
resuelve su modelo a través del Reescritor —por lo que `default.yaml` queda
idéntico a §3.2— pero conserva etiqueta propia en `trace.jsonl` y clave propia de
fixture. Sin esto sería imposible distinguir un parche de una reescritura al
diagnosticar un capítulo.

### D-3. Las incidencias mayores tienen tope de parches

**Spec:** §10.2 describe `if report.major: patch; continue` sin límite. Solo fija
tope para las bloqueantes.

**Decisión:** las mayores usan el mismo tope `limits.max_rewrite_attempts`.
Agotado, el capítulo continúa con las incidencias mayores registradas en su
informe, sin escalar. Tal cual está escrito en el spec, una incidencia mayor que
el parche no puede resolver produce un bucle infinito. Escalar tampoco sería
correcto: una incidencia mayor, por definición, no bloquea.

### D-4. `REP-NGRAM` en el perfil `micro`

**Spec:** T-03 pide que dos textos casi idénticos disparen `REP-NGRAM` en `full`
y **no** en `micro`. Pero `micro` define `jaccard_warning: 0.40`, y dos textos
casi idénticos superan ese umbral.

**Decisión:** el umbral de aviso emite una incidencia de severidad `minor` y el
bloqueante una de severidad `blocking`. El test comprueba que en `full` hay una
incidencia **bloqueante** y en `micro` no la hay, y que la métrica se registra en
ambos. Es la única lectura que respeta a la vez el contrato de §9.4 («un umbral
`null` desactiva esa severidad, no la comprobación») y la intención de T-03.

### D-5. `CONT-LOCATION-IMPOSSIBLE` exige intervalos solapados

**Spec:** §9.5 dice «mismo personaje en dos `location_id` en intervalos
solapados sin tránsito narrado».

**Decisión:** la comprobación exige literalmente que los intervalos se solapen.
Una primera implementación que marcaba cualquier cambio de localización entre
capítulos consecutivos daba falsos positivos en el caso más normal del mundo:
que un personaje se mueva de un capítulo al siguiente.

### D-6. `CONT-RULE-VIOLATION` tolera la flexión verbal

**Decisión:** un límite del canon se considera violado cuando el 80 % de sus
palabras significativas concurren en una misma frase, con un mínimo de tres.
Exigir el 100 % no detectaría nada, porque el español flexiona los verbos
(«muestra» / «mostró») y una coincidencia exacta es improbable.

### D-7. `CONT-NAME-DRIFT` exige la misma inicial

**Decisión:** además de la distancia de edición ≤ 2 de §9.5, el candidato debe
tener al menos cuatro caracteres y **la misma inicial** que la entidad canónica.
Sin esa condición, palabras españolas corrientes en mayúscula al principio de
frase («Desde», «Dentro») quedaban a distancia 2-3 de nombres del canon y
producían ruido constante. La deriva real de nombres —«Nadia» / «Nadya»—
conserva siempre la inicial.

### D-8. El juez se invoca desde el orquestador, no desde el validador

**Spec:** §9.5 sitúa la parte del juez LLM dentro del validador de continuidad.

**Decisión:** `continuity.validate` acepta `judge_issues` ya calculadas y las
fusiona; quien llama al Juez es el bucle de capítulo. Mantiene la regla de §2.3
—«los validadores no escriben, los agentes no validan»— y deja el validador
completamente determinista y testeable sin ningún proveedor LLM.

### D-9. El escaneo de marcadores de `check_inventory.py` excluye documentación

**Spec:** §21.1 pide comprobar que ningún fichero del inventario contiene
`TODO`, `FIXME` o `pass  # placeholder`.

**Decisión:** el escaneo se aplica solo a `.py`, `.yaml`, `.yml`, `.json`,
`.toml` y `.sh`. El propio `BUILD_SPEC.md` cita esos marcadores al enunciar la
regla, igual que lo hacen las skills: aplicarlo a la documentación haría el
inventario imposible de satisfacer por construcción.

### D-10. Recuento de módulos de `src/` y grupo `env`

**Spec:** §21.7 titula el grupo «37 módulos» pero la tabla enumera 43 ficheros.
§4 exige además `.env.example`, que no aparece en ningún grupo de §21.

**Decisión:** el inventario declara los 43 ficheros que la tabla enumera —la
lista manda sobre el titular— y añade un grupo `env` con `.env.example`. El total
queda por encima del mínimo de 113 que fija §21.12.

### D-11. La rama de trabajo es la asignada por el entorno

**Spec:** §17.0 y §22.1 nombran la rama `feat/harness-v1`.

**Decisión:** el trabajo va en `claude/funny-darwin-mj79un`, la rama que el
entorno de ejecución asigna a esta sesión y la única a la que tiene permiso de
escritura. El contenido y la convención de commits son los que pide §22.

### D-12. Las especificaciones de origen se mueven a `docs/`

**Decisión:** `especificaciones_funcionales.md`, `especificaciones_tecnicas.md` y
`flujo_agente_novela.drawio` pasan a `docs/`. §25.2 y §26.4 los referencian como
`docs/especificaciones_*.md`, y `CLAUDE.md` los importa con `@docs/…` para
cargarlos bajo demanda en lugar de pagarlos en cada sesión.

### D-13. La versión de Python es 3.12

**Decisión:** `requires-python = ">=3.12"` como pide §2.2. El entorno trae 3.11
por defecto, así que `make install` crea el entorno virtual con el intérprete
3.12 disponible en el sistema. `StrEnum` y la sintaxis de tipos usada lo exigen.

### D-14. La construcción funciona en Windows sin duplicar la lista de targets

**Problema:** el `Makefile` original solo funcionaba en Unix. Daba por hecho
`.venv/bin` (en Windows es `.venv/Scripts`) y usaba `test -f`, `rm -rf`, `find`
y `touch`, que no existen en `cmd.exe` ni en PowerShell. Además, GNU make no
viene instalado en Windows, así que arreglar el `Makefile` no habría bastado.

**Decisión:** la definición de los targets se mueve a `scripts/tasks.py`, un
ejecutor en Python que solo usa la biblioteca estándar. `Makefile` y `make.ps1`
quedan como envoltorios finos que delegan en él.

- `tasks.py::bin_dir` resuelve `Scripts` o `bin` según `os.name`. Ninguna ruta
  del entorno virtual se escribe a mano.
- `test -f` → `require_file`; `rm -rf` y `find … -exec rm` → `remove` y
  `pycache_dirs` sobre `pathlib` y `shutil`; `touch` → `Path.touch`.
- El `Makefile` ya no contiene **ninguna** orden de shell, solo delegaciones.
  Esa es la razón de que deje de importar qué shell use make.
- Un paso fallido lanza `TaskError` y sale con código distinto de cero. Nada se
  captura para continuar en silencio.

**La alternativa descartada** era mantener los pasos en el `Makefile` y escribir
un `make.ps1` paralelo con los mismos comandos. Se rechaza porque duplica la
definición de `verify`: dos listas que divergen en cuanto alguien añade un paso
a una sola, y el fallo se manifiesta como «en mi máquina pasa» meses después.

**Coste asumido:** una indirección más. `make verify` ya no muestra los pasos en
el propio `Makefile`; hay que abrir `tasks.py`. Se compensa con que `tasks.py`
imprime cada comando que ejecuta, precedido de `$`.

**Inventario:** `make.ps1` y `scripts/tasks.py` se añaden a `inventory.yaml`
(meta 11 → 12, scripts 3 → 4, total 120 → 122). §21.12 declara un total
**mínimo**, no una lista cerrada, así que ampliarlo no es una desviación.

**Pendiente:** la CI solo corre en `ubuntu-latest` y llama a las herramientas
directamente, sin pasar por `make`. Ni el `Makefile` ni `make.ps1` están
cubiertos por la CI. Añadir un `make --dry-run verify` en Linux y un job de
Windows con `./make.ps1 verify` cerraría ese hueco.

---

## Lo que conviene decidir antes de escalar a novela completa

1. **Calibración real de umbrales.** Los valores de `full.yaml` son un punto de
   partida, no medidas. Genera dos o tres novelas reales y ajústalos con las
   `metrics` que ya quedan registradas en cada `ValidationReport`. Es el punto
   con más impacto en la calidad percibida.
2. **Política de reescritura retroactiva** (punto 3). Congelar lo aprobado es lo
   conservador; si quieres editar el canon a mitad de obra, el modelo de datos
   necesita versionado de hechos por capítulo, no solo revocación.
3. **Presupuesto y enrutado por rol.** El Archivista y el Juez se invocan tantas
   veces como el Escritor. Bajarlos de gama es donde está el ahorro sin pérdida
   de calidad; subir el Escritor es donde está la mejora.
4. **Consistencia de proveedor con OpenRouter** (§24.6). Para los roles de prosa,
   `allow_fallbacks: false` ya está puesto, pero conviene fijar `provider_order`
   en cuanto sepas qué proveedor te da la voz que quieres: un capítulo atendido
   por otro proveedor se nota en una obra de 24 capítulos.
