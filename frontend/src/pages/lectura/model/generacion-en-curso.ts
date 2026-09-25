import type { Esquemas } from '@/shared/api'

/**
 * La generación que todavía puede cambiar, inicial o dirigida, o `undefined` si no hay
 * ninguna. La terminalidad es `es_terminal` del contrato, nunca el nombre del estado.
 */
export function generacionEnCurso(generaciones: readonly Esquemas['Generacion'][]) {
  return generaciones.find((generacion) => !generacion.es_terminal)
}
