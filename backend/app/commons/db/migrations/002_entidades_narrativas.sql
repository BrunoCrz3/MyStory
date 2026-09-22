-- Migracion 002 - H2. Entidades narrativas de la Capa 1 y sus relaciones.
--
-- Las cardinalidades salen de «Relaciones del dominio» de docs/definitions.md y
-- se traducen mecanicamente: 1:N clave en el lado N, 1:1 clave mas UNIQUE, N:M
-- tabla puente con clave primaria compuesta.
--
-- Cuatro de «las siete relaciones nuevas» que el plan situa en la 003 estan
-- aqui: `Novum impone Regla`, `Novum nombra Termino`, `Regla configura Faccion`
-- y `Faccion disputa Artefacto` tienen los dos extremos en la Capa 1, y sin la
-- primera no se puede cumplir A-51, que es de este hito. Las que tocan canon
-- —promesa, snapshot, estado epistemico, retcon— siguen en la 003.
--
-- `nombre` no aparece en la columna «Atributos clave» de la ontologia, que lista
-- los atributos que definen cada clase, no todos. Sin el, RF-NOVEL-02 no se
-- puede cumplir: una entidad que no se puede nombrar no se puede consultar.

-- Orden: primero las tablas a las que apuntan las columnas que se anaden
-- despues. SQLite acepta ALTER TABLE ... ADD COLUMN con REFERENCES solo si el
-- valor por defecto es NULL.

CREATE TABLE arco (
    id             INTEGER PRIMARY KEY,
    nombre         TEXT NOT NULL,
    estado_inicial TEXT,
    puntos_de_giro TEXT,
    estado_final   TEXT
);

-- `Personaje recorre Arco` es 1:1: clave foranea mas UNIQUE.
CREATE TABLE personaje (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT NOT NULL,
    deseo         TEXT,
    necesidad     TEXT,
    herida        TEXT,
    rol_narrativo TEXT,
    arco_id       INTEGER UNIQUE REFERENCES arco (id) ON DELETE SET NULL
);

-- `Voz` es la firma linguistica de un personaje: una y solo una por personaje.
CREATE TABLE voz (
    id                INTEGER PRIMARY KEY,
    personaje_id      INTEGER NOT NULL UNIQUE REFERENCES personaje (id) ON DELETE CASCADE,
    lexico            TEXT,
    registro          TEXT,
    sintaxis          TEXT,
    muletillas        TEXT,
    temas_recurrentes TEXT
);

CREATE TABLE lugar (
    id                  INTEGER PRIMARY KEY,
    nombre              TEXT NOT NULL,
    geografia           TEXT,
    atmosfera_sensorial TEXT,
    reglas_propias      TEXT
);

CREATE TABLE hilo_de_trama (
    id                 INTEGER PRIMARY KEY,
    nombre             TEXT NOT NULL,
    tipo               TEXT NOT NULL CHECK (tipo IN ('principal', 'secundario')),
    pregunta_dramatica TEXT,
    estado             TEXT
);

CREATE TABLE faccion (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL,
    objetivo TEXT,
    recursos TEXT
);

CREATE TABLE artefacto (
    id                 INTEGER PRIMARY KEY,
    nombre             TEXT NOT NULL,
    propiedades        TEXT,
    poseedor_actual_id INTEGER REFERENCES personaje (id) ON DELETE SET NULL,
    deuda_narrativa    TEXT
);

-- `limites` es NOT NULL por A-51: un novum sin limites declarados deja a
-- RF-QUA-01 sin nada contra lo que medir la plausibilidad especulativa. Que no
-- este vacio lo comprueba el servicio, que es donde se leen las reglas.
CREATE TABLE novum (
    id                       INTEGER PRIMARY KEY,
    nombre                   TEXT NOT NULL,
    mecanismo                TEXT NOT NULL,
    limites                  TEXT NOT NULL,
    consecuencias_en_cascada TEXT
);

-- `Novum impone Regla del mundo`, 1:N.
CREATE TABLE regla_del_mundo (
    id                     INTEGER PRIMARY KEY,
    novum_id               INTEGER NOT NULL REFERENCES novum (id) ON DELETE CASCADE,
    enunciado              TEXT NOT NULL,
    alcance                TEXT,
    excepciones_declaradas TEXT
);

-- `Novum nombra Termino canonico`, 1:N. La forma es unica: dos terminos con la
-- misma grafia son el mismo termino escrito dos veces.
CREATE TABLE termino_canonico (
    id                   INTEGER PRIMARY KEY,
    forma                TEXT NOT NULL UNIQUE,
    definicion           TEXT,
    novum_id             INTEGER REFERENCES novum (id) ON DELETE SET NULL,
    primera_aparicion_id INTEGER REFERENCES escena (id) ON DELETE SET NULL,
    variantes_prohibidas TEXT
);

CREATE TABLE tema (
    id        INTEGER PRIMARY KEY,
    nombre    TEXT NOT NULL,
    enunciado TEXT
);

CREATE TABLE motivo (
    id        INTEGER PRIMARY KEY,
    nombre    TEXT NOT NULL,
    forma     TEXT,
    evolucion TEXT
);

-- Configuracion del narrador: una por obra.
CREATE TABLE voz_narrativa (
    id                    INTEGER PRIMARY KEY,
    obra_id               INTEGER NOT NULL UNIQUE REFERENCES obra (id) ON DELETE CASCADE,
    persona               TEXT,
    tiempo_verbal         TEXT,
    distancia             TEXT,
    focalizacion          TEXT,
    ratio_escena_resumen  TEXT
);

-- Fabula. Separada del discurso a proposito: sin esta separacion no se pueden
-- gestionar analepsis ni revelaciones diferidas.
CREATE TABLE evento (
    id                   INTEGER PRIMARY KEY,
    que_ocurre           TEXT NOT NULL,
    momento_en_la_fabula TEXT,
    duracion             TEXT
);

-- `Personaje desea / necesita Objetivo`, 1:N. Los dos enumerados salen del
-- propio texto de la definicion.
CREATE TABLE objetivo (
    id           INTEGER PRIMARY KEY,
    personaje_id INTEGER NOT NULL REFERENCES personaje (id) ON DELETE CASCADE,
    enunciado    TEXT NOT NULL,
    alcance      TEXT CHECK (alcance IN ('de_escena', 'de_arco')),
    tipo         TEXT CHECK (tipo IN ('deseo', 'necesidad')),
    estado       TEXT
);

-- Beat: minimo cambio de valor emocional dentro de una escena.
CREATE TABLE beat (
    id            INTEGER PRIMARY KEY,
    escena_id     INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    orden         INTEGER NOT NULL,
    valor_inicial TEXT,
    valor_final   TEXT,
    UNIQUE (escena_id, orden)
);

-- Puentes N:M. Clave primaria compuesta en todos.

-- `Evento se narra en Escena`. Es N:M de verdad: una escena narra varios
-- eventos y un evento se narra en varias escenas o en ninguna. Colapsarlo a 1:N
-- haria imposibles la analepsis y la revelacion diferida.
CREATE TABLE evento_escena (
    evento_id INTEGER NOT NULL REFERENCES evento (id) ON DELETE CASCADE,
    escena_id INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    PRIMARY KEY (evento_id, escena_id)
);

-- «participantes» de un evento.
CREATE TABLE evento_personaje (
    evento_id    INTEGER NOT NULL REFERENCES evento (id) ON DELETE CASCADE,
    personaje_id INTEGER NOT NULL REFERENCES personaje (id) ON DELETE CASCADE,
    PRIMARY KEY (evento_id, personaje_id)
);

-- `Escena avanza Hilo de trama`.
CREATE TABLE escena_hilo (
    escena_id INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    hilo_id   INTEGER NOT NULL REFERENCES hilo_de_trama (id) ON DELETE CASCADE,
    PRIMARY KEY (escena_id, hilo_id)
);

-- «escenas que lo avanzan», atributo de Arco. Responde la pregunta de
-- competencia 8.
CREATE TABLE arco_escena (
    arco_id   INTEGER NOT NULL REFERENCES arco (id) ON DELETE CASCADE,
    escena_id INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    PRIMARY KEY (arco_id, escena_id)
);

-- `Personaje posee Artefacto`.
CREATE TABLE personaje_artefacto (
    personaje_id INTEGER NOT NULL REFERENCES personaje (id) ON DELETE CASCADE,
    artefacto_id INTEGER NOT NULL REFERENCES artefacto (id) ON DELETE CASCADE,
    PRIMARY KEY (personaje_id, artefacto_id)
);

-- `Personaje pertenece a Faccion`.
CREATE TABLE personaje_faccion (
    personaje_id INTEGER NOT NULL REFERENCES personaje (id) ON DELETE CASCADE,
    faccion_id   INTEGER NOT NULL REFERENCES faccion (id) ON DELETE CASCADE,
    PRIMARY KEY (personaje_id, faccion_id)
);

-- `Regla del mundo configura Faccion`.
CREATE TABLE regla_faccion (
    regla_id   INTEGER NOT NULL REFERENCES regla_del_mundo (id) ON DELETE CASCADE,
    faccion_id INTEGER NOT NULL REFERENCES faccion (id) ON DELETE CASCADE,
    PRIMARY KEY (regla_id, faccion_id)
);

-- `Faccion disputa Artefacto`.
CREATE TABLE faccion_artefacto (
    faccion_id   INTEGER NOT NULL REFERENCES faccion (id) ON DELETE CASCADE,
    artefacto_id INTEGER NOT NULL REFERENCES artefacto (id) ON DELETE CASCADE,
    PRIMARY KEY (faccion_id, artefacto_id)
);

-- «relaciones con otras facciones».
CREATE TABLE faccion_relacion (
    faccion_id       INTEGER NOT NULL REFERENCES faccion (id) ON DELETE CASCADE,
    otra_faccion_id  INTEGER NOT NULL REFERENCES faccion (id) ON DELETE CASCADE,
    descripcion      TEXT,
    PRIMARY KEY (faccion_id, otra_faccion_id),
    CHECK (faccion_id <> otra_faccion_id)
);

-- `Motivo encarna Tema`.
CREATE TABLE motivo_tema (
    motivo_id INTEGER NOT NULL REFERENCES motivo (id) ON DELETE CASCADE,
    tema_id   INTEGER NOT NULL REFERENCES tema (id) ON DELETE CASCADE,
    PRIMARY KEY (motivo_id, tema_id)
);

-- «apariciones» de un motivo.
CREATE TABLE motivo_escena (
    motivo_id INTEGER NOT NULL REFERENCES motivo (id) ON DELETE CASCADE,
    escena_id INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    PRIMARY KEY (motivo_id, escena_id)
);

-- Columnas que la 001 dejo pendientes porque su destino todavia no existia.
ALTER TABLE obra ADD COLUMN titulo TEXT;
ALTER TABLE capitulo ADD COLUMN pov_dominante_id INTEGER REFERENCES personaje (id);
ALTER TABLE escena ADD COLUMN personaje_pov_id INTEGER REFERENCES personaje (id);
ALTER TABLE escena ADD COLUMN lugar_id INTEGER REFERENCES lugar (id);

CREATE INDEX idx_escena_pov ON escena (personaje_pov_id);
CREATE INDEX idx_escena_lugar ON escena (lugar_id);
CREATE INDEX idx_regla_novum ON regla_del_mundo (novum_id);
CREATE INDEX idx_objetivo_personaje ON objetivo (personaje_id);
