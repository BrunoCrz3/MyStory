# El caso que solo detecta Lean

Caso de la presentación, a partir de las dos ejecuciones reales de Lean del plan 4: el L09
(una novela ya publicada, re-extraída en una copia) y el L10 (el brief B2 de la evaluación,
generado de principio a fin). Detalle y trazas en `docs/red-team.md` RT-003 y RT-004; resultado
completo en `ejemplos/evaluacion/resultado-b2.json`.

## Qué detectó Lean

**Un recuerdo fechado antes del nacimiento de la destinataria.** La novela de B2 cuenta que la
destinataria, nacida en 1990, conoció a su mejor amiga en la feria de 1986, y el extractor
registró ese recuerdo como un evento del año 1986 con ella presente.

- **Invariante que falló**: `lean_nacimiento`: ningún personaje participa en un evento de un año
  anterior a su nacimiento (O-66).
- **Dónde**: tres eventos de 1986 con la destinataria presente, que Lean nombra como `e12`
  (capítulo 3, el recuerdo de la feria), `e18` (capítulo 4, alguien habla de «la feria del 86»
  con ella delante) y `e58` (capítulo 10, «desde la feria de 1986 no se han separado nunca»).
- **Teoremas que no se demuestran**: `nacimiento_e12`, `nacimiento_e18` y `nacimiento_e58`.

Las otras tres invariantes pasaron: `lean_ubicacion` sobre 58 eventos (10 sin lugar), y
`lean_cronologia` y `lean_edad` sin nada que comprobar, porque el texto no declara ninguna
muerte, ninguna partida ni la edad de nadie en esos eventos.

## Por qué ningún otro validador lo detectó

| Validador | En el capítulo 3 | En el resto de la novela |
| --- | --- | --- |
| `consistencia_factica` programática | Pasa (1,0) | Pasa en los diez |
| `consistencia_factica` del judge | Pasa (0,9) | Pasa en nueve; en el capítulo 5 puntúa 0,85 (bajo su umbral, sin cerrar el paso) y su justificación dice que el capítulo **respeta** «la referencia al verano de 1986» |
| Los otros cinco criterios del judge | Pasan (0,88–0,95) | Pasan en los diez |
| `invencion_destinatario`, `temas_excluidos`, `nombres_exactos`, `reglas_mundo` | Pasan | Pasan en los diez |
| Entrevista (`intake/reglas.py`) | — | No la para: solo cruza la edad declarada (36) con la fecha de nacimiento, y cuadran |

Todos leen el texto y lo comparan con el canon o con el brief, y el brief **dice** que se
conocieron en 1986: para ellos, el recuerdo es fiel. Nadie resta años. Lean sí, porque compara el
año de cada evento con el de nacimiento de cada presente, en todos los eventos a la vez.

## Qué hizo el sistema

- **Avisó pronto**: el chequeo incremental falló tras aceptar el capítulo 3 y quedó en el audit
  log como `aviso`, sin detener la escritura (TO-016).
- **No publicó**: la versión 1 quedó `rechazada` por `GateEnRojo`. `lean_nacimiento` fue el
  **único** veredicto fallido del gate: `estructura_edicion`, `elementos_obligatorios`,
  `cierre_arco` y `render_visual` pasaron.
- **Devolvió el fallo al editor** con la invariante, el capítulo, el momento, el año y los
  personajes de cada evento, en el detalle de la detención (P-82).
- **No tocó ninguna versión vigente**: era la primera versión de una novela nueva, así que no
  había publicada que proteger. El caso de una regeneración rechazada con la publicada intacta se
  prueba en `tests/versioning/test_gate_lean.py`.

## ¿Real o provocado?

**Real** (spec 4 § 3.11, TO-067). El brief B2 busca la incoherencia a propósito —es lo que la
evaluación le pide—, pero **nadie la inyectó a mano**: el modelo escribió los capítulos, el
extractor fechó los eventos y Lean falló sobre esa story bible, sin tocar nada entre medias.

Lo que no demuestra, dicho también: con qué frecuencia pasa sin un brief que lo busque. En el L09,
la versión 3 publicada de la novela de la demo, re-extraída en una copia, no dio a Lean nada que
comprobar: la novela no fecha ningún evento (RT-003).

## El fichero Lean y la salida de `lake build`

Fragmento del `Cronologia/Hechos.lean` que el generador escribió desde la story bible de B2. Solo
identificadores sintéticos: ningún texto de la novela llega al compilador (regla 11). Los
comentarios son para leerlo aquí; en el fichero, cada identificador enlaza con su UUID.

```lean
-- e12: evento del capítulo 3 · p1: la destinataria · p2: su amiga
def e12 : Evento := Evento.mk 12 304 (some 1986) (some 3) [Presencia.mk 1 none, Presencia.mk 2 none]
def nacimientos : List Nacimiento := [Nacimiento.mk 1 1990]

-- Cronologia/Basico.lean: nadie está en un evento de un año anterior a su nacimiento
def nacimientoOk (ns : List Nacimiento) (e : Evento) : Bool :=
  e.presentes.all fun pr =>
    match nacimientoDe ns pr.personaje, e.anio with
    | some n, some a => Nat.ble n a
    | _, _ => true

theorem nacimiento_e12 : nacimientoOk nacimientos e12 = true := by decide
```

```text
error: Cronologia/Hechos.lean:327:67: Tactic `decide` proved that the proposition
  nacimientoOk nacimientos e12 = true
is false
error: Cronologia/Hechos.lean:333:67: Tactic `decide` proved that the proposition
  nacimientoOk nacimientos e18 = true
is false
error: Cronologia/Hechos.lean:373:67: Tactic `decide` proved that the proposition
  nacimientoOk nacimientos e58 = true
is false
error: build failed
```

Reproducido en local sobre la base de B2 en solo lectura (58 eventos, 1,7 s), sin llamar al
modelo.

## Versión para diapositiva

**Lean caza un recuerdo imposible**

- La destinataria nace en 1990; la novela la sitúa en la feria de 1986.
- Todos los demás validadores pasaron, y el judge dio la fecha por «respetada».
- `lean_nacimiento` no se demuestra en tres eventos: la versión no se publica.
- Caso real: ni el texto ni la story bible se tocaron a mano.

```lean
def e12 : Evento := Evento.mk 12 304 (some 1986) (some 3) [Presencia.mk 1 none, Presencia.mk 2 none]
def nacimientos : List Nacimiento := [Nacimiento.mk 1 1990]
theorem nacimiento_e12 : nacimientoOk nacimientos e12 = true := by decide
-- error: Tactic `decide` proved that the proposition … is false
```
