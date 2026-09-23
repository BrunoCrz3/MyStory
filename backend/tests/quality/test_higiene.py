"""H5 · prueba 1 — A-47, RF-QUA-06.

Va primera de todo el hito porque es determinista, vale milisegundos y protege
el punto unico de promocion. Sin ella, «Aqui tienes la escena» acaba en el canon
y en `training_samples`.

Corre **antes** de la critica y sin modelo: que el critico gaste una llamada en
decir que el texto empieza por un metatexto es caro y llega tarde.

El punto ciego declarado se asume: no cubre el metatexto escrito como prosa
narrativa.
"""

from __future__ import annotations

import pytest

from app.commons.db.conexion import Conexion
from app.quality import service as calidad
from app.quality.higiene import Fallo
from tests.quality import fabrica

LIMPIO = (
    "Ilia cruzo el vado al anochecer. El agua le llegaba a la cintura y no miro "
    "atras ni una vez. En la orilla, la puerta seguia abierta."
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        (f"Aqui tienes la escena que me pediste:\n\n{LIMPIO}", Fallo.METATEXTO),
        (f"[Nota: he supuesto que Ilia ya conocia el vado]\n{LIMPIO}", Fallo.METATEXTO),
        ("Lo siento, no puedo continuar con esta escena.", Fallo.RECHAZO),
        ("Como modelo de lenguaje, no me es posible escribir eso.", Fallo.RECHAZO),
        (f"{LIMPIO} Y entonces ella se giro y", Fallo.TRUNCAMIENTO),
        (f"{LIMPIO}\n[NOMBRE_DEL_PERSONAJE] entro despues.", Fallo.PLACEHOLDER),
        (f"{LIMPIO}\nTODO: rematar el dialogo.", Fallo.PLACEHOLDER),
        ("## Escena 4\n\n**Ilia** cruzo el vado.\n\n- llego\n- volvio", Fallo.FORMATO),
        (
            "She crossed the ford at dusk and did not look back at all, not even once.",
            Fallo.IDIOMA,
        ),
    ],
)
def test_un_borrador_con_metatexto_del_modelo_no_entra_al_ciclo(
    base: Conexion, texto: str, esperado: Fallo
) -> None:
    """Y sus hermanas: rechazo, truncamiento, placeholder, idioma y formato."""
    mundo = fabrica.mundo_criticable(base)
    resultado = calidad.puerta_de_higiene(base, fabrica.umbrales(), texto, mundo.escena_id)

    assert not resultado.pasa
    assert esperado in resultado.fallos


def test_un_borrador_limpio_pasa_la_puerta(base: Conexion) -> None:
    mundo = fabrica.mundo_criticable(base)
    resultado = calidad.puerta_de_higiene(base, fabrica.umbrales(), LIMPIO, mundo.escena_id)

    assert resultado.pasa, resultado.fallos
    assert resultado.fallos == []


def test_la_longitud_no_cierra_el_paso_mientras_su_umbral_siga_en_null(
    base: Conexion,
) -> None:
    """`higiene.desviacion_longitud_escena` es `[decision]` y sigue en `null`.

    La puerta es booleana salvo en la longitud, que necesita margen. Sin margen
    declarado la comprobacion no decide: se reporta como no evaluable y no
    bloquea. Inventar el numero seria peor que no medirlo.
    """
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.umbrales()
    assert umbrales.higiene.desviacion_longitud_escena is None

    resultado = calidad.puerta_de_higiene(base, umbrales, LIMPIO * 200, mundo.escena_id)

    assert resultado.pasa
    assert Fallo.LONGITUD in resultado.no_evaluables


def test_con_umbral_declarado_la_longitud_si_cierra_el_paso(base: Conexion) -> None:
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.con_umbral_de_longitud(fabrica.umbrales(), 0.2)

    corto = calidad.puerta_de_higiene(base, umbrales, "Cruzo.", mundo.escena_id)
    assert not corto.pasa
    assert Fallo.LONGITUD in corto.fallos
    assert corto.no_evaluables == []


def test_la_puerta_corre_antes_que_la_critica_y_la_bloquea(base: Conexion) -> None:
    """A-47: el punto es el sitio, no solo el coste."""
    mundo = fabrica.mundo_criticable(base)
    sucio = f"Aqui tienes la escena:\n\n{LIMPIO}"

    with pytest.raises(calidad.errores.BorradorNoHigienico):
        calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo, texto=sucio))

    assert calidad.informes_de(base, mundo.escena_id) == [], "no queda informe de un sucio"
