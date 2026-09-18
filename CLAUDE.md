# Reglas permanentes de este repositorio

Este repositorio genera novelas cortas de ciencia ficción. Tú, Claude Code,
eres el orquestador. No hay ningún servicio de modelo externo.

## Invariantes

1. La memoria del proyecto vive en `novela/`, nunca en la conversación.
   Antes de escribir cualquier capítulo, lee `novela/estado.json`,
   `novela/canon.md` y `novela/escaleta.json`. No te fíes de lo que creas recordar.
2. Los capítulos se escriben en orden. Nunca empieces el capítulo i+1 si el i
   no está cerrado y archivado.
3. Solo el subagente `archivista` escribe en `novela/estado.json`. Ningún otro
   agente y ningún otro proceso lo modifica.
4. `novela/canon.md` está congelado desde que el autor lo aprueba. Si un
   capítulo lo contradice, se corrige el capítulo, nunca el canon.
5. Toda validación se ejecuta con los scripts de `scripts/`. No estimes
   longitudes ni repeticiones "a ojo": ejecuta el script y lee su salida.
6. Después del estilista se vuelve a medir la longitud. Siempre.
7. Tras 3 reescrituras fallidas del mismo capítulo, para y avisa al autor.
8. Todo suceso relevante se registra con `python scripts/eventos.py`.
   Ver la skill `bitacora`.
9. La exportación a Langfuse vive en un solo sitio: `eventos.registrar()`
   llamando a `observabilidad.exportar()`. No la repartas por los agentes ni
   por el orquestador. `events.jsonl` es la fuente de verdad y nunca se apaga;
   un fallo de Langfuse nunca interrumpe la generación.

## Prohibiciones

- No instales dependencias. Solo biblioteca estándar de Python 3.12.
  `requirements-opcional.txt` es opcional de verdad: no se instala, y el
  sistema entero funciona sin él.
- No crees ficheros nuevos fuera del inventario de SPEC.md sección 16 sin
  que el autor lo pida.
- No escribas código Python que llame a un modelo de lenguaje.
- No leas variables de entorno **salvo en `scripts/observabilidad.py`**, que es
  el único módulo que habla con Langfuse y el único que puede leer
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` y `LANGFUSE_BASE_URL`. **Las dos
  claves no se imprimen nunca**, ni completas ni parciales, ni en un error ni
  en un diagnóstico: si falta alguna, di cuál por su nombre y nada más. El
  **host** de destino sí se muestra, a propósito, en la línea de arranque: no
  es un secreto, y saber contra qué servidor se traza es media diagnosis.
  `LANGFUSE_BASE_URL` es opcional y su ausencia nunca apaga la exportación:
  hay valor por defecto en el código. Ningún otro script lee el entorno, y no
  hay claves en el código ni en la configuración.
- No uses `make`, `rm -rf`, `test -f`, ni rutas tipo `.venv/bin`. Windows + PowerShell.
- No reescribas `config.json`.

## Cómo invocar a los especialistas

Usa el subagente adecuado en lugar de hacer tú el trabajo creativo:
`arquitecto`, `escaletista`, `escritor`, `continuista`, `estilista`,
`archivista`, `revisor-global`. Están en `.claude/agents/`.
