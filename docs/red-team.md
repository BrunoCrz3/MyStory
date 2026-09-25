# Red-team log

Un caso por cada intento adversarial o interferencia externa que se probó contra el sistema,
venga de un brief de prueba, del corpus de inyección (`A-95`) o de lo que apareció en una
ejecución real. Cada entrada nombra **qué validador lo detectó** —o que no lo detectó ninguno,
que es el caso que más vale— y el cambio que provocó (`docs/verification.md` § Enlace con el
red-team log, `E-19`).

| Caso | Origen | Qué se intentó o qué pasó | Quién lo detectó | Cambio |
| --- | --- | --- | --- | --- |
| RT-001 | Humo adversarial del P38 (cuatro ejecuciones reales) | Texto libre del comprador con una instrucción inyectada para el modelo | La instrucción **no llegó** a ninguna petición al modelo: el texto libre entra saneado y marcado como datos (`CLAUDE.md` regla 11). Las tres primeras ejecuciones se detuvieron por otros motivos (A-92, A-98, A-108); la cuarta publicó en verde | A-92, A-98, A-108 (`specs/progreso.md` § Coste real) |
| RT-002 | Ensayo de la demo, 2026-09-25, `proveedor: claude_code` | **Interferencia de las instrucciones de privacidad de la organización** en el subproceso del CLI: el redactor escribió `[NOMBRE_ANONIMIZADO]` nueve veces en lugar del nombre de la destinataria en el capítulo 10, y el judge citó fragmentos con `[PROFESION_OCULTA]` y `[SALUD_OCULTA]` | **Ninguno, al principio**: el capítulo se aceptó. Ahora: `nombres_exactos` (hook de capítulo, cierra el paso siempre) rechaza el marcador en el texto; `invencion_destinatario` coteja la cita del judge tratando el marcador como el trozo que sustituye | TO-056, TO-058, TO-061 |
| RT-003 | L09 del plan 4, 2026-09-25: la versión 3 publicada de la novela de la demo, re-extraída con el extractor nuevo **en una copia** de la base | Buscar una incoherencia temporal real en una novela ya publicada | **Nadie, y Lean tampoco**: el texto no declara ningún año, edad ni muerte o partida explícitos, así que tres de las cuatro invariantes quedan sin comprobar en los 48 eventos; la ubicación se demuestra (6 sin lugar). No es un caso que solo detecte Lean: es la razón de que el caso real salga de B2 | TO-067 |

## RT-002 — Anonimización impuesta por la organización

**Qué pasó.** Con `proveedor: claude_code` (TO-040), el redactor, el editor, el judge y el
extractor corren como subprocesos del CLI de Claude Code con la sesión del desarrollador. Su
organización tiene instrucciones de administrador que piden anonimizar datos personales, y esas
instrucciones llegan también al subproceso. El brief es ficticio (TO-052), pero el modelo
anonimizó igual:

- en la **salida del redactor**, el nombre de la destinataria del capítulo 10 salió como
  `[NOMBRE_ANONIMIZADO]`; los otros nueve capítulos la nombran;
- en las **citas del judge**, una profesión y un diagnóstico inyectados salieron como
  `[PROFESION_OCULTA]` y `[SALUD_OCULTA]`, lo que hacía que la cita no casara con el capítulo.

**Por qué no se detectó.** `nombres_exactos` buscaba nombres mal escritos, no nombres ausentes
(punto ciego declarado en O-02), y `invencion_destinatario` descartaba toda cita que no estuviera
literal en el capítulo (A-90).

**Qué lo detecta ahora.**

| Dónde aparece el marcador | Validador | Efecto |
| --- | --- | --- |
| Texto del capítulo | `nombres_exactos`, hook de capítulo | Falla y cierra el paso: el capítulo vuelve al editor o al redactor con el defecto (TO-056) |
| Cita del judge | `invencion_destinatario`, rol editor | El marcador vale por el trozo que sustituye, así que la invención cuenta (TO-058) |

**Qué no se hace.** No se añade a ningún prompt una instrucción para evitar la anonimización: es
una política del administrador de la organización y no corresponde a este repositorio esquivarla
(TO-061). Si el modelo insiste hasta agotar los intentos, la generación se detiene y lo dice
(regla 14). Las dos salidas legítimas están en TO-061.

## RT-003 — Lean sobre una novela publicada, en una copia

**Qué se hizo** (L09 del plan 4, TO-067). Se copió `data/storymaker-demo.db`, se migró la copia y
se volvieron a extraer con el extractor real —el que ya pide año, edades declaradas y
excluyentes— los diez capítulos de la versión 3 publicada de la novela de la demo, reemplazando
solo sus eventos **en la copia**. Después, el generador y `lake build`. La prueba compara el hash
de la base real antes y después (`6a0777ecfde99a7c…`, sin cambios): la story bible viva no se
tocó (regla 2). Prueba: `backend/tests/humo/test_lean_copia_real.py`, 5 min 53 s; traza
`41ca142437dcc661822be843c6f849cf`.

**Qué salió.**

| Invariante | Resultado | Sin comprobar |
| --- | --- | --- |
| `lean_ubicacion` | demostrado | 6 de 48 (eventos sin lugar) |
| `lean_cronologia` | demostrado, vacuamente | 48 de 48 |
| `lean_edad` | demostrado, vacuamente | 48 de 48 |
| `lean_nacimiento` | demostrado, vacuamente | 48 de 48 |

El extractor no devolvió **ningún** año, edad ni exclusión: la novela transcurre en un presente
sin fechas y nadie muere ni se marcha para siempre. Es lo que TO-064 pide —nunca suponer un
valor—, y el recuento de «sin comprobar» impide presentarlo como una demostración.

**Qué enseña.** Lean solo caza lo que el texto fecha. En una novela que no fecha nada, tres de
las cuatro invariantes no tienen nada que comprobar, y eso no se arregla con Lean: se arregla
con un brief cuyos recuerdos lleven año. Por eso el caso que se presenta es B2 (RT-004).
