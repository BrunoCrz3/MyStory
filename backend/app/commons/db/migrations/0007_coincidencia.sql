-- Coincidencia: detección de una palabra prohibida en un capítulo, con su posición y el
-- intento en que apareció (definitions.md § Guardrail; pregunta 25).

CREATE TABLE coincidencia (
    id          TEXT    NOT NULL PRIMARY KEY,
    novel_id    TEXT    NOT NULL REFERENCES obra (novel_id),
    capitulo_id TEXT    NOT NULL REFERENCES capitulo (id),
    palabra     TEXT    NOT NULL,
    nivel       TEXT    NOT NULL CHECK (nivel IN ('global', 'perfil', 'novela')),
    inicio      INTEGER NOT NULL,
    fin         INTEGER NOT NULL,
    intento     INTEGER NOT NULL CHECK (intento >= 0),
    decision    TEXT    NOT NULL DEFAULT 'devolver'
);

CREATE INDEX coincidencia_por_capitulo ON coincidencia (novel_id, capitulo_id);
