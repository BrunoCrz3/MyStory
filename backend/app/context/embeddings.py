"""Embeddings locales.

**Local** porque el corpus es la novela inedita del autor y no tiene por que
salir de la maquina. **Multilingue** porque el vocabulario del mundo —terminos
canonicos, neologismos del novum— no se parece al de ningun corpus de
entrenamiento general.

El modelo, su version y su dimension se declaran en `config/thresholds.yaml`, no
aqui. Y el vector que sale se comprueba contra la dimension declarada antes de
devolverlo: un modelo que cambia de tamano sin que nadie lo note produce una
recuperacion que devuelve lo que no toca.

El modelo se carga la primera vez que se pide un vector, no al importar. Son
gigas de pesos: un `import` no deberia descargarlos, y un arranque que solo
sirve consultas de canon no tiene por que pagarlos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.commons.config import Umbrales
from app.commons.errores import ConfiguracionInvalida, DimensionDeEmbeddingInvalida

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbebedorLocal:
    def __init__(self, umbrales: Umbrales) -> None:
        if umbrales.embeddings.version is None or umbrales.embeddings.dimension is None:
            raise ConfiguracionInvalida(
                "`embeddings.version` y `embeddings.dimension` son obligatorias: sin "
                "artefacto ni tamano declarados no se puede detectar un cambio de modelo"
            )
        self._artefacto = umbrales.embeddings.version
        self._dimension = umbrales.embeddings.dimension
        self._modelo: SentenceTransformer | None = None

    def _cargar(self) -> SentenceTransformer:
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer

            self._modelo = SentenceTransformer(self._artefacto)
        return self._modelo

    def vectorizar(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        matriz = self._cargar().encode(textos, normalize_embeddings=True)
        vectores = [[float(valor) for valor in fila] for fila in matriz]
        for vector in vectores:
            if len(vector) != self._dimension:
                raise DimensionDeEmbeddingInvalida(
                    f"el modelo {self._artefacto} devuelve vectores de {len(vector)} "
                    f"dimensiones y la configuracion declara {self._dimension}"
                )
        return vectores
