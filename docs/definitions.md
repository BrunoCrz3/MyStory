# Ontología de generación de novelas — Definiciones

2026-09-21 · @Bruno Cruz

Este documento define el vocabulario del dominio: qué clases existen, qué atributos tiene cada una y qué relaciones las unen. Cubre cinco capas: obra, canon, contexto, calidad y proceso. Los diagramas viven en el documento de conocimiento de dominio.

## Convenciones del modelo

La ontología se organiza en cinco capas con ciclos de vida distintos; mezclarlas es el error de diseño más común.

| Capa | Responde a | Cambia cuando |
| --- | --- | --- |
| Obra | ¿De qué está hecha la novela? | Se replanifica la estructura |
| Canon | ¿Qué es verdad en el punto t del texto? | Se acepta una escena |
| Contexto | ¿Qué ve el modelo al generar? | En cada llamada de generación |
| Calidad | ¿Esto está bien? | Se ajustan umbrales o criterios |
| Proceso | ¿Quién hace qué y en qué orden? | Se cambia el pipeline |

Criterio de inclusión: una clase entra en el modelo solo si alguna pregunta de competencia (última sección) la necesita. Convenciones de notación: `Clase` en mayúscula inicial, `atributo` en minúscula, `relación` en verbo. `t` denota una posición en el discurso, no una fecha del mundo ficcional.

## Modo de autoría: híbrido

La obra se planifica a nivel de acto y se descubre a nivel de escena. El esquema fija el destino y los puntos de giro; la escena concreta se genera sin guion de beats y lo que emerge se reincorpora al plan.

| Nivel | Modo | Fuente de verdad |
| --- | --- | --- |
| Obra y acto | Planificado | Esquema |
| Capítulo | Planificado con holgura | Esquema revisable |
| Escena | Descubrimiento acotado | Canon |
| Beat | Descubrimiento libre | Texto generado |

**Clases propias de este modo**

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Restricción de destino | Lo que la escena no puede cambiar sin replanificar | tipo (estado final, revelación, posición de personaje), alcance |
| Hallazgo | Elemento surgido al escribir y no previsto en el plan | tipo (hecho, promesa, motivo, personaje), escena de origen, estado de adopción |
| Estado de hallazgo | Situación del hallazgo en el ciclo de adopción | propuesto, adoptado, descartado, conflictivo, integrado |
| Extracción | Lectura automática de una escena aceptada para detectar hallazgos | entradas, hallazgos propuestos, confianza |
| Replanificación rodante | Revisión del esquema a la luz de los hallazgos acumulados | disparador, escenas afectadas, cambios al esquema |
| Deriva | Distancia acumulada entre lo escrito y el esquema vigente | medida, umbral de disparo |

**Reglas de gobierno**

- La escena descubre *cómo*, no *hacia dónde*: cambiar el destino exige pasar por replanificación, no se decide dentro de la escena.
- Nada se declara por adelantado salvo las restricciones de destino; el resto del canon se extrae después de aceptar la escena.
- El retcon deja de ser excepción y pasa a ser operación rutinaria, con propagación a las escenas afectadas.
- La replanificación se dispara por umbral de deriva o por cadencia fija (cada N escenas o al cerrar capítulo), nunca en mitad de una escena.

## Capa 1 — Obra

La **Escena** es la unidad atómica de generación y validación: todo lo demás se planifica hacia ella o se deriva de ella.

**Clases estructurales** (contenedoras, jerárquicas)

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Obra | La novela completa | premisa, género, extensión objetivo, público |
| Parte / Acto | Bloque de estructura dramática | función dramática, punto de giro que lo cierra |
| Capítulo | Unidad de publicación y lectura | POV dominante, gancho de cierre |
| Escena | Unidad de acción continua en tiempo y lugar | objetivo, conflicto, resultado, POV, lugar, momento, estado de entrada y salida |
| Beat | Mínimo cambio de valor emocional dentro de una escena | valor inicial, valor final |

**Entidades narrativas** (sustantivas, atraviesan la estructura)

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Personaje | Agente con deseo y capacidad de acción | deseo, necesidad, herida, rol narrativo, arco, voz, estado epistémico |
| Voz | Firma lingüística de un personaje | léxico, registro, sintaxis, muletillas, temas recurrentes |
| Arco | Trayectoria de transformación | estado inicial, puntos de giro, estado final, escenas que lo avanzan |
| Hilo de trama | Cadena causal de eventos con tensión propia | tipo (principal, secundario), pregunta dramática, estado |
| Lugar | Espacio donde ocurre acción | geografía, atmósfera sensorial, reglas propias |
| Facción | Grupo con agencia colectiva | objetivo, recursos, relaciones con otras facciones |
| Artefacto | Objeto con carga narrativa | propiedades, poseedor actual, deuda narrativa que genera |
| Novum | Punto de divergencia especulativa respecto al mundo real | mecanismo, límites, consecuencias en cascada |
| Regla del mundo | Restricción que el texto no puede violar | enunciado, alcance, excepciones declaradas |
| Término canónico | Neologismo o nombre propio del mundo | forma, definición, primera aparición, variantes prohibidas |
| Tema | Idea que la obra interroga | enunciado, motivos que lo encarnan |
| Motivo | Imagen u objeto que recurre con sentido | forma, apariciones, evolución |
| Voz narrativa | Configuración del narrador | persona, tiempo verbal, distancia, focalización, ratio escena/resumen |
| Evento | Suceso de la fábula, situado en el orden cronológico ficcional | qué ocurre, momento en la fábula, participantes, duración |
| Objetivo | Lo que un personaje persigue en un tramo de la obra | enunciado, alcance (de escena, de arco), tipo (deseo, necesidad), estado |

**Fábula y discurso.** La *fábula* es el conjunto de eventos en orden cronológico ficcional; el *discurso* es el orden y la forma en que se narran. Son dos clases separadas unidas por una relación `se narra en`. Sin esta separación no se pueden gestionar analepsis, revelaciones diferidas ni tramas con manipulación temporal, frecuentes en ciencia ficción.

## Capa 2 — Canon y estado

Una novela es una secuencia de transiciones de estado: toda escena nueva debe ser consistente con el estado vigente en su punto de inserción. Esta capa es la más difícil y la que más fallos de consistencia previene.

| Clase | Definición | Atributos clave |
| --- | --- | --- |
| Hecho canónico | Enunciado verdadero en el mundo ficcional | texto, tipo, escena que lo establece, estatus, alcance temporal |
| Estatus de hecho | Grado de fijación de un hecho | confirmado, implícito, provisional, retconeado, refutado |
| Snapshot de mundo | Estado derivado del mundo en el punto t | personajes vivos, ubicaciones, posesiones, relaciones, fecha ficcional |
| Estado epistémico | Qué sabe un agente y desde cuándo | agente, hecho, escena en que lo aprende, certeza |
| Ironía dramática | Desfase entre lo que sabe el lector y lo que sabe un personaje | hecho, quién lo sabe, quién no |
| Promesa narrativa | Expectativa abierta ante el lector | tipo (setup, pregunta, amenaza, deuda), escena de apertura, escena de pago, estado |
| Estado de promesa | Situación de la promesa | pendiente, pagada, rota, subvertida |
| Revelación | Hecho que pasa de oculto a conocido | hecho, destinatario (lector o personaje), escena mínima permitida |
| Contradicción | Conflicto detectado entre dos hechos | hechos implicados, tipo, gravedad, resolución |
| Retcon | Reescritura deliberada del canon previo | hecho antiguo, hecho nuevo, escenas afectadas |

**Regla de actualización.** El canon solo cambia cuando una escena se acepta. Un borrador rechazado no deja rastro en el canon; si lo dejara, cualquier iteración fallida contaminaría el estado del mundo.

**Visibilidad.** Cada hecho lleva dos marcas independientes: qué personajes lo conocen y si el lector lo conoce. Confundirlas produce los fallos más costosos del género: personajes que actúan con información que aún no han recibido, o revelaciones que llegan después de haberse filtrado.

**Canon extraído.** En modo híbrido el canon crece sobre todo por extracción, no por declaración: al aceptar una escena se leen los hechos, promesas y motivos que ha introducido sin que nadie los hubiera previsto. Cada hallazgo entra como `propuesto` hasta que el autor lo adopta, lo descarta o lo corrige; adoptarlo es lo que lo convierte en canon consultable. El nombre no es `provisional` a propósito: esa palabra ya es un `Estatus de hecho` y un concepto no puede tener dos nombres.

**Retcon rutinario.** Al descubrir escena a escena, las contradicciones no son fallos del sistema sino subproducto normal del método. El modelo necesita, por tanto, un retcon barato: identificar las escenas afectadas por el cambio de un hecho, marcarlas `obsoleta` y encolar su reescritura, sin tocar el resto de la obra.

## Capa 3 — Contexto y memoria

Generar la escena N es un problema de recuperación, compresión y proyección de estado bajo un presupuesto de tokens repartido explícitamente.

**Tipos de memoria**

| Clase | Definición | Contenido |
| --- | --- | --- |
| Memoria episódica | Lo que pasó, en su forma textual | escenas literales, diálogos |
| Memoria semántica | Lo que es verdad, derivado | hechos canónicos, snapshots, reglas |
| Memoria procedural | Cómo se escribe esta obra | guía de estilo, convenciones, voces |

**Capas del contexto de una escena**

| Capa | Contenido |
| --- | --- |
| Invariante | Premisa, guía de estilo, reglas de POV, glosario |
| Estructural | Brief de la escena y su lugar en el esquema |
| Estado | Snapshot en t(N), no el texto anterior |
| Local | Últimas escenas literales, para continuidad de prosa |
| Recuperado | Fragmentos filtrados por las entidades del brief |
| Estilo | Muestras de voz de los personajes presentes |
| Anticontexto | Metáforas ya usadas, repeticiones, clichés vetados, revelaciones prohibidas |

El reparto de la ventana entre estas siete capas, más el Margen, vive en `config/thresholds.yaml`: es la fuente única de cifras del sistema y no se copia a este documento. Aquí vive qué contiene cada capa; allí, cuánto ocupa.

**Otras clases**

- **Brief de escena**: encargo que define qué debe lograr la escena. Es el contrato contra el que se valida el resultado.
- **Jerarquía de compresión**: resúmenes multirresolución (escena → capítulo → acto) que permiten ajustar el zoom según el presupuesto disponible.
- **Política de recuperación**: recuperar por entidades declaradas en el brief, no por similitud semántica genérica; esta última trae fragmentos parecidos en tono pero irrelevantes en estado.
- **Anticontexto**: la capa que casi nadie modela y la que más mejora el resultado, porque combate la repetición y la regresión estilística a la media.
- **Ventana efectiva**: porción del contexto que el modelo realmente atiende; no coincide con la ventana nominal.

## Capa 4 — Calidad

Cada dimensión necesita definición, nivel de aplicación, método de medición y umbral. Sin las cuatro cosas no es una métrica, es una opinión.

| Dimensión | Qué mide | Nivel | Medición |
| --- | --- | --- | --- |
| Consistencia fáctica | Ningún hecho contradice el canon | Escena | Verificación contra hechos canónicos |
| Consistencia temporal | Los eventos respetan la cronología de la fábula | Obra | Orden de eventos vs. duraciones declaradas |
| Consistencia espacial | Ubicaciones y desplazamientos posibles | Capítulo | Snapshot de posiciones |
| Consistencia epistémica | Nadie usa información que no tiene | Escena | Estado epistémico del POV |
| Consistencia de caracterización | Acciones coherentes con deseo, herida y arco | Obra | Contraste con la ficha de personaje |
| Plausibilidad especulativa | El novum no viola sus propias reglas | Escena | Reglas del mundo declaradas |
| Distintividad de voz | Se identifica quién habla sin acotaciones | Escena | Clasificación ciega de diálogo |
| Calidad de prosa | Eco de n-gramas, clichés, palabras-filtro, varianza de frase | Frase | Métricas léxicas automáticas |
| Mostrar vs. contar | Proporción de escena dramatizada frente a resumen | Escena | Ratio escena/sumario |
| Integridad de POV | No hay fugas fuera de la focalización elegida | Escena | Detección de accesos mentales ajenos |
| Causalidad | La cadena avanza por «por tanto / pero», no por «y entonces» | Capítulo | Prueba de conectores causales |
| Curva de tensión | La tensión progresa y culmina donde debe | Obra | Puntuación de tensión por escena |
| Ritmo | Alternancia de densidad y respiro | Parte | Longitud y tipo de escena en secuencia |
| Carga expositiva | Infodumps y densidad de neologismos | Escena | Tokens de exposición sobre total |
| Sentido de la maravilla | Efecto estético propio del género | Obra | Evaluación cualitativa asistida |
| Originalidad | Distancia respecto a la prosa genérica del modelo | Obra | Comparación con línea base sin guía |
| Cumplimiento del brief | La escena hizo lo que se le encargó | Escena | Cotejo punto por punto |

**Regresión a la media.** El fallo característico de un modelo de lenguaje no es escribir mal, sino escribir correcto y genérico. La originalidad necesita métrica y presión propias; no aparece como efecto secundario de las demás.

**Defecto.** Incumplimiento concreto de una dimensión de calidad detectado en un borrador: dimensión violada, gravedad, alcance y localización en el texto. Es lo que un informe de crítica enumera.

**Clasificación del defecto.** Un *defecto local* se corrige reescribiendo en sitio. Un *defecto sistémico* invalida la planificación y obliga a replanificar. Distinguirlos determina la ruta de corrección y evita parchear síntomas de un problema estructural.

## Capa 5 — Proceso

El ciclo es planificar → generar → validar → consolidar → extraer, con replanificación periódica. Consolidar es lo único que modifica el canon; extraer es lo que devuelve los hallazgos al plan.

**Roles**

| Rol | Responsabilidad |
| --- | --- |
| Arquitecto | Premisa, mundo, estructura de actos |
| Planificador | Descompone la estructura en briefs de escena |
| Redactor | Genera la prosa a partir del brief y el contexto |
| Crítico | Evalúa contra las dimensiones de calidad |
| Verificador de continuidad | Contrasta la escena contra el canon |
| Editor | Aplica correcciones locales y de estilo |
| Autor humano | Decide dirección, acepta o rechaza, define el gusto |

**Artefactos**

| Artefacto | Definición |
| --- | --- |
| Biblia de la obra | Conjunto consolidado de mundo, personajes y reglas |
| Esquema | Estructura planificada de partes, capítulos y escenas |
| Brief de escena | Encargo concreto de una escena |
| Borrador | Salida de una generación, aún no aceptada |
| Informe de crítica | Defectos detectados, clasificados y priorizados |
| Versión | Estado del texto con su trazabilidad |
| Registro de generación | Prompt, modelo, parámetros y contexto usados |

**Estados de una escena**: `planificada` → `en borrador` → `en revisión` → `aceptada` → (`obsoleta` si un retcon la invalida). Solo la transición a `aceptada` escribe en el canon.

**Trazabilidad.** Cada versión guarda modelo, prompt, contexto ensamblado y semilla. Sin esto no se puede reproducir un resultado bueno ni diagnosticar uno malo.

**Roles añadidos por el modo híbrido**

| Rol | Responsabilidad |
| --- | --- |
| Extractor | Lee la escena aceptada y propone hallazgos: hechos, promesas, motivos |
| Replanificador | Revisa el esquema cuando la deriva supera el umbral |

**Dos bucles, no uno.** El bucle corto (por escena) genera, critica y consolida. El bucle largo (por capítulo o por umbral de deriva) recoge los hallazgos acumulados, revisa el esquema y reajusta las restricciones de destino de las escenas aún no escritas. Separarlos evita el fallo típico del descubrimiento asistido: replanificar en cada escena, que disuelve la estructura, o no replanificar nunca, que acumula deriva hasta hacer el esquema inservible.

## Relaciones del dominio

Las relaciones son lo que convierte un glosario en una ontología: sin ellas no se pueden responder las preguntas de competencia.

| Sujeto | Relación | Objeto | Cardinalidad |
| --- | --- | --- | --- |
| Obra | se compone de | Parte | 1:N |
| Capítulo | contiene | Escena | 1:N |
| Escena | se narra desde | Personaje (POV) | N:1 |
| Escena | transcurre en | Lugar | N:1 |
| Escena | avanza | Hilo de trama | N:M |
| Escena | establece | Hecho canónico | 1:N |
| Escena | abre / paga | Promesa narrativa | N:M |
| Escena | produce | Snapshot de mundo | 1:1 |
| Evento (fábula) | se narra en | Escena (discurso) | N:M |
| Personaje | conoce | Hecho canónico (desde escena) | N:M |
| Personaje | desea / necesita | Objetivo | 1:N |
| Personaje | recorre | Arco | 1:1 |
| Personaje | posee | Artefacto | N:M |
| Personaje | pertenece a | Facción | N:M |
| Hecho canónico | contradice | Hecho canónico | N:M |
| Brief de escena | encarga | Escena | 1:1 |
| Borrador | realiza | Brief de escena | N:1 |
| Informe de crítica | evalúa | Borrador | 1:1 |
| Defecto | viola | Dimensión de calidad | N:1 |
| Motivo | encarna | Tema | N:M |
| Novum | impone | Regla del mundo | 1:N |
| Novum | nombra | Término canónico | 1:N |
| Regla del mundo | configura | Facción | N:M |
| Facción | disputa | Artefacto | N:M |
| Artefacto | genera deuda | Promesa narrativa | 1:N |
| Hecho canónico | proyecta | Snapshot de mundo | N:M |
| Hecho canónico | visible para | Estado epistémico | 1:N |
| Contradicción | se resuelve con | Retcon | N:1 |

**Relaciones propias del modo híbrido**

| Sujeto | Relación | Objeto | Cardinalidad |
| --- | --- | --- | --- |
| Escena aceptada | revela | Hallazgo | 1:N |
| Extracción | propone | Hallazgo | 1:N |
| Hallazgo | se adopta como | Hecho canónico o Promesa | N:1 |
| Restricción de destino | acota | Brief de escena | 1:N |
| Esquema | fija | Restricción de destino | 1:N |
| Deriva | dispara | Replanificación rodante | N:1 |
| Replanificación rodante | revisa | Esquema | N:1 |
| Retcon | marca obsoleta | Escena | 1:N |

## Preguntas de competencia

La ontología está validada cuando el sistema responde estas preguntas. Es el criterio de parada: evita modelar de más y detecta clases que faltan.

**Canon y estado**

1. ¿Qué sabe un personaje concreto en el capítulo 12, y en qué escena lo aprendió?
2. ¿Dónde se estableció por primera vez un hecho del mundo?
3. ¿Qué hechos entran en contradicción entre sí y cuál prevalece?
4. ¿Qué escenas quedan invalidadas si se retconea un hecho?
5. ¿Dónde está cada personaje y qué posee al inicio de la escena N?

**Estructura y promesas**

6. ¿Qué promesas siguen sin pagar y desde hace cuántas escenas?
7. ¿Qué hilos de trama no avanzan desde hace más de X capítulos?
8. ¿Qué escenas hacen avanzar el arco de un personaje dado?
9. ¿Qué revelaciones están permitidas a partir de este punto del discurso?

**Contexto**

10. ¿Qué debe entrar en el contexto para generar la escena N, y con qué presupuesto?
11. ¿Qué metáforas, imágenes o formulaciones ya se han usado y conviene vetar?
12. ¿Qué fragmentos anteriores son relevantes para las entidades de este brief?

**Calidad y proceso**

13. ¿Qué dimensiones falla este borrador y con qué gravedad?
14. ¿Este defecto es local o exige replanificar?
15. ¿Con qué modelo, prompt y contexto se generó esta versión?
16. ¿Se distingue la voz de cada personaje sin acotaciones de diálogo?

**Modo híbrido**

17. ¿Qué hallazgos ha introducido esta escena que no estaban en el plan?
18. ¿Qué restricciones de destino acotan la escena N?
19. ¿Cuánta deriva hay entre lo escrito y el esquema vigente, y toca replanificar?
20. ¿Qué hallazgos siguen sin adoptar ni descartar?
21. ¿Qué escenas quedan obsoletas tras la última replanificación?

**Cobertura.** Añadir una pregunta nueva obliga a comprobar si el modelo la soporta; si no, falta una clase o una relación. Quitar una clase obliga a comprobar qué pregunta deja de responderse.
