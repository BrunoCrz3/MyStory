// Lee la tabla CL-03 de specs/spec1.md § 4.4 en cada ejecución. La tabla es del backend; si
// cambia, la prueba del contrato de lectura se entera sin copiar nada aquí.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

export interface FilaCl03 {
  testid: string
  padres: string[]
  atributos: string[]
  conId: boolean
}

const entreComillas = (celda: string) => [...celda.matchAll(/`([^`]+)`/g)].map((m) => m[1] ?? '')

export function tablaCl03(): FilaCl03[] {
  const spec = readFileSync(resolve(process.cwd(), '../specs/spec1.md'), 'utf-8')
  const inicio = spec.indexOf('**CL-03')
  if (inicio < 0) throw new Error('specs/spec1.md no tiene CL-03')
  const lineas = spec.slice(inicio).split('\n')
  const cabecera = lineas.findIndex((linea) => linea.startsWith('| `data-testid`'))
  const filas: FilaCl03[] = []
  for (const linea of lineas.slice(cabecera + 2)) {
    if (!linea.startsWith('|')) break
    const [, testid = '', , dentro = '', atributos = ''] = linea.split('|').map((celda) => celda.trim())
    filas.push({
      testid: entreComillas(testid)[0] ?? '',
      padres: entreComillas(dentro),
      atributos: entreComillas(atributos).filter((token) => token.startsWith('data-')),
      conId: atributos.includes('`id="'),
    })
  }
  return filas
}

/** El bloque de un `@media print`, con las llaves equilibradas. */
export function bloqueDeImpresion(css: string): string {
  const inicio = css.indexOf('@media print')
  if (inicio < 0) return ''
  const apertura = css.indexOf('{', inicio)
  let profundidad = 0
  for (let i = apertura; i < css.length; i++) {
    if (css[i] === '{') profundidad++
    if (css[i] === '}' && --profundidad === 0) return css.slice(apertura + 1, i)
  }
  return ''
}
