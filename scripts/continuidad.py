"""Comprobaciones mecanicas de coherencia: lo que se puede verificar sin leer.

Tres modos, tal como fija SPEC seccion 10.5:
  --capitulo NN   7 comprobaciones sobre un capitulo
  --escaleta      5 comprobaciones estructurales sobre el plan
  --global        3 comprobaciones sobre el conjunto

Lo que exige criterio (reglas especulativas violadas, conocimiento imposible,
personajes fuera de caracter) NO esta aqui: es trabajo del subagente
`continuista`. Ver SPEC seccion 11.4.

Codigos de salida: 0 sin incidencias; 1 mayores o menores; 2 alguna
bloqueante; 3 error de ejecucion.
"""

import argparse
import re

import nucleo

VALORES_NO_DISPONIBLE = ("muerto", "muerta", "ausente", "desaparecid")


def _codigo(incidencias: list) -> int:
    severidades = {i["severidad"] for i in incidencias}
    if "bloqueante" in severidades:
        return 2
    if severidades:
        return 1
    return 0


def _resumen(incidencias: list) -> dict:
    return {sev: sum(1 for i in incidencias if i["severidad"] == sev)
            for sev in ("bloqueante", "mayor", "menor")}


def _plan_de(escaleta: dict, n: int):
    for cap in escaleta.get("capitulos", []):
        if cap.get("n") == n:
            return cap
    return None


def _terminos_prohibidos() -> list:
    secciones = nucleo.secciones_canon(nucleo.leer_canon())
    terminos = []
    for linea in secciones.get("Terminos prohibidos",
                               secciones.get("Términos prohibidos", "")).splitlines():
        limpia = linea.strip().lstrip("-*").strip()
        if limpia:
            terminos.append(limpia)
    return terminos


def _nombres_del_canon() -> set:
    secciones = nucleo.secciones_canon(nucleo.leer_canon())
    palabras = set()
    for nombre in re.findall(r"\*\*(.+?)\*\*",
                             secciones.get("Personajes", "")):
        for trozo in nucleo.normalizar(nombre).split():
            if len(trozo) > 1:
                palabras.add(trozo)
    return palabras


def _nombres_conocidos(estado: dict) -> set:
    conocidos = _nombres_del_canon()
    for entidad in estado.get("entidades", []):
        etiquetas = [entidad.get("nombre", "")] + list(entidad.get("alias", []))
        for etiqueta in etiquetas:
            for trozo in nucleo.normalizar(etiqueta).split():
                if len(trozo) > 1:
                    conocidos.add(trozo)
    return conocidos


def _nombres_propios(lineas: list) -> list:
    """Palabras en mayuscula que no abren frase. Deliberadamente simple:
    produce falsos positivos y por eso su incidencia es 'menor' (SPEC 19.2)."""
    bordes = (".", "?", "!", "…")
    candidatos = []
    for linea in lineas:
        inicio = True
        for bruto in linea.split():
            limpia = bruto.strip('"«»“”()[],;:¿¡')
            limpia = limpia.strip("—–-")
            nucleo_pal = limpia.rstrip(".?!…")
            if nucleo_pal and nucleo_pal[0].isupper() and not inicio:
                candidatos.append(nucleo_pal)
            if limpia:
                inicio = bruto.rstrip('"»”)').endswith(bordes)
            else:
                inicio = True
    return candidatos


def _hechos_vigentes(hechos: list) -> dict:
    """Ultimo hecho registrado para cada clave."""
    vigentes = {}
    for hecho in hechos:
        clave = hecho.get("clave")
        if clave:
            vigentes[clave] = hecho
    return vigentes


def modo_capitulo(n: int, cfg: dict) -> dict:
    estado = nucleo.cargar_estado()
    escaleta = nucleo.cargar_escaleta()
    plan = _plan_de(escaleta, n)
    if plan is None:
        nucleo.salir({"script": "continuidad", "modo": "capitulo",
                      "error": f"la escaleta no define el capitulo {n}"}, 3)
    if not nucleo.ruta_capitulo(n).exists():
        nucleo.salir({"script": "continuidad", "modo": "capitulo",
                      "error": f"no existe el capitulo {n} en disco"}, 3)

    lineas = nucleo.lineas_capitulo(n)
    texto = nucleo.normalizar("\n".join(lineas))
    comprobaciones = []
    incidencias = []

    # 1. Todos los marcadores de todos los beats aparecen literalmente.
    faltan = []
    for beat in plan.get("beats", []):
        for marcador in beat.get("marcadores", []):
            if nucleo.normalizar(marcador) not in texto:
                faltan.append((beat.get("id", "?"), marcador))
                incidencias.append({
                    "severidad": "bloqueante", "tipo": "beat_no_cubierto",
                    "detalle": (f"El beat {beat.get('id', '?')} exige el marcador "
                                f"'{marcador}' y no aparece en el texto."),
                })
    comprobaciones.append({
        "id": "beats_cubiertos", "ok": not faltan,
        **({"detalle": f"falta el marcador '{faltan[0][1]}' del beat {faltan[0][0]}"}
           if faltan else {})})

    # 2. Ningun termino prohibido del canon aparece en el capitulo.
    prohibidos = []
    for termino in _terminos_prohibidos():
        clave = nucleo.normalizar(termino)
        if clave and clave in texto:
            prohibidos.append(termino)
            ancla = next((ln for ln in lineas if clave in nucleo.normalizar(ln)), "")
            incidencias.append({
                "severidad": "bloqueante", "tipo": "termino_prohibido",
                "detalle": f"'{termino}' esta en Terminos prohibidos del canon.",
                "ancla": ancla,
            })
    comprobaciones.append({
        "id": "terminos_prohibidos", "ok": not prohibidos,
        **({"detalle": ", ".join(prohibidos)} if prohibidos else {})})

    # 3. El dia no retrocede respecto al capitulo anterior, salvo analepsis.
    previo = _plan_de(escaleta, n - 1)
    cronologia_ok = True
    if previo is not None and not plan.get("analepsis", False):
        if plan.get("dia", 0) < previo.get("dia", 0):
            cronologia_ok = False
            incidencias.append({
                "severidad": "bloqueante", "tipo": "cronologia_retrocede",
                "detalle": (f"El capitulo {n} ocurre el dia {plan.get('dia')} y el "
                            f"capitulo {n - 1} el dia {previo.get('dia')}, y no "
                            f"esta marcado como analepsis."),
            })
    comprobaciones.append({"id": "cronologia", "ok": cronologia_ok})

    # 4. Personajes que constan como no disponibles y aparecen nombrados.
    ausentes = []
    for clave, hecho in _hechos_vigentes(estado.get("hechos", [])).items():
        if hecho.get("tipo") != "estado_personaje":
            continue
        if hecho.get("capitulo", 0) >= n:
            continue
        valor = nucleo.normalizar(str(hecho.get("valor", "")))
        if not any(marca in valor for marca in VALORES_NO_DISPONIBLE):
            continue
        nombre = clave.split(":", 1)[1] if ":" in clave else clave
        # Deliberadamente tonta: basta con que aparezca una parte del nombre
        # ("Nadia" por "Nadia Ferran"). Genera falsos positivos con recuerdos y
        # menciones, y por eso es 'mayor' y no bloqueante (SPEC 11.3, punto 4).
        trozos_nombre = [t for t in nucleo.normalizar(nombre).split() if len(t) > 2]
        if any(t in texto for t in trozos_nombre):
            ausentes.append(nombre)
            incidencias.append({
                "severidad": "mayor", "tipo": "personaje_no_disponible",
                "detalle": (f"{nombre} consta como {hecho.get('valor')} desde el "
                            f"capitulo {hecho.get('capitulo')} (hecho "
                            f"{hecho.get('id')}) y aparece nombrado en el "
                            f"capitulo {n}."),
                "nota": ("Puede ser legitimo si es un recuerdo o una mencion. "
                         "Lo confirma el continuista."),
            })
    comprobaciones.append({
        "id": "personajes_ausentes", "ok": not ausentes,
        **({"detalle": ", ".join(ausentes)} if ausentes else {})})

    # 5. El nombre del POV del plan aparece en el capitulo.
    pov = plan.get("pov", "")
    trozos = [t for t in nucleo.normalizar(pov).split() if len(t) > 2]
    pov_ok = bool(trozos) and any(t in texto for t in trozos)
    if pov and not pov_ok:
        incidencias.append({
            "severidad": "mayor", "tipo": "pov_ausente",
            "detalle": (f"El plan fija el POV de {pov} y su nombre no aparece "
                        f"en el capitulo."),
        })
    comprobaciones.append({"id": "pov_presente", "ok": pov_ok or not pov})

    # 6. Los hilos que el plan manda cerrar estan abiertos en el estado.
    abiertos = {h.get("id") for h in estado.get("hilos", [])
                if h.get("estado") == "abierto"}
    no_cerrables = []
    for hilo in plan.get("cierra_hilos", []):
        if hilo not in abiertos:
            no_cerrables.append(hilo)
            incidencias.append({
                "severidad": "mayor", "tipo": "hilo_cerrado_sin_abrir",
                "detalle": (f"El plan manda cerrar el hilo {hilo} y ese hilo no "
                            f"consta abierto en novela/estado.json."),
            })
    comprobaciones.append({
        "id": "hilos_cerrables", "ok": not no_cerrables,
        **({"detalle": ", ".join(no_cerrables)} if no_cerrables else {})})

    # 7. Nombres propios que no estan ni en el estado ni en el canon.
    conocidos = _nombres_conocidos(estado)
    vacias = nucleo.vacias()
    desconocidos = []
    for candidato in _nombres_propios(lineas):
        clave = nucleo.normalizar(candidato)
        if not clave or clave in vacias or clave in conocidos:
            continue
        if clave not in desconocidos:
            desconocidos.append(clave)
            incidencias.append({
                "severidad": "menor", "tipo": "entidad_no_registrada",
                "detalle": (f"{candidato} aparece en el capitulo y no esta en "
                            f"entidades ni en el canon."),
            })
    comprobaciones.append({
        "id": "entidades_no_registradas", "ok": not desconocidos,
        **({"detalle": f"{desconocidos[0]} no esta registrada"}
           if desconocidos else {})})

    return {
        "script": "continuidad", "modo": "capitulo", "capitulo": n,
        "comprobaciones": comprobaciones, "incidencias": incidencias,
        "resumen": _resumen(incidencias),
    }


def modo_escaleta(cfg: dict) -> dict:
    escaleta = nucleo.cargar_escaleta()
    capitulos = escaleta.get("capitulos", [])
    hilos = escaleta.get("hilos", [])
    esperados = cfg["capitulos"]
    comprobaciones = []
    incidencias = []

    # 1. Exactamente N capitulos, numerados de 1 a N sin huecos.
    numeros = sorted(c.get("n") for c in capitulos)
    numeracion_ok = numeros == list(range(1, esperados + 1))
    if not numeracion_ok:
        incidencias.append({
            "severidad": "bloqueante", "tipo": "numeracion_capitulos",
            "detalle": (f"config.json pide {esperados} capitulos numerados de 1 a "
                        f"{esperados} y la escaleta trae {numeros}."),
        })
    comprobaciones.append({"id": "numeracion_capitulos", "ok": numeracion_ok})

    abre_de = {h.get("id"): h.get("abre_en") for h in hilos}

    # 2. Todo hilo de cierra_hilos abre en ese capitulo o antes.
    cierres_ok = True
    for cap in capitulos:
        for hilo in cap.get("cierra_hilos", []):
            abre = abre_de.get(hilo)
            if abre is None or abre > cap.get("n", 0):
                cierres_ok = False
                incidencias.append({
                    "severidad": "bloqueante", "tipo": "hilo_cerrado_sin_abrir",
                    "detalle": (f"El capitulo {cap.get('n')} cierra el hilo {hilo}, "
                                f"que abre en el capitulo {abre}."),
                })
    comprobaciones.append({"id": "hilos_cierran_despues_de_abrir", "ok": cierres_ok})

    # 3. Todo hilo declarado tiene cierra_en no nulo y menor o igual a N.
    hilos_ok = True
    for hilo in hilos:
        cierra = hilo.get("cierra_en")
        if cierra is None or not isinstance(cierra, int) or cierra > esperados:
            hilos_ok = False
            incidencias.append({
                "severidad": "bloqueante", "tipo": "hilo_sin_cierre",
                "detalle": (f"El hilo {hilo.get('id')} tiene cierra_en={cierra}, "
                            f"y debe ser un capitulo entre 1 y {esperados}."),
            })
    comprobaciones.append({"id": "hilos_con_cierre", "ok": hilos_ok})

    # 4. El dia es no decreciente salvo analepsis.
    cronologia_ok = True
    ordenados = sorted(capitulos, key=lambda c: c.get("n", 0))
    for anterior, siguiente in zip(ordenados, ordenados[1:]):
        if siguiente.get("analepsis", False):
            continue
        if siguiente.get("dia", 0) < anterior.get("dia", 0):
            cronologia_ok = False
            incidencias.append({
                "severidad": "bloqueante", "tipo": "cronologia_retrocede",
                "detalle": (f"El capitulo {siguiente.get('n')} ocurre el dia "
                            f"{siguiente.get('dia')} y el capitulo "
                            f"{anterior.get('n')} el dia {anterior.get('dia')}, "
                            f"y no esta marcado como analepsis."),
            })
    comprobaciones.append({"id": "cronologia", "ok": cronologia_ok})

    # 5. Informacion nueva, minimo de beats y marcadores en cada beat.
    contenido_ok = True
    for cap in capitulos:
        n = cap.get("n")
        if not cap.get("informacion_nueva"):
            contenido_ok = False
            incidencias.append({
                "severidad": "mayor", "tipo": "sin_informacion_nueva",
                "detalle": f"El capitulo {n} no aporta informacion nueva.",
            })
        beats = cap.get("beats", [])
        if len(beats) < 2:
            contenido_ok = False
            incidencias.append({
                "severidad": "mayor", "tipo": "beats_insuficientes",
                "detalle": f"El capitulo {n} tiene {len(beats)} beats y el minimo es 2.",
            })
        for beat in beats:
            if not beat.get("marcadores"):
                contenido_ok = False
                incidencias.append({
                    "severidad": "mayor", "tipo": "beat_sin_marcadores",
                    "detalle": (f"El beat {beat.get('id', '?')} del capitulo {n} "
                                f"no lleva marcadores comprobables."),
                })
    comprobaciones.append({"id": "contenido_minimo", "ok": contenido_ok})

    return {
        "script": "continuidad", "modo": "escaleta",
        "comprobaciones": comprobaciones, "incidencias": incidencias,
        "resumen": _resumen(incidencias),
    }


def modo_global(cfg: dict) -> dict:
    estado = nucleo.cargar_estado()
    escaleta = nucleo.cargar_escaleta()
    comprobaciones = []
    incidencias = []

    # 1. No queda ningun hilo abierto.
    abiertos = [h for h in estado.get("hilos", []) if h.get("estado") == "abierto"]
    for hilo in abiertos:
        incidencias.append({
            "severidad": "mayor", "tipo": "hilo_abierto_al_final",
            "detalle": (f"El hilo {hilo.get('id')} ({hilo.get('titulo')}) sigue "
                        f"abierto desde el capitulo {hilo.get('abierto_en')}."),
        })
    comprobaciones.append({"id": "hilos_cerrados", "ok": not abiertos})

    # 2. Los capitulos en disco coinciden con los de la escaleta.
    planificados = sorted(c.get("n") for c in escaleta.get("capitulos", []))
    en_disco = nucleo.capitulos_existentes()
    faltan = [n for n in planificados if n not in en_disco]
    sobran = [n for n in en_disco if n not in planificados]
    if faltan or sobran:
        incidencias.append({
            "severidad": "bloqueante", "tipo": "capitulos_descuadrados",
            "detalle": (f"faltan en disco: {faltan}; no estan en la escaleta: "
                        f"{sobran}"),
        })
    comprobaciones.append({"id": "capitulos_completos", "ok": not (faltan or sobran)})

    # 3. Dos hechos con la misma clave y valores incompatibles.
    por_clave = {}
    for hecho in estado.get("hechos", []):
        por_clave.setdefault(hecho.get("clave"), []).append(hecho)
    choques = []
    for clave, lista in por_clave.items():
        valores = {str(h.get("valor")) for h in lista}
        if len(valores) < 2:
            continue
        # En estado_personaje, un valor posterior distinto es una evolucion
        # declarada (vivo -> muerto) y no cuenta como choque.
        if all(h.get("tipo") == "estado_personaje" for h in lista):
            continue
        choques.append(clave)
        incidencias.append({
            "severidad": "mayor", "tipo": "hechos_incompatibles",
            "detalle": (f"La clave '{clave}' tiene valores distintos en varios "
                        f"capitulos: {sorted(valores)}."),
        })
    comprobaciones.append({"id": "hechos_coherentes", "ok": not choques})

    return {
        "script": "continuidad", "modo": "global",
        "comprobaciones": comprobaciones, "incidencias": incidencias,
        "resumen": _resumen(incidencias),
    }


def main():
    parser = argparse.ArgumentParser(
        prog="continuidad.py",
        description="Comprobaciones mecanicas de coherencia sobre un capitulo, "
                    "sobre la escaleta o sobre el conjunto de la novela.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--capitulo", type=int, help="Numero de capitulo.")
    grupo.add_argument("--escaleta", action="store_true",
                       help="Valida la estructura de novela/escaleta.json.")
    grupo.add_argument("--global", dest="completo", action="store_true",
                       help="Valida el conjunto de la novela ya escrita.")
    args = parser.parse_args()

    cfg = nucleo.cargar_config()

    if args.escaleta:
        resultado = modo_escaleta(cfg)
    elif args.completo:
        resultado = modo_global(cfg)
    else:
        resultado = modo_capitulo(args.capitulo, cfg)

    nucleo.salir(resultado, _codigo(resultado["incidencias"]))


if __name__ == "__main__":
    main()
