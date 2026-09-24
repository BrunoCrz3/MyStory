import type { Esquemas } from '@/shared/api'
import { rutas } from '@/shared/config'

type Entrada = Esquemas['EntradaFicha']

function EntradaDeFicha({ entrada, tipo }: { entrada: Entrada; tipo: 'ficha-personaje' | 'ficha-lugar' }) {
  return (
    <li data-testid={tipo} data-nombre={entrada.nombre}>
      <strong>{entrada.nombre}</strong>
      {entrada.descripcion && <span>. {entrada.descripcion}</span>}{' '}
      <span className="ficha-capitulos">
        Aparece en{' '}
        {entrada.capitulos.map((numero, i) => (
          <span key={numero}>
            {i > 0 && ', '}
            <a data-testid="ficha-enlace-capitulo" data-capitulo={numero} href={rutas.capitulo(numero)}>
              capítulo {numero}
            </a>
          </span>
        ))}
      </span>
    </li>
  )
}

export function Ficha({ ficha }: { ficha: Esquemas['Ficha'] }) {
  return (
    <section data-testid="ficha" className="ficha" aria-label="Personajes y lugares">
      <h2>Personajes</h2>
      <ul>
        {ficha.personajes.map((entrada) => (
          <EntradaDeFicha key={entrada.nombre} entrada={entrada} tipo="ficha-personaje" />
        ))}
      </ul>
      <h2>Lugares</h2>
      <ul>
        {ficha.lugares.map((entrada) => (
          <EntradaDeFicha key={entrada.nombre} entrada={entrada} tipo="ficha-lugar" />
        ))}
      </ul>
    </section>
  )
}
