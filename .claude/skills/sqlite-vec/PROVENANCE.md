# Procedencia de esta skill

`sqlite-vec` está **vendorizada** en el repositorio: no se instala ni se actualiza
con `npx skills`.

| Campo | Valor |
| --- | --- |
| Origen | `existential-birds/beagle`, ruta `plugins/beagle-core/skills/sqlite-vec/` |
| Commit extraído | `242d64b403007e91be4e51815182e7d728b46fb7^` (estado previo al borrado) |
| Fecha de extracción | 2026-09-21 |
| Motivo de la copia | El upstream la eliminó el 2026-05-27 en `refactor!: restructure marketplace for official submission (#115)` («remove vendor skills from beagle-core»). Sigue listada en los registros de skills, pero ya no es instalable. |

Consecuencia: los cambios aguas arriba no llegan solos. Si `sqlite-vec` publica
una versión que invalide algo de aquí, se actualiza a mano contra la
documentación oficial: <https://alexgarcia.xyz/sqlite-vec> y
<https://github.com/asg017/sqlite-vec>.
