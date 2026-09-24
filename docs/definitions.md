# Ontología de generación de novelas personalizadas — Definiciones

2026-09-23 · @Bruno Cruz

Este documento define el vocabulario del dominio: qué clases existen, qué atributos tiene cada una y qué relaciones las unen. Cubre cinco capas: encargo y obra, canon, contexto, calidad y proceso. Los diagramas viven en el documento de conocimiento de dominio.

El sistema genera novelas personalizadas para regalar. Tiene dos objetivos de igual peso y ninguno subordinado al otro: que el destinatario se reconozca en el texto, y que el texto sea una novela y no una lista de datos suyos puestos en prosa. Cada clase de este documento sirve a uno de los dos, o a la maquinaria que los hace verificables.

## Convenciones del modelo

La ontología se organiza en cinco capas con ciclos de vida distintos; mezclarlas es el error de diseño más común.

| Capa | Responde a | Cambia cuando |
| --- | --- | --- |
| Encargo y obra | ¿Para quién es la novela y de qué está hecha? | Se cierra el brief o el lector pide un cambio |
| Canon | ¿Qué es verdad en el punto t del texto? | Se acepta un capítulo |
| Contexto | ¿Qué ve el modelo al generar? | En cada llamada de generación |
| Calidad | ¿Esto está bien? | Se ajustan umbrales o criterios |
| Proceso | ¿Quién hace qué y en qué orden? | Se cambia el harness |

El encargo y la obra comparten capa porque en este dominio son lo mismo visto dos veces: el brief no es un requisito externo a la novela, es de lo que la novela está hecha. Separarlos daría dos capas con el mismo disparador de cambio.

Criterio de inclusión: una clase entra en el modelo solo si alguna pregunta de competencia (última sección) la necesita. Convenciones de notación: `Clase` en mayúscula inicial, `atributo` en minúscula, `relación` en verbo. `t` denota una posición en el discurso, no una fecha del mundo ficcional.

**Un concepto, un nombre.** Dos clases nunca comparten nombre y una clase nunca tiene dos. Los pares que estuvieron a punto de colisionar quedan fijados aquí: `Brief de novela` es el encargo del comprador y `Brief de capítulo` el encargo de un capítulo; `Contradicción de brief` ocurre entre datos del comprador y `Contradicción de canon` entre hechos de la ficción; el `Comprador` paga y configura, y el `Lector` lee y pide cambios. La tabla de § Nomenclatura extiende la regla a cada ámbito donde el nombre reaparece: código, SQLite y Langfuse.

## Modelo de generación

La novela se planifica entera y se escribe capítulo a capítulo, sin humano en el bucle.

| Nivel | Modo | Fuente de verdad |
| --- | --- | --- |
| Obra | Planificado de una vez | Brief de novela |
| Capítulo | Destino fijado, camino descubierto | Esquema |
| Prosa del capítulo | Descubrimiento libre | Texto generado |

**El capítulo es la unidad atómica** de generación, validación, checkpoint, regeneración y marca de cambio entre versiones. Todo lo demás se planifica hacia él o se deriva de él. No hay unidad por debajo: a la longitud de capítulo que declara `config/thresholds.yaml` no cabe una subdivisión a la que colgarle un estado, un presupuesto o un validador propios, y una clase sin operación no entra en el modelo.

El grano temporal fino no lo da la estructura del discurso sino la fábula: es el `Evento` quien lleva momento, lugar y participantes, y es de él —no del capítulo— de donde sale el fichero que verifica la cronología.

**Clases propias de este modo**

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Restricción de destino | Lo que el capítulo no puede dejar de cumplir sin replanificar | tipo (estado final, revelación, posición de personaje), alcance, capítulo que la debe cumplir |
| Extracción | Lectura automática de un capítulo aceptado para detectar los hechos que ha introducido | entradas, hechos propuestos, confianza |
| Invalidación de restricción | Una restricción de destino aún no escrita que el canon vigente ya hace imposible | restricción, hecho que la contradice, capítulo afectado |
| Replanificación de capítulos pendientes | Revisión del esquema limitada a los capítulos aún no escritos | disparador, capítulos afectados, cambios al esquema |

**Qué declara el `alcance` de una restricción de destino.** No es un texto libre: es la lista explícita de lo que la restricción toca —`Personaje`, `Lugar`, `Hecho`, `Promesa narrativa` e `Hilo de trama`, cada uno por su identificador—. Sin esa lista, «¿ha vuelto el canon imposible esta restricción?» no se puede resolver con una consulta, porque no se sabe contra qué hechos compararla, y la invalidación vuelve a depender de un juicio. Es lo que convierte la `Invalidación de restricción` en el booleano determinista que sustituyó a la medida de deriva.

**Reglas de gobierno**

- El capítulo descubre *cómo*, no *hacia dónde*: cambiar el destino exige replanificar, no se decide dentro del capítulo.
- Nada se declara por adelantado salvo las restricciones de destino; el resto del canon se extrae después de aceptar el capítulo.
- El retcon es operación rutinaria, con propagación a los capítulos afectados y solo a ellos.
- La replanificación se dispara por invalidación de una restricción, nunca por cadencia y nunca en mitad de un capítulo.

**Por qué la invalidación y no una medida de deriva.** Con la obra planificada de una vez y generada en una sola corrida, la única pregunta con respuesta útil es binaria: ¿queda alguna restricción de destino pendiente que el canon ya ha vuelto imposible? Una medida acumulativa necesitaría un umbral, y un umbral necesita a alguien que etiquete cuándo replanificar; ese alguien era el autor humano y ya no está en el bucle. Un número que nadie puede calibrar no dispara nada: es peso muerto con aspecto de rigor.

## Capa 1 — Encargo y obra

### Bloque A — Encargo

Lo que el comprador aporta y lo que la entrevista convierte en contrato. Es la mitad del objetivo del sistema y la entrada de casi todos los validadores de personalización.

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Comprador | Quien encarga, paga y configura la novela | identificador, relación con el destinatario |
| Destinatario | Persona a quien va dirigida la novela | nombre, edad, rasgos, recuerdos, relación con el comprador |
| Ocasión | Motivo del regalo | tipo (cumpleaños, boda, aniversario, jubilación, nacimiento), fecha, tono esperado |
| Brief de novela | Salida estructurada y validada con schema de la entrevista | género, tono, extensión, estado, schema y versión con que se validó |
| Elemento personalizado | Detalle del destinatario que la novela debe integrar | enunciado, obligatoriedad, origen, estado de cobertura |
| Texto libre aportado | Anécdota o carta que el comprador pega sin estructura | contenido, procedencia, estado de saneamiento |
| Fragmento sospechoso | Parte del texto libre marcada como intento de instrucción al sistema | fragmento, motivo, decisión, texto libre de origen |
| Dato faltante | Campo del brief que la entrevista no logró rellenar | campo, obligatoriedad, pregunta de reintento |
| Contradicción de brief | Conflicto entre dos datos aportados por el comprador | campos implicados, tipo, resolución |
| Dedicatoria | Texto personal que abre la novela | texto, firma |

**El texto libre es contenido no confiable.** Entra marcado como datos y nunca en la posición donde el prompt pone sus instrucciones; de él se extraen hechos, y lo que parece una orden al sistema se registra como `Fragmento sospechoso` y se descarta. Es la única entrada del sistema que procede de fuera y la única que hace falta cuarentenar.

**Obligatorio y opcional no es un matiz.** Un `Elemento personalizado` obligatorio que no aparece en ningún capítulo impide publicar la versión; uno opcional no. La distinción es lo que convierte «que se note que es para él» en una consulta que decide un `SELECT`.

### Bloque B — Obra

**Clases estructurales** (contenedoras, jerárquicas)

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Obra | La novela completa | premisa, género, tono, extensión objetivo, estado |
| Capítulo | Unidad atómica de generación, validación y publicación | número, título, función dramática, POV, lugar, momento, gancho de cierre, estado, recuento de palabras, intentos |

No hay nivel intermedio entre obra y capítulo. La función dramática que sostendría un acto es atributo del capítulo, que es donde el validador de cierre del arco la necesita.

**Entidades narrativas** (sustantivas, atraviesan la estructura)

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Personaje | Agente con deseo y capacidad de acción | nombre, deseo, herida, rol narrativo, voz, fecha de nacimiento, es destinatario |
| Arco | Trayectoria de transformación | estado inicial, puntos de giro, estado final, capítulos que lo avanzan |
| Hilo de trama | Cadena causal de eventos con tensión propia | tipo, pregunta dramática, estado |
| Lugar | Espacio donde ocurre acción | nombre, geografía, atmósfera sensorial |
| Evento | Suceso de la fábula, situado en el orden cronológico ficcional | qué ocurre, momento, personajes presentes, lugar, duración |
| Evento excluyente | Evento tras el cual un personaje no puede volver a aparecer | evento, personajes excluidos, tipo (muerte, partida definitiva) |
| Regla del mundo | Restricción que el texto no puede violar | enunciado, alcance, excepciones declaradas, origen |
| Voz narrativa | Configuración del narrador | persona, tiempo verbal, distancia, focalización |

`Personaje` y `Lugar` son las dos entidades que la novela publica como ficha consultable, y por eso son las dos que sobreviven con nombre propio: lo que no se muestra ni se valida no necesita clase.

`Evento excluyente` es subtipo de `Evento` y existe por una razón concreta: es el que permite demostrar que ningún personaje aparece después de morir o de marcharse para siempre. Sin él, esa demostración no tiene de dónde leer.

`Regla del mundo` ya no deriva de un punto de divergencia especulativa: su origen es el brief. «El destinatario es alérgico a los gatos» y «el abuelo nunca aparece» son reglas del mundo tanto como lo sería la física de una novela de género.

**Fábula y discurso.** La *fábula* es el conjunto de eventos en orden cronológico ficcional; el *discurso* es el orden y la forma en que se narran. Son dos clases separadas unidas por una relación `se narra en`. Sin esta separación no se pueden gestionar analepsis ni revelaciones diferidas, y —lo que aquí pesa más— no se puede verificar la cronología: comprobar el orden de los capítulos no dice nada sobre el orden de los hechos.

## Capa 2 — Canon y estado

El canon es la **story bible**: el conjunto de lo que es verdad en la novela, con el registro de en qué capítulos se usa cada cosa. Es la capa que hace posible la regeneración dirigida y la que alimenta la verificación formal de la historia.

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Hecho | Enunciado verdadero en el mundo ficcional | enunciado, tipo, capítulo que lo establece, estado, alcance temporal, origen, fragmento que lo sostiene, **versión desde**, **versión hasta** |
| Estado de hecho | Grado de fijación de un hecho | propuesto, adoptado, descartado, retconeado, refutado |
| Snapshot | Estado derivado del mundo al cierre de un capítulo | personajes presentes, ubicaciones, relaciones, momento de la fábula |
| Promesa narrativa | Expectativa abierta ante el lector | tipo, capítulo de apertura, capítulo de pago, estado |
| Estado de promesa | Situación de la promesa | pendiente, pagada, rota |
| Contradicción de canon | Conflicto detectado entre dos hechos | hechos implicados, tipo, gravedad, resolución |
| Retcon | Reescritura deliberada del canon previo | hecho antiguo, hecho nuevo, capítulos afectados |

**Vigencia, y por qué no basta con el estatus.** Un retcon **no sobrescribe un hecho en su sitio**: cierra el viejo poniéndole `versión hasta` y abre el nuevo con `versión desde`. De ahí salen dos reglas que se confunden con facilidad. La primera: **el `Estado de hecho` describe la versión vigente, no la historia**. La segunda, que es consecuencia: **toda consulta por versión se resuelve con la vigencia, nunca con el estatus** —en la versión anterior, un hecho que hoy está `retconeado` seguía siendo verdad, y filtrar por estatus lo dejaría fuera—. Sin esta separación, una versión publicada se queda sin la base que la sostiene: Lean no se puede volver a ejecutar sobre ella y `query_story_bible` no puede responder por versión.

**Regla de actualización.** El canon solo cambia cuando un capítulo se acepta. Un borrador rechazado no deja rastro; si lo dejara, cualquier iteración fallida contaminaría el estado del mundo y la regeneración dirigida acabaría regenerando capítulos por hechos que nunca se escribieron.

**Uso de hecho.** Cada `Hecho` registra en qué capítulos se usa, en una relación N:M con `Capítulo`. No es metadato: es lo único que hace posible responder «si el perro pasa a llamarse Nala, ¿qué capítulos hay que reescribir?» sin releer la novela entera. Un hecho sin uso registrado es un hecho que la regeneración no sabrá propagar.

**El uso también tiene vigencia.** No basta con versionar el `Hecho`: la relación con el `Capítulo` lleva su propio `versión desde` y `versión hasta`, porque un capítulo puede dejar de mencionar un hecho al regenerarse sin que el hecho cambie. Sin eso, preguntar «qué capítulos usaban este hecho en la versión 2» devuelve los de la versión vigente, y tanto el análisis de impacto como la marca de capítulos modificados responden por la versión equivocada. **Invariante**: la vigencia de un uso está contenida en la del hecho que usa; un capítulo no puede apoyarse en un hecho que aún no existía o que ya se había cerrado.

**Canon extraído.** El canon crece sobre todo por extracción, no por declaración: al aceptar un capítulo se leen los hechos que ha introducido sin que nadie los hubiera previsto. Cada uno entra como `propuesto`, y lo que decide si pasa a `adoptado` es el **policy engine**, no una persona. Un hecho `propuesto` no es canon: no se consulta, no entra en el contexto del capítulo siguiente y no sostiene ninguna verificación.

**Procedencia y anclaje.** Todo hecho declara de dónde viene —brief, texto libre o extracción— y qué fragmento del capítulo lo sostiene. Lo primero permite tratar con desconfianza lo que procede del texto libre. Lo segundo es lo que impide que el canon derive de la novela que dice representar: un hecho que no puede citar el fragmento que lo respalda no se consolida.

**Retcon rutinario.** Al descubrir capítulo a capítulo, las contradicciones no son fallos del sistema sino subproducto normal del método. El retcon tiene que ser barato: identificar los capítulos afectados por el cambio de un hecho a través de su uso registrado, marcarlos `obsoleto` y encolar su reescritura, sin tocar el resto de la obra.

**La cronología no es una clase aparte.** Lo que la verificación formal lee —evento, momento, personajes presentes, lugar— ya está en `Evento` y en sus puentes a `Personaje` y `Lugar`. Darle una clase propia sería nombrar dos veces lo mismo.

## Capa 3 — Contexto y memoria

Generar el capítulo N es un problema de recuperación, compresión y proyección de estado bajo un presupuesto de tokens repartido explícitamente.

**Tipos de memoria**

| Clase | Definición | Contenido |
| --- | --- | --- |
| Memoria episódica | Lo que pasó, en su forma textual | capítulos literales, diálogos |
| Memoria semántica | Lo que es verdad, derivado | hechos, snapshots, reglas |
| Memoria procedural | Cómo se escribe esta obra | guía de estilo, voz narrativa, muestras de voz |

**Capas del contexto de un capítulo**

| Capa | Contenido |
| --- | --- |
| Invariante | Premisa, brief de novela, dedicatoria, guía de estilo, voz narrativa |
| Estructural | Brief de capítulo y su restricción de destino |
| Estado | Snapshot al cierre del capítulo N−1, no el texto anterior |
| Local | Últimos capítulos literales, para continuidad de prosa |
| Recuperado | Fragmentos filtrados por las entidades del brief de capítulo |
| Estilo | Muestras de voz de los personajes presentes |
| Anticontexto | Metáforas ya usadas, repeticiones, clichés vetados y las palabras prohibidas de la novela |

El reparto de la ventana entre estas siete capas, más el Margen, vive en `config/thresholds.yaml`: es la fuente única de cifras del sistema y no se copia a este documento. Aquí vive qué contiene cada capa; allí, cuánto ocupa.

**Dos presupuestos, no uno.** La ventana limita **una** petición; el pool de tokens concurrentes limita **cuántas caben a la vez**. Son cifras distintas aunque coincidan, viven en claves distintas del mismo fichero y confundirlas produce o bien un sistema que no paraleliza nada o bien uno que desborda el límite concurrente sin que ningún prompt individual lo supere.

**Otras clases**

- **Brief de capítulo**: encargo que define qué debe lograr el capítulo. Es mínimo por diseño —estado de entrada más restricción de destino— y es el contrato contra el que se valida el resultado.
- **Resumen de capítulo**: versión comprimida de un capítulo aceptado, para construir el contexto de los siguientes sin gastar la ventana en texto literal.
- **Jerarquía de compresión**: tres niveles —resumen de obra, resumen de capítulo, capítulo literal— que permiten ajustar el zoom según el presupuesto disponible.
- **Política de recuperación**: recuperar por entidades declaradas en el brief y solo después ordenar por similitud; la similitud sola trae fragmentos parecidos en tono e irrelevantes en estado.
- **Anticontexto**: la capa que casi nadie modela y la que más mejora el resultado. Aquí carga además las palabras prohibidas de la novela, de modo que el modelo las evite antes de que el guardrail tenga que rechazar el capítulo.
- **Ventana efectiva**: porción del contexto que el modelo realmente atiende; no coincide con la ventana nominal.

## Capa 4 — Calidad y validadores

Cada dimensión necesita definición, validador, tipo, punto de ejecución y nombre de score. Sin las cinco cosas no es una métrica, es una opinión.

Los **tipos** son cuatro: `programático` (decide un proceso determinista), `semántico` (decide un modelo con rúbrica), `formal-Lean` (se demuestra sobre la cronología) y `revisión humana`. Los **puntos de ejecución** son cinco: `hook de policy`, `hook de capítulo`, `rol editor`, `gate de publicación` y `export`. Los cuatro primeros deciden si un capítulo o una versión siguen adelante; **`export` corre después de publicar**, sobre un artefacto derivado de una versión ya válida, y por eso no bloquea nada: lo que caza es que el fichero entregado no diga lo mismo que lo que se validó.

| Dimensión | Qué mide | Tipo | Punto de ejecución |
| --- | --- | --- | --- |
| Conformidad de schema | El brief y la salida de cada rol cumplen su schema | programático | hook de policy |
| Ausencia de palabras prohibidas | Ninguna palabra vetada sobrevive en el capítulo | programático | hook de policy |
| Ortografía exacta de nombres | Destinatario y personajes escritos como en la story bible | programático | hook de capítulo |
| Longitud | El capítulo cae dentro del rango declarado | programático | hook de capítulo |
| Consistencia fáctica | Ningún enunciado contradice el canon vigente | programático + semántico | hook de capítulo |
| Calidad de prosa | Eco de n-gramas, clichés, muletillas, varianza de frase, giros típicos de texto generado | programático | hook de capítulo |
| Integridad de POV y voz narrativa | Persona, tiempo verbal y focalización se mantienen | programático | hook de capítulo |
| Cumplimiento del brief de capítulo | El capítulo satisface su restricción de destino | programático | hook de capítulo |
| Integración natural de la personalización | Los elementos personalizados están tejidos, no insertados | semántico | rol editor |
| Reconocibilidad del destinatario | El destinatario se reconocería en el texto | semántico + revisión humana | rol editor · revisión |
| Adecuación del tono | El registro corresponde a la edad y la ocasión | semántico | rol editor |
| Coherencia de personajes | Las acciones encajan con deseo, herida y arco | semántico | rol editor |
| Ritmo entre capítulos | Alternancia de densidad y respiro a lo largo de la obra | semántico | rol editor |
| Invención sobre el destinatario | Ningún hecho personal sobre el destinatario que no venga del brief o del texto libre | programático + semántico | rol editor |
| Temas excluidos | Los temas que el comprador vetó no aparecen, aunque ninguna palabra prohibida los nombre | semántico | rol editor |
| Cumplimiento de reglas del mundo | Ninguna `Regla del mundo` salida del brief se viola | programático | hook de capítulo |
| Legibilidad | El texto se lee a la altura de la edad del destinatario | programático | rol editor |
| Consistencia temporal | Los eventos respetan el orden cronológico declarado | formal-Lean | gate de publicación |
| Consistencia espacial | Ningún personaje está en dos lugares en el mismo momento, ni aparece tras un evento excluyente | formal-Lean | gate de publicación |
| Coherencia de edad | La edad de cada personaje en cada evento cuadra con su fecha de nacimiento | formal-Lean | gate de publicación |
| Cumplimiento de elementos obligatorios | Todo elemento obligatorio aparece en al menos un capítulo | programático | gate de publicación |
| Cierre del arco | Ninguna promesa queda pendiente al terminar la novela | programático + semántico | gate de publicación |
| Render visual | Índice, ficha de personajes y lugares y portada renderizan sin error | programático | gate de publicación |
| Paridad PDF ↔ web | El PDF exportado contiene lo mismo que la lectura web: capítulos, títulos, índice y dedicatoria | programático | export |
| Estructura de la edición | La obra tiene los capítulos que declara, con títulos únicos y no vacíos | programático | gate de publicación |
| Fidelidad de la regeneración | Los capítulos no afectados quedan idénticos, la marca de cambios es exacta y la versión anterior sigue entera | programático | gate de publicación |

**Aspiraciones sin validador.** Dos cosas que el sistema persigue y ninguna fila mide, declaradas aquí para que nadie las confunda con cobertura:

| Aspiración | Por qué no tiene validador |
| --- | --- |
| Originalidad | El fallo característico de un modelo no es escribir mal sino escribir correcto y genérico. La parte con forma reconocible —ecos, muletillas, clichés— la absorbe `calidad_prosa`; lo que queda no tiene criterio de aprobado escrito, y sin criterio ningún validador puede suspender |
| Satisfacción del comprador | Es la definición del criterio, no una consecuencia suya. Se estima por la revisión humana y no se automatiza |

**Verificación formal de la historia.** Las tres dimensiones `formal-Lean` se demuestran sobre un fichero generado desde la story bible con los hechos temporales: eventos, momento, personajes presentes, lugar, fechas de nacimiento y eventos excluyentes. Si la demostración falla, la versión no se publica y el fallo vuelve al editor como feedback. Lo que Lean verifica es la **historia**; el comportamiento del harness se verifica aparte y vive en la capa 5.

**Guardrail de palabras prohibidas**

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Palabra prohibida | Término que no puede aparecer en el texto | forma, nivel, origen, novela (si el nivel lo es) |
| Nivel de palabra prohibida | Alcance de la prohibición | global, perfil, novela |
| Normalización | Transformación que se aplica al texto y a la palabra antes de compararlos | conjunto de reglas, declarado en `config/thresholds.yaml` |
| Coincidencia | Detección de una palabra prohibida en un capítulo | palabra, nivel, capítulo, posición, intento, decisión |
| Límite de reescrituras | Número de veces que un capítulo vuelve al redactor antes de detener la generación | valor, alcanzado |

Los tres niveles: **global** son insultos y términos ofensivos, iguales para toda novela; **perfil** se deriva de la edad del destinatario y del tipo de ocasión; **novela** la define el comprador en la configuración —el nombre de una expareja, un tema que no quiere leer—.

**Por qué `perfil` es el tercer nivel.** Es el único de los tres que el comprador no puede enumerar y el sistema sí puede derivar solo: nadie sabe de antemano qué léxico es inadecuado para un niño de siete años, y sin este nivel una novela infantil queda protegida exactamente igual que una para adultos, es decir, solo por la lista de insultos. Es además el único que cierra sobre texto ya escrito la contradicción edad↔tono que el brief solo detecta antes de escribir.

Los tres niveles se aplican en conjunto y gana el más restrictivo. Toda coincidencia queda en el audit log y en Langfuse; agotado el límite de reescrituras, la generación se detiene y lo informa.

**Defecto.** Incumplimiento concreto de una dimensión detectado en un borrador: dimensión violada, gravedad, alcance y localización en el texto. Es lo que un informe de crítica enumera.

**Clasificación del defecto.** Un *defecto local* se corrige reescribiendo el capítulo. Un *defecto sistémico* invalida la planificación y obliga a replanificar los capítulos pendientes. Distinguirlos determina la ruta de corrección y evita parchear síntomas de un problema estructural.

**Rúbrica.** Criterios y escala con los que se puntúa lo semántico. La misma rúbrica la usan el rol editor y el revisor humano, que es lo que permite comparar el juicio del modelo con el de una persona; dos rúbricas distintas harían la comparación imposible.

Sus **seis criterios** son los que el encargo nombra, uno por dimensión semántica:

| Criterio de la rúbrica | Dimensión que puntúa |
| --- | --- |
| Continuidad | `consistencia_factica` |
| Tono | `adecuacion_tono` |
| Arco de la historia | `cierre_arco` |
| Coherencia de personajes | `coherencia_personajes` |
| Ritmo entre capítulos | `ritmo` |
| Integración natural de la personalización | `personalizacion_natural` |

**Cada criterio se puntúa por separado y cada puntuación va justificada.** Un único número para toda la rúbrica no dice qué hay que arreglar, y una puntuación sin justificación no se puede contrastar con la del revisor humano: eso es lo que hace que `Score` lleve justificación cuando el validador es semántico. `reconocibilidad` se puntúa con la misma escala pero fuera de estos seis, porque solo el revisor humano puede cerrarla.

**Cómo se mide un validador.** Un umbral solo significa algo si el validador que lo aplica acierta, y eso se mide separando: se parte de capítulos ya aceptados, se les inyectan defectos conocidos y se comprueba cuántos caza y cuántos se inventa.

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Defecto inyectado | Defecto conocido que se introduce a propósito en un capítulo aceptado para medir si un validador lo detecta | dimensión que viola, capítulo de origen, transformación aplicada, detectado por |
| Brief de prueba | Brief fijo del corpus de evaluación, diseñado para ejercitar un conjunto de validadores | identificador, qué modo de fallo provoca, validadores que debe disparar |

`Defecto inyectado` es lo que hace calibrables los umbrales marcados `[mutación]` en `config/thresholds.yaml`, y es la entrada de la precisión y la cobertura que se exige a cada validador. Un validador por debajo de esas dos cifras no aprueba ni suspende: adivina.

`Brief de prueba` es la unidad de la evaluación del sistema. La tabla brief × validador del encargo tiene una columna por cada uno, y sin la clase no hay nada que nombre sus filas.

**Los dos se quedan fuera de la story bible**, y es deliberado: no son verdad de ninguna novela sino instrumental de medida. Viven con el resto del corpus de evaluación, no en `data/storymaker.db`.


## Capa 5 — Proceso, harness y verificación formal del sistema

El ciclo es entrevistar → planificar → escribir → validar → publicar, con regeneración dirigida cuando el lector pide un cambio. Consolidar es lo único que modifica el canon; extraer es lo que devuelve los hechos a la story bible.

**Roles**

| Rol | Responsabilidad |
| --- | --- |
| Entrevistador | Recoge los datos del destinatario y produce el brief de novela validado |
| Planificador | Convierte el brief en el esquema de capítulos con sus restricciones de destino |
| Redactor | Genera la prosa del capítulo a partir del brief de capítulo y el contexto |
| Editor / Crítico | Puntúa el capítulo contra las dimensiones semánticas y aplica correcciones |
| Extractor | Lee el capítulo aceptado y propone los hechos que ha introducido |

**Componentes que no son roles**

| Componente | Responsabilidad |
| --- | --- |
| Policy engine | Decide lo que antes decidía el autor humano: adoptar o descartar un hecho, aceptar o devolver un capítulo, detener la generación |
| Guardrail | Aplica el veto de palabras prohibidas sobre cada capítulo antes de aceptarlo |
| Hook de policy | Punto de ejecución de los validadores de schema y de palabras prohibidas |
| Hook de capítulo | Punto de ejecución de los validadores programáticos de continuidad y prosa |
| Gate de publicación | Última puerta: sin todos sus validadores en verde no se publica una versión |
| Audit log | Registro de cada decisión del policy engine, con la regla aplicada y su resultado |

**El verificador de continuidad no es un rol.** Nombra al conjunto de validadores programáticos del hook de capítulo. La continuidad aquí se decide contra datos estructurados —hechos en la story bible, cronología en Lean—, y ambas son deterministas: un rol que opinara sobre ellas duplicaría peor lo que ya se demuestra.

**Humanos**

| Humano | Qué hace |
| --- | --- |
| Lector | Lee la novela publicada y pide cambios sobre ella. Es un papel, no una persona distinta: lo ocupa el comprador o el destinatario |
| Revisor humano | Evalúa al menos una novela completa con la misma rúbrica que el rol editor |

El autor humano ha salido del bucle de producción: la generación es automática y sus decisiones son ahora políticas del policy engine, trazadas en el audit log.

**Artefactos**

| Artefacto | Definición |
| --- | --- |
| Story bible | Conjunto consolidado de personajes, lugares, hechos y cronología. Es el canon consultable de la Capa 2 |
| Esquema | Plan de capítulos con sus funciones dramáticas y sus restricciones de destino |
| Brief de capítulo | Encargo concreto de un capítulo |
| Borrador | Salida de una generación, aún no aceptada |
| Informe de crítica | Defectos detectados, clasificados y priorizados |
| Versión de novela | Estado del texto con los capítulos que lo componen. Nace `candidata`; pasa a `publicada` solo si pasa el gate completo, `render_visual` incluido, y si no queda `rechazada`. Solo una `publicada` es la versión vigente |
| Checkpoint | Último capítulo completado, desde el que se reanuda una generación interrumpida |

**Versionado y regeneración**

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Solicitud de cambio | Petición del lector sobre un hecho o un fragmento | enunciado, hecho afectado, origen, estado |
| Análisis de impacto | Cálculo de los capítulos que usan el hecho afectado | solicitud, capítulos afectados, hechos derivados |
| Regeneración dirigida | Reescritura de solo los capítulos afectados | análisis de impacto, capítulos regenerados, versión resultante |

**La versión anterior se conserva siempre.** Una regeneración produce una versión nueva y no sobrescribe la anterior: sin eso, un cambio pedido por el lector que empeora el resultado no tiene marcha atrás. Que un capítulo haya cambiado respecto a la versión anterior es atributo del vínculo entre versión y capítulo, no una clase: nada se pregunta sobre esa marca que no sea a través de una versión concreta.

**El formato de lectura es la web, y el PDF es un export de ella.** La novela se lee en el frontend, y de ese mismo render sale el PDF que se entrega. Dos consecuencias para el modelo: la `Solicitud de cambio` llega siempre desde la propia página, así que su `origen` deja de distinguir formatos y solo registra desde qué capítulo o fragmento se pidió; y **no hay clase `Página de novedades`**, porque qué capítulos cambiaron ya vive en la marca del vínculo entre versión y capítulo, y presentarlo al principio del export es maquetación, no vocabulario del dominio.

**Estados de la novela**: `configurando` → `planificando` → `escribiendo` → `validando` → `publicando` → `publicada`. Desde `publicada`, una solicitud de cambio lleva a `regenerando` y de ahí de nuevo a `validando`. `detenida` es terminal y se alcanza al agotar el límite de intentos.

**Estados de un capítulo**: `pendiente` → `escribiendo` → `validando` → `aceptado`. Una validación fallida lleva a `reescribiendo` e incrementa el contador de intentos; agotado el límite, el capítulo queda `agotado` y detiene la novela. Un retcon o una replanificación marcan un capítulo aceptado como `obsoleto`, que vuelve a `pendiente`. Solo la transición a `aceptado` escribe en el canon.

Los dos conjuntos de estados son los mismos que la especificación formal del sistema, uno a uno y sin estados intermedios añadidos. Si el código necesita un estado que no está aquí, es este documento el que se actualiza primero.

**Verificación formal del sistema**

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Especificación del harness | Modelo formal del flujo de generación como máquina de estados | acciones, estados, correspondencia con el código |
| Invariante de seguridad | Propiedad que debe cumplirse en todo estado alcanzable | enunciado, alcance |
| Propiedad de liveness | Propiedad que garantiza que el sistema progresa | enunciado |
| Contraejemplo | Traza que viola una propiedad, hallada por el comprobador de modelos | propiedad violada, traza, cambio que provocó |

Lean verifica la **historia**; la especificación del harness verifica el **sistema**. Son dos verificaciones formales con objetos distintos y no se sustituyen: una novela puede tener una cronología impecable generada por un harness que publica capítulos sin validar.

**Trazabilidad.** Se expresa en términos de observabilidad, y sus clases son las que se consultan a posteriori:

| Clase | Definición | Alcance |
| --- | --- | --- |
| Sesión | Todo lo relativo a una novela | entrevista, generación y regeneraciones posteriores |
| Traza | Una generación completa | inicial o regeneración |
| Span | Un paso identificable dentro de una traza | un rol o una llamada a tool |
| Score | Resultado de un validador asociado a una traza | uno por validador ejecutado; lleva valor y, si el validador es semántico, la **justificación** de ese valor |
| Versión de prompt | Identificador versionado del prompt con que se generó un capítulo | permite atribuir un resultado a un prompt concreto |

Sin esto no se puede reproducir un resultado bueno, ni diagnosticar uno malo, ni decir qué versión de prompt produjo qué. El comprobador de modelos no participa: corre en desarrollo, no en cada generación.

## Relaciones del dominio

Las relaciones son lo que convierte un glosario en una ontología: sin ellas no se pueden responder las preguntas de competencia.

| Sujeto | Relación | Objeto | Cardinalidad |
| --- | --- | --- | --- |
| Comprador | encarga | Obra | 1:N |
| Comprador | regala a | Destinatario | 1:N |
| Obra | celebra | Ocasión | N:1 |
| Entrevista | produce | Brief de novela | 1:1 |
| Brief de novela | declara | Elemento personalizado | 1:N |
| Brief de novela | adjunta | Texto libre aportado | 1:N |
| Brief de novela | acusa | Dato faltante | 1:N |
| Brief de novela | acusa | Contradicción de brief | 1:N |
| Texto libre aportado | aporta | Hecho | 1:N |
| Texto libre aportado | contiene | Fragmento sospechoso | 1:N |
| Obra | se compone de | Capítulo | 1:N |
| Obra | abre con | Dedicatoria | 1:1 |
| Esquema | fija | Restricción de destino | 1:N |
| Restricción de destino | acota | Brief de capítulo | 1:1 |
| Brief de capítulo | encarga | Capítulo | 1:1 |
| Capítulo | se narra desde | Personaje (POV) | N:1 |
| Capítulo | transcurre en | Lugar | N:1 |
| Capítulo | avanza | Hilo de trama | N:M |
| Capítulo | establece | Hecho | 1:N |
| Capítulo | usa | Hecho | N:M, con vigencia propia |
| Capítulo | abre / paga | Promesa narrativa | N:M |
| Capítulo | produce | Snapshot | 1:1 |
| Capítulo | se resume en | Resumen de capítulo | 1:1 |
| Elemento personalizado | aparece en | Capítulo | N:M |
| Evento | se narra en | Capítulo | N:M |
| Evento | ocurre en | Lugar | N:1 |
| Evento | involucra a | Personaje | N:M |
| Evento excluyente | excluye a | Personaje | N:M |
| Personaje | recorre | Arco | 1:1 |
| Hecho | contradice | Hecho | N:M |
| Hecho | proyecta | Snapshot | N:M |
| Contradicción de canon | se resuelve con | Retcon | N:1 |
| Retcon | cierra | Hecho (antiguo) | N:1 |
| Retcon | abre | Hecho (nuevo) | N:1 |
| Retcon | marca obsoleto | Capítulo | 1:N |
| Extracción | propone | Hecho | 1:N |
| Policy engine | decide sobre | Hecho | 1:N |
| Policy engine | registra | Decisión de policy | 1:N |
| Invalidación de restricción | dispara | Replanificación de capítulos pendientes | N:1 |
| Replanificación de capítulos pendientes | revisa | Esquema | N:1 |
| Borrador | realiza | Brief de capítulo | N:1 |
| Informe de crítica | evalúa | Borrador | 1:1 |
| Defecto | viola | Dimensión de calidad | N:1 |
| Validador | mide | Dimensión de calidad | N:1 |
| Validador | emite | Score | 1:N |
| Palabra prohibida | se detecta como | Coincidencia | 1:N |
| Coincidencia | devuelve | Capítulo | N:1 |
| Versión de novela | incluye | Capítulo | N:M |
| Versión de novela | sucede a | Versión de novela | N:1 |
| Lector | pide | Solicitud de cambio | 1:N |
| Solicitud de cambio | afecta a | Hecho | N:1 |
| Solicitud de cambio | produce | Análisis de impacto | 1:1 |
| Análisis de impacto | ordena | Regeneración dirigida | 1:1 |
| Regeneración dirigida | produce | Versión de novela | 1:1 |
| Sesión | agrupa | Traza | 1:N |
| Traza | contiene | Span | 1:N |
| Traza | recoge | Score | 1:N |
| Span | usa | Versión de prompt | N:1 |

## Nomenclatura

Un concepto, un nombre **en cada ámbito**. Esta tabla fija la correspondencia entre el término del dominio y su identificador en código, que es vocabulario compartido y por tanto ontología. Los nombres de tabla viven en `architecture.md` § Story bible y los de span y score en `docs/verification.md`: son materialización, no vocabulario.

| Dominio (español) | Código |
| --- | --- |
| Entrevistador | `interviewer` |
| Planificador | `planner` |
| Redactor | `writer` |
| Editor / Crítico | `editor` |
| Extractor | `extractor` |
| Policy engine | `PolicyEngine` |
| Guardrail | `Guardrail` |
| Story bible | `StoryBible` |
| Obra | `Obra` |
| Capítulo | `Capitulo` |
| Brief de novela | `BriefNovela` |
| Brief de capítulo | `BriefCapitulo` |
| Destinatario | `Destinatario` |
| Elemento personalizado | `ElementoPersonalizado` |
| Hecho | `Hecho` |
| Evento | `Evento` |
| Promesa narrativa | `Promesa` |
| Versión de novela | `VersionNovela` |
| Solicitud de cambio | `SolicitudCambio` |
| Sesión | — |
| Traza | — |
| Score | `Score` |
| Versión de prompt | `VersionPrompt` |

**Las dimensiones de calidad no están en esta tabla**, y no por olvido: su identificador —`consistencia_factica`, `nombres_exactos`— es el mismo en el fichero de umbrales, en el código y en Langfuse, así que no hay correspondencia que mantener, solo un nombre. Cuál le toca a cada dimensión lo dice `docs/verification.md`, porque **no es derivable del nombre en español**: «Ortografía exacta de nombres» es `nombres_exactos` y «Integridad de POV y voz narrativa» es `integridad_pov`.

## Preguntas de competencia

La ontología está validada cuando el sistema responde estas preguntas. Es el criterio de parada: evita modelar de más y detecta clases que faltan.

**Encargo y personalización**

1. ¿Qué comprador encargó esta novela, para qué destinatario, con qué ocasión y con qué dedicatoria?
2. ¿Qué elementos obligatorios del brief no aparecen en ningún capítulo?
3. ¿Qué datos faltan en el brief y cuáles se contradicen entre sí?
4. ¿Qué fragmentos del texto libre se usaron como hechos y cuáles se descartaron por sospechosos?
5. ¿En qué capítulos aparece un elemento personalizado dado?

**Estructura y plan**

6. ¿Qué restricción de destino acota el capítulo N?
7. ¿Qué restricciones de destino aún no escritas ha vuelto imposibles el canon vigente?
8. ¿Qué arcos e hilos de trama llevan más capítulos de los declarados sin avanzar?
9. ¿Qué reglas del mundo salidas del brief afectan a este capítulo?
10. ¿Qué voz narrativa —persona y tiempo verbal— declara esta novela, y la respeta el capítulo N?

**Canon y cronología**

11. ¿Qué capítulos usan un hecho dado?
12. ¿Dónde se estableció por primera vez un hecho, y qué fragmento del texto lo sostiene?
13. ¿Dónde está cada personaje y qué es verdad del mundo al cierre del capítulo N?
14. ¿Qué edad tiene un personaje en cada evento?
15. ¿Puede un personaje estar en dos lugares en el mismo momento?
16. ¿Qué personajes aparecen después de un evento que los excluye?
17. ¿Qué hechos entran en contradicción entre sí y cuál prevalece?
18. ¿Qué promesas siguen pendientes al llegar al último capítulo?

**Contexto**

19. ¿Qué debe entrar en el contexto para generar el capítulo N, y con qué presupuesto por capa?

**Versiones y regeneración**

20. ¿Qué capítulos cambiaron entre dos versiones de la novela?
21. ¿Qué capítulos hay que regenerar si cambia un hecho dado?
22. ¿Qué versión de la novela estaba publicada antes de la última regeneración?
23. ¿Qué lector pidió este cambio y desde qué capítulo de la lectura lo pidió?

**Calidad y guardrails**

24. ¿Qué validadores fallaron en esta versión y con qué score?
25. ¿Qué palabras prohibidas se detectaron, en qué nivel y en qué capítulo?
26. ¿Este defecto es local o exige replanificar los capítulos pendientes?
27. ¿Qué puntuó el revisor humano frente a lo que puntuó el rol editor, criterio a criterio de la misma rúbrica?

**Proceso y observabilidad**

28. ¿Desde qué capítulo se reanuda la generación tras un fallo?
29. ¿Cuántos reintentos lleva un capítulo y cuánto le queda para agotarse?
30. ¿Qué versión de prompt produjo este capítulo?
31. ¿Qué decidió el policy engine sobre un hecho concreto, y con qué regla?
32. ¿Cuántos tokens y cuánto coste lleva esta novela, por capítulo y en total?
33. ¿Qué contraejemplos encontró el comprobador de modelos y qué cambio en el código provocó cada uno?

**Medida de los propios validadores**

34. ¿Qué precisión y qué cobertura tiene un validador sobre el corpus de `Defecto inyectado`, y qué defectos se le escaparon?
35. ¿Qué `Brief de prueba` ejercita cada validador, y cuáles pasaron y cuáles fallaron en la última ejecución?

**Cobertura.** Añadir una pregunta nueva obliga a comprobar si el modelo la soporta; si no, falta una clase o una relación. Quitar una clase obliga a comprobar qué pregunta deja de responderse.
