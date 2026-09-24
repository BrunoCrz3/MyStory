# Progreso del plan 1

Fichero de reanudación de `specs/plan1.md`. **Se actualiza al cerrar cada paso, en el mismo
commit que el paso.** Si la sesión se corta o se compacta, se retoma leyendo solo esto y el
paso que indica: nada de lo que hace falta para seguir vive fuera de aquí.

## Estado

| Campo | Valor |
| --- | --- |
| Plan | `specs/plan1.md` — **borrador, no aprobado** |
| Paso actual | — (P01 bloqueado hasta que el plan esté `aprobada`) |
| Estado del paso | `no-iniciado` · `pruebas-escritas` · `en-verde` · `cerrado` |
| Intentos fallidos en el paso actual | 0 de 3 |
| Rama | `backend-v1` (se crea en el P01) |
| Último commit de paso | — |

## Coste real

Tope de parada: **40 USD** acumulados (plan § 1, condición 4). Antes de cada ejecución
real: si `acumulado + coste.coste_maximo_novela > 40`, no se lanza.

| Fecha | Paso | Qué se ejecutó | Coste USD | Acumulado USD |
| --- | --- | --- | --- | --- |
| — | — | — | 0 | 0 |

**Novela de humo** (se reutiliza en F4 y F5): base `—`, `novel_id` `—`.

## Hecho

Un renglón por paso cerrado: paso, qué quedó y hash del commit.

- (nada todavía)

## Pendiente

- P01 a P48, en orden. Siguiente: **P01 · Esqueleto del proyecto y test de conformidad**,
  en cuanto el frontmatter del plan diga `estado: aprobada`.
- Decidir **D-01** (Dato faltante frente al schema de `BriefNovela`) antes de aprobar.

## Decisiones

Las que fija el plan son D-01 a D-24 (plan § 3, registradas como TO-036). Las que tome el
agente durante la ejecución van aquí como `A-NN`, con paso, decisión, porqué y dónde quedó
registrada.

| Id | Paso | Decisión | Porqué | Registro |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

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
