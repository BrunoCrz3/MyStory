-- Audit log: una fila por decisión del policy engine, con la regla aplicada, la entrada y el
-- resultado (RF-POL-01). **Solo de escritura** (RF-POL-02): los triggers abortan cualquier
-- modificación o borrado, así que no depende de que el código se acuerde.

CREATE TABLE audit_log (
    id         TEXT NOT NULL PRIMARY KEY,
    novel_id   TEXT NOT NULL REFERENCES obra (novel_id),
    momento    TEXT NOT NULL,
    sujeto     TEXT NOT NULL CHECK (sujeto IN ('capitulo', 'hecho', 'generacion', 'brief')),
    sujeto_id  TEXT NOT NULL,
    regla      TEXT NOT NULL,
    entrada    TEXT NOT NULL CHECK (json_valid(entrada)),
    resultado  TEXT NOT NULL
);

CREATE INDEX audit_log_por_sujeto ON audit_log (novel_id, sujeto, sujeto_id);

CREATE TRIGGER audit_log_sin_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log es solo de escritura');
END;

CREATE TRIGGER audit_log_sin_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log es solo de escritura');
END;
