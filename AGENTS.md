# AGENTS.md

storyMaker: un sistema agéntico que genera novelas personalizadas para regalar.

**Las instrucciones completas están en [`CLAUDE.md`](CLAUDE.md), en la raíz de este
repositorio.** Este archivo no contiene ninguna regla: solo apunta allí.

Si tu herramienta resuelve imports, `CLAUDE.md` ya está en tu contexto y no hay nada más
que hacer. Si no los resuelve —Codex, Cursor, Copilot y Aider leen este fichero de forma
nativa pero no siguen una referencia en prosa—, **abre `CLAUDE.md` y léelo entero antes de
tocar nada**. Ahí están el stack cerrado, el layout, el presupuesto de contexto, las
puertas del ciclo de cambio y las dieciséis reglas.

No se duplica aquí ni una línea de esas reglas, y es deliberado: dos copias de la misma
regla divergen, y la que se queda vieja es siempre la que alguien acaba leyendo. La
decisión está en [`docs/trade-offs.md`](docs/trade-offs.md) TO-002.
