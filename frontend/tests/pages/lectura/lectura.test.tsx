import { screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { NOVEL_ID } from '../../datos/identificadores'
import { PORTADA, textoDeCapitulo } from '../../datos/lectura'
import { responderLectura } from '../../datos/responder-lectura'

function montar() {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2)
  renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
  return prueba
}

async function lecturaLista() {
  const lectura = screen.getByTestId('lectura')
  await waitFor(() => expect(lectura).toHaveAttribute('data-estado', 'lista'))
  return lectura
}

describe('lectura: raíz, portada, índice y capítulos', () => {
  it('la raíz lleva la novela y la versión (CL-02)', async () => {
    montar()
    const lectura = await lecturaLista()
    expect(lectura).toHaveAttribute('data-novel-id', NOVEL_ID)
    expect(lectura).toHaveAttribute('data-version', '2')
  })

  it('el índice tiene diez entradas que enlazan a su capítulo (CA-06)', async () => {
    montar()
    await lecturaLista()
    const entradas = within(screen.getByTestId('indice')).getAllByTestId('indice-entrada')
    expect(entradas).toHaveLength(10)
    entradas.forEach((entrada, i) => {
      expect(entrada).toHaveAttribute('data-capitulo', String(i + 1))
      expect(within(entrada).getByRole('link')).toHaveAttribute('href', `#capitulo-${i + 1}`)
    })
  })

  it('los diez capítulos están en el DOM a la vez, cada uno en su ancla (CA-06, CL-01)', async () => {
    montar()
    await lecturaLista()
    const capitulos = screen.getAllByTestId('capitulo')
    expect(capitulos).toHaveLength(10)
    capitulos.forEach((capitulo, i) => {
      expect(capitulo).toHaveAttribute('id', `capitulo-${i + 1}`)
      expect(capitulo).toHaveAttribute('data-capitulo', String(i + 1))
      expect(within(capitulo).getByTestId('capitulo-titulo')).toHaveTextContent(`Capítulo ${i + 1}`)
      expect(within(capitulo).getByTestId('capitulo-texto').textContent).toBe(textoDeCapitulo(i + 1))
    })
  })

  it('la portada muestra título, dedicatoria y firma (CA-08)', async () => {
    montar()
    await lecturaLista()
    const portada = screen.getByTestId('portada')
    expect(within(portada).getByTestId('portada-titulo').textContent).toBe(PORTADA.titulo)
    expect(within(portada).getByTestId('portada-dedicatoria').textContent).toBe(PORTADA.dedicatoria.texto)
    expect(portada).toHaveTextContent(PORTADA.dedicatoria.firma ?? '')
  })

  it('empieza en cargando', () => {
    montar()
    expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'cargando')
  })
})
