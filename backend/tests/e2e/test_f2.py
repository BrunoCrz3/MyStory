"""Cierre de F2: un capítulo defectuoso a propósito vuelve al redactor, se corrige y se acepta,
y la traza de esa generación tiene los scores de los validadores y los seis del judge.

Por HTTP de principio a fin, con la app en proceso y los dos dobles: lo que se afirma está en
el `RegistroTrazas`, que no cruza a otro proceso.
"""

from __future__ import annotations

from typing import Any

from app.commons.llm import Peticion
from tests.conftest import Instancia
from tests.dobles.guiones import corregido, guion_completo, numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_orquestador import esperar

DEFECTUOSO = 3
HOOKS = [
    "schema_valido",
    "palabras_prohibidas",
    "longitud",
    "nombres_exactos",
    "consistencia_factica",
    "cumplimiento_brief",
    "reglas_mundo",
    "calidad_prosa",
    "integridad_pov",
]
JUDGE = [
    "consistencia_factica",
    "adecuacion_tono",
    "cierre_arco",
    "coherencia_personajes",
    "ritmo",
    "personalizacion_natural",
]
GATE = ["estructura_edicion", "elementos_obligatorios", "cierre_arco"]


def test_un_capitulo_defectuoso_vuelve_al_redactor_se_corrige_y_se_acepta(
    instancia: Instancia,
) -> None:
    modelo = instancia.modelo
    guion_completo(modelo)
    vistos: dict[int, int] = {}

    def redactor(p: Peticion) -> dict[str, str]:
        n = numero_de_la_tarea(p)
        vistos[n] = vistos.get(n, 0) + 1
        # El primer borrador del capítulo 3 se queda corto.
        return borrador(400) if n == DEFECTUOSO and vistos[n] == 1 else redactar(p)

    def editor(p: Peticion) -> dict[str, Any]:
        # Y el editor tampoco llega: el capítulo vuelve al redactor con el informe.
        return corregido(400)

    modelo.por_defecto["redactor"] = redactor
    modelo.por_defecto["editor"] = editor

    c = instancia.cliente
    novela = c.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = c.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(c, novela, gid, lambda g: g["es_terminal"], limite=120)
    assert g["estado"] == "Publicada", g
    assert vistos[DEFECTUOSO] == 2 and all(vistos[n] == 1 for n in vistos if n != DEFECTUOSO)

    capitulos = c.get(f"/novelas/{novela}/versiones/1/capitulos").json()
    tercero = capitulos[DEFECTUOSO - 1]
    assert tercero["estado"] == "Aceptado" and tercero["palabras"] >= 1000

    # Todos los scores son de la traza de esta generación.
    [traza] = [t.traza for t in instancia.trazas.trazas if t.sesion == novela]
    scores = [s for s in instancia.trazas.scores if s.traza == traza]
    assert len(scores) == len(instancia.trazas.scores)
    nombres = {s.nombre for s in scores}
    assert set(HOOKS) | set(JUDGE) | set(GATE) <= nombres

    # El capítulo 3 dejó su longitud suspendida dos veces (redactor y editor) y luego aprobada.
    longitudes = [s.valor for s in scores if s.nombre == "longitud"]
    assert longitudes.count(0.0) == 2 and longitudes.count(1.0) == 10
    # Los seis criterios del judge, con su justificación, en cada borrador que llegó a juicio.
    # Diez capítulos, más el corto del 3 y su corrección; `consistencia_factica` la emite
    # también el hook, y `cierre_arco`, también el último capítulo (TO-056) y el gate.
    for criterio in [
        "adecuacion_tono",
        "coherencia_personajes",
        "ritmo",
        "personalizacion_natural",
    ]:
        del_judge = [s for s in scores if s.nombre == criterio]
        assert len(del_judge) == 12
        assert all(s.comentario and s.comentario.startswith("Justificación") for s in del_judge)
    assert len([s for s in scores if s.nombre == "cierre_arco"]) == 12 + 1 + 1
