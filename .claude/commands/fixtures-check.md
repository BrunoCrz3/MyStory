---
description: Lanza el subagente fixture-smith para verificar la coherencia cruzada de las fixtures del FakeLLM.
allowed-tools: Bash(python scripts/make_fixtures.py), Bash(pytest *), Bash(python -m novela *)
---

Lanza el subagente `fixture-smith` para verificar `fixtures/llm/`.

Pásale estas instrucciones:

> Ejecuta `python scripts/make_fixtures.py` y comprueba las ocho reglas de
> coherencia cruzada. Si alguna falla, corrige `scripts/make_fixtures.py` —
> nunca los JSON a mano — y vuelve a ejecutarlo. Termina con
> `python -m novela demo`, `python scripts/assert_demo_output.py` y `pytest -q`
> en verde.

Cuando devuelva el resultado:

1. Confirma que `git diff --stat fixtures/` está vacío si no había nada que
   corregir: las fixtures deben regenerarse byte a byte idénticas.
2. Recuerda el criterio que más se incumple: unas fixtures incoherentes hacen
   que los tests pasen **sin probar nada**, que es peor que un test en rojo.
3. Si se ha cambiado el número de capítulos o la unidad de longitud, comprueba
   que `config/default.yaml` y `novela.example.yaml` siguen coherentes.
