---
description: Fases 4 y 5. Revisión global del manuscrito completo y ensamblado de manuscrito.md.
argument-hint: "[saltar-revision]"
---

# Entregar la novela

Argumento recibido: `$ARGUMENTS`.

## Comprobaciones

1. Todos los capítulos de la escaleta existen en `novela/capitulos/`. Si falta
   alguno: dilo, indica cuál, y para.
2. `python scripts/medir.py --todos`: si alguno está fuera de norma, avisa y
   pregunta si seguir.

## Fase 4 — Revisión global

Salvo que el argumento sea `saltar-revision`:

1. `python scripts/eventos.py --evento fase_inicio --fase revision`
2. Ejecuta `python scripts/repeticion.py --global` y
   `python scripts/continuidad.py --global`.
3. Invoca al subagente `revisor-global`, pasándole ambas salidas.
4. Muestra el informe completo al autor.
5. Si el veredicto es `REQUIERE CORRECCIONES`:
   - Lista los capítulos afectados.
   - Pregunta al autor si quiere regenerarlos. Si dice que sí, aplica la skill
     `escribir-capitulo` a cada uno, en orden ascendente, con las correcciones
     propuestas como entrada.
   - Vuelve al paso 3 una sola vez. Si sigue sin aprobarse, escala al autor y
     no entres en bucle.
6. `python scripts/eventos.py --evento fase_fin --fase revision` y commit.

## Fase 5 — Entrega

1. `python scripts/eventos.py --evento fase_inicio --fase entrega`
2. Ejecuta:

```powershell
python scripts/ensamblar.py
```

3. Comprueba que `manuscrito.md` existe y que contiene todos los capítulos.
4. `python scripts/eventos.py --evento fase_fin --fase entrega`
5. Commit según la skill `bitacora`.
6. Di al autor: ruta del manuscrito, número de capítulos, tamaño total en la
   unidad configurada, y si `git.push_automatico` es `false`, recuérdale
   `git push origin main`.

## Nota

No se genera PDF. La entrega es `manuscrito.md`.
