import { useMutation, useQuery } from '@tanstack/react-query'
import { exigir, useCliente, type Esquemas } from '@/shared/api'

export function useHechosDelCapitulo(novelId: string, version: number, capitulo: number, activa: boolean) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['hechos', novelId, version, capitulo],
    queryFn: () =>
      exigir(
        cliente.GET('/novelas/{novel_id}/versiones/{version}/hechos', {
          params: { path: { novel_id: novelId, version }, query: { capitulo } },
        }),
      ),
    enabled: activa,
    staleTime: Infinity,
  })
}

/** No regenera nada: devuelve el análisis de impacto para que el lector confirme. */
export function useCrearSolicitud(novelId: string) {
  const cliente = useCliente()
  return useMutation({
    mutationFn: (cuerpo: Esquemas['NuevaSolicitudCambio']) =>
      exigir(
        cliente.POST('/novelas/{novel_id}/solicitudes-cambio', {
          params: { path: { novel_id: novelId } },
          body: cuerpo,
        }),
      ),
  })
}

/** Lo único que regenera: encola la generación dirigida y la devuelve para sondearla. */
export function useConfirmarSolicitud(novelId: string) {
  const cliente = useCliente()
  return useMutation({
    mutationFn: (solicitudId: string) =>
      exigir(
        cliente.POST('/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}/confirmacion', {
          params: { path: { novel_id: novelId, solicitud_id: solicitudId } },
        }),
      ),
  })
}
