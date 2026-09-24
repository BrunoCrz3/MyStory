import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { BrowserRouter, Link } from 'react-router-dom'
import { crearCliente, ProveedorCliente, type Cliente } from '@/shared/api'
import { rutas } from '@/shared/config'
import { Rutas } from './router'
import './estilos.css'

interface Props {
  /** Solo lo pasan las pruebas; en el navegador, el cliente contra el proxy `/api`. */
  cliente?: Cliente
}

export function App({ cliente }: Props) {
  const [queryClient] = useState(() => new QueryClient())
  const [clienteApi] = useState(() => cliente ?? crearCliente())
  return (
    <QueryClientProvider client={queryClient}>
      <ProveedorCliente cliente={clienteApi}>
        <BrowserRouter>
          <header className="cabecera" data-controles="">
            <Link to={rutas.entrevista()}>storyMaker</Link>
          </header>
          <Rutas />
        </BrowserRouter>
      </ProveedorCliente>
    </QueryClientProvider>
  )
}
