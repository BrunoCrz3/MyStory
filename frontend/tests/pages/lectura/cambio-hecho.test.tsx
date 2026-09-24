import { screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { ejemploDeCuerpo, ejemploDeProblema } from '../../apoyo/ejemplos'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { RutaActual } from '../../apoyo/ruta-actual'
import { generacionDirigida, SOLICITUD_POR_HECHO } from '../../datos/cambio'
import { ENUNCIADO_NUEVO, GENERACION_DIRIGIDA_ID, NOVEL_ID } from '../../datos/identificadores'
import { HECHOS_CAPITULO_3 } from '../../datos/lectura'
import { responderLectura } from '../../datos/responder-lectura'

const CREAR = '/novelas/{novel_id}/solicitudes-cambio'
const CONFIRMAR = '/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}/confirmacion'
const HECHOS = '/novelas/{novel_id}/versiones/{version}/hechos'

async function montar(respuestaCrear: { status: number; cuerpo: unknown } = { status: 201, cuerpo: SOLICITUD_POR_HECHO }) {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2)
  prueba.responder('get', HECHOS, { status: 200, cuerpo: HECHOS_CAPITULO_3 })
  prueba.responder('post', CREAR, respuestaCrear)
  prueba.responder('post', CONFIRMAR, { status: 202, cuerpo: generacionDirigida() })
  const montado = renderizar(
    <>
      <Rutas />
      <RutaActual />
    </>,
    { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba },
  )
  await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
  return montado
}

async function pedirCambioDelHecho(usuario: ReturnType<typeof renderizar>['usuario']) {
  const capitulo3 = screen.getAllByTestId('capitulo')[2]!
  await usuario.click(within(capitulo3).getByRole('button', { name: 'Hechos de este capítulo' }))
  await usuario.click(await within(capitulo3).findByRole('button', { name: /cambiar «El perro se llama Luna»/i }))
  const panel = await screen.findByRole('region', { name: 'Petición de cambio' })
  await usuario.type(within(panel).getByRole('textbox', { name: 'Nuevo enunciado' }), ENUNCIADO_NUEVO)
  await usuario.click(within(panel).getByRole('button', { name: 'Ver qué capítulos cambian' }))
  return panel
}

describe('petición de cambio por hecho (CA-10, CA-11)', () => {
  it('pide los hechos del capítulo, envía el cuerpo porHecho y exige confirmar', async () => {
    const { prueba, usuario } = await montar()
    const panel = await pedirCambioDelHecho(usuario)

    expect(prueba.peticionesA('get', HECHOS)[0]?.query).toEqual({ capitulo: '3' })
    expect(prueba.peticionesA('post', CREAR)[0]?.cuerpo).toEqual(
      ejemploDeCuerpo<Esquemas['NuevaSolicitudCambio']>(CREAR, 'post', 'porHecho'),
    )

    expect(await within(panel).findByText(/Hecho que cambia/)).toHaveTextContent('El perro se llama Luna')
    const afectados = within(panel).getAllByRole('link', { name: /capítulo \d+/ })
    expect(afectados.map((a) => a.getAttribute('href'))).toEqual(['#capitulo-3', '#capitulo-7'])
    expect(prueba.peticionesA('post', CONFIRMAR)).toHaveLength(0)

    await usuario.click(within(panel).getByRole('button', { name: 'Confirmar y regenerar' }))

    expect(prueba.peticionesA('post', CONFIRMAR)).toHaveLength(1)
    expect(await screen.findByText(`/novelas/${NOVEL_ID}/generaciones/${GENERACION_DIRIGIDA_ID}`)).toBeInTheDocument()
  })

  it('cancelar cierra el panel sin confirmar nada', async () => {
    const { prueba, usuario } = await montar()
    const panel = await pedirCambioDelHecho(usuario)
    await within(panel).findByText(/Hecho que cambia/)

    await usuario.click(within(panel).getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('region', { name: 'Petición de cambio' })).not.toBeInTheDocument()
    expect(prueba.peticionesA('post', CONFIRMAR)).toHaveLength(0)
  })

  it('un 409 generacion-en-curso se muestra con enlace a la que corre', async () => {
    const { usuario } = await montar({ status: 409, cuerpo: ejemploDeProblema('Conflicto') })
    const panel = await pedirCambioDelHecho(usuario)

    const aviso = await within(panel).findByRole('alert')
    expect(aviso).toHaveTextContent('Ya hay una generación en curso para esta novela')
    expect(within(aviso).getByRole('link', { name: /ver su progreso/i })).toHaveAttribute(
      'href',
      `/novelas/${NOVEL_ID}/generaciones/8f1c0b6e-4f6a-4c8e-9a1e-2b7d5f0c3a11`,
    )
  })
})
