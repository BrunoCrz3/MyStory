import { Link } from 'react-router-dom'
import { rutas } from '@/shared/config'
import { useGeneraciones } from '../api/novela'
import { generacionEnCurso } from '../model/generacion-en-curso'

/**
 * Avisa de que viene una versión nueva. Es un control: no se imprime ni entra en el PDF, y
 * no cuenta para `data-estado`, así que si la consulta falla la lectura no se entera.
 */
export function AvisoRegeneracion({ novelId }: { novelId: string }) {
  const generaciones = useGeneraciones(novelId)
  const enCurso = generaciones.isSuccess ? generacionEnCurso(generaciones.data) : undefined
  if (!enCurso) return null
  return (
    <aside role="status" aria-label="Regeneración en curso" className="aviso-regeneracion" data-controles="">
      <p>
        Se está preparando una versión nueva de esta novela. Esta sigue siendo la vigente hasta que la nueva se
        publique.
      </p>
      <Link to={rutas.progreso(novelId, enCurso.generacion_id)}>Ver el progreso</Link>
    </aside>
  )
}
