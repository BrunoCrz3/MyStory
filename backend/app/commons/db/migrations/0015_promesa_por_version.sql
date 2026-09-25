-- Promesas por versión (TO-047, RF-VER-08).
--
-- Una promesa se abría y se pagaba en una columna de `promesa`, así que solo podía tener un
-- capítulo de apertura y uno de pago. Una regeneración dirigida crea filas nuevas de los
-- capítulos afectados, y la fila nueva tiene que poder reabrir la promesa que abría la vieja
-- o pagar la que pagaba sin tocar lo que lee la versión anterior (regla 15).
--
-- Desde aquí la apertura y el pago son vínculos de la promesa con filas de capítulo, como el
-- puente `hecho_capitulo`. Una versión ve lo que ven sus filas: el estado de una promesa se
-- deriva en cada lectura y no se guarda.

CREATE TABLE promesa_nueva (
    id        TEXT NOT NULL PRIMARY KEY,
    novel_id  TEXT NOT NULL REFERENCES obra (novel_id),
    enunciado TEXT NOT NULL,
    tipo      TEXT NOT NULL
);

INSERT INTO promesa_nueva (id, novel_id, enunciado, tipo)
    SELECT id, novel_id, enunciado, tipo FROM promesa ORDER BY rowid;

CREATE TABLE promesa_capitulo (
    novel_id    TEXT NOT NULL REFERENCES obra (novel_id),
    promesa_id  TEXT NOT NULL REFERENCES promesa_nueva (id),
    capitulo_id TEXT NOT NULL REFERENCES capitulo (id),
    papel       TEXT NOT NULL CHECK (papel IN ('apertura', 'pago')),
    PRIMARY KEY (promesa_id, capitulo_id, papel)
);

CREATE INDEX promesa_capitulo_por_capitulo ON promesa_capitulo (novel_id, capitulo_id, papel);

INSERT INTO promesa_capitulo (novel_id, promesa_id, capitulo_id, papel)
    SELECT novel_id, id, capitulo_apertura_id, 'apertura' FROM promesa;
INSERT INTO promesa_capitulo (novel_id, promesa_id, capitulo_id, papel)
    SELECT novel_id, id, capitulo_pago_id, 'pago' FROM promesa WHERE capitulo_pago_id IS NOT NULL;

DROP INDEX promesa_por_estado;
DROP TABLE promesa;
-- Renombrar reescribe también la referencia de `promesa_capitulo`.
ALTER TABLE promesa_nueva RENAME TO promesa;
