import { useQuery } from '@tanstack/react-query'
import { exigir, useCliente } from '@/shared/api'

/**
 * Sondea la generación al ritmo que ella misma dice. Se deja de sondear por `es_terminal`,
 * nunca por el nombre del estado (spec1 RF-PROC-05), y sin intervalo no se sondea: el
 * frontend no inventa uno.
 */
export function useGeneracion(novelId: string, generacionId: string) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['generacion', novelId, generacionId],
    queryFn: () =>
      exigir(
        cliente.GET('/novelas/{novel_id}/generaciones/{generacion_id}', {
          params: { path: { novel_id: novelId, generacion_id: generacionId } },
        }),
      ),
    refetchInterval: (query) => {
      const generacion = query.state.data
      if (!generacion || generacion.es_terminal || generacion.intervalo_sondeo_segundos == null) return false
      return generacion.intervalo_sondeo_segundos * 1000
    },
  })
}
