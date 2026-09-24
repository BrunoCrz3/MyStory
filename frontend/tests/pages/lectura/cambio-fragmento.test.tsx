import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { ejemploDeCuerpo } from '../../apoyo/ejemplos'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { generacionDirigida, HECHO_CANDIDATO, SOLICITUD_POR_FRAGMENTO } from '../../datos/cambio'
import { ENUNCIADO_NUEVO, FRAGMENTO, NOVEL_ID } from '../../datos/identificadores'
import { textoDeCapitulo } from '../../datos/lectura'
import { responderLectura } from '../../datos/responder-lectura'

const CREAR = '/novelas/{novel_id}/solicitudes-cambio'
const CONFIRMAR = '/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}/confirmacion'

async function montar() {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2)
  prueba.responder('post', CREAR, { status: 201, cuerpo: SOLICITUD_POR_FRAGMENTO })
  prueba.responder('post', CONFIRMAR, { status: 202, cuerpo: generacionDirigida() })
  const montado = renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
  await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
  return montado
}

/** Selecciona `fragmento` dentro del texto de un capítulo, como haría el lector con el ratón. */
function seleccionar(texto: HTMLElement, fragmento: string) {
  const nodo = texto.firstChild!
  const inicio = (nodo.textContent ?? '').indexOf(fragmento)
  const rango = document.createRange()
  rango.setStart(nodo, inicio)
  rango.setEnd(nodo, inicio + fragmento.length)
  const seleccion = window.getSelection()!
  seleccion.removeAllRanges()
  seleccion.addRange(rango)
  fireEvent.mouseUp(texto)
}

describe('petición de cambio por fragmento (CA-09)', () => {
  it('seleccionar texto del capítulo 3 envía el cuerpo porFragmento y exige confirmar', async () => {
    const { prueba, usuario } = await montar()
    const capitulo3 = screen.getAllByTestId('capitulo')[2]!
    const texto = within(capitulo3).getByTestId('capitulo-texto')

    expect(within(capitulo3).queryByRole('button', { name: 'Pedir cambio' })).not.toBeInTheDocument()
    seleccionar(texto, FRAGMENTO)
    await usuario.click(await within(capitulo3).findByRole('button', { name: 'Pedir cambio' }))

    const panel = await screen.findByRole('region', { name: 'Petición de cambio' })
    await usuario.type(within(panel).getByRole('textbox', { name: 'Nuevo enunciado' }), ENUNCIADO_NUEVO)
    await usuario.click(within(panel).getByRole('button', { name: 'Ver qué capítulos cambian' }))

    expect(prueba.peticionesA('post', CREAR)[0]?.cuerpo).toEqual(
      ejemploDeCuerpo<Esquemas['NuevaSolicitudCambio']>(CREAR, 'post', 'porFragmento'),
    )
    expect(await within(panel).findByText(/Hecho que el sistema propone/)).toHaveTextContent(HECHO_CANDIDATO)
    expect(prueba.peticionesA('post', CONFIRMAR)).toHaveLength(0)

    await usuario.click(within(panel).getByRole('button', { name: 'Confirmar y regenerar' }))
    expect(prueba.peticionesA('post', CONFIRMAR)).toHaveLength(1)
  })

  it('el texto del capítulo sigue siendo solo Capitulo.texto', async () => {
    const { usuario } = await montar()
    const capitulo3 = screen.getAllByTestId('capitulo')[2]!
    const texto = within(capitulo3).getByTestId('capitulo-texto')
    seleccionar(texto, FRAGMENTO)
    await within(capitulo3).findByRole('button', { name: 'Pedir cambio' })
    await usuario.click(within(capitulo3).getByRole('button', { name: 'Pedir cambio' }))

    expect(texto.textContent).toBe(textoDeCapitulo(3))
  })

  it('una selección fuera del texto del capítulo no ofrece pedir cambio', async () => {
    await montar()
    const capitulo3 = screen.getAllByTestId('capitulo')[2]!
    seleccionar(within(capitulo3).getByTestId('capitulo-titulo'), 'Capítulo')
    fireEvent.mouseUp(within(capitulo3).getByTestId('capitulo-texto'))
    expect(within(capitulo3).queryByRole('button', { name: 'Pedir cambio' })).not.toBeInTheDocument()
  })
})
