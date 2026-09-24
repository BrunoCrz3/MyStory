import { render, screen } from '@testing-library/react'
import { App } from '@/app'

describe('arranque', () => {
  it('monta la aplicación y muestra el nombre del producto', () => {
    render(<App />)
    expect(screen.getByRole('banner')).toHaveTextContent('storyMaker')
  })
})
