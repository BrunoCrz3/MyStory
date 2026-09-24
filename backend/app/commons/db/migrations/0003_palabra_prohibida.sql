-- Palabras prohibidas de nivel `novela`, las que declara el comprador. Los niveles `global`
-- y `perfil` son listas del repositorio en `guardrail/listas/`, porque no pertenecen a
-- ninguna novela (D-21). La columna `nivel` conserva los tres valores de la ontología.

CREATE TABLE palabra_prohibida (
    id       TEXT    NOT NULL PRIMARY KEY,
    novel_id TEXT    NOT NULL REFERENCES obra (novel_id),
    orden    INTEGER NOT NULL,
    forma    TEXT    NOT NULL,
    nivel    TEXT    NOT NULL DEFAULT 'novela' CHECK (nivel IN ('global', 'perfil', 'novela')),
    origen   TEXT    NOT NULL,
    UNIQUE (novel_id, orden)
);
