import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { crearCliente, ProveedorCliente } from '@/shared/api'
import { crearFetchDePrueba, type FetchDePrueba } from './fetch-de-prueba'

export const ORIGEN_DE_PRUEBA = 'http://prueba.local'

interface Opciones {
  ruta?: string
  prueba?: FetchDePrueba
  /** Para pruebas con temporizadores falsos. */
  avanzarTiempo?: (ms: number) => void
}

export function renderizar(ui: ReactElement, opciones: Opciones = {}) {
  const prueba = opciones.prueba ?? crearFetchDePrueba()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const cliente = crearCliente({ fetch: prueba.fetch, origen: ORIGEN_DE_PRUEBA })
  const usuario = userEvent.setup(opciones.avanzarTiempo ? { advanceTimers: opciones.avanzarTiempo } : {})
  const resultado = render(
    <QueryClientProvider client={queryClient}>
      <ProveedorCliente cliente={cliente}>
        <MemoryRouter initialEntries={[opciones.ruta ?? '/']}>{ui}</MemoryRouter>
      </ProveedorCliente>
    </QueryClientProvider>,
  )
  return { ...resultado, prueba, usuario }
}
