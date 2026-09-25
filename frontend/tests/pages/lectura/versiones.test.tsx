import { screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { RutaActual } from '../../apoyo/ruta-actual'
import { ENUNCIADO_NUEVO, NOVEL_ID } from '../../datos/identificadores'
import { responderVersiones } from '../../datos/responder-lectura'

async function montar() {
  const prueba = crearFetchDePrueba()
  responderVersiones(prueba, { 1: [], 2: [3, 7] })
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

const numerosConMarca = (testid: string) =>
  screen
    .getAllByTestId(testid)
    .filter((nodo) => within(nodo).queryByTestId('capitulo-modificado') !== null)
    .map((nodo) => nodo.getAttribute('data-capitulo'))

describe('capítulos modificados y versiones (CA-12)', () => {
  it('solo los capítulos 3 y 7 llevan la marca, en el índice y en su cabecera', async () => {
    await montar()
    expect(screen.getAllByTestId('capitulo-modificado')).toHaveLength(4)
    expect(numerosConMarca('indice-entrada')).toEqual(['3', '7'])
    expect(numerosConMarca('capitulo')).toEqual(['3', '7'])
    expect(screen.getAllByTestId('capitulo-modificado')[0]).toHaveTextContent('Modificado en esta versión')
  })

  it('el selector lista las versiones con su motivo y abre la 1 entera', async () => {
    const { usuario } = await montar()
    const selector = await screen.findByRole('combobox', { name: 'Versión' })
    expect(within(selector).getByRole('option', { name: new RegExp(ENUNCIADO_NUEVO) })).toHaveValue('2')
    expect(within(selector).getByRole('option', { name: /versión 1/i })).toHaveValue('1')

    await usuario.selectOptions(selector, '1')

    expect(await screen.findByText(`/novelas/${NOVEL_ID}/versiones/1`)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-version', '1'))
    await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
    expect(screen.getAllByTestId('capitulo')).toHaveLength(10)
    expect(screen.queryAllByTestId('capitulo-modificado')).toHaveLength(0)
  })
})

describe('versión candidata (TO-045, contrato 1.2.0)', () => {
  it('la lectura abre una candidata por su URL, como la pinta render_visual', async () => {
    const prueba = crearFetchDePrueba()
    responderVersiones(prueba, { 1: [], 2: [3, 7], 3: [3] }, [3])
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/3`, prueba })

    await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
    expect(screen.getByTestId('lectura')).toHaveAttribute('data-version', '3')
    expect(screen.getAllByTestId('capitulo')).toHaveLength(10)
    expect(numerosConMarca('indice-entrada')).toEqual(['3'])
  })

  it('el selector solo ofrece las versiones publicadas que da listarVersiones', async () => {
    const prueba = crearFetchDePrueba()
    responderVersiones(prueba, { 1: [], 2: [3, 7], 3: [3] }, [3])
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/3`, prueba })

    const selector = await screen.findByRole('combobox', { name: 'Versión' })
    const valores = within(selector)
      .getAllByRole('option')
      .map((opcion) => opcion.getAttribute('value'))
    expect(valores).toEqual(['2', '1'])
  })
})
