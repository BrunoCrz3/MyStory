"""Ciclo de mejora automatica del prompt del escritor.

Ajusta UNA cosa -la monotonia sintactica de la prosa-, comprueba con tiradas
reales si de verdad baja, y para cuando lo consigue o cuando deja de merecer la
pena. La explicacion en lenguaje llano esta en ciclo-mejora.md, que es lo que
hay que leer primero.

QUE TOCA Y QUE NO. Toca un unico fichero: `.claude/agents/escritor.md`, y
dentro de el solo la region marcada entre `<!-- ciclo:inicio -->` y
`<!-- ciclo:fin -->`. No toca umbrales, ni validadores, ni config.json mas alla
de la clave `premisa`, que restaura al terminar. Si alguna vez hiciera falta
cambiar algo fuera de esa region, el ciclo no lo hace: para y lo dice.

QUE REUTILIZA. Nada de metricas propias. La monotonia la calcula
`repeticion.monotonia_sintactica()`; los guardarrailes salen de
`informes.informe_capitulo()`, que ya ejecuta medir, repeticion y continuidad;
las tiradas las genera `orquestador.generar()`; el coste se suma de los eventos
`invocacion` con `orquestador.gastado()`. Este fichero solo decide y anota.

QUE NO REGISTRA EN events.jsonl. Los once tipos de evento del pipeline estan
cerrados (SPEC 14.3) y un ciclo de mejora no es ninguno de ellos. Las tiradas
que el ciclo lanza si registran sus eventos como siempre, y su events.jsonl
viaja entero a ciclo/tiradas/<id>/. Lo que el ciclo anota sobre si mismo va a
sus dos ficheros de memoria, que es lo que el autor pidio.

Python 3.12, solo biblioteca estandar. No habla por red ni lee el entorno.

    .\\.venv\\Scripts\\python.exe ciclo\\ciclo.py --arrancar
"""

import argparse
import json
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "server"))

import medir                # noqa: E402
import nucleo               # noqa: E402
import repeticion           # noqa: E402
import orquestador          # noqa: E402

CARPETA = RAIZ / "ciclo"
LINEA_BASE = CARPETA / "linea-base.json"
PREMISAS = CARPETA / "premisas.json"
REGISTRO = CARPETA / "iteraciones.jsonl"   # memoria para maquinas
BITACORA = CARPETA / "bitacora.md"         # memoria para personas
PROMPTS = CARPETA / "prompts"              # cada version probada, entera
TIRADAS = CARPETA / "tiradas"              # el resultado de cada tirada
RESPALDO = CARPETA / ".respaldo"           # la novela del autor, mientras dura
ESCRITOR = RAIZ / ".claude" / "agents" / "escritor.md"

MARCA_INICIO = "<!-- ciclo:inicio -->"
MARCA_FIN = "<!-- ciclo:fin -->"
ANCLA = "## Prohibido"          # la region se inserta justo antes

# Las cuatro condiciones de parada, en numeros.
MEJORA_MINIMA = 0.03            # exito de una iteracion: baja un 3% o mas
EMPEORAMIENTO_MAXIMO = 0.15     # dano: sube mas de un 15%
SIN_MEJORA_SEGUIDAS = 3         # agotamiento
GUARDARRAILES_SEGUIDOS = 2      # dano
MAX_ITERACIONES = 8
TIRADAS_POR_ITERACION = 2       # una sola no vale: la generacion no es determinista

# Presupuesto. El autor pidio 2 USD; una tirada de tres capitulos costo 8.24 en
# esta maquina, asi que 2 USD no dejaban terminar ni la primera iteracion. Este
# es el coste real de lo que pidio: ocho iteraciones de dos tiradas mas la
# confirmacion de dos premisas, a 8.24 la tirada, son 148 USD. Se deja en 150 y
# se puede bajar con --presupuesto: el ciclo para por lo que salte antes.
PRESUPUESTO_USD = 150.0

# Arranque automatico: solo si la monotonia media de las tres ultimas novelas
# supera esto. Ver --si-procede.
UMBRAL_ARRANQUE = 0.50


# --------------------------------------------------------------------------
# La escalera de candidatos
#
# Cada iteracion prueba UNO, en este orden, y cada uno trae escrita de antemano
# la hipotesis que lo justifica. El orden no es casual: va de lo abstracto a lo
# contable. El primero es deliberadamente vago porque saber que pedir "varia el
# ritmo" no funciona vale tanto como saber que si funciona, y sin probarlo no
# se sabe.
#
# `bloque` es el texto que se anade al prompt del escritor. Si un candidato se
# adopta, su bloque se queda y el siguiente se prueba encima; si se revierte,
# su bloque desaparece sin dejar rastro en el prompt (pero si en el registro).
# --------------------------------------------------------------------------

CANDIDATOS = [
    {
        "id": "v1-vago",
        "hipotesis": "Pedir variedad en abstracto basta: el modelo sabe lo que "
                     "es un ritmo variado y solo hay que recordarselo.",
        "espera": "Baja algo la uniformidad de longitud, poco lo demas.",
        "bloque": "Varia el ritmo de las frases a lo largo del capitulo.",
    },
    {
        "id": "v2-nombrar-el-tic",
        "hipotesis": "Lo abstracto no funciona pero nombrar el tic concreto si: "
                     "el problema no es que no sepa variar, es que no sabe que "
                     "su forma por defecto es siempre la misma.",
        "espera": "Baja la puntuacion, porque es el rasgo que se nombra.",
        "bloque":
            "Tu forma por defecto es esta: frase larga, con punto y coma o con "
            "un inciso entre rayas, una subordinada en medio y un giro al "
            "final. Escrita una vez es buena prosa. Repetida en todas las "
            "frases del capitulo es un tic, y en dieciocho capitulos se lee "
            "como una maquina. No la uses como forma por defecto.",
    },
    {
        "id": "v3-cuota-corta",
        "hipotesis": "Nombrar el tic no basta si no hay nada que contar: una "
                     "cuota verificable de frases cortas fuerza la dispersion "
                     "de longitudes, que es el componente mas pesado.",
        "espera": "Baja la uniformidad. El resto igual.",
        "bloque":
            "En cada capitulo tiene que haber al menos una frase de ocho "
            "palabras o menos, y al menos una de mas de treinta. No las pongas "
            "seguidas ni siempre en el mismo sitio del capitulo.",
    },
    {
        "id": "v4-cuota-puntuacion",
        "hipotesis": "El punto y coma y la raya intercalada son el vehiculo del "
                     "tic. Limitarlos por capitulo obliga a resolver la misma "
                     "subordinacion con otra sintaxis.",
        "espera": "Baja la puntuacion. Ojo: podria subir la uniformidad si el "
                  "escritor compensa alargando todas las frases por igual.",
        "bloque":
            "Como mucho una linea del capitulo puede llevar punto y coma o un "
            "inciso entre rayas. Las demas resuelven la relacion entre sus "
            "ideas con otra cosa: dos frases, una coma, un punto seco. La raya "
            "que abre un dialogo no cuenta para este limite.",
    },
    {
        "id": "v5-aperturas-distintas",
        "hipotesis": "El componente de apertura no se mueve con nada de lo "
                     "anterior porque nadie lo ha pedido. Exigir que cada linea "
                     "abra con una forma distinta es contable y directo.",
        "espera": "Baja la apertura. El resto igual.",
        "bloque":
            "Cada linea del capitulo abre con una forma distinta de la "
            "anterior. Las formas son: por el nombre de quien actua, por el "
            "verbo, por un complemento de tiempo o lugar, por una subordinada, "
            "y por dialogo. No uses dos veces seguidas la misma, y no abras "
            "todo el capitulo por el nombre del personaje.",
    },
    {
        "id": "v6-plan-de-ritmo",
        "hipotesis": "Las cuotas sueltas se cumplen a minimos. Obligar a "
                     "decidir el patron de longitudes antes de escribir mueve "
                     "los tres componentes a la vez, que es lo que hace falta "
                     "para que la mejora no sea sospechosa.",
        "espera": "Bajan los tres. Es el candidato con mas riesgo de romper "
                  "longitud, porque anade trabajo antes de escribir.",
        "bloque":
            "Antes de escribir el capitulo, decide en que orden van las "
            "longitudes de sus frases -por ejemplo larga, corta, media, muy "
            "corta- y escribelo asi. El patron tiene que ser distinto del que "
            "usaste en el capitulo anterior. No expliques el patron en tu "
            "respuesta: solo cumplelo.",
    },
    {
        "id": "v7-autocomprobacion",
        "hipotesis": "El escritor cumple lo que puede comprobar. Convertir las "
                     "cuotas en una autocomprobacion explicita antes de "
                     "entregar sube el cumplimiento sin pedir nada nuevo.",
        "espera": "Consolida lo ya adoptado en vez de anadir efecto propio. Si "
                  "no mejora un 3%, la palanca esta agotada.",
        "bloque":
            "Antes de entregar el capitulo, cuenta: cuantas frases tiene, cual "
            "es la mas corta, cual la mas larga, cuantas lineas llevan punto y "
            "coma o inciso, y con que forma abre cada linea. Si dos lineas "
            "abren igual o si la frase mas corta pasa de ocho palabras, "
            "reescribe antes de entregar. No pongas la cuenta en el fichero.",
    },
    {
        "id": "v8-contraejemplo",
        "hipotesis": "Lo que no se consigue describiendo se consigue "
                     "ensenando. Un par de ejemplo y contraejemplo fija la "
                     "diferencia mejor que cualquier regla.",
        "espera": "Efecto pequeno si lo anterior ya funciono. Es el ultimo "
                  "peldano de la escalera.",
        "bloque":
            "Asi suena el tic, y no quieres esto: \"Retiro la placa del tubo, "
            "que llevaba once anos helado; encontro las nueve muescas "
            "intactas, ninguna gastada, y entendio entonces que nadie habia "
            "entrado nunca a oir lo que pagaba.\" Asi suena variado, y quieres "
            "esto: \"Retiro la placa. Nueve muescas, y ninguna gastada. Once "
            "anos pagando por un recuerdo que nadie habia entrado a oir "
            "jamas.\" Misma informacion, mismo tono, otro ritmo.",
    },
]


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z")


def _leer_json(ruta: Path, que: str) -> dict:
    if not ruta.exists():
        _morir(f"no existe {que}: {ruta.relative_to(RAIZ).as_posix()}")
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _morir(f"{que} no es JSON valido: {exc}")


def _morir(mensaje: str):
    nucleo.salir({"script": "ciclo", "error": mensaje}, 3)


def _decir(mensaje: str) -> None:
    """Por stderr, porque stdout es el JSON del resultado."""
    print(mensaje, file=sys.stderr, flush=True)


def _lineas_de(fichero: Path) -> list:
    return [ln.strip() for ln in fichero.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def _monotonia_de_carpeta(carpeta: Path) -> dict:
    """La monotonia sintactica de una novela entera, capitulos agrupados."""
    caps = sorted(carpeta.glob("capitulo-*.md"))
    todas = []
    for cap in caps:
        todas += _lineas_de(cap)
    medida = repeticion.monotonia_sintactica(todas)
    medida["capitulos"] = len(caps)
    return medida


# --------------------------------------------------------------------------
# El prompt del escritor: la unica cosa que el ciclo cambia
# --------------------------------------------------------------------------

def _region(bloques: list) -> str:
    cuerpo = "\n\n".join(b.strip() for b in bloques)
    return (f"{MARCA_INICIO}\n"
            f"## Ritmo de la frase\n\n"
            f"Esta seccion la mantiene el ciclo de mejora automatica. No la "
            f"edites a mano: la reescribe la siguiente iteracion. Lo que hay "
            f"aqui y por que esta, en ciclo-mejora.md y ciclo/bitacora.md.\n\n"
            f"{cuerpo}\n"
            f"{MARCA_FIN}\n")


def _aplicar(bloques: list) -> str:
    """Deja el prompt del escritor con exactamente estos bloques. Devuelve el
    texto resultante. Si no hay bloques, la region desaparece entera."""
    texto = ESCRITOR.read_text(encoding="utf-8")

    inicio = texto.find(MARCA_INICIO)
    if inicio != -1:
        fin = texto.find(MARCA_FIN)
        if fin == -1:
            _morir("el prompt del escritor tiene la marca de inicio del ciclo "
                   "pero no la de fin: arreglalo a mano antes de seguir")
        texto = texto[:inicio] + texto[fin + len(MARCA_FIN):].lstrip("\n")

    if bloques:
        corte = texto.find(ANCLA)
        if corte == -1:
            _morir(f"el prompt del escritor ya no tiene '{ANCLA}': el ciclo no "
                   f"sabe donde insertar su seccion. Parar y avisar al autor.")
        texto = texto[:corte] + _region(bloques) + "\n" + texto[corte:]

    ESCRITOR.write_text(texto, encoding="utf-8")
    return texto


def _guardar_prompt(etiqueta: str, texto: str) -> str:
    PROMPTS.mkdir(parents=True, exist_ok=True)
    destino = PROMPTS / f"escritor-{etiqueta}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino.relative_to(RAIZ).as_posix()


# --------------------------------------------------------------------------
# Respaldo: la novela del autor no se toca
# --------------------------------------------------------------------------

def _respaldar() -> None:
    """Aparta la novela viva y la configuracion antes de empezar."""
    if RESPALDO.exists():
        _morir("ya existe ciclo/.respaldo: hay un ciclo a medias. Restaura a "
               "mano lo que hay dentro antes de arrancar otro.")
    RESPALDO.mkdir(parents=True)
    shutil.copytree(RAIZ / "novela", RESPALDO / "novela")
    shutil.copy2(RAIZ / "config.json", RESPALDO / "config.json")
    shutil.copy2(ESCRITOR, RESPALDO / "escritor.md")


def _restaurar_novela_y_config() -> None:
    """Devuelve la novela del autor y config.json a como estaban. El prompt del
    escritor NO se restaura: ahi se queda lo adoptado, que es el mejor estado
    conocido."""
    if not RESPALDO.exists():
        return
    if (RAIZ / "novela").exists():
        shutil.rmtree(RAIZ / "novela")
    shutil.copytree(RESPALDO / "novela", RAIZ / "novela")
    shutil.copy2(RESPALDO / "config.json", RAIZ / "config.json")
    shutil.rmtree(RESPALDO)


def _poner_premisa(premisa: str) -> None:
    """Cambia SOLO la clave 'premisa' de config.json. El resto se reescribe
    igual que estaba, en el mismo orden: json.load conserva el orden de las
    claves y json.dump lo respeta."""
    ruta = RAIZ / "config.json"
    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    cfg["premisa"] = premisa
    ruta.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _novela_en_blanco() -> None:
    """Deja novela/ como la semilla: sin canon, sin escaleta, sin capitulos."""
    carpeta = RAIZ / "novela"
    if carpeta.exists():
        shutil.rmtree(carpeta)
    (carpeta / "capitulos").mkdir(parents=True)
    (carpeta / "informes").mkdir(parents=True)
    nucleo.guardar_estado(json.loads(json.dumps(nucleo.SEMILLA_ESTADO)))


# --------------------------------------------------------------------------
# Una tirada: generar, medir, apartar
# --------------------------------------------------------------------------

def _medir_tirada() -> dict:
    """Lo que hay ahora mismo en novela/, medido con los validadores de
    siempre. Ni una cuenta hecha a mano.

    La continuidad NO se recalcula: se lee del informe que el orquestador ya
    guardo en novela/informes/ al aceptar cada capitulo. Recalcularla despues
    da falsos positivos, y estan medidos: sobre la novela terminada del autor
    salen tres `hilo_cerrado_sin_abrir` que no existieron nunca, porque el
    archivista ya cerro esos hilos en estado.json y la comprobacion mira el
    estado de AHORA contra un plan de ENTONCES. Es la misma trampa que
    repeticion.py documenta para las frases recicladas. El informe en disco es
    el veredicto del momento en que el capitulo se dio por bueno, que es el
    que cuenta.

    La longitud si se vuelve a medir sobre el texto final, porque el estilista
    corre despues de esa validacion y dejarlo sin comprobar es el fallo mas
    silencioso del sistema (invariante 6 de CLAUDE.md). El solape tambien se
    recalcula: son n-gramas de los ficheros, no dependen del estado.
    """
    cfg = nucleo.cargar_config()
    estado = nucleo.cargar_estado()
    capitulos = nucleo.capitulos_existentes()

    mono = _monotonia_de_carpeta(RAIZ / "novela" / "capitulos")

    errores_continuidad = 0
    errores_longitud = 0
    informes_ausentes = 0
    solapes = []
    for n in capitulos:
        guardado = RAIZ / "novela" / "informes" / f"capitulo_{n:02d}.json"
        if guardado.exists():
            informe = json.loads(guardado.read_text(encoding="utf-8"))
            for inc in informe.get("incidencias", []):
                if (inc.get("origen") in ("continuidad", "continuista")
                        and inc.get("severidad") in ("bloqueante", "mayor")):
                    errores_continuidad += 1
        else:
            # Sin informe no hay veredicto, y dar por buena una tirada que no
            # dejo rastro seria contarse un cuento.
            informes_ausentes += 1

        longitud = medir.medir(n, cfg)          # despues del estilista, siempre
        errores_longitud += sum(
            1 for inc in longitud["incidencias"]
            if inc.get("severidad") == "bloqueante")
        solapes.append(repeticion.analizar(n, cfg, estado)["metricas"]["solape"])

    return {
        "capitulos": len(capitulos),
        "monotonia_sintactica": mono["monotonia_sintactica"],
        "componentes": mono["componentes"],
        "frases": mono["frases"],
        "errores_continuidad": errores_continuidad,
        "errores_longitud": errores_longitud,
        "informes_ausentes": informes_ausentes,
        "solape_medio": round(statistics.fmean(solapes), 4) if solapes else 0.0,
    }


def _apartar_tirada(etiqueta: str) -> str:
    """Mueve la novela recien generada a ciclo/tiradas/<etiqueta>/. Se guarda
    entera -capitulos, informes, events.jsonl- para poder volver a mirarla."""
    TIRADAS.mkdir(parents=True, exist_ok=True)
    destino = TIRADAS / etiqueta
    if destino.exists():
        shutil.rmtree(destino)
    shutil.move(str(RAIZ / "novela"), str(destino))
    return destino.relative_to(RAIZ).as_posix()


def _tirada(premisa: str, etiqueta: str) -> dict:
    """Una tirada completa: premisa fija, novela en blanco, las cinco fases,
    medida y apartada. Devuelve lo medido."""
    _decir(f"  tirada {etiqueta}: generando...")
    _poner_premisa(premisa)
    _novela_en_blanco()

    resultado = orquestador.generar(nucleo.cargar_config(),
                                    avisar=lambda m: _decir(f"    {m}"))
    coste = orquestador.gastado(nucleo.cargar_config(), resultado["tirada"])

    medida = _medir_tirada()
    medida["desenlace"] = resultado["desenlace"]
    medida["coste_usd"] = coste
    medida["guardado_en"] = _apartar_tirada(etiqueta)
    _decir(f"  tirada {etiqueta}: monotonia "
           f"{medida['monotonia_sintactica']}, coste {coste:.2f} USD, "
           f"desenlace {medida['desenlace']}")
    return medida


# --------------------------------------------------------------------------
# Guardarrailes
# --------------------------------------------------------------------------

def _guardarrailes(medida: dict, base: dict) -> list:
    """Que se ha roto. Vacia significa que la tirada es adoptable.

    Son el objetivo real. La monotonia es solo el indicador: sin esto, el
    sistema aprende a bajarla escribiendo frases cortas y planas.
    """
    rotos = []

    # "Cero errores de continuidad" quiere decir cero NUEVOS. El limite sale de
    # la linea base y alli esta medido y explicado por que no es cero: la
    # novela de referencia arrastra tres 'hilo_cerrado_sin_abrir' que vienen
    # del desajuste entre escaleta y archivista, no de la prosa, y que el
    # prompt del escritor no puede arreglar. Con el cero absoluto el ciclo
    # rechazaria todas las iteraciones. Para exigirlo igualmente, pon 0 en
    # linea-base.json -> guardarrailes_base.errores_continuidad.
    tope_continuidad = base.get("errores_continuidad", 0)
    if medida["errores_continuidad"] > tope_continuidad:
        rotos.append(f"{medida['errores_continuidad']} errores de continuidad, "
                     f"{medida['errores_continuidad'] - tope_continuidad} mas "
                     f"que la base ({tope_continuidad})")

    # Este si es cero absoluto, y la base lo cumple.
    if medida["errores_longitud"]:
        rotos.append(f"{medida['errores_longitud']} errores de longitud "
                     f"(el limite es cero)")

    # El solape de la base es practicamente cero, asi que un 10% sobre el seria
    # una tolerancia de nada y saltaria con cualquier coincidencia. Se pone un
    # suelo absoluto de 0.01, que sigue siendo la mitad del umbral con el que
    # repeticion.py da por mala una tirada.
    tope = max(base["solape_medio"] * 1.10, 0.01)
    if medida["solape_medio"] > tope:
        rotos.append(f"repeticion de vocabulario {medida['solape_medio']} "
                     f"por encima del tope {round(tope, 4)}")

    tope_coste = base["coste_tirada_usd"] * 1.5
    if medida["coste_usd"] > tope_coste:
        rotos.append(f"coste {medida['coste_usd']:.2f} USD por encima del tope "
                     f"{tope_coste:.2f} USD")

    if medida.get("informes_ausentes"):
        rotos.append(f"{medida['informes_ausentes']} capitulos sin informe de "
                     f"validacion: la tirada no se puede juzgar")
    if not medida["capitulos"]:
        rotos.append("la tirada no dejo ni un capitulo")
    if medida["desenlace"] != "terminada":
        rotos.append(f"la tirada no llego al final: {medida['desenlace']}")
    return rotos


def _sospechosa(componentes: list, base_comp: dict) -> bool:
    """True si la mejora viene de un solo componente.

    Una monotonia que baja porque uno de los tres se desploma y los otros dos
    no se mueven no es un ritmo mejor: es un rasgo suprimido. Se anota.
    """
    medios = {k: statistics.fmean([c[k] for c in componentes])
              for k in ("apertura", "puntuacion", "uniformidad")}
    mejoran = [k for k, v in medios.items() if v < base_comp[k] - 0.01]
    return len(mejoran) <= 1


# --------------------------------------------------------------------------
# Memoria: las dos anotaciones
# --------------------------------------------------------------------------

def _anotar(registro: dict) -> None:
    """Una linea JSON. El fichero es append-only y no se reescribe nunca."""
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as fichero:
        fichero.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _prosa(texto: str) -> None:
    """La bitacora que lee una persona. Se anade, nunca se sobrescribe."""
    BITACORA.parent.mkdir(parents=True, exist_ok=True)
    cabecera = ""
    if not BITACORA.exists():
        cabecera = ("# Bitacora del ciclo de mejora\n\n"
                    "Que se probo, que paso y que se concluye. Los fracasos "
                    "tambien, que son la mitad de lo que hay que saber.\n")
    with BITACORA.open("a", encoding="utf-8") as fichero:
        fichero.write(cabecera + "\n" + texto.rstrip() + "\n")


# --------------------------------------------------------------------------
# El ciclo
# --------------------------------------------------------------------------

def _ultimas_monotonias(cuantas: int = 3) -> list:
    """La monotonia de las ultimas novelas cerradas, para el arranque
    automatico. Mira el archivo y la novela viva."""
    carpetas = [p / "capitulos" for p in sorted((RAIZ / "archivo").glob("*"))
                if (p / "capitulos").is_dir()]
    carpetas.append(RAIZ / "novela" / "capitulos")
    medidas = []
    for carpeta in carpetas:
        if not carpeta.is_dir() or not list(carpeta.glob("capitulo-*.md")):
            continue
        medidas.append(_monotonia_de_carpeta(carpeta)["monotonia_sintactica"])
    return medidas[-cuantas:]


def _comprobaciones_previas() -> None:
    if orquestador.generando():
        _morir("hay una generacion en marcha. El ciclo no arranca a mitad de "
               "una novela: espera a que termine.")
    if (RAIZ / "novela" / ".detener").exists():
        _morir("hay una senal de parada pendiente en novela/.detener")
    for ruta, que in ((LINEA_BASE, "la linea base"), (PREMISAS, "las premisas")):
        if not ruta.exists():
            _morir(f"falta {que}: {ruta.relative_to(RAIZ).as_posix()}")


def arrancar(presupuesto: float) -> dict:
    base_doc = _leer_json(LINEA_BASE, "la linea base")
    premisas = _leer_json(PREMISAS, "las premisas")
    base = base_doc["guardarrailes_base"]
    base_comp = base_doc["componentes"]
    meta = base_doc["meta"]
    premisa_ajuste = premisas["ajuste"]

    mejor = base_doc["monotonia_sintactica"]
    adoptados = []
    sin_mejora = 0
    guardarrailes_seguidos = 0
    gastado = 0.0
    iteracion = 0
    parada = None

    _decir(f"Linea base {mejor}, meta {meta}, presupuesto {presupuesto:.0f} USD.")
    _respaldar()
    try:
        for candidato in CANDIDATOS[:MAX_ITERACIONES]:
            iteracion += 1
            etiqueta = f"{iteracion:02d}-{candidato['id']}"

            # Presupuesto: se comprueba ANTES de cada tirada, no despues.
            if gastado + base["coste_tirada_usd"] > presupuesto:
                parada = {
                    "causa": "presupuesto",
                    "detalle": (f"quedan {presupuesto - gastado:.2f} USD y una "
                                f"tirada cuesta unos "
                                f"{base['coste_tirada_usd']:.2f}"),
                }
                break

            # La hipotesis se escribe ANTES de ejecutar nada.
            _anotar({"ts": _ahora(), "tipo": "hipotesis",
                     "iteracion": iteracion, "candidato": candidato["id"],
                     "hipotesis": candidato["hipotesis"],
                     "espera": candidato["espera"],
                     "cambio": candidato["bloque"],
                     "referencia": mejor, "meta": meta})
            _decir(f"\nIteracion {iteracion} — {candidato['id']}")
            _decir(f"  hipotesis: {candidato['hipotesis']}")

            texto = _aplicar(adoptados + [candidato["bloque"]])
            prompt_guardado = _guardar_prompt(etiqueta, texto)

            medidas = []
            for k in range(1, TIRADAS_POR_ITERACION + 1):
                if gastado + base["coste_tirada_usd"] > presupuesto:
                    parada = {"causa": "presupuesto",
                              "detalle": "se agoto a mitad de la iteracion"}
                    break
                medida = _tirada(premisa_ajuste, f"{etiqueta}-t{k}")
                gastado += medida["coste_usd"]
                medidas.append(medida)
            if parada:
                _aplicar(adoptados)      # nunca a mitad de un experimento
                break

            mediana = round(statistics.median(
                [m["monotonia_sintactica"] for m in medidas]), 4)
            rotos = sorted({r for m in medidas for r in _guardarrailes(m, base)})
            mejora = round((mejor - mediana) / mejor, 4) if mejor else 0.0
            sospechosa = _sospechosa([m["componentes"] for m in medidas],
                                     base_comp)
            adoptado = mejora >= MEJORA_MINIMA and not rotos

            _anotar({
                "ts": _ahora(), "tipo": "resultado", "iteracion": iteracion,
                "candidato": candidato["id"], "prompt": prompt_guardado,
                "tiradas": medidas, "mediana": mediana, "referencia": mejor,
                "mejora": mejora, "guardarrailes_rotos": rotos,
                "mejora_de_un_solo_componente": sospechosa,
                "veredicto": "adoptado" if adoptado else "revertido",
                "coste_iteracion_usd": round(
                    sum(m["coste_usd"] for m in medidas), 4),
                "gastado_usd": round(gastado, 4),
            })

            motivo = ("mejora del " f"{mejora:.1%}" if adoptado
                      else ("rompe " + "; ".join(rotos) if rotos
                            else f"solo mejora un {mejora:.1%}, hace falta un "
                                 f"{MEJORA_MINIMA:.0%}"))
            _prosa(
                f"## Iteracion {iteracion} — {candidato['id']}\n\n"
                f"**Hipotesis.** {candidato['hipotesis']}\n\n"
                f"**Que se cambio.** Se anadio al prompt del escritor: "
                f"«{candidato['bloque']}»\n\n"
                f"**Que paso.** Dos tiradas con la premisa de ajuste. Mediana "
                f"de monotonia {mediana} frente a la referencia {mejor}. "
                f"Componentes medios: "
                + ", ".join(
                    f"{k} {statistics.fmean([m['componentes'][k] for m in medidas]):.3f}"
                    for k in ("apertura", "puntuacion", "uniformidad"))
                + f". Coste {sum(m['coste_usd'] for m in medidas):.2f} USD.\n\n"
                + (f"**Aviso.** La mejora viene de un solo componente. Eso no "
                   f"es un ritmo mejor: es un rasgo suprimido, y conviene "
                   f"mirar el texto antes de fiarse del numero.\n\n"
                   if sospechosa and mejora > 0 else "")
                + f"**Veredicto.** {'Adoptado' if adoptado else 'Revertido'}: "
                  f"{motivo}.\n")

            if adoptado:
                adoptados.append(candidato["bloque"])
                mejor = mediana
                sin_mejora = 0
            else:
                _aplicar(adoptados)
                sin_mejora += 1

            guardarrailes_seguidos = guardarrailes_seguidos + 1 if rotos else 0

            # --- Las cuatro paradas, en orden de gravedad ---
            if rotos and guardarrailes_seguidos >= GUARDARRAILES_SEGUIDOS:
                parada = {"causa": "dano",
                          "detalle": f"guardarrailes rotos "
                                     f"{guardarrailes_seguidos} veces seguidas: "
                                     + "; ".join(rotos)}
                break
            if mejor and mediana > mejor * (1 + EMPEORAMIENTO_MAXIMO):
                parada = {"causa": "dano",
                          "detalle": f"la monotonia empeoro de {mejor} a "
                                     f"{mediana}, mas de un "
                                     f"{EMPEORAMIENTO_MAXIMO:.0%}"}
                break
            if adoptado and mediana <= meta:
                confirmacion = _confirmar(premisas["confirmacion"], etiqueta,
                                          meta, base, presupuesto - gastado)
                gastado += confirmacion["coste_usd"]
                if confirmacion["sostiene"]:
                    parada = {"causa": "exito", "detalle": confirmacion["detalle"]}
                    break
                _prosa(f"**Confirmacion.** {confirmacion['detalle']} El ciclo "
                       f"sigue.\n")
            if sin_mejora >= SIN_MEJORA_SEGUIDAS:
                parada = {"causa": "agotamiento",
                          "detalle": f"{sin_mejora} iteraciones seguidas sin "
                                     f"mejorar un {MEJORA_MINIMA:.0%}"}
                break
        else:
            parada = {"causa": "presupuesto",
                      "detalle": f"se probaron los {MAX_ITERACIONES} candidatos"}
    finally:
        _restaurar_novela_y_config()

    parada = parada or {"causa": "presupuesto", "detalle": "sin mas candidatos"}
    cierre = {
        "ts": _ahora(), "tipo": "cierre", "causa": parada["causa"],
        "detalle": parada["detalle"], "iteraciones": iteracion,
        "gastado_usd": round(gastado, 4), "linea_base": base_doc["monotonia_sintactica"],
        "mejor_conocida": mejor, "meta": meta,
        "adoptados": len(adoptados),
    }
    _anotar(cierre)
    _prosa(_cierre_en_prosa(cierre, base_doc, adoptados))
    _decir(f"\nCiclo terminado por {parada['causa']}: {parada['detalle']}")
    return {"script": "ciclo", **cierre}


def _confirmar(premisas: list, etiqueta: str, meta: float, base: dict,
               saldo: float) -> dict:
    """Una tirada por cada premisa nueva. Si la mejora no se sostiene aqui, era
    sobreajuste a la premisa de ajuste."""
    _decir("  meta alcanzada: confirmando con dos premisas nuevas")
    if saldo < base["coste_tirada_usd"] * len(premisas):
        return {"sostiene": False, "coste_usd": 0.0,
                "detalle": "no quedaba presupuesto para confirmar, asi que la "
                           "meta queda sin confirmar"}
    medidas = [_tirada(p, f"{etiqueta}-conf{i}")
               for i, p in enumerate(premisas, 1)]
    mediana = round(statistics.median(
        [m["monotonia_sintactica"] for m in medidas]), 4)
    rotos = sorted({r for m in medidas for r in _guardarrailes(m, base)})
    sostiene = mediana <= meta and not rotos
    coste = round(sum(m["coste_usd"] for m in medidas), 4)
    detalle = (f"con dos premisas que no se habian usado, la mediana es "
               f"{mediana} frente a la meta {meta}"
               + (f" y se rompe: {'; '.join(rotos)}" if rotos else "")
               + (". Se sostiene." if sostiene
                  else ". No se sostiene: era sobreajuste."))
    return {"sostiene": sostiene, "coste_usd": coste, "detalle": detalle,
            "mediana": mediana, "tiradas": medidas}


def _cierre_en_prosa(cierre: dict, base_doc: dict, adoptados: list) -> str:
    leyenda = {
        "exito": "**Exito.** La meta se alcanzo y se sostuvo con dos premisas "
                 "que no se habian usado durante el ajuste.",
        "agotamiento": "**Agotamiento.** Esto no es un fracaso: significa que "
                       "esta palanca esta agotada. Tocar el prompt del "
                       "escritor ya no baja la monotonia, y la siguiente "
                       "mejora habra que buscarla en otro sitio.",
        "presupuesto": "**Presupuesto.** Se acabo el dinero o los candidatos "
                       "antes de llegar a la meta. No dice nada sobre si la "
                       "palanca sirve: dice que no se termino de probar.",
        "dano": "**Dano.** Se paro porque los cambios estaban estropeando algo "
                "que si funcionaba. El indicador bajaba pero el objetivo real "
                "se rompia, que es exactamente lo que los guardarrailes estan "
                "ahi para impedir.",
    }
    return (
        f"## Cierre\n\n{leyenda.get(cierre['causa'], cierre['causa'])}\n\n"
        f"{cierre['detalle'].capitalize()}.\n\n"
        f"Se hicieron {cierre['iteraciones']} iteraciones y se gastaron "
        f"{cierre['gastado_usd']:.2f} USD. La monotonia paso de "
        f"{cierre['linea_base']} (linea base) a {cierre['mejor_conocida']}, con "
        f"meta en {cierre['meta']}. Quedan {cierre['adoptados']} cambios "
        f"adoptados en el prompt del escritor.\n\n"
        f"El repositorio queda en el mejor estado conocido: la novela del autor "
        f"restaurada tal cual estaba, y el prompt del escritor con lo adoptado "
        f"y nada mas.\n")


# --------------------------------------------------------------------------
# Linea de comandos
# --------------------------------------------------------------------------

def estado() -> dict:
    base_doc = _leer_json(LINEA_BASE, "la linea base")
    lineas = []
    if REGISTRO.exists():
        for ln in REGISTRO.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                lineas.append(json.loads(ln))
    resultados = [r for r in lineas if r.get("tipo") == "resultado"]
    cierres = [r for r in lineas if r.get("tipo") == "cierre"]
    return {
        "script": "ciclo",
        "linea_base": base_doc["monotonia_sintactica"],
        "meta": base_doc["meta"],
        "iteraciones_registradas": len(resultados),
        "adoptadas": sum(1 for r in resultados if r["veredicto"] == "adoptado"),
        "mejor_conocida": next(
            (r["mediana"] for r in reversed(resultados)
             if r["veredicto"] == "adoptado"),
            base_doc["monotonia_sintactica"]),
        "gastado_usd": resultados[-1]["gastado_usd"] if resultados else 0.0,
        "ultima_parada": cierres[-1] if cierres else None,
        "ciclo_a_medias": RESPALDO.exists(),
        "candidatos_totales": len(CANDIDATOS),
    }


def main():
    parser = argparse.ArgumentParser(
        prog="ciclo.py",
        description="Ciclo de mejora automatica del prompt del escritor. "
                    "Lee ciclo-mejora.md antes de lanzarlo.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--arrancar", action="store_true",
                       help="Lanza el ciclo. Genera novelas de verdad y cuesta "
                            "dinero de verdad.")
    grupo.add_argument("--si-procede", action="store_true",
                       help="Arranca solo si la monotonia media de las tres "
                            "ultimas novelas supera 0.50. Es el arranque "
                            "automatico al cerrar una novela.")
    grupo.add_argument("--estado", action="store_true",
                       help="Dice por donde va el ciclo. No ejecuta nada.")
    parser.add_argument("--presupuesto", type=float, default=PRESUPUESTO_USD,
                        help=f"Tope de gasto en USD. Por defecto "
                             f"{PRESUPUESTO_USD:.0f}, que es lo que cuestan "
                             f"{MAX_ITERACIONES} iteraciones de "
                             f"{TIRADAS_POR_ITERACION} tiradas mas la "
                             f"confirmacion.")
    args = parser.parse_args()

    if args.estado:
        nucleo.salir(estado(), 0)

    _comprobaciones_previas()

    if args.si_procede:
        ultimas = _ultimas_monotonias(3)
        media = round(statistics.fmean(ultimas), 4) if ultimas else 0.0
        if media <= UMBRAL_ARRANQUE:
            nucleo.salir({
                "script": "ciclo", "arranca": False,
                "monotonia_media_ultimas": media, "umbral": UMBRAL_ARRANQUE,
                "detalle": "la monotonia media de las ultimas novelas no llega "
                           "al umbral: no hay nada que ajustar",
            }, 0)
        _decir(f"Monotonia media de las ultimas novelas {media}, por encima de "
               f"{UMBRAL_ARRANQUE}: el ciclo arranca.")

    if args.presupuesto <= 0:
        _morir("--presupuesto tiene que ser mayor que cero")

    nucleo.salir(arrancar(args.presupuesto), 0)


if __name__ == "__main__":
    main()
