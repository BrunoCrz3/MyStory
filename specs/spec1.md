---
estado: aprobada
aprobada-por: Bruno Cruz
fecha: 2026-09-24
contrato-aprobado-con-ella: specs/openapi.yaml
modificada: 2026-09-24 · TO-037 y TO-040 · cambios aprobados por el desarrollador
---

# SRS 1 — Backend v1 de storyMaker

Especificación de requisitos del backend en su primera versión, inspirada en
ISO/IEC/IEEE 29148. Documento único: alcance, requisitos funcionales y no funcionales,
contrato de interfaz, datos, fases de construcción y trazabilidad.

> **Estado: aprobada** el 2026-09-24 por Bruno Cruz.
>
> **`specs/openapi.yaml` queda aprobado con ella, en la misma fecha**: el contrato es parte
> de esta spec, no un anexo, y aprobar una sin el otro dejaría al frontend construyendo
> contra algo revocable. A partir de aquí, cambiar el contrato es cambiar la spec.
>
> Falta `specs/plan1.md`, que nace en `borrador`: **no se escribe código hasta que ese plan
> esté aprobado** (`CLAUDE.md` § Ciclo de cambio).
>
> **Modificada el 2026-09-24, con el cambio aprobado por el desarrollador** (TO-037): el
> contrato pasa a la versión 1.1.0 con `BriefNovelaParcial` para la validación del brief
> (RF-INTAKE-01, § 4.1), y se añade el contrato de lectura con el frontend (§ 4.4). Los dos
> cambios salieron de revisar el plan 1 y los pidió el desarrollador; no son del agente.

---

## 1. Introducción

### 1.1 Propósito

Definir qué debe hacer el backend para que el sistema genere, de principio a fin y **sin
humano en el bucle**, una novela personalizada de regalo de diez capítulos, la sirva para
su lectura web y admita que el lector pida un cambio sobre ella.

El destinatario de este documento es quien escriba `specs/plan1.md` y, después, el código.
Está redactado para que ese plan se pueda ejecutar de forma autónoma de principio a fin.

### 1.2 Alcance del backend v1

**Dentro.** El ciclo completo de `docs/definitions.md` Capa 5 —configurar, planificar,
escribir, validar, publicar— sobre varias novelas y un solo usuario; la story bible en
SQLite con el uso de cada hecho por capítulo; los validadores programáticos y semánticos
que el alcance exige; el versionado por vigencia y la regeneración dirigida; la API que
consume el frontend; el export a PDF; y la observabilidad en Langfuse.

**Fuera.** Todo lo de § 10, y en particular: autenticación y cuentas, la especificación
TLA+ y su test de correspondencia, el servidor MCP, el agente de seguridad y las dos
propuestas de ontología que quedaron abiertas (PO-11 y PO-12).

**El frontend no se especifica aquí.** Se construye en paralelo desde hoy contra
`specs/openapi.yaml`, que es lo que hace posible el paralelismo. Lo único del frontend que
esta spec fija es el **contrato de lectura** de § 4.4: la ruta, los selectores y la hoja de
impresión que el backend necesita para validar el render y exportarlo.

### 1.3 Definiciones

**No se redefine nada.** Toda clase, estado, rol y dimensión de calidad que aparezca en
este documento está definida en el contexto semilla y se usa con ese significado exacto:

| Qué | Dónde |
| --- | --- |
| Clases, atributos, relaciones y preguntas de competencia | `docs/definitions.md` |
| Máquinas de estado, jerarquías y grafos | `docs/domain-knowledge.md` |
| Features, agentes, hooks, orquestación y story bible | `docs/architecture.md` |
| Qué valida cada validador, dónde corre y con qué score | `docs/verification.md` |
| Reglas cerradas y presupuesto de contexto | `CLAUDE.md` |
| **Todas las cifras** | `config/thresholds.yaml`, `config/models.yaml` |

Un nombre nuevo en esta spec sin entrada en la ontología es un error de esta spec.

### 1.4 Referencias

`docs/requerimientos/alcance-proyecto.md` (el encargo, citado por número de sección),
`docs/trade-offs.md` (decisiones, citadas `TO-NNN`), `docs/registro-iteraciones.md`,
`specs/openapi.yaml` (el contrato), RFC 9457 (formato de los errores) e
ISO/IEC/IEEE 29148 (la forma de este documento).

---

## 2. Descripción general

### 2.1 Funciones

Seis, y el resto del documento las desarrolla:

1. **Recoger el encargo** y convertirlo en un `BriefNovela` validado, tratando el texto
   libre como contenido no confiable.
2. **Planificar** la obra entera: diez capítulos, cada uno con su `Restricción de destino`.
3. **Escribir** capítulo a capítulo, ensamblando el contexto por capas bajo presupuesto.
4. **Validar** en cuatro puntos de ejecución y decidir con el policy engine.
5. **Publicar** versiones inmutables y **regenerar** solo lo afectado cuando el lector
   pide un cambio.
6. **Dejar rastro** de todo en Langfuse.

### 2.2 Usuarios

| Usuario | Qué hace con el backend | Cómo lo identifica el sistema |
| --- | --- | --- |
| **Comprador** | Encarga, configura y paga | **No lo identifica.** `Comprador.identificador` es un dato del brief, opaco, nunca un correo ni un nombre |
| **Lector** | Lee la novela publicada y pide cambios. Es un papel, no una persona distinta | Tampoco. Quien conoce el UUID de la novela la lee |
| **Desarrollador** | Arranca, opera, aprueba specs y planes | No hay consola: usa la API y `config/` |
| **Revisor humano** | Puntúa al menos una novela con la rúbrica del judge | Fuera de la API en v1: lee la lectura web y anota aparte |

**No hay autenticación y no la habrá en v1** (TO-004). No hay principal, no hay sesión y
ninguna tabla lleva `user_id` ni `tenant_id`.

### 2.3 Restricciones

| Restricción | Origen |
| --- | --- |
| Stack cerrado: FastAPI, Python 3.12, Pydantic v2, React 18 + TypeScript, Vite, **SQLite como única persistencia**. Sin Postgres, Redis, Celery ni ORM | `CLAUDE.md` § Requisitos técnicos |
| Backend por features en rodaja vertical; `commons/` solo para lo compartido; ninguna feature importa el `repository.py` de otra | `CLAUDE.md`, `docs/architecture.md` § Anatomía de una feature |
| Tope de tokens concurrentes en toda la instancia | `config/thresholds.yaml` § `en_vuelo.total` |
| Límite duro de contexto por petición, repartido en siete capas más margen | `config/thresholds.yaml` § `contexto` |
| Sin autenticación; la instancia escucha solo en la interfaz local | TO-004; `docs/architecture.md` § Seguridad |
| Ninguna credencial en el repositorio: solo `.env.example` con los nombres | `CLAUDE.md` regla 12 |
| Sin mocks en `backend/app/`, ni siquiera temporales | `CLAUDE.md` regla 8 |
| TDD: la prueba primero, y no hay código sin plan aprobado | `CLAUDE.md` regla 7 |
| Migraciones numeradas que nunca se editan tras commitear | `CLAUDE.md` regla 5 |

### 2.4 Supuestos y dependencias

| Dependencia | Para qué | Qué pasa si falta |
| --- | --- | --- |
| **API de Anthropic** | Los seis roles, con el identificador y el effort de `config/models.yaml` | El sistema no genera. Es la única dependencia dura |
| **Langfuse** | Trazas, spans, scores y versiones de prompt | La generación **sigue**, y lo registra como degradado en `GET /salud`. Perder observabilidad no debe costar una novela |
| **Lean 4 con `lake`** | Las tres demostraciones de cronología en el gate | Ya está previsto: `formal.gate_activo` está en `false` y el gate no corre. Se enciende al instalar la toolchain |
| **Playwright** | `render_visual` en el gate y el export a PDF | Sin él no hay export ni validación visual; la generación sí puede terminar |

**Supuestos declarados.** Una sola instancia del backend escribe sobre
`data/storymaker.db`; el reloj del sistema es fiable para ordenar versiones; y el
`Revisor humano` existe y puntuará una novela.

---

## 3. Requisitos funcionales

Formato EARS. Cada requisito lleva **[demo]** o **[post-demo]** y sus criterios de
aceptación en Dado / Cuando / Entonces. Agrupados por la feature de
`docs/architecture.md` que es dueña de las clases implicadas.

### 3.1 `intake/` — encargo

**RF-INTAKE-01 [demo]** · Cuando llega un brief a validar, el sistema deberá aceptarlo como
**`BriefNovelaParcial`** —todos los campos opcionales— y devolver los `Dato faltante`, las
`Contradicción de brief`, los `Fragmento sospechoso` y los hechos extraídos del texto libre,
**sin crear nada**. Un `Dato faltante` es todo campo obligatorio en `BriefNovela` que no
llega o llega vacío. **Crear la novela exige el `BriefNovela` completo** (TO-037).

> *Dado* un brief sin `destinatario.nombre`, *cuando* se envía a validar, *entonces* la
> respuesta es `200` con `valido: false` y un `Dato faltante` para ese campo con su
> pregunta de reintento. **El sistema repregunta; no rellena el hueco** (`CLAUDE.md`
> regla 4).
>
> *Dado* el mismo brief, *cuando* se envía a crear la novela, *entonces* la respuesta es
> `422 peticion-invalida` y no se crea nada: el brief parcial solo lo acepta la validación.

**RF-INTAKE-02 [demo]** · Cuando el brief contenga dos datos incompatibles, el sistema
deberá registrar una `Contradicción de brief` con su tipo, mediante **reglas
deterministas entre campos**.

> *Dado* un brief con `destinatario.edad: 7` y un tono declarado para adultos, *cuando* se
> valida, *entonces* aparece una contradicción de tipo `edad-vs-tono`. El alcance §1 exige
> al menos un tipo; este es el obligatorio.

**RF-INTAKE-03 [demo]** · Cuando el comprador aporte texto libre, el sistema deberá
tratarlo como **contenido no confiable**: extraer hechos de él, registrar como
`Fragmento sospechoso` lo que parezca una instrucción al sistema y descartarlo.

> *Dado* un texto libre que contiene «ignora las instrucciones anteriores», *cuando* se
> valida, *entonces* ese fragmento se devuelve como sospechoso, no entra en el brief, y
> ningún prompt posterior lo coloca en la posición de las instrucciones.

**RF-INTAKE-04 [demo]** · Cuando se cree una novela con un brief válido, el sistema
deberá persistirlo, asignar un `novel_id` y dejar la novela en `Configurando`, **sin
lanzar la generación**.

> *Dado* un brief válido, *cuando* se crea la novela, *entonces* la respuesta es `201` con
> el `novel_id`, y no se ha llamado al modelo ni una vez.

**RF-INTAKE-05 [demo]** · Cuando el brief declare palabras prohibidas, temas excluidos o
reglas del mundo, el sistema deberá guardarlas asociadas a la novela: las palabras como
nivel `novela` del guardrail, y las reglas de exclusión de entidad compiladas también a
ese nivel.

**RF-INTAKE-06 [post-demo]** · Cuando el comprador use el entrevistador conversacional, el
sistema deberá mantener el diálogo hasta producir el mismo `BriefNovela` validado,
repreguntando por cada `Dato faltante`.

> Es **requisito obligatorio del alcance §1**, no un descarte: la demo lo cubre con
> formulario y el diálogo llega después. El diálogo en curso se persiste con `novel_id`
> porque ocupa varias peticiones (`docs/architecture.md` § Corto plazo).

### 3.2 `process/` — orquestación

**RF-PROC-01 [demo]** · Cuando se solicite una generación para una novela sin ninguna en
curso, el sistema deberá encolar un trabajo y responder `202` de inmediato con el recurso
de progreso.

> *Dado* una novela en `Configurando`, *cuando* se lanza la generación, *entonces* la
> respuesta es `202` en menos de un segundo y el trabajo queda en la tabla de trabajos.

**RF-PROC-02 [demo]** · Cuando ya exista una generación o una regeneración viva para esa
novela, el sistema deberá rechazar la nueva con `409 generacion-en-curso` y el
identificador de la que corre.

> *Dado* una generación en `Escribiendo`, *cuando* se lanza otra, *entonces* `409`, el
> cuerpo trae el `generacion_id` vivo y **no se ha encolado nada**.

**RF-PROC-03 [demo]** · El sistema deberá ejecutar los trabajos con **un único worker
asíncrono en proceso**, arrancado en el `lifespan` de la aplicación, que reclama trabajos
de la tabla con una actualización condicional atómica.

> *Dado* dos intentos simultáneos de reclamar el mismo trabajo, *cuando* ambos ejecutan el
> `UPDATE ... WHERE estado = 'pendiente'`, *entonces* exactamente uno afecta a una fila y
> el otro a ninguna.
>
> **Arrancar con más de un worker de uvicorn queda prohibido** y documentado en el README:
> el pool de tokens es un semáforo en proceso y dos procesos lo duplicarían en silencio.

**RF-PROC-04 [demo]** · Cuando se consulte el historial de generaciones de una novela, el
sistema deberá devolver la inicial y todas las regeneraciones, con sus tokens y su coste.

**RF-PROC-05 [demo]** · Cuando se consulte una generación, el sistema deberá devolver su
estado, el capítulo actual, los aceptados, los intentos, el checkpoint, los tokens, el
coste, **si el estado es terminal** y **cada cuánto conviene volver a preguntar**.

> *Dado* una generación en `Publicada`, *cuando* se consulta, *entonces* `es_terminal` es
> `true` e `intervalo_sondeo_segundos` es `null`. El cliente deja de sondear por el
> booleano, nunca deduciendo la terminalidad del nombre del estado.

**RF-PROC-06 [demo]** · Cuando el proceso se reinicie a mitad de una generación, el
sistema deberá reanudar desde el `Checkpoint` sin duplicar ni perder capítulos.

> *Dado* una generación con los capítulos 1 a 4 en `Aceptado` y el 5 a medias, *cuando* el
> proceso se reinicia —incluido un reinicio por `--reload`—, *entonces* al arrancar los
> aceptados siguen siendo 1 a 4, el capítulo 5 queda normalizado a `Pendiente` y la
> generación continúa por él. **Esta es la prueba de reanudación de la fase F1.**
>
> La reanudación **no es una transición**: se resuelve en `orquestador.estado_inicial`
> (TO-023).

**RF-PROC-07 [demo]** · El sistema deberá implementar la máquina de estados como una
**tabla declarativa** `(estado, condición) → estado` en `process/`, con las acciones de
`docs/architecture.md` § Estados.

> *Dado* la tabla, *cuando* se pide una transición que no está en ella, *entonces* se
> rechaza con `transicion-invalida` y no se muta nada. La tabla existe **desde F1**, antes
> que la spec TLA+ que la comparará.

**RF-PROC-08 [demo]** · Cuando un capítulo agote `orquestacion.max_intentos_capitulo`, el
sistema deberá dejarlo en `Agotado`, la novela en `Detenida`, e informar con el motivo.

> *Dado* un capítulo que falla la validación tantas veces como permita el límite, *cuando*
> se agota, *entonces* la generación queda terminal, `detenida_por` lleva el `type` del
> problema y el informe de crítica del último intento queda consultable.

**RF-PROC-09 [demo]** · Cuando una llamada al modelo falle por infraestructura, el sistema
deberá reintentar con retroceso exponencial y jitter hasta
`orquestacion.max_intentos_trabajo`, **sin gastar** intentos del capítulo.

> *Dado* un 429 del proveedor, *cuando* se reintenta y luego se acepta el capítulo,
> *entonces* `intentos` del capítulo sigue en cero: un 429 no es un defecto del capítulo
> (TO-014).

**RF-PROC-10 [demo]** · Después de aceptar un capítulo, el sistema deberá extraer los
hechos que introdujo y proponerlos, **nunca antes**.

### 3.3 `context/` — ensamblado

**RF-CTX-01 [demo]** · Cuando se vaya a generar un capítulo, el sistema deberá ensamblar
el contexto en las siete capas de la ontología, cada una de su fuente.

**RF-CTX-02 [demo]** · El sistema deberá contar los tokens **antes** de llamar al modelo,
con el contador del proveedor, y **fallar en voz alta** si el ensamblado no cabe tras
degradar. Nunca truncar en silencio. Con `proveedor: claude_code` (TO-040) no hay contador
del proveedor antes de la llamada: el recuento previo es una **estimación por lo alto** con
el margen de `modelo.claude_code`, y el real llega después en el `usage` del CLI.

> *Dado* un ensamblado que supera `contexto.total`, *cuando* se ha degradado en el orden
> de `contexto.degradacion` y sigue sin caber, *entonces* el trabajo falla con un error
> explícito y **no se ha llamado al modelo**.

**RF-CTX-03 [demo]** · Cuando una capa desborde su presupuesto, el sistema deberá
comprimir **esa** capa, en el orden declarado, parando en cuanto quepa, **sin robar
presupuesto a otra** y sin degradar nunca la capa Invariante ni la restricción de destino.

**RF-CTX-04 [demo]** · La capa Recuperado deberá filtrar por las entidades del
`BriefCapitulo` **y solo después** ordenar. Sin `sqlite-vec` en v1 (TO-015): el filtro es
relacional.

**RF-CTX-05 [demo]** · Al arrancar, el sistema deberá comprobar que
`contexto.capas.margen` es mayor o igual que el `max_tokens` de **cada** rol y fallar en
voz alta si no.

### 3.4 `novel/` — obra y capítulos

**RF-NOVEL-01 [demo]** · Cuando el planificador reciba un brief validado, el sistema
deberá producir un `Esquema` con tantos capítulos como declare `obra.capitulos`, cada uno
con su `Restricción de destino` y su `alcance` —las entidades, promesas e hilos que toca—.

**RF-NOVEL-02 [demo]** · El sistema deberá listar las novelas de la instancia con su
estado y su versión vigente.

**RF-NOVEL-03 [demo]** · El sistema deberá devolver una novela con su estado, su brief y
su versión vigente.

**RF-NOVEL-04 [demo]** · Cuando el redactor produzca un borrador, el sistema deberá
someterlo al hook de policy, al hook de capítulo y al rol editor **en ese orden**, y solo
aceptarlo si todos pasan.

**RF-NOVEL-05 [demo]** · El sistema deberá servir los capítulos de una versión, con su
texto, su título y su marca de modificado.

### 3.5 `canon/` — story bible

**RF-CANON-01 [demo]** · Cuando se acepte un capítulo, el sistema deberá consolidar en una
**transacción** los hechos extraídos, su uso por capítulo, el `Snapshot` de cierre y el
`Resumen de capítulo`; y **solo** entonces.

> *Dado* un borrador rechazado, *cuando* se descarta, *entonces* la story bible no tiene
> ni un hecho, ni un resumen, ni un snapshot suyo.

**RF-CANON-02 [demo]** · El sistema deberá registrar, por cada `Hecho`, **en qué capítulos
se usa**, con vigencia propia del puente.

> Es lo que hace posible el análisis de impacto sin releer la novela. Un hecho sin uso
> registrado es un hecho que la regeneración no sabrá propagar.

**RF-CANON-03 [demo]** · El sistema deberá servir los hechos vigentes **de una versión
concreta**, resolviendo por vigencia y **nunca por estatus** (TO-028).

> *Dado* un hecho retconeado en la versión 3, *cuando* se piden los hechos de la versión 1,
> *entonces* el hecho aparece, porque en la versión 1 seguía siendo verdad.

**RF-CANON-04 [demo]** · Cuando el extractor proponga un hecho, el sistema deberá guardarlo
como `propuesto` con su `origen` y el **fragmento del capítulo que lo sostiene**; un hecho
que no pueda citar su fragmento no se consolida.

**RF-CANON-05 [post-demo]** · Cuando dos hechos se contradigan, el sistema deberá registrar
una `Contradicción de canon` y resolverla con un `Retcon`.

### 3.6 `guardrail/` — palabras prohibidas

**RF-GUARD-01 [demo]** · Cuando se valide un capítulo, el sistema deberá comprobarlo contra
los tres niveles de palabras prohibidas —`global`, `perfil` y `novela`— aplicados en
conjunto, ganando el más restrictivo.

**RF-GUARD-02 [demo]** · La detección deberá **normalizar los dos lados** —el texto y la
palabra— con las cinco transformaciones de `config/thresholds.yaml` § `guardrail`.

> *Dado* la palabra vetada `imbécil`, *cuando* el capítulo escribe `Imbeciles`, *entonces*
> coincide: minúsculas, acentos y plurales se normalizan antes de comparar.

**RF-GUARD-03 [demo]** · Cuando haya coincidencia, el sistema deberá devolver el capítulo
al redactor, registrarla en el audit log y en Langfuse, y **detener la generación tras dos
pasadas consecutivas sin limpiar**, sin esperar al tercer intento.

### 3.7 `quality/` — validadores

**RF-QUA-01 [demo]** · El sistema deberá ejecutar en el hook de policy los validadores
`schema_valido` y `palabras_prohibidas`.

**RF-QUA-02 [demo]** · El sistema deberá ejecutar en el hook de capítulo, **en paralelo y
fuera del pool de tokens**, los validadores programáticos: `nombres_exactos`, `longitud`,
`consistencia_factica`, `calidad_prosa`, `integridad_pov`, `cumplimiento_brief` y
`reglas_mundo`.

> *Dado* un capítulo que escribe el nombre del destinatario distinto de como está en la
> story bible, *cuando* corre `nombres_exactos`, *entonces* falla y el capítulo vuelve al
> redactor.

**RF-QUA-03 [demo]** · El sistema deberá ejecutar en el gate de publicación
`elementos_obligatorios`, `cierre_arco`, `estructura_edicion` y `render_visual`, y **no
publicar** si alguno falla.

> *Dado* un `Elemento personalizado` obligatorio que no aparece en ningún capítulo,
> *cuando* corre el gate, *entonces* la versión no se publica.

**RF-QUA-04 [demo]** · El `judge` deberá puntuar los seis criterios de la rúbrica **por
separado y con justificación**, en el modelo de `config/models.yaml` § `roles.judge`, que
es **distinto del redactor** (TO-013).

**RF-QUA-05 [demo]** · El `editor` deberá corregir el borrador a partir del informe de
crítica, y su salida deberá volver a pasar **todos** los validadores, no solo el que falló.

**RF-QUA-06 [demo]** · El sistema deberá ejecutar en el rol editor los validadores
`invencion_destinatario` y `temas_excluidos`.

> *Dado* un capítulo que atribuye al destinatario un hecho personal que no está en el brief
> ni en el texto libre, *cuando* corre `invencion_destinatario`, *entonces* falla. Es el
> fallo más grave del sistema en un regalo y `consistencia_factica` no lo detecta, porque
> el canon absorbió el hecho inventado al extraerlo.

**RF-QUA-07 [demo]** · Mientras `medicion.cerrar_el_paso` sea `false`, los validadores
semánticos deberán puntuar y **no** suspender; los booleanos cierran el paso siempre.

**RF-QUA-08 [post-demo]** · El sistema deberá medir precisión y cobertura de cada validador
sobre un corpus de `Defecto inyectado`.

### 3.8 `policy/` — decisiones

**RF-POL-01 [demo]** · El policy engine deberá decidir aceptar o devolver un capítulo y
adoptar o descartar un hecho, y dejar **una fila en el audit log por decisión**, con la
regla aplicada, la entrada y el resultado.

**RF-POL-02 [demo]** · El audit log deberá ser **solo de escritura**: ningún camino del
código lo actualiza ni lo borra.

### 3.9 `versioning/` — versiones y regeneración

**RF-VER-01 [demo]** · Cuando todos los capítulos estén aceptados y el gate pase, el
sistema deberá publicar una `Versión de novela` **inmutable**, con su hash y su vínculo a
la anterior.

**RF-VER-02 [demo]** · El sistema deberá servir cualquier versión publicada **entera**, con
su índice de capítulos y la marca de los modificados respecto a la anterior.

> *Dado* que se publicó la versión 3, *cuando* se pide la 1, *entonces* se devuelve tal
> como se publicó. **La versión anterior nunca se sobrescribe** (`CLAUDE.md` regla 15).

**RF-VER-03 [demo]** · El sistema deberá marcar `modificado` en el vínculo entre versión y
capítulo, y esa marca deberá coincidir con el cambio real del texto.

**RF-VER-04 [demo]** · El sistema deberá servir la ficha de personajes y lugares de una
versión, generada desde la story bible **de esa versión**, con los capítulos donde aparece
cada uno.

**RF-VER-05 [demo]** · El sistema deberá servir la portada con la dedicatoria del brief.

**RF-VER-06 [demo]** · Cuando el lector pida un cambio sobre un hecho, el sistema deberá
calcular el `Análisis de impacto` sobre la relación **`usa`** —no sobre `establece`— y
devolverlo **sin regenerar nada**.

> *Dado* un hecho establecido en el capítulo 2 y usado en el 7, *cuando* se pide el
> cambio, *entonces* el análisis devuelve los dos capítulos.

**RF-VER-07 [demo]** · Cuando el lector pida el cambio seleccionando un **fragmento**, el
sistema deberá proponer un hecho candidato y esperar confirmación: la selección de
fragmento **nunca regenera sola** (TO-011).

**RF-VER-08 [demo]** · Cuando el lector confirme la solicitud, el sistema deberá aplicar el
retcon por vigencia, marcar `Obsoleto` los capítulos afectados **y solo esos**, regenerarlos,
volver a pasar el gate completo y publicar una versión nueva.

> *Dado* una novela en la versión 1 con tres capítulos afectados, *cuando* se confirma el
> cambio, *entonces* la versión 2 tiene esos tres reescritos, **los otros siete idénticos
> byte a byte**, y la versión 1 sigue consultable.

**RF-VER-09 [demo]** · Cuando llegue una solicitud de cambio mientras hay una generación o
regeneración en curso para esa novela, el sistema deberá rechazarla con
`409 generacion-en-curso`.

### 3.10 `versioning/` — export

**RF-EXP-01 [demo]** · Cuando se pida el export de una versión, el sistema deberá generar
el PDF con `page.pdf()` de Playwright **del mismo render** que sirve la lectura web, una
sola vez por versión (TO-003, TO-025).

**RF-EXP-02 [demo]** · El sistema deberá servir el PDF generado y ejecutar
`paridad_pdf_web` al generarlo, comprobando recuento y títulos de capítulos, presencia de
dedicatoria e índice, y recuento de palabras dentro de
`export.tolerancia_recuento_palabras`.

**RF-EXP-03 [post-demo]** · Cuando `formal.gate_activo` sea `true`, el sistema deberá
generar el fichero Lean desde la story bible, ejecutar `lake build` en el gate y **no
publicar** si falla, devolviendo el fallo al editor como feedback.

> Está **fuera de la demo** porque no hay toolchain Lean instalada. Mientras tanto,
> `GET /salud` lo dice, para que la lectura no dé por demostrada una cronología que nadie
> ha demostrado.

### 3.11 `commons/` — observabilidad y meta

**RF-OBS-01 [demo]** · El sistema deberá abrir **una sesión de Langfuse por novela**, que
agrupe la entrevista, la generación y todas las regeneraciones.

**RF-OBS-02 [demo]** · El sistema deberá emitir **un span por rol y uno por tool**, con los
nombres de `docs/architecture.md` § Agentes. Una llamada al modelo sin span es un fallo.

**RF-OBS-03 [demo]** · El sistema deberá emitir **un score por validador ejecutado**, con
justificación cuando el validador sea semántico.

**RF-OBS-04 [demo]** · El sistema deberá registrar tokens, coste y latencia **por llamada,
por capítulo y por novela**.

**RF-OBS-05 [demo]** · El sistema deberá vincular cada capítulo a la **versión de prompt**
con que se generó, registrando el hash de git del fichero **realmente usado**.

**RF-META-01 [demo]** · El sistema deberá exponer su salud: si el gate de Lean está activo,
si la fase de medición cierra el paso, y cuánto presupuesto en vuelo queda libre.

---

## 4. Contrato OpenAPI

**Primero el contrato.** La interfaz entre backend y frontend es
**`specs/openapi.yaml`**, un OpenAPI 3.1 versionado en el repositorio. Este documento
**no lo duplica**: explica qué hace cada endpoint y a qué requisito responde, y remite al
fichero para su forma exacta —campos, tipos, códigos y ejemplos—.

**Cómo se usa, y por qué en este orden.** El fichero es la fuente, no un producto: el
backend lo implementa y **un test compara el OpenAPI que genera FastAPI con
`specs/openapi.yaml`; si divergen, el test falla**. El frontend genera su cliente tipado
desde el mismo fichero. Por eso el frontend puede empezar hoy: el contrato ya existe y no
depende de que el backend esté escrito.

### 4.1 Decisiones que fija el contrato

| Decisión | Elección | Por qué |
| --- | --- | --- |
| Idioma de rutas y `operationId` | **Español** | Los nombres del código son los de la ontología (`CLAUDE.md` regla 1). Los `operationId` son **estables**: de ellos salen los nombres del cliente |
| Identificadores | `novel_id` **UUID** del servidor; versión **entero correlativo** por novela | El correlativo se lee en la URL y es lo que compara la marca de capítulos modificados |
| Progreso | **Sondeo**, no SSE | OpenAPI 3.1 describe un `text/event-stream` pero ningún generador produce de ahí un cliente tipado útil, y el frontend tendría que escribir el parseo a mano. SSE queda post-demo |
| Cuándo dejar de sondear | Campo **`es_terminal`** y `intervalo_sondeo_segundos` en el propio recurso | El cliente no deduce la terminalidad del nombre del estado |
| Errores | **RFC 9457 `application/problem+json`** con `type` de catálogo cerrado | Da un `type` discriminable en vez de prosa, y admite contexto —`novel_id`, `capitulo`, `intentos_restantes`— |
| Petición repetida cara | `POST /generaciones` duplicado → **409** con el id vivo | Encolar dos gasta tokens dos veces; un `202` silencioso esconde que no se lanzó nada |
| Idempotencia | **Sin `Idempotency-Key`** | Ya vive donde importa: la escritura a la story bible por `novel_id` + `chapter_id` + `version` |
| Brief en dos formas | **`BriefNovelaParcial`** para `validarBrief`, todos los campos opcionales; **`BriefNovela`** completo para `crearNovela` (TO-037) | La validación tiene que poder decir qué falta sin rechazar la petición, y la creación no puede aceptar un brief al que le falte algo. Un solo schema obligaba a elegir entre las dos |

### 4.2 Endpoints y a qué requisito responden

| Operación | Método y ruta | RF | Fase |
| --- | --- | --- | --- |
| `obtenerSalud` | `GET /salud` | RF-META-01 | F0 |
| `validarBrief` | `POST /briefs/validacion` | RF-INTAKE-01/02/03 | F3 |
| `crearNovela` | `POST /novelas` | RF-INTAKE-04/05 | F1 |
| `listarNovelas` | `GET /novelas` | RF-NOVEL-02 | F1 |
| `obtenerNovela` | `GET /novelas/{novel_id}` | RF-NOVEL-03 | F1 |
| `lanzarGeneracion` | `POST /novelas/{novel_id}/generaciones` | RF-PROC-01/02 | F1 |
| `listarGeneraciones` | `GET …/generaciones` | RF-PROC-04 | F1 |
| `obtenerGeneracion` | `GET …/generaciones/{generacion_id}` | RF-PROC-05 | F1 |
| `listarVersiones` | `GET …/versiones` | RF-VER-01 | F1 |
| `obtenerVersion` | `GET …/versiones/{version}` | RF-VER-02/03 | F1 |
| `listarCapitulos` | `GET …/versiones/{version}/capitulos` | RF-NOVEL-05 | F1 |
| `obtenerCapitulo` | `GET …/capitulos/{numero}` | RF-NOVEL-05 | F1 |
| `obtenerFicha` | `GET …/versiones/{version}/ficha` | RF-VER-04 | F5 |
| `obtenerPortada` | `GET …/versiones/{version}/portada` | RF-VER-05 | F5 |
| `listarHechos` | `GET …/versiones/{version}/hechos` | RF-CANON-03 | F4 |
| `crearSolicitudCambio` | `POST …/solicitudes-cambio` | RF-VER-06/07/09 | F4 |
| `obtenerSolicitudCambio` | `GET …/solicitudes-cambio/{solicitud_id}` | RF-VER-06 | F4 |
| `confirmarSolicitudCambio` | `POST …/{solicitud_id}/confirmacion` | RF-VER-08 | F4 |
| `exportarVersion` | `POST …/versiones/{version}/export` | RF-EXP-01 | F5 |
| `descargarExport` | `GET …/versiones/{version}/export` | RF-EXP-02 | F5 |

### 4.3 Catálogo cerrado de errores

`peticion-invalida` (422), `brief-invalido` (400), `novela-no-encontrada` (404),
`version-no-encontrada` (404), `hecho-no-encontrado` (404), `generacion-en-curso` (409),
`transicion-invalida` (409), `trabajo-no-cabe-en-pool` (422),
`limite-de-intentos-agotado` (409), `palabra-prohibida-persistente` (409),
`export-no-disponible` (404) y `error-interno` (500).

**El 422 de validación de FastAPI se sobrescribe** para que también sea `problem+json`:
toda respuesta de error tiene la misma forma, y **el test de conformidad lo cubre**. Un
catálogo abierto degenera en un campo de texto que nadie puede discriminar.

### 4.4 Contrato de lectura

Lo que `render_visual` y el export a PDF necesitan de la página `lectura` del frontend. Es
el **segundo contrato** entre backend y frontend, y el único que no está en
`specs/openapi.yaml`, porque no es HTTP sino DOM (TO-037). **El frontend implementa esta
lista tal cual**; cambiarla es cambiar esta spec, igual que cambiar el OpenAPI.

**CL-01 · Ruta.** La lectura de una versión vive en la ruta del frontend
**`/novelas/{novel_id}/versiones/{version}`**, sobre la URL base que declara
`STORYMAKER_LECTURA_URL`. Esa ruta pinta **la versión entera en un solo documento**: portada,
índice, ficha y los diez capítulos están en el DOM a la vez, aunque en pantalla se plieguen.
Es lo que permite validar y exportar un único render.

**CL-02 · Señal de carga.** El elemento raíz `lectura` lleva `data-estado` con `cargando`,
`lista` o `error`. Playwright espera a `lista` antes de afirmar o de exportar: esperar a un
tiempo fijo es una prueba que falla según la máquina.

**CL-03 · Selectores `data-testid` estables.** Todos los `data-*` numéricos son el entero
del contrato OpenAPI —número de capítulo o versión—, sin ceros a la izquierda.

| `data-testid` | Cuántos | Dentro de | Atributos y contenido |
| --- | --- | --- | --- |
| `lectura` | 1 | — | `data-estado`, `data-novel-id`, `data-version` |
| `portada` | 1 | `lectura` | — |
| `portada-titulo` | 1 | `portada` | Texto: `Portada.titulo` |
| `portada-dedicatoria` | 1 | `portada` | Texto: `Dedicatoria.texto` |
| `indice` | 1 | `lectura` | — |
| `indice-entrada` | Uno por capítulo, en orden | `indice` | `data-capitulo`; contiene un enlace a `#capitulo-{n}` |
| `ficha` | 1 | `lectura` | — |
| `ficha-personaje` | Uno por entrada de `Ficha.personajes` | `ficha` | `data-nombre` |
| `ficha-lugar` | Uno por entrada de `Ficha.lugares` | `ficha` | `data-nombre` |
| `ficha-enlace-capitulo` | Uno por capítulo de cada entrada | `ficha-personaje` o `ficha-lugar` | `data-capitulo`; enlace a `#capitulo-{n}` |
| `capitulo` | Uno por capítulo, en orden | `lectura` | `data-capitulo`, `id="capitulo-{n}"` |
| `capitulo-titulo` | 1 por capítulo | `capitulo` | Texto: `Capitulo.titulo` |
| `capitulo-texto` | 1 por capítulo | `capitulo` | Texto: `Capitulo.texto`, sin añadidos, porque sobre él se cuentan las palabras de `paridad_pdf_web` |
| `capitulo-modificado` | 0 o 1 | `indice-entrada` y `capitulo` | Presente **solo** si `modificado` es `true` |

**CL-04 · Hoja de estilos de impresión.** La lectura tiene reglas `@media print`. Con los
medios en `print`: todos los `capitulo` son visibles aunque en pantalla estén plegados, cada
`capitulo` empieza en página nueva, y los controles interactivos —la petición de cambio,
la navegación— no se imprimen. El export emula `print` antes de `page.pdf()`.

**CL-05 · Qué comprueba el backend.** `render_visual` y `paridad_pdf_web` solo usan estos
selectores y estos atributos. Un selector que falte es un fallo del gate con el nombre del
selector, y se enruta como dice `docs/architecture.md` § `render_visual` en el gate: si el
dato está en la story bible y no se pinta, es un bug de maquetación y **no gasta intentos de
capítulo**.

---

## 5. Requisitos de datos

El esquema **no se copia aquí**. La correspondencia clase a tabla, el versionado por
vigencia y los seis índices viven en `docs/architecture.md` § Story bible, y el SQL sale
de ahí sin decidir nada más.

Lo que esta spec añade sobre esa sección:

- **`RD-01`** Toda tabla de dominio lleva `novel_id` desde la primera migración, y ninguna
  lleva `user_id` ni `tenant_id`.
- **`RD-02`** `novel_id` y `version` son **parámetros obligatorios sin valor por defecto**
  de toda consulta de dominio. Una consulta que los olvide devuelve «lo vigente» en
  silencio, que es el fallo que más caro sale.
- **`RD-03`** Las migraciones viven en `backend/app/commons/db/migrations/`, numeradas, se
  aplican en orden y **nunca se editan** una vez commiteadas.
- **`RD-04`** `WAL` activado y claves foráneas activas **en toda conexión**, no solo en la
  que abre el backend.
- **`RD-05`** La vigencia de una fila de `hecho_capitulo` está contenida en la de su
  `hecho`. Es un invariante de esquema, no una convención.
- **`RD-06`** Hay una tabla de **trabajos** que sostiene RF-PROC-03: es lo único que esta
  spec añade al modelo de `architecture.md`, y es materialización del `Checkpoint`, no una
  clase nueva de la ontología.

---

## 6. Requisitos no funcionales

Las cifras se referencian; ninguna se copia.

| # | Requisito | Cifra en |
| --- | --- | --- |
| **RNF-01** | Ningún prompt supera el límite de contexto por petición, y el reparto por capa suma exactamente ese total | `thresholds.yaml` § `contexto` |
| **RNF-02** | La suma de las llamadas simultáneas nunca supera el presupuesto en vuelo. El pool es un semáforo en proceso con admisión **FIFO estricta** | § `en_vuelo.total` |
| **RNF-03** | Un trabajo cuya estimación supera el presupuesto total **falla al encolarse**; esperar un hueco imposible es colgarse | § `en_vuelo.total` |
| **RNF-04** | Todo reintento tiene límite, y hay dos contadores que no se mezclan: defecto del capítulo y fallo de infraestructura | § `orquestacion` |
| **RNF-05** | Toda llamada al modelo es asíncrona y lleva **timeout explícito** | — |
| **RNF-06** | Las escrituras a la story bible son idempotentes por `novel_id` + `chapter_id` + `version` y ocurren en transacción | — |
| **RNF-07** | Una versión publicada es **inmutable**, y su hash lo demuestra | — |
| **RNF-08** | Todo rol y toda tool emiten span; todo validador, score. Sin excepción | — |
| **RNF-09** | **El texto libre es contenido no confiable**: entra marcado como datos, nunca en la posición de las instrucciones, y ningún camino del código ejecuta, evalúa ni lanza como proceso la salida del modelo | — |
| **RNF-10** | Aislamiento por `novel_id`: un brief no puede leer hechos de otra novela | — |
| **RNF-11** | **Ninguna credencial en el repositorio.** Solo `.env.example` con los nombres. Los casetes de prueba se graban sin cabeceras de autenticación y pasan el escaneo de secretos antes de commitear | `CLAUDE.md` regla 12 |
| **RNF-12** | La instancia **escucha solo en la interfaz local** mientras no haya autenticación | `architecture.md` § Seguridad |
| **RNF-13** | Coste y latencia por novela bajo umbral; superarlo detiene e informa | § `coste` |
| **RNF-14** | `config/` es la **fuente única de cifras**: ninguna se duplica en documentos ni se escribe suelta en el código | — |
| **RNF-15** | El arranque **falla en voz alta** si falta un umbral que se usa para cerrar el paso, o si el margen no cubre el `max_tokens` de algún rol | § `modelo`, § `medicion` |

**Proveedor del modelo (TO-040, aprobado por el desarrollador el 2026-09-24).** `proveedor`
en `config/models.yaml` elige entre la API (`api`) y el CLI de Claude Code como subproceso
(`claude_code`). Con `claude_code` cambian tres requisitos, y el cambio es deliberado:

- **RF-CTX-02 y RNF-01**: el recuento previo es una estimación con margen, no el del proveedor;
  «contar antes de llamar» se sigue cumpliendo, con la estimación.
- **RNF-13**: el coste que se registra y que vigila `coste_maximo_novela` es **nominal**, a
  precio de lista; la sesión no se factura por llamada.
- **Schema estricto** (`verification.md` A-68, O-01): no hay modo `strict`; la salida se
  valida después con Pydantic y un fallo de schema cuenta como intento fallido.

Y endurece **RNF-09**: el CLI se lanza sin ninguna herramienta, en una carpeta temporal vacía,
con el texto de la novela solo por la entrada estándar (`architecture.md` § Proveedor del
modelo).

### 6.1 Privacidad

**El brief contiene datos personales reales del destinatario** —nombre, edad, rasgos,
recuerdos—, y esos datos **viajan en los prompts y quedan en las trazas de Langfuse**. Tres
consecuencias, y ninguna es opcional:

- **`RNF-16`** `Comprador.identificador` es una cadena **opaca**: nunca un correo ni un
  nombre. El contrato lo dice en el schema y el validador de brief lo comprueba.
- **`RNF-17`** Todos los briefs de ejemplo, de prueba y de la documentación —incluidos los
  cinco briefs de evaluación y el de la novela de ejemplo— usan **datos ficticios**.
- **`RNF-18`** La retención de las trazas de Langfuse queda como **pregunta abierta**
  (§ 10.2). Decirlo aquí es lo que impide que se convierta en una decisión por omisión.

### 6.2 Estrategia de pruebas del cliente del modelo

`CLAUDE.md` regla 8 prohíbe mocks en `backend/app/`, «ni siquiera temporales», y el
redactor no se puede llamar de verdad en cada prueba. Tres capas:

1. **Costura por `Protocol`.** `commons/llm/` define un `Protocol` con **una sola**
   implementación de producción. El doble vive en **`tests/dobles/`** y se inyecta con el
   override de dependencias de FastAPI. No hay mock en el código de producción porque el
   doble no está en él.
2. **Casetes grabados** de respuestas reales, que cubren la serialización y el conteo de
   tokens, que es donde un doble escrito a mano miente. **Se graban solo si la credencial
   está en el entorno**; si no está, esta capa queda pendiente y **no bloquea** el resto.
   Se graban con las cabeceras de autenticación eliminadas y **pasan el escaneo de secretos
   antes de cualquier commit**.
3. **Un test en vivo** marcado `@pytest.mark.real`, **excluido de CI**, que se ejecuta a
   mano antes de una demo.

---

## 7. Fases de construcción

El plan las sigue **en este orden**. Cada fase termina con algo que se puede enseñar.

### F0 — Fundación

FastAPI con su `lifespan`; migraciones numeradas y su runner; carga y validación de
`config/thresholds.yaml` y `config/models.yaml` con el fallo en voz alta de RNF-15;
cliente del modelo con conteo de tokens del proveedor y el pool en vuelo; cliente de
Langfuse; handler central de errores en `problem+json`; y **el test de conformidad con
`specs/openapi.yaml`**.

*Criterio de terminado*: `GET /salud` responde, el test de conformidad pasa y un arranque
con un umbral de cierre en `null` falla con un mensaje que dice cuál.

### F1 — Generación de extremo a extremo

Desde un brief JSON: planner → writer → validadores programáticos mínimos
(`schema_valido`, `longitud`, `nombres_exactos`, `palabras_prohibidas`) → story bible
básica con hechos y su uso por capítulo → resúmenes → checkpoint y reanudación → versión
publicada. Endpoints de crear novela, lanzar generación, consultar progreso y leer
capítulos. **La tabla de transiciones del orquestador existe como dato desde esta fase**
(RF-PROC-07), antes que la spec TLA+ que la comparará.

*Criterio de terminado*: una novela completa de diez capítulos publicada como versión 1, y
**la prueba de reanudación**: matar el proceso a mitad del capítulo 5 y comprobar que al
rearrancar continúa por el 5 sin duplicar ni perder nada.

### F2 — Calidad

`editor` en el modelo alto y `judge` en el de `config/models.yaml` § `roles.judge`, con la
rúbrica de seis criterios, puntuación y justificación por criterio; scores en Langfuse;
reintentos con límite y los dos contadores separados; el resto de validadores del hook de
capítulo.

*Criterio de terminado*: un capítulo defectuoso a propósito vuelve al redactor, se corrige
y se acepta, con los scores visibles en la traza.

### F3 — Intake

Formulario que produce el mismo `BriefNovela` validado, con extracción de hechos del texto
libre como contenido no confiable, `Dato faltante`, contradicciones por reglas
deterministas, y temas y palabras prohibidas por novela, con `invencion_destinatario` y
`temas_excluidos`.

*Criterio de terminado*: el brief adversarial —con una inyección en el texto libre—
produce un `Fragmento sospechoso` registrado y descartado, y ningún capítulo obedece la
instrucción inyectada.

### F4 — Regeneración

Solicitud de cambio → análisis de impacto sobre `usa` → confirmación → retcon por vigencia
→ regeneración solo de los capítulos afectados → versión nueva que conserva la anterior y
marca los cambiados.

*Criterio de terminado*: «el perro se llama Nala» produce la versión 2 con los capítulos
afectados reescritos, **el resto idénticos byte a byte** y la versión 1 consultable entera.

### F5 — Salida

Ficha de personajes y lugares, portada con dedicatoria, `render_visual` con el browser MCP
y **export a PDF con Playwright**, con `paridad_pdf_web`, todo contra el **contrato de
lectura** de § 4.4. Hasta que el frontend tenga la página `lectura`, las pruebas del backend
usan una página de prueba que cumple ese contrato.

*Criterio de terminado*: `ejemplos/novela-ejemplo.pdf` generado desde una versión
publicada contra la página `lectura` real. **El export es entregable obligatorio del
alcance**: si hay que recortar, se recorta su pulido, nunca el export. Si la página `lectura`
todavía no existe al cerrar F5, el PDF queda **pendiente del paso de integración**, nunca
descartado. El gate de Lean entra si sobra tiempo y hay toolchain.

### Post-demo

Entrevistador conversacional (RF-INTAKE-06, obligatorio del alcance); spec TLA+ con sus
invariantes, TLC y el test de correspondencia; servidor MCP de solo lectura; agente de
seguridad; los cinco briefs de prueba y la tabla brief × validador; la iteración de tuning;
la revisión humana; el gate de Lean; SSE para el progreso; y PO-11 y PO-12.

---

## 8. Trazabilidad

| Requisito | Alcance § | Decisión | Filas de `docs/verification.md` |
| --- | --- | --- | --- |
| RF-INTAKE-01, 02 | §1 | TO-027, **TO-037** | P-65, P-66, O-01 |
| RF-INTAKE-03 | §1 | — | P-67, P-20, A-11, A-97 |
| RF-INTAKE-04, 05 | §1, §7 | — | O-01, O-05 |
| RF-INTAKE-06 | §1 | TO-027 | P-65 |
| RF-PROC-01, 02 | §3 | **TO-030** | P-59 |
| RF-PROC-03 | §3 | **TO-030** | P-59, A-74, A-75 |
| RF-PROC-04, 05 | §6 | **TO-031** | P-69, P-72 |
| RF-PROC-06 | §4 | TO-023 | P-61, A-16 |
| RF-PROC-07 | §5d | TO-020 | A-92, A-94, P-74 |
| RF-PROC-08 | §3 | TO-014 | P-58, A-81 |
| RF-PROC-09 | §3 | TO-014 | A-78 |
| RF-PROC-10 | §4 | — | P-60, A-54 |
| RF-CTX-01…05 | §3 | TO-015, TO-021 | A-01…A-10, A-73, A-77 |
| RF-NOVEL-01 | §5a | TO-005 | O-30, P-54 |
| RF-NOVEL-02, 03, 05 | §2 | — | A-43 |
| RF-NOVEL-04 | §5 | — | P-78, P-79 |
| RF-CANON-01 | §4 | — | A-17, A-27, A-28, O-32 |
| RF-CANON-02 | §4 | — | A-34, P-62 |
| RF-CANON-03 | §2 | TO-028 | A-84, A-85, A-86 |
| RF-CANON-04 | §4 | — | A-54 |
| RF-CANON-05 | §4 | TO-028 | A-30, A-34, § Puntos ciegos #7 |
| RF-GUARD-01, 02, 03 | §7 | TO-008, TO-014 | O-05, O-06, O-07, O-08, A-79 |
| RF-QUA-01…03 | §5a | TO-018 | O-01…O-04, O-09, O-34, O-57 |
| RF-QUA-04 | §5b | TO-013 | O-11, P-85 |
| RF-QUA-05 | §5 | — | A-49, A-50 |
| RF-QUA-06 | §1, §5b | **PO-1, PO-2** | O-20, O-21 |
| RF-QUA-07 | §5 | — | P-84, A-41 |
| RF-QUA-08 | §5 | — | P-50, P-88 |
| RF-POL-01, 02 | §7 | — | P-56, P-57, A-87 |
| RF-VER-01, 02, 03 | §2 | TO-028 | O-61, O-63, O-64, A-88, P-63 |
| RF-VER-04, 05 | §2 | — | O-59, O-60, O-18 |
| RF-VER-06, 07 | §2 | TO-011 | O-62, P-62 |
| RF-VER-08 | §2 | TO-011, TO-028 | P-62, P-64, O-61 |
| RF-VER-09 | §2 | **TO-032** | — |
| RF-EXP-01, 02 | §2 | TO-003, TO-025, TO-026 | O-16, A-103, A-105 |
| § 4.4 contrato de lectura, CL-01…05 | §2, §5a | **TO-037** | O-09, O-10, O-16, O-59, O-60 |
| RF-EXP-03 | §5c | TO-016 | O-13, O-14, O-15, P-81, P-82 |
| RF-OBS-01…05 | §6 | TO-024 | P-68…P-73, A-45, A-71 |
| RF-META-01 | §6 | — | P-84 |
| RD-01…06 | §4 | TO-004, TO-028 | A-53, A-83, A-84, A-86, A-19, A-82 |
| RNF-01…15 | §3, §7 | TO-014, TO-019 | A-01…A-09, A-74, A-78, A-88, RNF ↔ A-40 |
| RNF-16…18 | §1 | **TO-033** | — |
| § 6.2 pruebas | §3 | **TO-034** | A-44, A-99 |

**Cinco decisiones nuevas** se registran en `docs/trade-offs.md` como **TO-030** (worker
único en proceso), **TO-031** (sondeo frente a SSE), **TO-032** (RFC 9457 y el 409 sin
`Idempotency-Key`), **TO-033** (identidad ausente y privacidad del brief) y **TO-034**
(pruebas del cliente del modelo sin mocks). Las cinco salieron del grill de esta tarea y
están **aprobadas por el desarrollador**, no decididas por el agente.

**Decidido por el agente — revisar**: lo que este documento fija sin haber pasado por el
grill está marcado así en `docs/trade-offs.md` **TO-035**: la forma concreta de los
recursos y sus nombres, la paginación de `GET /novelas`, que `listarCapitulos` no pagine,
que el export sea `POST` más `GET` sobre la misma ruta, y la tabla de trabajos de RD-06.

**Cambio de contrato aprobado por el desarrollador**, **TO-037**: el brief parcial para la
validación, con el contrato OpenAPI en 1.1.0, y el contrato de lectura de § 4.4.

---

## 9. Fuera de alcance

Autenticación y cuentas (TO-004); pagos; impresión física; ilustraciones; audio; despliegue
en producción; búsqueda vectorial con `sqlite-vec` (TO-015); linters de prosa como
herramienta externa y el linter de edición manual (TO-017); tools de escritura sobre MCP; y
**PO-11** —coste de desplazamiento entre lugares— y **PO-12** —estado epistémico de
personaje—, que quedan post-demo y **no se usan en ningún requisito de esta spec**.

---

## 10. Preguntas abiertas

### 10.1 Que no bloquean la demo

1. **Retención de las trazas de Langfuse.** Contienen datos personales del destinatario
   (RNF-18). Hay que decidir plazo y borrado antes de que la instancia salga de local.
2. **Qué hacer con una novela `Detenida`.** Hoy es terminal y no hay forma de retomarla
   desde la API. ¿Se reanuda tras intervención, o se clona en una novela nueva?
3. **Límite de novelas simultáneas.** El pool acota los tokens, no el número de novelas en
   cola. Con un usuario no duele; conviene fijarlo antes de abrirlo.

### 10.2 Que el plan puede resolver

4. **Umbral de similitud para proponer un hecho candidato** desde un fragmento (RF-VER-07):
   es una cifra y va a `config/`, pero no hay corpus para elegirla.
5. **Orden exacto de los validadores dentro del hook de capítulo.** Corren en paralelo, así
   que el orden solo importa para el informe; el plan puede fijarlo.
