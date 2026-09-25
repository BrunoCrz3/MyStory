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
| RT-004 | L10 del plan 4, 2026-09-25: el brief B2 de la evaluación (`ejemplos/evaluacion/brief-b2-incoherencia-temporal.json`), generado de principio a fin con el modelo real y el gate activo | La destinataria, nacida en 1990, conoce a su amiga en la feria de **1986**: una incoherencia temporal que el propio brief declara y que la entrevista no cruza | **Solo Lean**: `lean_nacimiento` avisa desde el capítulo 3 y rechaza la versión en el gate; ningún validador de capítulo lo señaló en ningún intento, y el judge llegó a citar «la referencia al verano de 1986» como hecho respetado. **Caso real**, no provocado (P-83) | TO-067 |
| RT-005 | Demo, 2026-09-25: regeneración dirigida de la novela de la demo (capítulos 1–6 y 8), capítulo 6 | **Discrepancia entre un validador semántico y uno programático**: en cada intento el judge da 0,93–1,00 a `cierre_arco` y el capítulo pasa el hook, y justo después el `cierre_arco` programático lo devuelve con 0,0 porque el registro de promesas sigue viendo una pendiente. El texto la paga según el judge; el extractor no registra el pago | **El programático, por exceso**: bloquea un capítulo que el judge da por bueno, cinco veces, hasta agotarlo; la regeneración se detiene y la novela sigue en su versión publicada. Ningún validador compara las dos lecturas | Post-demo 17 y 23 (`specs/progreso.md`) |

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

## RT-004 — El caso que solo detecta Lean: B2, incoherencia temporal

**Qué se hizo** (L10 del plan 4, TO-067). Se generó una novela completa con **exactamente** el
brief B2 que usará la evaluación, `ejemplos/evaluacion/brief-b2-incoherencia-temporal.json`
(ficticio): la destinataria nace el 15 de marzo de 1990 y el mismo brief dice que conoció a su
amiga «en el verano de 1986, en la feria del puerto de Cádiz», como recuerdo y como elemento
obligatorio. Backend real sobre una base propia, con el gate de Lean activo, el servidor
Playwright MCP y la página `lectura`; `proveedor: claude_code`. Commit del código `9f87263`,
traza `ce9ddeffad797dbade91bdc4e802bf0f`, 57 min, 1.110.227 tokens, **7,98 USD** nominales. El
resultado completo —scores de capítulo, veredictos del gate, auditoría, coste— está en
`ejemplos/evaluacion/resultado-b2.json` para que la evaluación lo reutilice sin regenerar
mientras el código no cambie.

**Por qué no se detuvo antes.** Las reglas de la entrevista solo cruzan la edad declarada con la
fecha de nacimiento (`intake/reglas.py`), y las dos cuadran: 36 años el 10 de octubre de 2026. Los
años de los recuerdos no los cruza nadie.

**Qué pasó, capítulo a capítulo.**

| Capítulo | Qué entra en la story bible | Lean incremental |
| --- | --- | --- |
| 1–2 | El capítulo 2 **alude** al verano de 1986, pero no lo narra: ningún evento con año | demostrado (sin nada temporal que comprobar) |
| 3 | «Maribel recuerda el verano de 1986…»: evento con año 1986, Maribel presente | **aviso**: `lean_nacimiento` falla en ese evento |
| 4, 10 | Dos eventos más de 1986 con Maribel presente | aviso, con los tres eventos |

**Quién lo vio.**

| Validador | Resultado |
| --- | --- |
| `consistencia_factica` programática y del judge | Pasa en el capítulo 3 (1,0 y 0,9). En el intento 1 del capítulo 5 el judge escribió que el capítulo **respeta** «la referencia al verano de 1986» |
| Los seis criterios del judge, `invencion_destinatario`, `nombres_exactos`, `reglas_mundo` | Pasan en todos los capítulos aceptados |
| Gate: `estructura_edicion`, `elementos_obligatorios`, `cierre_arco`, `render_visual` | Pasan |
| `lean_ubicacion`, `lean_cronologia`, `lean_edad` | Demostrados (la edad, vacuamente: el texto no declara la de Maribel en esos eventos) |
| **`lean_nacimiento`** | **Falla**: capítulos 3 (momento 304), 4 (404) y 10 (1007), año 1986, con Maribel presente |

**Desenlace.** La versión 1 queda `rechazada` por `GateEnRojo` —el único veredicto fallido es
`lean_nacimiento`, con los tres eventos nombrados en el audit log— y la generación se detiene
(`detenida_por: error-interno`, el motivo que ya usa el gate, A-47). Es el **caso real** que pide
el alcance § 5c y que P-83 pedía: una incoherencia que el texto contiene, que ningún otro
validador detectó, y que Lean detectó sin que nadie la inyectara a mano. El brief la provoca a
propósito (`verification.md` P-83 lo dice: es más débil que encontrarla en el uso normal); el
texto la escribió el modelo y la extrajo el extractor.

**Qué no demuestra.** Con qué frecuencia ocurre sin un brief que la busque, y lo que pasa cuando
el texto no fecha el recuerdo: en el capítulo 2 la alusión a 1986 no generó evento y Lean no la
vio (RT-003 lo muestra a escala de novela).

## RT-005 — El judge da la promesa por pagada y el registro no

**Qué pasó.** En la regeneración dirigida de la demo (generación `11061cc7`, capítulos 1–6 y 8
a reescribir), el capítulo 6 repitió el mismo patrón en cada intento del audit log:

| Intento | Veredicto del hook de capítulo | `cierre_arco` del judge | `cierre_arco` programático | Decisión |
| --- | --- | --- | --- | --- |
| 0 | `todos-los-validadores-que-cierran-pasan` | 0,95 (no cierra el paso) | 0,0 (cierra el paso) | devolver |
| 1 | ídem | 0,93 | 0,0 | devolver |
| 3 | ídem | 0,93 | 0,0 | devolver |
| 4 | ídem | 0,97 | 0,0 | devolver |
| 5 | ídem | 1,00 | 0,0 | `limite-de-intentos-agotado` |

El capítulo quedó `Agotado`, la generación `Detenida` con ocho capítulos aceptados, y la novela
sigue en su versión publicada (TO-062). El audit log no tiene fila del intento 2.

**Por qué discrepan.** Son dos validadores distintos con el mismo nombre. El del judge lee el
texto y juzga si el arco se cierra. El programático (`process/aceptar.py`, A-127/A-128 de
TO-047) no lee el texto: cuenta las promesas que el capítulo reescrito tenía que pagar y que el
**extractor** no registró como pagadas. Según el judge el texto paga la promesa; el extractor no
lo anota, y la cuenta programática manda porque es la única que cierra el paso. Es el riesgo que
TO-047 ya declaraba («la comprobación cuenta lo que el extractor registra») y que el ensayo vio
por primera vez (RI-033).

**Quién lo detectó.** El programático, **por exceso**: un falso negativo repetido que gasta los
cinco intentos (redactor, judge, editor y extractor cada vez) y detiene la regeneración. Ningún
validador compara la lectura del judge con la del extractor, así que la contradicción solo se ve
leyendo el audit log a mano, y el nombre compartido la esconde: dos filas `cierre_arco` seguidas,
0,97 y 0,0, parecen el mismo validador cambiando de opinión.

**Qué se hará** (post-demo, sin cambio de código ahora; `specs/progreso.md` § Post-demo):

- **17**: decirle al extractor qué promesas debe cerrar el capítulo y pedirle que confirme si el
  texto las resuelve, sin quitarle la posibilidad de decir que no.
- **23**: dar nombre propio a cada validador duplicado (`cierre_arco` programático, por ejemplo
  `promesas_pagadas`; revisar `consistencia_factica` y `schema_valido`, que salen dos veces en
  cada veredicto del hook).

**Qué no demuestra.** Cuál de las dos lecturas acierta: nadie ha leído el capítulo para decidir si
la promesa está pagada, y el judge también puede equivocarse (RT-004 lo vio dar por respetado un
año imposible).
