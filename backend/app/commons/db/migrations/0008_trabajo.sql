-- Trabajos: la cola de generaciones en SQLite que ejecuta el worker único (TO-030, RD-06), y
-- el recurso `Generacion` de la API (D-04): `generacion_id` es la clave del trabajo.
--
-- `estado_cola` es de la cola (pendiente, en curso, terminado); `estado` es el de la novela
-- durante esta generación, con los valores de `EstadoNovela`.

CREATE TABLE trabajo (
    id                    TEXT    NOT NULL PRIMARY KEY,
    novel_id              TEXT    NOT NULL REFERENCES obra (novel_id),
    tipo                  TEXT    NOT NULL CHECK (tipo IN ('inicial', 'dirigida')),
    estado_cola           TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado_cola IN (
                              'pendiente', 'en-curso', 'terminado')),
    estado                TEXT    NOT NULL CHECK (estado IN (
                              'Configurando', 'Planificando', 'Escribiendo', 'Validando',
                              'Publicando', 'Publicada', 'Regenerando', 'Detenida')),
    version_objetivo      INTEGER NOT NULL CHECK (version_objetivo >= 1),
    estimacion            INTEGER NOT NULL CHECK (estimacion > 0),
    capitulo_actual       INTEGER,
    capitulos_a_regenerar TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(capitulos_a_regenerar)),
    intentos_infra        INTEGER NOT NULL DEFAULT 0,
    tokens_consumidos     INTEGER NOT NULL DEFAULT 0,
    coste_usd             REAL    NOT NULL DEFAULT 0,
    traza_langfuse_id     TEXT,
    detenida_por          TEXT,
    version_resultante    INTEGER,
    solicitud_id          TEXT,
    iniciada_en           TEXT    NOT NULL,
    terminada_en          TEXT
);

-- Una sola generación viva por novela, también por esquema (RF-PROC-02).
CREATE UNIQUE INDEX trabajo_vivo_por_novela ON trabajo (novel_id)
    WHERE estado_cola IN ('pendiente', 'en-curso');
CREATE INDEX trabajo_por_cola ON trabajo (estado_cola, iniciada_en);
CREATE INDEX trabajo_por_novela ON trabajo (novel_id, iniciada_en DESC);

-- Checkpoint: último capítulo completado de una generación, desde el que se reanuda.
CREATE TABLE checkpoint (
    generacion_id    TEXT    NOT NULL PRIMARY KEY REFERENCES trabajo (id),
    novel_id         TEXT    NOT NULL REFERENCES obra (novel_id),
    ultimo_capitulo  INTEGER NOT NULL CHECK (ultimo_capitulo >= 0),
    actualizado_en   TEXT    NOT NULL
);
