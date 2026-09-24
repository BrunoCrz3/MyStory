# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **aprobado** por el desarrollador el 2026-09-24 |
| Paso actual | P06 · Cliente del modelo con conteo previo |
| Estado del paso | `no-iniciado` |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | P05 |

## Coste real

Tope de parada: **40 USD** acumulados (plan § 1, condición 4; unidad y tope confirmados por
el desarrollador el 2026-09-24). Antes de cada ejecución
real: si `acumulado + coste.coste_maximo_novela > 40`, no se lanza.

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |
| — | — | — | 0 | 0 |

**Novela de humo** (se reutiliza en F4 y F5): base `—`, `novel_id` `—`.

## Hecho

Un renglón por paso cerrado: paso, qué quedó y hash del commit.

- **P01** — Esqueleto (pyproject, crear_app, lifespan), test de conformidad estructural con PENDIENTES y meta-prueba de 8 mutaciones; 12 pruebas
- **P02** — Comprobadores estáticos: grafo de importación leído de architecture.md, hojas intake/guardrail, sin dobles, sin dependencias excluidas, RD-02 en repositorios; 8 meta-pruebas
- **P03** — commons/config: modelos Pydantic estrictos de thresholds.yaml y models.yaml, suma de capas, margen >= max_tokens por rol, nulos según cerrar_el_paso, gate Lean sin timeout, judge != redactor; el lifespan aborta con la clave culpable; 25 pruebas nuevas
- **P04** — commons/errores: una excepción por type del catálogo, handler central problem+json (dominio, 422 reescrito, 500 sin detalles), OpenAPI sin el 422 genérico y con Problema idéntico al del contrato; commons/esquemas.opcional() para opcionales sin nulo
- **P05** — commons/db: conectar() con WAL y FK en toda conexión, transaccion() con BEGIN IMMEDIATE, BaseDatos con una conexión por unidad de trabajo en hilo; runner de migraciones con hash que falla si se edita una aplicada, atómico por migración; lifespan migra al arrancar; prueba RD-01 sobre toda migración; cada prueba con base temporal y sin credenciales

## Pendiente

- Siguiente: **P06 · Cliente del modelo con conteo previo**, y después el resto hasta el P49 en orden.
- **`ejemplos/novela-ejemplo.pdf` — entregable obligatorio del alcance, pendiente del paso
  de integración P49.** Se genera contra la página `lectura` real del frontend. Si al llegar
  al P49 esa página no existe todavía, el PDF sigue aquí como **pendiente, no descartado**,
  con el comando exacto, y el plan no se da por cerrado hasta que esté commiteado.

## Post-demo

Lo que se decidió no hacer en la demo y **no se olvida**. No es trabajo de este plan.

| Qué | Por qué queda fuera | Decisión |
| --- | --- | --- |
| **Replanificación de capítulos pendientes** (invalidación de restricción de destino) | Sin RF en la spec 1; un defecto sistémico se trata como reescritura y queda registrado con su clasificación | D-14, aceptada por el desarrollador |
| El resto de la lista post-demo de la spec | Entrevistador conversacional, TLA+, servidor MCP, agente de seguridad, gate de Lean, SSE, PO-11 y PO-12 | `specs/spec1.md` § 7 Post-demo |

## Decisiones

Las que fija el plan son D-01 a D-24 (plan § 3, registradas como TO-036). Las que tome el
agente durante la ejecución van aquí como `A-NN`, con paso, decisión, porqué y dónde quedó
registrada.

| Id | Paso | Decisión | Porqué | Registro |
| --- | --- | --- | --- | --- |
| — | plan | D-01 resuelta con un cambio de contrato: `BriefNovelaParcial` para validar, `BriefNovela` para crear; contrato 1.1.0 | Aprobado por el desarrollador | TO-037 |
| — | plan | D-08, D-09, D-14 y D-22 aceptadas; D-08 con seis aristas nuevas comprobadas sin ciclo | Aprobado por el desarrollador | TO-036, `docs/architecture.md` |
| — | plan | Contrato de lectura en la spec § 4.4 y paso P46 que lo lleva como dato | Pedido por el desarrollador | TO-037 |
| A-01 | P02 | De otra feature solo se importa `service`; `commons/`, `prompts/` y `skills/` son importables desde cualquier feature y no importan ninguna | La skill dice que `service.py` es lo único importable; `prompts/` es infraestructura de contenido (D-09) | TO-038 al cerrar F0 |
| A-02 | P02 | Consultas sin `novel_id` —listar todas las novelas, reclamar el siguiente trabajo— se declaran en `CONSULTAS_TRANSVERSALES` del repositorio | RD-02 no tiene excepción escrita y listar novelas la necesita | TO-038 |
| A-03 | P03 | Todo umbral con score (calidad salvo invencion_destinatario y temas_excluidos) solo cierra el paso con `medicion.cerrar_el_paso: true` y admite null en medición; los booleanos y los que cuentan hasta cero cierran siempre y no admiten null | `thresholds.yaml` no decía si los programáticos con score dependen de la fase de medición; se eligió la lectura que deja salir novelas mientras se calibra | TO-038 |
| A-04 | P04 | `Problema` lleva sus propias formas `DatoFaltanteProblema` y `ContradiccionProblema`; `intake/` tendrá las clases de la ontología | `commons/` no puede importar `intake/` ni contener clases de la ontología | TO-038 |
| A-05 | P04 | Los 404 de rutas inexistentes y los 405 siguen siendo los de Starlette | El catálogo es cerrado y ninguna operación del contrato los produce | TO-038 |
| A-06 | P05 | La tabla de control del runner se llama `_migracion` y es la única sin `novel_id`: las tablas que empiezan por `_` son del runner, no de dominio | RD-01 habla de tablas de dominio | TO-038 |

## Parada

Vacío mientras no se active ninguna de las cuatro condiciones del plan § 1. Si se activa:
condición, paso, qué se intentó y qué se necesita del desarrollador.

## Cómo reanudar

```bash
git switch backend-v1
cd backend && uv sync
uv run pytest          # debe estar en verde salvo el paso en curso
```

Después, ir al paso actual del plan. Si su estado es `pruebas-escritas`, las pruebas ya están
y se sigue por el código; si es `en-verde`, falta ejecutar su «Hecho cuando», actualizar
este fichero y hacer commit.
