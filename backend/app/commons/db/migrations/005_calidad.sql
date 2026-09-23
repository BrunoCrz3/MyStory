-- Migracion 005 - H5. Capa 4: dimensiones, informe de critica y defectos.
--
-- «Cada dimension necesita definicion, nivel de aplicacion, metodo de medicion y
-- umbral. Sin las cuatro cosas no es una metrica, es una opinion». Las tres
-- primeras son de la ontologia y viven en `dimension_calidad`; el umbral es la
-- cuarta y vive en `config/thresholds.yaml`, que es donde viven todas las
-- cifras. Por eso esta tabla no tiene columna de umbral.
--
-- Se siembran las catorce dimensiones clasificadas `T` en `docs/verification.md`,
-- que son las que `config/thresholds.yaml` lista bajo `calidad`. Las `D` y las
-- `U` —caracterizacion, curva de tension y sentido de la maravilla— quedan fuera
-- de v1 y por eso no estan aqui: una fila sin criterio de aprobado medible seria
-- una opinion con numero de tabla.
--
-- El `nivel` no es decorativo: es lo que decide si un defecto es local o
-- sistemico (RF-QUA-04). Lo que se mide en la frase o en la escena se corrige
-- reescribiendo en sitio; lo que se mide en la obra, la parte o el capitulo
-- invalida la planificacion.

CREATE TABLE dimension_calidad (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL UNIQUE,
    nivel    TEXT NOT NULL CHECK (nivel IN ('Frase', 'Escena', 'Capítulo', 'Parte', 'Obra')),
    medicion TEXT NOT NULL
);

INSERT INTO dimension_calidad (nombre, nivel, medicion) VALUES
    ('consistencia_factica',      'Escena',   'Verificación contra hechos canónicos'),
    ('consistencia_temporal',     'Obra',     'Orden de eventos vs. duraciones declaradas'),
    ('consistencia_espacial',     'Capítulo', 'Snapshot de posiciones'),
    ('consistencia_epistemica',   'Escena',   'Estado epistémico del POV'),
    ('plausibilidad_especulativa','Escena',   'Reglas del mundo declaradas'),
    ('distintividad_de_voz',      'Escena',   'Clasificación ciega de diálogo'),
    ('calidad_de_prosa',          'Frase',    'Métricas léxicas automáticas'),
    ('mostrar_vs_contar',         'Escena',   'Ratio escena/sumario'),
    ('integridad_de_pov',         'Escena',   'Detección de accesos mentales ajenos'),
    ('causalidad',                'Capítulo', 'Prueba de conectores causales'),
    ('ritmo',                     'Parte',    'Longitud y tipo de escena en secuencia'),
    ('carga_expositiva',          'Escena',   'Tokens de exposición sobre total'),
    ('originalidad',              'Obra',     'Comparación con línea base sin guía'),
    ('cumplimiento_del_brief',    'Escena',   'Cotejo punto por punto');

-- `Informe de critica evalua Borrador` es 1:1. `Borrador` nace en la migracion
-- 006, asi que aqui el borrador se identifica por la misma clave con la que el
-- resto del sistema lo identifica: escena mas version. El `unique` sobre el par
-- **es** esa cardinalidad; la clave foranea llega con la tabla.
CREATE TABLE informe_critica (
    id                INTEGER PRIMARY KEY,
    escena_id         INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    version           INTEGER NOT NULL,
    -- Punto ciego #15: la fase va junto a cada informe, con cuantas escenas
    -- aceptadas hay desde que se declaro. Un corpus que ya da para calibrar y
    -- una fase que sigue abierta es una senal, no un estado.
    fase_de_medicion  INTEGER NOT NULL CHECK (fase_de_medicion IN (0, 1)),
    escenas_aceptadas INTEGER NOT NULL,
    emitido_en        TEXT NOT NULL,
    UNIQUE (escena_id, version)
);

-- Una puntuacion por dimension y por informe. No es una clase de la ontologia
-- sino la relacion entre dos que si lo son, como los puentes de la Capa 1.
--
-- `valor` admite NULL y no es un olvido: hay dimensiones `T` que v1 no puede
-- medir porque la ontologia no da con que. Devolver un numero inventado seria
-- peor que no devolverlo — entraria en el historial y contaminaria A-50—, asi
-- que se guarda NULL y el motivo al lado.
CREATE TABLE puntuacion_de_dimension (
    informe_id   INTEGER NOT NULL REFERENCES informe_critica (id) ON DELETE CASCADE,
    dimension_id INTEGER NOT NULL REFERENCES dimension_calidad (id),
    valor        REAL,
    umbral       REAL,
    suspende     INTEGER NOT NULL DEFAULT 0 CHECK (suspende IN (0, 1)),
    motivo       TEXT,
    PRIMARY KEY (informe_id, dimension_id)
);

-- `Defecto viola Dimension de calidad`, N:1.
CREATE TABLE defecto (
    id           INTEGER PRIMARY KEY,
    informe_id   INTEGER NOT NULL REFERENCES informe_critica (id) ON DELETE CASCADE,
    dimension_id INTEGER NOT NULL REFERENCES dimension_calidad (id),
    gravedad     TEXT NOT NULL CHECK (gravedad IN ('baja', 'media', 'alta')),
    alcance      TEXT NOT NULL CHECK (alcance IN ('local', 'sistemico')),
    eje          TEXT,
    localizacion TEXT,
    descripcion  TEXT NOT NULL
);

CREATE INDEX idx_defecto_informe ON defecto (informe_id);
CREATE INDEX idx_informe_escena ON informe_critica (escena_id, version);
