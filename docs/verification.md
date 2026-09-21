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

**Cómo leer «Dónde vive».** Las rutas del backend son relativas a `backend/app/`, y las
de `tests/` espejan esa misma estructura. Las del frontend se escriben completas desde la
raíz del repositorio. El layout está en `AGENTS.md`.

## Cobertura

| Nivel | Filas | T | A | I | D | U |
| --- | --- | --- | --- | --- | --- | --- |
| Artefacto | 35 | 14 | 19 | 5 | 0 | 0 |
| Proceso | 31 | 19 | 3 | 1 | 6 | 2 |

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
| La recuperación filtra por entidades del brief **antes** de ordenar por similitud | `AGENTS.md` § Persistencia, backend y frontend; `definitions.md` Capa 3 | Pruebas unitarias + análisis estático | T, A | `context/recuperar-fragmentos` |
| El texto de obra y de canon entra en el prompt marcado como datos, nunca en la posición de las instrucciones | `architecture.md` § Resistencia a inyección; RF-CTX-11 | Pruebas unitarias + análisis estático | T, A | `context/` |
| Todo contrato entre capas es un modelo Pydantic; no cruzan `dict` sueltos | `AGENTS.md` § Persistencia, backend y frontend | Comprobación de tipos + análisis estático | A | comprobador de tipos, `ruff` |
| El frontend no contiene `any` | `AGENTS.md` § Persistencia, backend y frontend | Comprobación de tipos | A | `npm run typecheck` |
| El cliente tipado de `frontend/src/shared/api/` no diverge del OpenAPI de FastAPI | `AGENTS.md` § Persistencia, backend y frontend | Pruebas de contrato | T | paso de CI que regenera y compara |
| Las escrituras al canon son idempotentes por `scene_id` + `version` | `AGENTS.md` § Persistencia, backend y frontend; `architecture.md` § Reglas de ejecución | Pruebas basadas en propiedades | T | `tests/canon/` |
| Toda escritura al canon ocurre dentro de una transacción | `AGENTS.md` § Persistencia, backend y frontend | Análisis estático | A | `canon/` |
| `WAL` está activado en la conexión | `AGENTS.md` § Persistencia, backend y frontend | Inspección | I | `commons/db/` |
| Las migraciones están numeradas, se aplican en orden y no se editan tras commitear | `AGENTS.md` § Persistencia, backend y frontend; regla 5 | Inspección + pruebas unitarias sobre el hash aplicado | I, T | `commons/db/migrations/`, CI |
| Las cardinalidades de «Relaciones del dominio» están en el esquema | `definitions.md` § Relaciones del dominio | Restricciones de esquema + inspección de la migración | I | `commons/db/migrations/` |
| `Escena→Snapshot`, `Brief→Escena` e `Informe→Borrador` son 1:1 | `definitions.md` § Relaciones del dominio | Pruebas unitarias sobre restricciones `unique` | T | `tests/commons/db/` |
| `Evento` ↔ `Escena` es N:M y tiene tabla puente | `definitions.md` § Fábula y discurso; `domain-knowledge.md` § Fábula y discurso | Inspección | I | `commons/db/migrations/` |
| Los nombres de las clases del código coinciden con los de la ontología, sin excepciones | `AGENTS.md` regla 1 | Análisis estático | A | comprobador propio en CI, sobre los `models.py` de cada feature |
| La lógica de dominio no vive en los routers | `AGENTS.md` § Persistencia, backend y frontend | Análisis estático de importaciones | A | CI |
| El frontend no decide nada del canon | `AGENTS.md` § Persistencia, backend y frontend; `architecture.md` § Sistema | Análisis estático | A | CI |
| Solo `canon/` escribe en el canon; ningún agente lo hace directamente | `architecture.md` § Agentes | Análisis estático de importaciones | A | CI |
| Un borrador rechazado no deja rastro en el canon | `definitions.md` Capa 2 § Regla de actualización | Pruebas basadas en propiedades | T | `tests/canon/` |
| Solo la transición a `aceptada` escribe en el canon | `definitions.md` Capa 5; `domain-knowledge.md` § Ciclo de producción | Model checking | A | `novel/`, `canon/` |
| La máquina de estados de `Escena` no admite transiciones fuera del diagrama | `domain-knowledge.md` § Ciclo de producción | Model checking | A | `novel/` |
| Ídem para el ciclo de vida de `Hecho canónico` | `domain-knowledge.md` § Modelo de canon | Model checking | A | `canon/` |
| Ídem para el ciclo de vida de `Promesa narrativa` | `domain-knowledge.md` § Modelo de canon | Model checking | A | `canon/` |
| Ídem para el ciclo de vida de `Hallazgo` | `domain-knowledge.md` § Modo híbrido | Model checking | A | `findings/` |
| El retcon marca `obsoleta` solo a las escenas afectadas, sin tocar el resto | `AGENTS.md` § Modelo de autoría | Pruebas basadas en propiedades | T | `replanning/propagar-retcon` |
| Las llamadas al modelo son asíncronas y llevan timeout explícito | `AGENTS.md` § Persistencia, backend y frontend | Análisis estático | A | CI |
| Los errores de dominio se mapean a HTTP en un handler central | `AGENTS.md` § Persistencia, backend y frontend | Pruebas unitarias | T | `tests/commons/` |
| El stack cerrado no admite dependencias vetadas (Postgres, Redis, Celery, ORM…) | `AGENTS.md` § Requisitos técnicos, regla 6 | Análisis estático sobre el lockfile | A | lista de bloqueo en CI |
| Las 21 preguntas de competencia se responden con el esquema vigente, salvo las que el alcance vigente deje fuera | `definitions.md` § Preguntas de competencia; spec 001 § Criterios de aceptación | Pruebas de integración, una consulta por pregunta | T | `tests/competencia/` |
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
| Ningún agente ejecuta instrucciones halladas en texto narrativo | `architecture.md` § Resistencia a inyección; RF-PROC-10 | Red-teaming | T | campaña periódica |
| Un hallazgo entra como `provisional` y solo el autor lo convierte en canon | `AGENTS.md` § Modelo de autoría | Guardarraíles + análisis estático | A | `findings/extraer-hallazgos` |
| La replanificación nunca se dispara en mitad de una escena | `AGENTS.md` § Modelo de autoría | Guardarraíles + model checking | A | `replanning/detectar-deriva` |
| La deriva sobre umbral dispara replanificación rodante | `definitions.md` § Deriva; `domain-knowledge.md` § Modo híbrido | Evals + pruebas unitarias | T | `replanning/detectar-deriva` |
| Una versión buena se puede reproducir con su registro de generación | `definitions.md` Capa 5 § Trazabilidad | Observabilidad + demostración | D | `process/registrar-generacion` |
| Ningún agente inventa un hecho del mundo ni una clase del dominio | `AGENTS.md` regla 4 | Red-teaming + verificación multiagente | D | campaña periódica |
| Un cambio en los prompts o en el ensamblador no degrada la obra en curso | `architecture.md` § Sistema | Despliegue progresivo sobre un subconjunto de escenas + evals | D | proceso de release |
| El código y los prompts pasan por el mismo pipeline que el trabajo humano | `AGENTS.md` § Comandos | Integración en CI/CD | T | CI |
| La trayectoria de cada agente es visible y consultable a posteriori | `architecture.md` § Skills | Observabilidad / trazas en ejecución | I | `process/registrar-generacion` |
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

Sin respuesta a estas, hay filas del plan que no se pueden ejecutar. Se conserva la
numeración original de la primera redacción: las resueltas están en la tabla de abajo.

1. **La medida de deriva no está definida.** `definitions.md` le da a `Deriva` el
   atributo `medida` sin decir cuál es. Hasta que exista, la fila «la deriva sobre
   umbral dispara replanificación» no tiene criterio de aprobado.
6. **«Clasificación ciega de diálogo»: ¿quién clasifica?** Si es un clasificador con
   dataset, la distintividad de voz es `T`. Si es una persona, es `D`. La letra de esa
   fila depende de la respuesta.
8. **¿Se ejecutará alguna vez contenido generado por el modelo?** Hoy no, y por eso la
   ejecución en sandbox no aparece en el plan. Conviene que la respuesta quede escrita:
   es el tipo de decisión que cambia en silencio.

### Ya resueltas

No se borran: las skills y las specs las citan, y sin la decisión al lado vuelven a
leerse como abiertas.

| # | Pregunta | Decisión | Dónde vive |
| --- | --- | --- | --- |
| 2 | `config/thresholds.yaml` no existía en el repositorio | **Creado.** Fuente única de cifras y umbrales | `config/thresholds.yaml`; spec 001 §9.1, RNF-14 |
| 3 | Los presupuestos de contexto están declarados dos veces y no coinciden | **Manda el valor en tokens del fichero**, no el porcentaje de la Capa 3. La capa Estructural queda en 4 % real frente al 5 % declarado hasta reexportar la ontología | spec 001 §9.4, RF-CTX-02; `architecture.md` § Pendiente de llevar a la ontología |
| 4 | `Rota` sin arista de salida en `Promesa narrativa` | **Terminal por diseño.** No se revive | spec 001 §9.3, RF-CANON-10 |
| 5 | `Refutado` sin arista de salida en `Hecho canónico` | **Terminal por diseño.** No se revive | spec 001 §9.3, RF-CANON-10 |
| 7 | No había criterio frente a instrucciones inyectadas | **Tres reglas**: el texto entra marcado como datos, ningún agente ejecuta instrucciones halladas en él, y ningún hallazgo se adopta sin el autor | `architecture.md` § Resistencia a inyección; RF-CTX-11, RF-PROC-10, RF-FIND-05 |

Las dos primeras reglas de la 7 tienen fila propia en las tablas de arriba; la tercera ya
la cubría «un hallazgo entra como `provisional`».
