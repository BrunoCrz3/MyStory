-- Versiones publicadas de una novela y su vínculo con los capítulos (RF-VER-01…03, D-05).
--
-- Una versión publicada es **inmutable** (RNF-07, `CLAUDE.md` regla 15): los triggers abortan
-- cualquier modificación o borrado de la versión y de sus vínculos, y también de lo que su
-- hash cubre en los capítulos que lee —título y texto—. El estado del capítulo sí puede
-- cambiar después (un retcon lo marca `Obsoleto`): no es contenido publicado.

CREATE TABLE version_novela (
    id                  TEXT    NOT NULL PRIMARY KEY,
    novel_id            TEXT    NOT NULL REFERENCES obra (novel_id),
    version             INTEGER NOT NULL CHECK (version >= 1),
    version_anterior_id TEXT    REFERENCES version_novela (id),
    titulo              TEXT,
    hash                TEXT    NOT NULL,
    motivo              TEXT,
    generacion_id       TEXT    REFERENCES trabajo (id),
    publicada_en        TEXT    NOT NULL,
    UNIQUE (novel_id, version)
);

-- Qué fila de `capitulo` lee cada versión. Los capítulos que una regeneración no toca son la
-- misma fila en las dos versiones: idénticos por construcción (D-05).
CREATE TABLE version_capitulo (
    novel_id    TEXT    NOT NULL REFERENCES obra (novel_id),
    version     INTEGER NOT NULL,
    numero      INTEGER NOT NULL CHECK (numero >= 1),
    capitulo_id TEXT    NOT NULL REFERENCES capitulo (id),
    modificado  INTEGER NOT NULL CHECK (modificado IN (0, 1)),
    PRIMARY KEY (novel_id, version, numero),
    FOREIGN KEY (novel_id, version) REFERENCES version_novela (novel_id, version)
);

CREATE INDEX version_capitulo_por_capitulo ON version_capitulo (capitulo_id);

CREATE TRIGGER version_novela_sin_update
BEFORE UPDATE ON version_novela
BEGIN
    SELECT RAISE(ABORT, 'una versión publicada es inmutable');
END;

CREATE TRIGGER version_novela_sin_delete
BEFORE DELETE ON version_novela
BEGIN
    SELECT RAISE(ABORT, 'una versión publicada es inmutable');
END;

CREATE TRIGGER version_capitulo_sin_update
BEFORE UPDATE ON version_capitulo
BEGIN
    SELECT RAISE(ABORT, 'el vínculo de una versión publicada es inmutable');
END;

CREATE TRIGGER version_capitulo_sin_delete
BEFORE DELETE ON version_capitulo
BEGIN
    SELECT RAISE(ABORT, 'el vínculo de una versión publicada es inmutable');
END;

CREATE TRIGGER capitulo_publicado_sin_cambio_de_contenido
BEFORE UPDATE OF titulo, texto, palabras ON capitulo
WHEN EXISTS (SELECT 1 FROM version_capitulo WHERE capitulo_id = OLD.id)
BEGIN
    SELECT RAISE(ABORT, 'el contenido de un capítulo publicado es inmutable');
END;
