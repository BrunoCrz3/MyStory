# Especificación funcional — MyStory

**Versión:** 0.1
**Estado:** borrador

---

## 1. Propósito

Definir qué hace el agente desde el punto de vista del usuario: qué le pide, qué obtiene y
bajo qué reglas.

El agente debe ser capaz de **escribir una novela completa de principio a fin**: partiendo
de una premisa o incluso de una idea suelta, produce el manuscrito terminado sin requerir
intervención humana en el camino. El modo supervisado sigue existiendo, pero como opción,
no como requisito.

El problema que resuelve no es generar texto, sino **sostener la coherencia de una obra
larga**. Un autor pierde el hilo de lo que estableció en el capítulo 9; el agente no puede
permitírselo, porque en ejecución autónoma nadie va a detectar la contradicción por él.

## 2. Actores

| Actor | Descripción |
|---|---|
| **Autor** | Usuario principal. En modo asistido decide y aprueba; en modo autónomo fija los parámetros iniciales y recibe el resultado. |
| **Agente** | Ejecuta las seis fases. En modo autónomo toma también las decisiones narrativas y evalúa su propio trabajo en cada compuerta. |
| **Controlador** | Gobierna la ejecución autónoma: rúbricas, reintentos, presupuesto, checkpoints y escalado. |
| **Repositorio de artefactos** | Almacén versionado de todo lo producido. Única fuente de verdad. |

## 3. Alcance

### Incluido

- Generación de la premisa a partir de una idea suelta o de una semilla libre.
- Construcción de la biblia del mundo.
- Fichas y arcos de personaje.
- Escaleta por actos, capítulos y escenas.
- Redacción de todas las escenas hasta completar el manuscrito.
- Auditoría de continuidad y corrección de los hallazgos.
- Crítica estructural y de ritmo.
- **Ejecución end-to-end sin intervención humana**, con auto-evaluación en cada compuerta.
- Informe de progreso y dosier de decisiones.

### Excluido

- Publicar, maquetar o distribuir.
- Gestión de derechos, contratos o relación con editoriales.
- Sustituir la revisión editorial humana previa a publicación.

## 4. Modos de ejecución

El modo se fija al inicio y puede cambiarse en cualquier checkpoint.

### 4.1 Modo autónomo (end-to-end)

El agente recorre las seis fases y entrega el manuscrito completo sin pedir nada por el
camino.

**Entrada mínima:** nada. Con una invocación sin argumentos el agente genera premisa
propia. Opcionalmente: semilla temática, extensión objetivo, tono, muestra de estilo y
presupuesto.

```
/novela --palabras 90000 --tono "hard SF, sobrio" --estilo style-sample.md
/novela "una IA de terraformación desarrolla escrúpulos morales" --palabras 75000
/novela
```

**Salida:** manuscrito completo en `chapters/`, biblia, escaleta, informe de continuidad
limpio y `decisions-log.md` con cada decisión narrativa tomada y su motivo.

**Comportamiento en las compuertas.** Donde el modo asistido espera la aprobación del
autor, el modo autónomo ejecuta una auto-evaluación: el agente puntúa su propio artefacto
contra una rúbrica explícita y solo avanza si supera el umbral. Si no lo supera, rehace la
fase. Tras tres intentos fallidos, marca el problema, continúa con la mejor versión
disponible y lo registra como deuda en el informe final.

**Checkpoints.** Al cerrar cada fase el agente guarda el estado y emite un resumen. El autor
puede ignorarlos por completo, leerlos a posteriori o intervenir; nada queda bloqueado
esperándole.

**Escalado.** El agente solo se detiene y reclama atención humana si agota el presupuesto,
si acumula hallazgos de severidad `ALTO` que no consigue resolver en tres pasadas, o si
detecta que la escaleta no tiene solución estructural.

### 4.2 Modo asistido

Igual flujo, pero cada compuerta la resuelve el autor y la redacción avanza escena a
escena bajo su dirección. Es el modo recomendado cuando el autor quiere que la obra
conserve su voz.

### 4.3 Qué esperar de cada modo

| | Autónomo | Asistido |
|---|---|---|
| Intervención | Ninguna | En cada compuerta y escena |
| Voz | La del modelo, ajustada a la muestra si se aporta | La del autor |
| Techo de calidad | Manuscrito coherente y completo; originalidad limitada | Más alto |
| Uso típico | Primer borrador completo, prueba de una premisa, volumen | Obra de autor |

El modo autónomo produce **un primer borrador completo y coherente**, no una obra
terminada. Su valor está en tener 90.000 palabras estructuradas sobre las que trabajar, no
en sustituir la revisión humana.

## 5. Flujo funcional

Ver `diagrama.drawio`. Seis fases secuenciales con compuertas de calidad. El agente no
avanza de fase sin superar la compuerta —por aprobación del autor o por auto-evaluación,
según el modo— y puede retroceder en cualquier momento.

### Fase 0 — Premisa

Convierte una idea vaga en un compromiso narrativo concreto.

**Entrada:** idea libre del autor, o nada en modo autónomo sin semilla.
**Salida:** `premise.md` con logline, conflicto central, pregunta temática, público, tono y
tres referentes del género con los que la obra dialoga.
**Regla:** no se acepta una premisa que no distinga la obra de sus referentes.
**Autónomo:** el agente genera tres premisas candidatas, las puntúa contra la rúbrica de la
Compuerta 0 y se queda con la mejor. Registra en `decisions-log.md` las descartadas y por qué.

### Fase 1 — Biblia del mundo

**Entrada:** premisa aprobada.
**Salida:** directorio `bible/`.
**Regla:** se parte de **una** decisión especulativa central (el *novum*) y se deriva el
resto por consecuencia. Todo elemento del mundo debe poder complicar la vida del
protagonista; lo que no genera presión narrativa es decorado y se propone descartar.

### Fase 2 — Personajes

**Entrada:** biblia.
**Salida:** `characters/*.md`, uno por personaje con peso en la trama.
**Contenido mínimo por ficha:** deseo declarado, necesidad real, herida de origen, qué cree
al empezar, qué creerá al terminar, qué le cuesta ese cambio.
**Regla:** el agente señala personajes que duplican función narrativa y secundarios con más
motor que el protagonista.

### Fase 3 — Escaleta

**Entrada:** biblia y personajes.
**Salida:** `outline.md` con actos, capítulos y, por capítulo: POV, objetivo, obstáculo,
resultado y qué cambia respecto al anterior.
**Regla:** se rechazan capítulos donde no cambia el estado del mundo o del personaje. El
clímax debe resolver la pregunta temática de la Fase 0, no otra.

### Fase 4 — Redacción

**Entrada:** escaleta aprobada y, si existe, muestra de estilo del autor.
**Salida:** `chapters/NN-titulo.md`.
**Regla:** se trabaja **a nivel de escena**, no de capítulo completo. Antes de redactar se
fijan POV, tiempo verbal, distancia narrativa y extensión. Cada escena se entrega con nota
de qué elementos de la biblia se usaron y qué queda sin resolver.

**Autónomo:** el agente itera el bucle de escena hasta agotar la escaleta, sin pedir
confirmación. Decisiones que en modo asistido consultaría (un giro no previsto, un
personaje nuevo, un cambio en una regla del mundo) las toma por su cuenta, las aplica a la
biblia y las anota en `decisions-log.md`.

Cada 5 escenas ejecuta una **pasada de continuidad parcial** sobre lo escrito desde la
anterior. Sin esto, la deriva se acumula y llega intacta al final, donde corregirla cuesta
mucho más. Si aparece un hallazgo `ALTO`, lo resuelve antes de seguir.

Si sin muestra de estilo, fija el registro en la primera escena aprobada y la usa como
referencia de voz para el resto del manuscrito.

### Fase 5 — Continuidad y revisión

**Entrada:** capítulos redactados y biblia.
**Salida:** `continuity-report.md`.

Comprobaciones obligatorias:

| Eje | Qué verifica |
|---|---|
| Cronología | Fechas, edades, duración de viajes, simultaneidad |
| Tecnología | Que toda capacidad usada exista en las reglas; que no resuelva problemas anteriores |
| Personajes | Nombres, rasgos, tratamiento, quién sabe qué y desde cuándo |
| Espacio | Geografía, distancias, escenarios recurrentes |
| Registro | Consistencia de voz entre capítulos escritos con semanas de diferencia |

Cada hallazgo incluye ubicación, tipo, qué contradice y **dos opciones de arreglo con su
coste**. Severidades: `ALTO` (rompe la lógica del mundo), `MEDIO` (inconsistencia notable),
`BAJO` (detalle menor).

**Autónomo:** el agente elige la opción de arreglo de menor coste que no rompa nada aguas
arriba, la aplica y vuelve a auditar. Repite hasta que no queden hallazgos `ALTO` ni
`MEDIO`, con máximo tres pasadas completas. Los `BAJO` se entregan sin corregir en el
informe. Si tras tres pasadas persiste algún `ALTO`, escala al autor.

## 6. Compuertas y rúbricas

En modo autónomo las compuertas sustituyen la aprobación humana. Cada una es una lista de
criterios binarios; el artefacto pasa solo si los cumple todos. La evaluación la hace el
agente sobre su propio trabajo, en una llamada separada de la que lo generó.

### Compuerta 0 — Premisa

1. El logline expresa un conflicto, no una situación.
2. La pregunta temática admite al menos dos respuestas defendibles.
3. La premisa no es reducible a ninguno de sus tres referentes declarados.
4. El *novum* tiene consecuencias sociales o personales identificables.

### Compuerta 1 — Estructura

1. Todo capítulo tiene un cambio de estado explícito.
2. La escalada de presión es monótona por actos, sin mesetas de más de tres capítulos.
3. El clímax resuelve la pregunta temática de la Fase 0.
4. Todo personaje de `characters/` tiene al menos tres escenas con función propia.
5. No hay dos personajes con la misma función narrativa.
6. La suma de extensiones previstas está dentro del ±10 % del objetivo.

### Compuerta 2 — Continuidad

1. Cero hallazgos `ALTO`.
2. Cero hallazgos `MEDIO`.
3. Todo término del glosario aparece con forma canónica consistente.
4. Toda capacidad tecnológica usada existe en la biblia antes de su primer uso.
5. La cronología de la trama no tiene solapes ni ubicuidades.

**Límite de reintentos:** 3 por compuerta. Al agotarse, el agente continúa con la mejor
versión y registra la deuda en el informe final, salvo en los criterios 1 y 2 de la
Compuerta 2, que fuerzan escalado.

## 7. Comandos

| Comando | Función | Fase |
|---|---|---|
| `/estado` | Fase actual, progreso, bloqueos | Todas |
| `/premisa` | Inicia o revisa la premisa | 0 |
| `/mundo <tema>` | Desarrolla un área de la biblia | 1 |
| `/personaje <nombre>` | Crea o revisa una ficha | 2 |
| `/escaleta` | Trabaja la estructura | 3 |
| `/escena <cap>.<n>` | Redacta una escena | 4 |
| `/continuidad [rango]` | Pasada de auditoría | 5 |
| `/critica <cap>` | Crítica estructural | 4-5 |
| `/buscar <consulta>` | Consulta biblia y capítulos | Todas |
| `/novela [semilla] [opciones]` | **Ejecuta el ciclo completo end-to-end** | Todas |
| `/pausar` | Detiene la ejecución autónoma en el próximo checkpoint | Todas |
| `/reanudar` | Continúa desde el último checkpoint | Todas |
| `/deuda` | Lista las decisiones tomadas sin superar rúbrica | Todas |

Opciones de `/novela`: `--palabras`, `--tono`, `--estilo <archivo>`, `--presupuesto`,
`--modo asistido|autonomo`, `--checkpoint-en <fase>`.

## 8. Reglas de comportamiento

**Voz.** Si hay muestra del autor, el agente escribe en esa voz. Si no, fija una voz
coherente al inicio y la sostiene. En ambos casos evita los tics reconocibles de prosa
generada: adjetivación doble, cierres sentenciosos, construcciones de "no era X, era Y" y
párrafos que resumen la emoción en vez de dramatizarla. La deriva de registro es el fallo
más probable en una ejecución larga sin supervisión, y se audita explícitamente en la
Compuerta 2.

**Franqueza.** Si la premisa es débil, el giro es previsible o el capítulo no funciona, lo
dice. En modo autónomo esto se materializa en el informe de deuda: el agente no oculta que
pasó una compuerta con la tercera versión en lugar de la primera.

**Preguntas.** En modo asistido, máximo una por turno. En modo autónomo, ninguna: ante
información faltante asume lo más razonable, lo declara en `decisions-log.md` y sigue.

**Memoria.** Consulta la biblia antes de redactar. No improvisa hechos sobre el mundo: si
hace falta algo que no está, lo incorpora **explícitamente a la biblia** antes de usarlo en
la prosa. Un hecho que aparece en un capítulo sin estar en la biblia es un fallo de proceso,
no una licencia creativa.

## 9. Restricciones

- No reproduce texto con copyright ajeno ni imita a un autor vivo hasta sustituirlo.
- No usa personas reales identificables como personajes salvo marco de ficción histórica declarado.
- El nivel de contenido sensible (violencia, sexo, trauma) lo fija el autor al inicio y el agente lo respeta en ambas direcciones.
- El agente registra qué fragmentos redactó. En modo autónomo el manuscrito es íntegramente generado, y así debe constar en `decisions-log.md` para efectos de declaración editorial.

## 10. Criterios de aceptación

Sobre una ejecución autónoma completa con objetivo de 80.000 palabras:

1. El agente termina el manuscrito sin intervención humana.
2. La extensión final queda dentro del ±10 % del objetivo.
3. El informe de continuidad final no contiene hallazgos `ALTO` ni `MEDIO`.
4. Todo capítulo de la escaleta tiene un cambio de estado identificable.
5. Un lector externo no distingue cambios de registro entre el primer tercio y el último.
6. El agente rechaza y rehace al menos un artefacto en alguna compuerta; una ejecución que aprueba todo a la primera indica rúbricas mal calibradas.
7. `decisions-log.md` permite reconstruir por qué se tomó cualquier decisión narrativa.
8. Coste y tiempo totales quedan dentro del presupuesto declarado.

En modo asistido aplican además los criterios de la versión anterior de este documento
relativos a la conservación de la voz del autor.
