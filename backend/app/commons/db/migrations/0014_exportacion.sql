-- Export a PDF de una versión publicada (RF-EXP-01, RF-EXP-02, TO-025, TO-045).
--
-- Una fila por versión. El PDF se genera **una vez**: una fila `disponible` no cambia ni se
-- borra. Una `fallida` —sin navegador, sin lectura o sin paridad— se relanza con el siguiente
-- `POST` (A-119), y una `en-curso` que sobrevive a un reinicio pasa a `fallido` al arrancar.

CREATE TABLE exportacion (
    novel_id        TEXT    NOT NULL REFERENCES obra (novel_id),
    version         INTEGER NOT NULL,
    estado          TEXT    NOT NULL CHECK (estado IN ('en-curso', 'disponible', 'fallido')),
    ruta            TEXT,
    generado_en     TEXT,
    paridad_pdf_web INTEGER CHECK (paridad_pdf_web IN (0, 1)),
    detalle         TEXT,
    solicitado_en   TEXT    NOT NULL,
    PRIMARY KEY (novel_id, version),
    FOREIGN KEY (novel_id, version) REFERENCES version_novela (novel_id, version)
);

CREATE TRIGGER exportacion_disponible_sin_update
BEFORE UPDATE ON exportacion
WHEN OLD.estado = 'disponible'
BEGIN
    SELECT RAISE(ABORT, 'el export de una versión se genera una sola vez');
END;

CREATE TRIGGER exportacion_disponible_sin_delete
BEFORE DELETE ON exportacion
WHEN OLD.estado = 'disponible'
BEGIN
    SELECT RAISE(ABORT, 'el export de una versión se genera una sola vez');
END;
