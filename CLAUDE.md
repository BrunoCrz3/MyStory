# novela-agent

Harness multiagente que genera novelas de CF. Spec completo en BUILD_SPEC.md.

## Comandos

- `make verify`   — obligatorio antes de cualquier commit
- `make demo`     — pipeline completo offline (3 capítulos de 4 líneas)
- `make inventory`— comprueba los ficheros del inventario de §21

## Reglas permanentes

- Los capítulos se generan SECUENCIALMENTE. Nunca paralelizar.
- Contar líneas o palabras SOLO en `validators/length.py::count_units`.
- Ningún número mágico de capítulos o longitud en el código: todo viene de config.
- Solo el Archivista escribe en el estado del mundo, vía `store.commit_chapter`.
- Leer YAML, `os.environ` o flags de CLI SOLO en `config.py`. Los demás módulos
  reciben un `Config` ya resuelto.
- Los umbrales viven en `config/profiles/`, nunca en el módulo que los aplica.
- Un umbral `null` desactiva la severidad, no el cálculo de la métrica.
- Los hechos del ledger se revocan, no se borran.
- Los tests nunca usan red ni clave de API. El determinismo lo da `FakeLLM`.
- Nunca commitear `.env`, claves ni `out/`.
- Ninguna excepción se captura de forma genérica para continuar en silencio.

## Dos harnesses, no uno

- `src/` es el **runtime**: el pipeline Python que genera novelas. Todo lo que
  deba ejecutarse en producción sin Claude Code presente va aquí.
- `.claude/` es la **construcción**: ayudas para quien desarrolla este
  repositorio. Nunca contiene lógica del pipeline.

Meter lógica del pipeline en una skill, o pedirle a un subagente lo que debe
hacer un validador determinista, son los dos errores caros de este proyecto.

## Mapa

- Contratos de datos → BUILD_SPEC.md §5
- Validadores → §9    · Bucle de capítulo → §10
- Configuración → §3  · OpenRouter → §24
- Contexto y memoria → §8 y §26
- Inventario de entregables → §21

## Dónde va cada cosa

| Si la información es… | Va a… |
|---|---|
| Una regla siempre aplicable | este fichero |
| Un procedimiento para una tarea concreta | una skill de `.claude/skills/` |
| Una decisión de diseño y su motivo | `DECISIONS.md` |
| Una restricción que no puede depender del criterio del modelo | un hook |
| Una exploración costosa que devuelve poco | un subagente |
| Un dato del mundo narrativo | el ledger, vía Archivista |

Si tienes que repetir algo por tercera vez, deja de repetirlo y escríbelo aquí
o en una skill.

@docs/especificaciones_tecnicas.md
