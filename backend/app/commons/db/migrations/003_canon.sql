-- Migracion 003 - H3. Capa 2: el canon y el estado del mundo.
--
-- Dos decisiones de esta migracion conviene leerlas antes que el SQL:
--
-- 1. `Hecho canonico.tipo` se enumera a medias, y a proposito. El plan lo
--    declara como riesgo asumido: se implementa la mitad enumerable —la que
--    permite derivar el snapshot— y la descriptiva queda en un solo valor,
--    `descriptivo`, sin desglosar. Lo que no se hace es fingir que esta
--    resuelta.
--
-- 2. El snapshot no guarda el estado del mundo. Guarda que existe un snapshot
--    para una escena y con que fecha ficcional; el contenido se deriva de los
--    hechos vigentes (RF-CANON-03). Una columna con «personajes vivos» seria
--    una segunda fuente de verdad, y la consultada dejaria de ser la que los
--    hechos dicen.
--
-- El alcance temporal de un hecho son dos columnas: la escena que lo establece
-- es su inicio, y `vigente_hasta_escena_id` en NULL significa abierto. Un hecho
-- abierto sigue vigente hasta que otro lo cierra, y queda constancia de cual
-- (P-48, RF-CANON-15).

CREATE TABLE hecho_canonico (
    id                      INTEGER PRIMARY KEY,
    texto                   TEXT NOT NULL,
    tipo                    TEXT NOT NULL CHECK (
                                tipo IN (
                                    'estado_vital',
                                    'ubicacion',
                                    'posesion',
                                    'relacion',
                                    'descriptivo'
                                )
                            ),
    -- La escena que lo establece. RF-CANON-11: es lo unico que ata el canon a
    -- la prosa de la que salio.
    escena_id               INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    estatus                 TEXT NOT NULL DEFAULT 'provisional' CHECK (
                                estatus IN (
                                    'confirmado',
                                    'implicito',
                                    'provisional',
                                    'retconeado',
                                    'refutado'
                                )
                            ),
    sujeto_personaje_id     INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    objeto_personaje_id     INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    lugar_id                INTEGER REFERENCES lugar (id) ON DELETE SET NULL,
    artefacto_id            INTEGER REFERENCES artefacto (id) ON DELETE SET NULL,
    valor                   TEXT,
    -- Alcance temporal. NULL = abierto.
    vigente_hasta_escena_id INTEGER REFERENCES escena (id) ON DELETE SET NULL,
    cerrado_por_hecho_id    INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL,
    -- RF-CANON-10: si la trama vuelve sobre un hecho terminal, el sucesor lo
    -- referencia en vez de revivirlo.
    sucede_a_hecho_id       INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL
);

CREATE INDEX idx_hecho_escena ON hecho_canonico (escena_id);
CREATE INDEX idx_hecho_sujeto ON hecho_canonico (tipo, sujeto_personaje_id);
CREATE INDEX idx_hecho_artefacto ON hecho_canonico (tipo, artefacto_id);

-- `Escena produce Snapshot de mundo` es 1:1. `version` es la otra mitad de la
-- clave de idempotencia de RF-CANON-08: consolidar dos veces la misma escena
-- con la misma version no escribe dos veces.
CREATE TABLE snapshot_mundo (
    id              INTEGER PRIMARY KEY,
    escena_id       INTEGER NOT NULL UNIQUE REFERENCES escena (id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,
    fecha_ficcional TEXT,
    consolidado_en  TEXT NOT NULL
);

-- `Hecho canonico proyecta Snapshot de mundo`, N:M.
CREATE TABLE hecho_snapshot (
    hecho_id    INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    snapshot_id INTEGER NOT NULL REFERENCES snapshot_mundo (id) ON DELETE CASCADE,
    PRIMARY KEY (hecho_id, snapshot_id)
);

-- `Personaje conoce Hecho canonico (desde escena)`. La tercera columna no es
-- opcional: sin ella no se responde «que sabe este personaje en el capitulo 12
-- y desde cuando», que es la pregunta de competencia 1.
CREATE TABLE estado_epistemico (
    id           INTEGER PRIMARY KEY,
    personaje_id INTEGER NOT NULL REFERENCES personaje (id) ON DELETE CASCADE,
    hecho_id     INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    escena_id    INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    certeza      TEXT,
    UNIQUE (personaje_id, hecho_id)
);

-- Desfase entre lo que sabe el lector y lo que sabe un personaje.
CREATE TABLE ironia_dramatica (
    id                 INTEGER PRIMARY KEY,
    hecho_id           INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    lo_sabe_id         INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    no_lo_sabe_id      INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    UNIQUE (hecho_id, lo_sabe_id, no_lo_sabe_id)
);

CREATE TABLE promesa_narrativa (
    id           INTEGER PRIMARY KEY,
    texto        TEXT NOT NULL,
    tipo         TEXT NOT NULL CHECK (tipo IN ('setup', 'pregunta', 'amenaza', 'deuda')),
    estado       TEXT NOT NULL DEFAULT 'pendiente' CHECK (
                     estado IN ('pendiente', 'pagada', 'rota', 'subvertida')
                 ),
    -- `Artefacto genera deuda Promesa narrativa`, 1:N.
    artefacto_id INTEGER REFERENCES artefacto (id) ON DELETE SET NULL
);

-- `Escena abre / paga Promesa narrativa`, N:M con rol. Las dos escenas de la
-- ficha de la clase se derivan de aqui en vez de duplicarse en columnas.
CREATE TABLE escena_promesa (
    escena_id  INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    promesa_id INTEGER NOT NULL REFERENCES promesa_narrativa (id) ON DELETE CASCADE,
    rol        TEXT NOT NULL CHECK (rol IN ('abre', 'paga')),
    PRIMARY KEY (escena_id, promesa_id, rol)
);

CREATE TABLE revelacion (
    id                 INTEGER PRIMARY KEY,
    hecho_id           INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    destinatario       TEXT NOT NULL CHECK (destinatario IN ('lector', 'personaje')),
    personaje_id       INTEGER REFERENCES personaje (id) ON DELETE CASCADE,
    escena_minima_id   INTEGER REFERENCES escena (id) ON DELETE SET NULL
);

-- v1 responde que escenas invalidaria un retcon, pero no lo aplica (spec §1.3).
-- La tabla existe porque la ontologia la tiene; `retcon_escena` se queda vacia
-- hasta que entre el bucle largo.
CREATE TABLE retcon (
    id                INTEGER PRIMARY KEY,
    hecho_antiguo_id  INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    hecho_nuevo_id    INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL,
    decidido_en       TEXT
);

CREATE TABLE retcon_escena (
    retcon_id INTEGER NOT NULL REFERENCES retcon (id) ON DELETE CASCADE,
    escena_id INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    PRIMARY KEY (retcon_id, escena_id)
);

-- `Hecho canonico contradice Hecho canonico` es N:M con atributos, asi que la
-- relacion es esta entidad y no una tabla puente pelada.
CREATE TABLE contradiccion (
    id         INTEGER PRIMARY KEY,
    hecho_a_id INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    hecho_b_id INTEGER NOT NULL REFERENCES hecho_canonico (id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL,
    gravedad   TEXT NOT NULL CHECK (gravedad IN ('baja', 'media', 'alta')),
    resolucion TEXT,
    -- `Contradiccion se resuelve con Retcon`, N:1.
    retcon_id  INTEGER REFERENCES retcon (id) ON DELETE SET NULL,
    UNIQUE (hecho_a_id, hecho_b_id),
    CHECK (hecho_a_id <> hecho_b_id)
);

-- Orden del discurso. `t` es una posicion en el discurso, no una fecha del
-- mundo ficcional (definitions.md, Convenciones). Todo lo que dependa de «antes
-- de» y «despues de» pasa por aqui, para que haya un solo sitio donde se
-- decide que escena viene primero.
CREATE VIEW escena_ordenada AS
SELECT escena.id AS escena_id,
       ROW_NUMBER() OVER (ORDER BY parte.orden, capitulo.orden, escena.orden) AS posicion
FROM escena
JOIN capitulo ON capitulo.id = escena.capitulo_id
JOIN parte ON parte.id = capitulo.parte_id;
