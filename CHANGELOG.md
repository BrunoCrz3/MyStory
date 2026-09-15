# Changelog

Todos los cambios reseñables de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- **Soporte de Windows en la construcción.** `scripts/tasks.py`, ejecutor de
  targets multiplataforma que solo usa la biblioteca estándar, y `make.ps1`,
  envoltorio de PowerShell para quien no tiene GNU make. Los targets
  (`install`, `demo`, `test`, `lint`, `typecheck`, `inventory`, `verify`,
  `clean`) son los mismos en Linux, macOS y Windows. Ver `DECISIONS.md`, D-14.

### Cambiado

- El `Makefile` pasa a ser un envoltorio fino sobre `scripts/tasks.py` y ya no
  contiene órdenes de shell. Los nombres de los targets y su comportamiento no
  cambian: `make verify` sigue haciendo exactamente lo mismo en Unix.
- `inventory.yaml`: total mínimo de 120 a 122 ficheros (meta 11 → 12,
  scripts 3 → 4).

### Corregido

- La construcción daba por hecho `.venv/bin` y las órdenes `test -f`, `rm -rf`,
  `find` y `touch`, por lo que `make verify`, `make demo` y `make clean` no
  funcionaban en Windows.

## [0.1.0] — 2026-09-15

Primera construcción del harness, según `BUILD_SPEC.md` v1.0.

### Añadido

- **Configuración** (§3): resolución con precedencia de seis niveles, fusión
  profunda por clave y trazabilidad del origen de cada valor. Modelos Pydantic
  con `extra="forbid"`: una clave mal escrita falla con sugerencia. Perfiles de
  umbral `micro` y `full`. `novela config set` conserva los comentarios del YAML.
- **Contratos de datos** (§5): biblia, escaleta, ledger, versiones de capítulo e
  incidencias, con los 22 códigos de incidencia de la tabla del spec.
- **Capa LLM** (§6, §24): `Protocol` único con tres proveedores — `FakeLLM`
  determinista y offline con fallos programables, cliente Anthropic directo y
  cliente OpenRouter con cadena de degradación
  `json_schema → json_object → prompt`.
- **Agentes** (§7): Arquitecto, Escaletista, Escritor, Reescritor, Parcheador,
  Estilista, Archivista, Juez y Revisor global, con las diez plantillas de
  `prompts/` y el ciclo de reintento con inyección del error de validación.
- **Contexto** (§8): capas L0–L7 con presupuesto y prioridad de recorte
  L5 → L3 → L1; L0, L2, L4, L6 y L7 nunca se recortan.
- **Validadores** (§9): longitud, biblia, escaleta, repetición y continuidad.
  Repetición 100 % determinista, sin LLM. Un umbral `null` desactiva la
  severidad, nunca el cálculo de la métrica.
- **Orquestador** (§10): bucle de capítulo con reescritura, parche y
  revalidación; capítulos estrictamente secuenciales; escritura del estado del
  mundo en una única transacción atómica por capítulo.
- **CLI** (§11): quince comandos con Typer y `rich`, incluido `novela demo`, que
  ejecuta el pipeline completo offline en menos de dos segundos.
- **Exportación** (§12): `manuscrito.md` canónico y PDF vía Pandoc con generador
  de respaldo que nunca rompe el pipeline.
- **Observabilidad** (§14): `trace.jsonl` con hash de prompt y desglose de capas
  —nunca el prompt completo ni la clave— y agregación de coste por rol y
  capítulo.
- **Harness de Claude Code** (§25): `CLAUDE.md`, cinco skills, seis subagentes,
  cinco slash commands y cuatro hooks, entre ellos el bloqueo de secretos.
- **Tests** (§16): los quince criterios T-01…T-15, ninguno con red ni clave de
  API. Cobertura del 91 % global y del 94 % en validadores y orquestador.
- **CI** (§22.4): workflow offline sin secretos, y `nightly-real.yml` manual con
  tope de gasto para la validación con modelo real.

### Limitaciones conocidas

- Los umbrales de `config/profiles/full.yaml` **no están calibrados** con datos
  reales: son un punto de partida razonable.
- Un solo punto de vista por capítulo.
- Español fijo: los validadores usan palabras vacías españolas.
- Sin EPUB, DOCX, API HTTP ni interfaz web.
- Persistencia en SQLite; PostgreSQL y pgvector quedan tras la interfaz `Store`.

Los puntos abiertos pendientes de decidir están en `DECISIONS.md`.

[Sin publicar]: https://github.com/BrunoCrz3/MyStory/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BrunoCrz3/MyStory/releases/tag/v0.1.0
