-- Obra: la raíz de todo. Toda tabla de dominio referencia a `obra(novel_id)` (RD-01).
-- Los estados son los de `domain-knowledge.md` § Estados, uno a uno.

CREATE TABLE obra (
    novel_id        TEXT    NOT NULL PRIMARY KEY,
    titulo          TEXT,
    premisa         TEXT,
    genero          TEXT    NOT NULL,
    tono            TEXT    NOT NULL,
    estado          TEXT    NOT NULL DEFAULT 'Configurando' CHECK (estado IN (
                        'Configurando', 'Planificando', 'Escribiendo', 'Validando',
                        'Publicando', 'Publicada', 'Regenerando', 'Detenida')),
    total_capitulos INTEGER NOT NULL CHECK (total_capitulos > 0),
    creada_en       TEXT    NOT NULL
);

CREATE INDEX obra_por_fecha ON obra (creada_en DESC);
