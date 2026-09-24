import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema } from '@/shared/ui'
import { useConfirmarSolicitud, useCrearSolicitud } from '../api/cambio'
import { cuerpoDeSolicitud, type OrigenCambio } from '../model/peticion-cambio'

interface Props {
  novelId: string
  origen: OrigenCambio
  alCerrar: () => void
}

/**
 * Dos pasos, y el segundo solo con el lector: pedir el análisis de impacto (no regenera
 * nada) y confirmarlo (encola la regeneración dirigida). TO-011: nunca se regenera solo.
 */
export function PanelCambio({ novelId, origen, alCerrar }: Props) {
  const [enunciado, setEnunciado] = useState('')
  const crear = useCrearSolicitud(novelId)
  const confirmar = useConfirmarSolicitud(novelId)
  const navegar = useNavigate()
  const solicitud = crear.data

  function pedirAnalisis(evento: FormEvent) {
    evento.preventDefault()
    crear.mutate(cuerpoDeSolicitud(origen, enunciado))
  }

  function confirmarCambio(solicitudId: string) {
    confirmar.mutate(solicitudId, {
      onSuccess: (generacion) => navegar(rutas.progreso(novelId, generacion.generacion_id)),
    })
  }

  const hechoMostrado = solicitud?.hecho_afectado?.enunciado ?? solicitud?.hecho_candidato

  return (
    <section role="region" aria-label="Petición de cambio" className="panel-cambio" data-controles="">
      <h2>Pedir un cambio</h2>
      <p>
        Desde el capítulo {origen.capitulo}:{' '}
        {origen.tipo === 'hecho' ? <q>{origen.hecho.enunciado}</q> : <q>{origen.fragmento}</q>}
      </p>
      {!solicitud && (
        <form onSubmit={pedirAnalisis}>
          <label>
            Nuevo enunciado
            <textarea required value={enunciado} onChange={(evento) => setEnunciado(evento.target.value)} />
          </label>
          <button type="submit" disabled={crear.isPending || enunciado.trim() === ''}>
            Ver qué capítulos cambian
          </button>
        </form>
      )}
      {crear.isError && <AvisoProblema problema={problemaDe(crear.error)} novelId={novelId} />}
      {solicitud && (
        <div className="analisis-impacto">
          {hechoMostrado && (
            <p>
              {solicitud.hecho_afectado ? 'Hecho que cambia: ' : 'Hecho que el sistema propone: '}
              <strong>{hechoMostrado}</strong>
            </p>
          )}
          <p>Nuevo: {solicitud.enunciado_nuevo}</p>
          <p>
            Capítulos que se reescribirán:{' '}
            {solicitud.analisis_impacto?.capitulos_afectados.map((numero, i) => (
              <span key={numero}>
                {i > 0 && ', '}
                <a href={rutas.capitulo(numero)}>capítulo {numero}</a>
              </span>
            ))}
          </p>
          <button type="button" disabled={confirmar.isPending} onClick={() => confirmarCambio(solicitud.solicitud_id)}>
            Confirmar y regenerar
          </button>
        </div>
      )}
      {confirmar.isError && <AvisoProblema problema={problemaDe(confirmar.error)} novelId={novelId} />}
      <button type="button" onClick={alCerrar}>
        Cancelar
      </button>
    </section>
  )
}
