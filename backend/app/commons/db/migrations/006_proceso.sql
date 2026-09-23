-- Migracion 006 - H6. Capa 5: el ciclo de produccion y su trazabilidad.
--
-- Nueve tablas para las siete clases que `architecture.md` asigna a `process/`
-- --Esquema, Brief de escena, Restriccion de destino, Borrador, Version,
-- Registro de generacion y Deriva-- mas `training_samples`, que entra en v1 por
-- RF-PROC-09 sin estar ratificada en la ontologia (riesgo declarado en la spec
-- seccion 9 y en la fila A-46).
--
-- Lo que esta migracion NO hace, y conviene leerlo antes de buscarlo: no anade
-- la clave foranea que la 005 dejo anunciada de `informe_critica` a `borrador`.
-- Anadirla exige reconstruir la tabla, y cualquier informe emitido en H5 es
-- anterior a que existieran los borradores: la migracion fallaria en toda base
-- con historial. La cardinalidad 1:1 la sigue llevando el `UNIQUE (escena_id,
-- version)` que la 005 ya tiene, que es lo que el esquema puede afirmar.

-- ---------------------------------------------------------------------------
-- Esquema: un hito de plan
-- ---------------------------------------------------------------------------
-- `Esquema` es la estructura planificada, y lo que de ella importa al ciclo es
-- **cuando cambio**. Cada fila es un hito de plan: la huella del conjunto de
-- restricciones de destino aun no escritas, mas el motivo que escribe el autor.
--
-- En v1 editar el esquema a mano es la unica forma de replanificar, asi que
-- esta tabla **es** RF-PROC-13, y sus filas son las etiquetas con las que se
-- calibran los tres umbrales de deriva en modo sombra. Sin el motivo no hay
-- etiqueta: por eso `motivo` es NOT NULL y no admite cadena vacia.
--
-- `posicion` es donde estaba el discurso al fijarse el hito: la posicion de la
-- ultima escena aceptada en ese momento. Es lo que da sentido a «desde el
-- ultimo hito de plan» sin depender de relojes: un hilo o una promesa que se
-- abren mas adelante son canon que el plan no pudo recoger, porque el plan es
-- anterior a que existieran.
CREATE TABLE esquema (
    id        INTEGER PRIMARY KEY,
    plan_hash TEXT NOT NULL,
    motivo    TEXT NOT NULL CHECK (TRIM(motivo) <> ''),
    posicion  INTEGER NOT NULL,
    fijado_en TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Brief de escena y restriccion de destino
-- ---------------------------------------------------------------------------
-- `Brief de escena encarga Escena`, 1:1: el `UNIQUE` **es** esa cardinalidad.
--
-- El brief es minimo por diseno --estado de entrada mas restriccion de destino--
-- y no lleva beats: `Beat` es descubrimiento libre y su fuente de verdad es el
-- texto generado (AGENTS.md, Modelo de autoria). Una columna de beats aqui
-- seria el modo planificado entrando por la puerta de atras.
CREATE TABLE brief_escena (
    id                INTEGER PRIMARY KEY,
    escena_id         INTEGER NOT NULL UNIQUE REFERENCES escena (id) ON DELETE CASCADE,
    estado_de_entrada TEXT NOT NULL,
    encargo           TEXT,
    creado_en         TEXT NOT NULL
);

-- `Restriccion de destino acota Brief de escena`, 1:N, y `Esquema fija
-- Restriccion de destino`, 1:N.
--
-- Los tres `tipo` son los de la ontologia y son los tres comprobables contra un
-- snapshot sin modelo de por medio (verification.md, Soluciones picaras 5):
-- que estado queda declarado, si existe la revelacion, si esta el personaje
-- donde decia. Las columnas de abajo son lo que hace ejecutable cada pregunta.
--
-- `alcance` existe en la ontologia sin contenido especificado, y esta fila lo
-- hereda: es la carencia que deja `canon_huerfano` e `inviabilidad_pago` en su
-- forma debil (spec seccion 9, filas P-52 y P-53). No se inventa aqui un formato.
CREATE TABLE restriccion_destino (
    id           INTEGER PRIMARY KEY,
    brief_id     INTEGER NOT NULL REFERENCES brief_escena (id) ON DELETE CASCADE,
    tipo         TEXT NOT NULL CHECK (
                     tipo IN ('estado_final', 'revelacion', 'posicion_de_personaje')
                 ),
    enunciado    TEXT NOT NULL,
    alcance      TEXT,
    -- Lo declarado que se puede cotejar. Que columna usa cada tipo lo decide
    -- `process/deriva.py`, que es donde se lee la regla.
    personaje_id INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    lugar_id     INTEGER REFERENCES lugar (id) ON DELETE CASCADE,
    hecho_id     INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL,
    valor        TEXT
);

CREATE INDEX idx_restriccion_brief ON restriccion_destino (brief_id);

-- ---------------------------------------------------------------------------
-- Registro de generacion
-- ---------------------------------------------------------------------------
-- `registrar-generacion` corre en **toda** llamada al modelo, sin excepcion
-- (A-45, RF-PROC-04). Sin esta fila no se puede reproducir un resultado bueno
-- ni diagnosticar uno malo.
--
-- Las tres huellas son la picara 9: reproducir deja de ser comparar prosa y
-- pasa a ser comparar hashes. Si las huellas coinciden y la salida difiere, el
-- cambio es del proveedor y no nuestro, que es la mitad de `P-24` que el
-- sistema si controla.
--
-- `escena_id` admite NULL porque no toda llamada al modelo pertenece a una
-- escena: el planificador trabaja sobre el esquema. La fila se escribe igual.
CREATE TABLE registro_generacion (
    id                INTEGER PRIMARY KEY,
    escena_id         INTEGER REFERENCES escena (id) ON DELETE CASCADE,
    agente            TEXT NOT NULL,
    modelo            TEXT NOT NULL,
    prompt            TEXT NOT NULL,
    contexto          TEXT NOT NULL,
    semilla           TEXT,
    huella_prompt     TEXT NOT NULL,
    huella_contexto   TEXT NOT NULL,
    huella_parametros TEXT NOT NULL,
    tokens_de_entrada INTEGER,
    tokens_de_salida  INTEGER,
    timeout_segundos  REAL NOT NULL,
    registrado_en     TEXT NOT NULL
);

CREATE INDEX idx_registro_escena ON registro_generacion (escena_id, id);

-- ---------------------------------------------------------------------------
-- Borrador y version
-- ---------------------------------------------------------------------------
-- `Borrador realiza Brief de escena`, N:1: un brief acumula tantos borradores
-- como intentos haga falta. Cada uno apunta a su registro de generacion, que es
-- lo que ata el texto al prompt del que salio.
CREATE TABLE borrador (
    id          INTEGER PRIMARY KEY,
    brief_id    INTEGER NOT NULL REFERENCES brief_escena (id) ON DELETE CASCADE,
    escena_id   INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    intento     INTEGER NOT NULL,
    texto       TEXT NOT NULL,
    registro_id INTEGER NOT NULL REFERENCES registro_generacion (id),
    creado_en   TEXT NOT NULL,
    UNIQUE (escena_id, intento)
);

-- `Version` es el estado del texto con su trazabilidad. `numero` es la misma
-- version con la que la 005 identifica un `Informe de critica` y con la que
-- `canon/` consolida: escena mas version es la clave con la que todo el sistema
-- nombra un texto concreto.
--
-- `borrador_id` admite NULL en un solo caso, y es el que sostiene A-46: la
-- edicion a mano del autor no sale de ninguna llamada al modelo, asi que no
-- tiene borrador ni registro detras. El `CHECK` lo cierra: si el origen es un
-- agente, el borrador es obligatorio.
CREATE TABLE version (
    id          INTEGER PRIMARY KEY,
    escena_id   INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    numero      INTEGER NOT NULL,
    borrador_id INTEGER REFERENCES borrador (id) ON DELETE CASCADE,
    texto       TEXT NOT NULL,
    origen      TEXT NOT NULL CHECK (origen IN ('redactor', 'editor', 'autor')),
    creada_en   TEXT NOT NULL,
    UNIQUE (escena_id, numero),
    CHECK (origen = 'autor' OR borrador_id IS NOT NULL)
);

-- ---------------------------------------------------------------------------
-- Banco de ejemplos
-- ---------------------------------------------------------------------------
-- RF-PROC-09: append-only y sin lectura en v1. Se recoge desde el primer dia
-- porque un banco de ejemplos no se puede reconstruir hacia atras.
--
-- Las dos columnas de traza tienen el valor fijado por `CHECK`, y no es un
-- descuido: A-46 dice que **solo** entra texto aceptado y editado por el autor.
-- Entrenar sobre texto que unicamente paso umbrales es el bucle de
-- autoentrenamiento que `architecture.md` prohibe, y un banco sin esa traza no
-- es un banco pequeno: es un banco inservible. Las columnas existen para que
-- quien lea la tabla no tenga que conocer la regla.
CREATE TABLE training_samples (
    id                 INTEGER PRIMARY KEY,
    escena_id          INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    version_id         INTEGER NOT NULL UNIQUE REFERENCES version (id) ON DELETE CASCADE,
    brief              TEXT NOT NULL,
    contexto           TEXT NOT NULL,
    texto_aceptado     TEXT NOT NULL,
    editado_a_mano     INTEGER NOT NULL CHECK (editado_a_mano = 1),
    modo_de_aceptacion TEXT NOT NULL CHECK (modo_de_aceptacion = 'humana'),
    aceptado_en        TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Deriva
-- ---------------------------------------------------------------------------
-- `Deriva` es de `process/` y no de `replanning/`: se mide una vez por escena
-- aceptada, en el mismo punto y con la misma cadencia que el registro de
-- generacion. Lo que `replanning/` poseera es lo que **reacciona** a ella, y por
-- eso v1 puede medir desde el primer dia con el bucle largo entero fuera.
--
-- Numerador y denominador van **por separado** en cada componente. No es
-- cosmetico: una proporcion sola no se puede recalcular si manana cambia la
-- definicion del denominador, y RF-PROC-12 exige que cualquier definicion futura
-- se recalcule sobre el historico de v1 sin regenerar nada.
--
-- `fiable` admite NULL, que es el estado de v1: mientras
-- `deriva.densidad_declaracion_minima` siga en null no hay con que juzgar la
-- densidad, y decir fiable sin umbral seria inventarse la respuesta.
CREATE TABLE deriva_medicion (
    id                 INTEGER PRIMARY KEY,
    escena_id          INTEGER NOT NULL UNIQUE REFERENCES escena (id) ON DELETE CASCADE,
    esquema_id         INTEGER NOT NULL REFERENCES esquema (id),
    plan_hash          TEXT NOT NULL,
    invalidacion_num   INTEGER NOT NULL,
    invalidacion_den   INTEGER NOT NULL,
    canon_huerfano_num INTEGER NOT NULL,
    canon_huerfano_den INTEGER NOT NULL,
    inviabilidad_num   INTEGER NOT NULL,
    inviabilidad_den   INTEGER NOT NULL,
    densidad_num       INTEGER NOT NULL,
    densidad_den       INTEGER NOT NULL,
    fiable             INTEGER CHECK (fiable IN (0, 1)),
    definicion_version INTEGER NOT NULL,
    medido_en          TEXT NOT NULL
);

-- Los ingredientes. Es lo que hace el historico recalculable: cada elemento que
-- entro en la cuenta, con que papel entro y por que.
--
-- `cuenta_en` distingue las tres formas de entrar. El `candidato` existe porque
-- `inviabilidad_pago` no atribuye --sin el `alcance` de la restriccion no se sabe
-- cual recoge que promesa--, asi que su numerador se deduce comparando promesas
-- pendientes con candidatas de pago. Sin guardar las candidatas, ese numerador
-- no se podria recalcular.
--
-- `elemento_id` no lleva clave foranea a proposito: apunta a cuatro tablas
-- distintas segun `tipo_elemento`. Una columna por tabla seria mas estricta y
-- convertiria cada definicion nueva de la medida en una migracion.
CREATE TABLE deriva_ingrediente (
    id            INTEGER PRIMARY KEY,
    medicion_id   INTEGER NOT NULL REFERENCES deriva_medicion (id) ON DELETE CASCADE,
    componente    TEXT NOT NULL CHECK (
                      componente IN ('invalidacion', 'canon_huerfano', 'inviabilidad_pago')
                  ),
    tipo_elemento TEXT NOT NULL CHECK (
                      tipo_elemento IN (
                          'restriccion_destino',
                          'hilo_de_trama',
                          'promesa_narrativa',
                          'hallazgo'
                      )
                  ),
    elemento_id   INTEGER NOT NULL,
    cuenta_en     TEXT NOT NULL CHECK (cuenta_en IN ('numerador', 'denominador', 'candidato')),
    motivo        TEXT NOT NULL,
    hecho_id      INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL,
    UNIQUE (medicion_id, componente, tipo_elemento, elemento_id, cuenta_en)
);

CREATE INDEX idx_ingrediente_medicion ON deriva_ingrediente (medicion_id, componente);
