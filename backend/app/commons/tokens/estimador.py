"""Estimador local de tokens.

No es el contador que manda. El que decide es el del proveedor —`ContadorDeTokens`,
en este mismo paquete—, y corre una sola vez, justo antes de llamar (A-02, A-09).
Este estima **durante** el ensamblado, que itera al degradar: preguntar al
proveedor en cada vuelta de la escalera costaria una llamada por vuelta.

La diferencia entre los dos la absorbe `contexto.capas.margen`, que es
exactamente la mitigacion que `docs/verification.md` declara en A-09. Y el punto
ciego queda escrito: si esto cuenta menos que el tokenizador del proveedor, el
prompt cabe en la prueba y no en la ventana.

Nada de `tiktoken`: es el tokenizador de otro proveedor y subcuenta los tokens de
Claude. Una cifra equivocada con aspecto de exacta es peor que una aproximacion
declarada.
"""

from __future__ import annotations

from math import ceil

MIL = 1000


class EstimadorDeTokens:
    def __init__(self, tokens_por_mil_caracteres: int) -> None:
        self._tokens_por_mil_caracteres = tokens_por_mil_caracteres

    def contar(self, texto: str) -> int:
        if not texto:
            return 0
        return ceil(len(texto) * self._tokens_por_mil_caracteres / MIL)
