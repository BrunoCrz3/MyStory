# Specs archivadas

Lo que hay aquí **no se implementa**. Se conserva porque el historial de decisiones vale
más que el espacio que ocupa, y porque borrarlo dejaría sin contexto a las entradas del
registro de iteraciones que lo citan.

Toda spec de esta carpeta lleva `estado: archivada` en su frontmatter, que no es uno de los
tres estados del ciclo de cambio (`borrador`, `en-revision`, `aprobada`) precisamente para
que ningún agente la confunda con trabajo pendiente.

| Carpeta | Qué era | Por qué está aquí |
| --- | --- | --- |
| `001-backend-v1/` | SRS del backend v1 y su plan, aprobada el 2026-09-22 | Describe el sistema anterior entero: escenas como unidad, autor humano en el bucle, umbrales de deriva y `AGENTS.md` entre sus documentos de referencia. La ontología que especifica ya no existe (RI-001, RI-006) |

Las specs vigentes viven en `specs/`, en la raíz del repositorio.
