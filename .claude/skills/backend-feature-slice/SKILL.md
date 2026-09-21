---
name: backend-feature-slice
description: Estructura del backend FastAPI de este repositorio: rodajas verticales por feature (`router.py`, `schemas.py`, `models.py`, `service.py`, `repository.py`), qué entra en `commons/` y qué no, y la regla de importación entre features. Cárgala antes de crear cualquier archivo del backend, añadir un endpoint, decidir en qué carpeta vive una clase de la ontología, resolver una importación entre features, mover algo a `commons/`, definir un contrato Pydantic entre capas, escribir una llamada al modelo o mapear un error de dominio a HTTP. Úsala también cuando aparezcan las palabras router, service, repository, schemas, feature, commons, endpoint, FastAPI, Pydantic, idempotencia o dependencia circular, aunque nadie nombre la arquitectura. Es el equivalente de backend a `feature-sliced-design`: si la duda es «¿dónde va este archivo?» y el archivo es Python, es esta skill.
---

# Rodaja vertical de backend

El backend se organiza por features, no por capas técnicas. No es una preferencia de
estilo: «Convenciones del modelo», en `docs/definitions.md`, advierte que las cinco capas
de la ontología tienen ciclos de vida distintos y que mezclarlas es el error de diseño más
común de este dominio. El canon cambia al aceptar una escena; el contexto cambia en cada
llamada al modelo. Si ambos viven en un `services/` compartido, un cambio de presupuesto
de tokens toca el mismo archivo que una consolidación. Una carpeta por capa es lo que lo
impide.

## Las siete features

Cinco salen de las capas de la ontología, dos del modo híbrido:

| Feature | Capa |
| --- | --- |
| `novel/` | 1 — Obra |
| `canon/` | 2 — Canon |
| `context/` | 3 — Contexto |
| `quality/` | 4 — Calidad |
| `process/` | 5 — Proceso |
| `findings/` | híbrido |
| `replanning/` | híbrido |

**Cada clase del dominio tiene una dueña y solo una, y quién es está en
`docs/architecture.md` § Anatomía de una feature.** No la adivines por la capa ni la
copies aquí: esa tabla es la lista completa y se actualiza en un solo sitio.

Si una clase nueva no encaja en ninguna, el problema casi nunca es que falte una feature:
es que la clase no está en `docs/definitions.md`. Abre una pregunta al autor antes de
crear la carpeta.

## Anatomía

Cinco archivos, siempre los mismos, siempre con el mismo reparto:

```
canon/
  router.py       # endpoints FastAPI de esta feature y nada más
  schemas.py      # Pydantic de entrada y salida
  models.py       # entidades de la ontología que le pertenecen
  service.py      # lógica: es donde vive la regla de dominio
  repository.py   # SQL explícito contra SQLite
```

- **`router.py`** traduce HTTP a llamadas del servicio y nada más. Si tiene un `if` sobre
  una regla del mundo, esa regla está en el sitio equivocado.
- **`schemas.py`** es la frontera. Todo lo que entra o sale por HTTP es un modelo
  Pydantic v2; no cruzan `dict` sueltos entre capas. Un `dict` es un contrato que nadie
  valida y que ningún tipo documenta.
- **`models.py`** lleva los nombres de la ontología, exactos. Un nombre nuevo sin entrada
  en `docs/definitions.md` es un error, no una mejora.
- **`service.py`** es lo único que otra feature puede importar.
- **`repository.py`** escribe SQL explícito. No lo importa nadie de fuera.

## Dónde va un archivo

1. ¿Es una clase, regla o dato del dominio? Va a la feature dueña de su capa, según la
   tabla de arriba. Ante la duda entre una feature y `commons/`, va a la feature.
2. ¿Es infraestructura que ya usan **dos o más** features? Entonces `commons/`: conexión
   y migraciones de SQLite, cliente del modelo con su timeout, contador de tokens,
   excepciones de dominio y su handler HTTP.
3. ¿Es infraestructura que usa una sola feature? Se queda en la feature hasta que la
   segunda la necesite. Mover a `commons/` por adelantado convierte la carpeta en el
   cajón de sastre que la regla intenta evitar.

`commons/` no sabe qué es una escena. Si estás a punto de importar un modelo de la
ontología ahí, la pieza no es infraestructura.

## Regla de importación

Una feature importa de `commons/` y del `service.py` de otra feature. **Nunca de su
`repository.py`.** El servicio es el contrato; el repositorio es un detalle que cambia
cuando cambia el SQL.

Sin importaciones circulares. Si dos features se necesitan mutuamente, falta una tercera
o la frontera está mal puesta — resuélvelo moviendo la pieza compartida, no añadiendo un
import diferido ni una importación dentro de la función.

## Reglas que cruzan todas las features

- **Llamadas al modelo: asíncronas y con timeout explícito.** Un timeout implícito es un
  cuelgue esperando a ocurrir, y el trabajo largo corre dentro de este mismo proceso.
- **`registrar-generacion` corre en toda llamada al modelo, sin excepción.** Sin modelo,
  prompt, contexto y semilla guardados no se puede reproducir un resultado bueno ni
  diagnosticar uno malo.
- **Las escrituras al canon son idempotentes por `scene_id` + `version`.** Reintentar no
  puede consolidar dos veces.
- **Solo `canon/` escribe en el canon**, y solo al consolidar una escena aceptada. Un
  borrador rechazado no deja rastro: si lo dejara, cada iteración fallida contaminaría el
  estado del mundo.
- **Los errores de dominio son excepciones propias**, mapeadas a HTTP en el handler
  central de `commons/`. Un `HTTPException` lanzado desde un servicio ata la lógica al
  transporte.

## Qué no decide esta skill

Los nombres de clases, estados y relaciones salen de `docs/definitions.md` y
`docs/domain-knowledge.md`, no de aquí. El SQL y las migraciones tienen su propia skill
(`sqlite-relacional`), y el reparto de tokens de `context/` la suya
(`presupuesto-de-contexto`). Si algo de esta skill choca con `AGENTS.md`, manda
`AGENTS.md`.
