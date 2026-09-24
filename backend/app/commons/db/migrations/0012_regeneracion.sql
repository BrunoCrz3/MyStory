-- Regeneración dirigida: solicitud de cambio, análisis de impacto y retcon (definitions.md
-- Capa 2 y Capa 5; RF-VER-06…RF-VER-09). `solicitud_cambio` y `analisis_impacto` son de
-- `versioning/`; `retcon`, de `canon/` (architecture.md § Anatomía).
--
-- `contradiccion_canon` no tiene tabla todavía (A-96): ningún paso del plan 1 la escribe.

CREATE TABLE solicitud_cambio (
    id                 TEXT    NOT NULL PRIMARY KEY,
    novel_id           TEXT    NOT NULL REFERENCES obra (novel_id),
    version_base       INTEGER NOT NULL CHECK (version_base >= 1),
    hecho_id           TEXT    REFERENCES hecho (id),
    fragmento          TEXT,
    hecho_candidato_id TEXT    REFERENCES hecho (id),
    enunciado_nuevo    TEXT    NOT NULL,
    capitulo_origen    INTEGER NOT NULL CHECK (capitulo_origen >= 1),
    estado             TEXT    NOT NULL DEFAULT 'pendiente-de-confirmacion' CHECK (estado IN (
                           'pendiente-de-confirmacion', 'confirmada', 'aplicada', 'descartada')),
    version_resultante INTEGER CHECK (version_resultante IS NULL OR version_resultante >= 1),
    creada_en          TEXT    NOT NULL,
    -- Exactamente uno de los dos orígenes (NuevaSolicitudCambio, oneOf).
    CHECK ((hecho_id IS NULL) <> (fragmento IS NULL))
);

CREATE TABLE analisis_impacto (
    id                  TEXT NOT NULL PRIMARY KEY,
    novel_id            TEXT NOT NULL REFERENCES obra (novel_id),
    solicitud_id        TEXT NOT NULL UNIQUE REFERENCES solicitud_cambio (id),
    capitulos_afectados TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(capitulos_afectados)),
    hechos_derivados    TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(hechos_derivados)),
    creado_en           TEXT NOT NULL
);

CREATE TABLE retcon (
    id              TEXT    NOT NULL PRIMARY KEY,
    novel_id        TEXT    NOT NULL REFERENCES obra (novel_id),
    solicitud_id    TEXT    NOT NULL UNIQUE REFERENCES solicitud_cambio (id),
    hecho_viejo_id  TEXT    NOT NULL REFERENCES hecho (id),
    hecho_nuevo_id  TEXT    NOT NULL REFERENCES hecho (id),
    version         INTEGER NOT NULL CHECK (version >= 1),
    creado_en       TEXT    NOT NULL
);

CREATE INDEX solicitud_por_novela ON solicitud_cambio (novel_id, creada_en);
