---
name: narrative-canon
description: Usar al crear o editar la biblia narrativa, personajes, reglas del mundo o glosario, y al decidir si un cambio del canon puede promoverse sin romper capítulos ya escritos.
---

# Canon narrativo

El canon vive fuera del contexto del modelo, en `bible.json` y `ledger.json`. Lo
que no esté escrito ahí, no existe.

## Checklist de un canon sólido

1. **Logline** con protagonista, deseo y obstáculo concreto. Si cabe cualquier
   novela dentro, está mal.
2. **Tema** formulado como tensión, no como palabra suelta. «La memoria» no es
   un tema; «recordar es una forma de no perdonar» sí.
3. **Personajes**: `want` (lo que persigue) y `need` (lo que le falta) distintos.
   Si coinciden, no hay arco. Dos personajes con el mismo rol y el mismo `want`
   son el mismo personaje escrito dos veces → `BIB-CONTRADICTION`.
4. **Voz** declarada y reconocible: léxico, longitud de frase, qué evita decir.
   Es lo que después juzga `CONT-VOICE-DRIFT`.
5. **Localizaciones** con una propiedad que genere escena, no solo decorado.

## Toda tecnología necesita límites y coste

Es la regla que más incoherencias evita aguas abajo, y la que más se incumple.

- `limits`: qué NO puede hacer. Cada límite debe poder generar una escena. Si no
  puede, no es un límite, es un adorno → `BIB-NO-LIMITS`.
- `cost`: qué se paga cada vez que se usa, y **quién** lo paga.

Una tecnología sin límites destruye el conflicto: si el aparato puede resolverlo
todo, la única razón de que no lo haga es que el autor no quiere.

Los límites no son decorativos en el código: `validators/continuity.py` los usa
literalmente para detectar `CONT-RULE-VIOLATION`, comparando las palabras
significativas de cada límite contra cada frase del capítulo. Un límite vago no
detecta nada.

## Formato de un CanonFact

```json
{"id": "f_2_loc", "subject": "chr_1", "predicate": "ubicacion",
 "value": "Sala del Oráculo", "chapter_established": 2,
 "status": "vigente", "revoked_by": null,
 "evidence": "cita literal del capítulo, máximo 200 caracteres"}
```

- `predicate` usa vocabulario cerrado: `estado_vital`, `ubicacion`, `posee`,
  `sabe`, `relacion`.
- `evidence` es una cita **literal**. Un hecho sin cita es una inferencia, y el
  Archivista tiene prohibido inferir.
- Dos hechos `vigente` con el mismo `(subject, predicate)` y distinto `value`
  son `CONT-FACT-CONFLICT`, bloqueante.

## Cambiar el canon sin romper lo escrito

La política es **congelar lo aprobado** (§20, punto 3):

1. Los hechos **se revocan, no se borran**: emite el hecho anterior con
   `status: "revocado"` y `revoked_by` apuntando al que lo sustituye.
2. Un cambio del canon marca `stale` los capítulos afectados. `novela status`
   los lista.
3. Nada se regenera sin confirmación explícita del autor. El sistema avisa,
   propone y espera; nunca trunca ni improvisa.
4. Solo el Archivista escribe en el ledger, y solo vía
   `store.commit_chapter`, en una transacción por capítulo.

## Antes de dar el canon por bueno

- [ ] `limits` y `cost` sustantivos (más de 15 caracteres y con consecuencia)
- [ ] Ningún `pov_character_id` ni `location_id` de la escaleta sin respaldo
- [ ] `want` ≠ `need` en todos los personajes
- [ ] `motifs` son imágenes concretas, no temas abstractos
- [ ] `novela bible <pid>` sin incidencias bloqueantes
