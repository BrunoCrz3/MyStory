"""Ensamblador de contexto por capas (RF-CTX-01…03, `CLAUDE.md` § Presupuesto de contexto).

Cada capa trae su contenido como piezas y se cuenta **antes** de llamar al modelo, con el
contador del proveedor. Una capa que se pasa de su presupuesto se comprime **ella sola**
—primero sustituye piezas literales por su resumen, luego quita piezas, de menos a más
prioridad— y nunca roba sitio a otra. Si la petición entera sigue sin caber, se degrada en el
orden de `contexto.degradacion` y se para en cuanto cabe. La Invariante y la Estructural, que
lleva la restricción de destino, no se degradan nunca: si no caben, falla en voz alta.

Todo el contenido de la novela va en el mensaje de usuario, dentro de etiquetas de capa. El
`system` es solo el prompt del rol y sus skills, que son ficheros del repositorio (RNF-09).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config, Rol
from app.commons.llm import Mensaje, Peticion
from app.commons.llm.llamar import ContextoNoCabe
from app.prompts import prompt_de, skills_de

NombreCapa = Literal[
    "invariante", "estructural", "estado", "local", "recuperado", "estilo", "anticontexto"
]
CAPAS: tuple[NombreCapa, ...] = (
    "invariante",
    "estructural",
    "estado",
    "local",
    "recuperado",
    "estilo",
    "anticontexto",
)
NO_DEGRADABLES: frozenset[NombreCapa] = frozenset({"invariante", "estructural"})
ETIQUETA_NO_CONFIABLE = "texto_libre_no_confiable"


class Contador(Protocol):
    async def contar_texto(self, rol: Rol, texto: str) -> int: ...

    async def contar_peticion(self, peticion: Peticion) -> int: ...


class Pieza(BaseModel):
    """Un trozo de una capa. `resumen` es su versión de menos resolución, si la tiene."""

    model_config = ConfigDict(frozen=True)

    texto: str
    resumen: str | None = None
    prioridad: int = 0
    etiqueta: str | None = None
    no_confiable: bool = False


class Degradacion(BaseModel):
    model_config = ConfigDict(frozen=True)

    capa: NombreCapa
    paso: Literal["resumen", "fuera"]
    pieza: int
    motivo: Literal["capa", "total"]


class Ensamblado(BaseModel):
    peticion: Peticion
    tokens_por_capa: dict[str, int]
    tokens_entrada: int
    degradaciones: list[Degradacion]


def _escapar(texto: str) -> str:
    # Nada de lo que viene de la novela puede abrir ni cerrar una etiqueta del ensamblado.
    return texto.replace("<", "‹").replace(">", "›")


@dataclass
class _Capa:
    nombre: NombreCapa
    piezas: list[Pieza]
    estados: list[Literal["literal", "resumen", "fuera"]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.estados = ["literal"] * len(self.piezas)

    def pasos(self) -> list[tuple[int, Literal["resumen", "fuera"]]]:
        """Compresiones posibles desde el estado actual, en el orden en que se aplican."""
        orden = sorted(range(len(self.piezas)), key=lambda i: (self.piezas[i].prioridad, -i))
        a_resumen: list[tuple[int, Literal["resumen", "fuera"]]] = [
            (i, "resumen")
            for i in orden
            if self.estados[i] == "literal" and self.piezas[i].resumen is not None
        ]
        fuera: list[tuple[int, Literal["resumen", "fuera"]]] = [
            (i, "fuera") for i in orden if self.estados[i] != "fuera"
        ]
        return a_resumen + fuera

    def render(self) -> str:
        partes = []
        for pieza, estado in zip(self.piezas, self.estados, strict=True):
            if estado == "fuera":
                continue
            texto = _escapar(
                pieza.resumen if estado == "resumen" and pieza.resumen else pieza.texto
            )
            if pieza.etiqueta:
                texto = f"{_escapar(pieza.etiqueta)}:\n{texto}"
            if pieza.no_confiable:
                texto = f"<{ETIQUETA_NO_CONFIABLE}>\n{texto}\n</{ETIQUETA_NO_CONFIABLE}>"
            partes.append(texto)
        return "\n\n".join(partes)


class Ensamblador:
    def __init__(self, config: Config, contador: Contador) -> None:
        self.config = config
        self.contador = contador

    def _presupuesto(self, capa: NombreCapa) -> int:
        valor: int = getattr(self.config.umbrales.contexto.capas, capa)
        return valor

    async def _tokens(self, rol: Rol, capa: _Capa, system: str) -> int:
        tokens = await self.contador.contar_texto(rol, capa.render()) if capa.piezas else 0
        if capa.nombre == "invariante":
            tokens += await self.contador.contar_texto(rol, system)
        return tokens

    @staticmethod
    def _mensaje(capas: dict[NombreCapa, _Capa], tarea: str) -> str:
        bloques = [
            f'<capa nombre="{nombre}">\n{capas[nombre].render()}\n</capa>'
            for nombre in CAPAS
            if nombre in capas
        ]
        bloques.append(f"<tarea>\n{tarea}\n</tarea>")
        return "\n\n".join(bloques)

    async def ensamblar(
        self,
        rol: Rol,
        piezas: dict[str, list[Pieza]],
        *,
        tarea: str,
        esquema_salida: dict[str, Any] | None = None,
    ) -> Ensamblado:
        desconocidas = set(piezas) - set(CAPAS)
        if desconocidas:
            raise ValueError(f"capas desconocidas: {sorted(desconocidas)}")
        prompt = prompt_de(rol)
        skills = skills_de(rol)
        system = "\n\n".join([prompt.texto, *(s.texto for s in skills)])
        capas = {n: _Capa(n, list(piezas.get(n, []))) for n in CAPAS}
        degradaciones: list[Degradacion] = []
        tokens: dict[str, int] = {}

        # 1. Cada capa dentro de su presupuesto, comprimiendo solo esa capa.
        for nombre in CAPAS:
            capa = capas[nombre]
            presupuesto = self._presupuesto(nombre)
            tokens[nombre] = await self._tokens(rol, capa, system)
            if tokens[nombre] <= presupuesto:
                continue
            if nombre in NO_DEGRADABLES:
                raise ContextoNoCabe(
                    f"{rol}: la capa {nombre} ocupa {tokens[nombre]} tokens y su presupuesto es "
                    f"{presupuesto}; esta capa no se degrada nunca"
                )
            while tokens[nombre] > presupuesto:
                pasos = capa.pasos()
                if not pasos:
                    break
                indice, paso = pasos[0]
                capa.estados[indice] = paso
                degradaciones.append(
                    Degradacion(capa=nombre, paso=paso, pieza=indice, motivo="capa")
                )
                tokens[nombre] = await self._tokens(rol, capa, system)

        # 2. La petición entera, contada por el proveedor, dentro del límite por petición.
        limite = self.config.umbrales.contexto.total - self.config.umbrales.contexto.capas.margen

        def construir() -> Peticion:
            return Peticion(
                rol=rol,
                system=system,
                mensajes=[Mensaje(role="user", contenido=self._mensaje(capas, tarea))],
                esquema_salida=esquema_salida,
                prompt=prompt.nombre,
                hash_prompt=prompt.hash_git,
            )

        peticion = construir()
        total = await self.contador.contar_peticion(peticion)
        for nombre in self.config.umbrales.contexto.degradacion:
            capa = capas[nombre]
            while total > limite:
                pasos = capa.pasos()
                if not pasos:
                    break
                indice, paso = pasos[0]
                capa.estados[indice] = paso
                degradaciones.append(
                    Degradacion(capa=nombre, paso=paso, pieza=indice, motivo="total")
                )
                peticion = construir()
                total = await self.contador.contar_peticion(peticion)
                tokens[nombre] = await self._tokens(rol, capa, system)
            if total <= limite:
                break
        if total > limite:
            raise ContextoNoCabe(
                f"{rol}: la petición ocupa {total} tokens tras degradar todo lo degradable y el "
                f"límite de entrada es {limite}; no se trunca en silencio"
            )
        return Ensamblado(
            peticion=peticion,
            tokens_por_capa=tokens,
            tokens_entrada=total,
            degradaciones=degradaciones,
        )
