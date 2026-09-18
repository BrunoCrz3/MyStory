---
name: bitacora
description: Reglas de registro de eventos en novela/events.jsonl y de commits a Git. Úsala siempre que termines una fase, escribas o reescribas un capítulo, ejecutes una validación, o vayas a guardar el avance en el repositorio.
---

# Bitácora: eventos y commits

## Parte A — Eventos

Todo evento se escribe llamando al script. **Nunca escribas `events.jsonl` a mano
ni con otro script.** Es la única puerta de entrada, y eso es lo que permitirá
enchufar Langfuse después tocando un solo fichero.

```powershell
python scripts/eventos.py --evento <tipo> [--fase <fase>] [--capitulo <n>] [--intento <n>] [--datos "<json>"]
```

### Cuándo registrar, sin excepciones

| Momento | `--evento` | Campos adicionales |
|---|---|---|
| Empieza una fase | `fase_inicio` | `--fase canon|escaleta|redaccion|revision|entrega` |
| Termina una fase | `fase_fin` | `--fase ...` |
| Se genera un borrador | `borrador` | `--capitulo`, `--intento` |
| Termina una validación | `validacion` | `--capitulo`, `--intento`, `--datos` con métricas y recuento |
| Se reescribe entero | `reescritura` | `--capitulo`, `--intento` |
| Se parchean párrafos | `parche` | `--capitulo`, `--intento` |
| Empieza un capítulo | `capitulo_inicio` | `--capitulo` |
| Se cierra un capítulo | `capitulo_fin` | `--capitulo`, `--intento` |
| Se agotan los intentos | `escalado` | `--capitulo`, `--intento` |
| Se hace un commit | `commit` | `--datos` con el sha corto y el mensaje |

El identificador de tirada y la marca de tiempo los pone el script. Tú no los pasas.

### Qué NO se registra a mano

Los tokens y el modelo **no** se anotan a mano, y tampoco se escriben en
`events.jsonl`: ningún script llama a una API, así que el orquestador no los
ve. Existen en los transcripts de Claude Code, y el exportador los lee solo.

Cada vez que registras un evento, el exportador cosecha las llamadas de los
subagentes que ya han terminado y las manda a Langfuse con el evento. Es decir:
**el coste aparece en el panel durante la tirada, no al final.** No tienes que
hacer nada para que ocurra.

`retroalimentar.py` sigue existiendo para subir una tirada vieja, o para
recoger lo que quedó después del último evento:

```powershell
python scripts/retroalimentar.py --simular   # enseña qué subiría, sin subir
python scripts/retroalimentar.py             # lo sube a Langfuse
```

Es inocuo repetirlo: antes de enviar pregunta al panel qué tiene ya y omite lo
que sobra. Lo que **no** debes usar es `--reenviar-todo`, que se salta esa
comprobación y duplica en el panel todo lo que ya estuviera, inflando el coste.

Tampoco se anota el coste: no hay tabla de tarifas en el repositorio. Se envían
modelo y tokens, y Langfuse aplica la suya. Ver SPEC.md secciones 14.4 y 14.5.

Lo que sí se registra a mano son los sucesos del pipeline y los resultados de
las validaciones, con la tabla de arriba.

## Parte B — Commits

Lee `config.json` → `git`.

### Cuándo se hace commit

| Momento | Mensaje |
|---|---|
| Canon aprobado | `feat(canon): biblia narrativa de <titulo>` |
| Escaleta aprobada | `feat(escaleta): plan de N capitulos` |
| Capítulo cerrado y archivado (si `commit_por_capitulo` es `true`) | `feat(cap-NN): <titulo del capitulo>` |
| Revisión global terminada | `chore(revision): informe global` |
| Manuscrito ensamblado | `feat(entrega): manuscrito.md` |
| Escalado al autor | `wip(cap-NN): bloqueado tras N intentos` |

### Cómo

En PowerShell, siempre desde la raíz del repositorio:

```powershell
git add -A
git commit -m "feat(cap-01): Silencio en la siete" -m "3 hechos, 1 hilo abierto. 1 intento. Sin incidencias mayores."
```

El cuerpo del commit (el segundo `-m`) resume qué ha cambiado en el estado:
cuántos hechos, hilos y entidades ha añadido el archivista, y cuántos intentos
hicieron falta.

Al terminar, registra el evento:

```powershell
python scripts/eventos.py --evento commit --capitulo NN --datos "{\"sha\":\"<sha corto>\",\"mensaje\":\"<titulo>\"}"
```

### Push

Solo si `config.json` → `git.push_automatico` es `true`:

```powershell
git push origin main
```

Con el valor de partida (`false`), el push lo lanza el autor cuando quiere.

### Reglas

- Un commit por capítulo. No agrupes tres capítulos en un commit.
- El commit incluye siempre el estado: `novela/estado.json` va en el mismo
  commit que el capítulo que lo modificó. Por eso se usa `git add -A`.
- Nunca uses `--no-verify` ni `--force`.
- Si `git commit` falla porque no hay nada que comitear, no es un error: dilo y sigue.
