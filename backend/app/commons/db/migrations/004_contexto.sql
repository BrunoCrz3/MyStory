-- Migracion 004 - H4. Capa 3: indice de fragmentos, vec0 y registro de uso.
--
-- Las tablas virtuales `vec0` conviven con las relacionales en el mismo fichero.
-- Esa es la razon de ser de todo el stack: la recuperacion filtra por las
-- entidades del brief (SQL) y solo despues ordena por similitud (`vec0`), en la
-- misma transaccion y sin salir del proceso.
--
-- `embedding_model` y `embedding_version` en cada fila no son metadato
-- decorativo. Vectores de modelos distintos no son comparables: mezclarlos no
-- da error, da una recuperacion que devuelve lo que no toca y nadie sabe por
-- que. De ahi que un cambio de modelo o de version obligue a reindexar y se
-- detecte al arrancar (A-42, RF-CTX-10).
--
-- La dimension de `vec_fragmento` esta duplicada aqui y en
-- `config/thresholds.yaml` porque el DDL no puede leer el fichero. Que no se
-- separen lo comprueba una prueba, que es la unica forma de que la duplicacion
-- no se pudra.

CREATE TABLE fragmento (
    id                INTEGER PRIMARY KEY,
    escena_id         INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    texto             TEXT NOT NULL,
    nivel             TEXT NOT NULL CHECK (
                          nivel IN (
                              'resumen_de_acto',
                              'resumen_de_capitulo',
                              'resumen_de_escena',
                              'escena_literal'
                          )
                      ),
    embedding_model   TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    indexado_en       TEXT NOT NULL
);

CREATE INDEX idx_fragmento_escena ON fragmento (escena_id, nivel);
CREATE INDEX idx_fragmento_modelo ON fragmento (embedding_model, embedding_version);

-- Indice de entidades: el filtro relacional que va **antes** de la similitud.
CREATE TABLE fragmento_entidad (
    fragmento_id INTEGER NOT NULL REFERENCES fragmento (id) ON DELETE CASCADE,
    tipo         TEXT NOT NULL CHECK (
                     tipo IN ('personaje', 'lugar', 'artefacto', 'faccion', 'hilo', 'motivo')
                 ),
    entidad_id   INTEGER NOT NULL,
    PRIMARY KEY (fragmento_id, tipo, entidad_id)
);

CREATE INDEX idx_entidad_fragmento ON fragmento_entidad (tipo, entidad_id);

-- Registro de uso: la fuente del anticontexto en el diagrama de ensamblado.
-- Metaforas ya gastadas, cliches vetados y lo que todavia no se puede revelar.
CREATE TABLE uso_de_recurso (
    id            INTEGER PRIMARY KEY,
    escena_id     INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    tipo          TEXT NOT NULL CHECK (
                      tipo IN ('metafora', 'cliche_vetado', 'revelacion_prohibida')
                  ),
    texto         TEXT NOT NULL,
    registrado_en TEXT NOT NULL
);

CREATE INDEX idx_uso_escena ON uso_de_recurso (escena_id, tipo);

CREATE VIRTUAL TABLE vec_fragmento USING vec0(
    fragmento_id integer primary key,
    embedding float[1024] distance_metric=cosine
);
