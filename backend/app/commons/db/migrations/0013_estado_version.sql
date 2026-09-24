-- Estado de una versión de novela (TO-045, RF-QUA-03, RNF-19).
--
-- Una versión nace `candidata`, con sus vínculos, para que `render_visual` pueda pintarla; el
-- gate decide y pasa a `publicada` o a `rechazada`, una sola vez. Las dos salidas son
-- terminales. Las versiones que ya existían pasaron el gate de su momento: quedan
-- `publicada` (A-112).

ALTER TABLE version_novela
    ADD COLUMN estado TEXT NOT NULL DEFAULT 'publicada'
    CHECK (estado IN ('candidata', 'publicada', 'rechazada'));

CREATE INDEX version_novela_publicadas ON version_novela (novel_id, estado, version);

-- El único UPDATE que se admite es el cambio de estado de una candidata, con la fecha de
-- publicación como mucho. El contenido —hash, título, vínculos— no cambia nunca.
DROP TRIGGER version_novela_sin_update;

CREATE TRIGGER version_novela_sin_update
BEFORE UPDATE ON version_novela
WHEN NOT (
    OLD.estado = 'candidata'
    AND NEW.estado IN ('publicada', 'rechazada')
    AND NEW.id = OLD.id
    AND NEW.novel_id = OLD.novel_id
    AND NEW.version = OLD.version
    AND NEW.version_anterior_id IS OLD.version_anterior_id
    AND NEW.titulo IS OLD.titulo
    AND NEW.hash = OLD.hash
    AND NEW.motivo IS OLD.motivo
    AND NEW.generacion_id IS OLD.generacion_id
)
BEGIN
    SELECT RAISE(ABORT, 'una versión solo cambia de candidata a publicada o rechazada');
END;
