-- Encargo: el brief de novela y las clases del Bloque A, más la regla del mundo y la voz
-- narrativa, que salen del brief (`architecture.md` § Story bible, clase a tabla).
--
-- `brief_novela.contenido` guarda el `BriefNovela` validado tal como llegó: es la salida
-- estructurada de la entrevista y lo que devuelve la API. Las tablas de al lado son su
-- desglose consultable, y se escriben en la misma transacción (TO-039, A-16).

CREATE TABLE brief_novela (
    novel_id       TEXT NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    contenido      TEXT NOT NULL CHECK (json_valid(contenido)),
    schema_version TEXT NOT NULL,
    validado_en    TEXT NOT NULL
);

CREATE TABLE comprador (
    novel_id                  TEXT NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    identificador             TEXT NOT NULL,
    relacion_con_destinatario TEXT
);

CREATE TABLE destinatario (
    novel_id         TEXT    NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    nombre           TEXT    NOT NULL,
    edad             INTEGER NOT NULL CHECK (edad BETWEEN 0 AND 120),
    rasgos           TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(rasgos)),
    recuerdos        TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(recuerdos)),
    fecha_nacimiento TEXT
);

CREATE TABLE ocasion (
    novel_id      TEXT NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    tipo          TEXT NOT NULL CHECK (tipo IN (
                      'cumpleanos', 'boda', 'aniversario', 'jubilacion', 'nacimiento', 'otra')),
    fecha         TEXT,
    tono_esperado TEXT
);

CREATE TABLE dedicatoria (
    novel_id TEXT NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    texto    TEXT NOT NULL,
    firma    TEXT
);

CREATE TABLE elemento_personalizado (
    id          TEXT    NOT NULL PRIMARY KEY,
    novel_id    TEXT    NOT NULL REFERENCES obra (novel_id),
    orden       INTEGER NOT NULL,
    enunciado   TEXT    NOT NULL,
    obligatorio INTEGER NOT NULL CHECK (obligatorio IN (0, 1)),
    origen      TEXT    NOT NULL CHECK (origen IN ('formulario', 'texto-libre')),
    UNIQUE (novel_id, orden)
);

CREATE TABLE texto_libre (
    id                 TEXT    NOT NULL PRIMARY KEY,
    novel_id           TEXT    NOT NULL REFERENCES obra (novel_id),
    orden              INTEGER NOT NULL,
    contenido          TEXT    NOT NULL,
    procedencia        TEXT,
    estado_saneamiento TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado_saneamiento IN (
                           'pendiente', 'saneado', 'con-sospechosos')),
    UNIQUE (novel_id, orden)
);

CREATE TABLE regla_mundo (
    id        TEXT    NOT NULL PRIMARY KEY,
    novel_id  TEXT    NOT NULL REFERENCES obra (novel_id),
    orden     INTEGER NOT NULL,
    enunciado TEXT    NOT NULL,
    origen    TEXT    NOT NULL DEFAULT 'brief',
    UNIQUE (novel_id, orden)
);

CREATE TABLE voz_narrativa (
    novel_id      TEXT NOT NULL PRIMARY KEY REFERENCES obra (novel_id),
    persona       TEXT NOT NULL CHECK (persona IN ('primera', 'segunda', 'tercera')),
    tiempo_verbal TEXT NOT NULL CHECK (tiempo_verbal IN ('presente', 'pasado')),
    focalizacion  TEXT NOT NULL CHECK (focalizacion IN ('interna', 'externa', 'cero'))
);
