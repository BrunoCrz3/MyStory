# Contribuir a novela-agent

## Antes de nada

```bash
make install
make verify
```

`make verify` debe pasar en verde **sin red y sin clave de API**. Si algo falla
por falta de credenciales, es un bug de la implementación, no de tu entorno.

## Convención de commits

[Conventional Commits](https://www.conventionalcommits.org/). Un commit por paso
lógico; el historial es parte del entregable.

```
feat(validators): add lexical diversity check to repetition
fix(config): deep-merge nested blocks instead of replacing them
docs(skills): clarify when to use continuity-audit
test: add regression for CONT-LOCATION-IMPOSSIBLE
chore(ci): pin python to 3.12
```

Ámbitos en uso: `config`, `models`, `store`, `llm`, `agents`, `validators`,
`context`, `orchestrator`, `cli`, `export`, `skills`, `harness`, `ci`.

Reglas:

- Cada commit deja el repositorio **compilable** y `make verify` en verde.
- Los commits que cierran un criterio de aceptación de §16 lo citan en el
  cuerpo: `Closes T-06.`
- Nada de commits gigantes con todo el trabajo de una semana.

## Cómo correr los tests

```bash
make test                              # la suite entera
pytest tests/test_repetition.py -q     # un fichero
pytest -k "beat_coverage" -q           # un caso
pytest -q --cov=src/novela --cov-report=term-missing
```

Cobertura mínima: **80 % en `src/novela/validators/` y
`src/novela/orchestrator/`**, y 80 % global en CI.

Ningún test puede usar red ni clave de API. Si necesitas un proveedor,
usa `FakeLLM`; si necesitas HTTP, usa `httpx.MockTransport`.

## Cómo añadir un validador nuevo

1. **Escribe el test primero**, con el caso que debe disparar la incidencia **y**
   el caso que no debe. Sin el segundo, un validador que siempre emite pasaría.
2. Añade el código de incidencia a `DEFAULT_SEVERITY` en
   `src/novela/validators/base.py`. Los códigos son una **lista cerrada**: si
   añades uno, actualiza también §5 del spec y la skill `continuity-audit`.
3. Implementa la comprobación como una función `_check_*` privada y llámala
   desde la función `validate` del módulo.
4. **Registra siempre la métrica** en `ValidationReport.metrics`, aunque no
   emitas incidencia. Es lo que permite calibrar después con datos.
5. Los umbrales llegan en la configuración (`RepetitionCfg`, `ContinuityCfg`),
   **nunca** codificados en el módulo.
6. Comprueba que `make demo` sigue sin incidencias: un validador que dispara
   sobre las fixtures del repositorio está mal calibrado o mal implementado.

Restricciones del subsistema: un validador no escribe nunca en el store,
ninguna función pasa de 50 líneas, y `mypy --strict` queda limpio.

## Cómo calibrar umbrales

Los valores de `config/profiles/full.yaml` son un punto de partida razonable, no
valores medidos.

1. Genera dos o tres obras completas con `profile: full` y un proveedor real.
2. Reúne las métricas de `out/<pid>/reports/chapter_*.json` y
   `out/<pid>/reports/repetition.json`.
3. Mira la **distribución** (mediana, p90), no el máximo.
4. Lee a mano los capítulos del percentil alto: ¿repiten de verdad?
5. Sitúa el umbral bloqueante por encima del ruido observado. Si cae dentro de
   la nube de valores normales, el pipeline se pasará la vida reescribiendo.
6. Abre una issue con la plantilla `calibration.yml` pegando las métricas.

**Con menos de diez capítulos la varianza supera a la señal.** Un umbral
calibrado sobre tres capítulos no mide repetición: mide qué tres capítulos te
tocaron. Por eso `micro` desactiva esas severidades en lugar de bajarlas.

## Cómo tocar las fixtures

No edites los JSON de `fixtures/llm/` a mano. Cambia `scripts/make_fixtures.py`
y ejecútalo: genera **y verifica** la coherencia cruzada.

```bash
python scripts/make_fixtures.py
python -m novela demo && python scripts/assert_demo_output.py
```

Unas fixtures incoherentes hacen que los tests pasen **sin probar nada**, que es
peor que un test en rojo.

## Antipatrones que se rechazan en revisión

- Contar líneas o palabras fuera de `validators/length.py::count_units`.
- Cualquier constante de número de capítulos o de longitud en el código.
- Escribir en el ledger desde un agente o un validador.
- Paralelizar la generación de capítulos.
- Parsear salidas del modelo con expresiones regulares en lugar de JSON+Pydantic.
- Regenerar un capítulo entero cuando solo hay incidencias mayores.
- Umbrales codificados en el módulo que los aplica.
- Leer YAML, `os.environ` o flags de CLI fuera de `config.py`.
- Ignorar en silencio una clave desconocida de configuración.
- Cachear la configuración entre invocaciones.
- Meter el prompt completo en los logs.
- Tests que requieran red o clave de API.
- Capturar excepciones de forma genérica y continuar en silencio.

## Secretos

Ninguna clave, token ni credencial entra en el repositorio, ni siquiera en
fixtures, tests o ejemplos. Solo nombres de variable y marcadores tipo
`TU_CLAVE_AQUI`. Si alguna vez se filtra una clave, **se rota**: borrar el commit
no basta.
