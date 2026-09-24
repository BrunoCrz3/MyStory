import type { FetchDePrueba } from '../apoyo/fetch-de-prueba'
import { crearCapitulos, crearVersion, FICHA, PORTADA, VERSIONES } from './lectura'

const BASE = '/novelas/{novel_id}/versiones/{version}'

/** Registra todo lo que pide la página `lectura` para una versión. */
export function responderLectura(prueba: FetchDePrueba, version = 2, modificados: readonly number[] = []) {
  prueba.responder('get', BASE, { status: 200, cuerpo: crearVersion(version, modificados) })
  prueba.responder('get', `${BASE}/capitulos`, { status: 200, cuerpo: crearCapitulos(modificados) })
  prueba.responder('get', `${BASE}/portada`, { status: 200, cuerpo: PORTADA })
  prueba.responder('get', `${BASE}/ficha`, { status: 200, cuerpo: FICHA })
  prueba.responder('get', '/novelas/{novel_id}/versiones', { status: 200, cuerpo: VERSIONES })
}
