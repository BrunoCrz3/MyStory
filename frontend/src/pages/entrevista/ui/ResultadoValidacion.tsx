import type { Esquemas } from '@/shared/api'

interface Props {
  faltantes: Esquemas['DatoFaltante'][]
  contradicciones: Esquemas['ContradiccionBrief'][]
  sospechosos: Esquemas['FragmentoSospechoso'][]
  hechos: Esquemas['ResultadoValidacionBrief']['hechos_extraidos']
}

/** Pinta lo que devolvió el backend, sin reinterpretarlo: aquí no se detecta nada. */
export function ResultadoValidacion({ faltantes, contradicciones, sospechosos, hechos }: Props) {
  return (
    <div className="resultado-validacion">
      {faltantes.length > 0 && (
        <section aria-label="Datos que faltan">
          <h2>Datos que faltan</h2>
          <ul>
            {faltantes.map((dato) => (
              <li key={dato.campo}>
                <code>{dato.campo}</code>
                {dato.pregunta_reintento && <> · {dato.pregunta_reintento}</>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {contradicciones.length > 0 && (
        <section aria-label="Contradicciones">
          <h2>Contradicciones</h2>
          <ul>
            {contradicciones.map((contradiccion, i) => (
              <li key={i}>
                <strong>{contradiccion.tipo}</strong> entre {contradiccion.campos.map((campo) => <code key={campo}>{campo} </code>)}
                {contradiccion.explicacion && <p>{contradiccion.explicacion}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {sospechosos.length > 0 && (
        <section aria-label="Fragmentos descartados">
          <h2>Fragmentos descartados</h2>
          <p>Del texto libre, estos fragmentos parecían instrucciones al sistema. Se han descartado y no se usarán.</p>
          <ul>
            {sospechosos.map((sospechoso, i) => (
              <li key={i}>
                <q>{sospechoso.fragmento}</q> · descartado: {sospechoso.motivo}
              </li>
            ))}
          </ul>
        </section>
      )}
      {hechos.length > 0 && (
        <section aria-label="Hechos extraídos">
          <h2>Hechos extraídos del texto libre</h2>
          <ul>
            {hechos.map((hecho, i) => (
              <li key={i}>{hecho.enunciado}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
