# Especificaciones Funcionales
## Agente generador de novelas de ciencia ficción

**Versión:** 1.0
**Estado:** Borrador para revisión
**Documento hermano:** `especificaciones_tecnicas.md`

---

## 1. Propósito y alcance

### 1.1 Propósito
Definir el comportamiento observable de un sistema que, a partir de una **premisa** y un **número de capítulos** proporcionados por un autor humano, produce una novela de ciencia ficción completa, internamente coherente y no repetitiva.

### 1.2 Dentro del alcance
- Captura de la premisa y de los parámetros creativos.
- Construcción de una "biblia narrativa" (mundo, personajes, reglas, arcos).
- Planificación estructural en capítulos y escenas.
- Redacción capítulo a capítulo.
- Control automático de continuidad y de repetición.
- Revisión, edición e intervención del autor en cualquier punto.
- Exportación del manuscrito.

### 1.3 Fuera del alcance (v1)
- Ilustración de portada o interiores.
- Publicación o distribución en tiendas.
- Coautoría simultánea de varios usuarios sobre el mismo proyecto.
- Géneros distintos de la ciencia ficción (la arquitectura lo permitirá, pero los prompts y heurísticas se calibran para CF).
- Audio / narración.

---

## 2. Actores

| Actor | Descripción | Responsabilidad principal |
|---|---|---|
| **Autor** | Usuario humano propietario del proyecto | Aporta la premisa, fija parámetros, aprueba o rechaza artefactos, edita texto |
| **Sistema (Agente)** | Orquestador multi-etapa | Genera, valida y corrige el contenido |
| **Administrador** | Operador de la plataforma | Gestiona modelos, cuotas, plantillas de prompts |

---

## 3. Conceptos del dominio

| Término | Definición operativa |
|---|---|
| **Premisa** | Texto libre (50–2.000 caracteres) que describe la idea central de la novela |
| **Biblia narrativa** | Documento estructurado con el canon del mundo: personajes, lugares, tecnología, reglas físicas/sociales, cronología, tono |
| **Escaleta (outline)** | Plan jerárquico: novela → actos → capítulos → escenas |
| **Beat** | Unidad mínima de suceso dramático dentro de una escena |
| **Hecho canónico** | Afirmación verificable del mundo narrativo, con capítulo de origen y estado (vigente / revocado) |
| **Libro mayor de continuidad** | Registro acumulado del estado del mundo tras cada capítulo |
| **Hilo abierto** | Pregunta, promesa o conflicto planteado y aún no resuelto |

---

## 4. Entradas del autor

### 4.1 Obligatorias
| Campo | Tipo | Validación |
|---|---|---|
| Premisa | Texto | 50–2.000 caracteres |
| Número de capítulos | Entero | 3–60 |

### 4.2 Opcionales (con valores por defecto)
| Campo | Opciones | Defecto |
|---|---|---|
| Subgénero | space opera, cyberpunk, hard SF, post-apocalíptico, primer contacto, distopía social, solarpunk, viaje temporal | hard SF |
| Longitud objetivo por capítulo | 1.500 / 2.500 / 4.000 / 6.000 palabras | 2.500 |
| Punto de vista | 1ª persona, 3ª limitada, 3ª limitada multi-POV, 3ª omnisciente | 3ª limitada |
| Tiempo verbal | pasado, presente | pasado |
| Tono | sombrío, esperanzador, satírico, contemplativo, aventura | contemplativo |
| Estructura | tres actos, viaje del héroe, kishōtenketsu, libre | tres actos |
| Nivel de dureza científica | especulativo / plausible / riguroso | plausible |
| Idioma de salida | es, en, … | es |
| Contenido a evitar | lista libre de temas o elementos vedados | vacío |
| Referencias de estilo | descripción en prosa del estilo deseado (no imitación de un autor concreto) | vacío |
| Semilla aleatoria | entero | aleatoria |

---

## 5. Requisitos funcionales

### 5.1 Configuración del proyecto

- **RF-01** El sistema permitirá crear un proyecto introduciendo premisa y número de capítulos.
- **RF-02** El sistema validará las entradas y mostrará mensajes de error específicos por campo.
- **RF-03** El sistema permitirá guardar un proyecto como borrador y retomarlo después.
- **RF-04** El sistema permitirá duplicar un proyecto para explorar variantes de la misma premisa.

### 5.2 Fase 1 — Biblia narrativa

- **RF-10** A partir de la premisa, el sistema generará una biblia narrativa que incluirá, como mínimo:
  - logline y tema central;
  - 3–8 personajes con nombre, rol, deseo, miedo, contradicción, voz y arco previsto;
  - escenario (lugares principales, época, situación política y económica);
  - premisa tecnológica o científica y sus **reglas y límites explícitos**;
  - cronología de sucesos previos al capítulo 1;
  - glosario de términos inventados;
  - lista de motivos y símbolos recurrentes.
- **RF-11** El sistema detectará contradicciones internas en la biblia (p. ej. una regla tecnológica que invalida el conflicto) y las señalará antes de continuar.
- **RF-12** El autor podrá editar cualquier campo de la biblia, regenerar secciones concretas o aprobarla en bloque.
- **RF-13** Ninguna fase posterior comenzará sin una biblia en estado *aprobada*.

### 5.3 Fase 2 — Escaleta

- **RF-20** El sistema generará una escaleta con **exactamente N capítulos**, siendo N el valor indicado por el autor.
- **RF-21** Cada capítulo de la escaleta contendrá: título provisional, POV, objetivo dramático, 2–5 escenas con sus beats, hilos que abre, hilos que cierra, cambio de estado del mundo y gancho final.
- **RF-22** El sistema distribuirá los puntos de giro en función de N y de la estructura elegida, garantizando que ningún capítulo sea de mero relleno.
- **RF-23** El sistema verificará que **todo hilo abierto se cierre** antes del capítulo N, o lo marque deliberadamente como abierto (secuela).
- **RF-24** El sistema verificará que dos capítulos consecutivos no repitan la misma función dramática ni la misma localización y POV sin justificación.
- **RF-25** El autor podrá reordenar, reescribir, fusionar o dividir capítulos; al hacerlo, el sistema recalculará dependencias y avisará de las que se rompan.
- **RF-26** Si el autor cambia N después de aprobar la escaleta, el sistema propondrá una redistribución en lugar de truncar el plan.

### 5.4 Fase 3 — Redacción

- **RF-30** Los capítulos se redactarán **en orden secuencial**; cada uno recibirá como contexto la biblia, el estado de continuidad acumulado y el resumen de los capítulos previos.
- **RF-31** Cada capítulo se ajustará a ±20 % de la longitud objetivo.
- **RF-32** Cada capítulo respetará el POV y el tiempo verbal declarados para él.
- **RF-33** Cada capítulo cumplirá los beats de su escaleta; las desviaciones creativas se permitirán solo si no invalidan capítulos posteriores, y se registrarán.
- **RF-34** El sistema mostrará el progreso en tiempo real (capítulo en curso, fase, porcentaje).
- **RF-35** El autor podrá pausar, reanudar y cancelar la generación sin perder lo ya producido.
- **RF-36** El autor podrá regenerar un capítulo individual con instrucciones adicionales.
- **RF-37** Tras editar manualmente un capítulo, el sistema reextraerá los hechos canónicos de la versión editada y actualizará el estado del mundo.

### 5.5 Control de coherencia

- **RF-40** Tras cada capítulo, el sistema extraerá los hechos canónicos nuevos y los añadirá al libro mayor de continuidad.
- **RF-41** El sistema detectará y reportará, como mínimo:
  - contradicciones factuales (un personaje muerto que reaparece, un objeto en dos sitios);
  - incoherencias cronológicas (duraciones y órdenes imposibles);
  - violaciones de las reglas tecnológicas fijadas en la biblia;
  - deriva de nombres (variantes ortográficas del mismo elemento);
  - cambios de voz o de rasgos de personaje no justificados;
  - hilos abiertos huérfanos al llegar al final.
- **RF-42** Cada incidencia se clasificará como **bloqueante**, **mayor** o **menor**.
- **RF-43** Las incidencias bloqueantes dispararán una reescritura automática del capítulo (máximo de intentos configurable). Si persisten, el sistema detendrá el proceso y solicitará intervención del autor.
- **RF-44** El sistema mantendrá un panel de continuidad consultable: línea temporal, estado de cada personaje capítulo a capítulo, inventario de objetos y localizaciones.

### 5.6 Control de repetición

- **RF-50** El sistema impedirá la reutilización de:
  - estructuras de escena y funciones dramáticas ya empleadas recientemente;
  - metáforas, símiles e imágenes ya usadas;
  - muletillas y expresiones de alta frecuencia;
  - aperturas y cierres de capítulo con la misma fórmula;
  - descripciones repetidas del mismo personaje o lugar (cada reaparición debe aportar información nueva).
- **RF-51** El sistema mantendrá un registro de frases e imágenes utilizadas y lo entregará como restricción negativa al generar cada nuevo capítulo.
- **RF-52** El sistema medirá la similitud entre el capítulo nuevo y todos los anteriores; si supera el umbral configurado, forzará una reescritura.
- **RF-53** El sistema vigilará la diversidad léxica y avisará si cae por debajo del umbral establecido.
- **RF-54** El informe de calidad incluirá un listado de las expresiones más repetidas de toda la novela.

### 5.7 Revisión final

- **RF-60** Terminado el capítulo N, el sistema ejecutará una pasada global que produzca:
  - informe de continuidad (hilos, cronología, personajes);
  - informe de repetición;
  - informe de ritmo (longitud, densidad de diálogo, tensión por capítulo);
  - lista de correcciones sugeridas, cada una con capítulo, párrafo y motivo.
- **RF-61** El autor podrá aplicar las correcciones una a una o en bloque.
- **RF-62** El sistema propondrá títulos definitivos de capítulo y de novela, y una sinopsis comercial.

### 5.8 Exportación y versionado

- **RF-70** Exportación a Markdown, DOCX, EPUB y PDF.
- **RF-71** Exportación de los artefactos de trabajo (biblia, escaleta, libro mayor) en JSON.
- **RF-72** Historial de versiones por capítulo, con comparación y restauración.
- **RF-73** Registro de qué texto es generado, qué texto es editado por el autor y qué texto es mixto.

---

## 6. Flujo principal

```
1. Crear proyecto  →  premisa + N capítulos + parámetros
2. Generar biblia  →  revisar  →  editar  →  APROBAR
3. Generar escaleta →  revisar  →  editar  →  APROBAR
4. Bucle por capítulo i = 1..N
       4.1 Redactar borrador
       4.2 Validar continuidad y repetición
       4.3 ¿Incidencias bloqueantes? → reescribir (máx. k intentos)
       4.4 Pulir estilo
       4.5 Extraer hechos y actualizar estado del mundo
       4.6 Resumir capítulo para el contexto de los siguientes
5. Revisión global  →  informes  →  correcciones
6. Exportar
```

El autor puede intervenir entre cualquier par de pasos. La aprobación es explícita en los pasos 2 y 3; en el paso 4 puede configurarse como automática (modo desatendido) o manual (modo supervisado).

---

## 7. Reglas de negocio

- **RN-01** La biblia narrativa es la fuente de verdad. Ante conflicto entre texto generado y biblia, prevalece la biblia salvo que el autor promueva el cambio al canon.
- **RN-02** Un hecho canónico solo puede ser revocado por un suceso narrado explícitamente.
- **RN-03** Ningún capítulo puede introducir un elemento decisivo para el desenlace sin haberlo sembrado antes (regla anti-*deus ex machina*).
- **RN-04** El número de capítulos entregados es exactamente N. El sistema nunca añade ni omite capítulos por su cuenta.
- **RN-05** Las reglas tecnológicas fijadas en la biblia son inviolables; una excepción exige justificación diegética y registro en el canon.
- **RN-06** Toda edición manual del autor es definitiva y no será sobrescrita sin confirmación.
- **RN-07** El sistema no reproducirá personajes, mundos ni textos protegidos por derechos de autor, ni imitará de forma sustancial la obra de un autor identificable.

---

## 8. Criterios de aceptación

| # | Criterio | Medición |
|---|---|---|
| CA-01 | La novela tiene exactamente N capítulos | Recuento automático |
| CA-02 | Cero contradicciones factuales bloqueantes | Informe de continuidad |
| CA-03 | 100 % de hilos abiertos resueltos o marcados como intencionales | Informe de hilos |
| CA-04 | Similitud máxima entre capítulos por debajo del umbral | Métrica de similitud |
| CA-05 | Ningún trigrama no trivial repetido más de *m* veces | Informe de repetición |
| CA-06 | Desviación de longitud por capítulo ≤ 20 % | Recuento de palabras |
| CA-07 | Cobertura de beats de la escaleta ≥ 90 % | Verificación por capítulo |
| CA-08 | Valoración humana ≥ 3,5/5 en coherencia y en frescura sobre una muestra de capítulos | Evaluación manual |
| CA-09 | El autor puede intervenir y regenerar en cualquier fase sin pérdida de datos | Prueba funcional |

---

## 9. Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| **Rendimiento** | Biblia en <3 min; escaleta en <5 min; capítulo de 2.500 palabras en <4 min incluida la validación |
| **Escalabilidad** | 50 proyectos concurrentes sin degradación perceptible |
| **Fiabilidad** | Reanudación tras caída desde el último capítulo completado; ninguna pérdida de trabajo aprobado |
| **Trazabilidad** | Cada fragmento generado conserva modelo, prompt, parámetros y semilla |
| **Coste** | Coste estimado por novela visible antes de lanzar la generación, con alerta al superar el presupuesto |
| **Usabilidad** | El autor entiende en qué fase está y qué se espera de él sin leer documentación |
| **Privacidad** | Los proyectos son privados por defecto; el autor decide si su contenido se usa para mejorar el sistema |
| **Portabilidad del modelo** | Cambiar de proveedor de LLM no obliga a reescribir la lógica de orquestación |

---

## 10. Casos límite y su tratamiento

| Situación | Comportamiento esperado |
|---|---|
| Premisa vaga o de una línea | El sistema propone 3 interpretaciones y pide al autor que elija o afine |
| Premisa que no es ciencia ficción | Aviso y propuesta de enfoque especulativo; el autor decide continuar |
| N muy pequeño (3) con premisa muy amplia | Aviso de que la trama deberá comprimirse; propuesta de reducir subtramas |
| N muy grande (60) con premisa muy simple | Propuesta de subtramas y POV adicionales para sostener la extensión |
| El autor edita la biblia a mitad de la redacción | Se recalcula la coherencia de los capítulos ya escritos y se marcan los afectados |
| Fallo del proveedor de LLM | Reintento con retroceso exponencial; cambio a modelo alternativo; estado persistido |
| Reescrituras que no resuelven una incidencia bloqueante | Se detiene el proceso y se escala al autor con diagnóstico concreto |
| Premisa que exige contenido vedado por las políticas | Se rechaza con explicación y se ofrece una reformulación |

---

## 11. Métricas de producto

- Tasa de novelas completadas sin intervención bloqueante.
- Número medio de reescrituras por capítulo.
- Porcentaje de texto final editado manualmente por el autor (proxy inverso de calidad).
- Incidencias de continuidad detectadas por el autor y no por el sistema (fugas del validador).
- Tiempo y coste medios por novela.
- Satisfacción declarada del autor al finalizar.

---

## 12. Fases de entrega sugeridas

| Fase | Contenido | Resultado |
|---|---|---|
| **F1 — Núcleo** | Premisa → biblia → escaleta → capítulos secuenciales → export Markdown | Novela completa generable de extremo a extremo |
| **F2 — Calidad** | Validador de continuidad, detector de repetición, bucle de reescritura, informes | Coherencia y frescura medibles |
| **F3 — Autor** | Edición, regeneración selectiva, versionado, panel de continuidad | Control creativo real |
| **F4 — Producción** | EPUB/DOCX/PDF, multi-POV avanzado, multilingüe, optimización de coste | Producto publicable |
