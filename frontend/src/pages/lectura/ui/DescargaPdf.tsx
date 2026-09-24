import { problemaDe } from '@/shared/api'
import { AvisoProblema } from '@/shared/ui'
import { urlDeDescarga, useExportar } from '../api/exportacion'

export function DescargaPdf({ novelId, version }: { novelId: string; version: number }) {
  const exportar = useExportar(novelId, version)
  const exportacion = exportar.data

  return (
    <section role="region" aria-label="PDF" className="descarga-pdf" data-controles="">
      {!exportacion && (
        <button type="button" disabled={exportar.isPending} onClick={() => exportar.mutate()}>
          Descargar PDF
        </button>
      )}
      {exportar.isError && <AvisoProblema problema={problemaDe(exportar.error)} novelId={novelId} />}
      {exportacion?.estado === 'disponible' && (
        <a href={urlDeDescarga(novelId, version)} download>
          Descargar el PDF de la versión {version}
        </a>
      )}
      {exportacion?.estado === 'en-curso' && (
        <p>
          Se está generando el PDF.{' '}
          <button type="button" disabled={exportar.isPending} onClick={() => exportar.mutate()}>
            Volver a comprobar
          </button>
        </p>
      )}
      {exportacion?.estado === 'fallido' && <p>No se pudo generar el PDF de esta versión.</p>}
      {exportacion?.paridad_pdf_web != null && (
        <p>Paridad con la lectura web: {exportacion.paridad_pdf_web ? 'comprobada' : 'no superada'}</p>
      )}
    </section>
  )
}
