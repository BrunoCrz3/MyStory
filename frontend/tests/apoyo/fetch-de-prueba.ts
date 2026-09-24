// Sirve respuestas registradas a las peticiones del cliente. Vive solo en tests/: el
// cliente de src/ lo recibe inyectado y no sabe que existe.
import { PREFIJO_API } from '@/shared/api'

export interface RespuestaDePrueba {
  status: number
  cuerpo?: unknown
  tipo?: string
}

export interface PeticionRegistrada {
  metodo: string
  ruta: string
  plantilla: string
  query: Record<string, string>
  cuerpo: unknown
}

type Productor = RespuestaDePrueba | ((peticion: PeticionRegistrada) => RespuestaDePrueba)

function casa(plantilla: string, ruta: string): boolean {
  const patron = new RegExp(`^${plantilla.replace(/\{[^}]+\}/g, '[^/]+')}$`)
  return patron.test(ruta)
}

export function crearFetchDePrueba() {
  const registradas: { metodo: string; plantilla: string; productor: Productor }[] = []
  const peticiones: PeticionRegistrada[] = []

  function responder(metodo: string, plantilla: string, productor: Productor) {
    // La última registración de una ruta gana: una prueba puede cambiar la respuesta a mitad.
    registradas.unshift({ metodo: metodo.toUpperCase(), plantilla, productor })
  }

  async function fetchDePrueba(peticion: Request): Promise<Response> {
    const url = new URL(peticion.url)
    const ruta = url.pathname.startsWith(PREFIJO_API) ? url.pathname.slice(PREFIJO_API.length) : url.pathname
    const texto = await peticion.clone().text()
    const encontrada = registradas.find((r) => r.metodo === peticion.method && casa(r.plantilla, ruta))
    const registrada: PeticionRegistrada = {
      metodo: peticion.method,
      ruta,
      plantilla: encontrada?.plantilla ?? '',
      query: Object.fromEntries(url.searchParams),
      cuerpo: texto === '' ? undefined : JSON.parse(texto),
    }
    peticiones.push(registrada)

    if (!encontrada) {
      return new Response(
        JSON.stringify({ type: '/problemas/error-interno', title: `Sin respuesta de prueba para ${peticion.method} ${ruta}`, status: 404 }),
        { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
      )
    }
    const { status, cuerpo, tipo } = typeof encontrada.productor === 'function'
      ? encontrada.productor(registrada)
      : encontrada.productor
    const esError = status >= 400
    return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
      status,
      headers: { 'Content-Type': tipo ?? (esError ? 'application/problem+json' : 'application/json') },
    })
  }

  const peticionesA = (metodo: string, plantilla: string) =>
    peticiones.filter((p) => p.metodo === metodo.toUpperCase() && p.plantilla === plantilla)

  return { fetch: fetchDePrueba, responder, peticiones, peticionesA }
}

export type FetchDePrueba = ReturnType<typeof crearFetchDePrueba>
