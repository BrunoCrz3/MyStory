"""`temas_excluidos` (O-21, PO-2, D-13): un tema que el comprador vetó no aparece, aunque
ninguna palabra prohibida lo nombre.

Es un juicio semántico: lo decide el judge tema a tema, con la cita. Aquí se cuenta: solo
los temas que el brief excluye, y solo los que el judge dice que aparecen. Cuenta hasta
`calidad.temas_excluidos`, que es cero, y cierra el paso siempre.
"""

from __future__ import annotations

from app.commons.config import Config
from app.commons.texto import plano
from app.quality.models import ContextoJudge, Defecto, ResultadoValidador, TemaExcluidoVisto


def temas_excluidos(
    config: Config, vistos: list[TemaExcluidoVisto], contexto: ContextoJudge
) -> ResultadoValidador:
    excluidos = {plano(t).strip() for t in contexto.temas_excluidos}
    aparecen = [v for v in vistos if v.aparece and plano(v.tema).strip() in excluidos]
    cuenta = len(aparecen)
    return ResultadoValidador(
        nombre="temas_excluidos",
        tipo="semántico",
        punto="rol editor",
        pasa=cuenta <= config.umbrales.calidad.temas_excluidos,
        valor=float(cuenta),
        cierra_el_paso=True,
        detalle="; ".join(f"«{v.tema}»: «{v.fragmento}»" for v in aparecen)
        or "ningún tema excluido aparece",
        defectos=[
            Defecto(
                dimension="temas_excluidos",
                gravedad="alta",
                descripcion=f"aparece el tema excluido «{v.tema}»: «{v.fragmento}»",
            )
            for v in aparecen
        ],
    )
