import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { screen, waitFor } from '@testing-library/react'
import { Rutas } from '@/app'
import { bloqueDeImpresion, tablaCl03 } from '../../apoyo/contrato-lectura'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { NOVEL_ID } from '../../datos/identificadores'
import { crearCapitulos, FICHA, PORTADA } from '../../datos/lectura'
import { responderLectura } from '../../datos/responder-lectura'

const MODIFICADOS = [3, 7] as const
const capitulos = crearCapitulos(MODIFICADOS)
const enlacesDeFicha = [...FICHA.personajes, ...FICHA.lugares].reduce((total, e) => total + e.capitulos.length, 0)

// Cuántos debe haber de cada uno con estos datos, según la columna «Cuántos» de CL-03.
const CUANTOS: Record<string, number> = {
  lectura: 1,
  portada: 1,
  'portada-titulo': 1,
  'portada-dedicatoria': 1,
  indice: 1,
  'indice-entrada': 10,
  ficha: 1,
  'ficha-personaje': FICHA.personajes.length,
  'ficha-lugar': FICHA.lugares.length,
  'ficha-enlace-capitulo': enlacesDeFicha,
  capitulo: 10,
  'capitulo-titulo': 10,
  'capitulo-texto': 10,
  'capitulo-modificado': MODIFICADOS.length * 2,
}

const padreConTestid = (nodo: Element) => nodo.parentElement?.closest('[data-testid]')?.getAttribute('data-testid')

async function montarLista() {
  const prueba = crearFetchDePrueba()
  responderLectura(prueba, 2, MODIFICADOS)
  renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
  const lectura = screen.getByTestId('lectura')
  expect(lectura).toHaveAttribute('data-estado', 'cargando')
  await waitFor(() => expect(lectura).toHaveAttribute('data-estado', 'lista'))
  return lectura
}

describe('contrato de lectura de spec1.md § 4.4 (CA-15)', () => {
  const tabla = tablaCl03()

  it('esta prueba cubre todas las filas de CL-03, ni una más', () => {
    expect(tabla.map((fila) => fila.testid).sort()).toEqual(Object.keys(CUANTOS).sort())
  })

  it.each(tabla.map((fila) => [fila.testid, fila] as const))('%s: número, padre y atributos', async (testid, fila) => {
    const lectura = await montarLista()
    const nodos = testid === 'lectura' ? [lectura] : screen.queryAllByTestId(testid)

    expect(nodos).toHaveLength(CUANTOS[testid]!)
    for (const nodo of nodos) {
      if (fila.padres.length > 0) expect(fila.padres).toContain(padreConTestid(nodo))
      for (const atributo of fila.atributos) expect(nodo).toHaveAttribute(atributo)
      if (fila.conId) expect(nodo).toHaveAttribute('id', `capitulo-${nodo.getAttribute('data-capitulo')}`)
    }
  })

  it('los numéricos son el entero del contrato, sin ceros a la izquierda', async () => {
    const lectura = await montarLista()
    expect(lectura).toHaveAttribute('data-novel-id', NOVEL_ID)
    expect(lectura).toHaveAttribute('data-version', '2')
    const capitulosDom = screen.getAllByTestId('capitulo')
    expect(capitulosDom.map((c) => c.getAttribute('data-capitulo'))).toEqual(capitulos.map((c) => String(c.numero)))
    for (const enlace of screen.getAllByTestId('ficha-enlace-capitulo')) {
      expect(enlace).toHaveAttribute('href', `#capitulo-${enlace.getAttribute('data-capitulo')}`)
    }
    for (const entrada of screen.getAllByTestId('indice-entrada')) {
      expect(entrada.querySelector('a')).toHaveAttribute('href', `#capitulo-${entrada.getAttribute('data-capitulo')}`)
    }
  })

  it('el contenido es el del contrato, sin añadidos', async () => {
    await montarLista()
    expect(screen.getByTestId('portada-titulo').textContent).toBe(PORTADA.titulo)
    expect(screen.getByTestId('portada-dedicatoria').textContent).toBe(PORTADA.dedicatoria.texto)
    expect(screen.getAllByTestId('capitulo-titulo').map((n) => n.textContent)).toEqual(capitulos.map((c) => c.titulo))
    expect(screen.getAllByTestId('capitulo-texto').map((n) => n.textContent)).toEqual(capitulos.map((c) => c.texto))
    expect(screen.getAllByTestId('ficha-personaje').map((n) => n.getAttribute('data-nombre'))).toEqual(
      FICHA.personajes.map((p) => p.nombre),
    )
    const conMarca = screen.getAllByTestId('capitulo-modificado').map((m) => padreConTestid(m))
    expect(conMarca.filter((p) => p === 'indice-entrada')).toHaveLength(2)
    expect(conMarca.filter((p) => p === 'capitulo')).toHaveLength(2)
  })

  it('un 404 deja la lectura en error', async () => {
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/9` })
    await waitFor(() => expect(screen.getByTestId('lectura')).toHaveAttribute('data-estado', 'error'))
  })
})

describe('hoja de impresión (CA-16, CL-04)', () => {
  const css = readFileSync(resolve(process.cwd(), 'src/pages/lectura/lectura.css'), 'utf-8')
  const impresion = bloqueDeImpresion(css).replace(/\s+/g, ' ')

  it('tiene un bloque @media print', () => {
    expect(impresion).not.toBe('')
  })

  it('muestra todo capítulo y empieza cada uno en página nueva', () => {
    expect(impresion).toMatch(/\[data-testid="capitulo"\] \{[^}]*display: block !important/)
    expect(impresion).toMatch(/\[data-testid="capitulo"\] \{[^}]*break-before: page/)
  })

  it('no imprime los controles interactivos', () => {
    expect(impresion).toMatch(/\[data-controles\] \{[^}]*display: none !important/)
  })

  it('los controles de la lectura llevan la marca que oculta la impresión', async () => {
    await montarLista()
    for (const control of [
      screen.getByRole('combobox', { name: 'Versión' }).closest('label'),
      screen.getByRole('region', { name: 'PDF' }),
      ...screen.getAllByRole('button', { name: 'Hechos de este capítulo' }).map((b) => b.closest('aside')),
    ]) {
      expect(control).toHaveAttribute('data-controles')
    }
  })

  it('la lectura carga la hoja', () => {
    const pagina = readFileSync(resolve(process.cwd(), 'src/pages/lectura/ui/LecturaPage.tsx'), 'utf-8')
    expect(pagina).toContain("import '../lectura.css'")
  })
})
