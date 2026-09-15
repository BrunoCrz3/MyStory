---
description: Lanza el subagente threshold-calibrator sobre los informes de out/ para proponer umbrales.
argument-hint: <perfil: micro o full>
---

Lanza el subagente `threshold-calibrator` sobre los informes disponibles en
`out/**/reports/` para el perfil **$1**.

Pásale estas instrucciones:

> Reúne las métricas de todos los `reports/chapter_*.json` y
> `reports/repetition.json` que encuentres en `out/`. Calcula mínimo, mediana,
> p90 y máximo de cada métrica. Propón umbrales para
> `config/profiles/$1.yaml` y devuelve el bloque YAML listo para pegar.
> Indica el tamaño de muestra y advierte si es insuficiente.

Cuando devuelva el resultado:

1. Reproduce la tabla y el bloque YAML.
2. **No edites `config/profiles/$1.yaml`.** La decisión es del mantenedor.
3. Si el perfil es `micro`, recuerda que desactiva `jaccard_blocking` y
   `cosine_scene_blocking` a propósito: proponer activarlos sobre una muestra
   de tres capítulos es un error, no una mejora.
4. Sugiere abrir una issue con la plantilla `calibration.yml` pegando las
   métricas.
