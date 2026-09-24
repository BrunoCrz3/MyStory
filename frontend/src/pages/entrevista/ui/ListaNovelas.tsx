import { Link } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema, Cargando } from '@/shared/ui'
import { useNovelas } from '../api/entrevista'

export function ListaNovelas() {
  const novelas = useNovelas()
  return (
    <section aria-label="Novelas" className="lista-novelas">
      <h2>Novelas</h2>
      {novelas.isPending && <Cargando que="las novelas" />}
      {novelas.isError && <AvisoProblema problema={problemaDe(novelas.error)} />}
      {novelas.isSuccess && novelas.data.items.length === 0 && <p>Aún no hay ninguna.</p>}
      {novelas.isSuccess && (
        <ul>
          {novelas.data.items.map((novela) => (
            <li key={novela.novel_id}>
              <Link to={rutas.novela(novela.novel_id)}>{novela.titulo ?? 'Sin título todavía'}</Link> · {novela.estado}
              {novela.version_vigente != null && ` · versión ${novela.version_vigente}`}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
