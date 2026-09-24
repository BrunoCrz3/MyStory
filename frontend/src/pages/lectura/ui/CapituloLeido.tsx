import type { Esquemas } from '@/shared/api'
import type { OrigenCambio } from '../model/peticion-cambio'
import { HechosDelCapitulo } from './HechosDelCapitulo'
import { MarcaModificado } from './MarcaModificado'

interface Props {
  capitulo: Esquemas['Capitulo']
  novelId: string
  version: number
  alPedirCambio: (origen: OrigenCambio) => void
}

export function CapituloLeido({ capitulo, novelId, version, alPedirCambio }: Props) {
  return (
    <section
      data-testid="capitulo"
      data-capitulo={capitulo.numero}
      id={`capitulo-${capitulo.numero}`}
      className="capitulo"
    >
      <header className="capitulo-cabecera">
        <h2 data-testid="capitulo-titulo">{capitulo.titulo ?? `Capítulo ${capitulo.numero}`}</h2>
        <MarcaModificado modificado={capitulo.modificado} />
      </header>
      {/* Solo el texto, sin añadidos: sobre él cuenta palabras paridad_pdf_web (CL-03). */}
      <div data-testid="capitulo-texto" className="capitulo-texto">
        {capitulo.texto ?? ''}
      </div>
      {/* Los controles van dentro del capítulo pero fuera de capitulo-texto (CL-03). */}
      <aside className="capitulo-controles" data-controles="">
        <HechosDelCapitulo
          novelId={novelId}
          version={version}
          capitulo={capitulo.numero}
          alElegir={(hecho) => alPedirCambio({ tipo: 'hecho', hecho, capitulo: capitulo.numero })}
        />
      </aside>
    </section>
  )
}
