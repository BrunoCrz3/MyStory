---
name: manuscript-export
description: Usar al ensamblar el manuscrito final, al generar el PDF o al añadir un formato de salida nuevo como DOCX o EPUB.
---

# Exportación del manuscrito

`out/<pid>/manuscrito.md` es la **fuente canónica**. PDF, DOCX y EPUB son
derivados y **nunca se editan directamente**: si hay que corregir algo, se
corrige el capítulo y se vuelve a exportar.

## Estructura canónica del Markdown

```markdown
# <título de la novela>

> <logline>

---

## Capítulo 1 — <título>

<prosa del capítulo>

## Capítulo 2 — <título>
…
```

Reglas del ensamblado (`src/novela/export/assembler.py`):

- Los capítulos se ordenan por número y se toma la **versión vigente** de cada
  uno.
- El título de cada capítulo sale del Revisor global si existe; si no, del
  `working_title` de la escaleta.
- El cuerpo no lleva encabezados, viñetas ni numeración: el validador de
  longitud los rechaza con `LEN-FORBIDDEN-FORMAT`.

## Generación del PDF

`src/novela/export/pdf.py` intenta Pandoc si está en el PATH. Si no lo está,
usa un generador de respaldo mínimo y **nunca rompe el pipeline**: el Markdown ya
es el entregable.

Para una salida tipográficamente seria, invoca la skill pública **`pdf`** sobre
`manuscrito.md` en lugar del generador de respaldo. Para una eventual salida
Word, la skill pública **`docx`** cubre el caso; el punto de extensión está
abierto pero DOCX y EPUB quedan fuera de la v0.1.

## Anexos que acompañan al manuscrito

En `out/<pid>/reports/`: `continuity.json`, `repetition.json`, `pacing.json`,
`corrections.json`, `bible.json`, `outline.json`, `ledger.json`.

## Checklist previo a entrega

- [ ] `novela export <pid> --format md,pdf` sin errores
- [ ] `python scripts/assert_demo_output.py` en verde si es la demo
- [ ] Número de capítulos igual a `novel.chapters`
- [ ] Longitud de cada capítulo dentro de `LengthSpec.bounds()`
- [ ] Cero hilos abiertos en `ledger.json`
- [ ] Ninguna incidencia bloqueante en `reports/chapter_*.json`
- [ ] Títulos de capítulo sin numerar y distintos del título de la novela
- [ ] El manuscrito no se ha editado a mano: es reproducible desde
      `config.snapshot.yaml` + `bible.json` + `outline.json` + las fixtures

## Mantenimiento de estas skills

Las cinco skills de `.claude/skills/` se mantienen con **`skill-creator`**.
