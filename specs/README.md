# Specs

Ubicación canónica de las specs y los planes de v1. Una spec por cambio, numeración
correlativa y sin carpetas: `specN.md` y su `planN.md` al lado.

| Fichero | Qué es |
| --- | --- |
| `specN.md` | Qué se construye y por qué, con criterios de aceptación verificables |
| `planN.md` | Cómo se construye: pasos, ficheros, migraciones y las pruebas que se escriben primero |

Ambos abren con frontmatter —`estado`, `aprobada-por`, `fecha`—, nacen en `borrador` y solo
el desarrollador los mueve a `aprobada`. Las puertas están en `CLAUDE.md` § Ciclo de cambio.

Lo obsoleto no se borra ni se queda aquí: se mueve a `docs/specs/_archivo/` con
`estado: archivada`.
