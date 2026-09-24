import { screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { crearFetchDePrueba, type RespuestaDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { NOVEL_ID } from '../../datos/identificadores'
import { responderLectura } from '../../datos/responder-lectura'

const EXPORT = '/novelas/{novel_id}/versiones/{version}/export'

const exportacion = (estado: Esquemas['Exportacion']['estado'], paridad: boolean | null = null) =>
  ({ version: 2, estado, url_descarga: null, generado_en: null, paridad_pdf_web: paridad }) satisfies Esquemas['Exportacion']

async function montar(...respuestas: RespuestaDePrueba[]) {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2)
  let llamada = 0
  prueba.responder('post', EXPORT, () => respuestas[Math.min(llamada++, respuestas.length - 1)]!)
  const montado = renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
  await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
  const region = screen.getByRole('region', { name: 'PDF' })
  await montado.usuario.click(within(region).getByRole('button', { name: 'Descargar PDF' }))
  return { ...montado, region }
}

describe('descarga del PDF (CA-13)', () => {
  it('disponible: enlaza a descargarExport de esa versión y muestra la paridad', async () => {
    const { region } = await montar({ status: 200, cuerpo: exportacion('disponible', true) })
    expect(await within(region).findByRole('link', { name: /descargar el pdf de la versión 2/i })).toHaveAttribute(
      'href',
      `/api/novelas/${NOVEL_ID}/versiones/2/export`,
    )
    expect(region).toHaveTextContent('Paridad con la lectura web: comprobada')
  })

  it('en curso: ofrece volver a comprobar y no sondea por su cuenta', async () => {
    const { prueba, usuario, region } = await montar(
      { status: 202, cuerpo: exportacion('en-curso') },
      { status: 200, cuerpo: exportacion('disponible') },
    )
    const volver = await within(region).findByRole('button', { name: 'Volver a comprobar' })
    expect(region).toHaveTextContent('Se está generando')
    await new Promise((resolver) => setTimeout(resolver, 300))
    expect(prueba.peticionesA('post', EXPORT)).toHaveLength(1)

    await usuario.click(volver)

    expect(await within(region).findByRole('link', { name: /descargar el pdf/i })).toBeInTheDocument()
    expect(prueba.peticionesA('post', EXPORT)).toHaveLength(2)
  })

  it('fallido: lo dice', async () => {
    const { region } = await montar({ status: 200, cuerpo: exportacion('fallido', false) })
    expect(await within(region).findByText('No se pudo generar el PDF de esta versión.')).toBeInTheDocument()
    expect(region).toHaveTextContent('Paridad con la lectura web: no superada')
    expect(within(region).queryByRole('link')).not.toBeInTheDocument()
  })
})
