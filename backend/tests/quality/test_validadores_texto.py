"""Hook de capítulo sobre el texto: `calidad_prosa` e `integridad_pov`, y los siete
validadores del hook en paralelo y fuera del pool (RF-QUA-02; O-46…O-52, O-54)."""

from __future__ import annotations

import threading
from collections.abc import Callable

import pytest

from app.commons.config import cargar_config
from app.quality import service as quality
from app.quality.models import ResultadoValidador
from app.quality.registro import comprobar
from app.quality.validadores.texto import calidad_prosa, integridad_pov
from tests.arquitectura.comprobadores import RAIZ_REPO

CONFIG = cargar_config(RAIZ_REPO / "config")

# Prosa variada y sin tics: frases de longitudes distintas, sin muletillas ni clichés.
_FRASES_LIMPIAS = [
    "Marta bajó al puerto antes de que abrieran las lonjas.",
    "Olía a gasóleo y a sal.",
    "Tomás ya estaba allí, sentado sobre un cabo enrollado, con las manos manchadas de brea y "
    "la gorra echada hacia atrás como cuando eran críos y esperaban a los barcos del alba.",
    "Se saludaron sin palabras.",
    "La marea subía despacio por la rampa, lamiendo el hormigón verdoso que nadie limpiaba desde "
    "el invierno.",
    "Ella contó los amarres.",
    "Faltaba uno, el de siempre, el que su padre había pintado de azul un verano de viento.",
    "Una gaviota protestó desde el tejado de la cofradía y luego calló.",
]
_PALABRAS = [
    "ancla",
    "bahía",
    "barca",
    "boya",
    "cabo",
    "casco",
    "cubierta",
    "dársena",
    "espuma",
    "estela",
    "faro",
    "gaviota",
    "grúa",
    "lancha",
    "lonja",
    "malecón",
    "marea",
    "mástil",
    "muelle",
    "niebla",
    "orilla",
    "proa",
    "quilla",
    "rada",
    "red",
    "remo",
    "roca",
    "salitre",
    "timón",
    "vela",
    "viento",
]


def limpio(frases: int = 120) -> str:
    """Un capítulo sin ecos: cada frase lleva una palabra distinta que rompe los n-gramas."""
    salida = []
    for i in range(frases):
        palabras = _FRASES_LIMPIAS[i % len(_FRASES_LIMPIAS)].split()
        # Una marca única cada tres palabras: ningún 5-grama se repite.
        for k in range(len(palabras) - 1, 0, -3):
            palabras.insert(k, f"{_PALABRAS[(i + k) % len(_PALABRAS)]}{i}x{k}")
        salida.append(" ".join(palabras))
    return " ".join(salida)


def _metrica(r: ResultadoValidador, clave: str) -> bool:
    """True si la métrica `clave` aparece entre los defectos."""
    return any(clave in d.descripcion for d in r.defectos)


def test_un_capitulo_limpio_pasa_calidad_prosa() -> None:
    r = calidad_prosa(CONFIG, limpio(), anteriores=[])
    comprobar(r)
    assert r.pasa and r.valor == 1.0, r.detalle


@pytest.mark.parametrize(
    ("inyectar", "clave"),
    [
        (lambda t: t + (" y el viento del norte soplaba fuerte." * 4), "eco"),
        (lambda t: ("De repente, " * 20) + t, "muletillas"),
        (lambda t: ("Un escalofrío le recorrió la espalda. " * 12) + t, "clichés"),
        (lambda t: ("Lentamente, suavemente, tranquilamente. " * 20) + t, "adverbios"),
        (lambda t: "Una frase de siete palabras aquí. " * 150, "longitud de frase"),
        (lambda t: "## Capítulo 3\n\n**Aquí tienes** el capítulo.\n\n" + t, "metatexto"),
        (lambda t: t.rstrip(". ") + " y entonces ella", "truncado"),
    ],
)
def test_un_defecto_inyectado_por_metrica_de_prosa(
    inyectar: Callable[[str], str], clave: str
) -> None:
    r = calidad_prosa(CONFIG, inyectar(limpio()), anteriores=[])
    assert _metrica(r, clave), (clave, r.detalle)
    assert r.valor < 1.0


def test_el_eco_entre_capitulos_cuenta_los_anteriores() -> None:
    comun = "la vieja campana de la cofradía sonó tres veces sobre el agua"
    texto = limpio() + f" {comun}."
    anteriores = [f"Aquella tarde {comun}.", f"Por la noche {comun}."]
    assert not _metrica(calidad_prosa(CONFIG, texto, anteriores=[]), "eco")
    assert _metrica(calidad_prosa(CONFIG, texto, anteriores=anteriores), "eco")


def test_un_cambio_de_persona_narrativa_suspende_integridad_pov() -> None:
    primera = "Yo bajé al puerto aquella mañana. Mi hermano me esperaba junto a las barcas. "
    texto = limpio(40) + " " + primera * 10
    r = integridad_pov(
        CONFIG, texto, persona="tercera", tiempo_verbal="pasado", focalizacion="interna",
        pov="Marta", personajes=["Marta", "Tomás"],
    )  # fmt: skip
    comprobar(r)
    assert not r.pasa and r.valor < CONFIG.umbrales.calidad.integridad_pov  # type: ignore[operator]
    assert any("primera persona" in d.descripcion for d in r.defectos)


def test_el_dialogo_puede_cambiar_de_persona_y_la_narracion_limpia_pasa() -> None:
    dialogo = "\n—Yo no me voy de aquí —dijo Tomás.\n«Tú siempre vuelves», pensó ella.\n"
    texto = limpio(60) + dialogo + limpio(20)
    r = integridad_pov(
        CONFIG, texto, persona="tercera", tiempo_verbal="pasado", focalizacion="interna",
        pov="Marta", personajes=["Marta", "Tomás"],
    )  # fmt: skip
    assert r.pasa and r.valor == 1.0, r.detalle


def test_tiempo_presente_declarado_y_narracion_en_pasado() -> None:
    texto = (
        "Marta baja al puerto. Tomás la espera. " * 20 + "Marta llegó tarde y miró el mar. " * 20
    )
    r = integridad_pov(
        CONFIG, texto, persona="tercera", tiempo_verbal="presente", focalizacion="interna",
        pov="Marta", personajes=["Marta", "Tomás"],
    )  # fmt: skip
    assert not r.pasa and any("pasado" in d.descripcion for d in r.defectos)


def test_acceso_mental_de_quien_no_es_el_pov() -> None:
    texto = limpio(30) + " Tomás pensó que ella nunca volvería. " * 8
    r = integridad_pov(
        CONFIG, texto, persona="tercera", tiempo_verbal="pasado", focalizacion="interna",
        pov="Marta", personajes=["Marta", "Tomás"],
    )  # fmt: skip
    assert any("Tomás" in d.descripcion and "focalización" in d.descripcion for d in r.defectos)


@pytest.mark.anyio
async def test_los_validadores_del_hook_corren_a_la_vez() -> None:
    # Siete tareas que solo terminan si las siete están dentro a la vez: en serie, la barrera
    # expira y la prueba falla.
    barrera = threading.Barrier(7, timeout=5)

    def tarea(i: int) -> Callable[[], ResultadoValidador]:
        def correr() -> ResultadoValidador:
            barrera.wait()
            return ResultadoValidador(
                nombre=f"v{i}", tipo="programático", punto="hook de capítulo",
                pasa=True, valor=1.0, cierra_el_paso=True, detalle="",
            )  # fmt: skip

        return correr

    resultados = await quality.en_paralelo([tarea(i) for i in range(7)])
    assert [r.nombre for r in resultados] == [f"v{i}" for i in range(7)]


@pytest.mark.anyio
async def test_el_hook_ejecuta_siete_validadores_en_orden() -> None:
    entrada = quality.EntradaHookCapitulo(titulo="t", texto=limpio(), nombres=["Marta"])
    resultados = await quality.hook_capitulo(CONFIG, entrada)
    assert [r.nombre for r in resultados] == [
        "longitud", "nombres_exactos", "consistencia_factica", "cumplimiento_brief",
        "reglas_mundo", "calidad_prosa", "integridad_pov",
    ]  # fmt: skip
