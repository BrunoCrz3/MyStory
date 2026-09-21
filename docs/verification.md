# Verificación — cómo se comprueba cada afirmación del sistema

Inventario de las afirmaciones que este sistema hace sobre sí mismo, con el método que
establece cada una y la letra `T/A/I/D/U` que dice de qué naturaleza es esa evidencia.
Deriva de `definitions.md` (clases, relaciones, preguntas de competencia),
`domain-knowledge.md` (máquinas de estado y grafos) y `architecture.md` (componentes,
agentes y orden), más los límites duros de `AGENTS.md`.

**Qué no es.** No es un plan de pruebas ni una lista de tareas: no dice cuándo se
escribe cada comprobación, solo cuál corresponde y dónde vivirá. Tampoco fija umbrales
numéricos — esos van a `config/thresholds.yaml`. El vocabulario de metodologías es
cerrado y vive en `.claude/skills/plan-de-verificacion/references/metodologias.md`.

## Cobertura

| Nivel | Filas | T | A | I | D | U |
| --- | --- | --- | --- | --- | --- | --- |
| Artefacto | 34 | 13 | 18 | 5 | 0 | 0 |
| Proceso | 30 | 18 | 3 | 1 | 6 | 2 |

Una fila puede llevar dos letras cuando la prueba y el análisis son complementarios, de
ahí que las columnas sumen más que las filas.

La forma de la tabla dice algo del sistema: el nivel artefacto se sostiene sobre
análisis —tipos, estático, model checking— porque casi todo lo que puede fallar ahí es
estructural y enumerable. El nivel proceso se sostiene sobre pruebas con dataset
—evals— y concentra todas las `D` y las `U`, porque juzgar prosa no tiene oráculo
exacto. Ninguna fila del nivel proceso se establece por análisis: eso es una propiedad
del dominio, no una carencia del plan.

**La ejecución en sandbox no aparece en ninguna fila.** El sistema no ejecuta código ni
herramientas generadas por el modelo: la salida del redactor es prosa que se guarda, no
se corre. Si eso cambiara, la metodología entraría de inmediato y con prioridad alta.

---

## Nivel artefacto — ¿es correcto el código?

| Afirmación | Origen | Metodología | T/A/I/D/U | Dónde vive |
| --- | --- | --- | --- | --- |
| Ningún contexto ensamblado supera el total de `config/thresholds.yaml` | `AGENTS.md` § Presupuesto de contexto; `config/thresholds.yaml` | Pruebas basadas en propiedades | T | `context/`, `tests/context/` |
| El total se cuenta **antes** de llamar al modelo, no después | `AGENTS.md` § Presupuesto; `architecture.md` § Reglas de ejecución | Análisis estático / SAST | A | regla propia en CI |
| Un ensamblado que no cabe lanza error; nunca trunca en silencio | `AGENTS.md` regla 3 | Pruebas unitarias | T | `tests/context/` |
| Si una capa desborda se comprime esa capa, sin robar presupuesto a otra | `AGENTS.md` § Presupuesto | Pruebas basadas en propiedades | T | `context/` |
| Los siete presupuestos más el margen suman exactamente `contexto.total` | `config/thresholds.yaml` | Análisis | A | constante única, no números sueltos |
| El contexto tiene exactamente siete capas, con las fuentes del diagrama | `domain-knowledge.md` § Ensamblado del contexto | Inspección | I | `context/` |
| La recuperación filtra por entidades del brief **antes** de ordenar por similitud | `AGENTS.md` § Base de datos; `definitions.md` Capa 3 | Pruebas unitarias + análisis estático | T, A | `context/recuperar-fragmentos` |
| Todo contrato entre capas es un modelo Pydantic; no cruzan `dict` sueltos | `AGENTS.md` § Backend | Comprobación de tipos + análisis estático | A | comprobador de tipos, `ruff` |
| El frontend no contiene `any` | `AGENTS.md` § Frontend | Comprobación de tipos | A | `npm run typecheck` |
| El cliente tipado de `src/api/` no diverge del OpenAPI de FastAPI | `AGENTS.md` § Frontend | Pruebas de contrato | T | paso de CI que regenera y compara |
| Las escrituras al canon son idempotentes por `scene_id` + `version` | `AGENTS.md` § Backend; `architecture.md` § Reglas de ejecución | Pruebas basadas en propiedades | T | `tests/canon/` |
| Toda escritura al canon ocurre dentro de una transacción | `AGENTS.md` § Base de datos | Análisis estático | A | `canon/` |
| `WAL` está activado en la conexión | `AGENTS.md` § Base de datos | Inspección | I | `db/` |
| Las migraciones están numeradas, se aplican en orden y no se editan tras commitear | `AGENTS.md` § Base de datos, regla 5 | Inspección + pruebas unitarias sobre el hash aplicado | I, T | `db/migrations/`, CI |
| Las cardinalidades de «Relaciones del dominio» están en el esquema | `definitions.md` § Relaciones del dominio | Restricciones de esquema + inspección de la migración | I | `db/migrations/` |
| `Escena→Snapshot`, `Brief→Escena` e `Informe→Borrador` son 1:1 | `definitions.md` § Relaciones del dominio | Pruebas unitarias sobre restricciones `unique` | T | `tests/db/` |
| `Evento` ↔ `Escena` es N:M y tiene tabla puente | `definitions.md` § Fábula y discurso; `domain-knowledge.md` § Fábula y discurso | Inspección | I | `db/migrations/` |
| Los nombres de `domain/` coinciden con los de la ontología, sin excepciones | `AGENTS.md` regla 1 | Análisis estático | A | comprobador propio en CI |
| La lógica de dominio no vive en los routers | `AGENTS.md` § Backend | Análisis estático de importaciones | A | CI |
| El frontend no decide nada del canon | `AGENTS.md` § Frontend; `architecture.md` § Sistema | Análisis estático | A | CI |
| Solo `canon/` escribe en el canon; ningún agente lo hace directamente | `architecture.md` § Agentes | Análisis estático de importaciones | A | CI |
| Un borrador rechazado no deja rastro en el canon | `definitions.md` Capa 2 § Regla de actualización | Pruebas basadas en propiedades | T | `tests/canon/` |
| Solo la transición a `aceptada` escribe en el canon | `definitions.md` Capa 5; `domain-knowledge.md` § Ciclo de producción | Model checking | A | `domain/`, `canon/` |
| La máquina de estados de `Escena` no admite transiciones fuera del diagrama | `domain-knowledge.md` § Ciclo de producción | Model checking | A | `domain/` |
| Ídem para el ciclo de vida de `Hecho canónico` | `domain-knowledge.md` § Modelo de canon | Model checking | A | `domain/` |
| Ídem para el ciclo de vida de `Promesa narrativa` | `domain-knowledge.md` § Modelo de canon | Model checking | A | `domain/` |
| Ídem para el ciclo de vida de `Hallazgo` | `domain-knowledge.md` § Modo híbrido | Model checking | A | `domain/` |
| El retcon marca `obsoleta` solo a las escenas afectadas, sin tocar el resto | `AGENTS.md` § Modelo de autoría | Pruebas basadas en propiedades | T | `canon/propagar-retcon` |
| Las llamadas al modelo son asíncronas y llevan timeout explícito | `AGENTS.md` § Backend | Análisis estático | A | CI |
| Los errores de dominio se mapean a HTTP en un handler central | `AGENTS.md` § Backend | Pruebas unitarias | T | `tests/api/` |
| El stack cerrado no admite dependencias vetadas (Postgres, Redis, Celery, ORM…) | `AGENTS.md` § Requisitos técnicos, regla 6 | Análisis estático sobre el lockfile | A | lista de bloqueo en CI |
| Las 21 preguntas de competencia se responden con el esquema vigente | `definitions.md` § Preguntas de competencia | Pruebas de integración, una consulta por pregunta | T | `tests/competencia/` |
| La suite de `canon/` y `context/` detecta de verdad los fallos que dice cubrir | `AGENTS.md` regla 7 | Pruebas de mutación | T | CI nocturno |
| `registrar-generacion` corre en toda llamada al modelo, sin excepción | `architecture.md` § Skills | Análisis estático + observabilidad | A | CI, trazas |

---

## Nivel proceso — ¿se comporta el agente de forma fiable?

| Afirmación | Origen | Metodología | T/A/I/D/U | Dónde vive |
| --- | --- | --- | --- | --- |
| La escena descubre *cómo*, no *hacia dónde*: no altera la restricción de destino | `AGENTS.md` § Modelo de autoría | Evals + verificación multiagente | T | `quality/`, verificador |
| Consistencia fáctica: ningún hecho del borrador contradice el canon | `definitions.md` Capa 4 | Verificación multiagente + evals | T | `quality/verificar-continuidad` |
| Consistencia temporal: los eventos respetan la cronología de la fábula | `definitions.md` Capa 4 | Evals + model checking sobre el orden fábula/discurso | T | `quality/` |
| Consistencia espacial: ubicaciones y desplazamientos posibles | `definitions.md` Capa 4 | Evals contra el snapshot de posiciones | T | `quality/` |
| Consistencia epistémica: nadie usa información que aún no tiene | `definitions.md` Capa 4; `domain-knowledge.md` § Anatomía del personaje | Verificación multiagente + evals | T | `quality/verificar-continuidad` |
| Consistencia de caracterización: las acciones encajan con deseo, herida y arco | `definitions.md` Capa 4 | Evals contra la ficha de personaje | D | `quality/medir-calidad` |
| Plausibilidad especulativa: el novum no viola sus propias reglas | `definitions.md` Capa 4; `domain-knowledge.md` § Mundo especulativo | Evals contra las reglas declaradas | T | `quality/` |
| Distintividad de voz: se identifica quién habla sin acotaciones | `definitions.md` Capa 4 | Evals con clasificación ciega de diálogo | T | `quality/`, `muestrear-voz` |
| Calidad de prosa: eco de n-gramas, clichés, palabras-filtro, varianza de frase | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre métricas léxicas | T | `quality/` |
| Mostrar vs. contar: ratio de escena dramatizada frente a resumen | `definitions.md` Capa 4 | Evals | T | `quality/` |
| Integridad de POV: no hay accesos mentales fuera de la focalización | `definitions.md` Capa 4 | Evals | T | `quality/` |
| Causalidad: la cadena avanza por «por tanto / pero», no por «y entonces» | `definitions.md` Capa 4 | Evals sobre conectores causales | T | `quality/` |
| Curva de tensión: progresa y culmina donde debe | `definitions.md` Capa 4 | Evals con puntuación de tensión por escena | D | `quality/` |
| Ritmo: alternancia de densidad y respiro | `definitions.md` Capa 4 | Evals sobre longitud y tipo de escena en secuencia | T | `quality/` |
| Carga expositiva: infodumps y densidad de neologismos bajo umbral | `definitions.md` Capa 4 | Evals sobre ratio de tokens de exposición | T | `quality/` |
| Sentido de la maravilla: el efecto estético propio del género | `definitions.md` Capa 4 | — | U | — |
| Originalidad: distancia respecto a la prosa genérica del modelo | `definitions.md` Capa 4 § Regresión a la media | Evals contra línea base generada sin guía | T | `quality/` |
| Cumplimiento del brief: la escena hizo lo que se le encargó | `definitions.md` Capa 4 | Evals con cotejo punto por punto | T | `quality/` |
| El autor humano es el único que acepta una escena y adopta un hallazgo | `architecture.md` § Agentes | Revisión humana en el bucle + guardarraíles | A | `api/`, CI |
| Un hallazgo entra como `provisional` y solo el autor lo convierte en canon | `AGENTS.md` § Modelo de autoría | Guardarraíles + análisis estático | A | `canon/extraer-hallazgos` |
| La replanificación nunca se dispara en mitad de una escena | `AGENTS.md` § Modelo de autoría | Guardarraíles + model checking | A | `canon/detectar-deriva` |
| La deriva sobre umbral dispara replanificación rodante | `definitions.md` § Deriva; `domain-knowledge.md` § Modo híbrido | Evals + pruebas unitarias | T | `canon/detectar-deriva` |
| Una versión buena se puede reproducir con su registro de generación | `definitions.md` Capa 5 § Trazabilidad | Observabilidad + demostración | D | `domain/registrar-generacion` |
| Ningún agente inventa un hecho del mundo ni una clase del dominio | `AGENTS.md` regla 4 | Red-teaming + verificación multiagente | D | campaña periódica |
| Un cambio en los prompts o en el ensamblador no degrada la obra en curso | `architecture.md` § Sistema | Despliegue progresivo sobre un subconjunto de escenas + evals | D | proceso de release |
| El código y los prompts pasan por el mismo pipeline que el trabajo humano | `AGENTS.md` § Comandos | Integración en CI/CD | T | CI |
| La trayectoria de cada agente es visible y consultable a posteriori | `architecture.md` § Skills | Observabilidad / trazas en ejecución | I | `domain/registrar-generacion` |
| Un defecto se clasifica correctamente como local o sistémico | `definitions.md` Capa 4 § Clasificación del defecto | Evals sobre dataset etiquetado | T | `quality/medir-calidad` |
| El resultado satisface el gusto del autor | `definitions.md` Capa 5 § Roles | — | U | — |
| La ventana efectiva cubre las siete capas del contexto ensamblado | `definitions.md` Capa 3 § Ventana efectiva | Evals de recuperación por capa | D | `context/` |

---

## Lo que no se puede verificar

Dos afirmaciones son `U` sin matices, y seis más son verificables solo a través de un
proxy que conviene no confundir con la afirmación que representa.

**`U` puras**

| Afirmación | Por qué no es verificable | Qué la convertiría en verificable |
| --- | --- | --- |
| Sentido de la maravilla | La propia ontología la mide con «evaluación cualitativa asistida», que es un juicio, no un procedimiento con criterio de parada | Un conjunto de pasajes etiquetados por el autor convertiría el juicio en un eval con línea base. Seguiría midiendo el gusto de una persona, pero de forma reproducible |
| El resultado satisface el gusto del autor | El gusto es la definición del criterio, no una consecuencia de él; ningún modelo ocupa ese puesto | Nada. Esta fila debe seguir siendo `U`: el día que se automatice, el sistema habrá dejado de escribir la novela del autor |

**Proxies que no deben leerse como la afirmación**

- **Originalidad.** La distancia a una línea base sin guía mide *diferencia*, no calidad.
  Un texto puede alejarse de la media del modelo siendo peor. El eval protege contra la
  regresión a la media; no certifica que lo escrito valga.
- **Causalidad.** Contar conectores detecta el síntoma («y entonces») pero no la
  ausencia de cadena causal escrita con buenos conectores. Prueba la superficie.
- **Curva de tensión.** La puntuación por escena depende de un crítico cuyo acuerdo con
  el autor no está medido. Marcada `D` por eso: se observa el resultado, no se aprueba
  contra un oráculo.
- **Caracterización.** El contraste con la ficha detecta contradicciones explícitas, no
  la deriva lenta de un personaje que sigue siendo coherente y ha dejado de ser él.
- **Reproducibilidad de una versión.** El registro guarda modelo, prompt, contexto y
  semilla, pero la reproducción exacta depende de que el proveedor no cambie el modelo
  bajo el mismo identificador. `D`, no `T`.
- **Ventana efectiva.** Medir qué atiende el modelo exige sondas por capa cuyo resultado
  es indicativo. La afirmación fuerte —«el modelo usó la capa de estado»— no se
  establece con ninguna metodología del catálogo.

---

## Preguntas abiertas al autor

Sin respuesta a estas, hay filas del plan que no se pueden ejecutar.

1. **La medida de deriva no está definida.** `definitions.md` le da a `Deriva` el
   atributo `medida` sin decir cuál es. Hasta que exista, la fila «la deriva sobre
   umbral dispara replanificación» no tiene criterio de aprobado.
2. **`config/thresholds.yaml` se cita en `AGENTS.md` y en `architecture.md`, pero no
   existe en el repositorio.** Todas las filas de calidad dependen de él para tener
   umbral; sin fichero son métricas sin criterio.
3. **Los presupuestos de contexto están declarados dos veces y no coinciden.**
   `definitions.md` Capa 3 los da en porcentaje y `AGENTS.md` en tokens. La capa
   Estructural es el único desajuste: 4 000 / 100 000 = 4 %, frente al 5 % declarado.
   ¿Cuál manda? Mientras no se decida, la fila «los presupuestos suman 100 000» se
   verifica contra una tabla y contradice la otra.
4. **La máquina de estados de `Promesa narrativa` deja `Rota` sin salida.** `Pagada` y
   `Subvertida` van a `[*]`; `Rota` no. El model checking la marcará como estado
   sumidero. ¿Es terminal y falta la arista en el diagrama, o desde `Rota` se vuelve a
   `Pendiente` tras un retcon?
5. **Mismo problema en `Hecho canónico` con `Refutado`.** `Descartado` cierra,
   `Refutado` no. Si es terminal, hay que dibujarlo; si un retcon puede resucitarlo,
   falta la transición.
6. **«Clasificación ciega de diálogo»: ¿quién clasifica?** Si es un clasificador con
   dataset, la distintividad de voz es `T`. Si es una persona, es `D`. La letra de esa
   fila depende de la respuesta.
7. **No hay criterio declarado frente a instrucciones inyectadas** en el texto del autor
   o en los fragmentos que devuelve `vec0`. La ontología no modela esa amenaza, así que
   no hay afirmación que verificar. Si el sistema debe resistirla, es una regla nueva en
   el contexto semilla antes que una fila en este plan.
8. **¿Se ejecutará alguna vez contenido generado por el modelo?** Hoy no, y por eso la
   ejecución en sandbox no aparece en el plan. Conviene que la respuesta quede escrita:
   es el tipo de decisión que cambia en silencio.
