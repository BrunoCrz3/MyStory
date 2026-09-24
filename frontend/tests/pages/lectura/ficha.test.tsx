import { screen, waitFor, within } from '@testing-library/react'
import { Rutas } from '@/app'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { NOVEL_ID } from '../../datos/identificadores'
import { FICHA } from '../../datos/lectura'
import { responderLectura } from '../../datos/responder-lectura'

async function montar() {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2)
  renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
  await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'lista'))
  return within(screen.getByTestId('ficha'))
}

const enlacesDe = (entrada: HTMLElement) =>
  within(entrada)
    .getAllByTestId('ficha-enlace-capitulo')
    .map((enlace) => [enlace.getAttribute('data-capitulo'), enlace.getAttribute('href')])

describe('ficha de personajes y lugares (CA-07)', () => {
  it('un personaje de los capítulos 2 y 7 enlaza a los dos', async () => {
    const ficha = await montar()
    const personajes = ficha.getAllByTestId('ficha-personaje')
    expect(personajes).toHaveLength(FICHA.personajes.length)

    const primero = personajes[0]!
    expect(primero).toHaveAttribute('data-nombre', FICHA.personajes[0]!.nombre)
    expect(primero).toHaveTextContent(FICHA.personajes[0]!.descripcion)
    expect(enlacesDe(primero)).toEqual([
      ['2', '#capitulo-2'],
      ['7', '#capitulo-7'],
    ])
  })

  it('los lugares enlazan igual', async () => {
    const ficha = await montar()
    const lugares = ficha.getAllByTestId('ficha-lugar')
    expect(lugares).toHaveLength(1)
    expect(lugares[0]).toHaveAttribute('data-nombre', 'El puerto')
    expect(enlacesDe(lugares[0]!)).toEqual([
      ['1', '#capitulo-1'],
      ['3', '#capitulo-3'],
      ['10', '#capitulo-10'],
    ])
  })

  it('la lectura no está lista sin la ficha', async () => {
    const prueba = crearFetchDePrueba()
    responderLectura(prueba, 2)
    prueba.responder('get', '/novelas/{novel_id}/versiones/{version}/ficha', { status: 404, cuerpo: { type: '/problemas/version-no-encontrada', title: 'Versión no encontrada', status: 404 } })
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
    await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'error'))
  })
})
