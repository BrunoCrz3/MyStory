import { useParams } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { AvisoProblema } from '@/shared/ui'
import { useCapitulos, usePortada, useVersion } from '../api/lectura'
import { CapituloLeido } from './CapituloLeido'
import { Indice } from './Indice'
import { Portada } from './Portada'

/**
 * La versión entera en un solo documento (spec1.md § 4.4, CL-01): portada, índice y todos los
 * capítulos a la vez. `data-estado` es la señal que espera Playwright (CL-02).
 */
export function LecturaPage() {
  const { novelId = '', version: versionTexto = '' } = useParams()
  const version = Number(versionTexto)

  const datosVersion = useVersion(novelId, version)
  const capitulos = useCapitulos(novelId, version)
  const portada = usePortada(novelId, version)

  const consultas = [datosVersion, capitulos, portada]
  const fallida = consultas.find((consulta) => consulta.isError)
  const estado = fallida ? 'error' : consultas.every((consulta) => consulta.isSuccess) ? 'lista' : 'cargando'

  return (
    <article data-testid="lectura" data-estado={estado} data-novel-id={novelId} data-version={versionTexto}>
      {fallida && <AvisoProblema problema={problemaDe(fallida.error)} novelId={novelId} />}
      {portada.isSuccess && <Portada portada={portada.data} />}
      {datosVersion.isSuccess && <Indice capitulos={datosVersion.data.capitulos} />}
      {capitulos.isSuccess &&
        capitulos.data.map((capitulo) => <CapituloLeido key={capitulo.numero} capitulo={capitulo} />)}
    </article>
  )
}
