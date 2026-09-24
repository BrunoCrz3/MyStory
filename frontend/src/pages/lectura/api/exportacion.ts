import { useMutation } from '@tanstack/react-query'
import { exigir, PREFIJO_API, useCliente } from '@/shared/api'

/**
 * `exportarVersion` genera el PDF una vez por versión y, si ya existe, lo devuelve. Es
 * también como se consulta su estado (contrato, `descargarExport`). No se sondea: el
 * contrato no da intervalo y el frontend no inventa uno.
 */
export function useExportar(novelId: string, version: number) {
  const cliente = useCliente()
  return useMutation({
    mutationFn: () =>
      exigir(
        cliente.POST('/novelas/{novel_id}/versiones/{version}/export', {
          params: { path: { novel_id: novelId, version } },
        }),
      ),
  })
}

/**
 * La ruta de `descargarExport` bajo el proxy. Se construye con la ruta del contrato y no con
 * `url_descarga`, que es un `uri-reference` sin base declarada.
 */
export const urlDeDescarga = (novelId: string, version: number) =>
  `${PREFIJO_API}/novelas/${novelId}/versiones/${version}/export`
