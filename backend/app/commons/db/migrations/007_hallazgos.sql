-- Migracion 007 - H7. Modo hibrido: lo que la escritura descubre.
--
-- Dos tablas para las tres clases que `architecture.md` asigna a `findings/`:
-- `Extraccion`, `Hallazgo` y `Estado de hallazgo` --esta ultima es un `CHECK`,
-- que es la misma cosa dicha en SQL--.
--
-- Aqui es donde el ciclo se cierra. La flecha descendente del modo hibrido lleva
-- restricciones: que debe ser cierto al terminar la escena. La ascendente lleva
-- hallazgos: lo que surgio al escribirla y el plan no habia previsto.

-- ---------------------------------------------------------------------------
-- Extraccion
-- ---------------------------------------------------------------------------
-- «Lectura automatica de una escena aceptada para detectar hallazgos».
--
-- El `UNIQUE` sobre escena y version es la idempotencia del paso: volver a
-- extraer la misma version no duplica hallazgos. Sin el, cada reintento
-- sembraria la bandeja del autor de copias de lo mismo.
--
-- `registro_id` admite NULL y es el caso normal en v1: la extraccion
-- determinista no llama al modelo, asi que no hay generacion que registrar. Lo
-- lleva la candidatura que si venga de un modelo, para que el hallazgo se pueda
-- rastrear hasta el prompt del que salio.
CREATE TABLE extraccion (
    id          INTEGER PRIMARY KEY,
    escena_id   INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    version     INTEGER NOT NULL,
    entradas    TEXT NOT NULL,
    confianza   REAL,
    registro_id INTEGER REFERENCES registro_generacion (id) ON DELETE SET NULL,
    extraido_en TEXT NOT NULL,
    UNIQUE (escena_id, version)
);

-- ---------------------------------------------------------------------------
-- Hallazgo
-- ---------------------------------------------------------------------------
-- `Extraccion propone Hallazgo`, 1:N, y `Escena aceptada revela Hallazgo`, 1:N.
--
-- **El estado por defecto es `propuesto` y no hay forma de nacer en otro.** Es
-- el ultimo cortafuegos de la resistencia a inyeccion: aunque un texto lograra
-- colar una afirmacion, entra como propuesta y muere ahi salvo que el autor la
-- adopte. Por eso el `DEFAULT` esta en el esquema y no en el codigo.
--
-- Los cinco estados son los del ciclo de vida de `domain-knowledge.md`. El
-- nombre es `propuesto`, nunca `provisional`: `provisional` es un estatus de
-- `Hecho canonico` y son cosas distintas.
--
-- `decidido_por` solo admite un valor, y no es un descuido: adoptar un hallazgo
-- equivale a cambiar la novela que se esta escribiendo, y eso la ontologia no lo
-- deja automatizar. La columna existe para que quien lea la tabla no tenga que
-- conocer la regla.
--
-- Las cuatro columnas de adopcion son `Hallazgo se adopta como Hecho canonico o
-- Promesa`, N:1, ampliada a los otros dos `tipo` que la ontologia enumera. Todas
-- admiten NULL porque un hallazgo `propuesto` todavia no es nada.
CREATE TABLE hallazgo (
    id            INTEGER PRIMARY KEY,
    extraccion_id INTEGER NOT NULL REFERENCES extraccion (id) ON DELETE CASCADE,
    escena_id     INTEGER NOT NULL REFERENCES escena (id) ON DELETE CASCADE,
    tipo          TEXT NOT NULL CHECK (tipo IN ('hecho', 'promesa', 'motivo', 'personaje')),
    estado        TEXT NOT NULL DEFAULT 'propuesto' CHECK (
                      estado IN (
                          'propuesto',
                          'adoptado',
                          'descartado',
                          'conflictivo',
                          'integrado'
                      )
                  ),
    texto         TEXT NOT NULL,
    fuente        TEXT NOT NULL,
    confianza     REAL,
    hecho_id      INTEGER REFERENCES hecho_canonico (id) ON DELETE SET NULL,
    promesa_id    INTEGER REFERENCES promesa_narrativa (id) ON DELETE SET NULL,
    motivo_id     INTEGER REFERENCES motivo (id) ON DELETE SET NULL,
    personaje_id  INTEGER REFERENCES personaje (id) ON DELETE SET NULL,
    decidido_por  TEXT CHECK (decidido_por IS NULL OR decidido_por = 'autor_humano'),
    decidido_en   TEXT,
    propuesto_en  TEXT NOT NULL,
    UNIQUE (extraccion_id, tipo, texto)
);

CREATE INDEX idx_hallazgo_escena ON hallazgo (escena_id, estado);
CREATE INDEX idx_hallazgo_estado ON hallazgo (estado);
