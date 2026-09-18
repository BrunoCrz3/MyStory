"""Control determinista de la repeticion: n-gramas, frases ya usadas,
muletillas, tipo de apertura y primeras/ultimas palabras.

Aqui no hay ningun juicio sobre la prosa: solo cadenas, recuentos y umbrales.
Todos los umbrales salen de config.json -> validacion. Ver SPEC seccion 12.

Este script NUNCA devuelve incidencias bloqueantes: la repeticion se corrige con
un parche, no tirando el capitulo.

Codigos de salida: 0 limpio; 1 hay mayores o menores; 3 error de ejecucion.
"""

import argparse
import re
import statistics
from collections import Counter

import nucleo

MINIMO_PALABRAS_MULETILLA = 200
VENTANA_BORDES = 6
COINCIDENCIAS_BORDE = 4

# Monotonia sintactica (SPEC 12.8). Marcas con las que puede abrir una linea de
# dialogo: todas cuentan como la misma forma de apertura.
MARCAS_DIALOGO = ('"', "«", "—", "–", "-", "“")

# Un corte de frase es un punto, interrogacion, exclamacion o puntos
# suspensivos seguidos de espacio. Una linea puede llevar varias frases.
_CORTE_FRASE = re.compile(r"(?<=[.?!…])\s+")


def _tokens(n: int) -> list:
    return nucleo.normalizar(nucleo.cuerpo_capitulo(n)).split()


def _motivos_exentos() -> set:
    """Palabras de '## Motivos recurrentes' del canon: repeticion deliberada."""
    secciones = nucleo.secciones_canon(nucleo.leer_canon())
    texto = secciones.get("Motivos recurrentes", "")
    return set(nucleo.normalizar(texto).split())


def _tipo_apertura(n: int, estado: dict) -> str:
    lineas = nucleo.lineas_capitulo(n)
    if not lineas:
        return "descripcion_ambiente"
    primera = lineas[0].lstrip()
    if primera[:1] in ('"', "«", "—", "–", "-", "“"):
        return "dialogo"
    inicio = nucleo.normalizar(primera)
    for entidad in estado.get("entidades", []):
        if not isinstance(entidad, dict):
            continue      # lo denuncia estado_mal_formado(); aqui se ignora
        nombres = [entidad.get("nombre", "")] + list(entidad.get("alias", []))
        for nombre in nombres:
            clave = nucleo.normalizar(nombre)
            if clave and inicio.startswith(clave):
                return "accion"
    return "descripcion_ambiente"


def frases_de(lineas: list) -> list:
    """Parte las lineas en frases. Una linea puede llevar mas de una."""
    sueltas = []
    for linea in lineas:
        for trozo in _CORTE_FRASE.split(linea):
            trozo = trozo.strip()
            if trozo:
                sueltas.append(trozo)
    return sueltas


def _forma_de_apertura(linea: str) -> str:
    """Con que forma abre una linea.

    Tres clases, y ninguna necesita analisis gramatical: `dialogo` si abre con
    una marca de dialogo; la propia palabra si la primera es funcional (el, la,
    en, cuando...), porque ahi la forma ES la palabra; y `contenido` si abre con
    cualquier palabra con significado, que es como abren todas las frases que
    empiezan por el nombre del personaje o por el verbo.
    """
    if linea[:1] in MARCAS_DIALOGO:
        return "dialogo"
    palabras = nucleo.normalizar(linea).split()
    if not palabras:
        return "vacia"
    return palabras[0] if palabras[0] in nucleo.vacias() else "contenido"


def monotonia_sintactica(lineas: list) -> dict:
    """Cuanto se parecen entre si las frases POR SU FORMA, no por sus palabras.

    0 es maxima variedad y 1 maxima monotonia. Es la media de tres componentes,
    que se devuelven siempre por separado porque una mejora que venga de uno
    solo no es una mejora del ritmo:

      apertura     Cuanto pesa la forma de apertura mas repetida. 0 si todas
                   las lineas abren distinto, 1 si todas abren igual.
      puntuacion   Lineas con punto y coma o con raya intercalada, sobre el
                   total. La raya inicial no cuenta: eso es dialogo, no un
                   inciso, y penalizarla empujaria a escribir sin dialogo.
      uniformidad  1 menos el coeficiente de variacion de la longitud de las
                   frases, recortado a [0, 1]. Todas las frases igual de largas
                   da 1; una mezcla de frases cortas y largas se acerca a 0.

    Funcion pura sobre una lista de lineas: no lee disco ni el estado. Asi la
    misma cuenta sirve para un capitulo en curso y para una novela archivada.
    No dispara incidencias nunca. Ver SPEC seccion 12.8.
    """
    total = len(lineas)
    if not total:
        return {"monotonia_sintactica": 0.0, "frases": 0,
                "componentes": {"apertura": 0.0, "puntuacion": 0.0,
                                "uniformidad": 0.0}}

    formas = [_forma_de_apertura(linea) for linea in lineas]
    repetida = max(formas.count(f) for f in set(formas))
    apertura = round((repetida - 1) / (total - 1), 4) if total > 1 else 0.0

    marcadas = 0
    for linea in lineas:
        inciso = ("—" in linea[1:] or "–" in linea[1:]) and                  linea[:1] not in ("—", "–")
        if ";" in linea or inciso:
            marcadas += 1
    puntuacion = round(marcadas / total, 4)

    largos = [len(nucleo.palabras(f)) for f in frases_de(lineas)]
    largos = [x for x in largos if x]
    media = statistics.fmean(largos) if largos else 0.0
    if len(largos) > 1 and media:
        variacion = statistics.pstdev(largos) / media
        uniformidad = round(max(0.0, 1.0 - min(1.0, variacion)), 4)
    else:
        # Con una sola frase no hay dispersion que medir, y decir que es
        # perfectamente uniforme seria inventarse un dato.
        uniformidad = 0.0

    return {
        "monotonia_sintactica": round(
            (apertura + puntuacion + uniformidad) / 3, 4),
        "frases": len(largos),
        "componentes": {"apertura": apertura, "puntuacion": puntuacion,
                        "uniformidad": uniformidad},
    }


def _coincidencias_en_orden(a: list, b: list) -> int:
    return sum(1 for x, y in zip(a, b) if x == y)


def analizar(n: int, cfg: dict, estado: dict) -> dict:
    val = cfg["validacion"]
    tam_ngrama = val["ngrama"]
    umbral_solape = val["max_solape_ngramas"]
    umbral_muletilla = val["max_muletilla_por_mil"]
    max_aperturas = val["max_aperturas_del_mismo_tipo"]

    incidencias = []
    tokens = _tokens(n)
    anteriores = [c for c in nucleo.capitulos_existentes() if c < n]

    # 1. Solape de n-gramas con todos los capitulos anteriores.
    propios = nucleo.ngramas(tokens, tam_ngrama)
    previos = set()
    for c in anteriores:
        previos |= nucleo.ngramas(_tokens(c), tam_ngrama)
    repetidos = sorted(propios & previos)
    solape = round(len(repetidos) / len(propios), 4) if propios else 0.0
    if propios and solape > umbral_solape:
        incidencias.append({
            "severidad": "mayor", "tipo": "solape_ngramas",
            "detalle": f"solape {solape} supera el umbral {umbral_solape}",
            "ejemplos": [" ".join(g) for g in repetidos[:5]],
        })

    # 2. Frases ya usadas, buscadas como subcadena normalizada.
    #
    # `frases_usadas` es una lista plana sin capitulo de origen (SPEC 6.3), asi
    # que al revalidar un capitulo YA ARCHIVADO sus propias frases casarian
    # contra si mismo. Reciclar es repetir algo de un capitulo ANTERIOR, de modo
    # que la frase solo cuenta si ademas aparece en el texto de alguno de ellos.
    # No hace falta tocar el esquema del estado: los capitulos estan en disco.
    normalizado = " ".join(tokens)
    texto_anterior = " ".join(" ".join(_tokens(c)) for c in anteriores)
    recicladas = []
    for frase in estado.get("frases_usadas", []):
        clave = nucleo.normalizar(frase)
        if clave and clave in normalizado and clave in texto_anterior:
            recicladas.append(frase)
            ancla = next((ln for ln in nucleo.lineas_capitulo(n)
                          if clave in nucleo.normalizar(ln)), "")
            incidencias.append({
                "severidad": "mayor", "tipo": "frase_reciclada",
                "detalle": frase, "ancla": ancla,
            })

    # 3. Muletillas. Por debajo de 200 palabras la metrica no se evalua.
    crudas = nucleo.palabras(nucleo.cuerpo_capitulo(n))
    total_palabras = len(crudas)
    exentas = _motivos_exentos() | nucleo.vacias()
    muletilla_max = None
    if total_palabras < MINIMO_PALABRAS_MULETILLA:
        muletilla_max = {"estado": "no_aplica",
                         "detalle": f"{total_palabras} palabras, minimo "
                                    f"{MINIMO_PALABRAS_MULETILLA}"}
    else:
        cuenta = Counter(p for p in (nucleo.normalizar(w) for w in crudas)
                         if len(p) >= 5 and p not in exentas)
        for palabra, veces in cuenta.most_common():
            por_mil = round(veces * 1000 / total_palabras, 1)
            if muletilla_max is None:
                muletilla_max = {"palabra": palabra, "por_mil": por_mil}
            # Una muletilla es un tic por repeticion: con una sola aparicion
            # no lo es, por mucho que la frecuencia por mil supere el umbral.
            # Sin esta condicion, un capitulo de entre 200 y 333 palabras
            # marcaria como muletilla cada palabra de contenido que contiene.
            if veces >= 2 and por_mil > umbral_muletilla:
                incidencias.append({
                    "severidad": "menor", "tipo": "muletilla",
                    "detalle": (f"'{palabra}' aparece {veces} veces "
                                f"({por_mil} por mil, umbral {umbral_muletilla})"),
                })
        if muletilla_max is None:
            muletilla_max = {"palabra": None, "por_mil": 0.0}

    # 4. Tipo de apertura frente a los ya registrados en el estado.
    tipo = _tipo_apertura(n, estado)
    previas = [a for a in estado.get("aperturas", [])
               if isinstance(a, dict)
               and a.get("tipo") == tipo and a.get("capitulo") != n]
    if previas and len(previas) + 1 > max_aperturas:
        cap = previas[0].get("capitulo")
        incidencias.append({
            "severidad": "mayor", "tipo": "apertura_repetida",
            "detalle": (f"El tipo '{tipo}' ya se uso en el capitulo {cap} "
                        f"y el maximo permitido es {max_aperturas}."),
        })

    # 5. Primeras y ultimas 6 palabras frente a las de los capitulos anteriores.
    primeras = tokens[:VENTANA_BORDES]
    ultimas = tokens[-VENTANA_BORDES:]
    for c in anteriores:
        otros = _tokens(c)
        if _coincidencias_en_orden(primeras, otros[:VENTANA_BORDES]) >= COINCIDENCIAS_BORDE:
            incidencias.append({
                "severidad": "menor", "tipo": "apertura_repetida_literal",
                "detalle": (f"las primeras palabras coinciden con las del "
                            f"capitulo {c}: '{' '.join(primeras)}'"),
            })
        if _coincidencias_en_orden(ultimas, otros[-VENTANA_BORDES:]) >= COINCIDENCIAS_BORDE:
            incidencias.append({
                "severidad": "menor", "tipo": "cierre_repetido",
                "detalle": (f"las ultimas palabras coinciden con las del "
                            f"capitulo {c}: '{' '.join(ultimas)}'"),
            })

    # 6. Monotonia y diversidad. Estas dos no disparan incidencias: son
    # metricas de serie, pensadas para comparar tiradas entre si en Langfuse.
    # Ver SPEC seccion 12.8.
    #
    #   diversidad  0..1, mas alto es mejor: n-gramas distintos sobre posiciones.
    #   monotonia   0..1, mas alto es PEOR: media de los tres componentes.
    posiciones = max(len(tokens) - tam_ngrama + 1, 0)
    diversidad = round(len(propios) / posiciones, 4) if posiciones else 0.0

    sintactica = monotonia_sintactica(nucleo.lineas_capitulo(n))

    mono_apertura = round(len(previas) / len(anteriores), 4) if anteriores else 0.0
    por_mil_max = (muletilla_max or {}).get("por_mil") or 0.0
    mono_muletillas = (round(min(1.0, por_mil_max / umbral_muletilla), 4)
                       if umbral_muletilla else 0.0)
    lineas_cap = len(nucleo.lineas_capitulo(n))
    mono_reciclaje = (round(min(1.0, len(recicladas) / lineas_cap), 4)
                      if lineas_cap else 0.0)
    monotonia = round((mono_apertura + mono_muletillas + mono_reciclaje) / 3, 4)

    resumen = {
        "bloqueante": 0,
        "mayor": sum(1 for i in incidencias if i["severidad"] == "mayor"),
        "menor": sum(1 for i in incidencias if i["severidad"] == "menor"),
    }

    return {
        "script": "repeticion",
        "capitulo": n,
        "metricas": {
            "ngramas_total": len(propios),
            "ngramas_repetidos": len(repetidos),
            "solape": solape,
            "umbral_solape": umbral_solape,
            "frases_recicladas": len(recicladas),
            "muletilla_max": muletilla_max,
            "tipo_apertura": tipo,
            "diversidad": diversidad,
            "monotonia": monotonia,
            "monotonia_componentes": {
                "apertura": mono_apertura,
                "muletillas": mono_muletillas,
                "reciclaje": mono_reciclaje,
            },
            "monotonia_sintactica": sintactica["monotonia_sintactica"],
            "monotonia_sintactica_componentes": sintactica["componentes"],
            "frases": sintactica["frases"],
        },
        "incidencias": incidencias,
        "resumen": resumen,
    }


def analizar_global(cfg: dict, estado: dict) -> dict:
    tam_ngrama = cfg["validacion"]["ngrama"]
    capitulos = nucleo.capitulos_existentes()

    donde = {}
    for c in capitulos:
        for gramo in nucleo.ngramas(_tokens(c), tam_ngrama):
            donde.setdefault(gramo, set()).add(c)

    compartidos = sorted(
        ({"ngrama": " ".join(g), "capitulos": sorted(cs)}
         for g, cs in donde.items() if len(cs) > 1),
        key=lambda d: (-len(d["capitulos"]), d["ngrama"]))

    porcapitulo = [analizar(c, cfg, estado) for c in capitulos]
    resumen = {
        "bloqueante": 0,
        "mayor": sum(r["resumen"]["mayor"] for r in porcapitulo),
        "menor": sum(r["resumen"]["menor"] for r in porcapitulo),
    }
    return {
        "script": "repeticion",
        "modo": "global",
        "capitulos": porcapitulo,
        "repeticiones_entre_capitulos": compartidos,
        "resumen": resumen,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="repeticion.py",
        description="Mide la repeticion de un capitulo o de la novela entera. "
                    "Nunca devuelve incidencias bloqueantes.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--capitulo", type=int, help="Numero de capitulo.")
    grupo.add_argument("--global", dest="completo", action="store_true",
                       help="Recorre todos los capitulos y cruza sus n-gramas.")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()
    estado = nucleo.cargar_estado()

    if args.completo:
        resultado = analizar_global(cfg, estado)
    else:
        if not nucleo.ruta_capitulo(args.capitulo).exists():
            nucleo.salir({"script": "repeticion",
                          "error": f"no existe el capitulo {args.capitulo}"}, 3)
        resultado = analizar(args.capitulo, cfg, estado)

    total = resultado["resumen"]["mayor"] + resultado["resumen"]["menor"]
    nucleo.salir(resultado, 1 if total else 0)


if __name__ == "__main__":
    main()
