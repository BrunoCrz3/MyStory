import { useLocation } from 'react-router-dom'

/** Solo para pruebas: deja la ruta actual en el DOM para poder afirmar sobre ella. */
export function RutaActual() {
  const { pathname, hash } = useLocation()
  return <output data-testid="ruta-actual">{pathname + hash}</output>
}
