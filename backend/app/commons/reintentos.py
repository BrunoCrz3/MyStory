"""Backoff exponencial con jitter (RI-07).

Un limite de tasa del proveedor no es un defecto de la escena: es una espera. Y
si todos los trabajos que lo reciben reintentan a la vez, la espera se convierte
en cascada --todos piden, todos reciben 429, todos vuelven a pedir al mismo
tiempo--. El jitter existe para romper esa sincronia, no para que los numeros
queden bonitos.

**Esquema: full jitter.** La espera del intento `n` es un valor al azar entre
cero y `base * factor^(n-1)`. Se elige este y no otro porque es el que mas
dispersa los reintentos de una rafaga, que es exactamente el problema que hay
aqui: la rafaga de pasos de solo lectura de una escena sale junta.

**Con los umbrales en `null` no hay reintento**, y es el mismo criterio que en
toda la casa: un umbral que nadie ha puesto no decide. `max_intentos_trabajo`,
`base_segundos` y `factor` estan en `null` en v1, asi que una llamada se hace una
vez y su fallo sube. Ponerlos es una decision del autor sobre coste y paciencia,
y hasta que la tome el sistema no reintenta a su espalda.

**Un fallo de infraestructura no cuenta contra el tope de revisiones.** Son dos
corta-circuitos distintos: este cuenta intentos de una llamada, y el de
`orquestacion.max_iteraciones_revision` cuenta vueltas de critica. Mezclarlos
haria que un mal dia del proveedor gastara el presupuesto de revision de la
escena.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.commons.config import Umbrales

PRIMER_INTENTO = 1


@dataclass(frozen=True)
class PoliticaDeReintentos:
    """Cuantas veces y cuanto se espera. Ninguna cifra vive aqui (A-40)."""

    max_intentos: int | None
    base_segundos: float | None
    factor: float | None
    jitter: bool

    @classmethod
    def declarada(cls, umbrales: Umbrales) -> PoliticaDeReintentos:
        return cls(
            max_intentos=umbrales.orquestacion.max_intentos_trabajo,
            base_segundos=umbrales.orquestacion.backoff.base_segundos,
            factor=umbrales.orquestacion.backoff.factor,
            jitter=umbrales.orquestacion.backoff.jitter,
        )

    @property
    def activa(self) -> bool:
        """Hacen falta las tres cifras. Con una sola en `null` no hay politica:
        reintentar sin saber cuanto esperar es reintentar de inmediato."""
        return (
            self.max_intentos is not None
            and self.base_segundos is not None
            and self.factor is not None
        )

    def quedan_intentos(self, intento: int) -> bool:
        if not self.activa:
            return False
        assert self.max_intentos is not None
        return intento < self.max_intentos

    def espera(self, intento: int, azar: float | None = None) -> float:
        """Segundos antes del intento `intento + 1`.

        `azar` se puede fijar para poder probar la forma de la curva sin
        depender del generador: sin jitter no se usa, y con jitter multiplica.
        """
        if not self.activa:
            return 0.0
        assert self.base_segundos is not None and self.factor is not None
        tope = self.base_segundos * self.factor ** (intento - PRIMER_INTENTO)
        if not self.jitter:
            return tope
        proporcion = random.random() if azar is None else azar  # noqa: S311
        return tope * proporcion
