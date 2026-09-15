# novela-agent

[![ci](https://github.com/BrunoCrz3/MyStory/actions/workflows/ci.yml/badge.svg)](https://github.com/BrunoCrz3/MyStory/actions/workflows/ci.yml)

Harness multiagente que genera novelas de ciencia ficción coherentes y no
repetitivas: seis agentes LLM y cuatro validadores deterministas producen, a
partir de una premisa y un número de capítulos, un manuscrito en Markdown y PDF.

La idea que lo sostiene: **el canon vive fuera del contexto del modelo**. Los
hechos del mundo narrativo están en SQLite y en artefactos JSON, no en una
ventana que se compacta. Lo que puede comprobarse con código se comprueba con
código; el modelo solo escribe.

La especificación completa está en [`BUILD_SPEC.md`](BUILD_SPEC.md).

## Instalación y demo en tres comandos

En Linux y macOS:

```bash
make install          # crea .venv e instala el paquete con sus extras de desarrollo
make demo             # pipeline completo offline: 3 capítulos de 4 líneas
cat out/demo/manuscrito.md
```

En Windows, con PowerShell y **sin necesidad de instalar GNU make**:

```powershell
./make.ps1 install
./make.ps1 demo
Get-Content out/demo/manuscrito.md
```

`make demo` **no toca la red ni necesita ninguna clave de API**: usa el proveedor
`fake`, que resuelve cada llamada desde `fixtures/llm/`. Tarda menos de dos
segundos.

Para comprobar el proyecto entero:

```bash
make verify           # ./make.ps1 verify en Windows
```

### Los dos caminos son el mismo

`Makefile` y `make.ps1` son envoltorios finos sobre `scripts/tasks.py`, que es
donde vive la definición de cada target. No hay dos listas de pasos que puedan
separarse: hay una, en Python, y dos formas de invocarla.

| | Linux / macOS | Windows |
|---|---|---|
| Invocación | `make <target>` | `./make.ps1 <target>` |
| Sin envoltorio | `python scripts/tasks.py <target>` | idéntico |
| Entorno virtual | `.venv/bin/` | `.venv\Scripts\` |

Los targets son los mismos en ambos: `install`, `demo`, `test`, `lint`,
`typecheck`, `inventory`, `verify` y `clean`. `scripts/tasks.py` resuelve el
directorio de ejecutables del entorno virtual según la plataforma, así que
ninguna ruta `bin/` o `Scripts/` aparece escrita a mano.

Si usas `cmd.exe` en lugar de PowerShell, o prefieres no depender de ningún
envoltorio, llama directamente a `python scripts/tasks.py verify`.

**Nota sobre la versión de Python:** el proyecto exige 3.12 o superior. En
Windows, `./make.ps1 install` usa el lanzador `py -3.12` si está disponible,
porque el `python` del PATH puede ser una versión anterior. Para forzar un
intérprete concreto: `./make.ps1 install -Python C:/ruta/a/python.exe`, o
`make install PY=python3.12` en Linux y macOS.

## Cómo funciona

Cinco fases, estrictamente secuenciales:

| Fase | Agente | Produce |
|---|---|---|
| 1 | Arquitecto | `bible.json` — canon, personajes, reglas del mundo |
| 2 | Escaletista | `outline.json` — plan de los N capítulos |
| 3 | Escritor → validadores → Reescritor / Parcheador → Estilista → Archivista | `chapters/ch_NN.md`, `ledger.json` |
| 4 | Revisor global | informes de continuidad, repetición y ritmo |
| 5 | — | `manuscrito.md` y `manuscrito.pdf` |

Los capítulos se generan **uno detrás de otro**: el capítulo *i* depende del
estado del mundo tras el *i-1*. Solo el Archivista escribe en ese estado, en una
transacción por capítulo.

Entre el Escritor y el Estilista hay un bucle: si los validadores encuentran
algo bloqueante, se reescribe; si encuentran algo mayor, se parchea **y se
vuelve a validar**, porque un parche puede romper otra cosa.

## Parámetros configurables

Todo el comportamiento vive en YAML. **El número de capítulos y el tamaño de
capítulo no son constantes, son configuración.**

| Clave | Qué hace | Por defecto |
|---|---|---|
| `novel.chapters` | Número de capítulos, entre 3 y 60 | `3` |
| `novel.length.unit` | `lines` (pruebas) o `words` (producción) | `lines` |
| `novel.length.target` | Tamaño objetivo por capítulo, en esa unidad | `4` |
| `novel.length.tolerance` | Desviación admitida; `0` = exacto | `0` |
| `profile` | Umbrales de calidad: `micro` o `full` | `micro` |
| `llm.provider` | `fake`, `anthropic` u `openrouter` | `fake` |
| `llm.models.<rol>` | Modelo, temperatura y `max_tokens` por rol | ver `config/default.yaml` |
| `limits.max_cost_usd` | Corte de gasto por proyecto | `5.00` |
| `limits.max_rewrite_attempts` | Reescrituras antes de escalar | `3` |
| `limits.context_token_budget` | Presupuesto de contexto por capítulo | `30000` |
| `approval.{bible,outline,final}` | `auto` o `manual` | `auto` |

El fichero que se toca en el día a día es **`novela.yaml`**, que no se versiona:

```bash
novela config init              # lo crea desde novela.example.yaml, con comentarios
novela config show --resolved   # config efectiva y de dónde sale cada clave
novela config validate          # valida sin ejecutar nada
```

Precedencia, de menor a mayor: `config/default.yaml` → `config/profiles/<perfil>.yaml`
→ `novela.yaml` → `out/<pid>/config.yaml` → variables `NOVELA__*` → flags de CLI.

Una clave mal escrita **falla de forma ruidosa**, con sugerencia:

```
ConfigError: clave desconocida 'novel.chapter' en novela.yaml (¿querías decir 'novel.chapters'?)
```

## De `micro` a `full`

Pasar de una prueba de 3 capítulos de 4 líneas a una novela de 24 capítulos de
2500 palabras es **solo configuración**:

```yaml
# novela.yaml
novel:
  chapters: 24
  length:
    unit: words
    target: 2500
    tolerance: 500
profile: full
```

o, de forma equivalente:

```bash
novela config set novel.chapters 24
novela config set novel.length.unit words
novela config set novel.length.target 2500
novela config set novel.length.tolerance 500
novela config set profile full
```

Ambas vías escriben en el mismo sitio y `novela config set` conserva los
comentarios del YAML. Si para esto hubiera que tocar código, la implementación
sería incorrecta: lo verifica el test T-09.

**Por qué existe el perfil `micro`:** aplicar umbrales de novela larga a
capítulos de 4 líneas produce falsos positivos constantes. Con 12 líneas de
muestra, la varianza del solapamiento de n-gramas supera a la señal, así que
`micro` desactiva esas severidades en lugar de bajarlas. Sigue calculando las
métricas, que es lo que permite calibrar después.

## Uso con un proveedor real

```bash
cp .env.example .env     # y rellena la clave del proveedor que uses
novela config set llm.provider anthropic
novela init "Tu premisa aquí" --project-id mi-novela
novela run mi-novela --auto
novela cost mi-novela
```

Con `openrouter` puedes mezclar familias de modelos por rol: el Escritor pide
calidad de prosa, el Archivista extracción estructurada barata y el Juez criterio
independiente. Que el Juez sea de otra familia que el Escritor reduce además el
sesgo de autoevaluación.

`llm.openrouter.data_collection: deny` evita enrutar a proveedores que se
reservan el derecho a entrenar con lo que les mandas. Relajarlo amplía el
conjunto de proveedores y suele abaratar, a cambio de ceder obra creativa del
autor. Viene activado por defecto.

## Comandos

```
novela init "premisa…" [--chapters N] [--profile micro|full] [--project-id ID]
novela bible   <pid> [--approve] [--regenerate]
novela outline <pid> [--approve] [--regenerate]
novela write   <pid> [--from 1] [--to N]
novela review  <pid>
novela export  <pid> --format md,pdf
novela run     <pid> --auto
novela status  <pid>
novela continuity <pid>
novela cost    <pid>
novela config  init | show [--resolved] | get <clave> | set <clave> <valor> | validate
novela demo
```

## Desarrollo

```bash
make verify      # inventario + lint + tipos + tests + demo
make test        # solo la suite
make lint        # ruff check y ruff format --check
make typecheck   # mypy en modo estricto
make inventory   # comprueba el inventario de entregables de §21
make clean       # borra out/ (salvo .gitkeep) y las cachés
```

En Windows, el mismo target con el envoltorio de PowerShell:

```powershell
./make.ps1 verify
./make.ps1 lint test      # admite varios targets en una sola llamada
```

Los tests **nunca** usan red ni clave de API: el determinismo lo da el `FakeLLM`
con las fixtures de `fixtures/llm/`, que se regeneran con
`python scripts/make_fixtures.py`.

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md) para la convención de commits, cómo
añadir un validador y cómo calibrar umbrales.

## Claude Code

El repositorio trae un harness de desarrollo en `.claude/`: cinco skills, seis
subagentes, cinco slash commands y cuatro hooks, descritos en §25 del spec.
No forma parte del runtime — `make verify` no depende de él — y se mantiene con
la skill pública `skill-creator`. La skill `manuscript-export` se apoya en las
skills públicas `pdf` y, si algún día se añade salida Word, `docx`.

## Limitaciones conocidas

- Los umbrales de `full.yaml` son un punto de partida razonable, **no valores
  medidos**. Ver `DECISIONS.md`.
- Un solo punto de vista por capítulo.
- Español fijo: los validadores usan palabras vacías españolas.
- Sin EPUB ni DOCX, sin API HTTP y sin interfaz web.

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
