import type { ReactNode } from 'react'
import type { EstadoFormulario, FilaElemento, FilaTextoLibre, TipoOcasion } from '../model/formulario'

interface Props {
  estado: EstadoFormulario
  cambiar: (siguiente: EstadoFormulario) => void
  /** La pregunta de reintento de cada `DatoFaltante`, por su `campo` del contrato. */
  faltantes?: ReadonlyMap<string, string>
}

const OCASIONES: { valor: TipoOcasion; etiqueta: string }[] = [
  { valor: 'cumpleanos', etiqueta: 'Cumpleaños' },
  { valor: 'boda', etiqueta: 'Boda' },
  { valor: 'aniversario', etiqueta: 'Aniversario' },
  { valor: 'jubilacion', etiqueta: 'Jubilación' },
  { valor: 'nacimiento', etiqueta: 'Nacimiento' },
  { valor: 'otra', etiqueta: 'Otra' },
]

function Faltante({ faltantes, campo }: { faltantes: ReadonlyMap<string, string> | undefined; campo: string }) {
  const pregunta = faltantes?.get(campo)
  if (pregunta === undefined) return null
  return (
    <span role="note" className="dato-faltante" data-campo={campo}>
      {pregunta || 'Falta este dato.'}
    </span>
  )
}

function Campo({ etiqueta, campo, faltantes, children }: { etiqueta: string; campo: string; faltantes?: ReadonlyMap<string, string> | undefined; children: (id: string) => ReactNode }) {
  const id = `campo-${campo}`
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      {children(id)}
      <Faltante faltantes={faltantes} campo={campo} />
    </div>
  )
}

export function FormularioBrief({ estado, cambiar, faltantes }: Props) {
  const poner = <K extends keyof EstadoFormulario>(clave: K, valor: EstadoFormulario[K]) => cambiar({ ...estado, [clave]: valor })

  const texto = (etiqueta: string, campo: string, valor: string, alCambiar: (v: string) => void, tipo = 'text') => (
    <Campo etiqueta={etiqueta} campo={campo} faltantes={faltantes}>
      {(id) => <input id={id} type={tipo} value={valor} onChange={(e) => alCambiar(e.target.value)} />}
    </Campo>
  )
  const area = (etiqueta: string, campo: string, valor: string, alCambiar: (v: string) => void) => (
    <Campo etiqueta={etiqueta} campo={campo} faltantes={faltantes}>
      {(id) => <textarea id={id} value={valor} onChange={(e) => alCambiar(e.target.value)} />}
    </Campo>
  )

  const cambiarElemento = (i: number, fila: FilaElemento) =>
    poner('elementos', estado.elementos.map((actual, j) => (j === i ? fila : actual)))
  const cambiarTexto = (i: number, fila: FilaTextoLibre) =>
    poner('textos_libres', estado.textos_libres.map((actual, j) => (j === i ? fila : actual)))

  return (
    <>
      <fieldset>
        <legend>Quién encarga</legend>
        {texto('Identificador del comprador', 'comprador.identificador', estado.comprador.identificador, (v) =>
          poner('comprador', { ...estado.comprador, identificador: v }),
        )}
        {texto('Relación con el destinatario', 'comprador.relacion_con_destinatario', estado.comprador.relacion_con_destinatario, (v) =>
          poner('comprador', { ...estado.comprador, relacion_con_destinatario: v }),
        )}
      </fieldset>

      <fieldset>
        <legend>Para quién</legend>
        {texto('Nombre', 'destinatario.nombre', estado.destinatario.nombre, (v) => poner('destinatario', { ...estado.destinatario, nombre: v }))}
        {texto('Edad', 'destinatario.edad', estado.destinatario.edad, (v) => poner('destinatario', { ...estado.destinatario, edad: v }), 'number')}
        {area('Rasgos (uno por línea)', 'destinatario.rasgos', estado.destinatario.rasgos, (v) => poner('destinatario', { ...estado.destinatario, rasgos: v }))}
        {area('Recuerdos (uno por línea)', 'destinatario.recuerdos', estado.destinatario.recuerdos, (v) => poner('destinatario', { ...estado.destinatario, recuerdos: v }))}
        {texto('Fecha de nacimiento', 'destinatario.fecha_nacimiento', estado.destinatario.fecha_nacimiento, (v) => poner('destinatario', { ...estado.destinatario, fecha_nacimiento: v }), 'date')}
      </fieldset>

      <fieldset>
        <legend>La ocasión</legend>
        <Campo etiqueta="Ocasión" campo="ocasion.tipo" faltantes={faltantes}>
          {(id) => (
            <select
              id={id}
              value={estado.ocasion.tipo}
              onChange={(e) => {
                const elegida = OCASIONES.find((o) => o.valor === e.target.value)
                poner('ocasion', { ...estado.ocasion, tipo: elegida ? elegida.valor : '' })
              }}
            >
              <option value="">Sin indicar</option>
              {OCASIONES.map((o) => (
                <option key={o.valor} value={o.valor}>
                  {o.etiqueta}
                </option>
              ))}
            </select>
          )}
        </Campo>
        {texto('Fecha de la ocasión', 'ocasion.fecha', estado.ocasion.fecha, (v) => poner('ocasion', { ...estado.ocasion, fecha: v }), 'date')}
        {texto('Tono esperado de la ocasión', 'ocasion.tono_esperado', estado.ocasion.tono_esperado, (v) => poner('ocasion', { ...estado.ocasion, tono_esperado: v }))}
      </fieldset>

      <fieldset>
        <legend>La novela</legend>
        {texto('Género', 'genero', estado.genero, (v) => poner('genero', v))}
        {texto('Tono', 'tono', estado.tono, (v) => poner('tono', v))}
        {area('Premisa', 'premisa', estado.premisa, (v) => poner('premisa', v))}
        {area('Dedicatoria', 'dedicatoria.texto', estado.dedicatoria.texto, (v) => poner('dedicatoria', { ...estado.dedicatoria, texto: v }))}
        {texto('Firma', 'dedicatoria.firma', estado.dedicatoria.firma, (v) => poner('dedicatoria', { ...estado.dedicatoria, firma: v }))}
      </fieldset>

      <fieldset>
        <legend>Elementos personalizados</legend>
        <Faltante faltantes={faltantes} campo="elementos_personalizados" />
        {estado.elementos.map((fila, i) => (
          <div key={i} className="fila">
            {texto(`Elemento personalizado ${i + 1}`, `elementos_personalizados.${i}.enunciado`, fila.enunciado, (v) => cambiarElemento(i, { ...fila, enunciado: v }))}
            <label>
              <input
                type="checkbox"
                aria-label={`Elemento ${i + 1} obligatorio`}
                checked={fila.obligatorio}
                onChange={(e) => cambiarElemento(i, { ...fila, obligatorio: e.target.checked })}
              />{' '}
              Obligatorio
            </label>
            <button type="button" onClick={() => poner('elementos', estado.elementos.filter((_, j) => j !== i))}>
              Quitar elemento {i + 1}
            </button>
          </div>
        ))}
        <button type="button" onClick={() => poner('elementos', [...estado.elementos, { enunciado: '', obligatorio: false }])}>
          Añadir elemento personalizado
        </button>
      </fieldset>

      <fieldset>
        <legend>Lo que no debe aparecer</legend>
        {area('Temas excluidos (uno por línea)', 'temas_excluidos', estado.temas_excluidos, (v) => poner('temas_excluidos', v))}
        {area('Palabras prohibidas (una por línea)', 'palabras_prohibidas', estado.palabras_prohibidas, (v) => poner('palabras_prohibidas', v))}
        {area('Reglas del mundo (una por línea)', 'reglas_mundo', estado.reglas_mundo, (v) => poner('reglas_mundo', v))}
      </fieldset>

      <fieldset>
        <legend>Texto libre</legend>
        <p className="nota">Una anécdota o una carta, tal como la escribirías. Se trata como datos, nunca como instrucciones.</p>
        {estado.textos_libres.map((fila, i) => (
          <div key={i} className="fila">
            {area(`Texto libre ${i + 1}`, `textos_libres.${i}.contenido`, fila.contenido, (v) => cambiarTexto(i, { ...fila, contenido: v }))}
            {texto(`Procedencia del texto libre ${i + 1}`, `textos_libres.${i}.procedencia`, fila.procedencia, (v) => cambiarTexto(i, { ...fila, procedencia: v }))}
            <button type="button" onClick={() => poner('textos_libres', estado.textos_libres.filter((_, j) => j !== i))}>
              Quitar texto libre {i + 1}
            </button>
          </div>
        ))}
        <button type="button" onClick={() => poner('textos_libres', [...estado.textos_libres, { contenido: '', procedencia: '' }])}>
          Añadir texto libre
        </button>
      </fieldset>

      <fieldset>
        <legend>Voz narrativa</legend>
        <Campo etiqueta="Persona narrativa" campo="voz_narrativa.persona" faltantes={faltantes}>
          {(id) => (
            <select id={id} value={estado.voz.persona} onChange={(e) => {
              const v = e.target.value
              poner('voz', { ...estado.voz, persona: v === 'primera' || v === 'segunda' || v === 'tercera' ? v : '' })
            }}>
              <option value="">Sin indicar</option>
              <option value="primera">Primera</option>
              <option value="segunda">Segunda</option>
              <option value="tercera">Tercera</option>
            </select>
          )}
        </Campo>
        <Campo etiqueta="Tiempo verbal" campo="voz_narrativa.tiempo_verbal" faltantes={faltantes}>
          {(id) => (
            <select id={id} value={estado.voz.tiempo_verbal} onChange={(e) => {
              const v = e.target.value
              poner('voz', { ...estado.voz, tiempo_verbal: v === 'presente' || v === 'pasado' ? v : '' })
            }}>
              <option value="">Sin indicar</option>
              <option value="presente">Presente</option>
              <option value="pasado">Pasado</option>
            </select>
          )}
        </Campo>
        <Campo etiqueta="Focalización" campo="voz_narrativa.focalizacion" faltantes={faltantes}>
          {(id) => (
            <select id={id} value={estado.voz.focalizacion} onChange={(e) => {
              const v = e.target.value
              poner('voz', { ...estado.voz, focalizacion: v === 'interna' || v === 'externa' || v === 'cero' ? v : '' })
            }}>
              <option value="">Sin indicar</option>
              <option value="interna">Interna</option>
              <option value="externa">Externa</option>
              <option value="cero">Cero</option>
            </select>
          )}
        </Campo>
      </fieldset>
    </>
  )
}
