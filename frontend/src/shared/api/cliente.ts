import createClient from 'openapi-fetch'
import type { paths } from './schema'

/** Prefijo bajo el que el proxy de Vite sirve el backend. */
export const PREFIJO_API = '/api'

export type Cliente = ReturnType<typeof createClient<paths>>

export interface OpcionesCliente {
  /** Costura para las pruebas: sin él, el `fetch` del navegador. */
  fetch?: (peticion: Request) => Promise<Response>
  /** Origen absoluto; sin él, las rutas son relativas a la página. */
  origen?: string
}

export function crearCliente(opciones: OpcionesCliente = {}): Cliente {
  return createClient<paths>({
    baseUrl: `${opciones.origen ?? ''}${PREFIJO_API}`,
    ...(opciones.fetch ? { fetch: opciones.fetch } : {}),
  })
}
