import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { problemaDe } from '@/shared/api'
import { rutas } from '@/shared/config'
import { AvisoProblema } from '@/shared/ui'
import { useCrearYGenerar, useValidarBrief } from '../api/entrevista'
import { aBriefCompleto, aBriefParcial, FORMULARIO_VACIO, type EstadoFormulario } from '../model/formulario'
import { FormularioBrief } from './FormularioBrief'
import { ListaNovelas } from './ListaNovelas'
import { ResultadoValidacion } from './ResultadoValidacion'
import '../entrevista.css'

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
  const problema = crear.isError ? problemaDe(crear.error) : validar.isError ? problemaDe(validar.error) : undefined

  // Red de seguridad (spec 2, G1): los datos faltantes y las contradicciones se pintan
  // vengan en la respuesta que vengan —el 200 de la validación, un 400 o un 422—.
  const faltantes = [...(vigente?.datos_faltantes ?? []), ...(problema?.datos_faltantes ?? [])]
  const contradicciones = [...(vigente?.contradicciones ?? []), ...(problema?.contradicciones ?? [])]
  const preguntas = new Map(faltantes.map((dato) => [dato.campo, dato.pregunta_reintento ?? '']))

  function alValidar(evento: FormEvent) {
    evento.preventDefault()
    crear.reset()
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
        <div className="cabecera-formulario">{problema && <AvisoProblema problema={problema} />}</div>
        <FormularioBrief estado={estado} cambiar={setEstado} faltantes={preguntas} />
        <ResultadoValidacion
          faltantes={faltantes}
          contradicciones={contradicciones}
          sospechosos={vigente?.fragmentos_sospechosos ?? []}
          hechos={vigente?.hechos_extraidos ?? []}
        />
        <div className="acciones">
          <button type="submit" disabled={validar.isPending}>
            Validar
          </button>
          <button type="button" disabled={!completo || crear.isPending} onClick={alCrear}>
            Crear y generar
          </button>
        </div>
        {vigente?.valido && <p role="status">El brief está completo.</p>}
      </form>
      <ListaNovelas />
    </main>
  )
}
