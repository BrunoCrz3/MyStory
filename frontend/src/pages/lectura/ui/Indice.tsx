import type { Esquemas } from '@/shared/api'
import { rutas } from '@/shared/config'
import { MarcaModificado } from './MarcaModificado'

export function Indice({ capitulos }: { capitulos: Esquemas['CapituloIndice'][] }) {
  return (
    <nav data-testid="indice" aria-label="Índice">
      <h2>Índice</h2>
      <ol>
        {capitulos.map((capitulo) => (
          <li key={capitulo.numero} data-testid="indice-entrada" data-capitulo={capitulo.numero}>
            {/* Ancla del propio documento, no ruta del router: CL-01 pide un solo documento. */}
            <a href={rutas.capitulo(capitulo.numero)}>{capitulo.titulo ?? `Capítulo ${capitulo.numero}`}</a>{' '}
            <MarcaModificado modificado={capitulo.modificado} />
          </li>
        ))}
      </ol>
    </nav>
  )
}
