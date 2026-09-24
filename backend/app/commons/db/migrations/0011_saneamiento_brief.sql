-- Fragmento sospechoso: lo que el saneamiento retiró del texto libre al crear la novela, con
-- el motivo (definitions.md Capa 1A; RF-INTAKE-03, pregunta 4). Es la evidencia de qué se
-- descartó y por qué; el texto que se guarda en `texto_libre` ya va sin él.
--
-- `Dato faltante` y `Contradicción de brief` no tienen tabla (A-86): validar no crea nada y
-- crear rechaza el brief que los tiene, así que ninguna novela persistida llega a tenerlos.

CREATE TABLE fragmento_sospechoso (
    id        TEXT    NOT NULL PRIMARY KEY,
    novel_id  TEXT    NOT NULL REFERENCES obra (novel_id),
    orden     INTEGER NOT NULL CHECK (orden >= 0),
    fragmento TEXT    NOT NULL,
    motivo    TEXT    NOT NULL,
    creado_en TEXT    NOT NULL
);

CREATE INDEX fragmento_por_novela ON fragmento_sospechoso (novel_id, orden);
