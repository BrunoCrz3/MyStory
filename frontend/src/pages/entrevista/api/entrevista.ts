import { useMutation, useQuery } from '@tanstack/react-query'
import { exigir, useCliente, type Esquemas } from '@/shared/api'

export function useNovelas() {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['novelas'],
    queryFn: () => exigir(cliente.GET('/novelas')),
  })
}

/** Acepta el brief parcial y devuelve lo que falta en un 200 (TO-037). No crea nada. */
export function useValidarBrief() {
  const cliente = useCliente()
  return useMutation({
    mutationFn: (brief: Esquemas['BriefNovelaParcial']) => exigir(cliente.POST('/briefs/validacion', { body: brief })),
  })
}

/** Crea la novela con el brief completo y, con el 201, lanza su generación. */
export function useCrearYGenerar() {
  const cliente = useCliente()
  return useMutation({
    mutationFn: async (brief: Esquemas['BriefNovela']) => {
      const novela = await exigir(cliente.POST('/novelas', { body: brief }))
      const generacion = await exigir(
        cliente.POST('/novelas/{novel_id}/generaciones', { params: { path: { novel_id: novela.novel_id } } }),
      )
      return { novela, generacion }
    },
  })
}
