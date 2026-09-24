import { useState } from 'react'
import { problemaDe, type Esquemas } from '@/shared/api'
import { AvisoProblema, Cargando } from '@/shared/ui'
import { useHechosDelCapitulo } from '../api/cambio'

interface Props {
  novelId: string
  version: number
  capitulo: number
  alElegir: (hecho: Esquemas['Hecho']) => void
}

export function HechosDelCapitulo({ novelId, version, capitulo, alElegir }: Props) {
  const [abierto, setAbierto] = useState(false)
  const hechos = useHechosDelCapitulo(novelId, version, capitulo, abierto)
  return (
    <div className="hechos-del-capitulo">
      <button type="button" aria-expanded={abierto} onClick={() => setAbierto((valor) => !valor)}>
        Hechos de este capítulo
      </button>
      {abierto && hechos.isPending && <Cargando que="los hechos" />}
      {abierto && hechos.isError && <AvisoProblema problema={problemaDe(hechos.error)} novelId={novelId} />}
      {abierto && hechos.isSuccess && (
        <ul>
          {hechos.data.length === 0 && <li>Este capítulo no usa ningún hecho registrado.</li>}
          {hechos.data.map((hecho) => (
            <li key={hecho.hecho_id}>
              {hecho.enunciado}{' '}
              <button type="button" aria-label={`Cambiar «${hecho.enunciado}»`} onClick={() => alElegir(hecho)}>
                Cambiar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
