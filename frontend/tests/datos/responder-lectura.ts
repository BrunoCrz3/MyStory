import type { FetchDePrueba, PeticionRegistrada } from '../apoyo/fetch-de-prueba'
import { crearCapitulos, crearVersion, FICHA, PORTADA, VERSIONES } from './lectura'

const BASE = '/novelas/{novel_id}/versiones/{version}'

/** Capítulos modificados de cada versión que `obtenerVersion` sirve. */
export type MapaDeVersiones = Record<number, readonly number[]>

const versionDe = (peticion: PeticionRegistrada) => Number(peticion.ruta.split('/')[4])

/**
 * Registra todo lo que pide la página `lectura`, respondiendo según la versión de la ruta. Las
 * `candidatas` se sirven con `estado: candidata`; `listarVersiones` sigue dando solo `VERSIONES`,
 * las publicadas (TO-045).
 */
export function responderVersiones(prueba: FetchDePrueba, mapa: MapaDeVersiones, candidatas: readonly number[] = []) {
  const conVersion = (hacer: (version: number, modificados: readonly number[]) => unknown) =>
    (peticion: PeticionRegistrada) => {
      const version = versionDe(peticion)
      const modificados = mapa[version]
      return modificados === undefined
        ? { status: 404, cuerpo: { type: '/problemas/version-no-encontrada', title: 'Versión no encontrada', status: 404 } }
        : { status: 200, cuerpo: hacer(version, modificados) }
    }
  prueba.responder('get', BASE, conVersion((v, m) => crearVersion(v, m, candidatas.includes(v) ? 'candidata' : 'publicada')))
  prueba.responder('get', `${BASE}/capitulos`, conVersion((_, m) => crearCapitulos(m)))
  prueba.responder('get', `${BASE}/portada`, conVersion(() => PORTADA))
  prueba.responder('get', `${BASE}/ficha`, conVersion(() => FICHA))
  prueba.responder('get', '/novelas/{novel_id}/versiones', { status: 200, cuerpo: VERSIONES })
}

export function responderLectura(prueba: FetchDePrueba, version = 2, modificados: readonly number[] = []) {
  responderVersiones(prueba, { [version]: modificados })
}
