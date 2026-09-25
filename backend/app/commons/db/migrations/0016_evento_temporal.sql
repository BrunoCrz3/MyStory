-- Año, edad declarada y vigencia por versión del evento (TO-064, TO-066, spec 4).
--
-- `anio` es la cronología de la historia y `momento` sigue siendo el orden de narración: una
-- analepsis narra tarde un año temprano y no es una incoherencia. `anio` y `edad` solo se
-- rellenan cuando el texto los dice explícitamente; nulo es «no lo dice», nunca «cero».
--
-- La vigencia copia la del hecho (TO-028): semiabierta, `version_desde <= v < version_hasta`.
-- No se reconstruye la tabla porque `evento_personaje`, `evento_capitulo` y
-- `evento_excluyente` la referencian y las claves foráneas están activas dentro de la
-- transacción de la migración; `version_desde` se añade nula y un trigger impide que un evento
-- nuevo nazca sin ella (A-01 de specs/progreso-lean.md).

ALTER TABLE evento ADD COLUMN anio INTEGER CHECK (anio IS NULL OR anio >= 0);
ALTER TABLE evento_personaje ADD COLUMN edad INTEGER CHECK (edad IS NULL OR edad >= 0);
ALTER TABLE evento ADD COLUMN version_desde INTEGER CHECK (version_desde IS NULL OR version_desde >= 1);
ALTER TABLE evento ADD COLUMN version_hasta INTEGER
    CHECK (version_hasta IS NULL OR version_hasta >= version_desde);

-- Relleno. Un evento es de la fila de capítulo que lo narra, y vale desde la versión para la
-- que se escribió esa fila.
UPDATE evento SET version_desde = (
    SELECT c.version FROM evento_capitulo ec JOIN capitulo c ON c.id = ec.capitulo_id
    WHERE ec.evento_id = evento.id
);

-- Se cierra en la primera versión posterior, no rechazada, que ya no lee su capítulo.
UPDATE evento SET version_hasta = (
    SELECT MIN(v.version) FROM version_novela v
    WHERE v.novel_id = evento.novel_id
      AND v.version > evento.version_desde
      AND v.estado <> 'rechazada'
      AND NOT EXISTS (
          SELECT 1 FROM version_capitulo vc JOIN evento_capitulo ec
            ON ec.capitulo_id = vc.capitulo_id
          WHERE vc.novel_id = v.novel_id AND vc.version = v.version AND ec.evento_id = evento.id
      )
);

-- Lo que escribió una regeneración rechazada se revirtió con TO-062: intervalo vacío. Una
-- primera versión rechazada en el gate no se revierte y conserva sus eventos.
UPDATE evento SET version_hasta = version_desde
WHERE EXISTS (
    SELECT 1 FROM version_novela v
    WHERE v.novel_id = evento.novel_id AND v.version = evento.version_desde
      AND v.estado = 'rechazada' AND v.version_anterior_id IS NOT NULL
);

CREATE INDEX evento_por_vigencia ON evento (novel_id, version_desde, version_hasta);

CREATE TRIGGER evento_con_version
BEFORE INSERT ON evento
WHEN NEW.version_desde IS NULL
BEGIN
    SELECT RAISE(ABORT, 'evento.version_desde es obligatoria (TO-066)');
END;

CREATE TRIGGER evento_version_no_se_borra
BEFORE UPDATE OF version_desde ON evento
WHEN NEW.version_desde IS NULL
BEGIN
    SELECT RAISE(ABORT, 'evento.version_desde es obligatoria (TO-066)');
END;
