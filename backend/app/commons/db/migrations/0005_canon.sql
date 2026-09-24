-- Canon: la story bible versionada por vigencia (TO-028, D-06).
--
-- Una fila es vigente en la versión v si `version_desde <= v` y (`version_hasta` es NULL o
-- `v < version_hasta`): el intervalo es semiabierto. Un hecho descartado se cierra con
-- `version_hasta = version_desde` —un intervalo vacío— y así no es vigente en ninguna versión
-- sin tener que filtrar por estatus. Toda consulta por versión se resuelve por vigencia.

CREATE TABLE hecho (
    id                   TEXT    NOT NULL PRIMARY KEY,
    novel_id             TEXT    NOT NULL REFERENCES obra (novel_id),
    enunciado            TEXT    NOT NULL,
    tipo                 TEXT    NOT NULL,
    estado               TEXT    NOT NULL DEFAULT 'propuesto' CHECK (estado IN (
                             'propuesto', 'adoptado', 'descartado', 'retconeado', 'refutado')),
    origen               TEXT    NOT NULL CHECK (origen IN ('brief', 'texto-libre', 'extraccion')),
    fragmento_soporte    TEXT,
    capitulo_establece_id TEXT REFERENCES capitulo (id),
    alcance_temporal     TEXT,
    version_desde        INTEGER NOT NULL CHECK (version_desde >= 1),
    version_hasta        INTEGER CHECK (version_hasta IS NULL OR version_hasta >= version_desde),
    creado_en            TEXT    NOT NULL,
    -- Un hecho extraído sin el fragmento que lo sostiene no se consolida (RF-CANON-04).
    CHECK (origen <> 'extraccion' OR fragmento_soporte IS NOT NULL)
);

CREATE INDEX hecho_por_vigencia ON hecho (novel_id, version_desde, version_hasta);

-- Uso de hecho: qué capítulos se apoyan en él, con vigencia propia (RF-CANON-02).
CREATE TABLE hecho_capitulo (
    novel_id      TEXT    NOT NULL REFERENCES obra (novel_id),
    hecho_id      TEXT    NOT NULL REFERENCES hecho (id),
    capitulo_id   TEXT    NOT NULL REFERENCES capitulo (id),
    version_desde INTEGER NOT NULL CHECK (version_desde >= 1),
    version_hasta INTEGER CHECK (version_hasta IS NULL OR version_hasta >= version_desde),
    PRIMARY KEY (hecho_id, capitulo_id, version_desde)
);

CREATE INDEX hecho_capitulo_por_hecho
    ON hecho_capitulo (novel_id, hecho_id, version_desde, version_hasta);
CREATE INDEX hecho_capitulo_por_capitulo ON hecho_capitulo (novel_id, capitulo_id);

-- RD-05: la vigencia de un uso está contenida en la de su hecho. Es un invariante del
-- esquema, no una convención: un capítulo no puede apoyarse en un hecho que aún no existía o
-- que ya se había cerrado.
CREATE TRIGGER rd05_uso_dentro_del_hecho_al_insertar
BEFORE INSERT ON hecho_capitulo
FOR EACH ROW
WHEN EXISTS (
    SELECT 1 FROM hecho h WHERE h.id = NEW.hecho_id AND (
        NEW.version_desde < h.version_desde
        OR (h.version_hasta IS NOT NULL
            AND (NEW.version_hasta IS NULL OR NEW.version_hasta > h.version_hasta))))
BEGIN
    SELECT RAISE(ABORT, 'RD-05: la vigencia del uso no cabe en la del hecho');
END;

CREATE TRIGGER rd05_uso_dentro_del_hecho_al_actualizar
BEFORE UPDATE OF version_desde, version_hasta ON hecho_capitulo
FOR EACH ROW
WHEN EXISTS (
    SELECT 1 FROM hecho h WHERE h.id = NEW.hecho_id AND (
        NEW.version_desde < h.version_desde
        OR (h.version_hasta IS NOT NULL
            AND (NEW.version_hasta IS NULL OR NEW.version_hasta > h.version_hasta))))
BEGIN
    SELECT RAISE(ABORT, 'RD-05: la vigencia del uso no cabe en la del hecho');
END;

CREATE TRIGGER rd05_hecho_no_se_cierra_con_usos_abiertos
BEFORE UPDATE OF version_hasta ON hecho
FOR EACH ROW
WHEN NEW.version_hasta IS NOT NULL AND EXISTS (
    SELECT 1 FROM hecho_capitulo u WHERE u.hecho_id = NEW.id
        AND (u.version_hasta IS NULL OR u.version_hasta > NEW.version_hasta))
BEGIN
    SELECT RAISE(ABORT, 'RD-05: el hecho tiene usos vigentes más allá de su cierre');
END;

CREATE TABLE promesa (
    id                   TEXT NOT NULL PRIMARY KEY,
    novel_id             TEXT NOT NULL REFERENCES obra (novel_id),
    enunciado            TEXT NOT NULL,
    tipo                 TEXT NOT NULL,
    estado               TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN (
                             'pendiente', 'pagada', 'rota')),
    capitulo_apertura_id TEXT NOT NULL REFERENCES capitulo (id),
    capitulo_pago_id     TEXT REFERENCES capitulo (id)
);

CREATE INDEX promesa_por_estado ON promesa (novel_id, estado);

-- Snapshot: estado derivado del mundo al cierre de un capítulo (D-12). Uno por fila de
-- capítulo; su existencia es también la marca de que el capítulo ya se consolidó, que es lo
-- que hace idempotente la consolidación.
CREATE TABLE snapshot (
    id          TEXT NOT NULL PRIMARY KEY,
    novel_id    TEXT NOT NULL REFERENCES obra (novel_id),
    capitulo_id TEXT NOT NULL UNIQUE REFERENCES capitulo (id),
    contenido   TEXT NOT NULL CHECK (json_valid(contenido)),
    creado_en   TEXT NOT NULL
);

CREATE TABLE resumen_capitulo (
    id          TEXT NOT NULL PRIMARY KEY,
    novel_id    TEXT NOT NULL REFERENCES obra (novel_id),
    capitulo_id TEXT NOT NULL UNIQUE REFERENCES capitulo (id),
    texto       TEXT NOT NULL
);
