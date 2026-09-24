import { Link } from 'react-router-dom'
import type { Problema } from '@/shared/api'
import { rutas } from '@/shared/config'

interface Props {
  problema: Problema
  /** Novela del contexto, por si el problema trae `generacion_id` sin `novel_id`. */
  novelId?: string
}

/** Pinta un `Problema` tal como llega: sin reinterpretar su `type`. */
export function AvisoProblema({ problema, novelId }: Props) {
  const novela = problema.novel_id ?? novelId
  return (
    <div role="alert" className="aviso-problema">
      <p>
        <strong>{problema.title}</strong>
      </p>
      {problema.detail && <p>{problema.detail}</p>}
      {problema.generacion_id && novela && (
        <p>
          <Link to={rutas.progreso(novela, problema.generacion_id)}>Ver su progreso</Link>
        </p>
      )}
      {problema.traza_langfuse_id && <p>Traza: {problema.traza_langfuse_id}</p>}
    </div>
  )
}
