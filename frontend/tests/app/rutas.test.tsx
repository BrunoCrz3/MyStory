import { screen } from '@testing-library/react'
import { Rutas } from '@/app'
import { renderizar } from '../apoyo/render'
import { RutaActual } from '../apoyo/ruta-actual'
import { crearFetchDePrueba } from '../apoyo/fetch-de-prueba'
import { crearNovela, generacionEnCurso } from '../datos/novela'
import { GENERACION_ID, NOVEL_ID } from '../datos/identificadores'

const conRuta = (
  <>
    <Rutas />
    <RutaActual />
  </>
)

describe('rutas de la spec § 4', () => {
  it('/ pinta la entrevista', async () => {
    renderizar(conRuta, { ruta: '/' })
    expect(await screen.findByRole('heading', { level: 1, name: /entrevista/i })).toBeInTheDocument()
  })

  it('/novelas/:id/generaciones/:id pinta el progreso', async () => {
    renderizar(conRuta, { ruta: `/novelas/${NOVEL_ID}/generaciones/${GENERACION_ID}` })
    expect(await screen.findByRole('heading', { level: 1, name: /progreso/i })).toBeInTheDocument()
  })

  it('/novelas/:id/versiones/:v pinta la lectura', async () => {
    renderizar(conRuta, { ruta: `/novelas/${NOVEL_ID}/versiones/2` })
    expect(await screen.findByTestId('lectura')).toBeInTheDocument()
  })

  it('/novelas/:id redirige a la versión vigente', async () => {
    const prueba = crearFetchDePrueba()
    prueba.responder('get', '/novelas/{novel_id}', { status: 200, cuerpo: crearNovela(2) })
    renderizar(conRuta, { ruta: `/novelas/${NOVEL_ID}`, prueba })
    expect(await screen.findByText(`/novelas/${NOVEL_ID}/versiones/2`)).toBeInTheDocument()
  })

  it('/novelas/:id sin versión vigente redirige a la última generación', async () => {
    const prueba = crearFetchDePrueba()
    prueba.responder('get', '/novelas/{novel_id}', { status: 200, cuerpo: crearNovela(null) })
    prueba.responder('get', '/novelas/{novel_id}/generaciones', { status: 200, cuerpo: [generacionEnCurso()] })
    renderizar(conRuta, { ruta: `/novelas/${NOVEL_ID}`, prueba })
    expect(await screen.findByText(`/novelas/${NOVEL_ID}/generaciones/${GENERACION_ID}`)).toBeInTheDocument()
  })
})
