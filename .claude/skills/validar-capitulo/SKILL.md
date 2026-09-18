---
name: validar-capitulo
description: Ejecuta las tres validaciones de un capítulo (longitud, repetición, continuidad mecánica y continuidad de sentido) y fusiona los resultados en una sola lista de incidencias clasificadas por severidad. Úsalo cada vez que haya que juzgar si un borrador de capítulo es aceptable.
---

# Validar un capítulo

Entrada: el número de capítulo `NN`. Salida: una lista única de incidencias con
severidad, y el recuento por severidad.

## Orden de ejecución

El orden importa: lo barato y determinista va primero, para no gastar una
lectura completa del `continuista` en errores que un script detecta en un segundo.

### 1. Longitud

```powershell
python scripts/medir.py --capitulo NN
```

Devuelve JSON. Si `en_norma` es `false`, es una incidencia **bloqueante** de tipo
`longitud`. No sigas validando: devuélvelo al escritor con la cifra real y la
esperada. Es la corrección más barata que existe.

### 2. Repetición

```powershell
python scripts/repeticion.py --capitulo NN
```

Devuelve JSON con métricas e incidencias. Traducción de severidad:

| Hallazgo | Severidad |
|---|---|
| Frase de `frases_usadas` reproducida literalmente | mayor |
| Solape de n-gramas por encima de `max_solape_ngramas` | mayor |
| Tipo de apertura repetido más de lo permitido | mayor |
| Muletilla por encima de `max_muletilla_por_mil` | menor |
| Cierre del mismo tipo que el capítulo anterior | menor |

### 3. Continuidad mecánica

```powershell
python scripts/continuidad.py --capitulo NN
```

Devuelve JSON con las comprobaciones de la sección 11.3 del SPEC, cada una ya
etiquetada con su severidad. Úsalas tal cual.

### 4. Continuidad de sentido

Invoca al subagente `continuista` sobre NN, **pasándole la salida JSON del paso 3**
para que no repita el trabajo mecánico. Devuelve su propio JSON de incidencias.

## Fusión

1. Junta las incidencias de los pasos 1 a 4 en una sola lista.
2. Si dos incidencias apuntan a la misma cita y al mismo problema, deja una sola:
   la de mayor severidad.
3. Calcula el recuento: `{"bloqueante": X, "mayor": Y, "menor": Z}`.
4. **Persiste el informe completo.** Vuelca la respuesta JSON del `continuista`
   del paso 4 en un fichero temporal y pásasela al script, que reejecuta los
   tres validadores deterministas y guarda todo en
   `novela/informes/capitulo_NN.json`:

```powershell
python scripts/informes.py --capitulo NN --intento <intento> --continuista <fichero.json>
```

   Las métricas se guardan siempre, haya incidencias o no. Nunca escribas en
   `novela/informes/` a mano ni con otro script: `informes.py` es la única
   puerta. Esquema en SPEC.md sección 6.6.

5. Registra el resultado:

```powershell
python scripts/eventos.py --evento validacion --capitulo NN --intento <intento> --datos "<json compacto con metricas y recuento>"
```

6. Devuelve al procedimiento que te llamó: el recuento y la lista completa,
   con las bloqueantes primero.

## Reglas

- Nunca declares un capítulo válido sin haber ejecutado los cuatro pasos, salvo
  el atajo del paso 1.
- El informe se persiste **siempre**, también cuando el capítulo sale limpio y
  también cuando se toma el atajo del paso 1. Un informe sin incidencias no es
  un informe vacío: sus métricas son lo que permite calibrar los umbrales.
- Nunca estimes una métrica: ejecuta el script y lee su salida.
- Las incidencias menores se registran pero nunca detienen el flujo.
- Si un script falla al ejecutarse (no si encuentra incidencias: si falla),
  para y avisa al autor. Un validador roto es peor que ninguno.
