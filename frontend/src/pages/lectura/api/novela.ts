import { useQuery } from '@tanstack/react-query'
import { exigir, useCliente } from '@/shared/api'
import { generacionEnCurso } from '../model/generacion-en-curso'

export function useNovela(novelId: string) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['novela', novelId],
    queryFn: () => exigir(cliente.GET('/novelas/{novel_id}', { params: { path: { novel_id: novelId } } })),
  })
}

/** Mientras haya una generación en curso se vuelve a preguntar al ritmo que ella pide. */
export function useGeneraciones(novelId: string, activa = true) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['generaciones', novelId],
    queryFn: () =>
      exigir(cliente.GET('/novelas/{novel_id}/generaciones', { params: { path: { novel_id: novelId } } })),
    enabled: activa,
    refetchInterval: (consulta) => {
      const segundos = generacionEnCurso(consulta.state.data ?? [])?.intervalo_sondeo_segundos
      return segundos ? segundos * 1000 : false
    },
  })
}
