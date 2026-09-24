import { Link, Navigate, useParams } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema, Cargando } from '@/shared/ui'
import { useGeneraciones, useNovela } from '../api/novela'

/** `/novelas/:id`: a la versión vigente o, si aún no hay, a la última generación. */
export function RedireccionNovela() {
  const { novelId = '' } = useParams()
  const novela = useNovela(novelId)
  const sinVersion = novela.isSuccess && novela.data.version_vigente == null
  const generaciones = useGeneraciones(novelId, sinVersion)

  if (novela.isError) return <AvisoProblema problema={problemaDe(novela.error)} novelId={novelId} />
  if (!novela.isSuccess) return <Cargando que="la novela" />
  if (novela.data.version_vigente != null) {
    return <Navigate replace to={rutas.lectura(novelId, novela.data.version_vigente)} />
  }
  if (generaciones.isError) return <AvisoProblema problema={problemaDe(generaciones.error)} novelId={novelId} />
  if (!generaciones.isSuccess) return <Cargando que="las generaciones" />
  // El contrato las devuelve de la más reciente a la más antigua.
  const ultima = generaciones.data[0]
  if (ultima) return <Navigate replace to={rutas.progreso(novelId, ultima.generacion_id)} />
  return (
    <main>
      <p>Esta novela aún no se ha generado.</p>
      <Link to={rutas.entrevista()}>Volver a la entrevista</Link>
    </main>
  )
}
