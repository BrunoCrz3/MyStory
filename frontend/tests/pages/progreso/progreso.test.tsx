import { act, screen } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { GENERACION_ID, NOVEL_ID } from '../../datos/identificadores'
import { generacionDetenida, generacionEnCurso } from '../../datos/novela'

const RUTA = `/novelas/${NOVEL_ID}/generaciones/${GENERACION_ID}`
const PLANTILLA = '/novelas/{novel_id}/generaciones/{generacion_id}'

function montar(generacion: Esquemas['Generacion']) {
  const prueba = crearFetchDePrueba()
  prueba.responder('get', PLANTILLA, { status: 200, cuerpo: generacion })
  renderizar(<Rutas />, { ruta: RUTA, prueba, avanzarTiempo: vi.advanceTimersByTime })
  return prueba
}

describe('progreso de una generación (CA-05)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('en curso: muestra 3 de 10 y vuelve a pedir pasado su intervalo', async () => {
    const prueba = montar(generacionEnCurso())

    expect(await screen.findByText('3 de 10')).toBeInTheDocument()
    expect(screen.getByText('Escribiendo')).toBeInTheDocument()
    expect(prueba.peticionesA('get', PLANTILLA)).toHaveLength(1)

    await act(() => vi.advanceTimersByTimeAsync(3000))

    expect(prueba.peticionesA('get', PLANTILLA)).toHaveLength(2)
  })

  it('detenida: muestra por qué y deja de pedir', async () => {
    const prueba = montar(generacionDetenida())

    expect(await screen.findByText('limite-de-intentos-agotado')).toBeInTheDocument()
    await act(() => vi.advanceTimersByTimeAsync(30_000))

    expect(prueba.peticionesA('get', PLANTILLA)).toHaveLength(1)
    expect(screen.queryByRole('link', { name: /leer la versión/i })).not.toBeInTheDocument()
  })

  it('publicada: enlaza a la lectura de la versión resultante', async () => {
    montar({
      ...generacionEnCurso(),
      estado: 'Publicada',
      es_terminal: true,
      intervalo_sondeo_segundos: null,
      capitulos_aceptados: 10,
      version_resultante: 1,
    })

    expect(await screen.findByRole('link', { name: 'Leer la versión 1' })).toHaveAttribute(
      'href',
      `/novelas/${NOVEL_ID}/versiones/1`,
    )
  })

  it('dirigida: muestra los capítulos a regenerar', async () => {
    montar({ ...generacionEnCurso(), tipo: 'dirigida', capitulos_a_regenerar: [3, 7] })

    expect(await screen.findByText('3, 7')).toBeInTheDocument()
  })

  it('un 404 se pinta como problema', async () => {
    renderizar(<Rutas />, { ruta: RUTA, avanzarTiempo: vi.advanceTimersByTime })
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

describe('consumo de la generación (TO-055)', () => {
  it('rotula tokens y coste como estimados', async () => {
    montar({ ...generacionEnCurso(), tokens_consumidos: 12345, coste_usd: 1.5 })

    expect(await screen.findByText('Tokens (estimados)')).toBeInTheDocument()
    expect(screen.getByText('Coste en USD (estimado)')).toBeInTheDocument()
    expect(screen.getByText(/son estimaciones/i)).toBeInTheDocument()
    expect(screen.queryByText('Tokens')).not.toBeInTheDocument()
  })
})

describe('reintentos del capítulo en curso (TO-057)', () => {
  it('dice que son reintentos y qué cuentan', async () => {
    montar({ ...generacionEnCurso(), intentos_capitulo_actual: 2 })

    expect(await screen.findByText('Reintentos del capítulo actual')).toBeInTheDocument()
    expect(screen.getByText(/0 es el primer borrador/i)).toBeInTheDocument()
    expect(screen.getByText(/correcciones del editor y reescrituras/i)).toBeInTheDocument()
    expect(screen.queryByText('Intentos del capítulo actual')).not.toBeInTheDocument()
  })
})
