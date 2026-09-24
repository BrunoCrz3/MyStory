import { createContext, useContext, type ReactNode } from 'react'
import type { Cliente } from './cliente'

const ContextoCliente = createContext<Cliente | null>(null)

export function ProveedorCliente({ cliente, children }: { cliente: Cliente; children: ReactNode }) {
  return <ContextoCliente.Provider value={cliente}>{children}</ContextoCliente.Provider>
}

export function useCliente(): Cliente {
  const cliente = useContext(ContextoCliente)
  if (cliente === null) throw new Error('useCliente necesita un ProveedorCliente por encima')
  return cliente
}
