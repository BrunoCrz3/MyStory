# Especificación técnica — MyStory

**Versión:** 0.1
**Estado:** borrador

---

## 1. Decisión de arquitectura

**Un agente con máquina de estados por fases y un bucle de control externo**, no un sistema
multiagente.

La alternativa (worldbuilder + redactor + editor como agentes separados) añade orquestación
y coste de coordinación sin resolver el problema real, que es la gestión de contexto sobre
un corpus que crece.

El requisito de ejecución end-to-end sí introduce una separación necesaria: **quien genera
no evalúa**. El generador y el evaluador de compuerta son llamadas distintas, con prompts,
temperatura y contexto distintos. Un modelo que puntúa su propia salida en la misma llamada
que la produjo aprueba casi siempre, y en autónomo eso significa que nada frena la deriva.

## 2. Componentes

| Componente | Responsabilidad |
|---|---|
| **Controlador de ejecución** | Bucle autónomo, presupuesto, reintentos, checkpoints, escalado |
| **Orquestador** | Máquina de estados de fases, compuertas, enrutado de comandos |
| **Evaluador de compuerta** | Puntúa artefactos contra rúbrica; independiente del generador |
| **Gestor de artefactos** | Lectura/escritura del repositorio, parseo de front matter, commits |
| **Índice de contexto** | Recuperación selectiva de biblia y capítulos relevantes |
| **Motor de redacción** | Generación de escena con inyección de estilo |
| **Motor de continuidad** | Auditoría por ejes, generación del informe |
| **Registro de decisiones** | Traza de qué se decidió, cuándo, por qué y con qué puntuación |

## 3. Máquina de estados

```
PREMISA → [aprobación] → MUNDO → PERSONAJES → ESTRUCTURA
       → [aprobación] → REDACCION ⇄ [bucle escena]
       → CONTINUIDAD → [hallazgos ALTO/MEDIO] → REDACCION
                     → [sin hallazgos] → ESTABLE
```

El estado vive en `project.yaml`, no en la conversación. Cualquier sesión nueva reconstruye
el estado leyendo ese archivo. Transiciones prohibidas: saltar a `REDACCION` sin escaleta
aprobada, cerrar en `ESTABLE` con hallazgos `ALTO` abiertos.

```yaml
# project.yaml
modo: autonomo            # autonomo | asistido
fase: REDACCION
objetivo_palabras: 90000
premisa_aprobada: true
estructura_aprobada: true
escena_actual: "12.3"
palabras_totales: 41280
hallazgos_abiertos: { alto: 0, medio: 2, bajo: 7 }
reintentos: { compuerta_0: 1, compuerta_1: 2, compuerta_2: 0 }
presupuesto:
  tokens_max: 12000000
  tokens_usados: 5140000
  horas_max: 10
deuda: ["C1 criterio 2: meseta de 4 capítulos en acto II, aceptada tras 3 intentos"]
ultimo_checkpoint: "2026-09-15T11:42:00Z"
```

## 3.1 Bucle de ejecución autónoma

```
para cada fase en [PREMISA, MUNDO, PERSONAJES, ESTRUCTURA]:
    intento = 0
    repetir:
        artefacto = generar(fase, contexto)
        veredicto = evaluar(artefacto, rubrica[fase])      # llamada independiente
        intento += 1
    hasta veredicto.aprobado o intento == 3

    si no veredicto.aprobado:
        registrar_deuda(fase, veredicto.criterios_fallidos)
    persistir(artefacto); checkpoint()

mientras queden escenas:
    escena = redactar(siguiente_escena)
    persistir(escena)
    si escenas_desde_ultima_auditoria == 5:
        hallazgos = continuidad(incremental)
        si hallazgos.alto: corregir_antes_de_seguir()
    si presupuesto_agotado(): escalar(); salir

pasada = 0
repetir:
    hallazgos = continuidad(completa)
    aplicar_correcciones(hallazgos.alto + hallazgos.medio)
    pasada += 1
hasta (sin alto y sin medio) o pasada == 3

si quedan hallazgos alto: escalar()
si no: estado = ESTABLE
```

Tres invariantes del bucle: **nunca itera sin límite**, **nunca avanza sin persistir** y
**nunca se detiene en silencio** —toda parada produce un motivo legible.

## 4. Modelo de datos

Todo es texto plano versionable en git. No hay base de datos.

```
proyecto/
├── project.yaml
├── premise.md
├── outline.md
├── continuity-report.md
├── decisions-log.md         # Toda decisión narrativa autónoma y su motivo
├── debt-report.md           # Compuertas superadas con deuda
├── style-sample.md          # Muestra de voz del autor (opcional)
├── bible/
│   ├── novum.md
│   ├── technology.md
│   ├── society.md
│   ├── geography.md
│   ├── timeline.md
│   └── glossary.md
├── characters/*.md
└── chapters/NN-titulo.md
```

### Front matter de capítulo

```yaml
---
numero: 7
titulo: "Umbral"
pov: "Kira"
tiempo: "Día 41, tarde"
lugar: "Estación Meridiano, nivel 3"
objetivo: "Acceder a los registros sellados"
resultado: "Fracasa y queda marcada por el sistema"
palabras: 3120
estado: borrador        # esquema | borrador | revisado | final
elementos_biblia: [contencion-campos, protocolo-meridiano]
---
```

La auditoría de continuidad opera **primero sobre metadatos** y solo desciende al cuerpo
del texto cuando detecta un conflicto potencial. Sin esto, cada pasada releería la novela
entera.

### Glosario

Cada término inventado registra: forma canónica, variantes aceptadas, definición, capítulo
de primera aparición y si el lector ya lo conoce en ese punto. Es la defensa principal
contra la deriva terminológica.

### Cronología

Dos ejes independientes: **cronología del mundo** (lo anterior a la novela) y **cronología
de la trama** (día y hora de cada escena en orden absoluto, con independencia del orden de
lectura). El segundo detecta la mayoría de los errores temporales.

## 5. Gestión de contexto

Una novela terminada más su biblia supera cualquier ventana de contexto práctica. Estrategia
por capas:

1. **Siempre en contexto:** `project.yaml`, `premise.md`, `bible/novum.md`, ficha del POV
   de la escena actual y el bloque de escaleta correspondiente. ≈ 4–6k tokens.
2. **Recuperación selectiva:** búsqueda sobre el índice para traer solo las secciones de la
   biblia y los capítulos citados por `elementos_biblia` o por la consulta.
3. **Resumen rodante:** cada capítulo cerrado genera un resumen de 150 palabras en
   `chapters/.summaries/`. Para redactar el capítulo 30 se cargan resúmenes, no texto
   íntegro; los capítulos 28–29 sí van completos para continuidad de voz.

Índice: embeddings por sección con metadatos (tipo, capítulo, personajes citados),
reconstruible desde cero, no versionado.

## 6. Prompting

Cada llamada se compone de: rol y fase → reglas de la fase → artefactos de contexto →
muestra de estilo (solo en redacción) → instrucción concreta.

Las reglas de la fase son las de la especificación funcional, inyectadas literalmente. No se
confía en que el modelo las recuerde de turnos anteriores.

**Redacción:** temperatura media-alta, salida limitada a una escena. Devuelve la prosa más
un bloque de metadatos separado.

**Continuidad:** temperatura baja, salida estructurada obligatoria (JSON validado contra
esquema antes de renderizar a markdown). Un hallazgo sin ubicación verificable se descarta.

## 6.1 Evaluador de compuerta

Llamada separada de la generación, con tres diferencias deliberadas:

- **Temperatura baja** y salida estructurada obligatoria.
- **No recibe el razonamiento del generador**, solo el artefacto y la rúbrica. Si ve la
  justificación de por qué se escribió así, la adopta y aprueba.
- **Criterios binarios, no puntuación global.** Un "7,5 sobre 10" no es accionable; "el
  criterio 2 falla porque los capítulos 14–17 no escalan" sí.

```json
{
  "aprobado": false,
  "criterios": [
    {"id": 1, "cumple": true},
    {"id": 2, "cumple": false,
     "evidencia": "Caps. 14-17 mantienen la misma presión sobre Kira",
     "correccion_sugerida": "Adelantar la revelación del cap. 19 al 15"}
  ]
}
```

La corrección sugerida se inyecta en el siguiente intento de generación. Sin ella, el
reintento produce una variante del mismo fallo.

## 6.2 Presupuesto y control de coste

Una novela de 90.000 palabras en modo autónomo implica, con las tres capas de contexto y
reintentos incluidos, del orden de 8–15 millones de tokens. El controlador impone:

| Límite | Comportamiento al alcanzarlo |
|---|---|
| `tokens_max` | Checkpoint y escalado |
| `horas_max` | Checkpoint y escalado |
| 3 reintentos por compuerta | Continuar con deuda |
| 3 pasadas de continuidad final | Escalar si persiste `ALTO` |

Consumo estimado por fase: fases 0–3 alrededor del 15 %, redacción el 60 %, continuidad el
25 %. La continuidad es cara porque relee; de ahí que el Nivel 1 sea determinista.

## 7. Motor de continuidad

Pasada en dos niveles:

**Nivel 1 — determinista, sin modelo.** Sobre front matter y glosario: solapes temporales,
personajes en dos lugares a la vez, variantes de término no registradas, saltos de
numeración. Barato y ejecutable en cada commit.

**Nivel 2 — semántico, con modelo.** Sobre el cuerpo del texto, acotado a los capítulos
tocados desde la última pasada y a los que comparten `elementos_biblia`. Verifica
consistencia de reglas del mundo y de conocimiento de los personajes.

Contrato de salida:

```json
{
  "hallazgos": [{
    "severidad": "ALTO",
    "eje": "tecnologia",
    "ubicacion": "cap. 14, escena 2",
    "descripcion": "Kira desactiva el campo desde un terminal remoto",
    "contradice": "bible/technology.md — los campos requieren presencia física (cap. 5)",
    "opciones": [
      {"accion": "Cambiar la regla en la biblia", "coste": "Revisar cap. 5 y 9"},
      {"accion": "Kira usa un intermediario presente", "coste": "Introducir o reubicar personaje"}
    ]
  }]
}
```

## 8. Integración

Interfaz de línea de comandos sobre el directorio del proyecto. Los comandos de la
especificación funcional se mapean uno a uno.

Git como capa de persistencia: cada operación que modifica artefactos genera un commit con
mensaje trazable (`fase(escena): cap 14.2 — borrador`). Esto da historial y deshacer sin
construir nada.

Opcional: hook de pre-commit que ejecuta la continuidad de Nivel 1 y bloquea si aparece un
hallazgo `ALTO`.

## 9. Errores y degradación

| Situación | Respuesta |
|---|---|
| Artefacto de fase anterior ausente | Bloquear y nombrar el archivo que falta |
| Salida del modelo no válida contra esquema | Un reintento con el error; luego error al usuario |
| Contexto excedido | Degradar a resúmenes y avisar de qué se omitió |
| Estado inconsistente en `project.yaml` | Reconstruir desde los archivos presentes |

Principio: ante duda, el agente para y pregunta. Nunca escribe sobre un artefacto existente
sin confirmación.

## 10. Observabilidad

Por sesión se registra: fase, comando, artefactos leídos, tokens consumidos, latencia y
resultado. Métricas de interés: hallazgos por 10.000 palabras, tasa de rechazo de escenas
por el autor, coste por capítulo.

## 11. Riesgos del modo autónomo

| Riesgo | Mitigación |
|---|---|
| **Deriva de registro** entre el primer y el último tercio | Muestra de estilo fija; auditoría de registro en Compuerta 2; comparación de embeddings de estilo por tercios |
| **Auto-aprobación complaciente** | Evaluador independiente, criterios binarios, criterio 6 de aceptación (una ejecución que aprueba todo a la primera indica rúbricas mal calibradas) |
| **Homogeneización**: todas las escenas con la misma forma | Variación forzada de longitud, POV y tipo de escena desde la escaleta; auditoría de varianza |
| **Bucle infinito de corrección** | Límite duro de reintentos y pasadas |
| **Colapso de contexto** en capítulos tardíos | Resúmenes rodantes y recuperación selectiva; el capítulo 40 no ve el 3 en bruto |
| **Coste desbocado** | Presupuesto declarado y checkpoint al alcanzarlo |
| **Trama que se resuelve sola** porque el agente evita el conflicto | Criterio de cambio de estado por capítulo en Compuerta 1 |

El riesgo residual que ninguna mitigación elimina: el modo autónomo produce coherencia, no
necesariamente interés. La rúbrica detecta que un capítulo no escala; no detecta que la
novela entera es previsible. Eso sigue requiriendo lectura humana.

## 12. Abierto

- Estrategia de indexación cuando la biblia supere las 50.000 palabras.
- Si la continuidad de Nivel 2 debe correr en CI o solo bajo demanda (coste).
- Calibración empírica de los umbrales de rúbrica: con umbrales altos el agente no termina; con umbrales bajos entrega borradores planos.
- Si conviene un evaluador con modelo distinto al generador para reducir el sesgo de auto-aprobación.
- Soporte para series de varios libros con biblia compartida.
