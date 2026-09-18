# El ciclo de mejora

Un procedimiento que ajusta **una sola cosa** del sistema, comprueba con novelas
de verdad si el ajuste mejora algo, y para cuando lo consigue o cuando deja de
merecer la pena. No aprende solo ni cambia nada por su cuenta: prueba una lista
de ideas escritas de antemano y se queda con las que funcionan.

## Qué mejora

La **monotonía sintáctica** del escritor. La prosa es correcta, pero todas las
frases tienen la misma forma: larga, con punto y coma, una subordinada en medio
y un giro al final. En tres capítulos parece estilo; en dieciocho es un tic. Los
controles de repetición que ya existían no lo ven, porque miran las palabras, y
las palabras sí cambian.

El ciclo toca **un único fichero**: el prompt del escritor,
`.claude/agents/escritor.md`, y dentro de él solo un apartado marcado que añade
y quita él mismo. No toca umbrales, ni validadores, ni el canon, ni la
configuración. Si alguna vez hiciera falta cambiar algo más, el ciclo no lo
hace: para y lo dice.

## Cómo lo mide

Un número entre 0 y 1, donde **0 es máxima variedad**. Es la media de tres
cosas, que se apuntan siempre por separado:

| | Qué cuenta |
|---|---|
| **Apertura** | Cuánto pesa la forma de empezar más repetida. 0 si cada línea abre distinto, 1 si todas abren igual. |
| **Puntuación** | Qué proporción de líneas llevan punto y coma o un inciso entre rayas. La raya que abre un diálogo no cuenta. |
| **Uniformidad** | Si todas las frases miden más o menos lo mismo. Una mezcla de frases muy cortas y muy largas baja este número. |

Si la monotonía baja porque se desploma **uno solo** de los tres, el ciclo lo
marca como sospechoso: eso no es mejor ritmo, es un rasgo suprimido.

**La línea base es 0,2927**, medida sobre *El pagador de la 812* y congelada:
no se vuelve a calcular nunca. **La meta es 0,22.** Para comparar, la novela
anterior, *La sala de cotejo*, daba 0,6388 — ahí el tic estaba entero.

## Cómo se comprueba que un cambio sirve

Cada vuelta del ciclo hace esto, en este orden:

1. **Escribe la hipótesis antes de tocar nada**: qué cambia en el prompt y por
   qué debería bajar el número. Queda anotada antes de la prueba, no después.
2. **Genera dos novelas de 3 capítulos** con la misma premisa de siempre. Dos y
   no una, porque generar no da dos veces el mismo resultado.
3. **Mide las dos y se queda con el valor de en medio.**
4. **Adopta el cambio si baja un 3% o más y no rompe ningún guardarraíl.** Si
   no, lo revierte y prueba el siguiente.

### Los guardarraíles

Son **el objetivo real**; el número es solo el indicador. Sin ellos, el sistema
aprendería a bajar la monotonía escribiendo frases cortas y planas. Un cambio
que rompa cualquiera de estos se descarta **aunque el número mejore**:

- Ningún error de continuidad nuevo.
- Ningún error de longitud.
- Repetición de vocabulario no más de un 10% peor que la base.
- La novela no cuesta más de 1,5 veces lo que costaba.

> Una salvedad medida: la novela de referencia ya arrastra **tres** avisos de
> continuidad (el plan manda cerrar hilos que el archivista nunca registró como
> abiertos). No son culpa de la prosa y el escritor no puede arreglarlos, así
> que el límite es "ninguno **nuevo**". Si prefieres exigir cero absoluto, pon
> un `0` en `ciclo/linea-base.json`, en `errores_continuidad`.

### La confirmación final

Antes de cantar victoria, el ciclo genera **dos novelas con dos premisas que no
ha usado nunca** durante el ajuste. Si la mejora no se sostiene ahí, era
casualidad de esa premisa concreta y el ciclo continúa.

## Cuándo para

Por una de estas cuatro, y siempre dejando escrito cuál fue:

- **Éxito.** Llegó a 0,22 y se sostuvo con las dos premisas nuevas.
- **Agotamiento.** Tres vueltas seguidas sin mejorar un 3%. **Esto no es un
  fracaso**: significa que esta palanca está agotada y que la siguiente mejora
  hay que buscarla en otro sitio.
- **Presupuesto.** Se acabó el dinero o se probaron las 8 ideas de la lista. El
  saldo se comprueba **antes** de cada novela, nunca después.
- **Daño.** Un guardarraíl roto dos veces seguidas, o la monotonía empeora más
  de un 15%.

Pare por lo que pare, el repositorio queda **en el mejor estado conocido**: tu
novela vuelve tal como estaba y el prompt del escritor se queda solo con lo
adoptado. Nunca a mitad de un experimento.

## Qué recuerda

| Dónde | Qué hay |
|---|---|
| `ciclo/iteraciones.jsonl` | Una línea por hipótesis y otra por resultado: qué se cambió, las métricas, los guardarraíles, el veredicto y el coste. Para la máquina. |
| `ciclo/bitacora.md` | Lo mismo contado en prosa, **incluidos los fracasos**. Saber que pedir "varía el ritmo" en abstracto no funciona vale tanto como saber qué sí funciona. |
| `ciclo/prompts/` | Cada versión del prompt que se probó, entera, para poder volver atrás y comparar. |
| `ciclo/tiradas/` | Cada novela generada, con sus informes y su registro. |
| `ciclo/linea-base.json` | La línea base congelada y los guardarraíles de referencia. |
| `ciclo/premisas.json` | La premisa de ajuste y las dos de confirmación. |

## Cómo se lanza

```powershell
.\.venv\Scripts\python.exe ciclo\ciclo.py --arrancar
```

Otras dos formas:

```powershell
.\.venv\Scripts\python.exe ciclo\ciclo.py --estado       # por dónde va, sin gastar nada
.\.venv\Scripts\python.exe ciclo\ciclo.py --si-procede   # arranca solo si hace falta
```

`--si-procede` es el arranque automático: comprueba la monotonía media de las
tres últimas novelas y **solo arranca si pasa de 0,50**. Lánzalo al cerrar una
novela. Nunca arranca si hay una generación en marcha.

## Lo que cuesta

Una novela de 3 capítulos costó **8,24 USD** la última vez. Una vuelta del ciclo
son dos novelas, unos **16,50 USD**. Las 8 vueltas más la confirmación salen por
unos **148 USD**, y ese es el tope por defecto. Para gastar menos:

```powershell
.\.venv\Scripts\python.exe ciclo\ciclo.py --arrancar --presupuesto 40
```

Con 40 USD hace unas dos vueltas y para diciendo que se quedó sin saldo.
