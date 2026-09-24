import type { components } from './schema'

export type Problema = components['schemas']['Problema']

function esProblema(cuerpo: unknown): cuerpo is Problema {
  if (typeof cuerpo !== 'object' || cuerpo === null) return false
  const { type, title, status } = cuerpo as Record<string, unknown>
  return typeof type === 'string' && typeof title === 'string' && typeof status === 'number'
}

/**
 * Convierte el cuerpo de una respuesta de error en un `Problema`. Toda respuesta de error
 * del contrato lo es; si llega otra cosa —un proxy caído, por ejemplo— se representa como
 * `error-interno` con el status real, sin inventar más detalle.
 */
export function aProblema(cuerpo: unknown, status: number): Problema {
  if (esProblema(cuerpo)) return cuerpo
  return {
    type: '/problemas/error-interno',
    title: 'Respuesta inesperada del servidor',
    status: status >= 400 && status <= 599 ? status : 500,
  }
}

export class ErrorDeApi extends Error {
  constructor(readonly problema: Problema) {
    super(problema.title)
    this.name = 'ErrorDeApi'
  }
}

interface ResultadoFetch<T> {
  data?: T
  error?: unknown
  response: Response
}

/** Devuelve los datos de una llamada del cliente o lanza su `Problema` como `ErrorDeApi`. */
export async function exigir<T>(llamada: Promise<ResultadoFetch<T>>): Promise<T> {
  const { data, error, response } = await llamada
  if (!response.ok || data === undefined) throw new ErrorDeApi(aProblema(error, response.status))
  return data
}

/** El `Problema` de un error lanzado por `exigir`, o uno genérico si el error es otro. */
export function problemaDe(error: unknown): Problema {
  if (error instanceof ErrorDeApi) return error.problema
  return aProblema(undefined, 500)
}
