-- Estructura de la obra: capítulos, entidades narrativas, fábula y el esquema del planificador.
--
-- **Una fila de `capitulo` por texto escrito** (D-05): `version` es la versión de la novela
-- para la que se escribió. Una regeneración crea filas nuevas solo para los capítulos
-- afectados, y `version_capitulo` (0009) dice qué fila lee cada versión publicada. Los no
-- afectados son la misma fila en las dos versiones: idénticos por construcción.

CREATE TABLE personaje (
    id               TEXT    NOT NULL PRIMARY KEY,
    novel_id         TEXT    NOT NULL REFERENCES obra (novel_id),
    nombre           TEXT    NOT NULL,
    deseo            TEXT,
    herida           TEXT,
    rol_narrativo    TEXT,
    voz              TEXT,
    fecha_nacimiento TEXT,
    es_destinatario  INTEGER NOT NULL DEFAULT 0 CHECK (es_destinatario IN (0, 1)),
    UNIQUE (novel_id, nombre)
);

CREATE TABLE lugar (
    id         TEXT NOT NULL PRIMARY KEY,
    novel_id   TEXT NOT NULL REFERENCES obra (novel_id),
    nombre     TEXT NOT NULL,
    geografia  TEXT,
    atmosfera  TEXT,
    UNIQUE (novel_id, nombre)
);

CREATE TABLE capitulo (
    id                TEXT    NOT NULL PRIMARY KEY,
    novel_id          TEXT    NOT NULL REFERENCES obra (novel_id),
    numero            INTEGER NOT NULL CHECK (numero >= 1),
    version           INTEGER NOT NULL CHECK (version >= 1),
    estado            TEXT    NOT NULL DEFAULT 'Pendiente' CHECK (estado IN (
                          'Pendiente', 'Escribiendo', 'Validando', 'Aceptado',
                          'Reescribiendo', 'Agotado', 'Obsoleto')),
    titulo            TEXT,
    texto             TEXT,
    palabras          INTEGER,
    gancho_cierre     TEXT,
    pov_personaje_id  TEXT REFERENCES personaje (id),
    lugar_id          TEXT REFERENCES lugar (id),
    funcion_dramatica TEXT,
    intentos          INTEGER NOT NULL DEFAULT 0 CHECK (intentos >= 0),
    hash_prompt       TEXT,
    tokens_entrada    INTEGER NOT NULL DEFAULT 0,
    tokens_salida     INTEGER NOT NULL DEFAULT 0,
    coste_usd         REAL    NOT NULL DEFAULT 0,
    aceptado_en       TEXT,
    -- La aceptación de un capítulo ocurre a lo sumo una vez por versión (architecture.md
    -- § Checkpoint y reanudación): una fila por número y versión.
    UNIQUE (novel_id, numero, version),
    CHECK (estado <> 'Aceptado' OR (texto IS NOT NULL AND aceptado_en IS NOT NULL))
);

CREATE INDEX capitulo_por_version ON capitulo (novel_id, version, numero);

CREATE TABLE arco (
    id             TEXT NOT NULL PRIMARY KEY,
    novel_id       TEXT NOT NULL REFERENCES obra (novel_id),
    personaje_id   TEXT NOT NULL REFERENCES personaje (id),
    estado_inicial TEXT,
    estado_final   TEXT,
    UNIQUE (novel_id, personaje_id)
);

CREATE TABLE hilo_trama (
    id                 TEXT NOT NULL PRIMARY KEY,
    novel_id           TEXT NOT NULL REFERENCES obra (novel_id),
    nombre             TEXT NOT NULL,
    tipo               TEXT,
    pregunta_dramatica TEXT,
    estado             TEXT NOT NULL DEFAULT 'abierto',
    UNIQUE (novel_id, nombre)
);

CREATE TABLE evento (
    id          TEXT    NOT NULL PRIMARY KEY,
    novel_id    TEXT    NOT NULL REFERENCES obra (novel_id),
    descripcion TEXT    NOT NULL,
    momento     INTEGER NOT NULL,
    lugar_id    TEXT REFERENCES lugar (id),
    duracion    TEXT
);

CREATE INDEX evento_por_momento ON evento (novel_id, momento);

CREATE TABLE evento_personaje (
    novel_id     TEXT NOT NULL REFERENCES obra (novel_id),
    evento_id    TEXT NOT NULL REFERENCES evento (id),
    personaje_id TEXT NOT NULL REFERENCES personaje (id),
    PRIMARY KEY (evento_id, personaje_id)
);

CREATE INDEX evento_personaje_por_personaje ON evento_personaje (novel_id, personaje_id);

CREATE TABLE evento_capitulo (
    novel_id    TEXT NOT NULL REFERENCES obra (novel_id),
    evento_id   TEXT NOT NULL REFERENCES evento (id),
    capitulo_id TEXT NOT NULL REFERENCES capitulo (id),
    PRIMARY KEY (evento_id, capitulo_id)
);

CREATE TABLE evento_excluyente (
    novel_id     TEXT NOT NULL REFERENCES obra (novel_id),
    evento_id    TEXT NOT NULL REFERENCES evento (id),
    personaje_id TEXT NOT NULL REFERENCES personaje (id),
    tipo         TEXT NOT NULL CHECK (tipo IN ('muerte', 'partida')),
    PRIMARY KEY (evento_id, personaje_id)
);

-- El esquema del planificador no es una tabla: es la obra más una restricción de destino y
-- un brief por capítulo.
CREATE TABLE restriccion_destino (
    id        TEXT    NOT NULL PRIMARY KEY,
    novel_id  TEXT    NOT NULL REFERENCES obra (novel_id),
    numero    INTEGER NOT NULL CHECK (numero >= 1),
    tipo      TEXT    NOT NULL CHECK (tipo IN ('estado_final', 'revelacion', 'posicion_personaje')),
    enunciado TEXT    NOT NULL,
    alcance   TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(alcance)),
    UNIQUE (novel_id, numero)
);

CREATE TABLE brief_capitulo (
    id                  TEXT    NOT NULL PRIMARY KEY,
    novel_id            TEXT    NOT NULL REFERENCES obra (novel_id),
    numero              INTEGER NOT NULL CHECK (numero >= 1),
    restriccion_id      TEXT    NOT NULL UNIQUE REFERENCES restriccion_destino (id),
    titulo_provisional  TEXT    NOT NULL,
    funcion_dramatica   TEXT    NOT NULL,
    pov                 TEXT    NOT NULL,
    lugar               TEXT    NOT NULL,
    estado_entrada      TEXT    NOT NULL,
    elementos           TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(elementos)),
    UNIQUE (novel_id, numero)
);

CREATE TABLE elemento_capitulo (
    novel_id    TEXT NOT NULL REFERENCES obra (novel_id),
    elemento_id TEXT NOT NULL REFERENCES elemento_personalizado (id),
    capitulo_id TEXT NOT NULL REFERENCES capitulo (id),
    PRIMARY KEY (elemento_id, capitulo_id)
);
