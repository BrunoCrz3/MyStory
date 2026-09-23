# MyStory — generador de novelas cortas de ciencia ficción

Sistema de escritura asistida que funciona dentro de Claude Code en VS Code.
Sin claves de API y sin base de datos.

Hay **dos formas de usarlo**, y las dos valen:

- **Hablando con Claude Code**, con los cuatro comandos de abajo. Es como
  nació y sigue intacto.
- **Desde la web**, escribiendo la premisa en un formulario y dándole a un
  botón. Sirve para enseñárselo a alguien que no programa.

## La interfaz web

Un solo comando, desde la raíz del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.api:app --port 8000
```

Al arrancar escribe la dirección en la que abrirlo, que será
**http://127.0.0.1:8000**. Se para con Ctrl+C.

Cuatro pantallas:

| Pantalla | Para qué |
|---|---|
| **Nueva novela** | Escribes de qué va, cuántos capítulos y cómo de largos, y le das a generar. |
| **Cómo va** | En qué paso está, qué se ha detectado, cuántas veces ha habido que reescribir y cuánto lleva gastado. Con botón de detener. |
| **Leer** | El manuscrito con formato, capítulo a capítulo, con los personajes y los cabos sueltos al lado. Junto a cada capítulo, cómo se llegó a él. |
| **Cuánto ha costado** | El gasto total y el desglose por capítulo y por oficio. |

La generación corre por detrás: puedes cerrar la pestaña y el trabajo sigue.
Solo se genera una novela a la vez, y **se detiene sola** al llegar al máximo
de llamadas al modelo de `config.json` → `servidor.max_invocaciones`, que de
fábrica son 120. No es un presupuesto: es el freno que impide que un reintento
se repita sin fin. El coste se sigue midiendo y se ve en la pantalla de cuentas,
pero no detiene nada.

Empezar una novela nueva **archiva la anterior** en `archivo/<nombre>/` antes de
vaciar el sitio, así que no se pierde nada.

## Los cuatro comandos

| Comando | Cuándo |
|---|---|
| `/nueva-novela` | Una vez, al empezar. Crea el canon y la escaleta. |
| `/escribir` | Escribe el siguiente capítulo pendiente. Repítelo hasta acabar. |
| `/estado` | En cualquier momento. Dice por dónde va la novela. |
| `/entregar` | Al final. Revisión global y `manuscrito.md`. |

## Antes de empezar

Edita `config.json`: pon tu premisa y el número de capítulos. Si usas la web,
eso mismo lo rellena el formulario.

## Cómo está hecho

Lee `SPEC.md`, sección 1: "Cómo funciona esto".

---

# Qué se ve en Langfuse

El sistema puede enviar a Langfuse todo lo que hace, para que puedas responder
a la pregunta que de verdad importa: **¿esta tirada ha salido mejor que la
anterior?**

`novela/events.jsonl` sigue siendo la fuente de verdad y nunca se apaga.
Langfuse es un destino añadido. Si se cae, si no hay red o si faltan las
claves, la novela se genera igual: el fallo se anota en `novela/langfuse.log`
y el proceso continúa.

**Cómo viaja.** Las trazas y observaciones van por **OpenTelemetry** a
`/api/public/otel/v1/traces`, en OTLP/HTTP con JSON. Los scores van aparte,
por `/api/public/ingestion`. Están separados por una razón concreta: la API de
ingesta se apaga en Langfuse Cloud el **16 de noviembre de 2026** para todo
menos los scores, que se siguen aceptando por ahí. OTLP es el camino que la
documentación señala para instrumentación propia como esta.

## Cómo se enciende

Dos variables de entorno del usuario en Windows, y una tercera opcional:

| Variable | Qué es | ¿Obligatoria? |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | Clave pública del proyecto en Langfuse | Sí |
| `LANGFUSE_SECRET_KEY` | Clave secreta del proyecto | Sí |
| `LANGFUSE_BASE_URL` | URL de tu instancia | No: por defecto `https://us.cloud.langfuse.com` |

**Solo las claves apagan la exportación.** Que falte la URL no la apaga nunca:
se usa la nube de EE. UU., que es donde vive el proyecto. Esto no es un detalle
menor: antes, una URL ausente dejaba la observabilidad muerta en silencio y no
te enterabas hasta el final de la novela.

No hay `.env` y no hay claves en ningún fichero del repositorio. Para ver si
está listo, sin que se muestre ningún valor de clave:

```powershell
python scripts/observabilidad.py --estado   # el detalle, en JSON
python scripts/observabilidad.py --linea    # una linea legible
```

Dice qué claves faltan **por su nombre**, nunca su valor.

Y no hace falta que te acuerdes de mirar: **al arrancar cada generación** —en
cada `fase_inicio` y en cada `capitulo_inicio`— el pipeline escribe por
`stderr` una línea como esta:

```
[langfuse] activo -> us.cloud.langfuse.com (por defecto), entorno 'default', texto si
```

o, si no se está trazando:

```
[langfuse] INACTIVO: falta LANGFUSE_SECRET_KEY en el entorno. No se exporta nada; events.jsonl sigue registrandolo todo.
```

Va por `stderr` porque la salida normal de los scripts es JSON y tiene quien la
parsee.

En `config.json`:

```json
"observabilidad": {
  "langfuse": {
    "activo": null,
    "enviar_texto": true,
    "entorno": "default"
  }
}
```

- `activo`: `null` significa "enciéndete si están las tres variables". Ponlo a
  `false` para apagarlo aunque estén, o a `true` para dejar constancia de que
  lo quieres encendido.
- `enviar_texto`: con `false` viajan las métricas y los metadatos, pero **no**
  el texto de la prosa ni el de los prompts. Sirve para medir sin publicar el
  contenido.
- `entorno`: separa las tiradas de prueba de las buenas. Ponlo a `production`
  cuando escribas en serio y a `development` mientras trasteas; en el panel se
  filtran por separado y no se mezclan las estadísticas.

## La forma del panel

Lo que verás no es una lista plana de llamadas, sino el flujo de la novela:

```
TRAZA  MyStory1                          una por tirada
 ├── [span]  canon
 │    └── [agent] arquitecto             el subagente, como nodo propio
 │           └── 8 generation            sus llamadas al modelo
 ├── [span]  escaleta
 │    └── [agent] escaletista
 ├── [span]  redaccion
 │    ├── [span] capitulo 01             aquí cuelgan los scores
 │    │    ├── [span] intento 1 (borrador)
 │    │    │    ├── [agent] escritor
 │    │    │    ├── [agent] continuista
 │    │    │    └── [evaluator] validacion
 │    │    └── [span] intento 2 (parche)
 │    │         ├── [agent] estilista
 │    │         └── [agent] archivista
 │    ├── [span] capitulo 02
 │    └── [span] capitulo 03
 ├── [event] commit
 ├── [span]  revision
 └── [span]  ensamblado
```

**Cada subagente es una observación de tipo `agent`**, no un span genérico. Eso
le da nodo propio en el grafo de agentes de Langfuse y permite ver de quién
son las llamadas sin abrir cada una. Las validaciones son de tipo `evaluator`,
porque eso es lo que hacen: juzgar la calidad de un capítulo.

**Cómo se lee de un vistazo.** Un capítulo con tres intentos necesitó dos
correcciones; uno con un solo intento salió a la primera. Es la señal más
rápida de si el canon y la escaleta están bien puestos.

Todas las trazas comparten el mismo `session_id` (el nombre del proyecto), así
que varias tiradas de la misma premisa quedan agrupadas y se pueden comparar
una contra otra.

## Lo que lleva cada generación

Una generación es una llamada al modelo. Su nombre es el rol del subagente que
la hizo: `escritor`, `continuista`, `estilista`, `archivista`, `arquitecto`,
`escaletista` o `revisor-global`.

| Campo | Para qué sirve |
|---|---|
| Modelo | Qué modelo la atendió |
| Tokens de entrada | Contexto nuevo que ha habido que leer |
| Tokens de salida | Lo que el modelo escribió |
| Tokens de creación de caché | Contexto que se ha guardado para reutilizar |
| Tokens de lectura de caché | Contexto reutilizado, mucho más barato |
| Metadatos | Capítulo, intento, rol, `session_id`, y si usó o creó caché |

**Los cuatro tipos de token van por separado a propósito.** Es lo que permite
ver qué parte del gasto es trabajo real y qué parte es contexto que se recarga.
En una tirada normal los tokens de lectura de caché son, con diferencia, los
más numerosos: es el canon y el estado releídos una y otra vez, no prosa nueva.

**Sobre el coste.** Los tokens se leen de la invocación, nunca se estiman.
El coste lo calcula Langfuse aplicando su tarifa al modelo y a ese desglose,
así que una llamada con la caché caliente aparece como una fracción de la
primera. Si algún día una invocación devuelve su propio `total_cost_usd`, ese
valor manda sobre el cálculo.

## Los scores: lo que sirve para comparar tiradas

Cuelgan del span de cada capítulo y se guardan **siempre**, dispare o no una
incidencia. Una métrica limpia también es información.

| Score | Rango | Cómo se lee |
|---|---|---|
| `solape` | 0..1 | Fracción de n-gramas que ya aparecían en capítulos anteriores. Si sube según avanza la novela, el modelo se está repitiendo. |
| `diversidad` | 0..1 | N-gramas distintos sobre el total. **Más alto es mejor.** Si baja, la prosa da vueltas sobre sí misma. |
| `monotonia` | 0..1 | **Más alto es peor.** Media de sus tres componentes. |
| `monotonia_apertura` | 0..1 | Proporción de capítulos anteriores que empiezan igual (diálogo, acción, ambiente). |
| `monotonia_muletillas` | 0..1 | Cuánto se acerca la palabra más repetida a su umbral. |
| `monotonia_reciclaje` | 0..1 | Frases ya usadas que vuelven a aparecer. |
| `cobertura_beats` | 0..1 | Fracción de los beats de la escaleta que el capítulo cubre. Si no es 1, el capítulo se ha dejado algo del plan. |
| `frases_recicladas` | entero | Frases repetidas de un capítulo anterior. |
| `muletilla_por_mil` | por mil | Frecuencia de la palabra más repetida. |
| `incidencias_bloqueante` | entero | Si no es 0, el capítulo no debería haberse cerrado. |
| `incidencias_mayor` | entero | Lo que obliga a parchear. |
| `incidencias_menor` | entero | Ruido tolerable; solo preocupa la tendencia. |
| `intentos` | entero | **El score más útil.** Cuántas pasadas necesitó el capítulo. |
| `palabras`, `lineas` | entero | Tamaño del capítulo final. |

**Cómo usarlos.** Cambia un umbral en `config.json`, lanza otra tirada y
compara: si `intentos` sube y `monotonia` no baja, el umbral nuevo solo está
generando trabajo. Si `diversidad` sube sin que suban los intentos, ha
merecido la pena.

## Lo que lleva la traza de la novela

- **Entrada**: la premisa, el número de capítulos y la longitud configurada.
- **Salida**: el manuscrito final, o el primer capítulo si es muy largo.
- **Metadatos**: configuración efectiva, coste total, duración total y número
  total de reescrituras.
- **Etiquetas** para filtrar: perfil de umbrales (`umbrales:ngrama6-solape0.02-…`),
  versión del prompt del escritor (`escritor:9477c04e`, que cambia solo si
  editas `.claude/agents/escritor.md`), tirada y modelos usados.

La etiqueta del prompt del escritor es la que permite responder "¿mejoró la
prosa porque cambié el prompt, o porque tuve suerte?".

## Subir tiradas ya generadas

Los capítulos escritos antes de conectar Langfuse no se pierden:

```powershell
python scripts/retroalimentar.py --simular   # enseña qué subiría, sin subir
python scripts/retroalimentar.py             # lo sube
```

Lee `events.jsonl`, recalcula las métricas actuales de los capítulos ya
escritos (para que tengan también los scores añadidos después) y saca las
generaciones de los transcripts de Claude Code, que es el único sitio donde
está el desglose de tokens por llamada.

**No es idempotente por sí solo.** La ingesta por OpenTelemetry **no
deduplica**: reenviar un span crea otra observación en el panel. Por eso el
sistema lleva un registro local de lo ya enviado en
`novela/langfuse-enviados.txt`, y el script omite lo que ya viajó. Si borras
ese fichero, o usas `--reenviar-todo`, duplicarás lo que ya estuviera arriba.

Para rehacer una traza desde cero: bórrala primero en la interfaz de Langfuse,
quita sus identificadores del registro local y vuelve a lanzarlo.

No escribe en `events.jsonl`.

## Dependencias

Para Langfuse, ninguna. El envío usa `urllib` de la biblioteca estándar, y OTLP
se habla en JSON, así que no hace falta ni el SDK ni protobuf.
`requirements-opcional.txt` solo sirve si quieres el SDK oficial para consultar
el panel desde Python.

Las únicas dependencias del proyecto son las dos del servidor web, `fastapi` y
`uvicorn`, instaladas en `.venv`. Los scripts de `scripts/` siguen sin ninguna,
y `verificar.py` lo comprueba en cada pasada.

El SDK no se usa para exportar por un motivo técnico: no permite fijar el
identificador de un span, y aquí cada evento del pipeline es un proceso
distinto. Sin identificadores deterministas, el árbol no anidaría.
