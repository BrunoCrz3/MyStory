"""Cierre de F4: «el perro se llama Nala» por HTTP de principio a fin.

Sobre una novela publicada, el cambio de un hecho produce la versión 2 con los capítulos que
usan ese hecho reescritos, **el resto idénticos byte a byte** —comparando el texto que sirve
la API—, y la versión 1 consultable entera con su hash original.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from app.commons.llm import Peticion
from tests.canon.test_hechos_por_version import _extraer, publicada_con_uso
from tests.conftest import Instancia, ValidarContrato
from tests.dobles.guiones import capitulo_aceptado_de, guion_completo, numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_orquestador import esperar
from tests.process.test_regeneracion_promesas import alias, cierre_programatico

NUEVO = "El perro se llama Nala"


def _redactor(p: Peticion) -> dict[str, str]:
    if NUEVO in p.mensajes[0].contenido:
        n = numero_de_la_tarea(p)
        return borrador(titulo=f"Capítulo {n}: Nala", extra=f"{NUEVO}, y movió la cola.")
    return redactar(p)


def _textos(i: Instancia, novela: str, version: int) -> dict[int, str]:
    capitulos = i.cliente.get(f"/novelas/{novela}/versiones/{version}/capitulos").json()
    return {c["numero"]: c["texto"] for c in capitulos}


def test_un_cambio_de_hecho_produce_la_version_2_sin_tocar_el_resto(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    c = instancia.cliente
    novela = publicada_con_uso(instancia)
    v1_antes: dict[str, Any] = c.get(f"/novelas/{novela}/versiones/1").json()
    textos_v1 = _textos(instancia, novela, 1)
    assert all(NUEVO not in t for t in textos_v1.values())

    hechos = c.get(f"/novelas/{novela}/versiones/1/hechos").json()
    del_dos = next(h for h in hechos if h["capitulo_establece"] == 2)
    r = c.post(
        f"/novelas/{novela}/solicitudes-cambio",
        json={"hecho_id": del_dos["hecho_id"], "enunciado_nuevo": NUEVO, "capitulo_origen": 2},
    )
    validar_contra_contrato(r, "crearSolicitudCambio")
    solicitud = r.json()
    assert solicitud["analisis_impacto"]["capitulos_afectados"] == [2, 7]

    instancia.modelo.por_defecto["redactor"] = _redactor
    r = c.post(f"/novelas/{novela}/solicitudes-cambio/{solicitud['solicitud_id']}/confirmacion")
    validar_contra_contrato(r, "confirmarSolicitudCambio")
    assert r.status_code == 202
    gid = r.json()["generacion_id"]
    g = esperar(c, novela, gid, lambda g: g["es_terminal"], limite=120)
    assert g["estado"] == "Publicada", g
    assert g["tipo"] == "dirigida" and g["version_resultante"] == 2

    versiones = c.get(f"/novelas/{novela}/versiones").json()
    validar_contra_contrato(c.get(f"/novelas/{novela}/versiones"), "listarVersiones")
    assert sorted(v["version"] for v in versiones) == [1, 2]
    [v2] = [v for v in versiones if v["version"] == 2]
    assert v2["capitulos_modificados"] == [2, 7] and v2["version_anterior"] == 1

    textos_v2 = _textos(instancia, novela, 2)
    for n in range(1, 11):
        if n in (2, 7):
            assert textos_v2[n] != textos_v1[n] and NUEVO in textos_v2[n]
        else:
            assert textos_v2[n] == textos_v1[n]  # idénticos byte a byte

    # La versión 1, entera y con su hash de siempre.
    v1_despues = c.get(f"/novelas/{novela}/versiones/1").json()
    assert v1_despues["hash"] == v1_antes["hash"]
    assert _textos(instancia, novela, 1) == textos_v1
    hechos_v1 = c.get(f"/novelas/{novela}/versiones/1/hechos").json()
    assert del_dos["enunciado"] in [h["enunciado"] for h in hechos_v1]
    hechos_v2 = c.get(f"/novelas/{novela}/versiones/2/hechos").json()
    assert NUEVO in [h["enunciado"] for h in hechos_v2]
    assert del_dos["enunciado"] not in [h["enunciado"] for h in hechos_v2]

    r = c.get(f"/novelas/{novela}/solicitudes-cambio/{solicitud['solicitud_id']}")
    assert r.json()["estado"] == "aplicada" and r.json()["version_resultante"] == 2
    assert c.get(f"/novelas/{novela}").json()["version_vigente"] == 2


PROMESA = "¿Volverá el Alondra a navegar?"
INTRUSA = "¿Qué esconde Nala bajo la barca?"
RETOMA = "Ondina volvió a preguntarse si el Alondra navegaría."
DEVUELTO = "El borrador anterior no pasó la validación"


def test_una_regeneracion_que_tiende_a_abrir_una_promesa_nueva_la_corrige_y_publica(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    """El caso de la regeneración real 2 (P44): el capítulo reescrito abre una promesa que
    ningún capítulo no afectado paga. Ahora vuelve a su redactor como intento fallido, el
    redactor retoma la promesa que el capítulo ya abría, y la versión 2 se publica."""
    c = instancia.cliente
    guion_completo(instancia.modelo)
    v1: list[Any] = [partial(_extraer, n=n) for n in range(1, 11)]
    v1[1] = partial(_extraer, n=2, promesas=[PROMESA])
    v1[6] = partial(_extraer, n=7, usados=["H2"])
    v1[8] = lambda p: _extraer(p, n=9, pagadas=[alias(p, PROMESA)])
    instancia.modelo.encolar("extractor", *v1)
    novela = c.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = c.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    assert esperar(c, novela, gid, lambda g: g["es_terminal"])["estado"] == "Publicada"
    textos_v1 = _textos(instancia, novela, 1)

    def redactor(p: Peticion) -> dict[str, str]:
        contenido = p.mensajes[0].contenido
        if NUEVO not in contenido:
            return redactar(p)
        n = numero_de_la_tarea(p)
        extra = f"{NUEVO}, y movió la cola en el capítulo {n}."
        if "promesa" in contenido.partition(DEVUELTO)[2]:
            extra += " " + RETOMA
        return borrador(titulo=f"Capítulo {n}: Nala", extra=extra)

    def extractor(p: Peticion) -> dict[str, Any]:
        texto = capitulo_aceptado_de(p)
        if "en el capítulo 2." not in texto:
            return _extraer(p, n=107)
        if RETOMA not in texto:
            # Lo que se vio en real: una promesa nueva en vez de la que el capítulo ya abría.
            return _extraer(p, n=102, promesas=[INTRUSA])
        return _extraer(p, n=102, reabiertas=[alias(p, PROMESA)])

    hechos = c.get(f"/novelas/{novela}/versiones/1/hechos").json()
    del_dos = next(h for h in hechos if h["capitulo_establece"] == 2)
    solicitud = c.post(
        f"/novelas/{novela}/solicitudes-cambio",
        json={"hecho_id": del_dos["hecho_id"], "enunciado_nuevo": NUEVO, "capitulo_origen": 2},
    ).json()
    instancia.modelo.por_defecto["redactor"] = redactor
    instancia.modelo.por_defecto["extractor"] = extractor
    r = c.post(f"/novelas/{novela}/solicitudes-cambio/{solicitud['solicitud_id']}/confirmacion")
    validar_contra_contrato(r, "confirmarSolicitudCambio")
    g = esperar(c, novela, r.json()["generacion_id"], lambda g: g["es_terminal"], limite=120)
    assert g["estado"] == "Publicada" and g["version_resultante"] == 2, g

    reescrituras_del_2 = [
        p
        for p in instancia.modelo.peticiones
        if p.rol == "redactor" and numero_de_la_tarea(p) == 2 and NUEVO in p.mensajes[0].contenido
    ]
    assert len(reescrituras_del_2) == 2
    assert INTRUSA in reescrituras_del_2[1].mensajes[0].contenido.partition(DEVUELTO)[2]
    # El 2 reescrito suspende el cierre del arco una vez y lo pasa después; el gate, también.
    assert cierre_programatico(instancia.trazas)[-4:] == [0.0, 1.0, 1.0, 1.0]

    textos_v2 = _textos(instancia, novela, 2)
    assert RETOMA in textos_v2[2] and INTRUSA not in textos_v2[2]
    assert all(textos_v2[n] == textos_v1[n] for n in range(1, 11) if n not in (2, 7))
    assert _textos(instancia, novela, 1) == textos_v1
