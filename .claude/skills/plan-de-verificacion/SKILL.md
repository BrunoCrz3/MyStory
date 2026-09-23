---
name: plan-de-verificacion
description: Construye un plan de verificación a partir del contexto semilla de un proyecto (ontología, conocimiento de dominio, arquitectura), mapeando cada afirmación verificable a una metodología concreta del catálogo y clasificándola como T/A/I/D/U (Test, Analysis, Inspection, Demonstration, Unverifiable). Úsalo siempre que se pida un verification.md, un plan o estrategia de verificación, decidir cómo probar un sistema o un agente, clasificar requisitos por método de verificación, distinguir verificación de artefacto (¿es correcto el código?) de verificación de proceso (¿se comporta el agente de forma fiable?), o cuando se pregunte "cómo verificamos esto" sobre invariantes, máquinas de estado, presupuestos, contratos entre capas o salidas de un LLM. Aplícalo también cuando se hable de evals, guardarraíles, pruebas basadas en propiedades, model checking o red-teaming sin nombrar la palabra verificación.
---

# Plan de verificación

Convierte documentos de dominio en una tabla operativa: qué afirma el sistema, cómo se
comprueba cada afirmación y qué no se puede comprobar en absoluto.

Un plan de verificación no es una lista de pruebas por escribir. Es un inventario de
afirmaciones con el método más barato que de verdad las cubre. Dos errores lo vacían de
sentido: asignar «prueba unitaria» a todo, que finge cobertura donde no la hay, y
declarar verificable lo que depende del gusto de una persona. El valor del documento
está en las filas incómodas — las `U` — porque son las que dicen dónde el sistema
descansa sobre juicio humano y no sobre garantías.

## Entradas

El contexto semilla del proyecto. En este repositorio:

| Documento | Qué aporta al plan |
| --- | --- |
| `docs/definitions.md` | Clases, atributos, relaciones, cardinalidades y preguntas de competencia. Cada pregunta de competencia es ya una afirmación verificable. |
| `docs/domain-knowledge.md` | Máquinas de estado, jerarquías y aristas del grafo. Los invariantes de transición salen de aquí. |
| `docs/architecture.md` | Componentes, agentes, skills y orden de ejecución. Dice *dónde* vive cada comprobación. |
| `CLAUDE.md` | Requisitos técnicos cerrados y presupuesto de tokens. Los límites duros son afirmaciones de primera clase. |

Si el proyecto tiene otros documentos semilla, úsalos igual: el criterio es que
describan el dominio, no la implementación.

## Proceso

**1. Lee las entradas completas antes de escribir una sola fila.** Un plan hecho sobre
un índice hereda los huecos del índice.

**2. Extrae afirmaciones verificables.** Una afirmación es una frase que puede ser
falsa. Busca:

- límites numéricos duros (presupuestos, umbrales, tamaños de ventana);
- invariantes de estado («ningún agente escribe en el canon directamente»);
- transiciones de máquinas de estado, y las transiciones *ausentes*, que son
  afirmaciones tan fuertes como las presentes;
- cardinalidades y claves foráneas del modelo relacional;
- contratos entre capas (esquemas de entrada/salida, tipos generados);
- preguntas de competencia de la ontología;
- propiedades de calidad de lo que genera el modelo.

Cita el origen de cada afirmación con fichero y sección. Una fila sin origen no se
puede auditar después, y el plan envejece mal.

**3. Clasifica cada afirmación por nivel.** *Artefacto* si lo que puede fallar es el
código; *proceso* si lo que puede fallar es el comportamiento del agente o del modelo.
La distinción manda: una salida mala de un LLM no se arregla con una prueba unitaria,
y un esquema de base mal puesto no se arregla con un eval.

**4. Asigna metodología** desde `references/metodologias.md`. Lee ese fichero antes de
rellenar la columna; es una lista cerrada y los nombres importan porque el plan se
consulta después. Orientaciones que suelen acertar:

| Forma de la afirmación | Metodología que suele encajar |
| --- | --- |
| Límite numérico que debe cumplirse siempre | Pruebas basadas en propiedades + análisis estático del cálculo |
| Máquina de estados con transiciones prohibidas | Model checking, o pruebas basadas en propiedades si el espacio es grande |
| Contrato entre backend y frontend | Comprobación de tipos + pruebas de contrato |
| Invariante de escritura («solo X escribe en Y») | Análisis estático / SAST sobre las rutas de importación |
| Cardinalidad relacional | Restricciones de esquema + inspección de la migración |
| Calidad o continuidad de texto generado | Evals + verificación multiagente (crítico) |
| Acción de alta consecuencia sobre datos reales | Revisión humana en el bucle + guardarraíles |
| Fallo que solo aparece bajo adversario | Red-teaming |
| Una suite de pruebas que quizá no prueba nada | Pruebas de mutación |

Si una afirmación necesita dos metodologías, pon las dos: son complementarias, no
alternativas. Una prueba fija un ejemplo; el análisis cubre el espacio.

**5. Pon la letra T/A/I/D/U** según los criterios de `references/metodologias.md`.
Sé honesto con la `U`. Si la afirmación es «la prosa suena a este personaje», eso es
`U` hasta que alguien escriba el criterio, y decir lo contrario convierte el plan en
decoración.

**6. Sitúa cada comprobación.** La columna «Dónde vive» apunta a un módulo, un fichero
de pruebas o un paso de CI. Una comprobación sin sitio no se ejecuta nunca.

**7. Cierra con los huecos.** La sección final lista las `U` y las afirmaciones que no
pudiste extraer por falta de información, con la pregunta concreta que habría que
hacerle al autor. Este es el entregable más útil del documento.

## Estructura del documento

Usa esta plantilla. El orden importa: el lector busca primero su nivel, y dentro del
nivel su componente.

```markdown
# Verificación — cómo se comprueba cada afirmación del sistema

<Un párrafo: qué cubre este documento, de qué documentos deriva y qué no es.>

## Cobertura

<Tabla resumen: nº de afirmaciones por nivel y por letra T/A/I/D/U.>

## Nivel artefacto — ¿es correcto el código?

| Afirmación | Origen | Metodología | T/A/I/D/U | Dónde vive |
| --- | --- | --- | --- | --- |

## Nivel proceso — ¿se comporta el agente de forma fiable?

| Afirmación | Origen | Metodología | T/A/I/D/U | Dónde vive |
| --- | --- | --- | --- | --- |

## Lo que no se puede verificar

<Las filas U, una por una, con por qué y qué las convertiría en verificables.>

## Preguntas abiertas al autor

<Lo que falta para completar el plan.>
```

## Reglas

- **No inventes metodologías.** El catálogo es cerrado; si nada encaja, la afirmación
  es el problema.
- **No inventes afirmaciones.** Cada fila sale de un documento citable. Si una capa del
  sistema no aparece en el contexto semilla, dilo en «Preguntas abiertas» en vez de
  rellenar el hueco por tu cuenta.
- **Respeta el vocabulario del proyecto.** Los nombres de clases, estados y roles son
  los de la ontología. Un nombre nuevo en el plan es un error, no una mejora.
- **Nada de herramientas concretas en la columna de metodología.** «Pruebas basadas en
  propiedades», no «Hypothesis». La herramienta va, si acaso, en «Dónde vive».
- **Prefiere la letra más barata que de verdad cubra la afirmación.** Inspección vale
  cuando basta con mirar; gastar una prueba de mutación en una constante es ruido.
