export { crearCliente, PREFIJO_API, type Cliente, type OpcionesCliente } from './cliente'
export { ProveedorCliente, useCliente } from './contexto-cliente'
export { aProblema, ErrorDeApi, exigir, problemaDe, type Problema } from './problema'
export type { components, operations, paths } from './schema'

import type { components } from './schema'

/** Los schemas del contrato, por su nombre en `specs/openapi.yaml`. */
export type Esquemas = components['schemas']
