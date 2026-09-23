"""`extraer-hallazgos` y la adopcion. Aqui cierra el ciclo del modo hibrido.

Tres reglas gobiernan este modulo:

1. **Sin consolidacion no hay extraccion** (RF-FIND-04). La consolidacion es el
   punto **unico** de promocion de memoria corta a memoria larga, y la
   extraccion ocurre dentro de ese punto. Si se pudiera extraer de un borrador,
   cada iteracion fallida dejaria sedimento y la bandeja del autor seria el
   registro de lo que el sistema intento, no de lo que la novela dice.
2. **Todo hallazgo nace `propuesto` y solo el autor lo mueve** (RF-FIND-02,
   RF-FIND-05, P-21). Un hallazgo propuesto **no es canon**: es memoria larga en
   estado de propuesta. La diferencia es el ultimo cortafuegos de la resistencia
   a inyeccion, y aguanta aunque las otras dos reglas fallen.
3. **`findings/` no escribe el canon.** Un hallazgo adoptado apunta al hecho o a
   la promesa que el autor eligio; quien los creo fue `canon/` al consolidar.

## Que detecta v1, y que no

La extraccion determinista de v1 tiene dos detectores, y los dos miran a lo que
el esquema **ya declara** para ver que se salio de ahi:

- **Entidad no canonica**: un nombre propio de la prosa aceptada que no es
  ninguna entidad de la obra ni ningun termino canonico. Es lo que `P-25` llama
  «un nombre propio nuevo se detecta».

  Se lee la **prosa**, no el enunciado de los hechos consolidados, y la
  diferencia es todo el punto: los hechos son lo que el plan ya recogio, asi que
  un extractor que solo los leyera encontraria unicamente lo que ya se sabia.
- **Motivo no declarado**: un `Motivo` cuya forma aparece en la escena sin que
  nadie la haya registrado como aparicion suya. Una recurrencia que emergio sin
  que el plan la pusiera ahi.

Lo que **no** detecta, y esta escrito porque callarlo seria peor: el hecho
inventado sobre una entidad que ya existe --«el puerto llevaba anos cerrado»--
no tiene forma reconocible sin un modelo que lea. Esa mitad entra por
`Candidatura`, que es la via del `extractor`, y entra --como todo-- en estado
`propuesto`.

Y el punto ciego del detector de nombres propios, que se asume: no ve el nombre
propio que abre una frase, y confunde con un nombre propio cualquier palabra
capitalizada en mitad de una. El coste de equivocarse es una propuesta de mas en
una bandeja que el autor revisa, no una linea de canon.
"""

from __future__ import annotations

import re
import unicodedata

from app.canon import service as canon
from app.commons.db.conexion import Conexion
from app.commons.errores import (
    AdopcionSinDestino,
    AdopcionSoloDelAutor,
    ExtraccionSinConsolidar,
    TransicionInvalida,
)
from app.findings import repository, schemas
from app.findings.models import (
    TRANSICIONES_DEL_HALLAZGO,
    EstadoDeHallazgo,
    Extraccion,
    FuenteDelHallazgo,
    Hallazgo,
    ModoDeAdopcion,
    TipoDeHallazgo,
)
from app.novel import models as novel_models
from app.novel import service as novel

# Un nombre propio de una sola letra no es un nombre: es una inicial o un
# artefacto de puntuacion.
LONGITUD_MINIMA_DE_NOMBRE = 2

# Cierre de frase en espanol. Lo que va justo detras esta capitalizado por
# posicion y no por ser nombre propio, asi que no cuenta.
FIN_DE_FRASE = re.compile(r"[.!?\n…]+")

# Una cadena de palabras capitalizadas es un solo nombre: «La orilla norte» no
# son tres hallazgos.
NOMBRE_PROPIO = re.compile(
    r"[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ'-]*(?:\s+(?:de|del|la|las|los|el)"
    r"\s+[\wÁÉÍÓÚÜÑáéíóúüñ'-]+|\s+[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ'-]*)*"
)


# --- `extraer-hallazgos` --------------------------------------------------


def extraer(
    base: Conexion, escena_id: int, datos: schemas.PeticionDeExtraccion
) -> schemas.ResultadoDeExtraccion:
    """Lee una escena **ya consolidada** y deja sus hallazgos en `propuesto`.

    Es idempotente por escena y version: volver a extraer no duplica nada, y no
    es una comodidad sino una necesidad --el orquestador puede reintentar y la
    bandeja del autor no puede llenarse de copias--.
    """
    consolidada = canon.version_consolidada(base, escena_id)
    if consolidada is None:
        raise ExtraccionSinConsolidar(
            f"la escena {escena_id} no esta consolidada: la extraccion ocurre dentro del "
            "punto unico de promocion a memoria larga, no antes"
        )
    if consolidada != datos.version:
        raise ExtraccionSinConsolidar(
            f"la escena {escena_id} tiene consolidada la version {consolidada} y se pide "
            f"extraer de la {datos.version}"
        )

    ya_hecha = repository.extraccion_de(base, escena_id, datos.version)
    if ya_hecha is not None:
        return _resultado(base, ya_hecha)

    propuestas = [
        *_entidades_no_canonicas(base, datos.texto),
        *_motivos_no_declarados(base, escena_id, datos.texto),
        *(
            (
                candidatura.tipo,
                candidatura.texto,
                FuenteDelHallazgo.CANDIDATURA,
                candidatura.confianza,
            )
            for candidatura in datos.candidaturas
        ),
    ]
    extraccion = repository.guardar_extraccion(
        base,
        escena_id,
        datos.version,
        entradas="prosa aceptada de la escena, entidades de la obra y motivos declarados",
        registro_id=datos.registro_id,
        propuestas=propuestas,
    )
    return _resultado(base, extraccion)


def _resultado(base: Conexion, extraccion: Extraccion) -> schemas.ResultadoDeExtraccion:
    return schemas.ResultadoDeExtraccion(
        extraccion_id=extraccion.id,
        escena_id=extraccion.escena_id,
        version=extraccion.version,
        hallazgos=repository.hallazgos_de_la_extraccion(base, extraccion.id),
    )


Propuesta = tuple[TipoDeHallazgo, str, FuenteDelHallazgo, float | None]


def _entidades_no_canonicas(base: Conexion, texto: str) -> list[Propuesta]:
    conocidos = _nombres_conocidos(base)
    propuestas: dict[str, Propuesta] = {}
    for nombre in nombres_propios(texto):
        if _normalizar(nombre) in conocidos:
            continue
        propuestas.setdefault(
            nombre,
            (TipoDeHallazgo.PERSONAJE, nombre, FuenteDelHallazgo.ENTIDAD_NO_CANONICA, None),
        )
    return list(propuestas.values())


def nombres_propios(texto: str) -> list[str]:
    """Nombres propios del texto, saltando la palabra que abre cada frase.

    La que abre una frase esta capitalizada por posicion, no por ser nombre, y
    contarla llenaria la bandeja de propuestas con la primera palabra de cada
    oracion. El precio es el declarado: el nombre propio que abre frase no se ve.
    """
    encontrados: list[str] = []
    for frase in FIN_DE_FRASE.split(texto):
        limpia = frase.strip()
        if not limpia:
            continue
        # Se descarta la primera palabra recortandola, no filtrando despues: si
        # el nombre propio ocupa las dos primeras palabras, la segunda sigue
        # contando.
        _, _, resto = limpia.partition(" ")
        encontrados += [
            coincidencia.group(0).strip()
            for coincidencia in NOMBRE_PROPIO.finditer(resto)
            if len(coincidencia.group(0).strip()) >= LONGITUD_MINIMA_DE_NOMBRE
        ]
    return encontrados


def _nombres_conocidos(base: Conexion) -> set[str]:
    """Todo lo que la obra ya nombra. Lo que no esta aqui es un descubrimiento."""
    con_nombre = (
        novel_models.Personaje,
        novel_models.Lugar,
        novel_models.Artefacto,
        novel_models.Faccion,
        novel_models.Arco,
        novel_models.HiloDeTrama,
        novel_models.Tema,
        novel_models.Motivo,
        novel_models.Novum,
    )
    conocidos: set[str] = set()
    for modelo in con_nombre:
        for entidad in novel.listar(base, modelo):
            conocidos |= _partes(str(entidad.nombre))  # type: ignore[attr-defined]
    for termino in novel.listar(base, novel_models.TerminoCanonico):
        conocidos |= _partes(termino.forma)
    return conocidos


def _partes(nombre: str) -> set[str]:
    """El nombre entero y cada una de sus palabras.

    «La orilla norte» tiene que reconocerse entera y tambien cuando el texto
    dice solo «Orilla»: un detector que exige la forma completa propone como
    hallazgo cada mencion abreviada de lo que ya existe.
    """
    normalizado = _normalizar(nombre)
    return {normalizado} | {palabra for palabra in normalizado.split() if palabra}


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )
    return " ".join(sin_tildes.split())


def _motivos_no_declarados(base: Conexion, escena_id: int, texto: str) -> list[Propuesta]:
    """Un motivo que asoma en la escena sin que nadie registrara la aparicion."""
    declarados = _motivos_declarados_en(base, escena_id)
    normalizado = _normalizar(texto)
    return [
        (
            TipoDeHallazgo.MOTIVO,
            motivo.nombre,
            FuenteDelHallazgo.MOTIVO_NO_DECLARADO,
            None,
        )
        for motivo in novel.listar(base, novel_models.Motivo)
        if motivo.id not in declarados and motivo.forma and _normalizar(motivo.forma) in normalizado
    ]


def _motivos_declarados_en(base: Conexion, escena_id: int) -> set[int]:
    return {
        int(fila["motivo_id"])
        for fila in base.execute(
            "SELECT motivo_id FROM motivo_escena WHERE escena_id = ?", (escena_id,)
        )
    }


# --- Adopcion: solo el autor ----------------------------------------------


def decidir(
    base: Conexion,
    hallazgo_id: int,
    decision: schemas.DecisionDelAutor,
    *,
    modo: ModoDeAdopcion = ModoDeAdopcion.AUTOMATICA,
) -> Hallazgo:
    """Mueve un hallazgo por su ciclo de vida. **Solo el autor humano.**

    Adoptar un hallazgo equivale a cambiar la novela que se esta escribiendo:
    es donde el metodo hibrido concentra el juicio que ningun modelo puede
    sustituir. El defecto del modo es `AUTOMATICA` para que ninguna llamada que
    se olvide del argumento adopte nada.

    En v1 **todas** las transiciones son del autor, tambien las de salida de
    `conflictivo`: quien las daria de oficio es el `replanificador`, y el bucle
    largo queda fuera del corte.
    """
    if modo is not ModoDeAdopcion.HUMANA:
        raise AdopcionSoloDelAutor(
            f"el hallazgo {hallazgo_id} solo lo mueve el autor humano: ningun agente adopta, "
            "descarta ni integra un hallazgo"
        )

    hallazgo = repository.obtener_hallazgo(base, hallazgo_id)
    if decision.destino not in TRANSICIONES_DEL_HALLAZGO[hallazgo.estado]:
        raise TransicionInvalida(
            f"el hallazgo {hallazgo_id} esta en '{hallazgo.estado.value}' y el diagrama no "
            f"dibuja una transicion a '{decision.destino.value}'"
        )
    if decision.destino is EstadoDeHallazgo.ADOPTADO and not _tiene_destino(decision):
        raise AdopcionSinDestino(
            f"el hallazgo {hallazgo_id} se adopta sin decir como que: hace falta el hecho "
            "canonico, la promesa, el motivo o el personaje en que se convierte"
        )
    return repository.actualizar_estado(base, hallazgo_id, decision.destino, decision)


def _tiene_destino(decision: schemas.DecisionDelAutor) -> bool:
    return any((decision.hecho_id, decision.promesa_id, decision.motivo_id, decision.personaje_id))


# --- Consultas ------------------------------------------------------------


def hallazgos_de(base: Conexion, escena_id: int) -> list[Hallazgo]:
    return repository.hallazgos_de_la_escena(base, escena_id)


def propuestos(base: Conexion) -> list[Hallazgo]:
    """La bandeja del autor. Es lo unico que hay que revisar a mano."""
    return repository.hallazgos_en(base, EstadoDeHallazgo.PROPUESTO)


def adoptados(base: Conexion) -> list[Hallazgo]:
    return repository.adoptados(base)


def adoptados_desde(base: Conexion, posicion: int) -> list[Hallazgo]:
    """Los que `canon_huerfano` cuenta: adoptados despues del ultimo hito."""
    return repository.adoptados_desde(base, posicion)


__all__ = [
    "adoptados",
    "adoptados_desde",
    "decidir",
    "extraer",
    "hallazgos_de",
    "nombres_propios",
    "propuestos",
]
