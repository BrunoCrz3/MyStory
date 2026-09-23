"""La maquina de estados del ciclo. **No es un agente.**

El backend orquesta; los agentes no. Un agente recibe su entrada, devuelve su
salida y termina: no sabe quien lo llamo ni que viene despues. Si el agente
eligiera, el grafo de ejecucion dejaria de ser inspeccionable y los
corta-circuitos no se podrian imponer desde fuera --quien decide cuando parar no
puede ser quien quiere seguir--.

Dos propiedades sostienen que insertar una cola mas adelante no toque a ningun
agente (RD-05, RD-08, RD-09), y las dos viven aqui:

- **El siguiente paso se deduce del estado persistido de la escena**, no de
  variables en memoria ni de la pila de llamadas. `siguiente_paso` es una
  funcion pura de lo que hay en la base.
- **Nadie de fuera de `process/` puede preguntar ni invocar.** Lo comprueba
  `tests/reglas/test_orquestacion_cerrada.py`, por analisis estatico: ningun
  modulo ajeno importa este paquete.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum

from app.novel.models import EstadoDeEscena
from app.quality.models import AlcanceDelDefecto


class Paso(StrEnum):
    """Lo que toca hacer a continuacion.

    `ESCALAR_AL_AUTOR` es un resultado valido, no un error: es el mecanismo por
    el que el sistema devuelve el juicio al unico rol que la ontologia no deja
    automatizar.
    """

    REDACTOR = "redactor"
    CRITICO = "critico"
    VERIFICADOR = "verificador"
    EDITOR = "editor"
    REPLANIFICAR = "replanificar"
    EXTRACTOR = "extractor"
    ESCALAR_AL_AUTOR = "escalar_al_autor"


def siguiente_paso(
    estado: EstadoDeEscena,
    *,
    alcance_del_peor_defecto: AlcanceDelDefecto | None = None,
    hay_informe: bool = False,
    iteraciones_de_revision: int = 0,
    max_iteraciones_revision: int | None = None,
) -> Paso:
    """Las siete filas de `architecture.md`, seccion Maquina de estados.

    | Estado        | Condicion                | Siguiente             |
    | planificada   | --                       | `redactor`            |
    | en borrador   | --                       | `critico`             |
    | en revision   | sin defectos sobre umbral| `verificador`         |
    | en revision   | defecto local            | `editor`              |
    | en revision   | defecto sistemico        | vuelve a planificada  |
    | aceptada      | --                       | `extractor`           |
    | obsoleta      | --                       | vuelve a planificada  |

    Y el corta-circuitos, que se impone antes que la tabla: al llegar al maximo
    de iteraciones de revision la escena se queda **en revision** y escala al
    autor (RF-PROC-06, P-33). Sin ese tope una escena que no converge gira entre
    `critico` y `editor` gastando presupuesto.

    Con `orquestacion.max_iteraciones_revision` en `null` no hay tope y no se
    escala por este motivo. Es el mismo criterio que la fase de medicion: un
    umbral que nadie ha puesto no decide, y decidir con uno inventado seria
    peor que no decidir.

    **La extraccion es un paso, no un estado**: por eso `aceptada` tiene fila y
    la extraccion no.
    """
    if estado is EstadoDeEscena.PLANIFICADA:
        return Paso.REDACTOR
    if estado is EstadoDeEscena.EN_BORRADOR:
        return Paso.CRITICO
    if estado is EstadoDeEscena.ACEPTADA:
        return Paso.EXTRACTOR
    if estado is EstadoDeEscena.OBSOLETA:
        return Paso.REPLANIFICAR

    if max_iteraciones_revision is not None and iteraciones_de_revision >= max_iteraciones_revision:
        return Paso.ESCALAR_AL_AUTOR
    if not hay_informe:
        # En revision sin critica todavia: la critica es lo que falta, no el
        # verificador. Pasa cuando el autor devuelve una escena a revision.
        return Paso.CRITICO
    if alcance_del_peor_defecto is AlcanceDelDefecto.SISTEMICO:
        return Paso.REPLANIFICAR
    if alcance_del_peor_defecto is AlcanceDelDefecto.LOCAL:
        return Paso.EDITOR
    return Paso.VERIFICADOR


# Ninguna fila lleva a `aceptada`, y no es un olvido: solo el autor humano mueve
# una escena ahi. El orquestador nunca salta ese paso (RF-PROC-07, P-19), y por
# eso tras el `verificador` la escena se queda en revision esperandolo.
PASOS_QUE_ACEPTAN: frozenset[Paso] = frozenset()


class CerrojoDeGeneracion:
    """Una sola escena en generacion a la vez (RNF-09, P-35).

    Con un autor y una obra por instancia no existe la concurrencia entre
    escenas, asi que esto no es un reparto de recursos: es la afirmacion de que
    el grano de concurrencia del sistema es el del dominio. De paso convierte al
    escritor unico de SQLite en un no-problema, porque la serializacion ya la
    impone el proceso mucho antes de llegar a la base.

    Lo que **no** entra aqui son los pasos de solo lectura --`critico`,
    `verificador`, las skills de `context/`--: solo leen, el canon y el texto en
    `t` no cambian mientras corren, y serializarlos seria pagar latencia por
    nada.

    El punto ciego esta declarado en P-35 y se asume: cubre un proceso. Dos
    instancias sobre el mismo `data/novel.db` rompen la serializacion sin que
    nadie lo detecte.
    """

    def __init__(self) -> None:
        self._cerrojo = asyncio.Lock()
        self._escena_en_curso: int | None = None

    @property
    def escena_en_curso(self) -> int | None:
        return self._escena_en_curso

    @asynccontextmanager
    async def generando(self, escena_id: int) -> AsyncIterator[None]:
        async with self._cerrojo:
            self._escena_en_curso = escena_id
            try:
                yield
            finally:
                self._escena_en_curso = None
