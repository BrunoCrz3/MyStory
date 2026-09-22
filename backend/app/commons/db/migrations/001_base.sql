-- Migracion 001 - H1. Control de migraciones y arbol estructural de la Capa 1.
--
-- AGENTS.md regla 5: una migracion commiteada no se edita nunca. Si algo de aqui
-- esta mal, se corrige con la 002, no tocando este fichero.
--
-- Alcance: un solo autor y una sola obra por instancia. Ninguna tabla lleva
-- `user_id` ni `tenant_id` (RNF-11). Una segunda novela es otro proceso con su
-- propio `data/novel.db`.

-- Control de migraciones. Numero, nombre, hash y fecha: el hash es lo unico que
-- distingue una base reconstruida desde cero de una que aplico otra version.
CREATE TABLE migracion_aplicada (
    numero      INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL,
    hash        TEXT NOT NULL,
    aplicada_en TEXT NOT NULL
);

-- Obra. Atributos de `docs/definitions.md`, Capa 1, clases estructurales.
-- El CHECK sobre la clave es la traduccion literal de «una sola obra por instancia».
CREATE TABLE obra (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    premisa            TEXT NOT NULL,
    genero             TEXT NOT NULL,
    extension_objetivo INTEGER,
    publico            TEXT
);

-- Parte / Acto. `Obra se compone de Parte` es 1:N: la clave va en el lado N.
CREATE TABLE parte (
    id                INTEGER PRIMARY KEY,
    obra_id           INTEGER NOT NULL REFERENCES obra (id) ON DELETE CASCADE,
    orden             INTEGER NOT NULL,
    funcion_dramatica TEXT NOT NULL,
    punto_de_giro     TEXT,
    UNIQUE (obra_id, orden)
);

-- Capitulo. `pov_dominante` apunta a Personaje, que nace en la migracion 002:
-- la columna se anade alli, no se adivina aqui.
CREATE TABLE capitulo (
    id               INTEGER PRIMARY KEY,
    parte_id         INTEGER NOT NULL REFERENCES parte (id) ON DELETE CASCADE,
    orden            INTEGER NOT NULL,
    gancho_de_cierre TEXT,
    UNIQUE (parte_id, orden)
);

-- Escena, unidad atomica de generacion y validacion.
--
-- Dos cosas distintas se llaman «estado» en la ontologia y aqui se separan:
--   `estado`              es la maquina de estados del ciclo (cinco valores, ni uno mas:
--                         la extraccion no es un estado).
--   `estado_de_entrada`   y `estado_de_salida` son el estado del mundo que la escena
--                         recibe y deja, que es un atributo narrativo.
--
-- El CHECK cierra la lista de valores; las transiciones validas no van aqui sino en
-- el `service.py` de `novel/`: SQLite no las expresa y un trigger las escondería del
-- sitio donde se leen las reglas.
--
-- Las claves a Personaje (POV) y Lugar llegan con la migracion 002.
CREATE TABLE escena (
    id                INTEGER PRIMARY KEY,
    capitulo_id       INTEGER NOT NULL REFERENCES capitulo (id) ON DELETE CASCADE,
    orden             INTEGER NOT NULL,
    estado            TEXT NOT NULL DEFAULT 'planificada' CHECK (
                          estado IN (
                              'planificada',
                              'en_borrador',
                              'en_revision',
                              'aceptada',
                              'obsoleta'
                          )
                      ),
    objetivo          TEXT,
    conflicto         TEXT,
    resultado         TEXT,
    momento           TEXT,
    estado_de_entrada TEXT,
    estado_de_salida  TEXT,
    UNIQUE (capitulo_id, orden)
);

CREATE INDEX idx_escena_estado ON escena (estado);
