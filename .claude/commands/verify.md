---
description: Ejecuta make verify y resume solo los fallos, sin volcar la salida entera.
allowed-tools: Bash(make verify), Bash(make inventory), Bash(pytest *), Bash(ruff *), Bash(mypy *)
---

Ejecuta `make verify`.

Si pasa en verde, responde con **una sola línea** confirmándolo y nada más.

Si falla:

1. Identifica cuál de los seis pasos ha fallado: inventario, `ruff check`,
   `ruff format --check`, `mypy`, `pytest` o la demo.
2. Resume **solo los fallos**, agrupados por fichero. No vuelques la salida
   completa: es larga y casi toda irrelevante.
3. Por cada fallo, una línea con `ruta:línea` y la causa en lenguaje llano.
4. Termina con la acción mínima que lo arregla. No la apliques todavía.

Si fallan varios pasos, ordénalos por cuál hay que arreglar primero: el
inventario antes que el lint, el lint antes que los tipos, los tipos antes que
los tests.
