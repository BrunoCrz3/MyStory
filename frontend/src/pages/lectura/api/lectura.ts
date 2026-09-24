import { useQuery } from '@tanstack/react-query'
import { exigir, useCliente } from '@/shared/api'

// Una versión publicada es inmutable (spec1 RNF-07): lo leído no caduca.
const INMUTABLE = { staleTime: Infinity } as const

const ruta = (novelId: string, version: number) => ({ path: { novel_id: novelId, version } })

export function useVersion(novelId: string, version: number) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['version', novelId, version],
    queryFn: () => exigir(cliente.GET('/novelas/{novel_id}/versiones/{version}', { params: ruta(novelId, version) })),
    ...INMUTABLE,
  })
}

export function useCapitulos(novelId: string, version: number) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['capitulos', novelId, version],
    queryFn: () =>
      exigir(cliente.GET('/novelas/{novel_id}/versiones/{version}/capitulos', { params: ruta(novelId, version) })),
    ...INMUTABLE,
  })
}

export function usePortada(novelId: string, version: number) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['portada', novelId, version],
    queryFn: () =>
      exigir(cliente.GET('/novelas/{novel_id}/versiones/{version}/portada', { params: ruta(novelId, version) })),
    ...INMUTABLE,
  })
}

export function useFicha(novelId: string, version: number) {
  const cliente = useCliente()
  return useQuery({
    queryKey: ['ficha', novelId, version],
    queryFn: () =>
      exigir(cliente.GET('/novelas/{novel_id}/versiones/{version}/ficha', { params: ruta(novelId, version) })),
    ...INMUTABLE,
  })
}
