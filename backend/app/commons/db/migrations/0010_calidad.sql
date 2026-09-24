-- Calidad: informe de crítica por intento, sus defectos y un score por validador ejecutado
-- (definitions.md Capa 4; architecture.md § Story bible; RF-OBS-03, RF-PROC-08).
--
-- No hay tabla `validador`: el registro es un catálogo sin novela y vive en
-- `quality/registro.py`, comprobado contra docs/verification.md (A-62). Estas tablas no son
-- story bible: un borrador rechazado sigue sin dejar rastro en el canon, pero su crítica sí
-- queda, que es lo que hace consultable por qué se agotó un capítulo.

CREATE TABLE informe_critica (
    id          TEXT    NOT NULL PRIMARY KEY,
    novel_id    TEXT    NOT NULL REFERENCES obra (novel_id),
    capitulo_id TEXT    NOT NULL REFERENCES capitulo (id),
    intento     INTEGER NOT NULL CHECK (intento >= 0),
    decision    TEXT    NOT NULL CHECK (decision IN ('aceptar', 'devolver', 'agotar', 'detener')),
    -- Informe de crítica evalúa Borrador, 1:1: un informe por borrador. No es único por
    -- intento: si el proceso cae entre aceptar y extraer, la reanudación reescribe el
    -- capítulo con el mismo número de intento (A-44), y los dos informes se conservan.
    creado_en   TEXT    NOT NULL
);

CREATE TABLE defecto (
    id            TEXT    NOT NULL PRIMARY KEY,
    novel_id      TEXT    NOT NULL REFERENCES obra (novel_id),
    informe_id    TEXT    NOT NULL REFERENCES informe_critica (id),
    orden         INTEGER NOT NULL CHECK (orden >= 0),
    validador     TEXT    NOT NULL,
    dimension     TEXT    NOT NULL,
    gravedad      TEXT    NOT NULL CHECK (gravedad IN ('baja', 'media', 'alta')),
    descripcion   TEXT    NOT NULL,
    localizacion  TEXT,
    clasificacion TEXT    NOT NULL DEFAULT 'local' CHECK (clasificacion IN ('local', 'sistémico'))
);

CREATE TABLE score (
    id             TEXT    NOT NULL PRIMARY KEY,
    novel_id       TEXT    NOT NULL REFERENCES obra (novel_id),
    informe_id     TEXT    NOT NULL REFERENCES informe_critica (id),
    orden          INTEGER NOT NULL CHECK (orden >= 0),
    validador      TEXT    NOT NULL,
    valor          REAL    NOT NULL,
    pasa           INTEGER NOT NULL CHECK (pasa IN (0, 1)),
    cierra_el_paso INTEGER NOT NULL CHECK (cierra_el_paso IN (0, 1)),
    detalle        TEXT    NOT NULL
);

CREATE INDEX informe_por_capitulo ON informe_critica (novel_id, capitulo_id, intento);
CREATE INDEX defecto_por_informe ON defecto (novel_id, informe_id, orden);
CREATE INDEX score_por_informe ON score (novel_id, informe_id, orden);
