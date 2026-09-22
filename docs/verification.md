# Verificación — cómo se comprueba cada afirmación del sistema

Inventario de las afirmaciones que este sistema hace sobre sí mismo, con los validadores
que establecen cada una y la letra `T/A/I/D/U` que dice de qué naturaleza es esa
evidencia. Deriva de `definitions.md` (clases, relaciones, preguntas de competencia),
`domain-knowledge.md` (máquinas de estado y grafos) y `architecture.md` (componentes,
agentes y orden), más los límites duros de `AGENTS.md` y los requisitos numerados de
`docs/specs/001-backend-v1/spec.md`.

**Qué no es.** No es un plan de pruebas ni una lista de tareas: no dice cuándo se
escribe cada comprobación, solo cuál corresponde y dónde vivirá. Tampoco fija umbrales
numéricos — esos van a `config/thresholds.yaml`. El vocabulario de validadores es
cerrado y vive en `.claude/skills/plan-de-verificacion/references/metodologias.md`.

**Por qué existe.** Seis principios lo gobiernan, y no son decoración: son la razón de
que el documento tenga esta forma. **Uno**, un modelo no garantiza por sí mismo que su
salida sea correcta; la fiabilidad no se supone, se construye añadiendo validadores
alrededor. **Dos**, cada validador tiene una fortaleza y un punto ciego, y ninguno basta
solo. **Tres**, la confianza es propiedad del conjunto, no de cada fila: el plan solo
vale si enseña qué validador cubre el punto ciego de cuál. **Cuatro**, se prefiere el
validador programático aunque cubra la afirmación a medias; media cobertura barata y
determinista vale más que cobertura entera que depende de un juicio. **Cinco**, la
picaresca es legítima y se busca: un atajo que convierte una afirmación aparentemente
inverificable en algo que decide un `SELECT` es una victoria, siempre que haga el
resultado medible y no que lo falsee. **Seis**, los puntos ciegos se leen primero, no al
final; por eso están antes de las tablas.

**Cómo leer las columnas.**

- **Validadores** — uno o varios del catálogo cerrado. Dos en una fila son
  complementarios, no alternativos: uno fija un ejemplo, el otro cubre el espacio.
- **Programático** — `sí` cuando un proceso automático decide aprobado o suspenso sin
  juicio humano ni de modelo; `parcial` cuando solo una parte de la afirmación se decide
  así; `no` cuando todo depende de un juicio.
- **Punto ciego** — qué *no* detecta ese conjunto de validadores. Nunca está vacío.
- **Cubierto por** — qué fila o qué validador adicional cubre ese punto ciego, o `NADIE`.
  Todo lo marcado `NADIE` se recoge en «Puntos ciegos sin cubrir».
- **Dónde vive** — rutas del backend relativas a `backend/app/`; las de `tests/` espejan
  esa estructura. Las del frontend, completas desde la raíz. El layout está en
  `AGENTS.md`.

Cada afirmación lleva identificador (`A-nn` artefacto, `P-nn` proceso) para poder
referenciarla desde «Cubierto por».

---

## Cobertura

| Nivel | Filas | T | A | I | D | U | % programático | Ciegos sin cubrir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Artefacto | 46 | 23 | 24 | 8 | 0 | 0 | 98 % (89 sí · 9 parcial) | 5 |
| Proceso | 36 | 22 | 4 | 2 | 6 | 2 | 92 % (31 sí · 61 parcial) | 8 |

Una fila puede llevar dos letras cuando la prueba y el análisis son complementarios, de
ahí que las columnas sumen más que las filas. El porcentaje cuenta las filas marcadas
`sí` o `parcial`; el reparto exacto es 41 `sí`, 4 `parcial` y 1 `no` en artefacto, y 11
`sí`, 22 `parcial` y 3 `no` en proceso.

La forma de la tabla dice dos cosas. La primera, que el nivel artefacto es casi todo
programático y casi todo `A`: lo que puede fallar ahí es estructural y enumerable, así
que se establece razonando sobre el código sin ejecutarlo. La segunda, y es la incómoda,
que el nivel proceso concentra los `parcial`, todas las `D`, todas las `U` y la mayoría
de los puntos ciegos sin cubrir: casi cada fila de calidad tiene una mitad que decide un
`SELECT` y otra que decide un crítico cuyo acuerdo con el autor nadie ha medido.

**La ejecución en sandbox no aparece en ninguna fila.** El sistema no ejecuta código ni
herramientas generadas por el modelo: la salida del redactor es prosa que se guarda, no
se corre. `A-12` lo verifica como afirmación en vez de dejarlo en costumbre. Si eso
cambiara, la metodología entraría de inmediato y con prioridad alta.

---

## Puntos ciegos sin cubrir

Todo lo que las tablas marcan `NADIE`, ordenado por lo que se rompe si se materializa.
Es la sección que hay que leer primero: las tablas dicen qué se comprueba, esta dice
dónde el sistema está descubierto.

| # | Punto ciego | Filas | Qué se rompe | Qué validador lo cerraría |
| --- | --- | --- | --- | --- |
| 1 | **Ningún umbral está calibrado.** Todo `config/thresholds.yaml` está en `null`, y `A-41` comprueba que falte, no que esté bien puesto | A-41, y de rebote las 14 dimensiones con umbral | Toda la capa de calidad aprueba en vacío: las filas `T` dan por buenos borradores malos y nadie se entera hasta leerlos | **Pruebas de mutación aplicadas al texto**: inyectar defectos conocidos en escenas ya aceptadas y exigir que el crítico los detecte. Un umbral que no separa el original del mutante está mal puesto (§ Soluciones pícaras #12) |
| 2 | **Nadie mide el acuerdo entre el crítico y el autor.** Todas las filas de evals puntúan contra un criterio que nunca se ha contrastado con quien decide | P-29, P-13, P-06, P-02, P-05 | El sistema converge hacia lo que le gusta al crítico, no al autor, y la convergencia parece calidad porque las métricas suben | **Evals sobre dataset etiquetado por el autor**, midiendo acuerdo. Necesita una clase que hoy no existe: la etiqueta del autor sobre un borrador (§ Filas pendientes de ontología) |
| 3 | **La deriva no tiene medida ni umbral.** `definitions.md` da a `Deriva` el atributo `medida` sin decir cuál es, y `deriva.umbral` sigue en `null` | P-23 | El esquema deja de describir la obra y nada lo dispara. Es justo el fallo que el modo híbrido existe para evitar | Ninguno sirve antes de definir la medida; cualquiera después. Sigue siendo la primera pregunta abierta al autor |
| 4 | **Nadie sabe si el modelo atendió a una capa en la escena real.** El canario prueba que puede usarla en una sonda, no que la usara al escribir | P-31, A-04, A-08 | Una escena generada sin el estado que la condiciona: indistinguible de una buena hasta que el verificador encuentra la contradicción, o hasta que no la encuentra | Ninguno del catálogo alcanza la afirmación fuerte. El canario por escena (§ Soluciones pícaras #1) la reduce a este residuo, y el residuo se queda aquí |
| 5 | **Deriva lenta de personaje.** El contraste con la ficha detecta la contradicción explícita, no al personaje que sigue siendo coherente y ha dejado de ser él | P-06 | La novela pierde a su protagonista sin que falle ninguna fila | **Evals** sobre la trayectoria del arco y no sobre la escena: comparar la ficha con lo que el personaje hace en las últimas N escenas, no en la última |
| 6 | **Un cambio de prompt no se contrasta con lo ya escrito.** El despliegue progresivo compara escenas nuevas entre sí | P-26 | La escena 101 es buena y no pega con las cien anteriores; la incoherencia se detecta leyendo, no midiendo | **Evals de continuidad de estilo** contra una muestra congelada de escenas aceptadas como línea base |
| 7 | **El autor puede aprobar sin leer.** Los guardarraíles garantizan que la transición la dispare él, no que la haya leído | P-19, A-46 | `training_samples` se llena de texto que solo pasó umbrales: exactamente el bucle de autoentrenamiento que `architecture.md` prohíbe | **Observabilidad**: registrar ediciones y tiempo de revisión antes de aceptar, y distinguir aceptación leída de aceptación en bloque |
| 8 | **El frontend puede reimplementar reglas de canon.** El análisis estático mide importaciones, no contenido, y no hay ninguna fila de comportamiento del frontend | A-25, A-14 | Dos verdades sobre el canon: la del backend y la que ve el autor. La divergencia se nota cuando ya hay decisiones tomadas sobre la equivocada | **Pruebas de contrato** extendidas —toda vista deriva de una respuesta del backend y no recalcula— más pruebas de integración de frontend, hoy fuera de alcance |
| 9 | **Dos instancias sobre el mismo `data/novel.db`.** La serialización la impone el proceso, y nada impide arrancar dos | P-35, P-36 | El escritor único de SQLite deja de ser un no-problema: dos consolidaciones concurrentes sobre el mismo canon | **Guardarraíles**: cerrojo de instancia sobre el fichero al arrancar, con fallo en voz alta |
| 10 | **La instancia puede exponerse fuera de `127.0.0.1`.** `A-39` comprueba el valor por defecto, no el arranque real | A-39 | Sin autenticación en v1, el canon entero queda accesible en la red | **Guardarraíles**: negarse a escuchar fuera de la interfaz local mientras no haya autenticación |
| 11 | **Un hecho refutado puede resucitar como hecho nuevo.** `A-33` impide la transición, no la creación de un duplicado sin enlace al anterior | A-33, A-30 | El historial pierde el enlace y el canon deja de explicar por qué algo dejó de ser verdad | **Pruebas basadas en propiedades** sobre proximidad de enunciado: un hecho nuevo muy cercano a uno refutado exige referencia explícita |
| 12 | **Sentido de la maravilla y gusto del autor.** Sin validador, por razones distintas | P-16, P-30 | Nada mecánico: es el hueco por diseño del sistema. Importa saber que está ahí y no confundirlo con una carencia del plan | Para `P-16`, pasajes etiquetados por el autor lo convertirían en eval. Para `P-30`, nada, y debe seguir así (§ Lo que no se puede verificar) |

---

## Nivel artefacto — ¿es correcto el código?

| Afirmación | Origen | Validadores | T/A/I/D/U | Programático | Punto ciego | Cubierto por | Dónde vive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A-01** · Ningún contexto ensamblado supera `contexto.total` | `AGENTS.md` § Presupuesto; RNF-01 | Pruebas basadas en propiedades | T | sí | La propiedad se comprueba contra el contador propio: si cuenta menos que el tokenizador del proveedor, el prompt cabe en la prueba y no en la ventana | A-09 | `context/`, `tests/context/` |
| **A-02** · El total se cuenta **antes** de llamar al modelo, no después | `AGENTS.md` regla 3; `architecture.md` § Reglas de ejecución | Análisis estático / SAST | A | sí | Ve el orden de las llamadas, no si el texto cambió entre el recuento y el envío: una capa añadida después de contar pasa desapercibida | A-09 | regla propia en CI |
| **A-03** · Un ensamblado que no cabe lanza error; nunca trunca en silencio | `AGENTS.md` regla 3; RNF-01 | Pruebas unitarias / de integración | T | sí | Cubre el desbordamiento del ensamblador, no el recorte aguas arriba: un recuperador que devuelve menos fragmentos de los pedidos no desborda y el prompt sale incompleto sin error | A-04, A-05 | `tests/context/` |
| **A-04** · Si una capa desborda se comprime esa capa, sin robar presupuesto a otra | `AGENTS.md` § Presupuesto | Pruebas basadas en propiedades | T | sí | No mide si lo que queda de la capa comprimida sigue sirviendo: un snapshot podado hasta quedar vacío cumple la propiedad | § Soluciones pícaras #1 | `context/` |
| **A-05** · La compresión sigue el orden de `contexto.degradacion` y para en cuanto quepa | `AGENTS.md` § Política de degradación; `config/thresholds.yaml` | Pruebas basadas en propiedades | T | sí | Comprueba el orden, no el punto de parada: con un contador equivocado se degrada de más y el orden sigue siendo correcto | A-09 | `context/` |
| **A-06** · La capa Invariante y la restricción de destino no se degradan nunca | `AGENTS.md` § Política de degradación; `architecture.md` § Gestión de tokens | Pruebas basadas en propiedades + análisis estático | T, A | sí | Comprueba que llegan íntegras al prompt, no que el modelo las respete | P-01, § Soluciones pícaras #5 | `context/`, `tests/context/` |
| **A-07** · Los siete presupuestos más el margen suman exactamente `contexto.total` | `config/thresholds.yaml`; RF-CTX-02 | Pruebas unitarias / de integración | T | sí | Una suma correcta no dice nada del reparto: siete cifras que cuadran pueden dejar la capa Estado sin sitio para un snapshot real | P-31 | `tests/context/`, arranque |
| **A-08** · El contexto tiene exactamente siete capas, con las fuentes del diagrama | `domain-knowledge.md` § Ensamblado del contexto | Inspección | I | no | Nadie mira dos veces: si una capa llega vacía en producción, la inspección del código sigue viendo siete | § Soluciones pícaras #1 | `context/` |
| **A-09** · El recuento con el que se decide es el que aplica el proveedor; la diferencia cabe en `contexto.capas.margen` | `AGENTS.md` regla 3; `config/thresholds.yaml` | Pruebas unitarias / de integración + observabilidad | T | sí | Solo se confirma después de la llamada: un cambio de tokenizador del proveedor se detecta con una escena ya generada de por medio | A-03; el margen absorbe el error mientras tanto | `commons/tokens/`, trazas |
| **A-10** · La recuperación filtra por entidades del brief **antes** de ordenar por similitud | `AGENTS.md` § Persistencia…; `definitions.md` Capa 3 | Pruebas unitarias / de integración + análisis estático | T, A | sí | Comprueba el orden de las dos etapas, no la calidad del filtro: un brief con pocas entidades declaradas deja pasar casi todo y la similitud vuelve a mandar | P-31 | `context/recuperar-fragmentos` |
| **A-11** · El texto de obra y de canon entra en el prompt marcado como datos, nunca en la posición de las instrucciones | `architecture.md` § Resistencia a inyección; RF-CTX-11 | Pruebas unitarias / de integración + análisis estático | T, A | sí | Comprueba el marcado, no su eficacia: un delimitador correcto no impide que el modelo obedezca lo que hay dentro | P-20 | `context/` |
| **A-12** · Ningún camino del código ejecuta, evalúa ni lanza como proceso lo que devuelve el modelo | `architecture.md` § Resistencia a inyección; spec 001 §9.8 | Análisis estático / SAST | A | sí | Cubre el código propio; no cubre una dependencia que interprete el texto por su cuenta (una plantilla con expresiones, un render) | A-37 | regla propia en CI |
| **A-13** · Todo contrato entre capas es un modelo Pydantic; no cruzan `dict` sueltos | `AGENTS.md` § Persistencia… | Comprobación de tipos + análisis estático | A | sí | Un modelo con campos `Any` o un `dict` anidado dentro pasa el tipo y no dice nada | A-23 | comprobador de tipos, `ruff` |
| **A-14** · El frontend no contiene `any` | `AGENTS.md` § Persistencia… | Comprobación de tipos | A | sí | `as unknown as T` y `@ts-expect-error` no son `any` y abren el mismo agujero | A-15 | `npm run typecheck` |
| **A-15** · El cliente tipado de `frontend/src/shared/api/` no diverge del OpenAPI | `AGENTS.md` § Persistencia… | Pruebas de contrato | T | sí | Compara el cliente con el esquema, no el esquema con lo que el backend devuelve: un `response_model` mal puesto es coherente por los dos lados | A-43 | paso de CI que regenera y compara |
| **A-16** · Las escrituras al canon son idempotentes por `scene_id` + `version` | `AGENTS.md` § Persistencia…; `architecture.md` § Reglas de ejecución | Pruebas basadas en propiedades | T | sí | Idempotencia sobre la misma clave: dos consolidaciones de la misma escena con `version` distinta duplican hechos sin violar nada | A-27 | `tests/canon/` |
| **A-17** · Toda escritura al canon ocurre dentro de una transacción | `AGENTS.md` § Persistencia…; RNF-02 | Análisis estático / SAST | A | sí | Ve la transacción abierta, no su alcance: una que se cierra antes de la última escritura pasa el análisis | A-16 | `canon/` |
| **A-18** · `WAL` está activado en la conexión | `AGENTS.md` § Persistencia…; RNF-02 | Inspección | I | parcial | Se comprueba en la conexión que abre el backend; una creada aparte —una migración, un script— puede no llevarlo | A-19 | `commons/db/` |
| **A-19** · Migraciones numeradas, aplicadas en orden y nunca editadas tras commitear | `AGENTS.md` regla 5; RNF-03 | Inspección + pruebas unitarias sobre el hash aplicado | I, T | sí | El hash detecta la edición contra la base que ya la aplicó, no contra un clon que todavía no ha migrado | A-43 | `commons/db/migrations/`, CI |
| **A-20** · Las cardinalidades de «Relaciones del dominio» están en el esquema | `definitions.md` § Relaciones del dominio | Restricciones de esquema + inspección de la migración | I | parcial | Una restricción declarada no dice si el código la respeta al insertar con `INSERT OR IGNORE` | A-21, A-43 | `commons/db/migrations/` |
| **A-21** · `Escena→Snapshot`, `Brief→Escena` e `Informe→Borrador` son 1:1 | `definitions.md` § Relaciones del dominio | Pruebas unitarias sobre restricciones `unique` | T | sí | Prueba la unicidad, no la obligatoriedad: una escena aceptada sin snapshot no viola ningún `unique` | A-28 | `tests/commons/db/` |
| **A-22** · `Evento` ↔ `Escena` es N:M y tiene tabla puente | `definitions.md` § Fábula y discurso; `domain-knowledge.md` § Fábula y discurso | Inspección | I | parcial | La tabla puede existir y no escribirse nunca: la consistencia temporal se queda sin datos y sigue aprobando | P-03 | `commons/db/migrations/` |
| **A-23** · Los nombres de las clases del código coinciden con los de la ontología | `AGENTS.md` regla 1; RNF-07 | Análisis estático / SAST | A | sí | Detecta el nombre inventado en el código; no detecta la clase de la ontología que ningún módulo implementa | A-43 | comprobador propio en CI sobre los `models.py` |
| **A-24** · La lógica de dominio no vive en los routers | `AGENTS.md` § Persistencia… | Análisis estático de importaciones | A | sí | Mide importaciones, no contenido: un `router.py` con veinte líneas de reglas y ninguna importación rara pasa | P-34 | CI |
| **A-25** · El frontend no decide nada del canon | `AGENTS.md` § Persistencia…; `architecture.md` § Sistema | Análisis estático / SAST | A | parcial | Que no importe reglas no impide que las reimplemente en un componente «para mostrarlo mejor» | NADIE | CI |
| **A-26** · Solo `canon/` escribe en el canon; ningún agente lo hace directamente | `architecture.md` § Agentes | Análisis estático de importaciones | A | sí | Cubre las importaciones entre features; no cubre una escritura por SQL crudo desde `commons/db` | A-17 | CI |
| **A-27** · Un borrador rechazado no deja rastro en el canon | `definitions.md` Capa 2 § Regla de actualización | Pruebas basadas en propiedades | T | sí | Comprueba el canon, no las tablas de al lado: un borrador rechazado puede dejar embeddings, muestras de voz o filas de `training_samples` | A-46 | `tests/canon/` |
| **A-28** · Solo la transición a `aceptada` escribe en el canon | `definitions.md` Capa 5; `domain-knowledge.md` § Ciclo de producción | Model checking | A | sí | Verifica el modelo de la máquina, no el código que la implementa si los dos se escriben por separado | A-26 | `novel/`, `canon/` |
| **A-29** · La máquina de estados de `Escena` no admite transiciones fuera del diagrama | `domain-knowledge.md` § Ciclo de producción | Model checking | A | sí | Los dos documentos de ontología no coinciden en el estado `Extraida`: se verifica contra una versión y la otra queda sin cubrir | pendiente de ontología | `novel/` |
| **A-30** · Ídem para el ciclo de vida de `Hecho canónico` | `domain-knowledge.md` § Modelo de canon | Model checking | A | sí | Los valores de `Estatus de hecho` difieren entre documentos (`implícito` frente a `Descartado`): el `CHECK` de la columna sale distinto según cuál se lea | pendiente de ontología | `canon/` |
| **A-31** · Ídem para el ciclo de vida de `Promesa narrativa` | `domain-knowledge.md` § Modelo de canon | Model checking | A | sí | Mientras no se exporte la arista final, el verificador marca `Rota` como sumidero sin saber si es diseño o error | A-33 | `canon/` |
| **A-32** · Ídem para el ciclo de vida de `Hallazgo` | `domain-knowledge.md` § Modo híbrido | Model checking | A | sí | El estado inicial se llama `Propuesto` en el diagrama y `provisional` en el resto: se verifica un nombre que el código no usa | pendiente de ontología | `findings/` |
| **A-33** · `Refutado` y `Rota` son terminales: ninguna transición sale de ellos | spec 001 §9.3; RF-CANON-10 | Model checking + pruebas basadas en propiedades | A, T | sí | Impide la transición, no la creación de un hecho nuevo idéntico al refutado y sin referencia al anterior | NADIE | `canon/`, `tests/canon/` |
| **A-34** · El retcon marca `obsoleta` solo a las escenas afectadas, sin tocar el resto | `AGENTS.md` § Modelo de autoría | Pruebas basadas en propiedades | T | sí | «Afectada» se calcula por las entidades del hecho retconeado: una escena que dependía de él sin nombrarlo queda fuera y sobrevive | § Soluciones pícaras #4 | `replanning/propagar-retcon`; en v1 solo la consulta |
| **A-35** · Las llamadas al modelo son asíncronas y llevan timeout explícito | `AGENTS.md` § Persistencia… | Análisis estático / SAST | A | sí | Ve el timeout, no su valor ni si el reintento posterior multiplica el tiempo total por el número de intentos | P-36 | CI |
| **A-36** · Los errores de dominio se mapean a HTTP en un handler central | `AGENTS.md` § Persistencia… | Pruebas unitarias / de integración | T | sí | Prueba los errores que alguien recordó registrar; una excepción nueva sin entrada sale como 500 y su prueba no existe | A-44 | `tests/commons/` |
| **A-37** · El stack cerrado no admite dependencias vetadas | `AGENTS.md` § Requisitos técnicos, regla 6; RNF-08 | Análisis estático sobre el lockfile | A | sí | La lista de bloqueo es por nombre conocido: un paquete nuevo con la misma función —otro ORM, otro broker— pasa hasta que alguien lo añade | A-44 | lista de bloqueo en CI |
| **A-38** · Ninguna tabla lleva `user_id` ni `tenant_id` | `AGENTS.md` § Alcance; RNF-11 | Análisis estático / SAST + inspección | A, I | sí | Detecta el nombre: una columna `autor_id` con la misma intención pasa | P-34 | CI, `commons/db/migrations/` |
| **A-39** · La instancia escucha en `127.0.0.1` por defecto | `architecture.md` § Dónde escucha; RNF-12 | Inspección + pruebas unitarias | I, T | sí | Comprueba el valor por defecto; no impide que el arranque lo cambie por variable de entorno sin que nadie lo note | NADIE | `main.py`, `tests/` |
| **A-40** · `config/thresholds.yaml` es la fuente única: ninguna cifra duplicada en documentos ni suelta en el código | RNF-14; `AGENTS.md` § Presupuesto de contexto | Análisis estático / SAST | A | sí | Busca números en el código y en `docs/`; no detecta un umbral escrito con palabras («la mitad del presupuesto local») | A-41 | regla propia en CI |
| **A-41** · Si falta un umbral que se necesita, el arranque falla en voz alta | RF-QUA-05; `config/thresholds.yaml` | Pruebas unitarias / de integración | T | sí | Cubre el umbral ausente, no el presente y mal calibrado: un valor inventado arranca sin protestar | NADIE | `commons/`, `tests/commons/` |
| **A-42** · Un cambio de modelo o de versión de embeddings se detecta al arrancar y falla en voz alta | `architecture.md` § Embeddings y reindexado | Pruebas unitarias / de integración + inspección | T, I | sí | Compara lo declarado con lo almacenado: un proveedor que cambie los pesos bajo la misma versión pasa la comprobación y devuelve otros vecinos | § Soluciones pícaras #2 | `commons/db/`, arranque |
| **A-43** · Las 21 preguntas de competencia se responden con el esquema vigente, salvo las que el alcance deje fuera | `definitions.md` § Preguntas de competencia; spec 001 §8; RNF-04 | Pruebas unitarias / de integración, una consulta por pregunta | T | sí | Responder no es responder bien: una consulta que devuelve filas plausibles con un `JOIN` equivocado pasa igual | A-44 | `tests/competencia/` |
| **A-44** · La suite de `canon/` y `context/` detecta de verdad los fallos que dice cubrir | `AGENTS.md` regla 7 | Pruebas de mutación | T | sí | Muta el código, no los datos ni los prompts: una suite que no comprueba nada del texto generado sale indemne | § Soluciones pícaras #12 | CI nocturno |
| **A-45** · `registrar-generacion` corre en toda llamada al modelo, sin excepción | `architecture.md` § Skills; RNF-06 | Análisis estático / SAST + observabilidad | A | sí | Garantiza la fila, no su contenido: un registro con el prompt truncado o el contexto sin serializar cumple igual | P-24 | CI, trazas |
| **A-46** · Solo entra en `training_samples` texto aceptado **y editado** por el autor | `architecture.md` § Adaptación del modelo; RF-PROC-09 | Análisis estático / SAST + pruebas unitarias | A, T | sí | La traza distingue aceptación humana de automática; no distingue una aceptación humana hecha sin leer | NADIE | `process/`, `tests/process/` · pendiente de ontología |

---

## Nivel proceso — ¿se comporta el agente de forma fiable?

| Afirmación | Origen | Validadores | T/A/I/D/U | Programático | Punto ciego | Cubierto por | Dónde vive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **P-01** · La escena descubre *cómo*, no *hacia dónde*: no altera la restricción de destino | `AGENTS.md` § Modelo de autoría | Pruebas basadas en propiedades sobre el snapshot de salida + evals | T | parcial | Cubre los tres `tipo` declarados de restricción; el destino que el autor tenía en la cabeza y no declaró no se comprueba | P-19 | `quality/verificar-continuidad`, `process/` |
| **P-02** · Consistencia fáctica: ningún hecho del borrador contradice el canon | `definitions.md` Capa 4; RF-QUA-01 | Pruebas unitarias / de integración contra el canon + verificación multiagente | T | parcial | La parte programática solo alcanza a lo enunciado con términos canónicos y nombres propios: una contradicción parafraseada («ya no cojeaba») no la ve ninguna consulta | crítico, con el residuo en § Puntos ciegos #2 | `quality/verificar-continuidad` |
| **P-03** · Consistencia temporal: los eventos respetan la cronología de la fábula | `definitions.md` Capa 4 | Model checking sobre el orden fábula/discurso + evals | T | parcial | Comprueba los eventos registrados; uno que la escena narra y nadie registró en la tabla puente no entra en la comprobación | A-22 | `quality/` |
| **P-04** · Consistencia espacial: ubicaciones y desplazamientos posibles | `definitions.md` Capa 4 | Pruebas unitarias / de integración contra el snapshot de posiciones + evals | T | parcial | Sabe dónde estaba el personaje, no cuánto tarda en llegar: sin duraciones declaradas, un desplazamiento imposible es consistente | P-03 | `quality/` |
| **P-05** · Consistencia epistémica: nadie usa información que aún no tiene | `definitions.md` Capa 4; `domain-knowledge.md` § Anatomía del personaje | Pruebas unitarias / de integración sobre `Estado epistémico` + verificación multiagente | T | parcial | Detecta el uso explícito de un hecho que el POV no conoce; no detecta al personaje que actúa *como si* lo supiera sin nombrarlo | crítico, con el residuo en § Puntos ciegos #2 | `quality/verificar-continuidad` |
| **P-06** · Consistencia de caracterización: las acciones encajan con deseo, herida y arco | `definitions.md` Capa 4 | Evals contra la ficha de personaje + verificación multiagente | D | parcial | Detecta la contradicción explícita con la ficha; no detecta la deriva lenta del personaje que sigue siendo coherente y ha dejado de ser él | NADIE | `quality/medir-calidad` |
| **P-07** · Plausibilidad especulativa: el novum no viola sus propias reglas | `definitions.md` Capa 4; `domain-knowledge.md` § Mundo especulativo | Pruebas unitarias / de integración contra `Regla del mundo` + evals | T | parcial | Comprueba las reglas declaradas: una consecuencia en cascada del novum que nadie escribió como regla no se viola nunca | P-25 | `quality/` |
| **P-08** · Distintividad de voz: se identifica quién habla sin acotaciones | `definitions.md` Capa 4 | Evals con clasificación ciega de diálogo | T | parcial | Quién clasifica sigue abierto: si es una persona, la fila es `D` y no `T` | § Soluciones pícaras #10 | `quality/`, `muestrear-voz` |
| **P-09** · Calidad de prosa: eco de n-gramas, clichés, palabras-filtro, varianza de frase | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre métricas léxicas | T | sí | Mide repetición y muletillas, no que la frase diga algo: un texto sin ecos ni palabras filtro puede ser plano | P-17 | `quality/` |
| **P-10** · Mostrar vs. contar: ratio de escena dramatizada frente a resumen | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre el ratio escena/sumario | T | parcial | El ratio se calcula con marcas superficiales: un resumen escrito en presente y con diálogo cuenta como escena | P-13 | `quality/` |
| **P-11** · Integridad de POV: no hay accesos mentales fuera de la focalización | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre accesos mentales + evals | T | parcial | Detecta el verbo de acceso ajeno («supo que ella temía»); no detecta la fuga por descripción de lo que el POV no puede ver | P-05 | `quality/` |
| **P-12** · Causalidad: la cadena avanza por «por tanto / pero», no por «y entonces» | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre conectores causales + evals | T | parcial | Contar conectores detecta el síntoma, no la ausencia de cadena causal escrita con buenos conectores | § Soluciones pícaras #7 | `quality/` |
| **P-13** · Curva de tensión: progresa y culmina donde debe | `definitions.md` Capa 4 | Evals con puntuación de tensión por escena | D | parcial | La puntuación depende de un crítico cuyo acuerdo con el autor no está medido | § Soluciones pícaras #6, y el residuo en § Puntos ciegos #2 | `quality/` |
| **P-14** · Ritmo: alternancia de densidad y respiro | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre longitud y tipo de escena en secuencia | T | sí | Mide la alternancia, no si cae donde la estructura la pide: un patrón regular pasa aunque el respiro llegue en mitad del clímax | P-13 | `quality/` |
| **P-15** · Carga expositiva: infodumps y densidad de neologismos bajo umbral | `definitions.md` Capa 4 | Pruebas basadas en propiedades sobre el ratio de tokens de exposición | T | parcial | Necesita saber qué token es exposición: fuera del glosario canónico la marca es heurística | § Soluciones pícaras #4 | `quality/` |
| **P-16** · Sentido de la maravilla: el efecto estético propio del género | `definitions.md` Capa 4 | — | U | no | Sin criterio escrito, nadie sabe qué contaría como fallo: ningún validador puede suspender | NADIE | — |
| **P-17** · Originalidad: distancia respecto a la prosa genérica del modelo | `definitions.md` Capa 4 § Regresión a la media | Evals contra línea base generada sin guía | T | sí | Mide diferencia, no calidad: un texto puede alejarse de la media del modelo siendo peor | P-30 | `quality/` |
| **P-18** · Cumplimiento del brief: la escena hizo lo que se le encargó | `definitions.md` Capa 4 | Pruebas unitarias / de integración sobre la restricción de destino + evals | T | parcial | Cubre lo que el brief declara como restricción; lo que pide en prosa («que se note la tensión entre ambos») se queda en el eval | P-19 | `quality/`, `process/` |
| **P-19** · El autor humano es el único que acepta una escena y adopta un hallazgo | `architecture.md` § Agentes; RF-PROC-05 | Revisión humana en el bucle + guardarraíles + análisis estático | A | sí | Garantiza que la transición la dispare una petición del autor; no garantiza que la haya leído antes de aprobarla | NADIE | `api/`, CI |
| **P-20** · Ningún agente ejecuta instrucciones halladas en texto narrativo | `architecture.md` § Resistencia a inyección; RF-PROC-10 | Red-teaming / pruebas adversarias + guardarraíles | T | parcial | Una campaña cubre los ataques que se le ocurrieron a quien la escribió | § Soluciones pícaras #8 | campaña periódica, CI |
| **P-21** · Un hallazgo entra como `provisional` y solo el autor lo convierte en canon | `AGENTS.md` § Modelo de autoría; RF-FIND-05 | Guardarraíles + análisis estático | A | sí | Protege la adopción; no impide que un hallazgo provisional se cuele en el contexto de la escena siguiente como si fuera canon | A-11 | `findings/extraer-hallazgos`, `context/` |
| **P-22** · La replanificación nunca se dispara en mitad de una escena | `AGENTS.md` § Modelo de autoría | Guardarraíles + model checking | A | sí | `replanning/` está fuera de v1: hoy la regla no tiene implementación que verificar | alcance de la spec 001 §1.3 | `replanning/detectar-deriva` |
| **P-23** · La deriva sobre umbral dispara replanificación rodante | `definitions.md` § Deriva; RF-PROC-08 | Evals + pruebas unitarias / de integración | T | parcial | Sin medida definida y con `deriva.umbral` en `null`, hoy se verifica que se registra algo por escena, no que ese algo mida deriva | NADIE | `replanning/detectar-deriva`; en v1 solo el registro |
| **P-24** · Una versión buena se puede reproducir con su registro de generación | `definitions.md` Capa 5 § Trazabilidad; RNF-05 | Observabilidad / trazas en ejecución + demostración | D | parcial | Reproduce lo que el sistema controla; el proveedor puede cambiar el modelo bajo el mismo identificador | § Soluciones pícaras #9 | `process/registrar-generacion` |
| **P-25** · Ningún agente inventa un hecho del mundo ni una clase del dominio | `AGENTS.md` regla 4 | Red-teaming + verificación multiagente | D | parcial | Un nombre propio nuevo se detecta; un hecho inventado sobre una entidad que ya existe («el puerto llevaba años cerrado») no tiene forma reconocible | P-02 | campaña periódica, `findings/` |
| **P-26** · Un cambio en los prompts o en el ensamblador no degrada la obra en curso | `architecture.md` § Sistema | Despliegue progresivo + evals | D | parcial | Compara escenas nuevas entre sí; no dice nada de su coherencia con las cien escritas con el prompt anterior | NADIE | proceso de release |
| **P-27** · El código y los prompts pasan por el mismo pipeline que el trabajo humano | `AGENTS.md` § Comandos | Integración en CI/CD | T | sí | El pipeline corre lo que alguien puso en él: un prompt cambiado a mano en producción no pasa por CI | A-45 | CI |
| **P-28** · La trayectoria de cada agente es visible y consultable a posteriori | `architecture.md` § Skills; RNF-06 | Observabilidad / trazas en ejecución | I | parcial | Que exista la traza no la hace legible: sin una consulta que la reconstruya, nadie la mira hasta que hay un problema | A-45 | `process/registrar-generacion` |
| **P-29** · Un defecto se clasifica correctamente como local o sistémico | `definitions.md` Capa 4 § Clasificación del defecto | Evals sobre dataset etiquetado | T | no | El dataset lo etiqueta quien construyó el clasificador: sin etiquetas del autor, mide acuerdo consigo mismo | NADIE | `quality/medir-calidad` |
| **P-30** · El resultado satisface el gusto del autor | `definitions.md` Capa 5 § Roles | — | U | no | Ningún validador: es la definición del criterio, no una consecuencia suya | NADIE, por diseño | — |
| **P-31** · La ventana efectiva cubre las siete capas del contexto ensamblado | `definitions.md` Capa 3 § Ventana efectiva | Evals de recuperación por capa | D | parcial | Mide si el modelo *puede* usar cada capa en una sonda, no si usó la capa de estado en la escena real | § Soluciones pícaras #1, con el residuo en § Puntos ciegos #4 | `context/` |
| **P-32** · Un agente no invoca a otro ni elige el siguiente paso | `architecture.md` § Orquestación | Análisis estático de importaciones + model checking | A | sí | Ve las llamadas del código; no impide que un prompt pida al modelo «decidir qué hacer ahora» y que alguien obedezca ese texto | A-11, P-20 | CI, `process/` |
| **P-33** · Al agotar el máximo de iteraciones la escena se queda en `en revisión` y escala al autor | `architecture.md` § Corta-circuitos; `config/thresholds.yaml` | Pruebas unitarias / de integración + model checking | T | sí | Cuenta iteraciones de revisión: un bucle que gasta presupuesto sin cambiar de estado —reintentos de infraestructura— no toca ese contador | P-36 | `process/`, `tests/process/` |
| **P-34** · No se escribe código sin plan aprobado ni plan sin spec aprobada | `AGENTS.md` § Ciclo de cambio | Inspección + integración en CI/CD sobre el frontmatter | I | parcial | CI comprueba que existe un plan `aprobada`, no que el código commiteado sea el de ese plan | revisión humana en el bucle | CI, `docs/specs/` |
| **P-35** · Una sola escena en generación a la vez; en paralelo solo los pasos de solo lectura | RNF-09; `architecture.md` § Paralelo y serie | Pruebas basadas en propiedades | T | sí | Cubre un proceso: dos instancias apuntando al mismo `data/novel.db` rompen la serialización sin que nadie lo detecte | NADIE | `process/`, `tests/process/` |
| **P-36** · Un trabajo no arranca sin presupuesto de tokens en vuelo libre | RNF-10; `architecture.md` § Presupuesto en vuelo | Pruebas basadas en propiedades | T | sí | El pool es un semáforo en memoria: no sobrevive a un reinicio y no sabe de otras instancias | P-35 | `commons/`, `tests/commons/` |

---

## Soluciones pícaras

Atajos que convierten una afirmación cara, subjetiva o dependiente de juicio en algo que
decide código. Ninguno cubre la afirmación entera; todos cubren una parte por un coste
que no se parece al del validador que sustituyen. La columna que importa es la última:
qué sigue sin cubrir después del atajo.

**#1 · Hecho canario en la capa de Estado.** En vez de preguntar a un modelo si atendió a
la capa de Estado, se inyecta en el snapshot un hecho inventado para la prueba —un objeto
en un bolsillo, una hora concreta— y se comprueba **por código** si la salida lo usa.
Corre sobre una obra de prueba, nunca sobre `data/novel.db`, y el mismo patrón vale capa
por capa: un término en Invariante, una muestra de voz en Estilo, una metáfora vetada en
Anticontexto.
*Ahorra*: la batería de evals con juez de modelo sobre la ventana efectiva. *Baja de D a
T* la parte medible de `P-31`, y da a `A-04` y `A-08` una comprobación de que la capa
llega con contenido y no vacía. *Sigue sin cubrir*: que el modelo atendiera a esa capa en
la escena real, no en la sonda (§ Puntos ciegos #4).

**#2 · Vector canario de embeddings.** Se guarda el vector de una frase fija junto al
modelo y la versión con que se generó; al arrancar se vuelve a embeber y se compara. Si
el vector se mueve, el proveedor cambió los pesos aunque la versión diga lo mismo.
*Ahorra*: reindexados preventivos y la búsqueda a ciegas de por qué la recuperación
empeoró. *Sigue T*, pero cierra el punto ciego de `A-42`, que hoy solo compara etiquetas.

**#3 · Epistémica por SQL, modelo solo para lo dudoso.** En vez de que un crítico juzgue
la consistencia epistémica, se deriva de `Estado epistémico`: se extraen del borrador los
términos canónicos y nombres propios —enumerables, están en la base— y se cruzan con lo
que el POV conoce en `t`. Solo las discrepancias suben al modelo.
*Ahorra*: una llamada al crítico por escena se convierte en una consulta más una llamada
ocasional. *Baja de juicio a `T`* la mitad enumerable de `P-05` y `P-02`. *Sigue sin
cubrir*: el personaje que actúa como si supiera, sin nombrar nada.

**#4 · Glosario cerrado.** Todo nombre propio o término del mundo que aparezca en el
borrador y no exista en `Término canónico` ni en las entidades del brief se marca como
hallazgo candidato. Es un `SELECT` contra una lista cerrada, no un juicio.
*Ahorra*: la parte del red-teaming de `P-25` dedicada a nombres inventados, y da a `P-15`
el denominador de neologismos que hoy es heurístico. También mejora `A-34`: una escena
que menciona el término afectado por un retcon es afectada aunque no nombre el hecho.
*Sigue sin cubrir*: el hecho inventado sobre una entidad existente.

**#5 · Restricción de destino ejecutable.** Los tres `tipo` que `definitions.md` da a
`Restricción de destino` —estado final, revelación, posición de personaje— son los tres
comprobables contra el snapshot de salida de la escena: ¿queda el estado declarado?,
¿existe la fila de `Revelación`?, ¿está el personaje donde decía? Sin modelo de por medio.
*Ahorra*: el cotejo punto por punto con crítico de `P-18` y `P-01`. *Baja a `T`* la parte
declarada de las dos filas. *Sigue sin cubrir*: lo que el brief pide en prosa y el destino
que el autor no declaró.

**#6 · Tensión por promesas, no por puntuación.** En vez de puntuar la tensión con un
crítico, se deriva de canon: promesas en estado `Pendiente` por escena, escenas desde el
último pago, promesas abiertas frente a escenas restantes. Es el indicador que
`domain-knowledge.md` ya señala como el mejor aviso temprano de que una novela se
desarma.
*Ahorra*: una puntuación de modelo por escena sobre toda la obra. *Baja de D a T* la parte
estructural de `P-13`; la curva estética se queda en `D`. *Sigue sin cubrir*: que la
tensión suba donde la estructura la pide y no solo que haya deuda abierta.

**#7 · Causalidad por hilos de trama.** Una escena que no avanza ningún `Hilo de trama`,
no abre ni paga ninguna promesa y no establece ningún hecho es candidata a «y entonces»,
por bien escritos que estén sus conectores. Consulta contra las aristas del grafo.
*Ahorra*: nada de crítico; añade una señal que el conteo de conectores no ve. *Sigue
siendo T* pero cubre el punto ciego de `P-12`. *Sigue sin cubrir*: la escena que avanza un
hilo por casualidad, sin cadena causal escrita.

**#8 · Corpus de inyección con marcador inerte.** En vez de depender de campañas de
red-teaming, un corpus fijo de textos narrativos que contienen instrucciones con un
marcador inerte —una cadena que no significa nada para la obra— entra en CI como
regresión: si el marcador aparece en la salida, o si el sistema intenta cualquier acción
que no sea escribir prosa, la prueba falla.
*Ahorra*: convierte una campaña periódica cara en una prueba de segundos que corre en cada
cambio. *Baja a T determinista* la parte regresiva de `P-20`; la campaña sigue
haciendo falta para ataques nuevos. *Sigue sin cubrir*: el ataque que nadie ha imaginado.

**#9 · Huella del ensamblado.** Se guarda el hash del contexto ensamblado, del prompt
final y de los parámetros. Reproducir deja de ser «comparar prosa» y pasa a ser «comparar
hashes»: si coinciden y la salida difiere, el cambio es del proveedor, no nuestro.
*Ahorra*: la lectura comparada de dos versiones para decidir de quién fue la culpa. *Baja
de D a T* la parte que el sistema controla en `P-24`; la parte del proveedor sigue en `D`.
*Sigue sin cubrir*: reproducir la prosa exacta cuando el proveedor cambió.

**#10 · Clasificador ciego con el propio corpus.** Para `P-08`, un clasificador entrenado
sobre el diálogo ya aceptado de la obra, evaluado dejando fuera al personaje que se juzga:
si no acierta quién habla por encima del azar, las voces no están diferenciadas. Es
determinista con semilla fija y no necesita anotador.
*Ahorra*: el anotador humano por escena. *Mantendría `T`* sin depender de nadie. **No
cierra la pregunta abierta**: quién clasifica lo decide el autor, y esto es solo el
candidato barato (§ Preguntas abiertas).

**#11 · Prosa por código, crítico para el residuo.** Eco de n-gramas, palabras filtro,
varianza de longitud de frase y clichés de lista se miden sin modelo. El crítico solo
recibe los pasajes que ya pasaron ese filtro, y solo para lo que el filtro no ve.
*Ahorra*: la mayor parte de las llamadas al crítico de `P-09`. *Ya es T*; el atajo es de
coste, no de letra. *Sigue sin cubrir*: la prosa limpia y plana.

**#12 · Mutación de texto para calibrar umbrales.** El atajo más rentable del documento.
En vez de calibrar los umbrales de `config/thresholds.yaml` a ojo, se toman escenas ya
aceptadas, se les inyectan defectos conocidos —un hecho contradictorio, una fuga de POV,
una repetición— y se exige que el crítico los detecte. Un umbral que no separa el original
del mutante está mal puesto, y se sabe por código.
*Ahorra*: la calibración por prueba y error a lo largo de meses de escritura. *No cambia
ninguna letra*: cierra el punto ciego #1, que es el que hace que todas las demás letras
signifiquen algo. *Sigue sin cubrir*: los defectos que nadie sabe inyectar, que son los
mismos que el crítico no sabe ver.

---

## Lo que no se puede verificar

Dos afirmaciones siguen siendo `U` después de pasar por las soluciones pícaras, y seis más
son verificables solo a través de un proxy que conviene no confundir con la afirmación que
representa.

**`U` puras**

| Afirmación | Por qué ningún atajo la alcanza | Qué la convertiría en verificable |
| --- | --- | --- |
| **P-16** · Sentido de la maravilla | La ontología la mide con «evaluación cualitativa asistida», que es un juicio sin criterio de parada. Los atajos del documento miden presencia (un canario), estructura (promesas, hilos) o superficie (léxico); la maravilla no es ninguna de las tres, y medir densidad de novum solo mediría densidad de novum | Un conjunto de pasajes etiquetados por el autor la convertiría en eval con línea base. Seguiría midiendo el gusto de una persona, pero de forma reproducible |
| **P-30** · El resultado satisface el gusto del autor | El gusto es la definición del criterio, no una consecuencia de él. Ningún atajo puede hacerlo medible sin sustituir al autor, que es justo lo que no se quiere | Nada. Esta fila debe seguir siendo `U`: el día que se automatice, el sistema habrá dejado de escribir la novela del autor |

**Proxies que no deben leerse como la afirmación**

- **Originalidad (`P-17`).** La distancia a una línea base sin guía mide *diferencia*, no
  calidad. El eval protege contra la regresión a la media; no certifica que lo escrito
  valga.
- **Causalidad (`P-12`).** Contar conectores prueba la superficie. La pícara #7 añade una
  señal estructural, pero tampoco lee la cadena causal: lee si la escena movió algo.
- **Curva de tensión (`P-13`).** La pícara #6 baja a `T` el recuento de deuda narrativa
  abierta. Lo que queda en `D` —si la tensión culmina donde debe— sigue dependiendo de un
  crítico cuyo acuerdo con el autor no está medido.
- **Caracterización (`P-06`).** El contraste con la ficha detecta contradicciones
  explícitas, no la deriva lenta. Es el único punto ciego que ninguna pícara toca.
- **Reproducibilidad (`P-24`).** Con la pícara #9, el sistema demuestra que reprodujo su
  parte. La prosa idéntica depende de que el proveedor no cambie el modelo bajo el mismo
  identificador: `D`, no `T`.
- **Ventana efectiva (`P-31`).** El canario demuestra que la capa llegó y que el modelo
  puede usarla. La afirmación fuerte —«el modelo usó la capa de estado *en esta escena*»—
  no la establece ninguna metodología del catálogo.

---

## Filas pendientes de ontología

Filas cuyo criterio depende de una clase, un estado o un atributo que la ontología no
fija hoy. No se resuelven aquí: `definitions.md` y `domain-knowledge.md` son
exportaciones de documentos vivos y los edita el autor (`AGENTS.md` § Canonicidad y
sincronía).

| Fila | Qué le falta | Efecto mientras tanto |
| --- | --- | --- |
| A-29 | El estado `Extraida` de `Escena`: lo dibuja `domain-knowledge.md` y no lo lista `definitions.md` | El model checking se hace contra una de las dos versiones; la otra queda sin verificar |
| A-30 | Los valores de `Estatus de hecho`: `implícito` en la lista, `Descartado` en el diagrama | El `CHECK` de la columna sale distinto según qué documento se lea |
| A-31, A-33 | Las aristas de `Refutado` y `Rota` al estado final, ya decididas y pendientes de exportar | El verificador los marca como sumideros sin salida declarada |
| A-32 | El nombre del estado inicial de `Hallazgo`: `Propuesto` en el diagrama, `provisional` en los demás documentos | Se verifica un nombre que el código no usa |
| A-46 | `Muestra de entrenamiento` (`training_samples`) no está ratificada como clase | La tabla entra en v1; la fila verifica una tabla sin entrada en la ontología |
| P-23 | La medida de `Deriva` | Sin criterio de aprobado: se verifica el registro, no la medida |
| P-29, § Puntos ciegos #2 | La etiqueta del autor sobre un borrador, que sería la verdad de referencia del crítico | No hay dataset contra el que medir acuerdo |
| § Puntos ciegos #4 | Auditoría de texto sospechoso: no hay clase para un texto bajo sospecha ni estado de cuarentena para un hallazgo (`architecture.md` § Resistencia a inyección) | Las reglas antiinyección son de arquitectura y no se pueden auditar escena a escena |

---

## Preguntas abiertas al autor

Quedan dos. El resto de la lista original está decidido y vive abajo, con la fila del plan
en que se convirtió cada decisión: sin la decisión al lado vuelven a leerse como abiertas,
y las skills y las specs las citan por número.

1. **La medida de deriva no está definida.** `definitions.md` da a `Deriva` el atributo
   `medida` sin decir cuál es, y `deriva.umbral` sigue en `null` a la espera de histórico.
   Hasta que exista, `P-23` verifica que se registra algo por escena, no que ese algo mida
   deriva, y el punto ciego #3 sigue abierto. Es la pregunta más cara del documento: es el
   detector del fallo que el modo híbrido existe para evitar.
6. **«Clasificación ciega de diálogo»: ¿quién clasifica?** Si es un clasificador con
   dataset, `P-08` es `T`; si es una persona, es `D`. La solución pícara #10 propone el
   candidato barato —clasificador entrenado con el propio corpus, evaluado dejando fuera al
   personaje— pero no decide: la letra de esa fila depende de la respuesta del autor.

### Ya resueltas

| # | Pregunta | Decisión | En qué fila del plan se convirtió |
| --- | --- | --- | --- |
| 2 | `config/thresholds.yaml` no existía en el repositorio | **Creado.** Es la única fuente de umbrales y presupuestos; ninguna cifra se duplica en documentos ni se escribe suelta en el código | A-40, A-41 (RNF-14, RF-QUA-05) |
| 3 | Los presupuestos de contexto estaban declarados dos veces y no coincidían | **Viven solo en `config/thresholds.yaml`**, en tokens. La capa Estructural queda con el valor de `contexto.capas.estructural`; los porcentajes de la Capa 3 dejan de mandar y se retiran al reexportar la ontología | A-07, A-40 (RF-CTX-02) |
| 4 | `Rota` sin arista de salida en `Promesa narrativa` | **Terminal por diseño.** No se revive; si la trama vuelve sobre ello, se crea una entidad nueva que referencia a la anterior | A-31, A-33 (RF-CANON-10) |
| 5 | `Refutado` sin arista de salida en `Hecho canónico` | **Terminal por diseño**, por la misma razón. Falta dibujar la arista al estado final en el diagrama | A-30, A-33 (RF-CANON-10) |
| 7 | No había criterio frente a instrucciones inyectadas | **Tres reglas**: el texto de obra y canon entra marcado como datos, ningún agente ejecuta instrucciones halladas en texto narrativo, y ningún hallazgo se adopta sin el autor | A-11, P-20, P-21 (RF-CTX-11, RF-PROC-10, RF-FIND-05) |
| 8 | ¿Se ejecutará alguna vez contenido generado por el modelo? | **No.** La salida del redactor es prosa que se guarda, no se corre, y ningún camino del código la ejecuta, evalúa ni lanza como proceso. Es una decisión, no una pregunta: si cambiara, la ejecución en sandbox entraría en el plan con prioridad alta | A-12 |
