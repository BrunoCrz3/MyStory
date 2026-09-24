/**
 * Generado por scripts/generar-api.mjs desde specs/openapi.yaml. No editar a mano:
 * se regenera con `npm run gen:api` y la prueba de contrato falla si difiere.
 */

export interface paths {
    "/salud": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Estado de la instancia
         * @description Responde a RF-META-01. Sirve para que el frontend sepa, sin adivinar, si el gate
         *     de Lean está activo y cuánto presupuesto en vuelo queda libre.
         */
        get: operations["obtenerSalud"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/briefs/validacion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Valida un brief sin crear la novela
         * @description Responde a RF-INTAKE-01, RF-INTAKE-02 y RF-INTAKE-03. El formulario llama aquí
         *     antes de crear nada: devuelve los `Dato faltante`, las `Contradicción de brief`
         *     detectadas por reglas deterministas entre campos, los `Fragmento sospechoso`
         *     hallados en el texto libre y los hechos que de él se extraen.
         *
         *     El texto libre es **contenido no confiable**: entra marcado como datos y lo que
         *     parece una instrucción al sistema se registra y se descarta, nunca se obedece.
         *
         *     Acepta un **`BriefNovelaParcial`** (TO-037): todos los campos son opcionales, y un
         *     campo obligatorio del brief completo que no llega, o llega vacío, se devuelve como
         *     `Dato faltante` con su pregunta de reintento en un `200`. Solo un cuerpo mal formado
         *     —un tipo equivocado, un valor fuera de su `enum`— es un `422`.
         */
        post: operations["validarBrief"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Lista las novelas de la instancia
         * @description Responde a RF-NOVEL-02.
         */
        get: operations["listarNovelas"];
        put?: never;
        /**
         * Crea una novela a partir de un brief validado
         * @description Responde a RF-NOVEL-01. Valida el brief contra su schema y lo persiste; **no**
         *     lanza la generación, que es una operación aparte y cara.
         *
         *     Exige el **`BriefNovela` completo**: un campo obligatorio ausente es un `422`, porque
         *     el brief parcial solo lo acepta la validación (TO-037). Si el brief cumple el schema
         *     pero no pasa la validación de dominio —dos campos se contradicen, o un campo llega
         *     vacío— responde `400` con `brief-invalido` y el detalle en las extensiones del
         *     problema: la petición estaba bien formada.
         */
        post: operations["crearNovela"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        /**
         * Devuelve una novela con su estado y su versión vigente
         * @description Responde a RF-NOVEL-03.
         */
        get: operations["obtenerNovela"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/generaciones": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        /**
         * Historial de generaciones de una novela
         * @description Responde a RF-PROC-04. Incluye la inicial y todas las regeneraciones dirigidas,
         *     que es lo que permite reconstruir el coste total de la novela.
         */
        get: operations["listarGeneraciones"];
        put?: never;
        /**
         * Encola la generación completa de la novela
         * @description Responde a RF-PROC-01. Devuelve `202` en cuanto el trabajo queda encolado: la
         *     generación de diez capítulos dura minutos y el worker la ejecuta fuera de la
         *     petición. El progreso se sigue con `obtenerGeneracion`.
         *
         *     **Un segundo `POST` mientras hay una generación o una regeneración en curso
         *     devuelve `409` con `generacion-en-curso`** y el identificador de la que ya corre,
         *     en vez de encolar otra o de devolver la existente en silencio. Encolar dos sería
         *     gastar tokens dos veces; devolver un `202` silencioso escondería que no se ha
         *     lanzado nada nuevo, que es justo lo que hay que saber antes de esperar diez
         *     minutos.
         *
         *     Si la estimación del trabajo supera el presupuesto en vuelo, falla al encolarse
         *     con `trabajo-no-cabe-en-pool`: esperar un hueco que no va a existir nunca no es
         *     esperar, es colgarse.
         */
        post: operations["lanzarGeneracion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/generaciones/{generacion_id}": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                generacion_id: components["parameters"]["GeneracionId"];
            };
            cookie?: never;
        };
        /**
         * Progreso de una generación
         * @description Responde a RF-PROC-05. Es el recurso que el frontend sondea.
         *
         *     **Cuándo dejar de sondear**: cuando `es_terminal` es `true`. En ese caso
         *     `intervalo_sondeo_segundos` viene a `null`. Los estados terminales son
         *     `Publicada` y `Detenida`; cualquier otro es transitorio. El cliente no debe
         *     deducir la terminalidad del nombre del estado: para eso está el booleano.
         */
        get: operations["obtenerGeneracion"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        /**
         * Historial de versiones de una novela
         * @description Responde a RF-VER-01. Cada entrada dice a qué versión sucede y cuántos capítulos
         *     cambiaron respecto a ella, que es lo que la lectura marca.
         */
        get: operations["listarVersiones"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Una versión con su índice de capítulos
         * @description Responde a RF-VER-02. Es lo que alimenta el índice navegable: número, título y la
         *     marca `modificado` de cada capítulo respecto a la versión anterior.
         *
         *     **La versión anterior sigue siendo consultable entera** (`CLAUDE.md` regla 15):
         *     pedir la versión 1 después de publicar la 3 devuelve la 1 tal como se publicó.
         */
        get: operations["obtenerVersion"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/capitulos": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Capítulos de una versión, con su texto
         * @description Responde a RF-NOVEL-05. Devuelve la novela entera de esa versión. Con diez
         *     capítulos de 1.500 palabras la respuesta es de unos pocos cientos de kilobytes,
         *     así que no se pagina: paginar obligaría al lector a esperar entre capítulos.
         */
        get: operations["listarCapitulos"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/capitulos/{numero}": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
                /**
                 * @description Número de capítulo dentro de la obra, empezando en 1.
                 * @example 4
                 */
                numero: components["parameters"]["NumeroCapitulo"];
            };
            cookie?: never;
        };
        /**
         * Un capítulo de una versión
         * @description Responde a RF-NOVEL-05.
         */
        get: operations["obtenerCapitulo"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/ficha": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Ficha de personajes y lugares de una versión
         * @description Responde a RF-VER-04. Se genera desde la story bible de **esa** versión, no de la
         *     vigente, y cada entrada trae los capítulos donde aparece para que la lectura
         *     enlace a ellos.
         */
        get: operations["obtenerFicha"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/portada": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Portada con la dedicatoria
         * @description Responde a RF-VER-05.
         */
        get: operations["obtenerPortada"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/hechos": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Hechos vigentes en una versión
         * @description Responde a RF-CANON-03. Es lo que permite al lector elegir un hecho concreto
         *     cuando pide un cambio, en vez de seleccionar un fragmento y esperar que el
         *     sistema adivine.
         *
         *     **Se resuelve por vigencia, nunca por estatus** (TO-028): en la versión 1, un
         *     hecho que hoy está `retconeado` seguía siendo verdad, y filtrar por estatus lo
         *     dejaría fuera.
         */
        get: operations["listarHechos"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/solicitudes-cambio": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * El lector pide un cambio sobre un hecho o un fragmento
         * @description Responde a RF-VER-06 y RF-VER-07. **No regenera nada**: calcula el
         *     `Análisis de impacto` —los capítulos que **usan** el hecho, no solo el que lo
         *     estableció— y lo devuelve para que el lector lo confirme.
         *
         *     Si se envía `fragmento` en vez de `hecho_id`, el sistema propone un
         *     `hecho_candidato` y la solicitud queda `pendiente-de-confirmacion`: la selección
         *     de fragmento **nunca regenera sola** (TO-011).
         *
         *     Devuelve `409 generacion-en-curso` si la novela tiene una generación o una
         *     regeneración en marcha.
         */
        post: operations["crearSolicitudCambio"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                solicitud_id: components["parameters"]["SolicitudId"];
            };
            cookie?: never;
        };
        /**
         * Una solicitud de cambio con su análisis de impacto
         * @description Responde a RF-VER-06.
         */
        get: operations["obtenerSolicitudCambio"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}/confirmacion": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                solicitud_id: components["parameters"]["SolicitudId"];
            };
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Confirma la solicitud y encola la regeneración dirigida
         * @description Responde a RF-VER-08. Aplica el retcon —cierra el hecho viejo por vigencia y abre
         *     el nuevo—, marca `Obsoleto` los capítulos afectados y encola una regeneración que
         *     reescribe **solo** esos. El resultado es una versión nueva; la anterior se
         *     conserva entera.
         *
         *     Devuelve `202` con la `Generacion` dirigida, que se sondea igual que la inicial.
         */
        post: operations["confirmarSolicitudCambio"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/novelas/{novel_id}/versiones/{version}/export": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        /**
         * Descarga el PDF de una versión
         * @description Responde a RF-EXP-02. Devuelve `404 export-no-disponible` si todavía no se ha
         *     generado o si sigue en curso; el estado se consulta con `exportarVersion`.
         */
        get: operations["descargarExport"];
        put?: never;
        /**
         * Genera el PDF de una versión
         * @description Responde a RF-EXP-01. Sale del **mismo render** que la lectura web, con
         *     `page.pdf()` de Playwright: con otro motor se validaría uno y se entregaría otro.
         *
         *     Se genera **una vez por versión**, porque las versiones son inmutables (TO-025).
         *     Un segundo `POST` sobre una versión ya exportada devuelve `200` con el export que
         *     ya existe en vez de rehacerlo.
         */
        post: operations["exportarVersion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * Problema
         * @description Cuerpo de error según RFC 9457. **Toda** respuesta de error de esta API usa este
         *     schema y el tipo de medio `application/problem+json`, incluidos los 422 de
         *     validación.
         *
         *     El catálogo de `type` es **cerrado**. Un catálogo abierto degenera en un campo de
         *     texto que nadie puede discriminar.
         */
        Problema: {
            /**
             * @description Identificador estable del tipo de problema.
             * @enum {string}
             */
            type: "/problemas/peticion-invalida" | "/problemas/brief-invalido" | "/problemas/novela-no-encontrada" | "/problemas/version-no-encontrada" | "/problemas/hecho-no-encontrado" | "/problemas/generacion-en-curso" | "/problemas/transicion-invalida" | "/problemas/trabajo-no-cabe-en-pool" | "/problemas/limite-de-intentos-agotado" | "/problemas/palabra-prohibida-persistente" | "/problemas/export-no-disponible" | "/problemas/error-interno";
            /** @description Resumen legible, estable para un mismo `type`. */
            title: string;
            status: number;
            /** @description Explicación de **esta** ocurrencia. */
            detail?: string;
            /** Format: uri-reference */
            instance?: string;
            /** Format: uuid */
            novel_id?: string | null;
            /** Format: uuid */
            generacion_id?: string | null;
            capitulo?: number | null;
            intentos_restantes?: number | null;
            traza_langfuse_id?: string | null;
            datos_faltantes?: components["schemas"]["DatoFaltante"][];
            contradicciones?: components["schemas"]["ContradiccionBrief"][];
        };
        /**
         * EstadoNovela
         * @description Los estados de `domain-knowledge.md` § Estados, uno a uno y sin añadidos. Si el
         *     código necesita uno que no está aquí, se actualiza antes la ontología.
         * @enum {string}
         */
        EstadoNovela: "Configurando" | "Planificando" | "Escribiendo" | "Validando" | "Publicando" | "Publicada" | "Regenerando" | "Detenida";
        /**
         * EstadoCapitulo
         * @enum {string}
         */
        EstadoCapitulo: "Pendiente" | "Escribiendo" | "Validando" | "Aceptado" | "Reescribiendo" | "Agotado" | "Obsoleto";
        /**
         * Comprador
         * @description Quien encarga, paga y configura. **`identificador` es opaco**: nunca un correo ni
         *     un nombre. No hay autenticación, así que esto es un dato del brief y no un
         *     principal.
         */
        Comprador: {
            /**
             * @description Cadena opaca elegida por quien integra. No es PII.
             * @example comprador-0042
             */
            identificador: string;
            /** @example hermana */
            relacion_con_destinatario?: string;
        };
        /**
         * Destinatario
         * @description Persona a quien va dirigida la novela.
         */
        Destinatario: {
            nombre: string;
            edad: number;
            rasgos?: string[];
            recuerdos?: string[];
            /**
             * Format: date
             * @description Alimenta el invariante Lean de coherencia de edad, cuando el gate está activo.
             */
            fecha_nacimiento?: string | null;
        };
        /** Ocasion */
        Ocasion: {
            /** @enum {string} */
            tipo: "cumpleanos" | "boda" | "aniversario" | "jubilacion" | "nacimiento" | "otra";
            /** Format: date */
            fecha?: string | null;
            tono_esperado?: string | null;
        };
        /** Dedicatoria */
        Dedicatoria: {
            texto: string;
            firma?: string | null;
        };
        /**
         * ElementoPersonalizado
         * @description Detalle del destinatario que la novela debe integrar. **`obligatorio` no es un
         *     matiz**: uno obligatorio que no aparece en ningún capítulo impide publicar.
         */
        ElementoPersonalizado: {
            enunciado: string;
            obligatorio: boolean;
            /**
             * @default formulario
             * @enum {string}
             */
            origen?: "formulario" | "texto-libre";
        };
        /**
         * TextoLibre
         * @description Anécdota o carta que el comprador pega sin estructura. **Contenido no confiable**:
         *     entra marcado como datos, nunca en la posición de las instrucciones, y lo que
         *     parece una orden al sistema se registra como `Fragmento sospechoso` y se descarta.
         */
        TextoLibre: {
            contenido: string;
            /** @example carta de su hermana */
            procedencia?: string;
        };
        /** VozNarrativa */
        VozNarrativa: {
            /**
             * @default tercera
             * @enum {string}
             */
            persona?: "primera" | "segunda" | "tercera";
            /**
             * @default pasado
             * @enum {string}
             */
            tiempo_verbal?: "presente" | "pasado";
            /**
             * @default interna
             * @enum {string}
             */
            focalizacion?: "interna" | "externa" | "cero";
        };
        /**
         * BriefNovela
         * @description Salida estructurada y validada de la entrevista. En la demo lo produce el
         *     formulario; el entrevistador conversacional produce este mismo objeto.
         * @example {
         *       "comprador": {
         *         "identificador": "comprador-0042",
         *         "relacion_con_destinatario": "hermana"
         *       },
         *       "destinatario": {
         *         "nombre": "Marta",
         *         "edad": 34,
         *         "rasgos": [
         *           "tozuda",
         *           "le encanta el mar"
         *         ],
         *         "recuerdos": [
         *           "el verano en que aprendió a navegar"
         *         ],
         *         "fecha_nacimiento": "1992-04-18"
         *       },
         *       "ocasion": {
         *         "tipo": "cumpleanos",
         *         "fecha": "2026-10-02",
         *         "tono_esperado": "celebratorio"
         *       },
         *       "genero": "aventura costumbrista",
         *       "tono": "cálido y con humor",
         *       "dedicatoria": {
         *         "texto": "Para Marta, que siempre vuelve al mar.",
         *         "firma": "Tu hermana"
         *       },
         *       "elementos_personalizados": [
         *         {
         *           "enunciado": "Aprendió a navegar en un barco llamado Alondra",
         *           "obligatorio": true
         *         },
         *         {
         *           "enunciado": "Tiene un perro",
         *           "obligatorio": false
         *         }
         *       ],
         *       "temas_excluidos": [
         *         "enfermedad"
         *       ],
         *       "palabras_prohibidas": [
         *         "Luis"
         *       ],
         *       "reglas_mundo": [
         *         "El abuelo nunca aparece"
         *       ],
         *       "textos_libres": [
         *         {
         *           "contenido": "Aquel verano se empeñó en soltar amarras sin ayuda de nadie.",
         *           "procedencia": "carta de su hermana"
         *         }
         *       ]
         *     }
         */
        BriefNovela: {
            comprador: components["schemas"]["Comprador"];
            destinatario: components["schemas"]["Destinatario"];
            ocasion: components["schemas"]["Ocasion"];
            /** @example aventura costumbrista */
            genero: string;
            /** @example cálido y con humor */
            tono: string;
            dedicatoria: components["schemas"]["Dedicatoria"];
            premisa?: string | null;
            elementos_personalizados?: components["schemas"]["ElementoPersonalizado"][];
            /** @description Temas que no deben aparecer, aunque ninguna palabra los nombre. */
            temas_excluidos?: string[];
            /** @description Nivel `novela` del guardrail. Los niveles `global` y `perfil` los pone el sistema. */
            palabras_prohibidas?: string[];
            /** @description Restricciones que el texto no puede violar, del tipo «el abuelo nunca aparece». */
            reglas_mundo?: string[];
            textos_libres?: components["schemas"]["TextoLibre"][];
            voz_narrativa?: components["schemas"]["VozNarrativa"];
        };
        /**
         * CompradorParcial
         * @description `Comprador` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        CompradorParcial: {
            identificador?: string;
            relacion_con_destinatario?: string;
        };
        /**
         * DestinatarioParcial
         * @description `Destinatario` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        DestinatarioParcial: {
            nombre?: string;
            edad?: number;
            rasgos?: string[];
            recuerdos?: string[];
            /** Format: date */
            fecha_nacimiento?: string | null;
        };
        /**
         * OcasionParcial
         * @description `Ocasion` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        OcasionParcial: {
            /** @enum {string} */
            tipo?: "cumpleanos" | "boda" | "aniversario" | "jubilacion" | "nacimiento" | "otra";
            /** Format: date */
            fecha?: string | null;
            tono_esperado?: string | null;
        };
        /**
         * DedicatoriaParcial
         * @description `Dedicatoria` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        DedicatoriaParcial: {
            texto?: string;
            firma?: string | null;
        };
        /**
         * ElementoPersonalizadoParcial
         * @description `ElementoPersonalizado` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        ElementoPersonalizadoParcial: {
            enunciado?: string;
            obligatorio?: boolean;
            /**
             * @default formulario
             * @enum {string}
             */
            origen?: "formulario" | "texto-libre";
        };
        /**
         * TextoLibreParcial
         * @description `TextoLibre` sin campos obligatorios. Solo lo acepta la validación del brief.
         */
        TextoLibreParcial: {
            contenido?: string;
            procedencia?: string;
        };
        /**
         * BriefNovelaParcial
         * @description El brief tal como está mientras se rellena: **los mismos campos que `BriefNovela`,
         *     todos opcionales**, también dentro de los objetos anidados, y sin longitud mínima
         *     (TO-037). Es lo que acepta `validarBrief`, que responde con los `Dato faltante` en
         *     vez de rechazarlo. **No sirve para crear una novela**: `crearNovela` exige el
         *     `BriefNovela` completo.
         *
         *     Conserva los tipos, los `enum`, las longitudes máximas y los rangos: un valor mal
         *     formado sigue siendo un `422`. Lo único que se relaja es la obligatoriedad.
         * @example {
         *       "comprador": {
         *         "identificador": "comprador-0042"
         *       },
         *       "destinatario": {
         *         "edad": 7
         *       },
         *       "ocasion": {
         *         "tipo": "cumpleanos"
         *       },
         *       "tono": "adulto irónico",
         *       "dedicatoria": {
         *         "texto": "Para quien cumple siete."
         *       }
         *     }
         */
        BriefNovelaParcial: {
            comprador?: components["schemas"]["CompradorParcial"];
            destinatario?: components["schemas"]["DestinatarioParcial"];
            ocasion?: components["schemas"]["OcasionParcial"];
            genero?: string;
            tono?: string;
            dedicatoria?: components["schemas"]["DedicatoriaParcial"];
            premisa?: string | null;
            elementos_personalizados?: components["schemas"]["ElementoPersonalizadoParcial"][];
            temas_excluidos?: string[];
            palabras_prohibidas?: string[];
            reglas_mundo?: string[];
            textos_libres?: components["schemas"]["TextoLibreParcial"][];
            voz_narrativa?: components["schemas"]["VozNarrativa"];
        };
        /** DatoFaltante */
        DatoFaltante: {
            /** @example destinatario.nombre */
            campo: string;
            /**
             * @description Lo que el formulario vuelve a preguntar. El sistema repregunta; nunca rellena el
             *     hueco. Un campo es un dato faltante si es obligatorio en `BriefNovela` y no llega
             *     en el `BriefNovelaParcial`, o llega vacío.
             */
            pregunta_reintento?: string;
        };
        /**
         * ContradiccionBrief
         * @description Conflicto entre dos datos del comprador, detectado por reglas deterministas entre
         *     campos. El alcance exige al menos un tipo; `edad-vs-tono` es el obligatorio.
         */
        ContradiccionBrief: {
            campos: string[];
            /** @enum {string} */
            tipo: "edad-vs-tono" | "edad-vs-genero" | "fecha-vs-edad" | "otra";
            explicacion?: string;
        };
        /**
         * FragmentoSospechoso
         * @description Parte del texto libre marcada como intento de instrucción al sistema. Se registra y se descarta.
         */
        FragmentoSospechoso: {
            fragmento: string;
            /** @example Parece una instrucción dirigida al sistema */
            motivo: string;
        };
        /** ResultadoValidacionBrief */
        ResultadoValidacionBrief: {
            valido: boolean;
            datos_faltantes: components["schemas"]["DatoFaltante"][];
            contradicciones: components["schemas"]["ContradiccionBrief"][];
            fragmentos_sospechosos: components["schemas"]["FragmentoSospechoso"][];
            /** @description Hechos que el sistema ha leído del texto libre. Entran como propuestos. */
            hechos_extraidos: {
                enunciado: string;
                /** @enum {string} */
                origen?: "texto-libre";
            }[];
        };
        /** NovelaResumen */
        NovelaResumen: {
            /** Format: uuid */
            novel_id: string;
            /** @description Lo fija el planificador. Es `null` hasta que hay esquema. */
            titulo: string | null;
            estado: components["schemas"]["EstadoNovela"];
            version_vigente?: number | null;
            /** Format: date-time */
            creada_en: string;
        };
        /** Novela */
        Novela: {
            /** Format: uuid */
            novel_id: string;
            titulo?: string | null;
            estado: components["schemas"]["EstadoNovela"];
            version_vigente?: number | null;
            /** @description Sale de `config/thresholds.yaml` § `obra.capitulos`. */
            total_capitulos?: number;
            /** Format: date-time */
            creada_en: string;
            brief: components["schemas"]["BriefNovela"];
        };
        /**
         * Generacion
         * @description Una generación completa: la inicial o una regeneración dirigida. Es el recurso que
         *     el frontend sondea.
         */
        Generacion: {
            /** Format: uuid */
            generacion_id: string;
            /** Format: uuid */
            novel_id: string;
            /** @enum {string} */
            tipo: "inicial" | "dirigida";
            estado: components["schemas"]["EstadoNovela"];
            /**
             * @description `true` cuando no va a cambiar más. **El cliente deja de sondear aquí** y no
             *     deduce la terminalidad del nombre del estado.
             */
            es_terminal: boolean;
            /** @description Cada cuánto conviene volver a preguntar. `null` si `es_terminal`. */
            intervalo_sondeo_segundos: number | null;
            capitulo_actual?: number | null;
            capitulos_aceptados: number;
            total_capitulos: number;
            /** @description Solo en las dirigidas: los capítulos que **usan** el hecho cambiado. */
            capitulos_a_regenerar?: number[];
            intentos_capitulo_actual?: number;
            /** @description Último capítulo completado. Es desde donde se reanuda. */
            checkpoint?: number | null;
            tokens_consumidos?: number;
            coste_usd?: number;
            traza_langfuse_id?: string | null;
            /** @description Cuando el estado es `Detenida`, el `type` del problema que la detuvo. */
            detenida_por?: string | null;
            version_resultante?: number | null;
            /** Format: date-time */
            iniciada_en: string;
            /** Format: date-time */
            terminada_en?: string | null;
        };
        /** Capitulo */
        Capitulo: {
            numero: number;
            titulo?: string | null;
            estado: components["schemas"]["EstadoCapitulo"];
            /** @description Es `null` mientras el capítulo no está aceptado. */
            texto?: string | null;
            palabras?: number | null;
            resumen?: string | null;
            gancho_cierre?: string | null;
            /** @description Nombre del personaje desde el que se narra. */
            pov?: string | null;
            lugar?: string | null;
            funcion_dramatica?: string | null;
            intentos?: number;
            /**
             * @description Si cambió respecto a la versión anterior. Es atributo del vínculo entre
             *     versión y capítulo, y es lo que la lectura marca.
             * @default false
             */
            modificado?: boolean;
        };
        /**
         * CapituloIndice
         * @description Entrada del índice navegable. Sin texto.
         */
        CapituloIndice: {
            numero: number;
            titulo?: string | null;
            palabras?: number | null;
            modificado: boolean;
        };
        /** VersionResumen */
        VersionResumen: {
            version: number;
            /** Format: date-time */
            publicada_en: string;
            version_anterior?: number | null;
            capitulos_modificados: number[];
            /** @description En una regeneración, el enunciado de la solicitud de cambio. */
            motivo?: string | null;
        };
        /** Version */
        Version: {
            version: number;
            /** Format: uuid */
            novel_id: string;
            titulo?: string | null;
            /** Format: date-time */
            publicada_en: string;
            version_anterior?: number | null;
            /** @description Hash del contenido. Es lo que hace comprobable que una versión publicada no cambia. */
            hash?: string | null;
            dedicatoria?: components["schemas"]["Dedicatoria"];
            capitulos: components["schemas"]["CapituloIndice"][];
        };
        /** Portada */
        Portada: {
            titulo: string;
            dedicatoria: components["schemas"]["Dedicatoria"];
            destinatario?: string;
            ocasion?: string | null;
        };
        /** EntradaFicha */
        EntradaFicha: {
            nombre: string;
            descripcion?: string | null;
            /** @description Capítulos donde aparece, para que la ficha enlace a ellos. */
            capitulos: number[];
        };
        /**
         * Ficha
         * @description Personajes y lugares de una versión, generados desde la story bible de esa versión.
         */
        Ficha: {
            personajes: components["schemas"]["EntradaFicha"][];
            lugares: components["schemas"]["EntradaFicha"][];
        };
        /**
         * Hecho
         * @description Enunciado verdadero en el mundo ficcional, vigente en la versión consultada.
         */
        Hecho: {
            /** Format: uuid */
            hecho_id: string;
            enunciado: string;
            /** @enum {string} */
            estado: "propuesto" | "adoptado" | "descartado" | "retconeado" | "refutado";
            /** @enum {string} */
            origen?: "brief" | "texto-libre" | "extraccion";
            capitulo_establece?: number | null;
            /**
             * @description Capítulos que se apoyan en el hecho. **Es lo que decide el análisis de
             *     impacto**: un hecho establecido en el 2 y mencionado en el 7 obliga a
             *     reescribir los dos.
             */
            capitulos_usan: number[];
            /** @description Fragmento literal del capítulo que sostiene el hecho. */
            fragmento_soporte?: string | null;
        };
        /**
         * NuevaSolicitudCambio
         * @description El lector pide un cambio. **Exactamente uno** de `hecho_id` o `fragmento`: con
         *     `hecho_id` el cambio es directo; con `fragmento` el sistema propone un hecho
         *     candidato y espera confirmación.
         */
        NuevaSolicitudCambio: {
            /** Format: uuid */
            hecho_id?: string | null;
            fragmento?: string | null;
            enunciado_nuevo: string;
            /** @description Desde qué capítulo de la lectura se pidió. */
            capitulo_origen: number;
        } & (unknown | unknown);
        /** AnalisisImpacto */
        AnalisisImpacto: {
            /** @description Capítulos que **usan** el hecho. Se calcula sobre `usa`, no sobre `establece`. */
            capitulos_afectados: number[];
            hechos_derivados?: string[];
        };
        /** SolicitudCambio */
        SolicitudCambio: {
            /** Format: uuid */
            solicitud_id: string;
            /** Format: uuid */
            novel_id: string;
            enunciado_nuevo: string;
            capitulo_origen: number;
            /** @enum {string} */
            estado: "pendiente-de-confirmacion" | "confirmada" | "aplicada" | "descartada";
            hecho_afectado?: components["schemas"]["Hecho"];
            /**
             * @description Cuando la solicitud llegó por fragmento: el hecho que el sistema propone. El
             *     lector lo confirma antes de que se regenere nada.
             */
            hecho_candidato?: string | null;
            analisis_impacto?: components["schemas"]["AnalisisImpacto"];
            version_resultante?: number | null;
        };
        /** Exportacion */
        Exportacion: {
            version: number;
            /** @enum {string} */
            estado: "en-curso" | "disponible" | "fallido";
            /** Format: uri-reference */
            url_descarga?: string | null;
            /** Format: date-time */
            generado_en?: string | null;
            /** @description Resultado del validador que compara el PDF con la lectura web. */
            paridad_pdf_web?: boolean | null;
        };
        /** Salud */
        Salud: {
            /** @enum {string} */
            estado: "ok" | "degradado";
            version_api: string;
            /**
             * @description `config/thresholds.yaml` § `formal.gate_activo`. Con el gate apagado no corren
             *     las tres demostraciones de cronología y la lectura debe decirlo.
             */
            gate_lean_activo: boolean;
            /**
             * @description `config/thresholds.yaml` § `medicion.cerrar_el_paso`. Con `false`, los
             *     validadores semánticos puntúan y no suspenden.
             */
            cerrar_el_paso: boolean;
            tokens_en_vuelo?: number;
            tokens_en_vuelo_total?: number;
            trabajos_en_cola?: number;
        };
    };
    responses: {
        /**
         * @description La petición está mal formada o no cumple el schema. Es el 422 de FastAPI,
         *     reescrito como `problem+json` para que **toda** respuesta de error tenga la misma
         *     forma.
         */
        PeticionInvalida: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/peticion-invalida",
                 *       "title": "La petición no cumple el schema",
                 *       "status": 422,
                 *       "detail": "destinatario.edad: debe ser un entero mayor o igual que 0",
                 *       "instance": "/novelas"
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /**
         * @description La petición está bien formada y cumple el schema de `BriefNovela`, pero el brief no
         *     es válido como encargo: dos campos se contradicen o un campo llega vacío.
         */
        BriefInvalido: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/brief-invalido",
                 *       "title": "El brief no es válido como encargo",
                 *       "status": 400,
                 *       "detail": "Hay 1 contradicción sin resolver.",
                 *       "instance": "/novelas",
                 *       "contradicciones": [
                 *         {
                 *           "campos": [
                 *             "destinatario.edad",
                 *             "tono"
                 *           ],
                 *           "tipo": "edad-vs-tono",
                 *           "explicacion": "El tono «adulto irónico» no encaja con una edad de 7 años."
                 *         }
                 *       ]
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /** @description No existe una novela con ese `novel_id`. */
        NovelaNoEncontrada: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/novela-no-encontrada",
                 *       "title": "Novela no encontrada",
                 *       "status": 404,
                 *       "instance": "/novelas/3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18"
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /** @description La novela existe, pero no tiene esa versión. */
        VersionNoEncontrada: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/version-no-encontrada",
                 *       "title": "Versión no encontrada",
                 *       "status": 404,
                 *       "novel_id": "3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18"
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /**
         * @description El recurso no existe. El `type` concreto dice cuál: `novela-no-encontrada`,
         *     `version-no-encontrada` o `hecho-no-encontrado`.
         */
        NoEncontrado: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /**
         * @description La operación choca con el estado actual. `generacion-en-curso` cuando ya hay una
         *     generación o una regeneración viva para esa novela; `transicion-invalida` cuando
         *     se pide algo que la máquina de estados no permite;
         *     `limite-de-intentos-agotado` y `palabra-prohibida-persistente` cuando la
         *     generación se detuvo y no se puede continuar sin intervención.
         */
        Conflicto: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/generacion-en-curso",
                 *       "title": "Ya hay una generación en curso para esta novela",
                 *       "status": 409,
                 *       "detail": "Consulta su progreso en lugar de lanzar otra.",
                 *       "novel_id": "3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18",
                 *       "generacion_id": "8f1c0b6e-4f6a-4c8e-9a1e-2b7d5f0c3a11"
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /**
         * @description La estimación del trabajo supera el presupuesto en vuelo total
         *     (`config/thresholds.yaml` § `en_vuelo.total`), así que nunca habrá hueco. Falla al
         *     encolarse en vez de esperar para siempre.
         */
        TrabajoNoCabe: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/trabajo-no-cabe-en-pool",
                 *       "title": "El trabajo no cabe en el presupuesto en vuelo",
                 *       "status": 422,
                 *       "detail": "Es un error de diseño del ensamblado, no una espera."
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /** @description La versión no tiene PDF generado, o su export sigue en curso. */
        ExportNoDisponible: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/export-no-disponible",
                 *       "title": "El PDF de esta versión no está disponible",
                 *       "status": 404
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
        /**
         * @description Fallo no previsto. El cuerpo **nunca** incluye trazas ni detalles internos: lleva
         *     el identificador de la traza de Langfuse para poder diagnosticarlo.
         */
        ErrorInterno: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "type": "/problemas/error-interno",
                 *       "title": "Error interno",
                 *       "status": 500,
                 *       "traza_langfuse_id": "tr-7d21"
                 *     }
                 */
                "application/problem+json": components["schemas"]["Problema"];
            };
        };
    };
    parameters: {
        /**
         * @description Identificador de la novela. Lo genera el servidor.
         * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
         */
        NovelId: string;
        GeneracionId: string;
        SolicitudId: string;
        /**
         * @description Entero correlativo por novela, empezando en 1.
         * @example 2
         */
        Version: number;
        /**
         * @description Número de capítulo dentro de la obra, empezando en 1.
         * @example 4
         */
        NumeroCapitulo: number;
        Limite: number;
        Desplazamiento: number;
    };
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    obtenerSalud: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La instancia responde. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Salud"];
                };
            };
            500: components["responses"]["ErrorInterno"];
        };
    };
    validarBrief: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BriefNovelaParcial"];
            };
        };
        responses: {
            /**
             * @description El brief se ha analizado. `valido` en `false` **no** es un error de la
             *     petición: es el resultado normal de un brief incompleto, y por eso va en un
             *     200 y no en un 400.
             */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResultadoValidacionBrief"];
                };
            };
            422: components["responses"]["PeticionInvalida"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    listarNovelas: {
        parameters: {
            query?: {
                limite?: components["parameters"]["Limite"];
                desplazamiento?: components["parameters"]["Desplazamiento"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Listado, de la más reciente a la más antigua. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        items: components["schemas"]["NovelaResumen"][];
                        total: number;
                    };
                };
            };
            500: components["responses"]["ErrorInterno"];
        };
    };
    crearNovela: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BriefNovela"];
            };
        };
        responses: {
            /** @description Novela creada, en estado `Configurando`. */
            201: {
                headers: {
                    /** @description URI de la novela creada. */
                    Location?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Novela"];
                };
            };
            400: components["responses"]["BriefInvalido"];
            422: components["responses"]["PeticionInvalida"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerNovela: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La novela. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Novela"];
                };
            };
            404: components["responses"]["NovelaNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    listarGeneraciones: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Generaciones, de la más reciente a la más antigua. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Generacion"][];
                };
            };
            404: components["responses"]["NovelaNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    lanzarGeneracion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Trabajo encolado. */
            202: {
                headers: {
                    /** @description URI del recurso de progreso. */
                    Location?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Generacion"];
                };
            };
            404: components["responses"]["NovelaNoEncontrada"];
            409: components["responses"]["Conflicto"];
            422: components["responses"]["TrabajoNoCabe"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerGeneracion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                generacion_id: components["parameters"]["GeneracionId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Estado actual de la generación. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Generacion"];
                };
            };
            404: components["responses"]["NoEncontrado"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    listarVersiones: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Versiones, de la más reciente a la más antigua. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionResumen"][];
                };
            };
            404: components["responses"]["NovelaNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerVersion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La versión. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Version"];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    listarCapitulos: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Capítulos en orden de lectura. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Capitulo"][];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerCapitulo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
                /**
                 * @description Número de capítulo dentro de la obra, empezando en 1.
                 * @example 4
                 */
                numero: components["parameters"]["NumeroCapitulo"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description El capítulo. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Capitulo"];
                };
            };
            404: components["responses"]["NoEncontrado"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerFicha: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La ficha. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ficha"];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerPortada: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La portada. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Portada"];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    listarHechos: {
        parameters: {
            query?: {
                /** @description Devuelve solo los hechos que **usa** ese capítulo. */
                capitulo?: number;
            };
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Hechos vigentes en la versión pedida. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Hecho"][];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    crearSolicitudCambio: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NuevaSolicitudCambio"];
            };
        };
        responses: {
            /** @description Solicitud registrada, con su análisis de impacto. */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SolicitudCambio"];
                };
            };
            404: components["responses"]["NoEncontrado"];
            409: components["responses"]["Conflicto"];
            422: components["responses"]["PeticionInvalida"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    obtenerSolicitudCambio: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                solicitud_id: components["parameters"]["SolicitudId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La solicitud. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SolicitudCambio"];
                };
            };
            404: components["responses"]["NoEncontrado"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    confirmarSolicitudCambio: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                solicitud_id: components["parameters"]["SolicitudId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Regeneración encolada. */
            202: {
                headers: {
                    /** @description URI del recurso de progreso. */
                    Location?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Generacion"];
                };
            };
            404: components["responses"]["NoEncontrado"];
            409: components["responses"]["Conflicto"];
            422: components["responses"]["TrabajoNoCabe"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    descargarExport: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description El PDF. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": string;
                };
            };
            404: components["responses"]["ExportNoDisponible"];
            500: components["responses"]["ErrorInterno"];
        };
    };
    exportarVersion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /**
                 * @description Identificador de la novela. Lo genera el servidor.
                 * @example 3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18
                 */
                novel_id: components["parameters"]["NovelId"];
                /**
                 * @description Entero correlativo por novela, empezando en 1.
                 * @example 2
                 */
                version: components["parameters"]["Version"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description La versión ya estaba exportada. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Exportacion"];
                };
            };
            /** @description Export encolado. */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Exportacion"];
                };
            };
            404: components["responses"]["VersionNoEncontrada"];
            500: components["responses"]["ErrorInterno"];
        };
    };
}
