import { screen } from '@testing-library/react'
import { aProblema, ErrorDeApi } from '@/shared/api'
import { AvisoProblema } from '@/shared/ui'
import { ejemploDeProblema } from '../../apoyo/ejemplos'
import { renderizar } from '../../apoyo/render'

describe('lectura de problem+json', () => {
  it('un 409 del ejemplo Conflicto conserva su type y su generacion_id', () => {
    const problema = aProblema(ejemploDeProblema('Conflicto'), 409)
    expect(problema.type).toBe('/problemas/generacion-en-curso')
    expect(problema.generacion_id).toBe('8f1c0b6e-4f6a-4c8e-9a1e-2b7d5f0c3a11')
  })

  it('un cuerpo que no es un problema se representa como error-interno con su status', () => {
    const problema = aProblema('<html>Bad Gateway</html>', 502)
    expect(problema).toMatchObject({ type: '/problemas/error-interno', status: 502 })
  })

  it('ErrorDeApi lleva el problema', () => {
    const error = new ErrorDeApi(aProblema(ejemploDeProblema('Conflicto'), 409))
    expect(error.problema.status).toBe(409)
    expect(error.message).toBe('Ya hay una generación en curso para esta novela')
  })
})

describe('AvisoProblema', () => {
  it('pinta title, detail y el enlace al progreso de la generación que corre', () => {
    renderizar(<AvisoProblema problema={aProblema(ejemploDeProblema('Conflicto'), 409)} />)
    const aviso = screen.getByRole('alert')
    expect(aviso).toHaveTextContent('Ya hay una generación en curso para esta novela')
    expect(aviso).toHaveTextContent('Consulta su progreso en lugar de lanzar otra.')
    expect(screen.getByRole('link', { name: /ver su progreso/i })).toHaveAttribute(
      'href',
      '/novelas/3a7b1e42-9c33-4f51-8a2d-6e0b9c4d7f18/generaciones/8f1c0b6e-4f6a-4c8e-9a1e-2b7d5f0c3a11',
    )
  })

  it('pinta la traza de Langfuse de un error interno', () => {
    renderizar(<AvisoProblema problema={aProblema(ejemploDeProblema('ErrorInterno'), 500)} />)
    expect(screen.getByRole('alert')).toHaveTextContent('tr-7d21')
  })
})
