import { Link, Navigate, useParams } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema, Cargando } from '@/shared/ui'
import { useGeneraciones, useNovela } from '../api/novela'
import { generacionEnCurso } from '../model/generacion-en-curso'

/**
 * `/novelas/:id`: al progreso de la generación en curso si la hay, aunque ya exista una
 * versión publicada; si no, a la versión vigente; y si aún no hay ninguna, a la última
 * generación.
 */
export function RedireccionNovela() {
  const { novelId = '' } = useParams()
  const novela = useNovela(novelId)
  const generaciones = useGeneraciones(novelId)

  if (novela.isError) return <AvisoProblema problema={problemaDe(novela.error)} novelId={novelId} />
  if (!novela.isSuccess) return <Cargando que="la novela" />
  const vigente = novela.data.version_vigente
  // Sin la lista de generaciones, la versión vigente sigue siendo un destino válido.
  if (generaciones.isError) {
    if (vigente != null) return <Navigate replace to={rutas.lectura(novelId, vigente)} />
    return <AvisoProblema problema={problemaDe(generaciones.error)} novelId={novelId} />
  }
  if (!generaciones.isSuccess) return <Cargando que="las generaciones" />
  const enCurso = generacionEnCurso(generaciones.data)
  if (enCurso) return <Navigate replace to={rutas.progreso(novelId, enCurso.generacion_id)} />
  if (vigente != null) return <Navigate replace to={rutas.lectura(novelId, vigente)} />
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
