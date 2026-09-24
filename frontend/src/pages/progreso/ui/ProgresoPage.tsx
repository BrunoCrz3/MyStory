import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema, Cargando } from '@/shared/ui'
import { useGeneracion } from '../api/generacion'
import '../progreso.css'

function Dato({ nombre, children }: { nombre: string; children: ReactNode }) {
  return (
    <>
      <dt>{nombre}</dt>
      <dd>{children}</dd>
    </>
  )
}

export function ProgresoPage() {
  const { novelId = '', generacionId = '' } = useParams()
  const generacion = useGeneracion(novelId, generacionId)

  return (
    <main className="pagina-progreso">
      <h1>Progreso de la generación</h1>
      {generacion.isError && <AvisoProblema problema={problemaDe(generacion.error)} novelId={novelId} />}
      {generacion.isPending && <Cargando que="la generación" />}
      {generacion.isSuccess && (
        <>
          <dl className="progreso">
            <Dato nombre="Tipo">{generacion.data.tipo}</Dato>
            <Dato nombre="Estado">{generacion.data.estado}</Dato>
            <Dato nombre="Capítulos aceptados">
              {`${generacion.data.capitulos_aceptados} de ${generacion.data.total_capitulos}`}
            </Dato>
            {generacion.data.capitulo_actual != null && (
              <Dato nombre="Capítulo actual">{generacion.data.capitulo_actual}</Dato>
            )}
            {generacion.data.intentos_capitulo_actual != null && (
              <Dato nombre="Intentos del capítulo actual">{generacion.data.intentos_capitulo_actual}</Dato>
            )}
            {generacion.data.checkpoint != null && <Dato nombre="Checkpoint">{generacion.data.checkpoint}</Dato>}
            {generacion.data.capitulos_a_regenerar && generacion.data.capitulos_a_regenerar.length > 0 && (
              <Dato nombre="Capítulos a regenerar">{generacion.data.capitulos_a_regenerar.join(', ')}</Dato>
            )}
            {generacion.data.tokens_consumidos != null && (
              <Dato nombre="Tokens">{generacion.data.tokens_consumidos}</Dato>
            )}
            {generacion.data.coste_usd != null && <Dato nombre="Coste (USD)">{generacion.data.coste_usd}</Dato>}
            {generacion.data.detenida_por && <Dato nombre="Detenida por">{generacion.data.detenida_por}</Dato>}
            {generacion.data.traza_langfuse_id && (
              <Dato nombre="Traza">{generacion.data.traza_langfuse_id}</Dato>
            )}
          </dl>
          {!generacion.data.es_terminal && generacion.data.intervalo_sondeo_segundos != null && (
            <p role="status">Se actualiza cada {generacion.data.intervalo_sondeo_segundos} s.</p>
          )}
          {generacion.data.version_resultante != null && (
            <p>
              <Link to={rutas.lectura(novelId, generacion.data.version_resultante)}>
                {`Leer la versión ${generacion.data.version_resultante}`}
              </Link>
            </p>
          )}
        </>
      )}
    </main>
  )
}
