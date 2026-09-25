# Ejemplo del guardrail de palabras prohibidas

Dos ejemplos, y cada uno dice de dónde sale:

- **A · De una ejecución real**: la única coincidencia del guardrail en las ejecuciones reales
  que conservan base. Salió en la novela B2 del L10, no en la base de la demo, que no tiene
  ninguna.
- **B · Demostración sobre texto de ejemplo**: un párrafo real de *Soltar amarras* con tres
  palabras prohibidas añadidas **en memoria**, para enseñar los niveles y una variante que el caso
  real no cubre.

Ninguno llamó al modelo ni generó texto. Las bases se abrieron en solo lectura; la decisión del
policy engine del ejemplo B se simuló en una base temporal.

## A · Ejecución real: «Remedios» → «remedio»

**Dónde.** Novela B2 (`data/storymaker-b2.db`), capítulo 6, primer borrador (intento 0),
2026-09-25. El brief B2 veta el nombre «Remedios» (`palabras_prohibidas`, nivel `novela`).

**Qué pasó.** El guardrail normaliza los dos lados (minúsculas, sin acentos, sin signos, sin
plural, sin diminutivo o vocal final) y compara raíces. «Remedios» y «remedio» se quedan en la
misma raíz, `remedi`, así que el borrador que decía «remedio» —el sustantivo común, en minúscula—
se marcó como el nombre vetado.

| Paso | Valor real |
| --- | --- |
| Palabra vetada | `Remedios` · nivel `novela` · origen: brief |
| Fragmento del borrador | `remedio` (carácter 4383; el borrador rechazado no se guarda, regla 2) |
| Normalización | `Remedios` → `remedios` → `remedio` (plural) → `remedi` (vocal final); `remedio` → `remedi` |
| Tabla `coincidencia` | `palabra = Remedios`, `nivel = novela`, `inicio = 4383`, `fin = 4390`, `intento = 0`, `decision = devolver` |
| Defecto al redactor | «quita «remedio» en cualquiera de sus formas» |

**Audit log, tal como quedó** (dos entradas, en la misma transacción):

```json
{"regla": "palabra-prohibida", "resultado": "devolver",
 "entrada": {"intento": 0, "coincidencias": [{"palabra": "Remedios", "nivel": "novela", "inicio": 4383}]}}
{"regla": "validador-que-cierra-falla", "resultado": "devolver",
 "entrada": {"intentos": 0, "reescrituras_por_guardrail": 1,
             "veredictos": [{"nombre": "schema_valido", "pasa": true, "cierra_el_paso": true, "valor": 1.0},
                            {"nombre": "palabras_prohibidas", "pasa": false, "cierra_el_paso": true, "valor": 0.0}]}}
```

**Decisión.** Devolver al redactor: era la primera pasada con palabra vetada y el sublímite es 2
(`guardrail.max_reescrituras`, TO-014). El capítulo 6 se aceptó en el intento 2 y su texto final
no contiene ninguna forma de «remedio».

**Lo que enseña.** El veto funcionó, pero sobre una palabra que no era el nombre: un **falso
positivo por raíz compartida** entre un nombre propio y un sustantivo común. La prueba de falsos
positivos cubre subcadenas («Luis» no casa con «Luisa»), no raíces compartidas. Es un coste de
normalizar plurales y vocales finales, no un fallo del registro, y queda anotado para la
calibración del guardrail.

## B · Demostración sobre texto de ejemplo

**Texto.** La primera frase es real, del capítulo 1 de *Soltar amarras* (versión 1); la segunda se
añadió en memoria con tres palabras prohibidas:

> «Déjalas —dijo Ondina, y tiró suave de la correa—. **Anselmo** la llamó **imbécil** desde el
> muelle, y el **anselmito** de su sobrino se rio.

Palabras de la novela: `Anselmo` (el nombre vetado del brief de ejemplo). Perfil: 34 años,
cumpleaños.

| Fragmento | Palabra vetada | Nivel | Raíz normalizada | Variante |
| --- | --- | --- | --- | --- |
| `Anselmo` | `Anselmo` | `novela` | `anselm` | la forma exacta |
| `imbécil` | `imbécil` | `global` | `imbecil` | con acento: el acento se quita a los dos lados |
| `anselmito` | `Anselmo` | `novela` | `anselm` | diminutivo en minúscula |

**Decisión del policy engine**, simulada sobre una base temporal con el veredicto
`palabras_prohibidas` en rojo:

| Pasada con palabra vetada | Decisión | Regla en el audit log |
| --- | --- | --- |
| 1.ª | **devolver** al redactor | `validador-que-cierra-falla` |
| 2.ª seguida | **detener** la generación | `palabra-prohibida-persistente` |

```json
{"regla": "palabra-prohibida-persistente", "resultado": "detener",
 "entrada": {"intentos": 1, "reescrituras_por_guardrail": 2,
             "veredictos": [{"nombre": "palabras_prohibidas", "pasa": false, "cierra_el_paso": true, "valor": 0.0}]}}
```

## Qué prueba automática cubre cada caso

Todas en verde (35 de 35, `uv run pytest tests/guardrail tests/policy/test_policy.py
tests/process/test_capitulo.py`, 2026-09-25).

| Qué | Prueba | Resultado |
| --- | --- | --- |
| Nivel `global`, sin que nadie lo declare | `test_nivel_global_sin_que_nadie_lo_declare` | ✅ |
| Nivel `perfil` por edad y por ocasión | `test_nivel_perfil_depende_de_la_edad`, `test_nivel_perfil_depende_de_la_ocasion` | ✅ |
| Nivel `novela`, y gana el más restrictivo | `test_nivel_novela_y_gana_el_mas_restrictivo` | ✅ |
| Acento y plural | `test_acento_y_plural_se_normalizan` | ✅ |
| Mayúsculas | `test_mayusculas` | ✅ |
| Signos intercalados (`i-d-i-o-t-a`) | `test_signos_intercalados` | ✅ |
| Diminutivo | `test_diminutivo_regular` | ✅ |
| Cada una de las cinco transformaciones, apagada, deja pasar su variante | `test_cada_transformacion_apagada_deja_pasar_su_variante` (5 casos) | ✅ |
| La palabra de la lista también se normaliza | `test_la_normalizacion_se_aplica_a_la_palabra_tambien` | ✅ |
| Sin falsos positivos por subcadena | `test_no_hay_falsos_positivos_por_subcadena` | ✅ |
| Posición en el texto original y expresiones de varias palabras | `test_la_coincidencia_lleva_posicion_en_el_texto_original`, `test_expresion_de_varias_palabras` | ✅ |
| Coincidencias en su tabla y en el audit log | `test_coincidencias_quedan_registradas`, `test_palabra_vetada_se_registra_y_el_hook_de_capitulo_no_corre` | ✅ |
| Primera pasada: devolver | `test_un_validador_que_falla_devuelve_el_capitulo` | ✅ |
| Segunda pasada seguida: detener | `test_dos_pasadas_con_palabra_vetada_detienen`, `test_dos_pasadas_con_palabra_vetada_detienen_sin_tercer_intento` | ✅ |
| Raíz compartida entre nombre y sustantivo (el caso A) | **ninguna** | — sin cubrir |

## Versión para diapositiva

**El guardrail veta palabras en cualquiera de sus formas**

- Tres niveles: global, perfil del lector y lista del comprador; gana el más restrictivo.
- Normaliza los dos lados: mayúsculas, acentos, signos, plurales y diminutivos.
- Primera vez: vuelve al redactor. Segunda seguida: la generación se detiene.
- Caso real: vetó «remedio» por el nombre «Remedios», un falso positivo por la raíz compartida.

```text
ANTES      «…no había remedio…»                   (borrador, capítulo 6 de B2)
DETECCIÓN  remedio → remedi  =  Remedios → remedi  · nivel novela · carácter 4383
DECISIÓN   devolver al redactor (1.ª pasada; a la 2.ª, detener) → aceptado en el intento 2
```

La frase de «ANTES» es ilustrativa: el borrador rechazado no se guarda, así que se conocen el
fragmento («remedio») y su posición, no la frase entera.
