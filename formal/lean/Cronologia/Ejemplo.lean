/-
Cronología fija de ejemplo: `lake build` en verde. Cubre lo que no debe fallar: una
analepsis (el evento 3 se narra después con un año anterior), un evento sin año, una edad
declarada correcta antes del cumpleaños, un personaje sin nacimiento, y una exclusión en el
mismo año en que el personaje aún aparece.
-/
import Cronologia.Basico

namespace Cronologia.Ejemplo

-- p1 nace en 1980; p2 no tiene fecha de nacimiento. Lugares 1 y 2.
-- Evento.mk id momento anio lugar presentes; Presencia.mk personaje edad.
def e1 : Evento := Evento.mk 1 101 (some 1990) (some 1) [Presencia.mk 1 (some 9), Presencia.mk 2 none]
def e2 : Evento := Evento.mk 2 102 none (some 2) [Presencia.mk 1 none]
def e3 : Evento := Evento.mk 3 201 (some 1985) (some 1) [Presencia.mk 1 (some 5)]
def e4 : Evento := Evento.mk 4 202 (some 1995) (some 2) [Presencia.mk 2 none]
def e5 : Evento := Evento.mk 5 301 (some 1995) none [Presencia.mk 2 none]

def eventos : List Evento := [e1, e2, e3, e4, e5]
def excluyentes : List Excluyente := [Excluyente.mk 4 2]
def nacimientos : List Nacimiento := [Nacimiento.mk 1 1980]

theorem ubicacion_e1 : ubicacionOk eventos e1 = true := by decide
theorem ubicacion_e3 : ubicacionOk eventos e3 = true := by decide
theorem ubicacion_e5 : ubicacionOk eventos e5 = true := by decide
theorem cronologia_e5 : cronologiaOk eventos excluyentes e5 = true := by decide
theorem edad_e1 : edadOk nacimientos e1 = true := by decide
theorem edad_e3 : edadOk nacimientos e3 = true := by decide
theorem nacimiento_e3 : nacimientoOk nacimientos e3 = true := by decide
theorem nacimiento_e2 : nacimientoOk nacimientos e2 = true := by decide

end Cronologia.Ejemplo
