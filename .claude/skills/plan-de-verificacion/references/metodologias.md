# Catálogo de metodologías de verificación

Lista cerrada. Cada entrada trae una definición en lenguaje llano y un enlace que
explica **la metodología en sí**, no un producto que la vende.

Este catálogo es la fuente de nombres para la columna «Metodología» de un plan de
verificación. Si una afirmación no encaja en ninguna entrada, el problema es la
afirmación (está mal formulada o no es verificable), no el catálogo: clasifícala
como `U` y explica por qué, en vez de inventar una metodología nueva.

---

## Nivel artefacto — ¿es correcto el código?

| Metodología | Definición | Explicación |
| --- | --- | --- |
| Comprobación de tipos | Verificación automática de que los valores se usan de forma coherente con lo que las operaciones esperan de ellos | [Type system — Wikipedia](https://en.wikipedia.org/wiki/Type_system) |
| Análisis estático / SAST | Escanear el código fuente sin ejecutarlo, contrastándolo con patrones malos conocidos | [Static program analysis — Wikipedia](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Ejecución simbólica | Ejecutar el código con entradas simbólicas para derivar las condiciones exactas de fallo mediante un solver SMT | [Symbolic execution — Wikipedia](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Verificación formal / demostración de teoremas | Probar matemáticamente que el código satisface una especificación para toda entrada posible | [Formal verification — Wikipedia](https://en.wikipedia.org/wiki/Formal_verification) |
| Pruebas unitarias / de integración | Comprobar el comportamiento contra entradas de ejemplo concretas y sus salidas esperadas | [Unit testing — Wikipedia](https://en.wikipedia.org/wiki/Unit_testing) |
| Pruebas basadas en propiedades | Enunciar una propiedad general y generar muchas entradas buscando una violación | [QuickCheck — Claessen & Hughes, 2000](https://dl.acm.org/doi/10.1145/351240.351266) |
| Pruebas de mutación | Introducir bugs pequeños a propósito para comprobar si la suite de pruebas los detecta | [Mutation testing — Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing) |
| Pruebas de contrato | Verificar que la interfaz entre dos servicios sigue siendo coherente, con independencia de sus internos | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

## Nivel proceso — ¿se comporta el agente de forma fiable?

| Metodología | Definición | Explicación |
| --- | --- | --- |
| Observabilidad / trazas en ejecución | Instrumentar un agente para que su trayectoria sea visible y consultable a posteriori | [Observability primer — OpenTelemetry](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Pruebas estructuradas del comportamiento del agente contra un dataset y un método de puntuación | [HELM — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Ejecución en sandbox | Correr el código del agente en un entorno aislado para que las acciones malas fallen sin daño | [Sandbox (computer security) — Wikipedia](https://en.wikipedia.org/wiki/Sandbox_(computer_security)) |
| Guardarraíles | Políticas y filtros que restringen qué acciones puede producir un agente | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Revisión humana en el bucle | Una persona aprueba, rechaza o edita las acciones de alta consecuencia | [Human-in-the-loop — Wikipedia](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Verificación multiagente | Patrones de crítico, debate, autoconsistencia, reflexión o ensemble que revisan la salida del modelo | [AI Safety via Debate — Irving et al., 2018](https://arxiv.org/abs/1805.00899) |
| Integración en CI/CD | Hacer pasar los cambios generados por agentes por el mismo pipeline que los humanos | [Continuous integration — Wikipedia](https://en.wikipedia.org/wiki/Continuous_integration) |
| Despliegue progresivo | Sacar un cambio a un porcentaje pequeño del tráfico tras un flag antes del release completo | [Feature toggle — Wikipedia](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red-teaming / pruebas adversarias | Sondear deliberadamente en busca de fallos bajo un modelo de amenaza adversario | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Model checking | Explorar exhaustivamente los estados y transiciones alcanzables para verificar invariantes | [Model checking — Wikipedia](https://en.wikipedia.org/wiki/Model_checking) |

## Marco de clasificación

| Método | Definición | Explicación |
| --- | --- | --- |
| T / A / I / D / U (Trust Spec) | Clasificación por requisito: Test (prueba), Analysis (análisis), Inspection (inspección), Demonstration (demostración), Unverifiable (no verificable) | [Verification and validation — Wikipedia](https://en.wikipedia.org/wiki/Verification_and_validation) |

### Cómo elegir la letra

- **T — Test.** Existe un procedimiento repetible con criterio de aprobado/suspenso
  medible. Si puedes escribir la aserción, es `T`.
- **A — Analysis.** Se establece por razonamiento sobre el artefacto sin ejecutarlo:
  tipos, análisis estático, model checking, cálculo de un presupuesto. Cubre espacios
  de entrada que ninguna prueba enumera.
- **I — Inspection.** Alguien mira y confirma que está: una tabla existe, un nombre
  coincide con la ontología, un diagrama está actualizado. Barato y suficiente para
  afirmaciones estructurales.
- **D — Demonstration.** Se ejecuta el flujo de punta a punta y se observa que hace lo
  que dice. No hay oráculo exacto, pero el resultado es visible y reproducible.
- **U — Unverifiable.** No hay procedimiento que lo establezca: depende del gusto, del
  juicio del autor o de un criterio que nadie ha escrito todavía. Declararlo `U` es un
  resultado válido y a menudo el más útil del plan.

**Nota sobre las fuentes.** Las pruebas basadas en propiedades y los evals no tienen una
referencia fundacional neutral única como sí la tiene la verificación formal. Los enlaces
apuntan al trabajo que introdujo o formalizó la metodología (QuickCheck y HELM
respectivamente), no a la única elección posible.
