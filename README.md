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

---

# Qué se ve en Langfuse

El sistema puede enviar a Langfuse todo lo que hace, para que puedas responder
a la pregunta que de verdad importa: **¿esta tirada ha salido mejor que la
anterior?**

`novela/events.jsonl` sigue siendo la fuente de verdad y nunca se apaga.
Langfuse es un destino añadido. Si se cae, si no hay red o si faltan las
claves, la novela se genera igual: el fallo se anota en `novela/langfuse.log`
y el proceso continúa.

## Cómo se enciende

Tres variables de entorno del usuario en Windows:

| Variable | Qué es |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Clave pública del proyecto en Langfuse |
| `LANGFUSE_SECRET_KEY` | Clave secreta del proyecto |
| `LANGFUSE_BASE_URL` | URL de tu instancia, por ejemplo la de la nube europea |

No hay `.env` y no hay claves en ningún fichero del repositorio. Para ver si
está listo, sin que se muestre ningún valor:

```powershell
python scripts/observabilidad.py --estado
```

Dice qué variables faltan **por su nombre**. Si falta alguna, la integración
queda apagada sola y no se intenta ningún envío.

En `config.json`:

```json
"observabilidad": {
  "langfuse": {
    "activo": null,
    "enviar_texto": true
  }
}
```

- `activo`: `null` significa "enciéndete si están las tres variables". Ponlo a
  `false` para apagarlo aunque estén, o a `true` para dejar constancia de que
  lo quieres encendido.
- `enviar_texto`: con `false` viajan las métricas y los metadatos, pero **no**
  el texto de la prosa ni el de los prompts. Sirve para medir sin publicar el
  contenido.

## La forma del panel

Lo que verás no es una lista plana de llamadas, sino el flujo de la novela:

```
TRAZA  MyStory1                        una por tirada
 ├── canon                             fase
 │    └── 4 generaciones (arquitecto)
 ├── escaleta
 │    └── 15 generaciones (escaletista)
 ├── redaccion
 │    ├── capitulo 01                  aquí cuelgan los scores
 │    │    ├── intento 1 (borrador)
 │    │    │    └── generaciones: escritor, continuista
 │    │    └── intento 2 (parche)
 │    │         └── generaciones: estilista, archivista
 │    ├── capitulo 02
 │    └── capitulo 03
 ├── revision
 └── ensamblado
```

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

Es idempotente: los identificadores son deterministas, así que ejecutarlo dos
veces actualiza en vez de duplicar. No escribe en `events.jsonl`.

## Dependencias

Ninguna. El envío usa `urllib` de la biblioteca estándar. `requirements-opcional.txt`
solo hace falta si quieres el SDK oficial para consultar el panel desde Python.
