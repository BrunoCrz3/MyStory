import type { Esquemas } from '@/shared/api'
import { MarcaModificado } from './MarcaModificado'

export function CapituloLeido({ capitulo }: { capitulo: Esquemas['Capitulo'] }) {
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
    </section>
  )
}
