/-
Tipos y predicados de la cronología de una novela (spec 4, TO-064, TO-065).

Todo es `Nat` y `Option`: sin Mathlib (A-91). Los identificadores son sintéticos; el fichero
generado no lleva ningún texto de la novela (regla 11).

Dos ordenaciones, cada una para lo suyo: `momento` es el orden de narración y solo lo usa la
ubicación; `anio` es la cronología de la historia y lo usan las otras tres. Ninguna compara un
orden con el otro, así que una analepsis no es una incoherencia.

Un dato vacío (`none`) hace la comprobación vacuamente cierta: nunca se supone un valor. Y la
aritmética no resta, porque la resta de `Nat` trunca a cero y escondería un año anterior al
nacimiento (L-D07).
-/

namespace Cronologia

/-- Un personaje presente en un evento, con la edad que el texto le declara ahí. -/
structure Presencia where
  personaje : Nat
  edad : Option Nat

/-- Un evento de la versión: orden de narración, año de la historia, lugar y presentes. -/
structure Evento where
  id : Nat
  momento : Nat
  anio : Option Nat
  lugar : Option Nat
  presentes : List Presencia

/-- Un `Evento excluyente`: tras el evento `evento`, `personaje` no puede volver a aparecer. -/
structure Excluyente where
  evento : Nat
  personaje : Nat

/-- El año de nacimiento de un personaje que lo tiene. -/
structure Nacimiento where
  personaje : Nat
  anio : Nat

def estaEn (p : Nat) (e : Evento) : Bool :=
  e.presentes.any (fun pr => pr.personaje == p)

def anioDe (evs : List Evento) (id : Nat) : Option Nat :=
  (evs.find? (fun e => e.id == id)).bind (fun e => e.anio)

def nacimientoDe (ns : List Nacimiento) (p : Nat) : Option Nat :=
  (ns.find? (fun n => n.personaje == p)).map (fun n => n.anio)

/-- `lean_ubicacion` (O-14), en orden de narración: ningún presente en `e` está en otro
evento del mismo `momento` con un lugar distinto. -/
def ubicacionOk (evs : List Evento) (e : Evento) : Bool :=
  e.presentes.all fun pr =>
    evs.all fun otro =>
      !(otro.momento == e.momento && estaEn pr.personaje otro) ||
        match e.lugar, otro.lugar with
        | some a, some b => a == b
        | _, _ => true

/-- `lean_cronologia` (O-13), en la historia: ningún presente en `e` tiene un evento
excluyente de un año estrictamente anterior al de `e`. Mismo año no es violación. -/
def cronologiaOk (evs : List Evento) (xs : List Excluyente) (e : Evento) : Bool :=
  e.presentes.all fun pr =>
    xs.all fun x =>
      x.personaje != pr.personaje ||
        match anioDe evs x.evento, e.anio with
        | some ax, some ae => !(Nat.blt ax ae)
        | _, _ => true

/-- `lean_edad` (O-15): la edad declarada es `año − nacimiento` o uno menos, sin restar. -/
def edadOk (ns : List Nacimiento) (e : Evento) : Bool :=
  e.presentes.all fun pr =>
    match pr.edad, nacimientoDe ns pr.personaje, e.anio with
    | some d, some n, some a => d + n == a || d + n + 1 == a
    | _, _, _ => true

/-- `lean_nacimiento` (O-66): nadie está en un evento de un año anterior a su nacimiento.
Mismo año no es violación. -/
def nacimientoOk (ns : List Nacimiento) (e : Evento) : Bool :=
  e.presentes.all fun pr =>
    match nacimientoDe ns pr.personaje, e.anio with
    | some n, some a => Nat.ble n a
    | _, _ => true

end Cronologia
