import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema } from '@/shared/ui'
import { useCrearYGenerar, useValidarBrief } from '../api/entrevista'
import { aBriefCompleto, aBriefParcial, FORMULARIO_VACIO, type EstadoFormulario } from '../model/formulario'
import { FormularioBrief } from './FormularioBrief'
import { ListaNovelas } from './ListaNovelas'

export function EntrevistaPage() {
  const [estado, setEstado] = useState<EstadoFormulario>(FORMULARIO_VACIO)
  // Lo que se envió en la última validación: si el formulario cambia, esa validación caduca.
  const [validadoCon, setValidadoCon] = useState<string | null>(null)
  const validar = useValidarBrief()
  const crear = useCrearYGenerar()
  const navegar = useNavigate()

  const parcial = aBriefParcial(estado)
  const vigente = validadoCon === JSON.stringify(parcial) ? validar.data : undefined
  const completo = vigente?.valido ? aBriefCompleto(parcial) : null

  function alValidar(evento: FormEvent) {
    evento.preventDefault()
    setValidadoCon(JSON.stringify(parcial))
    validar.mutate(parcial)
  }

  function alCrear() {
    if (!completo) return
    crear.mutate(completo, {
      onSuccess: ({ novela, generacion }) => navegar(rutas.progreso(novela.novel_id, generacion.generacion_id)),
    })
  }

  return (
    <main>
      <h1>Entrevista</h1>
      <form aria-label="Brief de la novela" onSubmit={alValidar} noValidate>
        <FormularioBrief estado={estado} cambiar={setEstado} />
        <div className="acciones">
          <button type="submit" disabled={validar.isPending}>
            Validar
          </button>
          <button type="button" disabled={!completo || crear.isPending} onClick={alCrear}>
            Crear y generar
          </button>
        </div>
        {vigente?.valido && <p role="status">El brief está completo.</p>}
        {validar.isError && <AvisoProblema problema={problemaDe(validar.error)} />}
        {crear.isError && <AvisoProblema problema={problemaDe(crear.error)} />}
      </form>
      <ListaNovelas />
    </main>
  )
}
