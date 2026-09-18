# SPEC.md — Sistema generador de novelas cortas de ciencia ficción

Documento ejecutable. Claude Code lee este fichero y construye el proyecto completo en una sola pasada.

- **Repositorio destino:** `C:\Users\student\Documents\MyStory1`
- **Orquestador:** Claude Code en VS Code. No hay claves de API. No hay clientes de modelos.
- **Python:** 3.12, solo biblioteca estándar.
- **Ficheros a crear en la construcción:** 28. Límite duro: 35.

---

## 1. Cómo funciona esto (lenguaje llano) y glosario

### 1.1 Cómo funciona esto

Tú escribes una premisa y dices cuántos capítulos quieres. El sistema convierte eso en una novela corta coherente, capítulo a capítulo, sin repetirse. No hay ningún programa que "genere texto": quien escribe es Claude Code, dentro de VS Code, siguiendo instrucciones que están guardadas en este repositorio como ficheros de texto. Tú lanzas comandos; Claude Code hace el trabajo; el repositorio guarda la memoria.

La idea central es esta: **una novela larga no cabe en la memoria de una conversación, así que no la guardamos ahí**. Todo lo que la novela necesita recordar vive en ficheros dentro de la carpeta `novela/`. Si cierras VS Code, si se corta la conversación, si vuelves mañana: el sistema retoma exactamente donde estaba, porque lee esos ficheros, no su propia memoria.

El proceso tiene cinco fases.

**Fase 1 — El canon.** A partir de tu premisa, un especialista llamado *arquitecto* escribe la "biblia" de la novela: quién es cada personaje, qué quiere y qué teme, cómo funciona el mundo, qué reglas tiene la parte especulativa de ciencia ficción y, sobre todo, cuáles son sus límites y su coste. Ese documento se llama `novela/canon.md`. Tú lo lees y lo apruebas. A partir de ese momento queda congelado: nadie lo cambia sin que tú lo digas.

**Fase 2 — La escaleta.** Otro especialista, el *escaletista*, convierte el canon en un plan de capítulos: qué pasa en cada uno, desde el punto de vista de quién, qué información nueva recibe el lector, qué misterios abre y cuáles cierra. Se guarda en `novela/escaleta.json`. Tú también lo apruebas.

**Fase 3 — La redacción.** Aquí está el trabajo real y se hace **en orden estricto**: capítulo 1, luego 2, luego 3. Para cada capítulo ocurre siempre lo mismo:

1. Se reúne el contexto: el canon, el plan de ese capítulo, los hechos ya establecidos, los misterios abiertos, el resumen de lo anterior y las últimas líneas literales del capítulo previo, más la lista de frases que ya se han usado y están prohibidas.
2. El *escritor* redacta el borrador.
3. Dos programas de Python, que no piensan y por eso no se equivocan, miden el capítulo: uno comprueba la longitud y la repetición (frases recicladas, muletillas, aperturas iguales), otro comprueba la continuidad mecánica (¿aparece un personaje que murió?, ¿el día va hacia atrás?, ¿faltan cosas que el plan exigía?).
4. Un especialista, el *continuista*, lee el capítulo y busca lo que ningún programa puede detectar: contradicciones de sentido, reglas del mundo violadas, personajes que actúan contra su carácter.
5. Las incidencias se clasifican en tres niveles. **Bloqueante:** el capítulo se reescribe entero con la lista de errores delante. **Mayor:** se reescriben solo los párrafos señalados y se vuelve a validar. **Menor:** se anota y se sigue.
6. Si tres reescrituras seguidas no arreglan un bloqueante, el sistema **se para y te avisa**, en vez de seguir acumulando basura.
7. El *estilista* pule la prosa sin tocar ningún hecho ni ningún diálogo importante. Después se vuelve a medir la longitud, porque pulir es donde más silenciosamente se rompe.
8. El *archivista* lee el capítulo terminado y actualiza la memoria: qué hechos quedan establecidos y con qué frase se demuestran, qué misterios se abrieron o cerraron, qué nombres nuevos hay, un resumen, y qué frases e imágenes acaban de gastarse.
9. Se hace un commit a GitHub con ese capítulo.

**Fase 4 — La revisión global.** Cuando están todos los capítulos, el *revisor global* lee el manuscrito entero de una vez y busca lo que solo se ve desde arriba: un hilo que quedó abierto, un ritmo plano, tres capítulos que empiezan igual.

**Fase 5 — La entrega.** Un script junta todos los capítulos en `manuscrito.md`. Ese es el resultado.

Además, todo lo que pasa se anota como una línea por suceso en `novela/events.jsonl`: cuándo empezó cada fase, cuántas incidencias tuvo cada validación, cuántos intentos hizo falta. Es un fichero de texto que puedes abrir, y además la fuente de las métricas que se envían a Langfuse (sección 14).

**Lo único que tú haces** es lanzar cuatro comandos y aprobar dos documentos. Está todo en la tabla de la sección 17.

### 1.2 Glosario

| Término | Qué es, en una frase |
|---|---|
| **Canon** (o biblia) | El documento que fija la verdad de la novela: personajes, mundo, reglas de la ciencia ficción y su coste; una vez aprobado, nadie lo contradice. |
| **Escaleta** | El plan de todos los capítulos antes de escribir ninguno: qué ocurre en cada uno y para qué sirve. |
| **Beat** | La unidad mínima de acción dentro de una escena: un cambio concreto que tiene que ocurrir sí o sí en ese capítulo. |
| **Hilo** | Una pregunta o tensión que el texto abre y que el lector espera ver cerrada; cada hilo tiene capítulo de apertura y capítulo de cierre. |
| **Hecho establecido** | Algo que el texto ya ha afirmado y que por tanto ya no se puede contradecir; se guarda con la cita literal que lo demuestra. |
| **POV** | El personaje desde cuya mirada se cuenta el capítulo. |
| **Incidencia bloqueante** | Un error que hace el capítulo inservible (contradice el canon o los hechos); obliga a reescribir el capítulo entero. |
| **Incidencia mayor** | Un error real pero localizado; se arregla reescribiendo solo los párrafos afectados y se vuelve a validar. |
| **Incidencia menor** | Una imperfección que se anota pero no detiene nada. |
| **Parche quirúrgico** | La reescritura de párrafos concretos, no del capítulo entero, seguida obligatoriamente de una nueva validación. |
| **Subagente** | Un especialista de Claude Code con su propio contexto e instrucciones, definido en un fichero `.claude/agents/*.md`. |
| **Skill** | Un procedimiento escrito que Claude Code sigue cuando se da cierta situación, en `.claude/skills/*/SKILL.md`. |
| **Slash command** | Un comando que lanzas tú escribiendo `/nombre` en Claude Code. |
| **Tirada** | Una ejecución completa del sistema, de la premisa al manuscrito; tiene un identificador propio en el registro de eventos. |
| **Estado persistido** | Los ficheros de `novela/` que sobreviven a cualquier reinicio; la memoria real del sistema. |

---

## 2. Cómo usar el documento

### 2.1 Requisitos previos

1. VS Code con la extensión de Claude Code.
2. Python 3.12 accesible como `python` en PATH. Comprobación: `python --version`.
3. Git instalado y el repositorio de GitHub creado.

Si la carpeta todavía no es un repositorio Git (es el caso ahora mismo), ejecuta antes que nada en PowerShell:

```powershell
cd C:\Users\student\Documents\MyStory1
git init
git branch -M main
git remote add origin <https://github.com/BrunoCrz3/MyStory1>
```

### 2.2 Prompt literal de arranque

Abre Claude Code en `C:\Users\student\Documents\MyStory1` y pega esto tal cual:

```
Lee SPEC.md completo antes de escribir nada.

Construye el proyecto exactamente como lo describe: crea los 27 ficheros del
inventario de la seccion 16, con el contenido literal que el SPEC indica donde
lo indica. No inventes ficheros adicionales. No crees ningun fichero que el
inventario de la seccion 16 no liste. No instales dependencias. No uses pip.
No crees entorno virtual. No escribas codigo Python que llame a ningun modelo
de lenguaje ni que lea ninguna variable de entorno con una clave.

Respeta estas reglas de construccion:
- Python 3.12, solo biblioteca estandar.
- Todos los comandos documentados deben funcionar en PowerShell en Windows.
- Ningun script asume que la unidad de longitud es "palabras": se lee de config.json.
- No crees .mcp.json.

Cuando termines:
1. Ejecuta: python scripts/verificar.py
2. Pegame su salida.
3. Haz un unico commit inicial con mensaje "chore: andamiaje del generador de novelas".
4. Dime, en no mas de 15 lineas, que comando debo lanzar yo para empezar la novela.

No me hagas preguntas durante la construccion. Donde el SPEC deje algo abierto,
elige la opcion mas simple y anotala al final en un resumen.
```

### 2.3 Después de construir

Trabajo normal: sección 13 (flujo completo) y sección 17 (qué ejecutas tú y cuándo).

---

## 3. Principios de diseño y decisiones cerradas

### 3.1 Los cinco principios

1. **Markdown antes que código.** Si una pieza puede ser un fichero de texto que Claude Code lee, no se escribe como programa.
2. **JSON antes que base de datos.** El estado del mundo cabe en dos ficheros JSON. No hay SQLite, ni ORM, ni esquema versionado.
3. **Si puede no existir, no existe.** Cada fichero del inventario tiene que justificar su presencia respondiendo "qué pasaría si no estuviera" (secciones 7 y 8).
4. **Python solo para lo determinista.** Contar, medir, comparar cadenas, ensamblar. Todo lo que requiere criterio lo hace un subagente.
5. **La memoria vive en disco, nunca en la conversación.** Ninguna decisión del sistema puede depender de que Claude Code "recuerde" algo de hace veinte mensajes.

### 3.2 Decisiones cerradas (no se discuten en la construcción)

| Decisión | Qué se hace | Por qué |
|---|---|---|
| Sin claves de API | Ningún script lee `ANTHROPIC_API_KEY` ni equivalente | El modelo es Claude Code, no un servicio externo |
| Orquestación | Claude Code, guiado por `CLAUDE.md`, skills y comandos | Es el único "motor" disponible |
| Agentes del diagrama | Subagentes `.claude/agents/*.md` | Aíslan contexto y evitan contaminación entre tareas |
| Reescritor y parcheador | **No son agentes propios:** son modos del subagente `escritor` | Mismo oficio, distinta entrada; dos ficheros menos |
| Validador de repetición | **Script Python, sin agente** | Es 100 % determinista: n-gramas y recuentos |
| Validador de continuidad | **Script + subagente** | La mitad mecánica la hace el script; el juicio, el agente |
| Constructor de contexto | **Skill, no script** | Es un procedimiento de lectura de ficheros, no una transformación |
| Ensamblador | Script Python | Concatenar ficheros no necesita criterio |
| Estado | `novela/estado.json` (uno solo) + `novela/canon.md` + `novela/escaleta.json` | Tres ficheros de memoria, no quince |
| Longitud | Unidad configurable (`lineas` o `palabras`) | El requisito lo exige explícitamente |
| Base de datos, colas, Docker, FastAPI, embeddings, modelos de coste, proveedor falso | No existen | Restricción dura del proyecto |
| MCP | No se crea `.mcp.json` ahora | v1 no lo usa; sección 14.5 dice dónde encajará |
| PDF | No se genera | Opcional y no debe complicar nada; `manuscrito.md` es la entrega |
| Tests | No hay suite de tests; hay `scripts/verificar.py` | Un sistema de 27 ficheros se verifica ejecutándolo |

### 3.3 Reparto de responsabilidades: el diagrama, elemento a elemento

| Elemento del diagrama | Implementación | Justificación |
|---|---|---|
| ENTRADA: premisa + N capítulos | `config.json` | Un único punto editable |
| AGENTE ARQUITECTO | Subagente `arquitecto` | Trabajo creativo de fondo; conviene aislarlo |
| VALIDADOR DE BIBLIA | Autocomprobación dentro del propio subagente `arquitecto` + aprobación tuya | Un agente extra para revisar un documento que tú vas a leer igualmente no se paga |
| AGENTE ESCALETISTA | Subagente `escaletista` | Trabajo estructural, contexto propio |
| VALIDADOR DE ESCALETA | `scripts/continuidad.py --escaleta` + aprobación tuya | La coherencia estructural (hilos que se cierran sin abrirse, días que retroceden) es verificable mecánicamente |
| CONSTRUCTOR DE CONTEXTO | Skill `escribir-capitulo`, paso 1 | Es leer ficheros en un orden fijo |
| AGENTE ESCRITOR | Subagente `escritor` | El trabajo creativo por excelencia |
| VALIDADOR DE REPETICIÓN | `scripts/repeticion.py` | Determinista |
| VALIDADOR DE CONTINUIDAD | `scripts/continuidad.py` + subagente `continuista` | Mitad mecánica, mitad juicio |
| REESCRITURA DIRIGIDA | Subagente `escritor`, modo `reescritura` | Misma habilidad, entrada distinta |
| PARCHE QUIRÚRGICO | Subagente `escritor`, modo `parche` | Ídem |
| PAUSA: escalar al autor | Skill `escribir-capitulo`, paso 7 | Es una regla de decisión, no un programa |
| AGENTE ESTILISTA | Subagente `estilista` | Juicio de prosa; debe ir aislado para no reescribir hechos |
| AGENTE ARCHIVISTA | Subagente `archivista` | Extracción con criterio; es el único que escribe estado |
| AGENTE REVISOR GLOBAL | Subagente `revisor-global` | Lectura completa; contexto propio obligatorio |
| ENSAMBLADOR | `scripts/ensamblar.py` | Determinista |
| ESTADO PERSISTIDO | `novela/estado.json`, `novela/canon.md`, `novela/escaleta.json` | Ficheros, no memoria |
| (nuevo) Registro de sucesos | `scripts/eventos.py` → `novela/events.jsonl` | Fuente de verdad local y origen de las trazas de Langfuse |
| (nuevo) Observabilidad | `scripts/observabilidad.py`, `scripts/retroalimentar.py` | Exportación a Langfuse. Único punto del sistema que habla por red |

---

## 4. Configuración

### 4.1 El fichero

Existe **un solo** fichero de configuración: `config.json` en la raíz. Crea este contenido literal:

```json
{
  "proyecto": "MyStory1",
  "idioma": "es",
  "premisa": "ESCRIBE AQUI TU PREMISA EN UNA O DOS FRASES",
  "capitulos": 3,
  "longitud": {
    "unidad": "lineas",
    "objetivo": 4,
    "tolerancia": 0.0
  },
  "validacion": {
    "max_reescrituras": 3,
    "ngrama": 6,
    "max_solape_ngramas": 0.02,
    "max_aperturas_del_mismo_tipo": 1,
    "max_muletilla_por_mil": 3.0
  },
  "git": {
    "commit_por_capitulo": true,
    "push_automatico": false,
    "rama": "main"
  },
  "eventos": {
    "activo": true,
    "fichero": "novela/events.jsonl"
  }
}
```

### 4.2 Qué significa cada clave

| Clave | Significado | Valor de partida |
|---|---|---|
| `proyecto` | Nombre, se usa en el manuscrito y en los commits | `MyStory1` |
| `idioma` | Idioma de la novela | `es` |
| `premisa` | Tu premisa. **Es lo primero que tienes que editar.** | Marcador |
| `capitulos` | N de capítulos. Determina la escaleta y el bucle | `3` |
| `longitud.unidad` | `"lineas"` o `"palabras"`. **Ningún script asume palabras** | `lineas` |
| `longitud.objetivo` | Tamaño de cada capítulo en esa unidad | `4` |
| `longitud.tolerancia` | Fracción de desvío admitida. `0.0` = exacto | `0.0` |
| `validacion.max_reescrituras` | Intentos antes de parar y avisarte | `3` |
| `validacion.ngrama` | Tamaño de la secuencia de palabras que se compara para detectar reciclaje | `6` |
| `validacion.max_solape_ngramas` | Fracción máxima de n-gramas del capítulo que pueden aparecer en capítulos anteriores | `0.02` |
| `validacion.max_aperturas_del_mismo_tipo` | Cuántos capítulos pueden empezar con el mismo recurso | `1` |
| `validacion.max_muletilla_por_mil` | Frecuencia máxima por mil palabras de una palabra de contenido repetida | `3.0` |
| `git.commit_por_capitulo` | Commit automático al cerrar cada capítulo | `true` |
| `git.push_automatico` | Si `false`, el push lo lanzas tú | `false` |
| `git.rama` | Rama de trabajo | `main` |
| `eventos.activo` | Si `false`, no se escribe `events.jsonl` | `true` |
| `eventos.fichero` | Ruta del registro | `novela/events.jsonl` |

### 4.3 Cómo cambiarlo

Para una novela de 20 capítulos de 1.500 palabras, edita **solo** `config.json`:

```json
  "capitulos": 20,
  "longitud": { "unidad": "palabras", "objetivo": 1500, "tolerancia": 0.15 }
```

No se toca ningún script. `scripts/medir.py` lee `unidad` y cuenta de una forma u otra.

**Definición exacta de "línea":** cuando `unidad` es `lineas`, una línea es una línea no vacía del cuerpo del capítulo (se excluyen las que empiezan por `#`) que termina en `.`, `?`, `!`, `…`, `"`, `»` o `)`. Una línea que no cierre frase cuenta como incidencia de formato, no como línea válida.

### 4.4 Qué pasa si lo cambias a mitad de novela

| Cambio | Efecto | Qué debes hacer |
|---|---|---|
| `premisa` | El canon ya escrito deja de corresponder | Empezar de nuevo: borra `novela/canon.md`, `novela/escaleta.json` y reinicia `novela/estado.json` |
| `capitulos` **hacia arriba** | La escaleta se queda corta | Relanzar `/nueva-novela solo-escaleta`; los capítulos ya escritos se conservan |
| `capitulos` **hacia abajo** | Sobran capítulos escritos | El sistema no borra nada: te avisa y decides tú |
| `longitud.objetivo` o `unidad` | Los capítulos ya escritos no cumplen la nueva medida | Solo afecta a los capítulos siguientes. `python scripts/medir.py --todos` te dice cuáles quedan fuera de norma |
| `validacion.*` | Solo afecta a validaciones futuras | Nada |
| `git.*`, `eventos.*` | Efecto inmediato | Nada |

**Regla dura:** ningún script reescribe `config.json`. Lo editas tú, a mano.

---

## 5. Estructura completa del repositorio

```
MyStory1/
├── SPEC.md                              (1)  este documento
├── README.md                            (2)  qué es esto y los 4 comandos
├── CLAUDE.md                            (3)  reglas permanentes para Claude Code
├── config.json                          (4)  la única configuración
├── .gitignore                           (5)
│
├── .claude/
│   ├── agents/
│   │   ├── arquitecto.md                (6)
│   │   ├── escaletista.md               (7)
│   │   ├── escritor.md                  (8)
│   │   ├── continuista.md               (9)
│   │   ├── estilista.md                 (10)
│   │   ├── archivista.md                (11)
│   │   └── revisor-global.md            (12)
│   ├── skills/
│   │   ├── escribir-capitulo/SKILL.md   (13)
│   │   ├── validar-capitulo/SKILL.md    (14)
│   │   └── bitacora/SKILL.md            (15)
│   └── commands/
│       ├── nueva-novela.md              (16)
│       ├── escribir.md                  (17)
│       ├── estado.md                    (18)
│       └── entregar.md                  (19)
│
├── scripts/
│   ├── nucleo.py                        (20)  config, rutas, lectura/escritura de estado
│   ├── eventos.py                       (21)  ÚNICA función que escribe events.jsonl
│   ├── medir.py                         (22)  longitud
│   ├── repeticion.py                    (23)  n-gramas, muletillas, aperturas
│   ├── continuidad.py                   (24)  comprobaciones mecánicas de coherencia
│   ├── informes.py                      (25)  ÚNICA función que escribe novela/informes/
│   ├── ensamblar.py                     (26)  manuscrito.md
│   └── verificar.py                     (27)  autocomprobación de la instalación
│
└── novela/
    ├── estado.json                      (28)  semilla vacía, creada en la construcción
    ├── canon.md                              generado en fase 1
    ├── escaleta.json                         generado en fase 2
    ├── events.jsonl                          generado al ejecutar
    ├── capitulos/
    │   └── capitulo-01.md ...                generados en fase 3
    └── informes/
        ├── capitulo_NN.json ...              generados en cada validación
        └── global.json                       generado en fase 4

manuscrito.md                                 generado en fase 5
```

**28 ficheros creados en la construcción.** El resto los genera el sistema al trabajar.

No hay: `.mcp.json`, `requirements.txt`, `pyproject.toml`, `Makefile`, `tests/`, `src/`, `.venv/`, `Dockerfile`.

### 5.1 Contenido literal de `.gitignore`

```
__pycache__/
*.pyc
.venv/
.DS_Store
Thumbs.db
```

`novela/` **no** se ignora: el estado es parte del trabajo y debe viajar en los commits.

### 5.2 Contenido literal de `CLAUDE.md`

````markdown
# Reglas permanentes de este repositorio

Este repositorio genera novelas cortas de ciencia ficción. Tú, Claude Code,
eres el orquestador. No hay ningún servicio de modelo externo.

## Invariantes

1. La memoria del proyecto vive en `novela/`, nunca en la conversación.
   Antes de escribir cualquier capítulo, lee `novela/estado.json`,
   `novela/canon.md` y `novela/escaleta.json`. No te fíes de lo que creas recordar.
2. Los capítulos se escriben en orden. Nunca empieces el capítulo i+1 si el i
   no está cerrado y archivado.
3. Solo el subagente `archivista` escribe en `novela/estado.json`. Ningún otro
   agente y ningún otro proceso lo modifica.
4. `novela/canon.md` está congelado desde que el autor lo aprueba. Si un
   capítulo lo contradice, se corrige el capítulo, nunca el canon.
5. Toda validación se ejecuta con los scripts de `scripts/`. No estimes
   longitudes ni repeticiones "a ojo": ejecuta el script y lee su salida.
6. Después del estilista se vuelve a medir la longitud. Siempre.
7. Tras 3 reescrituras fallidas del mismo capítulo, para y avisa al autor.
8. Todo suceso relevante se registra con `python scripts/eventos.py`.
   Ver la skill `bitacora`.

## Prohibiciones

- No instales dependencias. Solo biblioteca estándar de Python 3.12.
- No crees ficheros nuevos fuera del inventario de SPEC.md sección 16 sin
  que el autor lo pida.
- No escribas código Python que llame a un modelo de lenguaje.
- No leas variables de entorno con claves de API.
- No uses `make`, `rm -rf`, `test -f`, ni rutas tipo `.venv/bin`. Windows + PowerShell.
- No reescribas `config.json`.

## Cómo invocar a los especialistas

Usa el subagente adecuado en lugar de hacer tú el trabajo creativo:
`arquitecto`, `escaletista`, `escritor`, `continuista`, `estilista`,
`archivista`, `revisor-global`. Están en `.claude/agents/`.
````

### 5.3 Contenido literal de `README.md`

````markdown
# MyStory1 — generador de novelas cortas de ciencia ficción

Sistema de escritura asistida que funciona dentro de Claude Code en VS Code.
Sin claves de API, sin dependencias, sin base de datos.

## Los cuatro comandos

| Comando | Cuándo |
|---|---|
| `/nueva-novela` | Una vez, al empezar. Crea el canon y la escaleta. |
| `/escribir` | Escribe el siguiente capítulo pendiente. Repítelo hasta acabar. |
| `/estado` | En cualquier momento. Dice por dónde va la novela. |
| `/entregar` | Al final. Revisión global y `manuscrito.md`. |

## Antes de empezar

Edita `config.json`: pon tu premisa y el número de capítulos.

## Cómo está hecho

Lee `SPEC.md`, sección 1: "Cómo funciona esto".
````

---

## 6. Formato de los ficheros de estado

Tres ficheros guardan la memoria. Todos en UTF-8. Los JSON se escriben con
`indent=2` y `ensure_ascii=False`.

### 6.1 `novela/canon.md` — el canon

Markdown con encabezados **fijos**. `scripts/continuidad.py` lee dos de ellos
(`## Personajes` y `## Términos prohibidos`), así que esos títulos no se cambian.

Ejemplo real:

````markdown
# Canon — La deriva de Kalpa

## Logline
Una ingeniera de balizas descubre que el silencio de la red no es una avería
sino un mensaje, y que responderlo cuesta exactamente una vida.

## Tema
Qué estamos dispuestos a gastar para dejar de estar solos.

## Personajes
- **Irene Sabal** — ingeniera de mantenimiento, 41 años. Alias: Sabal.
  Deseo: volver a oír la red. Miedo: haber sido ella quien la apagó.
  Arco: de la negación a la confesión.
- **Tomás Rey** — supervisor orbital, 58 años. Alias: el Supervisor.
  Deseo: cerrar la estación sin escándalo. Miedo: la auditoría.
  Arco: de cómplice a testigo.
- **Nadia Ferrán** — operadora júnior, 24 años. Alias: Nadia.
  Deseo: que la asciendan. Miedo: no estar a la altura.
  Arco: de obediente a insubordinada.

## Escenario
Estación de relé Kalpa-9, órbita alta de un gigante gaseoso. 14 tripulantes.
Ciclo día/noche artificial de 26 horas.

## Premisa especulativa
Las balizas de la red transmiten por acoplamiento cuántico entre pares de
partículas criadas juntas.
- **Reglas:** una baliza solo puede hablar con su gemela; el enlace es instantáneo.
- **Límites:** cada par soporta 10.000 transmisiones antes de degradarse.
- **Coste:** abrir un par nuevo exige el campo bioeléctrico de un cerebro humano
  vivo durante 40 minutos, que queda irreversiblemente dañado.

## Cronología previa
- Año -12: se instala Kalpa-9.
- Año -3: primera degradación masiva de pares.
- Día -40: se apaga la baliza 7. Nadie declara haberlo hecho.

## Glosario
- **Par**: dos partículas acopladas que forman un canal.
- **Silencio**: estado de una baliza que no responde.
- **Sangrado**: degradación progresiva de un par.

## Términos prohibidos
- hiperespacio
- warp
- telepatía
- inteligencia artificial consciente

## Motivos recurrentes
- El zumbido de los ventiladores como sustituto de la voz humana.
- Manos con quemaduras de frío.
````

### 6.2 `novela/escaleta.json` — el plan

```json
{
  "generada": "2026-09-17T12:04:11Z",
  "capitulos_totales": 3,
  "capitulos": [
    {
      "n": 1,
      "titulo": "Silencio en la siete",
      "pov": "Irene Sabal",
      "dia": 1,
      "analepsis": false,
      "funcion": "Detonante: el problema deja de ser técnico",
      "momento": "Turno de noche, sala de relé",
      "beats": [
        {
          "id": "B1.1",
          "texto": "Irene detecta que la baliza 7 no está averiada sino apagada a propósito",
          "marcadores": ["baliza", "siete"]
        },
        {
          "id": "B1.2",
          "texto": "Tomás le ordena cerrar el parte como avería",
          "marcadores": ["parte", "Tomás"]
        }
      ],
      "informacion_nueva": ["El silencio de la baliza 7 tiene una pauta regular"],
      "abre_hilos": ["T01"],
      "cierra_hilos": [],
      "cambio_mundo": "El fallo pasa de accidente a decisión de alguien",
      "gancho": "La pauta se repite con la cadencia de un pulso humano",
      "tamano_objetivo": 4
    },
    {
      "n": 2,
      "titulo": "El coste declarado",
      "pov": "Irene Sabal",
      "dia": 2,
      "analepsis": false,
      "funcion": "Escalada: el precio se hace explícito",
      "momento": "Archivo técnico",
      "beats": [
        {
          "id": "B2.1",
          "texto": "Irene encuentra el registro del coste de abrir un par",
          "marcadores": ["registro", "par"]
        },
        {
          "id": "B2.2",
          "texto": "Nadia se ofrece voluntaria",
          "marcadores": ["Nadia", "voluntaria"]
        }
      ],
      "informacion_nueva": ["Abrir un par cuesta un cerebro humano"],
      "abre_hilos": ["T02"],
      "cierra_hilos": [],
      "cambio_mundo": "La solución técnica se vuelve dilema moral",
      "gancho": "Irene descubre su propia firma en el parte de hace 40 días",
      "tamano_objetivo": 4
    },
    {
      "n": 3,
      "titulo": "Responder",
      "pov": "Irene Sabal",
      "dia": 3,
      "analepsis": false,
      "funcion": "Clímax y resolución",
      "momento": "Sala de pares",
      "beats": [
        {
          "id": "B3.1",
          "texto": "Irene se sienta ella en el asiento en lugar de Nadia",
          "marcadores": ["asiento", "Nadia"]
        },
        {
          "id": "B3.2",
          "texto": "La red responde y confirma que el silencio era un mensaje",
          "marcadores": ["responde", "mensaje"]
        }
      ],
      "informacion_nueva": ["El mensaje decía el nombre de Irene"],
      "abre_hilos": [],
      "cierra_hilos": ["T01", "T02"],
      "cambio_mundo": "La estación deja de estar sola y pierde a su ingeniera",
      "gancho": "Cierre",
      "tamano_objetivo": 4
    }
  ],
  "hilos": [
    { "id": "T01", "titulo": "Quién apagó la baliza 7", "abre_en": 1, "cierra_en": 3 },
    { "id": "T02", "titulo": "Quién pagará el coste del par nuevo", "abre_en": 2, "cierra_en": 3 }
  ]
}
```

### 6.3 `novela/estado.json` — la memoria del mundo

Solo lo escribe el subagente `archivista`. Semilla que se crea en la construcción:

```json
{
  "tirada": null,
  "capitulos_escritos": 0,
  "hechos": [],
  "hilos": [],
  "entidades": [],
  "resumenes": [],
  "frases_usadas": [],
  "aperturas": [],
  "cierres": []
}
```

Ejemplo real tras el capítulo 1:

```json
{
  "tirada": "20260917-1204",
  "capitulos_escritos": 1,
  "hechos": [
    {
      "id": "H001",
      "capitulo": 1,
      "clave": "estado:Irene Sabal",
      "valor": "viva",
      "tipo": "estado_personaje",
      "cita": "Irene apoyó las dos manos en la consola y esperó."
    },
    {
      "id": "H002",
      "capitulo": 1,
      "clave": "baliza-7:causa",
      "valor": "apagada de forma deliberada el día -40",
      "tipo": "mundo",
      "cita": "El corte era limpio: alguien había bajado el interruptor."
    }
  ],
  "hilos": [
    { "id": "T01", "titulo": "Quién apagó la baliza 7", "abierto_en": 1, "cerrado_en": null, "estado": "abierto" }
  ],
  "entidades": [
    { "nombre": "Irene Sabal", "tipo": "personaje", "alias": ["Sabal"], "primera_aparicion": 1 },
    { "nombre": "Tomás Rey", "tipo": "personaje", "alias": ["el Supervisor"], "primera_aparicion": 1 },
    { "nombre": "Kalpa-9", "tipo": "lugar", "alias": [], "primera_aparicion": 1 },
    { "nombre": "baliza 7", "tipo": "objeto", "alias": ["la siete"], "primera_aparicion": 1 }
  ],
  "resumenes": [
    {
      "capitulo": 1,
      "dia": 1,
      "resumen": "Irene descubre en el turno de noche que la baliza 7 no falló: la apagaron. Tomás le ordena archivarlo como avería.",
      "ultimas_lineas": "El silencio volvió a llegar, puntual, con la cadencia exacta de un pulso."
    }
  ],
  "frases_usadas": [
    "con la cadencia exacta de un pulso",
    "el zumbido de los ventiladores"
  ],
  "aperturas": [
    { "capitulo": 1, "tipo": "descripcion_ambiente", "primeras_palabras": "La sala de relé olía a plástico frío" }
  ],
  "cierres": [
    { "capitulo": 1, "tipo": "gancho_revelacion", "ultimas_palabras": "con la cadencia exacta de un pulso" }
  ]
}
```

**Tipos permitidos en `hechos.tipo`:** `estado_personaje`, `mundo`, `objeto`,
`relacion`, `cronologia`. Un hecho de tipo `estado_personaje` cuyo `valor`
contenga `muerto`, `muerta`, `ausente` o `desaparecid` activa la comprobación
mecánica de la sección 11.3.

**Tipos permitidos en `aperturas.tipo` y `cierres.tipo`:** `dialogo`,
`descripcion_ambiente`, `accion`, `reflexion_interior`, `documento_citado`,
`gancho_revelacion`, `gancho_amenaza`.

### 6.4 `novela/capitulos/capitulo-NN.md` — un capítulo

Formato fijo. La primera línea es el título y **no cuenta** para la longitud.

````markdown
# Capítulo 01 — Silencio en la siete

La sala de relé olía a plástico frío y a gente que se había ido hacía horas.
Irene apoyó las dos manos en la consola y esperó a que la baliza siete dijera algo.
El corte era limpio: alguien había bajado el interruptor y había firmado el parte como avería.
El silencio volvió a llegar, puntual, con la cadencia exacta de un pulso.
````

### 6.5 `novela/events.jsonl` — el registro

Una línea JSON por suceso. Esquema completo en la sección 14.

### 6.6 `novela/informes/` — los informes de validación

Cada validación deja constancia en disco. `novela/events.jsonl` guarda **que**
una validación ocurrió y su recuento; `novela/informes/` guarda **qué** dijo,
entera: todas las métricas y todas las incidencias.

**Regla dura:** `scripts/informes.py` es la **única** puerta de escritura de
esta carpeta, por el mismo motivo por el que solo `eventos.py` escribe
`events.jsonl`. Ningún agente escribe aquí.

**Las métricas se guardan siempre**, dispare o no una incidencia. Un informe
sin incidencias sigue siendo un informe: la serie de métricas limpias es lo que
permite calibrar los umbrales (sección 19.2, punto 2).

#### 6.6.1 `novela/informes/capitulo_NN.json`

Uno por capítulo, sobrescrito en cada validación. Refleja la última.

```json
{
  "esquema": 1,
  "tipo": "capitulo",
  "capitulo": 2,
  "generado": "2026-09-18T15:46:02.114Z",
  "tirada": "20260918-0056",
  "intento": 3,
  "metricas": {
    "longitud": { "capitulo": 2, "unidad": "lineas", "objetivo": 4,
                  "medido": 4, "minimo": 4, "maximo": 4,
                  "lineas_sin_cierre": 0, "en_norma": true },
    "repeticion": { "ngramas_total": 214, "ngramas_repetidos": 0,
                    "solape": 0.0, "umbral_solape": 0.02,
                    "frases_recicladas": 0,
                    "muletilla_max": { "palabra": "renglon", "por_mil": 11.9 },
                    "tipo_apertura": "accion" },
    "continuidad": { "comprobaciones": [ { "id": "beats_cubiertos", "ok": true } ] }
  },
  "incidencias": [
    { "origen": "repeticion", "severidad": "menor", "tipo": "muletilla",
      "detalle": "'renglon' aparece 3 veces (11.9 por mil, umbral 3.0)" }
  ],
  "resumen": { "bloqueante": 0, "mayor": 0, "menor": 9 },
  "por_origen": { "medir": 0, "repeticion": 9, "continuidad": 0, "continuista": 0 },
  "continuista_incluido": true
}
```

| Campo | Qué es |
|---|---|
| `esquema` | Versión del formato. Vale `1` |
| `tipo` | `capitulo` |
| `capitulo`, `intento` | Cuál y de qué intento; `intento` puede ser `null` |
| `generado`, `tirada` | ISO-8601 UTC con `Z`, y la tirada vigente |
| `metricas.longitud` | Salida de `medir.py` sin `script` ni `incidencias` |
| `metricas.repeticion` | El bloque `metricas` de `repeticion.py`, íntegro |
| `metricas.continuidad` | Las 7 comprobaciones de `continuidad.py --capitulo`, con su `ok` |
| `incidencias` | Lista única y fusionada. **Cada una lleva `origen`** |
| `origen` | `medir`, `repeticion`, `continuidad` o `continuista` |
| `resumen` | Recuento por severidad de la lista fusionada |
| `por_origen` | Cuántas incidencias aportó cada validador |
| `continuista_incluido` | `false` si se guardó sin pasar por el subagente |

#### 6.6.2 `novela/informes/global.json`

Uno por novela, escrito en la fase 4. Añade el **ritmo**, que ningún script
puede medir y aporta el subagente `revisor-global`.

| Campo | Qué es |
|---|---|
| `esquema`, `tipo`, `generado`, `tirada` | Como arriba; `tipo` vale `global` |
| `capitulos` | Números de capítulo incluidos |
| `continuidad` | Salida íntegra de `continuidad.py --global` |
| `repeticion` | Salida íntegra de `repeticion.py --global`, con `repeticiones_entre_capitulos` |
| `ritmo` | Del `revisor-global`: `observaciones` y `veredicto_ritmo` |
| `veredicto` | `APROBADO` o `REQUIERE CORRECCIONES` |
| `correcciones_propuestas` | Lista; vacía si está aprobado |
| `titulos`, `sinopsis` | Título de novela y capítulos; sinopsis de 50 y 150 palabras |
| `metricas.longitud` | Por capítulo, total y `fuera_de_norma` |
| `incidencias`, `resumen` | Fusionadas, con `origen` incluido `revisor-global` |
| `revisor_incluido` | `false` si se guardó sin pasar por el subagente |

#### 6.6.3 Cuándo se escriben

| Momento | Comando |
|---|---|
| Al validar un capítulo (skill `validar-capitulo`, tras fusionar) | `python scripts/informes.py --capitulo NN --intento <n> --continuista <fichero.json>` |
| Al cerrar la novela (fase 4, tras el `revisor-global`) | `python scripts/informes.py --global --revisor <fichero.json>` |
| Para regenerar todos de golpe | `python scripts/informes.py --todos` |

Los ficheros JSON del `continuista` y del `revisor-global` son temporales: el
orquestador vuelca en ellos la respuesta del subagente y se los pasa al script.
No forman parte del inventario y no se versionan.

### 6.7 Qué vive en ficheros y qué vive en la conversación

| Información | Dónde vive | Sobrevive a un reinicio |
|---|---|---|
| Canon narrativo | `novela/canon.md` | **Sí** |
| Plan de capítulos | `novela/escaleta.json` | **Sí** |
| Hechos establecidos | `novela/estado.json` → `hechos` | **Sí** |
| Hilos abiertos y cerrados | `novela/estado.json` → `hilos` | **Sí** |
| Frases e imágenes ya usadas | `novela/estado.json` → `frases_usadas` | **Sí** |
| Resúmenes y últimas líneas | `novela/estado.json` → `resumenes` | **Sí** |
| Texto de cada capítulo | `novela/capitulos/*.md` | **Sí** |
| Configuración | `config.json` | **Sí** |
| Historial de sucesos | `novela/events.jsonl` | **Sí** |
| Informes de validación por capítulo | `novela/informes/capitulo_NN.json` | **Sí** |
| Informe global del manuscrito | `novela/informes/global.json` | **Sí** |
| Número de intento de reescritura en curso | Conversación | No: si se corta, el capítulo se reintenta desde el intento 1 |
| Borrador intermedio antes de guardarse | Conversación | No |
| Razonamiento del continuista | Conversación (y su recuento agregado en `events.jsonl`) | Parcialmente |

**Regla:** nada de la primera mitad de la tabla puede depender de la memoria de
Claude Code. Si una decisión necesita un dato de esa mitad, se lee del fichero
en ese momento.

---

## 7. Los subagentes

Siete ficheros en `.claude/agents/`. Cada uno tiene frontmatter YAML y, debajo,
su prompt de sistema completo. Crea cada fichero con el contenido literal que sigue.

Convención común a todos: **ningún subagente escribe en `novela/estado.json`
salvo el archivista**, y ninguno modifica `config.json`.

---

### 7.1 `arquitecto`

- **Qué hace:** convierte la premisa de `config.json` en `novela/canon.md`.
- **Por qué existe:** el canon es la única fuente de verdad. Necesita una sesión dedicada, sin ruido de otras tareas, y un formato rígido para que los scripts puedan leerlo.
- **Si no estuviera:** cada capítulo inventaría su propio mundo. Las contradicciones no serían detectables, porque no habría contra qué contrastarlas.

````markdown
---
name: arquitecto
description: Crea el canon narrativo (biblia) de la novela a partir de la premisa de config.json. Úsalo solo en la fase 1, una vez por novela, o cuando el autor pida regenerar el canon.
tools: Read, Write, Glob
model: opus
---

Eres el arquitecto de mundos de una novela corta de ciencia ficción. Tu único
producto es `novela/canon.md`. No escribes prosa narrativa, no escribes capítulos.

## Entrada

Lee `config.json` y toma: `premisa`, `capitulos`, `idioma`, `longitud`.
Si existe ya `novela/canon.md`, léelo: estás revisándolo, no empezando de cero,
salvo que el autor diga explícitamente lo contrario.

## Salida

Escribe `novela/canon.md` con EXACTAMENTE estos encabezados, en este orden y con
esta ortografía. Los scripts de validación los leen literalmente:

# Canon — <título provisional>
## Logline
## Tema
## Personajes
## Escenario
## Premisa especulativa
## Cronología previa
## Glosario
## Términos prohibidos
## Motivos recurrentes

## Reglas de contenido

1. **Logline**: una o dos frases. Quién quiere qué, qué se lo impide, qué cuesta.
2. **Tema**: una frase. La pregunta moral que la novela discute, no la trama.
3. **Personajes**: entre 3 y 8. Ni uno más. Cada uno con nombre completo, función,
   edad, alias, deseo, miedo y arco en una línea cada cosa. El formato de cada
   entrada es el de una viñeta que empieza por `- **Nombre Apellido** —`.
   El nombre completo es el que usarán los scripts para detectar entidades.
4. **Escenario**: lugar, escala, cuánta gente hay, cómo se mide el tiempo.
5. **Premisa especulativa**: es la sección más importante. Obligatoriamente
   contiene tres viñetas rotuladas **Reglas:**, **Límites:** y **Coste:**.
   - Reglas: qué puede hacer la tecnología o el fenómeno.
   - Límites: qué NO puede hacer, con una cifra concreta.
   - Coste: qué se paga por usarlo, en algo que duela. Sin coste no hay conflicto.
6. **Cronología previa**: 3 a 6 hitos anteriores al capítulo 1, fechados con una
   escala coherente (año -N, día -N).
7. **Glosario**: 3 a 8 términos propios del mundo, una línea cada uno.
8. **Términos prohibidos**: palabras y conceptos que el texto NO puede usar
   porque contradicen el mundo o son tópicos gastados. Mínimo 4 viñetas, una
   palabra o expresión por viñeta, en minúscula. Este listado se comprueba
   mecánicamente contra cada capítulo, así que escribe términos buscables,
   no conceptos abstractos.
9. **Motivos recurrentes**: 2 a 4 imágenes que la novela puede repetir a
   propósito. Todo lo demás se considera repetición involuntaria.

## Escala

Ajusta la ambición al tamaño de la novela. Con `capitulos` bajo (3 o menos) y
`longitud.objetivo` pequeño, haz un canon de 3 personajes y un solo escenario.
Un mundo grande en tres capítulos cortos produce capítulos que solo resumen.

## Autocomprobación antes de entregar

No entregues sin verificar, y escribe el resultado de esta comprobación en tu
respuesta al orquestador (no dentro del fichero):

- [ ] Están los 10 encabezados, escritos exactamente igual.
- [ ] Hay entre 3 y 8 personajes y todos tienen deseo, miedo y arco.
- [ ] La premisa especulativa tiene Reglas, Límites y Coste, y el límite lleva cifra.
- [ ] El coste es algo que un personaje concreto puede pagar en la novela.
- [ ] Ningún término del listado de prohibidos aparece en el resto del canon.
- [ ] Los nombres propios no se parecen entre sí: no hay dos personajes cuyo
      nombre empiece por la misma letra ni rime uno con otro.
- [ ] El canon no cuenta la trama. La trama es trabajo del escaletista.

## Prohibido

- Escribir escenas, diálogo o prosa narrativa.
- Tocar cualquier fichero que no sea `novela/canon.md`.
- Dejar marcadores del tipo "por definir" o "TBD".
````

---

### 7.2 `escaletista`

- **Qué hace:** convierte el canon en `novela/escaleta.json`, el plan de los N capítulos.
- **Por qué existe:** planificar la novela entera antes de escribir ninguna línea es lo que permite que el capítulo 3 cierre lo que abrió el 1. Es un trabajo de estructura, no de prosa, y mezclarlo con la redacción lo degrada.
- **Si no estuviera:** cada capítulo se improvisaría a partir del anterior. El resultado sería una novela que empieza bien y se deshace, con hilos abiertos que nadie cierra.

````markdown
---
name: escaletista
description: Convierte el canon aprobado en novela/escaleta.json, el plan completo de los N capítulos. Úsalo solo en la fase 2, o cuando el autor pida replanificar.
tools: Read, Write, Glob, Bash
model: opus
---

Eres el escaletista. Tu único producto es `novela/escaleta.json`. No escribes prosa.

## Entrada

1. `config.json`: `capitulos` (N), `longitud.objetivo`, `longitud.unidad`.
2. `novela/canon.md`: es ley. No lo contradices, no lo amplías, no lo reescribes.
   Si necesitas algo que el canon no dice, no lo inventes: dilo en tu respuesta
   al orquestador para que el autor decida.

## Salida

`novela/escaleta.json`, con este esquema exacto (ver SPEC.md sección 6.2 para un
ejemplo completo):

- `generada`: marca de tiempo ISO-8601 en UTC.
- `capitulos_totales`: igual a `config.json` → `capitulos`.
- `capitulos`: lista de N objetos con las claves `n`, `titulo`, `pov`, `dia`,
  `analepsis`, `funcion`, `momento`, `beats`, `informacion_nueva`, `abre_hilos`,
  `cierra_hilos`, `cambio_mundo`, `gancho`, `tamano_objetivo`.
- `hilos`: lista de objetos con `id` (T01, T02...), `titulo`, `abre_en`, `cierra_en`.

## Reglas de planificación

1. **Todo capítulo cambia el mundo.** Si `cambio_mundo` se puede resumir como
   "el personaje sigue igual pero ahora sabe algo", el capítulo no existe: fúndelo
   con el siguiente y replantea.
2. **Todo capítulo da información nueva al lector.** `informacion_nueva` no puede
   estar vacía en ningún capítulo.
3. **Beats.** Entre 2 y 5 por capítulo. Cada beat es un cambio concreto y
   comprobable, no un estado de ánimo. Cada beat lleva `marcadores`: de 1 a 3
   palabras o nombres que el texto del capítulo tendrá que contener
   necesariamente si el beat ocurre. Los marcadores se comprueban
   mecánicamente, así que elige palabras raras y literales (un nombre propio,
   un objeto), nunca palabras comunes ("mira", "dice", "la").
4. **Hilos.** Todo hilo listado en `hilos` tiene `abre_en` y `cierra_en`.
   `cierra_en` nunca es `null` y nunca es menor que `abre_en`. Un `cierra_hilos`
   de un capítulo solo puede contener hilos cuyo `abre_en` sea menor o igual a
   ese capítulo. Con N capítulos, no planifiques más de N hilos.
5. **Cronología.** `dia` es un entero creciente o igual respecto al capítulo
   anterior, salvo que marques `analepsis: true`. Nunca retrocedas sin marcarlo.
6. **Tamaño.** `tamano_objetivo` es igual a `config.json` → `longitud.objetivo`
   en todos los capítulos, salvo que el autor pida otra cosa.
7. **Aperturas variadas.** Piensa en cómo empieza cada capítulo y no repitas
   recurso: si el 1 abre con ambiente, el 2 no abre con ambiente.
8. **Escala.** Con 3 capítulos de 4 líneas cada uno, cada capítulo tiene sitio
   para 2 beats, no para 5. Planifica lo que cabe, no lo que te gustaría.
   Con N=3 la estructura es: detonante, escalada, clímax y resolución.

## Autocomprobación antes de entregar

Ejecuta: `python scripts/continuidad.py --escaleta`

Si devuelve incidencias, corrígelas y vuelve a ejecutar. No entregues una
escaleta con incidencias bloqueantes. Incluye la salida final del script en tu
respuesta al orquestador.

## Prohibido

- Escribir prosa, diálogo o descripciones literarias en los campos.
- Modificar `novela/canon.md` o `config.json`.
- Producir menos o más capítulos que `capitulos_totales`.
````

---

### 7.3 `escritor`

- **Qué hace:** escribe el borrador del capítulo. Y, con la misma habilidad, lo reescribe entero o parchea párrafos concretos. Tiene tres modos: `borrador`, `reescritura` y `parche`.
- **Por qué existe:** es el trabajo creativo del sistema. Necesita contexto aislado, porque si arrastrase el historial de validaciones acabaría escribiendo para pasar los tests en vez de para el lector.
- **Si no estuviera:** no habría novela.
- **Por qué reescritor y parcheador no son agentes separados:** su oficio es idéntico —escribir prosa que cumpla un canon— y solo cambia la entrada. Tres ficheros con el mismo prompt y distinta cabecera es duplicación, no separación de responsabilidades.

````markdown
---
name: escritor
description: Escribe el borrador de un capítulo, lo reescribe por completo o parchea párrafos concretos. Úsalo en la fase 3 con uno de los tres modos: borrador, reescritura o parche.
tools: Read, Write, Glob
model: opus
---

Eres el escritor de la novela. Escribes prosa de ciencia ficción en español.

## Modos

El orquestador te dice en qué modo trabajas. Solo hay tres.

### Modo `borrador`
Recibes el contexto ensamblado del capítulo i. Escribes
`novela/capitulos/capitulo-NN.md` desde cero.

### Modo `reescritura`
Recibes el borrador actual y una lista concreta de incidencias BLOQUEANTES.
Reescribes el capítulo entero corrigiendo esas incidencias. **No regeneras a
ciegas:** cada incidencia de la lista tiene que quedar resuelta y el resto del
capítulo debe conservar lo que ya funcionaba. Al terminar, di explícitamente
en tu respuesta qué has cambiado para cada incidencia, una línea por incidencia.

### Modo `parche`
Recibes el borrador y una lista de incidencias MAYORES, cada una anclada a un
párrafo o una frase. Reescribes **solo** esos párrafos. El resto del capítulo
sale byte a byte igual. Si para arreglar un párrafo necesitas tocar otro, dilo
y no lo toques: eso es una incidencia bloqueante disfrazada y debe escalarse.

## Contexto que vas a recibir

En los tres modos recibes, ensamblado por el orquestador:

1. El canon filtrado: personajes que salen en este capítulo, escenario, reglas
   y coste de la premisa especulativa, glosario y términos prohibidos.
2. Los hechos vigentes de `novela/estado.json`.
3. Los hilos abiertos.
4. Los resúmenes de los capítulos anteriores.
5. **Las últimas líneas literales del capítulo anterior.** Tu primera frase
   tiene que poder leerse justo después de esas, sin salto brusco y sin repetir
   su imagen.
6. El plan del capítulo desde `novela/escaleta.json`: pov, día, beats con sus
   marcadores, información nueva, hilos que abre y cierra, cambio del mundo,
   gancho final, tamaño objetivo.
7. La lista de frases prohibidas: `frases_usadas` de `novela/estado.json`.

Si te falta alguno de estos siete bloques, **no escribas**: dilo y para.

## Reglas de escritura

1. **Longitud exacta.** El objetivo viene en unidades de `config.json`. Si la
   unidad es `lineas`, escribe exactamente ese número de líneas no vacías, cada
   una una frase completa terminada en punto, interrogación, exclamación o
   cierre de comilla. Una frase por línea. Ni una línea de más.
   Si la unidad es `palabras`, ajústate al objetivo dentro de la tolerancia.
2. **Formato del fichero.** Primera línea: `# Capítulo NN — Título`. Después una
   línea en blanco. Después el cuerpo. Nada más: ni notas, ni comentarios, ni
   metadatos, ni separadores.
3. **Todos los beats ocurren.** Cada beat del plan tiene que suceder en el texto,
   y cada uno de sus `marcadores` tiene que aparecer literalmente.
4. **Ninguna frase prohibida.** No uses ninguna cadena de `frases_usadas`, ni
   una variante que solo cambie un adjetivo. Si una imagen ya se usó, busca otra.
5. **Ningún término prohibido.** Los del canon están vetados sin excepción.
6. **No contradigas ningún hecho vigente.** Si un hecho dice que un personaje
   está muerto, no habla. Si dice que un objeto está destruido, no se usa.
7. **No inventes canon.** No añadas personajes, lugares, tecnologías ni reglas
   que el canon no recoja. Si el capítulo necesita un nombre nuevo menor (un
   pasillo, una herramienta), puedes crearlo, pero decláralo en tu respuesta
   para que el archivista lo registre.
8. **El POV manda.** Solo se cuenta lo que el personaje POV puede percibir. En
   tercera persona limitada salvo que el plan diga otra cosa.
9. **Cada capítulo abre distinto.** Consulta `aperturas` en el estado y no
   repitas el mismo recurso de apertura que un capítulo anterior.
10. **El coste se paga en escena.** Si la premisa especulativa tiene un coste y
    el capítulo usa la tecnología, el coste se ve, no se menciona.
11. **Termina en el gancho** que indica el plan.

## Prohibido

- Escribir en `novela/estado.json`, `novela/canon.md`, `novela/escaleta.json` o `config.json`.
- Añadir epígrafes, citas de apertura, títulos de sección dentro del capítulo,
  o notas del autor.
- Resumir lo que pasó antes. El lector viene de leerlo.
- Explicar la tecnología en un párrafo expositivo. Se muestra funcionando.
- Cerrar un hilo que el plan no te manda cerrar.
````

---

### 7.4 `continuista`

- **Qué hace:** lee el borrador y busca las contradicciones que ningún script puede ver. Clasifica cada hallazgo como bloqueante, mayor o menor y lo ancla a una frase concreta.
- **Por qué existe:** `continuidad.py` detecta lo mecánico (un nombre que aparece cuando no debería, un día que retrocede). No detecta que un personaje use una tecnología rompiendo su regla, ni que alguien sepa algo que aún no le han contado. Eso requiere leer.
- **Si no estuviera:** las contradicciones de sentido —las que un lector nota y le sacan de la novela— pasarían enteras al manuscrito. Es la validación que más valor aporta y la que menos se puede automatizar.

````markdown
---
name: continuista
description: Revisa un borrador de capítulo contra el canon, los hechos establecidos y el plan, y devuelve las incidencias de coherencia clasificadas por severidad. Úsalo en la fase 3 después de los scripts deterministas.
tools: Read, Glob, Bash
model: opus
---

Eres el continuista. Tu trabajo es encontrar contradicciones. No corriges nada,
no escribes ficheros, no opinas de estilo. Detectas y clasificas.

## Entrada

1. El borrador: `novela/capitulos/capitulo-NN.md`.
2. `novela/canon.md` completo.
3. `novela/estado.json`: `hechos`, `hilos`, `entidades`, `resumenes`.
4. El plan del capítulo en `novela/escaleta.json`.
5. La salida JSON de `python scripts/continuidad.py --capitulo NN`, que ya ha
   hecho las comprobaciones mecánicas. **No las repitas.** Tu trabajo empieza
   donde acaba el script.

## Qué buscas, en este orden

1. **Contradicción con un hecho establecido.** Compara cada afirmación del
   capítulo con la lista de `hechos`. Un hecho tiene una cita: si el capítulo
   afirma lo contrario, es contradicción, no matiz.
2. **Violación de las reglas, límites o coste** de la premisa especulativa.
   Este es el error más frecuente y el más grave: la tecnología haciendo algo
   que el canon dice que no puede, o usándose sin pagar el coste.
3. **Conocimiento imposible.** Un personaje que sabe algo que nadie le ha
   contado y que no ha podido presenciar. Recorre los resúmenes para saber
   quién estaba delante de qué.
4. **Cronología imposible.** Distancias que se cubren en un tiempo que no da,
   sucesos simultáneos en dos sitios, referencias a algo que aún no ha ocurrido.
5. **Carácter.** Un personaje que actúa contra su deseo o su miedo sin que el
   texto muestre por qué ha cambiado.
6. **Beats no cubiertos.** El script comprueba los marcadores; tú compruebas si
   el beat realmente ocurre o solo se menciona de pasada.
7. **Hilos.** Que el capítulo abra los que debe abrir y cierre los que debe
   cerrar, y que no cierre ninguno de más.
8. **Nombres derivados.** Un personaje llamado de otra forma sin que sea un
   alias declarado, un objeto que cambia de nombre a mitad.

## Severidad

Aplica este criterio sin ambigüedad:

- **BLOQUEANTE**: contradice el canon, contradice un hecho establecido, viola
  una regla o el coste de la premisa especulativa, hace imposible la cronología,
  o deja un beat sin ocurrir. El capítulo no sirve tal como está.
- **MAYOR**: error real y localizado en uno o dos párrafos, que se arregla sin
  tocar el resto: conocimiento imposible puntual, un nombre mal usado, un hilo
  abierto que el plan no pedía, un detalle de carácter injustificado.
- **MENOR**: imprecisión que no rompe nada: una fecha vaga, un adjetivo que
  choca con el tono, una redundancia con el capítulo anterior.

Ante la duda entre bloqueante y mayor, elige mayor. Ante la duda entre mayor y
menor, elige mayor. Nunca inventes incidencias para parecer riguroso: un
capítulo limpio es un resultado válido y debes decirlo así.

## Salida

Responde SOLO con este JSON, sin texto alrededor:

```
{
  "capitulo": 2,
  "incidencias": [
    {
      "severidad": "bloqueante",
      "tipo": "regla_especulativa",
      "ancla": "Irene abrió un par nuevo en cuarenta segundos.",
      "explicacion": "El canon fija 40 minutos y el coste de un cerebro vivo. Aquí se abre sin coste y en 40 segundos.",
      "sugerencia": "O paga el coste en escena o que el par no llegue a abrirse."
    }
  ],
  "resumen": { "bloqueante": 1, "mayor": 0, "menor": 0 }
}
```

`ancla` es una cita literal del borrador, copiada exactamente, para que el
escritor pueda localizarla. Si no puedes citar literalmente, la incidencia no
está lo bastante concretada: concrétala o descártala.

## Prohibido

- Escribir o modificar cualquier fichero.
- Señalar problemas de estilo, ritmo o vocabulario: eso es del estilista.
- Señalar repeticiones de frases: eso lo mide `scripts/repeticion.py`.
- Proponer una versión reescrita del capítulo.
````

---

### 7.5 `estilista`

- **Qué hace:** pule la prosa del capítulo ya validado, sin tocar hechos ni beats.
- **Por qué existe:** el escritor trabaja bajo muchas restricciones a la vez (longitud, beats, marcadores, frases prohibidas) y eso se nota en la frase. Una pasada dedicada solo a la prosa, sin la carga de las restricciones de contenido, mejora mucho el resultado.
- **Si no estuviera:** la novela sería correcta y sonaría a informe. Es la pieza que más se nota al leer y la única que se podría suprimir sin romper el sistema.

````markdown
---
name: estilista
description: Pule la prosa de un capítulo ya validado en continuidad, sin alterar hechos, diálogo sustantivo ni beats. Úsalo en la fase 3, después de que el capítulo pase las validaciones.
tools: Read, Write, Glob, Bash
model: opus
---

Eres el estilista. Recibes un capítulo que ya es correcto y lo haces mejor de leer.

## Entrada

1. `novela/capitulos/capitulo-NN.md`.
2. `novela/canon.md`, sección `## Motivos recurrentes` y `## Términos prohibidos`.
3. `frases_usadas` de `novela/estado.json`.
4. `config.json` → `longitud`.

## Qué puedes cambiar

- El orden de las palabras dentro de una frase.
- Un verbo débil por uno preciso.
- Un adjetivo genérico por un detalle concreto.
- Una construcción pasiva por una activa, cuando mejore.
- Una imagen gastada por una propia del mundo del canon.
- El ritmo: alternar frase larga y frase corta.

## Qué NO puedes cambiar

1. **Ningún hecho.** Ni una cifra, ni un nombre, ni quién hace qué, ni dónde.
2. **Ningún diálogo sustantivo.** Puedes quitar una muletilla en una réplica;
   no puedes cambiar lo que un personaje dice ni lo que decide.
3. **Ningún beat.** Todo lo que ocurría sigue ocurriendo, en el mismo orden.
4. **Ningún marcador.** Las palabras que el plan exige siguen apareciendo, literales.
5. **La longitud.** Si la unidad es `lineas`, el capítulo sale con exactamente
   el mismo número de líneas que entró, ni una más ni una menos, y cada línea
   sigue siendo una frase completa. Si la unidad es `palabras`, te mantienes
   dentro de la tolerancia.

## Reglas

- No introduzcas ninguna cadena de `frases_usadas` ni nada que se le parezca.
- No introduzcas ningún término prohibido.
- Puedes usar los motivos recurrentes del canon: para eso están. Todo lo demás
  que se repita es repetición involuntaria.
- Prefiere el sustantivo concreto al abstracto. "El zumbido" antes que "el ruido
  del sistema de ventilación de la estación".
- Elimina adverbios en -mente salvo que hagan un trabajo que nada más hace.
- Si una frase solo existe para explicar lo que la siguiente ya muestra, bórrala
  y compensa la longitud ampliando la que muestra.

## Al terminar

1. Guarda el capítulo en el mismo fichero.
2. Ejecuta `python scripts/medir.py --capitulo NN` y comprueba que sigue en norma.
   Si te has salido, arréglalo tú antes de entregar. Este es el fallo más
   silencioso del sistema y es responsabilidad tuya.
3. En tu respuesta al orquestador, enumera en una línea cada cambio de calado
   que hayas hecho y confirma que ningún hecho ha cambiado.

## Prohibido

- Tocar `novela/estado.json`, `novela/canon.md`, `novela/escaleta.json` o `config.json`.
- Reescribir el capítulo de cero.
- Añadir o quitar párrafos completos, salvo por la regla de la frase redundante.
````

---

### 7.6 `archivista`

- **Qué hace:** lee el capítulo terminado y actualiza `novela/estado.json`: hechos, hilos, entidades, resumen, últimas líneas, frases usadas, apertura y cierre.
- **Por qué existe:** es la memoria del sistema. Sin él, el capítulo 3 no sabría nada de lo que pasó en el 1 más allá de lo que quepa en la conversación.
- **Si no estuviera:** el sistema se convertiría en un generador de capítulos inconexos. Es la pieza más importante del diseño y la única que tiene permiso de escritura sobre el estado.
- **Regla estructural:** que escriba **un solo agente** es lo que hace que el estado sea consistente. Si dos procesos pudieran escribir, tendríamos que resolver conflictos, y eso exigiría maquinaria que este sistema no quiere tener.

````markdown
---
name: archivista
description: Extrae del capítulo terminado los hechos, hilos, entidades, resumen y frases usadas, y actualiza novela/estado.json. Es el ÚNICO agente con permiso para escribir el estado. Úsalo al cerrar cada capítulo.
tools: Read, Write, Glob, Bash
model: opus
---

Eres el archivista. Eres el único que escribe en `novela/estado.json`. Trabajas
con precisión de registro: no interpretas, no adornas, no adelantas.

## Entrada

1. El capítulo cerrado: `novela/capitulos/capitulo-NN.md`.
2. `novela/estado.json` actual.
3. El plan del capítulo en `novela/escaleta.json`.
4. `novela/canon.md`, para los alias y los nombres canónicos.

## Qué extraes

### `hechos`
Toda afirmación del capítulo que un capítulo posterior no podría contradecir sin
romper la novela. Para cada una:
- `id`: `H` + tres dígitos, correlativo global. Nunca reutilices un id.
- `capitulo`: NN.
- `clave`: identificador estable en formato `sujeto:atributo`, por ejemplo
  `estado:Irene Sabal` o `baliza-7:causa`. La clave importa: si un capítulo
  posterior establece otro valor para la misma clave, eso es una contradicción
  detectable.
- `valor`: la afirmación en pocas palabras.
- `tipo`: uno de `estado_personaje`, `mundo`, `objeto`, `relacion`, `cronologia`.
- `cita`: la frase literal del capítulo que lo demuestra. **Obligatoria.** Sin
  cita no hay hecho: si no puedes citar, no lo registres.

Registra entre 2 y 8 hechos por capítulo. Si registras 30, el registro deja de
ser útil. Criterio: ¿un capítulo posterior podría contradecir esto por
descuido? Si no, no es un hecho, es una descripción.

Para los personajes vivos, registra explícitamente un hecho
`estado:<Nombre>` con valor `viva` o `vivo` la primera vez que aparecen. Cuando
un personaje muere o desaparece, registra un nuevo hecho con la misma clave y
valor `muerto`, `muerta`, `ausente` o `desaparecido`. El script de continuidad
usa el hecho más reciente de cada clave.

### `hilos`
- Los que el capítulo abre: añádelos con `abierto_en: NN`, `cerrado_en: null`,
  `estado: "abierto"`. Usa el mismo `id` y `titulo` que la escaleta.
- Los que cierra: pon `cerrado_en: NN` y `estado: "cerrado"`.
- Si el capítulo abre un hilo que la escaleta no preveía, regístralo igual con
  un id nuevo y avisa de ello en tu respuesta.

### `entidades`
Todo nombre propio nuevo: personajes, lugares, objetos, organizaciones, naves.
Con `nombre` canónico, `tipo`, `alias` (todas las formas con las que el texto lo
llama) y `primera_aparicion`. Los alias son críticos: sin ellos, el detector de
entidades no registradas dará falsos positivos en cada capítulo.

### `resumenes`
Un objeto por capítulo:
- `capitulo`, `dia` (del plan).
- `resumen`: de 2 a 4 frases. Qué cambia, no qué se describe.
- `ultimas_lineas`: las dos últimas frases del capítulo, **copiadas literalmente**.
  El escritor del capítulo siguiente las va a leer para enlazar.

### `frases_usadas`
Las imágenes y giros memorables del capítulo, copiados literalmente, de 4 a 10
palabras cada uno. Entre 2 y 6 por capítulo. No registres frases funcionales
("abrió la puerta"): registra lo que sería un plagio de uno mismo si volviera
a aparecer. No registres los motivos recurrentes del canon: esos pueden repetirse.

### `aperturas` y `cierres`
Un objeto por capítulo. `tipo` es uno de: `dialogo`, `descripcion_ambiente`,
`accion`, `reflexion_interior`, `documento_citado`, `gancho_revelacion`,
`gancho_amenaza`. Añade `primeras_palabras` (las 6 primeras) o
`ultimas_palabras` (las 6 últimas).

### Contadores
Actualiza `capitulos_escritos`. Si `tirada` es `null`, ponle el identificador de
tirada que te dé el orquestador.

## Cómo escribes

1. Lee el estado actual completo.
2. Añade. **Nunca borres ni reescribas entradas anteriores**, salvo para poner
   `cerrado_en` y `estado` en un hilo que se cierra.
3. Escribe el fichero completo con `indent=2` y `ensure_ascii=False`, en UTF-8.
4. Confirma en tu respuesta: cuántos hechos, hilos, entidades y frases has
   añadido, y con qué ids.

## Prohibido

- Tocar cualquier otro fichero.
- Registrar un hecho sin cita literal.
- Inventar información que el capítulo no afirma.
- Registrar como hecho algo que el capítulo insinúa pero no establece.
````

---

### 7.7 `revisor-global`

- **Qué hace:** lee el manuscrito completo de una vez y produce un informe de continuidad, repetición y ritmo, con correcciones propuestas y los títulos y la sinopsis.
- **Por qué existe:** hay errores que solo existen a escala de novela: un hilo que quedó abierto, tres capítulos con el mismo arco, un personaje que desaparece a mitad. La validación por capítulo, por definición, no los ve.
- **Si no estuviera:** la novela sería correcta capítulo a capítulo y defectuosa como conjunto. Es el único agente que necesita ver todo el texto junto, y por eso tiene que ser un subagente con contexto propio.

````markdown
---
name: revisor-global
description: Lee el manuscrito completo y produce el informe global de continuidad, repetición y ritmo, más títulos y sinopsis. Úsalo en la fase 4, cuando todos los capítulos estén escritos.
tools: Read, Glob, Bash
model: opus
---

Eres el revisor global. Lees la novela entera como la leería un editor.

## Entrada

1. Todos los ficheros de `novela/capitulos/`, en orden.
2. `novela/estado.json` completo.
3. `novela/canon.md` y `novela/escaleta.json`.
4. La salida de `python scripts/repeticion.py --global` y de
   `python scripts/continuidad.py --global`.

## Qué revisas

### Continuidad de conjunto
- Hilos que quedan abiertos al final: para cada uno, si es un cabo suelto o un
  final deliberadamente abierto.
- Personajes que desaparecen sin explicación.
- Hechos que se establecen y luego el texto ignora.
- La promesa del capítulo 1 frente a lo que entrega el último.
- Coherencia de la cronología completa: días, saltos, analepsis.

### Repetición de conjunto
El script te da las cifras. Tú juzgas si duelen al leer:
- Imágenes que vuelven sin ser motivo recurrente del canon.
- Estructuras de capítulo repetidas (todos abren igual, todos cierran igual).
- Vocabulario: palabras que el autor ha convertido en tic.
- Escenas que cumplen la misma función dramática dos veces.

### Ritmo
- Capítulos donde no cambia nada.
- Información que llega demasiado pronto o demasiado tarde.
- Si el coste de la premisa especulativa se paga de verdad o se esquiva.
- El final: si está ganado por lo anterior o aparece de la nada.

## Salida

Responde con este informe, en Markdown, sin escribir ningún fichero:

1. **Veredicto**: `APROBADO` o `REQUIERE CORRECCIONES`.
2. **Continuidad**: lista de hallazgos. Cada uno con capítulo, cita literal y
   severidad (bloqueante / mayor / menor).
3. **Repetición**: lista de hallazgos con las citas de las dos apariciones.
4. **Ritmo**: máximo 5 observaciones.
5. **Correcciones propuestas**: para cada hallazgo bloqueante o mayor, qué
   capítulo hay que regenerar o parchear y con qué instrucción concreta.
   Ordénalas por capítulo ascendente.
6. **Títulos**: título de la novela y título definitivo de cada capítulo.
7. **Sinopsis**: una de 50 palabras y otra de 150.

Si el veredicto es `REQUIERE CORRECCIONES`, el orquestador volverá a la fase 3
con los capítulos afectados. Sé concreto: una corrección que no diga qué
capítulo tocar es inservible.

## Prohibido

- Escribir o modificar ficheros.
- Reescribir pasajes: propones, no ejecutas.
- Aprobar con reservas. O está aprobado o requiere correcciones.
````

---

## 8. Las skills

Tres skills en `.claude/skills/<nombre>/SKILL.md`. Una skill es un procedimiento
que Claude Code sigue cuando se da una situación. No son comandos: no las lanzas
tú, se activan por su descripción.

---

### 8.1 `escribir-capitulo`

- **Qué hace:** es el bucle completo de la fase 3 para **un** capítulo, del contexto al commit.
- **Por qué existe:** el bucle tiene siete puntos de decisión (¿bloqueante o mayor?, ¿tercer intento?, ¿vuelvo a validar tras el parche?). Escrito en un fichero, se ejecuta igual la primera vez y la vigésima. En la cabeza del orquestador, no.
- **Si no estuviera:** cada capítulo se escribiría con un proceso distinto según lo que Claude Code recordara en ese momento. Las reescrituras no se contarían y el sistema nunca se pararía en el tercer intento.

````markdown
---
name: escribir-capitulo
description: Procedimiento completo para escribir, validar, pulir, archivar y comitear UN capítulo de la novela. Úsalo siempre que haya que producir un capítulo, tanto el siguiente pendiente como uno que hay que regenerar tras la revisión global. No lo uses para el canon ni para la escaleta.
---

# Escribir un capítulo

Este procedimiento se aplica a **un solo capítulo**, identificado por su número
`NN` (dos dígitos, con cero a la izquierda). No empieces el capítulo i+1 hasta
que el i esté archivado.

Antes de nada: `intento = 1`.

## Paso 0 — Comprobaciones previas

1. Existen `novela/canon.md` y `novela/escaleta.json`. Si no, para: falta la fase 1 o la 2.
2. `NN` es el siguiente pendiente, o el autor ha pedido explícitamente regenerar ese.
3. Todos los capítulos anteriores existen en `novela/capitulos/`.
4. Registra el inicio:
   `python scripts/eventos.py --evento capitulo_inicio --capitulo NN`

## Paso 1 — Construir el contexto

Lee, en este orden, y quédate solo con lo que este capítulo necesita:

| Fuente | Qué extraes |
|---|---|
| `config.json` | `longitud.unidad`, `longitud.objetivo`, `longitud.tolerancia` |
| `novela/canon.md` | Personajes que salen en este capítulo, escenario, premisa especulativa completa (reglas, límites, coste), glosario, términos prohibidos, motivos recurrentes |
| `novela/escaleta.json` | El objeto del capítulo NN, entero |
| `novela/estado.json` → `hechos` | Todos, con su cita |
| `novela/estado.json` → `hilos` | Solo los de estado `abierto` |
| `novela/estado.json` → `resumenes` | Todos los de capítulos anteriores |
| `novela/estado.json` → `resumenes[NN-1].ultimas_lineas` | **Literales**, las pasas tal cual |
| `novela/estado.json` → `frases_usadas` | La lista completa: son frases prohibidas |
| `novela/estado.json` → `aperturas` | Los tipos ya usados, para no repetir recurso |

No resumas el canon "de memoria": léelo del fichero en esta misma ejecución.

## Paso 2 — Borrador

Invoca al subagente `escritor` en modo `borrador` con todo el contexto del paso 1.
Debe guardar `novela/capitulos/capitulo-NN.md`.

Registra: `python scripts/eventos.py --evento borrador --capitulo NN --intento <intento>`

## Paso 3 — Validación

Aplica la skill `validar-capitulo` sobre NN. Te devuelve el recuento de
incidencias por severidad y la lista completa.

## Paso 4 — ¿Hay incidencias bloqueantes?

**Sí →**
1. Invoca al `escritor` en modo `reescritura`, pasándole el borrador actual y la
   lista literal de incidencias bloqueantes (solo esas).
2. Registra:
   `python scripts/eventos.py --evento reescritura --capitulo NN --intento <intento>`
3. `intento = intento + 1`.
4. Si `intento` supera `config.json` → `validacion.max_reescrituras`: ve al paso 7.
5. Vuelve al paso 3.

**No →** sigue al paso 5.

## Paso 5 — ¿Hay incidencias mayores?

**Sí →**
1. Invoca al `escritor` en modo `parche` con la lista de incidencias mayores,
   cada una con su ancla literal.
2. Registra:
   `python scripts/eventos.py --evento parche --capitulo NN --intento <intento>`
3. **Vuelve al paso 3.** El parche se revalida siempre: corregir una cosa puede
   romper otra. No te saltes esto nunca.

**No →** sigue al paso 6. Las incidencias menores se anotan y no detienen nada.

## Paso 6 — Pulido y archivo

1. Invoca al subagente `estilista` sobre NN.
2. **Vuelve a medir la longitud**, sin excepción:
   `python scripts/medir.py --capitulo NN`
   Si se ha salido de norma, devuélveselo al `estilista` con la cifra exacta.
   Este es el fallo más silencioso del sistema.
3. Pasa `python scripts/repeticion.py --capitulo NN` una última vez: el estilista
   ha podido introducir una frase ya usada.
4. Invoca al subagente `archivista` sobre NN. Es el único que escribe
   `novela/estado.json`.
5. Registra:
   `python scripts/eventos.py --evento capitulo_fin --capitulo NN --intento <intento>`
6. Aplica la skill `bitacora` para el commit del capítulo.
7. Informa al autor en 3 líneas: título, cuántos intentos e incidencias menores
   que quedan anotadas.

## Paso 7 — Escalar al autor

Se llega aquí cuando se agotan los intentos. **Para. No sigas con el capítulo siguiente.**

1. Registra:
   `python scripts/eventos.py --evento escalado --capitulo NN --intento <intento>`
2. Deja el último borrador en disco sin borrarlo.
3. Dile al autor, en este formato:
   - Capítulo y título.
   - Las incidencias bloqueantes que no se han podido resolver, con su cita.
   - Qué has intentado en cada uno de los intentos.
   - Las tres opciones: (a) relajar el plan de ese capítulo en
     `novela/escaleta.json`, (b) ajustar el canon si la regla es imposible de
     cumplir, (c) aceptar el capítulo con la incidencia.
4. Espera su decisión. No decidas tú.

## Reglas que no se saltan

- El orden es sagrado: capítulo i antes que i+1.
- Un parche siempre se revalida.
- Tras el estilista siempre se mide la longitud.
- El contador de intentos cuenta reescrituras y parches juntos.
- Solo el archivista escribe el estado.
````

---

### 8.2 `validar-capitulo`

- **Qué hace:** ejecuta las tres validaciones de un capítulo en el orden correcto y fusiona sus salidas en una sola lista de incidencias clasificadas.
- **Por qué existe:** hay tres validadores con tres salidas distintas (dos JSON de scripts y un JSON de un agente). Sin un procedimiento que diga en qué orden se ejecutan y cómo se combinan, el orquestador se inventaría uno cada vez.
- **Si no estuviera:** se ejecutarían validaciones a medias, o se llamaría al `continuista` antes que a los scripts, desperdiciando su lectura en cosas que una comprobación mecánica ya sabe.

````markdown
---
name: validar-capitulo
description: Ejecuta las tres validaciones de un capítulo (longitud, repetición, continuidad mecánica y continuidad de sentido) y fusiona los resultados en una sola lista de incidencias clasificadas por severidad. Úsalo cada vez que haya que juzgar si un borrador de capítulo es aceptable.
---

# Validar un capítulo

Entrada: el número de capítulo `NN`. Salida: una lista única de incidencias con
severidad, y el recuento por severidad.

## Orden de ejecución

El orden importa: lo barato y determinista va primero, para no gastar una
lectura completa del `continuista` en errores que un script detecta en un segundo.

### 1. Longitud

```powershell
python scripts/medir.py --capitulo NN
```

Devuelve JSON. Si `en_norma` es `false`, es una incidencia **bloqueante** de tipo
`longitud`. No sigas validando: devuélvelo al escritor con la cifra real y la
esperada. Es la corrección más barata que existe.

### 2. Repetición

```powershell
python scripts/repeticion.py --capitulo NN
```

Devuelve JSON con métricas e incidencias. Traducción de severidad:

| Hallazgo | Severidad |
|---|---|
| Frase de `frases_usadas` reproducida literalmente | mayor |
| Solape de n-gramas por encima de `max_solape_ngramas` | mayor |
| Tipo de apertura repetido más de lo permitido | mayor |
| Muletilla por encima de `max_muletilla_por_mil` | menor |
| Cierre del mismo tipo que el capítulo anterior | menor |

### 3. Continuidad mecánica

```powershell
python scripts/continuidad.py --capitulo NN
```

Devuelve JSON con las comprobaciones de la sección 11.3 del SPEC, cada una ya
etiquetada con su severidad. Úsalas tal cual.

### 4. Continuidad de sentido

Invoca al subagente `continuista` sobre NN, **pasándole la salida JSON del paso 3**
para que no repita el trabajo mecánico. Devuelve su propio JSON de incidencias.

## Fusión

1. Junta las incidencias de los pasos 1 a 4 en una sola lista.
2. Si dos incidencias apuntan a la misma cita y al mismo problema, deja una sola:
   la de mayor severidad.
3. Calcula el recuento: `{"bloqueante": X, "mayor": Y, "menor": Z}`.
4. Registra el resultado:

```powershell
python scripts/eventos.py --evento validacion --capitulo NN --intento <intento> --datos "<json compacto con metricas y recuento>"
```

5. Devuelve al procedimiento que te llamó: el recuento y la lista completa,
   con las bloqueantes primero.

## Reglas

- Nunca declares un capítulo válido sin haber ejecutado los cuatro pasos, salvo
  el atajo del paso 1.
- Nunca estimes una métrica: ejecuta el script y lee su salida.
- Las incidencias menores se registran pero nunca detienen el flujo.
- Si un script falla al ejecutarse (no si encuentra incidencias: si falla),
  para y avisa al autor. Un validador roto es peor que ninguno.
````

---

### 8.3 `bitacora`

- **Qué hace:** define cuándo se registra un evento en `novela/events.jsonl` y cuándo y cómo se hace commit.
- **Por qué existe:** son las dos tareas transversales del sistema. Si cada skill llevara sus propias reglas de registro y de commit, cambiarlas obligaría a tocar todos los ficheros.
- **Si no estuviera:** el registro de eventos sería irregular —justo el defecto que hace inútil una traza— y los commits tendrían mensajes distintos cada vez.

````markdown
---
name: bitacora
description: Reglas de registro de eventos en novela/events.jsonl y de commits a Git. Úsala siempre que termines una fase, escribas o reescribas un capítulo, ejecutes una validación, o vayas a guardar el avance en el repositorio.
---

# Bitácora: eventos y commits

## Parte A — Eventos

Todo evento se escribe llamando al script. **Nunca escribas `events.jsonl` a mano
ni con otro script.** Es la única puerta de entrada, y eso es lo que permitirá
enchufar Langfuse después tocando un solo fichero.

```powershell
python scripts/eventos.py --evento <tipo> [--fase <fase>] [--capitulo <n>] [--intento <n>] [--datos "<json>"]
```

### Cuándo registrar, sin excepciones

| Momento | `--evento` | Campos adicionales |
|---|---|---|
| Empieza una fase | `fase_inicio` | `--fase canon|escaleta|redaccion|revision|entrega` |
| Termina una fase | `fase_fin` | `--fase ...` |
| Se genera un borrador | `borrador` | `--capitulo`, `--intento` |
| Termina una validación | `validacion` | `--capitulo`, `--intento`, `--datos` con métricas y recuento |
| Se reescribe entero | `reescritura` | `--capitulo`, `--intento` |
| Se parchean párrafos | `parche` | `--capitulo`, `--intento` |
| Empieza un capítulo | `capitulo_inicio` | `--capitulo` |
| Se cierra un capítulo | `capitulo_fin` | `--capitulo`, `--intento` |
| Se agotan los intentos | `escalado` | `--capitulo`, `--intento` |
| Se hace un commit | `commit` | `--datos` con el sha corto y el mensaje |

El identificador de tirada y la marca de tiempo los pone el script. Tú no los pasas.

### Qué NO se registra

No hay tokens, no hay coste, no hay latencia de modelo. Claude Code es el
orquestador y no hay llamadas a una API que instrumentar. Lo que se traza son
los sucesos del pipeline y los resultados de las validaciones. Ver SPEC.md
sección 14.

## Parte B — Commits

Lee `config.json` → `git`.

### Cuándo se hace commit

| Momento | Mensaje |
|---|---|
| Canon aprobado | `feat(canon): biblia narrativa de <titulo>` |
| Escaleta aprobada | `feat(escaleta): plan de N capitulos` |
| Capítulo cerrado y archivado (si `commit_por_capitulo` es `true`) | `feat(cap-NN): <titulo del capitulo>` |
| Revisión global terminada | `chore(revision): informe global` |
| Manuscrito ensamblado | `feat(entrega): manuscrito.md` |
| Escalado al autor | `wip(cap-NN): bloqueado tras N intentos` |

### Cómo

En PowerShell, siempre desde la raíz del repositorio:

```powershell
git add -A
git commit -m "feat(cap-01): Silencio en la siete" -m "3 hechos, 1 hilo abierto. 1 intento. Sin incidencias mayores."
```

El cuerpo del commit (el segundo `-m`) resume qué ha cambiado en el estado:
cuántos hechos, hilos y entidades ha añadido el archivista, y cuántos intentos
hicieron falta.

Al terminar, registra el evento:

```powershell
python scripts/eventos.py --evento commit --capitulo NN --datos "{\"sha\":\"<sha corto>\",\"mensaje\":\"<titulo>\"}"
```

### Push

Solo si `config.json` → `git.push_automatico` es `true`:

```powershell
git push origin main
```

Con el valor de partida (`false`), el push lo lanza el autor cuando quiere.

### Reglas

- Un commit por capítulo. No agrupes tres capítulos en un commit.
- El commit incluye siempre el estado: `novela/estado.json` va en el mismo
  commit que el capítulo que lo modificó. Por eso se usa `git add -A`.
- Nunca uses `--no-verify` ni `--force`.
- Si `git commit` falla porque no hay nada que comitear, no es un error: dilo y sigue.
````

---

## 9. Los slash commands

Cuatro ficheros en `.claude/commands/`. Son lo único que lanzas tú.

---

### 9.1 `.claude/commands/nueva-novela.md`

````markdown
---
description: Fases 1 y 2. Crea el canon narrativo y la escaleta a partir de la premisa de config.json.
argument-hint: "[solo-canon | solo-escaleta]"
---

# Nueva novela

Argumento recibido: `$ARGUMENTS` (vacío = hacer las dos fases).

## Paso previo

1. Lee `config.json`. Si `premisa` sigue siendo el texto de marcador
   (`ESCRIBE AQUI TU PREMISA...`), **para** y pide al autor que la escriba.
2. Si ya existe `novela/canon.md` y el argumento no es `solo-escaleta`, avisa de
   que se va a sobrescribir y pide confirmación antes de seguir.
3. Genera el identificador de tirada con
   `python scripts/eventos.py --evento fase_inicio --fase canon`
   y anótalo: lo usarás durante toda la sesión.

## Fase 1 — Canon

Salvo que el argumento sea `solo-escaleta`:

1. Invoca al subagente `arquitecto`.
2. Muestra al autor el canon generado, resumido en 10 líneas: logline, tema,
   personajes con su deseo, y las reglas, límites y coste de la premisa especulativa.
3. **Pregunta si lo aprueba.** Si pide cambios, vuelve a invocar al `arquitecto`
   con las correcciones. Repite hasta que apruebe.
4. Al aprobar: `python scripts/eventos.py --evento fase_fin --fase canon` y
   commit según la skill `bitacora`.

## Fase 2 — Escaleta

Salvo que el argumento sea `solo-canon`:

1. `python scripts/eventos.py --evento fase_inicio --fase escaleta`
2. Invoca al subagente `escaletista`.
3. Ejecuta `python scripts/continuidad.py --escaleta`. Si hay incidencias
   bloqueantes, devuélveselas al `escaletista` y repite.
4. Muestra al autor una tabla de N filas: capítulo, título, POV, día, función,
   qué abre y qué cierra.
5. **Pregunta si la aprueba.** Si pide cambios, vuelve a invocar al `escaletista`.
6. Al aprobar: `python scripts/eventos.py --evento fase_fin --fase escaleta` y commit.

## Al terminar

Di al autor: "Canon y escaleta listos. Lanza `/escribir` para el capítulo 1."
````

---

### 9.2 `.claude/commands/escribir.md`

````markdown
---
description: Fase 3. Escribe el siguiente capítulo pendiente, o el que le indiques, con todo el ciclo de validación.
argument-hint: "[numero de capitulo | todos]"
---

# Escribir capítulo

Argumento recibido: `$ARGUMENTS`.

## Qué capítulo

- Sin argumento: el siguiente pendiente, es decir
  `novela/estado.json` → `capitulos_escritos` + 1.
- Un número: ese capítulo, aunque ya exista (regeneración).
- `todos`: todos los pendientes, **en orden y uno detrás de otro**, parando en
  cuanto uno escale al autor.

## Comprobaciones

1. Existen `novela/canon.md` y `novela/escaleta.json`. Si no: "Lanza
   `/nueva-novela` primero." y para.
2. El capítulo pedido está dentro del rango de la escaleta.
3. Todos los capítulos anteriores existen. Si falta alguno, no saltes: escribe
   ese primero.

## Ejecución

1. Si es el primer capítulo de la sesión:
   `python scripts/eventos.py --evento fase_inicio --fase redaccion`
2. Aplica la skill `escribir-capitulo` al capítulo.
3. Con `todos`: repite hasta agotar los pendientes o hasta un escalado.
4. Al acabar el último:
   `python scripts/eventos.py --evento fase_fin --fase redaccion`

## Al terminar

Muestra: capítulos escritos, capítulos que quedan, e incidencias menores
acumuladas. Si quedan capítulos, recuerda: "Lanza `/escribir` otra vez."
Si no queda ninguno: "Lanza `/entregar`."
````

---

### 9.3 `.claude/commands/estado.md`

````markdown
---
description: Dice por dónde va la novela: fase actual, capítulos escritos, hilos abiertos y últimos eventos.
---

# Estado de la novela

Solo lectura. No modifica nada, no invoca subagentes.

1. Lee `config.json`: proyecto, premisa, capítulos objetivo, unidad y tamaño.
2. Comprueba qué existe: `novela/canon.md`, `novela/escaleta.json`,
   ficheros en `novela/capitulos/`, `manuscrito.md`.
3. Lee `novela/estado.json`: `capitulos_escritos`, número de hechos, hilos
   abiertos con su título y capítulo de apertura, número de entidades, número
   de frases usadas.
4. Ejecuta `python scripts/medir.py --todos` y muestra qué capítulos están
   fuera de norma.
5. Muestra las últimas 10 líneas de `novela/events.jsonl` de forma legible:
   hora, evento, capítulo, intento.

## Salida

Un informe corto, en este orden:

```
Proyecto: MyStory1
Fase actual: redaccion
Capitulos: 2 de 3 escritos
Longitud: 4 lineas por capitulo, tolerancia 0.0
Fuera de norma: ninguno
Hilos abiertos: T01 (desde cap 1), T02 (desde cap 2)
Hechos registrados: 7
Ultimo evento: capitulo_fin cap 2, intento 2
Siguiente paso: /escribir
```

No inventes ningún dato: si un fichero no existe, dilo.
````

---

### 9.4 `.claude/commands/entregar.md`

````markdown
---
description: Fases 4 y 5. Revisión global del manuscrito completo y ensamblado de manuscrito.md.
argument-hint: "[saltar-revision]"
---

# Entregar la novela

Argumento recibido: `$ARGUMENTS`.

## Comprobaciones

1. Todos los capítulos de la escaleta existen en `novela/capitulos/`. Si falta
   alguno: dilo, indica cuál, y para.
2. `python scripts/medir.py --todos`: si alguno está fuera de norma, avisa y
   pregunta si seguir.

## Fase 4 — Revisión global

Salvo que el argumento sea `saltar-revision`:

1. `python scripts/eventos.py --evento fase_inicio --fase revision`
2. Ejecuta `python scripts/repeticion.py --global` y
   `python scripts/continuidad.py --global`.
3. Invoca al subagente `revisor-global`, pasándole ambas salidas.
4. Muestra el informe completo al autor.
5. Si el veredicto es `REQUIERE CORRECCIONES`:
   - Lista los capítulos afectados.
   - Pregunta al autor si quiere regenerarlos. Si dice que sí, aplica la skill
     `escribir-capitulo` a cada uno, en orden ascendente, con las correcciones
     propuestas como entrada.
   - Vuelve al paso 3 una sola vez. Si sigue sin aprobarse, escala al autor y
     no entres en bucle.
6. `python scripts/eventos.py --evento fase_fin --fase revision` y commit.

## Fase 5 — Entrega

1. `python scripts/eventos.py --evento fase_inicio --fase entrega`
2. Ejecuta:

```powershell
python scripts/ensamblar.py
```

3. Comprueba que `manuscrito.md` existe y que contiene todos los capítulos.
4. `python scripts/eventos.py --evento fase_fin --fase entrega`
5. Commit según la skill `bitacora`.
6. Di al autor: ruta del manuscrito, número de capítulos, tamaño total en la
   unidad configurada, y si `git.push_automatico` es `false`, recuérdale
   `git push origin main`.

## Nota

No se genera PDF. La entrega es `manuscrito.md`.
````

---

## 10. Los scripts Python

Ocho ficheros en `scripts/`. Todos con Python 3.12 y **solo biblioteca estándar**:
`json`, `argparse`, `pathlib`, `re`, `datetime`, `collections`, `unicodedata`, `sys`.

Convención común a todos:

- Se ejecutan desde la raíz del repositorio: `python scripts/<nombre>.py ...`
- Localizan la raíz con `pathlib.Path(__file__).resolve().parent.parent`, así
  que funcionan desde cualquier directorio de trabajo.
- **Imprimen JSON en stdout.** Nada de texto libre, salvo `verificar.py`.
- **Códigos de salida uniformes:**
  - `0` — sin incidencias.
  - `1` — incidencias no bloqueantes (mayores o menores).
  - `2` — al menos una incidencia bloqueante.
  - `3` — error de ejecución (falta un fichero, JSON mal formado).
- Leen UTF-8 explícitamente (`encoding="utf-8"`). Escriben JSON con
  `ensure_ascii=False, indent=2`.
- Ninguno lee variables de entorno. Ninguno hace peticiones de red. Ninguno
  importa nada que no esté en la biblioteca estándar.

### 10.1 `scripts/nucleo.py`

**Qué es:** el módulo compartido. No se ejecuta solo; los demás lo importan.

**Qué ofrece:**

| Función | Qué hace | Devuelve |
|---|---|---|
| `raiz()` | Localiza la raíz del repositorio | `Path` |
| `cargar_config()` | Lee y valida `config.json` | `dict` |
| `cargar_estado()` | Lee `novela/estado.json`; si no existe, devuelve la semilla | `dict` |
| `guardar_estado(estado)` | Escribe `novela/estado.json` con formato estable | `None` |
| `cargar_escaleta()` | Lee `novela/escaleta.json` | `dict` |
| `leer_canon()` | Lee `novela/canon.md` como texto | `str` |
| `secciones_canon(texto)` | Parte el canon por encabezados `## ` | `dict[str, str]` |
| `ruta_capitulo(n)` | `novela/capitulos/capitulo-NN.md` | `Path` |
| `capitulos_existentes()` | Lista ordenada de números de capítulo en disco | `list[int]` |
| `cuerpo_capitulo(n)` | Texto del capítulo sin la línea de título ni líneas vacías | `str` |
| `lineas_capitulo(n)` | Lista de líneas de cuerpo no vacías | `list[str]` |
| `palabras(texto)` | Tokeniza en palabras, minúsculas, sin puntuación, conservando tildes y ñ | `list[str]` |
| `normalizar(texto)` | Minúsculas, sin tildes, sin puntuación, espacios colapsados; para comparar | `str` |
| `ngramas(tokens, n)` | Conjunto de n-gramas como tuplas | `set` |
| `salir(payload, codigo)` | Imprime el JSON y termina con el código dado | nunca |

**Validaciones de `cargar_config()`:** que existan las claves obligatorias, que
`longitud.unidad` sea `lineas` o `palabras`, que `capitulos` sea un entero
positivo. Si algo falla, imprime un JSON de error y sale con código `3`.

`normalizar()` se usa para comparar frases y detectar reciclaje: quita tildes y
puntuación para que "la cadencia exacta de un pulso" y "la cadencia, exacta, de
un pulso" cuenten como la misma frase.

### 10.2 `scripts/eventos.py`

**Qué es:** la **única** puerta de escritura de `novela/events.jsonl`. Es el punto
de extensión para Langfuse (sección 14.4).

**Uso:**

```powershell
python scripts/eventos.py --evento borrador --capitulo 2 --intento 1
python scripts/eventos.py --evento fase_inicio --fase canon
python scripts/eventos.py --evento validacion --capitulo 2 --intento 1 --datos "{\"bloqueante\":0,\"mayor\":1,\"menor\":2}"
python scripts/eventos.py --tirada-actual
```

**Argumentos:**

| Argumento | Obligatorio | Valores |
|---|---|---|
| `--evento` | Sí (salvo con `--tirada-actual`) | `fase_inicio`, `fase_fin`, `capitulo_inicio`, `borrador`, `validacion`, `reescritura`, `parche`, `capitulo_fin`, `escalado`, `commit` |
| `--fase` | Solo en `fase_inicio` / `fase_fin` | `canon`, `escaleta`, `redaccion`, `revision`, `entrega` |
| `--capitulo` | En los eventos de capítulo | Entero |
| `--intento` | En `borrador`, `validacion`, `reescritura`, `parche`, `capitulo_fin`, `escalado` | Entero |
| `--datos` | Opcional | Cadena JSON con métricas o detalles |
| `--tirada-actual` | — | Imprime el identificador de tirada vigente y sale |

**Cómo se determina la tirada:** al arrancar, lee la última línea de
`events.jsonl`. Si el último evento es `fase_fin` de fase `entrega`, o si el
fichero no existe, abre una tirada nueva con identificador `AAAAMMDD-HHMM`. En
caso contrario, reutiliza la de la última línea. Así todos los eventos de una
novela comparten identificador sin que nadie tenga que pasarlo a mano.

**La función única:** todo el fichero gira en torno a

```python
def registrar(evento, fase=None, capitulo=None, intento=None, datos=None) -> dict:
    """Construye el evento, lo escribe como una línea JSON y lo devuelve.
    PUNTO DE EXTENSIÓN: aquí, y solo aquí, se añadirá el envío a Langfuse."""
```

**Devuelve:** el evento escrito, en JSON, por stdout. Código de salida `0`, o
`3` si no puede escribir el fichero. Si `config.json` → `eventos.activo` es
`false`, no escribe nada y sale con `0`.

**Prohibido en este fichero:** importar nada fuera de la biblioteca estándar,
leer variables de entorno, hacer peticiones de red. Todo eso llegará el día que
se conecte Langfuse, y llegará **aquí**.

### 10.3 `scripts/medir.py`

**Qué comprueba:** la longitud del capítulo, en la unidad de `config.json`.

**Uso:**

```powershell
python scripts/medir.py --capitulo 1
python scripts/medir.py --todos
```

**Cómo mide:**

- Descarta la primera línea si empieza por `#`, y todas las líneas vacías.
- Si `unidad` es `lineas`: cuenta las líneas restantes. Además comprueba que
  cada una termina en `.`, `?`, `!`, `…`, `"`, `»` o `)`. Las que no, se cuentan
  aparte como `lineas_sin_cierre`.
- Si `unidad` es `palabras`: cuenta los tokens de `nucleo.palabras()`.
- Calcula el rango admitido: `objetivo * (1 - tolerancia)` a
  `objetivo * (1 + tolerancia)`, redondeando hacia fuera. Con `tolerancia: 0.0`
  el rango es exacto.

**Devuelve:**

```json
{
  "script": "medir",
  "capitulo": 1,
  "unidad": "lineas",
  "objetivo": 4,
  "medido": 4,
  "minimo": 4,
  "maximo": 4,
  "lineas_sin_cierre": 0,
  "en_norma": true,
  "incidencias": []
}
```

Con `--todos`, devuelve `{"script": "medir", "capitulos": [ ... ], "fuera_de_norma": [3]}`.

**Códigos:** `0` en norma; `2` fuera de norma o con líneas sin cierre de frase
(es bloqueante: se arregla en segundos y no tiene sentido validar nada más).

### 10.4 `scripts/repeticion.py`

**Qué comprueba:** que el capítulo no recicle frases, imágenes, muletillas ni
estructuras. Detalle y ejemplos en la sección 12.

**Uso:**

```powershell
python scripts/repeticion.py --capitulo 2
python scripts/repeticion.py --global
```

**Qué mide (cinco comprobaciones):**

1. **Solape de n-gramas.** Genera los n-gramas de tamaño `validacion.ngrama`
   del capítulo, normalizados, y los compara con los de todos los capítulos
   anteriores. Métrica: fracción de n-gramas del capítulo que ya aparecían.
   Umbral: `max_solape_ngramas`.
2. **Frases prohibidas.** Busca cada cadena de `estado.frases_usadas`,
   normalizada, dentro del capítulo normalizado. Coincidencia literal.
3. **Muletillas.** Cuenta la frecuencia de cada palabra de contenido (palabras
   de 5 letras o más que no estén en la lista de vacías) y la normaliza por mil
   palabras. Umbral: `max_muletilla_por_mil`. Las palabras que aparecen en
   `## Motivos recurrentes` del canon quedan exentas.
4. **Tipo de apertura.** Clasifica el arranque del capítulo con reglas simples:
   empieza con comilla o raya de diálogo → `dialogo`; empieza con un nombre de
   `estado.entidades` → `accion`; en otro caso → `descripcion_ambiente`. Compara
   con `estado.aperturas` y avisa si el mismo tipo se supera
   `max_aperturas_del_mismo_tipo` veces.
5. **Primeras y últimas palabras.** Compara las 6 primeras y las 6 últimas
   palabras con las de los capítulos anteriores. Coincidencia de 4 o más en el
   mismo orden → aviso.

**Devuelve:**

```json
{
  "script": "repeticion",
  "capitulo": 2,
  "metricas": {
    "ngramas_total": 118,
    "ngramas_repetidos": 3,
    "solape": 0.0254,
    "umbral_solape": 0.02,
    "frases_recicladas": 1,
    "muletilla_max": { "palabra": "silencio", "por_mil": 5.1 },
    "tipo_apertura": "descripcion_ambiente"
  },
  "incidencias": [
    {
      "severidad": "mayor",
      "tipo": "frase_reciclada",
      "detalle": "con la cadencia exacta de un pulso",
      "ancla": "Volvió a llegar con la cadencia exacta de un pulso."
    },
    {
      "severidad": "mayor",
      "tipo": "solape_ngramas",
      "detalle": "solape 0.0254 supera el umbral 0.02",
      "ejemplos": ["la sala de rele olia a"]
    }
  ],
  "resumen": { "bloqueante": 0, "mayor": 2, "menor": 1 }
}
```

Con `--global`, recorre todos los capítulos y añade
`repeticiones_entre_capitulos`: los n-gramas que aparecen en dos o más
capítulos, con la lista de capítulos donde salen.

**Códigos:** `0` limpio; `1` hay mayores o menores. Este script nunca devuelve
bloqueantes: la repetición se corrige con parche, no tirando el capítulo.

### 10.5 `scripts/continuidad.py`

**Qué comprueba:** las contradicciones detectables mecánicamente. Detalle y
ejemplos en la sección 11.

**Uso:**

```powershell
python scripts/continuidad.py --capitulo 2
python scripts/continuidad.py --escaleta
python scripts/continuidad.py --global
```

**Modo `--capitulo NN` — siete comprobaciones:**

| # | Comprueba | Severidad si falla |
|---|---|---|
| 1 | Todos los `marcadores` de todos los beats del plan aparecen literalmente en el capítulo | **bloqueante** |
| 2 | Ningún término de `## Términos prohibidos` del canon aparece en el capítulo | **bloqueante** |
| 3 | El `dia` del plan no retrocede respecto al capítulo anterior, salvo `analepsis: true` | **bloqueante** |
| 4 | Ningún personaje con hecho vigente `estado_personaje` de valor muerto/ausente/desaparecido aparece nombrado | **mayor** |
| 5 | El nombre del POV del plan aparece en el capítulo | **mayor** |
| 6 | Los hilos de `cierra_hilos` están abiertos en el estado | **mayor** |
| 7 | Todo nombre propio del capítulo está en `estado.entidades` (nombre o alias) o en `## Personajes` del canon | **menor** |

Detección de nombres propios para la comprobación 7: palabra que empieza por
mayúscula y no está al principio de frase ni después de `.`, `?`, `!`, `"` o
raya de diálogo, y no está en la lista de palabras vacías capitalizadas.

**Modo `--escaleta` — cinco comprobaciones estructurales:**

| # | Comprueba | Severidad si falla |
|---|---|---|
| 1 | Hay exactamente `config.capitulos` capítulos, numerados de 1 a N sin huecos | **bloqueante** |
| 2 | Todo hilo de `cierra_hilos` tiene `abre_en` menor o igual a ese capítulo | **bloqueante** |
| 3 | Todo hilo declarado en `hilos` tiene `cierra_en` no nulo y menor o igual a N | **bloqueante** |
| 4 | `dia` es no decreciente salvo `analepsis: true` | **bloqueante** |
| 5 | Ningún capítulo tiene `informacion_nueva` vacía, ni menos de 2 beats, ni un beat sin marcadores | **mayor** |

**Modo `--global` — tres comprobaciones:**

| # | Comprueba | Severidad si falla |
|---|---|---|
| 1 | No queda ningún hilo con `estado: "abierto"` | **mayor** |
| 2 | Los capítulos en disco coinciden en número con la escaleta | **bloqueante** |
| 3 | No hay dos hechos con la misma `clave` y valores incompatibles sin que el posterior sea una evolución declarada | **mayor** |

**Devuelve:**

```json
{
  "script": "continuidad",
  "modo": "capitulo",
  "capitulo": 2,
  "comprobaciones": [
    { "id": "beats_cubiertos", "ok": false, "detalle": "falta el marcador 'voluntaria' del beat B2.2" },
    { "id": "terminos_prohibidos", "ok": true },
    { "id": "cronologia", "ok": true },
    { "id": "personajes_ausentes", "ok": true },
    { "id": "pov_presente", "ok": true },
    { "id": "hilos_cerrables", "ok": true },
    { "id": "entidades_no_registradas", "ok": false, "detalle": "Vera Lund no está registrada" }
  ],
  "incidencias": [
    {
      "severidad": "bloqueante",
      "tipo": "beat_no_cubierto",
      "detalle": "El beat B2.2 exige el marcador 'voluntaria' y no aparece en el texto."
    },
    {
      "severidad": "menor",
      "tipo": "entidad_no_registrada",
      "detalle": "Vera Lund aparece en el capítulo y no está en entidades ni en el canon."
    }
  ],
  "resumen": { "bloqueante": 1, "mayor": 0, "menor": 1 }
}
```

**Códigos:** `0`, `1` o `2` según la peor severidad.

### 10.6 `scripts/informes.py`

**Qué hace:** persiste en `novela/informes/` el resultado completo de una
validación. Es la **única** puerta de escritura de esa carpeta, igual que
`eventos.py` lo es de `events.jsonl`. Esquema en la sección 6.6.

**No calcula nada por su cuenta:** importa `medir`, `repeticion` y
`continuidad`, guarda lo que devuelven, y le añade las incidencias de juicio
que le pasa el orquestador (el `continuista` por capítulo, el `revisor-global`
al cerrar). Cada incidencia queda etiquetada con el validador que la produjo,
en un campo `origen`.

**Uso:**

```powershell
python scripts/informes.py --capitulo 2 --intento 3 --continuista informe.json
python scripts/informes.py --todos
python scripts/informes.py --global --revisor revision.json
```

**Argumentos:**

| Argumento | Qué hace |
|---|---|
| `--capitulo N` | Escribe `novela/informes/capitulo_NN.json` |
| `--todos` | Regenera el informe de todos los capítulos en disco |
| `--global` | Escribe `novela/informes/global.json` |
| `--continuista <fichero>` | JSON con la salida del subagente `continuista` |
| `--continuista-dir <carpeta>` | Con `--todos`: carpeta con `capitulo_NN.json` |
| `--revisor <fichero>` | Con `--global`: JSON con el informe del `revisor-global` |
| `--intento N` | Intento al que corresponde la validación |

**Regla:** las métricas se escriben **siempre**, dispare o no una incidencia.
Un capítulo limpio produce un informe con `incidencias: []` y el bloque
`metricas` completo. Sin esa serie de métricas limpias no hay forma de
calibrar los umbrales (sección 19.2, punto 2).

**Devuelve:** por stdout, un JSON corto con la ruta escrita y el recuento.
**Códigos:** `0` sin incidencias; `1` mayores o menores; `2` alguna
bloqueante; `3` error.

### 10.7 `scripts/ensamblar.py`

**Qué hace:** concatena los capítulos en `manuscrito.md`. Determinista, sin criterio.

**Uso:**

```powershell
python scripts/ensamblar.py
python scripts/ensamblar.py --salida entrega/novela.md
```

**Qué produce:**

1. Portada: título de la novela (del encabezado `# Canon — <titulo>` de
   `novela/canon.md`), nombre del proyecto y fecha.
2. Logline y sinopsis, si están en el canon.
3. Los capítulos en orden numérico, separados por una línea `---`, con su
   encabezado `# Capítulo NN — Título` tal como está en cada fichero.
4. Un pie con las cifras: número de capítulos y tamaño total en la unidad
   configurada.

**Devuelve:**

```json
{
  "script": "ensamblar",
  "salida": "manuscrito.md",
  "capitulos": 3,
  "unidad": "lineas",
  "total": 12,
  "faltantes": []
}
```

**Códigos:** `0` si están todos los capítulos de la escaleta; `2` si falta
alguno (lo dice en `faltantes` y **no** escribe el manuscrito).

### 10.8 `scripts/verificar.py`

**Qué comprueba:** que el sistema está bien construido. Se ejecuta una vez tras
la construcción, y cuando algo no cuadre.

**Uso:**

```powershell
python scripts/verificar.py
```

**Qué comprueba, en orden:**

1. La versión de Python es 3.12 o superior.
2. Existen los 28 ficheros del inventario de la sección 16.
3. **No** existen ficheros prohibidos: `requirements.txt`, `pyproject.toml`,
   `Makefile`, `.mcp.json`, carpetas `src/`, `tests/`, `.venv/`.
4. `config.json` es JSON válido y tiene todas las claves obligatorias con tipos
   correctos.
5. `novela/estado.json` es JSON válido y tiene las 9 claves de la semilla.
6. Cada fichero de `.claude/agents/` empieza con frontmatter YAML que incluye
   `name` y `description`, y el `name` coincide con el nombre del fichero.
7. Cada `SKILL.md` tiene frontmatter con `name` y `description`.
8. Cada fichero de `.claude/commands/` tiene frontmatter con `description`.
9. Ningún fichero de `scripts/` contiene `import requests`, `import httpx`,
   `anthropic`, `openai`, `API_KEY`, `os.environ`, `pip install`.
10. Cada script se puede importar y responde a `--help` sin error.
11. Git está disponible y la carpeta es un repositorio.

**Devuelve:** texto legible, no JSON. Una línea por comprobación, con `OK` o
`FALLO` y el detalle. Al final, un recuento y el veredicto.

```
[OK]    Python 3.12.10
[OK]    28/28 ficheros del inventario presentes
[OK]    0 ficheros prohibidos
[OK]    config.json valido
[OK]    novela/estado.json valido
[OK]    7/7 subagentes con frontmatter correcto
[OK]    3/3 skills con frontmatter correcto
[OK]    4/4 comandos con frontmatter correcto
[OK]    scripts sin dependencias externas ni claves
[OK]    7/7 scripts ejecutables
[FALLO] git: la carpeta no es un repositorio. Ejecuta: git init

11 comprobaciones, 10 correctas, 1 fallo.
VEREDICTO: REVISAR
```

**Códigos:** `0` si todo correcto; `1` si hay fallos.

---

## 11. Cómo se controla la coherencia

La coherencia se controla en cuatro capas. Cada una atrapa lo que la anterior no
puede ver. Ninguna sustituye a las demás.

```
Capa 1  Prevención     El escritor recibe el canon y los hechos ANTES de escribir
Capa 2  Estructura     continuidad.py --escaleta valida el plan ANTES de escribir nada
Capa 3  Mecánica       continuidad.py --capitulo NN: 7 comprobaciones literales
Capa 4  Juicio         el subagente continuista lee y entiende
Capa 5  Conjunto       continuidad.py --global y el revisor-global, al final
```

### 11.1 Capa 1 — Prevención

La forma más barata de corregir una contradicción es no cometerla. Por eso el
paso 1 de la skill `escribir-capitulo` entrega al escritor, antes de que escriba
una palabra: todos los hechos vigentes con su cita, los hilos abiertos, los
resúmenes anteriores, las últimas líneas literales del capítulo previo y las
reglas, límites y coste de la premisa especulativa.

**Qué previene:** que el capítulo 3 mate a alguien que ya estaba muerto, que un
personaje use una tecnología sin pagar su coste, que el texto empiece
repitiendo la imagen con la que acabó el anterior.

### 11.2 Capa 2 — Estructura, antes de escribir

`python scripts/continuidad.py --escaleta` se ejecuta antes de que exista un
solo capítulo. Detecta errores de plan que, si pasan, contaminan la novela entera.

**Ejemplo de lo que detecta:**

```json
{
  "severidad": "bloqueante",
  "tipo": "hilo_cerrado_sin_abrir",
  "detalle": "El capítulo 2 cierra el hilo T03, que abre en el capítulo 3."
}
```

```json
{
  "severidad": "bloqueante",
  "tipo": "cronologia_retrocede",
  "detalle": "El capítulo 3 ocurre el día 2 y el capítulo 2 el día 5, y no está marcado como analepsis."
}
```

Arreglar esto en la escaleta cuesta un minuto. Arreglarlo con tres capítulos ya
escritos cuesta reescribir tres capítulos.

### 11.3 Capa 3 — Comprobación mecánica del capítulo

`python scripts/continuidad.py --capitulo NN`. Siete comprobaciones literales,
sin interpretación. Estas son las que detecta, con ejemplo real:

**1. Beats no cubiertos (bloqueante).** El plan del capítulo 2 tiene el beat
`B2.2` con marcadores `["Nadia", "voluntaria"]`. El script busca ambas palabras
en el texto. Si "voluntaria" no aparece:

```json
{ "severidad": "bloqueante", "tipo": "beat_no_cubierto",
  "detalle": "El beat B2.2 exige el marcador 'voluntaria' y no aparece en el texto." }
```

**2. Términos prohibidos (bloqueante).** El canon veta `hiperespacio`. El
capítulo dice "un salto por el hiperespacio":

```json
{ "severidad": "bloqueante", "tipo": "termino_prohibido",
  "detalle": "'hiperespacio' está en Términos prohibidos del canon.",
  "ancla": "un salto por el hiperespacio" }
```

**3. Cronología (bloqueante).** El capítulo 3 declara `dia: 2` y el capítulo 2
declaraba `dia: 5`, sin `analepsis: true`.

**4. Personaje muerto o ausente que aparece (mayor).** El estado tiene el hecho
`H014: estado:Nadia Ferrán = muerta` desde el capítulo 2. El capítulo 3 nombra a
Nadia:

```json
{ "severidad": "mayor", "tipo": "personaje_no_disponible",
  "detalle": "Nadia Ferrán consta como muerta desde el capítulo 2 (hecho H014) y aparece nombrada en el capítulo 3.",
  "nota": "Puede ser legítimo si es un recuerdo o una mención. Lo confirma el continuista." }
```

Esta comprobación es deliberadamente tonta: solo busca el nombre. Genera falsos
positivos, y por eso es **mayor** y no bloqueante: señala dónde mirar, y el
continuista decide.

**5. POV ausente (mayor).** El plan dice POV de Irene Sabal y su nombre no
aparece en el capítulo. Casi siempre significa que el capítulo se ha escrito
desde otra mirada.

**6. Hilo cerrado que no estaba abierto (mayor).** El plan del capítulo 2 manda
cerrar `T02`, pero en `estado.hilos` ese hilo no está abierto. O el capítulo
anterior no lo abrió, o el archivista no lo registró.

**7. Entidad no registrada (menor).** Aparece "Vera Lund" y no está ni en
`estado.entidades` ni en `## Personajes` del canon. O es un personaje nuevo que
hay que registrar, o es un nombre inventado sobre la marcha que contradice el
canon.

### 11.4 Capa 4 — Juicio del continuista

Lo que ningún script ve. Cuatro ejemplos de lo que solo detecta leyendo:

**Violación de la regla especulativa.** El canon dice que abrir un par exige 40
minutos y un cerebro humano vivo. El capítulo escribe: *"Irene abrió un par
nuevo en cuarenta segundos y se fue a dormir."* Ningún término prohibido,
todos los marcadores presentes, longitud correcta. Y la novela está rota.

**Conocimiento imposible.** En el capítulo 2, Irene descubre a solas el coste de
abrir un par. En el capítulo 3, Tomás dice: *"Ya sabes lo que cuesta."* Nadie se
lo ha contado y no estaba delante. Hay que mostrarlo o cambiar la réplica.

**Personaje contra su carácter.** El canon dice que el miedo de Tomás es la
auditoría. En el capítulo 3 llama él mismo a la auditoría sin que nada haya
cambiado en escena.

**Beat mencionado pero no ocurrido.** El marcador "voluntaria" aparece, pero en
la frase *"nunca se ofrecería voluntaria"*. El script da la comprobación por
buena. El beat no ha ocurrido.

### 11.5 Capa 5 — Conjunto

Al final, `continuidad.py --global` comprueba que no quede ningún hilo abierto,
que los capítulos en disco coincidan con la escaleta y que no haya dos hechos
con la misma clave y valores incompatibles. El `revisor-global` lee el
manuscrito entero y busca lo que solo existe a escala de novela: un personaje
que desaparece a mitad, una promesa del capítulo 1 que el final no cumple.

### 11.6 Qué se hace con cada severidad

| Severidad | Acción | Se revalida |
|---|---|---|
| Bloqueante | El `escritor` reescribe el capítulo entero, con la lista de incidencias delante | Sí, desde el principio |
| Mayor | El `escritor` reescribe **solo** los párrafos anclados | Sí, obligatorio |
| Menor | Se anota en la respuesta al autor y se sigue | No |

Tras `max_reescrituras` intentos (3 por defecto), el sistema para y escala. No
sigue acumulando errores.

---

## 12. Cómo se controla la repetición

Todo el control de repetición es determinista y vive en `scripts/repeticion.py`.
Ningún juicio, ninguna lectura: cadenas, recuentos y umbrales. La memoria que lo
hace posible son dos listas de `novela/estado.json` que el archivista mantiene:
`frases_usadas` y `aperturas`.

### 12.1 Solape de n-gramas

**Cómo funciona.** Se normaliza el texto (minúsculas, sin tildes, sin
puntuación), se parte en palabras y se generan todas las secuencias de
`validacion.ngrama` palabras consecutivas (6 por defecto). Se hace lo mismo con
todos los capítulos anteriores. Se cuenta qué fracción de los n-gramas del
capítulo nuevo ya existía.

**Por qué 6.** Con 4 palabras saltan coincidencias inevitables del español
("no se lo que"). Con 8, se escapan las reformulaciones. Seis es el punto donde
una coincidencia casi siempre significa reciclaje.

**Ejemplo.** Capítulo 1: *"La sala de relé olía a plástico frío."* Capítulo 3:
*"La sala de relé olía a metal caliente."* Comparten el 6-grama
`la sala de rele olia a`:

```json
{ "severidad": "mayor", "tipo": "solape_ngramas",
  "detalle": "solape 0.0254 supera el umbral 0.02",
  "ejemplos": ["la sala de rele olia a"] }
```

**Umbral.** `max_solape_ngramas: 0.02`. Es decir: como mucho un 2 % de las
secuencias del capítulo pueden haber aparecido antes. Con capítulos de 4 líneas
el umbral es muy exigente y basta un solape para saltar; es lo que se quiere.

### 12.2 Frases ya usadas

**Cómo funciona.** El archivista guarda, en `frases_usadas`, las imágenes
memorables de cada capítulo, copiadas literalmente. El script normaliza cada
una y la busca dentro del capítulo normalizado. Coincidencia exacta de subcadena.

**Ejemplo.** Tras el capítulo 1, `frases_usadas` contiene
`"con la cadencia exacta de un pulso"`. El capítulo 3 escribe *"Volvió a llegar
con la cadencia exacta de un pulso."*:

```json
{ "severidad": "mayor", "tipo": "frase_reciclada",
  "detalle": "con la cadencia exacta de un pulso",
  "ancla": "Volvió a llegar con la cadencia exacta de un pulso." }
```

**Lo que no detecta.** La variante *"con la cadencia justa de un latido"*. Eso lo
ve el `revisor-global` al final. Es un límite conocido y aceptado: detectarlo
automáticamente exigiría embeddings, y los embeddings están prohibidos por diseño.

**Excepción.** Los motivos listados en `## Motivos recurrentes` del canon son
repetición deliberada. El archivista tiene instrucción de no registrarlos como
frases usadas.

### 12.3 Muletillas

**Cómo funciona.** Se cuenta la frecuencia de cada palabra de contenido
(5 letras o más, fuera de la lista de palabras vacías) y se normaliza por mil
palabras. Se compara con `max_muletilla_por_mil`.

**Ejemplo.** En un capítulo de 980 palabras, "silencio" aparece 5 veces: 5,1 por
mil, por encima del umbral de 3,0.

```json
{ "severidad": "menor", "tipo": "muletilla",
  "detalle": "'silencio' aparece 5 veces (5.1 por mil, umbral 3.0)" }
```

Es **menor** a propósito: en ciencia ficción hay términos del mundo que tienen
que repetirse. El estilista decide.

**Nota con `unidad: lineas` y objetivo 4.** Un capítulo de cuatro frases tiene
unas 60 palabras: la frecuencia por mil se dispara con dos repeticiones. El
script exige un mínimo de 200 palabras para evaluar muletillas; por debajo, la
comprobación se marca `no_aplica`. Con la configuración de partida, esta métrica
no se activa.

### 12.4 Tipo de apertura

**Cómo funciona.** El script clasifica el arranque del capítulo con tres reglas
simples: si empieza por comilla o raya de diálogo, es `dialogo`; si empieza por
un nombre de `estado.entidades`, es `accion`; en otro caso,
`descripcion_ambiente`. Compara con los tipos que ya constan en
`estado.aperturas` y avisa si se supera `max_aperturas_del_mismo_tipo`.

**Ejemplo.** Los capítulos 1 y 2 abren ambos con `descripcion_ambiente` y el
umbral es 1:

```json
{ "severidad": "mayor", "tipo": "apertura_repetida",
  "detalle": "El tipo 'descripcion_ambiente' ya se usó en el capítulo 1 y el máximo permitido es 1." }
```

Es la repetición estructural más fácil de cometer y la que más cansa al lector:
tres capítulos seguidos que empiezan describiendo una sala.

### 12.5 Primeras y últimas palabras

**Cómo funciona.** Compara las 6 primeras y las 6 últimas palabras del capítulo
con las de todos los anteriores. Cuatro o más coincidentes en el mismo orden
generan aviso.

**Ejemplo.** Capítulo 1 termina en "con la cadencia exacta de un pulso" y el
capítulo 2 también. Aviso **menor** de `cierre_repetido`.

### 12.6 Revisión global de repetición

`python scripts/repeticion.py --global` recorre la novela entera y añade la
lista de n-gramas que aparecen en dos o más capítulos, con los capítulos donde
salen. El `revisor-global` la lee y juzga cuáles duelen y cuáles son el estilo
del autor.

### 12.7 Resumen de umbrales

| Comprobación | Clave de configuración | Valor de partida | Severidad |
|---|---|---|---|
| Solape de n-gramas | `max_solape_ngramas` | 0.02 | mayor |
| Tamaño del n-grama | `ngrama` | 6 | — |
| Frase reciclada | (sin umbral: coincidencia literal) | — | mayor |
| Muletilla | `max_muletilla_por_mil` | 3.0 | menor |
| Apertura repetida | `max_aperturas_del_mismo_tipo` | 1 | mayor |
| Cierre repetido | (4 de 6 palabras) | — | menor |

### 12.8 Métricas de serie: monotonía, diversidad y cobertura

Las comprobaciones de 12.1 a 12.5 dicen si un capítulo pasa o no pasa. Estas
tres no juzgan nada: **no disparan incidencias nunca**. Existen para poder
comparar una tirada con la siguiente, y por eso viajan a Langfuse como scores
del span del capítulo aunque valgan lo mismo que ayer.

| Métrica | Dónde se calcula | Rango | Definición |
|---|---|---|---|
| `diversidad` | `repeticion.py` | 0..1, **más alto mejor** | N-gramas distintos del capítulo dividido entre el número de posiciones de n-grama. Un 1.0 significa que ningún n-grama se repite dentro del propio capítulo. |
| `monotonia` | `repeticion.py` | 0..1, **más alto peor** | Media aritmética de sus tres componentes. |
| `monotonia_apertura` | `repeticion.py` | 0..1 | Capítulos anteriores que abren con el mismo tipo (12.4), sobre el total de anteriores. |
| `monotonia_muletillas` | `repeticion.py` | 0..1 | `muletilla_max.por_mil` dividido entre `max_muletilla_por_mil`, recortado a 1.0. |
| `monotonia_reciclaje` | `repeticion.py` | 0..1 | Frases recicladas (12.2) entre líneas del capítulo, recortado a 1.0. |
| `cobertura_beats` | `continuidad.py` | 0..1 | Marcadores de beat presentes sobre marcadores exigidos por la escaleta. |

`cobertura_beats` **no sustituye** a la comprobación `beats_cubiertos`, que
sigue siendo booleana y bloqueante: un solo marcador ausente tumba el capítulo
aunque la cobertura sea 0.9. La fracción solo sirve para ver la tendencia.

Los denominadores pueden ser cero en un capítulo vacío o en el primero de la
novela. En ese caso `diversidad` vale 0.0, `monotonia_apertura` vale 0.0 y
`cobertura_beats` vale 1.0, que es lo que corresponde a "no hay nada que
incumplir".

---

## 13. El flujo completo de generación de una novela

De la premisa al manuscrito, con la configuración de partida: 3 capítulos de
4 líneas.

### Momento 0 — Preparación (tú, una vez)

```powershell
cd C:\Users\student\Documents\MyStory1
python scripts/verificar.py
```

Debe decir `VEREDICTO: CORRECTO`. Después edita `config.json` y escribe tu
premisa en la clave `premisa`.

### Fase 1 — Canon

**Tú:** `/nueva-novela`

**El sistema:**
1. Lee `config.json`. Si la premisa sigue siendo el marcador, para y te lo dice.
2. `eventos.py --evento fase_inicio --fase canon` → abre la tirada `20260917-1204`.
3. Invoca al subagente `arquitecto`, que escribe `novela/canon.md`.
4. Te muestra el resumen: logline, tema, personajes, y reglas, límites y coste.
5. **Espera tu aprobación.**

**Tú:** apruebas o pides cambios. Si pides cambios, vuelve al paso 3.

**El sistema:** `fase_fin --fase canon` + commit
`feat(canon): biblia narrativa de La deriva de Kalpa`.

### Fase 2 — Escaleta

**El sistema**, sin que tengas que lanzar nada más:
1. `fase_inicio --fase escaleta`.
2. Invoca al `escaletista`, que escribe `novela/escaleta.json`.
3. Ejecuta `continuidad.py --escaleta`. Si hay bloqueantes, se los devuelve al
   escaletista y repite.
4. Te muestra la tabla de los 3 capítulos.
5. **Espera tu aprobación.**

**El sistema:** `fase_fin --fase escaleta` + commit
`feat(escaleta): plan de 3 capitulos`.

### Fase 3 — Redacción (el bucle)

**Tú:** `/escribir` (o `/escribir todos`)

Para el capítulo 1:

| Paso | Quién | Qué pasa |
|---|---|---|
| 1 | Skill `escribir-capitulo` | `capitulo_inicio`. Reúne el contexto de 9 fuentes |
| 2 | Subagente `escritor` (modo borrador) | Escribe `novela/capitulos/capitulo-01.md`. Evento `borrador`, intento 1 |
| 3 | `medir.py --capitulo 1` | ¿4 líneas exactas, todas cerrando frase? |
| 4 | `repeticion.py --capitulo 1` | Con el capítulo 1 no hay nada con qué comparar: limpio |
| 5 | `continuidad.py --capitulo 1` | Marcadores, términos prohibidos, cronología, POV, hilos, entidades |
| 6 | Subagente `continuista` | Lee y busca contradicciones de sentido. Devuelve JSON |
| 7 | Skill `validar-capitulo` | Fusiona todo. Evento `validacion` con métricas y recuento |
| 8 | Skill `escribir-capitulo` | Decide: bloqueante → reescritura; mayor → parche y revalidar; solo menores → seguir |
| 9 | Subagente `estilista` | Pule la prosa sin tocar hechos ni beats |
| 10 | `medir.py --capitulo 1` | **Otra vez.** Comprobar que el pulido no cambió la longitud |
| 11 | `repeticion.py --capitulo 1` | Otra vez: el estilista pudo meter una frase ya usada |
| 12 | Subagente `archivista` | Actualiza `novela/estado.json`: hechos, hilos, entidades, resumen, últimas líneas, frases usadas, apertura y cierre |
| 13 | Skill `bitacora` | Evento `capitulo_fin` + commit `feat(cap-01): Silencio en la siete` + evento `commit` |

Capítulo 2: igual, pero ahora hay con qué comparar. Ejemplo de ciclo real:

```
borrador (intento 1)
  validacion -> {"bloqueante":1,"mayor":1,"menor":0}
     bloqueante: beat B2.2 sin cubrir, falta el marcador 'voluntaria'
  reescritura (intento 2)
  validacion -> {"bloqueante":0,"mayor":1,"menor":1}
     mayor: frase reciclada "con la cadencia exacta de un pulso"
  parche (intento 3)
  validacion -> {"bloqueante":0,"mayor":0,"menor":1}
     menor: entidad no registrada "Vera Lund"
  estilista -> medir -> 4 lineas, en norma
  archivista -> 3 hechos, 1 hilo abierto, 1 entidad nueva
  commit feat(cap-02): El coste declarado
```

Capítulo 3: igual. Al acabar, `fase_fin --fase redaccion`.

**Si un capítulo agota los 3 intentos:** el sistema para, registra `escalado`,
deja el borrador en disco, hace commit `wip(cap-02): bloqueado tras 3 intentos`
y te presenta las incidencias con tres opciones: relajar el plan, ajustar el
canon o aceptar el capítulo con la incidencia. **No decide por ti.**

### Fase 4 — Revisión global

**Tú:** `/entregar`

1. `fase_inicio --fase revision`.
2. `repeticion.py --global` y `continuidad.py --global`.
3. Subagente `revisor-global`: lee los 3 capítulos enteros y produce el informe.
4. Si `REQUIERE CORRECCIONES`: te lista los capítulos afectados y te pregunta si
   regenerarlos. Si dices que sí, aplica `escribir-capitulo` a cada uno en
   orden. Vuelve a revisar **una sola vez**; si sigue sin aprobarse, escala.
5. `fase_fin --fase revision` + commit.

### Fase 5 — Entrega

1. `fase_inicio --fase entrega`.
2. `python scripts/ensamblar.py` → `manuscrito.md`.
3. `fase_fin --fase entrega` + commit `feat(entrega): manuscrito.md`.
4. Te dice la ruta, el número de capítulos y el tamaño total. Si
   `push_automatico` es `false`, te recuerda `git push origin main`.

### Qué queda en el repositorio al final

```
manuscrito.md                      la novela
novela/canon.md                    el mundo
novela/escaleta.json               el plan
novela/estado.json                 la memoria: hechos, hilos, entidades, frases
novela/capitulos/capitulo-0N.md    cada capítulo
novela/events.jsonl                todo lo que pasó, una línea por suceso
```

Y en el historial de Git, un commit por hito, en orden.

### Si se corta la conversación a mitad

No pasa nada. Abres Claude Code, lanzas `/estado`, te dice por dónde va leyendo
los ficheros, y lanzas `/escribir` para seguir. Lo único que se pierde es el
contador de intentos del capítulo en curso, que vuelve a empezar en 1.

---

## 14. Registro de eventos: `events.jsonl` y Langfuse

### 14.1 Qué se traza y qué no

**Corrección respecto a la v1 de este documento.** La v1 afirmaba que no había
tokens ni coste que instrumentar, porque ningún script llama a una API de
modelo. Lo primero sigue siendo cierto: no hay ninguna llamada a una API en
`scripts/`. Lo segundo era falso. Claude Code invoca a los subagentes con la
herramienta Task y **deja el desglose completo en sus propios transcripts**, en
`~/.claude/projects/<proyecto>/<sesión>/subagents/`: un `.meta.json` con el
`agentType` (el rol: escritor, continuista, estilista…) y un `.jsonl` con el
modelo y los cuatro contadores de token de cada llamada.

Eso convierte en instrumentable lo que se daba por perdido. Lo que sigue sin
existir es `total_cost_usd`: los transcripts no lo guardan. Por eso el sistema
**no calcula el coste**; envía modelo y tokens y deja que Langfuse aplique su
tarifa. Ver 14.6.

Lo que se traza:

- Qué fases se han ejecutado y cuándo.
- Cuántos borradores, reescrituras y parches ha hecho falta por capítulo.
- Qué ha devuelto cada validación: métricas y recuento de incidencias por severidad.
- Qué capítulos han escalado al autor.
- Qué commits se han hecho.
- Qué invocaciones a modelo ha habido, con su rol, su modelo y su desglose de
  tokens: entrada, salida, creación de caché y lectura de caché.

Eso responde a las preguntas útiles: ¿qué capítulo se atasca?, ¿qué validación
salta más?, ¿el solape de n-gramas sube conforme avanza la novela?, ¿bajar el
umbral de repetición dispara las reescrituras?, ¿qué parte del gasto es prosa
nueva y qué parte es contexto recargado?

### 14.2 Esquema de cada línea

`novela/events.jsonl`: un objeto JSON por línea, sin coma final, UTF-8,
`ensure_ascii=False`. Campos:

| Campo | Tipo | Siempre | Qué es |
|---|---|---|---|
| `ts` | string | Sí | Marca de tiempo ISO-8601 en UTC con `Z`: `2026-09-17T12:04:11.482Z` |
| `tirada` | string | Sí | Identificador de la ejecución completa: `AAAAMMDD-HHMM` |
| `evento` | string | Sí | Uno de los 11 tipos de la tabla 14.3 |
| `fase` | string\|null | No | `canon`, `escaleta`, `redaccion`, `revision`, `entrega` |
| `capitulo` | int\|null | No | Número de capítulo |
| `intento` | int\|null | No | Número de intento dentro del capítulo, empezando en 1 |
| `datos` | object | Sí (puede ir vacío) | Carga útil específica del evento |
| `esquema` | int | Sí | Versión del esquema. Vale `1` |

Ejemplo de fichero real:

```json
{"ts":"2026-09-17T12:04:11.482Z","tirada":"20260917-1204","evento":"fase_inicio","fase":"canon","capitulo":null,"intento":null,"datos":{},"esquema":1}
{"ts":"2026-09-17T12:07:52.010Z","tirada":"20260917-1204","evento":"fase_fin","fase":"canon","capitulo":null,"intento":null,"datos":{"personajes":3},"esquema":1}
{"ts":"2026-09-17T12:12:03.771Z","tirada":"20260917-1204","evento":"capitulo_inicio","fase":"redaccion","capitulo":2,"intento":null,"datos":{},"esquema":1}
{"ts":"2026-09-17T12:12:44.118Z","tirada":"20260917-1204","evento":"borrador","fase":"redaccion","capitulo":2,"intento":1,"datos":{},"esquema":1}
{"ts":"2026-09-17T12:13:20.664Z","tirada":"20260917-1204","evento":"validacion","fase":"redaccion","capitulo":2,"intento":1,"datos":{"metricas":{"unidad":"lineas","medido":4,"objetivo":4,"en_norma":true,"solape":0.0254,"umbral_solape":0.02,"frases_recicladas":1},"resumen":{"bloqueante":1,"mayor":1,"menor":0}},"esquema":1}
{"ts":"2026-09-17T12:14:02.339Z","tirada":"20260917-1204","evento":"reescritura","fase":"redaccion","capitulo":2,"intento":2,"datos":{"incidencias":["beat_no_cubierto"]},"esquema":1}
{"ts":"2026-09-17T12:16:10.901Z","tirada":"20260917-1204","evento":"capitulo_fin","fase":"redaccion","capitulo":2,"intento":3,"datos":{"hechos_nuevos":3,"hilos_abiertos":2},"esquema":1}
{"ts":"2026-09-17T12:16:15.220Z","tirada":"20260917-1204","evento":"commit","fase":"redaccion","capitulo":2,"intento":null,"datos":{"sha":"a1f3c02","mensaje":"feat(cap-02): El coste declarado"},"esquema":1}
```

### 14.3 Los once tipos de evento

| `evento` | Cuándo | `datos` contiene |
|---|---|---|
| `fase_inicio` | Al empezar una fase | `{}` |
| `fase_fin` | Al terminarla | Resumen: `{"personajes":3}`, `{"capitulos":3}` |
| `capitulo_inicio` | Al empezar un capítulo | `{}` |
| `borrador` | Al generar un borrador | `{}` |
| `validacion` | Al terminar una validación | `{"metricas":{...},"resumen":{"bloqueante":N,"mayor":N,"menor":N}}` |
| `reescritura` | Al reescribir entero | `{"incidencias":["tipo1","tipo2"]}` |
| `parche` | Al parchear párrafos | `{"incidencias":["tipo1"]}` |
| `capitulo_fin` | Al cerrar un capítulo | `{"hechos_nuevos":N,"hilos_abiertos":N}` |
| `escalado` | Al agotar los intentos | `{"motivo":"...","incidencias":[...]}` |
| `commit` | Al hacer commit | `{"sha":"...","mensaje":"..."}` |
| `invocacion` | Al terminar una llamada a modelo | `{"rol":"escritor","model":"...","session_id":"...","usage":{...}}`. Ver 14.6 |

### 14.4 Cómo está conectado Langfuse

**Transporte.** Dos endpoints, por una razón que conviene no olvidar:

| Qué | Dónde | Por qué |
|---|---|---|
| Trazas y observaciones | `POST /api/public/otel/v1/traces` | OTLP/HTTP en JSON, con la cabecera `x-langfuse-ingestion-version: 4`. Es el camino que la documentación señala para instrumentación propia |
| Scores | `POST /api/public/ingestion`, eventos `score-create` | OTLP no transporta scores |

La API de ingesta v3 **se apaga en Langfuse Cloud el 16 de noviembre de 2026**
para todo excepto los scores, que se siguen aceptando por ella. Los despliegues
autoalojados no se ven afectados por esa fecha hasta que activen el modo
v4-only. Además, marcar el tipo de una observación por esa vía exigía
`observation-create`, marcada como deprecada dentro de la propia API: las dos
razones apuntaban a OTLP.

**Correspondencia de conceptos:**

| Concepto de este sistema | Observación de Langfuse | Cómo se deriva |
|---|---|---|
| Una tirada de novela | Span **raíz**, que lleva los atributos de la traza | En OTLP no hay objeto traza: `langfuse.trace.*` van en la raíz |
| Una fase | `span` hijo de la raíz | Del par `fase_inicio` / `fase_fin` |
| Un capítulo | `span` hijo de la fase `redaccion` | Del par `capitulo_inicio` / `capitulo_fin` |
| Un intento | `span` hijo del capítulo | `borrador`/`reescritura`/`parche`, cerrado por su `validacion` |
| **Una ejecución de subagente** | **`agent`** hijo del intento | Evento `invocacion` agrupado por `datos.id_agente` |
| Una llamada al modelo | `generation` hija del `agent` | Evento `invocacion` |
| Una validación | **`evaluator`** | Evento `validacion` |
| Un commit | `event` colgando de la raíz | Evento `commit` |
| Cada métrica de validación | **Score** del span del capítulo | Todo `datos.metricas.*`, dispare o no incidencia. El `timestamp` del score es el del evento que lo produjo, nunca el reloj del envío: un score se identifica por `id` + `name` + **fecha**, así que con el reloj el mismo score reenviado al día siguiente entraría como uno nuevo |
| Recuento por severidad | Score numérico | `datos.resumen.*` |
| Intentos, palabras, líneas | Score numérico | Del `capitulo_fin` |
| Un escalado | `event` con `level: ERROR` y score | Evento `escalado` |

Que cada subagente sea de tipo `agent` y no un span genérico no es cosmético:
es lo que le da nodo propio en el grafo de agentes y permite ver de quién son
las llamadas sin abrir cada una.

**Atributos usados**, todos del espacio `langfuse.*`: `trace.name`,
`trace.input`, `trace.output`, `trace.tags`, `trace.metadata.*`, `session.id`,
`environment`, `observation.type`, `observation.input`, `observation.output`,
`observation.metadata.*`, `observation.level`, `observation.status_message`,
`observation.model.name`, `observation.usage_details`,
`observation.cost_details`.

**Dónde se toca el código.** En un solo sitio: la función `registrar()` de
`scripts/eventos.py`, que llama a `observabilidad.exportar(ev)` después de
escribir la línea en disco. Ninguna skill, ningún subagente y ningún otro
script participan.

```python
def registrar(evento, fase=None, capitulo=None, intento=None, datos=None) -> dict:
    cfg = nucleo.cargar_config()
    ev = _construir(cfg, evento, fase, capitulo, intento, datos)
    _escribir_linea(cfg, ev)          # fuente de verdad: siempre, y primero
    observabilidad.exportar(ev)       # destino adicional: nunca obligatorio
    return ev
```

**Por qué los identificadores son deterministas.** Cada evento del pipeline es
una invocación separada de `python scripts/eventos.py`: un proceso nuevo, sin
memoria del anterior. El id de traza (32 hex) y el de cada span (16 hex) se
derivan por hash de una clave legible (`nov-MyStory1-20260918-0056--cap-02--int-3`),
de modo que el mismo capítulo produce el mismo span desde cualquier proceso.

Es también la razón de no usar el SDK oficial: no permite fijar el id de un
span, así que con un proceso por evento el árbol no anidaría.

**La ingesta por OTLP no hace upsert.** A diferencia de la API v3, reenviar un
span con el mismo `spanId` **crea otra observación** en lugar de actualizarla.
La documentación de Langfuse lo dice sin rodeos: traza y observación son
*inmutables*, v4 no deduplica en la lectura, y reingerir el mismo id duplica el
registro, infla las métricas de coste y descuadra los paneles. Solo los
**scores** se pueden sobrescribir, y únicamente si coinciden `id`, `name` y la
**fecha** del `timestamp`.

De ahí las tres reglas que gobiernan el envío:

1. **Solo viaja lo que ya ha terminado.** Un tramo abierto —una fase empezada,
   un capítulo en curso, un intento sin validar— no se manda todavía: se manda
   en el envío del evento que lo cierra, que es cuando se conoce su duración
   real. Esto es lo que hace que el panel siga la novela **en vivo**, capítulo
   a capítulo, en lugar de llenarse de spans de duración cero que después ya no
   se podrían corregir. El span raíz es el último en salir, con el `fase_fin`
   de `entrega`.
2. **Se reconstruye el árbol entero en cada envío** y se filtra por el registro
   local de span ids ya enviados, `novela/langfuse-enviados.txt`. Como el
   inicio de una fase y su fin ocurren en procesos distintos, el exportador
   relee el histórico completo; el filtro evita que cada span se multiplique
   por el número de eventos de la tirada.
3. **Si falta el registro local, se le pregunta al panel.** Ese fichero está en
   `.gitignore` y no viaja con el repositorio, así que se pierde con cualquier
   clon nuevo; y sin él, todo se reenvía y todo se duplica. Antes de mandar
   nada, `sembrar_enviados()` consulta
   `GET /api/public/v2/observations?traceId=…` y apunta como enviado lo que el
   panel ya tiene. `retroalimentar.py` lo hace siempre y **se niega a enviar**
   si no ha podido preguntar; el camino en vivo lo hace solo cuando el
   registro no existe, para no meter una consulta por evento.

**Atributos de traza repetidos en cada span.** En v4 la traza es solo un grupo
de observaciones: lo que vive únicamente en la raíz no se puede filtrar ni
agregar desde sus hijos. Y como la raíz es lo último que se cierra, sin esto la
tirada en curso aparecería sin nombre y sin entorno hasta el final. Por eso
`trace.name`, `session.id`, `environment` y `trace.metadata.tirada` se copian a
**todos** los spans. Las `trace.tags`, que se calculan de agregados que cambian
durante la tirada, se quedan solo en la raíz: repetirlas daría un valor
distinto en cada span.

**Garantías, en orden de importancia:**

1. `events.jsonl` se escribe **primero y siempre**. Langfuse nunca lo sustituye
   ni lo desactiva.
2. `exportar()` no lanza excepciones jamás. Sin red, con las claves mal o con
   el servidor caído, devuelve `False`, anota el fallo en `novela/langfuse.log`
   y la generación sigue. El timeout es de 8 segundos.
3. Las **claves** salen solo de variables de entorno y no se escriben en
   ningún sitio. El log registra el tipo de error y, si es HTTP, el código;
   nunca la URL, ni las cabeceras, ni el cuerpo. El **host** de destino es la
   única excepción, y es deliberada: aparece en la línea de arranque, porque
   sin saber contra qué servidor se traza no se puede diagnosticar nada.
6. **Faltar la URL no apaga nada.** `LANGFUSE_BASE_URL` es opcional: si no
   está, se usa `https://us.cloud.langfuse.com`, la región del proyecto. Solo
   la ausencia de una **clave** desactiva la exportación. La regla anterior
   —apagarse si faltaba cualquiera de las tres— dejaba la observabilidad muerta
   en silencio por una variable que el código sabe deducir.
7. **El estado se anuncia al arrancar**, no al terminar. En `fase_inicio` y en
   `capitulo_inicio`, `eventos.registrar()` llama a `observabilidad.anunciar()`,
   que escribe una línea por **stderr** —stdout es JSON y tiene quien lo
   parsee— diciendo si se está trazando y contra qué host, o qué clave falta,
   por su nombre y sin su valor. `observabilidad.py --linea` da la misma línea
   a mano.
4. El vaciado va en un `atexit`: sin él se perderían las últimas trazas, porque
   el proceso de un evento dura milisegundos.
5. Los envíos se trocean por **tamaño real del JSON**, no por número de
   elementos: la API rechaza cuerpos por encima de 1 MB.

**Configuración**, en `config.json`:

```json
"observabilidad": {
  "langfuse": { "activo": null, "enviar_texto": true, "entorno": "default" }
}
```

`activo: null` significa "enciéndete si están las dos claves".
`enviar_texto: false` manda métricas y metadatos pero ningún texto. `entorno`
separa las tiradas de prueba de las buenas en el panel.

**Sin dependencias.** OTLP se habla en JSON con `urllib`, así que no hacen
falta ni el SDK ni protobuf. `requirements-opcional.txt` existe para quien
quiera el SDK oficial, y el sistema no lo usa.

### 14.5 El evento `invocacion` y el coste

Es el único evento que produce una `generation`, y el único que el pipeline no
genera por sí mismo: sale de los transcripts de Claude Code, que son el único
sitio donde existe el desglose de tokens por llamada.

Se cosecha en **dos** momentos, con el mismo código:

- **En vivo**, en cada envío. `observabilidad._generaciones()` lee los
  transcripts de los subagentes **en primer plano** —los que por definición han
  terminado cuando el orquestador recupera el control y vuelve a ejecutar
  `eventos.py`— y los sitúa en el punto del pipeline donde ocurrieron. Sin
  esto la traza en vivo no tendría ni una sola `generation` y el panel daría
  coste cero hasta el final de la novela.
- **A posteriori**, con `retroalimentar.py`, que además recoge lo que quedó
  después del último evento de la tirada.

Estas invocaciones **no se escriben en `events.jsonl`**: el registro local
cuenta lo que hizo el pipeline, y los transcripts son una fuente externa. Solo
viajan a Langfuse.

**Solo cuentan los subagentes.** Las llamadas del propio orquestador no se
suben. Es una decisión deliberada, y tiene consecuencias: el coste que muestra
el panel es el del trabajo creativo (arquitecto, escaletista, escritor,
continuista, estilista, archivista, revisor-global), no el gasto total de la
tirada, que es bastante mayor.

El día que exista un envoltorio que invoque al modelo y devuelva su JSON, ese
envoltorio solo tiene que llamar a `eventos.registrar()` con este evento y la
traza se completa sola.

Forma de `datos`:

```json
{
  "rol": "escritor",
  "model": "claude-opus-5",
  "session_id": "feb6c0bb-5078-424c-98d0-6331eed39fa9",
  "id_generacion": "req_011Cf9xir3Dn9s4VkioR7HfH",
  "usage": {
    "input_tokens": 2,
    "output_tokens": 147,
    "cache_creation_input_tokens": 8868,
    "cache_read_input_tokens": 31764
  },
  "total_cost_usd": null
}
```

Los cuatro contadores viajan **separados** en el atributo
`langfuse.observation.usage_details`. Es lo que permite
distinguir el trabajo real del contexto que se recarga: en una tirada normal
los tokens de lectura de caché son mayoría abrumadora, porque son el canon y el
estado releídos una y otra vez.

**El coste no se calcula aquí.** No hay tabla de tarifas en el repositorio. Se
envían el modelo y el desglose, y Langfuse aplica su propia tarifa, que
distingue caché barata de tokens nuevos. Si `total_cost_usd` viene informado,
se manda en `langfuse.observation.cost_details` y manda sobre el cálculo.

`datos.id_agente` agrupa las llamadas de una misma ejecución de subagente bajo
una sola observación de tipo `agent`. En la retroalimentación sale del
`toolUseId` que Claude Code guarda en el `.meta.json` del subagente.

### 14.6 Dónde encajaría un servidor MCP

**Hoy no se crea `.mcp.json`.** El sistema no depende de ningún servidor MCP y
funciona entero sin uno. Pero el diseño deja tres puertas abiertas:

1. **Langfuse por MCP.** De las dos alternativas que contemplaba la v1 se ha
   tomado la segunda: el script es la única puerta y él hace el envío, sin
   `.mcp.json`. Si algún día conviene pasar al servidor MCP, el cambio sigue
   siendo local, porque el punto de registro es único: bastaría sustituir la
   llamada a `observabilidad.exportar()` dentro de `registrar()`.
2. **Consulta de métricas.** Un servidor MCP de Langfuse permitiría que el
   comando `/estado` mostrara métricas históricas además del estado en disco.
   Sería un párrafo más en `.claude/commands/estado.md`.
3. **Fuentes documentales.** Si en el futuro el `arquitecto` necesitara consultar
   material de referencia (una wiki, un gestor documental), entraría como
   servidor MCP declarado en `.mcp.json` y como una herramienta más en el
   frontmatter de ese subagente.

**Lo que no se debe hacer para "dejarlo preparado":** crear un `.mcp.json` vacío,
escribir un cliente MCP propio, o añadir una capa de abstracción "por si acaso".
La puerta está abierta porque el registro de eventos tiene un único punto de
entrada, no porque haya código esperando.

---

## 15. Cómo y cuándo se hacen los commits a GitHub

El repositorio no es solo el sitio donde vive el código: es el historial de la
escritura. Un commit por hito permite volver al capítulo 2 antes del parche y
ver qué cambió.

### 15.1 Cuándo

| Hito | Mensaje (título) | Qué entra |
|---|---|---|
| Construcción del sistema | `chore: andamiaje del generador de novelas` | Los 27 ficheros |
| Canon aprobado | `feat(canon): biblia narrativa de <titulo>` | `novela/canon.md` |
| Escaleta aprobada | `feat(escaleta): plan de N capitulos` | `novela/escaleta.json` |
| Capítulo cerrado y archivado | `feat(cap-NN): <titulo del capitulo>` | El capítulo + `novela/estado.json` + `events.jsonl` |
| Capítulo bloqueado tras agotar intentos | `wip(cap-NN): bloqueado tras N intentos` | El borrador + `events.jsonl` |
| Revisión global terminada | `chore(revision): informe global` | `events.jsonl` y los capítulos corregidos |
| Manuscrito ensamblado | `feat(entrega): manuscrito.md` | `manuscrito.md` |
| Cambio de configuración hecho por ti | `chore(config): <que has cambiado>` | `config.json` |

### 15.2 Cómo

Siempre desde la raíz, en PowerShell:

```powershell
git add -A
git commit -m "feat(cap-01): Silencio en la siete" -m "3 hechos, 1 hilo abierto. 1 intento. Sin incidencias mayores."
```

`git add -A` es deliberado: el capítulo y el estado que ese capítulo modificó
tienen que viajar en el **mismo** commit. Si se separan, el repositorio puede
quedar en un punto donde el estado dice que hay 2 capítulos y en disco hay 1.

El cuerpo del commit (segundo `-m`) resume siempre lo mismo: cuántos hechos,
hilos y entidades ha añadido el archivista, cuántos intentos hicieron falta, y
qué incidencias menores quedan anotadas.

Después, el evento:

```powershell
python scripts/eventos.py --evento commit --capitulo 1 --datos "{\"sha\":\"a1f3c02\",\"mensaje\":\"feat(cap-01): Silencio en la siete\"}"
```

### 15.3 Push

Con la configuración de partida (`git.push_automatico: false`), el push lo
lanzas tú cuando quieras:

```powershell
git push origin main
```

Si pones `push_automatico` a `true`, el sistema hace `git push origin <rama>`
después de cada commit.

### 15.4 Reglas

- Un commit por capítulo. Nunca se agrupan varios capítulos.
- Nunca se usa `--no-verify`, `--force` ni `--amend`.
- Nunca se comitea un capítulo que no haya pasado por el archivista: el estado
  y el texto van juntos o no van.
- Si `git commit` dice que no hay nada que comitear, no es un error: se informa y
  se sigue.
- El sistema no crea ramas ni pull requests. Todo va a `main` salvo que tú
  cambies `git.rama`.
- El sistema no borra ni reescribe historia.

### 15.5 Si el repositorio todavía no existe en local

```powershell
cd C:\Users\student\Documents\MyStory1
git init
git branch -M main
git remote add origin <URL_DE_TU_REPO>
git add -A
git commit -m "chore: andamiaje del generador de novelas"
git push -u origin main
```

---

## 16. Inventario cerrado de entregables

39 ficheros. Claude Code crea **exactamente estos** y ninguno más. Si al terminar
hay 41, algo se ha inventado; si hay 37, algo falta.

Los ocho últimos (32 a 39) llegaron con la interfaz web, que el autor pidió
después de la primera construcción. Hasta entonces el inventario eran 31.

### 16.1 Raíz

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 1 | `SPEC.md` | Este documento, con las 19 secciones numeradas |
| 2 | `README.md` | Contenido literal de la sección 5.3. Menciona los 4 comandos |
| 3 | `CLAUDE.md` | Contenido literal de la sección 5.2. 8 invariantes y 6 prohibiciones |
| 4 | `config.json` | JSON válido con el contenido literal de la sección 4.1. `capitulos: 3`, `unidad: "lineas"`, `objetivo: 4` |
| 5 | `.gitignore` | Sección 5.1, más `novela/langfuse.log`. **No** ignora `novela/` |
| 29 | `requirements-opcional.txt` | Declara `langfuse` como dependencia **opcional**. El núcleo no la necesita: el exportador usa `urllib`. No se instala sola |
| 39 | `.vscode/settings.json` | Solo le dice al editor dónde buscar: `extraPaths` con `scripts` y `server`, y el intérprete del entorno virtual. No cambia cómo se ejecuta nada |

### 16.2 Subagentes (`.claude/agents/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 6 | `arquitecto.md` | Frontmatter con `name: arquitecto`, `description`, `tools`, `model`. Prompt de la sección 7.1. Exige los 10 encabezados del canon y la autocomprobación de 7 puntos |
| 7 | `escaletista.md` | `name: escaletista`. Prompt de la sección 7.2. Exige `marcadores` en cada beat y ejecutar `continuidad.py --escaleta` |
| 8 | `escritor.md` | `name: escritor`. Prompt de la sección 7.3. Define los tres modos: `borrador`, `reescritura`, `parche` |
| 9 | `continuista.md` | `name: continuista`. Prompt de la sección 7.4. Define las tres severidades y el formato JSON de salida con `ancla` literal |
| 10 | `estilista.md` | `name: estilista`. Prompt de la sección 7.5. Lista explícita de lo que NO puede cambiar y obligación de volver a medir |
| 11 | `archivista.md` | `name: archivista`. Prompt de la sección 7.6. Dice que es el único que escribe el estado y exige cita literal en cada hecho |
| 12 | `revisor-global.md` | `name: revisor-global`. Prompt de la sección 7.7. Produce los 7 apartados del informe |

Criterio común: el `name` del frontmatter coincide con el nombre del fichero sin
extensión. Ninguno tiene permiso de escritura sobre `config.json`. Solo
`archivista` menciona escribir `novela/estado.json`.

### 16.3 Skills (`.claude/skills/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 13 | `escribir-capitulo/SKILL.md` | Frontmatter con `name` y `description`. Los 8 pasos de la sección 8.1, con el contador de intentos y la escalada en el paso 7 |
| 14 | `validar-capitulo/SKILL.md` | Los 4 pasos en orden, la tabla de traducción de severidades y la fusión de incidencias |
| 15 | `bitacora/SKILL.md` | Parte A con la tabla de los 10 eventos y parte B con la tabla de mensajes de commit |

### 16.4 Comandos (`.claude/commands/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 16 | `nueva-novela.md` | Frontmatter con `description` y `argument-hint`. Fases 1 y 2, con dos puntos de aprobación del autor |
| 17 | `escribir.md` | Resuelve el capítulo pendiente desde `estado.json`. Soporta `todos`. Nunca salta un capítulo |
| 18 | `estado.md` | Solo lectura. No invoca subagentes. Produce el informe de la sección 9.3 |
| 19 | `entregar.md` | Fases 4 y 5. Reintenta la revisión **una sola vez**. No genera PDF |

### 16.5 Scripts (`scripts/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 20 | `nucleo.py` | Las 16 funciones de la sección 10.1. No se ejecuta solo. Solo biblioteca estándar |
| 21 | `eventos.py` | La función `registrar()` con el comentario `PUNTO DE EXTENSIÓN`. Resuelve la tirada leyendo la última línea. Respeta `eventos.activo` |
| 22 | `medir.py` | `--capitulo` y `--todos`. Lee la unidad de `config.json`. Comprueba cierre de frase en modo `lineas`. Sale con `2` si está fuera de norma |
| 23 | `repeticion.py` | `--capitulo` y `--global`. Las 5 comprobaciones de la sección 12. Nunca devuelve bloqueantes. Muletillas marcadas `no_aplica` por debajo de 200 palabras |
| 24 | `continuidad.py` | `--capitulo`, `--escaleta` y `--global`. Las 7 + 5 + 3 comprobaciones de la sección 10.5 |
| 25 | `informes.py` | ÚNICA puerta de escritura de `novela/informes/`. `--capitulo`, `--todos` y `--global`. Guarda las métricas SIEMPRE, haya incidencias o no. Ver sección 6.7 |
| 26 | `ensamblar.py` | Produce `manuscrito.md`. No escribe nada si falta algún capítulo |
| 27 | `verificar.py` | Las 11 comprobaciones de la sección 10.8. Salida legible, no JSON |
| 30 | `observabilidad.py` | Exportador a Langfuse (sección 14.4). Único módulo que lee variables de entorno y habla por red. No lanza excepciones jamás. `--estado` diagnostica sin mostrar valores |
| 31 | `retroalimentar.py` | Sube tiradas ya ejecutadas leyendo `events.jsonl`, los informes y los transcripts de Claude Code. `--simular` no envía nada. No escribe en `events.jsonl` |
| 32 | `intentos.py` | Congela texto e informe de cada intento en `novela/intentos/`, enganchado en `eventos.registrar()`. Calcula el diff al leer, nunca lo guarda |

Criterio común a los scripts: `python scripts/<nombre>.py --help` funciona; no
aparecen en ellos las cadenas `requests`, `httpx`, `anthropic`, `openai`,
`API_KEY` ni `pip install`; todos abren ficheros con `encoding="utf-8"`.

**Única excepción:** `observabilidad.py` puede usar `os.environ`, porque las
credenciales de Langfuse solo pueden venir de ahí. `verificar.py` lo recoge en
su lista `EXENCIONES` y le sigue aplicando todos los demás patrones: si alguna
vez contiene una clave literal o una dependencia externa, la comprobación 9
salta igual. Ningún otro script puede leer el entorno.

### 16.6 La interfaz web (`server/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 33 | `runner.py` | **Único** fichero que sabe invocar Claude Code. `--output-format json` y el coste leído de la respuesta; `--restricted` siempre; nunca `--bare`; sesiones encadenadas con `--resume`. `--append-system-prompt` va el último argumento. `--probar` hace tres invocaciones reales |
| 34 | `orquestador.py` | Recorre las cinco fases sin conversación. Importa los scripts de `scripts/`, no los reimplementa. Capítulos en orden, nunca en paralelo. Registra el coste como evento `invocacion`. Máximo de llamadas al modelo comprobado antes de cada invocación |
| 35 | `api.py` | Los siete endpoints. Sin estado en memoria: todo se relee de disco. Una generación a la vez, en segundo plano |
| 36 | `static/index.html` | Las cuatro pantallas. Sin `<script src>` externo |
| 37 | `static/estilos.css` | Sobrio y legible. Sin fuentes ni librerías de fuera |
| 38 | `static/app.js` | JavaScript plano, sin compilar. Nada de jerga en lo que se pinta |

Criterio común: `server/` tiene exactamente **dos** dependencias, `fastapi` y
`uvicorn`, instaladas en `.venv`. `scripts/` sigue sin ninguna. Se arranca con
un solo comando, `.\.venv\Scripts\python.exe -m uvicorn server.api:app
--port 8000`, que ya dice en qué dirección abrirlo.

**Los dos caminos conviven.** El conversacional —los comandos de
`.claude/commands/`— sigue intacto: el orquestador no lo sustituye, hace el
mismo recorrido sin que haya que dirigirlo. Lo que ambos comparten vive en
`scripts/` y en `.claude/agents/`, y por eso el historial de intentos se guarda
igual se genere por donde se genere.

### 16.7 Estado inicial (`novela/`)

| # | Fichero | Criterio de aceptación |
|---|---|---|
| 28 | `estado.json` | La semilla literal de la sección 6.3: 9 claves, listas vacías, `tirada: null`, `capitulos_escritos: 0` |

Las carpetas `novela/capitulos/` y `novela/informes/` se crean vacías.
`novela/canon.md`, `novela/escaleta.json`, `novela/events.jsonl`,
`novela/informes/*.json` y `manuscrito.md` **no** se crean en la construcción:
los genera el sistema al ejecutarse.

### 16.8 Ficheros que NO deben existir

`.mcp.json`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Makefile`,
`Dockerfile`, `docker-compose.yml`, `.env`, `.env.example`, `tests/`, `src/`,
`package.json`, y cualquier fichero que Claude Code considere "útil"
y no esté en las tablas 16.1 a 16.7.

`.venv/` **sí** existe desde que hay interfaz web, y está ignorada por git.
Antes estaba prohibida, y lo estaba con razón: mientras todo fue biblioteca
estándar, un entorno virtual solo podía significar que alguien había metido una
dependencia por la puerta de atrás. `fastapi` y `uvicorn` son las dos únicas
que hay, solo las usa `server/`, y la comprobación 9 de `verificar.py` sigue
vigilando que `scripts/` no tenga ninguna.

`novela/intentos/`, `novela/.detener` y `novela/.generando` los crea el sistema
al ejecutarse. Los dos últimos son señales de un momento y están ignorados por
git; la carpeta de intentos es parte del registro de la novela y sí se
versiona.

`requirements-opcional.txt` **sí** existe y no contradice la regla: lo prohibido
es `requirements.txt`, que implicaría dependencias obligatorias. Las de este
fichero no se instalan nunca solas y el sistema funciona entero sin ellas.

`novela/langfuse.log` lo crea el sistema al ejecutarse si algún envío falla, y
está ignorado por git: es diagnóstico, no fuente de verdad.

**Recuento:** 7 + 7 + 3 + 4 + 11 + 6 + 1 = **39**.

---

## 17. Cómo verifico que está bien construido

### 17.1 Qué ejecuto yo y cuándo

| Cuándo | Qué escribo | Dónde | Qué debo ver |
|---|---|---|---|
| Una vez, al principio | `git init` y `git remote add origin <URL>` | PowerShell | Sin errores |
| Tras la construcción | `python scripts/verificar.py` | PowerShell | `VEREDICTO: CORRECTO` |
| Antes de empezar la novela | Editar `config.json` → `premisa` | VS Code | Tu premisa, no el marcador |
| Al empezar la novela | `/nueva-novela` | Claude Code | El canon resumido y una pregunta de aprobación |
| Tras aprobar el canon | (nada: sigue solo) | — | La tabla de capítulos y otra pregunta |
| Escribir un capítulo | `/escribir` | Claude Code | El capítulo cerrado, con su commit |
| Escribir todos de golpe | `/escribir todos` | Claude Code | Los N capítulos, parando si alguno escala |
| En cualquier momento | `/estado` | Claude Code | El informe de la sección 9.3 |
| Al acabar | `/entregar` | Claude Code | El informe global y `manuscrito.md` |
| Cuando quieras subirlo | `git push origin main` | PowerShell | Sin errores |
| Ver el historial | `git log --oneline` | PowerShell | Un commit por hito |
| Ver las trazas | `Get-Content novela\events.jsonl -Tail 20` | PowerShell | Las últimas 20 líneas de eventos |

### 17.2 Verificación de la construcción

Ejecuta, en este orden, desde `C:\Users\student\Documents\MyStory1`:

**1. La autocomprobación completa**

```powershell
python scripts/verificar.py
```

Debes ver 11 líneas `[OK]` y `VEREDICTO: CORRECTO`. Si alguna dice `[FALLO]`, el
propio mensaje dice qué falta.

**2. El recuento de ficheros**

```powershell
(Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.git\\' }).Count
```

Debe dar **27**. Si da más, mira qué sobra:

```powershell
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.git\\' } | Select-Object -ExpandProperty FullName
```

**3. Que no hay dependencias ni claves**

```powershell
Get-ChildItem scripts\*.py | Select-String -Pattern "requests|httpx|anthropic|openai|API_KEY|os\.environ|pip install"
```

No debe devolver nada.

**4. Que no hay ficheros prohibidos**

```powershell
Get-ChildItem -Recurse -Include requirements.txt,pyproject.toml,Makefile,Dockerfile,.mcp.json,.env
```

No debe devolver nada.

**5. Que los scripts arrancan**

```powershell
python scripts/medir.py --help
python scripts/repeticion.py --help
python scripts/continuidad.py --help
python scripts/ensamblar.py --help
python scripts/eventos.py --help
```

Cada uno debe imprimir su ayuda y salir sin traza de error.

**6. Que la configuración se lee**

```powershell
python -c "import json;c=json.load(open('config.json',encoding='utf-8'));print(c['capitulos'],c['longitud']['unidad'],c['longitud']['objetivo'])"
```

Debe imprimir: `3 lineas 4`

**7. Que el estado es válido**

```powershell
python -c "import json;e=json.load(open('novela/estado.json',encoding='utf-8'));print(sorted(e.keys()))"
```

Debe imprimir las 9 claves: `['aperturas', 'capitulos_escritos', 'cierres', 'entidades', 'estado'...]`
— concretamente `aperturas`, `capitulos_escritos`, `cierres`, `entidades`,
`frases_usadas`, `hechos`, `hilos`, `resumenes`, `tirada`.

**8. Que el registro de eventos funciona**

```powershell
python scripts/eventos.py --evento fase_inicio --fase canon
Get-Content novela\events.jsonl
```

Debe aparecer una línea JSON con `ts`, `tirada`, `evento`, `esquema`. Bórrala
después si quieres empezar limpio:

```powershell
Remove-Item novela\events.jsonl
```

**9. Que los subagentes están registrados**

En Claude Code, escribe `/agents`. Deben aparecer los siete: `arquitecto`,
`escaletista`, `escritor`, `continuista`, `estilista`, `archivista`,
`revisor-global`.

**10. La prueba de fuego**

Escribe una premisa en `config.json` y lanza `/nueva-novela`. Si al cabo de unos
minutos tienes un `novela/canon.md` con los 10 encabezados y una escaleta de 3
capítulos que pasa `continuidad.py --escaleta`, el sistema está bien construido.

Luego `/escribir todos`. Con 3 capítulos de 4 líneas, el ciclo completo debería
terminar en minutos y dejarte un `manuscrito.md` de 12 líneas de novela. Eso es
lo que la configuración de partida está pensada para demostrar: que el pipeline
entero funciona, antes de gastar tiempo en capítulos largos.

---

## 18. Antipatrones: qué NO debe hacer Claude Code al construirlo

Cada uno de estos puntos es un error que ya se ha cometido en el intento
anterior o que es fácil cometer. Si Claude Code hace alguno, el resultado está mal.

### 18.1 Arquitectura

1. **No crear una capa de abstracción "por si acaso".** Nada de `BaseAgent`,
   `AgentRegistry`, `PipelineStage`, `StateManager`, `EventBus`. Los agentes son
   ficheros Markdown.
2. **No implementar los agentes como clases Python.** Si aparece un
   `class Escritor:` en algún sitio, el diseño se ha ignorado por completo.
3. **No crear un "orquestador" en Python.** El orquestador es Claude Code. Un
   `main.py` que encadene fases es exactamente lo que este diseño evita.
4. **No dividir un script de 150 líneas en cinco módulos.** `repeticion.py` es un
   fichero, no un paquete.
5. **No crear `src/`, `lib/`, `core/`, `domain/`, `infrastructure/`.** Hay dos
   carpetas: `scripts/` y `novela/`, más `.claude/`.
6. **No añadir un esquema JSON, un validador de esquemas ni tipos Pydantic.**
   `nucleo.py` comprueba las cuatro claves que importan y ya.

### 18.2 Dependencias y entorno

7. **No ejecutar `pip install`.** Ni una vez, ni "solo para probar".
8. **No crear `requirements.txt`, `pyproject.toml` ni entorno virtual.**
9. **No importar nada fuera de la biblioteca estándar.** Ni `pyyaml` para leer
   frontmatter: si hace falta, se lee con `re`.
10. **No usar `os.environ` para nada.** Ninguna configuración viene del entorno.
11. **No crear un `.env` ni un `.env.example`.** No hay secretos que gestionar.

### 18.3 Windows y comandos

12. **No escribir comandos que solo funcionen en bash**: `rm -rf`, `test -f`,
    `&&` encadenando en PowerShell 5.1, `export VAR=x`, rutas `.venv/bin/python`.
13. **No usar `make`.** No hay Makefile.
14. **No asumir que `python3` existe en Windows.** El comando es `python`.
15. **No usar rutas absolutas dentro de los scripts.** Se resuelven desde
    `Path(__file__).resolve().parent.parent`.
16. **No abrir ficheros sin `encoding="utf-8"`.** En Windows el valor por defecto
    no es UTF-8 y los acentos se rompen.

### 18.4 Alcance

17. **No crear ficheros que no estén en el inventario de la sección 16.** Ni un
    `CONTRIBUTING.md`, ni un `docs/`, ni un `examples/`, ni un `.editorconfig`.
18. **No generar PDF.** No es parte de la entrega.
19. **No escribir tests unitarios ni una carpeta `tests/`.** La verificación es
    `verificar.py` y ejecutar el sistema.
20. **No crear un proveedor de modelo falso para tests.** Está prohibido
    explícitamente.
21. **No escribir la novela de ejemplo.** La construcción crea el sistema, no
    contenido. `novela/canon.md` y `novela/escaleta.json` no se crean en la
    construcción.

### 18.5 Lógica del sistema

22. **No escribir Python que intente juzgar prosa.** Nada de "detectar si el
    diálogo suena natural" con expresiones regulares. Si necesita criterio, es
    un subagente.
23. **No dar por supuesto que la unidad es palabras.** Ni una constante
    `WORDS_PER_CHAPTER`. Todo sale de `config.json`.
24. **No permitir que ningún componente salvo el archivista escriba
    `novela/estado.json`.** Ni "solo para actualizar el contador".
25. **No saltarse la revalidación después de un parche.**
26. **No saltarse la medición de longitud después del estilista.**
27. **No dejar que el sistema decida solo cuando agota los intentos.** Se para y
    escala. Aceptar un capítulo roto "para no bloquear" es el peor fallo posible.
28. **No escribir en `events.jsonl` desde ningún sitio que no sea
    `scripts/eventos.py`.** Ni desde otro script, ni con un `Add-Content`.
29. **No añadir tokens, coste o latencia al registro de eventos.** No existen.
30. **No escribir los capítulos fuera de orden**, aunque parezca más rápido.

### 18.6 Documentación

31. **No sustituir el contenido literal por una descripción.** Donde el SPEC da
    el texto de un fichero, se copia ese texto.
32. **No hacer preguntas durante la construcción.** Donde haya ambigüedad, se
    elige lo más simple y se anota en el resumen final.

---

## 19. Decisiones que he tomado por ti y puntos a revisar más adelante

### 19.1 Decisiones tomadas

Donde el encargo dejaba margen, he elegido la opción más simple. Estas son las
elecciones, para que sepas qué puedes cambiar sin romper nada.

1. **Reescritor y parcheador no son subagentes propios.** Son los modos
   `reescritura` y `parche` del subagente `escritor`. Mismo oficio, distinta
   entrada. Ahorra dos ficheros y evita que tres prompts casi idénticos se
   desincronicen.
2. **El validador de biblia no existe como pieza separada.** Es la lista de
   autocomprobación dentro del prompt del `arquitecto`, más tu aprobación. Un
   agente extra para revisar un documento que vas a leer entero no se paga.
3. **El validador de escaleta es un script, no un agente.** Lo que hay que
   comprobar en una escaleta (hilos que se cierran antes de abrirse, días que
   retroceden, capítulos sin información nueva) es estructural y determinista.
4. **El constructor de contexto es un paso de una skill, no un script.** Es leer
   ficheros en un orden fijo. Un script que devolviera un bloque de texto
   gigante para pasárselo a un agente no aporta nada.
5. **Todo el estado del mundo en un solo `estado.json`.** Hechos, hilos,
   entidades, resúmenes, frases usadas, aperturas y cierres. Podrían ser siete
   ficheros; serían siete oportunidades de desincronización.
6. **Los hechos usan una `clave` en formato `sujeto:atributo`.** Es lo que hace
   que dos hechos contradictorios sean detectables mecánicamente en la revisión
   global. Sin clave, el registro es solo una lista de frases.
7. **Los beats llevan `marcadores` literales.** Es la forma de comprobar la
   cobertura de beats sin un modelo. Es imperfecta (detecta la palabra, no el
   suceso) y por eso el `continuista` la complementa.
8. **La comprobación de personajes muertos es deliberadamente tonta** y de
   severidad `mayor`, no bloqueante: busca el nombre y avisa. Produce falsos
   positivos con los recuerdos y las menciones. Es intencionado: prefiero un
   aviso de más que una contradicción de menos.
9. **`tolerancia: 0.0` por defecto.** Con capítulos de 4 líneas, cualquier
   tolerancia fraccionaria redondearía a lo mismo. Al pasar a palabras,
   0.15 es un valor razonable.
10. **Las muletillas no se evalúan por debajo de 200 palabras.** Con 60 palabras,
    cualquier palabra repetida dos veces dispara la métrica. Con la configuración
    de partida esa comprobación sale como `no_aplica`.
11. **Códigos de salida uniformes en todos los scripts** (0 limpio, 1 avisos,
    2 bloqueante, 3 error). Permite que una skill decida sin leer el JSON.
12. **La tirada se deduce del propio `events.jsonl`**, no se pasa a mano. Menos
    estado que arrastrar en la conversación.
13. **`git.push_automatico: false`.** Prefiero que el push sea una decisión tuya.
14. **`git add -A` en cada commit.** El capítulo y el estado que modificó viajan
    juntos, siempre.
15. **No se crea `.mcp.json`.** Un fichero vacío que nadie usa es ruido. La
    puerta está abierta porque el registro tiene un punto único de entrada, no
    porque haya un hueco reservado.
16. **No hay PDF.** `manuscrito.md` es la entrega.
17. **No hay tests.** `verificar.py` y ejecutar el sistema con 3 capítulos de
    4 líneas es la verificación.
18. **El `revisor-global` reintenta una sola vez.** Un bucle de revisión sin
    límite es una forma elegante de no terminar nunca.
19. **La configuración de partida (3 capítulos de 4 líneas) es un modo de
    prueba**, no una novela. Está pensada para que puedas recorrer el pipeline
    entero en minutos y ver que funciona antes de invertir en capítulos largos.

### 19.2 Puntos a revisar más adelante

Ninguno bloquea la v1. Los dejo anotados para cuando el sistema ya funcione.

1. **Detección de repetición semántica.** Hoy solo se detecta el reciclaje
   literal: "la cadencia exacta de un pulso" repetida se pilla, "la cadencia
   justa de un latido" no. Detectarlo automáticamente exigiría embeddings, que
   están prohibidos por diseño. De momento lo cubre el `revisor-global`.
   Revísalo si al leer notas que la novela se repite y los scripts no dicen nada.
2. **Los umbrales de repetición están sin calibrar.** `0.02` de solape y `6` de
   n-grama son cifras razonables, no medidas. Cuando tengas tres o cuatro
   novelas hechas, mira `events.jsonl` y ajústalos: si las reescrituras por
   repetición son constantes, el umbral es demasiado duro.
3. **El contador de intentos no sobrevive a un corte de conversación.** Si se
   corta a mitad del capítulo 2 en el intento 2, al retomar empieza en 1.
   Persistirlo obligaría a un fichero de estado efímero. Si te ocurre a menudo,
   se resuelve añadiendo `intento_actual` a `estado.json`.
4. **La detección de nombres propios dará falsos positivos** al principio de
   frase y con nombres compuestos. Es de severidad `menor` a propósito. Si
   molesta, la lista de palabras vacías capitalizadas de `continuidad.py` es el
   sitio donde se afina.
5. **Novelas largas y el tamaño del contexto.** Con 20 capítulos,
   `estado.json` crece y pasárselo entero al escritor deja de ser gratis. La
   solución, cuando llegue, es filtrar: pasar los hechos de los últimos 5
   capítulos más los marcados como permanentes. Hoy, con 3 capítulos, filtrar
   sería complicar sin motivo.
6. **El `continuista` y el `escritor` pueden entrar en desacuerdo.** Si el
   continuista marca como bloqueante algo que el escritor considera correcto, se
   agotan los intentos y el sistema escala. Es el comportamiento deseado, pero si
   pasa a menudo el problema suele estar en el canon: una regla imposible de
   cumplir.
7. **Langfuse.** Cuando llegue, la decisión pendiente es si el envío lo hace
   `scripts/eventos.py` (dependencia opcional) o Claude Code por MCP. Las dos
   funcionan; la primera es más simple, la segunda evita cualquier dependencia.
   Ver sección 14.4 y 14.5.
8. **Multilingüe.** Las listas de palabras vacías y la detección de cierre de
   frase de `medir.py` están pensadas para español. `config.idioma` existe pero
   hoy no cambia el comportamiento de ningún script.
9. **Aprobación del canon y la escaleta.** Hoy es conversacional: el sistema
   pregunta y tú contestas. No queda registrado en ningún fichero que el canon
   está aprobado. Si quisieras un congelado explícito, bastaría con una clave
   `aprobado: true` en un futuro `estado.json`. No la he añadido porque el
   commit del canon ya hace de marca.
10. **Ilustraciones, portada, exportación a EPUB.** Fuera de alcance. Si algún
    día se añaden, van como un script más en `scripts/`, nunca como una fase del
    pipeline.

---

*Fin del SPEC. 19 secciones, 27 ficheros, cero dependencias.*
