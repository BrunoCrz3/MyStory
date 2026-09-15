---
description: Lanza el subagente spec-auditor contra una sección concreta del BUILD_SPEC.
argument-hint: <sección, por ejemplo 9.4 o 24>
---

Lanza el subagente `spec-auditor` contra la sección **$1** de `BUILD_SPEC.md`.

Pásale estas instrucciones:

> Audita la sección $1 de BUILD_SPEC.md contra la implementación actual.
> Devuelve la tabla de afirmaciones verificables con su estado (CUMPLE, DESVÍA o
> NO VERIFICABLE) y la evidencia con `ruta:línea`. No modifiques ningún fichero.

Cuando devuelva el resultado:

1. Reproduce su tabla tal cual.
2. Añade como máximo tres líneas propias señalando qué desviación arreglarías
   primero y por qué.
3. Si alguna desviación corresponde a un punto abierto de §20, compruébalo en
   `DECISIONS.md` antes de tratarla como un fallo: puede ser un valor por
   defecto aplicado a propósito.
