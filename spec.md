# spec — MyStory

**Especificación del agente de escritura de novelas de ciencia ficción**

**Versión:** 0.2
**Estado:** borrador
**Sustituye a:** `especificacion-funcional.md`, `especificacion-tecnica.md`

---

## Índice

**Parte I — Qué debe hacer el agente**
1. Propósito · 2. Actores · 3. Alcance · 4. Modos de ejecución · 5. Fases ·
6. Compuertas y rúbricas · 7. Comandos · 8. Reglas de comportamiento · 9. Restricciones

**Parte II — Cómo se construye**
10. Arquitectura · 11. Máquina de estados · 12. Bucle autónomo · 13. Modelo de datos ·
14. Gestión de contexto · 15. Prompting y evaluación · 16. Motor de continuidad ·
17. Presupuesto · 18. Errores · 19. Observabilidad

**Parte III — Validación**
20. Riesgos · 21. Criterios de aceptación · 22. Cuestiones abiertas

---

# Parte I — Qué debe hacer el agente

## 1. Propósito

El agente debe ser capaz de **escribir una novela de ciencia ficción completa de principio a
fin**: partiendo de una premisa, de una idea suelta o de nada, produce el manuscrito
terminado sin requerir intervención humana en el camino. El modo supervisado existe como
opción, no como requisito.

El problema que resuelve no es generar texto, sino **sostener la coherencia de una obra
larga**. Un autor pierde el hilo de lo que estableció en el capítulo 9; el agente no puede
permitírselo, porque en ejecución autónoma nadie va a detectar la contradicción por él.

## 2. Actores

| Actor | Descripción |
|---|---|
| **Autor** | En modo asistido decide y aprueba; en modo autónomo fija los parámetros iniciales y recibe el resultado. |
| **Agente** | Ejecuta las seis fases. En modo autónomo toma también las decisiones narrativas. |
| **Controlador** | Gobierna la ejecución autónoma: rúbricas, reintentos, presupuesto, checkpoints y escalado. |
| **Evaluador** | Puntúa los artefactos contra las rúbricas. Independiente del generador. |
| **Repositorio de artefactos** | Almacén versionado de todo lo producido. Única fuente de verdad. |

## 3. Alcance

**Incluido**

- Generación de la premisa a partir de una idea suelta, de una semilla libre o sin entrada.
- Construcción de la biblia del mundo.
- Fichas y arcos de personaje.
- Escaleta por actos, capítulos y escenas.
- Redacción de todas las escenas hasta completar el manuscrito.
- Auditoría de continuidad y corrección de los hallazgos.
- Crítica estructural y de ritmo.
- **Ejecución end-to-end sin intervención humana**, con auto-evaluación en cada compuerta.
- Informe de progreso, dosier de decisiones e informe de deuda.

**Excluido**

- Publicar, maquetar o distribuir.
- Gestión de derechos, contratos o relación con editoriales.
- Sustituir la revisión editorial humana previa a publicación.

## 4. Modos de ejecución

El modo se fija al inicio y puede cambiarse en cualquier checkpoint.

### 4.1 Autónomo (end-to-end)

El agente recorre las seis fases y entrega el manuscrito completo sin pedir nada por el
camino.

**Entrada mínima:** ninguna. Sin argumentos, el agente genera premisa propia.
Opcionalmente: semilla temática, extensión objetivo, tono, muestra de estilo y presupuesto.

```
/novela --palabras 90000 --tono "hard SF, sobrio" --estilo style-sample.md
/novela "una IA de terraformación desarrolla escrúpulos morales" --palabras 75000
/novela
```

**Salida:** manuscrito en `chapters/`, biblia, escaleta, informe de continuidad limpio,
`decisions-log.md` y `debt-report.md`.

**Compuertas.** Donde el modo asistido espera la aprobación del autor, el autónomo ejecuta
una auto-evaluación contra rúbrica explícita. Si no la supera, rehace la fase. Tras tres
intentos, continúa con la mejor versión y lo registra como deuda.

**Checkpoints.** Al cerrar cada fase guarda el estado y emite un resumen. El autor puede
ignorarlos, leerlos a posteriori o intervenir; nada queda bloqueado esperándole.

**Escalado.** Solo se detiene si agota el presupuesto, si acumula hallazgos `ALTO`
irresolubles en tres pasadas, o si detecta que la escaleta no tiene solución estructural.

### 4.2 Asistido

Igual flujo, pero cada compuerta la resuelve el autor y la redacción avanza escena a escena
bajo su dirección. Recomendado cuando la obra debe conservar la voz del autor.

### 4.3 Qué esperar de cada modo

| | Autónomo | Asistido |
|---|---|---|
| Intervención | Ninguna | En cada compuerta y escena |
| Voz | La del modelo, ajustada a la muestra si se aporta | La del autor |
| Techo de calidad | Manuscrito coherente y completo; originalidad limitada | Más alto |
| Uso típico | Primer borrador completo, probar una premisa, volumen | Obra de autor |

El modo autónomo produce **un primer borrador completo y coherente**, no una obra terminada.
Su valor está en tener 90.000 palabras estructuradas sobre las que trabajar.

## 5. Fases

Seis fases secuenciales con compuertas de calidad. No se avanza sin superar la compuerta
—por aprobación del autor o por auto-evaluación, según el modo— y se puede retroceder en
cualquier momento.

### Fase 0 — Premisa

Convierte una idea vaga en un compromiso narrativo concreto.

- **Entrada:** idea libre, o nada.
- **Salida:** `premise.md` con logline, conflicto central, pregunta temática, público, tono y tres referentes del género con los que la obra dialoga.
- **Regla:** no se acepta una premisa que no se distinga de sus referentes.
- **Autónomo:** genera tres candidatas, las puntúa contra la Compuerta 0 y se queda con la mejor. Las descartadas van a `decisions-log.md`.

### Fase 1 — Biblia del mundo

- **Entrada:** premisa aprobada.
- **Salida:** directorio `bible/`.
- **Regla:** se parte de **una** decisión especulativa central (el *novum*) y se deriva el resto por consecuencia. Todo elemento debe poder complicar la vida del protagonista; lo que no genera presión narrativa es decorado y se descarta.

### Fase 2 — Personajes

- **Entrada:** biblia.
- **Salida:** `characters/*.md`, uno por personaje con peso en la trama.
- **Contenido mínimo:** deseo declarado, necesidad real, herida de origen, qué cree al empezar, qué creerá al terminar, qué le cuesta ese cambio.
- **Regla:** se señalan personajes que duplican función narrativa y secundarios con más motor que el protagonista.

### Fase 3 — Escaleta

- **Entrada:** biblia y personajes.
- **Salida:** `outline.md` con actos, capítulos y, por capítulo: POV, objetivo, obstáculo, resultado y qué cambia respecto al anterior.
- **Regla:** se rechazan capítulos donde no cambia el estado del mundo o del personaje. El clímax debe resolver la pregunta temática de la Fase 0, no otra.

### Fase 4 — Redacción

- **Entrada:** escaleta aprobada y, si existe, muestra de estilo.
- **Salida:** `chapters/NN-titulo.md`.
- **Regla:** se trabaja **a nivel de escena**, no de capítulo. Antes de redactar se fijan POV, tiempo verbal, distancia narrativa y extensión. Cada escena se entrega con nota de qué elementos de la biblia usó y qué queda sin resolver.
- **Autónomo:** itera hasta agotar la escaleta sin pedir confirmación. Las decisiones que en modo asistido consultaría —un giro no previsto, un personaje nuevo, un cambio en una regla del mundo— las toma, las aplica a la biblia y las anota.
- **Continuidad parcial:** cada 5 escenas audita lo escrito desde la anterior. Sin esto la deriva se acumula y llega intacta al final, donde corregirla cuesta mucho más. Un hallazgo `ALTO` se resuelve antes de seguir.
- **Sin muestra de estilo:** fija el registro en la primera escena aprobada y lo usa como referencia para el resto.

### Fase 5 — Continuidad y revisión

- **Entrada:** capítulos y biblia.
- **Salida:** `continuity-report.md`.

| Eje | Qué verifica |
|---|---|
| Cronología | Fechas, edades, duración de viajes, simultaneidad |
| Tecnología | Que toda capacidad usada exista en las reglas; que no resuelva problemas anteriores |
| Personajes | Nombres, rasgos, tratamiento, quién sabe qué y desde cuándo |
| Espacio | Geografía, distancias, escenarios recurrentes |
| Registro | Consistencia de voz entre capítulos escritos en momentos distintos |

Cada hallazgo incluye ubicación, tipo, qué contradice y **dos opciones de arreglo con su
coste**. Severidades: `ALTO` (rompe la lógica del mundo), `MEDIO` (inconsistencia notable),
`BAJO` (detalle menor).

**Autónomo:** elige la opción de menor coste que no rompa nada aguas arriba, la aplica y
vuelve a auditar. Máximo tres pasadas completas. Los `BAJO` se entregan sin corregir. Si
persiste algún `ALTO`, escala.

## 6. Compuertas y rúbricas

Cada compuerta es una lista de criterios binarios; el artefacto pasa solo si los cumple
todos. La evaluación la hace una llamada independiente de la que generó el artefacto.

**Compuerta 0 — Premisa**

1. El logline expresa un conflicto, no una situación.
2. La pregunta temática admite al menos dos respuestas defendibles.
3. La premisa no es reducible a ninguno de sus tres referentes declarados.
4. El *novum* tiene consecuencias sociales o personales identificables.

**Compuerta 1 — Estructura**

1. Todo capítulo tiene un cambio de estado explícito.
2. La escalada de presión es monótona por actos, sin mesetas de más de tres capítulos.
3. El clímax resuelve la pregunta temática de la Fase 0.
4. Todo personaje de `characters/` tiene al menos tres escenas con función propia.
5. No hay dos personajes con la misma función narrativa.
6. La suma de extensiones previstas está dentro del ±10 % del objetivo.

**Compuerta 2 — Continuidad**

1. Cero hallazgos `ALTO`.
2. Cero hallazgos `MEDIO`.
3. Todo término del glosario aparece con forma canónica consistente.
4. Toda capacidad tecnológica usada existe en la biblia antes de su primer uso.
5. La cronología de la trama no tiene solapes ni ubicuidades.

**Límite:** 3 reintentos por compuerta. Al agotarse, se continúa con deuda registrada, salvo
en los criterios 1 y 2 de la Compuerta 2, que fuerzan escalado.

## 7. Comandos

| Comando | Función | Fase |
|---|---|---|
| `/novela [semilla] [opciones]` | **Ejecuta el ciclo completo end-to-end** | Todas |
| `/estado` | Fase actual, progreso, bloqueos | Todas |
| `/premisa` | Inicia o revisa la premisa | 0 |
| `/mundo <tema>` | Desarrolla un área de la biblia | 1 |
| `/personaje <nombre>` | Crea o revisa una ficha | 2 |
| `/escaleta` | Trabaja la estructura | 3 |
| `/escena <cap>.<n>` | Redacta una escena | 4 |
| `/continuidad [rango]` | Pasada de auditoría | 5 |
| `/critica <cap>` | Crítica estructural | 4-5 |
| `/buscar <consulta>` | Consulta biblia y capítulos | Todas |
| `/pausar` | Detiene la ejecución en el próximo checkpoint | Todas |
| `/reanudar` | Continúa desde el último checkpoint | Todas |
| `/deuda` | Lista lo aprobado sin superar rúbrica | Todas |

Opciones de `/novela`: `--palabras`, `--tono`, `--estilo <archivo>`, `--presupuesto`,
`--modo asistido|autonomo`, `--checkpoint-en <fase>`.

## 8. Reglas de comportamiento

**Voz.** Con muestra del autor, escribe en esa voz. Sin ella, fija una voz coherente al
inicio y la sostiene. En ambos casos evita los tics reconocibles de prosa generada:
adjetivación doble, cierres sentenciosos, construcciones de "no era X, era Y" y párrafos que
resumen la emoción en vez de dramatizarla. La deriva de registro es el fallo más probable en
una ejecución larga sin supervisión, y se audita en la Compuerta 2.

**Franqueza.** Si la premisa es débil, el giro es previsible o el capítulo no funciona, lo
dice. En autónomo esto se materializa en `debt-report.md`: no oculta que pasó una compuerta
con la tercera versión en lugar de la primera.

**Preguntas.** En asistido, máximo una por turno. En autónomo, ninguna: ante información
faltante asume lo más razonable, lo declara y sigue.

**Memoria.** Consulta la biblia antes de redactar. No improvisa hechos sobre el mundo: si
hace falta algo que no está, lo incorpora **explícitamente a la biblia** antes de usarlo en
la prosa. Un hecho que aparece en un capítulo sin estar en la biblia es un fallo de proceso,
no una licencia creativa.

## 9. Restricciones

- No reproduce texto con copyright ajeno ni imita a un autor vivo hasta sustituirlo.
- No usa personas reales identificables como personajes salvo marco de ficción histórica declarado.
- El nivel de contenido sensible lo fija el autor al inicio y el agente lo respeta en ambas direcciones.
- En modo autónomo el manuscrito es íntegramente generado, y así consta en `decisions-log.md` para efectos de declaración editorial.

---

# Parte II — Cómo se construye

## 10. Arquitectura

**Un agente con máquina de estados por fases y un bucle de control externo**, no un sistema
multiagente. Separar worldbuilder, redactor y editor en agentes distintos añade coste de
coordinación sin resolver el problema real, que es la gestión de contexto sobre un corpus
que crece.

El requisito end-to-end sí impone una separación: **quien genera no evalúa**. Generador y
evaluador son llamadas distintas, con prompts, temperatura y contexto distintos. Un modelo
que puntúa su propia salida en la misma llamada que la produjo aprueba casi siempre, y en
autónomo eso significa que nada frena la deriva.

| Componente | Responsabilidad |
|---|---|
| **Controlador de ejecución** | Bucle autónomo, presupuesto, reintentos, checkpoints, escalado |
| **Orquestador** | Máquina de estados, compuertas, enrutado de comandos |
| **Evaluador de compuerta** | Puntúa artefactos contra rúbrica; independiente del generador |
| **Gestor de artefactos** | Lectura/escritura del repositorio, front matter, commits |
| **Índice de contexto** | Recuperación selectiva de biblia y capítulos |
| **Motor de redacción** | Generación de escena con inyección de estilo |
| **Motor de continuidad** | Auditoría por ejes, informe |
| **Registro de decisiones** | Qué se decidió, cuándo, por qué y con qué puntuación |

## 11. Máquina de estados

```
PREMISA → [compuerta 0] → MUNDO → PERSONAJES → ESTRUCTURA
        → [compuerta 1] → REDACCION ⇄ [bucle escena + continuidad parcial]
        → CONTINUIDAD → [compuerta 2] → REDACCION   (si hay hallazgos)
                                      → ESTABLE     (si no)
                                      → ESCALADO    (si se agotan límites)
```

El estado vive en `project.yaml`, no en la conversación. Cualquier sesión nueva lo
reconstruye leyendo ese archivo. Transiciones prohibidas: entrar en `REDACCION` sin escaleta
aprobada; cerrar en `ESTABLE` con hallazgos `ALTO` abiertos.

```yaml
modo: autonomo
fase: REDACCION
objetivo_palabras: 90000
premisa_aprobada: true
estructura_aprobada: true
escena_actual: "12.3"
palabras_totales: 41280
hallazgos_abiertos: { alto: 0, medio: 2, bajo: 7 }
reintentos: { compuerta_0: 1, compuerta_1: 2, compuerta_2: 0 }
presupuesto: { tokens_max: 12000000, tokens_usados: 5140000, horas_max: 10 }
deuda: ["C1 criterio 2: meseta de 4 capítulos en acto II, aceptada tras 3 intentos"]
ultimo_checkpoint: "2026-09-15T11:42:00Z"
```

## 12. Bucle autónomo

```
para cada fase en [PREMISA, MUNDO, PERSONAJES, ESTRUCTURA]:
    intento = 0
    repetir:
        artefacto = generar(fase, contexto)
        veredicto = evaluar(artefacto, rubrica[fase])      # llamada independiente
        intento += 1
    hasta veredicto.aprobado o intento == 3

    si no veredicto.aprobado: registrar_deuda(fase, veredicto.criterios_fallidos)
    persistir(artefacto); checkpoint()

mientras queden escenas:
    escena = redactar(siguiente_escena)
    persistir(escena)
    si escenas_desde_ultima_auditoria == 5:
        hallazgos = continuidad(incremental)
        si hallazgos.alto: corregir_antes_de_seguir()
    si presupuesto_agotado(): escalar(); salir

pasada = 0
repetir:
    hallazgos = continuidad(completa)
    aplicar_correcciones(hallazgos.alto + hallazgos.medio)
    pasada += 1
hasta (sin alto y sin medio) o pasada == 3

si quedan hallazgos alto: escalar()
si no: estado = ESTABLE
```

Tres invariantes: **nunca itera sin límite**, **nunca avanza sin persistir** y **nunca se
detiene en silencio** —toda parada produce un motivo legible.

## 13. Modelo de datos

Todo es texto plano versionable en git. No hay base de datos.

```
proyecto/
├── project.yaml
├── premise.md
├── outline.md
├── continuity-report.md
├── decisions-log.md         # Decisiones narrativas autónomas y su motivo
├── debt-report.md           # Compuertas superadas con deuda
├── style-sample.md          # Muestra de voz del autor (opcional)
├── bible/
│   ├── novum.md · technology.md · society.md
│   ├── geography.md · timeline.md · glossary.md
├── characters/*.md
└── chapters/NN-titulo.md
```

**Front matter de capítulo**

```yaml
---
numero: 7
titulo: "Umbral"
pov: "Kira"
tiempo: "Día 41, tarde"
lugar: "Estación Meridiano, nivel 3"
objetivo: "Acceder a los registros sellados"
resultado: "Fracasa y queda marcada por el sistema"
palabras: 3120
estado: borrador        # esquema | borrador | revisado | final
elementos_biblia: [contencion-campos, protocolo-meridiano]
---
```

La auditoría opera **primero sobre metadatos** y solo desciende al cuerpo del texto ante un
conflicto potencial. Sin esto, cada pasada releería la novela entera.

**Glosario.** Cada término inventado registra forma canónica, variantes aceptadas,
definición, capítulo de primera aparición y si el lector ya lo conoce. Es la defensa
principal contra la deriva terminológica.

**Cronología.** Dos ejes independientes: la del mundo (anterior a la novela) y la de la
trama (día y hora de cada escena en orden absoluto, con independencia del orden de lectura).
El segundo detecta la mayoría de los errores temporales.

## 14. Gestión de contexto

Una novela terminada más su biblia supera cualquier ventana práctica. Tres capas:

1. **Siempre en contexto:** `project.yaml`, `premise.md`, `bible/novum.md`, ficha del POV de la escena y bloque de escaleta correspondiente. ≈ 4–6k tokens.
2. **Recuperación selectiva:** solo las secciones de biblia y capítulos citados por `elementos_biblia` o por la consulta.
3. **Resumen rodante:** cada capítulo cerrado genera un resumen de 150 palabras. Para redactar el capítulo 30 se cargan resúmenes, no texto íntegro; los capítulos 28–29 sí van completos, por continuidad de voz.

Índice: embeddings por sección con metadatos, reconstruible desde cero, no versionado.

## 15. Prompting y evaluación

Cada llamada se compone de: rol y fase → reglas de la fase → artefactos de contexto →
muestra de estilo (solo en redacción) → instrucción concreta. Las reglas se inyectan
literalmente; no se confía en que el modelo las recuerde de turnos anteriores.

**Redacción:** temperatura media-alta, salida limitada a una escena, prosa más bloque de
metadatos separado.

**Evaluador de compuerta**, con tres diferencias deliberadas respecto del generador:

- Temperatura baja y salida estructurada obligatoria.
- **No recibe el razonamiento del generador**, solo el artefacto y la rúbrica. Si ve la justificación de por qué se escribió así, la adopta y aprueba.
- **Criterios binarios, no puntuación global.** Un "7,5 sobre 10" no es accionable; "el criterio 2 falla porque los capítulos 14–17 no escalan" sí.

```json
{
  "aprobado": false,
  "criterios": [
    {"id": 1, "cumple": true},
    {"id": 2, "cumple": false,
     "evidencia": "Caps. 14-17 mantienen la misma presión sobre Kira",
     "correccion_sugerida": "Adelantar la revelación del cap. 19 al 15"}
  ]
}
```

La corrección sugerida se inyecta en el siguiente intento. Sin ella, el reintento produce
una variante del mismo fallo.

## 16. Motor de continuidad

**Nivel 1 — determinista, sin modelo.** Sobre front matter y glosario: solapes temporales,
personajes en dos lugares a la vez, variantes de término no registradas, saltos de
numeración. Barato, ejecutable en cada commit.

**Nivel 2 — semántico, con modelo.** Sobre el cuerpo del texto, acotado a los capítulos
tocados desde la última pasada y a los que comparten `elementos_biblia`. Verifica
consistencia de reglas del mundo y de conocimiento de los personajes.

```json
{
  "hallazgos": [{
    "severidad": "ALTO",
    "eje": "tecnologia",
    "ubicacion": "cap. 14, escena 2",
    "descripcion": "Kira desactiva el campo desde un terminal remoto",
    "contradice": "bible/technology.md — los campos requieren presencia física (cap. 5)",
    "opciones": [
      {"accion": "Cambiar la regla en la biblia", "coste": "Revisar cap. 5 y 9"},
      {"accion": "Kira usa un intermediario presente", "coste": "Introducir o reubicar personaje"}
    ]
  }]
}
```

Un hallazgo sin ubicación verificable se descarta.

## 17. Presupuesto y control de coste

Una novela de 90.000 palabras en autónomo implica, con las tres capas de contexto y los
reintentos, del orden de 8–15 millones de tokens.

| Límite | Comportamiento al alcanzarlo |
|---|---|
| `tokens_max` | Checkpoint y escalado |
| `horas_max` | Checkpoint y escalado |
| 3 reintentos por compuerta | Continuar con deuda |
| 3 pasadas de continuidad final | Escalar si persiste `ALTO` |

Reparto estimado: fases 0–3 alrededor del 15 %, redacción el 60 %, continuidad el 25 %. La
continuidad es cara porque relee; de ahí que el Nivel 1 sea determinista.

## 18. Errores y degradación

| Situación | Respuesta |
|---|---|
| Artefacto de fase anterior ausente | Bloquear y nombrar el archivo que falta |
| Salida no válida contra esquema | Un reintento con el error; luego error al usuario |
| Contexto excedido | Degradar a resúmenes y avisar de qué se omitió |
| Estado inconsistente en `project.yaml` | Reconstruir desde los archivos presentes |

En modo asistido, ante duda el agente para y pregunta. En autónomo decide, lo registra y
sigue. En ningún modo sobrescribe un artefacto existente sin dejar traza.

## 19. Observabilidad

Por sesión se registra fase, comando, artefactos leídos, tokens, latencia y resultado.
Métricas de interés: hallazgos por 10.000 palabras, tasa de rechazo en compuertas, deuda
acumulada y coste por capítulo.

Git como capa de persistencia: cada operación que modifica artefactos genera un commit
trazable (`fase(escena): cap 14.2 — borrador`). Historial y deshacer sin construir nada.
Opcional: hook de pre-commit con la continuidad de Nivel 1, que bloquea ante un `ALTO`.

---

# Parte III — Validación

## 20. Riesgos

| Riesgo | Mitigación |
|---|---|
| **Deriva de registro** entre el primer y el último tercio | Muestra de estilo fija; auditoría en Compuerta 2; comparación de embeddings de estilo por tercios |
| **Auto-aprobación complaciente** | Evaluador independiente, criterios binarios, criterio de aceptación 6 |
| **Homogeneización** de todas las escenas | Variación forzada de longitud, POV y tipo de escena desde la escaleta |
| **Bucle infinito de corrección** | Límite duro de reintentos y pasadas |
| **Colapso de contexto** en capítulos tardíos | Resúmenes rodantes y recuperación selectiva |
| **Coste desbocado** | Presupuesto declarado y checkpoint al alcanzarlo |
| **Trama que se resuelve sola** | Criterio de cambio de estado por capítulo en Compuerta 1 |

Riesgo residual que ninguna mitigación elimina: el modo autónomo produce coherencia, no
necesariamente interés. La rúbrica detecta que un capítulo no escala; no detecta que la
novela entera es previsible. Eso sigue requiriendo lectura humana.

## 21. Criterios de aceptación

Sobre una ejecución autónoma completa con objetivo de 80.000 palabras:

1. El agente termina el manuscrito sin intervención humana.
2. La extensión final queda dentro del ±10 % del objetivo.
3. El informe de continuidad final no contiene hallazgos `ALTO` ni `MEDIO`.
4. Todo capítulo de la escaleta tiene un cambio de estado identificable.
5. Un lector externo no distingue cambios de registro entre el primer tercio y el último.
6. El agente rechaza y rehace al menos un artefacto en alguna compuerta. Una ejecución que aprueba todo a la primera indica rúbricas mal calibradas.
7. `decisions-log.md` permite reconstruir por qué se tomó cualquier decisión narrativa.
8. Coste y tiempo totales quedan dentro del presupuesto declarado.

## 22. Cuestiones abiertas

- Indexación cuando la biblia supere las 50.000 palabras.
- Si la continuidad de Nivel 2 debe correr en CI o solo bajo demanda.
- Calibración empírica de los umbrales de rúbrica: con umbrales altos el agente no termina; con umbrales bajos entrega borradores planos.
- Si conviene un modelo distinto para el evaluador, y reducir así el sesgo de auto-aprobación.
- Soporte para series de varios libros con biblia compartida.
