"""La máquina de estados del orquestador como **dato** (RF-PROC-07, TO-020).

Una fila por acción de `docs/architecture.md` § Estados, con la máquina a la que pertenece.
El orquestador no decide transiciones por su cuenta: pide `aplicar()`, y una transición que
no está en la tabla se rechaza sin mutar nada. La prueba de `tests/process/` compara esta
tabla con los dos diagramas de `domain-knowledge.md` y con la tabla de `architecture.md`, y
la spec TLA+ se comparará con este mismo dato.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.commons.errores import TransicionInvalida

Maquina = Literal["Capitulo", "Novela"]


@dataclass(frozen=True)
class Transicion:
    accion: str
    maquina: Maquina
    origen: str | None
    destino: str
    funcion: str


TRANSICIONES: tuple[Transicion, ...] = (
    Transicion("Init", "Capitulo", None, "Pendiente", "orquestador.estado_inicial"),
    Transicion("Escribir", "Capitulo", "Pendiente", "Escribiendo", "orquestador.escribir"),
    Transicion("Validar", "Capitulo", "Escribiendo", "Validando", "orquestador.validar"),
    Transicion("Aceptar", "Capitulo", "Validando", "Aceptado", "orquestador.aceptar"),
    Transicion("Reescribir", "Capitulo", "Validando", "Reescribiendo", "orquestador.reescribir"),
    Transicion("Reintentar", "Capitulo", "Reescribiendo", "Escribiendo", "orquestador.reintentar"),
    Transicion("Agotar", "Capitulo", "Reescribiendo", "Agotado", "orquestador.agotar"),
    Transicion("Obsoletar", "Capitulo", "Aceptado", "Obsoleto", "orquestador.obsoletar"),
    Transicion("Reencolar", "Capitulo", "Obsoleto", "Pendiente", "orquestador.reencolar"),
    Transicion("Planificar", "Novela", "Configurando", "Planificando", "orquestador.planificar"),
    Transicion(
        "FijarEsquema", "Novela", "Planificando", "Escribiendo", "orquestador.fijar_esquema"
    ),
    Transicion(
        "CerrarEscritura", "Novela", "Escribiendo", "Validando", "orquestador.cerrar_escritura"
    ),
    Transicion(
        "DevolverAlEditor", "Novela", "Validando", "Escribiendo", "orquestador.devolver_al_editor"
    ),
    Transicion("Publicar", "Novela", "Validando", "Publicando", "orquestador.publicar"),
    Transicion("Conservar", "Novela", "Publicando", "Publicada", "orquestador.conservar"),
    Transicion("Regenerar", "Novela", "Publicada", "Regenerando", "orquestador.regenerar"),
    Transicion(
        "CerrarRegeneracion",
        "Novela",
        "Regenerando",
        "Validando",
        "orquestador.cerrar_regeneracion",
    ),
    Transicion("Detener", "Novela", "Escribiendo", "Detenida", "orquestador.detener"),
    Transicion("Detener", "Novela", "Planificando", "Detenida", "orquestador.detener"),
    Transicion("Detener", "Novela", "Regenerando", "Detenida", "orquestador.detener"),
)

_INDICE: dict[tuple[Maquina, str | None, str], str] = {
    (t.maquina, t.origen, t.accion): t.destino for t in TRANSICIONES
}


def aplicar(maquina: Maquina, estado: str | None, accion: str) -> str:
    """Estado destino de `accion` desde `estado`, o `TransicionInvalida` si no está."""
    destino = _INDICE.get((maquina, estado, accion))
    if destino is None:
        posibles = sorted(acciones_desde(maquina, estado))
        raise TransicionInvalida(
            f"{maquina}: la acción {accion} no está permitida desde {estado}; "
            f"desde ahí solo {', '.join(posibles) or 'ninguna (estado terminal)'}"
        )
    return destino


def acciones_desde(maquina: Maquina, estado: str | None) -> set[str]:
    return {t.accion for t in TRANSICIONES if t.maquina == maquina and t.origen == estado}
