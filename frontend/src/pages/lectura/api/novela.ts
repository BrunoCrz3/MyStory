import { useQuery } from '@tanstack/react-query'
import { exigir, useCliente } from '@/shared/api'

export function useNovela(novelId: string) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['novela', novelId],
    queryFn: () => exigir(cliente.GET('/novelas/{novel_id}', { params: { path: { novel_id: novelId } } })),
  })
}

export function useGeneraciones(novelId: string, activa: boolean) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['generaciones', novelId],
    queryFn: () =>
      exigir(cliente.GET('/novelas/{novel_id}/generaciones', { params: { path: { novel_id: novelId } } })),
    enabled: activa,
  })
}
