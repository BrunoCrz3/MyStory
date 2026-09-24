import type { Esquemas } from '@/shared/api'
import { crearFetchDePrueba } from './fetch-de-prueba'
import { ejemploDeCuerpo, ejemploDeEsquema, ejemploDeProblema, ejemploDeRespuesta } from './ejemplos'

describe('ejemplos de specs/openapi.yaml', () => {
  it('lee el ejemplo enCurso de obtenerGeneracion', () => {
    const enCurso = ejemploDeRespuesta<Esquemas['Generacion']>(
      '/novelas/{novel_id}/generaciones/{generacion_id}', 'get', '200', 'enCurso',
    )
    expect(enCurso.estado).toBe('Escribiendo')
    expect(enCurso.capitulos_aceptados).toBe(3)
  })

  it('lee el ejemplo de un schema, de un cuerpo y de un problema', () => {
    expect(ejemploDeEsquema<Esquemas['BriefNovela']>('BriefNovela').comprador.identificador).toBe('comprador-0042')
    expect(ejemploDeEsquema<Esquemas['BriefNovelaParcial']>('BriefNovelaParcial').destinatario?.nombre).toBeUndefined()
    expect(ejemploDeCuerpo<Esquemas['NuevaSolicitudCambio']>('/novelas/{novel_id}/solicitudes-cambio', 'post', 'porHecho').capitulo_origen).toBe(3)
    expect(ejemploDeProblema('Conflicto').type).toBe('/problemas/generacion-en-curso')
  })
})

describe('fetch de prueba', () => {
  it('devuelve la respuesta registrada para su ruta y registra la petición', async () => {
    const prueba = crearFetchDePrueba()
    prueba.responder('post', '/novelas/{novel_id}/generaciones', { status: 202, cuerpo: { ok: true } })

    const respuesta = await prueba.fetch(new Request('http://prueba.local/api/novelas/abc/generaciones', {
      method: 'POST', body: JSON.stringify({ x: 1 }), headers: { 'Content-Type': 'application/json' },
    }))

    expect(respuesta.status).toBe(202)
    expect(await respuesta.json()).toEqual({ ok: true })
    expect(prueba.peticiones).toEqual([
      { metodo: 'POST', ruta: '/novelas/abc/generaciones', plantilla: '/novelas/{novel_id}/generaciones', query: {}, cuerpo: { x: 1 } },
    ])
  })

  it('devuelve un 404 problem+json para lo que no está registrado', async () => {
    const prueba = crearFetchDePrueba()
    const respuesta = await prueba.fetch(new Request('http://prueba.local/api/salud'))
    expect(respuesta.status).toBe(404)
    expect(respuesta.headers.get('Content-Type')).toBe('application/problem+json')
  })
})
