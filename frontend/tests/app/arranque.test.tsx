import { render, screen } from '@testing-library/react'
import { App } from '@/app'
import { crearCliente } from '@/shared/api'
import { crearFetchDePrueba } from '../apoyo/fetch-de-prueba'
import { ORIGEN_DE_PRUEBA } from '../apoyo/render'

describe('arranque', () => {
  it('monta la aplicación y muestra el nombre del producto', () => {
    const cliente = crearCliente({ fetch: crearFetchDePrueba().fetch, origen: ORIGEN_DE_PRUEBA })
    render(<App cliente={cliente} />)
    expect(screen.getByRole('banner')).toHaveTextContent('storyMaker')
  })
})
