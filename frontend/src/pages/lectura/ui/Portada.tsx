import type { Esquemas } from '@/shared/api'

export function Portada({ portada }: { portada: Esquemas['Portada'] }) {
  return (
    <section data-testid="portada" className="portada">
      <h1 data-testid="portada-titulo">{portada.titulo}</h1>
      {portada.destinatario && <p className="portada-para">Para {portada.destinatario}</p>}
      {portada.ocasion && <p className="portada-ocasion">{portada.ocasion}</p>}
      <blockquote className="portada-dedicatoria-bloque">
        <p data-testid="portada-dedicatoria">{portada.dedicatoria.texto}</p>
        {portada.dedicatoria.firma && <footer>{portada.dedicatoria.firma}</footer>}
      </blockquote>
    </section>
  )
}
